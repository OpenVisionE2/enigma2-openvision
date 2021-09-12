from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Screens.LocaleSelection import LocaleWizard
from Screens.Wizard import Wizard


class WizardLanguage(Wizard):
	def __init__(self, session, showSteps=True, showStepSlider=True, showList=True, showConfig=True):
		Wizard.__init__(self, session, showSteps, showStepSlider, showList, showConfig)
		self["key_red"] = StaticText(_("Locale/Language"))
		self["languagetext"] = Label(_("Change Language"))

	def red(self):
		self.session.open(LocaleWizard)
