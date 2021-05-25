Enigma2 Kernel Module
=====================

This module is a replacement for all exisiting hardware checks, it replaces 
boxbranding, enigma2 internal methods like getBoxType().  This feature is 
implemented via SystemInfo.  This is intended to be a single entry point 
for accessing and managing all hardware and system data.

This data is accessed and managed via the BoxInfo class within SystemInfo.py. 
Unlike the SystemInfo dictionary the data is contained and isolated within 
the SystemInfo module.  There is no need to export or share the dictionary 
across Enigma2 modules.

Enigma2 internal calls needs enigma2 to work first so can't be used outside it and boxbranding works if you import it so not a good solution for shell scripts and anything other than python.

Enigma2 kernel module is a pre-compiled .ko file which contains needed information about hardware features, as it's a compiled file it's secure and can't be changed later.

The module creates so many proc files which could be read with any language and in case of any failiure or multiboot situation we read the module description instead of relying on the proc files so "modinfo -d" will help us.

Current enigma2 reads the module via SystemInfo.py and current proc path is "/proc/enigma" and the module name is "enigma.ko" which could be changed if all teams agree on something.

OV's boxbranding is different although it's based on OE-A's sources but has some extra calls and some removed, also we have different names in OV, as the module is a replacement for boxbranding also we tried to have similar names but lets see what replaces what:

/proc/enigma/model replaces getBoxType (getMachineName and getMachineMake in OE-A's boxbranding)
/proc/enigma/displaymodel repalces getDisplayModel
/proc/enigma/brand replaces getBoxBrand (getMachineBrand and getBrandOEM in OE-A's boxbranding)
/proc/enigma/displaybrand replaces getDisplayBrand
/proc/enigma/platform replaces getMachineBuild
/proc/enigma/imgversion replaces getIMGVersion
/proc/enigma/imgrevision replaces getIMGRevision
/proc/enigma/imglanguage replaces getIMGLanguage
/proc/enigma/developername replaces getDeveloperName
/proc/enigma/feedsurl replaces getFeedsUrl
/proc/enigma/distro replaces getImageDistro
/proc/enigma/oe replaces getOEVersion
/proc/enigma/kernel replaces getKernelVersion
/proc/enigma/python
/proc/enigma/mediaservice replaces getE2Service
/proc/enigma/multilib replaces getHaveMultiLib
/proc/enigma/architecture replaces getImageArch
/proc/enigma/socfamily replaces getSoCFamily
/proc/enigma/blindscanbinary replaces getBlindscanBin
/proc/enigma/rctype replaces getRCType
/proc/enigma/rcname repalces getRCName
/proc/enigma/rcidnum replaces getRCIDNum
/proc/enigma/smallflash replaces getHaveSmallFlash
/proc/enigma/middleflash replaces getHaveMiddleFlash
/proc/enigma/imagedir replaces getImageFolder
/proc/enigma/imagefs replaces getImageFileSystem
/proc/enigma/mtdbootfs replaces getMachineMtdBoot
/proc/enigma/mtdrootfs replaces getMachineMtdRoot
/proc/enigma/mtdkernel replaces getMachineMtdKernel
/proc/enigma/rootfile repalces getMachineRootFile
/proc/enigma/kernelfile replaces getMachineKernelFile
/proc/enigma/mkubifs replaces getMachineMKUBIFS
/proc/enigma/ubinize replaces getMachineUBINIZE
/proc/enigma/forcemode replaces getForceMode
/proc/enigma/compiledate
/proc/enigma/fpu replaces getImageFPU
/proc/enigma/displaytype replaces getDisplayType
/proc/enigma/transcoding replaces getHaveTranscoding (getHaveTranscoding1 in OE-A's boxbranding)
/proc/enigma/multitranscoding replaces getHaveMultiTranscoding (getHaveTranscoding2 in OE-A's boxbranding)
/proc/enigma/hdmi replaces getHaveHDMI
/proc/enigma/yuv replaces getHaveYUV
/proc/enigma/rca replaces getHaveRCA
/proc/enigma/avjack replaces getHaveAVJACK
/proc/enigma/scart replaces getHaveSCART
/proc/enigma/dvi replaces getHaveDVI
/proc/enigma/svideo replaces getHaveSVIDEO
/proc/enigma/hdmihdin replaces getHaveHDMIinHD
/proc/enigma/hdmifhdin replaces getHaveHDMIinFHD
/proc/enigma/wol replaces getHaveWOL (Also getHaveWWOL in OE-A's boxbranding as we don't split Wake-on-LAN and Wake-on-WLAN)
/proc/enigma/ci replaces getHaveCI
/proc/enigma/vfdsymbol replaces getHaveVFDSymbol
/proc/enigma/fhdskin replaces getFHDSkin
/proc/enigma/dboxlcd replaces getDBoxLCD
/proc/enigma/imageversion replaces getImageVersion
/proc/enigma/imagebuild replaces getImageBuild
/proc/enigma/imagedevbuild replaces getImageDevBuild
/proc/enigma/imagetype replaces getImageType

* Replacement for getMachineProcModel is getBoxProc in StbHardware.py
* Replacement for OE-A's boxbranding getDriverDate is getDriverInstalledDate in About.py (Components)
* Replacement for OE-A's boxbranding getHaveMiniTV is LCDMiniTV in SystemInfo.py
* We don't have anything for OE-A's boxbranding getHaveSCARTYUV and we manage it via if conditions in VideoHardware.py

Time to explain each one and give examples (all proc files and modinfo data are immutable):

model:
	BoxInfo.getItem("model") (/proc/enigma/model)

	This variable defines the receiver model in OE sources.
	Real model could be a different thing in real life and this
	is only what kernel defconfig shows as hostname.

	Example: h9

displaymodel:
	BoxInfo.getItem("displaymodel") (/proc/enigma/displaymodel)

	This variable defines the receiver real model in real life.
	Real model is what printed on the receiver.

	Example: H9T

brand:
	BoxInfo.getItem("brand") (/proc/enigma/brand)

	This variable defines the receiver brand or the meta name in OE sources.
	Real brand could be a different thing in real life, also
	not all the times it's the brand name but sometimes it's the meta name so
	it's related to OE sources.

	Example: airdigital

displaybrand:
	BoxInfo.getItem("displaybrand") (/proc/enigma/displaybrand)

	This variable defines the receiver real brand in real life.
	Real brand is what printed on the receiver.

	Example: Zgemma

platform:
	BoxInfo.getItem("platform") (/proc/enigma/platform)

	This variable defines the receiver platform in OE sources.
	This is not a real thing, it's what developers call a family of similar hardwares.
	Instead of checking models one by one we could assing something to a family and reduce the checks.
	If a model does not belong to a family the platform will be same as model so model and platform
	are equal in some receivers.

	Example: zgemmahisi3798mv200

imgversion:
	BoxInfo.getItem("imgversion") (/proc/enigma/imgversion)

	This variable defines the main image version which only changes when GCC changes or
	when other important packages like python get updated.

	Example: 10.3

imgrevision:
	BoxInfo.getItem("imgrevision") (/proc/enigma/imgrevision)

	This variable defines the image revision which changes after a batch of changes.

	Example: r396

imglanguage:
	BoxInfo.getItem("imglanguage") (/proc/enigma/imglanguage)

	This variable defines the language set which could be english, multilanguage or
	extralanguage (which has all) depend on the flash size.
	multilanguage has ar, de, es, it, ru and tr locales.

	Example: extralanguage

developername:
	BoxInfo.getItem("developername") (/proc/enigma/developername)

	This variable defines who compiled the image which could be a real developer or
	just a certified compiler, some image compilers add/remove things and with
	this variable we know which one has what packages.

	Example: persianpros

feedsurl:
	BoxInfo.getItem("feedsurl") (/proc/enigma/feedsurl)

	This variable defines the main feed URL for opkg.

	Example: https://feeds.openenigma.org

distro:
	BoxInfo.getItem("distro") (/proc/enigma/distro)

	This variable defines the image distro.
	Mostly we use this for multiboot tools.

	Example: openvision

oe:
	BoxInfo.getItem("oe") (/proc/enigma/oe)

	This variable defines the OE branch.
	If it's anything other than "master" means it's fixed on a specific branch like pyro and
	there will be no more updates from main OE and requires only monthly maintenance to
	keep it up-to-date with other sources.

	Example: master

oe:
	BoxInfo.getItem("oe") (/proc/enigma/oe)

	This variable defines the OE branch.
	If it's anything other than "master" means it's fixed on a specific branch like pyro and
	there will be no more updates from main OE and requires only monthly maintenance to
	keep it up-to-date with other sources.
	Mostly we use it to determine which version of a tool should be used.

	Example: master

kernel:
	BoxInfo.getItem("kernel") (/proc/enigma/kernel)

	This variable defines the kernel version.
	Let us know what version of the kernel a receiver has so what features are compatible.

	Example: 4.4.35

python:
	BoxInfo.getItem("python") (/proc/enigma/python)

	This variable defines the python exact version.

	Example: 2.7.18

mediaservice:
	BoxInfo.getItem("mediaservice") (/proc/enigma/mediaservice)

	This variable defines the enigma2 media service.

	Example: enigma2-plugin-systemplugins-servicehisilicon

multilib:
	BoxInfo.getItem("multilib") (/proc/enigma/multilib)

	This variable defines the multilib situation.
	It can only be True if an image has aarch64 architecture and
	lib64 is available in the root direcotry.

	Example: False

architecture:
	BoxInfo.getItem("architecture") (/proc/enigma/architecture)

	This variable defines the main architecture of the image.
	Useful when we want to know what kind of ipk files we can install on a receiver via opkg or
	what type of binary files we could run.

	Example: cortexa15hf-neon-vfpv4

socfamily:
	BoxInfo.getItem("socfamily") (/proc/enigma/socfamily)

	This variable defines the SoC type.
	Some settings could be applied per SoC as they're CPU dependent.

	Example: hisi3798mv200

blindscanbinary:
	BoxInfo.getItem("blindscanbinary") (/proc/enigma/blindscanbinary)

	This variable defines the blindscan binary file name.
	We use this for blindscan tools.

	Example: blindscan

rctype:
	BoxInfo.getItem("rctype") (/proc/enigma/rctype)

	This variable defines the remote control type.

	Example: 28

rcname:
	BoxInfo.getItem("rcname") (/proc/enigma/rcname)

	This variable defines the remote control name which we use for xml and png files.

	Example: zgemma6

rcidnum:
	BoxInfo.getItem("rcidnum") (/proc/enigma/rcidnum)

	This variable defines the remote control ID number.
	In rc xml files we have a line like <rc id="2"> which define what ID number could be used.

	Example: 2

smallflash:
	BoxInfo.getItem("smallflash") (/proc/enigma/smallflash)

	This variable defines the flash size and if it's equal to 64MB or less than that.
	We use this to compile compatible images for small flash receivers.

	Example: False

middleflash:
	BoxInfo.getItem("middleflash") (/proc/enigma/middleflash)

	This variable defines the flash size and if it's equal to 128MB or less but more than 64MB.
	Even some receivers with 128MB flashes can not flash or boot images more than 96MB because of a
	limit in their CFE.
	We use this to compile compatible images for middle flash receivers.

	Example: False

imagedir:
	BoxInfo.getItem("imagedir") (/proc/enigma/imagedir)

	This variable defines the image directory for a receiver
	and how the structure of the zip file should be.
	Mostly we use this for backup tools.

	Example: h9

imagefs:
	BoxInfo.getItem("imagefs") (/proc/enigma/imagefs)

	This variable defines the image filesystem for a receiver which can boot.
	Mostly we use this for backup tools.

	Example: ubi (sometimes there's a space at the beginning of this variable which should be avoided)

mtdbootfs:
	BoxInfo.getItem("mtdbootfs") (/proc/enigma/mtdbootfs)

	This variable defines the boot filesystem mtd number of an image.
	Mostly we use this for backup/multiboot tools.

	Example: mmcblk0p4 (for h9 this is empty and I just wrote an example)

mtdrootfs:
	BoxInfo.getItem("mtdrootfs") (/proc/enigma/mtdrootfs)

	This variable defines the root filesystem mtd number of an image.
	Mostly we use this for backup/multiboot tools.

	Example: mtd7

mtdkernel:
	BoxInfo.getItem("mtdkernel") (/proc/enigma/mtdkernel)

	This variable defines the kernel mtd number of an image.
	Mostly we use this for backup/multiboot tools.

	Example: mtd6

rootfile:
	BoxInfo.getItem("rootfile") (/proc/enigma/rootfile)

	This variable defines the root file name of an image.
	Mostly we use this for backup/multiboot tools.

	Example: rootfs.ubi

kernelfile:
	BoxInfo.getItem("kernelfile") (/proc/enigma/kernelfile)

	This variable defines the kernel file name of an image.
	Mostly we use this for backup tools.

	Example: uImage

mkubifs:
	BoxInfo.getItem("mkubifs") (/proc/enigma/mkubifs)

	This variable defines the mkubifs command parameters.
	Mostly we use this for backup tools when want to repack the image.

	Example: -m 2048 -e 126976 -c 8192

ubinize:
	BoxInfo.getItem("ubinize") (/proc/enigma/ubinize)

	This variable defines the ubinize command parameters.
	Mostly we use this for backup tools when want to repack the image.

	Example: -m 2048 -p 128KiB

forcemode:
	BoxInfo.getItem("forcemode") (/proc/enigma/forcemode)

	This variable defines the force mode of the zip file.
	Some receivers won't flash without enabling the force mode.
	Mostly we use this for backup tools.

	Example: no

compiledate:
	BoxInfo.getItem("compiledate") (/proc/enigma/compiledate)

	This variable defines the compile date of the enigma.ko file.

	Example: 20210524

fpu:
	BoxInfo.getItem("fpu") (/proc/enigma/fpu)

	This variable defines the fpu type which is the float type of the architecure and
	it's CPU dependent.

	Example: hard

displaytype:
	BoxInfo.getItem("displaytype") (/proc/enigma/displaytype)

	This variable defines the front display type of a receiver.

	Example: colorlcd400 (for h9 this is empty and I just wrote an example)

transcoding:
	BoxInfo.getItem("transcoding") (/proc/enigma/transcoding)

	This variable defines if a receiver supports transcoding feature.

	Example: False

multitranscoding:
	BoxInfo.getItem("multitranscoding") (/proc/enigma/multitranscoding)

	This variable defines if a receiver supports multi transcoding feature.

	Example: True

hdmi:
	BoxInfo.getItem("hdmi") (/proc/enigma/hdmi)

	This variable defines if a receiver has HDMI output.

	Example: True

yuv:
	BoxInfo.getItem("yuv") (/proc/enigma/yuv)

	This variable defines if a receiver has YUV output.

	Example: False

rca:
	BoxInfo.getItem("rca") (/proc/enigma/rca)

	This variable defines if a receiver has RCA output.

	Example: False

avjack:
	BoxInfo.getItem("avjack") (/proc/enigma/avjack)

	This variable defines if a receiver has AV Jack output.

	Example: False

scart:
	BoxInfo.getItem("scart") (/proc/enigma/scart)

	This variable defines if a receiver has SCART output.

	Example: False

dvi:
	BoxInfo.getItem("dvi") (/proc/enigma/dvi)

	This variable defines if a receiver has DVI output.

	Example: False

svideo:
	BoxInfo.getItem("svideo") (/proc/enigma/svideo)

	This variable defines if a receiver has S-Video output.

	Example: False

hdmihdin:
	BoxInfo.getItem("hdmihdin") (/proc/enigma/hdmihdin)

	This variable defines if a receiver has HDMI-In input.

	Example: False

hdmifhdin:
	BoxInfo.getItem("hdmifhdin") (/proc/enigma/hdmifhdin)

	This variable defines if a receiver has HDMI-In (Full HD) input.

	Example: False

wol:
	BoxInfo.getItem("wol") (/proc/enigma/wol)

	This variable defines if a receiver supports Wake-on-LAN/WLAN feature.

	Example: True

ci:
	BoxInfo.getItem("ci") (/proc/enigma/ci)

	This variable defines if a receiver has DVB Common Interface slot.

	Example: True

vfdsymbol:
	BoxInfo.getItem("vfdsymbol") (/proc/enigma/vfdsymbol)

	This variable defines if a receiver supports VFD symbol feature.
	It depends on the display type also.

	Example: False

fhdskin:
	BoxInfo.getItem("fhdskin") (/proc/enigma/fhdskin)

	This variable defines if a receiver supports Full HD skins.

	Example: True

dboxlcd:
	BoxInfo.getItem("dboxlcd") (/proc/enigma/dboxlcd)

	This variable defines if a receiver supports eDBoxLCD enigma2 feature.

	Example: True

imageversion:
	BoxInfo.getItem("imageversion") (/proc/enigma/imageversion)

	This variable defines the image version.
	Mostly we use this for backup tools and compatibility with other images.

	Example: develop

imagebuild:
	BoxInfo.getItem("imagebuild") (/proc/enigma/imagebuild)

	This variable defines the image build.
	Mostly we use this for backup tools and compatibility with other images.

	Example: master

imagedevbuild:
	BoxInfo.getItem("imagedevbuild") (/proc/enigma/imagedevbuild)

	This variable defines the image developer build.
	Mostly we use this for backup tools and compatibility with other images.

	Example: new

imagetype:
	BoxInfo.getItem("imagetype") (/proc/enigma/imagetype)

	This variable defines the image type.
	Mostly we use this for backup tools and compatibility with other images.

	Example: release
