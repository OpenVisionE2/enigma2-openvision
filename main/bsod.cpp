#include <sys/klog.h>
#include <vector>
#include <csignal>
#include <fstream>
#include <sstream>
#ifdef __GLIBC__
#include <execinfo.h>
#endif
#include <dlfcn.h>
#include <lib/base/eenv.h>
#include <lib/base/eerror.h>
#include <lib/base/esimpleconfig.h>
#include <lib/base/nconfig.h>
#include <lib/gdi/gmaindc.h>
#include <asm/ptrace.h>
#include "version_info.h"

#ifdef AZBOX
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#endif

/************************************************/

static const char *crash_emailaddr =
#ifndef CRASH_EMAILADDR
	"the Open Vision forum (https://forum.openvision.tech) or https://github.com/OpenVisionE2";
#else
	CRASH_EMAILADDR;
#endif

/* Defined in eerror.cpp */
void retrieveLogBuffer(const char **p1, unsigned int *s1, const char **p2, unsigned int *s2);

static const std::string getConfigString(const char* key, const char* defaultValue)
{
	std::string value = eConfigManager::getConfigValue(key);

	//we get at least the default value if python is still alive
	if (!value.empty())
		return value;

	return eSimpleConfig::getString(key, defaultValue);
}

/* get the kernel log aka dmesg */
static void getKlog(FILE* f)
{
	fprintf(f, "\n\ndmesg\n\n");

	ssize_t len = klogctl(10, NULL, 0); /* read ring buffer size */
	if (len == -1)
	{
		fprintf(f, "Error reading klog %d - %m\n", errno);
		return;
	}
	else if(len == 0)
	{
		return;
	}

	std::vector<char> buf(len, 0);

	len = klogctl(4, &buf[0], len); /* read and clear ring buffer */
	if (len == -1)
	{
		fprintf(f, "Error reading klog %d - %m\n", errno);
		return;
	}

	buf.resize(len);
	fprintf(f, "%s\n", &buf[0]);
}

static void stringFromFile(FILE* f, const char* context, const char* filename)
{
	std::ifstream in(filename);

	if (in.good()) {
		std::string line;
		std::getline(in, line);
		fprintf(f, "%s=%s\n", context, line.c_str());
	}
}

static bool bsodhandled = false;

void bsodFatal(const char *component)
{
#ifdef AZBOX
	if (!component)
	{
		/* Azbox Sigma mode check, switch back from player mode to normal mode if player Python code crashed and enigma2 restart */		
		int val=0;
		FILE *f = fopen("/proc/player_status", "r");
		if (f)
		{		
			fscanf(f, "%d", &val);
			fclose(f);
		}
		if(val)
		{
			int rmfp_fd = open("/tmp/rmfp.kill", O_CREAT);
			if(rmfp_fd > 0) 
			{
				int t = 50;
				close(rmfp_fd);
				while(access("/tmp/rmfp.kill", F_OK) >= 0 && t--) {
				usleep(10000);
				}
			}		
			f = fopen("/proc/player", "w");
			if (f)
			{		
				fprintf(f, "%d", 1);
				fclose(f);
			}
		}
	}
#endif
	/* show no more than one bsod while shutting down/crashing */
	if (bsodhandled) {
		if (component) {
			sleep(1);
			raise(SIGKILL);
		}
		return;
	}
	bsodhandled = true;

	if (!component)
		component = "Enigma2";

	/* Retrieve current ringbuffer state */
	const char* logp1 = NULL;
	unsigned int logs1 = 0;
	const char* logp2 = NULL;
	unsigned int logs2 = 0;
	retrieveLogBuffer(&logp1, &logs1, &logp2, &logs2);

	FILE *f;
	std::string crashlog_name;
	std::ostringstream os;
	time_t t = time(0);
	struct tm tm;
	char tm_str[32];
	localtime_r(&t, &tm);
	strftime(tm_str, sizeof(tm_str), "%Y-%m-%d_%H-%M-%S", &tm);
	os << getConfigString("config.crash.debugPath", "/home/root/logs/");
	os << "enigma2_crash_";
	os << tm_str;
	os << ".log";
	crashlog_name = os.str();
	f = fopen(crashlog_name.c_str(), "wb");

	if (f == NULL)
	{
		/* No hardisk. If there is a crash log in /home/root, leave it
		 * alone because we may be in a crash loop and writing this file
		 * all night long may damage the flash. Also, usually the first
		 * crash log is the most interesting one. */
		crashlog_name = "/home/root/logs/enigma2_crash.log";
		if ((access(crashlog_name.c_str(), F_OK) == 0) ||
		    ((f = fopen(crashlog_name.c_str(), "wb")) == NULL))
		{
			/* Re-write the same file in /tmp/ because it's expected to
			 * be in RAM. So the first crash log will end up in /home
			 * and the last in /tmp */
			crashlog_name = "/tmp/enigma2_crash.log";
			f = fopen(crashlog_name.c_str(), "wb");
		}
	}

	if (f)
	{
		time_t t = time(0);
		struct tm tm = {};
		char tm_str[32] = {};

		localtime_r(&t, &tm);
		strftime(tm_str, sizeof(tm_str), "%a %b %_d %T %Y", &tm);

		fprintf(f,
			"Open Vision enigma2 crash log\n\n"
			"crashdate=%s\n"
			"compiledate=%s\n"
			"skin=%s\n"
			"sourcedate=%s\n"
			"branch=%s\n"
			"rev=%s\n"
			"component=%s\n\n",
			tm_str,
			__DATE__,
			getConfigString("config.skin.primary_skin", "Default Skin").c_str(),
			enigma2_date,
			enigma2_branch,
			enigma2_rev,
			component);

		stringFromFile(f, "stbmodel", "/etc/openvision/model");
		stringFromFile(f, "stbbrand", "/etc/openvision/brand");
		stringFromFile(f, "stbplatform", "/etc/openvision/platform");
		stringFromFile(f, "friendlyfamily", "/etc/openvision/friendlyfamily");
		stringFromFile(f, "socfamily", "/etc/openvision/socfamily");
		stringFromFile(f, "architecture", "/etc/openvision/architecture");
		stringFromFile(f, "kernel", "/etc/openvision/kernel");
		stringFromFile(f, "kernelcmdline", "/proc/cmdline");
		stringFromFile(f, "driverdate", "/etc/openvision/driverdate");
		stringFromFile(f, "nimsockets", "/proc/bus/nim_sockets");
		stringFromFile(f, "distro", "/etc/openvision/distro");
		stringFromFile(f, "oe", "/etc/openvision/oe");
		stringFromFile(f, "mediaservice", "/etc/openvision/mediaservice");
		stringFromFile(f, "visionversion", "/etc/openvision/visionversion");
		stringFromFile(f, "visionrevision", "/etc/openvision/visionrevision");
		stringFromFile(f, "visionlanguage", "/etc/openvision/visionlanguage");
		stringFromFile(f, "rctype", "/etc/openvision/rctype");
		stringFromFile(f, "rcname", "/etc/openvision/rcname");
		stringFromFile(f, "rcidnum", "/etc/openvision/rcidnum");
		stringFromFile(f, "compiledby", "/etc/openvision/developername");
		stringFromFile(f, "feedsurl", "/etc/openvision/feedsurl");
		stringFromFile(f, "binutils", "/etc/openvision/binutils");
		stringFromFile(f, "busybox", "/etc/openvision/busybox");
		stringFromFile(f, "ffmpeg", "/etc/openvision/ffmpeg");
		stringFromFile(f, "gcc", "/etc/openvision/gcc");
		stringFromFile(f, "glibc", "/etc/openvision/glibc");
		stringFromFile(f, "gstreamer", "/etc/openvision/gstreamer");
		stringFromFile(f, "openssl", "/etc/openvision/openssl");
		stringFromFile(f, "python", "/etc/openvision/python");

		/* dump the log ringbuffer */
		fprintf(f, "\n\n");
		if (logp1)
			fwrite(logp1, 1, logs1, f);
		if (logp2)
			fwrite(logp2, 1, logs2, f);

		/* dump the kernel log */
		getKlog(f);

		fclose(f);
	}

	ePtr<gMainDC> my_dc;
	gMainDC::getInstance(my_dc);

	gPainter p(my_dc);
	p.resetOffset();
	p.resetClip(eRect(ePoint(0, 0), my_dc->size()));
	p.setBackgroundColor(gRGB(0x008000));
	p.setForegroundColor(gRGB(0xFFFFFF));

	int hd =  my_dc->size().width() == 1920;
	ePtr<gFont> font = new gFont("Regular", hd ? 30 : 20);
	p.setFont(font);
	p.clear();

	eRect usable_area = eRect(hd ? 30 : 100, hd ? 30 : 70, my_dc->size().width() - (hd ? 60 : 150), hd ? 150 : 100);

	os.str("");
	os.clear();
	os << "We are really sorry. Your STB encountered "
		"a software problem, and needs to be restarted.\n"
		"Please send the logfile " << crashlog_name << " to " << crash_emailaddr << ".\n"
		"Better to enable Twisted log after and send us the twisted.log also.\n"
		"Your STB restarts in 10 seconds!\n"
		"Component: " << component;

	p.renderText(usable_area, os.str().c_str(), gPainter::RT_WRAP|gPainter::RT_HALIGN_LEFT);

	std::string logtail;
	int lines = 20;
	
	if (logp2)
	{
		unsigned int size = logs2;
		while (size) {
			const char* r = (const char*)memrchr(logp2, '\n', size);
			if (r) {
				size = r - logp2;
				--lines;
				if (!lines) {
					logtail = std::string(r, logs2 - size);
					break;
				} 
			}
			else {
				logtail = std::string(logp2, logs2);
				break;
			}
		}
	}

	if (lines && logp1)
	{
		unsigned int size = logs1;
		while (size) {
			const char* r = (const char*)memrchr(logp1, '\n', size);
			if (r) {
				--lines;
				size = r - logp1;
				if (!lines) {
					logtail += std::string(r, logs1 - size);
					break;
				} 
			}
			else {
				logtail += std::string(logp1, logs1);
				break;
			}
		}
	}

	if (!logtail.empty())
	{
		font = new gFont("Regular", hd ? 21 : 14);
		p.setFont(font);
		usable_area = eRect(hd ? 30 : 100, hd ? 180 : 170, my_dc->size().width() - (hd ? 60 : 180), my_dc->size().height() - (hd ? 30 : 20));
		p.renderText(usable_area, logtail, gPainter::RT_HALIGN_LEFT);
	}
	sleep(10);

	/*
	 * When 'component' is NULL, we are called because of a python exception.
	 * In that case, we'd prefer to to a clean shutdown of the C++ objects,
	 * and this should be safe, because the crash did not occur in the
	 * C++ part.
	 * However, when we got here for some other reason, a segfault probably,
	 * we prefer to stop immediately instead of performing a clean shutdown.
	 * We'd risk destroying things with every additional instruction we're
	 * executing here.
	 */
	if (component) raise(SIGKILL);
}

void oops(const mcontext_t &context)
{
#if defined(__MIPSEL__)
	eLog(lvlFatal, "PC: %08lx", (unsigned long)context.pc);
	int i;
	for (i=0; i<32; i += 4)
	{
		eLog(lvlFatal, "    %08x %08x %08x %08x",
			(int)context.gregs[i+0], (int)context.gregs[i+1],
			(int)context.gregs[i+2], (int)context.gregs[i+3]);
	}
#elif defined(__arm__)
	eLog(lvlFatal, "PC: %08lx", (unsigned long)context.arm_pc);
	eLog(lvlFatal, "Fault Address: %08lx", (unsigned long)context.fault_address);
	eLog(lvlFatal, "Error Code: %lu", (unsigned long)context.error_code);
#else
	eLog(lvlFatal, "FIXME: no oops support!");
#endif
}

/* Use own backtrace print procedure because backtrace_symbols_fd
 * only writes to files. backtrace_symbols cannot be used because
 * it's not async-signal-safe and so must not be used in signal
 * handlers.
 */
void print_backtrace()
{
#ifdef __GLIBC__
	void *array[15];
	size_t size;
	size_t cnt;

	size = backtrace(array, 15);
	eLog(lvlFatal, "Backtrace:");
	for (cnt = 1; cnt < size; ++cnt)
	{
		Dl_info info;

		if (dladdr(array[cnt], &info)
			&& info.dli_fname != NULL && info.dli_fname[0] != '\0')
		{
			eLog(lvlFatal, "%s(%s) [0x%lX]", info.dli_fname, info.dli_sname != NULL ? info.dli_sname : "n/a", (unsigned long int) array[cnt]);
		}
	}
#endif
}
void handleFatalSignal(int signum, siginfo_t *si, void *ctx)
{
	ucontext_t *uc = (ucontext_t*)ctx;
	oops(uc->uc_mcontext);
	print_backtrace();
	eLog(lvlFatal, "-------FATAL SIGNAL (%d)", signum);
	bsodFatal("enigma2, signal");
}

void bsodCatchSignals()
{
	struct sigaction act = {};
	act.sa_sigaction = handleFatalSignal;
	act.sa_flags = SA_RESTART | SA_SIGINFO;
	if (sigemptyset(&act.sa_mask) == -1)
		perror("sigemptyset");

		/* start handling segfaults etc. */
	sigaction(SIGSEGV, &act, 0);
	sigaction(SIGILL, &act, 0);
	sigaction(SIGBUS, &act, 0);
	sigaction(SIGABRT, &act, 0);
}
