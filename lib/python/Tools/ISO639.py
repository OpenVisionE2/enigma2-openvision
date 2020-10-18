#!/usr/bin/python
# -*- coding: utf-8 -*-
try:
	import cPickle as pickle
except:
	import pickle
import enigma
import six

with open(enigma.eEnv.resolve("${datadir}/enigma2/iso-639-3.pck"), 'rb') as f:
	if six.PY2:
		LanguageCodes = pickle.load(f)
	else:
		LanguageCodes = pickle.load(f, encoding="bytes")
