from fcntl import ioctl
from os import listdir, major, minor, mkdir, popen, rmdir, sep, stat, statvfs, system, unlink
from os.path import abspath, dirname, exists, ismount, join as pathjoin, normpath, realpath
from re import search
from time import sleep, time

from enigma import eTimer

from Components import Task
from Components.Console import Console
from Components.SystemInfo import BoxInfo
from Tools.CList import CList
from Tools.Directories import fileReadLine, fileReadLines
from Tools.StbHardware import getBoxProc

hw_type = getBoxProc()


def getProcMounts():
	mounts = fileReadLines("/proc/mounts", [])
	result = [line.strip().split(" ") for line in mounts]
	for item in result:
		item[1] = item[1].replace("\\040", " ")  # Spaces are encoded as \040 in mounts
	return result


def isFileSystemSupported(filesystem):
	for fs in fileReadLines("/proc/filesystems", []):
		if fs.strip().endswith(filesystem):
			return True
	return False


def findMountPoint(path):
	# Example: findMountPoint("/media/hdd/some/file") returns "/media/hdd"
	path = abspath(path)
	while not ismount(path):
		path = dirname(path)
	return path


class Harddisk:
	def __init__(self, device, removable=False):
		self.device = device
		self.card = False
		self.max_idle_time = 0
		self.idle_running = False
		self.last_access = time()
		self.last_stat = 0
		self.timer = None
		self.is_sleeping = False
		self.dev_path = ""
		self.disk_path = ""
		self.mount_path = None
		self.mount_device = None
		self.phys_path = realpath(self.sysfsPath("device"))
		self.removable = removable
		self.internal = "ide" in self.phys_path or "pci" in self.phys_path or "ahci" in self.phys_path or "sata" in self.phys_path
		data = fileReadLine(pathjoin("/sys/block", device, "queue/rotational"), "1")
		self.rotational = int(data)
		if BoxInfo.getItem("Udev"):
			self.dev_path = "/dev/" + self.device
			self.disk_path = self.dev_path
			self.card = "sdhci" in self.phys_path or "mmc" in self.device
		else:
			tmp = fileReadLine(self.sysfsPath("dev")).split(":")
			s_major = int(tmp[0])
			s_minor = int(tmp[1])
			for disc in listdir("/dev/discs"):
				dev_path = realpath("/dev/discs/" + disc)
				disk_path = dev_path + "/disc"
				try:
					rdev = stat(disk_path).st_rdev
				except (IOError, OSError):
					continue
				if s_major == major(rdev) and s_minor == minor(rdev):
					self.dev_path = dev_path
					self.disk_path = disk_path
					break
			self.card = self.device[:2] == "hd" and "host0" not in self.dev_path
		print("[Harddisk] New device '%s' -> '%s' -> '%s'." % (self.device, self.dev_path, self.disk_path))
		if (self.internal or not removable) and not self.card:
			self.startIdle()

	def __lt__(self, ob):
		return self.device < ob.device

	def partitionPath(self, n):
		if BoxInfo.getItem("Udev"):
			if self.dev_path.startswith("/dev/mmcblk"):
				return "%sp%s" % (self.dev_path, n)
			else:
				return "%s%s" % (self.dev_path, n)
		else:
			return pathjoin(self.dev_path, "part%s" % n)

	def sysfsPath(self, filename):
		return pathjoin("/sys/block", self.device, filename)

	def stop(self):
		if self.timer:
			self.timer.stop()
			self.timer.callback.remove(self.runIdle)

	def bus(self):
		ret = _("External")
		# SD/MMC
		if BoxInfo.getItem("Udev"):
			if "usb" in self.phys_path:
				type_name = " (USB)"
			else:
				type_name = " (SD/MMC)"
		# CF
		else:
			type_name = " (CF)"
		if self.card:
			ret += type_name
		else:
			if self.internal:
				ret = _("Internal")
			if not self.rotational:
				ret += " (SSD)"
		return ret

	def diskSize(self):
		line = fileReadLine(self.sysfsPath("size"))
		if line is None:
			dev = self.findMount()
			if dev:
				try:
					stat = statvfs(dev)
					cap = int(stat.f_blocks * stat.f_bsize)
					return cap / 1000 / 1000
				except (IOError, OSError):
					return 0
		cap = int(line)
		return cap / 1000 * 512 / 1000

	def capacity(self):
		cap = self.diskSize()
		if cap == 0:
			return ""
		if cap < 1000:
			return _("%d MB") % cap
		return _("%.2f GB") % (cap / 1000.0)

	def model(self):
		if self.device[:2] == "hd":
			return fileReadLine(pathjoin("/proc/ide", self.device, "model"), _("Unknown"))
		elif self.device[:2] == "sd":
			vendor = fileReadLine(self.sysfsPath("device/vendor"), _("Unknown"))
			model = fileReadLine(self.sysfsPath("device/model"), _("Unknown"))
			return "%s (%s)" % (vendor, model)
		elif self.device.startswith("mmcblk"):
			return fileReadLine(self.sysfsPath("device/name"), _("Unknown"))
		print("[Harddisk] Error: Failed to get model: No hdX or sdX or mmcX!")
		return "-?-"

	def free(self):
		dev = self.findMount()
		if dev:
			try:
				stat = statvfs(dev)
				return (stat.f_bfree / 1000) * (stat.f_bsize / 1024)
			except (IOError, OSError):
				pass
		return -1

	def totalFree(self):
		mediapath = []
		freetot = 0
		for parts in getProcMounts():
			if realpath(parts[0]).startswith(self.dev_path):
				mediapath.append(parts[1])
		for mpath in mediapath:
			try:
				stat = statvfs(mpath)
				freetot += (stat.f_bfree / 1000) * (stat.f_bsize / 1000)
			except (IOError, OSError):
				pass
		return freetot

	def Totalfree(self):
		return self.totalFree()

	def numPartitions(self):
		numPart = -1
		if BoxInfo.getItem("Udev"):
			try:
				devdir = listdir("/dev")
			except (IOError, OSError):
				return -1
			for filename in devdir:
				if filename.startswith(self.device):
					numPart += 1
		else:
			try:
				idedir = listdir(self.dev_path)
			except (IOError, OSError):
				return -1
			for filename in idedir:
				if filename.startswith("disc"):
					numPart += 1
				if filename.startswith("part"):
					numPart += 1
		return numPart

	def mountDevice(self):
		for parts in getProcMounts():
			if realpath(parts[0]).startswith(self.dev_path):
				self.mount_device = parts[0]
				self.mount_path = parts[1]
				return parts[1]
		return None

	def enumMountDevices(self):
		for parts in getProcMounts():
			if realpath(parts[0]).startswith(self.dev_path):
				yield parts[1]

	def findMount(self):
		if self.mount_path is None:
			return self.mountDevice()
		return self.mount_path

	def unmount(self):
		dev = self.mountDevice()
		if dev is None:
			return 0  # Not mounted, return OK.
		cmd = "umount %s" % dev
		print("[Harddisk] Command: '%s'." % cmd)
		res = system(cmd)
		return (res >> 8)

	def createPartition(self):
		cmd = 'printf("8,\n;0,0\n;0,0\n;0,0\ny\n") | sfdisk -f -uS ' + self.disk_path
		res = system(cmd)
		return (res >> 8)

	def mkfs(self):
		return 1  # No longer supported, use createInitializeJob instead.

	def mount(self):
		if self.mount_device is None:  # Try mounting through fstab first.
			dev = self.partitionPath("1")
		else:
			# if previously mounted, use the same spot
			dev = self.mount_device
		lines = fileReadLines("/etc/fstab")
		if lines is None:
			return -1
		for line in lines:
			parts = line.strip().split(" ")
			fspath = realpath(parts[0])
			if fspath == dev:
				print("[Harddisk] Mounting: '%s'." % fspath)
				cmd = "mount -t auto " + fspath
				res = system(cmd)
				return (res >> 8)
		# device is not in fstab
		res = -1
		if BoxInfo.getItem("Udev"):
			# we can let udev do the job, re-read the partition table
			res = system("hdparm -z %s" % self.disk_path)
			# give udev some time to make the mount, which it will do asynchronously
			sleep(3)
		return (res >> 8)

	def fsck(self):
		return 1  # No longer supported, use createCheckJob instead.

	def killPartitionTable(self):
		zero = "\0" * 512
		h = open(self.dev_path, "wb")
		# delete first 9 sectors, which will likely kill the first partition too
		for i in range(9):
			h.write(zero)
		h.close()

	def killPartition(self, n):
		zero = "\0" * 512
		part = self.partitionPath(n)
		h = open(part, "wb")
		for i in range(3):
			h.write(zero)
		h.close()

	def createMovieDir(self):
		mkdir(pathjoin(self.mount_path, 'movie'))

	def createInitializeJob(self):
		print("[Harddisk] Initializing storage device...")
		job = Task.Job(_("Initializing storage device..."))
		size = self.diskSize()
		print("[Harddisk] Disk size: %s MB." % size)
		task = UnmountTask(job, self)
		task = Task.PythonTask(job, _("Removing partition table."))
		task.work = self.killPartitionTable
		task.weighting = 1
		task = Task.LoggingTask(job, _("Rereading partition table."))
		task.weighting = 1
		task.setTool("hdparm")
		task.args.append("-z")
		task.args.append(self.disk_path)
		task = Task.ConditionTask(job, _("Waiting for partition."), timeoutCount=20)
		task.check = lambda: not exists(self.partitionPath("1"))
		task.weighting = 1
		if exists("/usr/sbin/parted"):
			use_parted = True
		else:
			if size > 2097151:
				addInstallTask(job, "parted")
				use_parted = True
			else:
				use_parted = False
		print("[Harddisk] Creating partition.")
		task = Task.LoggingTask(job, _("Creating partition."))
		task.weighting = 5
		if use_parted:
			task.setTool("parted")
			if size < 1024:
				alignment = "min"  # On very small devices, align to block only.
			else:
				alignment = "opt"  # Prefer optimal alignment for performance.
			if size > 2097151:
				parttype = "gpt"
			else:
				parttype = "msdos"
			task.args += ["-a", alignment, "-s", self.disk_path, "mklabel", parttype, "mkpart", "primary", "0%", "100%"]
		else:
			task.setTool("sfdisk")
			task.args.append("-f")
			task.args.append("-uS")
			task.args.append(self.disk_path)
			if size > 128000:
				# Start at sector 8 to better support 4k aligned disks
				print("[Harddisk] Detected >128GB disk, using 4k alignment.")
				task.initial_input = "8,,L\n;0,0\n;0,0\n;0,0\ny\n"
			else:
				# Smaller disks (CF cards, sticks etc) don't need that
				task.initial_input = ",,L\n;\n;\n;\ny\n"
		task = Task.ConditionTask(job, _("Waiting for partition"))
		task.check = lambda: exists(self.partitionPath("1"))
		task.weighting = 1
		task = MkfsTask(job, _("Creating filesystem"))
		big_o_options = ["dir_index"]
		if isFileSystemSupported("ext4"):
			task.setTool("mkfs.ext4")
			if size > 20000:
				try:
					version = map(int, fileReadLine("/proc/version").split(" ", 4)[2].split(".", 2)[:2])
					if (version[0] > 3) or (version[0] > 2 and version[1] >= 2):
						# Linux version 3.2 supports bigalloc and -C option, use 256k blocks
						task.args += ["-C", "262144"]
						big_o_options.append("bigalloc")
				except Exception as err:
					print("[Harddisk] Error: Failed to detect Linux version - '%s'!" % str(err))
		else:
			task.setTool("mkfs.ext3")
		if size > 250000:
			# No more than 256k i-nodes (prevent problems with fsck memory requirements)
			task.args += ["-T", "largefile", "-N", "262144"]
			big_o_options.append("sparse_super")
		elif size > 16384:
			# between 16GB and 250GB: 1 i-node per megabyte
			task.args += ["-T", "largefile"]
			big_o_options.append("sparse_super")
		elif size > 2048:
			# Over 2GB: 32 i-nodes per megabyte
			task.args += ["-T", "largefile", "-N", str(size * 32)]
		task.args += ["-F", "-F", "-m0", "-O", ",".join(big_o_options), self.partitionPath("1")]
		task = MountTask(job, self)
		task.weighting = 3
		task = Task.ConditionTask(job, _("Waiting for mount"), timeoutCount=20)
		task.check = self.mountDevice
		task.weighting = 1

		task = Task.PythonTask(job, _("Create directory") + ": movie")
		task.work = self.createMovieDir
		task.weighting = 1

		return job

	def initialize(self):
		return -5  # No longer supported.

	def check(self):
		return -5  # No longer supported.

	def createCheckJob(self):
		job = Task.Job(_("Checking filesystem..."))
		if self.findMount():
			# Create unmount task if it was not mounted
			UnmountTask(job, self)
			dev = self.mount_device
		else:
			# otherwise, assume there is one partition
			dev = self.partitionPath("1")
		task = Task.LoggingTask(job, "fsck")
		task.setTool("fsck.ext3")
		task.args.append("-f")
		task.args.append("-p")
		task.args.append(dev)
		MountTask(job, self)
		task = Task.ConditionTask(job, _("Waiting for mount"))
		task.check = self.mountDevice
		return job

	def getDeviceDir(self):
		return self.dev_path

	def getDeviceName(self):
		return self.disk_path

	# the HDD idle poll daemon.
	# as some harddrives have a buggy standby timer, we are doing this by hand here.
	# first, we disable the hardware timer. then, we check every now and then if
	# any access has been made to the disc. If there has been no access over a specifed time,
	# we set the hdd into standby.
	#
	def readStats(self):
		line = fileReadLine(pathjoin("/sys/block", self.device, "stat"))
		if line is None:
			return -1, -1
		data = line.split(None, 5)
		return (int(data[0]), int(data[4]))

	def startIdle(self):
		# disable HDD standby timer
		if self.bus() == _("External"):
			Console().ePopen(("sdparm", "sdparm", "--set=SCT=0", self.disk_path))
		else:
			Console().ePopen(("hdparm", "hdparm", "-S0", self.disk_path))
		self.timer = eTimer()
		self.timer.callback.append(self.runIdle)
		self.idle_running = True
		self.setIdleTime(self.max_idle_time)  # kick the idle polling loop

	def runIdle(self):
		if not self.max_idle_time:
			return
		t = time()
		idle_time = t - self.last_access
		stats = self.readStats()
		l = sum(stats)
		if l != self.last_stat and l >= 0:  # access
			self.last_stat = l
			self.last_access = t
			idle_time = 0
			self.is_sleeping = False
		if idle_time >= self.max_idle_time and not self.is_sleeping:
			self.setSleep()
			self.is_sleeping = True

	def setSleep(self):
		if self.bus() == _("External"):
			Console().ePopen(("sdparm", "sdparm", "--flexible", "--readonly", "--command=stop", self.disk_path))
		else:
			Console().ePopen(("hdparm", "hdparm", "-y", self.disk_path))

	def setIdleTime(self, idle):
		self.max_idle_time = idle
		if self.idle_running:
			if not idle:
				self.timer.stop()
			else:
				self.timer.start(idle * 100, False)  # poll 10 times per period.

	def isSleeping(self):
		return self.is_sleeping


class Partition:
	# for backward compatibility, force_mounted actually means "hotplug"
	def __init__(self, mountpoint, device=None, description="", force_mounted=False):
		self.mountpoint = mountpoint
		self.description = description
		self.force_mounted = mountpoint and force_mounted
		self.is_hotplug = force_mounted  # so far; this might change.
		self.device = device

	def __str__(self):
		return "Partition(mountpoint=%s,description=%s,device=%s)" % (self.mountpoint, self.description, self.device)

	def stat(self):
		if self.mountpoint:
			return statvfs(self.mountpoint)
		else:
			raise OSError("Device %s is not mounted" % self.device)

	def free(self):
		try:
			s = self.stat()
			return s.f_bavail * s.f_bsize
		except (IOError, OSError):
			return None

	def total(self):
		try:
			s = self.stat()
			return s.f_blocks * s.f_bsize
		except (IOError, OSError):
			return None

	def tabbedDescription(self):
		if self.mountpoint.startswith("/media/net") or self.mountpoint.startswith("/media/autofs"):
			# Network devices have a user defined name
			return self.description
		return self.description + "\t" + self.mountpoint

	def mounted(self, mounts=None):
		# THANK YOU PYTHON FOR STRIPPING AWAY f_fsid.
		# TODO: can ismount be used?
		if self.force_mounted:
			return True
		if self.mountpoint:
			if mounts is None:
				mounts = getProcMounts()
			for parts in mounts:
				if self.mountpoint.startswith(parts[1]):  # use startswith so a mount not ending with "/" is also detected.
					return True
		return False

	def filesystem(self, mounts=None):
		if self.mountpoint:
			if mounts is None:
				mounts = getProcMounts()
			for fields in mounts:
				if self.mountpoint.endswith("/") and not self.mountpoint == "/":
					if fields[1] + "/" == self.mountpoint:
						return fields[2]
				else:
					if fields[1] == self.mountpoint:
						return fields[2]
		return ""


def addInstallTask(job, package):
	task = Task.LoggingTask(job, "update packages")
	task.setTool("opkg")
	task.args.append("update")
	task = Task.LoggingTask(job, "Install " + package)
	task.setTool("opkg")
	task.args.append("install")
	task.args.append(package)


class HarddiskManager:
	def __init__(self):
		self.hdd = []
		self.cd = ""
		self.partitions = []
		self.devices_scanned_on_init = []
		self.on_partition_list_change = CList()
		self.enumerateBlockDevices()
		self.enumerateNetworkMounts()
		# Find stuff not detected by the enumeration
		p = (
			("/media/hdd", _("Hard disk")),
			("/media/card", _("Card")),
			("/media/cf", _("Compact flash")),
			("/media/mmc", _("MMC card")),
			("/media/net", _("Network mount")),
			("/media/net1", _("Network mount %s") % ("1")),
			("/media/net2", _("Network mount %s") % ("2")),
			("/media/net3", _("Network mount %s") % ("3")),
			("/media/ram", _("Ram disk")),
			("/media/usb", _("USB stick")),
			("/", _("Internal flash"))
		)
		known = set([normpath(a.mountpoint) for a in self.partitions if a.mountpoint])
		for m, d in p:
			if (m not in known) and ismount(m):
				self.partitions.append(Partition(mountpoint=m, description=d))

	def getBlockDevInfo(self, blockdev):
		devpath = "/sys/block/" + blockdev
		error = False
		removable = False
		BLACKLIST = []
		if BoxInfo.getItem("HasMMC"):
			BLACKLIST = ["%s" % (BoxInfo.getItem("mtdrootfs")[0:7])]
		if BoxInfo.getItem("HasMMC") and "root=/dev/mmcblk0p1" in fileReadLine("/proc/cmdline", ""):
			BLACKLIST = ["mmcblk0p1"]
		blacklisted = False
		if blockdev[:7] in BLACKLIST:
			blacklisted = True
		if blockdev.startswith("mmcblk") and (search(r"mmcblk\dboot", blockdev) or search(r"mmcblk\drpmb", blockdev)):
			blacklisted = True
		is_cdrom = False
		is_mmc = False
		partitions = []
		try:
			if exists(devpath + "/removable"):
				removable = bool(int(fileReadLine(pathjoin(devpath, "/removable"), "0")))
			if exists(devpath + "/dev"):
				dev = fileReadLine(pathjoin(devpath, "dev"))
				subdev = False if int(dev.split(":")[1]) % 32 == 0 else True
				dev = int(dev.split(":")[0])
			else:
				dev = None
				subdev = False
			# blacklist ram, loop, mtdblock, romblock, ramzswap
			blacklisted = dev in [1, 7, 31, 253, 254]
			# blacklist non-root eMMC devices
			if not blacklisted and dev == 179:
				is_mmc = True
				if (BoxInfo.getItem("BootDevice") and blockdev.startswith(BoxInfo.getItem("BootDevice"))) or subdev:
					blacklisted = True
			if blockdev[0:2] == "sr":
				is_cdrom = True
			if blockdev[0:2] == "hd":
				try:
					if "cdrom" in fileReadLine(pathjoin("/proc/ide", blockdev, "media"), ""):
						is_cdrom = True
				except (IOError, OSError):
					error = True
			# check for partitions
			if not is_cdrom and not is_mmc and exists(devpath):
				for partition in listdir(devpath):
					if partition[0:len(blockdev)] != blockdev:
						continue
					if dev == 179 and not search(r"mmcblk\dp\d+", partition):
						continue
					partitions.append(partition)
			else:
				self.cd = blockdev
		except (IOError, OSError):
			error = True
		# check for medium
		medium_found = True
		try:
			if exists(pathjoin("/dev", blockdev)):
				open(pathjoin("/dev", blockdev)).close()
		except (IOError, OSError) as err:
			if err.errno == 159:  # no medium present
				medium_found = False
		return error, blacklisted, removable, is_cdrom, partitions, medium_found

	def enumerateBlockDevices(self):
		print("[Harddisk] Enumerating block devices...")
		for blockdev in listdir("/sys/block"):
			error, blacklisted, removable, is_cdrom, partitions, medium_found = self.addHotplugPartition(blockdev)
			if not error and not blacklisted and medium_found:
				for part in partitions:
					self.addHotplugPartition(part)
				self.devices_scanned_on_init.append((blockdev, removable, is_cdrom, medium_found))

	def enumerateNetworkMounts(self, refresh=False):
		print("[Harddisk] Enumerating network mounts...")
		netmount = (exists("/media/net") and listdir("/media/net")) or ""
		if len(netmount) > 0:
			for fil in netmount:
				if ismount("/media/net/" + fil):
					print("[Harddisk] New network mount '%s' -> '%s'." % (fil, pathjoin("/media/net/", fil)))
					if refresh:
						self.addMountedPartition(device=pathjoin('/media/net/', fil + '/'), desc=fil)
					else:
						self.partitions.append(Partition(mountpoint=pathjoin('/media/net/', fil + '/'), description=fil))
		autofsmount = (exists("/media/autofs") and listdir("/media/autofs")) or ""
		if len(autofsmount) > 0:
			for fil in autofsmount:
				if ismount("/media/autofs/" + fil) or exists("/media/autofs/" + fil):
					print("[Harddisk] New network mount '%s' -> '%s'." % (fil, pathjoin("/media/autofs", fil)))
					if refresh:
						self.addMountedPartition(device=pathjoin('/media/autofs/', fil + '/'), desc=fil)
					else:
						self.partitions.append(Partition(mountpoint=pathjoin('/media/autofs/', fil + '/'), description=fil))
		if ismount("/media/hdd") and "/media/hdd/" not in [p.mountpoint for p in self.partitions]:
			print("[Harddisk] New network mount being used as HDD replacement -> '/media/hdd/'.")
			if refresh:
				self.addMountedPartition(device='/media/hdd/', desc='/media/hdd/')
			else:
				self.partitions.append(Partition(mountpoint='/media/hdd/', description='/media/hdd'))

	def getAutofsMountpoint(self, device):
		r = self.getMountpoint(device)
		if r is None:
			return "/media/" + device
		return r

	def getMountpoint(self, device):
		dev = "/dev/%s" % device
		for item in getProcMounts():
			if item[0] == dev:
				return item[1]
		return None

	def addHotplugPartition(self, device, physdev=None):
		# device is the device name, without /dev
		# physdev is the physical device path, which we (might) use to determine the userfriendly name
		if not physdev:
			dev, part = self.splitDeviceName(device)
			try:
				physdev = realpath("/sys/block/" + dev + "/device")[4:]
			except (IOError, OSError) as err:
				physdev = dev
				print("[Harddisk] Error %d: Couldn't determine blockdev physdev for device '%s'!  (%s)" % (err.errno, device, err.strerror))
		error, blacklisted, removable, is_cdrom, partitions, medium_found = self.getBlockDevInfo(device)
		if hw_type in ("elite", "premium", "premium+", "ultra"):
			if device[0:3] == "hda":
				blacklisted = True
		if not blacklisted and medium_found:
			description = self.getUserfriendlyDeviceName(device, physdev)
			p = Partition(mountpoint=self.getMountpoint(device), description=description, force_mounted=True, device=device)
			self.partitions.append(p)
			if p.mountpoint:  # Plugins won't expect unmounted devices
				self.on_partition_list_change("add", p)
			# see if this is a harddrive
			l = len(device)
			if l and (not device[l - 1].isdigit() or device.startswith("mmcblk")):
				self.hdd.append(Harddisk(device, removable))
				self.hdd.sort()
				BoxInfo.setItem("Harddisk", True)
		return error, blacklisted, removable, is_cdrom, partitions, medium_found

	def addHotplugAudiocd(self, device, physdev=None):
		# device is the device name, without /dev
		# physdev is the physical device path, which we (might) use to determine the userfriendly name
		if not physdev:
			dev, part = self.splitDeviceName(device)
			try:
				physdev = realpath("/sys/block/" + dev + "/device")[4:]
			except (IOError, OSError) as err:
				physdev = dev
				print("[Harddisk] Error %d: Couldn't determine blockdev physdev for device '%s'!  (%s)" % (err.errno, device, err.strerror))
		error, blacklisted, removable, is_cdrom, partitions, medium_found = self.getBlockDevInfo(device)
		if not blacklisted and medium_found:
			description = self.getUserfriendlyDeviceName(device, physdev)
			p = Partition(mountpoint="/media/audiocd", description=description, force_mounted=True, device=device)
			self.partitions.append(p)
			self.on_partition_list_change("add", p)
			BoxInfo.setItem("Harddisk", False)
		return error, blacklisted, removable, is_cdrom, partitions, medium_found

	def removeHotplugPartition(self, device):
		for x in self.partitions[:]:
			if x.device == device:
				self.partitions.remove(x)
				if x.mountpoint:  # Plugins won't expect unmounted devices
					self.on_partition_list_change("remove", x)
		l = len(device)
		if l and (not device[l - 1].isdigit() or (device.startswith("mmcblk") and not search(r"mmcblk\dp\d+", device))):
			for hdd in self.hdd:
				if hdd.device == device:
					hdd.stop()
					self.hdd.remove(hdd)
					break
			BoxInfo.setItem("Harddisk", len(self.hdd) > 0)

	def HDDCount(self):
		return len(self.hdd)

	def HDDList(self):
		list = []
		for hd in self.hdd:
			hdd = "%s - %s" % (hd.model(), hd.bus())
			cap = hd.capacity()
			if cap != "":
				hdd += " (%s)" % cap
			list.append((hdd, hd))
		return list

	def getCD(self):
		return self.cd

	def getMountedPartitions(self, onlyhotplug=False, mounts=None):
		if mounts is None:
			mounts = getProcMounts()
		parts = [x for x in self.partitions if (x.is_hotplug or not onlyhotplug) and x.mounted(mounts)]
		devs = set([x.device for x in parts])
		for devname in devs.copy():
			if not devname:
				continue
			dev, part = self.splitDeviceName(devname)
			if part and dev in devs:  # If this is a partition and we still have the wholedisk, remove wholedisk.
				devs.remove(dev)
		# return all devices which are not removed due to being a wholedisk when a partition exists
		return [x for x in parts if not x.device or x.device in devs]

	def splitDeviceName(self, devname):
		if search(r"^mmcblk\d(?:p\d+$|$)", devname):
			m = search(r"(?P<dev>mmcblk\d)p(?P<part>\d+)$", devname)
			if m:
				return m.group("dev"), m.group("part") and int(m.group("part")) or 0
			else:
				return devname, 0
		else:
			# this works for: sdaX, hdaX, sr0 (which is in fact dev="sr0", part=""). It doesn't work for other names like mtdblock3, but they are blacklisted anyway.
			dev = devname[:3]
			part = devname[3:]
			for p in part:
				if not p.isdigit():
					return devname, 0
			return dev, part and int(part) or 0

	def getUserfriendlyDeviceName(self, dev, phys):
		dev, part = self.splitDeviceName(dev)
		description = _("External Storage %s") % dev
		if exists(pathjoin("/sys", phys, "model")):
			description = fileReadLine(pathjoin("/sys", phys, "model"), _("Unknown"))
		elif exists(pathjoin("/sys", phys, "name")):
			description = fileReadLine(pathjoin("/sys", phys, "name"), _("Unknown"))
		else:
			print("[Harddisk] Error: Couldn't read model!")
		# not wholedisk and not partition 1
		if part and part != 1:
			description += _(" (Partition %d)") % part
		return description

	def addMountedPartition(self, device, desc):
		for x in self.partitions:
			if x.mountpoint == device:
				# already_mounted
				return
		newpartion = Partition(mountpoint=device, description=desc)
		self.partitions.append(newpartion)
		self.on_partition_list_change("add", newpartion)

	def removeMountedPartition(self, mountpoint):
		for x in self.partitions[:]:
			if x.mountpoint == mountpoint:
				self.partitions.remove(x)
				self.on_partition_list_change("remove", x)

	def setDVDSpeed(self, device, speed=0):
		ioctl_flag = int(0x5322)
		if not device.startswith("/"):
			device = "/dev/" + device
		try:
			cd = open(device)
			ioctl(cd.fileno(), ioctl_flag, speed)
			cd.close()
		except (IOError, OSError) as err:
			print("[Harddisk] Error %s: Failed to set '%s' speed to '%s'!  (%s)" % (err.errno, device, speed, err.strerror))


class UnmountTask(Task.LoggingTask):
	def __init__(self, job, hdd):
		Task.LoggingTask.__init__(self, job, _("Unmount"))
		self.hdd = hdd
		self.mountpoints = []

	def prepare(self):
		try:
			dev = self.hdd.disk_path.split(sep)[-1]
			open("/dev/nomount.%s" % dev, "wb").close()
		except (IOError, OSError) as err:
			print("[Harddisk] Error %d: UnmountTask failed to create '/dev/nomount' file!  (%s)" % (err.errno, err.strerror))
		self.setTool("umount")
		self.args.append("-f")
		for dev in self.hdd.enumMountDevices():
			self.args.append(dev)
			self.postconditions.append(Task.ReturncodePostcondition())
			self.mountpoints.append(dev)
		if not self.mountpoints:
			print("[Harddisk] UnmountTask: No mountpoints found?")
			self.cmd = "true"
			self.args = [self.cmd]

	def afterRun(self):
		for path in self.mountpoints:
			try:
				rmdir(path)
			except (IOError, OSError) as err:
				print("[Harddisk] Error %d: UnmountTask failed to remove path '%s'!  (%s)" % (err.errno, path, err.strerror))


class MountTask(Task.LoggingTask):
	def __init__(self, job, hdd):
		Task.LoggingTask.__init__(self, job, _("Mount."))
		self.hdd = hdd

	def prepare(self):
		try:
			dev = self.hdd.disk_path.split(sep)[-1]
			unlink("/dev/nomount.%s" % dev)
		except (IOError, OSError) as err:
			print("[Harddisk] Error %d: MountTask failed to remove '/dev/nomount' file!  (%s)" % (err.errno, err.strerror))
		if self.hdd.mount_device is None:
			dev = self.hdd.partitionPath("1")  # Try mounting through fstab first.
		else:
			dev = self.hdd.mount_device  # If previously mounted, use the same spot.
		lines = fileReadLines("/etc/fstab", [])
		for line in lines:
			parts = line.strip().split(" ")
			fspath = realpath(parts[0])
			if realpath(fspath) == dev:
				self.setCmdline("mount -t auto " + fspath)
				self.postconditions.append(Task.ReturncodePostcondition())
				return
		# device is not in fstab
		if BoxInfo.getItem("Udev"):
			# we can let udev do the job, re-read the partition table
			# Sorry for the sleep 2 hack...
			self.setCmdline("sleep 2; hdparm -z " + self.hdd.disk_path)
			self.postconditions.append(Task.ReturncodePostcondition())


class MkfsTask(Task.LoggingTask):
	def prepare(self):
		self.fsck_state = None

	def processOutput(self, data):
		print("[Harddisk] MkfsTask - [Mkfs] %s" % data)
		if "Writing inode tables:" in data:
			self.fsck_state = "inode"
		elif "Creating journal" in data:
			self.fsck_state = "journal"
			self.setProgress(80)
		elif "Writing superblocks " in data:
			self.setProgress(95)
		elif self.fsck_state == "inode":
			if "/" in data:
				try:
					d = data.strip(" \x08\r\n").split("/", 1)
					if "\x08" in d[1]:
						d[1] = d[1].split("\x08", 1)[0]
					self.setProgress(80 * int(d[0]) / int(d[1]))
				except Exception as err:
					print("[Harddisk] MkfsTask - [Mkfs] Error: %s" % err)
				return  # Don't log the progess.
		self.log.append(data)


harddiskmanager = HarddiskManager()


def isSleepStateDevice(device):
	ret = popen("hdparm -C %s" % device).read()
	if "SG_IO" in ret or "HDIO_DRIVE_CMD" in ret:
		return None
	if "drive state is:  standby" in ret or "drive state is:  idle" in ret:
		return True
	elif "drive state is:  active/idle" in ret:
		return False
	return None


def internalHDDNotSleeping(external=False):
	state = False
	if harddiskmanager.HDDCount():
		for hdd in harddiskmanager.HDDList():
			if hdd[1].internal or external:
				if hdd[1].idle_running and hdd[1].max_idle_time and not hdd[1].isSleeping():
					state = True
	return state


BoxInfo.setItem("ext4", isFileSystemSupported("ext4"))
