#!/usr/bin/python
import struct
import time
import sys

from keyids import KEYIDNAMES

"""
You need to stop enigma2 then run this file!
"""

path = "/dev/input/event%s" % (sys.argv[1] if len(sys.argv) > 1 else "0")

"""
FORMAT represents the format used by linux kernel input event struct
See https://github.com/torvalds/linux/blob/v5.5-rc5/include/uapi/linux/input.h#L28
Stands for: long int, long int, unsigned short, unsigned short, unsigned int
"""
FORMAT = 'llHHI'
EVENT_SIZE = struct.calcsize(FORMAT)
print("Starting the IR code scanner on %s." % path)
with open(path, "rb") as fd:  # Open file in binary mode.
	event = fd.read(EVENT_SIZE)
	while event:
		sec, usec, type, code, value = struct.unpack(FORMAT, event)
		if type != 0 or code != 0 or value != 0:
			print("Code: %3u, Name: %-20s Type: %1u, Value: %1u  -  %s.%d" % (code, KEYIDNAMES[code], type, value, time.strftime("%a %d-%b-%Y %H:%M:%S", time.localtime(sec)), usec))
		else:  # Events with code, type and value == 0 are "separator" events.
			print("-------------------------------------------------------")
		if code == 116 and type == 1 and value == 0:
			print("POWER button pressed, exiting.")
			break
		event = fd.read(EVENT_SIZE)
exit(0)
