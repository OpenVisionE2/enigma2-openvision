AC_INIT([enigma2],[11],[openvision.tech])
AM_INIT_AUTOMAKE([dist-bzip2 no-define tar-pax -Wno-portability])
AC_CONFIG_HEADERS([enigma2_config.h])

# Silent rules are available since 1.11, but older versions
# are still in use. So don't use them unconditionally.
m4_ifdef([AM_SILENT_RULES], [AM_SILENT_RULES([yes])])

AC_USE_SYSTEM_EXTENSIONS
AC_SYS_LARGEFILE

AC_PROG_CC
AC_PROG_CXX
m4_ifdef([LT_INIT], [LT_INIT], [AC_PROG_LIBTOOL])
AC_CONFIG_MACRO_DIR([m4])
AC_OPENMP()

AC_PATH_PROG(MSGFMT, msgfmt, AC_MSG_ERROR(Could not find msgfmt))

AM_PATH_PYTHON
AX_PYTHON_DEVEL
AX_PKG_SWIG
AX_SWIG_ENABLE_CXX
AX_SWIG_PYTHON
AX_PTHREAD

TUXBOX_APPS_DVB

AM_CONDITIONAL(HAVE_GIT_DIR, test -d "$srcdir/.git")
AM_CONDITIONAL(HAVE_FAKE_GIT_DIR, test -f "$srcdir/.git/last_commit_info")

dnl versions of plugins-base
PKG_CHECK_MODULES(TUXTXT, tuxbox-tuxtxt)
PKG_CHECK_MODULES(BASE, [freetype2 fribidi glib-2.0 libdvbsi++ libpng libxml-2.0 sigc++-2.0 libssl libcrypto])
PKG_CHECK_MODULES(LIBDDVD, libdreamdvd, HAVE_LIBDDVD="yes", HAVE_LIBDDVD="no")
AM_CONDITIONAL(HAVE_LIBDDVD, test "$HAVE_LIBDDVD" = "yes")
PKG_CHECK_MODULES(AVAHI, avahi-client)

AC_CHECK_LIB([udfread], [udfread_init])
AC_CHECK_LIB([dl], [dlopen], [LIBDL_LIBS="-ldl"], [AC_MSG_ERROR([Could not find libdl])])
AC_SUBST(LIBDL_LIBS)
AC_CHECK_LIB([jpeg], [jpeg_set_defaults], [LIBJPEG_LIBS="-ljpeg"], [AC_MSG_ERROR([Could not find libjpeg])])
AC_SUBST(LIBJPEG_LIBS)
AC_CHECK_LIB([ungif], [DGifOpen], [LIBGIF_LIBS="-lungif"], [AC_CHECK_LIB([gif], [DGifOpen], [LIBGIF_LIBS="-lgif"], [AC_MSG_ERROR([Could not find libgif or libungif])])])
AC_SUBST(LIBGIF_LIBS)

AC_ARG_WITH(crashlogemail,
	[  --with-crashlogemail=crash log email address],
	[CRASHLOGEMAIL="$withval"],[CRASHLOGEMAIL="crash@openvision.tech"])
AC_SUBST(CRASHLOGEMAIL)
AC_DEFINE_UNQUOTED(CRASH_EMAILADDR,"$CRASHLOGEMAIL",[crash log email address])

AC_ARG_WITH(boxtype,
	AS_HELP_STRING([--with-boxtype],[build for BOXTYPE, $withval]),
	[BOXTYPE="$withval"],[BOXTYPE=""])
AC_SUBST(BOXTYPE)
AC_DEFINE_UNQUOTED(BOXTYPE,"$BOXTYPE",[box type])

AC_ARG_WITH(boxbrand,
	AS_HELP_STRING([--with-boxbrand],[build for BOXBRAND, $withval]),
	[BOXBRAND="$withval"],[BOXBRAND=""])
AC_SUBST(BOXBRAND)
AC_DEFINE_UNQUOTED(BOXBRAND,"$BOXBRAND",[box brand])

AC_ARG_WITH(stbplatform,
	AS_HELP_STRING([--with-stbplatform],[build for STBPLATFORM, $withval]),
	[STBPLATFORM="$withval"],[STBPLATFORM=""])
AC_SUBST(STBPLATFORM)
AC_DEFINE_UNQUOTED(STBPLATFORM,"$STBPLATFORM",[stb platform])

AC_ARG_WITH(e2rev,
	AS_HELP_STRING([--with-e2rev],[value of E2REV, $withval]),
	[E2REV="$withval"],[E2REV=""])
AC_SUBST(E2REV)
AC_DEFINE_UNQUOTED(E2REV,"$E2REV",[enigma2 revision])

AC_ARG_WITH(nolcd,
	AC_HELP_STRING([--with-nolcd], [disable ascii based lcd, yes or no]),
	[[withnolcd=$withval]],
	[[withnolcd=no]]
)
if test x"$withnolcd" != xno ; then
	AC_DEFINE(NO_LCD, 1,[Define when disable an ascii based lcd device])
fi
AM_CONDITIONAL(NO_LCD, test x"$withnolcd" != xno)

AC_ARG_WITH(textlcd,
	AC_HELP_STRING([--with-textlcd], [use ascii based lcd, yes or no]),
	[[withtextlcd=$withval]],
	[[withtextlcd=no]]
)
if test x"$withtextlcd" != xno ; then
	AC_DEFINE(HAVE_TEXTLCD, 1,[Define when using an ascii based lcd device])
fi
AM_CONDITIONAL(HAVE_TEXTLCD, test x"$withtextlcd" != xno)

AC_ARG_WITH(7segment,
	AC_HELP_STRING([--with-7segment], [use 7 segment lcd, yes or no]),
	[[TEXTSKIN="7segment"]],
	[[TEXTSKIN="default"]]
)
AC_SUBST(TEXTSKIN)
if test x"$with7segment" != xno ; then
	AC_DEFINE(HAVE_7SEGMENT, 1,[Define when using an ascii based lcd device])
fi
AM_CONDITIONAL(HAVE_7SEGMENT, test x"$with7segment" != xno)

AC_ARG_WITH(colorlcd220,
	AC_HELP_STRING([--with-colorlcd220], [use 220x176 16bpp color display, yes or no]),
	[[withcolorlcd220=$withval]],
	[[withcolorlcd220=no]]
)
if test x"$withcolorlcd220" != xno ; then
	AC_DEFINE(HAVE_COLORLCD220, 1,[Define when using a 220x176 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD220, test x"$withcolorlcd220" != xno)

AC_ARG_WITH(colorlcd390,
	AC_HELP_STRING([--with-colorlcd390], [use 390x240 16bpp color display, yes or no]),
	[[withcolorlcd390=$withval]],
	[[withcolorlcd390=no]]
)
if test x"$withcolorlcd390" != xno ; then
	AC_DEFINE(HAVE_COLORLCD390, 1,[Define when using a 390x240 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD390, test x"$withcolorlcd390" != xno)

AC_ARG_WITH(colorlcd400,
	AC_HELP_STRING([--with-colorlcd400], [use 400x176 16bpp color display, yes or no]),
	[[withcolorlcd400=$withval]],
	[[withcolorlcd400=no]]
)
if test x"$withcolorlcd400" != xno ; then
	AC_DEFINE(HAVE_COLORLCD400, 1,[Define when using a 400x176 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD400, test x"$withcolorlcd400" != xno)

AC_ARG_WITH(colorlcd480,
	AC_HELP_STRING([--with-colorlcd480], [use 480x320 16bpp color display, yes or no]),
	[[withcolorlcd480=$withval]],
	[[withcolorlcd480=no]]
)
if test x"$withcolorlcd480" != xno ; then
	AC_DEFINE(HAVE_COLORLCD480, 1,[Define when using a 480x320 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD480, test x"$withcolorlcd480" != xno)

AC_ARG_WITH(colorlcd720,
	AC_HELP_STRING([--with-colorlcd720], [use 720x576 16bpp color display, yes or no]),
	[[withcolorlcd720=$withval]],
	[[withcolorlcd720=no]]
)
if test x"$withcolorlcd720" != xno ; then
	AC_DEFINE(HAVE_COLORLCD720, 1,[Define when using a 720x576 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD720, test x"$withcolorlcd720" != xno)

AC_ARG_WITH(colorlcd800,
	AC_HELP_STRING([--with-colorlcd800], [use 800x480 16bpp color display, yes or no]),
	[[withcolorlcd800=$withval]],
	[[withcolorlcd800=no]]
)
if test x"$withcolorlcd800" != xno ; then
	AC_DEFINE(HAVE_COLORLCD800, 1,[Define when using a 800x480 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD800, test x"$withcolorlcd800" != xno)

AC_ARG_WITH(bwlcd128,
	AC_HELP_STRING([--with-bwlcd128], [use 128x32 1bpp black and white display, yes or no]),
	[[withbwlcd128=$withval]],
	[[withbwlcd128=no]]
)
if test x"$withbwlcd128" != xno ; then
	AC_DEFINE(HAVE_BWLCD128, 1,[Define when using a 128x32 black and white display device])
fi
AM_CONDITIONAL(HAVE_BWLCD128, test x"$withbwlcd128" != xno)

AC_ARG_WITH(bwlcd140,
	AC_HELP_STRING([--with-bwlcd140], [use 140x32 1bpp black and white display, yes or no]),
	[[withbwlcd140=$withval]],
	[[withbwlcd140=no]]
)
if test x"$withbwlcd140" != xno ; then
	AC_DEFINE(HAVE_BWLCD140, 1,[Define when using a 140x32 black and white display device])
fi
AM_CONDITIONAL(HAVE_BWLCD140, test x"$withbwlcd140" != xno)

AC_ARG_WITH(bwlcd255,
	AC_HELP_STRING([--with-bwlcd255], [use 255x64 1bpp black and white display, yes or no]),
	[[withbwlcd255=$withval]],
	[[withbwlcd255=no]]
)
if test x"$withbwlcd255" != xno ; then
	AC_DEFINE(HAVE_BWLCD255, 1,[Define when using a 255x64 black and white display device])
fi
AM_CONDITIONAL(HAVE_BWLCD255, test x"$withbwlcd255" != xno)

AC_ARG_WITH(libsdl,
	AS_HELP_STRING([--with-libsdl],[use libsdl, yes or no]),
	[with_libsdl=$withval],[with_libsdl=no])
if test "$with_libsdl" = "yes"; then
	PKG_CHECK_MODULES(LIBSDL, sdl)
fi
AM_CONDITIONAL(HAVE_LIBSDL, test "$with_libsdl" = "yes")

AC_ARG_WITH(libxine,
	AS_HELP_STRING([--with-libxine],[use libxine, yes or no]),
	[with_libxine=$withval],[with_libxine=no])
if test "$with_libxine" = "yes"; then
	PKG_CHECK_MODULES(LIBXINE, libxine)
	AC_DEFINE([WITH_XINE],[1],[Define to 1 if you have libxine])
fi
AM_CONDITIONAL(HAVE_LIBXINE, test "$with_libxine" = "yes")

AC_ARG_WITH(debug,
	AS_HELP_STRING([--without-debug],[disable debugging code]),
	[with_debug="$withval"],[with_debug="yes"])
if test "$with_debug" = "yes"; then
	AC_DEFINE([DEBUG],[1],[Define to 1 to enable debugging code])
fi

AC_ARG_WITH(memcheck,
	AS_HELP_STRING([--with-memcheck],[enable memory leak checks]),
	[with_memcheck="$withval"],[with_memcheck="no"])
if test "$with_memcheck" = "yes"; then
	AC_DEFINE([MEMLEAK_CHECK],[1],[Define to 1 to enable memory leak checks])
fi

AC_ARG_WITH(po,
	AS_HELP_STRING([--with-po],[enable updating of po files]),
	[with_po="$withval"],[with_po="no"])
if test "$with_po" = "yes"; then
	AC_PATH_PROG(MSGINIT, msginit)
	AC_PATH_PROG(MSGMERGE, msgmerge)
	AC_PATH_PROG(MSGUNIQ, msguniq)
	AC_PATH_PROG(MSGATTRIB, msgattrib)
	AC_PATH_PROG(XGETTEXT, xgettext)
	if test -z "$MSGINIT" -o -z "$MSGMERGE" -o -z "$MSGUNIQ" -o -z "$MSGATTRIB" -o -z "$XGETTEXT"; then
		AC_MSG_ERROR([Could not find required gettext tools])
	fi
fi
AM_CONDITIONAL(UPDATE_PO, test "$with_po" = "yes")

AC_ARG_WITH(alsa,
	AC_HELP_STRING([--with-alsa], [Enable ALSA support]),
	[[with_alsa=$withval]],
	[[with_alsa=no]]
)
if test x"$with_alsa" == xyes ; then
	AC_DEFINE(HAVE_ALSA, 1,[Enables ALSA support])
	PKG_CHECK_MODULES(ALSA, alsa)
fi

AC_ARG_WITH(alsacard,
	AC_HELP_STRING([--with-alsacard=card], [use 'card' for alsa card device, e.g. hw:0]),
	[[with_alsacard=$withval]],
	[[with_alsacard=no]]
)
if test x"$with_alsacard" != xno ; then
	AC_DEFINE_UNQUOTED(ALSA_CARD, "$withval",[Defines which alsa card to use])
fi

AC_ARG_WITH(alsamixer,
	AC_HELP_STRING([--with-alsamixer=mixername], [use alsa 'mixername' for volume control, e.g. Master]),
	[[with_alsamixer=$withval]],
	[[with_alsamixer=no]]
)
if test x"$with_alsamixer" != xno ; then
	AC_DEFINE_UNQUOTED(ALSA_VOLUME_MIXER, "$withval",[Defines which alsa mixer to use for volume control])
fi

AC_ARG_WITH(fbdev,
	AC_HELP_STRING([--with-fbdev=devicename], [use devicename for framebuffer device, e.g. /dev/fb0 ]),
	[[with_fbdev=$withval]],
	[[with_fbdev=no]]
)
if test x"$with_fbdev" != xno ; then
	AC_DEFINE_UNQUOTED(FB_DEV, "$withval", [Defines which device to use for main framebuffer (e.g. /dev/fb0)])
fi

AC_ARG_WITH(lcddev,
	AC_HELP_STRING([--with-lcddev=devicename], [use devicename for lcd framebuffer device, e.g. /dev/fb1 ]),
	[[with_lcddev=$withval]],
	[[with_lcddev=no]]
)
if test x"$with_lcddev" != xno ; then
	AC_DEFINE_UNQUOTED(LCD_DEV, "$withval", [Defines which device to use for lcd (e.g. /dev/fb1)])
fi

AC_ARG_WITH(alphablendingacceleration,
	AC_HELP_STRING([--with-alphablendingacceleration=never/always/auto], [alphablending acceleration strategy: never accelerate / always accelerate / automatically decide when to accelerate (default)]),
	[[with_alphablendingacceleration=$withval]],
	[[with_alphablendingacceleration=auto]]
)
if test x"$with_alphablendingacceleration" = xnever ; then
	AC_DEFINE_UNQUOTED(FORCE_NO_BLENDING_ACCELERATION, 1, [Do not attempt to accelerate alphablending blits])
elif test x"$with_alphablendingacceleration" = xalways ; then
	AC_DEFINE_UNQUOTED(FORCE_ALPHABLENDING_ACCELERATION, 1, [Accelerate alphablending blits])
fi

AC_ARG_WITH(accelerationthreshold,
	AC_HELP_STRING([--with-accelerationthreshold=n], [use acceleration threshold of n bytes]),
	[[with_accelerationthreshold=$withval]],
	[[with_accelerationthreshold=48000]]
)
AC_DEFINE_UNQUOTED(GFX_SURFACE_ACCELERATION_THRESHOLD, $with_accelerationthreshold,[Configure threshold for accelerated surfaces (in bytes)])

AC_ARG_WITH(fillaccelerationthreshold,
	AC_HELP_STRING([--with-fillaccelerationthreshold=n], [use fill acceleration threshold of n bytes]),
	[[with_fillaccelerationthreshold=$withval]],
	[[with_fillaccelerationthreshold=80000]]
)
AC_DEFINE_UNQUOTED(GFX_SURFACE_FILL_ACCELERATION_THRESHOLD, $with_fillaccelerationthreshold,[Configure threshold for accelerated fill operations (in bytes)])

AC_ARG_WITH(blitaccelerationthreshold,
	AC_HELP_STRING([--with-blitaccelerationthreshold=n], [use blit acceleration threshold of n bytes]),
	[[with_blitaccelerationthreshold=$withval]],
	[[with_blitaccelerationthreshold=0]]
)
AC_DEFINE_UNQUOTED(GFX_SURFACE_BLIT_ACCELERATION_THRESHOLD, $with_blitaccelerationthreshold,[Configure threshold for accelerated blit operations (in bytes)])

AC_ARG_WITH(accelerationaccumulation,
	AC_HELP_STRING([--with-accelerationaccumulation], [accumulate blit/fill acceleration operations]),
	[[with_accelerationaccumulation=$withval]],
	[[with_accelerationaccumulation=no]]
)
if test x"$with_accelerationaccumulation" = xyes ; then
	AC_DEFINE(SUPPORT_ACCUMULATED_ACCELERATION_OPERATIONS, 1,[Accumulate blit/fill acceleration operations])
fi

AC_ARG_WITH(libvugles2,
	AS_HELP_STRING([--with-libvugles2],[use libvugles2, yes or no]),
	[with_libvugles2=$withval],[with_libvugles2=no])
if test "$with_libvugles2" = "yes"; then
	PKG_CHECK_MODULES(LIBVUGLES2, [libvugles2])
	GLES_CFLAGS="-DUSE_LIBVUGLES2"
fi
AM_CONDITIONAL(HAVE_LIBVUGLES2, test "$with_libvugles2" = "yes")

AC_ARG_WITH(libhiaccel,
	AS_HELP_STRING([--with-libhiaccel],[use libhiaccel, yes or no]),
	[with_libhiaccel=$withval],[with_libhiaccel=no])
if test "$with_libhiaccel" = "yes"; then
	PKG_CHECK_MODULES(LIBHIACCEL, [libhiaccel])
	HIACCEL_CFLAGS="-DUSE_LIBHIACCEL"
fi
if test x"$with_libhiaccel" != xno ; then
	AC_DEFINE(HAVE_HISILICON_ACCEL, 1,[define add HISILICON ACCEL])
fi

AC_ARG_WITH(olde2api,
	AS_HELP_STRING([--with-olde2api],[use olde2api, yes or no]),
	[with_olde2api=$withval],[with_olde2api=no])
if test x"$with_olde2api" != xno ; then
	AC_DEFINE(HAVE_OLDE2_API, 1,[define add old api of enigma2])
fi

AC_ARG_WITH(osdanimation,
	AC_HELP_STRING([--with-osdanimation], [use osd animation, yes or no]),
	[[withosdanimation=$withval]],
	[[withosdanimation=no]]
)
if test x"$withosdanimation" != xno ; then
	AC_DEFINE(HAVE_OSDANIMATION, 1,[Define if driver supports animation of osd])
fi
AM_CONDITIONAL(HAVE_OSDANIMATION, test x"$withosdanimation" != xno)

AC_ARG_WITH(subttxtabnormalptsdiffs,
	AC_HELP_STRING([--with-subttxtabnormalptsdiffs=n], [use n/90 msec diffs for subtitle and teletext abnormal pts]),
	[[with_subttxtabnormalptsdiffs=$withval]],
	[[with_subttxtabnormalptsdiffs=1800000]]
)
AC_DEFINE_UNQUOTED(SUBT_TXT_ABNORMAL_PTS_DIFFS, $with_subttxtabnormalptsdiffs,[Configure abnormal pts for subtitle and teletext])

AC_ARG_WITH(amlogic,
	AC_HELP_STRING([--with-amlogic], [use amlogic MPEG decoder]),
	[[with_amlogic=$withval]],
	[[with_amlogic=no]]
)
AM_CONDITIONAL(HAVE_AMLOGIC, test x"$with_amlogic" = xyes)
if test x"$with_amlogic" = xyes ; then
	AC_DEFINE(HAVE_AMLOGIC, 1,[Enables AMLOGIC decoder support])
	PKG_CHECK_MODULES(AMCODEC, libamcodec)
	PKG_CHECK_MODULES(AMADEC, libamadec)
	PKG_CHECK_MODULES(DVBCSA, libdvbcsa)
	ALSA_CFLAGS="-lasound"
fi

AC_ARG_WITH(fcc,
	AC_HELP_STRING([--with-fcc], [use FCC specific codes for fast channel change]),
	[[fcc=$withval]],
	[[fcc=no]]
)
AM_CONDITIONAL(HAVE_FCC_ABILITY, test x"$with_fcc" = xyes)
if test x"$with_fcc" = xyes ; then
	AC_DEFINE(HAVE_FCC_ABILITY, 1,[use FCC specific codes for fast channel change])
fi

if test "$BOXBRAND" == "rpi"; then
	PKG_CHECK_MODULES(DVBCSA, libdvbcsa)
	PKG_CHECK_MODULES(LIBNL, libnl-1 >= 1.0-pre8, has_libnl=yes, dummy=no)
	PKG_CHECK_MODULES(LIBNL, [libnl-3.0 libnl-genl-3.0], has_libnl=yes, dummy=no)
	if (test "${has_libnl}" = "no"); then
		AC_MSG_ERROR(Netlink library is required)
	fi
#	AC_CHECK_LIB([rpihddevice], [LIBRPIHDDEVICE_LIBS="-lrpihddevice"], [AC_MSG_ERROR([Could not find librpihddevice])])
#	AC_SUBST(LIBRPIHDDEVICE_LIBS)
#	PKG_CHECK_MODULES(LIBRPIHDDEVICE, e2-rpihddevice)
	BASE_LIBS+=" -lrpihddevice"
	BASE_LIBS+=" $LIBNL_LIBS"
	AC_DEFINE(OMX_SKIP64BIT, 1, [Required by the RPi implementation])
	RPI_CFLAGS=" $LIBNL_CFLAGS"
	CXXFLAGS+="$RPI_CFLAGS"
	AC_DEFINE(HAVE_RASPBERRYPI, 1,[enable rpi specific stuff])
	AC_DEFINE(VMSG_TYPE2, 1,[define vtuner_message type 2])
fi

AM_CONDITIONAL(DMAMLOGIC, test "$STBPLATFORM" == "dmamlogic")
AM_CONDITIONAL(RASPBERRYPI, test "$BOXBRAND" == "rpi")

AM_CONDITIONAL(HAVE_COLORLCD1, test "$BOXTYPE" == "dm8000" -o "$BOXTYPE" == "dm800" -o "$BOXTYPE" == "dm7020hd" -o "$BOXTYPE" == "dm7020hdv2")
AM_CONDITIONAL(HAVE_COLORLCD2, test "$BOXTYPE" == "dm800se" -o "$BOXTYPE" == "dm800sev2" -o "$BOXTYPE" == "dm820")
AM_CONDITIONAL(HAVE_COLORLCD3, test "$BOXTYPE" == "dm7080")
AM_CONDITIONAL(HAVE_GRAUTEC70X0, test "$BOXTYPE" == "dm7020hd" -o "$BOXTYPE" == "dm7020hdv2" -o "$BOXTYPE" == "dm7080")
AM_CONDITIONAL(HAVE_GRAUTEC8000, test "$BOXTYPE" == "dm8000")

if test "$STBPLATFORM" == "7000s" -o "$STBPLATFORM" == "7100s" -o "$BOXTYPE" == "twinboxlcdci5" -o "$STBPLATFORM" == "7210s" -o "$BOXTYPE" == "sf238" -o "$BOXTYPE" == "odin2hybrid" -o "$BOXTYPE" == "odinplus"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
fi

if test "$STBPLATFORM" == "8100s"; then
	AC_DEFINE(KEY_VIDEO_TO_KEY_BOOKMARKS, 1,[define when rc sends a KEY_VIDEO event for its KEY_BOOKMARKS])
fi

if test "$BOXBRAND" == "azbox"; then
	AC_DEFINE(AZBOX, 1, [Azbox hardware])
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(FORCE_NO_ACCELNEVER, 1,[define when the framebuffer acceleration auto not working correct])
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_HOME_TO_KEY_OPEN, 1,[define when rc sends a KEY_HOME event for its KEY_OPEN])
fi

if test "$BOXTYPE" == "azboxme" -o "$BOXTYPE" == "azboxminime"; then
	AC_DEFINE(KEY_TV_TO_KEY_STOP, 1,[define when rc sends a KEY_TV event for its KEY_STOP])
	AC_DEFINE(KEY_VIDEO_TO_KEY_SUBTITLE, 1,[define when rc sends a KEY_VIDEO event for its KEY_SUBTITLE])
	AC_DEFINE(KEY_RADIO_TO_KEY_RECORD, 1,[define when rc sends a KEY_RADIO event for its KEY_RECORD])
fi

if test "$BOXTYPE" == "azboxhd"; then
	AC_DEFINE(KEY_VIDEO_TO_KEY_EPG, 1,[define when rc sends a KEY_VIDEO event for its KEY_EPG])
	AC_DEFINE(KEY_TV_TO_KEY_MODE, 1,[define when rc sends a KEY_TV event for its KEY_MODE key])
	AC_DEFINE(KEY_TEXT_TO_KEY_AUDIO, 1,[define when rc sends a KEY_TEXT event for its KEY_AUDIO key])
	AC_DEFINE(AZBOXHD_LCD_CHARACTERS, 1,[define lcd characters for azboxhd family])
fi

if test "$BOXTYPE" == "blackbox7405"; then
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
	AC_DEFINE(KEY_PLAY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_MEDIA_TO_KEY_BOOKMARKS, 1,[define when rc sends a KEY_MEDIA event for its KEY_BOOKMARKS key])
	AC_DEFINE(KEY_VIDEO_IS_KEY_SCREEN, 1,[define when rc sends a KEY_VIDEO event for its KEY_SCREEN key])
	AC_DEFINE(KEY_ARCHIVE_TO_KEY_DIRECTORY, 1,[define when rc sends a KEY_MEDIA event for its KEY_BOOKMARKS key])
	AC_DEFINE(KEY_TIME_TO_KEY_SLOW, 1,[define when rc sends a KEY_TOME event for its KEY_SLOW key])
fi

if test "$BOXTYPE" == "bwidowx" -o "$BOXTYPE" == "bwidowx2"; then
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(KEY_ZOOM_TO_KEY_SCREEN, 1,[define when rc sends a KEY_ZOOM event for its KEY_SCREEN key])
	AC_DEFINE(KEY_LAST_TO_KEY_PVR, 1,[define when rc sends a KEY_LAST event for its KEY_PVR key])
fi

if test "$STBPLATFORM" == "octagonhisil" -o "$BOXTYPE" == "ustym4kpro" -o "$STBPLATFORM" == "gbmv200" -o "$BOXTYPE" == "beyonwizv2" -o "$BOXTYPE" == "viper4k" -o "$STBPLATFORM" == "dagsmv200"; then
	AC_DEFINE(HAVE_HISILICON, 1,[define it is a HISILICON chip])
	AC_DEFINE(CONFIG_HISILICON_FB, 1,[define add HISILICON framebuffer blit])
	AC_DEFINE(FORCE_ALPHABLENDING_ACCELERATION, 1,[define when the framebuffer acceleration has alphablending support, but detection slow down all])
	AC_DEFINE(VMSG_TYPE2, 1,[define vtuner_message type 2])
fi

if test "$BOXBRAND" == "dags"; then
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
fi

if test "$BOXBRAND" == "dreambox"; then
	AC_DEFINE(DREAMBOX, 1, [Dreambox hardware])
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
fi

if test "$STBPLATFORM" == "dmamlogic"; then
	AC_DEFINE(DMAMLOGIC, 1, [Dreambox Amlogic hardware])
fi

if test "$BOXTYPE" == "dm7080"; then
	AC_DEFINE(DREAMBOX_DUAL_TUNER, 1,[define dreambox dual tuner])
	AC_DEFINE(CONFIG_ION, 1,[define when we need to use ION allocator])
fi

if test "$BOXTYPE" == "dm7020hd" -o "$BOXTYPE" == "dm7020hdv2" -o "$BOXTYPE" == "dm820" -o "$BOXTYPE" == "dm800se" -o "$BOXTYPE" == "dm800sev2" -o "$STBPLATFORM" == "dmamlogic"; then
	AC_DEFINE(DREAMBOX_DUAL_TUNER, 1,[define dreambox dual tuner])
fi

if test "$BOXTYPE" == "dm820" -o "$BOXTYPE" == "dm520"; then
	AC_DEFINE(CONFIG_ION, 1,[define when we need to use ION allocator])
fi

if test "$STBPLATFORM" == "dm4kgen"; then
	AC_DEFINE(DREAMBOX_DUAL_TUNER, 1,[define dreambox dual tuner])
	AC_DEFINE(CONFIG_ION, 1,[define when we need to use ION allocator])
	AC_DEFINE(DREAMBOX_MOVE_LCD, 1,[define when we need to move lcd text a bit to the right])
fi

if test "$BOXTYPE" == "e4hd" -o "$BOXTYPE" == "e4hdhybrid"; then
	AC_DEFINE(KEY_POWER2_TO_KEY_WWW, 1,[define when rc sends a KEY_POWER2 event for its KEY_WWW key])
	AC_DEFINE(KEY_DIRECTORY_TO_KEY_FILE, 1,[define when rc sends a KEY_DIRECTORY event for its KEY_FILE key])
fi

if test "$BOXBRAND" == "ebox"; then
	AC_DEFINE(KEY_SCREEN_TO_KEY_ANGLE, 1,[define when rc sends a KEY_SCREEN event for its KEY_ANGLE key])
	AC_DEFINE(KEY_TIME_TO_KEY_SLEEP, 1,[define when rc sends a KEY_TIME event for its KEY_SLEEP])
	AC_DEFINE(KEY_MODE_TO_KEY_AUDIO, 1,[define when rc sends a KEY_MODE event for its AV plus])
fi

if test "$BOXTYPE" == "et10000"; then
	AC_DEFINE(HAVE_BWLCD128, 1,[define when using a 128x32 black and white display device])
fi

if test "$STBPLATFORM" == "2genxt" -o "$STBPLATFORM" == "1genxt" -o "$STBPLATFORM" == "7genxt"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_F3_TO_KEY_LIST, 1,[define when rc sends a KEY_F3 event for its KEY_LIST key])
fi

if test "$BOXTYPE" == "et8500"; then
	AC_DEFINE(FORCE_ALPHABLENDING_ACCELERATION, 1,[define when the framebuffer acceleration has alphablending support, but detection slow down all])
	AC_DEFINE(HAVE_COLORLCD720, 1,[define when using a 720x576 color display device])
fi

if test "$BOXTYPE" == "et1x000" -o "$BOXTYPE" == "et7x00" -o "$BOXTYPE" == "ultramini"; then
	AC_DEFINE(KEY_F1_TO_KEY_F2, 1,[define when rc sends a KEY_F1 event for its KEY_F2 key])
	AC_DEFINE(FORCE_ALPHABLENDING_ACCELERATION, 1,[define when the framebuffer acceleration has alphablending support, but detection slow down all])
fi

if test `echo "$BOXTYPE" | cut -b 1-3` == "bey"; then
	AC_DEFINE(AUSTRALIA, 1,[define Australia to enable country config])
fi

if test "$BOXTYPE" == "et13000" -o "$BOXTYPE" == "beyonwizu4"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_BOOKMARKS_IS_KEY_DIRECTORY, 1,[define when rc sends a KEY_BOOKMARKS but other box use this key for different mapping we remap to KEY_DIRECTORY])
	AC_DEFINE(FORCE_ALPHABLENDING_ACCELERATION, 1,[define when the framebuffer acceleration has alphablending support, but detection slow down all])
fi

if test "$STBPLATFORM" == "ew7358" -o "$BOXTYPE" == "bre2ze"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_MEDIA_TO_KEY_LIST, 1,[define when rc sends a KEY_MEDIA event for its KEY_LIST key])
fi

if test "$BOXTYPE" == "x2plus"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
fi

if test "$BOXBRAND" == "formuler" -o "$BOXBRAND" == "ax" -o "$BOXTYPE" == "sf108"; then
	AC_DEFINE(KEY_F3_TO_KEY_LIST, 1,[define when rc sends a KEY_F3 event for its KEY_LIST key])
	AC_DEFINE(KEY_LAST_TO_KEY_BACK, 1,[define when rc sends a KEY_LAST event for its KEY_BACK key])
	AC_DEFINE(KEY_BOOKMARKS_TO_KEY_MEDIA, 1,[define when rc Playlist sends a KEY_BOOKMARKS event for its KEY_MEDIA key])
	AC_DEFINE(KEY_VIDEO_TO_KEY_FAVORITES, 1,[define when rc FAV key sends a KEY_VIDEO event for its KEY_FAVORITES key])
fi

if test "$BOXTYPE" == "gb800solo" -o "$BOXTYPE" == "gb800se" -o "$BOXTYPE" == "gb800ue"; then
	AC_DEFINE(HAVE_NO_RTC, 1,[enable no RTC stuff])
fi

if test "$STBPLATFORM" == "gb7325" -o "$STBPLATFORM" == "gb7356" -o "$STBPLATFORM" == "gb7358" -o "$STBPLATFORM" == "gb7362" -o "$STBPLATFORM" == "gb73625"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_GUIDE_TO_KEY_EPG, 1,[define when rc sends a KEY_HELP event for its KEY_EPG key])
	AC_DEFINE(KEY_F2_TO_KEY_F6, 1,[define when rc sends a KEY_F2 event for its KEY_F6 key])
	AC_DEFINE(KEY_SCREEN_TO_KEY_MODE, 1,[define when rc sends a KEY_MODE event for its KEY_ASPECT key])
fi

if test "$STBPLATFORM" == "gb7252" -o "$BOXTYPE" == "gbx34k"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_GUIDE_TO_KEY_EPG, 1,[define when rc sends a KEY_HELP event for its KEY_EPG key])
	AC_DEFINE(KEY_F2_TO_KEY_F6, 1,[define when rc sends a KEY_F2 event for its KEY_F6 key])
	AC_DEFINE(KEY_SCREEN_TO_KEY_MODE, 1,[define when rc sends a KEY_MODE event for its KEY_ASPECT key])
	AC_DEFINE(KEY_CONTEXT_MENU_TO_KEY_AUX, 1,[define when rc sends a KEY_CONTEXT_MENU event for its KEY_AUX key])
fi

if test "$BOXTYPE" == "gbquad4k" -o "$BOXTYPE" == "vuuno4kse"; then
	AC_DEFINE(HAVE_COLORLCD400, 1,[define when using a 400x176 color display device])
fi

if test "$BOXTYPE" == "gbue4k"; then
	AC_DEFINE(HAVE_COLORLCD220, 1,[define when using a 220x176 color display device])
fi

if test "$BOXBRAND" == "gfutures" -o "$BOXBRAND" == "abcom"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_F3_TO_KEY_LIST, 1,[define when rc sends a KEY_F3 event for its KEY_LIST key])
fi

if test "$BOXTYPE" == "hd2400" -o "$BOXTYPE" == "vuultimo"; then
	AC_DEFINE(HAVE_BWLCD255, 1,[define when using a 255x64 black and white display device])
fi

if test "$BOXBRAND" == "ini"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(KEY_MEDIA_TO_KEY_OPEN, 1,[define when rc sends a KEY_MEDIA event for its KEY_OPEN key])
	AC_DEFINE(KEY_SEARCH_TO_KEY_WWW, 1,[define when rc sends a KEY_SEARCH event for its KEY_WWW key])
	AC_DEFINE(KEY_OPTION_TO_KEY_PC, 1,[define when rc sends a KEY_OPTION event for its KEY_PC key])
	AC_DEFINE(KEY_ZOOM_TO_KEY_SCREEN, 1,[define when rc sends a KEY_ZOOM event for its KEY_SCREEN key])
	AC_DEFINE(KEY_VIDEO_TO_KEY_MODE, 1,[define when rc sends a KEY_VIDEO event for its KEY_MODE key])
	AC_DEFINE(KEY_BOOKMARKS_TO_KEY_DIRECTORY, 1,[define when rc sends a KEY_BOOKMARKS event for its KEY_DIRECTORY key])
	AC_DEFINE(KEY_LIST_TO_KEY_PVR, 1,[define when rc sends a KEY_LIST event for its KEY_PVR key])
fi

if test "$BOXBRAND" == "ixuss"; then
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
fi

if test `echo "$BOXTYPE" | cut -b 1-7` == "mbmicro"; then
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(FORCE_NO_FILL_ACCELERATION, 1,[define when the framebuffer acceleration does not have fill support])
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
fi

if test "$BOXTYPE" == "axodin"; then
	AC_DEFINE(FORCE_ALPHABLENDING_ACCELERATION, 1,[define when the framebuffer acceleration has alphablending support, but detection slow down all])
	AC_DEFINE(KEY_POWER2_TO_KEY_WWW, 1,[define when rc sends a KEY_POWER2 event for its KEY_WWW key])
	AC_DEFINE(KEY_DIRECTORY_TO_KEY_FILE, 1,[define when rc sends a KEY_DIRECTORY event for its KEY_FILE key])
fi

if test "$BOXTYPE" == "maram9"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
fi

if test "$BOXTYPE" == "osnino" -o "$BOXTYPE" == "osninoplus" -o "$BOXTYPE" == "osninopro" -o "$STBPLATFORM" == "edision4k"; then
	AC_DEFINE(KEY_MEDIA_TO_KEY_LIST, 1,[define when rc sends a MEDIA event for its LIST])
	AC_DEFINE(KEY_VIDEO_TO_KEY_ANGLE, 1,[define when rc sends a VIDEO event for its ANGLE])
fi

if test "$STBPLATFORM" == "edision4k"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
fi

if test "$BOXTYPE" == "sf5008"; then
	AC_DEFINE(FORCE_ALPHABLENDING_ACCELERATION, 1,[define when the framebuffer acceleration has alphablending support, but detection slow down all])
	AC_DEFINE(KEY_LIST_TO_KEY_PVR, 1,[define when rc sends a KEY_LIST event for its KEY_PVR key])
fi

if test "$BOXTYPE" == "sh1" -o "$BOXTYPE" == "lc"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
fi

if test "$BOXTYPE" == "tiviarmin"; then
	AC_DEFINE(TIVIARRC, 1,[define use Tiviar RC keymap])
fi

if test "$BOXBRAND" == "dinobot"; then
	AC_DEFINE(HAVE_HISILICON, 1,[define it is a HISILICON chip])
fi

if test "$BOXBRAND" == "atto"; then
	AC_DEFINE(HAVE_HISIAPI, 1,[define we should use HISILICON API])
fi

if test "$STBPLATFORM" == "u53" -o "$STBPLATFORM" == "u532" -o "$STBPLATFORM" == "u533"; then
	AC_DEFINE(KEY_F6_TO_KEY_FAVORITES, 1,[define when rc FAV key sends a KEY_F6 event for its KEY_FAVORITES key])
	AC_DEFINE(KEY_CONTEXT_MENU_TO_KEY_BACK, 1,[define when rc MOUSE key sends a KEY_CONTEXT_MENU event for its KEY_BACK key])
	AC_DEFINE(KEY_WWW_TO_KEY_FILE, 1,[define when rc HOME key sends a KEY_WWW event for its KEY_FILE key])
	AC_DEFINE(KEY_HELP_TO_KEY_AUDIO, 1,[define when rc SETTINGS key sends a KEY_HELP event for its KEY_AUDIO key])
fi

if test "$BOXTYPE" == "tyrant" -o "$BOXTYPE" == "xcombo" -o "$STBPLATFORM" == "vg5000"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_F3_TO_KEY_LIST, 1,[define when rc sends a KEY_F3 event for its KEY_LIST key])
fi

if test "$BOXBRAND" == "vuplus"; then
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(FORCE_NO_FILL_ACCELERATION, 1,[define when the framebuffer acceleration does not have fill support])
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
	AC_DEFINE(KEY_HELP_TO_KEY_INFO, 1,[define when rc sends a KEY_HELP event we need KEY_INFO])
	AC_DEFINE(KEY_INFO_TO_KEY_EPG, 1,[define when rc sends a KEY_INFO event for its KEY_EPG key])
fi

if test "$BOXTYPE" == "vuduo2"; then
	AC_DEFINE(HAVE_BWLCD140, 1,[define when using a 140x32 black and white display device])
	AC_DEFINE(FORCE_AUTO_INV, 1,[force Inversion auto for vuplus mipsel boxes])
fi

if test "$BOXTYPE" == "vusolo4k" -o "$BOXTYPE" == "vuduo4k" -o "$BOXTYPE" == "vuduo4kse"; then
	AC_DEFINE(HAVE_COLORLCD480, 1,[define when using a 480x320 color display device])
fi

if test "$BOXTYPE" == "vuultimo4k"; then
	AC_DEFINE(HAVE_COLORLCD800, 1,[define when using a 800x480 color display device])
fi

if test "$STBPLATFORM" == "vu4kgen" -o "$BOXTYPE" == "sf4008"; then
	AC_DEFINE(VMSG_TYPE2, 1,[define vtuner_message type 2])
fi

if test "$BOXTYPE" == "vuzero" -o "$STBPLATFORM" == "vu1gen" -o "$BOXTYPE" == "vusolose" -o "$BOXTYPE" == "vusolo2"; then
	AC_DEFINE(FORCE_AUTO_INV, 1,[force Inversion auto for vuplus mipsel boxes])
fi

if test "$BOXBRAND" == "wetek" -o "$BOXTYPE" == "x8hp"; then
	AC_DEFINE(KEY_F7_TO_KEY_MENU, 1,[define when rc sends a KEY_F7 event for its KEY_MENU])
	AC_DEFINE(KEY_F1_TO_KEY_MEDIA, 1,[define when rc sends a KEY_F1 event for its KEY_MEDIA])
	AC_DEFINE(KEY_HOME_TO_KEY_INFO, 1,[define when rc sends a KEY_HOME event for its KEY_INFO])
	AC_DEFINE(KEY_BACK_TO_KEY_EXIT, 1,[define when rc sends a KEY_BACK event for its KEY_EXIT])
	AC_DEFINE(KEY_F2_TO_KEY_EPG, 1,[define when rc sends a KEY_F2 event for its KEY_EPG])
	AC_DEFINE(KEY_ENTER_TO_KEY_OK, 1,[define when rc sends a KEY_ENTER event for its KEY_OK])
	AC_DEFINE(WETEKRC, 1, [WeTek remote uses BACKSPACE to toggle extended functions on numeric buttons])
fi

if test "$STBPLATFORM" == "mipsspycat" -o "$BOXTYPE" == "osmini" -o "$BOXTYPE" == "osminiplus" -o "$BOXTYPE" == "osmega" -o "$STBPLATFORM" == "4kspycat"; then
	AC_DEFINE(KEY_MEDIA_TO_KEY_LIST, 1,[define when rc sends a MEDIA event for its LIST])
fi

AC_CHECK_HEADERS([sys/klog.h])
AC_CHECK_FUNCS([klogctl])

AC_CHECK_HEADERS([shadow.h])
AC_CHECK_LIB([crypt], [crypt], [BASE_LIBS+=" -lcrypt"], [AC_MSG_ERROR([Could not find crypt])])
AC_CHECK_LIB([rt], [clock_gettime], [BASE_LIBS+=" -lrt"], [AC_MSG_ERROR([Could not find rt])])

ENIGMA2_CFLAGS="-fno-rtti -fno-exceptions -rdynamic -funwind-tables"
AC_SUBST(ENIGMA2_CFLAGS)

AX_CXX_COMPILE_STDCXX_11([ext],[mandatory])

AX_CHECK_COMPILE_FLAG([-Wattribute-alias], [CXXFLAGS="$CXXFLAGS -Wattribute-alias"])
AX_CHECK_COMPILE_FLAG([-Wattribute-alias=1], [CXXFLAGS="$CXXFLAGS -Wattribute-alias=1"])

CPPFLAGS="$CPPFLAGS $PYTHON_CPPFLAGS"
CFLAGS="$CFLAGS -Wall"
CXXFLAGS="$CXXFLAGS -Wall -Wextra \
	-Wformat=2 -Wformat-overflow=2 -Wformat-nonliteral -Wformat-security \
	-Wimplicit-fallthrough=5 -Wduplicated-branches -Wtrampolines \
	-Wdangling-else -Wshift-overflow=2 -Wswitch \
	-Wunused-but-set-parameter -Wunused-const-variable=1 -Wuninitialized \
	-Wstringop-overflow=3 -Woverlength-strings -Wno-error=deprecated-declarations \
	-Wunsafe-loop-optimizations -Wpointer-arith \
	-Wfloat-equal -Wlogical-op \
	-Wno-error=cast-align=strict -Wno-error=ignored-qualifiers \
	-Wno-error=cast-function-type \
	-Wno-error=stringop-truncation -Wno-error=shadow -Wno-error=cast-qual \
	-Wno-error=aggregate-return -Wno-error=missing-field-initializers \
	-Wno-error=packed -Wno-error=vla -Wno-error=clobbered -Wno-error=unused-parameter \
	$BASE_CFLAGS $ENIGMA2_CFLAGS $PTHREAD_CFLAGS $OPENMP_CFLAGS $ALSA_CFLAGS \
	$GLES_CFLAGS $AMCODEC_CFLAGS $AMADEC_CFLAGS $DVBCSA_CFLAGS"

AC_CONFIG_FILES([
Makefile
data/Makefile
data/fonts/Makefile
data/countries/Makefile
data/display/Makefile
data/display/7segment/Makefile
data/display/display/Makefile
data/display/display96/Makefile
data/display/display128/Makefile
data/display/display128dm/Makefile
data/display/display220/Makefile
data/display/display390/Makefile
data/display/display400/Makefile
data/display/display480/Makefile
data/display/display720/Makefile
data/display/display800/Makefile
data/display/displaytext/Makefile
data/display/grautec70x0/Makefile
data/display/grautec70x0/fonts/Makefile
data/display/grautec8000/Makefile
data/display/grautec8000/fonts/Makefile
data/display/vfd128/Makefile
data/display/vfd140/Makefile
data/display/vfd255/Makefile
data/extensions/Makefile
data/keymaps/Makefile
data/skin_default/Makefile
data/skin_default/menu/Makefile
data/skin_default/icons/Makefile
data/skin_default/buttons/Makefile
data/skin_default/epg/Makefile
data/skin_default/LCDIcons/Makefile
data/skin_fallback_1080/Makefile
data/skin_fallback_1080/buttons/Makefile
data/skin_fallback_1080/icons/Makefile
include/Makefile
lib/Makefile
lib/base/eenv.cpp
lib/python/Makefile
lib/python/Components/Makefile
lib/python/Components/Converter/Makefile
lib/python/Components/Renderer/Makefile
lib/python/Components/Sources/Makefile
lib/python/Screens/Makefile
lib/python/Plugins/Makefile
lib/python/Plugins/SystemPlugins/AnimationSetup/Makefile
lib/python/Plugins/SystemPlugins/CableScan/Makefile
lib/python/Plugins/SystemPlugins/FastChannelChange/Makefile
lib/python/Plugins/SystemPlugins/FastChannelChange/meta/Makefile
lib/python/Plugins/SystemPlugins/FastScan/Makefile
lib/python/Plugins/SystemPlugins/OSDPositionSetup/Makefile
lib/python/Plugins/SystemPlugins/OSD3DSetup/Makefile
lib/python/Plugins/SystemPlugins/HdmiCEC/Makefile
lib/python/Plugins/SystemPlugins/VideoClippingSetup/Makefile
lib/python/Plugins/Extensions/CutListEditor/Makefile
lib/python/Plugins/Extensions/CutListEditor/meta/Makefile
lib/python/Plugins/Extensions/DVDBurn/Makefile
lib/python/Plugins/Extensions/DVDBurn/meta/Makefile
lib/python/Plugins/Extensions/DVDPlayer/Makefile
lib/python/Plugins/Extensions/DVDPlayer/meta/Makefile
lib/python/Plugins/Extensions/GraphMultiEPG/Makefile
lib/python/Plugins/Extensions/GraphMultiEPG/meta/Makefile
lib/python/Plugins/Extensions/Makefile
lib/python/Plugins/Extensions/MediaPlayer/Makefile
lib/python/Plugins/Extensions/MediaPlayer/meta/Makefile
lib/python/Plugins/Extensions/MediaScanner/Makefile
lib/python/Plugins/Extensions/MediaScanner/meta/Makefile
lib/python/Plugins/Extensions/PicturePlayer/Makefile
lib/python/Plugins/Extensions/PicturePlayer/meta/Makefile
lib/python/Plugins/Extensions/PicturePlayer/data/Makefile
lib/python/Plugins/Extensions/SocketMMI/Makefile
lib/python/Plugins/Extensions/SocketMMI/meta/Makefile
lib/python/Plugins/Extensions/SocketMMI/src/Makefile
lib/python/Plugins/SystemPlugins/CommonInterfaceAssignment/Makefile
lib/python/Plugins/SystemPlugins/CommonInterfaceAssignment/meta/Makefile
lib/python/Plugins/SystemPlugins/DefaultServicesScanner/Makefile
lib/python/Plugins/SystemPlugins/DefaultServicesScanner/meta/Makefile
lib/python/Plugins/SystemPlugins/DiseqcTester/Makefile
lib/python/Plugins/SystemPlugins/DiseqcTester/meta/Makefile
lib/python/Plugins/SystemPlugins/Hotplug/Makefile
lib/python/Plugins/SystemPlugins/Hotplug/meta/Makefile
lib/python/Plugins/SystemPlugins/Makefile
lib/python/Plugins/SystemPlugins/TempFanControl/Makefile
lib/python/Plugins/SystemPlugins/TempFanControl/meta/Makefile
lib/python/Plugins/SystemPlugins/NetworkWizard/Makefile
lib/python/Plugins/SystemPlugins/NetworkWizard/meta/Makefile
lib/python/Plugins/SystemPlugins/PositionerSetup/Makefile
lib/python/Plugins/SystemPlugins/PositionerSetup/meta/Makefile
lib/python/Plugins/SystemPlugins/SatelliteEquipmentControl/Makefile
lib/python/Plugins/SystemPlugins/SatelliteEquipmentControl/meta/Makefile
lib/python/Plugins/SystemPlugins/Satfinder/Makefile
lib/python/Plugins/SystemPlugins/Satfinder/meta/Makefile
lib/python/Plugins/SystemPlugins/SoftwareManager/Makefile
lib/python/Plugins/SystemPlugins/SoftwareManager/meta/Makefile
lib/python/Plugins/SystemPlugins/VideoEnhancement/Makefile
lib/python/Plugins/SystemPlugins/VideoEnhancement/meta/Makefile
lib/python/Plugins/SystemPlugins/VideoTune/Makefile
lib/python/Plugins/SystemPlugins/VideoTune/meta/Makefile
lib/python/Plugins/SystemPlugins/Videomode/Makefile
lib/python/Plugins/SystemPlugins/Videomode/meta/Makefile
lib/python/Plugins/SystemPlugins/WirelessLan/Makefile
lib/python/Plugins/SystemPlugins/WirelessLan/meta/Makefile
lib/python/Tools/Makefile
main/Makefile
tools/Makefile
tools/enigma2.sh
enigma2.pc
])
AC_OUTPUT
