# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from Components.Element import cached


class FrontendInfo2(Converter, object):
	BER = 0
	SNR = 1
	AGC = 2
	LOCK = 3
	SNRdB = 4
	SLOT_NUMBER = 5
	TUNER_TYPE = 6
	SNR_ANALOG = 7
	AGC_ANALOG = 8

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "BER":
			self.type = self.BER
		elif type == "SNR":
			self.type = self.SNR
		elif type == "SNRdB":
			self.type = self.SNRdB
		elif type == "AGC":
			self.type = self.AGC
		elif type == "NUMBER":
			self.type = self.SLOT_NUMBER
		elif type == "TYPE":
			self.type = self.TUNER_TYPE
		elif type == "SNR_ANALOG":
			self.type = self.SNR_ANALOG
		elif type == "AGC_ANALOG":
			self.type = self.AGC_ANALOG
		else:
			self.type = self.LOCK

	@cached
	def getText(self):
		assert self.type not in (self.LOCK, self.SLOT_NUMBER), "the text output of FrontendInfo cannot be used for lock info"
		percent = None
		if self.type == self.BER: # as count
			count = self.source.ber
			if count is not None:
				return str(count)
			else:
				return "N/A"
		elif self.type == self.AGC:
			percent = self.source.agc
		elif self.type == self.SNR:
			percent = self.source.snr
		elif self.type == self.SNRdB:
			#if self.source.snr_db is not None:
				#return "%3.01f dB" % (self.source.snr_db / 100.0)
			if self.source.snr is not None: #fallback to normal SNR
				return "%3.01f dB" % (0.32 * ((self.source.snr * 100) / 65536.0) / 2)
			return "N/A"
		elif self.type == self.TUNER_TYPE:
			return self.source.frontend_type and self.frontend_type or "Unknown"
		if percent is None:
			return "N/A"
		return "%d %%" % (percent * 100 / 65536.0)

	@cached
	def getBool(self):
		assert self.type in (self.LOCK, self.BER), "the boolean output of FrontendInfo can only be used for lock or BER info"
		if self.type == self.LOCK:
			lock = self.source.lock
			if lock is None:
				lock = False
			return lock
		else:
			ber = self.source.ber
			if ber is None:
				ber = 0
			return ber > 0

	text = property(getText)

	boolean = property(getBool)

	@cached
	def getValue(self):
		assert self.type != self.LOCK, "the value/range output of FrontendInfo can not be used for lock info"
		_local = 0
		if self.type == self.AGC:
			return self.source.agc or 0
		elif self.type == self.AGC_ANALOG:
			if self.source.agc is None:
				return 50
			_local = int(((self.source.agc * 60) / 65536.0) / 3)
			if _local < 10:
				return _local + 50
			elif _local >= 10:
				return _local - 10
		elif self.type == self.SNR:
			return self.source.snr or 0
		elif self.type == self.SNR_ANALOG:
			if self.source.snr is None:
				return 50
			_local = int(((self.source.snr * 60) / 65536.0) / 3)
			if _local < 10:
				return _local + 50
			elif _local >= 10:
				return _local - 10
		elif self.type == self.BER:
			if self.BER < self.range:
				return self.BER or 0
			else:
				return self.range
		elif self.type == self.TUNER_TYPE:
			type = self.source.frontend_type
			if type == 'DVB-S':
				return 0
			elif type == 'DVB-C':
				return 1
			elif type == 'DVB-T':
				return 2
			return -1
		elif self.type == self.SLOT_NUMBER:
			num = self.source.slot_number
			return num is None and -1 or num

	range = 65536
	value = property(getValue)
