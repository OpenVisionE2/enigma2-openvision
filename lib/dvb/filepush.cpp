#include "filepush.h"
#include <lib/base/eerror.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <poll.h>
#include <time.h>

//#define SHOW_WRITE_TIME

DEFINE_REF(eFilePushThread);

eFilePushThread::eFilePushThread(int blocksize, size_t buffersize):
	 m_sg(NULL),
	 m_stop(1),
	 m_send_pvr_commit(0),
	 m_stream_mode(0),
	 m_blocksize(blocksize),
	 m_buffersize(buffersize),
	 m_buffer((unsigned char *)malloc(buffersize)),
	 m_messagepump(eApp, 0, "eFilePushThread"),
	 m_run_state(0)
{
	if (m_buffer == NULL)
		eFatal("[eFilePushThread] Failed to allocate %zu bytes", buffersize);
	CONNECT(m_messagepump.recv_msg, eFilePushThread::recvEvent);
}

eFilePushThread::~eFilePushThread()
{
	stop(); /* eThread is borked, always call stop() from d'tor */
	if (m_buffer) {
		free(m_buffer);
	}
}

static void signal_handler(int x)
{
	eDebug("[eFilePush] SIGUSR1 received");
}

void eFilePushThread::thread()
{
	sigset_t sigmask;

	eDebug("[eFilePushThread] START thread");

	setIoPrio(IOPRIO_CLASS_BE, 0);

	/* Only allow SIGUSR1 to be delivered to our thread, don't let any
	 * other signals (like SIGHCHLD) interrupt our system calls.
	 * NOTE: signal block masks are per thread, so set it in the thread itself. */
	sigfillset(&sigmask);
	sigdelset(&sigmask, SIGUSR1);
	pthread_sigmask(SIG_SETMASK, &sigmask, nullptr);

	hasStarted(); /* "start()" blocks until we get here */

	do
	{
		int eofcount = 0;
		int buf_end = 0;
		size_t bytes_read = 0;
		off_t current_span_offset = 0;
		size_t current_span_remaining = 0;
		m_sof = 0;

		while (!m_stop)
		{
			if (m_sg && !current_span_remaining)
			{
				m_sg->getNextSourceSpan(m_current_position, bytes_read, current_span_offset, current_span_remaining, m_blocksize, m_sof);
				ASSERT(!(current_span_remaining % m_blocksize));
				m_current_position = current_span_offset;
				bytes_read = 0;
			}

			size_t maxread = m_buffersize;

			/* if we have a source span, don't read past the end */
			if (m_sg && maxread > current_span_remaining)
				maxread = current_span_remaining;

			/* align to blocksize */
			maxread -= maxread % m_blocksize;

			if (maxread && !m_sof)
			{
#ifdef SHOW_WRITE_TIME
				struct timeval starttime = {};
				struct timeval now = {};
				gettimeofday(&starttime, NULL);
#endif
				buf_end = m_source->read(m_current_position, m_buffer, maxread);
#ifdef SHOW_WRITE_TIME
				gettimeofday(&now, NULL);
				suseconds_t diff = (1000000 * (now.tv_sec - starttime.tv_sec)) + now.tv_usec - starttime.tv_usec;
				eDebug("[eFilePushThread] read %d bytes time: %9u us", buf_end, (unsigned int)diff);
#endif
			}
			else
				buf_end = 0;

			if (buf_end < 0)
			{
				buf_end = 0;
				/* Check m_stop after interrupted syscall. */
				if (m_stop)
					break;
				if (errno == EINTR || errno == EBUSY || errno == EAGAIN)
					continue;
				if (errno == EOVERFLOW)
				{
					eWarning("[eFilePushThread] OVERFLOW while playback?");
					continue;
				}
				eDebug("[eFilePushThread] read error: %m");
			}

			/* a read might be mis-aligned in case of a short read. */
			int d = buf_end % m_blocksize;
			if (d)
				buf_end -= d;

			if (buf_end == 0 || m_sof == 1)
			{
				/* on EOF, try COMMITting once. */
				if (m_send_pvr_commit)
				{
					struct pollfd pfd = {};
					pfd.fd = m_fd_dest;
					pfd.events = POLLIN;
					switch (poll(&pfd, 1, 250)) // wait for 250ms
					{
						case 0:
							eDebug("[eFilePushThread] wait for driver eof timeout");
							continue;
						case 1:
							eDebug("[eFilePushThread] wait for driver eof ok");
							break;
						default:
							eDebug("[eFilePushThread] wait for driver eof aborted by signal");
							/* Check m_stop after interrupted syscall. */
							if (m_stop)
								break;
							continue;
					}
				}

				if (m_stop)
					break;

				/* in stream_mode, we are sending EOF events
				   over and over until somebody responds.
				   in stream_mode, think of evtEOF as "buffer underrun occurred". */
				if (m_sof == 0)
					sendEvent(evtEOF);
				else
					sendEvent(evtUser); // start of file event

				if (m_stream_mode)
				{
					eDebug("[eFilePushThread] reached EOF, but we are in stream mode. delaying 1 second.");
					sleep(1);
					continue;
				}
				else if (++eofcount < 10)
				{
					eDebug("[eFilePushThread] reached EOF, but the file may grow. delaying 1 second.");
					sleep(1);
					continue;
				}
				break;
			}
			else
			{
				/* Write data to mux */
				int buf_start = 0;
				filterRecordData(m_buffer, buf_end);
				while ((buf_start != buf_end) && !m_stop)
				{
					int w = write(m_fd_dest, m_buffer + buf_start, buf_end - buf_start);

					if (w <= 0)
					{
						/* Check m_stop after interrupted syscall. */
						if (m_stop)
						{
							w = 0;
							buf_start = 0;
							buf_end = 0;
							break;
						}
						if (w < 0 && (errno == EINTR || errno == EAGAIN || errno == EBUSY))
							continue;
						eDebug("[eFilePushThread] write: %m");
						sendEvent(evtWriteError);
						break;
					}
					buf_start += w;
				}

				eofcount = 0;
				m_current_position += buf_end;
				bytes_read += buf_end;
				if (m_sg)
					current_span_remaining -= buf_end;
			}
		}
		sendEvent(evtStopped);

		{ /* mutex lock scope */
			eSingleLocker lock(m_run_mutex);
			m_run_state = 0;
			m_run_cond.signal(); /* Tell them we're here */
			while (m_stop == 2) {
				eDebug("[eFilePushThread] PAUSED");
				m_run_cond.wait(m_run_mutex);
			}
			if (m_stop == 0)
				m_run_state = 1;
		}
	} while (m_stop == 0);

	m_stopped = true;

	eDebug("[eFilePushThread] STOP");
}

void eFilePushThread::start(ePtr<iTsSource> &source, int fd_dest)
{
	m_source = source;
	m_fd_dest = fd_dest;
	m_current_position = 0;
	m_run_state = 1;
	m_stop = 0;
	m_stopped = false;

	/* Use a signal to interrupt blocking systems calls (like read()).
	 * We don't want to get enigma killed by the signal (default action),
	 * so install a handler. Don't use SIG_IGN (ignore signal) because
	 * then the system calls won't be interrupted by the signal.
	 * NOTE: signal options and handlers (except for a block mask) are
	 * global for the process, so install the handler here and not
	 * in the thread. */
	struct sigaction act = {};
	act.sa_handler = signal_handler;
	act.sa_flags = 0;
	sigaction(SIGUSR1, &act, nullptr);

	run();
}

void eFilePushThread::stop()
{
	static const struct timespec timespec_1 = { .tv_sec =  0, .tv_nsec = 1000000000 / 10 };
	int safeguard;

	if (m_stop == 1)
	{
		eDebug("[eFilePushThread]: stopping thread that is already stopped");
		return;
	}

	m_stop = 1;
	m_run_cond.signal(); /* Break out of pause if needed */

	for(safeguard = 100; safeguard > 0; safeguard--)
	{
		eDebug("[eFilePushThread] stopping thread: %d", safeguard);
		sendSignal(SIGUSR1);

		nanosleep(&timespec_1, nullptr);

		if(m_stopped)
			break;
	}

	if(safeguard > 0)
		kill();
	else
		eWarning("[eFilePushThread] thread could not be stopped!");
}

void eFilePushThread::pause()
{
	if (m_stop == 1)
	{
		eWarning("[eFilePushThread] pause called while not running");
		return;
	}
	/* Set thread into a paused state by setting m_stop to 2 and wait
	 * for the thread to acknowledge that */
	eSingleLocker lock(m_run_mutex);
	m_stop = 2;
	sendSignal(SIGUSR1);
	m_run_cond.signal(); /* Trigger if in weird state */
	while (m_run_state) {
		eDebug("[eFilePushThread] waiting for pause");
		m_run_cond.wait(m_run_mutex);
	}
}

void eFilePushThread::resume()
{
	if (m_stop != 2)
	{
		eWarning("[eFilePushThread] resume called while not paused");
		return;
	}
	/* Resume the paused thread by resetting the flag and
	 * signal the thread to release it */
	eSingleLocker lock(m_run_mutex);
	m_stop = 0;
	m_run_cond.signal(); /* Tell we're ready to resume */
}

void eFilePushThread::enablePVRCommit(int s)
{
	m_send_pvr_commit = s;
}

void eFilePushThread::setStreamMode(int s)
{
	m_stream_mode = s;
}

void eFilePushThread::setScatterGather(iFilePushScatterGather *sg)
{
	m_sg = sg;
}

void eFilePushThread::sendEvent(int evt)
{
	/* add a ref, to make sure the object is not destroyed while the messagepump contains unhandled messages */
	AddRef();
	m_messagepump.send(evt);
}

void eFilePushThread::recvEvent(const int &evt)
{
	m_event(evt);
	/* release the ref which we grabbed in sendEvent() */
	Release();
}

void eFilePushThread::filterRecordData(const unsigned char *data, int len)
{
}

eFilePushThreadRecorder::eFilePushThreadRecorder(unsigned char* buffer, size_t buffersize):
	m_fd_source(-1),
	m_buffersize(buffersize),
	m_buffer(buffer),
	m_overflow_count(0),
	m_stop(1),
	m_messagepump(eApp, 0, "eFilePushThreadRecorder")
{
	m_protocol = m_stream_id = m_session_id = m_packet_no = 0;
	CONNECT(m_messagepump.recv_msg, eFilePushThreadRecorder::recvEvent);
}

#define copy16(a, i, v)           \
	{                             \
		a[i] = ((v) >> 8) & 0xFF; \
		a[i + 1] = (v)&0xFF;      \
	}
#define copy32(a, i, v)                \
	{                                  \
		a[i] = ((v) >> 24) & 0xFF;     \
		a[i + 1] = ((v) >> 16) & 0xFF; \
		a[i + 2] = ((v) >> 8) & 0xFF;  \
		a[i + 3] = (v)&0xFF;           \
	}
#define _PROTO_RTSP_UDP 1
#define _PROTO_RTSP_TCP 2

int eFilePushThreadRecorder::pushReply(void *buf, int len)
{
	m_reply.insert(m_reply.end(), (unsigned char *)buf, (unsigned char *)buf + len);
	eDebug("[eFilePushThread] pushed reply of %d bytes", len);
	return 0;
}

static int errs;

int64_t eFilePushThreadRecorder::getTick()
{ //ms
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (ts.tv_nsec / 1000000) + (ts.tv_sec * 1000);
}

// wrapper around ::read, to read multiple of 188 or error (it does not block)
int eFilePushThreadRecorder::read_ts(int fd, unsigned char *buf, int size)
{
	int rb = 0, bytes = 0;
	int left = size;
	do
	{
		rb = ::read(fd, buf + bytes, left);
		if (rb > 0 && ((bytes % 188) != 0))
			eDebug("[eFilePushThread] %s read %d out of %d bytes, total %d, size %d, fd %d", ((bytes + rb) % 188) ? "incomplete" : "completed", rb, left, bytes, size, fd);

		if (rb <= 0 && errno != EAGAIN && errno != EINTR)
			return rb;

		if (rb > 0)
		{
			bytes += rb;
			left -= rb;
		}
		if ((bytes % 188) != 0)
		{
			left = 188 - (bytes % 188);
		}

	} while ((bytes % 188) != 0);

	if (bytes == 0)
		return rb;

	return bytes;
}

int eFilePushThreadRecorder::read_dmx(int fd, void *m_buffer, int size)
{
	unsigned char *buf;
	int it = 0, pos = 0, bytes = 0;
	int max_pack = 42;
	int i, left;
	static int cnt;
	unsigned char *b;
	uint64_t start = getTick();
	while (size - pos > 188 + 16)
	{
		left = size - pos - 16;
		left = (left > 188 * max_pack) ? 188 * max_pack : (((int)(left / 188) - 1) * 188);
		if (left < 188)
			break;

		buf = (unsigned char *)m_buffer + pos;

		bytes = read_ts(fd, buf + 16, left);

		if (bytes <= 0 && errno != EAGAIN && errno != EINTR)
		{
			eDebug("[eFilePushThread] error reading from DMX handle %d, errno %d: %m", fd, errno);
			break;
		}

		if (bytes > 0)
		{
			if ((bytes % 188) != 0)
				eDebug("[eFilePushThread] incomplete packet read from %d with size %d", fd, bytes);

			m_packet_no++;
			it++;
			for (i = 0; i < bytes; i += 188)
			{
				b = buf + 16 + i;
				int pid = (b[1] & 0x1F) * 256 + b[2];

				if ((b[3] & 0x80)) // mark decryption failed if not decrypted by enigma
				{
					if ((errs++ % 100) == 0)
						eDebug("[eFilePushThread] decrypt errs %d, pid %d, m_buffer %p, pos %d, buf %p, i %d: %02X %02X %02X %02X", errs, pid, m_buffer, pos, buf, i, b[0], b[1], b[2], b[3]);
					b[1] |= 0x1F;
					b[2] |= 0xFF;
				}
			}
			buf[0] = 0x24;
			buf[1] = 0;
			copy16(buf, 2, (uint16_t)(bytes + 12));
			copy16(buf, 4, 0x8021);
			copy16(buf, 6, m_stream_id);
			copy32(buf, 8, cnt);
			copy32(buf, 12, m_session_id);
			cnt++;
			pos += bytes + 16;
		}
		if (m_reply.size() > 0)
		{
			pos = m_reply.size();
			buf[0] = 0;
			memcpy(m_buffer, m_reply.data(), pos);
			eDebug("[eFilePushThread] added reply of %d bytes", pos);
			m_reply.clear();
			break; // reply to the server ASAP
		}
		uint64_t ts = getTick() - start;

		if ((pos > 0) && (bytes == -1) && (ts > 50)) // do not block more than 50ms if there is available data
			break;

		if (bytes < 0)
			usleep(5000);
	}
	uint64_t ts = getTick() - start;
	if (ts > 1000)
		eDebug("[eFilePushThread] returning %d bytes from %d, last read %d bytes in %jd ms (iteration %d)", pos, size, bytes, ts, m_packet_no);
	if (pos == 0)
		return bytes;
	return pos;
}

void eFilePushThreadRecorder::thread()
{
	ssize_t bytes;
	int rv;
	struct pollfd pfd = {};
	sigset_t sigmask;

	eDebug("[eFilePushThreadRecorder] THREAD START");

	setIoPrio(IOPRIO_CLASS_RT, 7);

	/* Only allow SIGUSR1 to be delivered to our thread, don't let any
	 * other signals (like SIGHCHLD) interrupt our system calls.
	 * NOTE: signal block masks are per thread, so set it in the thread itself. */
	sigfillset(&sigmask);
	sigdelset(&sigmask, SIGUSR1);
	pthread_sigmask(SIG_SETMASK, &sigmask, nullptr);

	hasStarted();

	if (m_protocol == _PROTO_RTSP_TCP)
	{
		int flags = fcntl(m_fd_source, F_GETFL, 0);
		flags |= O_NONBLOCK;
		if (fcntl(m_fd_source, F_SETFL, flags) == -1)
			eDebug("[eFilePushThread] failed setting DMX handle %d in non-blocking mode, error %d: %s", m_fd_source, errno, strerror(errno));
	}

	/* m_stop must be evaluated after each syscall. */
	while (!m_stop)
	{
		bytes = ::read(m_fd_source, m_buffer, m_buffersize);

		if (bytes < 0)
		{
			bytes = 0;

			/* EAGAIN can happen on the Broadcom encoder, even though the fd is not opened nonblocking */
			if(errno == EAGAIN)
			{
				pfd.fd = m_fd_source;
				pfd.events = POLLIN;
				pfd.revents = 0;

				errno = 0;
				rv = poll(&pfd, 1, 30000);

				if(rv < 0)
				{
					if(errno == EINTR)
					{
						eDebug("[eFilePushThreadRecorder] poll got interrupted by signal, stop: %d", m_stop);
						continue;
					}

					eWarning("[eFilePushThreadRecorder] POLL ERROR, aborting thread: %m");
					sendEvent(evtWriteError);

					break;
				}

				if(rv == 0)
				{
					eDebug("[eFilePushThreadRecorder] no fds ready %d", pfd.fd);
					continue;
				}

				if(rv != 1)
				{
					eWarning("[eFilePushThreadRecorder] POLL WEIRDNESS, fds != 1: %d, aborting thread", rv);
					sendEvent(evtWriteError);

					break;
				}

				if(pfd.revents & (POLLRDHUP | POLLERR | POLLHUP | POLLNVAL))
				{
					eWarning("[eFilePushThreadRecorder] POLL STATUS ERROR, aborting thread: %x, fd: %d\n", pfd.revents, pfd.fd);
					sendEvent(evtWriteError);

					break;
				}

				if(!(pfd.revents & POLLIN))
				{
					eWarning("[eFilePushThreadRecorder] POLL WEIRDNESS, fd not ready, aborting thread: %x\n", pfd.revents);
					sendEvent(evtWriteError);

					break;
				}

				continue;
			}

			if (errno == EINTR || errno == EBUSY)
			{
				eDebug("[eFilePushThreadRecorder] read got interrupted by signal, stop: %d", m_stop);
				continue;
			}

			if (errno == EOVERFLOW)
			{
				eWarning("[eFilePushThreadRecorder] OVERFLOW while recording");
				++m_overflow_count;
				continue;
			}
			eDebug("[eFilePushThreadRecorder] *read error* (%m) - aborting thread because i don't know what else to do.");
			sendEvent(evtReadError);
			break;
		}

#ifdef SHOW_WRITE_TIME
		struct timeval starttime = {};
		struct timeval now = {};
		gettimeofday(&starttime, NULL);
#endif
		int w = writeData(bytes);
#ifdef SHOW_WRITE_TIME
		gettimeofday(&now, NULL);
		suseconds_t diff = (1000000 * (now.tv_sec - starttime.tv_sec)) + now.tv_usec - starttime.tv_usec;
		eDebug("[eFilePushThreadRecorder] write %d bytes time: %9u us", bytes, (unsigned int)diff);
#endif
		if (w < 0)
		{
			eWarning("[eFilePushThreadRecorder] WRITE ERROR, aborting thread: %m");
			sendEvent(evtWriteError);
			break;
		}
	}
	flush();
	sendEvent(evtStopped);
	eDebug("[eFilePushThreadRecorder] THREAD STOP");
	m_stopped = true;
}

void eFilePushThreadRecorder::start(int fd)
{
	m_fd_source = fd;
	m_stop = 0;
	m_stopped = false;

	/* Use a signal to interrupt blocking systems calls (like read()).
	 * We don't want to get enigma killed by the signal (default action),
	 * so install a handler. Don't use SIG_IGN (ignore signal) because
	 * then the system calls won't be interrupted by the signal.
	 * NOTE: signal options and handlers (except for a block mask) are
	 * global for the process, so install the handler here and not
	 * in the thread. */
	struct sigaction act = {};
	act.sa_handler = signal_handler;
	act.sa_flags = 0;
	sigaction(SIGUSR1, &act, nullptr);

	run();
}
#ifdef HAVE_RASPBERRYPI
void eFilePushThreadRecorder::start(int fd, ePtr<eDVBDemux> &demux)
{
	eDecryptRawFile *f = new eDecryptRawFile();
	m_source = f;
	f->setfd(fd);
	f->setDemux(demux);

	struct sigaction action;

	m_fd_source = 0;
	m_stop = 0;

	/* prevent enigma main thread/process from being
	 * actually killed when a thread is signalled
	 * that not (yet) has signal handler or is not
	 * (yet) blocking signals. NB this is still in
	 * parent context. */
	action.sa_handler = signal_handler;
	action.sa_flags = 0;
	sigaction(SIGUSR1, &action, 0);

	run();
}
#endif
void eFilePushThreadRecorder::stop()
{
	static const struct timespec timespec_1 = { .tv_sec =  0, .tv_nsec = 1000000000 / 10 };
	int safeguard;

	if (m_stop == 1)
	{
		eDebug("[eFilePushThreadRecorder] requesting to stop thread but thread is already stopped");
		return;
	}

	m_stop = 1;

	for(safeguard = 100; safeguard > 0; safeguard--)
	{
		eDebug("[eFilePushThreadRecorder] stopping thread: %d", safeguard);
		sendSignal(SIGUSR1);

		nanosleep(&timespec_1, nullptr);

		if(m_stopped)
			break;
	}

	if(safeguard > 0)
		kill();
	else
		eWarning("[eFilePushThreadRecorder] thread could not be stopped!");
}

void eFilePushThreadRecorder::sendEvent(int evt)
{
	m_messagepump.send(evt);
}

void eFilePushThreadRecorder::recvEvent(const int &evt)
{
	m_event(evt);
}
