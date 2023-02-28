# -*- coding: utf-8 -*-
from Components.Element import Element
from os.path import exists
# this is not a GUI renderer.


class FrontpanelLed(Element):
	def __init__(self, which=0, patterns=[(20, 0, 0xffffffff), (20, 0x55555555, 0x84fc8c04)], boolean=True):
		self.which = which
		self.boolean = boolean
		self.patterns = patterns
		Element.__init__(self)

	def changed(self, *args, **kwargs):
		if self.boolean:
			val = self.source.boolean and 0 or 1
		else:
			val = self.source.value

		(speed, pattern, pattern_4bit) = self.patterns[val]

		if exists("/proc/stb/fp/led%s_pattern" % str(self.which)):
			print("[FrontpanelLed] Write to /proc/stb/fp/led%s_pattern" % str(self.which))
			with open("/proc/stb/fp/led%s_pattern" % str(self.which), "w") as f:
				f.write("%08x" % pattern)
				f.close()
		if self.which == 0:
			if exists("/proc/stb/fp/led_set_pattern"):
				print("[FrontpanelLed] Write to /proc/stb/fp/led_set_pattern")
				with open("/proc/stb/fp/led_set_pattern", "w") as f:
					f.write("%08x" % pattern_4bit)
					f.close()
			if exists("/proc/stb/fp/led_set_speed"):
				print("[FrontpanelLed] Write to /proc/stb/fp/led_set_speed")
				with open("/proc/stb/fp/led_set_speed", "w") as f:
					f.write("%d" % speed)
					f.close()
			if exists("/proc/stb/fp/led_pattern_speed"):
				print("[FrontpanelLed] Write to /proc/stb/fp/led_pattern_speed")
				with open("/proc/stb/fp/led_pattern_speed", "w") as f:
					f.write("%d" % speed)
					f.close()
