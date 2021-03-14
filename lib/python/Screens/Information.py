import boxbranding

from datetime import datetime
from enigma import eConsoleAppContainer, eDVBResourceManager, eGetEnigmaDebugLvl, eLabel, eTimer, getBoxBrand, getBoxType, getDesktop, getE2Rev
from glob import glob
from json import loads
from os import listdir, popen, remove
from os.path import basename, getmtime, isdir, isfile, join as pathjoin
from six import PY2, PY3
from ssl import _create_unverified_context  # For python 2.7.11 we need to bypass the certificate check
from subprocess import check_output
from time import localtime
try:
	from urllib2 import urlopen
except ImportError:
	from urllib.request import urlopen

from skin import parameters
from Components.About import about
from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.Console import Console
from Components.Harddisk import Harddisk, harddiskmanager
from Components.Network import iNetwork
from Components.NimManager import nimmanager
from Components.Pixmap import MultiPixmap
from Components.ScrollLabel import ScrollLabel
# from Components.Storage import Harddisk, storageManager
from Components.SystemInfo import SystemInfo
from Components.Sources.StaticText import StaticText
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen, ScreenSummary
from Tools.Geolocation import geolocation
from Tools.StbHardware import getFPVersion, getBoxProc, getBoxProcType, getHWSerial, getBoxRCType

INFO_COLORS = ["N", "H", "P", "V", "M"]
INFO_COLOR = {
	"B": None,
	"N": 0x00ffffff,  # Normal.
	"H": 0x00ffffff,  # Headings.
	"P": 0x00888888,  # Prompts.
	"V": 0x00888888,  # Values.
	"M": 0x00ffff00  # Messages.
}


def scaleNumber(number, suffix="B", style="Si"):  # This temporary code is borrowed from the new Storage.py!
	units = ["", "K", "M", "G", "T", "P", "E", "Z", "Y"]
	style = style.capitalize()
	if style not in ("Si", "Iec", "Jedec"):
		print("[Information] Error: Invalid number unit style '%s' specified so 'Si' is assumed!" % style)
	if style == "Si":
		units[1] = units[1].lower()
	negative = number < 0
	if negative:
		number = -number
	digits = len(str(number))
	scale = int((digits - 1) // 3)
	result = float(number) / (10 ** (scale * 3)) if style == "Si" else float(number) / (1024 ** scale)
	if negative:
		result = -result
	print("[Information] DEBUG: Number=%d, Digits=%d, Scale=%d, Factor=%d, Result=%f." % (number, digits, scale, 10 ** (scale * 3), result))
	return "%.3f %s%s%s" % (result, units[scale], ("i" if style == "Iec" and scale else ""), suffix)


class InformationBase(Screen, HelpableScreen):
	skin = [
		"""
	<screen name="Information" position="center,center" size="%d,%d">
		<widget name="information" position="%d,%d" size="e-%d,e-%d" colPosition="%d" divideChar="|" font="Regular;%d" noWrap="1" leftColAlign="left" rightColAlign="left" split="1" transparent="1" />
		<widget source="key_red" render="Label" position="%d,e-%d" size="%d,%d" backgroundColor="key_red" conditional="key_red" font="Regular;%d" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="%d,e-%d" size="%d,%d" backgroundColor="key_green" conditional="key_green" font="Regular;%d" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="%d,e-%d" size="%d,%d" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;%d" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="%d,e-%d" size="%d,%d" backgroundColor="key_blue" conditional="key_blue" font="Regular;%d" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-%d,e-%d" size="%d,%d" backgroundColor="key_back" conditional="key_help" font="Regular;%d" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="lab1" render="Label" position="0,0" size="0,0" conditional="lab1" font="Regular;22" transparent="1" />
		<widget source="lab2" render="Label" position="0,0" size="0,0" conditional="lab2" font="Regular;18" transparent="1" />
		<widget source="lab3" render="Label" position="0,0" size="0,0" conditional="lab3" font="Regular;18" transparent="1" />
		<widget source="lab4" render="Label" position="0,0" size="0,0" conditional="lab4" font="Regular;18" transparent="1" />
		<widget source="lab5" render="Label" position="0,0" size="0,0" conditional="lab5" font="Regular;18" transparent="1" />
		<widget source="lab6" render="Label" position="0,0" size="0,0" conditional="lab6" font="Regular;18" transparent="1" />
	</screen>""",
		900, 560,  # screen
		10, 10, 20, 60, 280, 20,  # information
		10, 50, 180, 40, 20,  # key_red
		200, 50, 180, 40, 20,  # key_green
		390, 50, 180, 40, 20,  # key_yellow
		580, 50, 180, 40, 20,  # key_blue
		90, 50, 80, 40, 20  # key_help
	]

	def __init__(self, session):
		Screen.__init__(self, session, mandatoryWidgets=["information"])
		HelpableScreen.__init__(self)
		self.skinName = ["Information"]
		self["information"] = ScrollLabel()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Refresh"))
		self["lab1"] = StaticText(_("OpenVision"))
		self["lab2"] = StaticText(_("Let's define enigma2 once more"))
		self["lab3"] = StaticText(_("Report problems to:"))
		self["lab4"] = StaticText(_("https://openvision.tech"))
		self["lab5"] = StaticText(_("Sources are available at:"))
		self["lab6"] = StaticText(_("https://github.com/OpenVisionE2"))
		self["actions"] = HelpableActionMap(self, ["CancelSaveActions", "OkActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Close the screen")),
			"close": (self.closeRecursive, _("Close the screen and exit all menus")),
			"save": (self.refreshInformation, _("Refresh the screen")),
			"ok": (self.refreshInformation, _("Refresh the screen")),
			"top": (self["information"].moveTop, _("Move to first line / screen")),
			"pageUp": (self["information"].pageUp, _("Move up a screen")),
			"up": (self["information"].pageUp, _("Move up a screen")),
			"down": (self["information"].pageDown, _("Move down a screen")),
			"pageDown": (self["information"].pageDown, _("Move down a screen")),
			"bottom": (self["information"].moveBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Common Information Actions"))
		colors = parameters.get("InformationColors", (0x00ffffff, 0x00ffffff, 0x00888888, 0x00888888, 0x00ffff00))
		if len(colors) == len(INFO_COLORS):
			for index in range(len(colors)):
				INFO_COLOR[INFO_COLORS[index]] = colors[index]
		else:
			print("[Information] Warning: %d colors are defined in the skin when %d were expected!" % (len(colors), len(INFO_COLORS)))
		self["information"].setText(_("Loading information, please wait..."))
		self.onInformationUpdated = [self.displayInformation]
		self.onLayoutFinish.append(self.displayInformation)
		self.informationTimer = eTimer()
		self.informationTimer.callback.append(self.fetchInformation)
		self.informationTimer.start(25)

	def keyCancel(self):
		self.close()

	def closeRecursive(self):
		self.close(True)

	def informationWindowClosed(self, *retVal):
		if retVal and retVal[0]:
			self.close(True)

	def fetchInformation(self):
		self.informationTimer.stop()
		for callback in self.onInformationUpdated:
			callback()

	def refreshInformation(self):
		self.informationTimer.start(25)
		for callback in self.onInformationUpdated:
			callback()

	def displayInformation(self):
		pass

	def getSummaryInformation(self):
		pass

	def createSummary(self):
		return InformationSummary


def formatLine(style, left, right=None):
	typeLen = len(style)
	leftStartColor = "" if typeLen > 0 and style[0] == "B" else "\c%08x" % (INFO_COLOR.get(style[0], "P") if typeLen > 0 else INFO_COLOR["P"])
	leftEndColor = "" if leftStartColor == "" else "\c%08x" % INFO_COLOR["N"]
	leftIndent = "    " * int(style[1]) if typeLen > 1 and style[1].isdigit() else ""
	rightStartColor = "" if typeLen > 2 and style[2] == "B" else "\c%08x" % (INFO_COLOR.get(style[2], "V") if typeLen > 2 else INFO_COLOR["V"])
	rightEndColor = "" if rightStartColor == "" else "\c%08x" % INFO_COLOR["N"]
	rightIndent = "    " * int(style[3]) if typeLen > 3 and style[3].isdigit() else ""
	if right is None:
		colon = "" if typeLen > 0 and style[0] in ("M", "P", "V") else ":"
		return "%s%s%s%s%s" % (leftIndent, leftStartColor, left, colon, leftEndColor)
	return "%s%s%s:%s|%s%s%s%s" % (leftIndent, leftStartColor, left, leftEndColor, rightIndent, rightStartColor, right, rightEndColor)


class BenchmarkInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Benchmark Information"))
		self.skinName.insert(0, "BenchmarkInformation")
		self.benchmark = _("Calculating benchmark...")

	def fetchInformation(self):
		self.informationTimer.stop()
		self.benchmark = about.getCPUBenchmark().replace("\n", "\n|")
		for callback in self.onInformationUpdated:
			callback()

	def refreshInformation(self):
		self.benchmark = _("Calculating benchmark...")
		self.informationTimer.start(25)
		for callback in self.onInformationUpdated:
			callback()

	def displayInformation(self):
		info = []
		info.append(formatLine("H", "%s %s %s" % (_("Benchmark for"), SystemInfo["MachineBrand"], SystemInfo["MachineModel"])))
		info.append("")
		info.append(formatLine("P1", _("CPU benchmark"), self.benchmark))
		self["information"].setText("\n".join(info).encode("UTF-8", "ignore") if PY2 else "\n".join(info))

	def getSummaryInformation(self):
		return "Benchmark Information"


class BoxBrandingInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("BoxBranding Information"))
		self.skinName.insert(0, "BoxBrandingInformation")

	def displayInformation(self):
		info = []
		info.append(formatLine("H", "%s %s %s" % (_("BoxBranding information for"), SystemInfo["MachineBrand"], SystemInfo["MachineModel"])))
		info.append("")
		for method in sorted(boxbranding.__dict__.keys()):
			if callable(getattr(boxbranding, method)):
				info.append(formatLine("P1", method, getattr(boxbranding, method)()))
		self["information"].setText("\n".join(info).encode("UTF-8", "ignore") if PY2 else "\n".join(info))

	def getSummaryInformation(self):
		return "Build Information"


class CommitLogInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.baseTitle = _("Commit Information")
		self.setTitle(self.baseTitle)
		self.skinName.insert(0, "CommitLogInformation")
		self["commitActions"] = HelpableActionMap(self, ["NavigationActions"], {
			"left": (self.previousCommit, _("Display previous commit log")),
			"right": (self.nextCommit, _("Display next commit log")),
		}, prio=0, description=_("Commit Information Actions"))
		try:
			branch = "?sha=" + "-".join(about.getEnigmaVersionString().split("-")[3:])
		except Exception as err:
			branch = ""
		oeGitUrl = "https://api.github.com/repos/OpenVisionE2/openvision-%s/commits" % ("development-platform" if boxbranding.getVisionVersion().startswith("10") else "oe")
		self.projects = [
			("OpenVision Enigma2", "https://api.github.com/repos/OpenVisionE2/enigma2-openvision/commits%s" % branch),
			("OpenVision OE-Alliance", oeGitUrl),
			("Enigma2 Plugins", "https://api.github.com/repos/OpenVisionE2/enigma2-plugins/commits"),
			("OE-Alliance Plugins", "https://api.github.com/repos/OpenVisionE2/alliance-plugins/commits"),
			("OpenWebIF", "https://api.github.com/repos/OpenVisionE2/OpenWebif/commits"),
			("OpenVision Core Plugin", "https://api.github.com/repos/OpenVisionE2/openvision-core-plugin/commits"),
			("Backup Suite Plugin", "https://api.github.com/repos/OpenVisionE2/BackupSuite/commits"),
			("OctEtFHD Skin", "https://api.github.com/repos/OpenVisionE2/OctEtFHD-skin/commits")
		]
		self.project = 0
		self.cachedProjects = {}
		self.log = _("Retrieving %s commit log, please wait...") % self.projects[self.project][0]

	def previousCommit(self):
		self.project = self.project == 0 and len(self.projects) - 1 or self.project - 1
		self.log = _("Retrieving %s commit log, please wait...") % self.projects[self.project][0]
		self.informationTimer.start(25)

	def nextCommit(self):
		self.project = self.project != len(self.projects) - 1 and self.project + 1 or 0
		self.log = _("Retrieving %s commit log, please wait...") % self.projects[self.project][0]
		self.informationTimer.start(25)

	def fetchInformation(self):
		# Limit the number of fetches per minute!
		self.informationTimer.stop()
		name = self.projects[self.project][0]
		url = self.projects[self.project][1]
		log = []
		try:
			try:
				rawLog = loads(urlopen(url, timeout=10, context=_create_unverified_context()).read())
			except Exception as err:
				rawLog = loads(urlopen(url, timeout=10).read())
			for data in rawLog:
				date = datetime.strptime(data["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%SZ").strftime("%x %X")
				creator = data["commit"]["author"]["name"]
				title = data["commit"]["message"]
				if log:
					log.append("")
				log.append("%s  %s" % (date, creator))
				log.append(title)
			if log:
				log = "\n".join(log).encode("UTF-8", "ignore") if PY2 else "\n".join(log)
				self.cachedProjects[name] = log
			else:
				log = _("The %s commit log contains no information.") % name
		except Exception as err:
			log.append(_("Error '%s' encountered retrieving the %s commit logs!") % (str(err), name))
			log.append("")
			log.append(_("The %s commit logs can't be retrieved, please try again later.") % name)
			log.append("")
			log.append(_("Access to the %s commit logs requires an internet connection.") % name)
			log = "\n".join(log)
		self.log = log
		for callback in self.onInformationUpdated:
			callback()

	def refreshInformation(self):
		# Limit the number of fetches per minute!
		self.cachedProjects = {}
		self.log = _("Retrieving %s commit log, please wait...") % self.projects[self.project][0]
		self.informationTimer.start(25)
		for callback in self.onInformationUpdated:
			callback()

	def displayInformation(self):
		name = self.projects[self.project][1]
		self.setTitle("%s - %s" % (self.baseTitle, name))
		if name in self.cachedProjects:
			self["information"].setText(self.cachedProjects[name])
		elif self.log:
			self["information"].setText(self.log)
		else:
			self["information"].setText(_("The %s commit log contains no information.") % name)


class GeolocationInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Geolocation Information"))
		self.skinName.insert(0, "GeolocationInformation")

	def displayInformation(self):
		info = []
		geolocationData = geolocation.getGeolocationData(fields="continent,country,regionName,city,lat,lon,timezone,currency,isp,org,mobile,proxy,query", useCache=False)
		if geolocationData.get("status", None) == "success":
			info.append(formatLine("H", _("Location information")))
			info.append("")
			continent = geolocationData.get("continent", None)
			if continent:
				info.append(formatLine("P1", _("Continent"), continent))
			country = geolocationData.get("country", None)
			if country:
				info.append(formatLine("P1", _("Country"), country))
			state = geolocationData.get("regionName", None)
			if state:
				info.append(formatLine("P1", _("State"), state))
			city = geolocationData.get("city", None)
			if city:
				info.append(formatLine("P1", _("City"), city))
			latitude = geolocationData.get("lat", None)
			if latitude:
				info.append(formatLine("P1", _("Latitude"), latitude))
			longitude = geolocationData.get("lon", None)
			if longitude:
				info.append(formatLine("P1", _("Longitude"), longitude))
			info.append("")
			info.append(formatLine("H", _("Local information")))
			info.append("")
			timezone = geolocationData.get("timezone", None)
			if timezone:
				info.append(formatLine("P1", _("Timezone"), timezone))
			currency = geolocationData.get("currency", None)
			if currency:
				info.append(formatLine("P1", _("Currency"), currency))
			info.append("")
			info.append(formatLine("H", _("Connection information")))
			info.append("")
			isp = geolocationData.get("isp", None)
			if isp:
				ispOrg = geolocationData.get("org", None)
				if ispOrg:
					info.append(formatLine("P1", _("ISP"), "%s  (%s)" % (isp, ispOrg)))
				else:
					info.append(formatLine("P1", _("ISP"), isp))
			mobile = geolocationData.get("mobile", None)
			info.append(formatLine("P1", _("Mobile connection"), (_("Yes") if mobile else _("No"))))
			proxy = geolocationData.get("proxy", False)
			info.append(formatLine("P1", _("Proxy detected"), (_("Yes") if proxy else _("No"))))
			publicIp = geolocationData.get("query", None)
			if publicIp:
				info.append(formatLine("P1", _("Public IP"), publicIp))
		else:
			info.append(_("Geolocation information cannot be retrieved, please try again later."))
			info.append("")
			info.append(_("Access to geolocation information requires an internet connection."))
		self["information"].setText("\n".join(info).encode("UTF-8", "ignore") if PY2 else "\n".join(info))

	def getSummaryInformation(self):
		return "Geolocation Information"


class ImageInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("OpenVision Information"))
		self.skinName.insert(0, "ImageInformation")
		self["key_yellow"] = StaticText(_("Commit Logs"))
		self["key_blue"] = StaticText(_("Translation"))
		self["receiverActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.showCommitLogs, _("Show latest commit log information")),
			"blue": (self.showTranslation, _("Show translation information"))
		}, prio=0, description=_("OpenVision Information Actions"))
		self.copyright = str("\xc2\xb0")
		self.resolutions = {
			480: _("NTSC"),
			576: _("PAL"),
			720: _("HD"),
			1080: _("FHD"),
			2160: _("4K"),
			4320: _("8K"),
			8640: _("16K")
		}

	def showCommitLogs(self):
		self.session.openWithCallback(self.informationWindowClosed, CommitLogInformation)

	def showTranslation(self):
		self.session.openWithCallback(self.informationWindowClosed, TranslationInformation)

	def displayInformation(self):
		info = []
		info.append(formatLine("M", _("Copyright %s 2018-%s Team OpenVision") % (u"\u00A9", localtime()[0])))
		info.append("")
		info.append(formatLine("M", _("OpenVision is an open source project with no commercial funding.")))
		info.append(formatLine("M", _("The team relies on donations to fund OpenVision development.")))
		info.append(formatLine("M", _("If you would like to support us then please consider donating.")))
		info.append("")
		info.append(formatLine("M", _("Donate at %s") % "https://forum.openvision.tech/app.php/donate"))
		info.append("")
		if config.misc.OVupdatecheck.value:
			try:
				if boxbranding.getVisionVersion().startswith("10"):
					ovUrl = "https://raw.githubusercontent.com/OpenVisionE2/openvision-development-platform/develop/meta-openvision/conf/distro/revision.conf"
				else:
					ovUrl = "https://raw.githubusercontent.com/OpenVisionE2/openvision-oe/develop/meta-openvision/conf/distro/revision.conf"
				ovResponse = urlopen(ovUrl)
				if PY2:
					ovRevision = ovResponse.read()
					ovRevisionUpdate = int(filter(str.isdigit, ovRevision))
				else:
					ovResponse = urlopen(ovUrl)
					ovRevision = ovResponse.read().decode()
					ovRevisionUpdate = ovRevision.split("r")[1][:3]
			except Exception as err:
				ovRevisionUpdate = _("Requires internet connection")
		else:
			ovRevisionUpdate = _("Disabled in configuration")
		visionVersion = open("/etc/openvision/visionversion", "r").read().strip() if isfile("/etc/openvision/visionversion") else boxbranding.getVisionVersion()
		info.append(formatLine("P1", _("OpenVision version"), visionVersion))
		visionRevision = open("/etc/openvision/visionrevision", "r").read().strip() if isfile("/etc/openvision/visionrevision") else boxbranding.getVisionRevision()
		info.append(formatLine("P1", _("OpenVision revision"), visionRevision))
		info.append(formatLine("P1", _("Latest revision on github"), str(ovRevisionUpdate)))
		if isfile("/etc/openvision/visionlanguage"):
			visionLanguage = open("/etc/openvision/visionlanguage", "r").read().strip()
			info.append(formatLine("P1", _("OpenVision language"), visionLanguage))
		info.append(formatLine("P1", _("OpenVision module"), about.getVisionModule()))
		if isfile("/etc/openvision/multiboot"):
			multibootFlag = open("/etc/openvision/multiboot", "r").read().strip()
			multibootFlag = _("Yes") if multibootFlag == "1" else _("No")
		else:
			multibootFlag = _("Yes")
		info.append(formatLine("P1", _("Soft multiboot"), multibootFlag))
		info.append(formatLine("P1", _("Flash type"), about.getFlashType()))
		xResolution = getDesktop(0).size().width()
		yResolution = getDesktop(0).size().height()
		info.append(formatLine("P1", _("Skin & Resolution"), "%s  [%s  (%s x %s)]") % (config.skin.primary_skin.value.split('/')[0], self.resolutions.get(yResolution, "Unknown"), xResolution, yResolution))
		info.append("")
		info.append(formatLine("H", _("Enigma2 information")))
		info.append("")
		# [WanWizard] Removed until we find a reliable way to determine the installation date
		# info.append(_("Installed:|%s") % about.getFlashDateString())
		enigmaVersion = about.getEnigmaVersionString()
		enigmaVersion = enigmaVersion.rsplit("-", enigmaVersion.count("-") - 2)
		if len(enigmaVersion) == 3:
		 	enigmaVersion = "%s (%s-%s)" % (enigmaVersion[0], enigmaVersion[2], enigmaVersion[1].capitalize())
		else:
			enigmaVersion = "%s (%s)" % (enigmaVersion[0], enigmaVersion[1].capitalize())
		info.append(formatLine("P1", _("Enigma2 version"), enigmaVersion))
		info.append(formatLine("P1", _("Enigma2 revision"), getE2Rev()))
		info.append(formatLine("P1", _("GitHub commit"), getE2Rev().split("+")[1]))
		info.append(formatLine("P1", _("Last update"), about.getUpdateDateString()))
		info.append(formatLine("P1", _("Enigma2 (re)starts"), config.misc.startCounter.value))
		info.append(formatLine("P1", _("Enigma2 debug level"), eGetEnigmaDebugLvl()))
		if isfile("/etc/openvision/mediaservice"):
			mediaService = open("/etc/openvision/mediaservice", "r").read().strip()
			info.append(formatLine("P1", _("Media service"), mediaService.replace("enigma2-plugin-systemplugins-", "")))
		info.append("")
		info.append(formatLine("H", _("Build information")))
		info.append("")
		info.append(formatLine("P1", _("Image"), boxbranding.getImageDistro()))
		info.append(formatLine("P1", _("Image build/branch"), boxbranding.getImageBuild()))
		info.append(formatLine("P1", _("Image build date"), about.getBuildDateString()))
		info.append(formatLine("P1", _("Image architecture"), boxbranding.getImageArch()))
		if boxbranding.getImageFolder():
			info.append(formatLine("P1", _("Image folder"), boxbranding.getImageFolder()))
		if boxbranding.getImageFileSystem():
			info.append(formatLine("P1", _("Image file system"), boxbranding.getImageFileSystem().strip()))
		info.append(formatLine("P1", _("Feed URL"), boxbranding.getFeedsUrl()))
		info.append(formatLine("P1", _("Compiled by"), boxbranding.getDeveloperName()))
		info.append("")
		info.append(formatLine("H", _("Software information")))
		info.append("")
		info.append(formatLine("P1", _("GStreamer version"), about.getGStreamerVersionString().replace("GStreamer", "")))
		info.append(formatLine("P1", _("FFmpeg version"), about.getFFmpegVersionString()))
		info.append(formatLine("P1", _("Python version"), about.getPythonVersionString()))
		if isfile("/proc/sys/kernel/random/boot_id"):
			bootId = open("/proc/sys/kernel/random/boot_id", "r").read().strip()
			info.append(formatLine("P1", _("Boot ID"), bootId))
		if isfile("/proc/sys/kernel/random/uuid"):
			uuId = open("/proc/sys/kernel/random/uuid", "r").read().strip()
			info.append(formatLine("P1", _("UUID"), uuId))
		info.append("")
		info.append(formatLine("H", _("Boot information")))
		info.append("")
		if boxbranding.getMachineMtdBoot():
			info.append(formatLine("P1", _("MTD boot"), boxbranding.getMachineMtdBoot()))
		if boxbranding.getMachineMtdRoot():
			info.append(formatLine("P1", _("MTD root"), boxbranding.getMachineMtdRoot()))
		if boxbranding.getMachineMtdKernel():
			info.append(formatLine("P1", _("MTD kernel"), boxbranding.getMachineMtdKernel()))
		if boxbranding.getMachineRootFile():
			info.append(formatLine("P1", _("Root file"), boxbranding.getMachineRootFile()))
		if boxbranding.getMachineKernelFile():
			info.append(formatLine("P1", _("Kernel file"), boxbranding.getMachineKernelFile()))
		if boxbranding.getMachineMKUBIFS():
			info.append(formatLine("P1", _("MKUBIFS"), boxbranding.getMachineMKUBIFS()))
		if boxbranding.getMachineUBINIZE():
			info.append(formatLine("P1", _("UBINIZE"), boxbranding.getMachineUBINIZE()))
		if SystemInfo["HiSilicon"]:
			info.append("")
			info.append(formatLine("H", _("HiSilicon specific information")))
			info.append("")
			packageList = check_output(["/usr/bin/opkg", "list-installed"])
			packageList = packageList.split("\n")
			revision = self.findPackageRevision("grab", packageList)
			if revision and revision != "r0":
				info.append(formatLine("P1", _("Grab"), revision))
			revision = self.findPackageRevision("hihalt", packageList)
			if revision:
				info.append(formatLine("P1", _("Halt"), revision))
			revision = self.findPackageRevision("libs", packageList)
			if revision:
				info.append(formatLine("P1", _("Libs"), revision))
			revision = self.findPackageRevision("partitions", packageList)
			if revision:
				info.append(formatLine("P1", _("Partitions"), revision))
			revision = self.findPackageRevision("reader", packageList)
			if revision:
				info.append(formatLine("P1", _("Reader"), revision))
			revision = self.findPackageRevision("showiframe", packageList)
			if revision:
				info.append(formatLine("P1", _("Showiframe"), revision))
		self["information"].setText("\n".join(info).encode("UTF-8", "ignore") if PY2 else "\n".join(info))

	def findPackageRevision(self, package, packageList):
		revision = None
		data = [x for x in packageList if "-%s" % package in x]
		if data:
			data = data[0].split("-")
			if len(data) >= 4:
				revision = data[3]
		return revision

	def getSummaryInformation(self):
		return "OpenVision Information"


class MemoryInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Memory Information"))
		self.skinName.insert(0, "MemoryInformation")
		self["clearActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.clearMemoryInformation, _("Clear the virtual memory caches"))
		}, prio=0, description=_("Memory Information Actions"))
		self["key_yellow"] = StaticText(_("Clear"))
		self.storageUnits = {
			"k": "kB",
			"M": "MB",
			"G": "GB",
			"T": "TB"
		}
		self.console = Console()
		self.flashTotal = ["-", ""]
		self.flashFree = ["-", ""]

	def fetchInformation(self):
		self.informationTimer.stop()
		self.console.ePopen("df -mh / | grep -v '^Filesystem'", self.flashInformationFinished)
		for callback in self.onInformationUpdated:
			callback()

	def flashInformationFinished(self, result, retVal, extraArgs=None):
		flash = result.strip().split()
		self.flashTotal = [flash[1][:-1], self.storageUnits.get(flash[1][-1:], "")]
		self.flashFree = [flash[3][:-1], self.storageUnits.get(flash[3][-1:], "")]
		for callback in self.onInformationUpdated:
			callback()

	def displayInformation(self):
		info = []
		memInfo = file("/proc/meminfo").readlines()
		info.append(formatLine("H", _("RAM (Summary)")))
		info.append("")
		for line in memInfo:
			key, value, units = [x for x in line.split()]
			if key == "MemTotal:":
				info.append(formatLine("P1", _("Total memory"), "%s %s" % (value, units)))
			if key == "MemFree:":
				info.append(formatLine("P1", _("Free memory"), "%s %s" % (value, units)))
			if key == "Buffers:":
				info.append(formatLine("P1", _("Buffers"), "%s %s" % (value, units)))
			if key == "Cached:":
				info.append(formatLine("P1", _("Cached"), "%s %s" % (value, units)))
			if key == "SwapTotal:":
				info.append(formatLine("P1", _("Total swap"), "%s %s" % (value, units)))
			if key == "SwapFree:":
				info.append(formatLine("P1", _("Free swap"), "%s %s" % (value, units)))
		info.append("")
		info.append(formatLine("H", _("FLASH")))
		info.append("")
		info.append(formatLine("P1", _("Total flash"), "%s %s" % (self.flashTotal[0], self.flashTotal[1])))
		info.append(formatLine("P1", _("Free flash"), "%s %s" % (self.flashFree[0], self.flashFree[1])))
		info.append("")
		info.append(formatLine("H", _("RAM (Details)")))
		info.append("")
		for line in memInfo:
			key, value, units = [x for x in line.split()]
			info.append(formatLine("P1", key[:-1], "%s %s" % (value, units)))
		info.append("")
		info.append(formatLine("P1", _("The detailed information is intended for developers only.")))
		info.append(formatLine("P1", _("Please don't panic if you see values that look suspicious.")))
		self["information"].setText("\n".join(info).encode("UTF-8", "ignore") if PY2 else "\n".join(info))

	def clearMemoryInformation(self):
		eConsoleAppContainer().execute(*["/bin/sync", "/bin/sync"])
		open("/proc/sys/vm/drop_caches", "w").write("3")
		self.informationTimer.start(25)
		for callback in self.onInformationUpdated:
			callback()

	def getSummaryInformation(self):
		return "Memory Information Data"


class MultiBootInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("MultiBoot Information"))
		self.skinName.insert(0, "MemoryInformation")

	def fetchInformation(self):
		self.informationTimer.stop()
		for callback in self.onInformationUpdated:
			callback()

	def displayInformation(self):
		info = []
		info.append(_("This screen is not yet available."))
		self["information"].setText("\n".join(info).encode("UTF-8", "ignore") if PY2 else "\n".join(info))

	def getSummaryInformation(self):
		return "MultiBoot Information Data"


class NetworkInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Network Information"))
		self.skinName = ["NetworkInformation", "WlanStatus"]
		self["key_yellow"] = StaticText(_("WAN Geolocation"))
		self["geolocationActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.useGeolocation, _("Use geolocation to get WAN information")),
		}, prio=0, description=_("Network Information Actions"))
		self.console = Console()
		self.interfaceData = {}
		self.geolocationData = []
		self.ifconfigAttributes = {
			"Link encap": "encapsulation",
			"HWaddr": "mac",
			"inet addr": "addr",
			"Bcast": "brdaddr",
			"Mask": "nmask",
			"inet6 addr": "addr6",
			"Scope": "scope",
			"MTU": "mtu",
			"Metric": "metric",
			"RX packets": "rxPackets",
			"rxerrors": "rxErrors",
			"rxdropped": "rxDropped",
			"rxoverruns": "rxOverruns",
			"rxframe": "rxFrame",
			"TX packets": "txPackets",
			"txerrors": "txErrors",
			"txdropped": "txDropped",
			"txoverruns": "txOverruns",
			"collisions": "txCollisions",
			"txqueuelen": "txQueueLen",
			"RX bytes": "rxBytes",
			"TX bytes": "txBytes"
		}
		self.iwconfigAttributes = {
			"interface": "interface",
			"standard": "standard",
			"ESSID": "ssid",
			"Mode": "mode",
			"Frequency": "frequency",
			"Access Point": "accessPoint",
			"Bit Rate": "bitrate",
			"Tx-Power": "transmitPower",
			"Retry short limit": "retryLimit",
			"RTS thr": "rtsThrottle",
			"Fragment thr": "fragThrottle",
			"Encryption key": "encryption",
			"Power Management": "powerManagement",
			"Link Quality": "signalQuality",
			"Signal level": "signalStrength",
			"Rx invalid nwid": "rxInvalidNwid",
			"Rx invalid crypt": "rxInvalidCrypt",
			"Rx invalid frag": "rxInvalidFrag",
			"Tx excessive retries": "txExcessiveReties",
			"Invalid misc": "invalidMisc",
			"Missed beacon": "missedBeacon"
		}
		self.ethtoolAttributes = {
			"Speed": "speed",
			"Duplex": "duplex",
			"Transceiver": "transceiver",
			"Auto-negotiation": "autoNegotiation",
			"Link detected": "link"
		}

	def useGeolocation(self):
		geolocationData = geolocation.getGeolocationData(fields="isp,org,mobile,proxy,query", useCache=False)
		info = []
		if geolocationData.get("status", None) == "success":
			info.append("")
			info.append(formatLine("H", _("WAN connection information")))
			isp = geolocationData.get("isp", None)
			if isp:
				ispOrg = geolocationData.get("org", None)
				if ispOrg:
					info.append(formatLine("P1", _("ISP"), "%s  (%s)" % (isp, ispOrg)))
				else:
					info.append(formatLine("P1", _("ISP"), isp))
			mobile = geolocationData.get("mobile", None)
			info.append(formatLine("P1", _("Mobile connection"), (_("Yes") if mobile else _("No"))))
			proxy = geolocationData.get("proxy", False)
			info.append(formatLine("P1", _("Proxy detected"), (_("Yes") if proxy else _("No"))))
			publicIp = geolocationData.get("query", None)
			if publicIp:
				info.append(formatLine("P1", _("Public IP"), publicIp))
		else:
			info.append(_("Geolocation information cannot be retrieved, please try again later."))
			info.append("")
			info.append(_("Access to geolocation information requires an internet connection."))
		self.geolocationData =  info
		for callback in self.onInformationUpdated:
			callback()

	def fetchInformation(self):
		self.informationTimer.stop()
		for interface in sorted([x for x in listdir("/sys/class/net") if not self.isBlacklisted(x)]):
			self.interfaceData[interface] = {}
			self.console.ePopen(("/sbin/ifconfig", "/sbin/ifconfig", interface), self.ifconfigInfoFinished, extra_args=interface)
			if iNetwork.isWirelessInterface(interface):
				self.console.ePopen(("/sbin/iwconfig", "/sbin/iwconfig", interface), self.iwconfigInfoFinished, extra_args=interface)
			else:
				self.console.ePopen(("/usr/sbin/ethtool", "/usr/sbin/ethtool", interface), self.ethtoolInfoFinished, extra_args=interface)
		for callback in self.onInformationUpdated:
			callback()

	def isBlacklisted(self, interface):
		for type in ("lo", "wifi", "wmaster", "sit", "tun", "sys", "p2p"):
			if interface.startswith(type):
				return True
		return False

	def ifconfigInfoFinished(self, result, retVal, extraArgs):  # This temporary code borrowed and adapted from the new but unreleased Network.py!
		if retVal == 0:
			capture = False
			data = ""
			for line in result.split("\n"):
				if line.startswith("%s " % extraArgs):
					capture = True
					if "HWaddr " in line:
						line = line.replace("HWaddr ", "HWaddr:")
					data += line
					continue
				if capture and line.startswith(" "):
					if " Scope:" in line:
						line = line.replace(" Scope:", " ")
					elif "X packets:" in line:
						pos = line.index("X packets:")
						direction = line[pos - 1:pos].lower()
						line = "%s%s" % (line[0:pos + 10], line[pos + 10:].replace(" ", "  %sx" % direction))
					elif " txqueuelen" in line:
						line = line.replace(" txqueuelen:", "  txqueuelen:")
					data += line
					continue
				if line == "":
					break
			data = list(filter(None, [x.strip().replace("=", ":", 1) for x in data.split("  ")]))
			data[0] = "interface:%s" % data[0]
			# print("[Network] DEBUG: Raw network data %s." % data)
			for item in data:
				if ":" not in item:
					flags = item.split()
					self.interfaceData[extraArgs]["up"] = True if "UP" in flags else False
					self.interfaceData[extraArgs]["status"] = "up" if "UP" in flags else "down"  # Legacy status flag.
					self.interfaceData[extraArgs]["running"] = True if "RUNNING" in flags else False
					self.interfaceData[extraArgs]["broadcast"] = True if "BROADCAST" in flags else False
					self.interfaceData[extraArgs]["multicast"] = True if "MULTICAST" in flags else False
					continue
				key, value = item.split(":", 1)
				key = self.ifconfigAttributes.get(key, None)
				if key:
					value = value.strip()
					if value.startswith("\""):
						value = value[1:-1]
					if key == "addr6":
						if key not in self.interfaceData[extraArgs]:
							self.interfaceData[extraArgs][key] = []
						self.interfaceData[extraArgs][key].append(value)
					else:
						self.interfaceData[extraArgs][key] = value
		for callback in self.onInformationUpdated:
			callback()

	def iwconfigInfoFinished(self, result, retVal, extraArgs):  # This temporary code borrowed and adapted from the new but unreleased Network.py!
		if retVal == 0:
			capture = False
			data = ""
			for line in result.split("\n"):
				if line.startswith("%s " % extraArgs):
					capture = True
					data += line
					continue
				if capture and line.startswith(" "):
					data += line
					continue
				if line == "":
					break
			data = list(filter(None, [x.strip().replace("=", ":", 1) for x in data.split("  ")]))
			data[0] = "interface:%s" % data[0]
			data[1] = "standard:%s" % data[1]
			for item in data:
				if ":" not in item:
					continue
				key, value = item.split(":", 1)
				key = self.iwconfigAttributes.get(key, None)
				if key:
					value = value.strip()
					if value.startswith("\""):
						value = value[1:-1]
					self.interfaceData[extraArgs][key] = value
			if "encryption" in self.interfaceData[extraArgs]:
				self.interfaceData[extraArgs]["encryption"] = _("Disabled or WPA/WPA2") if self.interfaceData[extraArgs]["encryption"] == "off" else _("Enabled")
			if "standard" in self.interfaceData[extraArgs] and "no wireless extensions" in self.interfaceData[extraArgs]["standard"]:
				del self.interfaceData[extraArgs]["standard"]
				self.interfaceData[extraArgs]["wireless"] = False
			else:
				self.interfaceData[extraArgs]["wireless"] = True
			if "ssid" in self.interfaceData[extraArgs]:
				self.interfaceData[extraArgs]["SSID"] = self.interfaceData[extraArgs]["ssid"]
		for callback in self.onInformationUpdated:
			callback()

	def ethtoolInfoFinished(self, result, retVal, extraArgs):  # This temporary code borrowed and adapted from the new but unreleased Network.py!
		if retVal == 0:
			for line in result.split("\n"):
				if "Speed:" in line:
					self.interfaceData[extraArgs]["speed"] = line.split(":")[1][:-4].strip()
				if "Duplex:" in line:
					self.interfaceData[extraArgs]["duplex"] = _(line.split(":")[1].strip().capitalize())
				if "Transceiver:" in line:
					self.interfaceData[extraArgs]["transeiver"] = _(line.split(":")[1].strip().capitalize())
				if "Auto-negotiation:" in line:
					self.interfaceData[extraArgs]["autoNegotiation"] = line.split(":")[1].strip().lower() == "on"
				if "Link detected:" in line:
					self.interfaceData[extraArgs]["link"] = line.split(":")[1].strip().lower() == "yes"
		for callback in self.onInformationUpdated:
			callback()

	def displayInformation(self):
		info = []
		hostname = open("/proc/sys/kernel/hostname").read().strip()
		info.append(formatLine("H0H", _("Hostname"), hostname))
		for interface in sorted(list(self.interfaceData.keys())):
			info.append("")
			info.append(formatLine("H", _("Interface '%s'") % interface, iNetwork.getFriendlyAdapterName(interface)))
			if "up" in self.interfaceData[interface]:
				info.append(formatLine("P1", _("Status"), (_("Up") if self.interfaceData[interface]["up"] else _("Down"))))
				if self.interfaceData[interface]["up"]:
					if "addr" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("IP address"), self.interfaceData[interface]["addr"]))
					if "nmask" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Netmask"), self.interfaceData[interface]["nmask"]))
					if "brdaddr" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Broadcast address"), self.interfaceData[interface]["brdaddr"]))
					if "addr6" in self.interfaceData[interface]:
						for addr6 in self.interfaceData[interface]["addr6"]:
							addr, scope = addr6.split()
							info.append(formatLine("P1", _("IPv6 address"), _("%s  -  Scope: %s") % (addr, scope)))
					if "mac" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("MAC address"), self.interfaceData[interface]["mac"]))
					if "speed" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Speed"), "%s Mbps" % self.interfaceData[interface]["speed"]))
					if "duplex" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Duplex"), self.interfaceData[interface]["duplex"]))
					if "mtu" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("MTU"), self.interfaceData[interface]["mtu"]))
					if "link" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Link detected"), (_("Yes") if self.interfaceData[interface]["link"] else _("No"))))
					if "ssid" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("SSID"), self.interfaceData[interface]["ssid"]))
					if "standard" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Standard"), self.interfaceData[interface]["standard"]))
					if "encryption" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Encryption"), self.interfaceData[interface]["encryption"]))
					if "frequency" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Frequency"), self.interfaceData[interface]["frequency"]))
					if "accessPoint" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Access point"), self.interfaceData[interface]["accessPoint"]))
					if "bitrate" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Bit rate"), self.interfaceData[interface]["bitrate"]))
					if "signalQuality" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Signal quality"), self.interfaceData[interface]["signalQuality"]))
					if "signalStrength" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Signal strength"), self.interfaceData[interface]["signalStrength"]))
			if "rxBytes" in self.interfaceData[interface] or "txBytes" in self.interfaceData[interface]:
				info.append("")
				info.append(formatLine("P1", _("Bytes received"), self.interfaceData[interface]["rxBytes"]))
				info.append(formatLine("P1", _("Bytes sent"), self.interfaceData[interface]["txBytes"]))
		info += self.geolocationData
		self["information"].setText("\n".join(info).encode("UTF-8", "ignore") if PY2 else "\n".join(info))


class ReceiverInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Receiver Information"))
		self.skinName.insert(0, "ReceiverInformation")
		self["key_yellow"] = StaticText(_("System"))
		self["key_blue"] = StaticText(_("Benchmark"))
		self["receiverActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.showSystem, _("Show system information")),
			"blue": (self.showBenchmark, _("Show benchmark information"))
		}, prio=0, description=_("Receiver Information Actions"))
		self.degree = str("\xc2\xb0C")

	def showSystem(self):
		self.session.openWithCallback(self.informationWindowClosed, SystemInformation)

	def showBenchmark(self):
		self.session.openWithCallback(self.informationWindowClosed, BenchmarkInformation)

	def displayInformation(self):
		model = SystemInfo["MachineModel"]
		info = []
		info.append(formatLine("H", _("Hardware information")))
		info.append("")
		stbPlatform = boxbranding.getMachineBuild()
		info.append(formatLine("P1", _("Hardware"), "%s %s" % (SystemInfo["MachineBrand"], SystemInfo["MachineModel"])))
		if stbPlatform != model:
			info.append(formatLine("P1", _("Platform"), stbPlatform))
		try:
			procModel = getBoxProc()
		except Exception as err:
			procModel = boxbranding.getMachineProcModel()
		if procModel != model:
			info.append(formatLine("P1", _("Proc model"), procModel))
		procModelType = getBoxProcType()
		if procModelType and procModelType != "unknown":
			info.append(formatLine("P1", _("Hardware type"), procModelType))
		hwSerial = getHWSerial()
		if hwSerial:
			info.append(formatLine("P1", _("Hardware serial"), (hwSerial if hwSerial != "unknown" else about.getCPUSerial())))
		if isfile("/proc/stb/info/release"):
			hwRelease = open("/proc/stb/info/release", "r").read().strip()
			info.append(formatLine("P1", _("Factory release"), hwRelease))
		info.append(formatLine("P1", _("Brand/Meta"), SystemInfo["MachineBrand"]))
		if not boxbranding.getDisplayType().startswith(" "):
			info.append(formatLine("P1", _("Front panel type"), boxbranding.getDisplayType()))
		fpVersion = getFPVersion()
		if fpVersion and fpVersion != "unknown":
			info.append(formatLine("P1", _("Front processor version"), fpVersion))
		info.append("")
		info.append(formatLine("H", _("Processor information")))
		info.append("")
		info.append(formatLine("P1", _("CPU"), about.getCPUInfoString()))
		info.append(formatLine("P1", _("CPU brand"), about.getCPUBrand()))
		socFamily = boxbranding.getSoCFamily()
		if socFamily:
			info.append(formatLine("P1", _("SoC family"), socFamily))
		info.append(formatLine("P1", _("CPU architecture"), about.getCPUArch()))
		if boxbranding.getImageFPU():
			info.append(formatLine("P1", _("FPU"), boxbranding.getImageFPU()))
		if boxbranding.getImageArch() == "aarch64":
			info.append(formatLine("P1", _("MultiLib"), (_("Yes") if boxbranding.getHaveMultiLib() == "True" else _("No"))))
		info.append("")
		info.append(formatLine("H", _("Remote control information")))
		info.append("")
		boxRcType = getBoxRCType()
		if boxRcType:
			if boxRcType == "unknown":
				if isfile("/usr/bin/remotecfg"):
					info.append(_("RC type:|%s") % _("Amlogic remote"))
				elif isfile("/usr/sbin/lircd"):
					info.append(_("RC type:|%s") % _("LIRC remote"))
			else:
				info.append(formatLine("P1", _("RC type"), boxRcType))
		info.append(formatLine("P1", _("RC code"), boxbranding.getRCType()))
		info.append(formatLine("P1", _("RC name"), boxbranding.getRCName()))
		info.append(formatLine("P1", _("RC ID number"), boxbranding.getRCIDNum()))
		info.append("")
		info.append(formatLine("H", _("Driver and kernel information")))
		info.append("")
		info.append(formatLine("P1", _("Drivers version"), about.getDriverInstalledDate()))
		info.append(formatLine("P1", _("Kernel version"), boxbranding.getKernelVersion()))
		moduleLayout = popen("find /lib/modules/ -type f -name 'openvision.ko' -exec modprobe --dump-modversions {} \; | grep 'module_layout' | cut -c-11").read().strip()
		info.append(formatLine("P1", _("Kernel module layout"), (moduleLayout if moduleLayout else _("N/A"))))
		if isfile("/proc/device-tree/amlogic-dt-id"):
			deviceId = open("/proc/device-tree/amlogic-dt-id", "r").read().strip()
			info.append(formatLine("P1", _("Device id"), deviceId))
		if isfile("/proc/device-tree/le-dt-id"):
			givenId = open("/proc/device-tree/le-dt-id", "r").read().strip()
			info.append(formatLine("P1", _("Given device id"), givenId))
		info.append("")
		info.append(formatLine("H", _("Detected NIMs")))
		info.append("")
		nims = nimmanager.nimListCompressed()
		for count in range(len(nims)):
			tuner, type = [x.strip() for x in nims[count].split(":", 1)]
			info.append(formatLine("P1", tuner, type))
		info.append("")
		info.append(formatLine("H", _("Detected HDDs")))
		info.append("")
		# hddList = storageManager.HDDList()
		hddList = harddiskmanager.HDDList()
		if hddList:
			for count in range(len(hddList)):
				hdd = hddList[count][1]
				# free = "%.3f GB" % (hdd.totalFree() / 1024.0) if int(hdd.free()) > 1024 else "%.3f MB" % hdd.totalFree()
				free = "%.3f GB" % (hdd.Totalfree() / 1024.0) if int(hdd.free()) > 1024 else "%.3f MB" % hdd.Totalfree()
				info.append(formatLine("P1", hdd.model(), "%s, %s %s" % (hdd.capacity(), free, _("free"))))
		else:
			info.append(formatLine("H", _("No hard disks detected.")))
		info.append("")
		info.append(formatLine("H", _("Network information")))
		info.append("")
		for x in about.GetIPsFromNetworkInterfaces():
			info.append(formatLine("P1", x[0], x[1]))
		info.append("")
		info.append(formatLine("H", _("Uptime"), about.getBoxUptime()))
		self["information"].setText("\n".join(info).encode("UTF-8", "ignore") if PY2 else "\n".join(info))

	def getSummaryInformation(self):
		return "Receiver Information"


class StorageInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Storage Information"))
		self.skinName.insert(0, "StorageInformation")
		self["information"].setText(_("Retrieving network server information, please wait..."))
		self.mountInfo = []
		self.console = Console()

	def fetchInformation(self):
		self.informationTimer.stop()
		self.console.ePopen("df -mh | grep -v '^Filesystem'", self.fetchComplete)
		for callback in self.onInformationUpdated:
			callback()

	def fetchComplete(self, result, retVal, extraArgs=None):
		result = result.decode().replace("\n                        ", " ").split("\n") if PY2 else result.replace("\n                        ", " ").split("\n")
		self.mountInfo = []
		for line in result:
			line = line.strip()
			if not line:
				continue
			data = line.split()
			if data[0].startswith("192") or data[0].startswith("//192"):
				# data[0] = ipAddress, data[1] = mountTotal, data[2] = mountUsed, data[3] = mountFree, data[4] = percetageUsed, data[5] = mountPoint.
				self.mountInfo.append(data)
		if isdir("/media/autofs"):
			for entry in sorted(listdir("/media/autofs")):
				path = pathjoin("/media/autofs", entry)
				keep = True
				for data in self.mountInfo:
					if data[5] == path:
						keep = False
						break
				if keep:
					self.mountInfo.append(["", 0, 0, 0, "N/A", path])
		for callback in self.onInformationUpdated:
			callback()

	def displayInformation(self):
		info = []
		info.append(formatLine("H", _("Detected storage devices")))
		# hddList = storageManager.HDDList()
		hddList = harddiskmanager.HDDList()
		if hddList:
			for drive in range(len(hddList)):
				hdd = hddList[drive][1]
				info.append("")
				info.append(formatLine("H1", hdd.getDeviceName(), hdd.bus()))
				info.append(formatLine("P2", _("Model"), hdd.model()))
				info.append(formatLine("P2", _("Capacity"), hdd.capacity()))
				info.append(formatLine("P2", _("Sleeping"), (_("Yes") if hdd.isSleeping() else _("No"))))
				for partition in range(hdd.numPartitions()):
					info.append(formatLine("P2", _("Partition"), partition + 1))
					info.append(formatLine("P3", _("Capacity"), hdd.capacity()))
					# info.append(formatLine("P3", _("Free"), hdd.space()))
					info.append(formatLine("P3", _("Free"), scaleNumber(hdd.free() * 1000)))
		else:
			info.append("")
			info.append(formatLine("H1", _("No hard disks detected.")))
		info.append("")
		info.append(formatLine("H", _("Detected network servers")))
		if self.mountInfo:
			for data in self.mountInfo:
				info.append("")
				info.append(formatLine("H1", data[5]))
				if data[0]:
					info.append(formatLine("P2", _("Network address"), data[0]))
					info.append(formatLine("P2", _("Capacity"), data[1]))
					info.append(formatLine("P2", _("Used"), "%s  (%s)" % (data[2], data[4])))
					info.append(formatLine("P2", _("Free"), data[3]))
				else:
					info.append(formatLine("P2", _("Not currently mounted.")))
		else:
			info.append("")
			info.append(formatLine("P1", _("No network servers detected.")))
		self["information"].setText("\n".join(info).encode("UTF-8", "ignore") if PY2 else "\n".join(info))


class SystemInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.baseTitle = _("System Information")
		self.setTitle(self.baseTitle)
		self.skinName.insert(0, "SystemInformation")
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["systemLogActions"] = HelpableActionMap(self, ["NavigationActions"], {
			"left": (self.previousDiagnostic, _("Display previous system information screen")),
			"right": (self.nextDiagnostic, _("Display next system information screen")),
		}, prio=0, description=_("System Information Actions"))
		self["logfileActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.deleteLog, _("Delete the currently displayed log file")),
			"blue": (self.deleteAllLogs, _("Delete all log files"))
		}, prio=0, description=_("System Information Actions"))
		self["logfileActions"].setEnabled(False)
		self.commands = []
		self.numberOfCommands = 0
		self.commandIndex = 0
		self.commandData = ""
		self.container = eConsoleAppContainer()
		self.container.dataAvail.append(self.dataAvail)
		self.container.appClosed.append(self.appClosed)
		self.log = _("Retrieving system information, please wait...")

	def previousDiagnostic(self):
		self.commandIndex = (self.commandIndex - 1) % len(self.commands)
		self.log = _("Retrieving system information, please wait...")
		self.refreshInformation()

	def nextDiagnostic(self):
		self.commandIndex = (self.commandIndex + 1) % len(self.commands)
		self.log = _("Retrieving system information, please wait...")
		self.refreshInformation()

	def deleteLog(self):
		if self.commandIndex >= self.numberOfCommands:
			self.session.openWithCallback(self.removeLog, MessageBox, _("Do you want to delete this log file?"), default=False)

	def removeLog(self, answer):
		if answer:
			try:
				args = self.commands[self.commandIndex][1].split()
				remove(args[-1])
				self.session.open(MessageBox, _("Log file '%s' deleted.") % args[-1], type=MessageBox.TYPE_INFO, timeout=5, close_on_any_key=True, title=self.baseTitle)
			except (IOError, OSError) as err:
				self.session.open(MessageBox, _("Log file '%s' deleted.") % args[-1], type=MessageBox.TYPE_ERROR, timeout=5, title=self.baseTitle)
			self.informationTimer.start(25)
			for callback in self.onInformationUpdated:
				callback()

	def deleteAllLogs(self):
		if self.commandIndex >= self.numberOfCommands:
			self.session.openWithCallback(self.removeAllLogs, MessageBox, _("Do you want to delete all log files?"), default=False)

	def removeAllLogs(self, answer):
		if answer:
			filenames = [x for x in sorted(glob("/mnt/hdd/*.log"), key=lambda x: isfile(x) and getmtime(x))]
			filenames += [x for x in sorted(glob("/home/root/logs/enigma2_crash*.log"), key=lambda x: isfile(x) and getmtime(x))]
			filenames += [x for x in sorted(glob("/home/root/logs/enigma2_debug*.log"), key=lambda x: isfile(x) and getmtime(x))]
			log = []
			type = MessageBox.TYPE_INFO
			close = True
			for filename in filenames:
				try:
					remove(filename)
					log.append(_("Log file '%s' deleted.") % filename)
				except (IOError, OSError) as err:
					type = MessageBox.TYPE_ERROR
					close = False
					log.append(_("Error %d: Log file '%s' wasn't deleted!  (%s)") % (err.errno, filename, err.strerror))
			log = "\n".join(log).encode("UTF-8", "ignore") if PY2 else "\n".join(log)
			self.session.open(MessageBox, log, type=type, timeout=5, close_on_any_key=close, title=self.baseTitle)
			self.informationTimer.start(25)
			for callback in self.onInformationUpdated:
				callback()

	def keyCancel(self):
		self.container.dataAvail.remove(self.dataAvail)
		self.container.appClosed.remove(self.appClosed)
		self.container = None
		InformationBase.keyCancel(self)

	def closeRecursive(self):
		self.container.dataAvail.remove(self.dataAvail)
		self.container.appClosed.remove(self.appClosed)
		self.container = None
		InformationBase.closeRecursive(self)

	def fetchInformation(self):
		self.informationTimer.stop()
		self.commands = [
			("dmesg", "/bin/dmesg", "dmesg"),
			("ifconfig", "/sbin/ifconfig", "ifconfig"),
			("df", "/bin/df -h", "df"),
			("top", "/usr/bin/top -b -n 1", "top"),
			("ps", "/bin/ps -l", "ps"),
			("messages", "/bin/cat /var/volatile/log/messages", "messages")
		]
		self.numberOfCommands = len(self.commands)
		#
		# TODO: Need to adjust path of log files to match current configurations!
		#
		installLog = "/home/root/autoinstall.log"
		if isfile(installLog):
			self.commands.append((_("Auto install log"), "/bin/cat %s" % installLog, installLog))
			self.numberOfCommands += 1
		crashLog = "/tmp/enigma2_crash.log"
		if isfile(crashLog):
			self.commands.append((_("Current crash log"), "/bin/cat %s" % crashLog, crashLog))
			self.numberOfCommands += 1
		filenames = [x for x in sorted(glob("/mnt/hdd/*.log"), key=lambda x: isfile(x) and getmtime(x))]
		if filenames:
			totalNumberOfLogfiles = len(filenames)
			logfileCounter = 1
			for filename in reversed(filenames):
				self.commands.append((_("Logfile '%s' (%d/%d)") % (basename(filename), logfileCounter, totalNumberOfLogfiles), "/bin/cat %s" % filename, filename))
				logfileCounter += 1
		filenames = [x for x in sorted(glob("/home/root/logs/enigma2_crash*.log"), key=lambda x: isfile(x) and getmtime(x))]
		if filenames:
			totalNumberOfLogfiles = len(filenames)
			logfileCounter = 1
			for filename in reversed(filenames):
				self.commands.append((_("Crash log '%s' (%d/%d)") % (basename(filename), logfileCounter, totalNumberOfLogfiles), "/bin/cat %s" % filename, filename))
				logfileCounter += 1
		filenames = [x for x in sorted(glob("/home/root/logs/enigma2_debug*.log"), key=lambda x: isfile(x) and getmtime(x))]
		if filenames:
			totalNumberOfLogfiles = len(filenames)
			logfileCounter = 1
			for filename in reversed(filenames):
				self.commands.append((_("Debug log '%s' (%d/%d)") % (basename(filename), logfileCounter, totalNumberOfLogfiles), "/usr/bin/tail -n 1000 %s" % filename, filename))
				logfileCounter += 1
		self.commandIndex = min(len(self.commands) - 1, self.commandIndex)
		self.refreshInformation()

	def refreshInformation(self):
		self.setTitle("%s - %s" % (self.baseTitle, self.commands[self.commandIndex][0]))
		command = self.commands[self.commandIndex][1]
		args = command.split()  # For safety don't use a shell command line!
		if args[0] == "/bin/cat":
			try:
				with open(args[1], "r") as fd:
					data = fd.read()
				data = data.encode("UTF-8", "ignore") if PY2 else data
				self.log = data
			except (IOError, OSError) as err:
				self.log = _("Error %d: The logfile '%s' could not be opened.  (%s)") % (err.errno, args[1], err.strerror)
		else:
			# print("[Information] DEBUG: System logs command='%s'." % command)
			# print("[Information] DEBUG: System logs args=%s." % args)
			self.commandData = ""
			args.insert(0, args[0])
			retVal = self.container.execute(*args)
			pid = self.container.getPID()
			# print("[Information] DEBUG: System logs PID=%d." % pid)
			# try:
			# 	waitpid(pid, 0)
			# except (IOError, OSError) as err:
			# 	pass
		if self.commandIndex >= self.numberOfCommands:
			self["key_yellow"].text = _("Delete logfile")
			self["key_blue"].text = _("Delete all logfiles")
			self["logfileActions"].setEnabled(True)
		else:
			self["key_yellow"].text = ""
			self["key_blue"].text = ""
			self["logfileActions"].setEnabled(False)
		for callback in self.onInformationUpdated:
			callback()

	def dataAvail(self, data):
		# print("[Information] Command data='%s'." % data)
		self.commandData += data

	def appClosed(self, retVal):
		self.log = self.commandData.encode("UTF-8", "ignore") if PY2 else self.commandData
		if retVal:
			self.log += "\n\n%s" % (_("An error occurred, error code %d, please try again later.") % retVal)
		for callback in self.onInformationUpdated:
			callback()

	def displayInformation(self):
		if not self.log:
			self.log = _("The '%s' log file contains no information.") % self.commands[self.commandIndex][2]
		self["information"].setText(self.log)


class TranslationInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Translation Information"))
		self.skinName.insert(0, "TranslationInformation")

	def displayInformation(self):
		info = []
		translateInfo = _("TRANSLATOR_INFO")
		if translateInfo != "TRANSLATOR_INFO":
			translateInfo = translateInfo.split("\n")
			for translate in translateInfo:
				info.append(formatLine("H", translate))
			info.append("")
		translateInfo = _("").split("\n")  # This is deliberate to dump the translation information.
		for translate in translateInfo:
			if not translate:
				continue
			translate = [x.strip() for x in translate.split(":", 1)]
			if len(translate) == 1:
				translate.append("")
			info.append(formatLine("P1", translate[0], translate[1]))
		self["information"].setText("\n".join(info).encode("UTF-8", "ignore") if PY2 else "\n".join(info))

	def getSummaryInformation(self):
		return "Translation Information"


class TunerInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Tuner Information"))
		self.skinName.insert(0, "TunerInformation")

	def displayInformation(self):
		info = []
		info.append(formatLine("H", _("Detected tuners")))
		info.append("")
		nims = nimmanager.nimList()
		descList = []
		curIndex = -1
		for count in range(len(nims)):
			data = nims[count].split(":")
			idx = data[0].strip("Tuner").strip()
			desc = data[1].strip()
			if descList and descList[curIndex]["desc"] == desc:
				descList[curIndex]["end"] = idx
			else:
				descList.append({
					"desc": desc,
					"start": idx,
					"end": idx
				})
				curIndex += 1
			count += 1
		for count in range(len(descList)):
			data = descList[count]["start"] if descList[count]["start"] == descList[count]["end"] else ("%s-%s" % (descList[count]["start"], descList[count]["end"]))
			info.append(formatLine("P1", "Tuner %s" % data, descList[count]["desc"]))
		# info.append("")
		# info.append(formatLine("H", _("Logical tuners")))  # Each tuner is a listed separately even if the hardware is common.
		# info.append("")
		# nims = nimmanager.nimListCompressed()
		# for count in range(len(nims)):
		# 	tuner, type = [x.strip() for x in nims[count].split(":", 1)]
		# 	info.append(formatLine("P1", tuner, type))
		info.append("")
		info.append(formatLine("", _("DVB API"), about.getDVBAPI()))
		numSlots = 0
		dvbFeToolTxt = ""
		nimSlots = nimmanager.getSlotCount()
		for nim in range(nimSlots):
			dvbFeToolTxt += eDVBResourceManager.getInstance().getFrontendCapabilities(nim)
		dvbApiVersion = dvbFeToolTxt.splitlines()[0].replace("DVB API version: ", "").strip()
		info.append(formatLine("", _("DVB API version"), dvbApiVersion))
		info.append("")
		info.append(formatLine("", _("Transcoding"), (_("Yes") if boxbranding.getHaveTranscoding() == "True" else _("No"))))
		info.append(formatLine("", _("MultiTranscoding"), (_("Yes") if boxbranding.getHaveMultiTranscoding() == "True" else _("No"))))
		info.append("")
		info.append(formatLine("", _("DVB-C"), (_("Yes") if "DVBC" in dvbFeToolTxt or "DVB-C" in dvbFeToolTxt else _("No"))))
		info.append(formatLine("", _("DVB-S"), (_("Yes") if "DVBS" in dvbFeToolTxt or "DVB-S" in dvbFeToolTxt else _("No"))))
		info.append(formatLine("", _("DVB-T"), (_("Yes") if "DVBT" in dvbFeToolTxt or "DVB-T" in dvbFeToolTxt else _("No"))))
		info.append("")
		info.append(formatLine("", _("Multistream"), (_("Yes") if "MULTISTREAM" in dvbFeToolTxt else _("No"))))
		info.append("")
		info.append(formatLine("", _("ANNEX-A"), (_("Yes") if "ANNEX_A" in dvbFeToolTxt or "ANNEX-A" in dvbFeToolTxt else _("No"))))
		info.append(formatLine("", _("ANNEX-B"), (_("Yes") if "ANNEX_B" in dvbFeToolTxt or "ANNEX-B" in dvbFeToolTxt else _("No"))))
		info.append(formatLine("", _("ANNEX-C"), (_("Yes") if "ANNEX_C" in dvbFeToolTxt or "ANNEX-C" in dvbFeToolTxt else _("No"))))
		self["information"].setText("\n".join(info).encode("UTF-8", "ignore") if PY2 else "\n".join(info))

	def getSummaryInformation(self):
		return "DVB Information"


class InformationSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self.parent = parent
		self["information"] = StaticText()
		parent.onInformationUpdated.append(self.updateSummary)
		# self.updateSummary()

	def updateSummary(self):
		# print("[Information] DEBUG: Updating summary.")
		self["information"].setText(self.parent.getSummaryInformation())
