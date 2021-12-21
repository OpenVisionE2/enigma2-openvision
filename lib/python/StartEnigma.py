from Tools.Profile import profile, profileFinal  # This facilitates the start up progress counter.
profile("StartPython")
import Tools.RedirectOutput  # Don't remove this line. This import facilitates connecting stdout and stderr redirections to the log files.

import enigma  # Establish enigma2 connections to processing methods.
import eBaseImpl
import eConsoleImpl
enigma.eTimer = eBaseImpl.eTimer
enigma.eSocketNotifier = eBaseImpl.eSocketNotifier
enigma.eConsoleAppContainer = eConsoleImpl.eConsoleAppContainer


# Session.open:
# * Push current active dialog ("current_dialog") onto stack.
# * Call execEnd for this dialog.
#   * Clear in_exec flag.
#   * Hide screen.
# * Instantiate new dialog into "current_dialog".
#   * Create screens, components.
#   * Read and apply skin.
#   * Create GUI for screen.
# * Call execBegin for new dialog.
#   * Set in_exec.
#   * Show GUI screen.
#   * Call components' / screen's onExecBegin.
# ... Screen is active, until it calls "close"...
#
# Session.close:
# * Assert in_exec.
# * Save return value.
# * Start deferred close handler ("onClose").
# * Call execEnd.
#   * Clear in_exec.
#   * Hide screen.
# .. a moment later:
# Session.doClose:
# * Destroy screen.
#
class Session:
	def __init__(self, desktop=None, summaryDesktop=None, navigation=None):
		self.desktop = desktop
		self.summaryDesktop = summaryDesktop
		self.nav = navigation
		self.delay_timer = enigma.eTimer()
		self.delay_timer.callback.append(self.processDelay)
		self.current_dialog = None
		self.dialog_stack = []
		self.summary_stack = []
		self.summary = None
		self.in_exec = False
		self.screen = SessionGlobals(self)
		for plugin in plugins.getPlugins(PluginDescriptor.WHERE_SESSIONSTART):
			try:
				plugin.__call__(reason=0, session=self)
			except:
				print("[StartEnigma] Error: Plugin raised exception at WHERE_SESSIONSTART!")
				import traceback
				traceback.print_exc()

	def processDelay(self):
		callback = self.current_dialog.callback
		retVal = self.current_dialog.returnValue
		if self.current_dialog.isTmp:
			self.current_dialog.doClose()
			# dump(self.current_dialog)
			del self.current_dialog
		else:
			del self.current_dialog.callback
		self.popCurrent()
		if callback is not None:
			callback(*retVal)

	def execBegin(self, first=True, do_show=True):
		if self.in_exec:
			raise AssertionError("[StartEnigma] Error: Already in exec!")
		self.in_exec = True
		currentDialog = self.current_dialog
		# When this is an execbegin after a execEnd of a "higher" dialog,
		# popSummary already did the right thing.
		if first:
			self.instantiateSummaryDialog(currentDialog)
		currentDialog.saveKeyboardMode()
		currentDialog.execBegin()
		# When execBegin opened a new dialog, don't bother showing the old one.
		if currentDialog == self.current_dialog and do_show:
			currentDialog.show()

	def execEnd(self, last=True):
		assert self.in_exec
		self.in_exec = False
		self.current_dialog.execEnd()
		self.current_dialog.restoreKeyboardMode()
		self.current_dialog.hide()
		if last and self.summary is not None:
			self.current_dialog.removeSummary(self.summary)
			self.popSummary()

	def instantiateDialog(self, screen, *arguments, **kwargs):
		return self.doInstantiateDialog(screen, arguments, kwargs, self.desktop)

	def deleteDialog(self, screen):
		screen.hide()
		screen.doClose()

	def deleteDialogWithCallback(self, callback, screen, *retVal):
		screen.hide()
		screen.doClose()
		if callback is not None:
			callback(*retVal)

	def instantiateSummaryDialog(self, screen, **kwargs):
		if self.summaryDesktop is not None:
			self.pushSummary()
			summary = screen.createSummary() or SimpleSummary
			arguments = (screen,)
			self.summary = self.doInstantiateDialog(summary, arguments, kwargs, self.summaryDesktop)
			self.summary.show()
			screen.addSummary(self.summary)

	def doInstantiateDialog(self, screen, arguments, kwargs, desktop):
		dialog = screen(self, *arguments, **kwargs)  # Create dialog.
		if dialog is None:
			return
		readSkin(dialog, None, dialog.skinName, desktop)  # Read skin data.
		dialog.setDesktop(desktop)  # Create GUI view of this dialog.
		dialog.applySkin()
		return dialog

	def pushCurrent(self):
		if self.current_dialog is not None:
			self.dialog_stack.append((self.current_dialog, self.current_dialog.shown))
			self.execEnd(last=False)

	def popCurrent(self):
		if self.dialog_stack:
			(self.current_dialog, do_show) = self.dialog_stack.pop()
			self.execBegin(first=False, do_show=do_show)
		else:
			self.current_dialog = None

	def execDialog(self, dialog):
		self.pushCurrent()
		self.current_dialog = dialog
		self.current_dialog.isTmp = False
		self.current_dialog.callback = None  # Would cause re-entrancy problems.
		self.execBegin()

	def openWithCallback(self, callback, screen, *arguments, **kwargs):
		dialog = self.open(screen, *arguments, **kwargs)
		dialog.callback = callback
		return dialog

	def open(self, screen, *arguments, **kwargs):
		if self.dialog_stack and not self.in_exec:
			raise RuntimeError("[StartEnigma] Error: Modal open are allowed only from a screen which is modal!")  # ...unless it's the very first screen.
		self.pushCurrent()
		dialog = self.current_dialog = self.instantiateDialog(screen, *arguments, **kwargs)
		dialog.isTmp = True
		dialog.callback = None
		self.execBegin()
		return dialog

	def close(self, screen, *retVal):
		if not self.in_exec:
			print("[StartEnigma] Close after exec!")
			return
		# Be sure that the close is for the right dialog!  If it's
		# not, you probably closed after another dialog was opened.
		# This can happen if you open a dialog onExecBegin, and
		# forget to do this only once.  After close of the top
		# dialog, the underlying dialog will gain focus again (for
		# a short time), thus triggering the onExec, which opens the
		# dialog again, closing the loop.
		if not screen == self.current_dialog:
			raise AssertionError("[StartEnigma] Error: Attempt to close non-current screen!")
		self.current_dialog.returnValue = retVal
		self.delay_timer.start(0, 1)
		self.execEnd()

	def pushSummary(self):
		if self.summary is not None:
			self.summary.hide()
			self.summary_stack.append(self.summary)
			self.summary = None

	def popSummary(self):
		if self.summary is not None:
			self.summary.doClose()
		if not self.summary_stack:
			self.summary = None
		else:
			self.summary = self.summary_stack.pop()
		if self.summary is not None:
			self.summary.show()


class PowerKey:
	"""PowerKey code - Handles the powerkey press and powerkey release actions."""

	def __init__(self, session):
		self.session = session
		globalActionMap.actions["power_down"] = lambda *args: None
		globalActionMap.actions["power_up"] = self.powerup
		globalActionMap.actions["power_long"] = self.powerlong
		globalActionMap.actions["deepstandby"] = self.shutdown  # Front panel long power button press.
		globalActionMap.actions["discrete_off"] = self.standby

	def powerup(self):
		if not Screens.Standby.inStandby and self.session.current_dialog and self.session.current_dialog.ALLOW_SUSPEND and self.session.in_exec:
			self.doAction(config.misc.hotkey.power.value)
		else:
			return 0

	def powerlong(self):
		if not Screens.Standby.inStandby and self.session.current_dialog and self.session.current_dialog.ALLOW_SUSPEND and self.session.in_exec:
			self.doAction(config.misc.hotkey.power_long.value)
		else:
			return 0

	def shutdown(self):
		print("[StartEnigma] Power off, now!")
		if not Screens.Standby.inTryQuitMainloop and self.session.current_dialog and self.session.current_dialog.ALLOW_SUSPEND:
			self.session.open(Screens.Standby.TryQuitMainloop, 1)  # QUIT_SHUTDOWN
		else:
			return 0

	def standby(self):
		if not Screens.Standby.inStandby and self.session.current_dialog and self.session.current_dialog.ALLOW_SUSPEND and self.session.in_exec:
			self.session.open(Screens.Standby.Standby)
		else:
			return 0

	def doAction(self, selected):
		if selected:
			selected = selected.split("/")
			if selected[0] == "Module":
				try:
					exec("from %s import *" % selected[1])
					exec("self.session.open(%s)" % ",".join(selected[2:]))
				except Exception:
					print("[StartEnigma] Error: Exception executing module '%s' screen '%s'!" % (selected[1], selected[2]))
			elif selected[0] == "Menu":
				root = mdom.getroot()
				for menu in root.findall("menu"):
					id = menu.find("id")
					if id is not None:
						val = id.get("val")
						if val and val == selected[1]:
							self.session.open(MainMenu, menu)


class AutoScartControl:
	def __init__(self, session):
		self.force = False
		self.current_vcr_sb = enigma.eAVSwitch.getInstance().getVCRSlowBlanking()
		if self.current_vcr_sb and config.av.vcrswitch.value:
			self.scartDialog = session.instantiateDialog(Scart, True)
		else:
			self.scartDialog = session.instantiateDialog(Scart, False)
		config.av.vcrswitch.addNotifier(self.recheckVCRSb)
		enigma.eAVSwitch.getInstance().vcr_sb_notifier.get().append(self.VCRSbChanged)

	def recheckVCRSb(self, configElement):
		self.VCRSbChanged(self.current_vcr_sb)

	def VCRSbChanged(self, value):
		# print("VCR SB changed to '%s'." % value)
		self.current_vcr_sb = value
		if config.av.vcrswitch.value or value > 2:
			if value:
				self.scartDialog.showMessageBox()
			else:
				self.scartDialog.switchToTV()


def runScreen():
	def runNextScreen(session, screensToRun, *result):
		if result:
			enigma.quitMainloop(*result)
			return
		screen = screensToRun[0][1]
		args = screensToRun[0][2:]
		if screensToRun:
			session.openWithCallback(boundFunction(runNextScreen, session, screensToRun[1:]), screen, *args)
		else:
			session.open(screen, *args)

	config.misc.startCounter.value += 1
	config.misc.startCounter.save()
	profile("ReadPluginList")
	enigma.pauseInit()
	plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
	enigma.resumeInit()
	profile("InitSession")
	nav = Navigation(config.misc.isNextRecordTimerAfterEventActionAuto.value, config.misc.isNextPowerTimerAfterEventActionAuto.value)  # Wake up to standby for RecordTimer and PowerTimer.
	session = Session(desktop=enigma.getDesktop(0), summaryDesktop=enigma.getDesktop(1), navigation=nav)
	CiHandler.setSession(session)
	screensToRun = [x.__call__ for x in plugins.getPlugins(PluginDescriptor.WHERE_WIZARD)]
	profile("InitWizards")
	screensToRun += wizardManager.getWizards()
	screensToRun.append((100, InfoBar.InfoBar))
	screensToRun.sort()
	enigma.ePythonConfigQuery.setQueryFunc(configfile.getResolvedKey)
	config.misc.epgcache_filename.addNotifier(setEPGCachePath)
	runNextScreen(session, screensToRun)
	profile("InitVolumeControl")
	vol = VolumeControl(session)
	profile("InitPowerKey")
	power = PowerKey(session)
	if BoxInfo.getItem("VFDSymbol"):
		profile("VFDSymbols")
		import Components.VfdSymbols
		Components.VfdSymbols.SymbolsCheck(session)
	session.scart = AutoScartControl(session)  # We need session.scart to access it from within menu.xml.
	profile("InitTrashcan")
	import Tools.Trashcan
	Tools.Trashcan.init(session)
	profile("RunReactor")
	profileFinal()
	runReactor()
	profile("Wakeup")
	from Tools.StbHardware import setFPWakeuptime, setRTCtime
	from Screens.SleepTimerEdit import isNextWakeupTime
	powerTimerWakeupAuto = False
	recordTimerWakeupAuto = False
	nowTime = time()  # Get current time.
	powerTimerList = sorted(
		[x for x in ((session.nav.RecordTimer.getNextRecordingTime(), 0, session.nav.RecordTimer.isNextRecordAfterEventActionAuto()),
					(session.nav.RecordTimer.getNextZapTime(isWakeup=True), 1),
					(plugins.getNextWakeupTime(), 2),
					(session.nav.PowerTimer.getNextPowerManagerTime(), 3, session.nav.PowerTimer.isNextPowerManagerAfterEventActionAuto()))
		if x[0] != -1]
	)
	sleepTimerList = sorted(
		[x for x in (
			(session.nav.RecordTimer.getNextRecordingTime(), 0),
			(session.nav.RecordTimer.getNextZapTime(isWakeup=True), 1),
			(plugins.getNextWakeupTime(), 2),
			(isNextWakeupTime(), 3)
		)
		if x[0] != -1]
	)
	if sleepTimerList:
		startSleepTime = sleepTimerList[0]
		if (startSleepTime[0] - nowTime) < 270:  # No time to switch box back on.
			wakeupTime = nowTime + 30  # So switch back on in 30 seconds.
		else:
			if brand == "gigablue":
				wakeupTime = startSleepTime[0] - 120  # GigaBlue already starts 2 min. before wakeup time.
			else:
				wakeupTime = startSleepTime[0] - 240
		if not config.ntp.timesync.value == "dvb":
			setRTCtime(nowTime)
		setFPWakeuptime(wakeupTime)
	if powerTimerList and powerTimerList[0][1] == 3:
		startTimePowerList = powerTimerList[0]
		if (startTimePowerList[0], nowTime) < 60:  # No time to switch box back on.
			wakeupTime = nowTime + 30  # So switch back on in 30 seconds.
		else:
			wakeupTime = startTimePowerList[0]
		if not config.ntp.timesync.value == "dvb":
			setRTCtime(nowTime)
		setFPWakeuptime(wakeupTime)
		powerTimerWakeupAuto = startTimePowerList[1] == 3 and startTimePowerList[2]
	config.misc.isNextPowerTimerAfterEventActionAuto.value = powerTimerWakeupAuto
	config.misc.isNextPowerTimerAfterEventActionAuto.save()
	if powerTimerList and powerTimerList[0][1] != 3:
		startTimePowerList = powerTimerList[0]
		if (startTimePowerList[0], nowTime) < 270:  # No time to switch box back on.
			wakeupTime = nowTime + 30  # So switch back on in 30 seconds.
		else:
			wakeupTime = (startTimePowerList[0], 240)
		if not config.ntp.timesync.value == "dvb":
			setRTCtime(nowTime)
		setFPWakeuptime(wakeupTime)
		recordTimerWakeupAuto = startTimePowerList[1] == 0 and startTimePowerList[2]
	config.misc.isNextRecordTimerAfterEventActionAuto.value = recordTimerWakeupAuto
	config.misc.isNextRecordTimerAfterEventActionAuto.save()
	profile("StopNavService")
	session.nav.stopService()
	profile("NavShutdown")
	session.nav.shutdown()
	profile("SaveConfigfile")
	configfile.save()
	from Screens import InfoBarGenerics
	InfoBarGenerics.saveResumePoints()
	return 0


def localeNotifier(configElement):
	international.activateLocale(configElement.value)


def setLoadUnlinkedUserbouquets(configElement):
	enigma.eDVBDB.getInstance().setLoadUnlinkedUserbouquets(configElement.value)


def setEPGCachePath(configElement):
	if isdir(configElement.value) or islink(configElement.value):
		configElement.value = pathjoin(configElement.value, "epg.dat")
	enigma.eEPGCache.getInstance().setCacheFile(configElement.value)


def dump(dir, p=""):
	had = dict()
	if isinstance(dir, dict):
		for (entry, val) in dir.items():
			dump(val, p + "(dict)/" + entry)
	if hasattr(dir, "__dict__"):
		for name, value in dir.__dict__.items():
			if str(value) not in had:
				had[str(value)] = 1
				dump(value, p + "/" + str(name))
			else:
				print("%s/%s:%s(cycle)" % (p, str(name), str(dir.__class__)))
	else:
		print("%s:%s" % (p, str(dir)))
		# + ":" + str(dir.__class__)


# Demo code for use of standby enter leave callbacks.
#
# def leaveStandby():
# 	print("[StartEnigma] Leaving standby.")
#
#
# def standbyCountChanged(configElement):
# 	print("!!!!!!!!!!!!!!!!!enter standby num %s" % configElement.value)
# 	from Screens.Standby import inStandby
# 	inStandby.onClose.append(leaveStandby)
#
#
# config.misc.standbyCounter.addNotifier(standbyCountChanged, initial_call=False)

#################################
#                               #
#  Code execution starts here!  #
#                               #
#################################

from sys import stdout

MODULE_NAME = __name__.split(".")[-1]

profile("Twisted")
try:  # Configure the twisted processor
	from twisted.python.runtime import platform
	platform.supportsThreads = lambda: True
	from e2reactor import install
	install()
	from twisted.internet import reactor

	def runReactor():
		reactor.run(installSignalHandlers=False)

except ImportError:
	print("[StartEnigma] Error: Twisted not available!")

	def runReactor():
		enigma.runMainloop()

try:  # Configure the twisted logging
	from twisted.python import log, util

	def quietEmit(self, eventDict):
		text = log.textFromEventDict(eventDict)
		if text is None:
			return
		formatDict = {
			"text": text.replace("\n", "\n\t")
		}
		msg = log._safeFormat("%(text)s\n", formatDict)
		util.untilConcludes(self.write, msg)
		util.untilConcludes(self.flush)

	logger = log.FileLogObserver(stdout)
	log.FileLogObserver.emit = quietEmit
	log.startLoggingWithObserver(logger.emit)
except ImportError:
	print("[StartEnigma] Error: Twisted not available!")

profile("SystemInfo")
from enigma import getE2Rev
from Components.SystemInfo import BoxInfo

model = BoxInfo.getItem("model")
brand = BoxInfo.getItem("brand")
platform = BoxInfo.getItem("platform")
socfamily = BoxInfo.getItem("socfamily")

print("[StartEnigma] Receiver name = %s %s" % (BoxInfo.getItem("displaybrand"), BoxInfo.getItem("displaymodel")))
print("[StartEnigma] %s version = %s" % (BoxInfo.getItem("displaydistro"), BoxInfo.getItem("imgversion")))
print("[StartEnigma] %s revision = %s" % (BoxInfo.getItem("displaydistro"), BoxInfo.getItem("imgrevision")))
print("[StartEnigma] Build Brand = %s" % brand)
print("[StartEnigma] Build Model = %s" % model)
print("[StartEnigma] Platform = %s" % platform)
print("[StartEnigma] SoC family = %s" % socfamily)
print("[StartEnigma] Enigma2 revision = %s" % getE2Rev())

profile("Imports")
from os.path import isdir, isfile, islink, join as pathjoin
from traceback import print_exc
from time import localtime, strftime, time

from Components.config import ConfigInteger, ConfigOnOff, ConfigSubsection, ConfigText, ConfigYesNo, NoSave, config, configfile
from Components.Console import Console
from Components.International import international
# from Screens.Standby import QUIT_ERROR_RESTART
from Tools.Directories import InitDefaultPaths, SCOPE_GUISKIN, SCOPE_PLUGINS, fileReadLine, fileWriteLine, resolveFilename

profile("CreateDefaultPaths")
InitDefaultPaths()

profile("BusyBoxInetd")
if isfile("/etc/init.d/inetd.busybox"):
	print("[StartEnigma] Starting BusyBox inetd to allow FTP access.")
	Console().ePopen("/etc/init.d/inetd.busybox start")
	print("[StartEnigma] Finished starting BusyBox inetd.")

profile("MultiLib")
if BoxInfo.getItem("multilib"):
	import usb.core
	import usb.backend.libusb1
	usb.backend.libusb1.get_backend(find_library=lambda x: "/lib64/libusb-1.0.so.0")

# These entries could be moved back to UsageConfig.py when it is safe to bring UsageConfig init to this location in StartEnigma2.py.
#
profile("InitializeConfigs")
config.crash = ConfigSubsection()
config.crash.debugActionMaps = ConfigYesNo(default=False)
config.crash.debugKeyboards = ConfigYesNo(default=False)
config.crash.debugRemoteControls = ConfigYesNo(default=False)
config.crash.debugScreens = ConfigYesNo(default=False)
config.expert = ConfigSubsection()
config.expert.autoinfo = ConfigOnOff(default=True)
config.expert.fastzap = ConfigOnOff(default=True)
config.expert.hideerrors = ConfigOnOff(default=False)
config.expert.satpos = ConfigOnOff(default=True)
config.expert.skipconfirm = ConfigOnOff(default=False)
config.osd = ConfigSubsection()
config.osd.language = ConfigText(default="en_US")
config.osd.language.addNotifier(localeNotifier)
config.misc.country = ConfigText(default="US")
config.misc.DeepStandby = NoSave(ConfigYesNo(default=False))  # Detect deepstandby.
config.misc.epgcache_filename = ConfigText(default="/hdd/epg.dat", fixed_size=False)
config.misc.language = ConfigText(default="en")
config.misc.load_unlinked_userbouquets = ConfigYesNo(default=True)
config.misc.load_unlinked_userbouquets.addNotifier(setLoadUnlinkedUserbouquets)
config.misc.locale = ConfigText(default="en_US")
# config.misc.locale.addNotifier(localeNotifier)  # This should not be enabled while config.osd.language is in use!
config.misc.isNextRecordTimerAfterEventActionAuto = ConfigYesNo(default=False)  # Auto action after event in RecordTimer.
config.misc.isNextPowerTimerAfterEventActionAuto = ConfigYesNo(default=False)  # Auto action after event in PowerTimer.
config.misc.RestartUI = ConfigYesNo(default=False)  # Detect user interface restart.
config.misc.standbyCounter = NoSave(ConfigInteger(default=0))  # Number of standby.
config.misc.startCounter = ConfigInteger(default=0)  # Number of e2 starts.
config.parental = ConfigSubsection()
config.parental.lock = ConfigOnOff(default=False)
config.parental.setuplock = ConfigOnOff(default=False)

profile("ClientMode")
from Components.ClientMode import InitClientMode
InitClientMode()

profile("SimpleSummary")
from Screens import InfoBar
from Screens.SimpleSummary import SimpleSummary

profile("Bouquets")
if config.clientmode.enabled.value == False:
	enigma.eDVBDB.getInstance().reloadBouquets()

profile("ParentalControl")
from Components.ParentalControl import InitParentalControl
InitParentalControl()

profile("Navigation")
from Navigation import Navigation

profile("Skin")
from skin import readSkin

# The skin module must be loaded before a resolveFilename() can be run against a skin!
#
config.misc.blackradiopic = ConfigText(default=resolveFilename(SCOPE_GUISKIN, "black.mvi"))
config.misc.radiopic = ConfigText(default=resolveFilename(SCOPE_GUISKIN, "radio.mvi"))

profile("Plugins")
from Components.PluginComponent import plugins  # Initialize autorun plugins and plugin menu entries.

profile("Wizard")
from Screens.Wizard import wizardManager
from Screens.StartWizard import *
from Tools.BoundFunction import boundFunction
from Plugins.Plugin import PluginDescriptor

profile("ScreenGlobals")
from Screens.Globals import Globals
from Screens.SessionGlobals import SessionGlobals
from Screens.Screen import Screen

profile("Screen")
Screen.globalScreen = Globals()

profile("Standby")
import Screens.Standby

profile("MainMenu")
from Screens.Menu import MainMenu, mdom

profile("GloabalActions")
from GlobalActions import globalActionMap

profile("Scart")
from Screens.Scart import Scart

profile("VolumeControl")
from Components.VolumeControl import VolumeControl

profile("StackTracePrinter")
from Components.StackTrace import StackTracePrinter
StackTracePrinterInst = StackTracePrinter()

profile("Skin")
from skin import InitSkins
InitSkins()

profile("InputDevice")
import Components.InputDevice
Components.InputDevice.InitInputDevices()

profile("Hotplug")
import Components.InputHotplug

profile("AVSwitch")
import Components.AVSwitch
Components.AVSwitch.InitAVSwitch()

profile("FanControl")
from Components.FanControl import fancontrol

profile("HdmiRecord")
import Components.HdmiRecord
Components.HdmiRecord.InitHdmiRecord()

profile("RecordingConfig")
import Components.RecordingConfig
Components.RecordingConfig.InitRecordingConfig()

profile("UsageConfig")
import Components.UsageConfig
Components.UsageConfig.InitUsageConfig()

profile("TimeZones")
from Components.Timezones import InitTimeZones
InitTimeZones()

profile("Keymap")
from Components.ActionMap import loadKeymap
loadKeymap(config.usage.keymap.value)

profile("Network")
from Components.Network import InitNetwork
InitNetwork()

profile("LCD")
import Components.Lcd
Components.Lcd.InitLcd()
Components.Lcd.IconCheck()

if platform == "dm4kgen" or model in ("dm7080", "dm820"):
	filename = "/proc/stb/hdmi-rx/0/hdmi_rx_monitor"
	check = fileReadLine(filename, "", source=MODULE_NAME)
	if check.startswith("on"):
		fileWriteLine(filename, "off", source=MODULE_NAME)
	filename = "/proc/stb/audio/hdmi_rx_monitor"
	check = fileReadLine(filename, "", source=MODULE_NAME)
	if check.startswith("on"):
		fileWriteLine(filename, "off", source=MODULE_NAME)

profile("RFMod")
from Components.RFmod import InitRFmod
InitRFmod()

profile("CommonInterface")
from Screens.Ci import CiHandler, InitCiConfig
InitCiConfig()

profile("EpgCacheScheduler")
from Components.EpgLoadSave import EpgCacheLoadCheck, EpgCacheSaveCheck
EpgCacheSaveCheck()
EpgCacheLoadCheck()

if config.clientmode.enabled.value:
	from Components.ChannelsImporter import autostart
	autostart()

# from enigma import dump_malloc_stats
# timer = eTimer()
# timer.callback.append(dump_malloc_stats)
# timer.start(1000)

# Lets get going and load a screen.
#
try:
	runScreen()  # Start running the first screen.
	plugins.shutdown()  # Shutdown all plugins.
	Components.ParentalControl.parentalControl.save()  # Save parental control settings.
except Exception:
	print("Error: Exception in Python StartEnigma startup code:")
	print("=" * 52)
	print_exc(file=stdout)
	enigma.quitMainloop(5)  # QUIT_ERROR_RESTART
	print("-" * 52)
