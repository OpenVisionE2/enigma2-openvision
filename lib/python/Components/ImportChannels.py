from __future__ import print_function
import threading
import os
import re
import shutil
import tempfile
from json import loads
from enigma import eDVBDB, eEPGCache
from Screens.MessageBox import MessageBox
from Components.config import config, ConfigText
from Tools.Notifications import AddNotificationWithID
from time import sleep
from sys import version_info
from six.moves.urllib.error import URLError, HTTPError
from six.moves.urllib.parse import quote
from six.moves.urllib.request import Request, urlopen
import xml.etree.ElementTree as et
if version_info.major >= 3:
	from base64 import encodebytes
	encodecommand = encodebytes
else: # Python 2
	from base64 import encodestring
	encodecommand = encodestring

supportfiles = ('lamedb', 'blacklist', 'whitelist', 'alternatives.')

channelslistpath = "/etc/enigma2"


class ImportChannels():
	DIR_ENIGMA2 = "/etc/enigma2/"
	DIR_HDD = "/media/hdd/"
	DIR_USB = "/media/usb/"
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
			print("[ImportChannels] %s" % err)
			if "[Errno -3]" in str(err.reason):
				try:
					print("[ImportChannels] Network is not up yet, delay 5 seconds")
					# network not up yet
					sleep(5)
					return self.getUrl(url, timeout)
				except URLError as err:
					print("[ImportChannels] %s" % err)
				return result

	def getTerrestrialUrl(self):
		url = config.usage.remote_fallback_dvb_t.value
		return url[:url.rfind(":")] if url else self.url

	def getFallbackSettings(self):
		if not URLError:  # currently disabled, we get syntax errors when we try to load settings from the server.
			return (str(self.getUrl("%s/web/settings" % self.getTerrestrialUrl())))

	def getFallbackSettingsValue(self, settings, e2settingname):
		if settings:
			root = et.fromstring(settings)
			for e2setting in root:
				if e2settingname in e2setting[0].text:
					return e2setting[1].text
			return ""

	def getTerrestrialRegion(self, settings):
		if settings:
			description = ""
			descr = self.getFallbackSettingsValue(settings, ".terrestrial")
			if "Europe" in descr:
				description = "fallback DVB-T/T2 Europe"
			if "Australia" in descr:
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
			AddNotificationWithID("ChannelsImportNOK", MessageBox, _("EPG and Channels not received receiver %s is turned off") % self.url, type=MessageBox.TYPE_ERROR, timeout=10) if config.usage.remote_fallback_nok.value else None

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
		for root, dirs, files in os.walk(targetdir):
			for name in files:
				if target in name[:targetLen]:
					os.remove(os.path.join(root, name))

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
		try:
			self.remoteEPGpath = self.DIR_USB
			self.remoteEPGfile = "epg"
			self.remoteEPGfile = "%s.dat" % self.remoteEPGfile.replace('.dat', '')
			print("[ImportChannels] Remote EPG filename. '%s%s'" % (self.remoteEPGpath, self.remoteEPGfile))
			result = self.FTPdownloadFile(self.remoteEPGpath, self.remoteEPGfile, "epg.dat")
			if result:
				self.importEPGCallback()
			else:
				print("[ImportChannels] Remote EPG filename not path in USB")
		except Exception as err:
			print("[ImportChannels] cannot save EPG %s" % err)

	def importEPGCallback(self):
		print("[ImportChannels] importEPGCallback '%s%s' downloaded successfully from server." % (self.remoteEPGpath, self.remoteEPGfile))
		print("[ImportChannels] importEPGCallback Removing current EPG data...")
		try:
			os.remove(config.misc.epgcache_filename.value)
		except OSError:
			pass
		shutil.move(self.DIR_TMP + "epg.dat", config.misc.epgcache_filename.value)
		self.removeFiles(self.DIR_TMP, "epg.dat")
		eEPGCache.getInstance().load()
		print("[ImportChannels] importEPGCallback New EPG data loaded...")
		print("[ImportChannels] importEPGCallback Closing importer.")
		self.ImportChannelsDone(False, _("EPG imported successfully from %s") % self.url) if config.usage.remote_fallback_ok.value else None

	def threaded_function(self):
		settings = self.getFallbackSettings()
		self.getTerrestrialRegion(settings)
		self.tmp_dir = tempfile.mkdtemp(prefix="ImportChannels_")

		if "epg" in self.remote_fallback_import and not config.clientmode.enabled.value or "channels_epg" in self.remote_fallback_import and not config.clientmode.enabled.value:
			config.clientmode_notifications_ok.value = False
			print("[ImportChannels] Starting to load epg.dat files and channels from server box")
			try:
				self.getUrl("%s/web/saveepg" % self.url, timeout=5)
			except Exception as err:
				print("[ImportChannels] %s" % err)
				return self.ImportChannelsDone(False, _("Server not available")) if config.usage.remote_fallback_nok.value else None
			print("[ImportChannels] Get EPG Location")
			try:
				epgdatfile = "/etc/enigma2/epg.dat"
				files = [file for file in loads(urlopen("%s/file?dir=%s" % (self.url, os.path.dirname(epgdatfile)), timeout=5).read())["files"] if os.path.basename(file).startswith("epg.dat")]
				epg_location = files[0] if files else None
				if epg_location:
					print("[ImportChannels] Copy EPG file...")
					try:
						try:
							os.mkdir("/tmp/epgdat")
						except:
							print("[ImportChannels] epgdat folder exists in tmp")
						epgdattmp = "/tmp/epgdat"
						epgdatserver = "/tmp/epgdat/epg.dat"
						open("%s/%s" % (epgdattmp, os.path.basename(epg_location)), "wb").write(urlopen("%s/file?file=%s" % (self.url, epg_location), timeout=5).read())
						if "epg.dat" in (epgdatserver):
							shutil.move("%s" % epgdatserver, "%s" % (config.misc.epgcache_filename.value))
							eEPGCache.getInstance().load()
							shutil.rmtree(epgdattmp)
							self.ImportChannelsDone(False, _("EPG imported successfully from %s") % self.url) if config.usage.remote_fallback_ok.value else None
							return self.importChannelsCallback()
					except Exception as err:
						print("[ImportChannels] cannot save EPG %s" % err)
			except Exception as err:
				print("[ImportChannels] %s" % err)
				return self.downloadEPG(), self.importChannelsCallback()
			try:
				epgdatfile = "/media/hdd/epg.dat"
				files = [file for file in loads(urlopen("%s/file?dir=%s" % (self.url, os.path.dirname(epgdatfile)), timeout=5).read())["files"] if os.path.basename(file).startswith("epg.dat")]
				epg_location = files[0] if files else None
				if epg_location:
					print("[ImportChannels] Copy EPG file...")
					try:
						try:
							os.mkdir("/tmp/epgdat")
						except:
							print("[ImportChannels] epgdat folder exists in tmp")
						epgdattmp = "/tmp/epgdat"
						epgdatserver = "/tmp/epgdat/epg.dat"
						open("%s/%s" % (epgdattmp, os.path.basename(epg_location)), "wb").write(urlopen("%s/file?file=%s" % (self.url, epg_location), timeout=5).read())
						if "epg.dat" in (epgdatserver):
							shutil.move("%s" % epgdatserver, "%s" % (config.misc.epgcache_filename.value))
							eEPGCache.getInstance().load()
							shutil.rmtree(epgdattmp)
							self.ImportChannelsDone(False, _("EPG imported successfully from %s") % self.url) if config.usage.remote_fallback_ok.value else None
							return self.importChannelsCallback()
					except Exception as err:
						print("[ImportChannels] cannot save EPG %s" % err)
			except Exception as err:
				print("[ImportChannels] %s" % err)
				return self.downloadEPG(), self.importChannelsCallback()
			try:
				epgdatfile = "/media/usb/epg.dat"
				files = [file for file in loads(urlopen("%s/file?dir=%s" % (self.url, os.path.dirname(epgdatfile)), timeout=5).read())["files"] if os.path.basename(file).startswith("epg.dat")]
				epg_location = files[0] if files else None
				if epg_location:
					print("[ImportChannels] Copy EPG file...")
					try:
						try:
							os.mkdir("/tmp/epgdat")
						except:
							print("[ImportChannels] epgdat folder exists in tmp")
						epgdattmp = "/tmp/epgdat"
						epgdatserver = "/tmp/epgdat/epg.dat"
						open("%s/%s" % (epgdattmp, os.path.basename(epg_location)), "wb").write(urlopen("%s/file?file=%s" % (self.url, epg_location), timeout=5).read())
						if "epg.dat" in (epgdatserver):
							shutil.move("%s" % epgdatserver, "%s" % (config.misc.epgcache_filename.value))
							eEPGCache.getInstance().load()
							shutil.rmtree(epgdattmp)
							self.ImportChannelsDone(False, _("EPG imported successfully from %s") % self.url) if config.usage.remote_fallback_ok.value else None
							return self.importChannelsCallback()
					except Exception as err:
						print("[ImportChannels] cannot save EPG %s" % err)
			except Exception as err:
				print("[ImportChannels] %s" % err)
				return self.downloadEPG(), self.importChannelsCallback()
		return self.importChannelsCallback()

	def importChannelsCallback(self):
		if "channels" in self.remote_fallback_import:
			channelslist = ('lamedb', 'bouquets.', 'userbouquet.', 'blacklist', 'whitelist', 'alternatives.')
			try:
				try:
					os.mkdir("/tmp/channelslist")
				except:
					print("[ImportChannels] channelslist folder exists in tmp")
				channelslistserver = "/tmp/channelslist"
				files = [file for file in loads(urlopen("%s/file?dir=%s" % (self.url, channelslistpath), timeout=5).read())["files"] if os.path.basename(file).startswith(channelslist)]
				count = 0
				for file in files:
					count += 1
					file = file if version_info.major >= 3 else file.encode("UTF-8")
					print("[ImportChannels] Downloading %s" % file)
					try:
						open("%s/%s" % (channelslistserver, os.path.basename(file)), "wb").write(urlopen("%s/file?file=%s" % (self.url, file), timeout=5).read())
					except:
						return self.ImportChannelsDone(False, _("ERROR downloading file %s") % file) if config.usage.remote_fallback_nok.value else None
			except:
				try:
					ipServer = [int(x) for x in self.url.split(":")[1][2:].split(".")]
					config.clientmode.serverIP.value = ipServer
					config.clientmode.save()
				except:
					print("[ImportChannels] You need to configure IP in ClientMode, do it from ImportChannels setup")
					return AddNotificationWithID("ChannelsImportNOK", MessageBox, _("You have not set manual IP for %s") % self.url, type=MessageBox.TYPE_ERROR, timeout=10)

			print("[ImportChannels] Removing files...")
			files = [file for file in os.listdir("%s" % channelslistpath) if file.startswith(channelslist) and file.startswith(channelslistserver)]
			for file in files:
				os.remove("%s/%s" % (channelslistpath, file))
			print("[ImportChannels] copying files...")
			files = [x for x in os.listdir(channelslistserver) if x.startswith(channelslist)]
			for file in files:
				shutil.move("%s/%s" % (channelslistserver, file), "%s/%s" % (channelslistpath, file))
			shutil.rmtree(channelslistserver)
			eDVBDB.getInstance().reloadBouquets()
			eDVBDB.getInstance().reloadServicelist()
			from Components.ChannelsImporter import ChannelsImporter
			self.ImportChannelsDone(False, _("Channels imported successfully from %s") % self.url) if config.usage.remote_fallback_ok.value and files else None
			ChannelsImporter() if not config.clientmode.enabled.value and not files else None
		#self.ImportChannelsDone(True, {"channels": _("Channels"), "epg": _("EPG"), "channels_epg": _("Channels and EPG")}[self.remote_fallback_import])

	def ImportChannelsDone(self, flag, message=None):
		shutil.rmtree(self.tmp_dir, True)
		if config.usage.remote_fallback_ok.value:
			AddNotificationWithID("ChannelsImportOK", MessageBox, _("%s") % message, type=MessageBox.TYPE_INFO, timeout=5)
		elif config.usage.remote_fallback_nok.value:
			AddNotificationWithID("ChannelsImportNOK", MessageBox, _("%s") % message, type=MessageBox.TYPE_ERROR, timeout=5)
