# -*- coding: utf-8 -*-
from os import listdir
from os.path import exists, join as pathjoin, normpath

from enigma import eConsoleAppContainer

from Components.config import ConfigSubsection, ConfigYesNo, config
from Components.Harddisk import harddiskmanager
from Components.SystemInfo import BoxInfo
from Tools.Directories import SCOPE_LIBDIR, fileReadLines, resolveFilename

MODULE_NAME = __name__.split(".")[-1]

opkgDestinations = []
opkgStatusPath = ""


def opkgExtraDestinations():
	return " ".join(["--add-dest %s:%s" % (x, x) for x in opkgDestinations])


def opkgAddDestination(mountpoint):
	global opkgDestinations
	if mountpoint not in opkgDestinations:
		opkgDestinations.append(mountpoint)
		print("[Opkg] Added to OPKG destinations: '%s'." % mountpoint)


def onPartitionChange(why, part):
	global opkgDestinations
	global opkgStatusPath
	mountpoint = normpath(part.mountpoint)
	if mountpoint and mountpoint != "/":
		if why == "add":
			if opkgStatusPath == "":
				opkgStatusPath = "var/lib/opkg/status"  # Recent opkg versions.
				if not exists(pathjoin("/", opkgStatusPath)):
					opkgStatusPath = resolveFilename(SCOPE_LIBDIR, "opkg/status")  # Older opkg versions.
			if exists(pathjoin(mountpoint, opkgStatusPath)):
				opkgAddDestination(mountpoint)
		elif why == "remove":
			if mountpoint in opkgDestinations:
				opkgDestinations.remove(mountpoint)
				print("[Opkg] Removed from OPKG destinations: '%s'." % mountpoint)


def listsDirPath():
	for line in fileReadLines("/etc/opkg/opkg.conf", default=[], source=MODULE_NAME):
		if line.startswith("option"):
			line = line.strip().split()
			if len(line) == 3 and line[1] == "lists_dir":
				return line[2]
	return "/var/lib/opkg/lists"


def enumFeeds():
	for file in listdir("/etc/opkg"):
		if file.endswith("-feed.conf"):
			for line in fileReadLines(pathjoin("/etc/opkg", file), default=[], source=MODULE_NAME):
				line = line.strip().split()
				if len(line) >= 2:
					yield line[1]


def enumPlugins(filterStart=""):
	listsDir = listsDirPath()
	for feed in enumFeeds():
		package = None
		try:
			for line in open(pathjoin(listsDir, feed), "r"):
				if line.startswith("Package:"):
					package = line.split(":", 1)[1].strip()
					version = ""
					description = ""
					if config.misc.extraopkgpackages.value == True:
						if package.startswith(filterStart) and not package.endswith("--pycache--"):
							continue
					else:
						if package.startswith(filterStart) and not package.endswith("-dev") and not package.endswith("-staticdev") and not package.endswith("-dbg") and not package.endswith("-doc") and not package.endswith("-src") and not package.endswith("-po") and not package.endswith("--pycache--"):
							continue
					package = None
				if package == None:
					continue
				if line.startswith("Version:"):
					version = line.split(":", 1)[1].strip()
				elif line.startswith("Description:"):
					description = line.split(":", 1)[1].strip()
				elif description and line.startswith(" "):
					description += line[:-1]
				elif len(line) <= 1:
					d = description.split(" ", 3)
					if len(d) > 3:
						if d[1] == "version":
							description = d[3]
						if description.startswith("gitAUTOINC"):
							description = description.split(" ", 1)[1]
					yield package, version, description.strip()
					package = None
		except (IOError, UnicodeDecodeError) as err:
				print("UnicodeDecodeError: %s" % err)


if __name__ == "__main__":
	for plugin in enumPlugins("enigma"):
		print(plugin)

harddiskmanager.on_partition_list_change.append(onPartitionChange)
for part in harddiskmanager.getMountedPartitions():
	onPartitionChange("add", part)


class OpkgComponent:
	CMD_INSTALL = 0
	CMD_LIST = 1
	CMD_REMOVE = 2
	CMD_UPDATE = 3
	CMD_UPGRADE = 4
	CMD_UPGRADE_LIST = 5
	CMD_LIST_INSTALLED = 6
	# NOTE: The following commands are internal use only and should NOT be used by external modules!
	CMD_CLEAN = 100
	CMD_CLEAN_UPDATE = 101
	CMD_SET_FLAG = 102
	CMD_UPGRADE_EXCLUDE = 103
	CMD_RESET_FLAG = 104

	EVENT_INSTALL = 0
	EVENT_DOWNLOAD = 1
	EVENT_INFLATING = 2
	EVENT_CONFIGURING = 3
	EVENT_REMOVE = 4
	EVENT_UPVERSION = 5
	EVENT_UPGRADE = 6
	EVENT_UPDATED = 7
	EVENT_DESELECTED = 8
	EVENT_LISTITEM = 9
	EVENT_DONE = 10
	EVENT_ERROR = 11
	EVENT_MODIFIED = 12

	def __init__(self, opkg="/usr/bin/opkg"):
		if not hasattr(config.plugins, "softwaremanager"):
			config.plugins.softwaremanager = ConfigSubsection()
		if not hasattr(config.plugins.softwaremanager, "overwriteSettingsFiles"):
			config.plugins.softwaremanager.overwriteBusyBox = ConfigYesNo(default=True)
			config.plugins.softwaremanager.overwriteSettingsFiles = ConfigYesNo(default=False)
			config.plugins.softwaremanager.overwriteDriversFiles = ConfigYesNo(default=True)
			config.plugins.softwaremanager.overwriteEmusFiles = ConfigYesNo(default=True)
			config.plugins.softwaremanager.overwritePiconsFiles = ConfigYesNo(default=True)
			config.plugins.softwaremanager.overwriteBootlogoFiles = ConfigYesNo(default=True)
			config.plugins.softwaremanager.overwriteSpinnerFiles = ConfigYesNo(default=True)
		self.opkg = opkg
		self.cmd = eConsoleAppContainer()
		self.callbackList = []
		self.fetchedList = []
		self.excludeList = []
		self.currentCommand = None
		self.nextCommand = None

	def startCmd(self, cmd, args=None):
		extra = []
		for destination in opkgDestinations:
			extra.append("--add-dest")
			extra.append("%s:%s" % (destination, destination))
		if cmd == self.CMD_UPDATE and config.misc.opkgcleanmode.value:
			cmd = self.CMD_CLEAN
		elif cmd == self.CMD_UPGRADE and self.excludeList:
			cmd = self.CMD_SET_FLAG
		self.currentCommand = cmd
		if cmd == self.CMD_CLEAN:
			argv = ["clean"]
			self.nextCommand = (self.CMD_CLEAN_UPDATE, args)
		elif cmd in (self.CMD_UPDATE, self.CMD_CLEAN_UPDATE):
			argv = extra + ["update"]
		elif cmd == self.CMD_UPGRADE:
			command = extra + ["upgrade"]
			if args["testMode"]:
				command.insert(0, "--noaction")
			argv = command
		elif cmd == self.CMD_SET_FLAG:
			argv = ["flag", "hold"] + [x[0] for x in self.excludeList]
			self.nextCommand = (self.CMD_UPGRADE_EXCLUDE, args)
		elif cmd == self.CMD_UPGRADE_EXCLUDE:
			command = extra + ["upgrade"]
			if args["testMode"]:
				command.insert(0, "--noaction")
			argv = command
			self.nextCommand = (self.CMD_RESET_FLAG, args)
		elif cmd == self.CMD_RESET_FLAG:
			packages = [x[0] for x in self.excludeList]
			argv = ["flag", "ok"] + packages
		elif cmd == self.CMD_LIST:
			self.fetchedList = []
			self.excludeList = []
			packages = args["package"].split() if args and "package" in args else []
			argv = extra + ["list"] + packages
		elif cmd == self.CMD_INSTALL:
			argv = ["--force-overwrite", "install"] + args["package"].split()
		elif cmd == self.CMD_REMOVE:
			argv = ["remove"] + args["package"].split()
		elif cmd == self.CMD_UPGRADE_LIST:
			self.fetchedList = []
			self.excludeList = []
			argv = extra + ["list-upgradable"]
		elif cmd == self.CMD_LIST_INSTALLED:
			self.fetchedList = []
			self.excludeList = []
			packages = args["package"].split() if args and "package" in args else []
			argv = extra + ["list-installed"] + packages
		print("[Opkg] Executing '%s' with '%s'." % (self.opkg, " ".join(argv)))
		self.cache = ""
		self.cachePtr = -1
		self.cmd.dataAvail.append(self.cmdData)
		self.cmd.appClosed.append(self.cmdFinished)
		# self.cmd.setBufferSize(50)
		argv.insert(0, self.opkg)
		if self.cmd.execute(self.opkg, *argv):
			self.cmdFinished(-1)

	def cmdData(self, data):
		from six import ensure_str
		data = ensure_str(data)
		self.cache = "%s%s" % (self.cache, data)
		while True:
			linePtr = self.cache.find("\n", self.cachePtr + 1)
			if linePtr == -1:
				break
			self.parseLine(self.cache[self.cachePtr + 1:linePtr])
			self.cachePtr = linePtr

	# # opkg install smartmontools
	# Installing mailx (12.5-5) on root
	# Downloading https://feeds.openvision.dedyn.io/11.2/Vision/.test/cortexa15hf-neon-vfpv4/mailx_12.5-5-r0_cortexa15hf-neon-vfpv4.ipk.
	# Installing smartmontools (7.2) on root
	# Downloading https://feeds.openvision.dedyn.io/11.2/Vision/.test/cortexa15hf-neon-vfpv4/smartmontools_7.2-r0_cortexa15hf-neon-vfpv4.ipk.
	# Configuring mailx.
	# Configuring smartmontools.
	#
	# # opkg remove smartmontools
	# Removing smartmontools (7.2) from root...
	#
	# # opkg remove mailx
	# Removing mailx (12.5-5) from root...
	#
	# # opkg clean
	#
	# # opkg update
	# Downloading https://feeds.openvision.dedyn.io/11.2/Vision/.test/all/Packages.gz.
	# Updated source 'openvision-all'.
	#
	# # opkg list-upgradable
	# enigma2-timezones - git263+6a6ce02-r0 - git266+1920ad0-r0
	#
	# # opkg upgrade
	# Upgrading enigma2-timezones (git263+6a6ce02-r0) to enigma2-timezones (git266+1920ad0) on root
	# Downloading https://feeds.openvision.dedyn.io/11.2/Vision/.test/all/enigma2-timezones_git266+1920ad0-r0_all.ipk.
	# Configuring enigma2-timezones.
	#
	def parseLine(self, line):
		# print("[Opkg] DEBUG: Line='%s'." % line)
		if not line or line.startswith(" "):  # Skip empty or continuation lines.
			return
		if self.currentCommand in (self.CMD_LIST, self.CMD_LIST_INSTALLED, self.CMD_UPGRADE_LIST):
			argv = line.split(" - ", 2)
			argc = len(argv)
			if not line.startswith("Not selecting "):
				if self.currentCommand == self.CMD_UPGRADE_LIST and self.isExcluded(argv[0]):
					self.excludeList.append(argv)
				else:
					self.fetchedList.append(argv)
					self.callCallbacks(self.EVENT_LISTITEM, argv)
			return
		try:
			argv = line.split()
			argc = len(argv)
			if line.startswith("Not selecting "):
				self.callCallbacks(self.EVENT_DESELECTED, argv[2])
			elif line.startswith("Downloading "):
				self.callCallbacks(self.EVENT_DOWNLOAD, argv[1])
			elif line.startswith("Updated source "):
				self.callCallbacks(self.EVENT_UPDATED, argv[2])
			elif line.startswith("Upgrading ") and argc == 8:
				self.callCallbacks(self.EVENT_UPVERSION, argv[1])
			elif line.startswith("Upgrading ") and argc == 5:
				self.callCallbacks(self.EVENT_UPGRADE, argv[1])
			elif line.startswith("Installing "):
				self.callCallbacks(self.EVENT_INSTALL, argv[1])
			elif line.startswith("Removing "):
				self.callCallbacks(self.EVENT_REMOVE, argv[1])
			elif line.startswith("Configuring "):
				self.callCallbacks(self.EVENT_CONFIGURING, argv[1])
			elif line.startswith("An error occurred"):
				self.callCallbacks(self.EVENT_ERROR, None)
			elif line.startswith("Failed to download"):
				self.callCallbacks(self.EVENT_ERROR, None)
			elif line.startswith("opkg_download: ERROR:"):
				self.callCallbacks(self.EVENT_ERROR, None)
			elif line.find("Configuration file '") >= 0:
				# Note: the config file update question doesn't end with a newline, so
				# if we get multiple config file update questions, the next ones
				# don't necessarily start at the beginning of a line.
				self.callCallbacks(self.EVENT_MODIFIED, line.split(" '", 3)[1][:-1])
		except IndexError as err:
			print("[Opkg] Error: Failed to parse line '%s'!  (%s)" % (line, str(err)))

	def isExcluded(self, item):
		if item.find("busybox") > -1 and not config.plugins.softwaremanager.overwriteBusyBox.value:
			exclude = True
		elif item.find("-settings-") > -1 and not config.plugins.softwaremanager.overwriteSettingsFiles.value:
			exclude = True
		elif item.find("kernel-module") > -1 and not config.plugins.softwaremanager.overwriteDriversFiles.value:
			exclude = True
		elif item.find("-softcams-") > -1 and not config.plugins.softwaremanager.overwriteEmusFiles.value:
			exclude = True
		elif item.find("-picons-") > -1 and not config.plugins.softwaremanager.overwritePiconsFiles.value:
			exclude = True
		elif item.find("%s-bootlogo" % BoxInfo.getItem("distro")) > -1 and not config.plugins.softwaremanager.overwriteBootlogoFiles.value:
			exclude = True
		elif item.find("-spinner-") > -1 and not config.plugins.softwaremanager.overwriteSpinnerFiles.value:
			exclude = True
		else:
			exclude = False
		return exclude

	def cmdFinished(self, retVal):
		self.cmd.dataAvail.remove(self.cmdData)
		self.cmd.appClosed.remove(self.cmdFinished)
		if config.crash.debugOpkg.value:
			print("[Opkg] Opkg command '%s' output:\n%s" % (self.getCommandText(self.currentCommand), self.cache))
		if self.nextCommand:
			cmd, args = self.nextCommand
			self.nextCommand = None
			self.startCmd(cmd, args)
		else:
			self.callCallbacks(self.EVENT_DONE if retVal == 0 else self.EVENT_ERROR)

	def callCallbacks(self, event, parameter=None):
		for callback in self.callbackList:
			callback(event, parameter)

	def addCallback(self, callback):
		if callback not in self.callbackList:
			self.callbackList.append(callback)
		else:
			print("[Opkg] Error: Callback '%s' already exists!" % str(callback))

	def removeCallback(self, callback):
		if callback in self.callbackList:
			self.callbackList.remove(callback)
		else:
			print("[Opkg] Error: Callback '%s' does not exist!" % str(callback))

	def getFetchedList(self):
		return self.fetchedList

	def getExcludeList(self):
		return self.excludeList

	def stop(self):
		self.cmd.kill()

	def isRunning(self):
		return self.cmd.running()

	def write(self, what):
		if what:
			if not what.endswith("\n"):  # We except unterminated commands.
				what = "%s\n" % what
			self.cmd.write(what, len(what))

	def getCommandText(self, command):
		return {
			0: "Install",
			1: "List",
			2: "Remove",
			3: "Update",
			4: "Upgrade",
			5: "Upgrade List",
			6: "List Installed",
			100: "Clean",
			101: "Update",
			102: "Set Flag",
			103: "Upgrade",
			104: "Reset Flag"
		}.get(command, "None")

	def getEventText(self, event):
		return {
			0: "Install",
			1: "Download",
			2: "Inflating",
			3: "Configuring",
			4: "Remove",
			5: "Upgrade Version",
			6: "Upgrade",
			7: "Updated",
			8: "Not Selected",
			9: "List Item",
			10: "Done",
			11: "Error",
			12: "Modified"
		}.get(event, "None")
