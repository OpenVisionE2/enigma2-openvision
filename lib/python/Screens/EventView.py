from six import PY2
from time import localtime, strftime

from enigma import eEPGCache, eTimer, eServiceReference

from RecordTimer import AFTEREVENT, RecordTimerEntry, createRecordTimerEntry, parseEvent
from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.Label import Label
from Components.PluginComponent import plugins
from Components.ScrollLabel import ScrollLabel
from Components.TimerList import TimerList
# from Components.UsageConfig import dropEPGNewLines, preferredTimerPath, replaceEPGSeparator
from Components.UsageConfig import preferredTimerPath
from Components.Sources.Event import Event
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.HelpMenu import HelpableScreen
from Screens.Screen import Screen
from Screens.TimerEdit import TimerSanityConflict
from Screens.TimerEntry import TimerEntry
from Tools.BoundFunction import boundFunction
from Tools.FallbackTimer import FallbackTimerList


def dropEPGNewLines(text):
	if config.epg.replace_newlines.value != "no":
		text = text.replace("\n", replaceEPGSeparator(config.epg.replace_newlines.value))
	return text


def replaceEPGSeparator(code):
	return {
		"newline": "\n",
		"2newlines": "\n\n",
		"space": " ",
		"dash": " - ",
		"dot": " . ",
		"asterisk": " * ",
		"hashtag": " # ",
		"nothing": ""
	}.get(code)


class EventViewBase:
	ADD_TIMER = 0
	REMOVE_TIMER = 1

	def __init__(self, event, serviceRef, callback=None, similarEPGCB=None, parent=None, windowTitle=None):
		self.event = event
		self.serviceRef = serviceRef
		self.callbackMethod = callback
		if similarEPGCB is None:
			self.similarBroadcastTimer = None
		else:
			self.similarBroadcastTimer = eTimer()
			self.similarBroadcastTimer.callback.append(self.getSimilarEvents)
		self.similarEPGCB = similarEPGCB
		if parent and hasattr(parent, "fallbackTimer"):
			self.fallbackTimer = parent.fallbackTimer
			self.onLayoutFinish.append(self.layoutFinished)
		else:
			self.fallbackTimer = FallbackTimerList(self, self.layoutFinished)
		self.windowTitle = windowTitle
		self.isRecording = (not serviceRef.ref.flags & eServiceReference.isGroup) and serviceRef.ref.getPath()
		self["channel"] = Label()
		self["datetime"] = Label()
		self["duration"] = Label()
		self["Service"] = ServiceEvent()
		self["Event"] = Event()
		self["epg_eventname"] = ScrollLabel()
		self["epg_description"] = ScrollLabel()
		self["FullDescription"] = ScrollLabel()
		self["key_red"] = StaticText("")
		self["key_green"] = StaticText("" if self.isRecording else _("Add Timer"))
		self.keyGreenAction = self.ADD_TIMER
		self["key_menu"] = StaticText(_("MENU"))
		self["key_info"] = StaticText(_("INFO"))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "EventViewActions"], {
			"cancel": (self.close, _("Close Event View screen")),
			"ok": (self.close, _("Close Event View screen")),
			"contextMenu": (self.doContext, _("Open context menu")),
			"timerAdd": (self.addTimer, _("Add a timer for the current event")),
			"pageUp": (self.pageUp, _("Show previous page of description")),
			"pageDown": (self.pageDown, _("Show next page of description"))
		}, prio=0, description=_("Event View Actions"))
		self["eventActions"] = HelpableActionMap(self, ["EventViewActions"], {
			"prevEvent": (self.prevEvent, _("Show previous event")),
			"nextEvent": (self.nextEvent, _("Show next event"))
		}, prio=0, description=_("Event View Actions"))
		self["eventActions"].setEnabled(callback is not None)
		self["similarActions"] = HelpableActionMap(self, ["EventViewActions"], {
			"openSimilarList": (self.openSimilarList, _("Find similar events in the EPG"))
		}, prio=0, description=_("Event View Actions"))
		self["similarActions"].setEnabled(False)

	def layoutFinished(self):
		self.setService(self.serviceRef)
		self.setEvent(self.event)

	def pageUp(self):
		self["epg_eventname"].pageUp()
		self["epg_description"].pageUp()
		self["FullDescription"].pageUp()

	def pageDown(self):
		self["epg_eventname"].pageDown()
		self["epg_description"].pageDown()
		self["FullDescription"].pageDown()

	def prevEvent(self):
		self.callbackMethod(self.setEvent, self.setService, -1)

	def nextEvent(self):
		self.callbackMethod(self.setEvent, self.setService, +1)

	def setService(self, service):
		self.serviceRef = service
		self["Service"].newService(service.ref)
		serviceName = service.getServiceName()
		self["channel"].setText("%s%s" % (serviceName if serviceName else _("Unknown Service"), " - %s" % _("Recording") if self.isRecording else ""))

	def setEvent(self, event):
		self.event = event
		self["Event"].newEvent(event)
		if event is None:
			return
		eventName = event.getEventName().strip()
		self.setTitle(eventName if self.windowTitle is None else self.windowTitle)
		self["epg_eventname"].setText(eventName)
		shortDescription = dropEPGNewLines(event.getShortDescription().strip())
		extentedDescription = dropEPGNewLines(event.getExtendedDescription().strip())
		description = [shortDescription, extentedDescription]
		if shortDescription == extentedDescription:
			del description[1]
		if eventName == shortDescription:
			del description[0]
		description = replaceEPGSeparator(config.epg.fulldescription_separator.value).join(description)
		self["epg_description"].setText(description)
		self["FullDescription"].setText(extentedDescription)
		begin = event.getBeginTime()
		beginTime = localtime(begin)
		duration = event.getDuration()
		endTime = localtime(begin + duration)
		self["datetime"].setText("%s - %s" % (strftime("%s, %s" % (config.usage.date.daylong.value, config.usage.time.short.value), beginTime), strftime(config.usage.time.short.value, endTime)))
		self["duration"].setText(_("%d min") % (duration // 60))
		self["key_red"].setText("")
		self["similarActions"].setEnabled(False)
		if self.similarBroadcastTimer:
			self.similarBroadcastTimer.start(25, True)
		self.setTimerState()

	def addTimer(self):
		if self.isRecording or self.event is None:
			return
		timer, isRecordEvent = self.doesTimerExist()
		if timer and isRecordEvent:
			menu = [
				(_("Delete Timer"), "delete"),
				(_("Edit Timer"), "edit")
			]
			buttons = ["red", "green"]

			def timerAction(choice):
				if choice is not None:
					if choice[1] == "delete":
						self.removeTimer(timer)
					elif choice[1] == "edit":
						self.session.openWithCallback(self.finishedEdit, TimerEntry, timer)

			text = [_("Select action for timer '%s'.") % timer.name]
			if timer.repeated:
				text.insert(0, _("Attention, this is a repeated timer!"))
			self.session.openWithCallback(timerAction, ChoiceBox, text="\n".join(text), list=menu, keys=buttons)
		else:
			newEntry = RecordTimerEntry(self.serviceRef, checkOldTimers=True, dirname=preferredTimerPath(), *parseEvent(self.event))
			newEntry.justplay = config.recording.timer_default_type.value == "zap"
			newEntry.always_zap = config.recording.timer_default_type.value == "zap+record"
			self.session.openWithCallback(self.finishedAdd, TimerEntry, newEntry)

	def finishedEdit(self, answer):
		if answer[0]:
			entry = answer[1]
			if entry.external_prev != entry.external:

				def removeEditTimer():
					entry.service_ref, entry.begin, entry.end, entry.external = entry.service_ref_prev, entry.begin_prev, entry.end_prev, entry.external_prev
					self.removeTimer(entry)

				def moveEditTimerError():
					entry.external = entry.external_prev
					self.onSelectionChanged()

				if entry.external:
					self.fallbackTimer.addTimer(entry, removeEditTimer, moveEditTimerError)
				else:
					newEntry = createRecordTimerEntry(entry)
					entry.service_ref, entry.begin, entry.end = entry.service_ref_prev, entry.begin_prev, entry.end_prev
					self.fallbackTimer.removeTimer(entry, boundFunction(self.finishedAdd, (True, newEntry)), moveEditTimerError)
			elif entry.external:
				self.fallbackTimer.editTimer(entry, self.setTimerState)
			else:
				simulTimerList = self.session.nav.RecordTimer.record(entry)
				if simulTimerList:
					for simulTimer in simulTimerList:
						if simulTimer.setAutoincreaseEnd(entry):
							self.session.nav.RecordTimer.timeChanged(simulTimer)
					simulTimerList = self.session.nav.RecordTimer.record(entry)
					if simulTimerList:
						self.session.openWithCallback(self.finishedEdit, TimerSanityConflict, simulTimerList)
						return
					else:
						self.session.nav.RecordTimer.timeChanged(entry)
				if answer is not None and len(answer) > 1:
					entry = answer[1]
					if not entry.disabled:
						self["key_green"].setText(_("Change Timer"))
						self.keyGreenAction = self.REMOVE_TIMER
					else:
						self["key_green"].setText(_("Add Timer"))
						self.keyGreenAction = self.ADD_TIMER

	def finishedAdd(self, answer):
		if answer[0]:
			entry = answer[1]
			if entry.external:
				self.fallbackTimer.addTimer(entry, self.setTimerState)
			else:
				simulTimerList = self.session.nav.RecordTimer.record(entry)
				if simulTimerList:
					for simulTimer in simulTimerList:
						if simulTimer.setAutoincreaseEnd(entry):
							self.session.nav.RecordTimer.timeChanged(simulTimer)
					simulTimerList = self.session.nav.RecordTimer.record(entry)
					if simulTimerList:
						if not entry.repeated and not config.recording.margin_before.value and not config.recording.margin_after.value and len(simulTimerList) > 1:
							changeTime = False
							conflictBegin = simulTimerList[1].begin
							conflictEnd = simulTimerList[1].end
							if conflictBegin == entry.end:
								entry.end -= 30
								changeTime = True
							elif entry.begin == conflictEnd:
								entry.begin += 30
								changeTime = True
							elif entry.begin == conflictBegin and (entry.service_ref and entry.service_ref.ref and entry.service_ref.ref.flags & eServiceReference.isGroup):
								entry.begin += 30
								changeTime = True
							if changeTime:
								simulTimerList = self.session.nav.RecordTimer.record(entry)
						if simulTimerList:
							self.session.openWithCallback(self.finishSanityCorrection, TimerSanityConflict, simulTimerList)
				self["key_green"].setText(_("Change Timer"))
				self.keyGreenAction = self.REMOVE_TIMER
		else:
			self["key_green"].setText(_("Add Timer"))
			self.keyGreenAction = self.ADD_TIMER

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def setTimerState(self):
		timer, isRecordEvent = self.doesTimerExist()
		if isRecordEvent and self.keyGreenAction != self.REMOVE_TIMER:
			self["key_green"].setText(_("Change Timer"))
			self.keyGreenAction = self.REMOVE_TIMER
		elif not isRecordEvent and self.keyGreenAction != self.ADD_TIMER:
			self["key_green"].setText(_("Add Timer"))
			self.keyGreenAction = self.ADD_TIMER

	def doesTimerExist(self):
		eventId = self.event.getEventId()
		begin = self.event.getBeginTime()
		end = begin + self.event.getDuration()
		refStr = ":".join(self.serviceRef.ref.toString().split(":")[:11])
		isRecordEvent = False
		for timer in self.session.nav.RecordTimer.getAllTimersList():
			neededRef = ":".join(timer.service_ref.ref.toString().split(":")[:11]) == refStr
			if neededRef and (timer.eit == eventId and (begin < timer.begin <= end or timer.begin <= begin <= timer.end) or timer.repeated and self.session.nav.RecordTimer.isInRepeatTimer(timer, self.event)):
				isRecordEvent = True
				break
		else:
			timer = None
		return timer, isRecordEvent

	def removeTimer(self, timer):
		if timer.external:
			self.fallbackTimer.removeTimer(timer, self.setTimerState)
		else:
			timer.afterEvent = AFTEREVENT.NONE
			self.session.nav.RecordTimer.removeEntry(timer)
			self["key_green"].setText(_("Add Timer"))
			self.keyGreenAction = self.ADD_TIMER

	def getSimilarEvents(self):
		if not self.event:
			return
		serviceRef = str(self.serviceRef)
		id = self.event.getEventId()
		epgcache = eEPGCache.getInstance()
		results = epgcache.search(("NB", 100, eEPGCache.SIMILAR_BROADCASTINGS_SEARCH, serviceRef, id))
		if results:
			similar = [_("Similar broadcasts:")]
			timeFormat = "%s, %s" % (config.usage.date.long.value, config.usage.time.short.value)
			for result in sorted(results, key=lambda x: x[1]):
				similar.append("%s  -  %s" % (strftime(timeFormat, localtime(result[1])), result[0]))
			self["epg_description"].setText("%s\n\n%s" % (self["epg_description"].getText(), "\n".join(similar)))
			self["FullDescription"].setText("%s\n\n%s" % (self["FullDescription"].getText(), "\n".join(similar)))
			if self.similarEPGCB:
				self["key_red"].setText(_("Similar"))
				self["similarActions"].setEnabled(True)

	def openSimilarList(self):
		id = self.event and self.event.getEventId()
		serviceRef = str(self.serviceRef)
		if id:
			self.similarEPGCB(id, serviceRef)

	def doContext(self):
		if self.event:
			if PY2:
				menu = [(p.name, boundFunction(self.runPlugin, p)) for p in plugins.getPlugins(where=PluginDescriptor.WHERE_EVENTINFO)
					if "servicelist" not in p.__call__.func_code.co_varnames
						if "selectedevent" not in p.__call__.func_code.co_varnames]
			else:
				menu = [(p.name, boundFunction(self.runPlugin, p)) for p in plugins.getPlugins(where=PluginDescriptor.WHERE_EVENTINFO)
					if "servicelist" not in p.__call__.__code__.co_varnames
						if "selectedevent" not in p.__call__.__code__.co_varnames]
			if len(menu) == 1:
				menu and menu[0][1]()
			elif len(menu) > 1:

				def boxAction(choice):
					if choice:
						choice[1]()

				text = "%s: %s" % (_("Select action"), self.event.getEventName())
				self.session.openWithCallback(boxAction, ChoiceBox, text=text, list=menu, windowTitle=_("Event View Context Menu"))

	def runPlugin(self, plugin):
		plugin.__call__(session=self.session, service=self.serviceRef, event=self.event, eventName=self.event.getEventName())


class EventViewSimple(Screen, HelpableScreen, EventViewBase):
	def __init__(self, session, event, serviceRef, callback=None, similarEPGCB=None, parent=None, windowTitle=None, skinName=None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		EventViewBase.__init__(self, event, serviceRef, callback=callback, similarEPGCB=similarEPGCB, parent=parent, windowTitle=windowTitle)
		self.skinName = ["EventView"]
		if skinName:
			if isinstance(skinName, str):
				self.skinName.insert(0, skinName)
			else:
				self.skinName = skinName + self.skinname


class EventViewEPGSelect(Screen, HelpableScreen, EventViewBase):
	def __init__(self, session, event, serviceRef, callback=None, singleEPGCB=None, multiEPGCB=None, similarEPGCB=None, parent=None, windowTitle=None, skinName=None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		EventViewBase.__init__(self, event, serviceRef, callback=callback, similarEPGCB=similarEPGCB, parent=parent, windowTitle=windowTitle)
		if singleEPGCB:
			self["key_yellow"] = StaticText(_("Single EPG"))
			self["singleAction"] = HelpableActionMap(self, ["EventViewEPGActions"], {
				"openSingleServiceEPG": (self.openSingleEPG, _("Open the single service EPG view"))
			}, prio=0, description=_("Event View Actions"))
			self.singleEPGCB = singleEPGCB
		if multiEPGCB:
			self["key_blue"] = StaticText(_("Multi EPG"))
			self["multiAction"] = HelpableActionMap(self, ["EventViewEPGActions"], {
				"openMultiServiceEPG": (self.openMultiEPG, _("Open the multi service EPG view"))
			}, prio=0, description=_("Event View Actions"))
			self.multiEPGCB = multiEPGCB
		self.skinName = ["EventView"]
		if skinName:
			if isinstance(skinName, str):
				self.skinName.insert(0, skinName)
			else:
				self.skinName = skinName + self.skinName

	def openSingleEPG(self):
		self.hide()
		self.singleEPGCB()
		self.close()

	def openMultiEPG(self):
		self.hide()
		self.multiEPGCB()
		self.close()
