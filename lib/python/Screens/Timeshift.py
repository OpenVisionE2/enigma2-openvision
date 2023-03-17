# -*- coding: utf-8 -*-
from os import stat, statvfs
from os.path import isdir, join as pathjoin

from Components.config import config
from Screens.LocationBox import DEFAULT_INHIBIT_DEVICES, TimeshiftLocationBox
from Screens.MessageBox import MessageBox
from Screens.Setup import Setup

itemchange = _("Press LEFT RIGHT OK or MENU to change path.")


class TimeshiftSettings(Setup):
	def __init__(self, session):
		self.buildChoices("TimeshiftPath", config.usage.timeshift_path, None)
		Setup.__init__(self, session=session, setup="Timeshift")
		self.greenText = self["key_green"].text
		self.errorItem = -1
		if self.getCurrentItem() is config.usage.timeshift_path:
			self.pathStatus(self.getCurrentValue())

	def selectionChanged(self):
		if self.errorItem == -1:
			Setup.selectionChanged(self)
		else:
			self["config"].setCurrentIndex(self.errorItem)

	def changedEntry(self):
		if self.getCurrentItem() is config.usage.timeshift_path:
			self.pathStatus(self.getCurrentValue())
		Setup.changedEntry(self)

	def keySelect(self):
		if self.getCurrentItem() is config.usage.timeshift_path:
			self.session.openWithCallback(self.pathSelect, TimeshiftLocationBox)
		else:
			Setup.keySelect(self)

	def keySave(self):
		if self.errorItem == -1:
			Setup.keySave(self)
		else:
			self.session.open(MessageBox, "%s\n\n%s" % (self.getFootnote() % _("Please select an acceptable directory.")), type=MessageBox.TYPE_ERROR)

	def buildChoices(self, item, configEntry, path):
		configList = config.usage.allowed_timeshift_paths.value[:]
		if configEntry.saved_value and configEntry.saved_value not in configList:
			configList.append(configEntry.saved_value)
			configEntry.value = configEntry.saved_value
		if path is None:
			path = configEntry.value
		if path and path not in configList:
			configList.append(path)
		pathList = [(x, x) for x in configList]
		configEntry.value = path
		configEntry.setChoices(pathList, default=configEntry.default)
		print("[Timeshift] DEBUG %s: Current='%s', Default='%s', Choices='%s'" % (item, configEntry.value, configEntry.default, configList))

	def pathSelect(self, path):
		if path is not None:
			path = pathjoin(path, "")
			self.buildChoices("TimeshiftPath", config.usage.timeshift_path, path)
		self["config"].invalidateCurrent()
		self.changedEntry()

	def pathStatus(self, path):
		from Tools.Directories import fileAccess # hasHardLinks this gives false errors.
		if not isdir(path):
			self.errorItem = self["config"].getCurrentIndex()
			footnote = _("'%s' does not exist.\n%s") % (path, itemchange)
			green = ""
		elif stat(path).st_dev in DEFAULT_INHIBIT_DEVICES:
			self.errorItem = self["config"].getCurrentIndex()
			footnote = _("'%s' is Internal Flash. It is not a storage device.\n%s") % (path, itemchange)
			green = ""
		elif not fileAccess(path, "w"):
			self.errorItem = self["config"].getCurrentIndex()
			footnote = _("'%s' not writeable.\n%s") % (path, itemchange)
			green = ""
		#elif not hasHardLinks(path):
			#self.errorItem = self["config"].getCurrentIndex()
			#footnote = _("Directory '%s' can't be linked to recordings!") % path
			#green = ""
		else:
			self.errorItem = -1
			footnote = ""
			green = self.greenText
		if isdir(path):
			size = statvfs(path)
			storage = int((size.f_bfree * size.f_frsize) // (1024 * 1024) // 1000)
			if storage:
				if isdir(path) and not stat(path).st_dev in DEFAULT_INHIBIT_DEVICES and fileAccess(path, "w") and storage <= 1:
					self.errorItem = self["config"].getCurrentIndex()
					footnote = _("'%s' Storage device free size %d GB.\n%s") % (path, storage, itemchange)
					green = ""
		self.setFootnote(footnote)
		self["key_green"].text = green
