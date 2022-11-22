# -*- coding: utf-8 -*-
from os.path import isfile
from enigma import getOEMInfo
from Components.SystemInfo import BoxInfo
from Tools.Directories import fileReadLine
from Tools.StbHardware import getFPVersion, getBoxProc, getBoxProcType

MODULE_NAME = __name__.split(".")[-1]

model = BoxInfo.getItem("model")
brand = BoxInfo.getItem("brand")
platform = BoxInfo.getItem("platform")
displaymodel = BoxInfo.getItem("displaymodel")
displaybrand = BoxInfo.getItem("displaybrand")
procType = getBoxProcType()
procModel = getBoxProc()
fpVersion = getFPVersion()

if getOEMInfo() == "available":
	if procModel == "dm525":
		model = procModel
		displaymodel = procModel
	elif model == "et7x00":
		if getChipSetString() == "bcm73625":
			displaymodel = "ET7100 V2"
		else:
			displaymodel = "ET7000"
	elif model == "sf8008":
		if procType == "10":
			model = "sf8008s"
			displaymodel = "SF8008 4K Single"
		elif procType == "11":
			model = "sf8008t"
			displaymodel = "SF8008 4K Twin"
	elif model == "sfx6008" and procType == "10":
		model = "sfx6018"
		displaymodel = "SFX6018 S2"
	elif platform == "7100s" and procModel == "7200s":
		platform == "7200s"
	elif model == "ustym4kpro":
		if procType == "10":
			model = "ustym4kprosingle"
			displaymodel = "Ustym 4K PRO Single"
		elif procType == "11":
			model = "ustym4kprotwin"
			displaymodel = "Ustym 4K PRO Twin"
	elif model == "ventonhdx":
		if procModel == "ini-3000":
			model = "uniboxhd1"
			displaymodel = "HD-1"
		elif procModel == "ini-5000":
			model = "uniboxhd2"
			displaymodel = "HD-2"
		elif procModel in ("ini-7000", "ini-7012"):
			model = "uniboxhd3"
			displaymodel = "HD-3"
	elif model == "xpeedlx":
		if procModel == "ini-1000lx":
			model = "xpeedlx2t"
			displaymodel = "LX-2T"
		elif procModel == "ini-1000de":
			if fpVersion == "2":
				model = "xpeedlx2"
			else:
				model = "xpeedlx1"

if isfile("/proc/stb/info/azmodel"):
		model = fileReadLine("/proc/stb/info/model", "unknown", source=MODULE_NAME)


def getOEMShowModel():
	return model


def getOEMShowBrand():
	return brand


def getOEMShowDisplayModel():
	return displaymodel


def getOEMShowDisplayBrand():
	return displaybrand


def getOEMShowPlatform():
	return platform
