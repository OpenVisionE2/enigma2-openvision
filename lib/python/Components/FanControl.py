# -*- coding: utf-8 -*-
from os.path import isfile

from Components.config import config, ConfigSubList, ConfigSubsection, ConfigSlider
from Tools.BoundFunction import boundFunction

import NavigationInstance
from enigma import iRecordableService
from Components.SystemInfo import BoxInfo

model = BoxInfo.getItem("model")


class FanControl:
	# ATM there's only support for one fan
	def __init__(self):
		if isfile("/proc/stb/fp/fan_vlt") or isfile("/proc/stb/fp/fan_pwm") or isfile("/proc/stb/fp/fan_speed"):
			self.fancount = 1
		else:
			self.fancount = 0
		self.createConfig()
		config.misc.standbyCounter.addNotifier(self.standbyCounterChanged, initial_call=False)

	def setVoltage_PWM(self):
		for fanid in range(self.getFanCount()):
			cfg = self.getConfig(fanid)
			self.setVoltage(fanid, cfg.vlt.value)
			self.setPWM(fanid, cfg.pwm.value)
			print("[FanControl] setting fan values: fanid = %d, voltage = %d, pwm = %d" % (fanid, cfg.vlt.value, cfg.pwm.value))

	def setVoltage_PWM_Standby(self):
		for fanid in range(self.getFanCount()):
			cfg = self.getConfig(fanid)
			self.setVoltage(fanid, cfg.vlt_standby.value)
			self.setPWM(fanid, cfg.pwm_standby.value)
			print("[FanControl] setting fan values (standby mode): fanid = %d, voltage = %d, pwm = %d" % (fanid, cfg.vlt_standby.value, cfg.pwm_standby.value))

	def getRecordEvent(self, recservice, event):
		recordings = len(NavigationInstance.instance.getRecordings())
		if event == iRecordableService.evEnd:
			if recordings == 0:
				self.setVoltage_PWM_Standby()
		elif event == iRecordableService.evStart:
			if recordings == 1:
				self.setVoltage_PWM()

	def leaveStandby(self):
		NavigationInstance.instance.record_event.remove(self.getRecordEvent)
		recordings = NavigationInstance.instance.getRecordings()
		if not recordings:
			self.setVoltage_PWM()

	def standbyCounterChanged(self, configElement):
		from Screens.Standby import inStandby
		inStandby.onClose.append(self.leaveStandby)
		recordings = NavigationInstance.instance.getRecordings()
		NavigationInstance.instance.record_event.append(self.getRecordEvent)
		if not recordings:
			self.setVoltage_PWM_Standby()

	def createConfig(self):
		def setVlt(fancontrol, fanid, configElement):
			fancontrol.setVoltage(fanid, configElement.value)

		def setPWM(fancontrol, fanid, configElement):
			fancontrol.setPWM(fanid, configElement.value)

		config.fans = ConfigSubList()
		for fanid in range(self.getFanCount()):
			fan = ConfigSubsection()
			fan.vlt = ConfigSlider(default=15, increment=5, limits=(0, 255))
			if model == "tm2t":
				fan.pwm = ConfigSlider(default=150, increment=5, limits=(0, 255))
			elif model == "tmsingle":
				fan.pwm = ConfigSlider(default=100, increment=5, limits=(0, 255))
			elif model == "beyonwizu4":
				fan.pwm = ConfigSlider(default=0xcc, increment=0x11, limits=(0x22, 0xff))
			elif model == "beyonwizt4":
				fan.pwm = ConfigSlider(default=200, increment=5, limits=(0, 255))
			else:
				fan.pwm = ConfigSlider(default=50, increment=5, limits=(0, 255))
			fan.vlt_standby = ConfigSlider(default=5, increment=5, limits=(0, 255))
			if model == "beyonwizu4":
				fan.pwm_standby = ConfigSlider(default=0x44, increment=0x11, limits=(0x22, 0xff))
			elif model == "beyonwizt4":
				fan.pwm_standby = ConfigSlider(default=10, increment=5, limits=(0, 0xff))
			else:
				fan.pwm_standby = ConfigSlider(default=0, increment=5, limits=(0, 255))
			fan.vlt.addNotifier(boundFunction(setVlt, self, fanid))
			fan.pwm.addNotifier(boundFunction(setPWM, self, fanid))
			config.fans.append(fan)

	def getConfig(self, fanid):
		return config.fans[fanid]

	def getFanCount(self):
		return self.fancount

	def hasRPMSensor(self, fanid):
		return isfile("/proc/stb/fp/fan_speed")

	def hasFanControl(self, fanid):
		return isfile("/proc/stb/fp/fan_vlt") or isfile("/proc/stb/fp/fan_pwm")

	def getFanSpeed(self, fanid):
		try:
			return int(open("/proc/stb/fp/fan_speed", "r").readline().strip()[:-4])
		except:
			print("[FanControl] Read /proc/stb/fp/fan_speed failed!")

	def getVoltage(self, fanid):
		try:
			return int(open("/proc/stb/fp/fan_vlt", "r").readline().strip(), 16)
		except:
			print("[FanControl] Read /proc/stb/fp/fan_vlt failed!")

	def setVoltage(self, fanid, value):
		if model == "beyonwizu4":
			return
		if value > 255:
			return
		try:
			open("/proc/stb/fp/fan_vlt", "w").write("%x" % value)
		except:
			print("[FanControl] Write to /proc/stb/fp/fan_vlt failed!")

	def getPWM(self, fanid):
		try:
			return int(open("/proc/stb/fp/fan_pwm", "r").readline().strip(), 16)
		except:
			print("[FanControl] Read /proc/stb/fp/fan_pwm failed!")

	def setPWM(self, fanid, value):
		if value > 255:
			return
		try:
			open("/proc/stb/fp/fan_pwm", "w").write("%x" % value)
		except:
			print("[FanControl] Write to /proc/stb/fp/fan_pwm failed!")


fancontrol = FanControl()
