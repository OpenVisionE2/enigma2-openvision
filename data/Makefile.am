SUBDIRS = countries fonts extensions keymaps skin_default skin_fallback_1080 rc_models

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
	black.mvi \
	encoding.conf \
	freesat.t1 \
	freesat.t2 \
	groupedservices \
	iso-639-3.pck \
	keymap.xml \
	keytranslation.xml \
	menu.xml \
	otv_00820000_fbff_16a8.dict \
	otv_011a0000_0002_07d4.dict \
	otv_06180000_1000_0011.dict \
	otv_06400000_00a9_0003.dict \
	prev.png \
	radio.mvi \
	rcpositions.xml \
	setup.xml \
	skin.xml \
	skin_default.xml \
	skin_subtitles.xml \
	startwizard.xml \
	unicable.xml

iso-639-3.pck: $(srcdir)/iso-639-3.tab
	python $(srcdir)/convert-iso-639-3.py $< $@
