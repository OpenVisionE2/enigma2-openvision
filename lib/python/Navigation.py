#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
from enigma import eServiceCenter, eServiceReference, pNavigation, getBestPlayableServiceReference, iPlayableService, setPreferredTuner, eStreamServer, iRecordableServicePtr, eDVBLocalTimeHandler, eTimer
from Components.ImportChannels import ImportChannels
from Components.ParentalControl import parentalControl
from Components.SystemInfo import BoxInfo
from Components.config import config, configfile
from Tools.BoundFunction import boundFunction
from Tools.StbHardware import getFPWasTimerWakeup
from Tools.Alternatives import ResolveCiAlternative
from Tools.Notifications import AddNotification
from time import time
import PowerTimer
import RecordTimer
import Screens.Standby
import NavigationInstance
from ServiceReference import ServiceReference, isPlayableForCur
from Screens.InfoBar import InfoBar
from Components.Sources.StreamService import StreamServiceList
from os import path

# TODO: remove pNavgation, eNavigation and rewrite this stuff in python.


class Navigation:
	def __init__(self, nextRecordTimerAfterEventActionAuto=False, nextPowerManagerAfterEventActionAuto=False):
		if NavigationInstance.instance is not None:
			raise NavigationInstance.instance

		NavigationInstance.instance = self
		self.ServiceHandler = eServiceCenter.getInstance()

		import Navigation as Nav
		Nav.navcore = self

		self.pnav = pNavigation()
		self.pnav.m_event.get().append(self.dispatchEvent)
		self.pnav.m_record_event.get().append(self.dispatchRecordEvent)
		self.event = []
		self.record_event = []
		self.currentlyPlayingServiceReference = None
		self.currentlyPlayingServiceOrGroup = None
		self.currentlyPlayingService = None
		self.RecordTimer = RecordTimer.RecordTimer()
		self.PowerTimer = PowerTimer.PowerTimer()
		self.__wasTimerWakeup = False
		self.__nextRecordTimerAfterEventActionAuto = nextRecordTimerAfterEventActionAuto
		self.__nextPowerManagerAfterEventActionAuto = nextPowerManagerAfterEventActionAuto
		if getFPWasTimerWakeup():
			self.__wasTimerWakeup = True
			self._processTimerWakeup()

		self.__isRestartUI = config.misc.RestartUI.value
		startup_to_standby = config.usage.startup_to_standby.value
		from Screens.SleepTimerEdit import isNextWakeupTime
		if isNextWakeupTime():
			wakeup_time_type = config.usage.wakeup_enabled.value
		wakeup_timer_enabled = False
		if config.usage.remote_fallback_import_restart.value:
			ImportChannels()
		if self.__wasTimerWakeup:
			wakeup_timer_enabled = wakeup_time_type == 3
			if not wakeup_timer_enabled:
				RecordTimer.RecordTimerEntry.setWasInDeepStandby()
		if config.misc.RestartUI.value:
			config.misc.RestartUI.value = False
			config.misc.RestartUI.save()
			configfile.save()
		else:
			if config.usage.remote_fallback_import.value and not config.usage.remote_fallback_import_restart.value:
				ImportChannels()
			if startup_to_standby == "yes" or self.__wasTimerWakeup and (wakeup_time_type == 0 or wakeup_time_type == 1 or (wakeup_time_type == 3 and startup_to_standby == "except")):
				if not Screens.Standby.inTryQuitMainloop:
					AddNotification(Screens.Standby.Standby, wakeup_timer_enabled and 1 or True)
		if config.usage.wakeup_enabled.value:
			configfile.save()

	def _processTimerWakeup(self):
		now = time()
		timeHandlerCallbacks = eDVBLocalTimeHandler.getInstance().m_timeUpdated.get()
		if self.__nextRecordTimerAfterEventActionAuto and now < eDVBLocalTimeHandler.timeOK:
			print('[Navigation] RECTIMER: wakeup to standby but system time not set.')
			if self._processTimerWakeup not in timeHandlerCallbacks:
				timeHandlerCallbacks.append(self._processTimerWakeup)
			return
		if self._processTimerWakeup in timeHandlerCallbacks:
			timeHandlerCallbacks.remove(self._processTimerWakeup)

		if self.__nextRecordTimerAfterEventActionAuto and abs(self.RecordTimer.getNextRecordingTime() - now) <= 360:
			print('[Navigation] RECTIMER: wakeup to standby detected.')
			open("/tmp/was_rectimer_wakeup", "w").write("1")
			# as we woke the box to record, place the box in standby.
			self.standbytimer = eTimer()
			self.standbytimer.callback.append(self.gotostandby)
			self.standbytimer.start(15000, True)

		elif self.__nextPowerManagerAfterEventActionAuto:
			print('[Navigation] POWERTIMER: wakeup to standby detected.')
			open("/tmp/was_powertimer_wakeup", "w").write("1")
			# as a PowerTimer WakeToStandby was actiond to it.
			self.standbytimer = eTimer()
			self.standbytimer.callback.append(self.gotostandby)
			self.standbytimer.start(15000, True)

	def wasTimerWakeup(self):
		return self.__wasTimerWakeup

	def gotostandby(self):
		print('[Navigation] TIMER: now entering standby')
		Notifications.AddNotification(Screens.Standby.Standby)

	def isRestartUI(self):
		return self.__isRestartUI

	def dispatchEvent(self, i):
		for x in self.event:
			x(i)
		if i == iPlayableService.evEnd:
			self.currentlyPlayingServiceReference = None
			self.currentlyPlayingServiceOrGroup = None
			self.currentlyPlayingService = None

	def dispatchRecordEvent(self, rec_service, event):
#		print("[Navigation] record_event", rec_service, event)
		for x in self.record_event:
			x(rec_service, event)

	def playService(self, ref, checkParentalControl=True, forceRestart=False, adjust=True):
		session = None
		startPlayingServiceOrGroup = None
		count = isinstance(adjust, list) and len(adjust) or 0
		if count > 1 and adjust[0] == 0:
			session = adjust[1]
			if count == 3:
				startPlayingServiceOrGroup = adjust[2]
			adjust = adjust[0]
		oldref = self.currentlyPlayingServiceOrGroup
		if ref and oldref and ref == oldref and not forceRestart:
			print("[Navigation] ignore request to play already running service(1)")
			return 1
		print("[Navigation] playing", ref and ref.toString())
		if path.exists("/proc/stb/lcd/symbol_signal") and config.lcd.mode.value == '1':
			try:
				if '0:0:0:0:0:0:0:0:0' not in ref.toString():
					signal = 1
				else:
					signal = 0
				print("[Navigation] Write to /proc/stb/lcd/symbol_signal")
				open("/proc/stb/lcd/symbol_signal", "w").write(str(signal))
			except:
				print("[Navigation] Write to /proc/stb/lcd/symbol_signal")
				open("/proc/stb/lcd/symbol_signal", "w").write("0")
		elif path.exists("/proc/stb/lcd/symbol_signal") and config.lcd.mode.value == '0':
			print("[Navigation] Write to /proc/stb/lcd/symbol_signal")
			open("/proc/stb/lcd/symbol_signal", "w").write("0")
		if ref is None:
			self.stopService()
			return 0
		from Components.ServiceEventTracker import InfoBarCount
		InfoBarInstance = InfoBarCount == 1 and InfoBar.instance
		if not checkParentalControl or parentalControl.isServicePlayable(ref, boundFunction(self.playService, checkParentalControl=False, forceRestart=forceRestart, adjust=(count > 1 and [0, session] or adjust)), session=session):
			if ref.flags & eServiceReference.isGroup:
				oldref = self.currentlyPlayingServiceReference or eServiceReference()
				playref = getBestPlayableServiceReference(ref, oldref)
				if playref and config.misc.use_ci_assignment.value and not isPlayableForCur(playref):
					alternative_ci_ref = ResolveCiAlternative(ref, playref)
					if alternative_ci_ref:
						playref = alternative_ci_ref
				print("[Navigation] alternative ref: ", playref and playref.toString())
				if playref and oldref and playref == oldref and not forceRestart:
					print("[Navigation] ignore request to play already running service(2)")
					return 1
				if not playref:
					alternativeref = getBestPlayableServiceReference(ref, eServiceReference(), True)
					self.stopService()
					if alternativeref and self.pnav:
						self.currentlyPlayingServiceReference = alternativeref
						self.currentlyPlayingServiceOrGroup = ref
						if self.pnav.playService(alternativeref):
							print("[Navigation] Failed to start: ", alternativeref.toString())
							self.currentlyPlayingServiceReference = None
							self.currentlyPlayingServiceOrGroup = None
						else:
							print("[Navigation] alternative ref as simulate: ", alternativeref.toString())
					return 0
				elif checkParentalControl and not parentalControl.isServicePlayable(playref, boundFunction(self.playService, checkParentalControl=False, forceRestart=forceRestart, adjust=(count > 1 and [0, session, ref] or adjust)), session=session):
					if self.currentlyPlayingServiceOrGroup and InfoBarInstance and InfoBarInstance.servicelist.servicelist.setCurrent(self.currentlyPlayingServiceOrGroup, adjust):
						self.currentlyPlayingServiceOrGroup = InfoBarInstance.servicelist.servicelist.getCurrent()
					return 1
			else:
				playref = ref
			if self.pnav:
				self.pnav.stopService()
				self.currentlyPlayingServiceReference = playref
				self.currentlyPlayingServiceOrGroup = ref
				if startPlayingServiceOrGroup and startPlayingServiceOrGroup.flags & eServiceReference.isGroup and not ref.flags & eServiceReference.isGroup:
					self.currentlyPlayingServiceOrGroup = startPlayingServiceOrGroup
				if InfoBarInstance and InfoBarInstance.servicelist.servicelist.setCurrent(ref, adjust):
					self.currentlyPlayingServiceOrGroup = InfoBarInstance.servicelist.servicelist.getCurrent()
				setPriorityFrontend = False
				if BoxInfo.getItem("DVB-T_priority_tuner_available") or BoxInfo.getItem("DVB-C_priority_tuner_available") or BoxInfo.getItem("DVB-S_priority_tuner_available") or BoxInfo.getItem("ATSC_priority_tuner_available"):
					str_service = playref.toString()
					if '%3a//' not in str_service and not str_service.rsplit(":", 1)[1].startswith("/"):
						type_service = playref.getUnsignedData(4) >> 16
						if type_service == 0xEEEE:
							if BoxInfo.getItem("DVB-T_priority_tuner_available") and config.usage.frontend_priority_dvbt.value != "-2":
								if config.usage.frontend_priority_dvbt.value != config.usage.frontend_priority.value:
									setPreferredTuner(int(config.usage.frontend_priority_dvbt.value))
									setPriorityFrontend = True
							if BoxInfo.getItem("ATSC_priority_tuner_available") and config.usage.frontend_priority_atsc.value != "-2":
								if config.usage.frontend_priority_atsc.value != config.usage.frontend_priority.value:
									setPreferredTuner(int(config.usage.frontend_priority_atsc.value))
									setPriorityFrontend = True
						elif type_service == 0xFFFF:
							if BoxInfo.getItem("DVB-C_priority_tuner_available") and config.usage.frontend_priority_dvbc.value != "-2":
								if config.usage.frontend_priority_dvbc.value != config.usage.frontend_priority.value:
									setPreferredTuner(int(config.usage.frontend_priority_dvbc.value))
									setPriorityFrontend = True
							if BoxInfo.getItem("ATSC_priority_tuner_available") and config.usage.frontend_priority_atsc.value != "-2":
								if config.usage.frontend_priority_atsc.value != config.usage.frontend_priority.value:
									setPreferredTuner(int(config.usage.frontend_priority_atsc.value))
									setPriorityFrontend = True
						else:
							if BoxInfo.getItem("DVB-S_priority_tuner_available") and config.usage.frontend_priority_dvbs.value != "-2":
								if config.usage.frontend_priority_dvbs.value != config.usage.frontend_priority.value:
									setPreferredTuner(int(config.usage.frontend_priority_dvbs.value))
									setPriorityFrontend = True
				if self.pnav.playService(playref):
					print("[Navigation] Failed to start: ", playref.toString())
					self.currentlyPlayingServiceReference = None
					self.currentlyPlayingServiceOrGroup = None
				if setPriorityFrontend:
					setPreferredTuner(int(config.usage.frontend_priority.value))
				return 0
		elif oldref and InfoBarInstance and InfoBarInstance.servicelist.servicelist.setCurrent(oldref, adjust):
			self.currentlyPlayingServiceOrGroup = InfoBarInstance.servicelist.servicelist.getCurrent()
		return 1

	def getCurrentlyPlayingServiceReference(self):
		return self.currentlyPlayingServiceReference

	def getCurrentlyPlayingServiceOrGroup(self):
		return self.currentlyPlayingServiceOrGroup

	def recordService(self, ref, simulate=False):
		service = None
		if not simulate:
			print("[Navigation] recording service:", (ref and ref.toString()))
		if isinstance(ref, ServiceReference):
			ref = ref.ref
		if ref:
			if ref.flags & eServiceReference.isGroup:
				ref = getBestPlayableServiceReference(ref, eServiceReference(), simulate)
			service = ref and self.pnav and self.pnav.recordService(ref, simulate)
			if service is None:
				print("[Navigation] record returned non-zero")
		return service

	def stopRecordService(self, service):
		ret = -1
		if service and isinstance(service, iRecordableServicePtr):
			ret = self.pnav and self.pnav.stopRecordService(service)
		return ret

	def getRecordings(self, simulate=False):
		recs = self.pnav and self.pnav.getRecordings(simulate)
		if not simulate and StreamServiceList:
			for rec in recs[:]:
				if rec.__deref__() in StreamServiceList:
					recs.remove(rec)
		return recs

	def getCurrentService(self):
		if not self.currentlyPlayingService:
			self.currentlyPlayingService = self.pnav and self.pnav.getCurrentService()
		return self.currentlyPlayingService

	def stopService(self):
		if self.pnav:
			self.pnav.stopService()
		self.currentlyPlayingServiceReference = None
		self.currentlyPlayingServiceOrGroup = None
		if path.exists("/proc/stb/lcd/symbol_signal"):
			print("[Navigation] Write to /proc/stb/lcd/symbol_signal")
			open("/proc/stb/lcd/symbol_signal", "w").write("0")

	def pause(self, p):
		return self.pnav and self.pnav.pause(p)

	def shutdown(self):
		self.RecordTimer.shutdown()
		self.PowerTimer.shutdown()
		self.ServiceHandler = None
		self.pnav = None

	def stopUserServices(self):
		self.stopService()

	def getClientsStreaming(self):
		return eStreamServer.getInstance() and eStreamServer.getInstance().getConnectedClients()
