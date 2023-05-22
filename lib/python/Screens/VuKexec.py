# -*- coding: utf-8 -*-
from os.path import join, exists, isfile
from Components.Harddisk import harddiskmanager
from Components.ActionMap import ActionMap
from Components.Console import Console
from Components.Label import Label
from Components.config import config
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import BoxInfo
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import QUIT_REBOOT, TryQuitMainloop

model = BoxInfo.getItem("model")
mtdrootfs = BoxInfo.getItem("mtdrootfs")
mtdkernel = BoxInfo.getItem("mtdkernel")

STARTUP = "kernel=/zImage root=/dev/%s rootsubdir=linuxrootfs0" % mtdrootfs # /STARTUP
STARTUP_RECOVERY = STARTUP # /STARTUP_RECOVERY
STARTUP_1 = "kernel=/linuxrootfs1/zImage root=/dev/%s rootsubdir=linuxrootfs1" % mtdrootfs # /STARTUP_1
STARTUP_2 = "kernel=/linuxrootfs2/zImage root=/dev/%s rootsubdir=linuxrootfs2" % mtdrootfs # /STARTUP_2
STARTUP_3 = "kernel=/linuxrootfs3/zImage root=/dev/%s rootsubdir=linuxrootfs3" % mtdrootfs # /STARTUP_3


class VuKexec(Screen):
	skin = """
	<screen name="VuKexec" position="center,180" size="980,235" resolution="1280,720">
		<widget source="footnote" render="Label" position="0,10" size="960,50" foregroundColor="yellow" horizontalAlignment="center" font="Regular;20" />
		<widget source="description" render="Label" position="60,100" size="910,400" horizontalAlignment="center" font="Regular;22"  />
		<widget source="key_green" render="Label" objectTypes="key_green,StaticText" position="20,e-145" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;18" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>
	"""

	def __init__(self, session, *args, **kwargs):
		Screen.__init__(self, session)
		self.title = _("Vu+ MultiBoot Manager")
		self["description"] = StaticText(_("Press GREEN button to enable MultiBoot.\n\nYour receiver will reboot and create the eMMC partitions."))
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

	def RootInit(self):
		partitions = sorted(harddiskmanager.getMountedPartitions(), key=lambda partitions: partitions.device or "")
		for partition in partitions:
			fileForceUpdate = join(partition.mountpoint, "%s/force.update") % BoxInfo.getItem("imagedir")
			if isfile(fileForceUpdate) and "noforce.update" not in fileForceUpdate:
				from shutil import move
				move(fileForceUpdate, fileForceUpdate.replace("force.update", "noforce.update"))
		if not config.misc.firstrun.value:
			self["actions"].setEnabled(False)  # This function takes time so disable the ActionMap to avoid responding to multiple button presses
			self["footnote"].text = _("Vu+ MultiBoot Initialization: Your receiver will reboot.")
			self["description"].text = _("Creating eMMC slots in progress.")
		if isfile("/usr/bin/kernel_auto.bin") and isfile("/usr/bin/STARTUP.cpio.gz"):
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
			print("[VuKexec][RootInit] Kernel Root", mtdkernel, "   ", mtdrootfs)
			cmdlist = []
			cmdlist.append("dd if=/dev/%s of=/zImage" % mtdkernel)  # backup old kernel
			cmdlist.append("dd if=/usr/bin/kernel_auto.bin of=/dev/%s" % mtdkernel)  # create new kernel
			cmdlist.append("mv -f /usr/bin/STARTUP.cpio.gz /STARTUP.cpio.gz")  # copy userroot routine
			Console().eBatch(cmdlist, self.RootInitEnd, debug=True) if not config.misc.firstrun.value else Console().eBatch(cmdlist, self.reBoot, debug=True)
		else:
			self.session.open(MessageBox, _("VuKexec: Create Vu+ Multiboot environment - Unable to complete, Vu+ Multiboot files missing."), MessageBox.TYPE_INFO, timeout=30)
			self.close()

	def RootInitEnd(self, *args, **kwargs):
		print("[VuKexec][RootInitEnd] rebooting")
		for usbslot in range(1, 4):
			if exists("/media/hdd/%s/linuxrootfs%s" % (model, usbslot)):
				Console().ePopen("cp -fR /media/hdd/%s/linuxrootfs%s . /" % (model, usbslot))
		self.session.open(TryQuitMainloop, QUIT_REBOOT)


class VuWizard(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.Console = Console(binary=True)
		self.onShow.append(self.askEnableMultiBoot)

	def askEnableMultiBoot(self):
		self.onShow.remove(self.askEnableMultiBoot)
		popup = self.session.openWithCallback(self.enableMultiBoot, MessageBox, _("Press \"Yes\" for Enable Vu+ MultiBoot.\n\nPress \"No\" to continue wizard."), type=MessageBox.TYPE_YESNO, timeout=-1, default=False)
		popup.setTitle(_("Enable Vu+ MultiBoot"))

	def enableMultiBoot(self, answer):
		if answer:
			VuKexec.RootInit(self)
		else:
			self.close()

	def reBoot(self, *args, **kwargs):
		if exists("/STARTUP.cpio.gz"):
			with open("/STARTUP", 'w') as f:
				f.write(STARTUP_RECOVERY)
			self.Console.ePopen("killall -9 enigma2 && init 6")
