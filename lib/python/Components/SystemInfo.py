from enigma import Misc_Options, eDVBCIInterfaces, eDVBResourceManager, eGetEnigmaDebugLvl, getBoxType, getBoxBrand
from Tools.Directories import SCOPE_PLUGINS, fileCheck, fileExists, fileHas, pathExists, resolveFilename
import os, re
from os import access, R_OK
from boxbranding import getDisplayType, getImageArch

SystemInfo = {}

#from Tools.Multiboot import getMultibootStartupDevice, getMultibootslots  # This import needs to be here to avoid a SystemInfo load loop!

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

SystemInfo["InDebugMode"] = eGetEnigmaDebugLvl() >= 4
SystemInfo["CommonInterface"] = eDVBCIInterfaces.getInstance().getNumOfSlots()
SystemInfo["CommonInterfaceCIDelay"] = fileCheck("/proc/stb/tsmux/rmx_delay")
for cislot in range(0, SystemInfo["CommonInterface"]):
	SystemInfo["CI%dSupportsHighBitrates" % cislot] = fileCheck("/proc/stb/tsmux/ci%d_tsclk" % cislot)
	SystemInfo["CI%dRelevantPidsRoutingSupport" % cislot] = fileCheck("/proc/stb/tsmux/ci%d_relevant_pids_routing" % cislot)
SystemInfo["HasSoftcamInstalled"] = hassoftcaminstalled()
SystemInfo["NumVideoDecoders"] = getNumVideoDecoders()
SystemInfo["Udev"] = not fileExists("/dev/.devfsd")
SystemInfo["PIPAvailable"] = model != "i55plus" and SystemInfo["NumVideoDecoders"] > 1
SystemInfo["CanMeasureFrontendInputPower"] = eDVBResourceManager.getInstance().canMeasureFrontendInputPower()
SystemInfo["12V_Output"] = Misc_Options.getInstance().detected_12V_output()
SystemInfo["ZapMode"] = fileCheck("/proc/stb/video/zapmode") or fileCheck("/proc/stb/video/zapping_mode")
SystemInfo["NumFrontpanelLEDs"] = countFrontpanelLEDs()
SystemInfo["FrontpanelDisplay"] = fileExists("/dev/dbox/oled0") or fileExists("/dev/dbox/lcd0")
SystemInfo["LCDsymbol_circle_recording"] = fileCheck("/proc/stb/lcd/symbol_circle") or model in ("hd51","vs1500") and fileCheck("/proc/stb/lcd/symbol_recording")
SystemInfo["LCDsymbol_timeshift"] = fileCheck("/proc/stb/lcd/symbol_timeshift")
SystemInfo["LCDshow_symbols"] = (model.startswith("et9") or model in ("hd51","vs1500")) and fileCheck("/proc/stb/lcd/show_symbols")
SystemInfo["LCDsymbol_hdd"] = model in ("hd51","vs1500") and fileCheck("/proc/stb/lcd/symbol_hdd")
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
SystemInfo["WakeOnLAN"] = model not in ("et8000","et10000") and fileCheck("/proc/stb/power/wol") or fileCheck("/proc/stb/fp/wol")
SystemInfo["HasExternalPIP"] = not (model.startswith("et9") or model.startswith("et5") or model.startswith("et6")) and fileCheck("/proc/stb/vmpeg/1/external")
SystemInfo["VideoDestinationConfigurable"] = fileExists("/proc/stb/vmpeg/0/dst_left")
SystemInfo["hasPIPVisibleProc"] = fileCheck("/proc/stb/vmpeg/1/visible")
SystemInfo["MaxPIPSize"] = model in ("hd51","h7","vs1500","e4hdultra") and (360, 288) or (540, 432)
SystemInfo["VFD_scroll_repeats"] = model != "et8500" and fileCheck("/proc/stb/lcd/scroll_repeats")
SystemInfo["VFD_scroll_delay"] = model != "et8500" and fileCheck("/proc/stb/lcd/scroll_delay")
SystemInfo["VFD_initial_scroll_delay"] = model != "et8500" and fileCheck("/proc/stb/lcd/initial_scroll_delay")
SystemInfo["VFD_final_scroll_delay"] = model != "et8500" and fileCheck("/proc/stb/lcd/final_scroll_delay")
SystemInfo["LcdLiveTV"] = fileCheck("/proc/stb/fb/sd_detach") or fileCheck("/proc/stb/lcd/live_enable")
SystemInfo["LcdLiveTVMode"] = fileCheck("/proc/stb/lcd/mode")
SystemInfo["LcdLiveDecoder"] = fileCheck("/proc/stb/lcd/live_decoder")
SystemInfo["FastChannelChange"] = False
SystemInfo["3DMode"] = fileCheck("/proc/stb/fb/3dmode") or fileCheck("/proc/stb/fb/primary/3d")
SystemInfo["3DZNorm"] = fileCheck("/proc/stb/fb/znorm") or fileCheck("/proc/stb/fb/primary/zoffset")
SystemInfo["Blindscan_t2_available"] = fileCheck("/proc/stb/info/vumodel")
SystemInfo["RcTypeChangable"] = not(model.startswith("et85") or model.startswith("et7")) and pathExists("/proc/stb/ir/rc/type")
SystemInfo["HasFullHDSkinSupport"] = model not in ("et4x00","et5x00","sh1","hd500c","hd1100","xp1000","lc") and brand not in ("minix","hardkernel")
SystemInfo["HasBypassEdidChecking"] = fileCheck("/proc/stb/hdmi/bypass_edid_checking")
SystemInfo["HasColorspace"] = fileCheck("/proc/stb/video/hdmi_colorspace")
SystemInfo["HasColorspaceSimple"] = SystemInfo["HasColorspace"] and model in ("vusolo4k","vuuno4k","vuuno4kse","vuultimo4k","vuduo4k")
SystemInfo["HasMultichannelPCM"] = fileCheck("/proc/stb/audio/multichannel_pcm")
SystemInfo["HasMMC"] = "root" in cmdline and cmdline["root"].startswith("/dev/mmcblk")
SystemInfo["HasTranscoding"] = pathExists("/proc/stb/encoder/0") or fileCheck("/dev/bcm_enc0")
SystemInfo["HasH265Encoder"] = fileHas("/proc/stb/encoder/0/vcodec_choices","h265")
SystemInfo["CanNotDoSimultaneousTranscodeAndPIP"] = model in ("vusolo4k","gbquad4k")
SystemInfo["HasColordepth"] = fileCheck("/proc/stb/video/hdmi_colordepth")
SystemInfo["HasFrontDisplayPicon"] = model in ("vusolo4k","et8500")
SystemInfo["Has24hz"] = fileCheck("/proc/stb/video/videomode_24hz")
SystemInfo["Has2160p"] = fileHas("/proc/stb/video/videomode_preferred","2160p50")
SystemInfo["HasHDMIpreemphasis"] = fileCheck("/proc/stb/hdmi/preemphasis")
SystemInfo["HasColorimetry"] = fileCheck("/proc/stb/video/hdmi_colorimetry")
SystemInfo["HasHdrType"] = fileCheck("/proc/stb/video/hdmi_hdrtype")
SystemInfo["HasHDMI-CEC"] = model not in ("dm800","dm8000") and fileExists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/HdmiCEC/plugin.pyo")) and (fileExists("/dev/cec0") or fileExists("/dev/hdmi_cec") or fileExists("/dev/misc/hdmi_cec0"))
SystemInfo["DreamBoxHDMIin"] = model in ("dm7080","dm820","dm900","dm920")
SystemInfo["HasHDMIHDin"] = model in ("sezammarvel","xpeedlx3","atemionemesis","mbultra","beyonwizt4","hd2400","dm7080","et10000")
SystemInfo["HasHDMIFHDin"] = model in ("dm820","dm900","dm920","vuultimo4k","beyonwizu4","et13000","sf5008","vuuno4kse", "vuduo4k","gbquad4k")
SystemInfo["HDMIin"] = SystemInfo["HasHDMIHDin"] or SystemInfo["HasHDMIFHDin"]
SystemInfo["HasYPbPr"] = model in ("dm8000","et5x00","et6x00","et9x00","et10000","formuler1","mbtwinplus","spycat","vusolo","vuduo","vuduo2","vuultimo")
SystemInfo["HasScart"] = model in ("dm8000","et4x00","et6x00","et8000","et9x00","et10000","formuler1","hd1100","hd1200","hd1265","hd2400","vusolo","vusolo2","vuduo","vuduo2","vuultimo","vuuno","xp1000")
SystemInfo["HasSVideo"] = model == "dm8000"
SystemInfo["HasComposite"] = model not in ("dm900","dm920","dreamone","i55","gbquad4k","gbue4k","hd1500","osnino","osninoplus","purehd","purehdse","revo4k","vusolo4k","vuzero4k")
SystemInfo["HasAutoVolume"] = fileExists("/proc/stb/audio/avl_choices") and fileCheck("/proc/stb/audio/avl")
SystemInfo["HasAutoVolumeLevel"] = fileExists("/proc/stb/audio/autovolumelevel_choices") and fileCheck("/proc/stb/audio/autovolumelevel")
SystemInfo["Has3DSurround"] = fileExists("/proc/stb/audio/3d_surround_choices") and fileCheck("/proc/stb/audio/3d_surround")
SystemInfo["Has3DSpeaker"] = fileExists("/proc/stb/audio/3d_surround_speaker_position_choices") and fileCheck("/proc/stb/audio/3d_surround_speaker_position")
SystemInfo["Has3DSurroundSpeaker"] = fileExists("/proc/stb/audio/3dsurround_choices") and fileCheck("/proc/stb/audio/3dsurround")
SystemInfo["Has3DSurroundSoftLimiter"] = fileExists("/proc/stb/audio/3dsurround_softlimiter_choices") and fileCheck("/proc/stb/audio/3dsurround_softlimiter")
SystemInfo["hasXcoreVFD"] = model in ("osmega","spycat4k","spycat4kmini","spycat4kcombo") and fileCheck("/sys/module/brcmstb_%s/parameters/pt6302_cgram" % model)
SystemInfo["HasOfflineDecoding"] = model not in ("osmini","osminiplus","et7000mini","et11000","mbmicro","mbtwinplus","mbmicrov2","et7x00","et8500")
#SystemInfo["MultibootStartupDevice"] = getMultibootStartupDevice()
#SystemInfo["canMode12"] = "%s_4.boxmode" % model in cmdline and cmdline["%s_4.boxmode" % model] in ("1","12") and "192M"
#SystemInfo["canMultiBoot"] = getMultibootslots()
SystemInfo["canFlashWithOfgwrite"] = brand != "dreambox"
SystemInfo["HDRSupport"] = fileExists("/proc/stb/hdmi/hlg_support_choices") and fileCheck("/proc/stb/hdmi/hlg_support")
SystemInfo["CanDownmixAC3"] = fileHas("/proc/stb/audio/ac3_choices","downmix")
SystemInfo["CanDownmixDTS"] = fileHas("/proc/stb/audio/dts_choices","downmix")
SystemInfo["CanDownmixAAC"] = fileHas("/proc/stb/audio/aac_choices","downmix")
SystemInfo["HDMIAudioSource"] = fileCheck("/proc/stb/hdmi/audio_source")
SystemInfo["BootDevice"] = getBootdevice()
SystemInfo["LnbPowerAlwaysOn"] = model in ("vusolo4k","vuduo4k","vuultimo4k","vuuno4k","vuuno4kse")
SystemInfo["SmallFlash"] = fileExists("/etc/smallflash")
SystemInfo["MiddleFlash"] = fileExists("/etc/middleflash")
SystemInfo["HaveCISSL"] = fileCheck("/etc/ssl/certs/customer.pem") and fileCheck("/etc/ssl/certs/device.pem")
SystemInfo["CanChangeOsdAlpha"] = access("/proc/stb/video/alpha", R_OK) and True or False
SystemInfo["ScalerSharpness"] = fileExists("/proc/stb/vmpeg/0/pep_scaler_sharpness")
SystemInfo["OScamInstalled"] = fileExists("/usr/bin/oscam") or fileExists("/usr/bin/oscam-emu") or fileExists("/usr/bin/oscam-smod")
SystemInfo["OScamIsActive"] = SystemInfo["OScamInstalled"] and fileExists("/tmp/.oscam/oscam.version")
SystemInfo["NCamInstalled"] = fileExists("/usr/bin/ncam")
SystemInfo["NCamIsActive"] = SystemInfo["NCamInstalled"] and fileExists("/tmp/.ncam/ncam.version")
SystemInfo["OpenVisionModule"] = fileCheck("/proc/stb/info/openvision")
SystemInfo["OLDE2API"] = model in ("dm800","su980")
SystemInfo["7segment"] = getDisplayType() == "7segment"
SystemInfo["CanFadeOut"] = brand not in ("linkdroid","mecool","minix","wetek","hardkernel","dinobot","maxytec","azbox") and model not in ("gbtrio4k","gbip4k","sf8008","sf8008m","cc1","ustym4kpro","beyonwizv2","viper4k","dreamone","hd60","hd61","h9","h9combo","h10","i55plus") and not pathExists("/proc/hisi") and not fileExists("/usr/bin/hihalt")
SystemInfo["OSDAnimation"] = fileCheck("/proc/stb/fb/animation_mode")
SystemInfo["RecoveryMode"] = fileCheck("/proc/stb/fp/boot_mode") and model not in ("hd51","h7")
SystemInfo["AndroidMode"] =  SystemInfo["RecoveryMode"] and model == "multibox" or brand in ("hypercube","linkdroid","mecool","wetek") or model == "dreamone"
SystemInfo["grautec"] = fileExists("/tmp/usbtft")
SystemInfo["CanAC3plusTranscode"] = fileExists("/proc/stb/audio/ac3plus_choices")
SystemInfo["CanDTSHD"] = fileExists("/proc/stb/audio/dtshd_choices")
SystemInfo["CanWMAPRO"] = fileExists("/proc/stb/audio/wmapro")
SystemInfo["CanDownmixAACPlus"] = fileExists("/proc/stb/audio/aacplus_choices")
SystemInfo["CanAACTranscode"] = fileExists("/proc/stb/audio/aac_transcode_choices")
SystemInfo["GraphicLCD"] = model in ("vuultimo","xpeedlx3","et10000","hd2400","sezammarvel","atemionemesis","mbultra","beyonwizt4","osmio4kplus")
SystemInfo["LCDMiniTV"] = fileExists("/proc/stb/lcd/mode")
SystemInfo["LCDMiniTVPiP"] = SystemInfo["LCDMiniTV"] and model not in ("gb800ueplus","gbquad4k","gbue4k")
SystemInfo["DefaultDisplayBrightness"] = model in ("dm900","dm920") and 8 or 5
SystemInfo["ConfigDisplay"] = SystemInfo["FrontpanelDisplay"] and getDisplayType() != "7segment"
SystemInfo["DreamBoxAudio"] = model in ("dm900","dm920","dm7080","dm800")
SystemInfo["DreamBoxDTSAudio"] = model in ("dm7080","dm820")
SystemInfo["GigaBlueAudio"] = model in ("gbquad4k","gbue4k","gbx34k")
SystemInfo["GigaBlueQuad"] = model in ("gbquad","gbquadplus")
SystemInfo["AmlogicFamily"] = brand in ("linkdroid","mecool","minix","wetek","hardkernel") or model == "dreamone"
SystemInfo["VFDDelay"] = model in ("sf4008","beyonwizu4")
SystemInfo["VFDRepeats"] = brand != "ixuss" and getDisplayType() != "7segment"
SystemInfo["HiSilicon"] = brand in ("dinobot","maxytec") or model in ("gbtrio4k","gbip4k","sf8008","sf8008m","cc1","ustym4kpro","beyonwizv2","viper4k","hd60","hd61","h9","h9combo","h10","i55plus") or pathExists("/proc/hisi") or fileExists("/usr/bin/hihalt")
SystemInfo["FirstCheckModel"] = model in ("tmtwin4k","mbmicrov2","revo4k","force3uhd","mbmicro","e4hd","e4hdhybrid","valalinux","lunix","tmnanom3","purehd","force2nano","purehdse") or brand in ("linkdroid","wetek")
SystemInfo["SecondCheckModel"] = model in ("osninopro","osnino","osninoplus","dm7020hd","dm7020hdv2","9910lx","9911lx","9920lx","tmnanose","tmnanoseplus","tmnanosem2","tmnanosem2plus","tmnanosecombo","force2plus","force2","force2se","optimussos","fusionhd","fusionhdse","force2plushv") or brand == "ixuss"
SystemInfo["ThirdCheckModel"] = model in ("gbtrio4k","gbip4k","sf8008","sf8008m","cc1","ustym4kpro","beyonwizv2","viper4k")
SystemInfo["DifferentLCDSettings"] = model in ("spycat4kmini","osmega")
SystemInfo["CanBTAudio"] = fileCheck("/proc/stb/audio/btaudio")
SystemInfo["CanBTAudioDelay"] = fileCheck("/proc/stb/audio/btaudio_delay")
SystemInfo["ArchIsARM64"] = brand in ("linkdroid","mecool") or model in ("wetekplay2","wetekhub","osmio4k","osmio4kplus","osmini4k","dreamone") or getImageArch() == "aarch64"
SystemInfo["ArchIsARM"] = SystemInfo["HiSilicon"] or brand in ("rpi","maxytec","octagon") or model in ("cube","su980","wetekplay","x8hp","odroidc2","beyonwizu4","bre2ze4k","hd51","hd60","hd61","h7","h9","h9combo","h10","i55plus","e4hdultra","protek4k","vs1500","et1x000","et13000","vusolo4k","vuuno4k","vuuno4kse","vuzero4k","vuultimo4k","vuduo4k","revo4k","tmtwin4k","galaxy4k","tm4ksuper","lunix34k","force4","lunix4k") or model.startswith("spycat4") or model.startswith("dm9") or model.startswith("force3u") or SystemInfo["GigaBlueAudio"]
SystemInfo["SeekStatePlay"] = False
SystemInfo["StatePlayPause"] = False
SystemInfo["StandbyState"] = False
SystemInfo["LEDButtons"] = model == "vuultimo"
SystemInfo["HasH9SD"] = model in ("h9","i55plus") and pathExists("/dev/mmcblk0p1")
SystemInfo["HasSDnomount"] = model in ("h9","i55plus") and (False, "none") or model in ("multibox","h9combo") and (True, "mmcblk0")
SystemInfo["canBackupEMC"] = model in ("hd51","h7") and ("disk.img", "%s" % SystemInfo["MultibootStartupDevice"]) or model in ("osmio4k","osmio4kplus","osmini4k") and ("emmc.img", "%s" % SystemInfo["MultibootStartupDevice"]) or model in ("viper4k","gbtrio4k","gbip4k","sf8008","sf8008m","beyonwizv2") and ("usb_update.bin", "none")
