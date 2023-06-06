# -*- coding: utf-8 -*-
from Components.config import config, ConfigSelection, ConfigSubDict, ConfigYesNo
from Components.SystemInfo import BoxInfo
from Tools.CList import CList
from os.path import isfile

model = BoxInfo.getItem("model")
brand = BoxInfo.getItem("brand")
platform = BoxInfo.getItem("platform")
socfamily = BoxInfo.getItem("socfamily").replace('bcm', '').replace('hisi', '').replace('advca', '').replace('smp', '').replace('aml', '')
has_dvi = BoxInfo.getItem("DreamBoxDVI")
has_scart = BoxInfo.getItem("scart")
has_yuv = BoxInfo.getItem("yuv")
has_rca = BoxInfo.getItem("rca")
has_avjack = BoxInfo.getItem("avjack")
Has24hz = BoxInfo.getItem("Has24hz")

# The "VideoHardware" is the interface to /proc/stb/video.
# It generates hotplug events, and gives you the list of
# available and preferred modes, as well as handling the currently
# selected mode. No other strict checking is done.

config.av.edid_override = ConfigYesNo(default=False)

axis = {"480i": "0 0 719 479",
	"480p": "0 0 719 479",
	"576i": "0 0 719 575",
	"576p": "0 0 719 575",
	"720p": "0 0 1279 719",
	"1080i": "0 0 1919 1079",
	"1080p": "0 0 1919 1079",
	"2160p30": "0 0 3839 2159",
	"2160p": "0 0 3839 2159",
	"smpte": "0 0 4095 2159"}

videomode_preferred = "/proc/stb/video/videomode_preferred"
videomode_choices = "/proc/stb/video/videomode_choices"
videomode_edid = "/proc/stb/video/videomode_edid"
disp_cap = "/sys/class/amhdmitx/amhdmitx0/disp_cap"


class VideoHardware:
	rates = {} # high-level, use selectable modes.
	modes = {}  # a list of (high-level) modes for a certain port.

	rates["PAL"] = {"50Hz": {50: "pal"}, "60Hz": {60: "pal60"}, "multi": {50: "pal", 60: "pal60"}}
	rates["NTSC"] = {"60Hz": {60: "ntsc"}}
	rates["Multi"] = {"multi": {50: "pal", 60: "ntsc"}}

	if platform == "dmamlogic":
		rates["480i"] = {"60Hz": {60: "480i60hz"}}
		rates["576i"] = {"50Hz": {50: "576i50hz"}}
		rates["480p"] = {"60Hz": {60: "480p60hz"}}
		rates["576p"] = {"50Hz": {50: "576p50hz"}}
		rates["720p"] = {"50Hz": {50: "720p50hz"}, "60Hz": {60: "720p60hz"}, "auto": {60: "720p60hz"}}
		rates["1080i"] = {"50Hz": {50: "1080i50hz"}, "60Hz": {60: "1080i60hz"}, "auto": {60: "1080i60hz"}}
		rates["1080p"] = {"50Hz": {50: "1080p50hz"}, "60Hz": {60: "1080p60hz"}, "30Hz": {30: "1080p30hz"}, "25Hz": {25: "1080p25hz"}, "24Hz": {24: "1080p24hz"}, "auto": {60: "1080p60hz"}}
		rates["2160p"] = {"50Hz": {50: "2160p50hz"}, "60Hz": {60: "2160p60hz"}, "30Hz": {30: "2160p30hz"}, "25Hz": {25: "2160p25hz"}, "24Hz": {24: "2160p24hz"}, "auto": {60: "2160p60hz"}}
		rates["2160p30"] = {"25Hz": {50: "2160p25hz"}, "30Hz": {60: "2160p30hz"}, "auto": {60: "2160p30hz"}}

		rates["smpte"] = {"50Hz": {50: "smpte50hz"}, "60Hz": {60: "smpte60hz"}, "30Hz": {30: "smpte30hz"}, "25Hz": {25: "smpte25hz"}, "24Hz": {24: "smpte24hz"}, "auto": {60: "smpte60hz"}}
	else:
		rates["480i"] = {"60Hz": {60: "480i"}}
		rates["576i"] = {"50Hz": {50: "576i"}}
		rates["480p"] = {"60Hz": {60: "480p"}}
		rates["576p"] = {"50Hz": {50: "576p"}}
		rates["720p"] = {"50Hz": {50: "720p50"}, "60Hz": {60: "720p"}, "multi": {50: "720p50", 60: "720p"}, "auto": {50: "720p50", 60: "720p", 24: "720p24"}}
		rates["1080i"] = {"50Hz": {50: "1080i50"}, "59Hz": {60: "1080i59"}, "60Hz": {60: "1080i"}, "multi": {50: "1080i50", 60: "1080i"}, "auto": {50: "1080i50", 60: "1080i", 24: "1080i24", 59: "1080i59"}}
		rates["1080p"] = {"50Hz": {50: "1080p50"}, "59Hz": {60: "1080p59"}, "60Hz": {60: "1080p"}, "multi": {50: "1080p50", 60: "1080p"}, "auto": {50: "1080p50", 60: "1080p", 24: "1080p24"}}
		if BoxInfo.getItem("uhd4k"):
			if platform == "dm4kgen":
				rates["2160p"] = {"50Hz": {50: "2160p50"}, "60Hz": {60: "2160p60"}, "multi": {50: "2160p50", 60: "2160p60"}, "auto": {50: "2160p50", 60: "2160p60", 24: "2160p24"}}
			else:
				rates["2160p"] = {"50Hz": {50: "2160p50"}, "60Hz": {60: "2160p"}, "multi": {50: "2160p50", 60: "2160p"}, "auto": {50: "2160p50", 60: "2160p", 24: "2160p24"}}
			rates["2160p30"] = {"25Hz": {50: "2160p25"}, "30Hz": {60: "2160p30"}, "multi": {50: "2160p25", 60: "2160p30"}, "auto": {50: "2160p25", 60: "2160p30", 24: "2160p24"}}

	rates["PC"] = {
		"1024x768": {60: "1024x768"},
		"800x600": {60: "800x600"},
		"720x480": {60: "720x480"},
		"720x576": {60: "720x576"},
		"1280x720": {60: "1280x720"},
		"1280x720 multi": {50: "1280x720_50", 60: "1280x720"},
		"1920x1080": {60: "1920x1080"},
		"1920x1080 multi": {50: "1920x1080", 60: "1920x1080_50"},
		"1280x1024": {60: "1280x1024"},
		"1366x768": {60: "1366x768"},
		"1366x768 multi": {50: "1366x768", 60: "1366x768_50"},
		"1280x768": {60: "1280x768"},
		"640x480": {60: "640x480"}
	}

	if has_scart:
		modes["Scart"] = ["PAL", "NTSC", "Multi"]
	if has_rca:
		modes["RCA"] = ["576i", "PAL", "NTSC", "Multi"]
	if has_avjack:
		modes["Jack"] = ["PAL", "NTSC", "Multi"]

	if BoxInfo.getItem("uhd4k"):
		if socfamily in ("7376", "7444"):
			modes["HDMI"] = ["720p", "1080p", "2160p", "1080i", "576p", "576i", "480p", "480i"]
			widescreen_modes = {"720p", "1080p", "1080i", "2160p"}
		elif socfamily in ("7252", "7251", "7251s", "7252s", "72604", "7278", "3798mv200", "3798mv310", "3798cv200", "3798mv300"):
			modes["HDMI"] = ["720p", "1080p", "2160p", "2160p30", "1080i", "576p", "576i", "480p", "480i"]
			widescreen_modes = {"720p", "1080p", "1080i", "2160p", "2160p30"}
		elif socfamily == "s905":
			modes["HDMI"] = ["720p", "1080p", "2160p", "2160p30", "1080i"]
			widescreen_modes = {"720p", "1080p", "1080i", "2160p", "2160p30"}
		elif platform == "dmamlogic":
			modes["HDMI"] = ["720p", "1080p", "smpte", "2160p30", "2160p", "1080i", "576p", "576i", "480p", "480i"]
			widescreen_modes = {"720p", "1080p", "1080i", "2160p", "smpte"}
	elif socfamily in ("7241", "7358", "7362", "73625", "7356", "73565", "7424", "7425", "7435", "7581", "3716mv410", "3716cv100", "8634", "8655", "8653"):
		modes["HDMI"] = ["720p", "1080p", "1080i", "576p", "576i", "480p", "480i"]
		widescreen_modes = {"720p", "1080p", "1080i"}
	elif socfamily == "8726":
		modes["HDMI"] = ["720p", "1080p", "1080i"]
		widescreen_modes = {"720p", "1080p", "1080i"}
	else:
		modes["HDMI"] = ["720p", "1080i", "576p", "576i", "480p", "480i"]
		widescreen_modes = {"720p", "1080i"}

# For raspberrypi feel free to check https://pimylifeup.com/raspberry-pi-screen-resolution/ and adapt the code.

	modes["HDMI-PC"] = ["PC"]

	if has_yuv:
		modes["YPbPr"] = modes["HDMI"]

	if "YPbPr" in modes and not has_yuv:
		del modes["YPbPr"]

	if "Scart" in modes and not has_scart and (has_rca or has_avjack):
		modes["RCA"] = modes["Scart"]
		del modes["Scart"]

	if "Scart" in modes and not has_rca and not has_scart and not has_avjack:
		del modes["Scart"]

	if model == "hd2400":
		print("[Videomode] Read /proc/stb/info/board_revision")
		rev = open("/proc/stb/info/board_revision", "r").read()
		if rev >= "2":
			del modes["YPbPr"]

	def getOutputAspect(self):
		ret = (16, 9)
		port = config.av.videoport.value
		if port not in config.av.videomode:
			print("[Videomode] VideoHardware current port not available in getOutputAspect!!! force 16:9")
		else:
			mode = config.av.videomode[port].value
			force_widescreen = self.isWidescreenMode(port, mode)
			is_widescreen = force_widescreen or config.av.aspect.value in ("16_9", "16_10")
			is_auto = config.av.aspect.value == "auto"
			if is_widescreen:
				if force_widescreen:
					pass
				else:
					aspect = {"16_9": "16:9", "16_10": "16:10"}[config.av.aspect.value]
					if aspect == "16:10":
						ret = (16, 10)
			elif is_auto:
				if isfile("/proc/stb/vmpeg/0/aspect"):
					try:
						aspect_str = open("/proc/stb/vmpeg/0/aspect", "r").read()
					except IOError:
						print("[Videomode] Read /proc/stb/vmpeg/0/aspect failed!")
				elif isfile("/sys/class/video/screen_mode"):
					try:
						aspect_str = open("/sys/class/video/screen_mode", "r").read()
					except IOError:
						print("[Videomode] Read /sys/class/video/screen_mode failed!")
				if aspect_str == "1": # 4:3
					ret = (4, 3)
			else:  # 4:3
				ret = (4, 3)
		return ret

	def __init__(self):
		self.last_modes_preferred = []
		self.on_hotplug = CList()
		self.current_mode = None
		self.current_port = None

		self.readAvailableModes()
		self.readPreferredModes()

		if "HDMI-PC" in self.modes and not self.getModeList("HDMI-PC"):
			print("[Videomode] VideoHardware remove HDMI-PC because of not existing modes")
			del self.modes["HDMI-PC"]
		if "Scart" in self.modes and not self.getModeList("Scart"):
			print("[Videomode] VideoHardware remove Scart because of not existing modes")
			del self.modes["Scart"]
		if "YPbPr" in self.modes and not has_yuv:
			del self.modes["YPbPr"]
		if "Scart" in self.modes and not has_scart and (has_rca or has_avjack):
			modes["RCA"] = modes["Scart"]
			del self.modes["Scart"]
		if "Scart" in self.modes and not has_rca and not has_scart and not has_avjack:
			del self.modes["Scart"]

		self.createConfig()

		# take over old AVSwitch component :)
		from Components.AVSwitch import AVSwitch
		config.av.aspectratio.notifiers = []
		config.av.tvsystem.notifiers = []
		config.av.wss.notifiers = []
		AVSwitch.getOutputAspect = self.getOutputAspect

		config.av.aspect.addNotifier(self.updateAspect)
		config.av.wss.addNotifier(self.updateAspect)
		config.av.policy_169.addNotifier(self.updateAspect)
		config.av.policy_43.addNotifier(self.updateAspect)

	def readAvailableModes(self):
		if isfile(disp_cap):
			print("[Videomode] Read %s" % disp_cap)
			modes = open(disp_cap).read()[:-1].replace('*', '')
			self.modes_available = modes.splitlines()
			return self.modes_available
		else:
			try:
				modes = open(videomode_choices).read()[:-1]
			except (IOError, OSError):
				print("[Videomode] Read %s failed!" % videomode_choices)
				self.modes_available = []
				return
			self.modes_available = modes.split(' ')

	def readPreferredModes(self):
		if config.av.edid_override.value == False:
			if isfile(disp_cap):
				modes = open(disp_cap).read()[:-1].replace('*', '')
				self.modes_preferred = modes.splitlines()
				print("[Videomode] VideoHardware reading disp_cap modes: ", self.modes_preferred)
			else:
				try:
					modes = open(videomode_edid).read()[:-1]
					self.modes_preferred = modes.split(' ')
					print("[Videomode] VideoHardware reading edid modes: ", self.modes_preferred)
				except (IOError, OSError):
					print("[Videomode] Read %s failed!" % videomode_edid)
					try:
						modes = open(videomode_preferred).read()[:-1]
						self.modes_preferred = modes.split(' ')
					except IOError:
						print("[Videomode] Read %s failed!" % videomode_preferred)
						self.modes_preferred = self.modes_available
			if len(self.modes_preferred) <= 1:
				self.modes_preferred = self.modes_available
				print("[Videomode] VideoHardware reading preferred modes is empty, using all video modes")
		else:
			self.modes_preferred = self.modes_available
			print("[Videomode] VideoHardware reading preferred modes override, using all video modes")
		self.last_modes_preferred = self.modes_preferred

	# check if a high-level mode with a given rate is available.
	def isModeAvailable(self, port, mode, rate):
		rate = self.rates[mode][rate]
		for mode in rate.values():
			if port == "HDMI":
				if mode not in self.modes_preferred:
					return False
			else:
				if mode not in self.modes_available:
					return False
		return True

	def isWidescreenMode(self, port, mode):
		return mode in self.widescreen_modes

	def setMode(self, port, mode, rate, force=None):
		print("[Videomode] VideoHardware setMode - port:", port, "mode:", mode, "rate:", rate)
		# we can ignore "port"
		self.current_mode = mode
		self.current_port = port
		modes = self.rates[mode][rate]

		mode_24 = modes.get(24)
		mode_25 = modes.get(25)
		mode_30 = modes.get(30)
		mode_50 = modes.get(50)
		mode_59 = modes.get(59)
		mode_60 = modes.get(60)

		if mode_50 is None or force == 60:
			mode_50 = mode_60
		if mode_59 is None or force == 50:
			mode_59 = mode_50
		if mode_60 is None or force == 50:
			mode_60 = mode_50

		if mode_24 is None or force:
			mode_24 = mode_60
			if force == 50:
				mode_24 = mode_50
		if mode_25 is None or force:
			mode_25 = mode_60
			if force == 50:
				mode_25 = mode_50
		if mode_30 is None or force:
			mode_30 = mode_60
			if force == 50:
				mode_30 = mode_50

		if platform == "dmamlogic":
			from Components.Console import Console
			amlmode = list(modes.values())[0]
			try:
				print("[Videomode] Amlogic setting videomode to mode: %s" % amlmode)
				open('/sys/class/display/mode', 'w').write(amlmode)
			except:
				print("[Videomode] Write to /sys/class/display/mode failed!")
			try:
				open("/etc/u-boot.scr.d/000_hdmimode.scr", "w").write("setenv hdmimode %s" % amlmode)
			except:
				print("[Videomode] Write to /etc/u-boot.scr.d/000_hdmimode.scr failed!")
			try:
				open("/etc/u-boot.scr.d/000_outputmode.scr", "w").write("setenv outputmode %s" % amlmode)
			except:
				print("[Videomode] Write to /etc/u-boot.scr.d/000_outputmode.scr failed!")
			Console().ePopen("update-autoexec")
			try:
				open('/sys/class/ppmgr/ppscaler', 'w').write('1')
			except:
				print("[Videomode] Write to /sys/class/ppmgr/ppscaler failed!")
			try:
				open('/sys/class/ppmgr/ppscaler', 'w').write('0')
			except:
				print("[Videomode] Write to /sys/class/ppmgr/ppscaler failed!")
			try:
				open('/sys/class/video/axis', 'w').write(axis[mode])
			except:
				print("[Videomode] Write to /sys/class/video/axis failed!")
			if isfile("/sys/class/graphics/fb0/stride"):
				from enigma import getDesktop
				stride = open("/sys/class/graphics/fb0/stride", "r").read().strip()
				print("[Videomode] Framebuffer mode:%s  stride:%s axis:%s" % (getDesktop(0).size().width(), stride, axis[mode]))

		try:
			open("/proc/stb/video/videomode_50hz", "w").write(mode_50)
		except IOError:
			print("[Videomode] Write to /proc/stb/video/videomode_50hz failed!")
			if isfile("/proc/stb/video/videomode"):
				try:
					# fallback if no possibility to setup 50 hz mode
					open("/proc/stb/video/videomode", "w").write(mode_50)
				except IOError:
					print("[Videomode] Write to /proc/stb/video/videomode failed!")
			elif isfile("/sys/class/display/mode"):
				try:
					# fallback if no possibility to setup 50 hz mode
					open("/sys/class/display/mode", "w").write(mode_50)
				except IOError:
					print("[Videomode] Write to /sys/class/display/mode failed!")
		try:
			open("/proc/stb/video/videomode_60hz", "w").write(mode_60)
		except IOError:
			print("[Videomode] Write to /proc/stb/video/videomode_60hz failed!")

		if Has24hz and mode_24 is not None:
			try:
				open("/proc/stb/video/videomode_24hz", "w").write(mode_24)
			except IOError:
				print("[Videomode] Write to /proc/stb/video/videomode_24hz failed!")

		if brand == "gigablue":
			try:
				# use 50Hz mode (if available) for booting
				open("/etc/videomode", "w").write(mode_50)
			except IOError:
				print("[Videomode] Write to /etc/videomode failed!")

		self.updateAspect(None)

	def saveMode(self, port, mode, rate):
		print("[Videomode] VideoHardware saveMode", port, mode, rate)
		config.av.videoport.value = port
		config.av.videoport.save()
		if port in config.av.videomode:
			config.av.videomode[port].value = mode
			config.av.videomode[port].save()
		if mode in config.av.videorate:
			config.av.videorate[mode].value = rate
			config.av.videorate[mode].save()

	def isPortAvailable(self, port):
		# fixme
		return True

	def isPortUsed(self, port):
		if port == "HDMI":
			self.readPreferredModes()
			return len(self.modes_preferred) != 0
		else:
			return True

	def getPortList(self):
		return [port for port in self.modes if self.isPortAvailable(port)]

	# get a list with all modes, with all rates, for a given port.
	def getModeList(self, port):
		print("[Videomode] VideoHardware getModeList for port", port)
		res = []
		for mode in self.modes[port]:
			# list all rates which are completely valid
			rates = [rate for rate in self.rates[mode] if self.isModeAvailable(port, mode, rate)]

			# if at least one rate is ok, add this mode
			if len(rates):
				res.append((mode, rates))
		return res

	def createConfig(self, *args):
		lst = []

		config.av.videomode = ConfigSubDict()
		config.av.videorate = ConfigSubDict()

		# create list of output ports
		portlist = self.getPortList()
		for port in portlist:
			descr = port
			if descr == 'HDMI' and has_dvi:
				descr = 'DVI'
			elif descr == 'HDMI-PC' and has_dvi:
				descr = 'DVI-PC'
			lst.append((port, descr))

			# create list of available modes
			modes = self.getModeList(port)
			if len(modes):
				config.av.videomode[port] = ConfigSelection(choices=[mode for (mode, rates) in modes])
			for (mode, rates) in modes:
				ratelist = []
				for rate in rates:
					if rate == "auto" and not Has24hz:
						continue
					ratelist.append((rate, rate))
				config.av.videorate[mode] = ConfigSelection(choices=ratelist)
		config.av.videoport = ConfigSelection(choices=lst)

	def setConfiguredMode(self):
		port = config.av.videoport.value
		if port not in config.av.videomode:
			print("[Videomode] VideoHardware current port not available, not setting videomode")
			return

		mode = config.av.videomode[port].value

		if mode not in config.av.videorate:
			print("[Videomode] VideoHardware current mode not available, not setting videomode")
			return

		rate = config.av.videorate[mode].value
		self.setMode(port, mode, rate)

	def updateAspect(self, cfgelement):
		# determine aspect = {any,4:3,16:9,16:10}
		# determine policy = {bestfit,letterbox,panscan,nonlinear}

		# based on;
		#   config.av.videoport.value: current video output device
		#     Scart:
		#   config.av.aspect:
		#     4_3:            use policy_169
		#     16_9,16_10:     use policy_43
		#     auto            always "bestfit"
		#   config.av.policy_169
		#     letterbox       use letterbox
		#     panscan         use panscan
		#     scale           use bestfit
		#   config.av.policy_43
		#     pillarbox       use panscan
		#     panscan         use letterbox  ("panscan" is just a bad term, it's inverse-panscan)
		#     nonlinear       use nonlinear
		#     scale           use bestfit

		port = config.av.videoport.value
		if port not in config.av.videomode:
			print("[Videomode] VideoHardware current port not available, not setting videomode")
			return
		mode = config.av.videomode[port].value

		force_widescreen = self.isWidescreenMode(port, mode)

		is_widescreen = force_widescreen or config.av.aspect.value in ("16_9", "16_10")
		is_auto = config.av.aspect.value == "auto"
		policy2 = "policy" # use main policy

		if is_widescreen:
			if force_widescreen:
				aspect = "16:9"
			else:
				aspect = {"16_9": "16:9", "16_10": "16:10"}[config.av.aspect.value]
			policy_choices = {"pillarbox": "panscan", "panscan": "letterbox", "nonlinear": "nonlinear", "scale": "bestfit", "full": "full", "auto": "auto"}
			policy = policy_choices[config.av.policy_43.value]
			policy2_choices = {"letterbox": "letterbox", "panscan": "panscan", "scale": "bestfit", "full": "full", "auto": "auto"}
			policy2 = policy2_choices[config.av.policy_169.value]
		elif is_auto:
			aspect = "any"
			if "auto" in config.av.policy_43.choices:
				policy = "auto"
			else:
				policy = "bestfit"
		else:
			aspect = "4:3"
			policy = {"letterbox": "letterbox", "panscan": "panscan", "scale": "bestfit", "full": "full", "auto": "auto"}[config.av.policy_169.value]

		if not config.av.wss.value:
			wss = "auto(4:3_off)"
		else:
			wss = "auto"

		print("[Videomode] VideoHardware -> setting aspect, policy, policy2, wss", aspect, policy, policy2, wss)

		if BoxInfo.getItem("AmlogicFamily"):
			if platform == "dmamlogic":
				arw = "0"
				if config.av.policy_43.value == "bestfit":
					arw = "10"
				if config.av.policy_43.value == "letterbox":
					arw = "11"
				if config.av.policy_43.value == "panscan":
					arw = "12"
				try:
					open("/sys/class/video/screen_mode", "w").write(arw)
				except IOError:
					print("[Videomode] Write to /sys/class/video/screen_mode failed!")
			elif socfamily == "8726":
				arw = "0"
				if config.av.policy_43.value == "bestfit":
					arw = "10"
				if config.av.policy_43.value == "panscan":
					arw = "11"
				if config.av.policy_43.value == "letterbox":
					arw = "12"
				try:
					open("/sys/class/video/screen_mode", "w").write(arw)
				except IOError:
					print("[Videomode] Write to /sys/class/video/screen_mode failed!")

		try:
			open("/proc/stb/video/aspect", "w").write(aspect)
		except IOError:
			print("[Videomode] Write to /proc/stb/video/aspect failed!")
		try:
			open("/proc/stb/video/policy", "w").write(policy)
		except IOError:
			print("[Videomode] Write to /proc/stb/video/policy failed!")
		try:
			open("/proc/stb/denc/0/wss", "w").write(wss)
		except IOError:
			print("[Videomode] Write to /proc/stb/denc/0/wss failed!")
		try:
			open("/proc/stb/video/policy2", "w").write(policy2)
		except IOError:
			print("[Videomode] Write to /proc/stb/video/policy2 failed!")


video_hw = VideoHardware()
video_hw.setConfiguredMode()
