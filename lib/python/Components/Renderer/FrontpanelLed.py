#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
from Components.Element import Element

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

		try:
			print("[FrontpanelLed] Write to /proc/stb/fp/led%d_pattern" % self.which)
			open("/proc/stb/fp/led%d_pattern" % self.which, "w").write("%08x" % pattern)
		except IOError:
			print("[FrontpanelLed] Write to /proc/stb/fp/led_pattern failed.")
		if self.which == 0:
			try:
				print("[FrontpanelLed] Write to /proc/stb/fp/led_pattern")
				open("/proc/stb/fp/led_set_pattern", "w").write("%08x" % pattern_4bit)
				print("[FrontpanelLed] Write to /proc/stb/fp/led_set_speed")
				open("/proc/stb/fp/led_set_speed", "w").write("%d" % speed)
			except IOError:
				print("[FrontpanelLed] Write to /proc/stb/fp/led_pattern failed.")
				print("[FrontpanelLed] Write to /proc/stb/fp/led_set_speed failed.")
			try:
				print("[FrontpanelLed] Write to /proc/stb/fp/led_pattern_speed")
				open("/proc/stb/fp/led_pattern_speed", "w").write("%d" % speed)
			except IOError:
				print("[FrontpanelLed] Write to /proc/stb/fp/led_pattern_speed failed.")
