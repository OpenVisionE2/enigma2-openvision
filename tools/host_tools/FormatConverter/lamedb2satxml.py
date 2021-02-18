#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
from datasource import genericdatasource
from satxml import satxml
from lamedb import lamedb

import sys

if len(sys.argv) != 3:
	print("[lamedb2satxml] usage: %s <lamedb> <satellites.xml>" % sys.argv[0])
	sys.exit()

gen = genericdatasource()
db = lamedb(sys.argv[1])
xml = satxml(sys.argv[2])

db.read()
gen.source = db
gen.destination = xml
gen.docopymerge(action="copy")
xml.write()
