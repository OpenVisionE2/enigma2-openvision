#ifndef __DVB_ENCODER_H_
#define __DVB_ENCODER_H_

#include <vector>

#include <lib/nav/core.h>
#include <lib/base/thread.h>

class eEncoder
{
	private:

		DECLARE_REF(eEncoder);

		enum
		{
			IOCTL_BROADCOM_SET_VPID_MIPS = 1,
			IOCTL_BROADCOM_SET_VPID_ARM = 11,
			IOCTL_BROADCOM_SET_APID_MIPS = 2,
			IOCTL_BROADCOM_SET_APID_ARM = 12,
			IOCTL_BROADCOM_SET_PMTPID_MIPS = 3,
			IOCTL_BROADCOM_SET_PMTPID_ARM = 13,
			IOCTL_BROADCOM_START_TRANSCODING = 100,
			IOCTL_BROADCOM_STOP_TRANSCODING = 200,
		};

		class encoder_t : public eThread
		{
			public:

				encoder_t(int encoder_in, int decoder_in, eNavigation *navigation_instance_in) :
						encoder(encoder_in),
						decoder(decoder_in),
						fd(-1),
						state(state_idle),
						navigation_instance(navigation_instance_in)
				{
				}

				int encoder;
				int decoder;
				int fd;

				enum
				{
					state_idle,
					state_wait_pmt,
					state_running,
					state_finishing,
					state_destroyed,
				} state;

				eNavigation *navigation_instance;

				void thread(void);
		};

		std::vector<encoder_t> encoder;
		bool bcm_encoder;
		ePtr<eConnection> m_nav_event_connection_0;
		ePtr<eConnection> m_nav_event_connection_1;

		static eEncoder *instance;

		enum {
			hdmiPatPid = 0x00, // 0
			hdmiPcrPid = 0x13, // 19
			hdmiPmtPid = 0x55, // 85
			hdmiAudioPid = 0xC0, // 196
			hdmiVideoPid = 0xE0, // 224
		};

		void navigation_event_0(int);
		void navigation_event_1(int);
		void navigation_event(int, int);

	public:

		eEncoder();
		~eEncoder();

		//FIXME: const
		int allocateEncoder(const std::string &serviceref, const int bitrate, const int width, const int height, const int framerate, const int interlaced, const int aspectratio, int &buffersize, const std::string &vcodec = "", const std::string &acodec = "");
		void freeEncoder(int encoderfd);
		int getUsedEncoderCount();


		int getPatPid() { return hdmiPatPid; }
		int getPcrPid() { return hdmiPcrPid; }
		int getPmtPid() { return hdmiPmtPid; }
		int getAudioPid() { return hdmiAudioPid; }
		int getVideoPid() { return hdmiVideoPid; }

		static eEncoder *getInstance();
};

#endif /* __DVB_ENCODER_H_ */
