from bisect import insort
from os import fsync, makedirs, remove, rename, sys
from os.path import exists, isdir, realpath
from sys import maxsize
from threading import Lock
from time import ctime, localtime, strftime, time

from enigma import eEPGCache, getBestPlayableServiceReference, eStreamServer, eServiceReference, iRecordableService, quitMainloop, eActionMap, setPreferredTuner

import NavigationInstance
from timer import Timer, TimerEntry
from ServiceReference import ServiceReference, isPlayableForCur
from Components.config import config
from Components.Harddisk import findMountPoint
from Components.SystemInfo import BoxInfo
from Components.TimerSanityCheck import TimerSanityCheck
import Components.ParentalControl
from Components.UsageConfig import defaultMoviePath
from Screens.MessageBox import MessageBox
from Screens.PictureInPicture import PictureInPicture
import Screens.Standby
import Screens.InfoBar
from Tools import Notifications, ASCIItranslit, Trashcan
from Tools.Alternatives import ResolveCiAlternative
from Tools.CIHelper import cihelper
from Tools.Directories import SCOPE_CONFIG, fileReadXML, getRecordingFilename, resolveFilename
from Tools.Notifications import AddNotification, AddNotificationWithCallback, AddPopup
from Tools.XMLTools import stringToXML

MODULE_NAME = __name__.split(".")[-1]

# For descriptions etc we have:
# service reference  (to get the service name)
# name               (title)
# description        (description)
# event data         (ONLY for time adjustments etc.)

# We need to handle concurrency when updating timers.xml and
# when checking was_rectimer_wakeup
#
writeLock = Lock()
wasrecLock = Lock()


# Parses an event, and gives out a (begin, end, name, duration, eit)-tuple.
# The begin and end will be corrected to include margin padding.
#
def parseEvent(event, description=True):
	if description:
		name = event.getEventName()
		description = event.getShortDescription()
		if description == "":
			description = event.getExtendedDescription()
	else:
		name = ""
		description = ""
	begin = event.getBeginTime()
	end = begin + event.getDuration()
	eit = event.getEventId()
	begin -= config.recording.margin_before.value * 60
	end += config.recording.margin_after.value * 60
	return (begin, end, name, description, eit)  # We should also report the margins!


class AFTEREVENT:
	NONE = 0
	STANDBY = 1
	DEEPSTANDBY = 2
	AUTO = 3


def findSafeRecordPath(dirname):
	if not dirname:
		return None
	dirname = realpath(dirname)
	mountPoint = findMountPoint(dirname)
	if mountPoint in ("/", "/media"):
		print("[RecordTimer] Media is not mounted for '%s'." % dirname)
		return None
	if not isdir(dirname):
		try:
			makedirs(dirname)
		except (IOError, OSError) as err:
			print("[RecordTimer] Error %d: Failed to create dir '%s'!  (%s)" % (err.errno, dirname, err.strerror))
			return None
	return dirname


# This code is for use by hardware with a stb device file which, when
# non-zero, can display a visual indication on the front-panel that
# recordings are in progress, with possibly different icons for
# different numbers of concurrent recordings.
# NOTE that Navigation.py uses symbol_signal (which the mbtwin does not
# have) to indicate that a recording is being played back. Different.
#
# Define the list of boxes which can use the code by setting the device
# path and number of different states it supports.
# Any undefined box will not use this code.
#
SID_symbol_states = {
	"mbtwin": ("/proc/stb/lcd/symbol_circle", 4)
}

SID_code_states = SID_symbol_states.setdefault(BoxInfo.getItem("model"), (None, 0))

n_recordings = 0  # Must be zero when we start running.
# Also use in Tools/Trashcan.py


def SetIconDisplay(nrec):
	if SID_code_states[0] == None:  # Not the code for us
		return
	(wdev, max_states) = SID_code_states
	if nrec == 0:                   # An absolute setting - clear it...
		open(wdev, "w").write("0")
		return
	sym = nrec
	if sym > max_states:
		sym = max_states
	if sym < 0:      # Sanity check - just in case...
		sym = 0
	open(wdev, "w").write(str(sym))
	return


# Define a function that is called at the start and stop of all
# recordings. This allows us to track the number of actual recordings.
# Other recording-related accounting could also be added here.
# alter is 1 at a recording start, -1 at a stop and 0 as enigma2 starts
# (to initialize things).
#
def RecordingsState(alter):
	global n_recordings  # Since we are about to modify it we need to declare it as global.
	if not -1 <= alter <= 1:
		return
	# Adjust the number of currently running recordings...
	if alter == 0:  # Initialize.
		n_recordings = 0
	else:
		n_recordings += alter
	if n_recordings < 0:  # Sanity check - just in case.
		n_recordings = 0
	SetIconDisplay(n_recordings)
	return


RecordingsState(0)  # Initialize active recordings to zero.

wasRecTimerWakeup = False


def checkForRecordings():
	if NavigationInstance.instance.getRecordings():
		return True
	rec_time = NavigationInstance.instance.RecordTimer.getNextTimerTime(isWakeup=True)
	return rec_time > 0 and (rec_time - time()) < 360


def createRecordTimerEntry(timer):
	return RecordTimerEntry(timer.service_ref, timer.begin, timer.end, timer.name, timer.description,
		timer.eit, timer.disabled, timer.justplay, timer.afterEvent, dirname=timer.dirname,
		tags=timer.tags, descramble=timer.descramble, record_ecm=timer.record_ecm, always_zap=timer.always_zap,
		zap_wakeup=timer.zap_wakeup, rename_repeat=timer.rename_repeat, conflict_detection=timer.conflict_detection,
		pipzap=timer.pipzap)


class RecordTimer(Timer):
	def __init__(self):
		Timer.__init__(self)
		self.fallback_timer_list = []
		self.timersFilename = resolveFilename(SCOPE_CONFIG, "timers.xml")
		self.loadTimers()

	def loadTimers(self, justLoad=False):
		timersDom = fileReadXML(self.timersFilename, source=MODULE_NAME)
		if timersDom is None:
			if not exists(self.timersFilename):
				return
			AddPopup(_("The timer file 'timers.xml' is corrupt and could not be loaded."), type=MessageBox.TYPE_ERROR, timeout=0, id="TimerLoadFailed")
			print("[RecordTimer] Error: Loading 'timers.xml' failed!")
			try:
				rename(self.timersFilename, "%s_bad" % self.timersFilename)
			except (IOError, OSError) as err:
				print("[RecordTimer] Error %d: Renaming broken timer file failed!  (%s)" % (err.errno, err.strerror))
			return
		check = False
		overlapText = [_("Timer overlaps detected in timers.xml!"), _("Please check all timers.")]
		for timer in timersDom.findall("timer"):
			newTimer = self.createTimer(timer)
			conflictList = self.record(newTimer, ignoreTSC=True, dosave=False, loadtimer=True, justLoad=justLoad)
			if conflictList:
				check = True
				if newTimer in conflictList:
					overlapText.append(_("Timer '%s' disabled!") % newTimer.name)
		if check:
			AddPopup("\n".join(overlapText), type=MessageBox.TYPE_ERROR, timeout=0, id="TimerLoadFailed")

	def loadTimer(self, justLoad=False):
		return self.loadTimers(justLoad=justLoad)

	def saveTimers(self):
		timerList = ["<?xml version=\"1.0\" ?>", "<timers>"]
		for timer in self.timer_list + self.processed_timers:
			if timer.dontSave:  # Some timers (instant records) don't want to be saved so skip them.
				continue
			timerEntry = []
			timerEntry.append("begin=\"%d\"" % timer.begin)
			timerEntry.append("end=\"%d\"" % timer.end)
			timerEntry.append("serviceref=\"%s\"" % stringToXML(str(timer.service_ref)))
			timerEntry.append("repeated=\"%d\"" % timer.repeated)
			timerEntry.append("name=\"%s\"" % stringToXML(timer.name))
			timerEntry.append("description=\"%s\"" % stringToXML(timer.description))
			timerEntry.append("afterevent=\"%s\"" % stringToXML({
				AFTEREVENT.NONE: "nothing",
				AFTEREVENT.STANDBY: "standby",
				AFTEREVENT.DEEPSTANDBY: "deepstandby",
				AFTEREVENT.AUTO: "auto"
			}[timer.afterEvent]))
			if timer.eit is not None:
				timerEntry.append("eit=\"%d\"" % timer.eit)
			if timer.dirname:
				timerEntry.append("location=\"%s\"" % stringToXML(timer.dirname))
			if timer.tags:
				timerEntry.append("tags=\"%s\"" % stringToXML(" ".join(timer.tags)))
			if timer.disabled:
				timerEntry.append("disabled=\"%d\"" % timer.disabled)
			timerEntry.append("justplay=\"%d\"" % timer.justplay)
			timerEntry.append("always_zap=\"%d\"" % timer.always_zap)
			timerEntry.append("pipzap=\"%d\"" % timer.pipzap)
			timerEntry.append("zap_wakeup=\"%s\"" % timer.zap_wakeup)
			timerEntry.append("rename_repeat=\"%d\"" % timer.rename_repeat)
			timerEntry.append("conflict_detection=\"%d\"" % timer.conflict_detection)
			timerEntry.append("descramble=\"%d\"" % timer.descramble)
			timerEntry.append("record_ecm=\"%d\"" % timer.record_ecm)
			timerEntry.append("isAutoTimer=\"%d\"" % timer.isAutoTimer)
			if timer.flags:
				timerEntry.append("flags=\"%s\"" % " ".join([stringToXML(x) for x in timer.flags]))
			timerList.append("\t<timer %s>" % " ".join(timerEntry))
			for time, code, msg in timer.log_entries:
				timerList.append("\t\t<log code=\"%d\" time=\"%d\">%s</log>" % (code, time, stringToXML(msg)))
			timerList.append("\t</timer>")
		timerList.append("</timers>\n")
		#
		# We have to run this section with a lock.  Imagine setting a timer
		# manually while the (background) AutoTimer scan is also setting a timer.
		# So we have two timers being set at "the same time".  Two process arrive
		# at the open().  The first opens it and writes to *.writing.  The
		# second opens it and overwrites (possibly slightly different) data to
		# the same file.  The first then gets to the rename and succeeds but the
		# second then tries to rename, but the "*.writing" file is now absent.
		# The result is OSError: [Errno 2] No such file or directory!
		#
		# NOTE that as Python threads are not concurrent (they run serially and
		# switch when one does something like I/O) we don't need to run the
		# list-creating loop under the lock.
		#
		with writeLock:
			file = open("%s.writing" % self.timersFilename, "w")
			file.write("\n".join(timerList))
			file.flush()
			fsync(file.fileno())
			file.close()
			rename("%s.writing" % self.timersFilename, self.timersFilename)

	def saveTimer(self):
		return self.saveTimers()

	def createTimer(self, timerDom):
		serviceReference = ServiceReference(timerDom.get("serviceref").encode("UTF-8"))
		begin = int(timerDom.get("begin"))
		end = int(timerDom.get("end"))
		name = timerDom.get("name").encode("UTF-8")
		description = timerDom.get("description").encode("UTF-8")
		eit = timerDom.get("eit")
		eit = int(eit) if eit and eit != "None" else None
		disabled = bool(int(timerDom.get("disabled", False)))
		justPlay = bool(int(timerDom.get("justplay", False)))
		afterEvent = {
			"nothing": AFTEREVENT.NONE,
			"standby": AFTEREVENT.STANDBY,
			"deepstandby": AFTEREVENT.DEEPSTANDBY,
			"auto": AFTEREVENT.AUTO
		}.get(timerDom.get("afterevent", "nothing"), "nothing")
		location = timerDom.get("location")
		location = location.encode("UTF-8") if location and location != "None" else None
		tags = timerDom.get("tags")
		tags = tags.encode("UTF-8").split(" ") if tags and tags != "None" else None
		descramble = bool(int(timerDom.get("descramble", True)))
		recordEcm = bool(int(timerDom.get("record_ecm", False)))
		isAutoTimer = bool(int(timerDom.get("isAutoTimer", False)))
		alwaysZap = bool(int(timerDom.get("always_zap", False)))
		zapWakeup = timerDom.get("zap_wakeup", "always")
		renameRepeat = bool(int(timerDom.get("rename_repeat", True)))
		conflictDetection = bool(int(timerDom.get("conflict_detection", True)))
		pipZap = bool(int(timerDom.get("pipzap", False)))
		# filename = timerDom.get("filename").encode("UTF-8")
		entry = RecordTimerEntry(serviceReference, begin, end, name, description, eit, disabled, justPlay, afterEvent, dirname=location, tags=tags, descramble=descramble, record_ecm=recordEcm, isAutoTimer=isAutoTimer, always_zap=alwaysZap, zap_wakeup=zapWakeup, rename_repeat=renameRepeat, conflict_detection=conflictDetection, pipzap=pipZap)
		entry.repeated = bool(int(timerDom.get("repeated", False)))
		flags = timerDom.get("flags")
		if flags:
			entry.flags = set(flags.encode("UTF-8").split(" "))
		for log in timerDom.findall("log"):
			entry.log_entries.append((int(log.get("time")), int(log.get("code")), log.text.strip().encode("UTF-8")))
		return entry

	def doActivate(self, w):
		# when activating a timer which has already passed,
		# simply abort the timer. don't run trough all the stages.
		if w.shouldSkip():
			w.state = RecordTimerEntry.StateEnded
		else:
			# when active returns true, this means "accepted".
			# otherwise, the current state is kept.
			# the timer entry itself will fix up the delay then.
			if w.activate():
				w.state += 1
		self.timer_list.remove(w)
		# did this timer reached the last state?
		if w.state < RecordTimerEntry.StateEnded:
			# no, sort it into active list
			insort(self.timer_list, w)
		else:
			# yes. Process repeated, and re-add.
			if w.repeated:
				w.processRepeated()
				w.state = RecordTimerEntry.StateWaiting
				w.first_try_prepare = True
				self.addTimerEntry(w)
			else:
				# correct wrong running timers
				self.checkWrongRunningTimers()
				# check for disabled timers, if time as passed set to completed
				self.cleanupDisabled()
				# Remove old timers as set in config
				self.cleanupDaily(config.recording.keep_timers.value)
				# If we want to keep done timers, re-insert in the active list
				if config.recording.keep_timers.value > 0 and w not in self.processed_timers:
					insort(self.processed_timers, w)
					self.saveTimers()
		self.stateChanged(w)

	def isRecTimerWakeup(self):
		return wasRecTimerWakeup

	def checkWrongRunningTimers(self):
		now = time() + 100
		if int(now) > 1072224000:
			wrongTimers = [entry for entry in (self.processed_timers + self.timer_list) if entry.state in (1, 2) and entry.begin > now]
			for timer in wrongTimers:
				timer.state = RecordTimerEntry.StateWaiting
				self.timeChanged(timer)

	def isRecording(self):
		for timer in self.timer_list:
			if timer.isRunning() and not timer.justplay:
				return True
		return False

	def getNextZapTime(self, isWakeup=False):
		now = time()
		for timer in self.timer_list:
			if not timer.justplay or timer.begin < now or isWakeup and timer.zap_wakeup in ("from_standby", "never"):
				continue
			return timer.begin
		return -1

	def getNextRecordingTime(self):
		now = time()
		for timer in self.timer_list:
			nextActivation = timer.getNextActivation()
			if timer.justplay or nextActivation < now:
				continue
			return nextActivation
		return -1

	def getNextTimerTime(self, isWakeup=False):
		now = time()
		for timer in self.timer_list:
			nextActivation = timer.getNextActivation()
			if nextActivation < now or isWakeup and timer.justplay and timer.zap_wakeup in ("from_standby", "never"):
				continue
			return nextActivation
		return -1

	def isNextRecordAfterEventActionAuto(self):
		now = time()
		t = None
		for timer in self.timer_list:
			if timer.justplay or timer.begin < now:
				continue
			if t is None or t.begin == timer.begin:
				t = timer
				if t.afterEvent == AFTEREVENT.AUTO:
					return True
		return False

	# If justLoad is True then we (temporarily) turn off conflict detection
	# as we load.  On a restore we may not have the correct tuner
	# configuration (and no USB tuners).
	#
	def record(self, entry, ignoreTSC=False, dosave=True, loadtimer=False, justLoad=False):
		real_cd = entry.conflict_detection
		if justLoad:
			entry.conflict_detection = False
		check_timer_list = self.timer_list[:]
		timersanitycheck = TimerSanityCheck(check_timer_list, entry)
		answer = None
		if not timersanitycheck.check():
			if not ignoreTSC:
				print("[RecordTimer] Timer conflict detected!")
				print(timersanitycheck.getSimulTimerList())
				return timersanitycheck.getSimulTimerList()
			else:
				print("[RecordTimer] Ignore timer conflict.")
				if not dosave and loadtimer:
					simulTimerList = timersanitycheck.getSimulTimerList()
					if entry in simulTimerList:
						entry.disabled = True
						if entry in check_timer_list:
							check_timer_list.remove(entry)
					answer = simulTimerList
		elif timersanitycheck.doubleCheck():
			print("[RecordTimer] Ignore duplicated timer.")
			return None
		elif not loadtimer and not entry.disabled and not entry.justplay and entry.state == 0 and not (entry.service_ref and "%3a//" in entry.service_ref.ref.toString()):
			for x in check_timer_list:
				if x.begin == entry.begin and not x.disabled and not x.justplay and not (x.service_ref and "%3a//" in x.service_ref.ref.toString()):
					entry.begin += 1
		entry.conflict_detection = real_cd
		entry.timeChanged()
		print("[RecordTimer] Record %s." % str(entry))
		entry.Timer = self
		self.addTimerEntry(entry)
		if dosave:
			self.saveTimers()
		return answer

	def isInRepeatTimer(self, timer, event):
		time_match = 0
		is_editable = False
		begin = event.getBeginTime()
		duration = event.getDuration()
		end = begin + duration
		timer_end = timer.end
		if timer.disabled and timer.isRunning():
			if begin < timer.begin <= end or timer.begin <= begin <= timer_end:
				return True
			else:
				return False
		if timer.justplay and (timer_end - timer.begin) <= 1:
			timer_end += 60
		bt = localtime(begin)
		bday = bt.tm_wday
		begin2 = 1440 + bt.tm_hour * 60 + bt.tm_min
		end2 = begin2 + duration / 60
		xbt = localtime(timer.begin)
		xet = localtime(timer_end)
		offset_day = False
		checking_time = timer.begin < begin or begin <= timer.begin <= end
		if xbt.tm_yday != xet.tm_yday:
			oday = bday - 1
			if oday == -1:
				oday = 6
			offset_day = timer.repeated & (1 << oday)
		xbegin = 1440 + xbt.tm_hour * 60 + xbt.tm_min
		xend = xbegin + ((timer_end - timer.begin) / 60)
		if xend < xbegin:
			xend += 1440
		if timer.repeated & (1 << bday) and checking_time:
			if begin2 < xbegin <= end2:
				if xend < end2:  # Recording within event.
					time_match = (xend - xbegin) * 60
					is_editable = True
				else:  # Recording last part of event.
					time_match = (end2 - xbegin) * 60
					summary_end = (xend - end2) * 60
					is_editable = not summary_end and True or time_match >= summary_end
			elif xbegin <= begin2 <= xend:
				if xend < end2:  # Recording first part of event.
					time_match = (xend - begin2) * 60
					summary_end = (begin2 - xbegin) * 60
					is_editable = not summary_end and True or time_match >= summary_end
				else:  # Recording whole event.
					time_match = (end2 - begin2) * 60
					is_editable = True
			elif offset_day:
				xbegin -= 1440
				xend -= 1440
				if begin2 < xbegin <= end2:
					if xend < end2: # Recording within event.
						time_match = (xend - xbegin) * 60
						is_editable = True
					else:  # Recording last part of event.
						time_match = (end2 - xbegin) * 60
						summary_end = (xend - end2) * 60
						is_editable = not summary_end and True or time_match >= summary_end
				elif xbegin <= begin2 <= xend:
					if xend < end2:  # Recording first part of event.
						time_match = (xend - begin2) * 60
						summary_end = (begin2 - xbegin) * 60
						is_editable = not summary_end and True or time_match >= summary_end
					else:  # Recording whole event.
						time_match = (end2 - begin2) * 60
						is_editable = True
		elif offset_day and checking_time:
			xbegin -= 1440
			xend -= 1440
			if begin2 < xbegin <= end2:
				if xend < end2:  # Recording within event.
					time_match = (xend - xbegin) * 60
					is_editable = True
				else:  # Recording last part of event.
					time_match = (end2 - xbegin) * 60
					summary_end = (xend - end2) * 60
					is_editable = not summary_end and True or time_match >= summary_end
			elif xbegin <= begin2 <= xend:
				if xend < end2:  # Recording first part of event.
					time_match = (xend - begin2) * 60
					summary_end = (begin2 - xbegin) * 60
					is_editable = not summary_end and True or time_match >= summary_end
				else:  # Recording whole event.
					time_match = (end2 - begin2) * 60
					is_editable = True
		return time_match and is_editable

	def setFallbackTimerList(self, list):
		self.fallback_timer_list = [timer for timer in list if timer.state != 3]

	def getAllTimersList(self):
		return self.timer_list + self.fallback_timer_list

	def isInTimer(self, eventid, begin, duration, service):
		returnValue = None
		type = 0
		timeMatch = 0
		bt = None
		check_offset_time = not config.recording.margin_before.value and not config.recording.margin_after.value
		end = begin + duration
		refstr = ":".join(service.split(":")[:11])
		for timer in self.getAllTimersList():
			check = ":".join(timer.service_ref.ref.toString().split(":")[:11]) == refstr
			if check:
				timer_end = timer.end
				timer_begin = timer.begin
				type_offset = 0
				if not timer.repeated and check_offset_time:
					if 0 < end - timer_end <= 59:
						timer_end = end
					elif 0 < timer_begin - begin <= 59:
						timer_begin = begin
				if timer.justplay:
					type_offset = 5
					if (timer_end - timer.begin) <= 1:
						timer_end += 60
					if timer.pipzap:
						type_offset = 30
				if timer.always_zap:
					type_offset = 10
				timer_repeat = timer.repeated
				# If set "don't stop current event but disable coming events" for repeat timer.
				running_only_curevent = timer.disabled and timer.isRunning() and timer_repeat
				if running_only_curevent:
					timer_repeat = 0
					type_offset += 15
				if timer_repeat != 0:
					type_offset += 15
					if bt is None:
						bt = localtime(begin)
						bday = bt.tm_wday
						begin2 = 1440 + bt.tm_hour * 60 + bt.tm_min
						end2 = begin2 + duration / 60
					xbt = localtime(timer.begin)
					xet = localtime(timer_end)
					offset_day = False
					checking_time = timer.begin < begin or begin <= timer.begin <= end
					if xbt.tm_yday != xet.tm_yday:
						oday = bday - 1
						if oday == -1:
							oday = 6
						offset_day = timer.repeated & (1 << oday)
					xbegin = 1440 + xbt.tm_hour * 60 + xbt.tm_min
					xend = xbegin + ((timer_end - timer.begin) / 60)
					if xend < xbegin:
						xend += 1440
					if timer.repeated & (1 << bday) and checking_time:
						if begin2 < xbegin <= end2:
							if xend < end2:  # Recording within event.
								timeMatch = (xend - xbegin) * 60
								type = type_offset + 3
							else:  # Recording last part of event.
								timeMatch = (end2 - xbegin) * 60
								type = type_offset + 1
						elif xbegin <= begin2 <= xend:
							if xend < end2:  # Recording first part of event.
								timeMatch = (xend - begin2) * 60
								type = type_offset + 4
							else:  # Recording whole event.
								timeMatch = (end2 - begin2) * 60
								type = type_offset + 2
						elif offset_day:
							xbegin -= 1440
							xend -= 1440
							if begin2 < xbegin <= end2:
								if xend < end2:  # Recording within event.
									timeMatch = (xend - xbegin) * 60
									type = type_offset + 3
								else:  # Recording last part of event.
									timeMatch = (end2 - xbegin) * 60
									type = type_offset + 1
							elif xbegin <= begin2 <= xend:
								if xend < end2:  # Recording first part of event.
									timeMatch = (xend - begin2) * 60
									type = type_offset + 4
								else:  # Recording whole event.
									timeMatch = (end2 - begin2) * 60
									type = type_offset + 2
					elif offset_day and checking_time:
						xbegin -= 1440
						xend -= 1440
						if begin2 < xbegin <= end2:
							if xend < end2:  # Recording within event.
								timeMatch = (xend - xbegin) * 60
								type = type_offset + 3
							else:  # Recording last part of event.
								timeMatch = (end2 - xbegin) * 60
								type = type_offset + 1
						elif xbegin <= begin2 <= xend:
							if xend < end2:  # Recording first part of event.
								timeMatch = (xend - begin2) * 60
								type = type_offset + 4
							else:  # Recording whole event.
								timeMatch = (end2 - begin2) * 60
								type = type_offset + 2
				else:
					if begin < timer_begin <= end:
						if timer_end < end:  # Recording within event.
							timeMatch = timer_end - timer_begin
							type = type_offset + 3
						else:  # Recording last part of event.
							timeMatch = end - timer_begin
							type = type_offset + 1
					elif timer_begin <= begin <= timer_end:
						if timer_end < end:  # Recording first part of event.
							timeMatch = timer_end - begin
							type = type_offset + 4
						else:  # Recording whole event.
							timeMatch = end - begin
							type = type_offset + 2
				if timeMatch:
					if type in (2, 7, 12, 17, 22, 27, 32):  # When full recording do not look further.
						returnValue = (timeMatch, [type])
						break
					elif returnValue:
						if type not in returnValue[1]:
							returnValue[1].append(type)
					else:
						returnValue = (timeMatch, [type])
		return returnValue

	def removeEntry(self, entry):
		print("[RecordTimer] Remove entry '%s'." % str(entry))
		entry.repeated = False  # Avoid re-enqueuing.
		entry.autoincrease = False
		entry.abort()  # Abort timer.  This sets the end time to current time, so timer will be stopped.
		if entry.state != entry.StateEnded:
			self.timeChanged(entry)
		print("[RecordTimer] State: %s." % entry.state)
		print("[RecordTimer] In processed: %s." % entry in self.processed_timers)
		print("[RecordTimer] In running: %s." % entry in self.timer_list)
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


class RecordTimerEntry(TimerEntry, object):
	# The following static methods and members are only in use when the box is in (soft) standby!
	#
	wasInStandby = False
	wasInDeepStandby = False
	receiveRecordEvents = False

	@staticmethod
	def keypress(key=None, flag=1):
		if flag and (RecordTimerEntry.wasInStandby or RecordTimerEntry.wasInDeepStandby):
			RecordTimerEntry.wasInStandby = False
			RecordTimerEntry.wasInDeepStandby = False
			eActionMap.getInstance().unbindAction("", RecordTimerEntry.keypress)

	@staticmethod
	def setWasInDeepStandby():
		RecordTimerEntry.wasInDeepStandby = True
		eActionMap.getInstance().bindAction("", -maxsize - 1, RecordTimerEntry.keypress)

	@staticmethod
	def setWasInStandby():
		if not RecordTimerEntry.wasInStandby:
			if not RecordTimerEntry.wasInDeepStandby:
				eActionMap.getInstance().bindAction("", -maxsize - 1, RecordTimerEntry.keypress)
			RecordTimerEntry.wasInDeepStandby = False
			RecordTimerEntry.wasInStandby = True

	@staticmethod
	def shutdown():
		quitMainloop(1)

	@staticmethod
	def staticGotRecordEvent(recservice, event):
		if event == iRecordableService.evEnd:
			print("[RecordTimer] staticGotRecordEvent(iRecordableService.evEnd)")
			if not checkForRecordings():
				print("[RecordTimer] No recordings busy of scheduled within 6 minutes of shutdown.")
				RecordTimerEntry.shutdown()  # Immediate shutdown.
		elif event == iRecordableService.evStart:
			print("[RecordTimer] staticGotRecordEvent(iRecordableService.evStart)")

	@staticmethod
	def stopTryQuitMainloop():
		print("[RecordTimer] stopTryQuitMainloop")
		NavigationInstance.instance.record_event.remove(RecordTimerEntry.staticGotRecordEvent)
		RecordTimerEntry.receiveRecordEvents = False

	@staticmethod
	def TryQuitMainloop():
		if not RecordTimerEntry.receiveRecordEvents and Screens.Standby.inStandby:
			print("[RecordTimer] TryQuitMainloop")
			NavigationInstance.instance.record_event.append(RecordTimerEntry.staticGotRecordEvent)
			RecordTimerEntry.receiveRecordEvents = True
			# Send fake event to check if other recordings are running or
			# other timers start in a few seconds.
			RecordTimerEntry.staticGotRecordEvent(None, iRecordableService.evEnd)

	# End of static methods and members that are only in use when the box is in (soft) standby!

	def __init__(self, serviceref, begin, end, name, description, eit, disabled=False, justplay=False, afterEvent=AFTEREVENT.AUTO, checkOldTimers=False, dirname=None, tags=None, descramble=True, record_ecm=False, isAutoTimer=False, always_zap=False, zap_wakeup="always", rename_repeat=True, conflict_detection=True, pipzap=False):
		TimerEntry.__init__(self, int(begin), int(end))
		if checkOldTimers:
			if self.begin < time() - 1209600:
				self.begin = int(time())
		if self.end < self.begin:
			self.end = self.begin
		if not isinstance(serviceref, ServiceReference):
			raise AssertionError("invalid serviceref")
		if serviceref and serviceref.isRecordable():
			self.service_ref = serviceref
		else:
			self.service_ref = ServiceReference(None)
		self.eit = eit
		self.dontSave = False
		self.name = name
		self.description = description
		self.disabled = disabled
		self.timer = None
		self.__record_service = None
		self.rec_ref = None
		self.start_prepare = 0
		self.justplay = justplay
		self.always_zap = always_zap
		self.zap_wakeup = zap_wakeup
		self.pipzap = pipzap
		self.afterEvent = afterEvent
		self.dirname = dirname
		self.dirnameHadToFallback = False
		self.autoincrease = False
		self.autoincreasetime = 3600 * 24  # 1 day.
		self.tags = tags or []
		self.descramble = descramble
		self.record_ecm = record_ecm
		self.rename_repeat = rename_repeat
		self.conflict_detection = conflict_detection
		self.external = self.external_prev = False
		self.setAdvancedPriorityFrontend = None
		self.background_zap = None
		if BoxInfo.getItem("DVB-T_priority_tuner_available") or BoxInfo.getItem("DVB-C_priority_tuner_available") or BoxInfo.getItem("DVB-S_priority_tuner_available") or BoxInfo.getItem("ATSC_priority_tuner_available"):
			rec_ref = self.service_ref and self.service_ref.ref
			str_service = rec_ref and rec_ref.toString()
			if str_service and "%3a//" not in str_service and not str_service.rsplit(":", 1)[1].startswith("/"):
				type_service = rec_ref.getUnsignedData(4) >> 16
				if type_service == 0xEEEE:
					if BoxInfo.getItem("DVB-T_priority_tuner_available") and config.usage.recording_frontend_priority_dvbt.value != "-2":
						if config.usage.recording_frontend_priority_dvbt.value != config.usage.frontend_priority.value:
							self.setAdvancedPriorityFrontend = config.usage.recording_frontend_priority_dvbt.value
					if BoxInfo.getItem("ATSC_priority_tuner_available") and config.usage.recording_frontend_priority_atsc.value != "-2":
						if config.usage.recording_frontend_priority_atsc.value != config.usage.frontend_priority.value:
							self.setAdvancedPriorityFrontend = config.usage.recording_frontend_priority_atsc.value
				elif type_service == 0xFFFF:
					if BoxInfo.getItem("DVB-C_priority_tuner_available") and config.usage.recording_frontend_priority_dvbc.value != "-2":
						if config.usage.recording_frontend_priority_dvbc.value != config.usage.frontend_priority.value:
							self.setAdvancedPriorityFrontend = config.usage.recording_frontend_priority_dvbc.value
					if BoxInfo.getItem("ATSC_priority_tuner_available") and config.usage.recording_frontend_priority_atsc.value != "-2":
						if config.usage.recording_frontend_priority_atsc.value != config.usage.frontend_priority.value:
							self.setAdvancedPriorityFrontend = config.usage.recording_frontend_priority_atsc.value
				else:
					if BoxInfo.getItem("DVB-S_priority_tuner_available") and config.usage.recording_frontend_priority_dvbs.value != "-2":
						if config.usage.recording_frontend_priority_dvbs.value != config.usage.frontend_priority.value:
							self.setAdvancedPriorityFrontend = config.usage.recording_frontend_priority_dvbs.value
		self.needChangePriorityFrontend = self.setAdvancedPriorityFrontend is not None or config.usage.recording_frontend_priority.value != "-2" and config.usage.recording_frontend_priority.value != config.usage.frontend_priority.value
		self.change_frontend = False
		self.InfoBarInstance = Screens.InfoBar.InfoBar.instance
		self.ts_dialog = None
		self.isAutoTimer = isAutoTimer
		self.log_entries = []
		self.flags = set()
		self.resetState()

	def __repr__(self):
		return "RecordTimerEntry(name=%s, begin=%s, serviceref=%s, justplay=%s, isAutoTimer=%s)" % (self.name, ctime(self.begin), self.service_ref, self.justplay, self.isAutoTimer)

	def log(self, code, msg):
		self.log_entries.append((int(time()), code, msg))
		print("[RecordTimer] Log message: '%s'." % msg)

	def calculateFilename(self, name=None):
		serviceName = self.service_ref.getServiceName()
		beginDate = strftime("%Y%m%d %H%M", localtime(self.begin))
		name = name or self.name
		filename = "%s - %s" % (beginDate, serviceName)
		if name:
			if config.recording.filename_composition.value == "event":
				filename = "%s - %s_%s" % (name, beginDate, serviceName)
			elif config.recording.filename_composition.value == "short":
				filename = "%s - %s" % (strftime("%Y%m%d", localtime(self.begin)), name)
			elif config.recording.filename_composition.value == "long":
				filename = "%s - %s - %s" % (filename, name, self.description)
			else:
				filename = "%s - %s" % (filename, name)  # Standard
		if config.recording.ascii_filenames.value:
			filename = ASCIItranslit.legacyEncode(filename)
		if not self.dirname:
			dirname = findSafeRecordPath(defaultMoviePath())
		else:
			dirname = findSafeRecordPath(self.dirname)
			if dirname is None:
				dirname = findSafeRecordPath(defaultMoviePath())
				self.dirnameHadToFallback = True
		if not dirname:
			return None
		self.Filename = getRecordingFilename(filename, dirname)
		self.log(0, "Filename calculated as '%s'." % self.Filename)
		return self.Filename

	def tryPrepare(self):
		if self.justplay:
			return True
		else:
			if not self.calculateFilename():
				self.do_backoff()
				self.start_prepare = time() + self.backoff
				return False
			rec_ref = self.service_ref and self.service_ref.ref
			if rec_ref and rec_ref.flags & eServiceReference.isGroup:
				rec_ref = getBestPlayableServiceReference(rec_ref, eServiceReference())
				if not rec_ref:
					self.log(1, "The 'get best playable service for group... record' call failed!")
					return False
			if rec_ref and config.misc.use_ci_assignment.value and not (self.record_ecm and not self.descramble):
				current_ref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
				is_playable = isPlayableForCur(rec_ref)
				live_ci_ref = False
				if current_ref and current_ref != rec_ref:
					cur_assignment = cihelper.ServiceIsAssigned(current_ref.toString())
					rec_assignment = cihelper.ServiceIsAssigned(rec_ref.toString())
					if cur_assignment and rec_assignment and cur_assignment[0] == rec_assignment[0]:
						if cihelper.canMultiDescramble(rec_assignment[0]):
							for x in (4, 2, 3):
								if current_ref.getUnsignedData(x) != rec_ref.getUnsignedData(x):
									live_ci_ref = True
									break
						else:
							live_ci_ref = True
				if live_ci_ref or not is_playable:
					start_zap = record_ecm_notdescramble = False
					if self.service_ref.ref.flags & eServiceReference.isGroup:
						alternative_ci_ref = ResolveCiAlternative(self.service_ref.ref, ignore_ref=not is_playable and rec_ref, record_mode=live_ci_ref and cur_assignment)
						if alternative_ci_ref:
							rec_ref = alternative_ci_ref
						elif live_ci_ref and is_playable:
							start_zap = True
						elif not is_playable:
							record_ecm_notdescramble = True
					elif live_ci_ref and is_playable:
						start_zap = True
					elif not is_playable:
						record_ecm_notdescramble = True
					if record_ecm_notdescramble:
						self.record_ecm = True
						self.descramble = False
					if start_zap:
						self.log(1, "Zapping in CI+ used.")
						self.failureCB(answer=True, ref=rec_ref)
						Notifications.AddNotification(MessageBox, _("In order to record a timer, the TV was switched to the recording service!\n"), type=MessageBox.TYPE_INFO, timeout=20)
			self.log(1, "The 'record ref' is %s." % rec_ref and rec_ref.toString())
			self.setRecordingPreferredTuner()
			self.record_service = rec_ref and NavigationInstance.instance.recordService(rec_ref)
			if not self.record_service:
				self.log(1, "The 'record service' call failed!")
				self.setRecordingPreferredTuner(setdefault=True)
				return False
			self.rec_ref = rec_ref
			name = self.name
			description = self.description
			if self.repeated:
				epgcache = eEPGCache.getInstance()
				queryTime = self.begin + (self.end - self.begin) / 2
				evt = epgcache.lookupEventTime(rec_ref, queryTime)
				if evt:
					if self.rename_repeat:
						event_description = evt.getShortDescription()
						if not event_description:
							event_description = evt.getExtendedDescription()
						if event_description and event_description != description:
							description = event_description
						event_name = evt.getEventName()
						if event_name and event_name != name:
							name = event_name
							if not self.calculateFilename(event_name):
								self.do_backoff()
								self.start_prepare = time() + self.backoff
								return False
					event_id = evt.getEventId()
				else:
					event_id = -1
			else:
				event_id = self.eit
				if event_id is None:
					event_id = -1
			prep_res = self.record_service.prepare(self.Filename + self.record_service.getFilenameExtension(), self.begin, self.end, event_id, name.replace("\n", " "), description.replace("\n", " "), " ".join(self.tags), bool(self.descramble), bool(self.record_ecm))
			if prep_res:
				if prep_res == -255:
					self.log(4, "Failed to write meta information!")
				else:
					self.log(2, "The 'prepare' call failed with error %d!" % prep_res)
				# We must calc our start time before stopRecordService call because in Screens/Standby.py
				# TryQuitMainloop tries to get the next start time in evEnd event handler.
				self.do_backoff()
				self.start_prepare = time() + self.backoff
				NavigationInstance.instance.stopRecordService(self.record_service)
				self.record_service = None
				self.rec_ref = None
				self.setRecordingPreferredTuner(setdefault=True)
				return False
			return True

	def do_backoff(self):
		if self.backoff == 0:
			self.backoff = 5
		else:
			self.backoff *= 2
			if self.backoff > 100:
				self.backoff = 100
		self.log(10, "Backoff, retry in %d seconds." % self.backoff)

	def sendactivesource(self):
		if BoxInfo.getItem("HasHDMI-CEC") and config.hdmicec.enabled.value and config.hdmicec.sourceactive_zaptimers.value:
			import Components.HdmiCec
			Components.HdmiCec.hdmi_cec.sendMessage(0, "sourceactive")
			print("[RecordTimer] Source active was sent.")

	def activate(self):
		next_state = self.state + 1
		self.log(5, "Activating state %d." % next_state)
		if next_state == self.StatePrepared:
			if self.always_zap:
				if Screens.Standby.inStandby:
					self.log(5, "Wakeup and zap to recording service.")
					RecordTimerEntry.setWasInStandby()
					Screens.Standby.inStandby.prev_running_service = self.service_ref.ref  # Set service to zap after standby.
					Screens.Standby.inStandby.paused_service = None
					Screens.Standby.inStandby.Power()  # Wake up standby.
				else:
					self.sendactivesource()
					if RecordTimerEntry.wasInDeepStandby:
						RecordTimerEntry.setWasInStandby()
					cur_ref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
					if not cur_ref or not cur_ref.getPath():
						if self.checkingTimeshiftRunning():
							if self.ts_dialog is None:
								self.openChoiceActionBeforeZap()
						else:
							Notifications.AddNotification(MessageBox, _("In order to record a timer, the TV was switched to the recording service!\n"), type=MessageBox.TYPE_INFO, timeout=20)
							self.setRecordingPreferredTuner()
							self.failureCB(answer=True)
							self.log(5, "Zap to recording service.")
			if self.tryPrepare():
				self.log(6, "Prepare okay, waiting for begin.")
				# create file to "reserve" the filename
				# because another recording at the same time on another service can try to record the same event
				# i.e. cable / sat.. then the second recording needs an own extension... when we create the file
				# here than calculateFilename is happy
				if not self.justplay:
					open(self.Filename + self.record_service.getFilenameExtension(), "w").close()
					# Give the Trashcan a chance to clean up
					# Need try/except as Trashcan.instance may not exist
					# for a missed recording started at boot-time.
					try:
						Trashcan.instance.cleanIfIdle(self.Filename)
					except Exception as e:
						print("[RecordTimer] Failed to call Trashcan.instance.cleanIfIdle()!")
						print("[RecordTimer] Error: %s" % str(e))
				# Fine, it worked, resources are allocated.
				self.next_activation = self.begin
				self.backoff = 0
				return True
			self.log(7, "Prepare failed!")
			if eStreamServer.getInstance().getConnectedClients():
				eStreamServer.getInstance().stopStream()
				return False
			if self.first_try_prepare or (self.ts_dialog is not None and not self.checkingTimeshiftRunning()):
				self.first_try_prepare = False
				cur_ref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
				if cur_ref and not cur_ref.getPath():
					if self.always_zap:
						return False
					if Screens.Standby.inStandby:
						self.setRecordingPreferredTuner()
						self.failureCB(answer=True)
					elif self.checkingTimeshiftRunning():
						if self.ts_dialog is None:
							self.openChoiceActionBeforeZap()
					elif not config.recording.asktozap.value:
						self.log(8, "Asking user to zap away.")
						Notifications.AddNotificationWithCallback(self.failureCB, MessageBox, _("A timer failed to record!\nDisable TV and try again?\n"), timeout=20, default=True)
					else:  # Zap without asking.
						self.log(9, "Zap without asking.")
						Notifications.AddNotification(MessageBox, _("In order to record a timer, the TV was switched to the recording service!\n"), type=MessageBox.TYPE_INFO, timeout=20)
						self.setRecordingPreferredTuner()
						self.failureCB(answer=True)
				elif cur_ref:
					self.log(8, "Currently running service is not a live service so stopping it makes no sense.")
				else:
					self.log(8, "Currently no service running so we dont need to stop it.")
			return False

		elif next_state == self.StateRunning:
			global wasRecTimerWakeup
			# Run this under a lock.
			# We've seen two threads arrive here "together".
			# Both see the file as existing, but only one can delete it...
			with wasrecLock:
				if exists("/tmp/was_rectimer_wakeup") and not wasRecTimerWakeup:
					wasRecTimerWakeup = int(open("/tmp/was_rectimer_wakeup", "r").read()) and True or False
					remove("/tmp/was_rectimer_wakeup")
			self.autostate = Screens.Standby.inStandby
			# If this timer has been cancelled, just go to "end" state.
			if self.cancelled:
				return True
			if self.justplay:
				if Screens.Standby.inStandby:
					if RecordTimerEntry.wasInDeepStandby and self.zap_wakeup in ("always", "from_deep_standby") or self.zap_wakeup in ("always", "from_standby"):
						self.log(11, "Wake up and zap.")
						RecordTimerEntry.setWasInStandby()
						Screens.Standby.inStandby.prev_running_service = self.service_ref.ref  # Set service to zap after standby.
						Screens.Standby.inStandby.paused_service = None
						Screens.Standby.inStandby.Power()  # Wake up standby.
				else:
					self.sendactivesource()
					if RecordTimerEntry.wasInDeepStandby:
						RecordTimerEntry.setWasInStandby()
					notify = config.usage.show_message_when_recording_starts.value and self.InfoBarInstance and self.InfoBarInstance.execing
					cur_ref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
					pip_zap = self.pipzap or (cur_ref and cur_ref.getPath() and "%3a//" not in cur_ref.toString() and BoxInfo.getItem("PIPAvailable"))
					if pip_zap:
						cur_ref_group = NavigationInstance.instance.getCurrentlyPlayingServiceOrGroup()
						if cur_ref_group and cur_ref_group != self.service_ref.ref and self.InfoBarInstance and hasattr(self.InfoBarInstance.session, "pipshown") and not Components.ParentalControl.parentalControl.isProtected(self.service_ref.ref):
							if self.InfoBarInstance.session.pipshown:
								hasattr(self.InfoBarInstance, "showPiP") and self.InfoBarInstance.showPiP()
							if hasattr(self.InfoBarInstance.session, "pip"):
								del self.InfoBarInstance.session.pip
								self.InfoBarInstance.session.pipshown = False
							self.InfoBarInstance.session.pip = self.InfoBarInstance.session.instantiateDialog(PictureInPicture)
							self.InfoBarInstance.session.pip.show()
							if self.InfoBarInstance.session.pip.playService(self.service_ref.ref):
								self.InfoBarInstance.session.pipshown = True
								self.InfoBarInstance.session.pip.servicePath = self.InfoBarInstance.servicelist and self.InfoBarInstance.servicelist.getCurrentServicePath()
								self.log(11, "Zapping as PiP.")
								if notify:
									Notifications.AddPopup(text=_("Zapped to timer service %s as Picture in Picture!") % self.service_ref.getServiceName(), type=MessageBox.TYPE_INFO, timeout=5)
								return True
							else:
								del self.InfoBarInstance.session.pip
								self.InfoBarInstance.session.pipshown = False
					if self.checkingTimeshiftRunning():
						if self.ts_dialog is None:
							self.openChoiceActionBeforeZap()
					else:
						self.log(11, "Zapping.")
						force = False
						if cur_ref and cur_ref.getPath():
							if self.InfoBarInstance:
								self.InfoBarInstance.lastservice = self.service_ref.ref
							from Screens.InfoBar import MoviePlayer
							MoviePlayerinstance = MoviePlayer.movie_instance
							try:
								from Plugins.Extensions.MediaPlayer.plugin import MediaPlayer
								MediaPlayerinstance = MediaPlayer.media_instance
							except:
								MediaPlayerinstance = None
							if MoviePlayerinstance:
								MoviePlayerinstance.lastservice = self.service_ref.ref
								if hasattr(MoviePlayerinstance, "movieselection_dlg") and MoviePlayerinstance.movieselection_dlg:
									MoviePlayerinstance.returning = True
									MoviePlayerinstance.movieselection_dlg.close(None)
									force = True
								elif hasattr(MoviePlayerinstance, "execing") and MoviePlayerinstance.execing:
									from Screens.InfoBarGenerics import setResumePoint
									setResumePoint(MoviePlayerinstance.session)
									MoviePlayerinstance.close()
									force = True
							if not force and MediaPlayerinstance and hasattr(MediaPlayerinstance, "execing") and MediaPlayerinstance.execing:
								MediaPlayerinstance.oldService = self.service_ref.ref
								MediaPlayerinstance.exitCallback(True)
								force = True
						if not force:
							self.failureCB(answer=True, close_pip=False)
						if notify or force:
							Notifications.AddPopup(text=_("Zapped to timer service %s!") % self.service_ref.getServiceName(), type=MessageBox.TYPE_INFO, timeout=5)
				return True
			else:
				if RecordTimerEntry.wasInDeepStandby:
					RecordTimerEntry.keypress()
					if Screens.Standby.inStandby:  # In case some plugin did put the receiver already in standby.
						config.misc.standbyCounter.value = 0
					else:
						Notifications.AddNotification(Screens.Standby.Standby, StandbyCounterIncrease=False)
				if config.recording.zap_record_service_in_standby.value and Screens.Standby.inStandby:
					cur_ref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
					if self.rec_ref and (not cur_ref or cur_ref != self.rec_ref):
						NavigationInstance.instance.playService(self.rec_ref, checkParentalControl=False, adjust=False)
						cur_ref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
						if cur_ref and self.rec_ref == cur_ref:
							self.background_zap = cur_ref
				record_res = self.record_service.start()
				self.setRecordingPreferredTuner(setdefault=True)
				if record_res:
					self.log(13, "Start recording error %d!" % record_res)
					self.do_backoff()
					# retry
					self.begin = time() + self.backoff
					return False
				# Tell the trashcan we started recording. The trashcan gets events,
				# but cannot tell what the associated path is.
				try:
					Trashcan.instance.markDirty(self.Filename)
				except:
					pass
				self.log_tuner(11, "Start")
				return True
		elif next_state == self.StateEnded:
			old_end = self.end
			self.ts_dialog = None
			if self.setAutoincreaseEnd():
				self.log(12, "Auto increase recording length %d minute(s)." % int((self.end - old_end) / 60))
				self.state -= 1
				return True
			self.log_tuner(12, "Stop")
			RecordingsState(-1)
			if not self.justplay:
				NavigationInstance.instance.stopRecordService(self.record_service)
				if self.background_zap is not None and Screens.Standby.inStandby:
					cur_ref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
					if cur_ref and self.background_zap == cur_ref:
						NavigationInstance.instance.stopService()
				self.record_service = None
				self.rec_ref = None
				self.background_zap = None
			if not checkForRecordings():
				if self.afterEvent == AFTEREVENT.DEEPSTANDBY or (wasRecTimerWakeup and self.afterEvent == AFTEREVENT.AUTO and Screens.Standby.inStandby or RecordTimerEntry.wasInStandby) and not config.misc.standbyCounter.value:
					if not Screens.Standby.inTryQuitMainloop:
						if Screens.Standby.inStandby:
							RecordTimerEntry.TryQuitMainloop()
						else:
							msg = _("A completed recording timer is about to shut down your receiver. Would you like to proceed?")
							Notifications.AddNotificationWithCallback(self.sendTryQuitMainloopNotification, MessageBox, msg, timeout=20, default=True)
				elif self.afterEvent == AFTEREVENT.STANDBY or (not wasRecTimerWakeup and self.autostate and self.afterEvent == AFTEREVENT.AUTO) or RecordTimerEntry.wasInStandby:
					if not Screens.Standby.inStandby:
						msg = _("A completed recording timer is about to put your receiver in standby mode. Would you like to proceed?")
						Notifications.AddNotificationWithCallback(self.sendStandbyNotification, MessageBox, msg, timeout=20, default=True)
				else:
					RecordTimerEntry.keypress()
			return True

	def setAutoincreaseEnd(self, entry=None):
		if not self.autoincrease:
			return False
		if entry is None:
			new_end = int(time()) + self.autoincreasetime
		else:
			new_end = entry.begin - 30
		dummyentry = RecordTimerEntry(self.service_ref, self.begin, new_end, self.name, self.description, self.eit, disabled=True, justplay=self.justplay, afterEvent=self.afterEvent, dirname=self.dirname, tags=self.tags)
		dummyentry.disabled = self.disabled
		timersanitycheck = TimerSanityCheck(NavigationInstance.instance.RecordTimer.timer_list, dummyentry)
		if not timersanitycheck.check():
			simulTimerList = timersanitycheck.getSimulTimerList()
			if simulTimerList is not None and len(simulTimerList) > 1:
				new_end = simulTimerList[1].begin
				new_end -= 30  # Leave a few seconds (30) of preparation time.
		if new_end <= time():
			return False
		self.end = new_end
		return True

	def setRecordingPreferredTuner(self, setdefault=False):
		if self.needChangePriorityFrontend:
			elem = None
			if not self.change_frontend and not setdefault:
				elem = (self.setAdvancedPriorityFrontend is not None and self.setAdvancedPriorityFrontend) or config.usage.recording_frontend_priority.value
				self.change_frontend = True
			elif self.change_frontend and setdefault:
				elem = config.usage.frontend_priority.value
				self.change_frontend = False
				self.setAdvancedPriorityFrontend = None
			if elem is not None:
				setPreferredTuner(int(elem))

	def checkingTimeshiftRunning(self):
		return config.usage.check_timeshift.value and self.InfoBarInstance and self.InfoBarInstance.timeshiftEnabled() and self.InfoBarInstance.timeshift_was_activated

	def openChoiceActionBeforeZap(self):
		if self.ts_dialog is None:
			type = _("record")
			if self.justplay:
				type = _("zap")
			elif self.always_zap:
				type = _("zap and record")
			message = _("You must switch to the service %s (%s - '%s')!\n") % (type, self.service_ref.getServiceName(), self.name)
			if self.repeated:
				message += _("Attention, this is repeated timer!\n")
			message += _("Timeshift is running. Select an action.\n")
			choice = [(_("Zap"), "zap"), (_("Don't zap and disable timer"), "disable"), (_("Don't zap and remove timer"), "remove")]
			if not self.InfoBarInstance.save_timeshift_file:
				choice.insert(0, (_("Save timeshift and zap"), "save"))
			else:
				message += _("Reminder, you have chosen to save timeshift file.")
			# If self.justplay or self.always_zap:
			# 	choice.insert(2, (_("Don't zap"), "continue"))
			choice.insert(2, (_("Don't zap"), "continue"))

			def zapAction(choice):
				start_zap = True
				if choice:
					if choice in ("zap", "save"):
						self.log(8, "Zap to recording service.")
						if choice == "save":
							ts = self.InfoBarInstance.getTimeshift()
							if ts and ts.isTimeshiftEnabled():
								del ts
								self.InfoBarInstance.save_timeshift_file = True
								self.InfoBarInstance.SaveTimeshift()
					elif choice == "disable":
						self.disable()
						NavigationInstance.instance.RecordTimer.timeChanged(self)
						start_zap = False
						self.log(8, "Zap canceled by the user, timer disabled.")
					elif choice == "remove":
						start_zap = False
						self.afterEvent = AFTEREVENT.NONE
						NavigationInstance.instance.RecordTimer.removeEntry(self)
						self.log(8, "Zap canceled by the user, timer removed.")
					elif choice == "continue":
						if self.justplay:
							self.end = self.begin
						start_zap = False
						self.log(8, "Zap canceled by the user.")
				if start_zap:
					if not self.justplay:
						self.setRecordingPreferredTuner()
						self.failureCB(answer=True)
					else:
						self.log(8, "Zapping.")
						self.failureCB(answer=True, close_pip=False)

			self.ts_dialog = self.InfoBarInstance.session.openWithCallback(zapAction, MessageBox, message, simple=True, list=choice, timeout=20)

	def sendStandbyNotification(self, answer):
		RecordTimerEntry.keypress()
		if answer:
			Notifications.AddNotification(Screens.Standby.Standby)

	def sendTryQuitMainloopNotification(self, answer):
		RecordTimerEntry.keypress()
		if answer:
			Notifications.AddNotification(Screens.Standby.TryQuitMainloop, 1)
		else:
			global wasRecTimerWakeup
			wasRecTimerWakeup = False

	def getNextActivation(self):
		if self.state == self.StateEnded:
			return self.end
		next_state = self.state + 1
		return {
			self.StatePrepared: self.start_prepare,
			self.StateRunning: self.begin,
			self.StateEnded: self.end
		}[next_state]

	def failureCB(self, answer=False, close_pip=True, ref=None):
		self.ts_dialog = None
		if answer:
			self.log(13, "Okay, zapped away.")
			if close_pip and not self.first_try_prepare and self.InfoBarInstance and hasattr(self.InfoBarInstance.session, "pipshown") and self.InfoBarInstance.session.pipshown:
				hasattr(self.InfoBarInstance, "showPiP") and self.InfoBarInstance.showPiP()
				if hasattr(self.InfoBarInstance.session, "pip"):
					del self.InfoBarInstance.session.pip
					self.InfoBarInstance.session.pipshown = False
			addService = False
			old_ref_group = NavigationInstance.instance.getCurrentlyPlayingServiceOrGroup()
			if self.service_ref.ref and (not old_ref_group or old_ref_group != self.service_ref.ref):
				addService = True
			NavigationInstance.instance.playService(ref or self.service_ref.ref, adjust=False)
			if addService and hasattr(self.InfoBarInstance, "servicelist"):
				next_ref_group = NavigationInstance.instance.getCurrentlyPlayingServiceOrGroup()
				if next_ref_group and next_ref_group == (ref or self.service_ref.ref):
					self.InfoBarInstance.servicelist.servicelist.setCurrent(self.service_ref.ref, adjust=True)
					selectedService = self.InfoBarInstance.servicelist.getCurrentSelection()
					if selectedService and selectedService == self.service_ref.ref:
						self.InfoBarInstance.servicelist.addToHistory(self.service_ref.ref)
						self.InfoBarInstance.servicelist.saveChannel(self.service_ref.ref)
		else:
			self.log(14, "User didn't want to zap away, record will probably fail.")

	def log_tuner(self, level, state):  # Report the tuner that the current recording is using.
		# If we have a Zap timer then the tuner is for the current service
		if self.justplay:
			timer_rs = NavigationInstance.instance.getCurrentService()
		else:
			timer_rs = self.record_service
		feinfo = timer_rs and hasattr(timer_rs, "frontendInfo") and timer_rs.frontendInfo()
		fedata = feinfo and hasattr(feinfo, "getFrontendData") and feinfo.getFrontendData()
		tuner_info = fedata and "tuner_number" in fedata and chr(ord("A") + fedata.get("tuner_number")) or "(fallback) stream"
		self.log(level, "%s recording on tuner %s." % (state, tuner_info))

	def timeChanged(self):
		oldPrepare = self.start_prepare
		self.start_prepare = self.begin - self.prepare_time
		self.backoff = 0
		print("[RecordTimer] DEBUG: In timeChanged. oldPrepare=%d, newPrepare=%d." % (oldPrepare, self.start_prepare))
		if int(oldPrepare) and int(oldPrepare) != int(self.start_prepare):
			self.log(15, "Record time changed, start prepare is now %s." % ctime(self.start_prepare))

	def gotRecordEvent(self, record, event):
		# TODO: this is not working (never true), please fix. (comparing two swig wrapped ePtrs)
		if self.__record_service.__deref__() != record.__deref__():
			return
		self.log(16, "Record event %d." % event)
		if event == iRecordableService.evRecordWriteError:
			print("[RecordTimer] Write error on recording!")
			# show notification. the "id" will make sure that it will be
			# displayed only once, even if more timers are failing at the
			# same time. (which is very likely in case of disk fullness)
			Notifications.AddPopup(text=_("Write error while recording.\n"), type=MessageBox.TYPE_ERROR, timeout=0, id="WriteErrorMessage")
			# ok, the recording has been stopped. we need to properly note
			# that in our state, with also keeping the possibility to re-try.
			# TODO: this has to be done.
		elif event == iRecordableService.evStart:
			RecordingsState(1)
			text = _("A recording has started:\n%s") % self.name
			notify = config.usage.show_message_when_recording_starts.value and not Screens.Standby.inStandby and self.InfoBarInstance and self.InfoBarInstance.execing
			if self.dirnameHadToFallback:
				text = "\n".join((text, _("Please note that the previously selected media could not be accessed and therefore the default directory is being used instead.")))
				notify = True
			if notify:
				Notifications.AddPopup(text=text, type=MessageBox.TYPE_INFO, timeout=3)
		elif event == iRecordableService.evRecordAborted:
			NavigationInstance.instance.RecordTimer.removeEntry(self)
		elif event == iRecordableService.evGstRecordEnded:
			if self.repeated:
				self.processRepeated(findRunningEvent=False)
			NavigationInstance.instance.RecordTimer.doActivate(self)

	def setRecordService(self, service):  # We have record_service as property to automatically subscribe to record service events.
		if self.__record_service is not None:
			print("[RecordTimer] Remove callback.")
			NavigationInstance.instance.record_event.remove(self.gotRecordEvent)
		self.__record_service = service
		if self.__record_service is not None:
			print("[RecordTimer] Add callback.")
			NavigationInstance.instance.record_event.append(self.gotRecordEvent)

	record_service = property(lambda self: self.__record_service, setRecordService)
