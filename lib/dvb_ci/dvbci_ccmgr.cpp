/* DVB CI Content Control Manager */

#include <lib/dvb_ci/dvbci_ccmgr.h>
#include <lib/dvb_ci/res_content_ctrl.h>

eDVBCICcSession::eDVBCICcSession(eDVBCISlot *tslot) :
		slot(tslot), pimpl(new eDVBCICcSessionImpl(this, tslot->getSlotID(), 1))
{
	slot->setCCManager(this);
}

eDVBCICcSession::~eDVBCICcSession()
{
	slot->setCCManager(0);
}

int eDVBCICcSession::receivedAPDU(const unsigned char *tag, const void *data, int len)
{
	eDebug("SESSION(%d)/CC %02x %02x %02x", session_nb, tag[0],tag[1], tag[2]);
	//eDebugNoNewLine("SESSION(%d)/CC %02x %02x %02x: ", session_nb, tag[0],tag[1], tag[2]);
	//for (int i=0; i<len; i++)
	//	eDebugNoNewLine("%02x ", ((const unsigned char*)data)[i]);
	//eDebug(" ");

	pimpl->receiveAPDU(tag, data, len);

	return 0;
}

int eDVBCICcSession::doAction()
{
	switch (state) {
	case stateStarted:
		break;
	default:
		eDebug("unknown state");
		break;
	}
	return 0;
}

void eDVBCICcSession::send(const unsigned char *tag, const void *data, int len)
{
	sendAPDU(tag, data, len);
}

void eDVBCICcSession::addProgram(uint16_t program_number, std::vector<uint16_t>& pids)
{
	eDebugNoNewLine("SESSION(%d)/ADD PROGRAM %04x: ", session_nb, program_number);
	for (std::vector<uint16_t>::iterator it = pids.begin(); it != pids.end(); ++it)
		eDebugNoNewLine("%02x ", *it);
	eDebug(" ");

	if (!pids.empty())
		pimpl->addProgram(program_number, pids);
}

void eDVBCICcSession::removeProgram(uint16_t program_number, std::vector<uint16_t>& pids)
{
	eDebugNoNewLine("SESSION(%d)/REMOVE PROGRAM %04x: ", session_nb, program_number);
	for (std::vector<uint16_t>::iterator it = pids.begin(); it != pids.end(); ++it)
		eDebugNoNewLine("%02x ", *it);
	eDebug(" ");

	if (!pids.empty())
		pimpl->removeProgram(program_number, pids);
}
