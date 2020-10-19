#!/usr/bin/python
# -*- coding: utf-8 -*-
from enigma import Misc_Options, eDVBCIInterfaces, eDVBResourceManager, eGetEnigmaDebugLvl, getBoxType, getBoxBrand
from Tools.Directories import SCOPE_PLUGINS, fileCheck, fileExists, fileHas, pathExists, resolveFilename
import os, re
from os import access, R_OK
from boxbranding import getDisplayType, getImageArch, getHaveHDMIinFHD, getHaveHDMIinHD, getHaveSCART, getHaveYUV, getHaveRCA, getHaveTranscoding, getHaveMultiTranscoding, getSoCFamily, getHaveHDMI, getMachineBuild, getHaveVFDSymbol, getHaveSVIDEO

SystemInfo = {}
SystemInfo["HasRootSubdir"] = False

from Tools.Multiboot import getMultibootStartupDevice, getMultibootslots  # This import needs to be here to avoid a SystemInfo load loop!

# Parse the boot commandline.
with open("/proc/cmdline", "r") as fd:
	cmdline = fd.read()
cmdline = {k: v.strip('"') for k, v in re.findall(r'(\S+)=(".*?"|\S+)', cmdline)}

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

model = getBoxType()
brand = getBoxBrand()
platform = getMachineBuild()
displaytype = getDisplayType()
architecture = getImageArch()
socfamily = getSoCFamily()

SystemInfo["InDebugMode"] = eGetEnigmaDebugLvl() >= 4
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
SystemInfo["PowerOffDisplay"] = model != "formuler1" and fileCheck("/proc/stb/power/vfd") or fileCheck("/proc/stb/lcd/vfd")
SystemInfo["WakeOnLAN"] = fileCheck("/proc/stb/power/wol") or fileCheck("/proc/stb/fp/wol")
SystemInfo["HasExternalPIP"] = platform != "1genxt" and fileCheck("/proc/stb/vmpeg/1/external")
SystemInfo["VideoDestinationConfigurable"] = fileExists("/proc/stb/vmpeg/0/dst_left")
SystemInfo["hasPIPVisibleProc"] = fileCheck("/proc/stb/vmpeg/1/visible")
SystemInfo["MaxPIPSize"] = platform in ("gfuturesbcmarm","8100s","h7") and (360, 288) or (540, 432)
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
SystemInfo["HasFullHDSkinSupport"] = model not in ("et4x00","et5x00","sh1","hd500c","hd1100","xp1000","lc") and brand not in ("minix","hardkernel")
SystemInfo["HasBypassEdidChecking"] = fileCheck("/proc/stb/hdmi/bypass_edid_checking")
SystemInfo["HasColorspace"] = fileCheck("/proc/stb/video/hdmi_colorspace")
SystemInfo["HasColorspaceSimple"] = SystemInfo["HasColorspace"] and model in ("vusolo4k","vuuno4k","vuuno4kse","vuultimo4k","vuduo4k","vuduo4kse")
SystemInfo["HasMultichannelPCM"] = fileCheck("/proc/stb/audio/multichannel_pcm")
SystemInfo["HasMMC"] = "root" in cmdline and cmdline["root"].startswith("/dev/mmcblk")
SystemInfo["HasTranscoding"] = getHaveTranscoding() == "True" or getHaveMultiTranscoding() == "True" or pathExists("/proc/stb/encoder/0") or fileCheck("/dev/bcm_enc0")
SystemInfo["HasH265Encoder"] = fileHas("/proc/stb/encoder/0/vcodec_choices","h265")
SystemInfo["CanNotDoSimultaneousTranscodeAndPIP"] = model in ("vusolo4k","gbquad4k")
SystemInfo["HasColordepth"] = fileCheck("/proc/stb/video/hdmi_colordepth")
SystemInfo["HasFrontDisplayPicon"] = model in ("vusolo4k","et8500")
SystemInfo["Has24hz"] = fileCheck("/proc/stb/video/videomode_24hz")
SystemInfo["HasHDMIpreemphasis"] = fileCheck("/proc/stb/hdmi/preemphasis")
SystemInfo["HasColorimetry"] = fileCheck("/proc/stb/video/hdmi_colorimetry")
SystemInfo["HasHdrType"] = fileCheck("/proc/stb/video/hdmi_hdrtype")
SystemInfo["HasHDMI-CEC"] = getHaveHDMI() == "True" and fileExists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/HdmiCEC/plugin.pyo")) and (fileExists("/dev/cec0") or fileExists("/dev/hdmi_cec") or fileExists("/dev/misc/hdmi_cec0"))
SystemInfo["HasHDMIHDin"] = getHaveHDMIinHD() == "True"
SystemInfo["HasHDMIFHDin"] = getHaveHDMIinFHD() == "True"
SystemInfo["HDMIin"] = SystemInfo["HasHDMIHDin"] or SystemInfo["HasHDMIFHDin"]
SystemInfo["HasYPbPr"] = getHaveYUV() == "True"
SystemInfo["HasScart"] = getHaveSCART() == "True"
SystemInfo["HasSVideo"] = getHaveSVIDEO() == "True"
SystemInfo["HasComposite"] = getHaveRCA() == "True"
SystemInfo["HasAutoVolume"] = fileExists("/proc/stb/audio/avl_choices") and fileCheck("/proc/stb/audio/avl")
SystemInfo["HasAutoVolumeLevel"] = fileExists("/proc/stb/audio/autovolumelevel_choices") and fileCheck("/proc/stb/audio/autovolumelevel")
SystemInfo["Has3DSurround"] = fileExists("/proc/stb/audio/3d_surround_choices") and fileCheck("/proc/stb/audio/3d_surround")
SystemInfo["Has3DSpeaker"] = fileExists("/proc/stb/audio/3d_surround_speaker_position_choices") and fileCheck("/proc/stb/audio/3d_surround_speaker_position")
SystemInfo["Has3DSurroundSpeaker"] = fileExists("/proc/stb/audio/3dsurround_choices") and fileCheck("/proc/stb/audio/3dsurround")
SystemInfo["Has3DSurroundSoftLimiter"] = fileExists("/proc/stb/audio/3dsurround_softlimiter_choices") and fileCheck("/proc/stb/audio/3dsurround_softlimiter")
SystemInfo["hasXcoreVFD"] = (model == "osmega" or platform == "4kspycat") and fileCheck("/sys/module/brcmstb_%s/parameters/pt6302_cgram" % model)
SystemInfo["HasOfflineDecoding"] = model not in ("osmini","osminiplus","et7000mini","et11000","mbmicro","mbtwinplus","mbmicrov2","et7x00","et8500")
SystemInfo["MultibootStartupDevice"] = getMultibootStartupDevice()
SystemInfo["canMode12"] = "%s_4.boxmode" % model in cmdline and cmdline["%s_4.boxmode" % model] in ("1","12") and "192M"
SystemInfo["canMultiBoot"] = getMultibootslots()
SystemInfo["canFlashWithOfgwrite"] = brand != "dreambox"
SystemInfo["HDRSupport"] = fileExists("/proc/stb/hdmi/hlg_support_choices") and fileCheck("/proc/stb/hdmi/hlg_support")
SystemInfo["CanDownmixAC3"] = fileHas("/proc/stb/audio/ac3_choices","downmix")
SystemInfo["CanDownmixDTS"] = fileHas("/proc/stb/audio/dts_choices","downmix")
SystemInfo["CanDownmixAAC"] = fileHas("/proc/stb/audio/aac_choices","downmix")
SystemInfo["HDMIAudioSource"] = fileCheck("/proc/stb/hdmi/audio_source")
SystemInfo["BootDevice"] = getBootdevice()
SystemInfo["FbcTunerPowerAlwaysOn"] = model in ("vusolo4k","vuduo4k","vuduo4kse","vuultimo4k","vuuno4k","vuuno4kse") or platform == "gb7252"
SystemInfo["SmallFlash"] = fileExists("/etc/openvision/smallflash")
SystemInfo["MiddleFlash"] = fileExists("/etc/openvision/middleflash") and not fileExists("/etc/openvision/smallflash")
SystemInfo["HaveCISSL"] = fileCheck("/etc/ssl/certs/customer.pem") and fileCheck("/etc/ssl/certs/device.pem")
SystemInfo["CanChangeOsdAlpha"] = access("/proc/stb/video/alpha", R_OK) and True or False
SystemInfo["ScalerSharpness"] = fileExists("/proc/stb/vmpeg/0/pep_scaler_sharpness")
SystemInfo["OScamInstalled"] = fileExists("/usr/bin/oscam") or fileExists("/usr/bin/oscam-emu") or fileExists("/usr/bin/oscam-smod")
SystemInfo["OScamIsActive"] = SystemInfo["OScamInstalled"] and fileExists("/tmp/.oscam/oscam.version")
SystemInfo["NCamInstalled"] = fileExists("/usr/bin/ncam")
SystemInfo["NCamIsActive"] = SystemInfo["NCamInstalled"] and fileExists("/tmp/.ncam/ncam.version")
SystemInfo["OpenVisionModule"] = fileCheck("/proc/stb/info/openvision")
SystemInfo["OLDE2API"] = model in ("dm800","su980")
SystemInfo["7segment"] = displaytype == "7segment" or "7seg" in displaytype
SystemInfo["HiSilicon"] = socfamily.startswith("hisi") or pathExists("/proc/hisi") or fileExists("/usr/bin/hihalt") or pathExists("/usr/lib/hisilicon")
SystemInfo["DefineSat"] = platform in ("octagonhisil","gbmv200") or model in ("ustym4kpro","beyonwizv2","viper4k")
SystemInfo["AmlogicFamily"] = socfamily.startswith("aml") or fileExists("/proc/device-tree/amlogic-dt-id") or fileExists("/usr/bin/amlhalt") or pathExists("/sys/module/amports")
SystemInfo["OSDAnimation"] = fileCheck("/proc/stb/fb/animation_mode")
SystemInfo["RecoveryMode"] = fileCheck("/proc/stb/fp/boot_mode") and model not in ("hd51","h7")
SystemInfo["AndroidMode"] =  SystemInfo["RecoveryMode"] and model == "multibox" or brand in ("hypercube","linkdroid","mecool","wetek")
SystemInfo["grautec"] = fileExists("/tmp/usbtft")
SystemInfo["CanAC3plusTranscode"] = fileExists("/proc/stb/audio/ac3plus_choices")
SystemInfo["CanDTSHD"] = fileExists("/proc/stb/audio/dtshd_choices")
SystemInfo["CanWMAPRO"] = fileExists("/proc/stb/audio/wmapro")
SystemInfo["CanDownmixAACPlus"] = fileExists("/proc/stb/audio/aacplus_choices")
SystemInfo["CanAACTranscode"] = fileExists("/proc/stb/audio/aac_transcode_choices")
SystemInfo["GraphicLCD"] = model in ("vuultimo","xpeedlx3","et10000","hd2400","sezammarvel","atemionemesis","mbultra","beyonwizt4","osmio4kplus")
SystemInfo["LCDMiniTV"] = fileExists("/proc/stb/lcd/mode")
SystemInfo["LCDMiniTVPiP"] = SystemInfo["LCDMiniTV"] and model not in ("gb800ueplus","gbquad4k","gbue4k")
SystemInfo["DefaultDisplayBrightness"] = platform == "dm4kgen" and 8 or 5
SystemInfo["ConfigDisplay"] = SystemInfo["FrontpanelDisplay"] and displaytype != "7segment" and "7seg" not in displaytype
SystemInfo["DreamBoxAudio"] = platform == "dm4kgen" or model in ("dm7080","dm800")
SystemInfo["VFDDelay"] = model in ("sf4008","beyonwizu4")
SystemInfo["VFDRepeats"] = brand != "ixuss" and displaytype != "7segment" and "7seg" not in displaytype
SystemInfo["VFDSymbol"] = getHaveVFDSymbol() == "True"
SystemInfo["CanBTAudio"] = fileCheck("/proc/stb/audio/btaudio")
SystemInfo["CanBTAudioDelay"] = fileCheck("/proc/stb/audio/btaudio_delay")
SystemInfo["ArchIsARM64"] = architecture == "aarch64" or "64" in architecture
SystemInfo["ArchIsARM"] = architecture.startswith("arm") or architecture.startswith("cortex")
SystemInfo["SeekStatePlay"] = False
SystemInfo["StatePlayPause"] = False
SystemInfo["StandbyState"] = False
SystemInfo["HasH9SD"] = model in ("h9","i55plus") and pathExists("/dev/mmcblk0p1")
SystemInfo["HasSDnomount"] = model in ("h9","h3","i55plus") and (False, "none") or model in ("multibox","h9combo","h3") and (True, "mmcblk0")
SystemInfo["canBackupEMC"] = model in ("hd51","h7") and ("disk.img", "%s" % SystemInfo["MultibootStartupDevice"]) or platform == "edision4k" and ("emmc.img", "%s" % SystemInfo["MultibootStartupDevice"]) or SystemInfo["DefineSat"] and ("usb_update.bin", "none")
