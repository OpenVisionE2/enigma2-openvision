from xml.etree.cElementTree import ParseError, parse

from Components.config import ConfigInteger, config
from Components.Pixmap import MovingPixmap, MultiPixmap
from Components.SystemInfo import SystemInfo

config.misc.rcused = ConfigInteger(default=1)


class Rc:
	def __init__(self):
		self["rc"] = MultiPixmap()
		nSelectPics = 16
		rcHeights = (500,) * 2
		self.selectPics = []
		for indicator in range(nSelectPics):
			self.selectPics.append(self.KeyIndicator(self, rcHeights, ("indicatorU%d" % indicator, "indicatorL%d" % indicator)))
		self.rcPositions = RcPositions()
		self.oldNSelectedKeys = self.nSelectedKeys = 0
		self.clearSelectedKeys()
		self.onLayoutFinish.append(self.initRc)
		# self.onExecBegin.append(self.testIndicators)  # Test code to visit every button in turn.

	class KeyIndicator:

		class KeyIndicatorPixmap(MovingPixmap):
			def __init__(self, activeYPos, pixmap):
				MovingPixmap.__init__(self)
				self.activeYPos = activeYPos
				self.pixmapName = pixmap

		def __init__(self, owner, activeYPos, pixmaps):
			self.pixmaps = []
			for actYpos, pixmap in zip(activeYPos, pixmaps):
				pm = self.KeyIndicatorPixmap(actYpos, pixmap)
				# print("[Rc] KeyIndicator DEBUG: actPos='%s', pixmap='%s'." % (actYpos, pixmap))
				owner[pixmap] = pm
				self.pixmaps.append(pm)
			self.pixmaps.sort(key=lambda x: x.activeYPos)

		def slideTime(self, frm, to, time=20):
			if not self.pixmaps:
				return time
			dist = ((to[0] - frm[0]) ** 2 + (to[1] - frm[1]) ** 2) ** 0.5
			slide = int(round(dist / self.pixmaps[-1].activeYPos * time))
			return slide if slide > 0 else 1

		def moveTo(self, pos, rcPos, moveFrom=None, time=20):
			foundActive = False
			for index, pixmap in enumerate(self.pixmaps):
				fromX, fromY = pixmap.getPosition()
				if moveFrom:
					fromX, fromY = moveFrom.pixmaps[index].getPosition()
				x = pos[0] + rcPos[0]
				y = pos[1] + rcPos[1]
				if pos[1] <= pixmap.activeYPos and not foundActive:
					pixmap.move(fromX, fromY)
					pixmap.moveTo(x, y, self.slideTime((fromX, fromY), (x, y), time))
					pixmap.show()
					pixmap.startMoving()
					foundActive = True
				else:
					pixmap.move(x, y)

		def hide(self):
			for pixmap in self.pixmaps:
				pixmap.hide()

	def initRc(self):
		# if self.isDefaultRc:
		# 	self["rc"].setPixmapNum(config.misc.rcused.value)
		# else:
		# 	self["rc"].setPixmapNum(0)
		self["rc"].setPixmapNum(0)
		rcHeight = self["rc"].getSize()[1]
		for selectPic in self.selectPics:
			nBreaks = len(selectPic.pixmaps)
			roundup = nBreaks - 1
			n = 1
			# print("[Rc] KeyIndicator DEBUG: nBreaks=%d, roundup=%d." % (nBreaks, roundup))
			for pic in selectPic.pixmaps:
				pic.activeYPos = (rcHeight * n + roundup) / nBreaks
				n += 1
				# print("[Rc] KeyIndicator DEBUG: n=%d, activeYPos=%d." % (n, pic.activeYPos))

	def getRcPositions(self):
		return self.rcPositions

	def hideRc(self):
		self["rc"].hide()
		self.hideSelectPics()

	def showRc(self):
		self["rc"].show()

	def selectKey(self, key):
		pos = self.rcPositions.getRcKeyPos(key)
		if pos and self.nSelectedKeys < len(self.selectPics):
			rcPos = self["rc"].getPosition()
			selectPic = self.selectPics[self.nSelectedKeys]
			self.nSelectedKeys += 1
			if self.oldNSelectedKeys > 0 and self.nSelectedKeys > self.oldNSelectedKeys:
				selectPic.moveTo(pos, rcPos, moveFrom=self.selectPics[self.oldNSelectedKeys - 1], time=int(config.usage.help_animspeed.value))
			else:
				selectPic.moveTo(pos, rcPos, time=int(config.usage.help_animspeed.value))

	def clearSelectedKeys(self):
		self.showRc()
		self.oldNSelectedKeys = self.nSelectedKeys
		self.nSelectedKeys = 0
		self.hideSelectPics()

	def hideSelectPics(self):
		for selectPic in self.selectPics:
			selectPic.hide()

	# Visits all the buttons in turn, sliding between them.  Leaves the
	# indicator at the incorrect position at the end of the test run.
	# Change to another entry in the help list to get the indicator in
	# the correct position.
	#
	# def testIndicators(self):
	# 	if not self.selectPics or not self.selectPics[0].pixmaps:
	# 		return
	# 	self.hideSelectPics()
	# 	pixmap = self.selectPics[0].pixmaps[0]
	# 	pixmap.show()
	# 	rcPos = self["rc"].getPosition()
	# 	for key in self.rcPositions.getRcKeyList():
	# 		pos = self.rcPositions.getRcKeyPos(key)
	# 		pixmap.addMovePoint(rcPos[0] + pos[0], rcPos[1] + pos[1], time=5)
	# 		pixmap.addMovePoint(rcPos[0] + pos[0], rcPos[1] + pos[1], time=10)
	# 	pixmap.startMoving()


class RcPositions:
	def __init__(self):
		remoteFile = SystemInfo["RCMapping"]
		self.rcs = {}
		self.rc = {"names": [], "keypos": {}}
		try:
			with open(remoteFile, "r") as fd:  # This open gets around a possible file handle leak in Python's XML parser.
				try:
					rcs = parse(fd).getroot()
					for rc in rcs:
						id = int(rc.attrib["id"])
						self.rcs[id] = {"names": [], "keypos": {}}
						for key in rc:
							name = key.attrib["name"]
							pos = key.attrib["pos"].split(",")
							self.rcs[id]["keypos"][name] = (int(pos[0]), int(pos[1]))
							self.rcs[id]["names"].append(name)
					self.rc = self.rcs[SystemInfo["RCTypeIndex"]]
				except ParseError as err:
					fd.seek(0)
					content = fd.readlines()
					line, column = err.position
					print("[Rc] XML Parse Error: '%s' in '%s'!" % (err, remoteFile))
					data = content[line - 1].replace("\t", " ").rstrip()
					print("[Rc] XML Parse Error: '%s'" % data)
					print("[Rc] XML Parse Error: '%s^%s'" % ("-" * column, " " * (len(data) - column - 1)))
				except Exception as err:
					print("[Rc] Error: Unable to parse remote control mapping data in '%s' - '%s'!" % (remoteFile, err))
		except (IOError, OSError) as err:
			print("[Rc] Error %d: Opening remote control mapping file '%s'! (%s)" % (err.errno, remoteFile, err.strerror))
		except Exception as err:
			print("[Rc] Error %d: Unexpected error opening remote control mapping file '%s'! (%s)" % (err.errno, remoteFile, err.strerror))

	def getRc(self):
		return self.rc

	def getRcKeyPos(self, key):
		return self.rc["keypos"].get(key)

	def getRcKeyList(self):
		return self.rc["names"]
