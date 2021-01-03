from enigma import eEnv
from six import PY2
from xml.etree.cElementTree import parse

from Components.ActionMap import NumberActionMap
from Components.config import ConfigBoolean, ConfigNothing, ConfigSelection, config
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.SystemInfo import SystemInfo
from Components.Sources.Boolean import Boolean
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen

# FIXME: use resolveFile!
# Read the setupmenu.
try:
	# First we search in the current path.
	setupFile = open("data/setup.xml", "r")
except (IOError, OSError) as err:
	# If not found in the current path, we use the global datadir-path.
	setupFile = open(eEnv.resolve("${datadir}/enigma2/setup.xml"), "r")
setupdom = parse(setupFile)
setupFile.close()


class Setup(ConfigListScreen, Screen):
	ALLOW_SUSPEND = True

	def __init__(self, session, setup):
		Screen.__init__(self, session)
		# For the skin: first try a setup_<setupID>, then Setup.
		self.skinName = ["setup_" + setup, "Setup"]
		self.list = []
		self.forceUpdateList = False
		xmldata = setupdom.getroot()
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
		self["config"].onSelectionChanged.append(self.__onSelectionChanged)
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

	def __onSelectionChanged(self):
		if self.forceUpdateList:
			self["config"].onSelectionChanged.remove(self.__onSelectionChanged)
			self.createSetupList()
			self["config"].onSelectionChanged.append(self.__onSelectionChanged)
			self.forceUpdateList = False
		if not (isinstance(self["config"].getCurrent()[1], ConfigBoolean) or isinstance(self["config"].getCurrent()[1], ConfigSelection)):
			self.forceUpdateList = True

	def createSummary(self):
		return SetupSummary

	def run(self):
		self.keySave()


class SetupSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["SetupTitle"] = StaticText(parent.getTitle())
		self["SetupEntry"] = StaticText("")
		self["SetupValue"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if hasattr(self.parent, "onChangedEntry"):
			self.parent.onChangedEntry.append(self.selectionChanged)
			self.parent["config"].onSelectionChanged.append(self.selectionChanged)
			self.selectionChanged()

	def removeWatcher(self):
		if hasattr(self.parent, "onChangedEntry"):
			self.parent.onChangedEntry.remove(self.selectionChanged)
			self.parent["config"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		self["SetupEntry"].text = self.parent.getCurrentEntry()
		self["SetupValue"].text = self.parent.getCurrentValue()
		if hasattr(self.parent, "getCurrentDescription") and "description" in self.parent:
			self.parent["description"].text = self.parent.getCurrentDescription()

def getConfigMenuItem(configElement):
	for item in setupdom.getroot().findall("./setup/item/."):
		if item.text == configElement:
			return _(item.attrib["text"]), eval(configElement)
	return "", None

def getSetupTitle(id):
	xmlData = setupdom.getroot()
	for x in xmlData.findall("setup"):
		if x.get("key") == id:
			if PY2:
				return x.get("title", "").encode("UTF-8")
			else:
				return x.get("title", "")
	print("[Setup] Error: Unknown setup id '%s'!" % repr(id))
	return "Unknown setup id '%s'!" % repr(id)
