SUBDIRS = countries fonts extensions keymaps skin_default rc_models hw_info

if HAVE_BWLCD128
SUBDIRS += vfd128
endif

if HAVE_BWLCD140
SUBDIRS += vfd140
endif

if HAVE_BWLCD255
SUBDIRS += vfd255
endif

if HAVE_COLORLCD1
SUBDIRS += display128
endif

if HAVE_COLORLCD2
SUBDIRS += display96
endif

if HAVE_COLORLCD220
SUBDIRS += display220
endif

if HAVE_COLORLCD3
SUBDIRS += display128dm
endif

if HAVE_COLORLCD390
SUBDIRS += display390
endif

if HAVE_COLORLCD400
SUBDIRS += display400
endif

if HAVE_COLORLCD480
SUBDIRS += display480
endif

if HAVE_COLORLCD720
SUBDIRS += display720
endif

if HAVE_COLORLCD800
SUBDIRS += display800
endif

if HAVE_GRAUTEC70X0
SUBDIRS += grautec70x0
endif

if HAVE_GRAUTEC8000
SUBDIRS += grautec8000
endif

if HAVE_TEXTLCD
if HAVE_7SEGMENT
SUBDIRS += 7segment
else
SUBDIRS += displaytext
endif
endif

dist_pkgdata_DATA = \
	encoding.conf \
	keymap.xml \
	keytranslation.xml \
	menu.xml \
	prev.png \
	radio.mvi \
	black.mvi \
	rcpositions.xml \
	setup.xml \
	skin_default.xml \
	skin_subtitles.xml \
	skin.xml \
	startwizard.xml \
	freesat.t1 \
	freesat.t2 \
	iso-639-3.pck \
	timezone.xml \
	unicable.xml \
	groupedservices

iso-639-3.pck: $(srcdir)/iso-639-3.tab
	python $(srcdir)/convert-iso-639-3.py $< $@
