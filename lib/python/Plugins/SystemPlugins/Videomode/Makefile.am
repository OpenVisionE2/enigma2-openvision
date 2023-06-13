installdir = $(pkglibdir)/python/Plugins/SystemPlugins/Videomode

SUBDIRS = meta

install_PYTHON = \
	__init__.py \
	plugin.py \
	VideoHardware.py \
	VideoWizard.py

dist_install_DATA = \
	HDMI.png \
	Jack.png \
	lcd_HDMI.png \
	lcd_Jack.png \
	lcd_RCA.png \
	lcd_Scart.png \
	lcd_YPbPr.png \
	RCA.png \
	Scart.png \
	YPbPr.png \
	videowizard.xml

if DREAMBOXDVI
dist_install_DATA += DVI.png lcd_DVI.png
endif
