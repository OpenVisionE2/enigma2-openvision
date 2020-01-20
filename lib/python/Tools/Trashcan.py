from __future__ import print_function
import time
import os
import enigma
from Components.config import config
from Components import Harddisk
from twisted.internet import threads
from Components.GUIComponent import GUIComponent
from Components.VariableText import VariableText
import Components.Task

def getTrashFolder(path=None):
	# Returns trash folder without symlinks
	try:
		if path is None or os.path.realpath(path) == '/media/autofs':
			print('[Trashcan] path is none')
			return ""
		else:
			trashcan = Harddisk.findMountPoint(os.path.realpath(path))
			if '/movie' in path:
				trashcan = os.path.join(trashcan, 'movie')
			elif config.usage.default_path.value in path:
				# if default_path happens to not be the default /hdd/media/movie, then we can have a trash folder there instead
				trashcan = os.path.join(trashcan, config.usage.default_path.value)
			return os.path.realpath(os.path.join(trashcan, ".Trash"))
	except:
		return None

def createTrashFolder(path=None):
	print('[Trashcan]] DeBug path', path)
	trash = getTrashFolder(path)
	print('[Trashcan] DeBug', trash)
	if trash and os.access(os.path.split(trash)[0], os.W_OK):
		if not os.path.isdir(trash):
			try:
				os.mkdir(trash)
			except:
				return None
		return trash
	else:
		return None

def get_size(start_path = '.'):
	total_size = 0
	if start_path:
		for dirpath, dirnames, filenames in os.walk(start_path):
			for f in filenames:
				try:
					fp = os.path.join(dirpath, f)
					total_size += os.path.getsize(fp)
				except:
					pass
	return total_size

def enumTrashFolders():
	# Walk through all Trash folders. This may access network
	# drives and similar, so might block for minutes.
	for mount in Harddisk.getProcMounts():
		if mount[1].startswith('/media/'):
			mountpoint = mount[1]
			movie = os.path.join(mountpoint, 'movie')
			if os.path.isdir(movie):
				mountpoint = movie
			result = os.path.join(mountpoint, ".Trash")
			if os.path.isdir(result):
				yield result

class Trashcan:
	def __init__(self, session):
		self.session = session
		self.isCleaning = False
		self.session = None
		self.dirty = set()

	def init(self, session):
		self.session = session
		session.nav.record_event.append(self.gotRecordEvent)

	def markDirty(self, path):
		# Marks a path for purging, for when a recording on that
		# device starts or ends.
		if not path:
			return
		trash = getTrashFolder(path)
		self.dirty.add(trash)

	def gotRecordEvent(self, service, event):
		from RecordTimer import n_recordings
		if event == enigma.iRecordableService.evEnd:
			self.cleanIfIdle()

	def destroy(self):
		if self.session is not None:
			self.session.nav.record_event.remove(self.gotRecordEvent)
		self.session = None

	def __del__(self):
		self.destroy()

	def cleanIfIdle(self, path=None):
		# RecordTimer calls this when preparing a recording. That is a
		# nice moment to clean up. It also mentions the path, so mark
		# it as dirty.
		from RecordTimer import n_recordings
		if n_recordings > 0:
			print("[Trashcan] Recording(s) in progress:", n_recordings)
			return
		self.markDirty(path)
		if not self.dirty:
			return
		if self.isCleaning:
			print("[Trashcan] Cleanup already running")
			return
		if (self.session is not None) and self.session.nav.getRecordings():
			return
		self.isCleaning = True
		ctimeLimit = time.time() - (config.usage.movielist_trashcan_days.value * 3600 * 24)
		reserveBytes = 1024*1024*1024 * int(config.usage.movielist_trashcan_reserve.value)
		cleanset = self.dirty
		self.dirty = set()
		threads.deferToThread(purge, cleanset, ctimeLimit, reserveBytes).addCallbacks(self.cleanReady, self.cleanFail)

	def cleanReady(self, result=None):
		self.isCleaning = False
		# schedule another clean loop if needed (so we clean up all devices, not just one)
		self.cleanIfIdle()

	def cleanFail(self, failure):
		print("[Trashcan] ERROR in clean:", failure)
		self.isCleaning = False

def purge(cleanset, ctimeLimit, reserveBytes):
	# Remove expired items from trash, and attempt to have
	# reserveBytes of free disk space.
	for trash in cleanset:
		if not os.path.isdir(trash):
			print("[Trashcan] No trash.", trash)
			return 0
		diskstat = os.statvfs(trash)
		free = diskstat.f_bfree * diskstat.f_bsize
		bytesToRemove = reserveBytes - free
		candidates = []
		print("[Trashcan] bytesToRemove", bytesToRemove, trash)
		size = 0
		for root, dirs, files in os.walk(trash, topdown=False):
			for name in files:
				try:
					fn = os.path.join(root, name)
					st = os.stat(fn)
					if st.st_ctime < ctimeLimit:
						print("[Trashcan] Too old:", name, st.st_ctime)
						enigma.eBackgroundFileEraser.getInstance().erase(fn)
						bytesToRemove -= st.st_size
					else:
						candidates.append((st.st_ctime, fn, st.st_size))
						size += st.st_size
				except Exception as e:
					print("[Trashcan] Failed to stat %s:"% name, e)
			# Remove empty directories if possible
			for name in dirs:
				try:
					os.rmdir(os.path.join(root, name))
				except:
					pass
		candidates.sort()
		# Now we have a list of ctime, candidates, size. Sorted by ctime (=deletion time)
		print("[Trashcan] Bytes to remove remaining:", bytesToRemove, trash)
		for st_ctime, fn, st_size in candidates:
			if bytesToRemove < 0:
				break
			enigma.eBackgroundFileEraser.getInstance().erase(fn)
			bytesToRemove -= st_size
			size -= st_size
		print("[Trashcan] Size after purging:", size, trash)

def cleanAll(trash):
	if not os.path.isdir(trash):
		print("[Trashcan] No trash.", trash)
		return 0
	for root, dirs, files in os.walk(trash, topdown=False):
		for name in files:
			fn = os.path.join(root, name)
			try:
				enigma.eBackgroundFileEraser.getInstance().erase(fn)
			except Exception as e:
				print("[Trashcan] Failed to erase %s:"% name, e)
		# Remove empty directories if possible
		for name in dirs:
			try:
				os.rmdir(os.path.join(root, name))
			except:
				pass

def init(session):
	global instance
	instance = Trashcan(session)

class CleanTrashTask(Components.Task.PythonTask):
	def openFiles(self, ctimeLimit, reserveBytes):
		self.ctimeLimit = ctimeLimit
		self.reserveBytes = reserveBytes

	def work(self):
		mounts=[]
		matches = []
		print("[Trashcan] probing folders")
		f = open('/proc/mounts', 'r')
		for line in f.readlines():
			parts = line.strip().split()
			if parts[1] == '/media/autofs':
				continue
			if config.usage.movielist_trashcan_network_clean.value and parts[1].startswith('/media/net'):
				mounts.append(parts[1])
			elif config.usage.movielist_trashcan_network_clean.value and parts[1].startswith('/media/autofs'):
				mounts.append(parts[1])
			elif not parts[1].startswith('/media/net') and not parts[1].startswith('/media/autofs'):
				mounts.append(parts[1])
		f.close()

		for mount in mounts:
			if os.path.isdir(os.path.join(mount,'.Trash')):
				matches.append(os.path.join(mount,'.Trash'))
			if os.path.isdir(os.path.join(mount,'movie/.Trash')):
				matches.append(os.path.join(mount,'movie/.Trash'))

		print("[Trashcan] found following trashcan's:",matches)
		if len(matches):
			for trashfolder in matches:
				print("[Trashcan] looking in trashcan",trashfolder)
				trashsize = get_size(trashfolder)
				diskstat = os.statvfs(trashfolder)
				free = diskstat.f_bfree * diskstat.f_bsize
				bytesToRemove = self.reserveBytes - free
				print("[Trashcan] " + str(trashfolder) + ": Size:",trashsize)
				candidates = []
				size = 0
				for root, dirs, files in os.walk(trashfolder, topdown=False):
					for name in files:
# Don't delete any per-directory config files from .Trash if the option is in use
						if (config.movielist.settings_per_directory.value and name == ".e2settings.pkl"):
							continue
						try:
							fn = os.path.join(root, name)
							st = os.stat(fn)
							if st.st_ctime < self.ctimeLimit:
								enigma.eBackgroundFileEraser.getInstance().erase(fn)
								bytesToRemove -= st.st_size
							else:
								candidates.append((st.st_ctime, fn, st.st_size))
								size += st.st_size
						except Exception as e:
							print("[Trashcan] Failed to stat %s:"% name, e)
					# Remove empty directories if possible
					for name in dirs:
						try:
							os.rmdir(os.path.join(root, name))
						except:
							pass
					candidates.sort()
					# Now we have a list of ctime, candidates, size. Sorted by ctime (=deletion time)
					for st_ctime, fn, st_size in candidates:
						if bytesToRemove < 0:
							break
						try:
							# somtimes the file does not exist, can happen if trashcan is on a network, the main box could also be emptying trash at same time.
							enigma.eBackgroundFileEraser.getInstance().erase(fn)
						except:
							pass
						bytesToRemove -= st_size
						size -= st_size
					print("[Trashcan] " + str(trashfolder) + ": Size now:",size)

class TrashInfo(VariableText, GUIComponent):
	FREE = 0
	USED = 1
	SIZE = 2

	def __init__(self, path, type, update = True):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.type = type
		if update and path != '/media/autofs/':
			self.update(path)

	def update(self, path):
		try:
			total_size = get_size(getTrashFolder(path))
		except OSError:
			return -1

		if self.type == self.USED:
			try:
				if total_size < 10000000:
					total_size = _("%d KB") % (total_size >> 10)
				elif total_size < 10000000000:
					total_size = _("%d MB") % (total_size >> 20)
				else:
					total_size = _("%d GB") % (total_size >> 30)
				self.setText(_("Trashcan:") + " " + total_size)
			except:
				# occurs when f_blocks is 0 or a similar error
				self.setText("-?-")

	GUI_WIDGET = enigma.eLabel
