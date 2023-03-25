# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Components.Harddisk import harddiskmanager
from twisted.internet.protocol import Protocol, Factory
from os import remove
from os.path import isfile, exists

# globals
hotplugNotifier = []
audiocd = False


def AudiocdAdded():
	global audiocd
	if audiocd:
		return True
	else:
		return False


def processHotplugData(self, v):
	print("[Hotplug]:", v)
	action = v.get("ACTION")
	device = v.get("DEVPATH")
	physdevpath = v.get("PHYSDEVPATH")
	if physdevpath == "-":
		physdevpath = None
	media_state = v.get("X_E2_MEDIA_STATUS")
	global audiocd

	dev = device.split('/')[-1]

	if action == "add":
		error, blacklisted, removable, is_cdrom, partitions, medium_found = harddiskmanager.addHotplugPartition(dev, physdevpath)
	elif action == "remove":
		harddiskmanager.removeHotplugPartition(dev)
	elif action == "audiocdadd":
		audiocd = True
		media_state = "audiocd"
		error, blacklisted, removable, is_cdrom, partitions, medium_found = harddiskmanager.addHotplugAudiocd(dev, physdevpath)
		print("[Hotplug] AUDIO CD ADD")
	elif action == "audiocdremove":
		audiocd = False
		file = []
		# Removing the invalid playlist.e2pls If its still the audio cd's list
		# Default setting is to save last playlist on closing Mediaplayer.
		# If audio cd is removed after Mediaplayer was closed,
		# the playlist remains in if no other media was played.
		if isfile('/etc/enigma2/playlist.e2pls'):
			with open('/etc/enigma2/playlist.e2pls', 'r') as f:
				file = f.readline().strip()
		if file:
			if '.cda' in file:
				try:
					remove('/etc/enigma2/playlist.e2pls')
				except OSError:
					pass
		harddiskmanager.removeHotplugPartition(dev)
		print("[Hotplug] REMOVING AUDIOCD")
	elif media_state is not None:
		if media_state == '1':
			harddiskmanager.removeHotplugPartition(dev)
			harddiskmanager.addHotplugPartition(dev, physdevpath)
		elif media_state == '0':
			harddiskmanager.removeHotplugPartition(dev)

	for callback in hotplugNotifier:
		try:
			callback(dev, action or media_state)
		except AttributeError:
			hotplugNotifier.remove(callback)


class Hotplug(Protocol):
	def connectionMade(self):
		print("[Hotplug] connection!")
		self.received = ""

	def dataReceived(self, data):
		from six import ensure_str
		data = ensure_str(data)
		self.received += data
		print("[Hotplug] complete", self.received)

	def connectionLost(self, reason):
		print("[Hotplug] connection lost!")
		data = self.received.split('\0')[:-1]
		v = {}
		for x in data:
			i = x.find('=')
			var, val = x[:i], x[i + 1:]
			v[var] = val
		processHotplugData(self, v)


def autostart(reason, **kwargs):
	if reason == 0:
		from twisted.internet import reactor
		try:
			if exists("/tmp/hotplug.socket"):
				remove("/tmp/hotplug.socket")
			factory = Factory()
			factory.protocol = Hotplug
			reactor.listenUNIX("/tmp/hotplug.socket", factory)
		except (OSError, CannotListenError) as err:
			print("[Hotplug]", err)


def Plugins(**kwargs):
	return PluginDescriptor(name=_("Hotplug"), description=_("listens to hotplug events"), where=PluginDescriptor.WHERE_AUTOSTART, needsRestart=True, fnc=autostart)
