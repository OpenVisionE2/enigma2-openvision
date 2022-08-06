# -*- coding: utf-8 -*-
from Screens.Wizard import WizardSummary
from Screens.WizardLanguage import WizardLanguage
from Screens.HelpMenu import ShowRemoteControl
from Plugins.SystemPlugins.Videomode.VideoHardware import video_hw
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.config import config, ConfigBoolean, configfile
from Components.SystemInfo import BoxInfo
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

has_hdmi = BoxInfo.getItem("hdmi")

config.misc.showtestcard = ConfigBoolean(default=False)


class VideoWizardSummary(WizardSummary):
	def __init__(self, session, parent):
		WizardSummary.__init__(self, session, parent)

	def setLCDPicCallback(self):
		self.parent.setLCDTextCallback(self.setText)

	def setLCDPic(self, file):
		self["pic"].instance.setPixmapFromFile(file)


class VideoWizard(WizardLanguage, ShowRemoteControl):
	skin = """
		<screen position="fill" title="Welcome..." flags="wfNoBorder" >
			<panel name="WizardMarginsTemplate"/>
			<panel name="WizardPictureLangTemplate"/>
			<panel name="RemoteControlTemplate"/>
			<panel position="left" size="10,*" />
			<panel position="right" size="10,*" />
			<panel position="fill">
				<widget name="text" position="top" size="*,270" font="Regular;23" valign="center" />
				<panel position="fill">
					<panel position="left" size="150,*">
						<widget name="portpic" position="top" zPosition="10" size="150,150" transparent="1" alphatest="on"/>
					</panel>
					<panel position="fill" layout="stack">
						<widget source="list" render="Listbox" position="fill" scrollbarMode="showOnDemand" >
							<convert type="StringList" />
						</widget>
						<!--<widget name="config" position="fill" zPosition="1" scrollbarMode="showOnDemand" />-->
					</panel>
				</panel>
			</panel>
		</screen>"""

	def __init__(self, session):
		# FIXME anyone knows how to use relative paths from the plugin's directory?
		self.xmlfile = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/Videomode/videowizard.xml")
		self.hw = video_hw

		WizardLanguage.__init__(self, session, showSteps=False, showStepSlider=False)
		ShowRemoteControl.__init__(self)
		self["wizard"] = Pixmap()
		self["portpic"] = Pixmap()
		self["lab1"] = StaticText(_("OpenVision"))
		self["lab2"] = StaticText(_("Lets define enigma2 once more"))
		self["lab3"] = StaticText(_("Report problems to:"))
		self["lab4"] = StaticText(_("https://openvision.tech"))
		self["lab5"] = StaticText(_("Sources are available at:"))
		self["lab6"] = StaticText(_("https://github.com/OpenVisionE2"))
		self.port = None
		self.mode = None
		self.rate = None

	def createSummary(self):
		print("[Videomode] VideoWizard createSummary")
		from Screens.Wizard import WizardSummary
		return VideoWizardSummary

	def markDone(self):
		self.hw.saveMode(self.port, self.mode, self.rate)
		config.misc.videowizardenabled.value = 0
		config.misc.videowizardenabled.save()
		configfile.save()

	def listInputChannels(self):
		list = []

		for port in self.hw.getPortList():
			if self.hw.isPortUsed(port):
				descr = port
				if descr == 'DVI' and has_hdmi:
					descr = 'HDMI'
				if port != "DVI-PC":
					list.append((descr, port))
		list.sort(key=lambda x: x[0])
		print("[Videomode] VideoWizard listInputChannels:", list)
		return list

	def inputSelectionMade(self, index):
		print("[Videomode] VideoWizard inputSelectionMade:", index)
		self.port = index
		self.inputSelect(index)

	def inputSelectionMoved(self):
		print("[Videomode] VideoWizard input selection moved:", self.selection)
		self.inputSelect(self.selection)
		if self["portpic"].instance is not None:
			picname = self.selection
			if picname == 'DVI' and has_hdmi:
				picname = "HDMI"
			self["portpic"].instance.setPixmapFromFile(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/Videomode/" + picname + ".png"))

	def inputSelect(self, port):
		print("[Videomode] VideoWizard inputSelect:", port)
		modeList = self.hw.getModeList(self.selection)
		print("[Videomode] VideoWizard modeList:", modeList)
		self.port = port
		if (len(modeList) > 0):
			ratesList = self.listRates(modeList[0][0])
			self.hw.setMode(port=port, mode=modeList[0][0], rate=ratesList[0][0])

	def listModes(self):
		list = []
		print("[Videomode] VideoWizard modes for port", self.port)
		for mode in self.hw.getModeList(self.port):
			#if mode[0] != "PC":
				list.append((mode[0], mode[0]))
		print("[Videomode] VideoWizard modeslist:", list)
		return list

	def modeSelectionMade(self, index):
		print("[Videomode] VideoWizard modeSelectionMade:", index)
		self.mode = index
		self.modeSelect(index)

	def modeSelectionMoved(self):
		print("[Videomode] VideoWizard mode selection moved:", self.selection)
		self.modeSelect(self.selection)

	def modeSelect(self, mode):
		ratesList = self.listRates(mode)
		print("[Videomode] VideoWizard ratesList:", ratesList)
		if self.port == "DVI" and mode in ("720p", "1080i", "1080p", "2160p", "2160p30"):
			if BoxInfo.getItem("Has24hz"):
				self.rate = "auto"
				self.hw.setMode(port=self.port, mode=mode, rate="auto")
			else:
				self.rate = "multi"
				self.hw.setMode(port=self.port, mode=mode, rate="multi")
		else:
			self.hw.setMode(port=self.port, mode=mode, rate=ratesList[0][0])

	def listRates(self, querymode=None):
		if querymode is None:
			querymode = self.mode
		list = []
		print("[Videomode] VideoWizard modes for port", self.port, "and mode", querymode)
		for mode in self.hw.getModeList(self.port):
			print("[Videomode] VideoWizard mode:", mode)
			if mode[0] == querymode:
				for rate in mode[1]:
					if self.port == "DVI-PC":
						print("[Videomode] VideoWizard rate:", rate)
						if rate == "640x480":
							list.insert(0, (rate, rate))
							continue
					list.append((rate, rate))
		return list

	def rateSelectionMade(self, index):
		print("[Videomode] VideoWizard rateSelectionMade:", index)
		self.rate = index
		self.rateSelect(index)

	def rateSelectionMoved(self):
		print("[Videomode] VideoWizard rate selection moved:", self.selection)
		self.rateSelect(self.selection)

	def rateSelect(self, rate):
		self.hw.setMode(port=self.port, mode=self.mode, rate=rate)

	def showTestCard(self, selection=None):
		if selection is None:
			selection = self.selection
		print("[Videomode] VideoWizard set config.misc.showtestcard to", {'yes': True, 'no': False}[selection])
		if selection == "yes":
			config.misc.showtestcard.value = True
		else:
			config.misc.showtestcard.value = False

	def keyNumberGlobal(self, number):
		if number in (1, 2, 3):
			if number == 1:
				self.hw.saveMode("DVI", "720p", "multi")
			elif number == 2:
				self.hw.saveMode("DVI", "1080i", "multi")
			elif number == 3:
				self.hw.saveMode("Scart", "Multi", "multi")
			self.hw.setConfiguredMode()
			self.close()

		WizardLanguage.keyNumberGlobal(self, number)
