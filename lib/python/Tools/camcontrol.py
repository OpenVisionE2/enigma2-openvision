# -*- coding: utf-8 -*-
from os import listdir, readlink, unlink, symlink
from os.path import exists, split
from enigma import eConsoleAppContainer


class CamControl:
	'''CAM convention is that a softlink named /etc/init.c/softcam.* points
	to the start/stop script.'''

	def __init__(self, name):
		self.name = name
		self.link = '/etc/init.d/' + name
		if not exists(self.link):
			print("[camcontrol] No softcam link?", self.link)

	def getList(self):
		result = []
		prefix = self.name + '.'
		for f in listdir("/etc/init.d"):
			if f.startswith(prefix):
				result.append(f[len(prefix):])
		return result

	def current(self):
		try:
			l = readlink(self.link)
			prefix = self.name + '.'
			return split(l)[1].split(prefix, 2)[1]
		except:
			pass
		return None

	def command(self, cmd):
		if exists(self.link):
			print("[camcontrol] Executing", self.link + ' ' + cmd)
			eConsoleAppContainer().execute(self.link + ' ' + cmd)

	def select(self, which):
		print("[camcontrol] Selecting CAM:", which)
		if not which:
			which = "None"
		dst = self.name + '.' + which
		if not exists('/etc/init.d/' + dst):
			print("[camcontrol] init script does not exist:", dst)
			return
		try:
			unlink(self.link)
		except:
			pass
		try:
			symlink(dst, self.link)
		except:
			print("[camcontrol] Failed to create symlink for softcam:", dst)
			import sys
			print(sys.exc_info()[:2])
