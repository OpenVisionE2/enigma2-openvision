# -*- coding: utf-8 -*-
import threading
from os import listdir, mkdir, remove, walk
from os.path import basename, dirname, exists, join
import re
import shutil
import tempfile
from json import loads
from enigma import eDVBDB, eEPGCache
from Screens.MessageBox import MessageBox
from Components.config import config
from Tools.Notifications import AddNotificationWithID
from time import sleep
from Tools.PyVerHelper import getPyVS
if getPyVS() >= 3:
	from base64 import encodebytes
	encodecommand = encodebytes
else: # Python 2
	from base64 import encodestring
	encodecommand = encodestring
from six.moves.urllib.error import URLError, HTTPError
from six.moves.urllib.parse import quote
from six.moves.urllib.request import Request, urlopen
import xml.etree.ElementTree as et

supportfiles = ('lamedb', 'blacklist', 'whitelist', 'alternatives.')
channelslistpath = "/etc/enigma2"
channelsepg = False


class ImportChannels():
	DIR_ENIGMA2 = "/etc/enigma2/"
	DIR_HDD = "/media/hdd/"
	DIR_TMP = "/tmp/"

	def __init__(self):
		if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_import.value and config.usage.remote_fallback.value and not "ChannelsImport" in [x.name for x in threading.enumerate()]:
			self.header = None
			if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_import.value and config.usage.remote_fallback_import_url.value != "same" and config.usage.remote_fallback_import_url.value:
				self.url = config.usage.remote_fallback_import_url.value.rsplit(":", 1)[0]
			else:
				self.url = config.usage.remote_fallback.value.rsplit(":", 1)[0]
			if config.usage.remote_fallback_openwebif_customize.value:
				self.url = "%s:%s" % (self.url, config.usage.remote_fallback_openwebif_port.value)
				if config.usage.remote_fallback_openwebif_userid.value and config.usage.remote_fallback_openwebif_password.value:
					self.header = "Basic %s" % encodecommand(("%s:%s" % (config.usage.remote_fallback_openwebif_userid.value, config.usage.remote_fallback_openwebif_password.value)).encode("UTF-8")).strip()
			self.remote_fallback_import = config.usage.remote_fallback_import.value
			self.thread = threading.Thread(target=self.threaded_function, name="ChannelsImport")
			self.thread.start()

	def getUrl(self, url, timeout=5):
		request = Request(url)
		if self.header:
			request.add_header("Authorization", self.header)
		try:
			result = urlopen(request, timeout=timeout)
		except URLError as err:
			if "[Errno -3]" in str(err):
				print("[ImportChannels] Network is not up yet, delay 5 seconds")
				# network not up yet
				sleep(5)
				return self.getUrl(url, timeout)
			print("[ImportChannels]", err)
			raise (err)
		return result

	def getFallbackSettings(self):
		try:
			return self.getUrl(self.url + "/api/settings")
		except HTTPError as err:
			self.ImportChannelsNotDone(True, "%s" % err)
			return

	def getFallbackSettingsValue(self, settings, e2settingname):
		if isinstance(settings, bytes):
			root = et.fromstring(settings)
			for e2setting in root:
				if e2settingname in e2setting[0].text:
					return e2setting[1].text
			return ""

	def getTerrestrialRegion(self, settings):
		if settings:
			description = ""
			descr = self.getFallbackSettingsValue(settings, ".terrestrial")
			if descr and "Europe" in descr:
				description = "fallback DVB-T/T2 Europe"
			if descr and "Australia" in descr:
				description = "fallback DVB-T/T2 Australia"
			config.usage.remote_fallback_dvbt_region.value = description

	def getRemoteAddress(self):
		if config.clientmode.serverAddressType.value == "ip":
			return '%d.%d.%d.%d' % (config.clientmode.serverIP.value[0], config.clientmode.serverIP.value[1], config.clientmode.serverIP.value[2], config.clientmode.serverIP.value[3])
		else:
			return config.clientmode.serverDomain.value

	def downloadEPG(self):
		print("[ImportChannels] downloadEPG Force EPG save on remote receiver...")
		self.forceSaveEPGonRemoteReceiver()
		print("[ImportChannels] downloadEPG Searching for epg.dat...")
		result = self.FTPdownloadFile(self.DIR_ENIGMA2, "settings", "settings")
		if result:
			self.checkEPGCallback()
		else:
			self.ImportChannelsNotDone(True, _("EPG and Channels not received receiver %s is turned off") % self.url)

	def forceSaveEPGonRemoteReceiver(self):
		url = "%s/api/saveepg" % self.url
		print('[ImportChannels] saveEPGonRemoteReceiver URL: %s' % url)
		try:
			req = Request(url)
			response = urlopen(req)
			print('[ImportChannels] saveEPGonRemoteReceiver Response: %d, %s' % (response.getcode(), response.read().strip().replace("\r", "").replace("\n", "")))
		except HTTPError as err:
			print('[ImportChannels] saveEPGonRemoteReceiver ERROR: %s', err)
		except URLError as err:
			print('[ImportChannels] saveEPGonRemoteReceiver ERROR: %s', err)
		except:
			print('[ImportChannels] saveEPGonRemoteReceiver undefined error')

	def FTPdownloadFile(self, sourcefolder, sourcefile, destfile):
		print("[ImportChannels] Downloading remote file '%s'" % sourcefile)
		try:
			from ftplib import FTP
			ftp = FTP()
			ftp.set_pasv(config.clientmode.passive.value)
			ftp.connect(host=self.getRemoteAddress(), port=config.clientmode.serverFTPPort.value, timeout=5)
			ftp.login(user=config.clientmode.serverFTPusername.value, passwd=config.clientmode.serverFTPpassword.value)
			ftp.cwd(sourcefolder)
			with open(self.DIR_TMP + destfile, 'wb') as f:
				result = ftp.retrbinary('RETR %s' % sourcefile, f.write)
				ftp.quit()
				f.close()
				if result.startswith("226"):
					return True
			return False
		except Exception as err:
			print("[ImportChannels] FTPdownloadFile Error:", err)
			return False

	def removeFiles(self, targetdir, target):
		targetLen = len(target)
		for root, dirs, files in walk(targetdir):
			for name in files:
				if target in name[:targetLen]:
					remove(join(root, name))

	def checkEPGCallback(self):
		try:
			self.remoteEPGpath = self.DIR_ENIGMA2
			self.remoteEPGfile = "epg"
			self.remoteEPGfile = "%s.dat" % self.remoteEPGfile.replace('.dat', '')
			print("[ImportChannels] Remote EPG filename. '%s%s'" % (self.remoteEPGpath, self.remoteEPGfile))
			result = self.FTPdownloadFile(self.remoteEPGpath, self.remoteEPGfile, "epg.dat")
			if result:
				self.importEPGCallback()
			else:
				print("[ImportChannels] Remote EPG filename not path in internal flash")
		except Exception as err:
			print("[ImportChannels] cannot save EPG %s" % err)
		try:
			self.remoteEPGpath = self.DIR_HDD
			self.remoteEPGfile = "epg"
			self.remoteEPGfile = "%s.dat" % self.remoteEPGfile.replace('.dat', '')
			print("[ImportChannels] Remote EPG filename. '%s%s'" % (self.remoteEPGpath, self.remoteEPGfile))
			result = self.FTPdownloadFile(self.remoteEPGpath, self.remoteEPGfile, "epg.dat")
			if result:
				self.importEPGCallback()
			else:
				print("[ImportChannels] Remote EPG filename not path in HDD")
		except Exception as err:
			print("[ImportChannels] cannot save EPG %s" % err)

	def importEPGCallback(self):
		print("[ImportChannels] importEPGCallback '%s%s' downloaded successfully from server." % (self.remoteEPGpath, self.remoteEPGfile))
		print("[ImportChannels] importEPGCallback Removing current EPG data...")
		try:
			remove(config.misc.epgcache_filename.value)
		except OSError:
			pass
		shutil.move(self.DIR_TMP + "epg.dat", config.misc.epgcache_filename.value)
		self.removeFiles(self.DIR_TMP, "epg.dat")
		eEPGCache.getInstance().load()
		print("[ImportChannels] importEPGCallback New EPG data loaded...")
		print("[ImportChannels] importEPGCallback Closing importer.")
		self.ImportChannelsDone(True, _("EPG imported successfully from %s") % self.url)

	def threaded_function(self):
		settings = self.getFallbackSettings()
		self.getTerrestrialRegion(settings)
		self.tmp_dir = tempfile.mkdtemp(prefix="ImportChannels_")
		if "epg" in self.remote_fallback_import and not config.clientmode.enabled.value:
			if config.usage.remote_fallback_import_restart.value or config.usage.remote_fallback_import_standby.value:
				config.clientmode_notifications_ok.value = False
				print("[ImportChannels] Starting to load epg.dat files and channels from server box")
				try:
					urlopen(self.url + "/api/saveepg")
				except Exception as err:
					print("[ImportChannels] %s" % err)
					self.ImportChannelsNotDone(True, _("Server not available"))
					return AddNotificationWithID("ChannelsImportNOK", MessageBox, _("Set new value to \"Fallback remote receiver\" change URL %s") % self.url, type=MessageBox.TYPE_ERROR, timeout=10)
				print("[ImportChannels] Get EPG Location")
				if "channels_epg" in self.remote_fallback_import:
					self.importChannelsCallback()
				try:
					searchPaths = ("/etc/enigma2/", "/media/hdd/")
					for epg in searchPaths:
						epgdatfile = join(epg, "epg.dat")
						files = [file for file in loads(urlopen("%s/file?dir=%s" % (self.url, dirname(epgdatfile)), timeout=5).read())["files"] if basename(file).startswith("epg.dat")]
						epg_location = files[0] if files else None
						if epg_location:
							print("[ImportChannels] Copy EPG file...")
							try:
								try:
									mkdir("/tmp/epgdat")
								except:
									print("[ImportChannels] epgdat folder exists in tmp")
								epgdattmp = "/tmp/epgdat"
								epgdatserver = "/tmp/epgdat/epg.dat"
								open("%s/%s" % (epgdattmp, basename(epg_location)), "wb").write(urlopen("%s/file?file=%s" % (self.url, epg_location), timeout=5).read())
								if "epg.dat" in epgdatserver:
									shutil.move("%s" % epgdatserver, "%s" % (config.misc.epgcache_filename.value))
									eEPGCache.getInstance().load()
									shutil.rmtree(epgdattmp)
									self.ImportChannelsDone(True, _("EPG imported successfully from %s") % self.url)
							except Exception as err:
								print("[ImportChannels] cannot save EPG %s" % err)
				except Exception as err:
					print("[ImportChannels] %s" % err)
					return self.downloadEPG(), self.importChannelsCallback() if "channels_epg" in self.remote_fallback_import else None
		return self.importChannelsCallback()

	def ImportGetFilelist(self, remote=False, *files):
		result = []
		for file in files:
			# determine the type of bouquet file
			type = 1 if file.endswith('.tv') else 2
			# read the contents of the file
			try:
				if remote:
					try:
						content = self.getUrl("%s/file?file=%s/%s" % (self.url, channelslistpath, quote(file))).readlines()
						content = map(lambda l: l.decode('utf-8', 'replace'), content) if getPyVS() >= 3 else content
					except Exception as err:
						print("[ImportChannels] Exception: %s" % str(err))
						self.ImportChannelsNotDone(True, _("%s\nRead failled %s/%s from %s") % (err, channelslistpath, file, self.url))
						return
				else:
					with open('%s/%s' % (channelslistpath, file), 'r') as f:
						content = f.readlines()
			except Exception as e:
				# for the moment just log and ignore
				print("[ImportChannels] %s" % str(e))
				continue

			# check the contents for more bouquet files
			for line in content:
#				print ("[ImportChannels] %s" % line)
				# check if it contains another bouquet reference
				r = re.match('#SERVICE 1:7:%d:0:0:0:0:0:0:0:FROM BOUQUET "(.*)" ORDER BY bouquet' % type, line)
				if r:
					# recurse
					result.extend(self.ImportGetFilelist(remote, r.group(1)))

			# add add the file itself
			result.append(file)

		# return the file list
		return result

	def importChannelsCallback(self):
		global channelsepg
		if "channels_epg" in self.remote_fallback_import:
			config.usage.remote_fallback_import.value = "channels"
			config.usage.remote_fallback_import.save()
			channelsepg = True
		if "channels" in self.remote_fallback_import:
			print("[ImportChannels] Enumerate remote files")
			files = self.ImportGetFilelist(True, 'bouquets.tv', 'bouquets.radio')

			print("[ImportChannels] Enumerate remote support files")
			for file in loads(self.getUrl("%s/file?dir=%s" % (self.url, channelslistpath)).read())["files"]:
				if basename(file).startswith(supportfiles):
					files.append(file.replace(channelslistpath, ''))

			print("[ImportChannels] Fetch remote files")
			for file in files:
				if exists(file):
					print("[ImportChannels] Downloading %s..." % file)
				try:
					open(join(self.tmp_dir, basename(file)), "wb").write(self.getUrl("%s/file?file=%s/%s" % (self.url, channelslistpath, quote(file))).read())
				except Exception as err:
					if not "epg" in self.remote_fallback_import:
						self.ImportChannelsNotDone(True, _("%s\nFailed to download %s/%s from %s") % (err, channelslistpath, file, self.url))
					if channelsepg:
						config.usage.remote_fallback_import.value = "channels_epg"
						config.usage.remote_fallback_import.save()
					return

			print("[ImportChannels] Enumerate local files")
			files = self.ImportGetFilelist(False, 'bouquets.tv', 'bouquets.radio')
			print("[ImportChannels] Removing files...")
			for file in files:
				if exists(join(channelslistpath, file)):
					remove(join(channelslistpath, file))
			print("[ImportChannels] Updating files...")
			files = [x for x in listdir(self.tmp_dir)]
			for file in files:
				print("- Moving %s..." % file)
				shutil.move(join(self.tmp_dir, file), join(channelslistpath, file))
			from Screens.InfoBar import InfoBar
			from Screens.ClientMode import ClientModeScreen
			eDVBDB.getInstance().reloadBouquets()
			eDVBDB.getInstance().reloadServicelist()
			InfoBar.instance.servicelist.showFavourites()
			self.ImportChannelsDone(True, _("Channels imported successfully from %s") % self.url)
			if not files and not config.clientmode.enabled.value and not "0.0.0.0" in ClientModeScreen.getRemoteAddress(self):
				from Components.ChannelsImporter import ChannelsImporter  # resource to import channels from ChannelsImporter
				ChannelsImporter()

	def ImportChannelsDone(self, flag, message=None):
		if hasattr(self, "tmp_dir") and exists(self.tmp_dir):
			shutil.rmtree(self.tmp_dir, True)
		if config.usage.remote_fallback_ok.value:
			AddNotificationWithID("ChannelsImportOK", MessageBox, _("%s") % message, type=MessageBox.TYPE_INFO, timeout=5)

	def ImportChannelsNotDone(self, flag, message=None):
		if hasattr(self, "tmp_dir") and exists(self.tmp_dir):
			shutil.rmtree(self.tmp_dir, True)
		if config.usage.remote_fallback_nok.value:
			AddNotificationWithID("ChannelsImportNOK", MessageBox, _("%s") % message, type=MessageBox.TYPE_ERROR, timeout=5)
