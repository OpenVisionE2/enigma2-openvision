#!/usr/bin/python
# -*- coding: utf-8 -*-
try:
	import cPickle as pickle
except:
	import pickle
import enigma
with open(enigma.eEnv.resolve("${datadir}/enigma2/iso-639-3.pck"), 'rb') as f:
	LanguageCodes = pickle.load(f)
