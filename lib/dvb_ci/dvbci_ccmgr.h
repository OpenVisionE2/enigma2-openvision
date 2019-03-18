#ifndef __dvbci_dvbci_ccmgr_h
#define __dvbci_dvbci_ccmgr_h

#include <memory>
#include <lib/dvb_ci/dvbci_session.h>

class eDVBCICcSessionImpl;

class eDVBCICcSession: public eDVBCISession
{
	eDVBCISlot *slot;
	std::auto_ptr<eDVBCICcSessionImpl> pimpl;

	int receivedAPDU(const unsigned char *tag, const void *data, int len);
	int doAction();

public:
	eDVBCICcSession(eDVBCISlot *tslot);
	~eDVBCICcSession();

	void send(const unsigned char *tag, const void *data, int len);
	void addProgram(uint16_t program_number, std::vector<uint16_t>& pids);
	void removeProgram(uint16_t program_number, std::vector<uint16_t>& pids);
};

#endif
