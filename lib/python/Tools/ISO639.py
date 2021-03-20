#!/usr/bin/python
# -*- coding: utf-8 -*-
try:
	import cPickle as pickle
except:
	import pickle
import enigma
from six import PY2

with open(enigma.eEnv.resolve("${datadir}/enigma2/iso-639-3.pck"), 'rb') as f:
	if PY2:
		LanguageCodes = pickle.load(f)
	else:
		LanguageCodes = pickle.load(f, encoding="bytes")
