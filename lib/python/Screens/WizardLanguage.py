# -*- coding: utf-8 -*-
from Tools.Geolocation import geolocation
from Components.Label import Label
from Screens.LanguageSelection import LanguageWizard
from Screens.Wizard import Wizard
from Components.config import config, ConfigBoolean

config.misc.firstrun = ConfigBoolean(default=True)

geolocationData = geolocation.getGeolocationData(fields="isp,org,mobile,proxy,query", useCache=False)


class WizardLanguage(Wizard):
	if geolocationData.get("status", None) != "success" and config.misc.firstrun.value:
		def __init__(self, session, showSteps=True, showStepSlider=True, showList=True, showConfig=True):
			Wizard.__init__(self, session, showSteps, showStepSlider, showList, showConfig)
			self["key_red"] = Label()
			self["languagetext"] = Label(_("Change Language"))

		def red(self):
			self.session.open(LanguageWizard)

	if not config.misc.firstrun.value:
		def __init__(self, session, showSteps=True, showStepSlider=True, showList=True, showConfig=True):
			Wizard.__init__(self, session, showSteps, showStepSlider, showList, showConfig)
			self["key_red"] = Label()
			self["languagetext"] = Label(_("Change Language"))

		def red(self):
			self.session.open(LanguageWizard)
