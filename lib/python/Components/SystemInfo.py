from enigma import eDVBResourceManager, Misc_Options, eDVBCIInterfaces, eGetEnigmaDebugLvl, getBoxType, getBoxBrand
from Tools.Directories import fileExists, fileCheck, pathExists, fileHas
from Tools.HardwareInfo import HardwareInfo
import os
from os import access, R_OK

SystemInfo = {}

def getNumVideoDecoders():
	number_of_video_decoders = 0
	while fileExists("/dev/dvb/adapter0/video%d" % (number_of_video_decoders), 'f'):
		number_of_video_decoders += 1
	return number_of_video_decoders

def countFrontpanelLEDs():
	number_of_leds = fileExists("/proc/stb/fp/led_set_pattern") and 1 or 0
	while fileExists("/proc/stb/fp/led%d_pattern" % number_of_leds):
		number_of_leds += 1
	return number_of_leds

def hassoftcaminstalled():
	from Tools.camcontrol import CamControl
	return len(CamControl('softcam').getList()) > 1

SystemInfo["InDebugMode"] = eGetEnigmaDebugLvl() >= 4
SystemInfo["CommonInterface"] = eDVBCIInterfaces.getInstance().getNumOfSlots()
SystemInfo["CommonInterfaceCIDelay"] = fileCheck("/proc/stb/tsmux/rmx_delay")
for cislot in range (0, SystemInfo["CommonInterface"]):
	SystemInfo["CI%dSupportsHighBitrates" % cislot] = fileCheck("/proc/stb/tsmux/ci%d_tsclk"  % cislot)
	SystemInfo["CI%dRelevantPidsRoutingSupport" % cislot] = fileCheck("/proc/stb/tsmux/ci%d_relevant_pids_routing"  % cislot)

SystemInfo["HasSoftcamInstalled"] = hassoftcaminstalled()
SystemInfo["NumVideoDecoders"] = getNumVideoDecoders()
SystemInfo["PIPAvailable"] = SystemInfo["NumVideoDecoders"] > 1
SystemInfo["CanMeasureFrontendInputPower"] = eDVBResourceManager.getInstance().canMeasureFrontendInputPower()
SystemInfo["12V_Output"] = Misc_Options.getInstance().detected_12V_output()
SystemInfo["ZapMode"] = fileCheck("/proc/stb/video/zapmode") or fileCheck("/proc/stb/video/zapping_mode")
SystemInfo["NumFrontpanelLEDs"] = countFrontpanelLEDs()
SystemInfo["FrontpanelDisplay"] = fileExists("/dev/dbox/oled0") or fileExists("/dev/dbox/lcd0")
SystemInfo["LCDsymbol_circle_recording"] = fileCheck("/proc/stb/lcd/symbol_circle") or getBoxType() in ("hd51","vs1500") and fileCheck("/proc/stb/lcd/symbol_recording")
SystemInfo["LCDsymbol_timeshift"] = fileCheck("/proc/stb/lcd/symbol_timeshift")
SystemInfo["LCDshow_symbols"] = (getBoxType().startswith("et9") or getBoxType() in ("hd51","vs1500")) and fileCheck("/proc/stb/lcd/show_symbols")
SystemInfo["LCDsymbol_hdd"] = getBoxType() in ("hd51","vs1500") and fileCheck("/proc/stb/lcd/symbol_hdd")
SystemInfo["FrontpanelDisplayGrayscale"] = fileExists("/dev/dbox/oled0")
SystemInfo["DeepstandbySupport"] = getBoxType() != "dm800"
SystemInfo["Fan"] = fileCheck("/proc/stb/fp/fan")
SystemInfo["FanPWM"] = SystemInfo["Fan"] and fileCheck("/proc/stb/fp/fan_pwm")
SystemInfo["PowerLED"] = fileCheck("/proc/stb/power/powerled")
SystemInfo["StandbyLED"] = fileCheck("/proc/stb/power/standbyled")
SystemInfo["SuspendLED"] = fileCheck("/proc/stb/power/suspendled")
SystemInfo["LedPowerColor"] = fileExists("/proc/stb/fp/ledpowercolor")
SystemInfo["LedStandbyColor"] = fileExists("/proc/stb/fp/ledstandbycolor")
SystemInfo["LedSuspendColor"] = fileExists("/proc/stb/fp/ledsuspendledcolor")
SystemInfo["Power4x7On"] = fileExists("/proc/stb/fp/power4x7on")
SystemInfo["Power4x7Standby"] = fileExists("/proc/stb/fp/power4x7standby")
SystemInfo["Power4x7Suspend"] = fileExists("/proc/stb/fp/power4x7suspend")
SystemInfo["Display"] = SystemInfo["FrontpanelDisplay"] or SystemInfo["StandbyLED"]
SystemInfo["PowerOffDisplay"] = getBoxType() not in "formuler1" and fileCheck("/proc/stb/power/vfd") or fileCheck("/proc/stb/lcd/vfd")
SystemInfo["WakeOnLAN"] = not getBoxType().startswith("et8000") and fileCheck("/proc/stb/power/wol") or fileCheck("/proc/stb/fp/wol")
SystemInfo["HasExternalPIP"] = not (getBoxType().startswith("et9") or getBoxType().startswith("et5") or getBoxType().startswith("et6")) and fileCheck("/proc/stb/vmpeg/1/external")
SystemInfo["VideoDestinationConfigurable"] = fileExists("/proc/stb/vmpeg/0/dst_left")
SystemInfo["hasPIPVisibleProc"] = fileCheck("/proc/stb/vmpeg/1/visible")
SystemInfo["MaxPIPSize"] = getBoxType() in ("hd51","h7","vs1500","e4hdultra") and (360, 288) or (540, 432)
SystemInfo["VFD_scroll_repeats"] = not getBoxType().startswith("et8500") and fileCheck("/proc/stb/lcd/scroll_repeats")
SystemInfo["VFD_scroll_delay"] = not getBoxType().startswith("et8500") and fileCheck("/proc/stb/lcd/scroll_delay")
SystemInfo["VFD_initial_scroll_delay"] = not getBoxType().startswith("et8500") and fileCheck("/proc/stb/lcd/initial_scroll_delay")
SystemInfo["VFD_final_scroll_delay"] = not getBoxType().startswith("et8500") and fileCheck("/proc/stb/lcd/final_scroll_delay")
SystemInfo["LcdLiveTV"] = fileCheck("/proc/stb/fb/sd_detach") or fileCheck("/proc/stb/lcd/live_enable")
SystemInfo["LcdLiveTVMode"] = fileCheck("/proc/stb/lcd/mode")
SystemInfo["LcdLiveDecoder"] = fileCheck("/proc/stb/lcd/live_decoder")
SystemInfo["FastChannelChange"] = False
SystemInfo["3DMode"] = fileCheck("/proc/stb/fb/3dmode") or fileCheck("/proc/stb/fb/primary/3d")
SystemInfo["3DZNorm"] = fileCheck("/proc/stb/fb/znorm") or fileCheck("/proc/stb/fb/primary/zoffset")
SystemInfo["Blindscan_t2_available"] = fileCheck("/proc/stb/info/vumodel")
SystemInfo["RcTypeChangable"] = not(getBoxType().startswith("et8500") or getBoxType().startswith("et7")) and pathExists("/proc/stb/ir/rc/type")
SystemInfo["HasFullHDSkinSupport"] = getBoxType() not in ("et4x00","et5x00","sh1","hd500c","hd1100","xp1000","lc","k1plus","k1pro","k2pro","k2prov2","k3pro")
SystemInfo["HasBypassEdidChecking"] = fileCheck("/proc/stb/hdmi/bypass_edid_checking")
SystemInfo["HasColorspace"] = fileCheck("/proc/stb/video/hdmi_colorspace")
SystemInfo["HasColorspaceSimple"] = SystemInfo["HasColorspace"] and getBoxType() in ("vusolo4k","vuuno4k","vuuno4kse","vuultimo4k","vuduo4k")
SystemInfo["HasMultichannelPCM"] = fileCheck("/proc/stb/audio/multichannel_pcm")
SystemInfo["HasMMC"] = fileExists("/proc/cmdline") and "root=/dev/mmcblk" in open("/proc/cmdline","r").read()
SystemInfo["HasTranscoding"] = pathExists("/proc/stb/encoder/0") or fileCheck("/dev/bcm_enc0")
SystemInfo["HasH265Encoder"] = fileHas("/proc/stb/encoder/0/vcodec_choices","h265")
SystemInfo["CanNotDoSimultaneousTranscodeAndPIP"] = getBoxType() in "vusolo4k"
SystemInfo["HasColordepth"] = fileCheck("/proc/stb/video/hdmi_colordepth")
SystemInfo["HasFrontDisplayPicon"] = getBoxType() in ("vusolo4k","et8500")
SystemInfo["Has24hz"] = fileCheck("/proc/stb/video/videomode_24hz")
SystemInfo["Has2160p"] = fileHas("/proc/stb/video/videomode_preferred","2160p50")
SystemInfo["HasHDMIpreemphasis"] = fileCheck("/proc/stb/hdmi/preemphasis")
SystemInfo["HasColorimetry"] = fileCheck("/proc/stb/video/hdmi_colorimetry")
SystemInfo["HasHdrType"] = fileCheck("/proc/stb/video/hdmi_hdrtype")
SystemInfo["HasHDMI-CEC"] = HardwareInfo().has_hdmi() and fileExists("/usr/lib/enigma2/python/Plugins/SystemPlugins/HdmiCEC/plugin.pyo") and (fileExists("/dev/cec0") or fileExists("/dev/hdmi_cec") or fileExists("/dev/misc/hdmi_cec0"))
SystemInfo["HasYPbPr"] = getBoxType() in ("dm8000","et5x00","et6x00","et9x00","et10000","formuler1","mbtwinplus","spycat","vusolo","vuduo","vuduo2","vuultimo")
SystemInfo["HasScart"] = getBoxType() in ("dm8000","et4x00","et6x00","et8000","et9x00","et10000","formuler1","hd1100","hd1200","hd1265","hd2400","vusolo","vusolo2","vuduo","vuduo2","vuultimo","vuuno","xp1000")
SystemInfo["HasSVideo"] = getBoxType() == "dm8000"
SystemInfo["HasComposite"] = getBoxType() not in ("dm900","dm920","i55","gbquad4k","gbue4k","hd1500","osnino","osninoplus","purehd","purehdse","revo4k","vusolo4k","vuzero4k")
SystemInfo["HasAutoVolume"] = fileExists("/proc/stb/audio/avl_choices") and fileCheck("/proc/stb/audio/avl")
SystemInfo["HasAutoVolumeLevel"] = fileExists("/proc/stb/audio/autovolumelevel_choices") and fileCheck("/proc/stb/audio/autovolumelevel")
SystemInfo["Has3DSurround"] = fileExists("/proc/stb/audio/3d_surround_choices") and fileCheck("/proc/stb/audio/3d_surround")
SystemInfo["Has3DSpeaker"] = fileExists("/proc/stb/audio/3d_surround_speaker_position_choices") and fileCheck("/proc/stb/audio/3d_surround_speaker_position")
SystemInfo["Has3DSurroundSpeaker"] = fileExists("/proc/stb/audio/3dsurround_choices") and fileCheck("/proc/stb/audio/3dsurround")
SystemInfo["Has3DSurroundSoftLimiter"] = fileExists("/proc/stb/audio/3dsurround_softlimiter_choices") and fileCheck("/proc/stb/audio/3dsurround_softlimiter")
SystemInfo["hasXcoreVFD"] = getBoxType() in ("osmega","spycat4k","spycat4kmini","spycat4kcombo") and fileCheck("/sys/module/brcmstb_%s/parameters/pt6302_cgram" % getBoxType())
SystemInfo["HasOfflineDecoding"] = getBoxType() not in ("osmini","osminiplus","et7000mini","et11000","mbmicro","mbtwinplus","mbmicrov2","et7x00","et8500")
SystemInfo["HasRootSubdir"] = fileHas("/proc/cmdline", "rootsubdir=")
SystemInfo["canMultiBoot"] = SystemInfo["HasRootSubdir"] and (1, 4, "mmcblk0", False) or fileHas("/proc/cmdline", "_4.boxmode=") and (1, 4, "mmcblk0", False) or getBoxType() in ("gbue4k","gbquad4k") and (3, 3, "mmcblk0", True) or getBoxType() == "e4hdultra" and (1, 4, "mmcblk0", False) or getBoxType() in ("osmio4k","osmio4kplus") and (1, 4, "mmcblk1", True)
SystemInfo["canMode12"] = fileHas("/proc/cmdline", "_4.boxmode=1 ") and '192M' or fileHas("/proc/cmdline", "_4.boxmode=12") and '192M'
SystemInfo["canFlashWithOfgwrite"] = not(getBoxType().startswith("dm"))
SystemInfo["HDRSupport"] = fileExists("/proc/stb/hdmi/hlg_support_choices") and fileCheck("/proc/stb/hdmi/hlg_support")
SystemInfo["CanDownmixAC3"] = fileHas("/proc/stb/audio/ac3_choices","downmix")
SystemInfo["CanDownmixDTS"] = fileHas("/proc/stb/audio/dts_choices","downmix")
SystemInfo["CanDownmixAAC"] = fileHas("/proc/stb/audio/aac_choices","downmix")
SystemInfo["HDMIAudioSource"] = fileCheck("/proc/stb/hdmi/audio_source")
SystemInfo["SmallFlash"] = fileExists("/etc/smallflash")
SystemInfo["CIHelper"] = fileExists("/usr/bin/cihelper")
SystemInfo["HaveCISSL"] = fileCheck("/etc/ssl/certs/customer.pem") and fileCheck("/etc/ssl/certs/device.pem")
SystemInfo["CanChangeOsdAlpha"] = access("/proc/stb/video/alpha", R_OK) and True or False
SystemInfo["ScalerSharpness"] = fileExists("/proc/stb/vmpeg/0/pep_scaler_sharpness")
SystemInfo["OScamInstalled"] = fileExists("/usr/bin/oscam") or fileExists("/usr/bin/oscam-emu") or fileExists("/usr/bin/oscam-smod")
SystemInfo["OScamIsActive"] = SystemInfo["OScamInstalled"] and fileExists("/tmp/.oscam/oscam.version")
SystemInfo["NCamInstalled"] = fileExists("/usr/bin/ncam")
SystemInfo["NCamIsActive"] = SystemInfo["NCamInstalled"] and fileExists("/tmp/.ncam/ncam.version")
SystemInfo["OpenVisionModule"] = fileCheck("/proc/stb/info/openvision")
SystemInfo["OLDE2API"] = getBoxType() in ("dm800","su980")
SystemInfo["RecoveryMode"] = fileCheck("/proc/stb/fp/boot_mode") and getBoxType() not in ("hd51","h7")
SystemInfo["AndroidMode"] = getBoxType() == "su980" or SystemInfo["RecoveryMode"] and getBoxType() == "multibox"
SystemInfo["grautec"] = fileExists("/tmp/usbtft")
SystemInfo["CanAC3plusTranscode"] = fileExists("/proc/stb/audio/ac3plus_choices")
SystemInfo["CanDTSHD"] = fileExists("/proc/stb/audio/dtshd_choices")
SystemInfo["CanWMAPRO"] = fileExists("/proc/stb/audio/wmapro")
SystemInfo["CanDownmixAACPlus"] = fileExists("/proc/stb/audio/aacplus_choices")
SystemInfo["CanAACTranscode"] = fileExists("/proc/stb/audio/aac_transcode_choices")
SystemInfo["GraphicLCD"] = getBoxType() in ("vuultimo","xpeedlx3","et10000","hd2400","sezammarvel","atemionemesis","mbultra","beyonwizt4","osmio4kplus")
SystemInfo["LCDMiniTV"] = fileExists("/proc/stb/lcd/mode")
SystemInfo["DefaultDisplayBrightness"] = getBoxType() in ("dm900","dm920") and 8 or 5
SystemInfo["ConfigDisplay"] = SystemInfo["FrontpanelDisplay"] and getBoxType() not in ("atemio6000","atemio6100","bwidowx2","mbhybrid","opticumtt","osmini","spycatmini","spycatminiplus","bwidowx","xpeedlx1","odinplus","xp1000","h3","h5","h6","sh1","9910lx","9911lx","9920lx","e4hdcombo","odin2hybrid","bre2ze","h4","h7","lc","vipercombohdd","evominiplus","enfinity","marvel1","vipercombo","formuler3","formuler4","hd1100","hd1200","hd1265","hd1500","hd500c","hd530c","vs1000","classm","axodin","axodinc","starsatlx","genius","evo","galaxym6","9900lx","tiviarmin","t2cable","xcombo","enibox","mago","x1plus","sf108","anadol4k","anadol4kcombo","anadol4kv2","axashis4kcombo","axashis4kcomboplus","dinobot4k","dinobot4kl","dinobot4kmini","dinobot4kplus","dinobot4kpro","dinobot4kse","dinobotu55","ferguson4k","mediabox4k","sf128","sf138","bre2zet2c","formuler4turbo","osninopro","osnino","osninoplus","osmio4k","hd60","hd61","h9combo","et1x000","bcm7358","vp7358ci","gbtrio4k","ustym4kpro","cc1","sf8008","beyonwizv2")
SystemInfo["PiconLCDSupport"] = getBoxType() in ("vuultimo","sezammarvel","xpeedlx3","atemionemesis","mbultra","beyonwizt4","hd2400","vuduo2")
SystemInfo["DreamBoxAudio"] = getBoxType() in ("dm900","dm920","dm7080","dm800")
SystemInfo["DreamBoxDTSAudio"] = getBoxType() in ("dm7080","dm820")
SystemInfo["GigaBlueAudio"] = getBoxType() in ("gbquad4k","gbue4k")
SystemInfo["GigaBlueQuad"] = getBoxType() in ("gbquad","gbquadplus")
SystemInfo["AmlogicFamily"] = getBoxBrand() in ("linkdroid","mecool","minix","wetek","hardkernel") or getBoxType() == "dreamone"
SystemInfo["VFDDelay"] = getBoxType() in ("sf4008","beyonwizu4")
SystemInfo["VFDRepeats"] = getBoxBrand() != "ixuss" and getBoxType() not in ("atemio6000","atemio6100","bwidowx2","mbhybrid","opticumtt","osmini","spycatmini","spycatminiplus","bwidowx","xpeedlx1","odinplus","xp1000","h3","h5","h6","sh1","9910lx","9911lx","9920lx","e4hdcombo","odin2hybrid","bre2ze","h4","h7","lc","vipercombohdd","evominiplus","enfinity","marvel1","vipercombo","formuler3","formuler4","hd1100","hd1200","hd1265","hd1500","hd500c","hd530c","vs1000","classm","axodin","axodinc","starsatlx","genius","evo","galaxym6","9900lx","tiviarmin","t2cable","xcombo","enibox","mago","x1plus","sf108","anadol4k","anadol4kcombo","anadol4kv2","axashis4kcombo","axashis4kcomboplus","dinobot4k","dinobot4kl","dinobot4kmini","dinobot4kplus","dinobot4kpro","dinobot4kse","dinobotu55","ferguson4k","mediabox4k","sf128","sf138","bre2zet2c","formuler4turbo","osninopro","osnino","osninoplus","osmio4k","hd60","hd61","h9combo","et1x000","bcm7358","vp7358ci","gbtrio4k","ustym4kpro","cc1","sf8008","beyonwizv2")
SystemInfo["HiSilicon"] = getBoxType() in ("gbtrio4k","sf8008","cc1","ustym4kpro","beyonwizv2","viper4k")
SystemInfo["FirstCheckModel"] = getBoxType() in ("tmtwin4k","mbmicrov2","revo4k","force3uhd","mbmicro","e4hd","e4hdhybrid","valalinux","lunix","tmnanom3","purehd","force2nano","purehdse") or getBoxBrand() in ("linkdroid","wetek")
SystemInfo["SecondCheckModel"] = getBoxType() in ("osninopro","osnino","osninoplus","dm7020hd","dm7020hdv2","9910lx","9911lx","9920lx","tmnanose","tmnanoseplus","tmnanosem2","tmnanosem2plus","tmnanosecombo","force2plus","force2","force2se","optimussos","fusionhd","fusionhdse","force2plushv") or getBoxBrand() == "ixuss"
SystemInfo["DifferentLCDSettings"] = getBoxType() in ("spycat4kmini","osmega")
SystemInfo["CanBTAudio"] = fileCheck("/proc/stb/audio/btaudio")
SystemInfo["CanBTAudioDelay"] = fileCheck("/proc/stb/audio/btaudio_delay")
SystemInfo["ArchIsARM64"] = getBoxBrand() in ("linkdroid","mecool") or getBoxType() in ("wetekplay2","wetekhub","osmio4k","osmio4kplus","dreamone")
SystemInfo["ArchIsARM"] = SystemInfo["HiSilicon"] or getBoxBrand() in ("dinobot","rpi","maxytec","octagon") or getBoxType() in ("cube","su980","wetekplay","x8hp","odroidc2","beyonwizu4","bre2ze4k","hd51","hd60","hd61","h7","h9","h9combo","h10","i55plus","e4hdultra","protek4k","vs1500","et1x000","et13000","vusolo4k","vuuno4k","vuuno4kse","vuzero4k","vuultimo4k","vuduo4k","revo4k","tmtwin4k","galaxy4k","tm4ksuper","lunix3-4k","force4","lunix4k") or getBoxType().startswith("spycat4") or getBoxType().startswith("dm9") or getBoxType().startswith("force3u") or SystemInfo["GigaBlueAudio"]
SystemInfo["SeekStatePlay"] = False
SystemInfo["StatePlayPause"] = False
SystemInfo["StandbyState"] = False
