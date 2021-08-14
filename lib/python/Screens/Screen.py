from enigma import eRCInput, eTimer, eWindow, getDesktop

from skin import GUI_SKIN_ID, applyAllAttributes
from Components.config import config
from Components.GUIComponent import GUIComponent
from Components.Sources.Source import Source
from Components.Sources.StaticText import StaticText
from Tools.CList import CList


# The lines marked DEBUG: are proposals for further fixes or improvements when partner code is updated.
#
class Screen(dict):
	NO_SUSPEND, SUSPEND_STOPS, SUSPEND_PAUSES = list(range(3))
	ALLOW_SUSPEND = NO_SUSPEND
	globalScreen = None

	def __init__(self, session, parent=None, mandatoryWidgets=None):
		dict.__init__(self)
		self.skinName = self.__class__.__name__
		self.session = session
		self.parent = parent
		self.mandatoryWidgets = mandatoryWidgets
		self.onClose = []
		self.onFirstExecBegin = []
		self.onExecBegin = []
		self.onExecEnd = []
		self.onLayoutFinish = []
		self.onShown = []
		self.onShow = []
		self.onHide = []
		self.execing = False
		self.shown = True
		# DEBUG: Variable already_shown used in CutListEditor/ui.py and StartKodi/plugin.py.
		# DEBUG: self.alreadyShown = False  # Already shown is false until the screen is really shown (after creation).
		self.already_shown = False  # Already shown is false until the screen is really shown (after creation).
		self.renderer = []
		self.helpList = []  # In order to support screens *without* a help, we need the list in every screen. how ironic.
		self.close_on_next_exec = None
		# DEBUG: Variable already_shown used in webinterface/src/WebScreens.py.
		# DEBUG: self.standAlone = False  # Stand alone screens (for example web screens) don't care about having or not having focus.
		self.stand_alone = False  # Stand alone screens (for example web screens) don't care about having or not having focus.
		self.keyboardMode = None
		self.desktop = None
		self.instance = None
		self.summaries = CList()
		self["Title"] = StaticText()
		self["ScreenPath"] = StaticText()
		self.screenPath = ""  # This is the current screen path without the title.
		self.screenTitle = ""  # This is the current screen title without the path.

	def __repr__(self):
		return str(type(self))

	def execBegin(self):
		self.activeComponents = []
		if self.close_on_next_exec is not None:
			tmp = self.close_on_next_exec
			self.close_on_next_exec = None
			self.execing = True
			self.close(*tmp)
		else:
			single = self.onFirstExecBegin
			self.onFirstExecBegin = []
			for callback in self.onExecBegin + single:
				callback()
				# DEBUG: if not self.standAlone and self.session.current_dialog != self:
				if not self.stand_alone and self.session.current_dialog != self:
					return
			# assert self.session is None, "[Screen] A screen can only exec once per time!"
			# self.session = session
			for value in list(self.values()) + self.renderer:
				value.execBegin()
				# DEBUG: if not self.standAlone and self.session.current_dialog != self:
				if not self.stand_alone and self.session.current_dialog != self:
					return
				self.activeComponents.append(value)
			self.execing = True
			for callback in self.onShown:
				callback()

	def execEnd(self):
		for component in self.activeComponents:
			component.execEnd()
		self.activeComponents = []
		self.execing = False
		for callback in self.onExecEnd:
			callback()

	def doClose(self):  # Never call this directly - it will be called from the session!
		self.hide()
		for callback in self.onClose:
			callback()
		del self.helpList  # Fixup circular references.
		self.deleteGUIScreen()
		# First disconnect all render from their sources. We might split this out into
		# a "unskin"-call, but currently we destroy the screen afterwards anyway.
		for item in self.renderer:
			item.disconnectAll()  # Disconnect converter/sources and probably destroy them. Sources will not be destroyed.
		del self.session
		for (name, item) in list(self.items()):
			item.destroy()
			del self[name]
		self.renderer = []
		self.__dict__.clear()  # Really delete all elements now.

	def close(self, *retval):
		if not self.execing:
			self.close_on_next_exec = retval
		else:
			self.session.close(self, *retval)

	def show(self):
		print("[Screen] Showing screen '%s'." % self.skinName)  # To ease identification of screens.
		# DEBUG: if (self.shown and self.alreadyShown) or not self.instance:
		if (self.shown and self.already_shown) or not self.instance:
			return
		self.shown = True
		# DEBUG: self.alreadyShown = True
		self.already_shown = True
		self.instance.show()
		for callback in self.onShow:
			callback()
		for value in list(self.values()) + self.renderer:
			if isinstance(value, GUIComponent) or isinstance(value, Source):
				value.onShow()

	def hide(self):
		if not self.shown or not self.instance:
			return
		self.shown = False
		self.instance.hide()
		for callback in self.onHide:
			callback()
		for value in list(self.values()) + self.renderer:
			if isinstance(value, GUIComponent) or isinstance(value, Source):
				value.onHide()

	def isAlreadyShown(self):  # Already shown is false until the screen is really shown (after creation).
		return self.already_shown

	def isStandAlone(self):  # Stand alone screens (for example web screens) don't care about having or not having focus.
		return self.stand_alone

	def getScreenPath(self):
		return self.screenPath

	def setTitle(self, title, showPath=True):
		try:  # This protects against calls to setTitle() before being fully initialised like self.session is accessed *before* being defined.
			self.screenPath = ""
			# These two lines are the old shortcut code, kept for reference.
			# if self.session and len(self.session.dialog_stack) > 1:
			# 	self.screenPath = " > ".join(dialog[0].getTitle() for dialog in self.session.dialog_stack[1:])
			if self.session.dialog_stack:
				screenClasses = [dialog[0].__class__.__name__ for dialog in self.session.dialog_stack]
				if "MainMenu" in screenClasses:
					index = screenClasses.index("MainMenu")
					if self.session and len(screenClasses) > index:
						self.screenPath = " > ".join(dialog[0].getTitle() for dialog in self.session.dialog_stack[index:])
			if self.instance:
				self.instance.setTitle(title)
			self.summaries.setTitle(title)
		except AttributeError:
			pass
		self.screenTitle = title
		if showPath and config.usage.showScreenPath.value == "large" and title:
			screenPath = ""
			screenTitle = "%s > %s" % (self.screenPath, title) if self.screenPath else title
		elif showPath and config.usage.showScreenPath.value == "small":
			screenPath = "%s >" % self.screenPath if self.screenPath else ""
			screenTitle = title
		else:
			screenPath = ""
			screenTitle = title
		self["ScreenPath"].text = screenPath
		self["Title"].text = screenTitle

	def getTitle(self):
		return self.screenTitle

	title = property(getTitle, setTitle)

	def setFocus(self, object):
		self.instance.setFocus(object.instance)

	def setKeyboardModeNone(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)

	def setKeyboardModeAscii(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmAscii)

	def restoreKeyboardMode(self):
		rcinput = eRCInput.getInstance()
		if self.keyboardMode is not None:
			rcinput.setKeyboardMode(self.keyboardMode)

	def saveKeyboardMode(self):
		rcinput = eRCInput.getInstance()
		self.keyboardMode = rcinput.getKeyboardMode()

	def setDesktop(self, desktop):
		self.desktop = desktop

	def setAnimationMode(self, mode):
		if self.instance:
			self.instance.setAnimationMode(mode)

	def getRelatedScreen(self, name):
		if name == "session":
			return self.session.screen
		elif name == "parent":
			return self.parent
		elif name == "global":
			return self.globalScreen
		return None

	def callLater(self, function):
		self.__callLaterTimer = eTimer()
		self.__callLaterTimer.callback.append(function)
		self.__callLaterTimer.start(0, True)

	def applySkin(self):
		bounds = (getDesktop(GUI_SKIN_ID).size().width(), getDesktop(GUI_SKIN_ID).size().height())
		resolution = bounds
		zPosition = 0
		for (key, value) in self.skinAttributes:
			if key == "resolution":
				resolution = tuple([int(x.strip()) for x in value.split(",")])
			elif key == "zPosition":
				zPosition = int(value)
		if not self.instance:
			self.instance = eWindow(self.desktop, zPosition)
		if "title" not in self.skinAttributes and self.screenTitle:
			self.skinAttributes.append(("title", self.screenTitle))
		else:
			for attribute in self.skinAttributes:
				if attribute[0] == "title":
					self.setTitle(_(attribute[1]))
		self.scale = ((bounds[0], resolution[0]), (bounds[1], resolution[1]))
		applyAllAttributes(self.instance, self.desktop, self.skinAttributes, self.scale)
		self.createGUIScreen(self.instance, self.desktop)

	def createGUIScreen(self, parent, desktop, updateonly=False):
		for item in self.renderer:
			if isinstance(item, GUIComponent):
				if not updateonly:
					item.GUIcreate(parent)
				if not item.applySkin(desktop, self):
					print("[Screen] Warning: Skin is missing renderer '%s' in %s." % (item, str(self)))
		for (name, item) in self.items():
			if isinstance(item, GUIComponent):
				if not updateonly:
					item.GUIcreate(parent)
				depr = item.deprecationInfo
				if item.applySkin(desktop, self):
					if depr:
						print("[Screen] WARNING: OBSOLETE COMPONENT '%s' USED IN SKIN. USE '%s' INSTEAD!" % (key, depr[0]))
						print("[Screen] OBSOLETE COMPONENT WILL BE REMOVED %s, PLEASE UPDATE!" % depr[1])
				elif not depr:
					print("[Screen] Warning: Skin is missing element '%s' in %s." % (key, str(self)))
		for item in self.additionalWidgets:
			if not updateonly:
				item.instance = item.widget(parent)
			applyAllAttributes(item.instance, desktop, item.skinAttributes, self.scale)
		for callback in self.onLayoutFinish:
			if not isinstance(callback, type(self.close)):
				# The following command triggers an error in Puthon 3 even if a PY2 test is used!!!
				exec callback in globals(), locals()  # Use this version for Python 2.
				# exec(callback, globals(), locals())  # Use this version for Python 3.
			else:
				callback()

	def deleteGUIScreen(self):
		for (name, item) in self.items():
			if isinstance(item, GUIComponent):
				item.GUIdelete()

	def createSummary(self):
		return None

	def addSummary(self, summary):
		if summary is not None:
			self.summaries.append(summary)

	def removeSummary(self, summary):
		if summary is not None:
			self.summaries.remove(summary)


class ScreenSummary(Screen):
	skin = """
	<screen position="fill" flags="wfNoBorder">
		<widget source="global.CurrentTime" render="Label" position="0,0" size="e,20" font="Regular;16" halign="center" valign="center">
			<convert type="ClockToText">WithSeconds</convert>
		</widget>
		<widget source="Title" render="Label" position="0,25" size="e,45" font="Regular;18" halign="center" valign="center" />
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["Title"] = StaticText(parent.getTitle())
		names = parent.skinName
		if not isinstance(names, list):
			names = [names]
		self.skinName = ["%sSummary" % x for x in names]
		self.skinName.append("ScreenSummary")
		self.skinName += ["%s_summary" % x for x in names]  # DEBUG: Old summary screens currently kept for compatibility.
		self.skinName.append("SimpleSummary")  # DEBUG: Old summary screens currently kept for compatibility.
		self.skin = parent.__dict__.get("skinSummary", self.skin)  # If parent has a "skinSummary" defined, use that as default.
