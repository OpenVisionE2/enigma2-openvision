from os import R_OK, access, listdir, walk
from os.path import isdir, isfile, join as pathjoin
from re import findall
from subprocess import PIPE, Popen

from enigma import Misc_Options, eDVBCIInterfaces, eDVBResourceManager, eGetEnigmaDebugLvl

from Tools.Directories import SCOPE_SKIN, fileCheck, fileExists, fileHas, fileReadLine, fileReadLines, pathExists, resolveFilename

MODULE_NAME = __name__.split(".")[-1]
ENIGMA_KERNEL_MODULE = "enigma.ko"
PROC_PATH = "/proc/enigma"

SystemInfo = {}


class BoxInformation:  # To maintain data integrity class variables should not be accessed from outside of this class!
	def __init__(self):
		self.enigmaList = []
		self.enigmaInfo = {}
		self.immutableList = []
		self.boxInfo = {}
		self.procList = [file for file in listdir(PROC_PATH) if isfile(pathjoin(PROC_PATH, file))] if isdir(PROC_PATH) else []
		lines = fileReadLines("/etc/enigma.conf", source=MODULE_NAME)
		if lines:
			for line in lines:
				if line.startswith("#") or line.strip() == "":
					continue
				if "=" in line:
					item, value = [x.strip() for x in line.split("=", 1)]
					if item:
						self.enigmaList.append(item)
						self.enigmaInfo[item] = self.processValue(value)
			print("[SystemInfo] Enigma config override file available and data loaded into BoxInfo.")
		for dirpath, dirnames, filenames in walk("/lib/modules"):
			if ENIGMA_KERNEL_MODULE in filenames:
				modulePath = pathjoin(dirpath, ENIGMA_KERNEL_MODULE)
				self.boxInfo["enigmamodule"] = modulePath
				self.immutableList.append("enigmamodule")
				break
		# As the /proc values are static we can save time by using cached
		# values loaded here.  If the values become dynamic this code
		# should be disabled and the dynamic code below enabled.
		if self.procList:
			for item in self.procList:
				self.boxInfo[item] = self.processValue(fileReadLine(pathjoin(PROC_PATH, item), source=MODULE_NAME))
				self.immutableList.append(item)
			print("[SystemInfo] Enigma kernel module available and data loaded into BoxInfo.")
		else:
			process = Popen(("/sbin/modinfo", "-d", modulePath), stdout=PIPE, stderr=PIPE)
			stdout, stderr = process.communicate()
			if process.returncode == 0:
				for line in stdout.split("\n"):
					if "=" in line:
						item, value = line.split("=", 1)
						if item:
							self.procList.append(item)
							self.boxInfo[item] = self.processValue(value)
							self.immutableList.append(item)
				print("[SystemInfo] Enigma kernel module not available but modinfo data loaded into BoxInfo!")
			else:
				print("[SystemInfo] Error: Unable to load Enigma kernel module data!  (Error %d: %s)" % (process.returncode, stderr.strip()))
		self.enigmaList = sorted(self.enigmaList)
		self.procList = sorted(self.procList)

	def processValue(self, value):
		if value is None:
			pass
		elif value.startswith("\"") or value.startswith("'") and value.endswith(value[0]):
			value = value[1:-1]
		elif value.startswith("(") and value.endswith(")"):
			data = []
			for item in [x.strip() for x in value[1:-1].split(",")]:
				data.append(self.processValue(item))
			value = tuple(data)
		elif value.startswith("[") and value.endswith("]"):
			data = []
			for item in [x.strip() for x in value[1:-1].split(",")]:
				data.append(self.processValue(item))
			value = list(data)
		elif value.upper() == "NONE":
			value = None
		elif value.upper() in ("FALSE", "NO", "OFF", "DISABLED"):
			value = False
		elif value.upper() in ("TRUE", "YES", "ON", "ENABLED"):
			value = True
		elif value.isdigit() or (value[0:1] == "-" and value[1:].isdigit()):
			value = int(value)
		elif value.startswith("0x") or value.startswith("0X"):
			value = int(value, 16)
		elif value.startswith("0o") or value.startswith("0O"):
			value = int(value, 8)
		elif value.startswith("0b") or value.startswith("0B"):
			value = int(value, 2)
		else:
			try:
				value = float(value)
			except ValueError:
				pass
		return value

	def getEnigmaList(self):
		return self.enigmaList

	def getProcList(self):
		return self.procList

	def getItemsList(self):
		return sorted(list(self.boxInfo.keys()))

	def getItem(self, item, default=None):
		if item in self.enigmaList:
			value = self.enigmaInfo[item]
		# As the /proc values are static we can save time by uusing cached
		# values loaded above.  If the values become dynamic this code
		# should be enabled.
		# elif item in self.procList:
		# 	value = self.processValue(fileReadLine(pathjoin(PROC_PATH, item), source=MODULE_NAME))
		elif item in self.boxInfo:
			value = self.boxInfo[item]
		elif item in SystemInfo:
			value = SystemInfo[item]
		else:
			value = default
		return value

	def setItem(self, item, value, immutable=False):
		if item in self.immutableList or item in self.procList:
			print("[BoxInfo] Error: Item '%s' is immutable and can not be %s!" % (item, "changed" if item in self.boxInfo else "added"))
			return False
		if immutable:
			self.immutableList.append(item)
		self.boxInfo[item] = value
		SystemInfo[item] = value
		return True

	def deleteItem(self, item):
		if item in self.immutableListor or item in self.procList:
			print("[BoxInfo] Error: Item '%s' is immutable and can not be deleted!" % item)
		elif item in self.boxInfo:
			del self.boxInfo[item]
			return True
		return False


BoxInfo = BoxInformation()

from Tools.Multiboot import getMultibootStartupDevice, getMultibootslots  # This import needs to be here to avoid a SystemInfo load loop!

# Parse the boot commandline.
cmdline = fileReadLine("/proc/cmdline", source=MODULE_NAME)
cmdline = {k: v.strip('"') for k, v in findall(r'(\S+)=(".*?"|\S+)', cmdline)}


def getNumVideoDecoders():
	numVideoDecoders = 0
	while fileExists("/dev/dvb/adapter0/video%d" % numVideoDecoders, "f"):
		numVideoDecoders += 1
	return numVideoDecoders


def countFrontpanelLEDs():
	numLeds = fileExists("/proc/stb/fp/led_set_pattern") and 1 or 0
	while fileExists("/proc/stb/fp/led%d_pattern" % numLeds):
		numLeds += 1
	return numLeds


def hassoftcaminstalled():
	from Tools.camcontrol import CamControl
	return len(CamControl("softcam").getList()) > 1


def getBootdevice():
	dev = ("root" in cmdline and cmdline["root"].startswith("/dev/")) and cmdline["root"][5:]
	while dev and not fileExists("/sys/block/%s" % dev):
		dev = dev[:-1]
	return dev


def getRCFile(ext):
	filename = resolveFilename(SCOPE_SKIN, pathjoin("rc_models", "%s.%s" % (BoxInfo.getItem("rcname"), ext)))
	if not isfile(filename):
		filename = resolveFilename(SCOPE_SKIN, pathjoin("rc_models", "dmm1.%s" % ext))
	return filename


def getModuleLayout():
	modulePath = BoxInfo.getItem("enigmamodule")
	if modulePath:
		process = Popen(("/sbin/modprobe", "--dump-modversions", modulePath), stdout=PIPE, stderr=PIPE)
		stdout, stderr = process.communicate()
		if process.returncode == 0:
			for detail in stdout.split("\n"):
				if "module_layout" in detail:
					return detail.split("\t")[0]
	return None


model = BoxInfo.getItem("model")
brand = BoxInfo.getItem("brand")
platform = BoxInfo.getItem("platform")
displaytype = BoxInfo.getItem("displaytype")
architecture = BoxInfo.getItem("architecture")
socfamily = BoxInfo.getItem("socfamily")

BoxInfo.setItem("DebugLevel", eGetEnigmaDebugLvl())
BoxInfo.setItem("InDebugMode", eGetEnigmaDebugLvl() >= 4)
BoxInfo.setItem("ModuleLayout", getModuleLayout(), immutable=True)

# Remote control related data.
#
BoxInfo.setItem("RCImage", getRCFile("png"))
BoxInfo.setItem("RCMapping", getRCFile("xml"))
BoxInfo.setItem("RemoteEnable", model in ("dm800", "azboxhd"))
if model in ("maram9", "axodin"):
	repeat = 400
elif model == "azboxhd":
	repeat = 150
else:
	repeat = 100
BoxInfo.setItem("RemoteRepeat", repeat)
BoxInfo.setItem("RemoteDelay", 200 if model in ("maram9", "axodin") else 700)

SystemInfo["CommonInterface"] = eDVBCIInterfaces.getInstance().getNumOfSlots()
SystemInfo["CommonInterfaceCIDelay"] = fileCheck("/proc/stb/tsmux/rmx_delay")
for cislot in range(0, SystemInfo["CommonInterface"]):
	SystemInfo["CI%dSupportsHighBitrates" % cislot] = fileCheck("/proc/stb/tsmux/ci%d_tsclk" % cislot)
	SystemInfo["CI%dRelevantPidsRoutingSupport" % cislot] = fileCheck("/proc/stb/tsmux/ci%d_relevant_pids_routing" % cislot)
SystemInfo["HasSoftcamInstalled"] = hassoftcaminstalled()
SystemInfo["NumVideoDecoders"] = getNumVideoDecoders()
SystemInfo["Udev"] = not fileExists("/dev/.devfsd")
SystemInfo["PIPAvailable"] = SystemInfo["NumVideoDecoders"] > 1
SystemInfo["CanMeasureFrontendInputPower"] = eDVBResourceManager.getInstance().canMeasureFrontendInputPower()
SystemInfo["12V_Output"] = Misc_Options.getInstance().detected_12V_output()
SystemInfo["ZapMode"] = fileCheck("/proc/stb/video/zapmode") or fileCheck("/proc/stb/video/zapping_mode")
SystemInfo["NumFrontpanelLEDs"] = countFrontpanelLEDs()
SystemInfo["FrontpanelDisplay"] = fileExists("/dev/dbox/oled0") or fileExists("/dev/dbox/lcd0")
SystemInfo["LCDsymbol_circle_recording"] = fileCheck("/proc/stb/lcd/symbol_circle") or platform == "gfuturesbcmarm" and fileCheck("/proc/stb/lcd/symbol_recording")
SystemInfo["LCDsymbol_timeshift"] = fileCheck("/proc/stb/lcd/symbol_timeshift")
SystemInfo["LCDshow_symbols"] = (model == "et9x00" or platform == "gfuturesbcmarm") and fileCheck("/proc/stb/lcd/show_symbols")
SystemInfo["LCDsymbol_hdd"] = platform == "gfuturesbcmarm" and fileCheck("/proc/stb/lcd/symbol_hdd")
SystemInfo["FrontpanelDisplayGrayscale"] = fileExists("/dev/dbox/oled0")
SystemInfo["DeepstandbySupport"] = model != "dm800"
SystemInfo["Fan"] = fileCheck("/proc/stb/fp/fan")
SystemInfo["FanPWM"] = SystemInfo["Fan"] and fileCheck("/proc/stb/fp/fan_pwm")
SystemInfo["PowerLED"] = fileCheck("/proc/stb/power/powerled")
SystemInfo["PowerLED2"] = fileCheck("/proc/stb/power/powerled2")
SystemInfo["StandbyLED"] = fileCheck("/proc/stb/power/standbyled")
SystemInfo["SuspendLED"] = fileCheck("/proc/stb/power/suspendled")
SystemInfo["Display"] = SystemInfo["FrontpanelDisplay"] or SystemInfo["StandbyLED"]
SystemInfo["LedPowerColor"] = fileCheck("/proc/stb/fp/ledpowercolor")
SystemInfo["LedStandbyColor"] = fileCheck("/proc/stb/fp/ledstandbycolor")
SystemInfo["LedSuspendColor"] = fileCheck("/proc/stb/fp/ledsuspendledcolor")
SystemInfo["Power4x7On"] = fileCheck("/proc/stb/fp/power4x7on")
SystemInfo["Power4x7Standby"] = fileCheck("/proc/stb/fp/power4x7standby")
SystemInfo["Power4x7Suspend"] = fileCheck("/proc/stb/fp/power4x7suspend")
SystemInfo["WakeOnLAN"] = fileCheck("/proc/stb/power/wol") or fileCheck("/proc/stb/fp/wol")
SystemInfo["HasExternalPIP"] = platform != "1genxt" and fileCheck("/proc/stb/vmpeg/1/external")
SystemInfo["VideoDestinationConfigurable"] = fileExists("/proc/stb/vmpeg/0/dst_left")
SystemInfo["hasPIPVisibleProc"] = fileCheck("/proc/stb/vmpeg/1/visible")
SystemInfo["MaxPIPSize"] = platform in ("gfuturesbcmarm", "8100s", "h7") and (360, 288) or (540, 432)
SystemInfo["VFD_scroll_repeats"] = model != "et8500" and fileCheck("/proc/stb/lcd/scroll_repeats")
SystemInfo["VFD_scroll_delay"] = model != "et8500" and fileCheck("/proc/stb/lcd/scroll_delay")
SystemInfo["VFD_initial_scroll_delay"] = model != "et8500" and fileCheck("/proc/stb/lcd/initial_scroll_delay")
SystemInfo["VFD_final_scroll_delay"] = model != "et8500" and fileCheck("/proc/stb/lcd/final_scroll_delay")
SystemInfo["LcdLiveTV"] = fileCheck("/proc/stb/fb/sd_detach") or fileCheck("/proc/stb/lcd/live_enable")
SystemInfo["LcdLiveTVMode"] = fileCheck("/proc/stb/lcd/mode")
SystemInfo["LcdLiveDecoder"] = fileCheck("/proc/stb/lcd/live_decoder")
SystemInfo["3DMode"] = fileCheck("/proc/stb/fb/3dmode") or fileCheck("/proc/stb/fb/primary/3d")
SystemInfo["3DZNorm"] = fileCheck("/proc/stb/fb/znorm") or fileCheck("/proc/stb/fb/primary/zoffset")
SystemInfo["Blindscan_t2_available"] = brand == "vuplus"
SystemInfo["HasFullHDSkinSupport"] = BoxInfo.getItem("fhdskin")
SystemInfo["HasBypassEdidChecking"] = fileCheck("/proc/stb/hdmi/bypass_edid_checking")
SystemInfo["HasColorspace"] = fileCheck("/proc/stb/video/hdmi_colorspace")
SystemInfo["HasColorspaceSimple"] = SystemInfo["HasColorspace"] and model in ("vusolo4k", "vuuno4k", "vuuno4kse", "vuultimo4k", "vuduo4k", "vuduo4kse")
SystemInfo["HasMultichannelPCM"] = fileCheck("/proc/stb/audio/multichannel_pcm")
SystemInfo["HasMMC"] = "root" in cmdline and cmdline["root"].startswith("/dev/mmcblk")
SystemInfo["HasTranscoding"] = BoxInfo.getItem("transcoding") or BoxInfo.getItem("multitranscoding") or pathExists("/proc/stb/encoder/0") or fileCheck("/dev/bcm_enc0")
SystemInfo["HasH265Encoder"] = fileHas("/proc/stb/encoder/0/vcodec_choices", "h265")
SystemInfo["CanNotDoSimultaneousTranscodeAndPIP"] = model in ("vusolo4k", "gbquad4k")
SystemInfo["HasColordepth"] = fileCheck("/proc/stb/video/hdmi_colordepth")
SystemInfo["HasFrontDisplayPicon"] = model in ("et8500", "vusolo4k", "vuuno4kse", "vuduo4k", "vuduo4kse", "vuultimo4k")
SystemInfo["Has24hz"] = fileCheck("/proc/stb/video/videomode_24hz") and platform != "dmamlogic"
SystemInfo["HasHDMIpreemphasis"] = fileCheck("/proc/stb/hdmi/preemphasis")
SystemInfo["HasColorimetry"] = fileCheck("/proc/stb/video/hdmi_colorimetry")
SystemInfo["HasHdrType"] = fileCheck("/proc/stb/video/hdmi_hdrtype")
SystemInfo["HasHDMI"] = BoxInfo.getItem("hdmi")
SystemInfo["HasHDMI-CEC"] = SystemInfo["HasHDMI"] and (fileExists("/dev/cec0") or fileExists("/dev/hdmi_cec") or fileExists("/dev/misc/hdmi_cec0"))
SystemInfo["HasHDMIHDin"] = BoxInfo.getItem("hdmihdin")
SystemInfo["HasHDMIFHDin"] = BoxInfo.getItem("hdmifhdin")
SystemInfo["HasHDMIin"] = SystemInfo["HasHDMIHDin"] or SystemInfo["HasHDMIFHDin"]
SystemInfo["HasYPbPr"] = BoxInfo.getItem("yuv")
SystemInfo["HasScart"] = BoxInfo.getItem("scart")
SystemInfo["HasSVideo"] = BoxInfo.getItem("svideo")
SystemInfo["HasComposite"] = BoxInfo.getItem("rca")
SystemInfo["HasAutoVolume"] = fileExists("/proc/stb/audio/avl_choices") or fileCheck("/proc/stb/audio/avl")
SystemInfo["HasAutoVolumeLevel"] = fileExists("/proc/stb/audio/autovolumelevel_choices") or fileCheck("/proc/stb/audio/autovolumelevel")
SystemInfo["Has3DSurround"] = fileExists("/proc/stb/audio/3d_surround_choices") or fileCheck("/proc/stb/audio/3d_surround")
SystemInfo["Has3DSpeaker"] = fileExists("/proc/stb/audio/3d_surround_speaker_position_choices") or fileCheck("/proc/stb/audio/3d_surround_speaker_position")
SystemInfo["Has3DSurroundSpeaker"] = fileExists("/proc/stb/audio/3dsurround_choices") or fileCheck("/proc/stb/audio/3dsurround")
SystemInfo["Has3DSurroundSoftLimiter"] = fileExists("/proc/stb/audio/3dsurround_softlimiter_choices") or fileCheck("/proc/stb/audio/3dsurround_softlimiter")
SystemInfo["hasXcoreVFD"] = (model == "osmega" or platform == "4kspycat") and fileCheck("/sys/module/brcmstb_%s/parameters/pt6302_cgram" % model)
SystemInfo["HasOfflineDecoding"] = model not in ("osmini", "osminiplus", "et7000mini", "et11000", "mbmicro", "mbtwinplus", "mbmicrov2", "et7x00", "et8500")
SystemInfo["MultibootStartupDevice"] = getMultibootStartupDevice()
SystemInfo["canMode12"] = "%s_4.boxmode" % model in cmdline and cmdline["%s_4.boxmode" % model] in ("1", "12") and "192M"
SystemInfo["canMultiBoot"] = getMultibootslots()
SystemInfo["canFlashWithOfgwrite"] = brand != "dreambox"
SystemInfo["HDRSupport"] = fileExists("/proc/stb/hdmi/hlg_support_choices") or fileCheck("/proc/stb/hdmi/hlg_support")
SystemInfo["CanDownmixAC3"] = fileHas("/proc/stb/audio/ac3_choices", "downmix")
SystemInfo["CanDownmixDTS"] = fileHas("/proc/stb/audio/dts_choices", "downmix")
SystemInfo["CanDownmixAAC"] = fileHas("/proc/stb/audio/aac_choices", "downmix")
SystemInfo["HDMIAudioSource"] = fileCheck("/proc/stb/hdmi/audio_source")
SystemInfo["BootDevice"] = getBootdevice()
SystemInfo["FbcTunerPowerAlwaysOn"] = model in ("vusolo4k", "vuduo4k", "vuduo4kse", "vuultimo4k", "vuuno4k", "vuuno4kse") or platform == "gb7252"
SystemInfo["HasPhysicalLoopthrough"] = ["Vuplus DVB-S NIM(AVL2108)", "GIGA DVB-S2 NIM (Internal)"]
SystemInfo["HasFBCtuner"] = ["Vuplus DVB-C NIM(BCM3158)", "Vuplus DVB-C NIM(BCM3148)", "Vuplus DVB-S NIM(7376 FBC)", "Vuplus DVB-S NIM(45308X FBC)", "Vuplus DVB-S NIM(45208 FBC)", "DVB-S NIM(45208 FBC)", "DVB-S2X NIM(45308X FBC)", "DVB-S2 NIM(45308 FBC)", "DVB-C NIM(3128 FBC)", "BCM45208", "BCM45308X", "BCM3158"]
SystemInfo["SmallFlash"] = fileExists("/etc/openvision/smallflash")
SystemInfo["MiddleFlash"] = fileExists("/etc/openvision/middleflash") and not fileExists("/etc/openvision/smallflash")
SystemInfo["HaveCISSL"] = fileCheck("/etc/ssl/certs/customer.pem") and fileCheck("/etc/ssl/certs/device.pem")
SystemInfo["CanChangeOsdAlpha"] = access("/proc/stb/video/alpha", R_OK) and True or False
SystemInfo["ScalerSharpness"] = fileExists("/proc/stb/vmpeg/0/pep_scaler_sharpness")
SystemInfo["OScamInstalled"] = fileExists("/usr/bin/oscam") or fileExists("/usr/bin/oscam-emu") or fileExists("/usr/bin/oscam-smod")
SystemInfo["OScamIsActive"] = SystemInfo["OScamInstalled"] and fileExists("/tmp/.oscam/oscam.version")
SystemInfo["NCamInstalled"] = fileExists("/usr/bin/ncam")
SystemInfo["NCamIsActive"] = SystemInfo["NCamInstalled"] and fileExists("/tmp/.ncam/ncam.version")
SystemInfo["OpenVisionModule"] = fileCheck("/proc/enigma/distro")
SystemInfo["OLDE2API"] = model in ("dm800", "su980")
SystemInfo["7segment"] = displaytype == "7segment" or "7seg" in displaytype
SystemInfo["HiSilicon"] = socfamily.startswith("hisi") or pathExists("/proc/hisi") or fileExists("/usr/bin/hihalt") or pathExists("/usr/lib/hisilicon")
SystemInfo["DefineSat"] = platform in ("octagonhisil", "gbmv200", "dagsmv200") or model in ("ustym4kpro", "beyonwizv2", "viper4k")
SystemInfo["AmlogicFamily"] = socfamily.startswith(("aml", "meson")) or fileExists("/proc/device-tree/amlogic-dt-id") or fileExists("/usr/bin/amlhalt") or pathExists("/sys/module/amports")
SystemInfo["OSDAnimation"] = fileCheck("/proc/stb/fb/animation_mode")
SystemInfo["RecoveryMode"] = fileCheck("/proc/stb/fp/boot_mode") and model not in ("hd51", "h7")
SystemInfo["AndroidMode"] = SystemInfo["RecoveryMode"] and model == "multibox" or brand in ("hypercube", "linkdroid", "mecool", "wetek") or platform == "dmamlogic"
SystemInfo["canDualBoot"] = fileExists("/dev/block/by-name/flag")
SystemInfo["grautec"] = fileExists("/tmp/usbtft")
SystemInfo["CanAC3plusTranscode"] = fileExists("/proc/stb/audio/ac3plus_choices")
SystemInfo["CanDTSHD"] = fileExists("/proc/stb/audio/dtshd_choices")
SystemInfo["CanWMAPRO"] = fileExists("/proc/stb/audio/wmapro")
SystemInfo["CanDownmixAACPlus"] = fileExists("/proc/stb/audio/aacplus_choices")
SystemInfo["CanAACTranscode"] = fileExists("/proc/stb/audio/aac_transcode_choices")
SystemInfo["GraphicLCD"] = model in ("vuultimo", "xpeedlx3", "et10000", "hd2400", "sezammarvel", "atemionemesis", "mbultra", "beyonwizt4", "osmio4kplus")
SystemInfo["LCDMiniTV"] = fileExists("/proc/stb/lcd/mode")
SystemInfo["LCDMiniTVPiP"] = SystemInfo["LCDMiniTV"] and model not in ("gb800ueplus", "gbquad4k", "gbue4k")
SystemInfo["DefaultDisplayBrightness"] = platform == "dm4kgen" and 8 or 5
SystemInfo["ConfigDisplay"] = SystemInfo["FrontpanelDisplay"] and displaytype != "7segment" and "7seg" not in displaytype
SystemInfo["DreamBoxAudio"] = platform == "dm4kgen" or model in ("dm7080", "dm800")
SystemInfo["VFDDelay"] = model in ("sf4008", "beyonwizu4")
SystemInfo["VFDRepeats"] = brand != "ixuss" and displaytype != "7segment" and "7seg" not in displaytype
SystemInfo["VFDSymbol"] = BoxInfo.getItem("vfdsymbol")
SystemInfo["CanBTAudio"] = fileCheck("/proc/stb/audio/btaudio")
SystemInfo["CanBTAudioDelay"] = fileCheck("/proc/stb/audio/btaudio_delay")
SystemInfo["ArchIsARM64"] = architecture == "aarch64" or "64" in architecture
SystemInfo["ArchIsARM"] = architecture.startswith(("arm", "cortex"))
SystemInfo["SeekStatePlay"] = False
SystemInfo["StatePlayPause"] = False
SystemInfo["StandbyState"] = False
SystemInfo["HasH9SD"] = model in ("h9", "i55plus") and pathExists("/dev/mmcblk0p1")
SystemInfo["HasSDnomount"] = model in ("h9", "h3", "i55plus") and (False, "none") or model in ("multibox", "h9combo", "h3") and (True, "mmcblk0")
SystemInfo["canBackupEMC"] = model in ("hd51", "h7") and ("disk.img", "%s" % SystemInfo["MultibootStartupDevice"]) or platform == "edision4k" and ("emmc.img", "%s" % SystemInfo["MultibootStartupDevice"]) or SystemInfo["DefineSat"] and ("usb_update.bin", "none")
SystemInfo["CanSyncMode"] = fileExists("/proc/stb/video/sync_mode_choices")
SystemInfo["FrontpanelLEDBlinkControl"] = fileExists("/proc/stb/fp/led_blink")
SystemInfo["FrontpanelLEDBrightnessControl"] = fileExists("/proc/stb/fp/led_brightness")
SystemInfo["FrontpanelLEDColorControl"] = fileExists("/proc/stb/fp/led_color")
SystemInfo["FrontpanelLEDFadeControl"] = fileExists("/proc/stb/fp/led_fade")
