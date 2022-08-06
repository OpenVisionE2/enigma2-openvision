# -*- coding: utf-8 -*-
from Components.Label import Label
from Screens.LocaleSelection import LocaleWizard
from Screens.Wizard import Wizard


class WizardLanguage(Wizard):
	def __init__(self, session, showSteps=True, showStepSlider=True, showList=True, showConfig=True):
		Wizard.__init__(self, session, showSteps, showStepSlider, showList, showConfig)
		self["key_red"] = Label()
		self["languagetext"] = Label(_("Locale/Language"))

	def red(self):
		self.session.open(LocaleWizard)
