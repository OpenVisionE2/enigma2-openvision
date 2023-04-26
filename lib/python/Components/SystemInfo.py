# -*- coding: utf-8 -*-
from hashlib import md5
from os import R_OK, access
from os.path import exists, isfile, join as pathjoin
from re import findall
from subprocess import PIPE, Popen

from enigma import Misc_Options, eDVBCIInterfaces, eDVBResourceManager, eGetEnigmaDebugLvl

from Tools.Directories import SCOPE_LIBDIR, SCOPE_SKINS, scopeLCDSkin, fileCheck, fileContains, fileReadLine, fileReadLines, resolveFilename
from Tools.StbHardware import getWakeOnLANType

MODULE_NAME = __name__.split(".")[-1]

SystemInfo = {}


class BoxInformation:  # To maintain data integrity class variables should not be accessed from outside of this class!
	def __init__(self):
		self.immutableList = []
		self.boxInfo = {}
		self.enigmaInfoList = []
		self.enigmaConfList = []
		lines = fileReadLines(pathjoin(resolveFilename(SCOPE_LIBDIR), "enigma.info"), source=MODULE_NAME)
		if lines:
			modified = self.checkChecksum(lines)
			if modified:
				print("[SystemInfo] WARNING: Enigma information file checksum is incorrect!  File appears to have been modified.")
				self.boxInfo["checksumerror"] = True
			else:
				print("[SystemInfo] Enigma information file checksum is correct.")
				self.boxInfo["checksumerror"] = False
			for line in lines:
				if line.startswith("#") or line.strip() == "":
					continue
				if "=" in line:
					item, value = [x.strip() for x in line.split("=", 1)]
					if item:
						self.immutableList.append(item)
						self.enigmaInfoList.append(item)
						self.boxInfo[item] = self.processValue(value)
			self.enigmaInfoList = sorted(self.enigmaInfoList)
			print("[SystemInfo] Enigma information file data loaded into BoxInfo.")
		else:
			print("[SystemInfo] ERROR: Enigma information file is not available!  The system is unlikely to boot or operate correctly.")
		filename = isfile(resolveFilename(SCOPE_LIBDIR, "enigma.conf"))
		if filename:
			lines = fileReadLines(pathjoin(resolveFilename(SCOPE_LIBDIR), "enigma.conf"), source=MODULE_NAME)
			print("[SystemInfo] Enigma config override file available and data loaded into BoxInfo.")
			self.boxInfo["overrideactive"] = True
			for line in lines:
				if line.startswith("#") or line.strip() == "":
					continue
				if "=" in line:
					item, value = [x.strip() for x in line.split("=", 1)]
					if item:
						self.enigmaConfList.append(item)
						if item in self.boxInfo:
							print("[SystemInfo] Note: Enigma information value '%s' with value '%s' being overridden to '%s'." % (item, self.boxInfo[item], value))
						self.boxInfo[item] = self.processValue(value)
			self.enigmaConfList = sorted(self.enigmaConfList)
		else:
			self.boxInfo["overrideactive"] = False

	def checkChecksum(self, lines):
		value = "Undefined!"
		data = []
		for line in lines:
			if line.startswith("checksum"):
				item, value = [x.strip() for x in line.split("=", 1)]
			else:
				data.append(line)
		data.append("")
		result = md5(bytearray("\n".join(data), "UTF-8", errors="ignore")).hexdigest()
		return value != result

	def processValue(self, value):
		valueTest = value.upper() if value else ""
		if value is None:
			pass
		elif (value.startswith("\"") or value.startswith("'")) and value.endswith(value[0]):
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
		elif valueTest == "NONE":
			value = None
		elif valueTest in ("FALSE", "NO", "OFF", "DISABLED", "DISABLE"):
			value = False
		elif valueTest in ("TRUE", "YES", "ON", "ENABLED", "ENABLE"):
			value = True
		elif value.isdigit() or ((value[0:1] == "-" or value[0:1] == "+") and value[1:].isdigit()):
			value = int(value)
		elif valueTest.startswith("0X"):
			try:
				value = int(value, 16)
			except ValueError:
				pass
		elif valueTest.startswith("0O"):
			try:
				value = int(value, 8)
			except ValueError:
				pass
		elif valueTest.startswith("0B"):
			try:
				value = int(value, 2)
			except ValueError:
				pass
		else:
			try:
				value = float(value)
			except ValueError:
				pass
		return value

	def getEnigmaInfoList(self):
		return self.enigmaInfoList

	def getEnigmaConfList(self):
		return self.enigmaConfList

	def getItemsList(self):
		return sorted(list(self.boxInfo.keys()))

	def getItem(self, item, default=None):
		if item in self.boxInfo:
			value = self.boxInfo[item]
		elif item in SystemInfo:
			value = SystemInfo[item]
		else:
			value = default
		return value

	def setItem(self, item, value, immutable=False):
		if item in self.immutableList:
			print("[BoxInfo] Error: Item '%s' is immutable and can not be %s!" % (item, "changed" if item in self.boxInfo else "added"))
			return False
		if immutable:
			self.immutableList.append(item)
		self.boxInfo[item] = value
		SystemInfo[item] = value
		return True

	def deleteItem(self, item):
		if item in self.immutableList:
			print("[BoxInfo] Error: Item '%s' is immutable and can not be deleted!" % item)
		elif item in self.boxInfo:
			del self.boxInfo[item]
			return True
		return False


BoxInfo = BoxInformation()

BoxInfo.setItem('HasUsbhdd', {})
BoxInfo.setItem('HasRootSubdir', False)
BoxInfo.setItem('HasMultibootMTD', False)
BoxInfo.setItem('HasKexecUSB', False)
BoxInfo.setItem('RecoveryMode', False)

from Tools.MultiBoot import getMultiBootStartupDevice, getMultiBootSlots  # This import needs to be here to avoid a SystemInfo load loop!

# Parse the boot commandline.
cmdline = fileReadLine("/proc/cmdline", source=MODULE_NAME)
cmdline = {k: v.strip('"') for k, v in findall(r'(\S+)=(".*?"|\S+)', cmdline)}


def getNumVideoDecoders():
	numVideoDecoders = 0
	while exists("/dev/dvb/adapter0/video%d" % numVideoDecoders):
		numVideoDecoders += 1
	return numVideoDecoders


def countFrontpanelLEDs():
	numLeds = exists("/proc/stb/fp/led_set_pattern") and 1 or 0
	while exists("/proc/stb/fp/led%d_pattern" % numLeds):
		numLeds += 1
	return numLeds


def hassoftcaminstalled():
	from Tools.camcontrol import CamControl
	return len(CamControl("softcam").getList()) > 1


def getBootdevice():
	dev = ("root" in cmdline and cmdline["root"].startswith("/dev/")) and cmdline["root"][5:]
	while dev and not exists("/sys/block/%s" % dev):
		dev = dev[:-1]
	return dev


def getRCFile(ext):
	filename = resolveFilename(SCOPE_SKINS, pathjoin("rc", "%s.%s" % (BoxInfo.getItem("rcname"), ext)))
	if not isfile(filename):
		filename = resolveFilename(SCOPE_SKINS, pathjoin("rc", "dmm1.%s" % ext))
	return filename


def getModuleLayout():
	modulePath = BoxInfo.getItem("enigmamodule")
	if modulePath:
		process = Popen(("/sbin/modprobe", "--dump-modversions", modulePath), stdout=PIPE, stderr=PIPE, universal_newlines=True)
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
mtdkernel = BoxInfo.getItem("mtdkernel")

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

BoxInfo.setItem("multiboot", 0 if BoxInfo.getItem("distro", "").lower() == "openvision" else 1, immutable=True)

SystemInfo["CommonInterface"] = model in ("h9combo", "h9combose", "pulse4kmini") and 1 or eDVBCIInterfaces.getInstance().getNumOfSlots() or model == "vuzero" and 0
SystemInfo["CommonInterfaceCIDelay"] = fileCheck("/proc/stb/tsmux/rmx_delay")
for cislot in range(BoxInfo.getItem("CommonInterface", 0)):
	SystemInfo["CI%dSupportsHighBitrates" % cislot] = fileCheck("/proc/stb/tsmux/ci%d_tsclk" % cislot)
	SystemInfo["CI%dRelevantPidsRoutingSupport" % cislot] = fileCheck("/proc/stb/tsmux/ci%d_relevant_pids_routing" % cislot)
SystemInfo["HasSoftcamInstalled"] = hassoftcaminstalled()
SystemInfo["NumVideoDecoders"] = getNumVideoDecoders()
SystemInfo["Udev"] = not fileCheck("/dev/.devfsd")
SystemInfo["PIPAvailable"] = BoxInfo.getItem("NumVideoDecoders", 0) > 1
SystemInfo["CanMeasureFrontendInputPower"] = eDVBResourceManager.getInstance().canMeasureFrontendInputPower()
SystemInfo["12V_Output"] = Misc_Options.getInstance().detected_12V_output()
SystemInfo["ZapMode"] = fileCheck("/proc/stb/video/zapmode") or fileCheck("/proc/stb/video/zapping_mode")
SystemInfo["NumFrontpanelLEDs"] = countFrontpanelLEDs()
SystemInfo["FrontpanelDisplay"] = exists(scopeLCDSkin) and fileCheck("/dev/dbox/oled0") or exists(scopeLCDSkin) and fileCheck("/dev/dbox/lcd0")
SystemInfo["NoFpDisplay"] = not exists(scopeLCDSkin)
SystemInfo["LCDsymbol_circle_recording"] = fileCheck("/proc/stb/lcd/symbol_circle") or platform == "gfuturesbcmarm" and fileCheck("/proc/stb/lcd/symbol_recording")
SystemInfo["LCDsymbol_timeshift"] = fileCheck("/proc/stb/lcd/symbol_timeshift")
SystemInfo["LCDshow_symbols"] = (model == "et9x00" or platform == "gfuturesbcmarm") and fileCheck("/proc/stb/lcd/show_symbols")
SystemInfo["LCDsymbol_hdd"] = platform == "gfuturesbcmarm" and fileCheck("/proc/stb/lcd/symbol_hdd")
SystemInfo["FrontpanelDisplayGrayscale"] = fileCheck("/dev/dbox/oled0")
SystemInfo["DeepstandbySupport"] = model != "dm800"
SystemInfo["Fan"] = fileCheck("/proc/stb/fp/fan") or BoxInfo.getItem("fan")
SystemInfo["FanPWM"] = BoxInfo.getItem("Fan") and fileCheck("/proc/stb/fp/fan_pwm")
SystemInfo["PowerLED"] = fileCheck("/proc/stb/power/powerled")
SystemInfo["PowerLED2"] = fileCheck("/proc/stb/power/powerled2")
SystemInfo["StandbyLED"] = fileCheck("/proc/stb/power/standbyled")
SystemInfo["SuspendLED"] = fileCheck("/proc/stb/power/suspendled")
SystemInfo["Display"] = BoxInfo.getItem("FrontpanelDisplay") or BoxInfo.getItem("StandbyLED")
SystemInfo["LedPowerColor"] = fileCheck("/proc/stb/fp/ledpowercolor")
SystemInfo["LedStandbyColor"] = fileCheck("/proc/stb/fp/ledstandbycolor")
SystemInfo["LedSuspendColor"] = fileCheck("/proc/stb/fp/ledsuspendledcolor")
SystemInfo["Power4x7On"] = fileCheck("/proc/stb/fp/power4x7on")
SystemInfo["Power4x7Standby"] = fileCheck("/proc/stb/fp/power4x7standby")
SystemInfo["Power4x7Suspend"] = fileCheck("/proc/stb/fp/power4x7suspend")
SystemInfo["WakeOnLAN"] = fileCheck("/proc/stb/power/wol") or fileCheck("/proc/stb/fp/wol")
SystemInfo["WakeOnLANType"] = getWakeOnLANType(BoxInfo.getItem("WakeOnLAN")) if BoxInfo.getItem("WakeOnLAN") else False
SystemInfo["HasExternalPIP"] = platform != "1genxt" and fileCheck("/proc/stb/vmpeg/1/external")
SystemInfo["VideoDestinationConfigurable"] = fileCheck("/proc/stb/vmpeg/0/dst_left")
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
SystemInfo["HasEMMC"] = BoxInfo.getItem("emmc")
SystemInfo["HasMMC"] = BoxInfo.getItem("mmc") or "root" in cmdline and cmdline["root"].startswith("/dev/mmcblk") if isfile("/proc/cmdline") else "mmcblk" in mtdkernel
SystemInfo["MMCEMMC"] = BoxInfo.getItem("HasMMC") or BoxInfo.getItem("HasEMMC")
SystemInfo["HasTranscoding"] = BoxInfo.getItem("transcoding") or BoxInfo.getItem("multitranscoding") or fileCheck("/proc/stb/encoder/0") or fileCheck("/dev/bcm_enc0")
SystemInfo["HasH265Encoder"] = fileContains("/proc/stb/encoder/0/vcodec_choices", "h265")
SystemInfo["CanNotDoSimultaneousTranscodeAndPIP"] = model == "vusolo4k" or platform == "gb7252"
SystemInfo["HasFrontDisplayPicon"] = model in ("et8500", "vusolo4k", "vuuno4kse", "vuduo4k", "vuduo4kse", "vuultimo4k") or platform == "gb7252"
SystemInfo["Has24hz"] = fileCheck("/proc/stb/video/videomode_24hz")
SystemInfo["HasHDMI"] = BoxInfo.getItem("hdmi")
SystemInfo["HasHDMI-CEC"] = BoxInfo.getItem("HasHDMI") and (fileCheck("/dev/cec0") or fileCheck("/dev/hdmi_cec") or fileCheck("/dev/misc/hdmi_cec0"))
SystemInfo["HasHDMIHDin"] = BoxInfo.getItem("hdmihdin")
SystemInfo["HasHDMIFHDin"] = BoxInfo.getItem("hdmifhdin")
SystemInfo["HasHDMIin"] = BoxInfo.getItem("HasHDMIHDin") or BoxInfo.getItem("HasHDMIFHDin")
SystemInfo["HasYPbPr"] = BoxInfo.getItem("yuv")
SystemInfo["HasScart"] = BoxInfo.getItem("scart")
SystemInfo["HasSVideo"] = BoxInfo.getItem("svideo")
SystemInfo["HasComposite"] = BoxInfo.getItem("rca")
SystemInfo["hasXcoreVFD"] = (model == "osmega" or platform == "4kspycat") and fileCheck("/sys/module/brcmstb_%s/parameters/pt6302_cgram" % model)
SystemInfo["HasOfflineDecoding"] = model not in ("osmini", "osminiplus", "et7000mini", "et11000", "mbmicro", "mbtwinplus", "mbmicrov2", "et7x00", "et8500")
SystemInfo["hasKexec"] = fileContains("/proc/cmdline", "kexec=1")
SystemInfo["canKexec"] = platform == "vu4kgen" and not BoxInfo.getItem("hasKexec") and isfile("/usr/bin/kernel_auto.bin") and isfile("/usr/bin/STARTUP.cpio.gz")
SystemInfo["MultiBootStartupDevice"] = getMultiBootStartupDevice()
SystemInfo["canMode12"] = "%s_4.boxmode" % model in cmdline and cmdline["%s_4.boxmode" % model] in ("1", "12") and "192M"
SystemInfo["canMultiBoot"] = getMultiBootSlots()
SystemInfo["canDualBoot"] = fileCheck("/dev/block/by-name/flag")
SystemInfo["BootDevice"] = getBootdevice()
SystemInfo["FbcTunerPowerAlwaysOn"] = platform == "vu4kgen" and not model == "vuzero4k"
SystemInfo["HasPhysicalLoopthrough"] = ["Vuplus DVB-S NIM(AVL2108)", "GIGA DVB-S2 NIM (Internal)"]
SystemInfo["HasPhysicalLoopthrough"] = ["Vuplus DVB-S NIM(AVL2108)", "GIGA DVB-S2 NIM (Internal)", "AVL6211"] if model in ("et7x00", "et8500") else ["Vuplus DVB-S NIM(AVL2108)", "GIGA DVB-S2 NIM (Internal)"]
SystemInfo["HasFBCtuner"] = ["Vuplus DVB-C NIM(BCM3158)", "Vuplus DVB-C NIM(BCM3148)", "Vuplus DVB-S NIM(7376 FBC)", "Vuplus DVB-S NIM(45308X FBC)", "Vuplus DVB-S NIM(45208 FBC)", "DVB-S2 NIM(45208 FBC)", "DVB-S2X NIM(45308X FBC)", "DVB-S2 NIM(45308 FBC)", "DVB-C NIM(3128 FBC)", "BCM45208", "BCM45308X", "BCM3158"]
SystemInfo["SmallFlash"] = BoxInfo.getItem("smallflash") and not BoxInfo.getItem("middleflash") or fileCheck("/etc/openvision/smallflash")
SystemInfo["MiddleFlash"] = BoxInfo.getItem("middleflash") and not BoxInfo.getItem("smallflash") or fileCheck("/etc/openvision/middleflash")
SystemInfo["HasCISSL"] = fileCheck("/etc/ssl/certs/customer.pem") and fileCheck("/etc/ssl/certs/device.pem")
SystemInfo["CanChangeOsdAlpha"] = access("/proc/stb/video/alpha", R_OK) and True or False
SystemInfo["ScalerSharpness"] = fileCheck("/proc/stb/vmpeg/0/pep_scaler_sharpness")
SystemInfo["OScamInstalled"] = fileCheck("/usr/bin/oscam") or fileCheck("/usr/bin/oscam-emu") or fileCheck("/usr/bin/oscam-smod")
SystemInfo["OScamIsActive"] = BoxInfo.getItem("OScamInstalled") and fileCheck("/tmp/.oscam/oscam.version")
SystemInfo["NCamInstalled"] = fileCheck("/usr/bin/ncam")
SystemInfo["NCamIsActive"] = BoxInfo.getItem("NCamInstalled") and fileCheck("/tmp/.ncam/ncam.version")
SystemInfo["OpenVisionModule"] = fileCheck("/proc/enigma/distro")
SystemInfo["OLDE2API"] = model == "dm800"
SystemInfo["7segment"] = displaytype == "7segment" or "7seg" in displaytype
SystemInfo["HiSilicon"] = socfamily.startswith("hisi") or fileCheck("/proc/hisi") or fileCheck("/usr/bin/hihalt") or fileCheck("/usr/lib/hisilicon")
SystemInfo["DefineSat"] = platform in ("octagonhisil", "octagonhisilnew", "gbmv200", "uclanhisil") or model in ("beyonwizv2", "viper4k")
SystemInfo["AmlogicFamily"] = socfamily.startswith(("aml", "meson")) or fileCheck("/proc/device-tree/amlogic-dt-id") or fileCheck("/usr/bin/amlhalt") or fileCheck("/sys/module/amports")
SystemInfo["RecoveryMode"] = fileCheck("/proc/stb/fp/boot_mode") and model not in ("hd51", "h7")
SystemInfo["AndroidMode"] = BoxInfo.getItem("RecoveryMode") and model == "multibox" or brand == "wetek"
SystemInfo["grautec"] = fileCheck("/tmp/usbtft")
SystemInfo["GraphicLCD"] = model in ("vuultimo", "xpeedlx3", "et10000", "hd2400", "sezammarvel", "atemionemesis", "mbultra", "beyonwizt4", "osmio4kplus")
SystemInfo["LCDMiniTV"] = fileCheck("/proc/stb/lcd/mode")
SystemInfo["LCDMiniTVPiP"] = BoxInfo.getItem("LCDMiniTV") and not model == "gb800ueplus" and not platform == "gb7252"
SystemInfo["DefaultDisplayBrightness"] = platform == "dm4kgen" and 8 or 5
SystemInfo["ConfigDisplay"] = BoxInfo.getItem("FrontpanelDisplay") and displaytype != "7segment" and "7seg" not in displaytype
SystemInfo["DreamBoxAudio"] = platform == "dm4kgen" or model in ("dm7080", "dm800")
SystemInfo["VFDDelay"] = model in ("sf4008", "beyonwizu4")
SystemInfo["VFDRepeats"] = brand != "ixuss" and displaytype != "7segment" and "7seg" not in displaytype
SystemInfo["VFDSymbol"] = BoxInfo.getItem("vfdsymbol")
SystemInfo["ArchIsARM64"] = architecture == "aarch64" or "64" in architecture
SystemInfo["ArchIsARM"] = architecture.startswith(("arm", "cortex"))
SystemInfo["SeekStatePlay"] = False
SystemInfo["StatePlayPause"] = False
SystemInfo["StandbyState"] = False
SystemInfo["HasH9SD"] = model in ("h9", "i55plus") and fileCheck("/dev/mmcblk0p1")
SystemInfo["HasSDnomount"] = model in ("h9", "h3", "i55plus") and (False, "none") or model in ("multibox", "h9combo", "h3") and (True, "mmcblk0")
SystemInfo["canBackupEMC"] = model in ("hd51", "h7", "vs1500") or platform == "8100s" and ("disk.img", str(BoxInfo.getItem("MultiBootStartupDevice"))) or platform == "edision4k" and ("emmc.img", str(BoxInfo.getItem("MultiBootStartupDevice"))) or BoxInfo.getItem("DefineSat") and ("usb_update.bin", "none") or model in ("og2ott4k", "ip8") and ("usb_update.bin", "none")
SystemInfo["FrontpanelLEDBlinkControl"] = fileCheck("/proc/stb/fp/led_blink")
SystemInfo["FrontpanelLEDBrightnessControl"] = fileCheck("/proc/stb/fp/led_brightness")
SystemInfo["FrontpanelLEDColorControl"] = fileCheck("/proc/stb/fp/led_color")
SystemInfo["FrontpanelLEDFadeControl"] = fileCheck("/proc/stb/fp/led_fade")
SystemInfo["FCC"] = False
SystemInfo["CanProc"] = BoxInfo.getItem("MMCEMMC") and brand != "vuplus"
SystemInfo["CanAACTranscode"] = fileCheck("/proc/stb/audio/aac_transcode_choices")
SystemInfo["CanAC3PlusTranscode"] = fileContains("/proc/stb/audio/ac3plus_choices", "force_ac3")
SystemInfo["CanAudioDelay"] = fileCheck("/proc/stb/audio/audio_delay_pcm") or fileCheck("/proc/stb/audio/audio_delay_bitstream")
SystemInfo["CanBTAudioDelay"] = fileCheck("/proc/stb/audio/btaudio_delay") or fileCheck("/proc/stb/audio/btaudio_delay_pcm")
SystemInfo["CanBTAudio"] = fileCheck("/proc/stb/audio/btaudio")
SystemInfo["CanDownmixAAC"] = fileContains("/proc/stb/audio/aac_choices", "downmix")
SystemInfo["CanDownmixAACPlus"] = fileCheck("/proc/stb/audio/aacplus_choices")
SystemInfo["CanDownmixAC3"] = fileContains("/proc/stb/audio/ac3_choices", "downmix")
SystemInfo["CanDownmixDTS"] = fileContains("/proc/stb/audio/dts_choices", "downmix")
SystemInfo["CanDTSHD"] = fileCheck("/proc/stb/audio/dtshd_choices")
SystemInfo["CanSyncMode"] = fileCheck("/proc/stb/video/sync_mode_choices")
SystemInfo["CanWMAPRO"] = fileCheck("/proc/stb/audio/wmapro")
SystemInfo["Has3DSpeaker"] = fileCheck("/proc/stb/audio/3d_surround_speaker_position_choices") or fileCheck("/proc/stb/audio/3d_surround_speaker_position")
SystemInfo["Has3DSurround"] = fileCheck("/proc/stb/audio/3d_surround_choices") or fileCheck("/proc/stb/audio/3d_surround")
SystemInfo["Has3DSurroundSoftLimiter"] = fileCheck("/proc/stb/audio/3dsurround_softlimiter_choices") or fileCheck("/proc/stb/audio/3dsurround_softlimiter")
SystemInfo["Has3DSurroundSpeaker"] = fileCheck("/proc/stb/audio/3dsurround_choices") or fileCheck("/proc/stb/audio/3dsurround")
SystemInfo["HasAutoVolume"] = fileContains("/proc/stb/audio/avl_choices", "none") or fileContains("/proc/stb/audio/avl_choices", "hdmi") or fileCheck("/proc/stb/audio/avl")
SystemInfo["HasAutoVolumeLevel"] = fileCheck("/proc/stb/audio/autovolumelevel_choices") or fileCheck("/proc/stb/audio/autovolumelevel")
SystemInfo["HasBypassEdidChecking"] = fileCheck("/proc/stb/hdmi/bypass_edid_checking")
SystemInfo["HasColordepthChoices"] = fileCheck("/proc/stb/video/hdmi_colordepth_choices")
SystemInfo["HasColordepth"] = fileCheck("/proc/stb/video/hdmi_colordepth")
SystemInfo["HasColorimetryChoices"] = fileCheck("/proc/stb/video/hdmi_colorimetry_choices")
SystemInfo["HasColorimetry"] = fileCheck("/proc/stb/video/hdmi_colorimetry")
SystemInfo["HasColorspaceChoices"] = fileCheck("/proc/stb/video/hdmi_colorspace_choices")
SystemInfo["HasColorspace"] = fileCheck("/proc/stb/video/hdmi_colorspace")
SystemInfo["HasColorspaceSimple"] = BoxInfo.getItem("HasColorspace") and BoxInfo.getItem("FbcTunerPowerAlwaysOn")
SystemInfo["HasHDMIpreemphasis"] = fileCheck("/proc/stb/hdmi/preemphasis")
SystemInfo["HasHdrType"] = fileCheck("/proc/stb/video/hdmi_hdrtype")
SystemInfo["HasMultichannelPCM"] = fileCheck("/proc/stb/audio/multichannel_pcm")
SystemInfo["HDMIAudioSource"] = fileCheck("/proc/stb/hdmi/audio_source")
SystemInfo["HDRSupport"] = fileCheck("/proc/stb/hdmi/hlg_support_choices") or fileCheck("/proc/stb/hdmi/hlg_support")
