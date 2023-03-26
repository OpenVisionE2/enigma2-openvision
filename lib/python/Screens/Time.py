# -*- coding: utf-8 -*-
from Components.ActionMap import ActionMap, HelpableActionMap
from os.path import islink
from Components.Console import Console
from Components.config import config, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Screens.Setup import Setup
from Screens.Screen import Screen
from Screens.HelpMenu import ShowRemoteControl
from Tools.Directories import fileContains
from Tools.Geolocation import geolocation


class Time(Setup):
	def __init__(self, session):
		Setup.__init__(self, session=session, setup="Time")
		self["key_yellow"] = StaticText("")
		self["geolocationActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.useGeolocation, _("Use geolocation to set the current time zone location")),
			"green": self.keySave
		}, prio=0, description=_("Time Setup Actions"))
		self.selectionChanged()

	def checkTimeSyncRootFile(self):
		if config.ntp.timesync.value != "dvb":
			if not islink("/etc/network/if-up.d/timesync") and not fileContains("/var/spool/cron/root", "timesync"):
				Console().ePopen("ln -s /usr/bin/timesync /etc/network/if-up.d/timesync;echo '30 * * * * /usr/bin/timesync silent' >>/var/spool/cron/root")
		else:
			if islink("/etc/network/if-up.d/timesync") and fileContains("/var/spool/cron/root", "timesync"):
				Console().ePopen("sed -i '/timesync/d' /var/spool/cron/root;unlink /etc/network/if-up.d/timesync")

	def keySave(self):
		Setup.keySave(self)
		self.checkTimeSyncRootFile()

	def selectionChanged(self):
		if Setup.getCurrentItem(self) in (config.timezone.area, config.timezone.val):
			self["key_yellow"].setText(_("Use Geolocation"))
			self["geolocationActions"].setEnabled(True)
		else:
			self["key_yellow"].setText("")
			self["geolocationActions"].setEnabled(False)
		Setup.selectionChanged(self)

	def useGeolocation(self):
		geolocationData = geolocation.getGeolocationData(fields="status,message,timezone,proxy")
		if geolocationData.get("proxy", True):
			self.setFootnote(_("Geolocation is not available."))
			return
		tz = geolocationData.get("timezone", None)
		if tz is None:
			self.setFootnote(_("Geolocation does not contain time zone information."))
		else:
			areaItem = None
			valItem = None
			for item in self["config"].list:
				if item[1] is config.timezone.area:
					areaItem = item
				if item[1] is config.timezone.val:
					valItem = item
			area, zone = tz.split("/", 1)
			config.timezone.area.value = area
			if areaItem is not None:
				areaItem[1].changed()
			self["config"].invalidate(areaItem)
			config.timezone.val.value = zone
			if valItem is not None:
				valItem[1].changed()
			self["config"].invalidate(valItem)
			self.setFootnote(_("Geolocation has been used to set the time zone."))


class TimeWizard(ConfigListScreen, Screen, ShowRemoteControl):
	skin = """
	<screen name="TimeWizard" position="center,60" size="980,635" resolution="1280,720">
		<widget name="text" position="10,10" size="e-20,25" font="Regular;20" transparent="1" verticalAlignment="center" />
		<widget name="config" position="10,40" size="e-20,250" enableWrapAround="1" entryFont="Regular;25" valueFont="Regular;25" itemHeight="35" scrollbarMode="showOnDemand" />
		<widget source="key_red" render="Label" objectTypes="key_red,StaticText" position="180,e-50" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" objectTypes="key_yellow,StaticText" position="390,e-50" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget name="HelpWindow" position="0,0" size="0,0" alphaTest="blend" conditional="HelpWindow" transparent="1" zPosition="+1" />
		<widget name="rc" conditional="rc" alphaTest="blend" position="10,290" size="100,360" />
		<widget name="wizard" conditional="wizard" pixmap="picon_default.png" position="740,400" size="220,132" alphaTest="blend" />
		<widget name="indicatorU0" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorU1" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorU2" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorU3" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorU4" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorU5" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorU6" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorU7" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorU8" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorU9" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorU10" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorU11" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorU12" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorU13" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorU14" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorU15" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorL0" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorL1" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorL2" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorL3" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorL4" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorL5" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorL6" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorL7" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorL8" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorL9" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorL10" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorL11" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorL12" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorL13" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorL14" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		<widget name="indicatorL15" pixmap="rc_circle.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		ShowRemoteControl.__init__(self)
		self.skinName = ["TimeWizard"]
		self.setTitle(_("Time Wizard"))
		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self["text"] = Label()
		self["text"].setText(_("Press YELLOW button to set your schedule."))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_yellow"] = StaticText(_("Set local time"))
		self["wizard"] = Pixmap()
		self["lab1"] = StaticText(_("OpenVision"))
		self["lab2"] = StaticText(_("Lets define enigma2 once more"))
		self["lab3"] = StaticText(_("Report problems to:"))
		self["lab4"] = StaticText(_("https://openvision.tech"))
		self["lab5"] = StaticText(_("Sources are available at:"))
		self["lab6"] = StaticText(_("https://github.com/OpenVisionE2"))
		self["actions"] = ActionMap(["WizardActions", "ColorActions"], {
			"yellow": self.yellow,
			"ok": self.red,
			"red": self.red,
			"back": self.red
		}, -2)
		self.onLayoutFinish.append(self.selectKeys)
		self.updateTimeList()

	def selectKeys(self):
		self.clearSelectedKeys()
		self.selectKey("UP")
		self.selectKey("DOWN")
		self.selectKey("LEFT")
		self.selectKey("RIGHT")
		self.selectKey("RED")
		self.selectKey("YELLOW")

	def updateTimeList(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Time zone area"), config.timezone.area))
		self.list.append(getConfigListEntry(_("Time zone"), config.timezone.val))
		if config.usage.date.enabled.value:
			self.list.append(getConfigListEntry(_("Date style"), config.usage.date.dayfull))
			config.usage.date.dayfull.save()
		if config.usage.time.enabled.value:
			self.list.append(getConfigListEntry(_("Time style"), config.usage.time.long))
			config.usage.time.long.save()
		self.list.append(getConfigListEntry(_("Time synchronization method"), config.ntp.timesync))
		config.ntp.timesync.save()
		if config.ntp.timesync.value != "dvb":
			self.list.append(getConfigListEntry(_("RFC 5905 hostname (SNTP - Simple Network Time Protocol)"), config.ntp.sntpserver))
			config.ntp.sntpserver.save()
			self.list.append(getConfigListEntry(_("RFC 868 hostname (rdate - Remote Date)"), config.ntp.rdateserver))
			config.ntp.rdateserver.save()
		config.timezone.val.save()
		config.timezone.area.save()
		self["config"].list = self.list
		self["config"].setList(self.list)

	def useGeolocation(self):
		geolocationData = geolocation.getGeolocationData(fields="status,message,timezone,proxy")
		if geolocationData.get("proxy", True):
			self["text"].setText(_("Geolocation is not available."))
			return
		tz = geolocationData.get("timezone", None)
		if not tz:
			self["text"].setText(_("Geolocation does not contain time zone information."))
		else:
			areaItem = None
			valItem = None
			for item in self["config"].list:
				if item[1] is config.timezone.area:
					areaItem = item
				if item[1] is config.timezone.val:
					valItem = item
			area, zone = tz.split("/", 1)
			config.timezone.area.value = area
			if areaItem:
				areaItem[1].changed()
			self["config"].invalidate(areaItem)
			config.timezone.val.value = zone
			if valItem:
				valItem[1].changed()
			self["config"].invalidate(valItem)
			self.updateTimeList()
			self["text"].setText(_("Your local time has been set successfully. Settings has been saved.\n\nPress \"OK\" to continue wizard."))

	def checkTimeSyncRootFile(self):
		if config.ntp.timesync.value != "dvb":
			if not islink("/etc/network/if-up.d/timesync") and not fileContains("/var/spool/cron/root", "timesync"):
				Console().ePopen("ln -s /usr/bin/timesync /etc/network/if-up.d/timesync;echo '30 * * * * /usr/bin/timesync silent' >>/var/spool/cron/root")
		else:
			if islink("/etc/network/if-up.d/timesync") and fileContains("/var/spool/cron/root", "timesync"):
				Console().ePopen("sed -i '/timesync/d' /var/spool/cron/root;unlink /etc/network/if-up.d/timesync")

	def red(self):
		self.close()

	def yellow(self):
		self.useGeolocation()
		self.checkTimeSyncRootFile()
