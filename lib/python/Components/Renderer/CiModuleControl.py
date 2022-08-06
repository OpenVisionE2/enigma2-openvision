# -*- coding: utf-8 -*-
from Components.Renderer.Renderer import Renderer
from enigma import eDVBCI_UI, eLabel, iPlayableService
from Components.SystemInfo import BoxInfo
from Components.VariableText import VariableText
from os import popen


class CiModuleControl(Renderer, VariableText):
	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)
		self.eDVBCIUIInstance = eDVBCI_UI.getInstance()
		self.eDVBCIUIInstance and self.eDVBCIUIInstance.ciStateChanged.get().append(self.ciModuleStateChanged)
		self.text = ""
		self.allVisible = False
		self.no_visible_state1 = "ciplushelper" in popen("top -n 1").read()

	GUI_WIDGET = eLabel

	def applySkin(self, desktop, parent):
		attribs = self.skinAttributes[:]
		for (attrib, value) in self.skinAttributes:
			if attrib == "allVisible":
				self.allVisible = value == "1"
				attribs.remove((attrib, value))
				break
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def ciModuleStateChanged(self, slot):
		self.changed(True)

	def changed(self, what):
		if what == True or what[0] == self.CHANGED_SPECIFIC and what[1] == iPlayableService.evStart:
			string = ""
			NUM_CI = BoxInfo.getItem("CommonInterface")
			if NUM_CI and NUM_CI > 0:
				if self.eDVBCIUIInstance:
					for slot in range(NUM_CI):
						state = self.eDVBCIUIInstance.getState(slot)
						if state == 1 and self.no_visible_state1:
							continue
						add_num = True
						if string:
							string += " "
						if state not in (-1, 3):
							if state == 0:
								if not self.allVisible:
									string += ""
									add_num = False
								else:
									string += "\c007f7f7f"
							elif state == 1:
								string += "\c00ffff00"
							elif state == 2:
								string += "\c0000ff00"
						else:
							if not self.allVisible:
								string += ""
								add_num = False
							else:
								string += "\c00ff2525"
						if add_num:
							string += "%d" % (slot + 1)
					if string:
						string = _("CI slot: ") + string
			self.text = string
