# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens.ParentalControlSetup import ProtectedScreen
from enigma import eConsoleAppContainer, eDVBDB, eTimer
from Components.ActionMap import ActionMap, NumberActionMap
from Components.config import config, ConfigSubsection, ConfigText, ConfigYesNo
from Components.PluginComponent import plugins
from Components.PluginList import *
from Components.Label import Label
from Components.Language import language
from Components.ServiceList import refreshServiceList
from Components.Harddisk import harddiskmanager
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import BoxInfo, hassoftcaminstalled
from Components import Opkg
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.Console import Console
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_GUISKIN, isPluginInstalled
from Tools.LoadPixmap import LoadPixmap

from time import time
from os import unlink
from os.path import normpath

language.addCallback(plugins.reloadPlugins)

config.misc.pluginbrowser = ConfigSubsection()

config.misc.pluginbrowser.alsautils = ConfigYesNo(default=False)
config.misc.pluginbrowser.bluez = ConfigYesNo(default=False)
config.misc.pluginbrowser.busybox = ConfigYesNo(default=False)
config.misc.pluginbrowser.e2fsprogs = ConfigYesNo(default=False)
config.misc.pluginbrowser.enigma2locale = ConfigYesNo(default=False)
config.misc.pluginbrowser.firmware = ConfigYesNo(default=False)
config.misc.pluginbrowser.frequency = ConfigYesNo(default=False)
config.misc.pluginbrowser.glibccharmap = ConfigYesNo(default=False)
config.misc.pluginbrowser.glibcgconv = ConfigYesNo(default=False)
config.misc.pluginbrowser.gstplugins = ConfigYesNo(default=False)
config.misc.pluginbrowser.kernelmodule = ConfigYesNo(default=False)
config.misc.pluginbrowser.mtdutils = ConfigYesNo(default=False)
config.misc.pluginbrowser.packagegroupbase = ConfigYesNo(default=False)
config.misc.pluginbrowser.pamplugin = ConfigYesNo(default=False)
config.misc.pluginbrowser.perlmodule = ConfigYesNo(default=False)
config.misc.pluginbrowser.python = ConfigYesNo(default=False)
config.misc.pluginbrowser.samba = ConfigYesNo(default=False)
config.misc.pluginbrowser.tzdata = ConfigYesNo(default=False)
config.misc.pluginbrowser.utillinux = ConfigYesNo(default=False)

config.misc.pluginbrowser.plugin_order = ConfigText(default="")


class PluginBrowserSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["entry"] = StaticText("")
		self["desc"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent.selectionChanged()

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)

	def selectionChanged(self, name, desc):
		self["entry"].text = name
		self["desc"].text = desc


class PluginBrowser(Screen, ProtectedScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Plugin browser"))
		ProtectedScreen.__init__(self)

		self.firsttime = True

		self["key_red"] = self["red"] = Label(_("Remove plugins"))
		self["key_green"] = self["green"] = Label(_("Download plugins"))
		self["key_yellow"] = self["yellow"] = Label(_("User plugins"))
		self.list = []
		self["list"] = PluginList(self.list)

		self["actions"] = ActionMap(["WizardActions", "MenuActions"],
		{
			"ok": self.save,
			"back": self.close,
			"menu": self.pluginbrowserSetup,
		})
		self["PluginDownloadActions"] = ActionMap(["ColorActions"],
		{
			"red": self.delete,
			"green": self.download,
			"yellow": self.userInstalledPlugins
		})
		self["DirectionActions"] = ActionMap(["DirectionActions"],
		{
			"moveUp": self.moveUp,
			"moveDown": self.moveDown,
			"upUp": self.doNothing,
			"downUp": self.doNothing,
			"leftUp": self.pageUp,
			"rightUp": self.pageDown
		})
		self["NumberActions"] = NumberActionMap(["NumberActions"],
		{
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		})
		self["HelpActions"] = ActionMap(["HelpActions"],
		{
			"displayHelp": self.showHelp,
		})
		self.help = False

		self.number = 0
		self.nextNumberTimer = eTimer()
		self.nextNumberTimer.callback.append(self.okbuttonClick)

		self.onFirstExecBegin.append(self.checkWarnings)
		self.onShown.append(self.updateList)
		self.onChangedEntry = []
		self["list"].onSelectionChanged.append(self.selectionChanged)
		self.onLayoutFinish.append(self.saveListsize)

	def pluginbrowserSetup(self):
		from Screens.Setup import Setup
		self.session.open(Setup, "PluginBrowser")

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and (not config.ParentalControl.config_sections.main_menu.value or hasattr(self.session, 'infobar') and self.session.infobar is None) and config.ParentalControl.config_sections.plugin_browser.value

	def exit(self):
		self.close(True)

	def saveListsize(self):
		listsize = self["list"].instance.size()
		self.listWidth = listsize.width()
		self.listHeight = listsize.height()

	def createSummary(self):
		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["list"].getCurrent()
		if item:
			p = item[0]
			name = p.name
			desc = p.description
		else:
			name = "-"
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def checkWarnings(self):
		if len(plugins.warnings):
			text = _("Some plugins are not available:\n")
			for (pluginname, error) in plugins.warnings:
				text += "%s (%s)\n" % (pluginname, error)
			plugins.resetWarnings()
			self.session.open(MessageBox, text=text, type=MessageBox.TYPE_WARNING)

	def save(self):
		self.run()

	def run(self):
		plugin = self["list"].l.getCurrentSelection()[0]
		plugin.__call__(session=self.session)
		self.help = False

	def setDefaultList(self, answer):
		if answer:
			config.misc.pluginbrowser.plugin_order.value = ""
			config.misc.pluginbrowser.plugin_order.save()
			self.updateList()

	def keyNumberGlobal(self, number):
		if number == 0 and self.number == 0:
			if len(self.list) > 0 and config.misc.pluginbrowser.plugin_order.value != "":
				self.session.openWithCallback(self.setDefaultList, MessageBox, _("Sort plugins list to default?"), MessageBox.TYPE_YESNO)
		else:
			self.number = self.number * 10 + number
			if self.number and self.number <= len(self.list):
				if number * 10 > len(self.list) or self.number >= 10:
					self.okbuttonClick()
				else:
					self.nextNumberTimer.start(1400, True)
			else:
				self.resetNumberKey()

	def okbuttonClick(self):
		self["list"].moveToIndex(self.number - 1)
		self.resetNumberKey()
		self.run()

	def resetNumberKey(self):
		self.nextNumberTimer.stop()
		self.number = 0

	def moveUp(self):
		self.move(-1)

	def moveDown(self):
		self.move(1)

	def pageUp(self):
		self["list"].instance.moveSelection(self["list"].instance.pageUp)

	def pageDown(self):
		self["list"].instance.moveSelection(self["list"].instance.pageDown)

	def doNothing(self):
		pass

	def move(self, direction):
		if len(self.list) > 1:
			currentIndex = self["list"].getSelectionIndex()
			swapIndex = (currentIndex + direction) % len(self.list)
			if currentIndex == 0 and swapIndex != 1:
				self.list = self.list[1:] + [self.list[0]]
			elif swapIndex == 0 and currentIndex != 1:
				self.list = [self.list[-1]] + self.list[:-1]
			else:
				self.list[currentIndex], self.list[swapIndex] = self.list[swapIndex], self.list[currentIndex]
			self["list"].l.setList(self.list)
			if direction == 1:
				self["list"].down()
			else:
				self["list"].up()
			plugin_order = []
			for x in self.list:
				plugin_order.append(x[0].path[24:])
			config.misc.pluginbrowser.plugin_order.value = ",".join(plugin_order)
			config.misc.pluginbrowser.plugin_order.save()

	def updateList(self, showHelp=False):
		self.list = []
		pluginlist = plugins.getPlugins(PluginDescriptor.WHERE_PLUGINMENU)[:]
		for x in config.misc.pluginbrowser.plugin_order.value.split(","):
			plugin = list(plugin for plugin in pluginlist if plugin.path[24:] == x)
			if plugin:
				self.list.append(PluginEntryComponent(plugin[0], self.listWidth))
				pluginlist.remove(plugin[0])
		self.list = self.list + [PluginEntryComponent(plugin, self.listWidth) for plugin in pluginlist]
		if config.usage.menu_show_numbers.value in ("menu&plugins", "plugins") or showHelp:
			for x in enumerate(self.list):
				tmp = list(x[1][1])
				tmp[7] = "%s %s" % (x[0] + 1, tmp[7])
				x[1][1] = tuple(tmp)
		self["list"].l.setList(self.list)

	def showHelp(self):
		if config.usage.menu_show_numbers.value not in ("menu&plugins", "plugins"):
			self.help = not self.help
			self.updateList(self.help)

	def delete(self):
		self.session.openWithCallback(self.PluginDownloadBrowserClosed, PluginDownloadBrowser, PluginDownloadBrowser.REMOVE)

	def download(self):
		self.session.openWithCallback(self.PluginDownloadBrowserClosed, PluginDownloadBrowser, PluginDownloadBrowser.DOWNLOAD, self.firsttime)
		self.firsttime = False

	def PluginDownloadBrowserClosed(self):
		self.updateList()
		self.checkWarnings()

	def openExtensionmanager(self):
		if isPluginInstalled("SoftwareManager"):
			try:
				from Plugins.SystemPlugins.SoftwareManager.plugin import PluginManager
			except ImportError as e:
				self.session.open(MessageBox, _("The software management extension is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)
			else:
				self.session.openWithCallback(self.PluginDownloadBrowserClosed, PluginManager)

	def userInstalledPlugins(self):
		from Screens.UserPlugins import AboutUserInstalledPlugins
		self.session.open(AboutUserInstalledPlugins)


class PluginDownloadBrowser(Screen):
	DOWNLOAD = 0
	REMOVE = 1
	PLUGIN_PREFIX = 'enigma2-plugin-'
	ALSAUTILS_PREFIX = 'alsa-utils-'
	BLUEZ_PREFIX = 'bluez5-'
	BUSYBOX_PREFIX = 'busybox-'
	E2FSPROGS_PREFIX = 'e2fsprogs-'
	ENIGMA2LOCALE_PREFIX = 'enigma2-locale-'
	FIRMWARE_PREFIX = 'firmware-'
	FREQUENCY_PREFIX = 'frequency-xml-list-'
	GLIBCCHARMAP_PREFIX = 'glibc-charmap-'
	GLIBCGCONC_PREFIX = 'glibc-gconv-'
	if BoxInfo.getItem("brand") == "wetek":
		GSTPLUGINS_PREFIX = 'gst-plugins-'
	else:
		GSTPLUGINS_PREFIX = 'gstreamer1.0-plugins-'
	GSTOLDPLUGINS_PREFIX = 'gst-plugins-'
	KERNELMODULE_PREFIX = 'kernel-module-'
	MTDUTILS_PREFIX = 'mtd-utils-'
	PACKAGEGROUPBASE_PREFIX = 'packagegroup-base-'
	PAMPLUGIN_PREFIX = 'pam-plugin-'
	PERLMODULE_PREFIX = 'perl-module-'
	if BoxInfo.getItem("python").startswith("2"):
		PYTHON_PREFIX = 'python-'
	else:
		PYTHON_PREFIX = 'python3-'
	SAMBA_PREFIX = 'samba-'
	TZDATA_PREFIX = 'tzdata-'
	UTILLINUX_PREFIX = 'util-linux-'
	lastDownloadDate = None

	def __init__(self, session, type=0, needupdate=True):
		Screen.__init__(self, session)

		self.type = type
		self.needupdate = needupdate

		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.runFinished)
		self.container.dataAvail.append(self.dataAvail)
		self.onLayoutFinish.append(self.startRun)
		self.setTitle(self.type == self.DOWNLOAD and _("Downloadable new plugins") or _("Remove plugins"))
		self.list = []
		self["list"] = PluginList(self.list)
		self.pluginlist = []
		self.expanded = []
		self.installedplugins = []
		self.plugins_changed = False
		self.reload_settings = False
		self.check_softcams = False
		self.check_settings = False
		self.install_settings_name = ''
		self.remove_settings_name = ''
		self["text"] = Label(self.type == self.DOWNLOAD and _("Downloading plugin information. Please wait...") or _("Getting plugin information. Please wait..."))
		self.run = 0
		self.remainingdata = ""
		self["actions"] = ActionMap(["WizardActions"],
		{
			"ok": self.go,
			"back": self.requestClose,
		})
		self.opkg = 'opkg'
		self.opkg_install = self.opkg + ' install'
		self.opkg_remove = self.opkg + ' remove --autoremove'

	def go(self):
		sel = self["list"].l.getCurrentSelection()

		if sel is None:
			return

		sel = sel[0]
		if isinstance(sel, str): # category
			if sel in self.expanded:
				self.expanded.remove(sel)
			else:
				self.expanded.append(sel)
			self.updateList()
		else:
			if self.type == self.DOWNLOAD:
				self.session.openWithCallback(self.runInstall, MessageBox, _("Do you really want to download\nthe plugin \"%s\"?") % sel.name)
			elif self.type == self.REMOVE:
				self.session.openWithCallback(self.runInstall, MessageBox, _("Do you really want to remove\nthe plugin \"%s\"?") % sel.name)

	def requestClose(self):
		if self.plugins_changed:
			plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
		if self.reload_settings:
			self["text"].setText(_("Reloading bouquets and services..."))
			eDVBDB.getInstance().reloadBouquets()
			eDVBDB.getInstance().reloadServicelist()
			from Components.ParentalControl import parentalControl
			parentalControl.open()
			refreshServiceList()
		if self.check_softcams:
			BoxInfo.setItem("HasSoftcamInstalled", hassoftcaminstalled())
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
		self.container.appClosed.remove(self.runFinished)
		self.container.dataAvail.remove(self.dataAvail)
		self.close()

	def resetPostInstall(self):
		try:
			del self.postInstallCall
		except:
			pass

	def installDestinationCallback(self, result):
		if result is not None:
			dest = result[1]
			if dest.startswith('/'):
				# Custom install path, add it to the list too
				dest = normpath(dest)
				extra = '--add-dest %s:%s -d %s' % (dest, dest, dest)
				Opkg.opkgAddDestination(dest)
			else:
				extra = '-d ' + dest
			self.doInstall(self.installFinished, self["list"].l.getCurrentSelection()[0].name + ' ' + extra)
		else:
			self.resetPostInstall()

	def runInstall(self, val):
		if val:
			if self.type == self.DOWNLOAD:
				if self["list"].l.getCurrentSelection()[0].name.startswith("picons-"):
					supported_filesystems = frozenset(('ext4', 'ext3', 'ext2', 'reiser', 'reiser4', 'jffs2', 'ubifs', 'rootfs'))
					candidates = []
					import Components.Harddisk
					mounts = Components.Harddisk.getProcMounts()
					for partition in harddiskmanager.getMountedPartitions(False, mounts):
						if partition.filesystem(mounts) in supported_filesystems:
							candidates.append((partition.description, partition.mountpoint))
					if candidates:
						from Components.Renderer import Picon
						self.postInstallCall = Picon.initPiconPaths
						self.session.openWithCallback(self.installDestinationCallback, ChoiceBox, title=_("Install picons on"), list=candidates)
					return
				elif self["list"].l.getCurrentSelection()[0].name.startswith("display-picon"):
					supported_filesystems = frozenset(('ext4', 'ext3', 'ext2', 'reiser', 'reiser4', 'jffs2', 'ubifs', 'rootfs'))
					candidates = []
					import Components.Harddisk
					mounts = Components.Harddisk.getProcMounts()
					for partition in harddiskmanager.getMountedPartitions(False, mounts):
						if partition.filesystem(mounts) in supported_filesystems:
							candidates.append((partition.description, partition.mountpoint))
					if candidates:
						from Components.Renderer import LcdPicon
						self.postInstallCall = LcdPicon.initLcdPiconPaths
						self.session.openWithCallback(self.installDestinationCallback, ChoiceBox, title=_("Install display picons on"), list=candidates)
					return
				self.install_settings_name = self["list"].l.getCurrentSelection()[0].name
				if self["list"].l.getCurrentSelection()[0].name.startswith('settings-'):
					self.check_settings = True
					self.startOpkgListInstalled(self.PLUGIN_PREFIX + 'settings-*')
				else:
					self.runSettingsInstall()
			elif self.type == self.REMOVE:
				self.doRemove(self.installFinished, self["list"].l.getCurrentSelection()[0].name)

	def doRemove(self, callback, pkgname):
		if pkgname.startswith((self.ALSAUTILS_PREFIX, self.BLUEZ_PREFIX, self.BUSYBOX_PREFIX, self.E2FSPROGS_PREFIX, self.ENIGMA2LOCALE_PREFIX, self.FIRMWARE_PREFIX, self.FREQUENCY_PREFIX, self.GLIBCCHARMAP_PREFIX, self.GLIBCGCONC_PREFIX, self.GSTPLUGINS_PREFIX, self.GSTOLDPLUGINS_PREFIX, self.KERNELMODULE_PREFIX, self.MTDUTILS_PREFIX, self.PACKAGEGROUPBASE_PREFIX, self.PAMPLUGIN_PREFIX, self.PERLMODULE_PREFIX, self.PYTHON_PREFIX, self.SAMBA_PREFIX, self.TZDATA_PREFIX, self.UTILLINUX_PREFIX)):
			self.session.openWithCallback(callback, Console, cmdlist=[self.opkg_remove + Opkg.opkgExtraDestinations() + " " + pkgname, "sync"], skin="Console_Pig")
		else:
			self.session.openWithCallback(callback, Console, cmdlist=[self.opkg_remove + Opkg.opkgExtraDestinations() + " " + self.PLUGIN_PREFIX + pkgname, "sync"], skin="Console_Pig")

	def doInstall(self, callback, pkgname):
		if pkgname.startswith((self.ALSAUTILS_PREFIX, self.BLUEZ_PREFIX, self.BUSYBOX_PREFIX, self.E2FSPROGS_PREFIX, self.ENIGMA2LOCALE_PREFIX, self.FIRMWARE_PREFIX, self.FREQUENCY_PREFIX, self.GLIBCCHARMAP_PREFIX, self.GLIBCGCONC_PREFIX, self.GSTPLUGINS_PREFIX, self.GSTOLDPLUGINS_PREFIX, self.KERNELMODULE_PREFIX, self.MTDUTILS_PREFIX, self.PACKAGEGROUPBASE_PREFIX, self.PAMPLUGIN_PREFIX, self.PERLMODULE_PREFIX, self.PYTHON_PREFIX, self.SAMBA_PREFIX, self.TZDATA_PREFIX, self.UTILLINUX_PREFIX)):
			self.session.openWithCallback(callback, Console, cmdlist=[self.opkg_install + " " + pkgname, "sync"], skin="Console_Pig")
		else:
			self.session.openWithCallback(callback, Console, cmdlist=[self.opkg_install + " " + self.PLUGIN_PREFIX + pkgname, "sync"], skin="Console_Pig")

	def runSettingsRemove(self, val):
		if val:
			self.doRemove(self.runSettingsInstall, self.remove_settings_name)

	def runSettingsInstall(self):
		self.doInstall(self.installFinished, self.install_settings_name)

	def startOpkgListInstalled(self, pkgname=PLUGIN_PREFIX + '*'):
		self.container.execute(self.opkg + Opkg.opkgExtraDestinations() + " list_installed '%s'" % pkgname)

	def startOpkgListAvailable(self):
		self.container.execute(self.opkg + Opkg.opkgExtraDestinations() + " list")

	def startRun(self):
		listsize = self["list"].instance.size()
		self["list"].instance.hide()
		self.listWidth = listsize.width()
		self.listHeight = listsize.height()
		if self.type == self.DOWNLOAD:
			if self.needupdate and not PluginDownloadBrowser.lastDownloadDate or (time() - PluginDownloadBrowser.lastDownloadDate) > 3600:
				# Only update from internet once per hour
				self.container.execute(self.opkg + " update")
				PluginDownloadBrowser.lastDownloadDate = time()
			else:
				self.run = 1
				self.startOpkgListInstalled()
		elif self.type == self.REMOVE:
			self.run = 1
			self.startOpkgListInstalled()

	def installFinished(self):
		if hasattr(self, 'postInstallCall'):
			try:
				self.postInstallCall()
			except Exception as ex:
				print("[PluginBrowser] postInstallCall failed:", ex)
			self.resetPostInstall()
		try:
			unlink('/tmp/opkg.conf')
		except:
			pass
		for plugin in self.pluginlist:
			if plugin[3] == self["list"].l.getCurrentSelection()[0].name:
				self.pluginlist.remove(plugin)
				break
		self.plugins_changed = True
		if self["list"].l.getCurrentSelection()[0].name.startswith("settings-"):
			self.reload_settings = True
		if self["list"].l.getCurrentSelection()[0].name.startswith("softcams-"):
			self.check_softcams = True
		self.expanded = []
		self.updateList()
		self["list"].moveToIndex(0)

	def runFinished(self, retval):
		if self.check_settings:
			self.check_settings = False
			self.runSettingsInstall()
			return
		self.remainingdata = ""
		if self.run == 0:
			self.run = 1
			if self.type == self.DOWNLOAD:
				self.startOpkgListInstalled()
		elif self.run == 1 and self.type == self.DOWNLOAD:
			self.run = 2
			pluginlist = []
			self.pluginlist = pluginlist
			for plugin in Opkg.enumPlugins(self.PLUGIN_PREFIX):
				if plugin[0] not in self.installedplugins:
					pluginlist.append(plugin + (plugin[0][15:],))
			if config.misc.pluginbrowser.alsautils.value:
				for plugin in Opkg.enumPlugins(self.ALSAUTILS_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.bluez.value:
				for plugin in Opkg.enumPlugins(self.BLUEZ_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.busybox.value:
				for plugin in Opkg.enumPlugins(self.BUSYBOX_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.e2fsprogs.value:
				for plugin in Opkg.enumPlugins(self.E2FSPROGS_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.enigma2locale.value:
				for plugin in Opkg.enumPlugins(self.ENIGMA2LOCALE_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.firmware.value:
				for plugin in Opkg.enumPlugins(self.FIRMWARE_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.frequency.value:
				for plugin in Opkg.enumPlugins(self.FREQUENCY_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.glibccharmap.value:
				for plugin in Opkg.enumPlugins(self.GLIBCCHARMAP_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.glibcgconv.value:
				for plugin in Opkg.enumPlugins(self.GLIBCGCONC_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.gstplugins.value:
				for plugin in Opkg.enumPlugins(self.GSTPLUGINS_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
				for plugin in Opkg.enumPlugins(self.GSTOLDPLUGINS_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.kernelmodule.value:
				for plugin in Opkg.enumPlugins(self.KERNELMODULE_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.mtdutils.value:
				for plugin in Opkg.enumPlugins(self.MTDUTILS_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.packagegroupbase.value:
				for plugin in Opkg.enumPlugins(self.PACKAGEGROUPBASE_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.pamplugin.value:
				for plugin in Opkg.enumPlugins(self.PAMPLUGIN_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.perlmodule.value:
				for plugin in Opkg.enumPlugins(self.PERLMODULE_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.python.value:
				for plugin in Opkg.enumPlugins(self.PYTHON_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.samba.value:
				for plugin in Opkg.enumPlugins(self.SAMBA_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.tzdata.value:
				for plugin in Opkg.enumPlugins(self.TZDATA_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if config.misc.pluginbrowser.utillinux.value:
				for plugin in Opkg.enumPlugins(self.UTILLINUX_PREFIX):
					if plugin[0] not in self.installedplugins:
						pluginlist.append(plugin + (plugin[0],))
			if pluginlist:
				pluginlist.sort()
				self.updateList()
				self["text"].instance.hide()
				self["list"].instance.show()
			else:
				self["text"].setText(_("No new plugins found"))
		else:
			if self.pluginlist:
				self.updateList()
				self["text"].instance.hide()
				self["list"].instance.show()
			else:
				self["text"].setText(_("No new plugins found"))

	def dataAvail(self, str):
		#prepend any remaining data from the previous call
		from six import ensure_str
		str = ensure_str(str)
		str = self.remainingdata + str
		#split in lines
		lines = str.split('\n')
		#'str' should end with '\n', so when splitting, the last line should be empty. If this is not the case, we received an incomplete line
		if len(lines[-1]):
			#remember this data for next time
			self.remainingdata = lines[-1]
			lines = lines[0:-1]
		else:
			self.remainingdata = ""

		if self.check_settings:
			self.check_settings = False
			self.remove_settings_name = str.split(' - ')[0].replace(self.PLUGIN_PREFIX, '')
			self.session.openWithCallback(self.runSettingsRemove, MessageBox, _('You already have a channel list installed,\nwould you like to remove\n"%s"?') % self.remove_settings_name)
			return

		if self.run == 1:
			for x in lines:
				plugin = x.split(" - ", 2)
				# 'opkg list_installed' only returns name + version, no description field
				if len(plugin) >= 2:
					if config.misc.extraopkgpackages.value is True:
						if not plugin[0].endswith('--pycache--'):
							if plugin[0] not in self.installedplugins:
								if self.type == self.DOWNLOAD:
									self.installedplugins.append(plugin[0])
								else:
									if len(plugin) == 2:
										plugin.append('')
									plugin.append(plugin[0][15:])
									self.pluginlist.append(plugin)
					else:
						if not plugin[0].endswith('-dev') and not plugin[0].endswith('-staticdev') and not plugin[0].endswith('-dbg') and not plugin[0].endswith('-doc') and not plugin[0].endswith('-src') and not plugin[0].endswith('-po') and not plugin[0].endswith('--pycache--'):
							if plugin[0] not in self.installedplugins:
								if self.type == self.DOWNLOAD:
									self.installedplugins.append(plugin[0])
								else:
									if len(plugin) == 2:
										plugin.append('')
									plugin.append(plugin[0][15:])
									self.pluginlist.append(plugin)

	def updateList(self):
		list = []
		expandableIcon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/expandable-plugins.png"))
		expandedIcon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/expanded-plugins.png"))
		verticallineIcon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/verticalline-plugins.png"))

		self.plugins = {}
		for x in self.pluginlist:
			split = x[3].split('-', 1)
			if len(split) < 2:
				continue
			if split[0] not in self.plugins:
				self.plugins[split[0]] = []

			self.plugins[split[0]].append((PluginDescriptor(name=x[3], description=x[2], icon=verticallineIcon), split[1], x[1]))

		for x in self.plugins.keys():
			if x in self.expanded:
				list.append(PluginCategoryComponent(x, expandedIcon, self.listWidth))
				list.extend([PluginDownloadComponent(plugin[0], plugin[1], plugin[2], self.listWidth) for plugin in self.plugins[x]])
			else:
				list.append(PluginCategoryComponent(x, expandableIcon, self.listWidth))
		self.list = list
		self["list"].l.setList(list)
