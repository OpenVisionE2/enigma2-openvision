#ifndef __volume_h
#define __volume_h

#ifdef DMAMLOGIC
#ifdef HAVE_ALSA
#undef HAVE_ALSA
#endif
#endif

#ifdef HAVE_ALSA
#include <alsa/asoundlib.h>
#endif

#include <lib/base/ebase.h>
#ifdef HAVE_RASPBERRYPI
#include <omx.h>
#endif

class eDVBVolumecontrol
{
private:
#ifdef HAVE_ALSA
	snd_mixer_elem_t *mainVolume;
	snd_mixer_t *alsaMixerHandle;
#endif
	static eDVBVolumecontrol *instance;
	eDVBVolumecontrol();
#ifdef SWIG
	~eDVBVolumecontrol();
#endif
#ifdef HAVE_RASPBERRYPI
	cOmx *m_omx;
#endif
	int openMixer();
	void closeMixer(int fd);

	bool muted;
	int leftVol, rightVol;
	int m_volsteps;

	int checkVolume(int vol);

public:
	static eDVBVolumecontrol* getInstance();

	void setVolumeSteps(int steps);
	void volumeUp(int left = 0, int right = 0);
	void volumeDown(int left = 0, int right = 0);

	void setVolume(int left, int right);

	void volumeMute();
	void volumeUnMute();
	void volumeToggleMute();

	int getVolume();
	bool isMuted();
};

#endif //__volume_h
