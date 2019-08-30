import os
from enigma import getBoxType
from Tools.Directories import SCOPE_SKIN, resolveFilename
from Tools.StbHardware import getFPVersion, getBoxProc

class RcModel:
	RcModels = {}
	fp_version = str(getFPVersion())
	procmodel = getBoxProc()
	remote = "dmm1"	# default. Assume files for dmm1 exists
	def __init__(self):
		self.model = getBoxType()
		# cfg files has modelname  rcname entries.
		# modelname is boxname optionally followed by .rctype
		for line in open((resolveFilename(SCOPE_SKIN, 'rc_models/rc_models.cfg')), 'r'):
			if line.startswith(self.model):
				m, r = line.strip().split()
				self.RcModels[m] = r

	def rcIsDefault(self):
		# Default RC can only happen with DMM type remote controls...
		return self.model.startswith('dm')

	def getRcFile(self, ext):
		# check for rc/type every time so rctype changes will be noticed
		if os.path.exists('/proc/stb/ir/rc/type'):
			rc = open('/proc/stb/ir/rc/type').read().strip()
			modeltype = '%s.%s' % (self.model, rc)
		else:
			modeltype = None

		if modeltype is not None and modeltype in self.RcModels.keys():
			remote = self.RcModels[modeltype]
		elif self.model in self.RcModels.keys():
			remote = self.RcModels[self.model]
		elif self.model == "azboxhd" and not procmodel in ("elite","ultra"):
			remote = "azboxhd"
		elif procmodel in ("elite","ultra"):
			remote = "azboxelite"
		elif self.model == "et9x00" and not procmodel == "et9500":
			remote = "et9x00"
		elif procmodel == "et9500":
			remote = "et9500"
		elif self.model in ("et5x00","et6x00") and not procmodel == "et6500":
			remote = "et6x00"
		elif procmodel == "et6500":
			remote = "et6500"
		elif self.model == "ventonhdx" or procmodel == "ini-3000" and fp_version.startswith('1'):
			remote = "ini0"
		elif procmodel in ("ini-5000","ini-7000","ini-7012"):
			remote = "ini1"
		elif self.model == "ventonhdx" or procmodel == "ini-3000" and not fp_version.startswith('1'):
			remote = "ini2"
		f = resolveFilename(SCOPE_SKIN, 'rc_models/' + remote + '.' + ext)
		if not os.path.exists(f):
			f = resolveFilename(SCOPE_SKIN, 'rc_models/dmm1.' + ext)
		return f

	def getRcImg(self):
		return self.getRcFile('png')

	def getRcPositions(self):
		return self.getRcFile('xml')

rc_model = RcModel()
