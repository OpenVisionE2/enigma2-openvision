from Components.Pixmap import Pixmap
from Components.Renderer.Renderer import Renderer
from enigma import iServiceInformation
from string import upper
from enigma import ePixmap
from Tools.Directories import fileExists, SCOPE_CURRENT_SKIN, resolveFilename

class PicCript(Renderer):
	__module__ = __name__
	searchPaths = ('/usr/share/enigma2/%s/','/media/hdd/%s/','/media/usb/%s/','/media/ba/%s/')

	def __init__(self):
		Renderer.__init__(self)
		self.path = 'cript'
		self.nameCache = {}
		self.pngname = ''
		self.picon_default = "picon_default.png"

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value,) in self.skinAttributes:
			if (attrib == 'path'):
				self.path = value
			elif (attrib == 'picon_default'):
				self.picon_default = value
			else:
				attribs.append((attrib, value))

		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	GUI_WIDGET = ePixmap

	def changed(self, what):
		if self.instance:
			pngname = ''
			if (what[0] != self.CHANGED_CLEAR):
				sname = "none"
				service = self.source.service
				if service:
					info = (service and service.info())
					if info:
						caids = info.getInfoObject(iServiceInformation.sCAIDs)
						if caids:
							if (len(caids) > 0):
								for caid in caids:
									caid = self.int2hex(caid)
									if (len(caid) == 3):
										caid = ("0%s" % caid)
										caid = caid[:2]
										caid = caid.upper()
										if (caid == "26"):
											sname = "BiSS"
										elif (caid == "01"):
											sname = "SEC"
										elif (caid == "06"):
											sname = "IRD"
										elif (caid == "17"):
											sname = "BET"
										elif (caid == "05"):
											sname = "VIA"
										elif (caid == "18"):
											sname = "NAG"
										elif (caid == "09"):
											sname = "NDS"
										elif (caid == "0B"):
											sname = "CONN"
										elif (caid == "0D"):
											sname = "CRW"
										elif (caid == "4A"):
											sname = "DRE"
										elif (caid == "0E"):
											sname = "PowerVU"
										elif (caid == "22"):
											sname = "Codicrypt"
										elif (caid == "07"):
											sname = "DigiCipher"
										elif (caid == "A1"):
											sname = "Rosscrypt"
										elif (caid == "56"):
											sname = "Verimatrix"

				pngname = self.nameCache.get(sname, '')
				if (pngname == ''):
					pngname = self.findPicon(sname)
					if (pngname != ''):
						self.nameCache[sname] = pngname
			if (pngname == ''):
				pngname = self.nameCache.get('default', '')
				if (pngname == ''):
					pngname = self.findPicon('picon_default')
					if (pngname == ''):
						tmp = resolveFilename(SCOPE_CURRENT_SKIN, 'picon_default.png')
						if fileExists(tmp):
							pngname = tmp
						self.nameCache['default'] = pngname

			if (self.pngname != pngname):
				self.pngname = pngname
				self.instance.setPixmapFromFile(self.pngname)

	def int2hex(self, int):
		return ("%x" % int)

	def findPicon(self, serviceName):
		for path in self.searchPaths:
			pngname = (((path % self.path) + serviceName) + '.png')
			if fileExists(pngname):
				return pngname
		return ''
