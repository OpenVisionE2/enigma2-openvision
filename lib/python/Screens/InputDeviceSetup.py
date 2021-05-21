from Components.ActionMap import HelpableActionMap
from Components.config import ConfigSelection, ConfigYesNo, config, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.InputDevice import REMOTE_DISPLAY_NAME, REMOTE_MACHINE_BUILD, REMOTE_RCTYPE, inputDevices, remoteControl
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.Setup import Setup
from Tools.Directories import SCOPE_CURRENT_SKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap


class InputDeviceSelection(Screen, HelpableScreen):
	skin = """
	<screen name="InputDeviceSelection" position="center,center" size="560,400">
		<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="list" render="Listbox" position="5,50" size="550,280" zPosition="10" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				<!--  device, description, devicepng, divpng  -->
				{
				"template": [
					MultiContentEntryPixmapAlphaBlend(pos = (2, 8), size = (54, 54), png = 2),  # Index 3 is the interface pixmap
					MultiContentEntryText(pos = (65, 6), size = (450, 54), font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER | RT_WRAP, text = 1)  # Index 1 is the interfacename
				],
				"fonts": [gFont("Regular", 28), gFont("Regular", 20)],
				"itemHeight": 70
				}
			</convert>
		</widget>
		<ePixmap pixmap="div-h.png" position="0,340" zPosition="1" size="560,2"/>
		<widget source="introduction" render="Label" position="0,350" size="560,50" zPosition="10" font="Regular;21" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setTitle(_("Select Input Device"))
		self["deviceActions"] = HelpableActionMap(self, ["OkCancelActions"], {
			"ok": (self.keySelect, _("Select input device")),
			"cancel": (self.keyClose, _("Exit input device selection")),
			"close": (self.keyCloseRecursive, _("Exit input device selection and close all menus"))
		}, prio=-2, description=_("Input Device Actions"))
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Select"))
		self["introduction"] = StaticText(_("Press OK to edit the settings of the selected device."))
		self["list"] = List()
		self.devices = [(inputDevices.getDeviceName(x), x) for x in inputDevices.getDeviceList()]
		# for index, device in enumerate(self.devices):
		# 	print("[InputDeviceSetup] DEBUG: Found device #%d: Event='%s' -> '%s'." % (index, device[1], device[0]))
		self.updateList()

	def keySelect(self):
		selection = self["list"].getCurrent()
		if selection is not None:
			self.session.openWithCallback(self.keySelectClosed, InputDeviceDriverSetup, selection[0])

	def keySelectClosed(self, *ret):
		self.updateList()

	def keyClose(self):
		self.close()

	def keyCloseRecursive(self):
		self.close(True)

	def updateList(self):
		deviceIndex = self["list"].getIndex()
		deviceList = []
		for device in self.devices:
			deviceList.append(self.buildInterfaceList(device[1], _(device[0]), inputDevices.getDeviceAttribute(device[1], "type")))
		self["list"].setList(deviceList)
		size = len(deviceList)
		if deviceIndex >= size:
			deviceIndex = size - 1 if size else 0
		self["list"].setIndex(deviceIndex)

	def buildInterfaceList(self, device, description, type, isInputDevice=True):
		enabled = "-configured" if inputDevices.getDeviceAttribute(device, "enabled") else ""
		if type == "remote":
			deviceImage = "icons/input_rcnew%s.png" % enabled
		elif type == "keyboard":
			deviceImage = "icons/input_keyboard%s.png" % enabled
		elif type == "mouse":
			deviceImage = "icons/input_mouse%s.png" % enabled
		elif isInputDevice:
			deviceImage = "icons/input_rcnew.png"
		else:
			deviceImage = None
		if deviceImage:
			deviceImage = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, deviceImage))
		divImage = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "div-h.png"))
		return ((device, description, deviceImage, divImage))


class InputDeviceDriverSetup(Setup):
	def __init__(self, session, device):
		self.device = device
		inputDevices.currentDevice = device
		configItem = getattr(config.inputDevices, device)
		self.enableEntry = getConfigListEntry(self.formatItemText(_("Change device settings")), configItem.enabled, self.formatItemDescription(configItem.enabled, _("Select 'Yes' to enable editing of this device's settings. Selecting 'No' resets the devices settings to their default values.")))
		self.nameEntry = getConfigListEntry(self.formatItemText(_("Device name")), configItem.name, self.formatItemDescription(configItem.name, _("Enter a new name for this device.")))
		self.delayEntry = getConfigListEntry(self.formatItemText(_("Delay before key repeat starts (ms)")), configItem.delay, self.formatItemDescription(configItem.delay, _("Select the time delay before the button starts repeating.")))
		self.repeatEntry = getConfigListEntry(self.formatItemText(_("Interval between keys when repeating (ms)")), configItem.repeat, self.formatItemDescription(configItem.repeat, _("Select the time delay between each repeat of the button.")))
		Setup.__init__(self, session, "DriverSettings")
		self.setTitle(_("Input Device Driver Setup"))
		self.skinName.insert(0, "InputDeviceDriverSetup")

	def createSetup(self):
		settingsList = []
		if self.enableEntry and isinstance(self.enableEntry[1], ConfigYesNo):
			settingsList.append(self.enableEntry)
			if self.enableEntry[1].value is True:
				settingsList.append(self.nameEntry)
				settingsList.append(self.delayEntry)
				settingsList.append(self.repeatEntry)
			else:
				self.nameEntry[1].setValue(self.nameEntry[1].default)
				self.delayEntry[1].setValue(self.delayEntry[1].default)
				self.repeatEntry[1].setValue(self.repeatEntry[1].default)
		self["config"].list = settingsList

	def keySave(self):
		self.session.openWithCallback(self.keySaveConfirm, MessageBox, _("Use these input device settings for '%s' (%s)?") % (self.device, self.nameEntry[1].value), MessageBox.TYPE_YESNO, timeout=20, default=True)

	def keySaveConfirm(self, confirmed):
		if confirmed:
			configItem = getattr(config.inputDevices, self.device)
			configItem.save()
			print("[InputDeviceSetup] Changes made for '%s' (%s) saved." % (self.device, self.nameEntry[1].value))
			return Setup.keySave(self)
		else:
			print("[InputDeviceSetup] Changes made for '%s' (%s) were not confirmed." % (self.device, self.nameEntry[1].value))


class InputDeviceSetup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "InputDevices")
		self.initialKeyboardMap = config.inputDevices.keyboardMap.value
		self.initialRemotesIndex = config.inputDevices.remotesIndex.value

	def keySave(self):
		map = config.inputDevices.keyboardMap.value
		if map != self.initialKeyboardMap:
			print("[InputDevice] Activating keyboard keymap: '%s'." % map)
			mapPath = resolveFilename(SCOPE_KEYMAPS, map)
			if isfile(mapPath):
				Console().ePopen("/sbin/loadkmap < %s" % mapPath)
			else:
				print("[InputDevice] Error: Selected keyboard keymap file '%s' doesn't exist!" % mapPath)
		index = config.inputDevices.remotesIndex.value
		if index != self.initialRemotesIndex:
			index = int(index)
			rcType = config.inputDevices.remotesIndex.default if index == 0 else remoteControl.remotes[index][REMOTE_RCTYPE]
			if rcType:
				remoteControl.writeRemoteControlType(rcType)
				print("[InputDeviceSetup] Trying remote control index=%d, getMachineBuild='%s', rcType='%s', name='%s'." % (index, remoteControl.remotes[index][REMOTE_MACHINE_BUILD], remoteControl.remotes[index][REMOTE_RCTYPE], remoteControl.remotes[index][REMOTE_DISPLAY_NAME]))
			else:
				print("[InputDeviceSetup] Remote control index=%d, getMachineBuild='%s', rcType='%s', name='%s' does not use rcType." % (index, remoteControl.remotes[index][REMOTE_MACHINE_BUILD], remoteControl.remotes[index][REMOTE_RCTYPE], remoteControl.remotes[index][REMOTE_DISPLAY_NAME]))
			self.session.openWithCallback(self.keySaveCallback, MessageBox, _("Is the remote control working okay?"), MessageBox.TYPE_YESNO, timeout=10, default=False, timeout_default=False)
			return
		Setup.keySave(self)

	def keySaveCallback(self, answer):
		if answer:
			return Setup.keySave(self)
		self.restoreOldSetting()

	def keyCancel(self):
		self.restoreOldSetting()
		return Setup.keyCancel(self)

	def restoreOldSetting(self):
		config.inputDevices.remotesIndex.value = self.initialRemotesIndex
		index = int(self.initialRemotesIndex)
		remoteControl.writeRemoteControlType(remoteControl.remotes[index][REMOTE_RCTYPE])
		print("[InputDeviceSetup] Restoring remote control index=%d, getMachineBuild='%s', rcType='%s', name='%s'." % (index, remoteControl.remotes[index][REMOTE_MACHINE_BUILD], remoteControl.remotes[index][REMOTE_RCTYPE], remoteControl.remotes[index][REMOTE_DISPLAY_NAME]))
		for item in self["config"].list:
			self["config"].invalidate(item)
