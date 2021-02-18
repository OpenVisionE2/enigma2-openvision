from sys import maxsize

from enigma import eActionMap

from Components.ActionMap import ActionMap
from Components.HelpMenuList import HelpMenuList
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Screens.Rc import Rc
from Screens.Screen import Screen


class HelpMenu(Screen, Rc):
	helpText = "\n\n".join([
		_("Help Screen"),
		_("Brief help information for buttons in your current context."),
		_("Navigate up/down with UP/DOWN buttons and page up/down with LEFT/RIGHT. EXIT to return to the help screen. OK to perform the action described in the currently highlighted help."),
		_("Other buttons will jump to the help for that button, if there is help."),
		_("If an action is user-configurable, its help entry will be flagged with a (C)."),
		_("A highlight on the remote control image shows which button the help refers to. If more than one button performs the indicated function, more than one highlight will be shown. Text below the list indicates whether the function is for a long press of the button(s)."),
		_("The order and grouping of the help information list can be controlled using MENU>Setup>User Interface>Settings>Sort order for help screen.")
	])

	def __init__(self, session, list):
		Screen.__init__(self, session)
		Rc.__init__(self)
		self.setTitle(_("Help"))
		self["list"] = HelpMenuList(list, self.close, rcPos=self.getRcPositions())
		self["description"] = Label("")
		self["longshift_key0"] = Label("")
		self["longshift_key1"] = Label("")
		self["key_help"] = StaticText(_("HELP"))
		self["helpActions"] = ActionMap(["HelpActions"], {
			"select": self["list"].ok,
			"cancel": self.close,
			"displayHelp": self.showHelp
		}, prio=-1)
		# Wildcard binding with slightly higher priority than the
		# wildcard bindings in InfoBarGenerics.InfoBarUnhandledKey,
		# but with a gap so that other wildcards can be interposed
		# if needed.
		eActionMap.getInstance().bindAction("", maxsize - 100, self["list"].handleButton)
		# Ignore keypress breaks for the keys in the ListboxActions context.
		self["listboxFilterActions"] = ActionMap(["HelpMenuListboxActions"], {
			"ignore": lambda: 1
		}, prio=1)
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.closed)

	def layoutFinished(self):
		self["list"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def closed(self):
		eActionMap.getInstance().unbindAction("", self["list"].handleButton)
		self["list"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		self.clearSelectedKeys()
		selection = self["list"].getCurrent()
		longText = [""] * 2
		longButtons = []
		shiftButtons = []
		if selection:
			help = selection[4]
			self["description"].text = isinstance(help, (list, tuple)) and len(help) > 1 and help[1] or ""
			for button in selection[3]:
				if len(button) > 1:
					if button[1] == "SHIFT":
						self.selectKey("SHIFT")
						shiftButtons.append(button[0])
					elif button[1] == "long":
						longText[0] = _("Long key press")
						longButtons.append(button[0])
				self.selectKey(button[0])
			textline = 0
			if len(selection[3]) > 1:
				if longButtons:
					print("[HelpMenu] SelectionChanged: %s." % longButtons)
					longText[textline] = _("Long press: %s") % pgettext("Text list separator", ", ").join(longButtons)
					textline += 1
				if shiftButtons:
					longText[textline] = _("SHIFT: %s") % pgettext("Text list separator", ", ").join(shiftButtons)
		self["longshift_key0"].setText(longText[0])
		self["longshift_key1"].setText(longText[1])

	def showHelp(self):
		# MessageBox import deferred so that MessageBox's import of HelpMenu doesn't cause an import loop.
		from Screens.MessageBox import MessageBox
		self.session.open(MessageBox, HelpMenu.helpText, type=MessageBox.TYPE_INFO)


class HelpableScreen:
	def __init__(self):
		self["helpActions"] = ActionMap(["HelpActions"], {
			"displayHelp": self.showHelp
		}, prio=0)
		self["key_help"] = StaticText(_("HELP"))

	def showHelp(self):
		try:
			if self.secondInfoBarScreen and self.secondInfoBarScreen.shown:
				self.secondInfoBarScreen.hide()
		except Exception:
			pass
		self.session.openWithCallback(self.callHelpAction, HelpMenu, self.helpList)

	def callHelpAction(self, *args):
		if args:
			(actionmap, context, action) = args
			actionmap.action(context, action)
