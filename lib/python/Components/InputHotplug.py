# -*- coding: utf-8 -*-
from Components import Netlink
from enigma import addInputDevice, removeInputDevice
from os.path import join


class NetlinkReader():
	def __init__(self):
		from twisted.internet import reactor
		self.nls = Netlink.NetlinkSocket()
		reactor.addReader(self)

	def fileno(self):
		return self.nls.fileno()

	def doRead(self):
		for event in self.nls.parse():
			try:
				subsystem = event['SUBSYSTEM']
				if subsystem == 'input':
					devname = event['DEVNAME']
					action = event['ACTION']
					if action == 'add':
						print("[InputHotplug] New input device detected:", devname)
						addInputDevice(join('/dev', devname))
					elif action == 'remove':
						print("[InputHotplug] Removed input device:", devname)
						removeInputDevice(join('/dev', devname))
				elif subsystem == 'net':
					from Components.Network import iNetwork
					iNetwork.hotplug(event)
			except KeyError:
				# Ignore "not found"
				pass

	def connectionLost(self, failure):
		# Ignore...
		print("[InputHotplug] connectionLost?", failure)
		self.nls.close()

	def logPrefix(self):
		return 'NetlinkReader'


reader = NetlinkReader()
