# -*- coding: utf-8 -*-
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Console import Console
from Components.ScrollLabel import ScrollLabel
from Screens.Screen import Screen


class AboutUserInstalledPlugins(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("User installed plugins"))
		self.skinName = ["Information"]

		self["key_red"] = self["red"] = Label(_("Close"))
		self["actions"] = ActionMap(["SetupActions", "NavigationActions"],
		{
			"cancel": self.close,
			"up": self.pageUp,
			"down": self.pageDown,
			"left": self.pageUp,
			"right": self.pageDown,
			"pageUp": self.pageUp,
			"pageDown": self.pageDown,
		}, -2)

		self.Console = Console()
		self["information"] = ScrollLabel()
		self.onLayoutFinish.append(self.checkOPKG)

	def checkOPKG(self):
		self.Console.ePopen("opkg status", self.readOPKG)

	def readOPKG(self, result, retval, extra_args):
		if result:
			plugins_out = []
			opkg_status_list = result.split("\n\n")
			for opkg_status in opkg_status_list:
				plugin = ""
				opkg_status_split = opkg_status.split("\n")
				for line in opkg_status_split:
					if line.startswith("Package"):
						parts = line.strip().split()
						if len(parts) > 1 and parts[1] not in ("opkg", "openvision-bootlogo"):
							plugin = parts[1]
							continue
					if plugin and line.startswith("Status") and "user installed" in line:
						plugins_out.append(plugin)
						break
			self["information"].setText("\n".join(sorted(plugins_out)))
		else:
			self["information"].setText(_("No user installed plugins found"))

	def pageUp(self):
		self["information"].pageUp()

	def pageDown(self):
		self["information"].pageDown()
