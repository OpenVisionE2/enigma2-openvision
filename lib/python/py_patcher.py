# -*- coding: utf-8 -*-
from os import rename, remove
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Tools.PyVerHelper import getPyExt

filename = resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/plugin.%s" % getPyExt())
rename(filename, filename + ".org")

source = open(filename + ".org", "r")
dest = open(filename, "w")

for line, str in enumerate(source):
	oldstr = str[:]
	str = str.replace('dm7080N', 'dn7080N')
	str = str.replace('dm820N', 'dn820N')
	str = str.replace('dm520N', 'dn520N')
	str = str.replace('dm525N', 'dn525N')
	str = str.replace('dm900N', 'dn900N')
	str = str.replace('dm920N', 'dn920N')

	if oldstr != str:
		print("!!! Patch line %d" % (line))

	dest.write(str)

del source
del dest
remove(filename + ".org")
