# -*- coding: utf-8 -*-
from os.path import basename, normpath
from Components.Converter.Converter import Converter
from Components.Element import cached, ElementError
from enigma import iServiceInformation, eServiceReference
from ServiceReference import ServiceReference
from Components.UsageConfig import dropEPGNewLines, replaceEPGSeparator
from Components.config import config


class MovieInfo(Converter):
	MOVIE_SHORT_DESCRIPTION = 0 # meta description when available.. when not .eit short description
	MOVIE_META_DESCRIPTION = 1 # just meta description when available
	MOVIE_REC_SERVICE_NAME = 2 # name of recording service
	MOVIE_REC_FILESIZE = 3 # filesize of recording
	MOVIE_FULL_DESCRIPTION = 4 # short and exended description
	MOVIE_NAME = 5 # recording name

	def __init__(self, type):
		if type == "ShortDescription":
			self.type = self.MOVIE_SHORT_DESCRIPTION
		elif type == "MetaDescription":
			self.type = self.MOVIE_META_DESCRIPTION
		elif type == "RecordServiceName":
			self.type = self.MOVIE_REC_SERVICE_NAME
		elif type == "FileSize":
			self.type = self.MOVIE_REC_FILESIZE
		elif type == "FullDescription":
			self.type = self.MOVIE_FULL_DESCRIPTION
		elif type == "Name":
			self.type = self.MOVIE_NAME
		else:
			raise ElementError("'%s' is not <ShortDescription|MetaDescription|RecordServiceName|FileSize> for MovieInfo converter" % type)
		Converter.__init__(self, type)

	@cached
	def getText(self):
		service = self.source.service
		info = self.source.info
		event = self.source.event
		if info and service:
			isDirectory = (service.flags & eServiceReference.flagDirectory) == eServiceReference.flagDirectory
			if self.type == self.MOVIE_SHORT_DESCRIPTION:
				if isDirectory:
					# Short description for Directory is the full path
					return service.getPath()
				return (info.getInfoString(service, iServiceInformation.sDescription)
					or (event and dropEPGNewLines(event.getShortDescription()))
					or service.getPath())
			elif self.type == self.MOVIE_FULL_DESCRIPTION:
				if isDirectory:
					return ""
				description = (event and dropEPGNewLines(event.getShortDescription())
						or info.getInfoString(service, iServiceInformation.sDescription))
				extended = event and dropEPGNewLines(event.getExtendedDescription().rstrip())
				if description and extended:
					if description.replace('\n', '') == extended.replace('\n', ''):
						return extended
					description += replaceEPGSeparator(config.epg.fulldescription_separator.value)
				return description + (extended if extended else "")
			elif self.type == self.MOVIE_META_DESCRIPTION:
				return ((event and (dropEPGNewLines(event.getExtendedDescription()) or dropEPGNewLines(event.getShortDescription())))
					or info.getInfoString(service, iServiceInformation.sDescription)
					or service.getPath())
			elif self.type == self.MOVIE_NAME:
				if isDirectory:
					return basename(normpath(service.getPath()))
				return event and event.getEventName() or info and info.getName(service)
			elif self.type == self.MOVIE_REC_SERVICE_NAME:
				rec_ref_str = info.getInfoString(service, iServiceInformation.sServiceref)
				return ServiceReference(rec_ref_str).getServiceName()
			elif self.type == self.MOVIE_REC_FILESIZE:
				if isDirectory:
					return _("Directory")
				filesize = info.getFileSize(service)
				if filesize is not None:
					from Components.Harddisk import bytesToHumanReadable
					return bytesToHumanReadable(filesize)
		return ""

	text = property(getText)
