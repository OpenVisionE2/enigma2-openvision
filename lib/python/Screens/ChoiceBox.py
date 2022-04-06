from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import config, ConfigSubsection, ConfigText
from Components.ChoiceList import ChoiceEntryComponent, ChoiceList
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen, ScreenSummary

config.misc.pluginlist = ConfigSubsection()
config.misc.pluginlist.eventInfoOrder = ConfigText(default="")
config.misc.pluginlist.extensionOrder = ConfigText(default="")


class ChoiceBox(Screen, HelpableScreen):
	def __init__(self, session, text=None, list=None, keys=None, selection=0, skinName=None, windowTitle=None, title=None, skin_name=None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		if title is not None:  # Process legacy title argument.
			text = title
		if text is None:
			text = ""
		self.text = text
		self["text"] = Label(text)
		if list is None:
			list = []
		if keys is None:
			keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "red", "green", "yellow", "blue"]
		self.inputKeys = keys + (len(list) - len(keys)) * ["dummy"]
		pos = 0
		self.list = []
		self.keyMap = {}
		for item in list:
			if item:
				self.list.append(ChoiceEntryComponent(key=str(self.inputKeys[pos]), text=item))
				if self.inputKeys[pos] != "":
					self.keyMap[self.inputKeys[pos]] = list[pos]
				pos += 1
		self["list"] = ChoiceList(list=self.list, selection=selection)
		if skin_name is not None:  # Process legacy skin_name argument.
			skinName = skin_name
		self.skinName = ["ChoiceBox"]
		if skinName:
			if isinstance(skinName, str):
				self.skinName.insert(0, skinName)
			else:
				self.skinName = skinName + self.skinName
		self["actions"] = HelpableNumberActionMap(self, ["ChoiceBoxActions", "NumberActions", "ColorActions", "NavigationActions", "MenuActions"], {
			"cancel": (self.keyCancel, _("Cancel the action selection and exit")),
			"select": (self.keySelect, _("Run the currently highlighted action")),
			"1": (self.keyNumberGlobal, _("Run the numbered action")),
			"2": (self.keyNumberGlobal, _("Run the numbered action")),
			"3": (self.keyNumberGlobal, _("Run the numbered action")),
			"4": (self.keyNumberGlobal, _("Run the numbered action")),
			"5": (self.keyNumberGlobal, _("Run the numbered action")),
			"6": (self.keyNumberGlobal, _("Run the numbered action")),
			"7": (self.keyNumberGlobal, _("Run the numbered action")),
			"8": (self.keyNumberGlobal, _("Run the numbered action")),
			"9": (self.keyNumberGlobal, _("Run the numbered action")),
			"0": (self.keyNumberGlobal, _("Run the numbered action")),
			"menu": self.KeyMenu,
			"red": (self.keyRed, _("Run the RED action")),
			"green": (self.keyGreen, _("Run the GREEN action")),
			"yellow": (self.keyYellow, _("Run the YELLOW action")),
			"blue": (self.keyBlue, _("Run the BLUE action")),
			"top": (self.top, _("Move to first line")),
			"pageUp": (self.pageUp, _("Move up a page")),
			"up": (self.up, _("Move up a line")),
			# "first": (self.top, _("Move to first line")),
			# "left": (self.pageUp, _("Move up a page")),
			# "right": (self.pageDown, _("Move down a page")),
			# "last": (self.bottom, _("Move to last line")),
			"down": (self.down, _("Move down a line")),
			"pageDown": (self.pageDown, _("Move down a page")),
			"bottom": (self.bottom, _("Move to last line"))
		}, prio=-2, description=_("Choice Box Actions"))
		self.setTitle(windowTitle or _("Select"))
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["list"].instance.allowNativeKeys(False)  # Override listbox navigation.

	def keyCancel(self):
		self.close(None)

	def keySelect(self):
		current = self["list"].l.getCurrentSelection()
		if current:
			self.goEntry(current[0])
		else:
			self.keyCancel()

	def keyNumberGlobal(self, number):
		self.goKey(str(number))

	def KeyMenu(self):
		if "menu" in self.keyMap:
			self.goKey("menu")
		else:
			self.keyCancel()

	def keyRed(self):
		self.goKey("red")

	def keyGreen(self):
		self.goKey("green")

	def keyYellow(self):
		self.goKey("yellow")

	def keyBlue(self):
		self.goKey("blue")

	def goKey(self, key):  # Lookups a key in the key map, then runs it.
		if key in self.keyMap:
			entry = self.keyMap[key]
			self.goEntry(entry)

	def goEntry(self, entry):  # Runs a specific entry.
		if len(entry) > 2 and isinstance(entry[1], str) and entry[1] == "CALLFUNC":
			arg = self["list"].l.getCurrentSelection()[0]  # CALLFUNC needs to have the current selection as argument.
			entry[2](arg)
		else:
			self.close(entry)

	def top(self):
		self.move(-1, self["list"].instance.moveTop)

	def pageUp(self):
		self.move(-1, self["list"].instance.pageUp)

	def up(self):
		self.move(-1, self["list"].instance.moveUp)

	def down(self):
		self.move(1, self["list"].instance.moveDown)

	def pageDown(self):
		self.move(1, self["list"].instance.pageDown)

	def bottom(self):
		self.move(1, self["list"].instance.moveEnd)

	def move(self, direction, step):  # The list should not start or end in a separator line.
		limit = len(self["list"].list) - 1 if direction > 0 else 0
		self["list"].instance.moveSelection(step)
		if self["list"].l.getCurrentSelection()[0][0] == "--" and self["list"].l.getCurrentSelectionIndex() != limit:
			direction = self["list"].instance.moveDown if direction > 0 else self["list"].instance.moveUp
			while True:
				self["list"].instance.moveSelection(direction)
				if self["list"].l.getCurrentSelection()[0][0] != "--" or self["list"].l.getCurrentSelectionIndex() == limit:
					break

	def autoResize(self):  # Dummy method place holder for some legacy skins.
		pass

	def createSummary(self):
		return ChoiceBoxSummary


class ChoiceBoxSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self["text"] = StaticText(parent.text)
		self["option"] = StaticText("")
		if hasattr(self, "list"):
			if self.addWatcher not in self.onShow:
				self.onShow.append(self.addWatcher)
			if self.removeWatcher not in self.onHide:
				self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if self.selectionChanged not in self.parent["list"].onSelectionChanged:
			self.parent["list"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def removeWatcher(self):
		if self.selectionChanged in self.parent["list"].onSelectionChanged:
			self.parent["list"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		self["option"].setText(self.parent["list"].l.getCurrentSelection()[0][0])


class OrderedChoiceBox(ChoiceBox):
	def __init__(self, session, text=None, list=None, keys=None, selection=0, order=None, skinName=None, windowTitle=None):
		if order:
			self.initialList = list
			if keys is None:
				keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "red", "green", "yellow", "blue"]
			self.initialKeys = keys
			self.configType = getattr(config.misc.pluginlist, order)
			if self.configType.value:
				prevList = [x for x in zip(list, keys)]  # Note that list() can not be used as it is also a variable that is used elsewhere!
				newList = []
				for item in self.configType.value.split(","):
					for entry in prevList:
						if entry[0][0] == item:
							newList.append(entry)
							prevList.remove(entry)
				list = [x for x in zip(*(newList + prevList))]  # Note that list() can not be used as it is also a variable that is used elsewhere!
				list, keys = list[0], list[1]
				number = 1
				newKeys = []
				for key in keys:
					if (not key or key.isdigit()) and number <= 10:
						newKeys.append(str(number % 10))
						number += 1
					else:
						newKeys.append(not key.isdigit() and key or "")
				keys = newKeys
				self.list = list
		ChoiceBox.__init__(self, session, text=text, list=list, keys=keys, selection=selection, skinName=skinName, windowTitle=windowTitle)
		if order and len(self.list) > 1:
			self["resetActions"] = HelpableActionMap(self, ["ChoiceBoxActions"], {
				"resetList": (self.setDefaultChoiceList, _("Reset list order to default"))
			}, prio=0, description=_("Choice Box Order Actions"))
			self["resetActions"].setEnabled(self.configType.value != "")
			self["key_text"] = StaticText(_("TEXT") if self.configType.value != "" else "")
			self["orderActions"] = HelpableActionMap(self, ["ChoiceBoxActions"], {
				"moveItemUp": (self.additionalMoveUp, _("Move the current item up one line")),
				"moveItemDown": (self.additionalMoveDown, _("Move the current item down one line"))
			}, prio=0, description=_("Choice Box Order Actions"))

	def setDefaultChoiceList(self):
		self.session.openWithCallback(self.setDefaultChoiceListCallback, MessageBox, _("Reset list order to default?"), MessageBox.TYPE_YESNO)

	def setDefaultChoiceListCallback(self, answer):
		if answer:
			inputKeys = self.initialKeys + (len(self.initialList) - len(self.initialKeys)) * ["dummy"]
			pos = 0
			list = []
			for item in self.initialList:
				if item:
					list.append(ChoiceEntryComponent(key=str(inputKeys[pos]), text=item))
					pos += 1
			self.list = list
			self["list"].setList(list)
			self.configType.value = ""
			self.configType.save()
			self["resetActions"].setEnabled(False)
			self["key_text"].setText("")

	def additionalMoveUp(self):
		self.additionalMove(-1)

	def additionalMoveDown(self):
		self.additionalMove(1)

	def additionalMove(self, direction):
		if len(self.list) > 1:
			currentIndex = self["list"].getSelectionIndex()
			swapIndex = (currentIndex + direction) % len(self.list)
			if currentIndex == 0 and swapIndex != 1:
				self.list = self.list[1:] + [self.list[0]]
			elif currentIndex != 1 and swapIndex == 0:
				self.list = [self.list[-1]] + self.list[:-1]
			else:
				self.list[currentIndex], self.list[swapIndex] = self.list[swapIndex], self.list[currentIndex]
			self["list"].l.setList(self.list)
			if direction == 1:
				self["list"].down()
			else:
				self["list"].up()
			self.configType.value = ",".join(x[0][0] for x in self.list)
			self.configType.save()
			self["resetActions"].setEnabled(True)
			self["key_text"].setText(_("TEXT"))
