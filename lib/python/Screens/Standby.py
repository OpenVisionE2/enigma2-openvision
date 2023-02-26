# -*- coding: utf-8 -*-
from os.path import isfile
import struct
import RecordTimer
import Components.ParentalControl
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.config import config
from Components.AVSwitch import AVSwitch
from Components.Console import Console
from Components.ImportChannels import ImportChannels
from Components.SystemInfo import BoxInfo
from Components.Sources.StreamService import StreamServiceList
from Components.Task import job_manager
from Tools.Directories import mediaFilesInUse
from Tools.Notifications import AddNotification
from time import time, localtime
from GlobalActions import globalActionMap
from enigma import eDVBVolumecontrol, eTimer, eDVBLocalTimeHandler, eServiceReference, eStreamServer, quitMainloop, iRecordableService
from Tools.OEMInfo import getOEMShowDisplayModel, getOEMShowDisplayBrand

displaybrand = getOEMShowDisplayBrand()
displaymodel = getOEMShowDisplayModel()
model = BoxInfo.getItem("model")

inStandby = None
infoBarInstance = None
TVinStandby = None

QUIT_SHUTDOWN = 1
QUIT_REBOOT = 2
QUIT_RESTART = 3
QUIT_UPGRADE_FP = 4
QUIT_ERROR_RESTART = 5
QUIT_DEBUG_RESTART = 6
QUIT_MANUFACTURER_RESET = 7
QUIT_REBOOT_ANDROID = 12
QUIT_REBOOT_RECOVERY = 16
QUIT_UPGRADE_PROGRAM = 42
QUIT_IMAGE_RESTORE = 43
QUIT_UPGRADE_FPANEL = 44
QUIT_WOL = 45


class TVstate: #load in Navigation
	def __init__(self):
		global TVinStandby
		if TVinStandby is not None:
			print("[Standby] only one TVstate instance is allowed!")
		TVinStandby = self

		try:
			import Components.HdmiCec
			self.hdmicec_instance = Components.HdmiCec.hdmi_cec.instance
			self.hdmicec_ok = self.hdmicec_instance and config.hdmicec.enabled.value
		except:
			self.hdmicec_ok = False

		if not self.hdmicec_ok:
			print('[Standby] HDMI-CEC is not enabled or unavailable!')

	def skipHdmiCecNow(self, value):
		if self.hdmicec_ok:
			if value is True or value is False:
				self.hdmicec_instance.tv_skip_messages = value
			elif 'zaptimer' in value:
				self.hdmicec_instance.tv_skip_messages = config.hdmicec.control_tv_wakeup.value and not config.hdmicec.tv_wakeup_zaptimer.value and inStandby
			elif 'zapandrecordtimer' in value:
				self.hdmicec_instance.tv_skip_messages = config.hdmicec.control_tv_wakeup.value and not config.hdmicec.tv_wakeup_zapandrecordtimer.value and inStandby
			elif 'wakeuppowertimer' in value:
				self.hdmicec_instance.tv_skip_messages = config.hdmicec.control_tv_wakeup.value and not config.hdmicec.tv_wakeup_wakeuppowertimer.value and inStandby

	def getTVstandby(self, value):
		if self.hdmicec_ok:
			if 'zaptimer' in value:
				return config.hdmicec.control_tv_wakeup.value and not config.hdmicec.tv_wakeup_zaptimer.value
			elif 'zapandrecordtimer' in value:
				return config.hdmicec.control_tv_wakeup.value and not config.hdmicec.tv_wakeup_zapandrecordtimer.value
			elif 'wakeuppowertimer' in value:
				return config.hdmicec.control_tv_wakeup.value and not config.hdmicec.tv_wakeup_wakeuppowertimer.value
		return False

	def getTVstate(self, value):
		if self.hdmicec_ok:
			if not config.hdmicec.check_tv_state.value or self.hdmicec_instance.sendMessagesIsActive():
				return False
			elif value == 'on':
				return value in self.hdmicec_instance.tv_powerstate and config.hdmicec.control_tv_standby.value
			elif value == 'standby':
				return value in self.hdmicec_instance.tv_powerstate and config.hdmicec.control_tv_wakeup.value
			elif value == 'active':
				return 'on' in self.hdmicec_instance.tv_powerstate and self.hdmicec_instance.activesource
			elif value == 'notactive':
				return 'standby' in self.hdmicec_instance.tv_powerstate or not self.hdmicec_instance.activesource
		return False

	def setTVstate(self, value):
		if self.hdmicec_ok:
			if value == 'on' or (value == 'power' and config.hdmicec.handle_deepstandby_events.value and not self.hdmicec_instance.handleTimer.isActive()):
				self.hdmicec_instance.wakeupMessages()
			elif value == 'standby':
				self.hdmicec_instance.standbyMessages()


def isInfoBarInstance():
	global infoBarInstance
	if infoBarInstance is None:
		from Screens.InfoBar import InfoBar
		if InfoBar.instance:
			infoBarInstance = InfoBar.instance
	return infoBarInstance


def checkTimeshiftRunning():
	infobar_instance = isInfoBarInstance()
	return config.usage.check_timeshift.value and infobar_instance and infobar_instance.timeshiftEnabled() and infobar_instance.timeshift_was_activated


class StandbyScreen(Screen):
	def __init__(self, session, StandbyCounterIncrease=True):
		self.skinName = "Standby"
		Screen.__init__(self, session)
		self.avswitch = AVSwitch()

		print("[Standby] enter standby")
		BoxInfo.setItem("StandbyState", True)

		if isfile("/usr/script/standby_enter.sh"):
			Console().ePopen("/usr/script/standby_enter.sh")

		self["actions"] = ActionMap(["StandbyActions"],
		{
			"power": self.Power,
			"discrete_on": self.Power
		}, -1)

		globalActionMap.setEnabled(False)

		self.infoBarInstance = isInfoBarInstance()
		from Screens.SleepTimerEdit import isNextWakeupTime
		self.StandbyCounterIncrease = StandbyCounterIncrease
		self.standbyTimeoutTimer = eTimer()
		self.standbyTimeoutTimer.callback.append(self.standbyTimeout)
		self.standbyStopServiceTimer = eTimer()
		self.standbyStopServiceTimer.callback.append(self.stopService)
		self.standbyWakeupTimer = eTimer()
		self.standbyWakeupTimer.callback.append(self.standbyWakeup)
		self.timeHandler = None

		self.setMute()

		self.paused_service = self.paused_action = False

		self.prev_running_service = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if Components.ParentalControl.parentalControl.isProtected(self.prev_running_service):
			self.prev_running_service = eServiceReference(config.tv.lastservice.value)
		service = self.prev_running_service and self.prev_running_service.toString()
		if service:
			if "%3a//" not in service and service.rsplit(":", 1)[1].startswith("/"):
				self.paused_service = hasattr(self.session.current_dialog, "pauseService") and hasattr(self.session.current_dialog, "unPauseService") and self.session.current_dialog or self.infoBarInstance
				self.paused_action = hasattr(self.paused_service, "seekstate") and hasattr(self.paused_service, "SEEK_STATE_PLAY") and self.paused_service.seekstate == self.paused_service.SEEK_STATE_PLAY
				self.paused_action and self.paused_service.pauseService()
		if not self.paused_service:
			self.timeHandler = eDVBLocalTimeHandler.getInstance()
			if self.timeHandler.ready():
				if self.session.nav.getCurrentlyPlayingServiceOrGroup():
					self.stopService()
				else:
					self.standbyStopServiceTimer.startLongTimer(5)
				self.timeHandler = None
			else:
				self.timeHandler.m_timeUpdated.get().append(self.stopService)

		if hasattr(self.session, "pipshown") and self.session.pipshown:
			self.infoBarInstance and hasattr(self.infoBarInstance, "showPiP") and self.infoBarInstance.showPiP()
		if hasattr(self.session, "pip"):
			del self.session.pip
		self.session.pipshown = False

		if BoxInfo.getItem("ScartSwitch"):
			self.avswitch.setInput("SCART")
		else:
			self.avswitch.setInput("AUX")

		if isfile("/proc/stb/hdmi/output"):
			try:
				print("[Standby] Write to /proc/stb/hdmi/output")
				open("/proc/stb/hdmi/output", "w").write("off")
			except:
				print("[Standby] Write to /proc/stb/hdmi/output failed.")

		if BoxInfo.getItem("AmlogicFamily"):
			try:
				print("[Standby] Write to /sys/class/leds/led-sys/brightness")
				open("/sys/class/leds/led-sys/brightness", "w").write("0")
			except:
				print("[Standby] Write to /sys/class/leds/led-sys/brightness failed.")
			try:
				print("[Standby] Write to /sys/class/cec/cmd")
				open("/sys/class/cec/cmd", "w").write("0f 36")
			except:
				print("[Standby] Write to /sys/class/cec/cmd failed.")

		gotoShutdownTime = int(config.usage.standby_to_shutdown_timer.value)
		if gotoShutdownTime:
			self.standbyTimeoutTimer.startLongTimer(gotoShutdownTime)

		if self.StandbyCounterIncrease: # Wakeup timer with value "yes" or "standby" (only standby mode) in SleepTimerEdit.
			gotoWakeupTime = isNextWakeupTime(True)
			if gotoWakeupTime != -1:
				curtime = localtime(time())
				if curtime.tm_year > 1970:
					wakeup_time = int(gotoWakeupTime - time())
					if wakeup_time > 0:
						self.standbyWakeupTimer.startLongTimer(wakeup_time)

		self.onFirstExecBegin.append(self.__onFirstExecBegin)
		self.onClose.append(self.__onClose)

	def __onClose(self):
		global inStandby
		inStandby = None
		self.standbyTimeoutTimer.stop()
		self.standbyStopServiceTimer.stop()
		self.standbyWakeupTimer.stop()
		self.timeHandler and self.timeHandler.m_timeUpdated.get().remove(self.stopService)
		if self.paused_service:
			self.paused_action and self.paused_service.unPauseService()
		elif self.prev_running_service:
			service = self.prev_running_service.toString()
			if config.servicelist.startupservice_onstandby.value:
				self.session.nav.playService(eServiceReference(config.servicelist.startupservice.value))
				self.infoBarInstance and self.infoBarInstance.servicelist.correctChannelNumber()
			else:
				self.session.nav.playService(self.prev_running_service)
		self.session.screen["Standby"].boolean = False
		globalActionMap.setEnabled(True)
		if RecordTimer.RecordTimerEntry.receiveRecordEvents:
			RecordTimer.RecordTimerEntry.stopTryQuitMainloop()
		self.avswitch.setInput("ENCODER")
		self.leaveMute()
		if isfile("/usr/script/standby_leave.sh"):
			Console().ePopen("/usr/script/standby_leave.sh")
		if config.usage.remote_fallback_import_standby.value and not config.clientmode.enabled.value:
			ImportChannels()

	def __onFirstExecBegin(self):
		global inStandby
		inStandby = self
		self.session.screen["Standby"].boolean = True
		if self.StandbyCounterIncrease:
			config.misc.standbyCounter.value += 1

	def Power(self):
		print("[Standby] leave standby")
		BoxInfo.setItem("StandbyState", False)
		self.close(True)

		if isfile("/usr/script/StandbyLeave.sh"):
			Console().ePopen("/usr/script/StandbyLeave.sh")

		if isfile("/proc/stb/hdmi/output"):
			try:
				print("[Standby] Write to /proc/stb/hdmi/output")
				open("/proc/stb/hdmi/output", "w").write("on")
			except:
				print("[Standby] Write to /proc/stb/hdmi/output failed.")

		if BoxInfo.getItem("AmlogicFamily"):
			try:
				print("[Standby] Write to /sys/class/leds/led-sys/brightness")
				open("/sys/class/leds/led-sys/brightness", "w").write("1")
			except:
				print("[Standby] Write to /sys/class/leds/led-sys/brightness failed")
			try:
				print("[Standby] Write to /sys/class/cec/cmd")
				open("/sys/class/cec/cmd", "w").write("10 04")
			except:
				print("[Standby] Write to /sys/class/cec/cmd failed.")

	def setMute(self):
		self.wasMuted = eDVBVolumecontrol.getInstance().isMuted()
		if not self.wasMuted:
			eDVBVolumecontrol.getInstance().volumeMute()

	def leaveMute(self):
		if not self.wasMuted:
			eDVBVolumecontrol.getInstance().volumeUnMute()

	def stopService(self):
		self.prev_running_service = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if Components.ParentalControl.parentalControl.isProtected(self.prev_running_service):
			self.prev_running_service = eServiceReference(config.tv.lastservice.value)
		self.session.nav.stopService()

	def standbyTimeout(self):
		if config.usage.standby_to_shutdown_timer_blocktime.value:
			curtime = localtime(time())
			if curtime.tm_year > 1970: #check if the current time is valid
				curtime = (curtime.tm_hour, curtime.tm_min, curtime.tm_sec)
				begintime = tuple(config.usage.standby_to_shutdown_timer_blocktime_begin.value)
				endtime = tuple(config.usage.standby_to_shutdown_timer_blocktime_end.value)
				if begintime <= endtime and (curtime >= begintime and curtime < endtime) or begintime > endtime and (curtime >= begintime or curtime < endtime):
					duration = (endtime[0] * 3600 + endtime[1] * 60) - (curtime[0] * 3600 + curtime[1] * 60 + curtime[2])
					if duration:
						if duration < 0:
							duration += 24 * 3600
						self.standbyTimeoutTimer.startLongTimer(duration)
						return
		if self.session.screen["TunerInfo"].tuner_use_mask or mediaFilesInUse(self.session):
			self.standbyTimeoutTimer.startLongTimer(600)
		else:
			RecordTimer.RecordTimerEntry.TryQuitMainloop()

	def standbyWakeup(self):
		self.Power()

	def createSummary(self):
		return StandbySummary


class Standby(StandbyScreen):
	def __init__(self, session, StandbyCounterIncrease=True):
		if checkTimeshiftRunning():
			self.skin = """<screen position="0,0" size="0,0"/>"""
			Screen.__init__(self, session)
			self.infoBarInstance = isInfoBarInstance()
			self.StandbyCounterIncrease = StandbyCounterIncrease
			self.onFirstExecBegin.append(self.showCheckTimeshiftRunning)
			self.onHide.append(self.close)
		else:
			StandbyScreen.__init__(self, session, StandbyCounterIncrease)

	def showCheckTimeshiftRunning(self):
		self.infoBarInstance.checkTimeshiftRunning(self.showCheckTimeshiftRunningCallback, timeout=20)

	def showCheckTimeshiftRunningCallback(self, answer=False):
		if answer:
			self.onClose.append(self.goStandby)

	def goStandby(self):
		AddNotification(StandbyScreen, self.StandbyCounterIncrease)


class StandbySummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget source="global.CurrentTime" render="Label" position="0,0" size="132,64" font="Regular;40" horizontalAlignment="center">
			<convert type="ClockToText" />
		</widget>
		<widget source="session.RecordState" render="FixedLabel" text=" " position="0,0" size="132,64" zPosition="1" >
			<convert type="ConfigEntryTest">config.usage.blinking_display_clock_during_recording,True,CheckSourceBoolean</convert>
			<convert type="ConditionalShowHide">Blink</convert>
		</widget>
	</screen>"""


class QuitMainloopScreen(Screen):
	def __init__(self, session, retvalue=QUIT_SHUTDOWN):
		self.skin = """<screen name="QuitMainloopScreen" position="fill" flags="wfNoBorder">
				<ePixmap pixmap="icons/input_info.png" position="c-27,c-60" size="53,53" alphaTest="on" />
				<widget name="text" position="center,c+5" size="720,100" font="Regular;22" horizontalAlignment="center" />
			</screen>"""
		Screen.__init__(self, session)
		from Components.Label import Label
		text = {
			QUIT_SHUTDOWN: _("Your %s %s is shutting down") % (displaybrand, displaymodel),
			QUIT_REBOOT: _("Your %s %s is rebooting") % (displaybrand, displaymodel),
			QUIT_RESTART: _("The user interface of your %s %s is restarting") % (displaybrand, displaymodel),
			QUIT_UPGRADE_FP: _("Your frontprocessor will be updated\nPlease wait until your %s %s reboots\nThis may take a few minutes") % (displaybrand, displaymodel),
			QUIT_DEBUG_RESTART: _("The user interface of your %s %s is restarting in debug mode") % (displaybrand, displaymodel),
			QUIT_REBOOT_ANDROID: _("Your %s %s is rebooting into android mode") % (displaybrand, displaymodel),
			QUIT_REBOOT_RECOVERY: _("Your %s %s is rebooting into recovery mode") % (displaybrand, displaymodel),
			QUIT_UPGRADE_PROGRAM: _("Unattended update in progress\nPlease wait until your %s %s reboots\nThis may take a few minutes") % (displaybrand, displaymodel),
			QUIT_MANUFACTURER_RESET: _("Manufacturer reset in progress\nPlease wait until your %s %s restarts") % (displaybrand, displaymodel),
			QUIT_UPGRADE_FPANEL: _("Front panel your %s %s will be updated\nThis may take a few minutes") % (displaybrand, displaymodel),
			QUIT_WOL: _("Your %s %s goes to WOL") % (displaybrand, displaymodel)
		}.get(retvalue)
		self["text"] = Label(text)


inTryQuitMainloop = False


def getReasons(session, retvalue=QUIT_SHUTDOWN):
	recordings = session.nav.getRecordings()
	jobs = len(job_manager.getPendingJobs())
	reasons = []
	next_rec_time = -1
	if not recordings:
		next_rec_time = session.nav.RecordTimer.getNextRecordingTime()
	if recordings or (next_rec_time > 0 and (next_rec_time - time()) < 360):
		reasons.append(_("Recording(s) are in progress or coming up in few seconds!"))
	if jobs:
		if jobs == 1:
			job = job_manager.getPendingJobs()[0]
			reasons.append("%s: %s (%d%%)" % (job.getStatustext(), job.name, int(100 * job.progress / float(job.end))))
		else:
			reasons.append((ngettext("%d job is running in the background!", "%d jobs are running in the background!", jobs) % jobs))
	if checkTimeshiftRunning():
		reasons.append(_("You seem to be in timeshift!"))
	if eStreamServer.getInstance().getConnectedClients() or StreamServiceList:
		reasons.append(_("Client is streaming from this box!"))
	if not reasons and mediaFilesInUse(session) and retvalue in (QUIT_SHUTDOWN, QUIT_REBOOT, QUIT_RESTART, QUIT_UPGRADE_FP, QUIT_UPGRADE_PROGRAM, QUIT_UPGRADE_FPANEL):
		reasons.append(_("A file from media is in use!"))
	return "\n".join(reasons)


class TryQuitMainloop(MessageBox):
	def __init__(self, session, retvalue=QUIT_SHUTDOWN, timeout=-1, default_yes=False, check_reasons=True):
		self.retval = retvalue
		self.connected = False
		reason = check_reasons and getReasons(session, retvalue)
		if reason:
			text = {
				QUIT_SHUTDOWN: _("Really shutdown now?"),
				QUIT_REBOOT: _("Really reboot now?"),
				QUIT_RESTART: _("Really restart now?"),
				QUIT_UPGRADE_FP: _("Really update the front processor and reboot now?"),
				QUIT_DEBUG_RESTART: _("Really restart in debug mode now?"),
				QUIT_REBOOT_ANDROID: _("Really reboot into android mode?"),
				QUIT_REBOOT_RECOVERY: _("Really reboot into recovery mode?"),
				QUIT_UPGRADE_PROGRAM: _("Really update your settop box and reboot now?"),
				QUIT_MANUFACTURER_RESET: _("Really perform a manufacturer reset now?"),
				QUIT_UPGRADE_FPANEL: _("Really update the front panel and reboot now?"),
				QUIT_WOL: _("Really WOL now?")
			}.get(retvalue, None)
			if text:
				MessageBox.__init__(self, session, "%s\n%s" % (reason, text), type=MessageBox.TYPE_YESNO, timeout=timeout, default=default_yes)
				self.skinName = "MessageBoxSimple"
				session.nav.record_event.append(self.getRecordEvent)
				self.connected = True
				self.onShow.append(self.__onShow)
				self.onHide.append(self.__onHide)
				return
		self.skin = """<screen position="0,0" size="0,0"/>"""
		Screen.__init__(self, session)
		self.close(True)

	def getRecordEvent(self, recservice, event):
		if event == iRecordableService.evEnd:
			recordings = self.session.nav.getRecordings()
			if not recordings: # no more recordings exist
				rec_time = self.session.nav.RecordTimer.getNextRecordingTime()
				if rec_time > 0 and (rec_time - time()) < 360:
					self.initTimeout(360) # wait for next starting timer
					self.startTimer()
				else:
					self.close(True) # immediate shutdown
		elif event == iRecordableService.evStart:
			self.stopTimer()

	def close(self, value):
		if self.connected:
			self.connected = False
			self.session.nav.record_event.remove(self.getRecordEvent)
		if value:
			self.hide()
			if self.retval == QUIT_SHUTDOWN:
				config.misc.DeepStandby.value = True
				if not inStandby:
					if isfile("/usr/script/standby_enter.sh"):
						Console().ePopen("/usr/script/standby_enter.sh")
			elif not inStandby:
				config.misc.RestartUI.value = True
				config.misc.RestartUI.save()
			if BoxInfo.getItem("Display") and BoxInfo.getItem("LCDMiniTV"):
				print("[Standby] LCDminiTV off")
				try:
					print("[Standby] Write to /proc/stb/lcd/mode")
					open("/proc/stb/lcd/mode", "w").write(0)
				except:
					print("[Standby] Write to /proc/stb/lcd/mode failed.")
			if model == "vusolo4k":
				try:
					print("[Standby] Write to /proc/stb/fp/oled_brightness")
					open("/proc/stb/fp/oled_brightness", "w").write("0")
				except:
					print("[Standby] Write to /proc/stb/fp/oled_brightness failed.")
			if model == "pulse4k":
				try:
					print("[Standby] Write to /proc/stb/lcd/oled_brightness")
					open("/proc/stb/lcd/oled_brightness", "w").write("0")
				except:
					print("[Standby] Write to /proc/stb/lcd/oled_brightness failed.")
			self.quitMainloop()
		else:
			MessageBox.close(self, True)

	def quitMainloop(self):
		self.session.nav.stopService()
		self.quitScreen = self.session.instantiateDialog(QuitMainloopScreen, retvalue=self.retval)
		self.quitScreen.show()
		quitMainloop(self.retval)

	def __onShow(self):
		global inTryQuitMainloop
		inTryQuitMainloop = True

	def __onHide(self):
		global inTryQuitMainloop
		inTryQuitMainloop = False

	def createSummary(self):  # Suppress the normal MessageBox ScreenSummary screen.
		return None


class SwitchToAndroid(Screen):
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self["myActionMap"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"ok": self.goAndroid,
			"cancel": self.close,
		}, -1)
		self.onShown.append(self.switchAndroid)

	def goAndroid(self, answer):
		from Screens.Standby import TryQuitMainloop
		if answer:
			with open('/dev/block/by-name/flag', 'wb') as f:
				f.write(struct.pack("B", 0))
			self.session.open(TryQuitMainloop, 2)
		else:
			self.close()

	def switchAndroid(self):
		self.onShown.remove(self.switchAndroid)
		self.session.openWithCallback(self.goAndroid, MessageBox, _("\n Do you want to switch to Android ?"))
