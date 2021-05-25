from array import array
from binascii import hexlify
from fcntl import ioctl
from glob import glob
from os import popen, stat
from os.path import isfile
from six import PY2
from socket import AF_INET, SOCK_DGRAM, inet_ntoa, socket
from struct import pack, unpack
from subprocess import PIPE, Popen
from sys import maxsize, modules
from time import localtime, strftime

from enigma import getEnigmaVersionString as getEnigmaVersion

from Components.Console import Console
from Components.SystemInfo import BoxInfo
from Tools.Directories import fileReadLine, fileReadLines

MODULE_NAME = __name__.split(".")[-1]

socfamily = BoxInfo.getItem("socfamily")


def _ifinfo(sock, addr, ifname):
	iface = pack("256s", ifname[:15])
	info = ioctl(sock.fileno(), addr, iface)
	if addr == 0x8927:
		return "".join(["%02x:" % ord(char) for char in info[18:24]])[:-1].upper()
	return inet_ntoa(info[20:24])


def getIfConfig(ifname):
	ifreq = {"ifname": ifname}
	infos = {}
	sock = socket(AF_INET, SOCK_DGRAM)
	# Offsets defined in /usr/include/linux/sockios.h on linux 2.6.
	infos["addr"] = 0x8915  # SIOCGIFADDR
	infos["brdaddr"] = 0x8919  # SIOCGIFBRDADDR
	infos["hwaddr"] = 0x8927  # SIOCSIFHWADDR
	infos["netmask"] = 0x891b  # SIOCGIFNETMASK
	try:
		for k, v in infos.items():
			ifreq[k] = _ifinfo(sock, v, ifname)
	except:
		pass
	return ifreq


def getIfTransferredData(ifname):
	lines = fileReadLines("/proc/net/dev", source=MODULE_NAME)
	if lines:
		for line in lines:
			if ifname in line:
				data = line.split("%s:" % ifname)[1].split()
				rx_bytes, tx_bytes = (data[0], data[8])
				return rx_bytes, tx_bytes


def getVersionString():
	return getImageVersionString()


def getImageVersionString():
	if isfile("/var/lib/opkg/status"):
		status = stat("/var/lib/opkg/status")
		tm = localtime(status.st_mtime)
		if tm.tm_year >= 2018:
			return strftime("%Y-%m-%d %H:%M:%S", tm)
	return _("Unavailable")


def getFlashDateString():  # WW -placeholder for BC purposes, commented out for the moment in the Screen.
	return _("Unknown")


def getBuildDateString():
	version = fileReadLine("/etc/version", source=MODULE_NAME)
	if version is None:
		return _("Unknown")
	return "%s-%s-%s" % (version[:4], version[4:6], version[6:8])


def getUpdateDateString():
	if isfile("/proc/enigma/compiledate"):
		build = fileReadLine("/proc/enigma/compiledate", source=MODULE_NAME)
	elif isfile("/etc/openvision/compiledate"):
		build = fileReadLine("/etc/openvision/compiledate", source=MODULE_NAME)
	else:
		build = None
	if build is not None:
		build = build.strip()
		if build.isdigit():
			return "%s-%s-%s" % (build[:4], build[4:6], build[6:])
	return _("Unknown")


def getEnigmaVersionString():
	enigmaVersion = getEnigmaVersion()
	if "-(no branch)" in enigmaVersion:
		enigmaVersion = enigmaVersion[:-12]
	return enigmaVersion


def getGStreamerVersionString():
	if isfile("/usr/bin/gst-launch-0.10"):
		return "0.10.36"
	else:
		filenames = glob("/var/lib/opkg/info/gstreamer?.[0-9].control")
		if filenames:
			lines = fileReadLines(filenames[0], source=MODULE_NAME)
			if lines:
				for line in lines:
					if line[0:8] == "Version:":
						return line[9:].split("+")[0].split("-")[0]
	return _("Not Installed")


def getFFmpegVersionString():
	lines = fileReadLines("/var/lib/opkg/info/ffmpeg.control", source=MODULE_NAME)
	if lines:
		for line in lines:
			if line[0:8] == "Version:":
				return line[9:].split("+")[0]
	return _("Not Installed")


def getKernelVersionString():
	version = fileReadLine("/proc/version", source=MODULE_NAME)
	if version is None:
		return _("Unknown")
	return version.split(" ", 4)[2].split("-", 2)[0]


def getCPUBenchmark():
	cpuCount = 0
	lines = fileReadLines("/proc/cpuinfo", source=MODULE_NAME)
	if lines:
		for line in lines:
			line = [x.strip() for x in line.strip().split(":")]
			if line[0] == "processor":
				cpuCount += 1
	if not isfile("/tmp/dhry.txt"):
		benchmarkCmd = "/usr/bin/dhry > /tmp/dhry.txt"
		Console().ePopen(benchmarkCmd)
	if isfile("/tmp/dhry.txt"):
		lines = fileReadLines("/tmp/dhry.txt", source=MODULE_NAME)
		cpuBenchmark = 0
		cpuRating = ""
		if lines:
			for line in lines:
				if line.startswith("Open Vision DMIPS"):
					cpuBenchmark = int([x.strip() for x in line.split(":")][1])
				if line.startswith("Open Vision CPU status"):
					cpuRating = [x.strip() for x in line.split(":")][1]
		if cpuCount > 1:
			cpuMaxBenchmark = cpuBenchmark * cpuCount
			return "%s DMIPS per core\n%s DMIPS for all (%s) cores (%s)" % (cpuBenchmark, cpuMaxBenchmark, cpuCount, cpuRating)
		else:
			return "%s DMIPS (%s)" % (cpuBenchmark, cpuRating)
	return _("Unknown")


def getRAMBenchmark():
	if not isfile("/tmp/streambench.txt"):
		benchmarkCmd = "/usr/bin/streambench > /tmp/streambench.txt"
		Console().ePopen(benchmarkCmd)
	if isfile("/tmp/streambench.txt"):
		lines = fileReadLines("/tmp/streambench.txt", source=MODULE_NAME)
		ramBenchmark = 0
		if lines:
			for line in lines:
				if line.startswith("Open Vision copy rate"):
					ramBenchmark = [x.strip() for x in line.split(":")][1]
		return "%s MB/s copy rate" % ramBenchmark
	return _("Unknown")


def getCPUSerial():
	lines = fileReadLines("/proc/cpuinfo", source=MODULE_NAME)
	if lines:
		for line in lines:
			if line[0:6] == "Serial":
				return line[10:26]
	return _("Undefined")


def getCPUInfoString():
	cpuCount = 0
	cpuSpeed = 0
	processor = ""
	lines = fileReadLines("/proc/cpuinfo", source=MODULE_NAME)
	if lines:
		for line in lines:
			line = [x.strip() for x in line.strip().split(":", 1)]
			if not processor and line[0] in ("system type", "model name", "Processor"):
				processor = line[1].split()[0]
			elif not cpuSpeed and line[0] == "cpu MHz":
				cpuSpeed = "%1.0f" % float(line[1])
			elif line[0] == "processor":
				cpuCount += 1
		if processor.startswith("ARM") and isfile("/proc/stb/info/chipset"):
			processor = "%s (%s)" % (fileReadLine("/proc/stb/info/chipset", "", source=MODULE_NAME).upper(), processor)
		if not cpuSpeed:
			cpuSpeed = fileReadLine("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq", source=MODULE_NAME)
			if cpuSpeed is None:
				try:
					cpuSpeed = int(int(hexlify(open("/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency", "rb").read()), 16) / 100000000) * 100
				except:
					print("[About] Read /sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency failed.")
					cpuSpeed = "-"
			else:
				cpuSpeed = int(cpuSpeed) / 1000

		temperature = None
		if isfile("/proc/stb/fp/temp_sensor_avs"):
			temperature = fileReadLine("/proc/stb/fp/temp_sensor_avs", source=MODULE_NAME)
		elif isfile("/proc/stb/power/avs"):
			temperature = fileReadLine("/proc/stb/power/avs", source=MODULE_NAME)
		elif isfile("/proc/stb/fp/temp_sensor"):
			temperature = fileReadLine("/proc/stb/fp/temp_sensor", source=MODULE_NAME)
		elif isfile("/proc/stb/sensors/temp0/value"):
			temperature = fileReadLine("/proc/stb/sensors/temp0/value", source=MODULE_NAME)
		elif isfile("/proc/stb/sensors/temp/value"):
			temperature = fileReadLine("/proc/stb/sensors/temp/value", source=MODULE_NAME)
		elif isfile("/sys/devices/virtual/thermal/thermal_zone0/temp"):
			temperature = fileReadLine("/sys/devices/virtual/thermal/thermal_zone0/temp", source=MODULE_NAME)
			if temperature:
				temperature = int(temperature) / 1000
		elif isfile("/sys/class/thermal/thermal_zone0/temp"):
			temperature = fileReadLine("/sys/class/thermal/thermal_zone0/temp", source=MODULE_NAME)
			if temperature:
				temperature = int(temperature) / 1000
		elif isfile("/proc/hisi/msp/pm_cpu"):
			lines = fileReadLines("/proc/hisi/msp/pm_cpu", source=MODULE_NAME)
			if lines:
				for line in lines:
					if "temperature = " in line:
						temperature = line.split("temperature = ")[1].split()[0]
		if temperature:
			degree = u"\u00B0"
			if not isinstance(degree, str):
				degree = degree.encode("UTF-8", errors="ignore")
			return "%s %s MHz (%s) %s%sC" % (processor, cpuSpeed, ngettext("%d core", "%d cores", cpuCount) % cpuCount, temperature, degree)
		return "%s %s MHz (%s)" % (processor, cpuSpeed, ngettext("%d core", "%d cores", cpuCount) % cpuCount)


def getChipSetString():
	chipset = fileReadLine("/proc/stb/info/chipset", source=MODULE_NAME)
	if chipset is None:
		return _("Undefined")
	return chipset.lower()


def getCPUBrand():
	if BoxInfo.getItem("AmlogicFamily"):
		return _("Amlogic")
	elif BoxInfo.getItem("HiSilicon"):
		return _("HiSilicon")
	elif socfamily.startswith("smp"):
		return _("Sigma Designs")
	elif socfamily.startswith("bcm") or BoxInfo.getItem("brand") == "rpi":
		return _("Broadcom")
	print("[About] No CPU brand?")
	return _("Undefined")


def getCPUArch():
	if BoxInfo.getItem("ArchIsARM64"):
		return _("ARM64")
	elif BoxInfo.getItem("ArchIsARM"):
		return _("ARM")
	return _("Mipsel")


def getFlashType():
	if BoxInfo.getItem("SmallFlash"):
		return _("Small - Tiny image")
	elif BoxInfo.getItem("MiddleFlash"):
		return _("Middle - Lite image")
	return _("Normal - Standard image")


def getDVBAPI():
	return _("Old") if BoxInfo.getItem("OLDE2API") else _("New")


def getVisionModule():
	if BoxInfo.getItem("OpenVisionModule"):
		return _("Loaded")
	print("[About] No Open Vision module!  Hard multiboot?")
	return _("Unknown")


def getDriverInstalledDate():
	filenames = glob("/var/lib/opkg/info/*dvb-modules*.control")
	if filenames:
		lines = fileReadLines(filenames[0], source=MODULE_NAME)
		if lines:
			for line in lines:
				if line[0:8] == "Version:":
					driver = line.split("-")[1]
					return "%s-%s-%s" % (driver[:4], driver[4:6], driver[6:])
	filenames = glob("/var/lib/opkg/info/*dvb-proxy*.control")
	if filenames:
		lines = fileReadLines(filenames[0], source=MODULE_NAME)
		if lines:
			for line in lines:
				if line[0:8] == "Version:":
					return line.split("-")[1]
	filenames = glob("/var/lib/opkg/info/*platform-util*.control")
	if filenames:
		lines = fileReadLines(filenames[0], source=MODULE_NAME)
		if lines:
			for line in lines:
				if line[0:8] == "Version:":
					return line.split("-")[1]
	return _("Unknown")


def getPythonVersionString():
	process = Popen(("/usr/bin/python", "-V"), stdout=PIPE, stderr=PIPE)
	stdout, stderr = process.communicate()
	if process.returncode == 0:
		return stderr.strip().split()[1]
	print("[About] Get python version failed.")
	return _("Unknown")


def GetIPsFromNetworkInterfaces():
	structSize = 40 if maxsize > 2 ** 32 else 32
	sock = socket(AF_INET, SOCK_DGRAM)
	maxPossible = 8  # Initial value.
	while True:
		_bytes = maxPossible * structSize
		names = array("B")
		for index in range(_bytes):
			names.append(0)
		outbytes = unpack("iL", ioctl(sock.fileno(), 0x8912, pack("iL", _bytes, names.buffer_info()[0])))[0]  # 0x8912 = SIOCGIFCONF
		if outbytes == _bytes:
			maxPossible *= 2
		else:
			break
	nameStr = names.tostring() if PY2 else names
	ifaces = []
	for index in range(0, outbytes, structSize):
		ifaceName = bytes.decode(nameStr[index:index + 16]).split("\0", 1)[0].encode("ascii") if PY2 else str(nameStr[index:index + 16]).split("\0", 1)[0]
		if ifaceName != "lo":
			ifaces.append((ifaceName, inet_ntoa(nameStr[index + 20:index + 24])))
	return ifaces


def getBoxUptime():
	upTime = fileReadLine("/proc/uptime", source=MODULE_NAME)
	if upTime is None:
		return "-"
	secs = int(upTime.split(".")[0])
	times = []
	if secs > 86400:
		days = secs / 86400
		secs = secs % 86400
		times.append(ngettext("%d day", "%d days", days) % days)
	h = secs / 3600
	m = (secs % 3600) / 60
	times.append(ngettext("%d hour", "%d hours", h) % h)
	times.append(ngettext("%d minute", "%d minutes", m) % m)
	return " ".join(times)


def getGlibcVersion():
	process = Popen(("/lib/libc.so.6"), stdout=PIPE, stderr=PIPE)
	stdout, stderr = process.communicate()
	if process.returncode == 0:
		for line in stdout.split("\n"):
			if line.startswith("GNU C Library"):
				data = line.split()[-1]
				if data.endswith("."):
					data = data[0:-1]
				return data
	print("[About] Get glibc version failed.")
	return _("Unknown")


def getGccVersion():
	process = Popen(("/lib/libc.so.6"), stdout=PIPE, stderr=PIPE)
	stdout, stderr = process.communicate()
	if process.returncode == 0:
		for line in stdout.split("\n"):
			if line.startswith("Compiled by GNU CC version"):
				data = line.split()[-1]
				if data.endswith("."):
					data = data[0:-1]
				return data
	print("[About] Get gcc version failed.")
	return _("Unknown")


# For modules that do "from About import about".
about = modules[__name__]
