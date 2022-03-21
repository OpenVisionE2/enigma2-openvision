#!/usr/bin/python
# -*- coding: utf-8 -*-
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
from six import PY2
from six.moves.urllib.error import URLError
from six.moves.urllib.parse import quote
import xml.etree.ElementTree as et
if PY2:
	from urllib2 import Request, urlopen
	from base64 import encodestring
	encodecommand = encodestring
else: # Python 3
	from six.moves.urllib.request import Request, urlopen
	from base64 import encodebytes
	encodecommand = encodebytes

settingfiles = ('lamedb', 'bouquets.', 'userbouquet.', 'blacklist', 'whitelist', 'alternatives.')


class ImportChannels():

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
			if "[Errno -3]" in str(err.reason):
				print("[ImportChannels] Network is not up yet, delay 5 seconds")
				# network not up yet
				sleep(5)
				return self.getUrl(url, timeout)
			print("[ImportChannels] URLError ", err)
			raise err
		return result

	def getTerrestrialUrl(self):
		url = config.usage.remote_fallback_dvb_t.value
		return url[:url.rfind(":")] if url else self.url

	def getFallbackSettings(self):
		if not URLError:
			return self.getUrl("%s/web/settings" % self.getTerrestrialUrl()).read()

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

	"""
	Enumerate all the files that make up the bouquet system, either local or on a remote machine
	"""

	def ImportGetFilelist(self, remote=False, *files):
		result = []
		for file in files:
			# read the contents of the file
			try:
				if remote:
					try:
						content = self.getUrl("%s/file?file=/etc/enigma2/%s" % (self.url, quote(file))).readlines()
					except Exception as e:
						print("[ImportChannels] Exception: %s" % str(e))
						self.ImportChannelsDone(False, _("ERROR downloading file /etc/enigma2/%s") % file)
						return
				else:
					with open('/etc/enigma2/%s' % file, 'r') as f:
						content = f.readlines()
			except Exception as e:
				# for the moment just log and ignore
				print("[ImportChannels] %s" % str(e))
				continue

			# check the contents for more bouquet files
			for line in content:
				# check if it contains another bouquet reference
				r = re.match('#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "(.*)" ORDER BY bouquet', str(line))
				if r:
					# recurse
					result.extend(self.ImportGetFilelist(remote, r.group(1)))

			# add add the file itself
			result.append(file)

		# return the file list
		return result

	def threaded_function(self):
		settings = self.getFallbackSettings()
		self.getTerrestrialRegion(settings)
		self.tmp_dir = tempfile.mkdtemp(prefix="ImportChannels_")

		if "epg" in self.remote_fallback_import:
			print("[ImportChannels] Writing epg.dat file on sever box")
			try:
				self.getUrl("%s/web/saveepg" % self.url, timeout=30).read()
			except:
				self.ImportChannelsDone(False, _("Error when writing epg.dat on server"))
				return
			print("[ImportChannels] Get EPG Location")
			try:
				epgdatfile = self.getFallbackSettingsValue(settings, "config.misc.epgcache_filename") or "/media/hdd/epg.dat"
				try:
					files = [file for file in loads(self.getUrl("%s/file?dir=%s" % (self.url, os.path.dirname(epgdatfile))).read())["files"] if os.path.basename(file).startswith(os.path.basename(epgdatfile))]
				except:
					files = [file for file in loads(self.getUrl("%s/file?dir=/" % self.url).read())["files"] if os.path.basename(file).startswith("epg.dat")]
				epg_location = files[0] if files else None
			except:
				self.ImportChannelsDone(False, _("Error while retreiving location of epg.dat on server"))
				return
			if epg_location:
				print("[ImportChannels] Copy EPG file...")
				try:
					open(os.path.join(self.tmp_dir, "epg.dat"), "wb").write(self.getUrl("%s/file?file=%s" % (self.url, epg_location)).read())
					shutil.move(os.path.join(self.tmp_dir, "epg.dat"), config.misc.epgcache_filename.value)
				except:
					self.ImportChannelsDone(False, _("Error while retreiving epg.dat from server"))
					return
			else:
				self.ImportChannelsDone(False, _("No epg.dat file found server"))

		if "channels" in self.remote_fallback_import:
			print("[ImportChannels] enumerate remote files")
			files = self.ImportGetFilelist(True, 'bouquets.tv', 'bouquets.radio')

			print("[ImportChannels] fetch remote files")
			for file in files:
				print("[ImportChannels] Downloading %s..." % file)
				try:
					open(os.path.join(self.tmp_dir, os.path.basename(file)), "wb").write(self.getUrl("%s/file?file=/etc/enigma2/%s" % (self.url, quote(file))).read())
				except Exception as e:
					print("[ImportChannels] Exception: %s" % str(e))

			print("[ImportChannels] enumerate local files")
			files = self.ImportGetFilelist(False, 'bouquets.tv', 'bouquets.radio')

			print("[ImportChannels] Removing old local files...")
			for file in files:
				print("[ImportChannels] Removing %s..." % file)
				os.remove(os.path.join("/etc/enigma2", file))
			print("[ImportChannels] copying files...")
			files = [x for x in os.listdir(self.tmp_dir)]
			for file in files:
				print("[ImportChannels] Moving %s..." % file)
				shutil.move(os.path.join(self.tmp_dir, file), os.path.join("/etc/enigma2", file))
		self.ImportChannelsDone(True, {"channels": _("Channels"), "epg": _("EPG"), "channels_epg": _("Channels and EPG")}[self.remote_fallback_import])

	def ImportChannelsDone(self, flag, message=None):
		shutil.rmtree(self.tmp_dir, True)
		if flag:
			AddNotificationWithID("ChannelsImportOK", MessageBox, _("%s imported from fallback tuner") % message, type=MessageBox.TYPE_INFO, timeout=5)
		else:
			AddNotificationWithID("ChannelsImportNOK", MessageBox, _("Import from fallback tuner failed, %s") % message, type=MessageBox.TYPE_ERROR, timeout=5)
