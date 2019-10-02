#ifndef __dvb_edvbdemux_h
#define __dvb_edvbdemux_h

#include <lib/dvb/idvb.h>
#include <lib/dvb/idemux.h>
#include <lib/dvb/decsa.h>

class eDVBDemux: public iDVBDemux
{
	DECLARE_REF(eDVBDemux);
public:
	enum {
		evtFlush
	};
	eDVBDemux(int adapter, int demux);
	virtual ~eDVBDemux();

	RESULT setSourceFrontend(int fenum);
	int getSource() { return source; }
	RESULT setSourcePVR(int pvrnum);
	int getDvrId() { return m_dvr_id; }

	RESULT createSectionReader(eMainloop *context, ePtr<iDVBSectionReader> &reader);
	RESULT createPESReader(eMainloop *context, ePtr<iDVBPESReader> &reader);
	RESULT createTSRecorder(ePtr<iDVBTSRecorder> &recorder, unsigned int packetsize = 188, bool streaming=false);
	RESULT getMPEGDecoder(ePtr<iTSMPEGDecoder> &reader, int index);
	RESULT getSTC(pts_t &pts, int num);
	RESULT getCADemuxID(uint8_t &id) { id = demux; return 0; }
	RESULT getCAAdapterID(uint8_t &id) { id = adapter; return 0; }
	RESULT flush();
	RESULT connectEvent(const sigc::slot1<void,int> &event, ePtr<eConnection> &conn);
	int openDVR(int flags);

	int getRefCount() { return ref; }

	RESULT setCaDescr(ca_descr_t *ca_descr, bool initial);
	RESULT setCaPid(ca_pid_t *ca_pid);
	bool decrypt(uint8_t *data, int len, int &packetsCount);
private:
	int adapter, demux, source;
	cDeCSA *decsa;
	int m_dvr_busy;
	int m_dvr_id;
	int m_dvr_source_offset;
	friend class eDVBSectionReader;
	friend class eDVBPESReader;
	friend class eDVBAudio;
	friend class eDVBVideo;
	friend class eDVBPCR;
	friend class eDVBTText;
	friend class eDVBTSRecorder;
	friend class eDVBCAService;
	friend class eTSMPEGDecoder;
#ifdef HAVE_AMLOGIC
	int m_pvr_fd;
	friend class eAMLTSMPEGDecoder;
#endif
	sigc::signal1<void, int> m_event;

	int openDemux(void);
};

//	vdr/remux.h

#define MAX33BIT  0x00000001FFFFFFFFLL // max. possible value with 33 bit

typedef unsigned char uchar;

inline bool PesLongEnough(int Length)
{
  return Length >= 6;
}

inline bool PesHasLength(const uchar *p)
{
  return p[4] | p[5];
}

inline int PesLength(const uchar *p)
{
  return 6 + p[4] * 256 + p[5];
}

inline int PesPayloadOffset(const uchar *p)
{
  return 9 + p[8];
}

inline bool PesHasPts(const uchar *p)
{
  return (p[7] & 0x80) && p[8] >= 5;
}

inline int64_t PesGetPts(const uchar *p)
{
  return ((((int64_t)p[ 9]) & 0x0E) << 29) |
         (( (int64_t)p[10])         << 22) |
         ((((int64_t)p[11]) & 0xFE) << 14) |
         (( (int64_t)p[12])         <<  7) |
         ((((int64_t)p[13]) & 0xFE) >>  1);
}

int64_t PtsDiff(int64_t Pts1, int64_t Pts2);
       ///< Returns the difference between two PTS values. The result of Pts2 - Pts1
       ///< is the actual number of 90kHz time ticks that pass from Pts1 to Pts2,
       ///< properly taking into account the 33bit wrap around. If Pts2 is "before"
       ///< Pts1, the result is negative.

#endif
