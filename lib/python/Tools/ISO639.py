# -*- coding: utf-8 -*-
from six.moves import cPickle as pickle
from enigma import eEnv
from six import PY2

with open(eEnv.resolve("${datadir}/enigma2/iso-639-3.pck"), 'rb') as f:
	if PY2:
		LanguageCodes = pickle.load(f)
	else:
		LanguageCodes = pickle.load(f, encoding="bytes")
