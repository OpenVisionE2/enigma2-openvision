# -*- coding: utf-8 -*-
from __future__ import print_function
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigSlider, ConfigYesNo, ConfigNothing
from enigma import eDBoxLCD, eTimer, eActionMap, getBoxType
from Components.SystemInfo import SystemInfo
from Screens.InfoBar import InfoBar
from Screens.Screen import Screen
from Tools.Directories import fileExists
from sys import maxint
from twisted.internet import threads
import Screens.Standby
import usb

class dummyScreen(Screen):
	skin = """<screen position="0,0" size="0,0" transparent="1">
	<widget source="session.VideoPicture" render="Pig" position="0,0" size="0,0" backgroundColor="transparent" zPosition="1"/>
	</screen>"""
	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.close()

def IconCheck(session=None, **kwargs):
	if fileExists("/proc/stb/lcd/symbol_network") or fileExists("/proc/stb/lcd/symbol_usb"):
		global networklinkpoller
		networklinkpoller = IconCheckPoller()
		networklinkpoller.start()

class IconCheckPoller:
	def __init__(self):
		self.timer = eTimer()

	def start(self):
		if self.iconcheck not in self.timer.callback:
			self.timer.callback.append(self.iconcheck)
		self.timer.startLongTimer(0)

	def stop(self):
		if self.iconcheck in self.timer.callback:
			self.timer.callback.remove(self.iconcheck)
		self.timer.stop()

	def iconcheck(self):
		try:
			threads.deferToThread(self.JobTask)
		except:
			pass
		self.timer.startLongTimer(30)

	def JobTask(self):
		LinkState = 0
		if fileExists('/sys/class/net/wlan0/operstate'):
			LinkState = open('/sys/class/net/wlan0/operstate').read()
			if LinkState != 'down':
				LinkState = open('/sys/class/net/wlan0/operstate').read()
		elif fileExists('/sys/class/net/eth0/operstate'):
			LinkState = open('/sys/class/net/eth0/operstate').read()
			if LinkState != 'down':
				LinkState = open('/sys/class/net/eth0/carrier').read()
		LinkState = LinkState[:1]
		if fileExists("/proc/stb/lcd/symbol_network") and config.lcd.mode.value == '1':
			open("/proc/stb/lcd/symbol_network", "w").write(str(LinkState))
		elif fileExists("/proc/stb/lcd/symbol_network") and config.lcd.mode.value == '0':
			open("/proc/stb/lcd/symbol_network", "w").write("0")

		USBState = 0
		busses = usb.busses()
		for bus in busses:
			devices = bus.devices
			for dev in devices:
				if dev.deviceClass != 9 and dev.deviceClass != 2 and dev.idVendor != 3034 and dev.idVendor > 0:
					USBState = 1
		if fileExists("/proc/stb/lcd/symbol_usb"):
			open("/proc/stb/lcd/symbol_usb", "w").write(str(USBState))

		self.timer.startLongTimer(30)

class LCD:
	def __init__(self):
		eActionMap.getInstance().bindAction('', -maxint -1, self.DimUpEvent)
		self.autoDimDownLCDTimer = eTimer()
		self.autoDimDownLCDTimer.callback.append(self.autoDimDownLCD)
		self.autoDimUpLCDTimer = eTimer()
		self.autoDimUpLCDTimer.callback.append(self.autoDimUpLCD)
		self.currBrightness = self.dimBrightness = self.Brightness = None
		self.dimDelay = 0
		config.misc.standbyCounter.addNotifier(self.standbyCounterChanged, initial_call = False)

	def standbyCounterChanged(self, configElement):
		Screens.Standby.inStandby.onClose.append(self.leaveStandby)
		self.autoDimDownLCDTimer.stop()
		self.autoDimUpLCDTimer.stop()
		eActionMap.getInstance().unbindAction('', self.DimUpEvent)

	def leaveStandby(self):
		eActionMap.getInstance().bindAction('', -maxint -1, self.DimUpEvent)

	def DimUpEvent(self, key, flag):
		self.autoDimDownLCDTimer.stop()
		if not Screens.Standby.inTryQuitMainloop:
			if self.Brightness is not None and not self.autoDimUpLCDTimer.isActive():
				self.autoDimUpLCDTimer.start(10, True)

	def autoDimDownLCD(self):
		if not Screens.Standby.inTryQuitMainloop:
			if self.dimBrightness is not None and  self.currBrightness > self.dimBrightness:
				self.currBrightness = self.currBrightness - 1
				eDBoxLCD.getInstance().setLCDBrightness(self.currBrightness)
				self.autoDimDownLCDTimer.start(10, True)

	def autoDimUpLCD(self):
		if not Screens.Standby.inTryQuitMainloop:
			self.autoDimDownLCDTimer.stop()
			if self.currBrightness < self.Brightness:
				self.currBrightness = self.currBrightness + 5
				if self.currBrightness >= self.Brightness:
					self.currBrightness = self.Brightness
				eDBoxLCD.getInstance().setLCDBrightness(self.currBrightness)
				self.autoDimUpLCDTimer.start(10, True)
			else:
				if self.dimBrightness is not None and self.currBrightness > self.dimBrightness and self.dimDelay is not None and self.dimDelay > 0:
					self.autoDimDownLCDTimer.startLongTimer(self.dimDelay)

	def setBright(self, value):
		value *= 255
		value /= 10
		if value > 255:
			value = 255
		self.autoDimDownLCDTimer.stop()
		self.autoDimUpLCDTimer.stop()
		self.currBrightness = self.Brightness = value
		eDBoxLCD.getInstance().setLCDBrightness(self.currBrightness)
		if self.dimBrightness is not None and  self.currBrightness > self.dimBrightness:
			if self.dimDelay is not None and self.dimDelay > 0:
				self.autoDimDownLCDTimer.startLongTimer(self.dimDelay)

	def setStandbyBright(self, value):
		value *= 255
		value /= 10
		if value > 255:
			value = 255
		self.autoDimDownLCDTimer.stop()
		self.autoDimUpLCDTimer.stop()
		self.Brightness = value
		if self.dimBrightness is None:
			self.dimBrightness = value
		if self.currBrightness is None:
			self.currBrightness = value
		eDBoxLCD.getInstance().setLCDBrightness(self.Brightness)

	def setDimBright(self, value):
		value *= 255
		value /= 10
		if value > 255:
			value = 255
		self.dimBrightness = value

	def setDimDelay(self, value):
		self.dimDelay = int(value)

	def setContrast(self, value):
		value *= 63
		value /= 20
		if value > 63:
			value = 63
		eDBoxLCD.getInstance().setLCDContrast(value)

	def setInverted(self, value):
		if value:
			value = 255
		eDBoxLCD.getInstance().setInverted(value)

	def setFlipped(self, value):
		eDBoxLCD.getInstance().setFlipped(value)

	def setScreenShot(self, value):
 		eDBoxLCD.getInstance().setDump(value)

	def isOled(self):
		return eDBoxLCD.getInstance().isOled()

	def setMode(self, value):
		if fileExists("/proc/stb/lcd/show_symbols"):
			print('[Lcd] setLCDMode',value)
			open("/proc/stb/lcd/show_symbols", "w").write(value)
		if config.lcd.mode.value == "0":
			SystemInfo["SeekStatePlay"] = False
			SystemInfo["StatePlayPause"] = False
			if fileExists("/proc/stb/lcd/symbol_hdd"):
				open("/proc/stb/lcd/symbol_hdd", "w").write("0")
			if fileExists("/proc/stb/lcd/symbol_hddprogress"):
				open("/proc/stb/lcd/symbol_hddprogress", "w").write("0")
			if fileExists("/proc/stb/lcd/symbol_network"):
				open("/proc/stb/lcd/symbol_network", "w").write("0")
			if fileExists("/proc/stb/lcd/symbol_signal"):
				open("/proc/stb/lcd/symbol_signal", "w").write("0")
			if fileExists("/proc/stb/lcd/symbol_timeshift"):
				open("/proc/stb/lcd/symbol_timeshift", "w").write("0")
			if fileExists("/proc/stb/lcd/symbol_tv"):
				open("/proc/stb/lcd/symbol_tv", "w").write("0")
			if fileExists("/proc/stb/lcd/symbol_usb"):
				open("/proc/stb/lcd/symbol_usb", "w").write("0")

	def setPower(self, value):
		if fileExists("/proc/stb/power/vfd"):
			print('[Lcd] setLCDPower',value)
			open("/proc/stb/power/vfd", "w").write(value)
		elif fileExists("/proc/stb/lcd/vfd"):
			print('[Lcd] setLCDPower',value)
			open("/proc/stb/lcd/vfd", "w").write(value)

	def setShowoutputresolution(self, value):
		if fileExists("/proc/stb/lcd/show_outputresolution"):
			print('[Lcd] setLCDShowoutputresolution',value)
			open("/proc/stb/lcd/show_outputresolution", "w").write(value)

	def setfblcddisplay(self, value):
		if fileExists("/proc/stb/fb/sd_detach"):
			print('[Lcd] setfblcddisplay',value)
			open("/proc/stb/fb/sd_detach", "w").write(value)

	def setRepeat(self, value):
		if fileExists("/proc/stb/lcd/scroll_repeats"):
			print('[Lcd] setLCDRepeat',value)
			open("/proc/stb/lcd/scroll_repeats", "w").write(value)

	def setScrollspeed(self, value):
		if fileExists("/proc/stb/lcd/scroll_delay"):
			print('[Lcd] setLCDScrollspeed',value)
			open("/proc/stb/lcd/scroll_delay", "w").write(value)

	def setLEDNormalState(self, value):
		eDBoxLCD.getInstance().setLED(value, 0)

	def setLEDDeepStandbyState(self, value):
		eDBoxLCD.getInstance().setLED(value, 1)

	def setLEDBlinkingTime(self, value):
		eDBoxLCD.getInstance().setLED(value, 2)

	def setLCDMiniTVMode(self, value):
		if fileExists("/proc/stb/lcd/mode"):
			print('[Lcd] setLCDMiniTVMode',value)
			open("/proc/stb/lcd/mode", "w").write(value)

	def setLCDMiniTVPIPMode(self, value):
		print('[Lcd] setLCDMiniTVPIPMode',value)

	def setLCDMiniTVFPS(self, value):
		if fileExists("/proc/stb/lcd/fps"):
			print('[Lcd] setLCDMiniTVFPS',value)
			open("/proc/stb/lcd/fps", "w").write(value)

def leaveStandby():
	config.lcd.bright.apply()
	if SystemInfo["LEDButtons"]:
		config.lcd.ledbrightness.apply()
		config.lcd.ledbrightnessdeepstandby.apply()

def standbyCounterChanged(configElement):
	Screens.Standby.inStandby.onClose.append(leaveStandby)
	config.lcd.standby.apply()
	config.lcd.ledbrightnessstandby.apply()
	config.lcd.ledbrightnessdeepstandby.apply()

def InitLcd():
	if SystemInfo["FirstCheckModel"] or getBoxType() in ("force4","viperslim","lunix4k","vipert2c","evoslimse","evoslimt2c","tmtwin4k","evoslim","ultrabox","i55","dm520","hd11","sf98","et7000mini","xpeedc","beyonwizt2","gb800se","gb800solo","gb800seplus","gbultrase","gbipbox","tmsingle","tmnano2super","iqonios300hd","iqonios300hdv2","optimussos1plus","optimussos1","vusolo","et4x00","et5x00","et6x00","et7x00","ebox7358","eboxlumi","gbx1","gbx2","gbx3","gbx34k","gbx3h"):
		detected = False
	else:
		detected = eDBoxLCD.getInstance().detected()
	SystemInfo["Display"] = detected
	config.lcd = ConfigSubsection();

	if fileExists("/proc/stb/lcd/mode"):
		can_lcdmodechecking = open("/proc/stb/lcd/mode", "r").read()
	else:
		can_lcdmodechecking = False
	SystemInfo["LCDMiniTV"] = can_lcdmodechecking

	if detected:
		ilcd = LCD()
		if can_lcdmodechecking:
			def setLCDModeMinitTV(configElement):
				try:
					print('[Lcd] setLCDModeMinitTV',configElement.value)
					open("/proc/stb/lcd/mode", "w").write(configElement.value)
				except:
					pass
			def setMiniTVFPS(configElement):
				try:
					print('[Lcd] setMiniTVFPS',configElement.value)
					open("/proc/stb/lcd/fps", "w").write(configElement.value)
				except:
					pass
			def setLCDModePiP(configElement):
				pass
			def setLCDScreenshot(configElement):
				ilcd.setScreenShot(configElement.value)

			config.lcd.modepip = ConfigSelection(choices={
					"0": _("off"),
					"5": _("PIP"),
					"7": _("PIP with OSD")},
					default = "0")
			if SystemInfo["GigaBlueQuad"]:
				config.lcd.modepip.addNotifier(setLCDModePiP)
			else:
				config.lcd.modepip = ConfigNothing()
			config.lcd.screenshot = ConfigYesNo(default=False)
			config.lcd.screenshot.addNotifier(setLCDScreenshot)

			config.lcd.modeminitv = ConfigSelection(choices={
					"0": _("normal"),
					"1": _("MiniTV"),
					"2": _("OSD"),
					"3": _("MiniTV with OSD")},
					default = "0")
			config.lcd.fpsminitv = ConfigSlider(default=30, limits=(0, 30))
			config.lcd.modeminitv.addNotifier(setLCDModeMinitTV)
			config.lcd.fpsminitv.addNotifier(setMiniTVFPS)
		else:
			config.lcd.modeminitv = ConfigNothing()
			config.lcd.screenshot = ConfigNothing()
			config.lcd.fpsminitv = ConfigNothing()

		config.lcd.scroll_speed = ConfigSelection(default = "300", choices = [
			("500", _("slow")),
			("300", _("normal")),
			("100", _("fast"))])
		config.lcd.scroll_delay = ConfigSelection(default = "10000", choices = [
			("10000", "10 " + _("seconds")),
			("20000", "20 " + _("seconds")),
			("30000", "30 " + _("seconds")),
			("60000", "1 " + _("minute")),
			("300000", "5 " + _("minutes")),
			("noscrolling", _("off"))])

		def setLCDbright(configElement):
			ilcd.setBright(configElement.value);

		def setLCDstandbybright(configElement):
			ilcd.setStandbyBright(configElement.value);

		def setLCDdimbright(configElement):
			ilcd.setDimBright(configElement.value);

		def setLCDdimdelay(configElement):
			ilcd.setDimDelay(configElement.value);

		def setLCDcontrast(configElement):
			ilcd.setContrast(configElement.value);

		def setLCDinverted(configElement):
			ilcd.setInverted(configElement.value);

		def setLCDflipped(configElement):
			ilcd.setFlipped(configElement.value);

		def setLCDmode(configElement):
			ilcd.setMode(configElement.value);

		def setLCDpower(configElement):
			ilcd.setPower(configElement.value);

		def setfblcddisplay(configElement):
			ilcd.setfblcddisplay(configElement.value);

		def setLCDshowoutputresolution(configElement):
			ilcd.setShowoutputresolution(configElement.value);

		def setLCDminitvmode(configElement):
			ilcd.setLCDMiniTVMode(configElement.value)

		def setLCDminitvpipmode(configElement):
			ilcd.setLCDMiniTVPIPMode(configElement.value)

		def setLCDminitvfps(configElement):
			ilcd.setLCDMiniTVFPS(configElement.value)

		def setLEDnormalstate(configElement):
			ilcd.setLEDNormalState(configElement.value);

		def setLEDdeepstandby(configElement):
			ilcd.setLEDDeepStandbyState(configElement.value);

		def setLEDblinkingtime(configElement):
			ilcd.setLEDBlinkingTime(configElement.value);

		def setPowerLEDstate(configElement):
			if fileExists("/proc/stb/power/powerled"):
				open("/proc/stb/power/powerled", "w").write(configElement.value)

		def setPowerLEDstate2(configElement):
			if fileExists("/proc/stb/power/powerled2"):
				open("/proc/stb/power/powerled2", "w").write(configElement.value)

		def setPowerLEDstanbystate(configElement):
			if fileExists("/proc/stb/power/standbyled"):
				open("/proc/stb/power/standbyled", "w").write(configElement.value)

		def setPowerLEDdeepstanbystate(configElement):
			if fileExists("/proc/stb/power/suspendled"):
				open("/proc/stb/power/suspendled", "w").write(configElement.value)

		def setLedPowerColor(configElement):
			if fileExists("/proc/stb/fp/ledpowercolor"):
				open("/proc/stb/fp/ledpowercolor", "w").write(configElement.value)

		def setLedStandbyColor(configElement):
			if fileExists("/proc/stb/fp/ledstandbycolor"):
				open("/proc/stb/fp/ledstandbycolor", "w").write(configElement.value)

		def setLedSuspendColor(configElement):
			if fileExists("/proc/stb/fp/ledsuspendledcolor"):
				open("/proc/stb/fp/ledsuspendledcolor", "w").write(configElement.value)

		def setPower4x7On(configElement):
			if fileExists("/proc/stb/fp/power4x7on"):
				open("/proc/stb/fp/power4x7on", "w").write(configElement.value)

		def setPower4x7Standby(configElement):
			if fileExists("/proc/stb/fp/power4x7standby"):
				open("/proc/stb/fp/power4x7standby", "w").write(configElement.value)

		def setPower4x7Suspend(configElement):
			if fileExists("/proc/stb/fp/power4x7suspend"):
				open("/proc/stb/fp/power4x7suspend", "w").write(configElement.value)

		def setXcoreVFD(configElement):
			if fileExists("/sys/module/brcmstb_osmega/parameters/pt6302_cgram"):
				open("/sys/module/brcmstb_osmega/parameters/pt6302_cgram", "w").write(configElement.value)
			if fileExists("/sys/module/brcmstb_spycat4k/parameters/pt6302_cgram"):
				open("/sys/module/brcmstb_spycat4k/parameters/pt6302_cgram", "w").write(configElement.value)
			if fileExists("/sys/module/brcmstb_spycat4kmini/parameters/pt6302_cgram"):
				open("/sys/module/brcmstb_spycat4kmini/parameters/pt6302_cgram", "w").write(configElement.value)
			if fileExists("/sys/module/brcmstb_spycat4kcombo/parameters/pt6302_cgram"):
				open("/sys/module/brcmstb_spycat4kcombo/parameters/pt6302_cgram", "w").write(configElement.value)

		config.usage.vfd_xcorevfd = ConfigSelection(default = "0", choices = [("0", _("12 character")), ("1", _("8 character"))])
		config.usage.vfd_xcorevfd.addNotifier(setXcoreVFD)

		config.usage.lcd_powerled = ConfigSelection(default = "on", choices = [("off", _("Off")), ("on", _("On"))])
		config.usage.lcd_powerled.addNotifier(setPowerLEDstate)

		config.usage.lcd_powerled2 = ConfigSelection(default = "on", choices = [("off", _("Off")), ("on", _("On"))])
		config.usage.lcd_powerled2.addNotifier(setPowerLEDstate2)

		config.usage.lcd_standbypowerled = ConfigSelection(default = "on", choices = [("off", _("Off")), ("on", _("On"))])
		config.usage.lcd_standbypowerled.addNotifier(setPowerLEDstanbystate)

		config.usage.lcd_deepstandbypowerled = ConfigSelection(default = "on", choices = [("off", _("Off")), ("on", _("On"))])
		config.usage.lcd_deepstandbypowerled.addNotifier(setPowerLEDdeepstanbystate)

		config.usage.lcd_ledpowercolor = ConfigSelection(default = "1", choices = [("0", _("off")),("1", _("blue")), ("2", _("red")), ("3", _("violet"))])
		config.usage.lcd_ledpowercolor.addNotifier(setLedPowerColor)

		config.usage.lcd_ledstandbycolor = ConfigSelection(default = "3", choices = [("0", _("off")),("1", _("blue")), ("2", _("red")), ("3", _("violet"))])
		config.usage.lcd_ledstandbycolor.addNotifier(setLedStandbyColor)

		config.usage.lcd_ledsuspendcolor = ConfigSelection(default = "2", choices = [("0", _("off")),("1", _("blue")), ("2", _("red")), ("3", _("violet"))])
		config.usage.lcd_ledsuspendcolor.addNotifier(setLedSuspendColor)

		config.usage.lcd_power4x7on = ConfigSelection(default = "on", choices = [("off", _("Off")), ("on", _("On"))])
		config.usage.lcd_power4x7on.addNotifier(setPower4x7On)

		config.usage.lcd_power4x7standby = ConfigSelection(default = "on", choices = [("off", _("Off")), ("on", _("On"))])
		config.usage.lcd_power4x7standby.addNotifier(setPower4x7Standby)

		config.usage.lcd_power4x7suspend = ConfigSelection(default = "on", choices = [("off", _("Off")), ("on", _("On"))])
		config.usage.lcd_power4x7suspend.addNotifier(setPower4x7Suspend)

		if getBoxType() in ("dm900","dm920","e4hdultra","protek4k"):
			standby_default = 4
		elif SystemInfo["DifferentLCDSettings"]:
			standby_default = 10
		else:
			standby_default = 1

		if not ilcd.isOled():
			config.lcd.contrast = ConfigSlider(default=5, limits=(0, 20))
			config.lcd.contrast.addNotifier(setLCDcontrast);
		else:
			config.lcd.contrast = ConfigNothing()

		if getBoxType() in ("h3","ebox5000","ebox5100","sh1","spycat"):
			config.lcd.standby = ConfigSlider(default=standby_default, limits=(0, 4))
			config.lcd.dimbright = ConfigSlider(default=standby_default, limits=(0, 4))
			config.lcd.bright = ConfigSlider(default=4, limits=(0, 4))
		elif SystemInfo["DifferentLCDSettings"]:
			config.lcd.standby = ConfigSlider(default=standby_default, limits=(0, 10))
			config.lcd.dimbright = ConfigSlider(default=standby_default, limits=(0, 10))
			config.lcd.bright = ConfigSlider(default=10, limits=(0, 10))
		else:
			config.lcd.standby = ConfigSlider(default=standby_default, limits=(0, 10))
			config.lcd.dimbright = ConfigSlider(default=standby_default, limits=(0, 10))
			config.lcd.bright = ConfigSlider(default=SystemInfo["DefaultDisplayBrightness"], limits=(0, 10))
		config.lcd.dimbright.addNotifier(setLCDdimbright);
		config.lcd.dimbright.apply = lambda : setLCDdimbright(config.lcd.dimbright)
		config.lcd.dimdelay = ConfigSelection(default = "0", choices = [
			("5", "5 " + _("seconds")),
			("10", "10 " + _("seconds")),
			("15", "15 " + _("seconds")),
			("20", "20 " + _("seconds")),
			("30", "30 " + _("seconds")),
			("60", "1 " + _("minute")),
			("120", "2 " + _("minutes")),
			("300", "5 " + _("minutes")),
			("0", _("off"))])
		config.lcd.dimdelay.addNotifier(setLCDdimdelay);
		config.lcd.standby.addNotifier(setLCDstandbybright);
		config.lcd.standby.apply = lambda : setLCDstandbybright(config.lcd.standby)
		config.lcd.bright.addNotifier(setLCDbright);
		config.lcd.bright.apply = lambda : setLCDbright(config.lcd.bright)
		config.lcd.bright.callNotifiersOnSaveAndCancel = True

		config.lcd.invert = ConfigYesNo(default=False)
		config.lcd.invert.addNotifier(setLCDinverted);

		def PiconPackChanged(configElement):
			configElement.save()
		config.lcd.picon_pack = ConfigYesNo(default=False)
		config.lcd.picon_pack.addNotifier(PiconPackChanged)

		config.lcd.flip = ConfigYesNo(default=False)
		config.lcd.flip.addNotifier(setLCDflipped)

		if SystemInfo["LcdLiveTV"]:
			def lcdLiveTvChanged(configElement):
				if "live_enable" in SystemInfo["LcdLiveTV"]:
					open(SystemInfo["LcdLiveTV"], "w").write(configElement.value and "enable" or "disable")
				else:
					open(SystemInfo["LcdLiveTV"], "w").write(configElement.value and "0" or "1")
				try:
					InfoBarInstance = InfoBar.instance
					InfoBarInstance and InfoBarInstance.session.open(dummyScreen)
				except:
					pass
			config.lcd.showTv = ConfigYesNo(default = False)
			config.lcd.showTv.addNotifier(lcdLiveTvChanged)

		if SystemInfo["LCDMiniTV"] and not SystemInfo["GigaBlueQuad"] and not SystemInfo["GigaBlueAudio"]:
			config.lcd.minitvmode = ConfigSelection([("0", _("normal")), ("1", _("MiniTV")), ("2", _("OSD")), ("3", _("MiniTV with OSD"))], "0")
			config.lcd.minitvmode.addNotifier(setLCDminitvmode)
			config.lcd.minitvpipmode = ConfigSelection([("0", _("off")), ("5", _("PIP")), ("7", _("PIP with OSD"))], "0")
			config.lcd.minitvpipmode.addNotifier(setLCDminitvpipmode)
			config.lcd.minitvfps = ConfigSlider(default=30, limits=(0, 30))
			config.lcd.minitvfps.addNotifier(setLCDminitvfps)

		if SystemInfo["VFD_scroll_repeats"] and SystemInfo["VFDRepeats"]:
			def scroll_repeats(el):
				open(SystemInfo["VFD_scroll_repeats"], "w").write(el.value)
			choicelist = [("0", _("None")), ("1", _("1X")), ("2", _("2X")), ("3", _("3X")), ("4", _("4X")), ("500", _("Continues"))]
			config.usage.vfd_scroll_repeats = ConfigSelection(default = "3", choices = choicelist)
			config.usage.vfd_scroll_repeats.addNotifier(scroll_repeats, immediate_feedback = False)
		else:
			config.usage.vfd_scroll_repeats = ConfigNothing()

		if SystemInfo["VFD_scroll_delay"] and SystemInfo["VFDRepeats"]:
			def scroll_delay(el):
				# add workaround for Boxes who need hex code
				if SystemInfo["VFDDelay"]:
					open(SystemInfo["VFD_scroll_delay"], "w").write(hex(int(el.value)))
				else:
					open(SystemInfo["VFD_scroll_delay"], "w").write(str(el.value))
			config.usage.vfd_scroll_delay = ConfigSlider(default = 150, increment = 10, limits = (0, 500))
			config.usage.vfd_scroll_delay.addNotifier(scroll_delay, immediate_feedback = False)
			config.lcd.hdd = ConfigSelection([("0", _("No")), ("1", _("Yes"))], "1")
		else:
			config.lcd.hdd = ConfigNothing()
			config.usage.vfd_scroll_delay = ConfigNothing()

		if SystemInfo["VFD_initial_scroll_delay"] and SystemInfo["VFDRepeats"]:
			def initial_scroll_delay(el):
				if SystemInfo["VFDDelay"]:
					# add workaround for Boxes who need hex code
					open(SystemInfo["VFD_initial_scroll_delay"], "w").write(hex(int(el.value)))
				else:
					open(SystemInfo["VFD_initial_scroll_delay"], "w").write(el.value)

			choicelist = [
			("3000", "3 " + _("seconds")),
			("5000", "5 " + _("seconds")),
			("10000", "10 " + _("seconds")),
			("20000", "20 " + _("seconds")),
			("30000", "30 " + _("seconds")),
			("0", _("no delay"))]
			config.usage.vfd_initial_scroll_delay = ConfigSelection(default = "10000", choices = choicelist)
			config.usage.vfd_initial_scroll_delay.addNotifier(initial_scroll_delay, immediate_feedback = False)
		else:
			config.usage.vfd_initial_scroll_delay = ConfigNothing()

		if SystemInfo["VFD_final_scroll_delay"] and SystemInfo["VFDRepeats"]:
			def final_scroll_delay(el):
				if SystemInfo["VFDDelay"]:
					# add workaround for Boxes who need hex code
					open(SystemInfo["VFD_final_scroll_delay"], "w").write(hex(int(el.value)))
				else:
					open(SystemInfo["VFD_final_scroll_delay"], "w").write(el.value)

			choicelist = [
			("3000", "3 " + _("seconds")),
			("5000", "5 " + _("seconds")),
			("10000", "10 " + _("seconds")),
			("20000", "20 " + _("seconds")),
			("30000", "30 " + _("seconds")),
			("0", _("no delay"))]
			config.usage.vfd_final_scroll_delay = ConfigSelection(default = "10000", choices = choicelist)
			config.usage.vfd_final_scroll_delay.addNotifier(final_scroll_delay, immediate_feedback = False)
		else:
			config.usage.vfd_final_scroll_delay = ConfigNothing()

		if fileExists("/proc/stb/lcd/show_symbols"):
			config.lcd.mode = ConfigSelection([("0", _("No")), ("1", _("Yes"))], "1")
			config.lcd.mode.addNotifier(setLCDmode);
		else:
			config.lcd.mode = ConfigNothing()

		if fileExists("/proc/stb/power/vfd") or fileExists("/proc/stb/lcd/vfd"):
			config.lcd.power = ConfigSelection([("0", _("No")), ("1", _("Yes"))], "1")
			config.lcd.power.addNotifier(setLCDpower);
		else:
			config.lcd.power = ConfigNothing()

		if fileExists("/proc/stb/fb/sd_detach"):
			config.lcd.fblcddisplay = ConfigSelection([("1", _("No")), ("0", _("Yes"))], "1")
			config.lcd.fblcddisplay.addNotifier(setfblcddisplay);
		else:
			config.lcd.fblcddisplay = ConfigNothing()

		if fileExists("/proc/stb/lcd/show_outputresolution"):
			config.lcd.showoutputresolution = ConfigSelection([("0", _("No")), ("1", _("Yes"))], "1")
			config.lcd.showoutputresolution.addNotifier(setLCDshowoutputresolution);
		else:
			config.lcd.showoutputresolution = ConfigNothing()

		if getBoxType() == "vuultimo":
			config.lcd.ledblinkingtime = ConfigSlider(default = 5, increment = 1, limits = (0,15))
			config.lcd.ledblinkingtime.addNotifier(setLEDblinkingtime);
			config.lcd.ledbrightnessdeepstandby = ConfigSlider(default = 1, increment = 1, limits = (0,15))
			config.lcd.ledbrightnessdeepstandby.addNotifier(setLEDnormalstate);
			config.lcd.ledbrightnessdeepstandby.addNotifier(setLEDdeepstandby);
			config.lcd.ledbrightnessdeepstandby.apply = lambda : setLEDdeepstandby(config.lcd.ledbrightnessdeepstandby)
			config.lcd.ledbrightnessstandby = ConfigSlider(default = 1, increment = 1, limits = (0,15))
			config.lcd.ledbrightnessstandby.addNotifier(setLEDnormalstate);
			config.lcd.ledbrightnessstandby.apply = lambda : setLEDnormalstate(config.lcd.ledbrightnessstandby)
			config.lcd.ledbrightness = ConfigSlider(default = 3, increment = 1, limits = (0,15))
			config.lcd.ledbrightness.addNotifier(setLEDnormalstate);
			config.lcd.ledbrightness.apply = lambda : setLEDnormalstate(config.lcd.ledbrightness)
			config.lcd.ledbrightness.callNotifiersOnSaveAndCancel = True
		else:
			def doNothing():
				pass
			config.lcd.ledbrightness = ConfigNothing()
			config.lcd.ledbrightness.apply = lambda : doNothing()
			config.lcd.ledbrightnessstandby = ConfigNothing()
			config.lcd.ledbrightnessstandby.apply = lambda : doNothing()
			config.lcd.ledbrightnessdeepstandby = ConfigNothing()
			config.lcd.ledbrightnessdeepstandby.apply = lambda : doNothing()
			config.lcd.ledblinkingtime = ConfigNothing()
	else:
		def doNothing():
			pass
		config.lcd.contrast = ConfigNothing()
		config.lcd.bright = ConfigNothing()
		config.lcd.standby = ConfigNothing()
		config.lcd.bright.apply = lambda : doNothing()
		config.lcd.standby.apply = lambda : doNothing()
		config.lcd.power = ConfigNothing()
		config.lcd.fblcddisplay = ConfigNothing()
		config.lcd.mode = ConfigNothing()
		config.lcd.hdd = ConfigNothing()
		config.lcd.scroll_speed = ConfigSelection(default = "300", choices = [
		("500", _("slow")),
		("300", _("normal")),
		("100", _("fast"))])
		config.lcd.scroll_delay = ConfigSelection(default = "10000", choices = [
		("10000", "10 " + _("seconds")),
		("20000", "20 " + _("seconds")),
		("30000", "30 " + _("seconds")),
		("60000", "1 " + _("minute")),
		("300000", "5 " + _("minutes")),
		("noscrolling", _("off"))])
		config.lcd.showoutputresolution = ConfigNothing()
		config.lcd.ledbrightness = ConfigNothing()
		config.lcd.ledbrightness.apply = lambda : doNothing()
		config.lcd.ledbrightnessstandby = ConfigNothing()
		config.lcd.ledbrightnessstandby.apply = lambda : doNothing()
		config.lcd.ledbrightnessdeepstandby = ConfigNothing()
		config.lcd.ledbrightnessdeepstandby.apply = lambda : doNothing()
		config.lcd.ledblinkingtime = ConfigNothing()
		config.lcd.picon_pack = ConfigNothing()

	config.misc.standbyCounter.addNotifier(standbyCounterChanged, initial_call = False)
