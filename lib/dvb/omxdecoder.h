/*
 * rpihddevice - Enigma2 rpihddevice library for Raspberry Pi
 * Copyright (C) 2014, 2015, 2016 Thomas Reufer
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */

#ifndef OMX_DEVICE_H
#define OMX_DEVICE_H

#include <tools.h>
#include <lib/dvb/edvbdemux.h>

//	vdr/device.h

// Note that VDR itself always uses pmAudioVideo when replaying a recording!
enum ePlayMode { pmNone,           // audio/video from decoder
                 pmAudioVideo,     // audio/video from player
                 pmAudioOnly,      // audio only from player, video from decoder
                 pmAudioOnlyBlack, // audio only from player, no video (black screen)
                 pmVideoOnly,      // video only from player, audio from decoder
                 pmExtern_THIS_SHOULD_BE_AVOIDED
                 // external player (e.g. MPlayer), release the device
                 // WARNING: USE THIS MODE ONLY AS A LAST RESORT, IF YOU
                 // ABSOLUTELY, POSITIVELY CAN'T IMPLEMENT YOUR PLAYER
                 // THE WAY IT IS SUPPOSED TO WORK. FORCING THE DEVICE
                 // TO RELEASE ITS FILES HANDLES (OR WHATEVER RESOURCES
                 // IT MAY USE) TO ALLOW AN EXTERNAL PLAYER TO ACCESS
                 // THEM MEANS THAT SUCH A PLAYER WILL NEED TO HAVE
                 // DETAILED KNOWLEDGE ABOUT THE INTERNALS OF THE DEVICE
                 // IN USE. AS A CONSEQUENCE, YOUR PLAYER MAY NOT WORK
                 // IF A PARTICULAR VDR INSTALLATION USES A DEVICE NOT
                 // KNOWN TO YOUR PLAYER.
               };

class cOmx;
class cRpiAudioDecoder;
class cMutex;

class cOmxDevice //: cDevice
{

public:

	cOmxDevice(int display, int layer);
	void setScrambled(bool doDescramble);
	virtual ~cOmxDevice();

	virtual cString DeviceName(void) const { return "rpihddevice"; }
		///< Returns a string identifying the name of this device.
		///< The default implementation returns an empty string.
	virtual int Init(void);
	virtual int DeInit(void);

	virtual bool Start(void);

	virtual bool HasDecoder(void) const { return true; }
		///< Tells whether this device has an MPEG decoder.
	virtual bool CanReplay(void)  const { return true; }
		///< Returns true if this device can currently start a replay session.
	virtual bool HasIBPTrickSpeed(void);
		///< Returns true if this device can handle all frames in 'fast forward'
		///< trick speeds.
	virtual void GetOsdSize(int &Width, int &Height, double &PixelAspect);
		///< Returns the Width, Height and PixelAspect ratio the OSD should use
		///< to best fit the resolution of the output device. If PixelAspect
		///< is not 1.0, the OSD may take this as a hint to scale its
		///< graphics in a way that, e.g., a circle will actually
		///< show up as a circle on the screen, and not as an ellipse.
		///< Values greater than 1.0 mean to stretch the graphics in the
		///< vertical direction (or shrink it in the horizontal direction,
		///< depending on which dimension shall be fixed). Values less than
		///< 1.0 work the other way round. Note that the OSD is not guaranteed
		///< to actually use this hint.
	virtual void GetVideoSize(int &Width, int &Height, double &VideoAspect);
		///< Returns the Width, Height and VideoAspect ratio of the currently
		///< displayed video material. Width and Height are given in pixel
		///< (e.g. 720x576) and VideoAspect is e.g. 1.33333 for a 4:3 broadcast,
		///< or 1.77778 for 16:9.
		///< The default implementation returns 0 for Width and Height
		///< and 1.0 for VideoAspect.
/*	
	virtual cRect CanScaleVideo(const cRect &Rect, int Alignment = taCenter)
		{ return Rect; }
	virtual void ScaleVideo(const cRect &Rect = cRect::Null);
*/
	virtual bool SetPlayMode(ePlayMode PlayMode);
		///< Sets the device into the given play mode.
		///< Returns true if the operation was successful.
	virtual void StillPicture(const uchar *Data, int Length);
		///< Displays the given I-frame as a still picture.
		///< Data points either to a series of TS (first byte is 0x47) or PES (first byte
		///< is 0x00) data of the given Length. The default implementation
		///< converts TS to PES and calls itself again, allowing a derived class
		///< to display PES if it can't handle TS directly.
	virtual int PlayAudio(const uchar *Data, int Length, uchar Id);
		///< Plays the given data block as audio.
		///< Data points to exactly one complete PES packet of the given Length.
		///< Id indicates the type of audio data this packet holds.
		///< PlayAudio() shall process the packet either as a whole (returning
		///< Length) or not at all (returning 0 or -1 and setting 'errno' accordingly).
		///< Returns the number of bytes actually taken from Data, or -1
		///< in case of an error.
	virtual int PlayVideo(const uchar *Data, int Length)
		{ return PlayVideo(Data, Length, false); }

	virtual int PlayVideo(const uchar *Data, int Length, bool EndOfFrame);
		///< Plays the given data block as video.
		///< Data points to exactly one complete PES packet of the given Length.
		///< PlayVideo() shall process the packet either as a whole (returning
		///< Length) or not at all (returning 0 or -1 and setting 'errno' accordingly).
		///< Returns the number of bytes actually taken from Data, or -1
		///< in case of an error.
	virtual int64_t GetSTC(void);
		///< Gets the current System Time Counter, which can be used to
		///< synchronize audio, video and subtitles. If this device is able to
		///< replay, it must provide an STC.
		///< The value returned doesn't need to be an actual "clock" value,
		///< it is sufficient if it holds the PTS (Presentation Time Stamp) of
		///< the most recently presented frame. A proper value must be returned
		///< in normal replay mode as well as in any trick modes (like slow motion,
		///< fast forward/rewind).
		///< Only the lower 32 bit of this value are actually used, since some
		///< devices can't handle the msb correctly.
	virtual uchar *GrabImage(int &Size, bool Jpeg = true, int Quality = -1,
			int SizeX = -1, int SizeY = -1);
		///< Grabs the currently visible screen image.
		///< Size is the size of the returned data block.
		///< If Jpeg is true it will write a JPEG file. Otherwise a PNM file will be written.
		///< Quality is the compression factor for JPEG. 1 will create a very blocky
		///< and small image, 70..80 will yield reasonable quality images while keeping the
		///< image file size around 50 KB for a full frame. The default will create a big
		///< but very high quality image.
		///< SizeX is the number of horizontal pixels in the frame (default is the current screen width).
		///< SizeY is the number of vertical pixels in the frame (default is the current screen height).
		///< Returns a pointer to the grabbed image data, or NULL in case of an error.
		///< The caller takes ownership of the returned memory and must free() it once it isn't needed any more.
#if APIVERSNUM >= 20103
	virtual void TrickSpeed(int Speed, bool Forward);
#else
	virtual void TrickSpeed(int Speed);
#endif
		///< Sets the device into a mode where replay is done slower.
		///< Every single frame shall then be displayed the given number of
		///< times. Forward is true if replay is done in the normal (forward)
		///< direction, false if it is done reverse.
		///< The cDvbPlayer uses the following values for the various speeds:
		///<                   1x   2x   3x
		///< Fast Forward       6    3    1
		///< Fast Reverse       6    3    1
		///< Slow Forward       8    4    2
		///< Slow Reverse      63   48   24
	virtual void Clear(void);
		///< Clears all video and audio data from the device.
		///< A derived class must call the base class function to make sure
		///< all registered cAudio objects are notified.
	virtual void Play(void);
		///< Sets the device into play mode (after a previous trick
		///< mode)
	virtual void Freeze(void);
		///< Puts the device into "freeze frame" mode.
	virtual void SetVolumeDevice(int Volume);
		///< Sets the audio volume on this device (Volume = 0...255).
	virtual bool Poll(cPoller &Poller, int TimeoutMs = 0);
		///< Returns true if the device itself or any of the file handles in
		///< Poller is ready for further action.
		///< If TimeoutMs is not zero, the device will wait up to the given number
		///< of milliseconds before returning in case it can't accept any data.
protected:

	enum eDirection {
		eForward,
		eBackward,
		eNumDirections
	};

	static const char* DirectionStr(eDirection dir) {
		return 	dir == eForward ? "forward" :
				dir == eBackward ? "backward" : "unknown";
	}

	enum ePlaybackSpeed {
		ePause,
		eSlowest,
		eSlower,
		eSlow,
		eNormal,
		eFast,
		eFaster,
		eFastest,
		eNumPlaybackSpeeds
	};

	static const char* PlaybackSpeedStr(ePlaybackSpeed speed) {
		return 	speed == ePause   ? "pause"   :
				speed == eSlowest ? "slowest" :
				speed == eSlower  ? "slower"  :
				speed == eSlow    ? "slow"    :
				speed == eNormal  ? "normal"  :
				speed == eFast    ? "fast"    :
				speed == eFaster  ? "faster"  :
				speed == eFastest ? "fastest" : "unknown";
	}

	enum eLiveSpeed {
		eNegMaxCorrection,
		eNegCorrection,
		eNoCorrection,
		ePosCorrection,
		ePosMaxCorrection,
		eNumLiveSpeeds
	};

	static const char* LiveSpeedStr(eLiveSpeed corr) {
		return	corr == eNegMaxCorrection ? "max negative" :
				corr == eNegCorrection    ? "negative"     :
				corr == eNoCorrection     ? "no"           :
				corr == ePosCorrection    ? "positive"     :
				corr == ePosMaxCorrection ? "max positive" : "unknown";
	}

	static const int s_playbackSpeeds[eNumDirections][eNumPlaybackSpeeds];
	static const int s_liveSpeeds[eNumLiveSpeeds];

	static const uchar s_pesVideoHeader[14];
	static const uchar s_mpeg2EndOfSequence[4];
	static const uchar s_h264EndOfSequence[8];

private:

	virtual cVideoCodec::eCodec ParseVideoCodec(const uchar *data, int length);

	static void OnBufferStall(void *data)
		{ (static_cast <cOmxDevice*> (data))->HandleBufferStall(); }

	static void OnEndOfStream(void *data)
		{ (static_cast <cOmxDevice*> (data))->HandleEndOfStream(); }

	static void OnStreamStart(void *data)
		{ (static_cast <cOmxDevice*> (data))->HandleStreamStart(); }

	static void OnVideoSetupChanged(void *data)
		{ (static_cast <cOmxDevice*> (data))->HandleVideoSetupChanged(); }

	void HandleBufferStall();
	void HandleEndOfStream();
	void HandleStreamStart();
	void HandleVideoSetupChanged();

	void FlushStreams(bool flushVideoRender = false);
	bool SubmitEOS(void);

	void ApplyTrickSpeed(int trickSpeed, bool forward);
	void PtsTracker(int64_t ptsDiff);

	void AdjustLiveSpeed(void);

	cOmx			 *m_omx;
	cRpiAudioDecoder *m_audio;
	cMutex			 *m_mutex;
	cTimeMs 		 *m_timer;

	cVideoCodec::eCodec	m_videoCodec;

	ePlayMode           m_playMode;
	eLiveSpeed          m_liveSpeed;
	ePlaybackSpeed      m_playbackSpeed;
	eDirection          m_direction;

	bool	m_hasVideo;
	bool	m_hasAudio;

	bool	m_skipAudio;
	int		m_playDirection;
	int		m_trickRequest;

	int64_t	m_audioPts;
	int64_t	m_videoPts;

	int64_t	m_lastStc;

	int m_display;
	int m_layer;

	bool doDescramble;
};

#endif
