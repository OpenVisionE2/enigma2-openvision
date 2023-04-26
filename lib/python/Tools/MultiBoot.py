# -*- coding: utf-8 -*-
from datetime import datetime
from os import rename, rmdir, sep, stat
from os.path import basename, exists, isfile, ismount, join as pathjoin
from glob import glob
from tempfile import mkdtemp
from subprocess import check_output
from Components.Console import Console
from Components.SystemInfo import BoxInfo
from Tools.Directories import fileReadLine, fileReadLines

MODULE_NAME = __name__.split(".")[-1]

canMode12 = BoxInfo.getItem("canMode12")
hasKexec = BoxInfo.getItem("hasKexec")

PREFIX = "MultiBoot_"
MOUNT = "/bin/mount"
UMOUNT = "/bin/umount"

startupDevice = None
bootSlots = {}
bootArgs = fileReadLine("/sys/firmware/devicetree/base/chosen/bootargs", source=MODULE_NAME)


def getArgValue(line, arg):
	return line.replace("userdataroot", "rootuserdata").rsplit("%s=" % arg, 1)[1].split(" ", 1)[0]


def getSlotImageData(imageDir):
	imageData = {}
	path = pathjoin(imageDir, "usr/lib/enigma.info")
	if isfile(path):
		lines = fileReadLines(path, source=MODULE_NAME)
		if lines:
			modified = BoxInfo.checkChecksum(lines)
			if modified:
				print("[MultiBoot] WARNING: Enigma information file checksum is incorrect!  File appears to have been modified.")
			for line in lines:
				if line.startswith("#") or line.strip() == "":
					continue
				if "=" in line:
					item, value = [x.strip() for x in line.split("=", 1)]
					if item:
						imageData[item] = BoxInfo.processValue(value)
	else:
		imageDateList = [
			"usr/share/enigma2/bootlogo.mvi",
			"usr/share/bootlogo.mvi",
			"var/lib/opkg/status"
		]
		fileDate = ""
		for file in imageDateList:
			path = pathjoin(imageDir, file)
			if isfile(path):
				fileDate = datetime.fromtimestamp(stat(path).st_mtime).strftime("%Y%m%d")
				if not fileDate.startswith("1970"):
					break
		enigmaDate = datetime.fromtimestamp(stat(pathjoin(imageDir, "usr/bin/enigma2")).st_mtime).strftime("%Y%m%d")  # Method not called if enigma2 does not exist!
		imageData["compiledate"] = max(fileDate, enigmaDate) or _("Unknown")
		lines = fileReadLines(pathjoin(imageDir, "etc/issue"), source=MODULE_NAME)
		imageData["displaydistro"] = lines[-2].capitalize().strip()[:-6] if lines else _("Unknown")
	return imageData


def getMultiBootStartupDevice():
	global startupDevice
	startupDevice = None
	tempDir = mkdtemp(prefix=PREFIX)
	bootList = ("/dev/block/by-name/bootoptions", "/dev/mmcblk0p1", "/dev/mmcblk1p1", "/dev/mmcblk0p3", "/dev/mmcblk0p4", "/dev/mtdblock2") if not BoxInfo.getItem("hasKexec") else ("/dev/mmcblk0p4", "/dev/mmcblk0p7", "/dev/mmcblk0p9")
	for device in bootList:
		if exists(device):
			if exists("/dev/block/by-name/flag"):
				Console().ePopen((MOUNT, MOUNT, "--bind", device, tempDir))
			else:
				Console().ePopen((MOUNT, MOUNT, device, tempDir))
			if isfile(pathjoin(tempDir, "STARTUP")):
				startupDevice = device
				print("[MultiBoot] Startup device '%s' found." % device)
			Console().ePopen((UMOUNT, UMOUNT, tempDir))
			if startupDevice:
				break
	if not ismount(tempDir):
		rmdir(tempDir)
	return startupDevice


def getMultiBootSlots():
	global bootSlots, startupDevice
	bootSlots = {}
	mode12Found = False
	BoxInfo.setItem("VuUUIDSlot", "")
	UUID = ""
	UUIDnum = 0
	if startupDevice is None:
		startupDevice = getMultiBootStartupDevice()
	if startupDevice:
		tempDir = mkdtemp(prefix=PREFIX)
		Console().ePopen((MOUNT, MOUNT, startupDevice, tempDir))
		for file in glob(pathjoin(tempDir, "STARTUP_*")):
			if "MODE_" in file:
				mode12Found = True
				slotNumber = file.rsplit("_", 3)[1]
			elif "STARTUP_RECOVERY" in file:
				BoxInfo.setItem("RecoveryMode", True)
				print("[MultiBoot] Recovery mode is set to True.")
				slotNumber = "0"
			else:
				slotNumber = file.rsplit("_", 1)[1]
			if slotNumber.isdigit() and slotNumber not in bootSlots:
				if hasKexec and int(slotNumber) > 3:
					BoxInfo.setItem("HasKexecUSB", True)
				lines = fileReadLines(file, source=MODULE_NAME)
				if lines:
					slot = {}
					print("[MultiBoot][getMultibootslots] slot", slot)
					for line in lines:
						if "root=" in line:
							device = getArgValue(line, "root")
							if "UUID=" in device:
								UUID = device
								UUIDnum += 1
								slotx = str(getUUIDtoSD(device))
								if slotx is not None:
									device = slotx
								slot["kernel"] = "/linuxrootfs%s/zImage" % slotNumber
							if exists(device) or device == 'ubi0:ubifs':
								slot["device"] = device
								slot["startupfile"] = basename(file)
								slot["slotType"] = "eMMC" if "mmc" in slot["device"] else "USB"
								if "rootsubdir" in line:
									BoxInfo.setItem("HasRootSubdir", True)
									slot["kernel"] = getArgValue(line, "kernel")
									slot["rootsubdir"] = getArgValue(line, "rootsubdir")
								elif not hasKexec and 'sda' in line:
									slot["kernel"] = getArgValue(line, "kernel")
									slot["rootsubdir"] = None
								else:
									slot["kernel"] = "%sp%s" % (device.split("p")[0], int(device.split("p")[1]) - 1)
								bootSlots[int(slotNumber)] = slot
							break
				else:
					print("[MultiBoot] Warning: No content in file '%s' for slot number '%s'!" % (file, slotNumber))
			else:
				print("[MultiBoot] Warning: Unexpected slot number '%s' in file '%s'!" % (slotNumber, file))
		Console().ePopen((UMOUNT, UMOUNT, tempDir))
		if not ismount(tempDir):
			rmdir(tempDir)
		if not mode12Found and canMode12:
			# The boot device has ancient content and does not contain the correct STARTUP files!
			for slot in range(1, 5):
				bootSlots[slot] = {"device": "/dev/mmcblk0p%s" % (slot * 2 + 1), "startupfile": None}
	if bootSlots:
		for slot in sorted(list(bootSlots.keys())):
			print("[MultiBoot] Boot slot %d: %s" % (slot, str(bootSlots[slot])))
	else:
		print("[MultiBoot] No boot slots found.")
	return bootSlots


def getCurrentImage():
	global bootSlots, bootArgs
	UUID = ""
	UUIDnum = 0
	if bootSlots:
		if not hasKexec:
			slot = [x[-1] for x in bootArgs.split() if x.startswith("rootsubdir")]
			if slot:
				return int(slot[0])
			else:
				device = getArgValue(bootArgs, "root")
				for slot in bootSlots.keys():
					if bootSlots[slot]["device"] == device:
						return slot
		else: # kexec kernel multiboot VU+
			rootsubdir = [x for x in bootArgs.split() if x.startswith("rootsubdir")]
			char = "/" if "/" in rootsubdir[0] else "="
			BoxInfo.setItem("VuUUIDSlot", UUID, UUIDnum if UUIDnum != 0 else "")
			return int(rootsubdir[0].rsplit(char, 1)[1][11:])
	return None


def getCurrentImageMode():
	global bootArgs
	return bool(bootSlots) and canMode12 and int(bootArgs.split("=")[-1])


def getImageList(Recovery=None):
	imageList = {}
	if bootSlots:
		tempDir = mkdtemp(prefix=PREFIX)
		for slot in sorted(list(bootSlots.keys())):
			if slot == 0:
				if not Recovery:  # called by ImageManager
					continue
				else:  # called by FlashImage
					imageList[slot] = {"imagename": _("Recovery Mode")}
					continue
			print("[MultiBoot] [getImageList] slot = ", slot)
			try:  # Avoid problems Dev lost USB Slots Kexec
				Console().ePopen((MOUNT, MOUNT, bootSlots[slot]["device"], tempDir))
			except:
				pass
			imageDir = sep.join(filter(None, [tempDir, bootSlots[slot].get("rootsubdir", "")]))
			if isfile(pathjoin(imageDir, "usr/bin/enigma2")):
				imageData = getSlotImageData(imageDir)
				version = "%s " % imageData["imgversion"] if imageData.get("imgversion", None) else ""
				revision = "%s " % imageData["imgrevision"] if imageData.get("imgrevision", None) and imageData.get("imgrevision", 0) != imageData.get("compiledate", 0) else ""
				imgtype = "%s " % imageData["imagetype"] if imageData.get("imagetype", None) else ""
				date = str(imageData["compiledate"])
				if imageData.get("compiledate", 0) == 0:
					date = ""
				else:
					date = str(imageData["compiledate"])
					date = " (%s-%s-%s)" % (date[0:4], date[4:6], date[6:8])
				imageList[slot] = {"imagename": "%s %s%s%s%s" % (imageData.get("displaydistro", imageData.get("distro", _("Unknown"))), version, revision, imgtype, date)}
			elif isfile(pathjoin(imageDir, "usr/bin/enigma2.bak")):
				imageList[slot] = {"imagename": _("Deleted image")}
			else:
				imageList[slot] = {"imagename": _("Empty slot")}
			Console().ePopen((UMOUNT, UMOUNT, tempDir))
		if not ismount(tempDir):
			rmdir(tempDir)
	return imageList


def emptySlot(slot):
	tempDir = mkdtemp(prefix=PREFIX)
	Console().ePopen((MOUNT, MOUNT, bootSlots[slot]["device"], tempDir))
	imageDir = sep.join(filter(None, [tempDir, bootSlots[slot].get("rootsubdir", "")]))
	enigmaBinaryFile = pathjoin(imageDir, "usr/bin/enigma2")
	if isfile(enigmaBinaryFile):
		rename(enigmaBinaryFile, "%sx" % enigmaBinaryFile)
		print("[MultiBoot] Slot %d marked as empty." % slot)
		ret = 0
	else:
		print("[MultiBoot] No enigma2 found in slot %d to rename (mark as empty)." % slot)
		ret = 4
	Console().ePopen((UMOUNT, UMOUNT, tempDir))
	if not ismount(tempDir):
		rmdir(tempDir)
	return ret


def deleteImage(slot):
	tempDir = mkdtemp(prefix=PREFIX)
	Console().ePopen((MOUNT, MOUNT, bootSlots[slot]["device"], tempDir))
	enigmaBinaryFile = pathjoin(sep.join(filter(None, [tempDir, bootSlots[slot].get("rootsubdir", "")])), "usr/bin/enigma2")
	if exists(enigmaBinaryFile):
		rename(enigmaBinaryFile, "%s.bak" % enigmaBinaryFile)
	Console().ePopen((UMOUNT, UMOUNT, tempDir))
	if not ismount(tempDir):
		rmdir(tempDir)


def restoreImage(slot):
	tempDir = mkdtemp(prefix=PREFIX)
	Console().ePopen((MOUNT, MOUNT, bootSlots[slot]["device"], tempDir))
	enigmaBinaryFile = pathjoin(sep.join(filter(None, [tempDir, bootSlots[slot].get("rootsubdir", "")])), "usr/bin/enigma2")
	if exists("%s.bak" % enigmaBinaryFile):
		rename("%s.bak" % enigmaBinaryFile, enigmaBinaryFile)
	Console().ePopen((UMOUNT, UMOUNT, tempDir))
	if not ismount(tempDir):
		rmdir(tempDir)


def restoreImages():
	for slot in bootSlots:
		restoreImage(slot)


def getUUIDtoSD(UUID): # returns None on failure
	check = "/sbin/blkid"
	if exists(check):
		lines = check_output([check]).decode(encoding="utf8", errors="ignore").split("\n")
		for line in lines:
			if UUID in line.replace('"', ''):
				return line.split(":")[0].strip()
	else:
		return None
