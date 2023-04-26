# -*- coding: utf-8 -*-
from os.path import join
from Components.Harddisk import harddiskmanager
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
	<screen name="VuplusKexec" position="center,180" size="980,235" resolution="1280,720">
		<widget source="footnote" render="Label" position="0,10" size="960,50" foregroundColor="yellow" horizontalAlignment="center" font="Regular;20" />
		<widget source="description" render="Label" position="0,70" size="960,500" horizontalAlignment="center" font="Regular;22"  />
		<widget source="key_green" render="Label" objectTypes="key_green,StaticText" position="20,e-170" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;18" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>
	"""

	def __init__(self, session, *args, **kwargs):
		Screen.__init__(self, session)
		self.title = _("Vu+ MultiBoot Manager")
		self["description"] = StaticText(_("Press GREEN button to enable MultiBoot\n\nWill reboot within 10 seconds,\nunless you have eMMC slots to restore.\nRestoring eMMC slots can take from 1 -> 5 minutes per slot."))
		# self["key_red"] = StaticText(_("Cancel"))
		self["footnote"] = StaticText()
		self["key_green"] = StaticText(_("Init Vu+ MultiBoot"))
		self["actions"] = ActionMap(["SetupActions"],
		{
			"save": self.RootInit,
			"ok": self.close,
			"cancel": self.close,
			"menu": self.close,
		}, -1)
		partitions = sorted(harddiskmanager.getMountedPartitions(), key=lambda partitions: partitions.device or "")
		for partition in partitions:
			self.folderVuplus = join(partition.mountpoint, "vuplus")
			if BoxInfo.getItem("model") == "vuzero4k" and pathExists(self.folderVuplus):
				self["footnote"].text = _("Delete or rename folder \"vuplus\" in path '%s' before initializing.") % partition.mountpoint

	def RootInit(self):
		if BoxInfo.getItem("model") == "vuzero4k" and pathExists(self.folderVuplus):
			self.close()
		else:
			self["actions"].setEnabled(False)  # This function takes time so disable the ActionMap to avoid responding to multiple button presses
			if fileExists("/usr/bin/kernel_auto.bin") and fileExists("/usr/bin/STARTUP.cpio.gz"):
				self["footnote"].text = _("Vu+ MultiBoot Initialisation - will reboot after 10 seconds.")
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
