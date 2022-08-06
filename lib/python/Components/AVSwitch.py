# -*- coding: utf-8 -*-
from Components.config import config, ConfigSlider, ConfigSelection, ConfigYesNo, ConfigEnableDisable, ConfigOnOff, ConfigSubsection, ConfigBoolean, ConfigSelectionNumber, ConfigNothing, NoSave
from enigma import eAVSwitch, eDVBVolumecontrol, getDesktop
from Components.SystemInfo import BoxInfo
import os

model = BoxInfo.getItem("model")
platform = BoxInfo.getItem("platform")


class AVSwitch:
	def setInput(self, input):
		INPUT = {"ENCODER": 0, "SCART": 1, "AUX": 2}
		eAVSwitch.getInstance().setInput(INPUT[input])

	def setColorFormat(self, value):
		eAVSwitch.getInstance().setColorFormat(value)

	def setAspectRatio(self, value):
		eAVSwitch.getInstance().setAspectRatio(value)

	def setSystem(self, value):
		eAVSwitch.getInstance().setVideomode(value)

	def getOutputAspect(self):
		valstr = config.av.aspectratio.value
		if valstr in ("4_3_letterbox", "4_3_panscan"): # 4:3
			return (4, 3)
		elif valstr == "16_9": # auto ... 4:3 or 16:9
			try:
				print("[AVSwitch] Read /proc/stb/vmpeg/0/aspect")
				if "1" in open("/proc/stb/vmpeg/0/aspect", "r").read(): # 4:3
					return (4, 3)
			except IOError:
				print("[AVSwitch] Read /proc/stb/vmpeg/0/aspect failed.")
		elif valstr in ("16_9_always", "16_9_letterbox"): # 16:9
			pass
		elif valstr in ("16_10_letterbox", "16_10_panscan"): # 16:10
			return (16, 10)
		return (16, 9)

	def getFramebufferScale(self):
		aspect = self.getOutputAspect()
		fb_size = getDesktop(0).size()
		return (aspect[0] * fb_size.height(), aspect[1] * fb_size.width())

	def getAspectRatioSetting(self):
		valstr = config.av.aspectratio.value
		if valstr == "4_3_letterbox":
			val = 0
		elif valstr == "4_3_panscan":
			val = 1
		elif valstr == "16_9":
			val = 2
		elif valstr == "16_9_always":
			val = 3
		elif valstr == "16_10_letterbox":
			val = 4
		elif valstr == "16_10_panscan":
			val = 5
		elif valstr == "16_9_letterbox":
			val = 6
		return val

	def setAspectWSS(self, aspect=None):
		if not config.av.wss.value:
			value = 2 # auto(4:3_off)
		else:
			value = 1 # auto
		eAVSwitch.getInstance().setWSS(value)


def InitAVSwitch():
	config.av = ConfigSubsection()
	if model == "vuduo" or BoxInfo.getItem("brand") == "ixuss":
		config.av.yuvenabled = ConfigBoolean(default=False)
	else:
		config.av.yuvenabled = ConfigBoolean(default=True)
	colorformat_choices = {"cvbs": _("CVBS")}

	# when YUV, Scart or S-Video is not support by HW, don't let the user select it
	if BoxInfo.getItem("yuv"):
		colorformat_choices["yuv"] = _("YPbPr")
	if BoxInfo.getItem("scart"):
		colorformat_choices["rgb"] = _("RGB")
	if BoxInfo.getItem("svideo"):
		colorformat_choices["svideo"] = _("S-Video")

	config.av.colorformat = ConfigSelection(choices=colorformat_choices, default="cvbs")
	config.av.aspectratio = ConfigSelection(choices={
			"4_3_letterbox": _("4:3 Letterbox"),
			"4_3_panscan": _("4:3 PanScan"),
			"16_9": _("16:9"),
			"16_9_always": _("16:9 always"),
			"16_10_letterbox": _("16:10 Letterbox"),
			"16_10_panscan": _("16:10 PanScan"),
			"16_9_letterbox": _("16:9 Letterbox")},
			default="16_9")
	config.av.aspect = ConfigSelection(choices={
			"4_3": _("4:3"),
			"16_9": _("16:9"),
			"16_10": _("16:10"),
			"auto": _("Automatic")},
			default="auto")
	policy2_choices = {
	# TRANSLATORS: (aspect ratio policy: black bars on top/bottom) in doubt, keep english term.
	"letterbox": _("Letterbox"),
	# TRANSLATORS: (aspect ratio policy: cropped content on left/right) in doubt, keep english term
	"panscan": _("Pan&scan"),
	# TRANSLATORS: (aspect ratio policy: scale as close to fullscreen as possible)
	"scale": _("Just scale")}
	try:
		print("[AVSwitch] Read /proc/stb/video/policy2_choices")
		if "full" in open("/proc/stb/video/policy2_choices").read():
			# TRANSLATORS: (aspect ratio policy: display as fullscreen, even if the content aspect ratio does not match the screen ratio)
			policy2_choices.update({"full": _("Full screen")})
	except:
		print("[AVSwitch] Read /proc/stb/video/policy2_choices failed.")
	try:
		print("[AVSwitch] Read /proc/stb/video/policy2_choices")
		if "auto" in open("/proc/stb/video/policy2_choices").read():
			# TRANSLATORS: (aspect ratio policy: automatically select the best aspect ratio mode)
			policy2_choices.update({"auto": _("Auto")})
	except:
		print("[AVSwitch] Read /proc/stb/video/policy2_choices failed.")
	config.av.policy_169 = ConfigSelection(choices=policy2_choices, default="scale")
	policy_choices = {
	# TRANSLATORS: (aspect ratio policy: black bars on left/right) in doubt, keep english term.
	"pillarbox": _("Pillarbox"),
	# TRANSLATORS: (aspect ratio policy: cropped content on left/right) in doubt, keep english term
	"panscan": _("Pan&scan"),
	# TRANSLATORS: (aspect ratio policy: scale as close to fullscreen as possible)
	"scale": _("Just scale")}
	try:
		print("[AVSwitch] Read /proc/stb/video/policy_choices")
		if "nonlinear" in open("/proc/stb/video/policy_choices").read():
			# TRANSLATORS: (aspect ratio policy: display as fullscreen, with stretching the left/right)
			policy_choices.update({"nonlinear": _("Nonlinear")})
	except:
		print("[AVSwitch] Read /proc/stb/video/policy_choices failed.")
	try:
		print("[AVSwitch] Read /proc/stb/video/policy_choices")
		if "full" in open("/proc/stb/video/policy_choices").read():
			# TRANSLATORS: (aspect ratio policy: display as fullscreen, even if the content aspect ratio does not match the screen ratio)
			policy_choices.update({"full": _("Full screen")})
	except:
		print("[AVSwitch] Read /proc/stb/video/policy_choices failed.")
	try:
		print("[AVSwitch] Read /proc/stb/video/policy_choices")
		if "auto" in open("/proc/stb/video/policy_choices").read():
			# TRANSLATORS: (aspect ratio policy: automatically select the best aspect ratio mode)
			policy_choices.update({"auto": _("Auto")})
	except:
		print("[AVSwitch] Read /proc/stb/video/policy_choices failed.")
	config.av.policy_43 = ConfigSelection(choices=policy_choices, default="scale")
	config.av.tvsystem = ConfigSelection(choices={"pal": _("PAL"), "ntsc": _("NTSC"), "multinorm": _("multinorm")}, default="pal")
	config.av.wss = ConfigEnableDisable(default=True)
	config.av.generalAC3delay = ConfigSelectionNumber(-1000, 1000, 5, default=0)
	config.av.generalPCMdelay = ConfigSelectionNumber(-1000, 1000, 5, default=0)
	config.av.vcrswitch = ConfigEnableDisable(default=False)

	iAVSwitch = AVSwitch()

	def setColorFormat(configElement):
		if model == "et6x00":
			map = {"cvbs": 3, "rgb": 3, "svideo": 2, "yuv": 3}
		elif platform == "gb7356" or model.startswith('et'):
			map = {"cvbs": 0, "rgb": 3, "svideo": 2, "yuv": 3}
		else:
			map = {"cvbs": 0, "rgb": 1, "svideo": 2, "yuv": 3}
		iAVSwitch.setColorFormat(map[configElement.value])

	def setAspectRatio(configElement):
		map = {"4_3_letterbox": 0, "4_3_panscan": 1, "16_9": 2, "16_9_always": 3, "16_10_letterbox": 4, "16_10_panscan": 5, "16_9_letterbox": 6}
		iAVSwitch.setAspectRatio(map[configElement.value])

	def setSystem(configElement):
		map = {"pal": 0, "ntsc": 1, "multinorm": 2}
		iAVSwitch.setSystem(map[configElement.value])

	def setWSS(configElement):
		iAVSwitch.setAspectWSS()

	# this will call the "setup-val" initial
	config.av.colorformat.addNotifier(setColorFormat)
	config.av.aspectratio.addNotifier(setAspectRatio)
	config.av.tvsystem.addNotifier(setSystem)
	config.av.wss.addNotifier(setWSS)

	iAVSwitch.setInput("ENCODER") # init on startup
	if platform == "gb7356" or model in ("et5x00", "et6x00", "ixussone", "ixusszero", "axodin", "axase3", "optimussos1", "optimussos2", "gb800seplus", "gb800ueplus", "gbultrase", "gbultraue", "gbultraueh", "twinboxlcd"):
		detected = False
	else:
		detected = eAVSwitch.getInstance().haveScartSwitch()

	BoxInfo.setItem("ScartSwitch", detected)

	if BoxInfo.getItem("CanDownmixAC3"):
		def setAC3Downmix(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/ac3")
			if BoxInfo.getItem("DreamBoxAudio"):
				open("/proc/stb/audio/ac3", "w").write(configElement.value)
			else:
				open("/proc/stb/audio/ac3", "w").write(configElement.value and "downmix" or "passthrough")
		if BoxInfo.getItem("DreamBoxAudio"):
			choice_list = [("downmix", _("Downmix")), ("passthrough", _("Passthrough")), ("multichannel", _("convert to multi-channel PCM")), ("hdmi_best", _("use best / controlled by HDMI"))]
			config.av.downmix_ac3 = ConfigSelection(choices=choice_list, default="downmix")
		else:
			config.av.downmix_ac3 = ConfigYesNo(default=True)
		config.av.downmix_ac3.addNotifier(setAC3Downmix)

	if BoxInfo.getItem("CanAC3plusTranscode"):
		def setAC3plusTranscode(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/ac3plus")
			open("/proc/stb/audio/ac3plus", "w").write(configElement.value)
		if BoxInfo.getItem("DreamBoxAudio"):
			choice_list = [("use_hdmi_caps", _("controlled by HDMI")), ("force_ac3", _("convert to AC3")), ("multichannel", _("convert to multi-channel PCM")), ("hdmi_best", _("use best / controlled by HDMI")), ("force_ddp", _("force AC3plus"))]
			config.av.transcodeac3plus = ConfigSelection(choices=choice_list, default="force_ac3")
		elif platform in ("gb7252", "gb72604"):
			choice_list = [("downmix", _("Downmix")), ("passthrough", _("Passthrough")), ("force_ac3", _("convert to AC3")), ("multichannel", _("convert to multi-channel PCM")), ("force_dts", _("convert to DTS"))]
			config.av.transcodeac3plus = ConfigSelection(choices=choice_list, default="force_ac3")
		else:
			choice_list = [("use_hdmi_caps", _("controlled by HDMI")), ("force_ac3", _("convert to AC3"))]
			config.av.transcodeac3plus = ConfigSelection(choices=choice_list, default="force_ac3")
		config.av.transcodeac3plus.addNotifier(setAC3plusTranscode)

	if BoxInfo.getItem("CanDownmixDTS"):
		def setDTSDownmix(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/dts")
			open("/proc/stb/audio/dts", "w").write(configElement.value and "downmix" or "passthrough")
		config.av.downmix_dts = ConfigYesNo(default=True)
		config.av.downmix_dts.addNotifier(setDTSDownmix)

	if BoxInfo.getItem("CanDTSHD"):
		def setDTSHD(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/dtshd")
			open("/proc/stb/audio/dtshd", "w").write(configElement.value)
		if model in ("dm7080", "dm820"):
			choice_list = [("use_hdmi_caps", _("controlled by HDMI")), ("force_dts", _("convert to DTS"))]
			config.av.dtshd = ConfigSelection(choices=choice_list, default="use_hdmi_caps")
		else:
			choice_list = [("downmix", _("Downmix")), ("force_dts", _("convert to DTS")), ("use_hdmi_caps", _("controlled by HDMI")), ("multichannel", _("convert to multi-channel PCM")), ("hdmi_best", _("use best / controlled by HDMI"))]
			config.av.dtshd = ConfigSelection(choices=choice_list, default="downmix")
		config.av.dtshd.addNotifier(setDTSHD)

	if BoxInfo.getItem("CanWMAPRO"):
		def setWMAPRO(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/wmapro")
			open("/proc/stb/audio/wmapro", "w").write(configElement.value)
		choice_list = [("downmix", _("Downmix")), ("passthrough", _("Passthrough")), ("multichannel", _("convert to multi-channel PCM")), ("hdmi_best", _("use best / controlled by HDMI"))]
		config.av.wmapro = ConfigSelection(choices=choice_list, default="downmix")
		config.av.wmapro.addNotifier(setWMAPRO)

	if BoxInfo.getItem("CanDownmixAAC"):
		def setAACDownmix(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/aac")
			if BoxInfo.getItem("DreamBoxAudio") or platform in ("gb7252", "gb72604"):
				open("/proc/stb/audio/aac", "w").write(configElement.value)
			else:
				open("/proc/stb/audio/aac", "w").write(configElement.value and "downmix" or "passthrough")
		if BoxInfo.getItem("DreamBoxAudio"):
			choice_list = [("downmix", _("Downmix")), ("passthrough", _("Passthrough")), ("multichannel", _("convert to multi-channel PCM")), ("hdmi_best", _("use best / controlled by HDMI"))]
			config.av.downmix_aac = ConfigSelection(choices=choice_list, default="downmix")
		elif platform in ("gb7252", "gb72604"):
			choice_list = [("downmix", _("Downmix")), ("passthrough", _("Passthrough")), ("multichannel", _("convert to multi-channel PCM")), ("force_ac3", _("convert to AC3")), ("force_dts", _("convert to DTS")), ("use_hdmi_cacenter", _("use_hdmi_cacenter")), ("wide", _("wide")), ("extrawide", _("extrawide"))]
			config.av.downmix_aac = ConfigSelection(choices=choice_list, default="downmix")
		else:
			config.av.downmix_aac = ConfigYesNo(default=True)
		config.av.downmix_aac.addNotifier(setAACDownmix)

	if BoxInfo.getItem("CanDownmixAACPlus"):
		def setAACDownmixPlus(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/aacplus")
			open("/proc/stb/audio/aacplus", "w").write(configElement.value)
		choice_list = [("downmix", _("Downmix")), ("passthrough", _("Passthrough")), ("multichannel", _("convert to multi-channel PCM")), ("force_ac3", _("convert to AC3")), ("force_dts", _("convert to DTS")), ("use_hdmi_cacenter", _("use_hdmi_cacenter")), ("wide", _("wide")), ("extrawide", _("extrawide"))]
		config.av.downmix_aacplus = ConfigSelection(choices=choice_list, default="downmix")
		config.av.downmix_aacplus.addNotifier(setAACDownmixPlus)

	if BoxInfo.getItem("CanAACTranscode"):
		def setAACTranscode(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/aac_transcode")
			open("/proc/stb/audio/aac_transcode", "w").write(configElement.value)
		choice_list = [("off", _("off")), ("ac3", _("AC3")), ("dts", _("DTS"))]
		config.av.transcodeaac = ConfigSelection(choices=choice_list, default="off")
		config.av.transcodeaac.addNotifier(setAACTranscode)
	else:
		config.av.transcodeaac = ConfigNothing()

	if BoxInfo.getItem("CanBTAudio"):
		def setBTAudio(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/btaudio")
			open("/proc/stb/audio/btaudio", "w").write("on" if configElement.value else "off")
		config.av.btaudio = ConfigOnOff(default=False)
		config.av.btaudio.addNotifier(setBTAudio)
	else:
		config.av.btaudio = ConfigNothing()

	if BoxInfo.getItem("CanBTAudioDelay"):
		def setBTAudioDelay(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/btaudio_delay")
			open("/proc/stb/audio/btaudio_delay", "w").write(format(configElement.value * 90))
		config.av.btaudiodelay = ConfigSelectionNumber(-1000, 1000, 5, default=0)
		config.av.btaudiodelay.addNotifier(setBTAudioDelay)
	else:
		config.av.btaudiodelay = ConfigNothing()

	if BoxInfo.getItem("CanChangeOsdAlpha"):
		def setAlpha(config):
			print("[AVSwitch] Write to /proc/stb/video/alpha")
			open("/proc/stb/video/alpha", "w").write(str(config.value))
		config.av.osd_alpha = ConfigSlider(default=255, limits=(0, 255))
		config.av.osd_alpha.addNotifier(setAlpha)

	if BoxInfo.getItem("ScalerSharpness"):
		def setScaler_sharpness(config):
			myval = int(config.value)
			try:
				print("--> setting scaler_sharpness to: %0.8X" % myval)
				print("[AVSwitch] Write to /proc/stb/vmpeg/0/pep_scaler_sharpness")
				open("/proc/stb/vmpeg/0/pep_scaler_sharpness", "w").write("%0.8X" % myval)
				print("[AVSwitch] Write to /proc/stb/vmpeg/0/pep_apply")
				open("/proc/stb/vmpeg/0/pep_apply", "w").write("1")
			except IOError:
				print("[AVSwitch] couldn't write pep_scaler_sharpness")

		if platform == "gb7356":
			config.av.scaler_sharpness = ConfigSlider(default=5, limits=(0, 26))
		else:
			config.av.scaler_sharpness = ConfigSlider(default=13, limits=(0, 26))
		config.av.scaler_sharpness.addNotifier(setScaler_sharpness)
	else:
		config.av.scaler_sharpness = NoSave(ConfigNothing())

	if BoxInfo.getItem("HasMultichannelPCM"):
		def setMultichannelPCM(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/multichannel_pcm")
			open(BoxInfo.getItem("HasMultichannelPCM"), "w").write(configElement.value and "enable" or "disable")
		config.av.multichannel_pcm = ConfigYesNo(default=False)
		config.av.multichannel_pcm.addNotifier(setMultichannelPCM)

	if BoxInfo.getItem("HasAutoVolume"):
		def setAutoVolume(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/avl")
			open("/proc/stb/audio/avl", "w").write(configElement.value)
		config.av.autovolume = ConfigSelection(default="none", choices=[("none", _("off")), ("hdmi", _("HDMI")), ("spdif", _("SPDIF")), ("dac", _("DAC"))])
		config.av.autovolume.addNotifier(setAutoVolume)

	if BoxInfo.getItem("HasAutoVolumeLevel"):
		def setAutoVolumeLevel(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/autovolumelevel")
			open("/proc/stb/audio/autovolumelevel", "w").write(configElement.value and "enabled" or "disabled")
		config.av.autovolumelevel = ConfigYesNo(default=False)
		config.av.autovolumelevel.addNotifier(setAutoVolumeLevel)

	if BoxInfo.getItem("Has3DSurround"):
		def set3DSurround(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/3d_surround")
			open("/proc/stb/audio/3d_surround", "w").write(configElement.value)
		config.av.surround_3d = ConfigSelection(default="none", choices=[("none", _("off")), ("hdmi", _("HDMI")), ("spdif", _("SPDIF")), ("dac", _("DAC"))])
		config.av.surround_3d.addNotifier(set3DSurround)

	if BoxInfo.getItem("Has3DSpeaker"):
		def set3DSpeaker(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/3d_surround_speaker_position")
			open("/proc/stb/audio/3d_surround_speaker_position", "w").write(configElement.value)
		config.av.speaker_3d = ConfigSelection(default="center", choices=[("center", _("center")), ("wide", _("wide")), ("extrawide", _("extra wide"))])
		config.av.speaker_3d.addNotifier(set3DSpeaker)

	if BoxInfo.getItem("Has3DSurroundSpeaker"):
		def set3DSurroundSpeaker(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/3dsurround")
			open("/proc/stb/audio/3dsurround", "w").write(configElement.value)
		config.av.surround_3d_speaker = ConfigSelection(default="disabled", choices=[("disabled", _("off")), ("center", _("center")), ("wide", _("wide")), ("extrawide", _("extra wide"))])
		config.av.surround_3d_speaker.addNotifier(set3DSurroundSpeaker)

	if BoxInfo.getItem("Has3DSurroundSoftLimiter"):
		def set3DSurroundSoftLimiter(configElement):
			print("[AVSwitch] Write to /proc/stb/audio/3dsurround_softlimiter")
			open("/proc/stb/audio/3dsurround_softlimiter", "w").write(configElement.value and "enabled" or "disabled")
		config.av.surround_softlimiter_3d = ConfigYesNo(default=False)
		config.av.surround_softlimiter_3d.addNotifier(set3DSurroundSoftLimiter)

	if BoxInfo.getItem("HDMIAudioSource"):
		def setHDMIAudioSource(configElement):
			print("[AVSwitch] Write to /proc/stb/hdmi/audio_source")
			open(BoxInfo.getItem("HDMIAudioSource"), "w").write(configElement.value)
		config.av.hdmi_audio_source = ConfigSelection(default="pcm", choices=[("pcm", _("PCM")), ("spdif", _("SPDIF"))])
		config.av.hdmi_audio_source.addNotifier(setHDMIAudioSource)

	def setVolumeStepsize(configElement):
		eDVBVolumecontrol.getInstance().setVolumeSteps(int(configElement.value))
	config.av.volume_stepsize = ConfigSelectionNumber(1, 10, 1, default=5)
	config.av.volume_stepsize.addNotifier(setVolumeStepsize)
