#ifndef __FB_H
#define __FB_H

#include <lib/base/eerror.h>
#include <linux/fb.h>

#ifndef FB_DEV
# define FB_DEV "/dev/fb0"
#endif

#ifdef HAVE_HISIAPI
	typedef struct hiRECT_S
	{
		int s32X;
		int s32Y;
		int s32Width;
		int s32Height;
	} HI_RECT_S;

	typedef struct hiDISP_VIRTSCREEN_S
	{
		int enDisp;
		HI_RECT_S stVirtScreen;
	} DISP_VIRTSCREEN_S;

	#define HI_ID_DISP 34
	#define IOC_DISP_SET_VIRTSCREEN 12
	#define CMD_DISP_SET_VIRTSCREEN _IOW(HI_ID_DISP, IOC_DISP_SET_VIRTSCREEN, DISP_VIRTSCREEN_S)
#endif

class fbClass
{
	int fbFd;
#ifdef HAVE_HISIAPI
	int fdDisp;
#endif
	int xRes, yRes, stride, bpp;
	int available;
	struct fb_var_screeninfo screeninfo;
	fb_cmap cmap;
	uint16_t red[256], green[256], blue[256], trans[256];
	static fbClass *instance;
	int locked;

	int m_manual_blit;
	int m_number_of_pages;
	int m_phys_mem;
#ifdef SWIG
	fbClass(const char *fb=FB_DEV);
	~fbClass();
public:
#else
public:
	unsigned char *lfb;
#ifdef CONFIG_ION
	int m_accel_fd;
#endif
	void enableManualBlit();
	void disableManualBlit();
	int showConsole(int state);
	int SetMode(int xRes, int yRes, int bpp);
	void getMode(int &xres, int &yres, int &bpp);
	int Available() { return available; }

	int getNumPages() { return m_number_of_pages; }

	unsigned long getPhysAddr() { return m_phys_mem; }

	int setOffset(int off);
	int waitVSync();
	void blit();
	unsigned int Stride() { return stride; }
	fb_cmap *CMAP() { return &cmap; }

	fbClass(const char *fb=FB_DEV);
	~fbClass();

			// low level gfx stuff
	int PutCMAP();
#endif
	static fbClass *getInstance();

	int lock();
	void unlock();
	int islocked() { return locked; }
};

#endif
