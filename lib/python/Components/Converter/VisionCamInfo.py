from Components.Converter.Converter import Converter
from Components.config import config
from Components.Element import cached
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS
from Components.Converter.Poll import Poll


class VisionCamInfo(Poll, Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.poll_interval = 2000
		self.poll_enabled = True

	@cached
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if not service:
			return None
		camd = ""
		serlist = None
		camdlist = None
		nameemu = []
		nameser = []
		if not info:
			return ""
		# Alternative SoftCam Manager 
		if fileExists(resolveFilename(SCOPE_PLUGINS, "Extensions/AlternativeSoftCamManager/plugin.pyo")): 
			if config.plugins.AltSoftcam.actcam.value != "none": 
				return config.plugins.AltSoftcam.actcam.value 
			else: 
				return None
		#  GlassSysUtil 
		elif fileExists("/tmp/ucm_cam.info"):
			return open("/tmp/ucm_cam.info").read()
		# Pli
		elif fileExists("/etc/init.d/softcam") or fileExists("/etc/init.d/cardserver"):
			try:
				for line in open("/etc/init.d/softcam"):
					if "echo" in line:
						nameemu.append(line)
				camdlist = "%s" % nameemu[1].split('"')[1]
			except:
				pass
			try:
				for line in open("/etc/init.d/cardserver"):
					if "echo" in line:
						nameser.append(line)
				serlist = "%s" % nameser[1].split('"')[1]
			except:
				pass
			if serlist is not None and camdlist is not None:
				return ("%s %s" % (serlist, camdlist))
			elif camdlist is not None:
				return "%s" % camdlist
			elif serlist is not None:
				return "%s" % serlist
			return ""
		else:
			return None
  
		if serlist is not None:
			try:
				cardserver = ""
				for current in serlist.readlines():
					cardserver = current
				serlist.close()
			except:
				pass
		else:
			cardserver = " "

		if camdlist is not None:
			try:
				emu = ""
				for current in camdlist.readlines():
					emu = current
				camdlist.close()
			except:
				pass
		else:
			emu = " "

		return "%s %s" % (cardserver.split('\n')[0], emu.split('\n')[0])

	text = property(getText)

	def changed(self, what):
		Converter.changed(self, what)
