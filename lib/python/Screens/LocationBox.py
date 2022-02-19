# Generic Screen to select a path/filename combination

from os import sep, statvfs
from os.path import exists, isdir, join as pathjoin
from six import PY2

from enigma import eTimer

from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import config
from Components.FileList import FileList
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.BoundFunction import boundFunction
from Tools.Directories import createDir, removeDir, renameDir
from Tools.NumericalTextInput import NumericalTextInput

BOOKMARKS_INDENT = 3

defaultInhibitDirs = ["/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/picon", "/piconlcd", "/proc", "/run", "/sbin", "/share", "/sys", "/tmp", "/usr", "/var"]


class LocationBox(Screen, NumericalTextInput, HelpableScreen):
	"""Simple Class similar to MessageBox / ChoiceBox but used to choose a directory/pathname combination"""

	skin = """
	<screen name="LocationBox" position="center,center" size="1000,570" resolution="1280,720">
		<widget name="text" position="10,10" size="e-20,25" font="Regular;20" transparent="1" valign="center" />
		<widget name="target" position="10,35" size="e-20,25" font="Regular;20" transparent="1" valign="center" />
		<widget name="filetext" position="10,70" size="e-20,25" backgroundColor="#00ffffff" font="Regular;20" foregroundColor="#00000000" valign="center" />
		<widget name="filelist" position="10,95" size="e-20,245" enableWrapAround="1" itemHeight="25" scrollbarMode="showOnDemand" transparent="1" />
		<widget name="quickselect" position="10,95" size="e-20,245" font="Regular;100" foregroundColor="#0000ffff" halign="center" transparent="1" valign="center" zPosition="+1" />
		<widget name="booktext" position="10,355" size="e-20,25" backgroundColor="#00ffffff" font="Regular;20" foregroundColor="#00000000" valign="center" />
		<widget name="booklist" position="10,380" size="e-20,125" font="Regular;20" itemHeight="25" scrollbarMode="showOnDemand" selectionDisabled="1" transparent="1" />
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="200,e-50" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="390,e-50" size="180,40" backgroundColor="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="580,e-50" size="180,40" backgroundColor="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_menu" render="Label" position="e-180,e-50" size="80,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-90,e-50" size="80,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, text="", filename="", currDir=None, bookmarks=None, userMode=False, windowTitle=None, minFree=None, autoAdd=False, editDir=False, inhibitDirs=None, inhibitMounts=None):
		Screen.__init__(self, session, mandatoryWidgets=["filetext", "quickselect"])
		NumericalTextInput.__init__(self, handleTimeout=False, mode="SearchUpper")
		HelpableScreen.__init__(self)
		if not inhibitDirs:
			inhibitDirs = []
		if not inhibitMounts:
			inhibitMounts = []
		self.text = text
		self.filename = filename
		self.bookmarks = bookmarks
		self.bookmarksList = bookmarks and bookmarks.value[:] or []
		self.bookmarksList.sort()
		self.userMode = userMode
		self.minFree = minFree
		self.autoAdd = autoAdd
		self.editDir = editDir
		self.inhibitDirs = inhibitDirs
		self["filetext"] = Label("  %s" % _("Directories"))
		self["filelist"] = FileList(currDir, showDirectories=True, showFiles=False, inhibitMounts=inhibitMounts, inhibitDirs=inhibitDirs, enableWrapAround=True)
		self["booktext"] = Label("  %s" % _("Bookmarks"))
		self["booklist"] = MenuList(self.formatBookmarks(self.bookmarksList), enableWrapAround=True)
		self["quickselect"] = Label("")
		self["quickselect"].visible = False
		self["text"] = Label(text)
		self["target"] = Label()
		self["key_menu"] = StaticText(_("MENU"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Select"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self.timer = eTimer()  # Initialize QuickSelect timer.
		self.timer.callback.append(self.timeout)
		self.timerType = 0
		self.quickSelect = ""
		self.quickSelectPos = -1

		class LocationBoxActionMap(HelpableActionMap):  # Custom action handler.
			def __init__(self, parent, context, actions=None, prio=0, description=None):
				HelpableActionMap.__init__(self, parent, context, actions, prio, description)
				self.box = parent

			def action(self, contexts, action):
				if action not in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9"):
					self.box.timeout(force=True)  # Reset QuickSelect on non numbers.
				return HelpableActionMap.action(self, contexts, action)

		# Actions that will reset QuickSelect...
		self["locationActions"] = LocationBoxActionMap(self, ["LocationBoxActions", "NavigationActions"], {
			"enter": (self.enter, (_("Change directory / Select bookmark"), _("If the upper panel is active pressing OK will change the current directory.  If the lower panel is active pressing OK will select the current bookmark and exit."))),
			"cancel": (self.cancel, _("Cancel the location selection")),
			"menu": (self.showMenu, _("Display context menu")),
			"top": (self.moveTop, _("Move up to first line")),
			"pageUp": (self.pageUp, _("Move up a screen")),
			"up": (self.moveUp, _("Move up a line")),
			"down": (self.moveDown, _("Mode down a line")),
			"pageDown": (self.pageDown, _("Mode down a screen")),
			"bottom": (self.moveBottom, _("Move down to last line"))
		}, prio=0, description=_("LocationBox Actions"))
		self["selectAction"] = LocationBoxActionMap(self, "LocationBoxActions", {
			"select": (self.select, _("Select the currently highlighted location and exit"))
		}, prio=0, description=_("LocationBox Actions"))
		self["selectAction"].setEnabled(True)
		self["panelActions"] = LocationBoxActionMap(self, ["LocationBoxActions", "NavigationActions"], {
			"first": (self.switchToFileList, _("Switch to directories panel")),
			"left": (self.switchToFileList, _("Switch to directories panel")),
			"right": (self.switchToBookList, _("Switch to bookmarks panel")),
			"last": (self.switchToBookList, _("Switch to bookmarks panel")),
			"swap": (self.swapPanels, _("Switch to the other panel"))
		}, prio=0, description=_("Panel Selection Actions"))
		self["panelActions"].setEnabled(True)
		self["bookmarkAction"] = LocationBoxActionMap(self, "LocationBoxActions", {
			"bookmark": (self.addDeleteBookmark, _("Add / Delete bookmark"))
		}, prio=0, description=_("Bookmark Actions"))
		self["bookmarkAction"].setEnabled(True)
		self["renameAction"] = LocationBoxActionMap(self, "LocationBoxActions", {
			"rename": (self.rename, _("Rename directory"))
		}, prio=0, description=_("Directory Actions"))
		self["renameAction"].setEnabled(False)
		# Action used by QuickSelect...
		smsMsg = _("SMS style QuickSelect location selection")
		self["numberActions"] = HelpableNumberActionMap(self, "NumberActions", {
			"1": (self.keyNumberGlobal, smsMsg),
			"2": (self.keyNumberGlobal, smsMsg),
			"3": (self.keyNumberGlobal, smsMsg),
			"4": (self.keyNumberGlobal, smsMsg),
			"5": (self.keyNumberGlobal, smsMsg),
			"6": (self.keyNumberGlobal, smsMsg),
			"7": (self.keyNumberGlobal, smsMsg),
			"8": (self.keyNumberGlobal, smsMsg),
			"9": (self.keyNumberGlobal, smsMsg),
			"0": (self.keyNumberGlobal, smsMsg)
		}, prio=0, description=_("Quick Select Actions"))
		self["numberActions"].setEnabled(True)
		if self.userMode:
			self.switchToBookList()
			self["filelist"].hide()
			self["bookmarkAction"].setEnabled(False)
			self["panelActions"].setEnabled(False)
		self.setTitle(_("Select Location") if windowTitle is None else windowTitle)
		if self.layoutFinished not in self.onLayoutFinish:
			self.onLayoutFinish.append(self.layoutFinished)

	def __repr__(self):
		return "%s(%s)" % (type(self), self.text)

	def layoutFinished(self):
		self["filelist"].instance.allowNativeKeys(False)  # Override listbox navigation.
		self["booklist"].instance.allowNativeKeys(False)  # Override listbox navigation.
		if self.bookmarksList:
			self.switchToBookList()
			currDir = self["filelist"].current_directory
			if currDir in self.bookmarksList:
				self["booklist"].moveToIndex(self.bookmarksList.index(currDir))
		else:
			self.switchToFileList()
		self.showHideRename()

	def switchToFileList(self):
		if not self.userMode:
			self.currList = "filelist"
			self["filelist"].selectionEnabled(True)
			self["booklist"].selectionEnabled(False)
			self["numberActions"].setEnabled(True)
			self["key_yellow"].setText(_("Add Bookmark"))
			self.updateTarget()

	def switchToBookList(self):
		if self.bookmarksList:  # Dont jump to bookmarks panel if there are no bookmarks.
			self.currList = "booklist"
			self["filelist"].selectionEnabled(False)
			self["booklist"].selectionEnabled(True)
			self["numberActions"].setEnabled(False)
			self["key_yellow"].setText(_("Delete Bookmark"))
			self.updateTarget()

	def swapPanels(self):
		if self.currList == "booklist":
			self.switchToFileList()
		else:
			self.switchToBookList()

	def updateTarget(self):
		directory = self.getCurrentSelection()
		if directory is None:
			self["target"].setText(_("Error: Invalid location!"))
			self["key_green"].setText("")
			self["selectAction"].setEnabled(False)
			self["bookmarkAction"].setEnabled(False)
			self["key_yellow"].setText("")
		else:
			self["target"].setText(pathjoin(directory, self.filename))
			self["key_green"].setText(_("Select"))
			self["selectAction"].setEnabled(True)
			if self.currList == "filelist" and directory not in self.bookmarksList:
				self["bookmarkAction"].setEnabled(True)
				self["key_yellow"].setText(_("Add Bookmark"))
			elif self.currList == "booklist":
				self["bookmarkAction"].setEnabled(True)
				self["key_yellow"].setText(_("Delete Bookmark"))
			else:
				self["bookmarkAction"].setEnabled(False)
				self["key_yellow"].setText("")
		if self.bookmarksList and not self.userMode:  # DEBUG: This may be a problem in userMode when there are NO bookmarks available!!!
			self["panelActions"].setEnabled(True)
		else:
			self["panelActions"].setEnabled(False)

	def getCurrentSelection(self):
		return self["filelist"].getSelection()[0] if self.currList == "filelist" else self["booklist"].getCurrent()[BOOKMARKS_INDENT:]

	def showHideRename(self):
		if self.filename == "":  # Don't allow renaming when filename is empty.
			self["renameAction"].setEnabled(False)
			self["key_blue"].setText("")
		else:
			self["renameAction"].setEnabled(True)
			self["key_blue"].setText(_("Rename"))

	def rename(self):
		self.session.openWithCallback(self.renameCallback, VirtualKeyBoard, title=_("Please enter a new filename"), text=self.filename)

	def renameCallback(self, filename):
		if filename is not None:
			if len(filename):
				self.filename = filename
				self.updateTarget()
			else:
				self.session.open(MessageBox, _("Error: The filename may not be blank!"), type=MessageBox.TYPE_ERROR, timeout=5)

	def moveTop(self):
		self[self.currList].top()
		self.updateTarget()

	def pageUp(self):
		self[self.currList].pageUp()
		self.updateTarget()

	def moveUp(self):
		self[self.currList].up()
		self.updateTarget()

	def moveDown(self):
		self[self.currList].down()
		self.updateTarget()

	def pageDown(self):
		self[self.currList].pageDown()
		self.updateTarget()

	def moveBottom(self):
		self[self.currList].bottom()
		self.updateTarget()

	def showMenu(self):
		if not self.userMode and self.bookmarksList:
			if self.currList == "filelist":
				menu = [(_("Switch to bookmarks panel"), self.switchToBookList)]
				if self["filelist"].current_directory is not None:
					menu.append((_("Add bookmark"), self.addDeleteBookmark))
				menu.append((_("Reload bookmarks"), self.reloadBookmarks))
				if self.editDir and self["filelist"].current_directory is not None:
					menu.extend((
						(_("Create directory"), self.createDirectory),
						(_("Rename directory"), self.renameDirectory),
						(_("Delete directory"), self.deleteDirectory)
					))
			else:
				menu = [(_("Switch to directories panel"), self.switchToFileList)]
				if self.bookmarksList:
					menu.append((_("Delete bookmark"), self.addDeleteBookmark))
				menu.append((_("Reload bookmarks"), self.reloadBookmarks))
			self.session.openWithCallback(self.menuCallback, ChoiceBox, title=_("Location Box Context Menu"), list=menu)

	def menuCallback(self, choice):
		if choice:
			choice[1]()

	def addDeleteBookmark(self):
		directory = self.getCurrentSelection()
		if self.currList == "filelist":  # Add bookmark.
			if directory is not None and directory not in self.bookmarksList:
				self.bookmarksList.append(directory)
				self.bookmarksList.sort()
				self["booklist"].setList(self.formatBookmarks(self.bookmarksList))
				self.updateTarget()
		elif not self.userMode:  # Delete bookmark.
			self.session.openWithCallback(boundFunction(self.addDeleteBookmarkCallback, directory), MessageBox, _("Do you really want to delete the '%s' bookmark?") % directory)

	def addDeleteBookmarkCallback(self, directory, answer):
		if answer and directory in self.bookmarksList:
			self.bookmarksList.remove(directory)
			self["booklist"].setList(self.formatBookmarks(self.bookmarksList))
			if self.bookmarksList:
				self.updateTarget()
			else:
				self.switchToFileList()

	def formatBookmarks(self, bookmarks):
		return ["%s%s" % (" " * BOOKMARKS_INDENT, x) for x in bookmarks]

	def reloadBookmarks(self):
		self.bookmarksList = self.bookmarks and self.bookmarks.value[:] or []
		self.bookmarksList.sort()
		self["booklist"].setList(self.bookmarksList)

	def createDirectory(self):
		if self["filelist"].current_directory is not None:
			self.session.openWithCallback(self.createDirectoryCallback, VirtualKeyBoard, title=_("Enter name of new directory:"), text=self.filename)

	def createDirectoryCallback(self, directory):
		if directory:
			path = pathjoin(self["filelist"].current_directory, directory)
			if isdir(path):
				self.session.open(MessageBox, _("Error: Directory '%s' already exists!") % path, type=MessageBox.TYPE_ERROR, timeout=5)
			elif createDir(path):
				self["filelist"].refresh()
			else:
				self.session.open(MessageBox, _("Error: Unable to create directory '%s'!") % path, type=MessageBox.TYPE_ERROR, timeout=5)

	def renameDirectory(self):
		directory = self["filelist"].getSelection()
		if directory and isdir(directory[0]):
			name = directory[0][:-1].split(sep)[-1]  # Extract the directory name, not the absolute path.
			self.session.openWithCallback(boundFunction(self.renameDirectoryCallback, directory[0]), VirtualKeyBoard, title=_("Enter new directory name:"), text=name)
		else:
			self.session.open(MessageBox, _("Error: Invalid directory '%s' selected!") % directory[0], type=MessageBox.TYPE_ERROR, timeout=5)

	def renameDirectoryCallback(self, directory, newName):
		if newName:
			newPath = pathjoin(self["filelist"].current_directory, newName)
			if exists(newPath):
				self.session.open(MessageBox, _("Error: File or directory '%s' already exists!") % newPath, type=MessageBox.TYPE_ERROR, timeout=5)
			elif renameDir(directory, newPath):
				self["filelist"].refresh()
			else:
				self.session.open(MessageBox, _("Error: Unable to rename directory '%s' to '%s'!") % (directory, newPath), type=MessageBox.TYPE_ERROR, timeout=5)

	def deleteDirectory(self):
		directory = self["filelist"].getSelection()
		if directory and isdir(directory[0]):
			self.session.openWithCallback(boundFunction(self.deleteDirectoryCallback, directory[0]), MessageBox, _("Do you really want to delete the '%s' directory?") % directory[0])
		else:
			self.session.open(MessageBox, _("Error: Invalid directory '%s' selected!") % directory[0], type=MessageBox.TYPE_ERROR, timeout=5)

	def deleteDirectoryCallback(self, directory, answer):
		if answer:
			if removeDir(directory):
				self["filelist"].refresh()
				self.addDeleteBookmarkCallback(directory, True)
			else:
				self.session.open(MessageBox, _("Error: Unable to delete directory '%s'! (Diretory may not be empty.)") % directory, type=MessageBox.TYPE_ERROR, timeout=5)

	def enter(self):
		if self.currList == "filelist":
			if self["filelist"].canDescent():
				self["filelist"].descent()
				self.updateTarget()
		else:
			self.select()

	def cancel(self):
		self.disableTimer()
		self.close(None)

	def select(self):
		currentFolder = self.getCurrentSelection()
		if currentFolder is not None:  # Do nothing unless current directory is valid.
			if self.minFree is None:  # Check if we need to have a minimum of free space available.
				self.selectConfirmed(True)  # There is no minimum space requirement.
			else:
				try:  # Try to read fs stats.
					stats = statvfs(currentFolder)
					if (stats.f_bavail * stats.f_bsize) / 1000000 > self.minFree:
						return self.selectConfirmed(True)  # There is enough free space.
				except (IOError, OSError):
					pass
				self.session.openWithCallback(self.selectConfirmed, MessageBox, _("There may not be enough space on the selected location.\n\nDo you really want to continue?"))

	def selectConfirmed(self, answer):
		if answer:
			path = pathjoin(self.getCurrentSelection(), self.filename)
			if self.bookmarks and self.bookmarksList != sorted(self.bookmarks.value):
				self.bookmarks.value = self.bookmarksList
				self.bookmarks.save()
			self.disableTimer()
			self.close(path)

	def keyNumberGlobal(self, digit):
		self.timer.stop()
		if self.lastKey != digit:  # Is this a different digit?
			self.nextKey()  # Reset lastKey again so NumericalTextInput triggers its keychange.
			self.selectByStart()
			self.quickSelectPos += 1
		char = self.getKey(digit)  # Get char and append to text.
		self.quickSelect = self.quickSelect[:self.quickSelectPos] + (unicode(char) if PY2 else str(char))
		self["quickselect"].setText(self.quickSelect)
		self["quickselect"].visible = True
		self.timerType = 0
		self.timer.start(1000, 1)  # Allow 1 second to select the desired character for the QuickSelect text.

	def timeout(self, force=False):
		if not force and self.timerType == 0:
			self.selectByStart()
			self.timerType = 1
			self.timer.start(2000, 1)  # Allow 2 seconds before reseting the QuickSelect text.
		else:  # Timeout QuickSelect
			self.timer.stop()
			self.quickSelect = ""
			self.quickSelectPos = -1
		self.lastKey = -1  # Finalise current character.

	def selectByStart(self):  # Try to select what was typed so far.
		currentDir = self["filelist"].getCurrentDirectory()
		if currentDir and self.quickSelect:  # Don't try to select if there is no directory or QuickSelect text.
			self["quickselect"].visible = False
			self["quickselect"].setText("")
			pattern = pathjoin(currentDir, self.quickSelect).lower()
			files = self["filelist"].getFileList()  # Files returned by getFileList() are absolute paths.
			for index, file in enumerate(files):
				if file[0][0] and file[0][0].lower().startswith(pattern):  # Select first file starting with case insensitive QuickSelect text.
					self["filelist"].instance.moveSelectionTo(index)
					self.updateTarget()
					break

	def disableTimer(self):
		self.timer.stop()
		self.timer.callback.remove(self.timeout)


class MovieLocationBox(LocationBox):
	def __init__(self, session, text, currDir, filename="", minFree=None):
		LocationBox.__init__(
			self,
			session,
			text=text,
			filename=filename,
			currDir=currDir,
			bookmarks=config.movielist.videodirs,
			# userMode=False,
			windowTitle=_("Select Movie Location"),
			minFree=minFree,
			autoAdd=config.movielist.add_bookmark.value,
			editDir=True,
			inhibitDirs=defaultInhibitDirs,
			# inhibitMounts=None
		)
		self.skinName = "LocationBox"


class TimeshiftLocationBox(LocationBox):
	def __init__(self, session):
		LocationBox.__init__(
			self,
			session,
			text=_("Where to save temporary timeshift recordings?"),
			currDir=config.usage.timeshift_path.value,
			bookmarks=config.usage.allowed_timeshift_paths,
			# userMode=False,
			windowTitle=_("Select Timeshift Location"),
			minFree=1024,  # The same minFree requirement is hardcoded in servicedvb.cpp.
			autoAdd=True,
			editDir=True,
			inhibitDirs=defaultInhibitDirs,
			# inhibitMounts=None
		)
		self.skinName = "LocationBox"

	def cancel(self):
		config.usage.timeshift_path.cancel()
		LocationBox.cancel(self)

	def selectConfirmed(self, answer):
		if answer:
			config.usage.timeshift_path.value = self.getCurrentSelection()
			config.usage.timeshift_path.save()
			LocationBox.selectConfirmed(self, answer)
