# -*- coding: utf-8 -*-
from Components.ActionMap import ActionMap
from Components.Console import Console
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import BoxInfo
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import QUIT_REBOOT, TryQuitMainloop
from Tools.Directories import fileExists, pathExists

STARTUP = "kernel=/zImage root=/dev/%s rootsubdir=linuxrootfs0" % BoxInfo.getItem("mtdrootfs")					# /STARTUP
STARTUP_RECOVERY = "kernel=/zImage root=/dev/%s rootsubdir=linuxrootfs0" % BoxInfo.getItem("mtdrootfs") 		# /STARTUP_RECOVERY
STARTUP_1 = "kernel=/linuxrootfs1/zImage root=/dev/%s rootsubdir=linuxrootfs1" % BoxInfo.getItem("mtdrootfs") 	# /STARTUP_1
STARTUP_2 = "kernel=/linuxrootfs2/zImage root=/dev/%s rootsubdir=linuxrootfs2" % BoxInfo.getItem("mtdrootfs") 	# /STARTUP_2
STARTUP_3 = "kernel=/linuxrootfs3/zImage root=/dev/%s rootsubdir=linuxrootfs3" % BoxInfo.getItem("mtdrootfs") 	# /STARTUP_3


class VuplusKexec(Screen):

	skin = """
	<screen name="VuplusKexec" position="center,center" size="750,700" flags="wfNoBorder" backgroundColor="transparent">
		<eLabel name="b" position="0,0" size="750,700" backgroundColor="#00ffffff" zPosition="-2" />
		<eLabel name="a" position="1,1" size="748,698" backgroundColor="#00000000" zPosition="-1" />
		<widget source="Title" render="Label" position="center,14" foregroundColor="#00ffffff" size="e-10%,35" horizontalAlignment="left" verticalAlignment="center" font="Regular; 28" backgroundColor="#00000000" />
		<eLabel name="line" position="1,60" size="748,1" backgroundColor="#00ffffff" zPosition="1" />
		<eLabel name="line2" position="1,250" size="748,4" backgroundColor="#00ffffff" zPosition="1" />
		<widget source="description" render="Label" position="2,80" size="730,30" horizontalAlignment="center" font="Regular; 22" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<!-- widget source="key_red" render="Label" position="30,200" size="150,30" noWrap="1" zPosition="1" verticalAlignment="center" font="Regular; 20" horizontalAlignment="left" backgroundColor="#00000000" foregroundColor="#00ffffff" / -->
		<widget source="key_green" render="Label" position="200,200" size="150,30" noWrap="1" zPosition="1" verticalAlignment="center" font="Regular; 20" horizontalAlignment="left" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="200,200" size="40,40" alphaTest="blend" />
	</screen>
	"""

	def __init__(self, session, *args, **kwargs):
		Screen.__init__(self, session)
		self.title = _("Vu+ MultiBoot Manager")
		self["description"] = StaticText(_("Press GREEN button to enable MultiBoot\n\nWill reboot within 10 seconds,\nunless you have eMMC slots to restore.\nRestoring eMMC slots can take from 1 -> 5 minutes per slot."))
		# self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Init Vu+ MultiBoot"))
		self["actions"] = ActionMap(["SetupActions"],
		{
			"save": self.RootInit,
			"ok": self.close,
			"cancel": self.close,
			"menu": self.close,
		}, -1)

	def RootInit(self):
		self["actions"].setEnabled(False)  # This function takes time so disable the ActionMap to avoid responding to multiple button presses
		if fileExists("/usr/bin/kernel_auto.bin") and fileExists("/usr/bin/STARTUP.cpio.gz"):
			self.title = _("Vu+ MultiBoot Initialisation - will reboot after 10 seconds.")
			self["description"].text = _("Vu+ MultiBoot Initialisation in progress\n\nWill reboot after restoring any eMMC slots\nThis can take from 1 -> 5 minutes per slot.")
			with open("/STARTUP", 'w') as f:
				f.write(STARTUP)
			with open("/STARTUP_RECOVERY", 'w') as f:
				f.write(STARTUP_RECOVERY)
			with open("/STARTUP_1", 'w') as f:
				f.write(STARTUP_1)
			with open("/STARTUP_2", 'w') as f:
				f.write(STARTUP_2)
			with open("/STARTUP_3", 'w') as f:
				f.write(STARTUP_3)
			print("[VuplusKexec][RootInit] Kernel Root", BoxInfo.getItem("mtdkernel"), "   ", BoxInfo.getItem("mtdrootfs"))
			cmdlist = []
			cmdlist.append("dd if=/dev/%s of=/zImage" % BoxInfo.getItem("mtdkernel"))						# backup old kernel
			cmdlist.append("dd if=/usr/bin/kernel_auto.bin of=/dev/%s" % BoxInfo.getItem("mtdkernel"))  # create new kernel
			cmdlist.append("mv /usr/bin/STARTUP.cpio.gz /STARTUP.cpio.gz")						# copy userroot routine
			Console().eBatch(cmdlist, self.RootInitEnd, debug=True)
		else:
			self.session.open(MessageBox, _("VuplusKexec: Create Vu+ Multiboot environment - Unable to complete, Vu+ Multiboot files missing."), MessageBox.TYPE_INFO, timeout=30)
			self.close()

	def RootInitEnd(self, *args, **kwargs):
		print("[VuplusKexec][RootInitEnd] rebooting")
		for usbslot in range(1, 4):
			if pathExists("/media/hdd/%s/linuxrootfs%s" % (BoxInfo.getItem("model"), usbslot)):
				Console().ePopen("cp -R /media/hdd/%s/linuxrootfs%s . /" % (BoxInfo.getItem("model"), usbslot))
		self.session.open(TryQuitMainloop, QUIT_REBOOT)