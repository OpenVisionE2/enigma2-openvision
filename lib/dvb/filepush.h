#ifndef __lib_base_filepush_h
#define __lib_base_filepush_h

#include <lib/base/thread.h>
#include <lib/base/ioprio.h>
#include <libsig_comp.h>
#include <lib/base/message.h>
#include <sys/types.h>
#include <lib/base/rawfile.h>

class iFilePushScatterGather
{
public:
	virtual void getNextSourceSpan(off_t current_offset, size_t bytes_read, off_t &start, size_t &size, int blocksize, int &sof)=0;
	virtual ~iFilePushScatterGather() {}
};

class eFilePushThread: public eThread, public sigc::trackable, public iObject
{
	DECLARE_REF(eFilePushThread);
public:
	eFilePushThread(int blocksize, size_t buffersize);
	~eFilePushThread();
	void thread();
	void stop();
	void start(ePtr<iTsSource> &source, int destfd);

	void pause();
	void resume();

	void enablePVRCommit(int);
	/* stream mode will wait on EOF until more data is available. */
	void setStreamMode(int);
	void setScatterGather(iFilePushScatterGather *);

#if SIGCXX_MAJOR_VERSION == 3
	enum { evtEOF, evtReadError, evtWriteError, evtUser, evtStopped };
	sigc::signal<void(int)> m_event;
#else
	enum { evtEOF, evtReadError, evtWriteError, evtUser, evtStopped, evtFlush };
	sigc::signal1<void,int> m_event;
#endif

		/* you can send private events if you want */
	void sendEvent(int evt);
protected:
	virtual void filterRecordData(const unsigned char *data, int len);
private:
	iFilePushScatterGather *m_sg;
	int m_stop;
	bool m_stopped;
	int m_fd_dest;
	int m_send_pvr_commit;
	int m_stream_mode;
	int m_sof;
	int m_blocksize;
	size_t m_buffersize;
	unsigned char* m_buffer;
	off_t m_current_position;

	ePtr<iTsSource> m_source;

	eFixedMessagePump<int> m_messagepump;
	eSingleLock m_run_mutex;
	eCondition m_run_cond;
	int m_run_state;

	void recvEvent(const int &evt);
};

class eFilePushThreadRecorder: public eThread, public sigc::trackable
{
public:
#if HAVE_AMLOGIC
	eFilePushThreadRecorder(unsigned char* buffer, size_t buffersize=10*188*1024);
#else
	eFilePushThreadRecorder(unsigned char* buffer, size_t buffersize);
#endif
	void thread();
	void stop();
	void start(int sourcefd);
#ifdef HAVE_RASPBERRYPI
	void start(int fd, ePtr<eDVBDemux> &demux);
#endif
#if SIGCXX_MAJOR_VERSION == 3
	enum { evtEOF, evtReadError, evtWriteError, evtUser, evtStopped };
	sigc::signal<void(int)> m_event;
#else
	enum { evtEOF, evtReadError, evtWriteError, evtUser, evtStopped, evtRetune };
	sigc::signal1<void,int> m_event;
#endif

	int getProtocol() { return m_protocol;}
	void setProtocol(int i){ m_protocol = i;}
	void setSession(int se, int st) { m_session_id = se; m_stream_id = st;}
	int read_dmx(int fd, void *m_buffer, int size);
	int pushReply(void *buf, int len);
	void sendEvent(int evt);
	static int64_t getTick();
	static int read_ts(int fd, unsigned char *buf, int size);
protected:
	// This method should write the data out and return the number of bytes written.
	// If result <0, set 'errno'. The simplest implementation is just "::write(m_buffer, ...)"
	// The method may freely modify m_buffer and m_buffersize
	virtual int writeData(int len) = 0;
	// Called when terminating the recording thread. Allows to clean up memory and
	// flush buffers, terminate outstanding IO requests.
	virtual void flush() = 0;

	int m_fd_source;
	size_t m_buffersize;
	unsigned char* m_buffer;
	unsigned int m_overflow_count;
private:
	int m_stop;
	bool m_stopped;
	eFixedMessagePump<int> m_messagepump;
#ifdef HAVE_RASPBERRYPI
	ePtr<iTsSource> m_source;
#endif
	void recvEvent(const int &evt);
	int m_protocol, m_session_id, m_stream_id, m_packet_no;
	std::vector<unsigned char> m_reply;
};

#endif
