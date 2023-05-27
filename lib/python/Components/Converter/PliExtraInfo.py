# -*- coding: utf-8 -*-
from enigma import iServiceInformation, iPlayableService
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config
from Tools.Transponder import ConvertToHumanReadable
from Tools.GetEcmInfo import GetEcmInfo
from Components.Converter.Poll import Poll
from Components.SystemInfo import BoxInfo
from skin import parameters
from os.path import isfile

caid_data = (
	("0x0100", "0x01ff", "Seca", "S", True),
	("0x0500", "0x05ff", "Via", "V", True),
	("0x0600", "0x06ff", "Irdeto", "I", True),
	("0x0900", "0x09ff", "NDS", "Nd", True),
	("0x0b00", "0x0bff", "Conax", "Co", True),
	("0x0d00", "0x0dff", "CryptoW", "Cw", True),
	("0x0e00", "0x0eff", "PowerVU", "P", False),
	("0x1000", "0x10FF", "Tandberg", "TB", False),
	("0x1700", "0x17ff", "Beta", "B", True),
	("0x1800", "0x18ff", "Nagra", "N", True),
	("0x2600", "0x2600", "Biss", "Bi", False),
	("0x2700", "0x2710", "Dre3", "D3", False),
	("0x4ae0", "0x4ae1", "Dre", "D", False),
	("0x4aee", "0x4aee", "BulCrypt", "B1", False),
	("0x5581", "0x5581", "BulCrypt", "B2", False),
	("0x5601", "0x5604", "Verimatrix", "Vm", False)
)

# stream type to codec map
codec_data = {
	-1: "N/A",
	0: "MPEG2",
	1: "AVC",
	2: "H263",
	3: "VC1",
	4: "MPEG4-VC",
	5: "VC1-SM",
	6: "MPEG1",
	7: "HEVC",
	8: "VP8",
	9: "VP9",
	10: "XVID",
	11: "N/A 11",
	12: "N/A 12",
	13: "DIVX 3.11",
	14: "DIVX 4",
	15: "DIVX 5",
	16: "AVS",
	18: "VP6",
	19: "N/A 19",
	20: "N/A 20",
	21: "SPARK",
	40: "AVS2",
}

# Dynamic range ("gamma") value to text
gamma_data = {
	0: "SDR",
	1: "HDR",
	2: "HDR10",
	3: "HLG",
}


def addspace(text):
	if text:
		text += " "
	return text


class PliExtraInfo(Poll, Converter):
	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.type = type
		self.poll_interval = 1000
		self.poll_enabled = True
		self.info_fields = {
			# Field combinations accessible from skin
			"All": (
				(  # config.usage.show_cryptoinfo.value <= 0
					"ProviderName",
					"TransponderInfo",
					"TransponderName",
					"NewLine",
					"CryptoBar",
					"CryptoCurrentSource",
					"NewLine",
					"CryptoSpecial",
					"VideoCodec",
					"ResolutionString",
				), (  # config.usage.show_cryptoinfo.value > 0
					"ProviderName",
					"TransponderInfo",
					"TransponderName",
					"NewLine",
					"CryptoBar",
					"CryptoSpecial",
					"NewLine",
					"PIDInfo",
					"VideoCodec",
					"ResolutionString",
				)
			),
			"CryptoInfo": (
				(  # config.usage.show_cryptoinfo.value <= 0
					"CryptoBar",
					"CryptoCurrentSource",
					"CryptoSpecial",
				), (  # config.usage.show_cryptoinfo.value > 0
					"CryptoBar",
					"CryptoSpecial",
				)
			),
			"ServiceInfo": (
				"ProviderName",
				"TunerSystem",
				"TransponderFrequency",
				"TransponderPolarization",
				"TransponderSymbolRate",
				"TransponderFEC",
				"TransponderModulation",
				"OrbitalPosition",
				"TransponderName",
				"VideoCodec",
				"ResolutionString",
			),
			"TransponderInfo": (
				( # not feraw
					"StreamURLInfo",
				),
				(  # feraw and "DVB-T" not in feraw.get("tuner_type", "")
					"TunerSystem",
					"TransponderFrequencyMHz",
					"TransponderPolarization",
					"TransponderSymbolRate",
					"TransponderFEC",
					"TransponderModulation",
					"OrbitalPosition",
					"TransponderInfoMisPls",
				),
				(  # feraw and "DVB-T" in feraw.get("tuner_type", "")
					"TunerSystem",
					"TerrestrialChannelNumber",
					"TransponderFrequencyMHz",
					"TransponderPolarization",
					"TransponderSymbolRate",
					"TransponderFEC",
					"TransponderModulation",
					"OrbitalPosition",
				)
			),
			"TransponderInfo2line": (
				"ProviderName",
				"TunerSystem",
				"TransponderName",
				"NewLine",
				"TransponderFrequencyMHz",
				"TransponderPolarization",
				"TransponderSymbolRate",
				"TransponderModulationFEC",
			),
			"User": (),
		}
		self.ca_table = (
			("CryptoCaidSecaAvailable", "S", False),
			("CryptoCaidViaAvailable", "V", False),
			("CryptoCaidIrdetoAvailable", "I", False),
			("CryptoCaidNDSAvailable", "Nd", False),
			("CryptoCaidConaxAvailable", "Co", False),
			("CryptoCaidCryptoWAvailable", "Cw", False),
			("CryptoCaidPowerVUAvailable", "P", False),
			("CryptoCaidBetaAvailable", "B", False),
			("CryptoCaidNagraAvailable", "N", False),
			("CryptoCaidBissAvailable", "Bi", False),
			("CryptoCaidDre3Available", "D3", False),
			("CryptoCaidDreAvailable", "D", False),
			("CryptoCaidBulCrypt1Available", "B1", False),
			("CryptoCaidBulCrypt2Available", "B2", False),
			("CryptoCaidVerimatrixAvailable", "Vm", False),
			("CryptoCaidTandbergAvailable", "TB", False),
			("CryptoCaidSecaSelected", "S", True),
			("CryptoCaidViaSelected", "V", True),
			("CryptoCaidIrdetoSelected", "I", True),
			("CryptoCaidNDSSelected", "Nd", True),
			("CryptoCaidConaxSelected", "Co", True),
			("CryptoCaidCryptoWSelected", "Cw", True),
			("CryptoCaidPowerVUSelected", "P", True),
			("CryptoCaidBetaSelected", "B", True),
			("CryptoCaidNagraSelected", "N", True),
			("CryptoCaidBissSelected", "Bi", True),
			("CryptoCaidDre3Selected", "D3", True),
			("CryptoCaidDreSelected", "D", True),
			("CryptoCaidBulCrypt1Selected", "B1", True),
			("CryptoCaidBulCrypt2Selected", "B2", True),
			("CryptoCaidVerimatrixSelected", "Vm", True),
			("CryptoCaidTandbergSelected", "TB", True),
		)
		self.type = self.type.split(',')
		if self.type[0] == "User":
			self.info_fields[self.type[0]] = tuple(self.type[1:])
		self.type = self.type[0]
		self.ecmdata = GetEcmInfo()
		self.feraw = self.fedata = self.updateFEdata = None
		self.recursionCheck = set()

	def getCryptoInfo(self, info):
		if info.getInfo(iServiceInformation.sIsCrypted) == 1:
			data = self.ecmdata.getEcmData()
			self.current_source = data[0]
			self.current_caid = data[1]
			self.current_provid = data[2]
			self.current_ecmpid = data[3]
		else:
			self.current_source = ""
			self.current_caid = "0"
			self.current_provid = "0"
			self.current_ecmpid = "0"

	def createCryptoBar(self, info):
		res = ""
		available_caids = info.getInfoObject(iServiceInformation.sCAIDs)
		colors = parameters.get("PliExtraInfoColors", (0x0000FF00, 0x00FFFF00, 0x007F7F7F, 0x00FFFFFF)) # "found", "not found", "available", "default" colors

		for caid_entry in caid_data:
			if int(caid_entry[0], 16) <= int(self.current_caid, 16) <= int(caid_entry[1], 16):
				color = "\c%08x" % colors[0] # green
			else:
				color = "\c%08x" % colors[2] # grey
				try:
					for caid in available_caids:
						if int(caid_entry[0], 16) <= caid <= int(caid_entry[1], 16):
							color = "\c%08x" % colors[1] # yellow
				except:
					pass

			if color != "\c%08x" % colors[2] or caid_entry[4]:
				if res:
					res += " "
				res += color + caid_entry[3]

		res += "\c%08x" % colors[3] # white (this acts like a color "reset" for following strings
		return res

	def createCryptoSpecial(self, info):
		caid_name = "FTA"
		try:
			for caid_entry in caid_data:
				if int(caid_entry[0], 16) <= int(self.current_caid, 16) <= int(caid_entry[1], 16):
					caid_name = caid_entry[2]
					break
			return caid_name + ":%04x:%04x:%04x:%04x" % (int(self.current_caid, 16), int(self.current_provid, 16), info.getInfo(iServiceInformation.sSID), int(self.current_ecmpid, 16))
		except:
			pass
		return ""

	def createResolution(self, info):
		xres = info.getInfo(iServiceInformation.sVideoWidth)
		if not xres or xres == -1:
			if isfile("/proc/stb/vmpeg/0/xres"):
				print("[PliExtraInfo] Read /proc/stb/vmpeg/0/xres")
				f = open("/proc/stb/vmpeg/0/xres", "r")
				try:
					xres = int(f.read(), 16)
				except:
					print("[PliExtraInfo] Read /proc/stb/vmpeg/0/xres failed.")
			elif isfile("/sys/class/video/frame_width"):
				print("[PliExtraInfo] Read /sys/class/video/frame_width")
				f = open("/sys/class/video/frame_width", "r")
				try:
					xres = int(f.read())
				except:
					print("[PliExtraInfo] Read /sys/class/video/frame_width failed")
		yres = info.getInfo(iServiceInformation.sVideoHeight)
		if not yres:
			if isfile("/proc/stb/vmpeg/0/yres"):
				print("[PliExtraInfo] Read /proc/stb/vmpeg/0/yres")
				f = open("/proc/stb/vmpeg/0/yres", "r")
				try:
					yres = int(f.read(), 16)
				except:
					print("[PliExtraInfo] Read /proc/stb/vmpeg/0/yres failed.")
			elif isfile("/sys/class/video/frame_height"):
				print("[PliExtraInfo] Read /sys/class/video/frame_height")
				f = open("/sys/class/video/frame_height", "r")
				try:
					yres = int(f.read())
				except:
					print("[PliExtraInfo] Read /sys/class/video/frame_height failed")
		mode = ("i", "p", " ")[info.getInfo(iServiceInformation.sProgressive)]
		if not mode:
			try:
				print("[PliExtraInfo] Read /proc/stb/vmpeg/0/progressive")
				mod = open("/proc/stb/vmpeg/0/progressive", "r")
				if BoxInfo.getItem("AmlogicFamily"):
					mode = "p" if int(mod.read()) else "i"
				else:
					mode = "p" if int(mod.read(), 16) else "i"
			except:
				print("[PliExtraInfo] Read /proc/stb/vmpeg/0/progressive failed.")
		fps = (info.getInfo(iServiceInformation.sFrameRate) + 500) // 1000
		if not fps or fps == -1:
			try:
				if isfile("/proc/stb/vmpeg/0/framerate"):
					print("[PliExtraInfo] Read /proc/stb/vmpeg/0/framerate")
					fps = (int(open("/proc/stb/vmpeg/0/framerate", "r").read()) + 500) // 1000
				elif isfile("/proc/stb/vmpeg/0/fallback_framerate"):
					print("[PliExtraInfo] Read /proc/stb/vmpeg/0/fallback_framerate")
					fps = (int(open("/proc/stb/vmpeg/0/fallback_framerate", "r").read()) + 0) // 1000
			except:
				print("[PliExtraInfo] Read framerate failed.")
		return "%sx%s%s%s" % (xres, yres, mode, fps)

	def createGamma(self, info):
		return gamma_data.get(info.getInfo(iServiceInformation.sGamma), "")

	def createVideoCodec(self, info):
		return codec_data.get(info.getInfo(iServiceInformation.sVideoType), _("N/A"))

	def createPIDInfo(self, info):
		vpid = info.getInfo(iServiceInformation.sVideoPID)
		apid = info.getInfo(iServiceInformation.sAudioPID)
		pcrpid = info.getInfo(iServiceInformation.sPCRPID)
		sidpid = info.getInfo(iServiceInformation.sSID)
		tsid = info.getInfo(iServiceInformation.sTSID)
		onid = info.getInfo(iServiceInformation.sONID)
		if vpid < 0:
			vpid = 0
		if apid < 0:
			apid = 0
		if pcrpid < 0:
			pcrpid = 0
		if sidpid < 0:
			sidpid = 0
		if tsid < 0:
			tsid = 0
		if onid < 0:
			onid = 0
		return "%d-%d:%05d:%04d:%04d:%04d" % (onid, tsid, sidpid, vpid, apid, pcrpid)

	def createInfoString(self, fieldGroup, fedata, feraw, info):
		if fieldGroup in self.recursionCheck:
			return _("?%s-recursive?") % fieldGroup
		self.recursionCheck.add(fieldGroup)

		fields = self.info_fields[fieldGroup]
		if fields and isinstance(fields[0], (tuple, list)):
			if fieldGroup == "TransponderInfo":
				fields = fields[feraw and int("DVB-T" in feraw.get("tuner_type", "")) + 1 or 0]
			else:
				fields = fields[int(config.usage.show_cryptoinfo.value) > 0]

		ret = ""
		vals = []
		for field in fields:
			val = None
			if field == "CryptoCurrentSource":
				self.getCryptoInfo(info)
				vals.append(self.current_source)
			elif field == "StreamURLInfo":
				val = self.createStreamURLInfo(info)
			elif field == "TransponderModulationFEC":
				val = self.createModulation(fedata) + '-' + self.createFEC(fedata, feraw)
			elif field == "TransponderName":
				val = self.createTransponderName(feraw)
			elif field == "ProviderName":
				val = self.createProviderName(info)
			elif field in ("NewLine", "NL"):
				ret += "  ".join(vals) + "\n"
				vals = []
			else:
				val = self.getTextByType(field)

			if val:
				vals.append(val)

		return ret + "  ".join(vals)

	def createStreamURLInfo(self, info):
		refstr = info.getInfoString(iServiceInformation.sServiceref)
		if "%3a//" in refstr.lower():
			return refstr.split(":")[10].replace("%3a", ":").replace("%3A", ":")
		return ""

	def createFrequency(self, feraw):
		frequency = feraw.get("frequency")
		if frequency:
			if "DVB-T" in feraw.get("tuner_type"):
				return "%d %s" % (int(frequency // 1000000. + 0.5), _("MHz"))
			else:
				return str(int(frequency // 1000 + 0.5))
		return ""

	def createChannelNumber(self, fedata, feraw):
		return "DVB-T" in feraw.get("tuner_type", "") and fedata.get("channel") or ""

	def createSymbolRate(self, fedata, feraw):
		if "DVB-T" in feraw.get("tuner_type", ""):
			bandwidth = fedata.get("bandwidth")
			if bandwidth:
				return bandwidth
		else:
			symbolrate = fedata.get("symbol_rate")
			if symbolrate:
				return str(symbolrate // 1000)
		return ""

	def createPolarization(self, fedata):
		return fedata.get("polarization_abbreviation") or ""

	def createFEC(self, fedata, feraw):
		if "DVB-T" in feraw.get("tuner_type", ""):
			code_rate_lp = fedata.get("code_rate_lp")
			code_rate_hp = fedata.get("code_rate_hp")
			guard_interval = fedata.get("guard_interval")
			if code_rate_lp and code_rate_hp and guard_interval:
				return code_rate_lp + "-" + code_rate_hp + "-" + guard_interval
		else:
			fec = fedata.get("fec_inner")
			if fec:
				return fec
		return ""

	def createModulation(self, fedata):
		if fedata.get("tuner_type") == _("Terrestrial"):
			constellation = fedata.get("constellation")
			if constellation:
				return constellation
		else:
			modulation = fedata.get("modulation")
			if modulation:
				return modulation
		return ""

	def createTunerType(self, feraw):
		return feraw.get("tuner_type") or ""

	def createTunerSystem(self, fedata):
		return fedata.get("system") or ""

	def createOrbPos(self, feraw):
		orbpos = feraw.get("orbital_position")
		if orbpos:
			if orbpos > 1800:
				return _("%.1f° W") % ((3600 - orbpos) / 10.0)
			elif orbpos > 0:
				return _("%.1f° E") % (orbpos / 10.0)
		return ""

	def createOrbPosOrTunerSystem(self, fedata, feraw):
		orbpos = self.createOrbPos(feraw)
		if orbpos != "":
			return orbpos
		return self.createTunerSystem(fedata)

	def createProviderName(self, info):
		return info.getInfoString(iServiceInformation.sProvider)

	def createMisPls(self, fedata):
		tmp = ""
		if fedata.get("is_id"):
			if fedata.get("is_id") > -1:
				tmp = "MIS %d" % fedata.get("is_id")
		if fedata.get("pls_code"):
			if fedata.get("pls_code") > 0:
				tmp = addspace(tmp) + "%s %d" % (fedata.get("pls_mode"), fedata.get("pls_code"))
		if fedata.get("t2mi_plp_id"):
			if fedata.get("t2mi_plp_id") > -1:
				tmp = addspace(tmp) + "T2MI %d PID %d" % (fedata.get("t2mi_plp_id"), fedata.get("t2mi_pid"))
		return tmp

	@cached
	def getText(self):
		self.recursionCheck.clear()
		return self.getTextByType(self.type)

	def getTextByType(self, textType):
		service = self.source.service
		if service is None:
			return ""
		info = service and service.info()

		if not info:
			return ""

		if textType == "CryptoBar":
			self.getCryptoInfo(info)
			return self.createCryptoBar(info)

		if textType == "CryptoSpecial":
			self.getCryptoInfo(info)
			return self.createCryptoSpecial(info)

		if textType == "Resolution":
			return self.createResolution(info)

		if textType == "ResolutionString":
			return addspace(self.createResolution(info)) + self.createGamma(info)

		if textType == "VideoCodec":
			return self.createVideoCodec(info)

		if textType == "Gamma":
			return self.createGamma(info)

		if self.updateFEdata:
			feinfo = service.frontendInfo()
			if feinfo:
				self.feraw = feinfo.getAll(config.usage.infobar_frontend_source.value == "settings")
				if self.feraw:
					self.fedata = ConvertToHumanReadable(self.feraw)

		feraw = self.feraw
		if not feraw:
			feraw = info.getInfoObject(iServiceInformation.sTransponderData)
			fedata = ConvertToHumanReadable(feraw)
		else:
			fedata = self.fedata

		if textType in self.info_fields:
			return self.createInfoString(textType, fedata, feraw, info)

		if textType == "PIDInfo":
			return self.createPIDInfo(info)

		if textType == "ServiceRef":
			return self.createServiceRef(info)

		if not feraw:
			return ""

		if textType == "TransponderFrequency":
			return self.createFrequency(feraw)

		if textType == "TransponderFrequencyMHz":
			return self.createFrequency(fedata)

		if textType == "TransponderSymbolRate":
			return self.createSymbolRate(fedata, feraw)

		if textType == "TransponderPolarization":
			return self.createPolarization(fedata)

		if textType == "TransponderFEC":
			return self.createFEC(fedata, feraw)

		if textType == "TransponderModulation":
			return self.createModulation(fedata)

		if textType == "OrbitalPosition":
			return self.createOrbPos(feraw)

		if textType == "TunerType":
			return self.createTunerType(feraw)

		if textType == "TunerSystem":
			return self.createTunerSystem(fedata)

		if textType == "OrbitalPositionOrTunerSystem":
			return self.createOrbPosOrTunerSystem(fedata, feraw)

		if textType == "TerrestrialChannelNumber":
			return self.createChannelNumber(fedata, feraw)

		if textType == "TransponderInfoMisPls":
			return self.createMisPls(fedata)

		return _("?%s?") % textType

	text = property(getText)

	@cached
	def getBool(self):
		service = self.source.service
		info = service and service.info()

		if not info:
			return False

		request_caid = None
		for x in self.ca_table:
			if x[0] == self.type:
				request_caid = x[1]
				request_selected = x[2]
				break

		if request_caid is None:
			return False

		if info.getInfo(iServiceInformation.sIsCrypted) != 1:
			return False

		data = self.ecmdata.getEcmData()

		if data is None:
			return False

		current_caid = data[1]

		available_caids = info.getInfoObject(iServiceInformation.sCAIDs)

		for caid_entry in caid_data:
			if caid_entry[3] == request_caid:
				if request_selected:
					if int(caid_entry[0], 16) <= int(current_caid, 16) <= int(caid_entry[1], 16):
						return True
				else: # request available
					try:
						for caid in available_caids:
							if int(caid_entry[0], 16) <= caid <= int(caid_entry[1], 16):
								return True
					except:
						pass

		return False

	boolean = property(getBool)

	def changed(self, what):
		if what[0] == self.CHANGED_SPECIFIC:
			self.updateFEdata = False
			if what[1] == iPlayableService.evNewProgramInfo:
				self.updateFEdata = True
			if what[1] == iPlayableService.evEnd:
				self.feraw = self.fedata = None
			Converter.changed(self, what)
		elif what[0] == self.CHANGED_POLL and self.updateFEdata is not None:
			self.updateFEdata = False
			Converter.changed(self, what)
