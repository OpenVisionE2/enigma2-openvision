from enigma import eEnv
from os.path import getmtime, join as pathJoin
from six import PY2
from xml.etree.cElementTree import ParseError, fromstring, parse

from Components.ActionMap import NumberActionMap
from Components.config import ConfigBoolean, ConfigNothing, ConfigSelection, config
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.SystemInfo import SystemInfo
from Components.Sources.Boolean import Boolean
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen, ScreenSummary
from Tools.Directories import SCOPE_PLUGINS, SCOPE_SKIN, resolveFilename

domSetups = {}
setupModTimes = {}


class Setup(ConfigListScreen, Screen):
	def __init__(self, session, setup):
		Screen.__init__(self, session)
		# For the skin: first try a setup_<setupID>, then Setup.
		self.skinName = ["setup_" + setup, "Setup"]
		self.onChangedEntry = []
		self.list = []
		self.forceUpdateList = False
		xmldata = setupDom(setup)
		for x in xmldata.findall("setup"):
			if x.get("key") == setup:
				self.setup = x
				break
		if PY2:
			self.setupTitle = self.setup.get("title", "").encode("UTF-8")
		else:
			self.setupTitle = self.setup.get("title", "")
		self.seperation = int(self.setup.get("separation", "0"))
		# Check for list.entries > 0 else self.close.
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["footnote"] = Label()
		self["footnote"].hide()
		self["description"] = Label("")
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)
		self["actions"] = NumberActionMap(["SetupActions", "MenuActions"], {
			"cancel": self.keyCancel,
			"save": self.keySave,
			"menu": self.closeRecursive,
		}, -2)
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry)
		self.createSetupList()
		if self.selectionChanged not in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.setTitle(_(self.setupTitle))

	def createSetupList(self):
		currentItem = self["config"].getCurrent()
		self.list = []
		for x in self.setup:
			if not x.tag:
				continue
			if x.tag == "item":
				itemLevel = int(x.get("level", 0))
				itemTuxTxtLevel = int(x.get("tt_level", 0))
				if itemLevel > config.usage.setup_level.index:
					continue
				if (itemTuxTxtLevel == 1) and (config.usage.tuxtxt_font_and_res.value != "expert_mode"):
					continue
				requires = x.get("requires")
				if requires:
					meets = True
					for requires in requires.split(";"):
						negate = requires.startswith("!")
						if negate:
							requires = requires[1:]
						if requires.startswith("config."):
							try:
								item = eval(requires)
								SystemInfo[requires] = True if item.value and item.value not in ("0", "False", "false", "off") else False
							except AttributeError:
								print("[Setup] Unknown 'requires' config element: '%s'." % requires)
						if requires:
							if not SystemInfo.get(requires, False):
								if not negate:
									meets = False
									break
							else:
								if negate:
									meets = False
									break
					if not meets:
						continue
				if PY2:
					itemText = _(x.get("text", "??").encode("UTF-8"))
					itemDescription = _(x.get("description", " ").encode("UTF-8"))
				else:
					itemText = _(x.get("text", "??"))
					itemDescription = _(x.get("description", " "))
				b = eval(x.text or "")
				if b == "":
					continue
				# Add to configlist.
				item = b
				# The first b is the item itself, ignored by the configList.
				# The second one is converted to string.
				if not isinstance(item, ConfigNothing):
					self.list.append((itemText, item, itemDescription))
		self["config"].setList(self.list)
		if config.usage.sort_settings.value:
			self["config"].list.sort()
		self.moveToItem(currentItem)

	def moveToItem(self, item):
		if item != self["config"].getCurrent():
			self["config"].setCurrentIndex(self.getIndexFromItem(item))

	def getIndexFromItem(self, item):
		return self["config"].list.index(item) if item in self["config"].list else 0

	def changedEntry(self):
		if isinstance(self["config"].getCurrent()[1], ConfigBoolean) or isinstance(self["config"].getCurrent()[1], ConfigSelection):
			self.createSetupList()

	def selectionChanged(self):
		if self["config"]:
			self.setFootnote(None)
			self["description"].text = self.getCurrentDescription()
		else:
			self["description"].text = _("There are no items currently available for this screen.")

	def setFootnote(self, footnote):
		if footnote is None:
			if self.getCurrentEntry().endswith("*"):
				self["footnote"].text = _("* = Restart Required")
				self["footnote"].show()
			else:
				self["footnote"].text = ""
				self["footnote"].hide()
		else:
			self["footnote"].text = footnote
			self["footnote"].show()

	def getFootnote(self):
		return self["footnote"].text

	def createSummary(self):
		return SetupSummary


class SetupSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self["entry"] = StaticText("")  # DEBUG: Proposed for new summary screens.
		self["value"] = StaticText("")  # DEBUG: Proposed for new summary screens.
		self["SetupTitle"] = StaticText(parent.getTitle())
		self["SetupEntry"] = StaticText("")
		self["SetupValue"] = StaticText("")
		if self.addWatcher not in self.onShow:
			self.onShow.append(self.addWatcher)
		if self.removeWatcher not in self.onHide:
			self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if self.selectionChanged not in self.parent.onChangedEntry:
			self.parent.onChangedEntry.append(self.selectionChanged)
		if self.selectionChanged not in self.parent["config"].onSelectionChanged:
			self.parent["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def removeWatcher(self):
		if self.selectionChanged in self.parent.onChangedEntry:
			self.parent.onChangedEntry.remove(self.selectionChanged)
		if self.selectionChanged in self.parent["config"].onSelectionChanged:
			self.parent["config"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		self["entry"].text = self.parent.getCurrentEntry()  # DEBUG: Proposed for new summary screens.
		self["value"].text = self.parent.getCurrentValue()  # DEBUG: Proposed for new summary screens.
		self["SetupEntry"].text = self.parent.getCurrentEntry()
		self["SetupValue"].text = self.parent.getCurrentValue()


# Read the setup XML file.
#
def setupDom(setup=None, plugin=None):
	# Constants for checkItems()
	ROOT_ALLOWED = ("setup", )  # Tags allowed in top level of setupxml entry.
	ELEMENT_ALLOWED = ("item", "if")  # Tags allowed in top level of setup entry.
	IF_ALLOWED = ("item", "if", "elif", "else")  # Tags allowed inside <if />.
	AFTER_ELSE_ALLOWED = ("item", "if")  # Tags allowed after <elif /> or <else />.
	CHILDREN_ALLOWED = ("setup", "if", )  # Tags that may have children.
	TEXT_ALLOWED = ("item", )  # Tags that may have non-whitespace text (or tail).
	KEY_ATTRIBUTES = {  # Tags that have a reference key mandatory attribute.
		"setup": "key",
		"item": "text"
	}
	MANDATORY_ATTRIBUTES = {  # Tags that have a list of mandatory attributes.
		"setup": ("key", "title"),
		"item": ("text", )
	}

	def checkItems(parentNode, key, allowed=ROOT_ALLOWED, mandatory=MANDATORY_ATTRIBUTES, reference=KEY_ATTRIBUTES):
		keyText = " in '%s'" % key if key else ""
		for element in parentNode:
			if element.tag not in allowed:
				print("[Setup] Error: Tag '%s' not permitted%s!  (Permitted: '%s')" % (element.tag, keyText, ", ".join(allowed)))
				continue
			if mandatory and element.tag in mandatory:
				valid = True
				for attrib in mandatory[element.tag]:
					if element.get(attrib) is None:
						print("[Setup] Error: Tag '%s'%s does not contain the mandatory '%s' attribute!" % (element.tag, keyText, attrib))
						valid = False
				if not valid:
					continue
			if element.tag not in TEXT_ALLOWED:
				if element.text and not element.text.isspace():
					print("[Setup] Tag '%s'%s contains text '%s'." % (element.tag, keyText, element.text.strip()))
				if element.tail and not element.tail.isspace():
					print("[Setup] Tag '%s'%s has trailing text '%s'." % (element.tag, keyText, element.text.strip()))
			if element.tag not in CHILDREN_ALLOWED and len(element):
				itemKey = ""
				if element.tag in reference:
					itemKey = " (%s)" % element.get(reference[element.tag])
				print("[Setup] Tag '%s'%s%s contains children where none expected." % (element.tag, itemKey, keyText))
			if element.tag in CHILDREN_ALLOWED:
				if element.tag in reference:
					key = element.get(reference[element.tag])
				checkItems(element, key, allowed=IF_ALLOWED)
			elif element.tag == "else":
				allowed = AFTER_ELSE_ALLOWED  # Another else and elif not permitted after else.
			elif element.tag == "elif":
				pass

	setupFileDom = fromstring("<setupxml></setupxml>")
	setupFile = resolveFilename(SCOPE_PLUGINS, pathJoin(plugin, "setup.xml")) if plugin else resolveFilename(SCOPE_SKIN, "setup.xml")
	global domSetups, setupModTimes
	try:
		modTime = getmtime(setupFile)
	except (IOError, OSError) as err:
		print("[Setup] Error: Unable to get '%s' modified time - Error (%d): %s!" % (setupFile, err.errno, err.strerror))
		if setupFile in domSetups:
			del domSetups[setupFile]
		if setupFile in setupModTimes:
			del setupModTimes[setupFile]
		return setupFileDom
	cached = setupFile in domSetups and setupFile in setupModTimes and setupModTimes[setupFile] == modTime
	print("[Setup] XML%s setup file '%s', using element '%s'%s." % (" cached" if cached else "", setupFile, setup, " from plugin '%s'" % plugin if plugin else ""))
	if cached:
		return domSetups[setupFile]
	try:
		if setupFile in domSetups:
			del domSetups[setupFile]
		if setupFile in setupModTimes:
			del setupModTimes[setupFile]
		with open(setupFile, "r") as fd:  # This open gets around a possible file handle leak in Python's XML parser.
			try:
				fileDom = parse(fd).getroot()
				checkItems(fileDom, None)
				setupFileDom = fileDom
				domSetups[setupFile] = setupFileDom
				setupModTimes[setupFile] = modTime
				for setup in setupFileDom.findall("setup"):
					key = setup.get("key")
					if key:  # If there is no key then this element is useless and can be skipped!
						title = setup.get("title", "").encode("UTF-8", errors="ignore") if PY2 else setup.get("title", "")
						if title == "":
							print("[Setup] Error: Setup key '%s' title is missing or blank!" % key)
							title = "** Setup error: '%s' title is missing or blank!" % key
						# print("[Setup] DEBUG: XML setup load: key='%s', title='%s'." % (key, setup.get("title", "").encode("UTF-8", errors="ignore")))
			except ParseError as err:
				fd.seek(0)
				content = fd.readlines()
				line, column = err.position
				print("[Setup] XML Parse Error: '%s' in '%s'!" % (err, setupFile))
				data = content[line - 1].replace("\t", " ").rstrip()
				print("[Setup] XML Parse Error: '%s'" % data)
				print("[Setup] XML Parse Error: '%s^%s'" % ("-" * column, " " * (len(data) - column - 1)))
			except Exception as err:
				print("[Setup] Error: Unable to parse setup data in '%s' - '%s'!" % (setupFile, err))
	except (IOError, OSError) as err:
		if err.errno == errno.ENOENT:  # No such file or directory.
			print("[Setup] Warning: Setup file '%s' does not exist!" % setupFile)
		else:
			print("[Setup] Error %d: Opening setup file '%s'! (%s)" % (err.errno, setupFile, err.strerror))
	except Exception as err:
		print("[Setup] Error %d: Unexpected error opening setup file '%s'! (%s)" % (err.errno, setupFile, err.strerror))
	return setupFileDom

# Temporary legacy interface.  Known to be used by the Heinz plugin and possibly others.
#
def setupdom(setup=None, plugin=None):
	return setupDom(setup, plugin)

def getConfigMenuItem(configElement):
	for item in setupDom.findall("./setup/item/."):
		if item.text == configElement:
			return _(item.attrib["text"]), eval(configElement)
	return "", None

def getSetupTitle(id):
	xmlData = setupDom()
	for x in xmlData.findall("setup"):
		if x.get("key") == id:
			if PY2:
				return x.get("title", "").encode("UTF-8")
			else:
				return x.get("title", "")
	print("[Setup] Error: Unknown setup id '%s'!" % repr(id))
	return "Unknown setup id '%s'!" % repr(id)
