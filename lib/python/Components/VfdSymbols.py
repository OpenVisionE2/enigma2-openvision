from twisted.internet import threads
from config import config
from enigma import eDBoxLCD, eTimer, iPlayableService, pNavigation, getBoxType
import NavigationInstance
from Tools.Directories import fileExists
from Components.ParentalControl import parentalControl
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import SystemInfo

POLLTIME = 5 # seconds

def SymbolsCheck(session, **kwargs):
		global symbolspoller, POLLTIME
		if getBoxType() in ("alien5","osninopro","osnino","osninoplus","tmtwin4k","mbmicrov2","revo4k","force3uhd","wetekplay","wetekplay2","wetekhub","ixussone","ixusszero","mbmicro","e4hd","e4hdhybrid","dm7020hd","dm7020hdv2","9910lx","9911lx","9920lx","valalinux","lunix","tmnanose","tmnanoseplus","tmnanosem2","tmnanom3","tmnanosem2plus","tmnanosecombo","force2plus","force2","force2se","optimussos","fusionhd","fusionhdse","purehd","force2nano","force2plushv","purehdse","ustym4kpro","beyonwizv2","sf8008","gbtrio4k","cc1"):
			POLLTIME = 1
		symbolspoller = SymbolsCheckPoller(session)
		symbolspoller.start()

class SymbolsCheckPoller:
	def __init__(self, session):
		self.session = session
		self.blink = False
		self.led = "0"
		self.timer = eTimer()
		self.onClose = []
		self.__event_tracker = ServiceEventTracker(screen=self,eventmap=
			{
				iPlayableService.evUpdatedInfo: self.__evUpdatedInfo,
			})

	def __onClose(self):
		pass

	def start(self):
		if self.symbolscheck not in self.timer.callback:
			self.timer.callback.append(self.symbolscheck)
		self.timer.startLongTimer(0)

	def stop(self):
		if self.symbolscheck in self.timer.callback:
			self.timer.callback.remove(self.symbolscheck)
		self.timer.stop()

	def symbolscheck(self):
		threads.deferToThread(self.JobTask)
		self.timer.startLongTimer(POLLTIME)

	def JobTask(self):
		self.Recording()
		self.PlaySymbol()
		self.timer.startLongTimer(POLLTIME)

	def __evUpdatedInfo(self):
		self.service = self.session.nav.getCurrentService()
		self.Subtitle()
		self.ParentalControl()
		self.PlaySymbol()
		del self.service

	def Recording(self):
		if fileExists("/proc/stb/lcd/symbol_circle"):
			recordings = len(NavigationInstance.instance.getRecordings())
			if recordings > 0:
				open("/proc/stb/lcd/symbol_circle", "w").write("3")
			else:
				open("/proc/stb/lcd/symbol_circle", "w").write("0")
		elif getBoxType() in ("alphatriplehd","ebox5000","ebox7358","eboxlumi","ebox5000","sf3038"):
			recordings = len(NavigationInstance.instance.getRecordings())
			if recordings > 0:
				open("/proc/stb/lcd/symbol_recording", "w").write("1")
			else:
				open("/proc/stb/lcd/symbol_recording", "w").write("0")
		elif getBoxType() in ("alien5","osninopro","wetekplay","wetekplay2","wetekhub","ixussone","ixusszero","9910lx","9911lx","osnino","osninoplus","9920lx"):
			recordings = len(NavigationInstance.instance.getRecordings())
			self.blink = not self.blink
			if recordings > 0:
				if self.blink:
					open("/proc/stb/lcd/powerled", "w").write("1")
					self.led = "1"
				else:
					open("/proc/stb/lcd/powerled", "w").write("0")
					self.led = "0"
			elif self.led == "1":
				open("/proc/stb/lcd/powerled", "w").write("0")
		elif getBoxType() in ("mbmicrov2","mbmicro","e4hd","e4hdhybrid"):
			recordings = len(NavigationInstance.instance.getRecordings())
			self.blink = not self.blink
			if recordings > 0:
				if self.blink:
					open("/proc/stb/lcd/powerled", "w").write("0")
					self.led = "1"
				else:
					open("/proc/stb/lcd/powerled", "w").write("1")
					self.led = "0"
			elif self.led == "1":
				open("/proc/stb/lcd/powerled", "w").write("1")
		elif getBoxType() in ("dm7020hd","dm7020hdv2"):
			recordings = len(NavigationInstance.instance.getRecordings())
			self.blink = not self.blink
			if recordings > 0:
				if self.blink:
					open("/proc/stb/fp/led_set", "w").write("0x00000000")
					self.led = "1"
				else:
					open("/proc/stb/fp/led_set", "w").write("0xffffffff")
					self.led = "0"
			else:
				open("/proc/stb/fp/led_set", "w").write("0xffffffff")
		elif getBoxType() in ("valalinux","lunix","tmnanose","tmnanoseplus","tmnanosem2","tmnanom3","tmnanosem2plus","tmnanosecombo","force2plus","force2","force2se","optimussos","fusionhd","fusionhdse","purehd","force2nano","force2plushv","purehdse","tmtwin4k","revo4k","force3uhd"):
			recordings = len(NavigationInstance.instance.getRecordings())
			self.blink = not self.blink
			if recordings > 0:
				if self.blink:
					open("/proc/stb/lcd/symbol_rec", "w").write("1")
					self.led = "1"
				else:
					open("/proc/stb/lcd/symbol_rec", "w").write("0")
					self.led = "0"
			elif self.led == "1":
				open("/proc/stb/lcd/symbol_rec", "w").write("0")
		elif SystemInfo["HiSilicon"]:
			import Screens.Standby
			recordings = len(NavigationInstance.instance.getRecordings())
			if recordings > 0:
				open("/proc/stb/fp/mixerled", "w").write("on")
			elif not Screens.Standby.inStandby:
				open("/proc/stb/fp/poweronled", "w").write("on")
			elif Screens.Standby.inStandby:
				open("/proc/stb/fp/standbyled", "w").write("on")

		else:
			if not fileExists("/proc/stb/lcd/symbol_recording") or not fileExists("/proc/stb/lcd/symbol_record_1") or not fileExists("/proc/stb/lcd/symbol_record_2"):
				return
	
			recordings = len(NavigationInstance.instance.getRecordings())
		
			if recordings > 0:
				open("/proc/stb/lcd/symbol_recording", "w").write("1")
				if recordings == 1:
					open("/proc/stb/lcd/symbol_record_1", "w").write("1")
					open("/proc/stb/lcd/symbol_record_2", "w").write("0")
				elif recordings >= 2:
					open("/proc/stb/lcd/symbol_record_1", "w").write("1")
					open("/proc/stb/lcd/symbol_record_2", "w").write("1")
			else:
				open("/proc/stb/lcd/symbol_recording", "w").write("0")
				open("/proc/stb/lcd/symbol_record_1", "w").write("0")
				open("/proc/stb/lcd/symbol_record_2", "w").write("0")


	def Subtitle(self):
		if not fileExists("/proc/stb/lcd/symbol_smartcard"):
			return

		subtitle = self.service and self.service.subtitle()
		subtitlelist = subtitle and subtitle.getSubtitleList()

		if subtitlelist:
			subtitles = len(subtitlelist)
			if subtitles > 0:
				open("/proc/stb/lcd/symbol_smartcard", "w").write("1")
			else:
				open("/proc/stb/lcd/symbol_smartcard", "w").write("0")
		else:
			open("/proc/stb/lcd/symbol_smartcard", "w").write("0")

	def ParentalControl(self):
		if not fileExists("/proc/stb/lcd/symbol_parent_rating"):
			return

		service = self.session.nav.getCurrentlyPlayingServiceReference()

		if service:
			if parentalControl.getProtectionLevel(service.toCompareString()) == -1:
				open("/proc/stb/lcd/symbol_parent_rating", "w").write("0")
			else:
				open("/proc/stb/lcd/symbol_parent_rating", "w").write("1")
		else:
			open("/proc/stb/lcd/symbol_parent_rating", "w").write("0")

	def PlaySymbol(self):
		if not fileExists("/proc/stb/lcd/symbol_play "):
			return

		open("/proc/stb/lcd/symbol_play ", "w").write("0")
