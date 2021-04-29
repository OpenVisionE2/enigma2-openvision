from array import array
from fcntl import ioctl
from glob import glob
from os import popen, stat
from os.path import isfile
from re import search
from six import PY2
from socket import AF_INET, SOCK_DGRAM, inet_ntoa, socket
from struct import pack, unpack
from subprocess import PIPE, Popen
from sys import maxsize, modules
from time import localtime, strftime

from boxbranding import getSoCFamily
from enigma import getBoxType, getBoxBrand, getEnigmaVersionString as getEnigmaVersion

from Components.Console import Console
from Components.SystemInfo import SystemInfo
from Tools.Directories import fileReadLine, fileReadLines

socfamily = getSoCFamily()


def _ifinfo(sock, addr, ifname):
	iface = pack("256s", ifname[:15])
	info = ioctl(sock.fileno(), addr, iface)
	if addr == 0x8927:
		return "".join(["%02x:" % ord(char) for char in info[18:24]])[:-1].upper()
	else:
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
	lines = fileReadLines("/proc/net/dev")
	if lines:
		for line in lines:
			if ifname in line:
				data = line.split("%s:" % ifname)[1].split()
				rx_bytes, tx_bytes = (data[0], data[8])
				return rx_bytes, tx_bytes


def getVersionString():
	return getImageVersionString()


def getImageVersionString():
	try:
		if isfile("/var/lib/opkg/status"):
			print("[About] Read /var/lib/opkg/status")
			status = stat("/var/lib/opkg/status")
		tm = localtime(status.st_mtime)
		if tm.tm_year >= 2018:
			return strftime("%Y-%m-%d %H:%M:%S", tm)
	except:
		print("[About] Read /var/lib/opkg/status failed.")
	return _("Unavailable")


def getFlashDateString():  # WW -placeholder for BC purposes, commented out for the moment in the Screen.
	return _("Unknown")


def getBuildDateString():
	version = fileReadLine("/etc/version")
	if version is None:
		return _("Unknown")
	return "%s-%s-%s" % (version[:4], version[4:6], version[6:8])


def getUpdateDateString():
	if isfile("/proc/openvision/compiledate"):
		build = fileReadLine("/proc/openvision/compiledate")
	elif isfile("/etc/openvision/compiledate"):
		build = fileReadLine("/etc/openvision/compiledate")
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
		try:
			print("[About] Read /var/lib/opkg/info/gstreamer.control")
			gst = [x.split("Version: ") for x in open(glob("/var/lib/opkg/info/gstreamer?.[0-9].control")[0], "r") if x.startswith("Version:")][0]
			return "%s" % gst[1].split("+")[0].replace("\n", "")
		except:
			print("[About] Read /var/lib/opkg/info/gstreamer.control failed.")
			return _("Not Installed")


def getFFmpegVersionString():
	try:
		print("[About] Read /var/lib/opkg/info/ffmpeg.control")
		ffmpeg = [x.split("Version: ") for x in open(glob("/var/lib/opkg/info/ffmpeg.control")[0], "r") if x.startswith("Version:")][0]
		version = ffmpeg[1].split("-")[0].replace("\n", "")
		return "%s" % version.split("+")[0]
	except:
		print("[About] Read /var/lib/opkg/info/ffmpeg.control failed.")
		return _("Not Installed")


def getKernelVersionString():
	version = fileReadLine("/proc/version")
	if version is None:
		return _("Unknown")
	return version.split(" ", 4)[2].split("-", 2)[0]


def getCPUBenchmark():
	try:
		cpucount = 0
		print("[About] Read /proc/cpuinfo")
		for line in open("/proc/cpuinfo").readlines():
			line = [x.strip() for x in line.strip().split(":")]
			if line[0] == "processor":
				cpucount += 1

		if not isfile("/tmp/dhry.txt"):
			cmdbenchmark = "dhry > /tmp/dhry.txt"
			Console().ePopen(cmdbenchmark)
		if isfile("/tmp/dhry.txt"):
			print("[About] Read /tmp/dhry.txt")
			cpubench = popen("cat /tmp/dhry.txt | grep 'Open Vision DMIPS' | sed 's|[^0-9]*||'").read().strip()
			benchmarkstatus = popen("cat /tmp/dhry.txt | grep 'Open Vision CPU status' | cut -f2 -d':'").read().strip()

		if cpucount > 1:
			cpumaxbench = int(cpubench) * int(cpucount)
			return "%s DMIPS per core\n%s DMIPS for all (%s) cores (%s)" % (cpubench, cpumaxbench, cpucount, benchmarkstatus)
		else:
			return "%s DMIPS (%s)" % (cpubench, benchmarkstatus)
	except:
		print("[About] Read /tmp/dhry.txt failed.")
		return _("Unknown")


def getRAMBenchmark():
	try:
		if not isfile("/tmp/streambench.txt"):
			streambenchmark = "streambench > /tmp/streambench.txt"
			Console().ePopen(streambenchmark)
		if isfile("/tmp/streambench.txt"):
			print("[About] Read /tmp/streambench.txt")
			streambench = popen("cat /tmp/streambench.txt | grep 'Open Vision copy rate' | sed 's|[^0-9]*||'").read().strip()

		return "%s MB/s copy rate" % (streambench)
	except:
		print("[About] Read /tmp/streambench.txt failed.")
		return _("Unknown")


def getCPUSerial():
	lines = fileReadLines("/proc/cpuinfo")
	if lines:
		for line in lines:
			if line[0:6] == "Serial":
				return line[10:26]
	return "0000000000000000"


def getCPUInfoString():
	try:
		cpu_count = 0
		cpu_speed = 0
		processor = ""
		print("[About] Read /proc/cpuinfo")
		for line in open("/proc/cpuinfo").readlines():
			line = [x.strip() for x in line.strip().split(":")]
			if not processor and line[0] in ("system type", "model name", "Processor"):
				processor = line[1].split()[0]
			elif not cpu_speed and line[0] == "cpu MHz":
				cpu_speed = "%1.0f" % float(line[1])
			elif line[0] == "processor":
				cpu_count += 1

		if processor.startswith("ARM") and isfile("/proc/stb/info/chipset"):
			print("[About] Read /proc/stb/info/chipset")
			processor = "%s (%s)" % (open("/proc/stb/info/chipset").readline().strip().upper(), processor)

		if not cpu_speed:
			try:
				print("[About] Read /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq")
				cpu_speed = int(open("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq").read()) / 1000
			except:
				print("[About] Read /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq failed.")
				try:
					import binascii
					print("[About] Read /sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency")
					cpu_speed = int(int(binascii.hexlify(open("/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency", "rb").read()), 16) / 100000000) * 100
				except:
					print("[About] Read /sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency failed.")
					cpu_speed = "-"

		temperature = None
		if isfile("/proc/stb/fp/temp_sensor_avs"):
			print("[About] Read /proc/stb/fp/temp_sensor_avs")
			temperature = open("/proc/stb/fp/temp_sensor_avs").readline().replace("\n", "")
		elif isfile("/proc/stb/power/avs"):
			print("[About] Read /proc/stb/power/avs")
			temperature = open("/proc/stb/power/avs").readline().replace("\n", "")
		elif isfile("/proc/stb/fp/temp_sensor"):
			print("[About] Read /proc/stb/fp/temp_sensor")
			temperature = open("/proc/stb/fp/temp_sensor").readline().replace("\n", "")
		elif isfile("/proc/stb/sensors/temp0/value"):
			print("[About] Read /proc/stb/sensors/temp0/value")
			temperature = open("/proc/stb/sensors/temp0/value").readline().replace("\n", "")
		elif isfile("/proc/stb/sensors/temp/value"):
			print("[About] Read /proc/stb/sensors/temp/value")
			temperature = open("/proc/stb/sensors/temp/value").readline().replace("\n", "")
		elif isfile("/sys/devices/virtual/thermal/thermal_zone0/temp"):
			try:
				print("[About] Read /sys/devices/virtual/thermal/thermal_zone0/temp")
				temperature = int(open("/sys/devices/virtual/thermal/thermal_zone0/temp").read().strip()) / 1000
			except:
				print("[About] Read /sys/devices/virtual/thermal/thermal_zone0/temp failed.")
		elif isfile("/sys/class/thermal/thermal_zone0/temp"):
			try:
				print("[About] Read /sys/class/thermal/thermal_zone0/temp")
				temperature = int(open("/sys/class/thermal/thermal_zone0/temp").read().strip()) / 1000
			except:
				print("[About] Read /sys/class/thermal/thermal_zone0/temp failed.")
		elif isfile("/proc/hisi/msp/pm_cpu"):
			try:
				print("[About] Read /proc/hisi/msp/pm_cpu")
				temperature = search("temperature = (\d+) degree", open("/proc/hisi/msp/pm_cpu").read()).group(1)
			except:
				print("[About] Read /proc/hisi/msp/pm_cpu failed.")
		if temperature:
			degree = u"\u00B0"
			if not isinstance(degree, str):
				degree = degree.encode("UTF-8", errors="ignore")
			return "%s %s MHz (%s) %s%sC" % (processor, cpu_speed, ngettext("%d core", "%d cores", cpu_count) % cpu_count, temperature, degree)
		return "%s %s MHz (%s)" % (processor, cpu_speed, ngettext("%d core", "%d cores", cpu_count) % cpu_count)
	except:
		print("[About] Read temperature failed.")
		return _("undefined")


def getChipSetString():
	chipset = fileReadLine("/proc/stb/info/chipset")
	if chipset is None:
		return _("Undefined")
	return str(chipset.lower())


def getCPUBrand():
	if SystemInfo["AmlogicFamily"]:
		return _("Amlogic")
	elif SystemInfo["HiSilicon"]:
		return _("HiSilicon")
	elif socfamily.startswith("smp"):
		return _("Sigma Designs")
	elif socfamily.startswith("bcm") or getBoxBrand() == "rpi":
		return _("Broadcom")
	print("[About] No CPU brand?")
	return _("Undefined")


def getCPUArch():
	if SystemInfo["ArchIsARM64"]:
		return _("ARM64")
	elif SystemInfo["ArchIsARM"]:
		return _("ARM")
	return _("Mipsel")


def getFlashType():
	if SystemInfo["SmallFlash"]:
		return _("Small - Tiny image")
	elif SystemInfo["MiddleFlash"]:
		return _("Middle - Lite image")
	return _("Normal - Standard image")


def getDVBAPI():
	return _("Old") if SystemInfo["OLDE2API"] else _("New")


def getVisionModule():
	if SystemInfo["OpenVisionModule"]:
		return _("Loaded")
	else:
		print("[About] No Open Vision module!  Hard multiboot?")
		return _("Unknown")


def getDriverInstalledDate():
	try:
		try:
			if getBoxType() in ("dm800", "dm8000"):
				print("[About] Read /var/lib/opkg/info/dvb-modules.control")
				driver = [x.split("-")[-2:-1][0][-9:] for x in open(glob("/var/lib/opkg/info/*dvb-modules*.control")[0], "r") if x.startswith("Version:")][0]
				return "%s-%s-%s" % (driver[:4], driver[4:6], driver[6:])
			else:
				print("[About] Read /var/lib/opkg/info/dvb-modules.control")
				driver = [x.split("-")[-2:-1][0][-8:] for x in open(glob("/var/lib/opkg/info/*dvb-modules*.control")[0], "r") if x.startswith("Version:")][0]
				return "%s-%s-%s" % (driver[:4], driver[4:6], driver[6:])
		except:
			print("[About] Read /var/lib/opkg/info/dvb-modules.control failed.")
			try:
				print("[About] Read /var/lib/opkg/info/dvb-proxy.control")
				driver = [x.split("Version:") for x in open(glob("/var/lib/opkg/info/*dvb-proxy*.control")[0], "r") if x.startswith("Version:")][0]
				return "%s" % driver[1].replace("\n", "")
			except:
				print("[About] Read /var/lib/opkg/info/dvb-proxy.control failed.")
				print("[About] Read /var/lib/opkg/info/platform-util.control")
				driver = [x.split("Version:") for x in open(glob("/var/lib/opkg/info/*platform-util*.control")[0], "r") if x.startswith("Version:")][0]
				return "%s" % driver[1].replace("\n", "")
	except:
		print("[About] Read driver date failed.")
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
		for i in range(_bytes):
			names.append(0)
		outbytes = unpack("iL", ioctl(
			sock.fileno(),
			0x8912,  # SIOCGIFCONF
			pack("iL", _bytes, names.buffer_info()[0])
		))[0]
		if outbytes == _bytes:
			maxPossible *= 2
		else:
			break
	namestr = names.tostring() if PY2 else names
	ifaces = []
	for i in range(0, outbytes, structSize):
		if PY2:
			iface_name = bytes.decode(namestr[i:i + 16]).split("\0", 1)[0].encode("ascii")
		else:
			iface_name = str(namestr[i:i + 16]).split("\0", 1)[0]
		if iface_name != "lo":
			iface_addr = inet_ntoa(namestr[i + 20:i + 24])
			ifaces.append((iface_name, iface_addr))
	return ifaces


def getBoxUptime():
	upTime = fileReadLine("/proc/uptime")
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
