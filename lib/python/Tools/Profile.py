# -*- coding: utf-8 -*-
from os.path import join, isfile
from time import time

from Tools.Directories import SCOPE_CONFIG, SCOPE_LIBDIR, fileReadLines, fileWriteLine, resolveFilename

MODULE_NAME = __name__.split(".")[-1]

PERCENTAGE_START = 0
PERCENTAGE_END = 100

profileData = {}
profileStart = time()
totalTime = 1
timeStamp = None
profileFile = resolveFilename(SCOPE_CONFIG, "profile")
profileFd = None
# model = BoxInfo.get("model")  # For when we can use BoxInfo.
model = None

# Workaround to get the model name.  When SystemInfo can be loaded earlier in
# the boot process we can use BoxInfo directly rather than using this code.
#
lines = []
lines = fileReadLines(join(resolveFilename(SCOPE_LIBDIR), "enigma.info"), lines, source=MODULE_NAME)
for line in lines:
	if line.startswith("#") or line.strip() == "":
		continue
	if "=" in line:
		item, value = [x.strip() for x in line.split("=", 1)]
		if item == "model":
			model = value
			break

profileOld = fileReadLines(profileFile, source=MODULE_NAME)
if profileOld:
	for line in profileOld:
		if "\t" in line:
			(timeStamp, checkPoint) = line.strip().split("\t")
			timeStamp = float(timeStamp)
			totalTime = timeStamp
			profileData[checkPoint] = timeStamp
else:
	print("[Profile] Error: No profile data available!")

try:
	profileFd = open(profileFile, "w")
except (IOError, OSError) as err:
	print("[Profile] Error %d: Couldn't open profile file '%s'!  (%s)" % (err.errno, profileFile, err.strerror))


def profile(checkPoint):
	now = time() - profileStart
	if profileFd:
		profileFd.write("%7.3f\t%s\n" % (now, checkPoint))
		if checkPoint in profileData:
			timeStamp = profileData[checkPoint]
			if totalTime:
				percentage = timeStamp * (PERCENTAGE_END - PERCENTAGE_START) // totalTime + PERCENTAGE_START
			else:
				percentage = PERCENTAGE_START
			if model == "axodin":
				fileWriteLine("/dev/dbox/oled0", "%d" % percentage, source=MODULE_NAME)
			elif model == "beyonwizu4":
				fileWriteLine("/dev/dbox/oled0", "Loading %d%%\n" % percentage, source=MODULE_NAME)
			elif model in ("gb800solo", "gb800se", "gb800seplus", "gbultrase"):
				fileWriteLine("/dev/mcu", "%d  \n" % percentage, source=MODULE_NAME)
			elif model in ("sezammarvel", "xpeedlx3", "atemionemesis"):
				fileWriteLine("/proc/vfd", "Loading %d%% " % percentage, source=MODULE_NAME)
			elif model in ("ebox5000", "osmini", "spycatmini", "osminiplus", "spycatminiplus"):
				fileWriteLine("/proc/progress", "%d" % percentage, source=MODULE_NAME)
			elif isfile("/proc/progress"):
				fileWriteLine("/proc/progress", "%d \n" % percentage, source=MODULE_NAME)


def profileFinal():
	global profileFd
	if profileFd is not None:
		profileFd.close()
		profileFd = None
