# -*- coding: utf-8 -*-
from Components.MenuList import MenuList


class FIFOList(MenuList):
	def __init__(self, list=None, len=10):
		self.list = list or []
		self.len = len
		MenuList.__init__(self, self.list)

	def addItem(self, item):
		self.list.append(item)
		self.l.setList(self.list[-int(self.len):])

	def clear(self):
		del self.list[:]
		self.l.setList(self.list)

	def getCurrentSelection(self):
		return self.list and self.getCurrent() or None

	def listAll(self):
		self.l.setList(self.list)
		self.selectionEnabled(True)
