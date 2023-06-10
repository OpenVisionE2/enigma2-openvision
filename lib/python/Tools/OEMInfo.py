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

if getOEMInfo() == "available":
	if procModel == "dm525":
		model = procModel
		displaymodel = procModel
	elif model == "et4x00":
		displaymodel = "ET4000"
	elif model == "et5x00":
		displaymodel = "ET5000"
	elif model == "et6x00":
		if procModel == "et6000":
			displaymodel = "ET6000"
		elif procModel == "et6500":
			displaymodel = "ET6500"
	elif model == "et7x00":
		if procModel == "et7000":
			if getChipSetString() == "bcm73625":
				displaymodel = "ET7100 V2"
			else:
				displaymodel = "ET7000"
		elif procModel == "et7500":
			displaymodel = "ET7500"
	elif model == "et9x00":
		if procModel == "et9000":
			displaymodel = "ET9000"
		elif procModel == "et9100":
			displaymodel = "ET9100"
		elif procModel == "et9200":
			displaymodel = "ET9200"
		elif procModel == "et9500":
			displaymodel = "ET9500"
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
	elif model == "sx88v2" and procType == "00" or procType == "unknown":
		model = "sx888"
		displaymodel = "SX888V2 4K DUAL OS"
	elif platform == "7100s" and procModel == "7200s":
		platform == "7200s"
	elif model == "ustym4kpro":
		if procType == "10":
			model = "ustym4kprosingle"
			displaymodel = "Ustym 4K PRO Single"
		elif procType == "11":
			model = "ustym4kprotwin"
			displaymodel = "Ustym 4K PRO Twin"
		elif procType == "12":
			model = "ustym4kprocombo"
			displaymodel = "Ustym 4K PRO Combo"
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
			if getFPVersion() == "2":
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
