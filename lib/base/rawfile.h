#ifndef __lib_base_rawfile_h
#define __lib_base_rawfile_h

#include <string>
#include <lib/base/itssource.h>
#ifdef HAVE_RASPBERRYPI
#include <lib/base/tsRingbuffer.h>
#include <lib/dvb/edvbdemux.h>
#endif

class eRawFile: public iTsSource
{
	DECLARE_REF(eRawFile);
#ifndef HAVE_RASPBERRYPI
	eSingleLock m_lock;
#endif
public:
	eRawFile(unsigned int packetsize = 188);
	~eRawFile();
	int open(const char *filename);
#ifdef HAVE_RASPBERRYPI
	void setfd(int fd);
#endif
	// iTsSource
	ssize_t read(off_t offset, void *buf, size_t count);
	off_t length();
	off_t offset();
	int valid();
#ifdef HAVE_RASPBERRYPI
protected:
	eSingleLock m_lock;
	int m_fd;
private:
	int m_nrfiles;
#else
private:
	int m_fd;
	int m_nrfiles;
#endif
	off_t m_splitsize;
	off_t m_totallength;
	off_t m_current_offset;
	off_t m_base_offset;
	off_t m_last_offset;
	int m_current_file;
	std::string m_basename;

	int close();
	void scan();
	int switchOffset(off_t off);
	off_t lseek_internal(off_t offset);
	int openFileUncached(int nr);
};
#ifdef HAVE_RASPBERRYPI
class eDecryptRawFile: public eRawFile
{
public:
	eDecryptRawFile(int packetsize = 188);
	~eDecryptRawFile();
	void setDemux(ePtr<eDVBDemux> demux);
	ssize_t read(off_t offset, void *buf, size_t count);
private:
	ePtr<eDVBDemux> demux;
	cRingBufferLinear *ringBuffer;
	int bs_size;
	bool delivered;
	int lastPacketsCount;
	bool stream_correct;

	uint8_t* getPackets(int &packetsCount);
};
#endif
#endif
