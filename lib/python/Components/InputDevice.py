#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
from Components.config import config, ConfigSlider, ConfigSubsection, ConfigYesNo, ConfigText, ConfigInteger
from enigma import getBoxType
from Components.SystemInfo import SystemInfo
import errno
import xml.etree.cElementTree
from enigma import eRCInput
from keyids import KEYIDS
from Components.RcModel import rc_model
from fcntl import ioctl
import os
import struct
import platform
from Tools.Directories import pathExists
from boxbranding import getRCType

model = getBoxType()

# include/uapi/asm-generic/ioctl.h
# asm-generic/ioctl.h for HAVE_OLDE2_API
IOC_NRBITS = 8L
IOC_TYPEBITS = 8L

if SystemInfo["OLDE2API"]:
	IOC_SIZEBITS = 13L
	IOC_DIRBITS = 3L
else:
	IOC_SIZEBITS = 13L if "mips" in platform.machine() else 14L
	IOC_DIRBITS = 3L if "mips" in platform.machine() else 2L

IOC_NRSHIFT = 0L
IOC_TYPESHIFT = IOC_NRSHIFT+IOC_NRBITS
IOC_SIZESHIFT = IOC_TYPESHIFT+IOC_TYPEBITS
IOC_DIRSHIFT = IOC_SIZESHIFT+IOC_SIZEBITS

IOC_READ = 2L

def EVIOCGNAME(length):
	return (IOC_READ<<IOC_DIRSHIFT)|(length<<IOC_SIZESHIFT)|(0x45<<IOC_TYPESHIFT)|(0x06<<IOC_NRSHIFT)


class inputDevices:

	def __init__(self):
		self.Devices = {}
		self.currentDevice = ""
		self.getInputDevices()

	def getInputDevices(self):
		devices = sorted(os.listdir("/dev/input/"))

		for evdev in devices:
			try:
				buffer = "\0"*512
				self.fd = os.open("/dev/input/" + evdev, os.O_RDWR | os.O_NONBLOCK)
				self.name = ioctl(self.fd, EVIOCGNAME(256), buffer)
				self.name = self.name[:self.name.find("\0")]
				os.close(self.fd)
			except (IOError,OSError), err:
				print("[InputDevice] getInputDevices " + evdev + " <ERROR: ioctl(EVIOCGNAME): " + str(err) + " >")
				self.name = None

			if self.name:
				self.Devices[evdev] = {'name': self.name, 'type': self.getInputDeviceType(self.name),'enabled': False, 'configuredName': None }
				if model.startswith("et"):
					self.setDefaults(evdev)


	def getInputDeviceType(self,name):
		if "remote control" in str(name).lower():
			return "remote"
		elif "keyboard" in str(name).lower():
			return "keyboard"
		elif "mouse" in str(name).lower():
			return "mouse"
		else:
			print("[InputDevice] Unknown device type:",name)
			return None

	def getDeviceName(self, x):
		if x in self.Devices.keys():
			return self.Devices[x].get("name", x)
		else:
			return "Unknown device name"

	def getDeviceList(self):
		return sorted(self.Devices.iterkeys())

	def setDeviceAttribute(self, device, attribute, value):
		#print("[InputDevice] setting for device", device, "attribute", attribute, " to value", value)
		if device in self.Devices:
			self.Devices[device][attribute] = value

	def getDeviceAttribute(self, device, attribute):
		if device in self.Devices:
			if attribute in self.Devices[device]:
				return self.Devices[device][attribute]
		return None

	def setEnabled(self, device, value):
		oldval = self.getDeviceAttribute(device, 'enabled')
		#print("[InputDevice] setEnabled for device %s to %s from %s" % (device,value,oldval))
		self.setDeviceAttribute(device, 'enabled', value)
		if oldval is True and value is False:
			self.setDefaults(device)

	def setName(self, device, value):
		#print("[InputDevice] setName for device %s to %s" % (device,value))
		self.setDeviceAttribute(device, 'configuredName', value)

	#struct input_event {
	#	struct timeval time;    -> ignored
	#	__u16 type;             -> EV_REP (0x14)
	#	__u16 code;             -> REP_DELAY (0x00) or REP_PERIOD (0x01)
	#	__s32 value;            -> DEFAULTS: 700(REP_DELAY) or 100(REP_PERIOD)
	#}; -> size = 16

	def setDefaults(self, device):
		print("[InputDevice] setDefaults for device %s" % device)
		self.setDeviceAttribute(device, 'configuredName', None)
		event_repeat = struct.pack('LLHHi', 0, 0, 0x14, 0x01, 100)
		event_delay = struct.pack('LLHHi', 0, 0, 0x14, 0x00, 700)
		fd = os.open("/dev/input/" + device, os.O_RDWR)
		os.write(fd, event_repeat)
		os.write(fd, event_delay)
		os.close(fd)

	def setRepeat(self, device, value): #REP_PERIOD
		if self.getDeviceAttribute(device, 'enabled'):
			print("[InputDevice] setRepeat for device %s to %d ms" % (device,value))
			event = struct.pack('LLHHi', 0, 0, 0x14, 0x01, int(value))
			fd = os.open("/dev/input/" + device, os.O_RDWR)
			os.write(fd, event)
			os.close(fd)

	def setDelay(self, device, value): #REP_DELAY
		if self.getDeviceAttribute(device, 'enabled'):
			print("[InputDevice] setDelay for device %s to %d ms" % (device,value))
			event = struct.pack('LLHHi', 0, 0, 0x14, 0x00, int(value))
			fd = os.open("/dev/input/" + device, os.O_RDWR)
			os.write(fd, event)
			os.close(fd)


class InitInputDevices:

	def __init__(self):
		self.currentDevice = ""
		self.createConfig()

	def createConfig(self, *args):
		config.inputDevices = ConfigSubsection()
		for device in sorted(iInputDevices.Devices.iterkeys()):
			self.currentDevice = device
			#print("[InitInputDevices] creating config entry for device: %s -> %s  " % (self.currentDevice, iInputDevices.Devices[device]["name"]))
			self.setupConfigEntries(self.currentDevice)
			self.remapRemoteControl(self.currentDevice)
			self.currentDevice = ""

	def inputDevicesEnabledChanged(self,configElement):
		if self.currentDevice != "" and iInputDevices.currentDevice == "":
			iInputDevices.setEnabled(self.currentDevice, configElement.value)
		elif iInputDevices.currentDevice != "":
			iInputDevices.setEnabled(iInputDevices.currentDevice, configElement.value)

	def inputDevicesNameChanged(self,configElement):
		if self.currentDevice != "" and iInputDevices.currentDevice == "":
			iInputDevices.setName(self.currentDevice, configElement.value)
			if configElement.value != "":
				devname = iInputDevices.getDeviceAttribute(self.currentDevice, 'name')
				if devname != configElement.value:
					cmd = "config.inputDevices." + self.currentDevice + ".enabled.value = False"
					exec(cmd)
					cmd = "config.inputDevices." + self.currentDevice + ".enabled.save()"
					exec(cmd)
		elif iInputDevices.currentDevice != "":
			iInputDevices.setName(iInputDevices.currentDevice, configElement.value)

	def inputDevicesRepeatChanged(self,configElement):
		if self.currentDevice != "" and iInputDevices.currentDevice == "":
			iInputDevices.setRepeat(self.currentDevice, configElement.value)
		elif iInputDevices.currentDevice != "":
			iInputDevices.setRepeat(iInputDevices.currentDevice, configElement.value)

	def inputDevicesDelayChanged(self,configElement):
		if self.currentDevice != "" and iInputDevices.currentDevice == "":
			iInputDevices.setDelay(self.currentDevice, configElement.value)
		elif iInputDevices.currentDevice != "":
			iInputDevices.setDelay(iInputDevices.currentDevice, configElement.value)

	def setupConfigEntries(self,device):
		cmd = "config.inputDevices." + device + " = ConfigSubsection()"
		exec(cmd)
		if model in ("dm800","azboxhd"):
			cmd = "config.inputDevices." + device + ".enabled = ConfigYesNo(default = True)"
		else:
			cmd = "config.inputDevices." + device + ".enabled = ConfigYesNo(default = False)"
		exec(cmd)
		cmd = "config.inputDevices." + device + ".enabled.addNotifier(self.inputDevicesEnabledChanged,config.inputDevices." + device + ".enabled)"
		exec(cmd)
		cmd = "config.inputDevices." + device + '.name = ConfigText(default="")'
		exec(cmd)
		cmd = "config.inputDevices." + device + ".name.addNotifier(self.inputDevicesNameChanged,config.inputDevices." + device + ".name)"
		exec(cmd)
		if model in ("maram9","axodin"):
			cmd = "config.inputDevices." + device + ".repeat = ConfigSlider(default=400, increment = 10, limits=(0, 500))"
		elif model == "azboxhd":
			cmd = "config.inputDevices." + device + ".repeat = ConfigSlider(default=150, increment = 10, limits=(0, 500))"
		else:		
			cmd = "config.inputDevices." + device + ".repeat = ConfigSlider(default=100, increment = 10, limits=(0, 500))"	
		exec(cmd)
		cmd = "config.inputDevices." + device + ".repeat.addNotifier(self.inputDevicesRepeatChanged,config.inputDevices." + device + ".repeat)"
		exec(cmd)
		if model in ("maram9","axodin"):
			cmd = "config.inputDevices." + device + ".delay = ConfigSlider(default=200, increment = 100, limits=(0, 5000))"
		else:
			cmd = "config.inputDevices." + device + ".delay = ConfigSlider(default=700, increment = 100, limits=(0, 5000))"
		exec(cmd)
		cmd = "config.inputDevices." + device + ".delay.addNotifier(self.inputDevicesDelayChanged,config.inputDevices." + device + ".delay)"
		exec(cmd)

	def remapRemoteControl(self, device):
		filename = rc_model.getRcPositions()
		domRemote = self.loadRemoteControl(filename)
		logRemaps = []
		remapButtons = {}
		if domRemote is not None:
			rc = domRemote.find("rc")
			if rc is not None:
				for button in rc.findall("button"):
					keyid = KEYIDS.get(button.attrib.get("keyid"))
					remap = KEYIDS.get(button.attrib.get("remap"))
					if keyid is not None and remap is not None:
						logRemaps.append((button.attrib.get("keyid"), button.attrib.get("remap")))
						remapButtons[keyid] = remap
		if len(logRemaps):
			print("[InputDevice] Remapping remote control buttons for '%s':" % filename)
			for remap in logRemaps:
				print("[InputDevice] Remapping '%s' to '%s'." % (remap[0], remap[1]))
			for evdev, evdevinfo in iInputDevices.Devices.items():
				if evdevinfo["type"] == "remote":
					res = eRCInput.getInstance().setKeyMapping(evdevinfo["name"], remapButtons)
					resStr = {
						eRCInput.remapOk: "Remap completed okay.",
						eRCInput.remapUnsupported: "Error: Remapping not supported on device!",
						eRCInput.remapFormatErr: "Error: Remap map in incorrect format!",
						eRCInput.remapNoSuchDevice: "Error: Unknown device!",
					}.get(res, "Error: Unknown error!")
					print("[InputDevice] Remote remap evdev='%s', name='%s': %s" % (evdev, evdevinfo["name"], resStr))

	def loadRemoteControl(self, filename):
		domRemote = None
		try:
			with open(filename, "r") as fd:  # This open gets around a possible file handle leak in Python's XML parser.
				try:
					domRemote = xml.etree.cElementTree.parse(fd).getroot()
				except xml.etree.cElementTree.ParseError as err:
					fd.seek(0)
					content = fd.readlines()
					line, column = err.position
					print("[InputDevice] RC remap XML Parse Error: '%s' in '%s'!" % (err, filename))
					data = content[line - 1].replace("\t", " ").rstrip()
					print("[InputDevice] RC remap XML Parse Error: '%s'" % data)
					print("[InputDevice] RC remap XML Parse Error: '%s^%s'" % ("-" * column, " " * (len(data) - column - 1)))
				except Exception as err:
					print("[skin] Error: Unable to parse remote control data in '%s' - '%s'!" % (filename, err))
		except (IOError, OSError) as err:
			if err.errno == errno.ENOENT:  # No such file or directory
				print("[InputDevice] RC remap warning: Remote control file '%s' does not exist!" % filename)
			else:
				print("[InputDevice] RC remap error %d: Opening remote control file '%s'! (%s)" % (err.errno, filename, err.strerror))
		except Exception as err:
			print("[InputDevice] RC remap error: Unexpected error opening remote control file '%s'! (%s)" % (filename, err))
		return domRemote

iInputDevices = inputDevices()


config.plugins.remotecontroltype = ConfigSubsection()
config.plugins.remotecontroltype.rctype = ConfigInteger(default = int(getRCType()))
config.plugins.remotecontroltype.multirc = ConfigYesNo(default = False)

class RcTypeControl():
	def __init__(self):
		if pathExists("/proc/stb/ir/rc/type") and config.plugins.remotecontroltype.multirc.value is True:
			self.isSupported = True
			if config.plugins.remotecontroltype.rctype.value != 0:
				self.writeRcType(config.plugins.remotecontroltype.rctype.value)
		else:
			self.isSupported = False

	def multipleRcSupported(self):
		return self.isSupported

	def writeRcType(self, rctype):
		if self.isSupported and rctype > 0:
			open('/proc/stb/ir/rc/type', 'w').write('%d' % rctype)

	def readRcType(self):
		rc = 0
		if self.isSupported:
			rc = open('/proc/stb/ir/rc/type', 'r').read().strip()
		return int(rc)

iRcTypeControl = RcTypeControl()
