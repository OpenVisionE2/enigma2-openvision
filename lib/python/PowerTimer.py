# -*- coding: utf-8 -*-
from bisect import insort
from os import fsync, remove, rename
from os.path import isfile
from sys import maxsize
from time import ctime, localtime, mktime, time

from enigma import eActionMap, quitMainloop

import NavigationInstance
from timer import Timer, TimerEntry
from Components.config import config
from Components.Harddisk import internalHDDNotSleeping
from Components.TimerSanityCheck import TimerSanityCheck
from Screens.MessageBox import MessageBox
import Screens.Standby
from Tools.Directories import SCOPE_CONFIG, fileReadXML, resolveFilename, isPluginInstalled
from Tools.Notifications import AddNotification, AddNotificationWithUniqueIDCallback, AddPopup
from Tools.XMLTools import stringToXML

MODULE_NAME = __name__.split(".")[-1]


# Parses an event, and gives out a (begin, end)-tuple.
#
def parseEvent(event):
	begin = event.getBeginTime()
	end = begin + event.getDuration()
	return (begin, end)


class AFTEREVENT:
	NONE = 0
	WAKEUPTOSTANDBY = 1
	STANDBY = 2
	DEEPSTANDBY = 3


class TIMERTYPE:
	NONE = 0
	WAKEUP = 1
	WAKEUPTOSTANDBY = 2
	AUTOSTANDBY = 3
	AUTODEEPSTANDBY = 4
	STANDBY = 5
	DEEPSTANDBY = 6
	REBOOT = 7
	RESTART = 8


class PowerTimer(Timer):
	def __init__(self):
		Timer.__init__(self)
		self.timersFilename = resolveFilename(SCOPE_CONFIG, "pm_timers.xml")
		self.loadTimers()
		if self.getWakeupEPGImport is not None:
			self.getWakeupEPGImport()

	def loadTimers(self):
		timersDom = fileReadXML(self.timersFilename, source=MODULE_NAME)
		if timersDom is None:
			if not isfile(self.timersFilename):
				return
			AddPopup(_("The timer file 'pm_timers.xml' is corrupt and could not be loaded."), type=MessageBox.TYPE_ERROR, timeout=0, id="TimerLoadFailed")
			print("[PowerTimer] Error: Loading 'pm_timers.xml' failed!")
			try:
				rename(self.timersFilename, "%s_bad" % self.timersFilename)
			except (IOError, OSError) as err:
				print("[PowerTimer] Error %d: Renaming broken timer file failed!  (%s)" % (err.errno, err.strerror))
			return
		check = True
		overlapText = [_("Timer overlaps detected in pm_timers.xml!"), _("Please check all timers!")]
		for timer in timersDom.findall("timer"):
			newTimer = self.createTimer(timer)
			if (self.record(newTimer, True, dosave=False) is not None) and (check == True):
				AddPopup("\n".join(overlapText), type=MessageBox.TYPE_ERROR, timeout=0, id="TimerLoadFailed")
				check = False  # At moment it is enough when the message is displayed one time.

	def loadTimer(self):
		return self.loadTimers()

	def saveTimers(self):
		timerList = ["<?xml version=\"1.0\" ?>", "<timers>"]
		for timer in self.timer_list + self.processed_timers:
			if timer.dontSave:  # Some timers (instant records) don't want to be saved so skip them.
				continue
			timerEntry = []
			timerEntry.append("timertype=\"%s\"" % stringToXML({
				TIMERTYPE.WAKEUP: "wakeup",
				TIMERTYPE.WAKEUPTOSTANDBY: "wakeuptostandby",
				TIMERTYPE.AUTOSTANDBY: "autostandby",
				TIMERTYPE.AUTODEEPSTANDBY: "autodeepstandby",
				TIMERTYPE.STANDBY: "standby",
				TIMERTYPE.DEEPSTANDBY: "deepstandby",
				TIMERTYPE.REBOOT: "reboot",
				TIMERTYPE.RESTART: "restart"
			}[timer.timerType]))
			timerEntry.append("begin=\"%d\"" % timer.begin)
			timerEntry.append("end=\"%d\"" % timer.end)
			timerEntry.append("repeated=\"%d\"" % timer.repeated)
			timerEntry.append("afterevent=\"%s\"" % stringToXML({
				AFTEREVENT.NONE: "nothing",
				AFTEREVENT.WAKEUPTOSTANDBY: "wakeuptostandby",
				AFTEREVENT.STANDBY: "standby",
				AFTEREVENT.DEEPSTANDBY: "deepstandby"
			}[timer.afterEvent]))
			timerEntry.append("disabled=\"%d\"" % timer.disabled)
			timerEntry.append("autosleepinstandbyonly=\"%s\"" % timer.autosleepinstandbyonly)
			timerEntry.append("autosleepdelay=\"%s\"" % timer.autosleepdelay)
			timerEntry.append("autosleeprepeat=\"%s\"" % timer.autosleeprepeat)
			timerList.append("\t<timer %s>" % " ".join(timerEntry))
			# Handle repeat entries, which never end and so never get pruned by cleanupDaily.
			# Repeating timers get autosleeprepeat="repeated" or repeated="127" (daily) or
			# "31" (weekdays) [dow bitmap] etc.
			ignoreBefore = 0
			if config.recording.keep_timers.value > 0:
				if timer.autosleeprepeat == "repeated" or int(timer.repeated) > 0:
					ignoreBefore = time() - config.recording.keep_timers.value * 86400
			for logTime, logCode, logMsg in timer.log_entries:
				if logTime < ignoreBefore:
					continue
				timerList.append("\t\t<log code=\"%d\" time=\"%d\">%s</log>" % (int(logCode), int(logTime), stringToXML(str(logMsg))))
			timerList.append("\t</timer>")
		timerList.append("</timers>\n")
		# Should this code also use a writeLock as for the regular timers?
		file = open("%s.writing" % self.timersFilename, "w")
		file.write("\n".join(timerList))
		file.flush()
		fsync(file.fileno())
		file.close()
		rename("%s.writing" % self.timersFilename, self.timersFilename)

	def saveTimer(self):
		return self.saveTimers()

	def createTimer(self, timerDom):
		begin = int(timerDom.get("begin"))
		end = int(timerDom.get("end"))
		disabled = bool(int(timerDom.get("disabled", False)))
		afterevent = {
			"nothing": AFTEREVENT.NONE,
			"wakeuptostandby": AFTEREVENT.WAKEUPTOSTANDBY,
			"standby": AFTEREVENT.STANDBY,
			"deepstandby": AFTEREVENT.DEEPSTANDBY
		}.get(timerDom.get("afterevent", "nothing"), "nothing")
		timertype = {
			"wakeup": TIMERTYPE.WAKEUP,
			"wakeuptostandby": TIMERTYPE.WAKEUPTOSTANDBY,
			"autostandby": TIMERTYPE.AUTOSTANDBY,
			"autodeepstandby": TIMERTYPE.AUTODEEPSTANDBY,
			"standby": TIMERTYPE.STANDBY,
			"deepstandby": TIMERTYPE.DEEPSTANDBY,
			"reboot": TIMERTYPE.REBOOT,
			"restart": TIMERTYPE.RESTART
		}.get(timerDom.get("timertype", "wakeup"), "wakeup")
		# If this is a repeating auto* timer then start it in 30 secs,
		# which means it will start its repeating countdown from when enigma2
		# starts each time rather then waiting until anything left over from the
		# last enigma2 running.
		autosleeprepeat = timerDom.get("autosleeprepeat", "once")
		if autosleeprepeat == "repeated":
			begin = time() + int(timerDom.get("autosleepdelay", "0"))
			if end <= begin:
				end = begin
		entry = PowerTimerEntry(begin, end, disabled, afterevent, timertype)
		entry.autosleepinstandbyonly = timerDom.get("autosleepinstandbyonly", "no")
		entry.autosleepdelay = int(timerDom.get("autosleepdelay", "0"))
		entry.autosleeprepeat = autosleeprepeat
		entry.repeated = 0 if entry.autosleeprepeat == "repeated" else int(timerDom.get("repeated"))  # Ensure timer repeated is cleared if we have an autosleeprepeat.
		for log in timerDom.findall("log"):
			from Tools.PyVerHelper import getPyVS
			msg = log.text.strip().encode("UTF-8").decode() if getPyVS() >= 3 else log.text.strip().encode("UTF-8")
			entry.log_entries.append((int(log.get("time")), int(log.get("code")), msg))
		return entry

	def doActivate(self, w):
		# When activating a timer which has already passed, simply
		# abort the timer.  Don't run trough all the stages.
		if w.shouldSkip():
			w.state = PowerTimerEntry.StateEnded
		else:
			# When active returns true, this means "accepted".
			# Otherwise, the current state is kept.
			# The timer entry itself will fix up the delay.
			if w.activate():
				w.state += 1
		try:
			self.timer_list.remove(w)
		except Exception:
			print("[PowerTimer] Remove list failed!")
		if w.state < PowerTimerEntry.StateEnded:  # Did this timer reached the last state?
			insort(self.timer_list, w)  # No, sort it into active list.
		else:  # Yes, process repeated, and re-add.
			if w.repeated:
				# If we have saved original begin/end times for a backed off timer
				# restore those values now.
				if hasattr(w, "real_begin"):
					w.begin = w.real_begin
					w.end = w.real_end
					# Now remove the temporary holding attributes.
					del w.real_begin
					del w.real_end
				w.processRepeated()
				w.state = PowerTimerEntry.StateWaiting
				self.addTimerEntry(w)
			else:
				# Remove old timers as set in config.
				self.cleanupDaily(config.recording.keep_timers.value)  # DEBUG: This method does not appear to be defined!!!
				insort(self.processed_timers, w)
		self.stateChanged(w)

	def isProcessing(self, exceptTimer=None, endedTimer=None):
		isRunning = False
		for timer in self.timer_list:
			if timer.timerType != TIMERTYPE.AUTOSTANDBY and timer.timerType != TIMERTYPE.AUTODEEPSTANDBY and timer.timerType != exceptTimer and timer.timerType != endedTimer:
				if timer.isRunning():
					isRunning = True
					break
		return isRunning

	def getNextZapTime(self):
		now = time()
		for timer in self.timer_list:
			if timer.begin < now:
				continue
			return timer.begin
		return -1

	def getNextWakeupSleepTimer(self): # Start wakeup from deepstandby or standby with [SleepTimerEdit].
		now = localtime(time())
		current_week_day = int(now.tm_wday)
		return int(mktime((now.tm_year, now.tm_mon, now.tm_mday, config.usage.wakeup_time[current_week_day].value[0], config.usage.wakeup_time[current_week_day].value[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst))) # Timer config.usage.wakeup_time.value.

	def getNextPowerTimeActive(self):
		now = time()
		for timer in self.timer_list:
			if timer.timerType != TIMERTYPE.AUTOSTANDBY or timer.timerType != TIMERTYPE.AUTODEEPSTANDBY:
				next_act = timer.getNextWakeup()
				if next_act < now:
					continue
				return next_act
		if config.usage.wakeup_enabled.value != "no":
			if self.getNextWakeupSleepTimer() > now: # [SleepTimerEdit] Start wake up.
				if Screens.Standby.inStandby and config.usage.wakeup_enabled.value == "standby": # [SleepTimerEdit] wake up from "standby".
					return self.getNextWakeupSleepTimer()
				elif config.usage.wakeup_enabled.value != "standby": # [SleepTimerEdit] wake up from "deepstandby" or "yes".
					return self.getNextWakeupSleepTimer()
		return -1 # [StartEnigma] Not time powerTimerList or sleepTimerList.

	def getNextPowerManagerTime(self):
		nextTime = self.getNextPowerTimeActive()
		fakeTime = time() + 300
		if hasattr(self, "timeshift") and config.usage.timeshift_start_delay.value:
			return nextTime if 0 < nextTime < fakeTime else fakeTime
		return nextTime

	def isNextPowerManagerAfterEventActionAuto(self):
		now = time()
		# t = None
		for timer in self.timer_list:
			if timer.timerType == TIMERTYPE.WAKEUPTOSTANDBY or timer.afterEvent == AFTEREVENT.WAKEUPTOSTANDBY:
				return True
		return False

	def record(self, entry, ignoreTSC=False, dosave=True):
		entry.timeChanged()
		print("[PowerTimer] Entry '%s'." % str(entry))
		entry.Timer = self
		self.addTimerEntry(entry)
		if dosave:
			self.saveTimers()
		return None

	def removeEntry(self, entry):
		print("[PowerTimer] Remove entry '%s'." % str(entry))
		entry.repeated = False  # Avoid re-enqueuing.
		entry.autoincrease = False
		entry.abort()  # Abort timer.  This sets the end time to current time, so timer will be stopped.
		if entry.state != entry.StateEnded:
			self.timeChanged(entry)
		# print("[PowerTimer] State: %s." % entry.state)
		# print("[PowerTimer] In processed: %s." % entry in self.processed_timers)
		# print("[PowerTimer] In running: %s." % entry in self.timer_list)
		if entry.state != 3:  # Disable timer first.
			entry.disable()
		if not entry.dontSave:  # Auto increase instant timer if possible.
			for timer in self.timer_list:
				if timer.setAutoincreaseEnd():
					self.timeChanged(timer)
		if entry in self.processed_timers:  # Now the timer should be in the processed_timers list, remove it from there.
			self.processed_timers.remove(entry)
		self.saveTimers()

	def shutdown(self):
		self.saveTimers()

	def cleanup(self):
		Timer.cleanup(self)
		self.saveTimers()

	def cleanupDaily(self, days):
		Timer.cleanupDaily(self, days)
		self.saveTimers()

	def getWakeupEPGImport(self):
		now = localtime(time())
		begin = int(mktime(localtime(time())))
		if isPluginInstalled("EPGImport") and config.misc.prev_wakeup_time_type.value == 2:
			importwakeup = config.plugins.epgimport.wakeup.value
			importtime = int(mktime((now.tm_year, now.tm_mon, now.tm_mday, importwakeup[0], importwakeup[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))
			if not config.misc.RestartUI.value and \
				not config.plugins.epgimport.shutdown.value and \
				not config.plugins.epgimport.standby_afterwakeup.value:
					if not isPluginInstalled("EPGRefresh"):
						return AddPopup(_("Plugin EPGImport actived EPG import and woke up your receiver"), type=MessageBox.TYPE_INFO, timeout=0)
					else:
						refreshwakeup = config.plugins.epgrefresh.begin.value
						refreshtime = int(mktime((now.tm_year, now.tm_mon, now.tm_mday, refreshwakeup[0], refreshwakeup[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))
						if (refreshtime - begin) < 360 and (refreshtime - begin) > 0:
							return None
						elif (importtime - begin) < 240 and (importtime - begin) > 0:
							return AddPopup(_("Plugin EPGImport actived EPG import and woke up your receiver"), type=MessageBox.TYPE_INFO, timeout=0)
		return None


class PowerTimerEntry(TimerEntry, object):
	def __init__(self, begin, end, disabled=False, afterEvent=AFTEREVENT.NONE, timerType=TIMERTYPE.WAKEUP, checkOldTimers=False):
		TimerEntry.__init__(self, int(begin), int(end))
		if checkOldTimers:
			if self.begin < time() - 1209600:
				self.begin = int(time())
		if self.end < self.begin:
			self.end = self.begin
		self.dontSave = False
		self.disabled = disabled
		self.timer = None
		self.__record_service = None
		self.start_prepare = 0
		self.timerType = timerType
		self.afterEvent = afterEvent
		self.autoincrease = False
		self.autoincreasetime = 3600 * 24  # 1 day.
		self.autosleepinstandbyonly = "no"
		self.autosleepdelay = 60
		self.autosleeprepeat = "once"
		self.log_entries = []
		self.resetState()

	def __repr__(self):
		timertype = {
			TIMERTYPE.WAKEUP: "wakeup",
			TIMERTYPE.WAKEUPTOSTANDBY: "wakeuptostandby",
			TIMERTYPE.AUTOSTANDBY: "autostandby",
			TIMERTYPE.AUTODEEPSTANDBY: "autodeepstandby",
			TIMERTYPE.STANDBY: "standby",
			TIMERTYPE.DEEPSTANDBY: "deepstandby",
			TIMERTYPE.REBOOT: "reboot",
			TIMERTYPE.RESTART: "restart"
		}[self.timerType]
		if not self.disabled:
			return "PowerTimerEntry(type=%s, begin=%s)" % (timertype, ctime(self.begin))
		else:
			return "PowerTimerEntry(type=%s, begin=%s Disabled)" % (timertype, ctime(self.begin))

	def log(self, code, msg):
		if config.powertimerlog.actived.value:
			self.log_entries.append((int(time()), code, msg))
		else:
			self.log_entries = []

	def do_backoff(self):  # Back-off an auto-repeat timer by its autosleepdelay, not 5, 10, 20, 30 mins.
		if self.autosleeprepeat == "repeated" and self.timerType in (TIMERTYPE.AUTOSTANDBY, TIMERTYPE.AUTODEEPSTANDBY):
			self.backoff = int(self.autosleepdelay) * 60
		elif self.backoff == 0:
			self.backoff = 5 * 60
		else:
			self.backoff *= 2
			if self.backoff > 1800:
				self.backoff = 1800
		self.log(10, "Backoff, retry in %d minutes." % (self.backoff // 60))
		# If this is the first backoff of a repeat timer remember the original
		# begin/end times, so that we can use *these* when setting up the repeat.
		if self.repeated != 0 and not hasattr(self, "real_begin"):
			self.real_begin = self.begin
			self.real_end = self.end
		# Delay the timer by the back-off time.
		self.begin = time() + self.backoff
		if self.end <= self.begin:
			self.end = self.begin

	def activate(self):
		next_state = self.state + 1
		self.log(5, "Activating state %d." % next_state)
		if next_state == self.StatePrepared and (self.timerType == TIMERTYPE.AUTOSTANDBY or self.timerType == TIMERTYPE.AUTODEEPSTANDBY):
			# This is the first action for an auto* timer.
			# It binds any key press to keyPressed(), which resets the timer delay,
			# and sets the initial delay.
			eActionMap.getInstance().bindAction("", -maxsize - 1, self.keyPressed)
			self.begin = time() + int(self.autosleepdelay) * 60
			if self.end <= self.begin:
				self.end = self.begin
		if next_state == self.StatePrepared:
			self.log(6, "Prepare okay, waiting for begin.")
			self.next_activation = self.begin
			self.backoff = 0
			return True
		elif next_state == self.StateRunning:
			self.wasPowerTimerWakeup = False
			if isfile("/tmp/was_powertimer_wakeup"):
				self.wasPowerTimerWakeup = int(open("/tmp/was_powertimer_wakeup", "r").read()) and True or False
				remove("/tmp/was_powertimer_wakeup")
			# If this timer has been cancelled, just go to "end" state.
			if self.cancelled:
				return True
			if self.failed:
				return True
			if self.timerType == TIMERTYPE.WAKEUP:
				if Screens.Standby.inStandby:
					Screens.Standby.inStandby.Power()
				return True
			elif self.timerType == TIMERTYPE.WAKEUPTOSTANDBY:
				return True
			elif self.timerType == TIMERTYPE.STANDBY:
				if not Screens.Standby.inStandby:  # Not already in standby.
					AddNotificationWithUniqueIDCallback(self.sendStandbyNotification, "PT_StateChange", MessageBox, _("A finished powertimer wants to set your receiver to standby. Do that now?"), timeout=180)
				return True
			elif self.timerType == TIMERTYPE.AUTOSTANDBY:
				if NavigationInstance.instance.getCurrentlyPlayingServiceReference() and ("0:0:0:0:0:0:0:0:0" in NavigationInstance.instance.getCurrentlyPlayingServiceReference().toString() or "4097:" in NavigationInstance.instance.getCurrentlyPlayingServiceReference().toString()):
					self.do_backoff()  # Retry.
					return False
				if not Screens.Standby.inStandby:  # Not already in standby.
					AddNotificationWithUniqueIDCallback(self.sendStandbyNotification, "PT_StateChange", MessageBox, _("A finished powertimer wants to set your receiver to standby. Do that now?"), timeout=180)
					if self.autosleeprepeat == "once":
						eActionMap.getInstance().unbindAction("", self.keyPressed)
						return True
					else:
						self.begin = time() + int(self.autosleepdelay) * 60
						if self.end <= self.begin:
							self.end = self.begin
				else:
					self.begin = time() + int(self.autosleepdelay) * 60
					if self.end <= self.begin:
						self.end = self.begin

			elif self.timerType == TIMERTYPE.AUTODEEPSTANDBY:
				# Check for there being any active Movie playback or IPTV channel
				# or any streaming clients before going to Deep Standby.
				# However, it is possible to put the box into Standby with the
				# MoviePlayer still active (it will play if the box is taken out
				# of Standby) - similarly for the IPTV player. This should not
				# prevent a DeepStandby
				# And check for existing or imminent recordings, etc..
				# Also added () around the test and split them across lines
				# to make it clearer what each test is.
				from Components.Converter.ClientsStreaming import ClientsStreaming
				if ((not Screens.Standby.inStandby and NavigationInstance.instance.getCurrentlyPlayingServiceReference() and
					("0:0:0:0:0:0:0:0:0" in NavigationInstance.instance.getCurrentlyPlayingServiceReference().toString() or
					 "4097:" in NavigationInstance.instance.getCurrentlyPlayingServiceReference().toString()
					 ) or
					 (int(ClientsStreaming("NUMBER").getText()) > 0)
					) or
					(NavigationInstance.instance.RecordTimer.isRecording() or
					 abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - time()) <= 900 or
					 abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - time()) <= 900) or
					 (self.autosleepinstandbyonly == "yes" and not Screens.Standby.inStandby) or
					 (self.autosleepinstandbyonly == "yes" and Screens.Standby.inStandby and internalHDDNotSleeping()
					)
				   ):
					self.do_backoff()  # Retry.
					return False
				if not Screens.Standby.inTryQuitMainloop:  # Not a shutdown messagebox is open.
					if Screens.Standby.inStandby:  # In standby.
						quitMainloop(1)
						return True
					else:
						AddNotificationWithUniqueIDCallback(self.sendTryQuitMainloopNotification, "PT_StateChange", MessageBox, _("A finished powertimer wants to shutdown your receiver. Do that now?"), timeout=180)
						if self.autosleeprepeat == "once":
							eActionMap.getInstance().unbindAction("", self.keyPressed)
							return True
						else:
							self.begin = time() + int(self.autosleepdelay) * 60
							if self.end <= self.begin:
								self.end = self.begin
			elif self.timerType == TIMERTYPE.DEEPSTANDBY and self.wasPowerTimerWakeup:
				return True
			elif self.timerType == TIMERTYPE.DEEPSTANDBY and not self.wasPowerTimerWakeup:
				if NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - time()) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - time()) <= 900:
					self.do_backoff()  # Retry.
					return False
				if not Screens.Standby.inTryQuitMainloop:  # Not a shutdown messagebox is open.
					if Screens.Standby.inStandby:  # In standby.
						quitMainloop(1)
					else:
						AddNotificationWithUniqueIDCallback(self.sendTryQuitMainloopNotification, "PT_StateChange", MessageBox, _("A finished powertimer wants to shutdown your receiver. Do that now?"), timeout=180)
				return True
			elif self.timerType == TIMERTYPE.REBOOT:
				if NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - time()) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - time()) <= 900:
					self.do_backoff()  # Retry.
					return False
				if not Screens.Standby.inTryQuitMainloop:  # Not a shutdown messagebox is open.
					if Screens.Standby.inStandby:  # In standby.
						quitMainloop(2)
					else:
						AddNotificationWithUniqueIDCallback(self.sendTryToRebootNotification, "PT_StateChange", MessageBox, _("A finished powertimer wants to reboot your receiver. Do that now?"), timeout=180)
				return True
			elif self.timerType == TIMERTYPE.RESTART:
				if NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - time()) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - time()) <= 900:
					self.do_backoff()  # Retry.
					return False
				if not Screens.Standby.inTryQuitMainloop:  # Not a shutdown messagebox is open.
					if Screens.Standby.inStandby:  # In standby.
						quitMainloop(3)
					else:
						AddNotificationWithUniqueIDCallback(self.sendTryToRestartNotification, "PT_StateChange", MessageBox, _("A finished powertimer wants to restart the user interface.\nDo that now?"), timeout=180)
				return True
		elif next_state == self.StateEnded:
			old_end = self.end
			NavigationInstance.instance.PowerTimer.saveTimers()
			if self.afterEvent == AFTEREVENT.STANDBY:
				if not Screens.Standby.inStandby:  # Not already in standby.
					AddNotificationWithUniqueIDCallback(self.sendStandbyNotification, "PT_StateChange", MessageBox, _("A finished powertimer wants to set your receiver to standby. Do that now?"), timeout=180)
			elif self.afterEvent == AFTEREVENT.DEEPSTANDBY:
				if NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - time()) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - time()) <= 900:
					self.do_backoff()  # Retry.
					return False
				if not Screens.Standby.inTryQuitMainloop:  # Not a shutdown messagebox is open.
					if Screens.Standby.inStandby:  # In standby.
						quitMainloop(1)
					else:
						AddNotificationWithUniqueIDCallback(self.sendTryQuitMainloopNotification, "PT_StateChange", MessageBox, _("A finished powertimer wants to shutdown your receiver. Do that now?"), timeout=180)
			return True

	def setAutoincreaseEnd(self, entry=None):
		if not self.autoincrease:
			return False
		if entry is None:
			new_end = int(time()) + self.autoincreasetime
		else:
			new_end = entry.begin - 30
		dummyentry = PowerTimerEntry(self.begin, new_end, disabled=True, afterEvent=self.afterEvent, timerType=self.timerType)
		dummyentry.disabled = self.disabled
		timersanitycheck = TimerSanityCheck(NavigationInstance.instance.PowerManager.timer_list, dummyentry)
		if not timersanitycheck.check():
			simulTimerList = timersanitycheck.getSimulTimerList()
			if simulTimerList is not None and len(simulTimerList) > 1:
				new_end = simulTimerList[1].begin
				new_end -= 30
		if new_end <= time():
			return False
		self.end = new_end
		return True

	def sendStandbyNotification(self, answer):
		if answer:
			AddNotification(Screens.Standby.Standby)

	def sendTryQuitMainloopNotification(self, answer):
		if answer:
			AddNotification(Screens.Standby.TryQuitMainloop, 1)

	def sendTryToRebootNotification(self, answer):
		if answer:
			AddNotification(Screens.Standby.TryQuitMainloop, 2)

	def sendTryToRestartNotification(self, answer):
		if answer:
			AddNotification(Screens.Standby.TryQuitMainloop, 3)

	def keyPressed(self, key, tag):
		self.begin = time() + int(self.autosleepdelay) * 60
		if self.end <= self.begin:
			self.end = self.begin

	def getNextActivation(self):
		if self.state == self.StateEnded or self.state == self.StateFailed:
			return self.end

		next_state = self.state + 1

		return {self.StatePrepared: self.start_prepare,
				self.StateRunning: self.begin,
				self.StateEnded: self.end}[next_state]

	def getNextWakeup(self):
		if self.state == self.StateEnded or self.state == self.StateFailed:
			return self.end

		if self.timerType != TIMERTYPE.WAKEUP and self.timerType != TIMERTYPE.WAKEUPTOSTANDBY and not self.afterEvent:
			return -1
		elif self.timerType != TIMERTYPE.WAKEUP and self.timerType != TIMERTYPE.WAKEUPTOSTANDBY and self.afterEvent:
			return self.end
		next_state = self.state + 1
		return {self.StatePrepared: self.start_prepare,
				self.StateRunning: self.begin,
				self.StateEnded: self.end}[next_state]

	def timeChanged(self):
		old_prepare = self.start_prepare
		self.start_prepare = self.begin - self.prepare_time
		self.backoff = 0

		if int(old_prepare) > 60 and int(old_prepare) != int(self.start_prepare):
			self.log(15, "Time changed, start preparing is now %s." % ctime(self.start_prepare))
