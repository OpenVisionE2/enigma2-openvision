#include <sstream>
#include <fcntl.h>
#include <sys/ioctl.h>

#include <ios>
#include <fstream>
#include <sstream>
#include <iomanip>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/cfile.h>
#include <lib/base/ebase.h>

#include <lib/base/eerror.h>
#include <lib/base/nconfig.h> // access to python config
#include <lib/dvb/db.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb_ci/dvbci.h>
#include <lib/dvb_ci/dvbci_session.h>
#include <lib/dvb_ci/dvbci_camgr.h>
#include <lib/dvb_ci/dvbci_ui.h>
#include <lib/dvb_ci/dvbci_appmgr.h>
#include <lib/dvb_ci/dvbci_mmi.h>
#include <lib/dvb_ci/dvbci_ccmgr.h>

#include <dvbsi++/ca_program_map_section.h>

//#define CIDEBUG 1

#ifdef CIDEBUG
	#define eDebugCI(x...) eDebug(x)
#else
	#define eDebugCI(x...)
#endif

eDVBCIInterfaces *eDVBCIInterfaces::instance = 0;

#if HAVE_HYPERCUBE_DISABLED
#define __cplusplus

#include <lib/ciplus/driver_dvbci.h>
#include <lib/ciplus/inc/trid_datatype.h>
#include <lib/ciplus/inc/trid_errno.h>
#include <lib/ciplus/inc/trid_ci_types.h>
#include <lib/ciplus/inc/trid_ci_api.h>

int dvbci_slot1_gpio_cs = 1;
int dvbci_slot1_gpio_cd1 = 3;
int dvbci_slot1_gpio_cd2 = 4;
int dvbci_slot1_gpio_ireq = 52;
int dvbci_slot1_gpio_reset = 49;
int dvbci_slot2_gpio_cs = 0;
int dvbci_slot2_gpio_cd1 = 0;
int dvbci_slot2_gpio_cd2 = 0;
int dvbci_slot2_gpio_ireq  = 0;
int dvbci_slot2_gpio_reset = 0;

trid_uint8 app_info[128];
trid_uint8 language[32];
trid_uint8 country[32];

int ca_manager = 0;

unsigned int CardStatus;
std::vector<uint16_t> caids;

enum
{
NOTIFY_CARD_STATUS=0x01,
NOTIFY_MENU_DATA = 0x02,
NOTIFY_LIST_DATA = 0x04,
NOTIFY_ENQ_DATA = 0x08,
NOTIFY_CLOSE_MMI = 0x10
};

Trid_T_Menu menu_data;
Trid_T_List list_data;
Trid_T_Enq enq_data;

int Tridci_cb_status = 0;
int Tridci_init = 0;
void DVBCI_TridInit();

int DVBCI_GetCbStatus()
{
	if (Tridci_init == 0)
	{
		DVBCI_TridInit();
		Tridci_init = 1;
	}
	return Tridci_cb_status;
}

#define ci_ca

void DVBCI_Packcaids()
{	
	uint16_t ca_system_id[64]; 
	trid_sint32 num=64;
	RETURN_TYPE ret;
	ret = Trid_CI_GetCASystemId((trid_uint16*)ca_system_id, &num);
	if (!num)
	{
		for (int i=0; i<num; i++)
		{
			caids.push_back(ca_system_id[i]);
		}
		std::sort(caids.begin(), caids.end());
	}
	else
	{
		for (int i=0; i<num; i++)
		{
			caids.push_back(ca_system_id[i]);
		}
		std::sort(caids.begin(), caids.end());
	}
	eDebugCI("[CI] DVBCI_Packcaids.ret(%d) num(%d):\n", ret, num);
	for (ret=0;ret<num;ret++)
	{
		eDebugCI("0x%x.", ca_system_id[ret]);
	}
}

const std::vector<uint16_t> DVBCI_GetCAIDs(void)
{
	DVBCI_Packcaids(); 
	return caids;
}

#define call_driver

Trid_CI_CardStatus_t DVBCI_GetCardStatus() 
{
	Trid_CI_CardStatus_t CardStatus;
	eDebugCI("[CI] call function Trid_CI_GetCardStatus (%d).", CardStatus);
	Trid_CI_GetCardStatus(&CardStatus); 
	return CardStatus;
}

int DVBCI_StartMMI()
{
	eDebugCI("[CI] Trid_CI_AppInfo_EnterMenu.");
	Trid_CI_AppInfo_EnterMenu(); 
	return 0;
}

int DVBCI_StopMMI() 
{
	eDebugCI("[CI] Trid_CI_MMI_SendCloseMMI.");
	Trid_CI_MMI_SendCloseMMI();
	return 0;
}

int DVBCI_AnswerText(int answer)
{
	eDebugCI("[CI] Trid_CI_MMI_SendMenuAnsw.");
	Trid_CI_MMI_SendMenuAnsw((trid_uint8)answer);
	return 0;
}

int DVBCI_AnswerEnq(unsigned char *answer)
{
	eDebugCI("[CI] Trid_CI_MMI_SendEnqAnsw.");
	Trid_CI_MMI_SendEnqAnsw(1, strlen(answer), (trid_uint8*)answer); 
	return 0;
}

int DVBCI_CancelEnq()
{
	eDebugCI("[CI] Trid_CI_MMI_CloseEnqAnsw.");
	Trid_CI_MMI_SendEnqAnsw(0, 0, 0); 
	return 0;
}

trid_uint16 audioPid;
trid_uint16 videoPid;

int DVBCI_SendCAPMT(unsigned char *pmt, int len)
{
	trid_sint32 ca_system_id_match;RETURN_TYPE ret;
	ret = Trid_CI_SendCAPmt((trid_uint8* )pmt, len, &ca_system_id_match);
	eDebug("[CI] ret is %d. ca_system_id_match is %d.\n", ret, ca_system_id_match);
	return 0;
}

#define golobal_callback

trid_sint32 DVBCI_CardStatusChangeNotifyCallback(Trid_CI_CardStatus_t status)
{
	eDebugCI("[CI] <DVBCI_CardStatusChangeNotifyCallback>status %d.\n", status);
	eDVBCIInterfaces::getInstance()->CardStatusChangeNotifyCallback(0, status);
	return 0;
}

trid_sint32 DVBCI_CardGetHostLanguageCountryNotifyCallback(trid_uint8 language_code[], trid_uint8 country_code[])
{
	eDebugCI("[CI] <DVBCI_CardGetHostLanguageCountryNotifyCallback>language_code %s, country_code %s.  USA, ENG.\n", language_code, country_code);
	country_code[0]='U';
	country_code[1]='S';
	country_code[2]='A';
	language_code[0]='E';
	language_code[1]='N';
	language_code[2]='G';
	return 0;
}

trid_sint32 DVBCI_CardGetHostAVPIDCallback(trid_uint16 *AudioPID, trid_uint16 *VideoPID)
{
	eDebugCI("[CI] <DVBCI_CardGetHostAVPIDCallback> audio:%d, video:%d. set to audio:%d, video:%d.", *AudioPID, *VideoPID, audioPid, videoPid);
	*AudioPID = audioPid;
	*VideoPID = videoPid;
	return 0;
}

trid_sint32 DVBCI_CardTuneChannelCallback(trid_uint16 network_id, trid_uint16 orignal_network_id, trid_uint16 ts_id, trid_uint16 service_id)
{
	eDebugCI("[CI] <DVBCI_CardTuneChannelCallback>      sorry   no   realize   now .\n");
	return 0;
}

void DVBCI_CardSetDesKeyCallback(trid_uint8 key[/*8*/],trid_uint8 odd_even)
{
	eDebugCI("[CI] <DVBCI_CardSetDesKeyCallback>      sorry   no   realize   now .\n");
	return ;
}

void DVBCI_CardSetAesKeyCallback(trid_uint8 key[/*16*/],trid_uint8 iv[/*16*/],trid_uint8 odd_even)
{
	eDebugCI("[CI] <DVBCI_CardSetAesKeyCallback>      sorry   no   realize   now .\n");
	return ;
}

trid_bool DVBCI_MHEGAppQuerySupportCallback(
	trid_uint8                  app_domain_id[],
	trid_uint8                  app_domain_id_len,
	trid_uint8                  init_object[],
	trid_uint8                  init_object_len,
	Trid_CI_MHEG_StartAckCode_e *p_ack_code
)
{
	eDebugCI("[CI] <DVBCI_MHEGAppQuerySupportCallback>      sorry   no   realize   now .\n");
}

void DVBCI_MHEGFileAckNotifyCallback
(
	trid_uint8 file_name[], 
	trid_uint32  file_name_len,
	trid_uint8 file_data[], 
	trid_uint32 file_data_len
)
{
	eDebugCI("[CI] <DVBCI_MHEGFileAckNotifyCallback>      sorry   no   realize   now .\n");
}

void DVBCI_MHEGDataAckNotifyCallback
(
	trid_uint8 data[], 
	trid_uint32 data_len
)
{
	eDebugCI("[CI] <DVBCI_MHEGDataAckNotifyCallback>      sorry   no   realize   now .\n");
}

void DVBCI_MHEGAppAbortNotifyCallback(void)
{
	eDebugCI("[CI] <DVBCI_MHEGAppAbortNotifyCallback>      sorry   no   realize   now .\n");
}

#define data_callback 0

trid_sint32 DVBCI_MenuDataNotifyCallback(Trid_T_Menu* menu)
{
	eDVBCIInterfaces::getInstance()->MenuDataNotifyCallback(menu);
	return 0;
}

trid_sint32 DVBCI_ListDataNotifyCallback(Trid_T_List* list)
{
	eDVBCIInterfaces::getInstance()->ListDataNotifyCallback(list);
	return 0;
}

trid_sint32 DVBCI_EnqDataNotifyCallback(Trid_T_Enq* enq)
{
	eDVBCIInterfaces::getInstance()->EnqDataNotifyCallback(enq);
	return 0;
}

trid_sint32 DVBCI_CloseMMINotifyCallback()
{
	eDVBCIInterfaces::getInstance()->CloseMMINotifyCallback();
	return 0;
}
#define init_fun
RETURN_TYPE DVBCI_Set_Pcmcia_Func(void)
{
	CI_phys_driver phys_funcs;
	RETURN_TYPE ret = 0;
	phys_funcs.pcmcia_init = cnxt_dvbci_init;
	phys_funcs.pcmcia_term = cnxt_dvbci_term;
	phys_funcs.pcmcia_open = cnxt_dvbci_open;
	phys_funcs.pcmcia_close = cnxt_dvbci_close;
	phys_funcs.pcmcia_module_init = cnxt_dvbci_module_init;
	phys_funcs.pcmcia_register_read = cnxt_dvbci_register_read;
	phys_funcs.pcmcia_register_write = cnxt_dvbci_register_write;
	phys_funcs.pcmcia_attribute_mem_read = cnxt_dvbci_attribute_mem_read;
	phys_funcs.pcmcia_attribute_mem_write = cnxt_dvbci_attribute_mem_write;
	phys_funcs.pcmcia_signal_get_state = cnxt_dvbci_signal_get_state;
	phys_funcs.pcmcia_signal_set_state = cnxt_dvbci_signal_set_state;
	phys_funcs.pcmcia_enable_ts = cnxt_dvbci_enable_ts;
	phys_funcs.pcmcia_disable_ts = cnxt_dvbci_disable_ts;
	ret = Trid_CI_Set_Pcmcia_Func(&phys_funcs);
	eDebugCI("[CI] Trid_CI_Set_Pcmcia_Func return is %d.", ret);
	return 0;
}

void DVBCI_TridInit()
{
	RETURN_TYPE ret = 0;
	ret = cnxt_kal_initialize();
	ret = cnxt_dvbci_drv_init();
	DVBCI_Set_Pcmcia_Func();
	ret = Trid_CI_Start(DVBCI_CardStatusChangeNotifyCallback, 
							DVBCI_CardGetHostLanguageCountryNotifyCallback, 
							DVBCI_CardGetHostAVPIDCallback, 
							DVBCI_CardTuneChannelCallback, 
							DVBCI_CardSetDesKeyCallback,
							DVBCI_CardSetAesKeyCallback);
	ret = Trid_CI_MMI_RegisterMenuDataNotify(DVBCI_MenuDataNotifyCallback/*trid_sint32 (*callback)(Trid_T_Menu* menu)*/);
	ret = Trid_CI_MMI_RegisterListDataNotify(DVBCI_ListDataNotifyCallback/*trid_sint32 (*callback)(Trid_T_List* list)*/);
	ret = Trid_CI_MMI_RegisterEnqDataNotify(DVBCI_EnqDataNotifyCallback/*trid_sint32 (*callback)(Trid_T_Enq* enq)*/);
	ret = Trid_CI_MMI_RegisterCloseMMINotify(DVBCI_CloseMMINotifyCallback);
	ret = Trid_CI_MHEG_RegisterAppQuerySupport(DVBCI_MHEGAppQuerySupportCallback);
	ret = Trid_CI_MHEG_RegisterFileAckNotify(DVBCI_MHEGFileAckNotifyCallback);
	ret = Trid_CI_MHEG_RegisterDataAckNotify(DVBCI_MHEGDataAckNotifyCallback);
	ret = Trid_CI_MHEG_RegisterAppAbortNotify(DVBCI_MHEGAppAbortNotifyCallback);
	return ;
}
#endif

char* eDVBCISlot::readInputCI(int tuner_no)
{
	char id1[] = "NIM Socket";
	char id2[] = "Input_Name";
	char keys1[] = "1234567890";
	char keys2[] = "12ABCDabcd";
	char *inputName = 0;
	char buf[256];
	FILE *f;

	f = fopen("/proc/bus/nim_sockets", "rt");
	if (f)
	{
		while (fgets(buf, sizeof(buf), f))
		{
			char *p = strcasestr(buf, id1);
			if (!p)
				continue;

			p += strlen(id1);
			p += strcspn(p, keys1);
			if (*p && strtol(p, 0, 0) == tuner_no)
				break;
		}

		while (fgets(buf, sizeof(buf), f))
		{
			if (strcasestr(buf, id1))
				break;

			char *p = strcasestr(buf, id2);
			if (!p)
				continue;

			p = strchr(p + strlen(id2), ':');
			if (!p)
				continue;

			p++;
			p += strcspn(p, keys2);
			size_t len = strspn(p, keys2);
			if (len > 0)
			{
				inputName = strndup(p, len);
				break;
			}
		}

		fclose(f);
	}

	return inputName;
}

std::string eDVBCISlot::getTunerLetterDM(int tuner_no)
{
	char *srcCI = readInputCI(tuner_no);
	if (srcCI) return std::string(srcCI);
	return eDVBCISlot::getTunerLetter(tuner_no);
}

eCIClient::eCIClient(eDVBCIInterfaces *handler, int socket) : eUnixDomainSocket(socket, 1, eApp), parent(handler)
{
	receivedData = NULL;
	receivedCmd = 0;
	CONNECT(connectionClosed_, eCIClient::connectionLost);
	CONNECT(readyRead_, eCIClient::dataAvailable);
}

void eCIClient::connectionLost()
{
	if (parent) parent->connectionLost();
}

void eCIClient::dataAvailable()
{
	if (!receivedCmd)
	{
		if ((unsigned int)bytesAvailable() < sizeof(ciplus_header)) return;
		if ((unsigned int)readBlock((char*)&header, sizeof(ciplus_header)) < sizeof(ciplus_header)) return;
		header.magic = ntohl(header.magic);
		header.cmd = ntohl(header.cmd);
		header.size = ntohl(header.size);
		if (header.magic != CIPLUSHELPER_MAGIC)
		{
			if (parent) parent->connectionLost();
			return;
		}
		receivedCmd = header.cmd;
		receivedCmdSize = header.size;
	}
	if (receivedCmdSize)
	{
		if ((unsigned int)bytesAvailable() < receivedCmdSize) return;
		if (receivedCmdSize) delete [] receivedData;
		receivedData = new unsigned char[receivedCmdSize];
		if ((unsigned int)readBlock((char*)receivedData, receivedCmdSize) < receivedCmdSize) return;

		ciplus_message *message = (ciplus_message *)receivedData;
		switch (header.cmd)
		{
		default:
			{
				unsigned char *data = &receivedData[sizeof(ciplus_message)];
				parent->getSlot(ntohl(message->slot))->send(data, ntohl(message->size));
			}
			break;
		case eCIClient::CIPLUSHELPER_STATE_CHANGED:
			{
				eDVBCISession::setAction(ntohl(message->session), receivedData[sizeof(ciplus_message)]);
			}
			break;
		}
		receivedCmdSize = 0;
		receivedCmd = 0;
	}
}

void eCIClient::sendData(int cmd, int slot, int session, unsigned long idtag, unsigned char *tag, unsigned char *data, int len)
{
	ciplus_message message;
	message.slot = ntohl(slot);
	message.idtag = ntohl(idtag);
	memcpy(&message.tag, tag, 4);
	message.session = ntohl(session);
	message.size = ntohl(len);

	ciplus_header header;
	header.magic = htonl(CIPLUSHELPER_MAGIC);
	header.size = htonl(sizeof(message) + len);
	header.cmd = htonl(cmd);

	writeBlock((const char*)&header, sizeof(header));
	writeBlock((const char*)&message, sizeof(message));
	if (len)
	{
		writeBlock((const char*)data, len);
	}
}

void eDVBCIInterfaces::newConnection(int socket)
{
	if (client)
	{
		delete client;
	}
	client = new eCIClient(this, socket);
}

void eDVBCIInterfaces::connectionLost()
{
	if (client)
	{
		delete client;
		client = NULL;
	}
}

void eDVBCIInterfaces::sendDataToHelper(int cmd, int slot, int session, unsigned long idtag, unsigned char *tag, unsigned char *data, int len)
{
	if (client)	client->sendData(cmd, slot, session, idtag, tag, data, len);
}

bool eDVBCIInterfaces::isClientConnected()
{
	if (client) return true;
	return false;
}

#define CIPLUS_SERVER_SOCKET "/tmp/.listen.ciplus.socket"

eDVBCIInterfaces::eDVBCIInterfaces()
 : eServerSocket(CIPLUS_SERVER_SOCKET, eApp)
{
	int num_ci = 0;
	std::stringstream path;

	instance = this;
	client = NULL;
	m_stream_interface = interface_none;
	m_stream_finish_mode = finish_none;

	eDebug("[CI] scanning for common interfaces..");
#if HAVE_HYPERCUBE_DISABLED
	ePtr<eDVBCISlot> cislot;
	cislot = new eDVBCISlot(eApp, num_ci);
	m_slots.push_back(cislot);
	num_ci++;
#else
	for (;;)
	{
		path.str("");
		path.clear();
		path << "/dev/ci" << num_ci;

		if(::access(path.str().c_str(), R_OK) < 0)
			break;

		ePtr<eDVBCISlot> cislot;

		cislot = new eDVBCISlot(eApp, num_ci);
		m_slots.push_back(cislot);

		++num_ci;
	}

	for (eSmartPtrList<eDVBCISlot>::iterator it(m_slots.begin()); it != m_slots.end(); ++it)
#ifdef DREAMBOX_DUAL_TUNER
		it->setSource(eDVBCISlot::getTunerLetterDM(0));
#else
		it->setSource("A");
#endif

	for (int tuner_no = 0; tuner_no < 26; ++tuner_no) // NOTE: this assumes tuners are A .. Z max.
	{
		path.str("");
		path.clear();
		path << "/proc/stb/tsmux/input" << tuner_no << "_choices";

		if(::access(path.str().c_str(), R_OK) < 0)
			break;

#ifdef DREAMBOX_DUAL_TUNER
		setInputSource(tuner_no, eDVBCISlot::getTunerLetterDM(tuner_no));
#else
		setInputSource(tuner_no, eDVBCISlot::getTunerLetter(tuner_no));
#endif
	}
#endif
	eDebug("[CI] done, found %d common interface slots", num_ci);

	if (num_ci)
	{
		static const char *proc_ci_choices = "/proc/stb/tsmux/ci0_input_choices";

		if (CFile::contains_word(proc_ci_choices, "PVR"))	// lowest prio = PVR
			m_stream_interface = interface_use_pvr;

		if (CFile::contains_word(proc_ci_choices, "DVR"))	// low prio = DVR
			m_stream_interface = interface_use_dvr;

		if (CFile::contains_word(proc_ci_choices, "DVR0"))	// high prio = DVR0
			m_stream_interface = interface_use_dvr;

		if (m_stream_interface == interface_none)			// fallback = DVR
		{
			m_stream_interface = interface_use_dvr;
			eDebug("[CI] Streaming CI routing interface not advertised, assuming DVR method");
		}

		if (CFile::contains_word(proc_ci_choices, "PVR_NONE"))	// low prio = PVR_NONE
			m_stream_finish_mode = finish_use_pvr_none;

		if (CFile::contains_word(proc_ci_choices, "NONE"))		// high prio = NONE
			m_stream_finish_mode = finish_use_none;

		if (m_stream_finish_mode == finish_none)				// fallback = "tuner"
		{
			m_stream_finish_mode = finish_use_tuner_a;
			eDebug("[CI] Streaming CI finish interface not advertised, assuming \"tuner\" method");
		}
	}
}

eDVBCIInterfaces::~eDVBCIInterfaces()
{
#if HAVE_HYPERCUBE_DISABLED
	cnxt_kal_terminate();
#endif
}

eDVBCIInterfaces *eDVBCIInterfaces::getInstance()
{
	return instance;
}

eDVBCISlot *eDVBCIInterfaces::getSlot(int slotid)
{
	for(eSmartPtrList<eDVBCISlot>::iterator i(m_slots.begin()); i != m_slots.end(); ++i)
		if(i->getSlotID() == slotid)
			return i;

	eDebug("[CI] FIXME: request for unknown slot");

	return 0;
}

int eDVBCIInterfaces::getSlotState(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return eDVBCISlot::stateInvalid;

	return slot->getState();
}

int eDVBCIInterfaces::reset(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	return slot->reset();
}

int eDVBCIInterfaces::initialize(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	slot->removeService();

	return sendCAPMT(slotid);
}

int eDVBCIInterfaces::sendCAPMT(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	PMTHandlerList::iterator it = m_pmt_handlers.begin();
	while (it != m_pmt_handlers.end())
	{
		eDVBCISlot *tmp = it->cislot;
		while (tmp && tmp != slot)
			tmp = tmp->linked_next;
		if (tmp)
		{
			tmp->sendCAPMT(it->pmthandler);  // send capmt
			break;
		}
		++it;
	}

	return 0;
}

int eDVBCIInterfaces::startMMI(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	return slot->startMMI();
}

int eDVBCIInterfaces::stopMMI(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	return slot->stopMMI();
}

int eDVBCIInterfaces::answerText(int slotid, int answer)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	return slot->answerText(answer);
}

int eDVBCIInterfaces::answerEnq(int slotid, char *value)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	return slot->answerEnq(value);
}

int eDVBCIInterfaces::cancelEnq(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	return slot->cancelEnq();
}

void eDVBCIInterfaces::ciRemoved(eDVBCISlot *slot)
{
	if (slot->use_count)
	{
		eDebug("[CI] Slot %d: removed... usecount %d", slot->getSlotID(), slot->use_count);
		for (PMTHandlerList::iterator it(m_pmt_handlers.begin());
			it != m_pmt_handlers.end(); ++it)
		{
			if (it->cislot == slot) // remove the base slot
				it->cislot = slot->linked_next;
			else if (it->cislot)
			{
				eDVBCISlot *prevSlot = it->cislot, *hSlot = it->cislot->linked_next;
				while (hSlot)
				{
					if (hSlot == slot) {
						prevSlot->linked_next = slot->linked_next;
						break;
					}
					prevSlot = hSlot;
					hSlot = hSlot->linked_next;
				}
			}
		}
		if (slot->linked_next)
			slot->linked_next->setSource(slot->current_source);
		else // last CI in chain
#ifdef DREAMBOX_DUAL_TUNER
			setInputSource(slot->current_tuner, eDVBCISlot::getTunerLetterDM(slot->current_tuner));
#else
			setInputSource(slot->current_tuner, eDVBCISlot::getTunerLetter(slot->current_tuner));
#endif
		slot->linked_next = 0;
		slot->use_count=0;
		slot->plugged=true;
		slot->user_mapped=false;
		slot->removeService(0xFFFF);
		recheckPMTHandlers();
	}
}

#if HAVE_HYPERCUBE_DISABLED
int eDVBCIInterfaces::CardStatusChangeNotifyCallback(int slotid, Trid_CI_CardStatus_t status)
{
	eDebugCI("[CI] CardStatusChangeNotifyCallback. status %d.", status);
	switch (status)
	{
	case _TRID_CARD_REMOVE_:
		CardStatus=0;
		break;
	case _TRID_CARD_INSERT_:
		CardStatus=1<<1;
		break;
	case _TRID_CARD_INVALID_CARD_:
		CardStatus=1<<2;
		break;
	case _TRID_CARD_MMI_READY_:
		CardStatus|=1<<3;
		break;
	case _TRID_CARD_CA_READY_:
		CardStatus|=1<<4;
		break;
	case _TRID_CARD_MMI_CA_READY_:
		CardStatus|=1<<5;
		break;
	case _TRID_CARD_UPGRADE_START_:
		CardStatus|=1<<6;
		break;
	case _TRID_CARD_UPGRADE_FINISH_:
		CardStatus|=1<<7;
		break;
	case _TRID_CARD_RESET_START_:
		CardStatus|=1<<8;
		break;
	case _TRID_CARD_IO_ERROR_:
		CardStatus=1<<9;
		break;
	}
	Tridci_cb_status |= NOTIFY_CARD_STATUS;
	return 0;
}
 
trid_sint32 eDVBCIInterfaces::MenuDataNotifyCallback(Trid_T_Menu* menu)
{
	Trid_T_Menu* pmenu;
	pmenu = &menu_data;
	eDebugCI("[CI] MenuDataNotifyCallback.");
	memcpy((char *)pmenu, (char *)menu, sizeof(Trid_T_Menu));
	Tridci_cb_status |= NOTIFY_MENU_DATA;
	return 0;
}

trid_sint32 eDVBCIInterfaces::ListDataNotifyCallback(Trid_T_List* list)
{
	Trid_T_List* plist;
	plist = &list_data;
	eDebugCI("[CI] ListDataNotifyCallback.");
	memcpy((char *)plist, (char *)list, sizeof(Trid_T_List));
	Tridci_cb_status |= NOTIFY_LIST_DATA;
	return 0;
}

trid_sint32 eDVBCIInterfaces::EnqDataNotifyCallback(Trid_T_Enq* enq)
{
	Trid_T_Enq* penq;
	eDebugCI("[CI] EnqDataNotifyCallback.");
	penq = &enq_data;
	memcpy((char *)penq, (char *)enq, sizeof(Trid_T_Enq));
	Tridci_cb_status |= NOTIFY_ENQ_DATA;
	return 0;
}

trid_sint32 eDVBCIInterfaces::CloseMMINotifyCallback()
{
	Tridci_cb_status |= NOTIFY_CLOSE_MMI;
	eDebugCI("[CI] CloseMMINotifyCallback.");
	return 0;
}

trid_sint32 eDVBCIInterfaces::GetHostAVPIDCallback(trid_uint16 *AudioPID, trid_uint16 *VideoPID)
{
	Tridci_cb_status |= NOTIFY_CLOSE_MMI;
	eDebugCI("[CI] CloseMMINotifyCallback.");
	return 0;
}
#endif

static bool canDescrambleMultipleServices(int slotid)
{
	char configStr[255];
	snprintf(configStr, 255, "config.ci.%d.canDescrambleMultipleServices", slotid);
	std::string str = eConfigManager::getConfigValue(configStr);
	if ( str == "auto" )
	{
		std::string appname = eDVBCI_UI::getInstance()->getAppName(slotid);
		if (appname.find("AlphaCrypt") != std::string::npos || appname.find("Multi") != std::string::npos)
			return true;
	}
	else if (str == "yes")
		return true;
	return false;
}

#if HAVE_HYPERCUBE_DISABLED
void eDVBCIInterfaces::recheckPMTHandlers()
{
	eDebugCI("[CI] eDVBCIInterfaces recheckPMTHandlers.");
	for (PMTHandlerList::iterator it(m_pmt_handlers.begin());
		it != m_pmt_handlers.end(); ++it)
	{
		CAID_LIST caids;
		ePtr<eDVBService> service;
		eServiceReferenceDVB ref;
		eDVBCISlot *tmp = it->cislot;
		eDVBServicePMTHandler *pmthandler = it->pmthandler;
		eDVBServicePMTHandler::program p;
		bool plugged_cis_exist = false;
		pmthandler->getServiceReference(ref);
		pmthandler->getService(service);
		eDebugCI("[CI] recheck %p %s", pmthandler, ref.toString().c_str());
		for (eSmartPtrList<eDVBCISlot>::iterator ci_it(m_slots.begin()); ci_it != m_slots.end(); ++ci_it)
			if (ci_it->plugged && ci_it->getCAManager())
			{
				eDebug("[CI] Slot %d plugged", ci_it->getSlotID());
				ci_it->plugged = false;
				plugged_cis_exist = true;
			}
		if (!plugged_cis_exist)
		{
			while(tmp)
			{
				if (!tmp->running_services.empty())
					break;
				tmp=tmp->linked_next;
			}
			if (tmp)
			{
				eDebugCI("[CI] already assigned and running CI!");
				continue;
			}
		}
		if (!pmthandler->getProgramInfo(p))
		{
			int cnt=0;
			std::set<eDVBServicePMTHandler::program::capid_pair> set(p.caids.begin(), p.caids.end());
			for (std::set<eDVBServicePMTHandler::program::capid_pair>::reverse_iterator x(set.rbegin()); x != set.rend(); ++x, ++cnt)
				caids.push_front(x->caid);
			if (service && cnt)
				service->m_ca = caids;
		}
		if (service)
		{
			caids = service->m_ca;
		}
		if (caids.empty())
		{
			continue;
		}
		for (eSmartPtrList<eDVBCISlot>::iterator ci_it(m_slots.begin()); ci_it != m_slots.end(); ++ci_it)
		{
			eDebugCI("[CI] check Slot %d", ci_it->getSlotID());
			bool useThis=false;
			bool user_mapped=true;
			int ca_manager = ci_it->getCAManager();
			eDebugCI("[CI] if ca_manager %d.", ca_manager);
			if (ca_manager)
			{
				int mask=0;
				if (!ci_it->possible_services.empty())
				{
					eDebugCI("[CI] if (!ci_it->possible_services.empty()).");
					mask |= 1;
					serviceSet::iterator it = ci_it->possible_services.find(ref);
					if (it != ci_it->possible_services.end())
					{
						eDebug("[CI] '%s' is in service list of slot %d... so use it", ref.toString().c_str(), ci_it->getSlotID());
						useThis = true;
					}
					else
					{
						eServiceReferenceDVB parent_ref = ref.getParentServiceReference();
						if (parent_ref)
						{
							it = ci_it->possible_services.find(ref);
							if (it != ci_it->possible_services.end())
							{
								eDebug("[CI] parent '%s' of '%s' is in service list of slot %d... so use it",
									parent_ref.toString().c_str(), ref.toString().c_str(), ci_it->getSlotID());
								useThis = true;
							}
						}
					}
				}
				if (!useThis && !ci_it->possible_providers.empty())
				{
					eDebugCI("[CI] if (!useThis && !ci_it->possible_providers.empty())");
					eDVBNamespace ns = ref.getDVBNamespace();
					mask |= 2;
					if (!service)
					{
						eServiceReferenceDVB parent_ref = ref.getParentServiceReference();
						eDVBDB::getInstance()->getService(parent_ref, service);
					}
					if (service)
					{
						providerSet::iterator it = ci_it->possible_providers.find(providerPair(service->m_provider_name, ns.get()));
						if (it != ci_it->possible_providers.end())
						{
							eDebug("[CI] '%s/%08x' is in provider list of slot %d... so use it", service->m_provider_name.c_str(), ns.get(), ci_it->getSlotID());
							useThis = true;
						}
					}
				}
				if (!useThis && !ci_it->possible_caids.empty())
				{
					eDebugCI("[CI] if (!useThis && !ci_it->possible_caids.empty())");
					mask |= 4;
					for (CAID_LIST::iterator ca(caids.begin()); ca != caids.end(); ++ca)
					{
						caidSet::iterator it = ci_it->possible_caids.find(*ca);
						if (it != ci_it->possible_caids.end())
						{
							eDebug("[CI] caid '%04x' is in caid list of slot %d... so use it", *ca, ci_it->getSlotID());
							useThis = true;
							break;
						}
					}
				}
				if (!useThis && !mask)
				{
					eDebugCI("[CI] if (!useThis && !mask)");
					const std::vector<uint16_t> &ci_caids = DVBCI_GetCAIDs();
					for (CAID_LIST::iterator ca(caids.begin()); ca != caids.end(); ++ca)
					{
						std::vector<uint16_t>::const_iterator z =
						std::lower_bound(ci_caids.begin(), ci_caids.end(), *ca);
						if ( z != ci_caids.end() && *z == *ca )
						{
							eDebug("[CI] The CI in Slot %d has said it can handle caid %04x... so use it", ci_it->getSlotID(), *z);
							useThis = true;
							user_mapped = false;
							break;
						}
					}
				}
			}

			eDebugCI("[CI] if (useThis) %d.", useThis);
			if (useThis)
			{
				eDVBCISlot *tmp = it->cislot;
				while(tmp)
				{
					if (tmp == ci_it)
						break;
					tmp=tmp->linked_next;
				}
				if (tmp)
				{
					eDebugCI("[CI] already assigned!");
					continue;
				}
				eDebugCI("[CI] current slot %d usecount %d", ci_it->getSlotID(), ci_it->use_count);
				if (ci_it->use_count)
				{
					bool found = false;
					useThis = false;
					PMTHandlerList::iterator tmp = m_pmt_handlers.begin();
					while (!found && tmp != m_pmt_handlers.end())
					{
						eDebugCI("[CI] .");
						eDVBCISlot *tmp_cislot = tmp->cislot;
						while (!found && tmp_cislot)
						{
							eDebugCI("[CI] ..");
							eServiceReferenceDVB ref2;
							tmp->pmthandler->getServiceReference(ref2);
							if ( tmp_cislot == ci_it && it->pmthandler != tmp->pmthandler )
							{
								eDebugCI("[CI] check pmthandler %s for same service/tp", ref2.toString().c_str());
								eDVBChannelID s1, s2;
								if (ref != ref2)
								{
									eDebugCI("[CI] different services!");
									ref.getChannelID(s1);
									ref2.getChannelID(s2);
								}
								if (ref == ref2 || (s1 == s2 && canDescrambleMultipleServices(tmp_cislot->getSlotID())))
								{
									found = true;
									eDebugCI("[CI] found!");
									eDVBCISlot *tmpci = it->cislot = tmp->cislot;
									while(tmpci)
									{
										++tmpci->use_count;
										eDebug("[CI] (2)CISlot %d, usecount now %d", tmpci->getSlotID(), tmpci->use_count);
										tmpci=tmpci->linked_next;
									}
								}
							}
							tmp_cislot=tmp_cislot->linked_next;
						}
						eDebugCI("[CI] ...");
						++tmp;
					}
				}
				if (useThis)
				{
					if (ci_it->user_mapped)
					{
						eDebugCI("[CI] user mapped CI already in use... dont link!");
						continue;
					}
					++ci_it->use_count;
					eDebug("[CI] (1)CISlot %d, usecount now %d", ci_it->getSlotID(), ci_it->use_count);
					data_source ci_source=CI_A;
					switch(ci_it->getSlotID())
					{
						case 0: ci_source = CI_A; break;
						case 1: ci_source = CI_B; break;
						case 2: ci_source = CI_C; break;
						case 3: ci_source = CI_D; break;
						default:
							eDebug("[CI] try to get source for CI %d!!\n", ci_it->getSlotID());
							break;
					}
					if (!it->cislot)
					{
						int tunernum = -1;
						eUsePtr<iDVBChannel> channel;
						if (!pmthandler->getChannel(channel))
						{
							ePtr<iDVBFrontend> frontend;
							if (!channel->getFrontend(frontend))
							{
								eDVBFrontend *fe = (eDVBFrontend*) &(*frontend);
								tunernum = fe->getSlotID();
							}
						}
						ASSERT(tunernum != -1);
						data_source tuner_source = TUNER_A;
						switch (tunernum)
						{
							case 0: tuner_source = TUNER_A; break;
							case 1: tuner_source = TUNER_B; break;
							case 2: tuner_source = TUNER_C; break;
							case 3: tuner_source = TUNER_D; break;
							default:
								eDebug("[CI] try to get source for tuner %d!!\n", tunernum);
								break;
						}
						ci_it->current_tuner = tunernum;
						setInputSource(tunernum, ci_source);
						ci_it->setSource(tuner_source);
					}
					else
					{
						ci_it->current_tuner = it->cislot->current_tuner;
						ci_it->linked_next = it->cislot;
						ci_it->setSource(ci_it->linked_next->current_source);
						ci_it->linked_next->setSource(ci_source);
					}
					it->cislot = ci_it;
					eDebugCI("[CI] assigned!");
					gotPMT(pmthandler);
				}
				if (it->cislot && user_mapped)
				{
					eDebugCI("[CI] user mapped CI assigned... dont link CIs!");
					break;
				}
			}
		}
	}
	eDebugCI("[CI] eDVBCIInterfaces recheckPMTHandlers.end");
}
#else
void eDVBCIInterfaces::recheckPMTHandlers()
{
	eDebugCI("[CI] recheckPMTHAndlers()");
	for (PMTHandlerList::iterator it(m_pmt_handlers.begin());
		it != m_pmt_handlers.end(); ++it)
	{
		CAID_LIST caids;
		ePtr<eDVBService> service;
		eServiceReferenceDVB ref;
		eDVBCISlot *tmp = it->cislot;
		eDVBServicePMTHandler *pmthandler = it->pmthandler;
		eDVBServicePMTHandler::program p;
		bool plugged_cis_exist = false;

		pmthandler->getServiceReference(ref);
		pmthandler->getService(service);

		eDebugCI("[CI] recheck %p %s", pmthandler, ref.toString().c_str());
		for (eSmartPtrList<eDVBCISlot>::iterator ci_it(m_slots.begin()); ci_it != m_slots.end(); ++ci_it)
			if (ci_it->plugged && ci_it->getCAManager())
			{
				eDebug("[CI] Slot %d plugged", ci_it->getSlotID());
				ci_it->plugged = false;
				plugged_cis_exist = true;
			}

		// check if this pmt handler has already assigned CI(s) .. and this CI(s) are already running
		if (!plugged_cis_exist)
		{
			while(tmp)
			{
				if (!tmp->running_services.empty())
					break;
				tmp=tmp->linked_next;
			}
			if (tmp) // we dont like to change tsmux for running services
			{
				eDebugCI("[CI] already assigned and running CI!\n");
				continue;
			}
		}

		if (!pmthandler->getProgramInfo(p))
		{
			int cnt=0;
			std::set<eDVBServicePMTHandler::program::capid_pair> set(p.caids.begin(), p.caids.end());
			for (std::set<eDVBServicePMTHandler::program::capid_pair>::reverse_iterator x(set.rbegin()); x != set.rend(); ++x, ++cnt)
				caids.push_front(x->caid);
			if (service && cnt)
				service->m_ca = caids;
		}

		if (service)
			caids = service->m_ca;

		if (caids.empty())
			continue; // unscrambled service

		for (eSmartPtrList<eDVBCISlot>::iterator ci_it(m_slots.begin()); ci_it != m_slots.end(); ++ci_it)
		{
			eDebugCI("[CI] check Slot %d", ci_it->getSlotID());
			bool useThis=false;
			bool user_mapped=true;
			eDVBCICAManagerSession *ca_manager = ci_it->getCAManager();

			if (ca_manager)
			{
				int mask=0;
				if (!ci_it->possible_services.empty())
				{
					mask |= 1;
					serviceSet::iterator it = ci_it->possible_services.find(ref);
					if (it != ci_it->possible_services.end())
					{
						eDebug("[CI] '%s' is in service list of slot %d... so use it", ref.toString().c_str(), ci_it->getSlotID());
						useThis = true;
					}
					else // check parent
					{
						eServiceReferenceDVB parent_ref = ref.getParentServiceReference();
						if (parent_ref)
						{
							it = ci_it->possible_services.find(ref);
							if (it != ci_it->possible_services.end())
							{
								eDebug("[CI] parent '%s' of '%s' is in service list of slot %d... so use it",
								parent_ref.toString().c_str(), ref.toString().c_str(), ci_it->getSlotID());
								useThis = true;
							}
						}
					}
				}
				if (!useThis && !ci_it->possible_providers.empty())
				{
					eDVBNamespace ns = ref.getDVBNamespace();
					mask |= 2;
					if (!service) // subservice?
					{
						eServiceReferenceDVB parent_ref = ref.getParentServiceReference();
						eDVBDB::getInstance()->getService(parent_ref, service);
					}
					if (service)
					{
						providerSet::iterator it = ci_it->possible_providers.find(providerPair(service->m_provider_name, ns.get()));
						if (it != ci_it->possible_providers.end())
						{
							eDebug("[CI] '%s/%08x' is in provider list of slot %d... so use it", service->m_provider_name.c_str(), ns.get(), ci_it->getSlotID());
							useThis = true;
						}
					}
				}
				if (!useThis && !ci_it->possible_caids.empty())
				{
					mask |= 4;
					for (CAID_LIST::iterator ca(caids.begin()); ca != caids.end(); ++ca)
					{
						caidSet::iterator it = ci_it->possible_caids.find(*ca);
						if (it != ci_it->possible_caids.end())
						{
							eDebug("[CI] caid '%04x' is in caid list of slot %d... so use it", *ca, ci_it->getSlotID());
							useThis = true;
							break;
						}
					}
				}
				if (!useThis && !mask)
				{
					const std::vector<uint16_t> &ci_caids = ca_manager->getCAIDs();
					for (CAID_LIST::iterator ca(caids.begin()); ca != caids.end(); ++ca)
					{
						std::vector<uint16_t>::const_iterator z =
							std::lower_bound(ci_caids.begin(), ci_caids.end(), *ca);
						if ( z != ci_caids.end() && *z == *ca )
						{
							eDebug("[CI] The CI in Slot %d has said it can handle caid %04x... so use it", ci_it->getSlotID(), *z);
							useThis = true;
							user_mapped = false;
							break;
						}
					}
				}
			}

			if (useThis)
			{
				// check if this CI is already assigned to this pmthandler
				eDVBCISlot *tmp = it->cislot;
				while(tmp)
				{
					if (tmp == ci_it)
						break;
					tmp=tmp->linked_next;
				}
				if (tmp) // ignore already assigned cislots...
				{
					eDebugCI("[CI] already assigned!");
					continue;
				}
				eDebugCI("[CI] current slot %d usecount %d", ci_it->getSlotID(), ci_it->use_count);
				if (ci_it->use_count)  // check if this CI can descramble more than one service
				{
					bool found = false;
					useThis = false;
					PMTHandlerList::iterator tmp = m_pmt_handlers.begin();
					while (!found && tmp != m_pmt_handlers.end())
					{
						eDebugCI("[CI] .");
						eDVBCISlot *tmp_cislot = tmp->cislot;
						while (!found && tmp_cislot)
						{
							eDebugCI("[CI] ..");
							eServiceReferenceDVB ref2;
							tmp->pmthandler->getServiceReference(ref2);
							if ( tmp_cislot == ci_it && it->pmthandler != tmp->pmthandler )
							{
								eDebugCI("[CI] check pmthandler %s for same service/tp", ref2.toString().c_str());
								eDVBChannelID s1, s2;
								if (ref != ref2)
								{
									eDebugCI("[CI] different services!");
									ref.getChannelID(s1);
									ref2.getChannelID(s2);
								}
								if (ref == ref2 || (s1 == s2 && canDescrambleMultipleServices(tmp_cislot->getSlotID())))
								{
									found = true;
									eDebugCI("[CI] found!");
									eDVBCISlot *tmpci = it->cislot = tmp->cislot;
									while(tmpci)
									{
										++tmpci->use_count;
										eDebug("[CI] (2)CISlot %d, usecount now %d", tmpci->getSlotID(), tmpci->use_count);
										tmpci=tmpci->linked_next;
									}
								}
							}
							tmp_cislot=tmp_cislot->linked_next;
						}
						eDebugCI("[CI] ...");
						++tmp;
					}
				}

				if (useThis)
				{
					if (ci_it->user_mapped)  // we dont like to link user mapped CIs
					{
						eDebugCI("[CI] user mapped CI already in use... dont link!");
						continue;
					}

					++ci_it->use_count;
					eDebug("[CI] (1)Slot %d, usecount now %d", ci_it->getSlotID(), ci_it->use_count);

					std::stringstream ci_source;
					ci_source << "CI" << ci_it->getSlotID();

					if (!it->cislot)
					{
						int tunernum = -1;
						eUsePtr<iDVBChannel> channel;
						if (!pmthandler->getChannel(channel))
						{
							ePtr<iDVBFrontend> frontend;
							if (!channel->getFrontend(frontend))
							{
								eDVBFrontend *fe = (eDVBFrontend*) &(*frontend);
								tunernum = fe->getSlotID();
							}
							if (tunernum != -1)
							{
								setInputSource(tunernum, ci_source.str());
#ifdef DREAMBOX_DUAL_TUNER
								ci_it->setSource(eDVBCISlot::getTunerLetterDM(tunernum));
#else
								ci_it->setSource(eDVBCISlot::getTunerLetter(tunernum));
#endif
							}
							else
							{
								/*
								 * No associated frontend, this must be a DVR source
								 *
								 * No need to set tuner input (setInputSource), because we have no tuner.
								 */

								switch(m_stream_interface)
								{
									case interface_use_dvr:
									{
										std::stringstream source;
#ifndef HAVE_RASPBERRYPI
										source << "DVR" << channel->getDvrId();
#endif
										ci_it->setSource(source.str());
										break;
									}

									case interface_use_pvr:
									{
										ci_it->setSource("PVR");
										break;
									}

									default:
									{
										eDebug("[CI] warning: no valid CI streaming interface");
										break;
									}
								}
							}
						}
						ci_it->current_tuner = tunernum;
					}
					else
					{
						ci_it->current_tuner = it->cislot->current_tuner;
						ci_it->linked_next = it->cislot;
						ci_it->setSource(ci_it->linked_next->current_source);
						ci_it->linked_next->setSource(ci_source.str());
					}
					it->cislot = ci_it;
					eDebugCI("[CI] assigned!");
					gotPMT(pmthandler);
				}

				if (it->cislot && user_mapped) // CI assigned to this pmthandler in this run.. and user mapped? then we break here.. we dont like to link other CIs to user mapped CIs
				{
					eDebugCI("[CI] user mapped CI assigned... dont link CIs!");
					break;
				}
			}
		}
	}
}
#endif
void eDVBCIInterfaces::addPMTHandler(eDVBServicePMTHandler *pmthandler)
{
	// check if this pmthandler is already registered
	PMTHandlerList::iterator it = m_pmt_handlers.begin();
	while (it != m_pmt_handlers.end())
	{
		if ( *it++ == pmthandler )
			return;
	}

	eServiceReferenceDVB ref;
	pmthandler->getServiceReference(ref);
	eDebug("[eDVBCIInterfaces] addPMTHandler %s", ref.toString().c_str());

	m_pmt_handlers.push_back(CIPmtHandler(pmthandler));
	recheckPMTHandlers();
}

void eDVBCIInterfaces::removePMTHandler(eDVBServicePMTHandler *pmthandler)
{
	PMTHandlerList::iterator it=std::find(m_pmt_handlers.begin(),m_pmt_handlers.end(),pmthandler);
	if (it != m_pmt_handlers.end())
	{
		eDVBCISlot *slot = it->cislot;
		eDVBCISlot *base_slot = slot;
		eDVBServicePMTHandler *pmthandler = it->pmthandler;
		m_pmt_handlers.erase(it);

		eServiceReferenceDVB service_to_remove;
		pmthandler->getServiceReference(service_to_remove);

		bool sameServiceExist=false;
		for (PMTHandlerList::iterator i=m_pmt_handlers.begin(); i != m_pmt_handlers.end(); ++i)
		{
			if (i->cislot)
			{
				eServiceReferenceDVB ref;
				i->pmthandler->getServiceReference(ref);
				if ( ref == service_to_remove )
				{
					sameServiceExist=true;
					break;
				}
			}
		}

		while(slot)
		{
			eDVBCISlot *next = slot->linked_next;
			if (!sameServiceExist)
			{
				eDebug("[eDVBCIInterfaces] remove last pmt handler for service %s send empty capmt",
					service_to_remove.toString().c_str());
				std::vector<uint16_t> caids;
				caids.push_back(0xFFFF);
				slot->sendCAPMT(pmthandler, caids);  // send a capmt without caids to remove a running service
				slot->removeService(service_to_remove.getServiceID().get());

				if (slot->current_tuner == -1)
				{
					// no previous tuner to go back to, signal to CI interface CI action is finished

					std::string finish_source;

					switch (m_stream_finish_mode)
					{
						case finish_use_tuner_a:
						{
							finish_source = "A";
							break;
						}

						case finish_use_pvr_none:
						{
							finish_source = "PVR_NONE";
							break;
						}

						case finish_use_none:
						{
							finish_source = "NONE";
							break;
						}

						default:
							(void)0;
					}

					if(finish_source == "")
					{
						eDebug("[CI] warning: CI streaming finish mode not set, assuming \"tuner A\"");
						finish_source = "A";
					}

					slot->setSource(finish_source);
				}
			}

			if (!--slot->use_count)
			{
				if (slot->linked_next)
					slot->linked_next->setSource(slot->current_source);
				else
#ifdef DREAMBOX_DUAL_TUNER
					setInputSource(slot->current_tuner, eDVBCISlot::getTunerLetterDM(slot->current_tuner));
#else
					setInputSource(slot->current_tuner, eDVBCISlot::getTunerLetter(slot->current_tuner));
#endif

				if (base_slot != slot)
				{
					eDVBCISlot *tmp = it->cislot;
					while(tmp->linked_next != slot)
						tmp = tmp->linked_next;
					ASSERT(tmp);
					if (slot->linked_next)
						tmp->linked_next = slot->linked_next;
					else
						tmp->linked_next = 0;
				}
				else // removed old base slot.. update ptr
					base_slot = slot->linked_next;
				slot->linked_next = 0;
				slot->user_mapped = false;
			}
			eDebug("[CI] (3)slot %d usecount is now %d", slot->getSlotID(), slot->use_count);
			slot = next;
		}
		// check if another service is waiting for the CI
		recheckPMTHandlers();
	}
}

void eDVBCIInterfaces::gotPMT(eDVBServicePMTHandler *pmthandler)
{
	eDebug("[eDVBCIInterfaces] gotPMT");
	PMTHandlerList::iterator it=std::find(m_pmt_handlers.begin(), m_pmt_handlers.end(), pmthandler);
	if (it != m_pmt_handlers.end() && it->cislot)
	{
		eDVBCISlot *tmp = it->cislot;
		while(tmp)
		{
			eDebugCI("[CI] check slot %d %d %d", tmp->getSlotID(), tmp->running_services.empty(), canDescrambleMultipleServices(tmp->getSlotID()));
			if (tmp->running_services.empty() || canDescrambleMultipleServices(tmp->getSlotID()))
				tmp->sendCAPMT(pmthandler);
			tmp = tmp->linked_next;
		}
	}
}

int eDVBCIInterfaces::getMMIState(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	return slot->getMMIState();
}

int eDVBCIInterfaces::setInputSource(int tuner_no, const std::string &source)
{
	if (tuner_no >= 0)
	{
		char buf[64];
		snprintf(buf, sizeof(buf), "/proc/stb/tsmux/input%d", tuner_no);

		if (CFile::write(buf, source.c_str()) == -1)
		{
			eDebug("[CI] eDVBCIInterfaces setInputSource for input %s failed!", source.c_str());
			return 0;
		}

		eDebug("[CI] eDVBCIInterfaces setInputSource(%d, %s)", tuner_no, source.c_str());
	}
	return 0;
}

PyObject *eDVBCIInterfaces::getDescrambleRules(int slotid)
{
	eDVBCISlot *slot = getSlot(slotid);
	if (!slot)
	{
		char tmp[255];
		snprintf(tmp, 255, "eDVBCIInterfaces::getDescrambleRules try to get rules for CI Slot %d... but just %zd slots are available", slotid, m_slots.size());
		PyErr_SetString(PyExc_StandardError, tmp);
		return 0;
	}
	ePyObject tuple = PyTuple_New(3);
	int caids = slot->possible_caids.size();
	int services = slot->possible_services.size();
	int providers = slot->possible_providers.size();
	ePyObject caid_list = PyList_New(caids);
	ePyObject service_list = PyList_New(services);
	ePyObject provider_list = PyList_New(providers);
	caidSet::iterator caid_it(slot->possible_caids.begin());
	while(caids)
	{
		--caids;
		PyList_SET_ITEM(caid_list, caids, PyLong_FromLong(*caid_it));
		++caid_it;
	}
	serviceSet::iterator ref_it(slot->possible_services.begin());
	while(services)
	{
		--services;
		PyList_SET_ITEM(service_list, services, PyString_FromString(ref_it->toString().c_str()));
		++ref_it;
	}
	providerSet::iterator provider_it(slot->possible_providers.begin());
	while(providers)
	{
		ePyObject tuple = PyTuple_New(2);
		PyTuple_SET_ITEM(tuple, 0, PyString_FromString(provider_it->first.c_str()));
		PyTuple_SET_ITEM(tuple, 1, PyLong_FromUnsignedLong(provider_it->second));
		--providers;
		PyList_SET_ITEM(provider_list, providers, tuple);
		++provider_it;
	}
	PyTuple_SET_ITEM(tuple, 0, service_list);
	PyTuple_SET_ITEM(tuple, 1, provider_list);
	PyTuple_SET_ITEM(tuple, 2, caid_list);
	return tuple;
}

const char *PyObject_TypeStr(PyObject *o)
{
	return o->ob_type && o->ob_type->tp_name ? o->ob_type->tp_name : "unknown object type";
}

RESULT eDVBCIInterfaces::setDescrambleRules(int slotid, SWIG_PYOBJECT(ePyObject) obj )
{
	eDVBCISlot *slot = getSlot(slotid);
	if (!slot)
	{
		char tmp[255];
		snprintf(tmp, 255, "eDVBCIInterfaces::setDescrambleRules try to set rules for CI Slot %d... but just %zd slots are available", slotid, m_slots.size());
		PyErr_SetString(PyExc_StandardError, tmp);
		return -1;
	}
	if (!PyTuple_Check(obj))
	{
		char tmp[255];
		snprintf(tmp, 255, "2nd argument of setDescrambleRules is not a tuple.. it is a '%s'!!", PyObject_TypeStr(obj));
		PyErr_SetString(PyExc_StandardError, tmp);
		return -1;
	}
	if (PyTuple_Size(obj) != 3)
	{
		const char *errstr = "eDVBCIInterfaces::setDescrambleRules not enough entrys in argument tuple!!\n"
			"first argument should be a pythonlist with possible services\n"
			"second argument should be a pythonlist with possible providers/dvbnamespace tuples\n"
			"third argument should be a pythonlist with possible caids";
		PyErr_SetString(PyExc_StandardError, errstr);
		return -1;
	}
	ePyObject service_list = PyTuple_GET_ITEM(obj, 0);
	ePyObject provider_list = PyTuple_GET_ITEM(obj, 1);
	ePyObject caid_list = PyTuple_GET_ITEM(obj, 2);
	if (!PyList_Check(service_list) || !PyList_Check(provider_list) || !PyList_Check(caid_list))
	{
		char errstr[512];
		snprintf(errstr, 512, "eDVBCIInterfaces::setDescrambleRules incorrect data types in argument tuple!!\n"
			"first argument(%s) should be a pythonlist with possible services (reference strings)\n"
			"second argument(%s) should be a pythonlist with possible providers (providername strings)\n"
			"third argument(%s) should be a pythonlist with possible caids (ints)",
			PyObject_TypeStr(service_list), PyObject_TypeStr(provider_list), PyObject_TypeStr(caid_list));
		PyErr_SetString(PyExc_StandardError, errstr);
		return -1;
	}
	slot->possible_caids.clear();
	slot->possible_services.clear();
	slot->possible_providers.clear();
	int size = PyList_Size(service_list);
	while(size)
	{
		--size;
		ePyObject refstr = PyList_GET_ITEM(service_list, size);
		if (!PyString_Check(refstr))
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules entry in service list is not a string.. it is '%s'!!", PyObject_TypeStr(refstr));
			PyErr_SetString(PyExc_StandardError, buf);
			return -1;
		}
		char *tmpstr = PyString_AS_STRING(refstr);
		eServiceReference ref(tmpstr);
		if (ref.valid())
			slot->possible_services.insert(ref);
		else
			eDebug("[CI] eDVBCIInterfaces::setDescrambleRules '%s' is not a valid service reference... ignore!!", tmpstr);
	};
	size = PyList_Size(provider_list);
	while(size)
	{
		--size;
		ePyObject tuple = PyList_GET_ITEM(provider_list, size);
		if (!PyTuple_Check(tuple))
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules entry in provider list is not a tuple it is '%s'!!", PyObject_TypeStr(tuple));
			PyErr_SetString(PyExc_StandardError, buf);
			return -1;
		}
		if (PyTuple_Size(tuple) != 2)
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules provider tuple has %zd instead of 2 entries!!", PyTuple_Size(tuple));
			PyErr_SetString(PyExc_StandardError, buf);
			return -1;
		}
		if (!PyString_Check(PyTuple_GET_ITEM(tuple, 0)))
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules 1st entry in provider tuple is not a string it is '%s'", PyObject_TypeStr(PyTuple_GET_ITEM(tuple, 0)));
			PyErr_SetString(PyExc_StandardError, buf);
			return -1;
		}
		if (!PyLong_Check(PyTuple_GET_ITEM(tuple, 1)))
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules 2nd entry in provider tuple is not a long it is '%s'", PyObject_TypeStr(PyTuple_GET_ITEM(tuple, 1)));
			PyErr_SetString(PyExc_StandardError, buf);
			return -1;
		}
		char *tmpstr = PyString_AS_STRING(PyTuple_GET_ITEM(tuple, 0));
		uint32_t orbpos = PyLong_AsUnsignedLong(PyTuple_GET_ITEM(tuple, 1));
		if (strlen(tmpstr))
			slot->possible_providers.insert(std::pair<std::string, uint32_t>(tmpstr, orbpos));
		else
			eDebug("[CI] eDVBCIInterfaces::setDescrambleRules ignore invalid entry in provider tuple (string is empty)!!");
	};
	size = PyList_Size(caid_list);
	while(size)
	{
		--size;
		ePyObject caid = PyList_GET_ITEM(caid_list, size);
		if (!PyLong_Check(caid))
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules entry in caid list is not a long it is '%s'!!", PyObject_TypeStr(caid));
			PyErr_SetString(PyExc_StandardError, buf);
			return -1;
		}
		int tmpcaid = PyLong_AsLong(caid);
		if (tmpcaid > 0 && tmpcaid < 0x10000)
			slot->possible_caids.insert(tmpcaid);
		else
			eDebug("[CI] eDVBCIInterfaces::setDescrambleRules %d is not a valid caid... ignore!!", tmpcaid);
	};
	return 0;
}

PyObject *eDVBCIInterfaces::readCICaIds(int slotid)
{
	eDVBCISlot *slot = getSlot(slotid);
	if (!slot)
	{
		char tmp[255];
		snprintf(tmp, 255, "eDVBCIInterfaces::readCICaIds try to get CAIds for CI Slot %d... but just %zd slots are available", slotid, m_slots.size());
		PyErr_SetString(PyExc_StandardError, tmp);
	}
	else
	{
		int idx=0;
#if HAVE_HYPERCUBE_DISABLED
		int ca_manager = slot->getCAManager();
		const std::vector<uint16_t> *ci_caids = ca_manager ? &DVBCI_GetCAIDs() : 0;
#else
		eDVBCICAManagerSession *ca_manager = slot->getCAManager();
		const std::vector<uint16_t> *ci_caids = ca_manager ? &ca_manager->getCAIDs() : 0;
#endif
		ePyObject list = PyList_New(ci_caids ? ci_caids->size() : 0);
		if (ci_caids)
		{
			for (std::vector<uint16_t>::const_iterator it = ci_caids->begin(); it != ci_caids->end(); ++it)
				PyList_SET_ITEM(list, idx++, PyLong_FromLong(*it));
		}
		return list;
	}
	return 0;
}

int eDVBCIInterfaces::setCIClockRate(int slotid, int rate)
{
	eDVBCISlot *slot = getSlot(slotid);
	if (slot)
		return slot->setClockRate(rate);
	return -1;
}

int eDVBCISlot::send(const unsigned char *data, size_t len)
{
	int res=0;
	//int i;
	//eDebugNoNewLineStart("< ");
	//for(i=0;i<len;i++)
	//	eDebugNoNewLine("%02x ",data[i]);
	//eDebugNoNewLine("\n");
#if HAVE_HYPERCUBE_DISABLED
	return 0;
#else
	if (sendqueue.empty())
		res = ::write(fd, data, len);

	if (res < 0 || (unsigned int)res != len)
	{
		unsigned char *d = new unsigned char[len];
		memcpy(d, data, len);
		sendqueue.push( queueData(d, len) );
		notifier->setRequested(eSocketNotifier::Read | eSocketNotifier::Priority | eSocketNotifier::Write);
	}

	return res;
#endif
}
#if HAVE_HYPERCUBE_DISABLED
void eDVBCISlot::cdata(int/*Trid_CI_CardStatus_t*/ status)
{
	switch (status)
		{
	case _TRID_CARD_REMOVE_:
		eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_REMOVE_ set ui state to 0.");
		if(state != stateRemoved) {
			state = stateRemoved;
			eDebugCI("[CI] <eDVBCISlot data> state = stateRemoved");
			while(sendqueue.size())
			{
				delete [] sendqueue.top().data;
				sendqueue.pop();
			}
			application_manager = 0;
			ca_manager = 0;
			mmi_session = 0;
			eDVBCIInterfaces::getInstance()->ciRemoved(this);
			eDVBCI_UI::getInstance()->setState(getSlotID(),0);
		}
	  	break;
	case _TRID_CARD_INSERT_:
		eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_INSERT_  set ui state to 1.");			 
		if(state != stateInserted) {
			eDebug("[CI] ci inserted in slot %d", getSlotID());
			state = stateInserted;
			eDebugCI("[CI] <eDVBCISlot data> state == stateInserted  set ui state 1");
			eDVBCI_UI::getInstance()->setState(getSlotID(),1);
		}
		break;
	case _TRID_CARD_INVALID_CARD_:
		eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_INVALID_CARD_ <nothing>");			 
		break;
	case _TRID_CARD_MMI_READY_:
		eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_MMI_READY_  set ui state to 2.");			 
		{
			RETURN_TYPE ret;
			trid_uint8 menu_str_len;
			setAppManager(1);
			ret = Trid_CI_AppInfo_GetMenuStr(app_info,&menu_str_len);
			eDebugCI("[CI] <eDVBCISlot data> get app info name: %s.", app_info);
			app_info[menu_str_len] = 0;
			eDVBCI_UI::getInstance()->setAppName(getSlotID(), app_info);
			eDVBCI_UI::getInstance()->setState(getSlotID(), 2);
		}
		break;
	case _TRID_CARD_CA_READY_:
		eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_CA_READY_  eDVBCICAManagerSession ca info:");
		setCAManager(1);
		DVBCI_Packcaids();
		eDVBCIInterfaces::getInstance()->recheckPMTHandlers();
		break;
	case _TRID_CARD_MMI_CA_READY_:
		eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_MMI_CA_READY_ set mmi state to 1.");		
		DVBCI_Packcaids();
		eDVBCIInterfaces::getInstance()->recheckPMTHandlers();
		setCAManager(1);
		break;
	case _TRID_CARD_UPGRADE_START_:
		eDebugCI("[CI] <deDVBCISlot data> CardStatusChange: _TRID_CARD_UPGRADE_START_<nothing>");			 
		break;
	case _TRID_CARD_UPGRADE_FINISH_:
		eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_UPGRADE_FINISH_<nothing>");			 
		break;
	case _TRID_CARD_RESET_START_:
		eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_RESET_START_");		
		break;
	case _TRID_CARD_IO_ERROR_:
		eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_IO_ERROR_<nothing>");			 
		break;
		}
}

void eDVBCISlot::data(int/*Trid_CI_CardStatus_t*/ status)
{
	if (status & NOTIFY_CARD_STATUS)
	{
		if (CardStatus == 0)
		{
			eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_REMOVE_ set ui state to 0.\n");			   
			if(state != stateRemoved) 
			{
				state = stateRemoved;
				eDebugCI("[CI] <eDVBCISlot data> state = stateRemoved\n");
				while(sendqueue.size())
				{
					delete [] sendqueue.top().data;
					sendqueue.pop();
			  	}
			  	application_manager = 0;
			  	ca_manager = 0;
			  	mmi_session = 0;
			  	eDVBCIInterfaces::getInstance()->ciRemoved(this);
			  	eDVBCI_UI::getInstance()->setState(getSlotID(),0);
		  	}
		}
		else if (CardStatus == 1<<_TRID_CARD_IO_ERROR_)
		{
			eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_IO_ERROR_<nothing>");
		}
		else if (CardStatus == 1<<_TRID_CARD_INVALID_CARD_)
		{
			eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_INVALID_CARD_");
			if(state != stateInvalid) {
				eDebug("[CI] ci inserted in slot %d", getSlotID());
				state = stateInvalid;
				eDVBCI_UI::getInstance()->setState(getSlotID(),-1);
			}
		}
		else
		{
			if (CardStatus & (1<<_TRID_CARD_INSERT_))
			{
				eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_INSERT_  set ui state to 1.");			 
				if(state != stateInserted) 
				{
					eDebugCI("[CI] <eDVBCISlot data> state == stateInserted	set ui state 1");
					state = stateInserted;
					eDVBCI_UI::getInstance()->setState(getSlotID(),1);
				}
				CardStatus &= ~(1<<_TRID_CARD_INSERT_);
			}
			if (CardStatus & (1<<_TRID_CARD_RESET_START_))
			{
				eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_RESET_START_");		
				if(state != stateInserted) {
					state = stateInserted;
					eDVBCI_UI::getInstance()->setState(getSlotID(),1);
				}
				CardStatus &= ~(1<<_TRID_CARD_RESET_START_);
			}
			if (CardStatus & (1<<_TRID_CARD_MMI_READY_))
			{
				eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_MMI_READY_  set ui state to 2.");			 
				if(state != stateInserted) {
					eDebugCI("[CI] <eDVBCISlot data> state == stateInserted	set ui state 1");
					state = stateInserted;
					eDVBCI_UI::getInstance()->setState(getSlotID(),1);
				}
				{
					RETURN_TYPE ret;
					trid_uint8 menu_str_len;
					setAppManager(1);
					setMMIManager(1);
					ret = Trid_CI_AppInfo_GetMenuStr(app_info,&menu_str_len);
					eDebugCI("[CI] <eDVBCISlot data> get app info name: %s.", app_info);
					app_info[menu_str_len] = 0;
					eDVBCI_UI::getInstance()->setAppName(getSlotID(), app_info);
					eDVBCI_UI::getInstance()->setState(getSlotID(), 2);
				}
				CardStatus &= ~(1<<_TRID_CARD_MMI_READY_);
			}
			if (CardStatus & (1<<_TRID_CARD_CA_READY_))
			{
				eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_CA_READY_	eDVBCICAManagerSession ca info:");
				if(state != stateInserted) 
				{
					state = stateInserted;
					{
						RETURN_TYPE ret;
						trid_uint8 menu_str_len;
						setAppManager(1);
						ret = Trid_CI_AppInfo_GetMenuStr(app_info,&menu_str_len);
						app_info[menu_str_len] = 0;
						eDVBCI_UI::getInstance()->setAppName(getSlotID(), app_info);
						eDVBCI_UI::getInstance()->setState(getSlotID(), 2);
					}
				}
				DVBCI_Packcaids();
				eDVBCIInterfaces::getInstance()->recheckPMTHandlers();
				setCAManager(1);
				CardStatus &= ~(1<<_TRID_CARD_CA_READY_);
			}
			if (CardStatus & (1<<_TRID_CARD_MMI_CA_READY_))
			{
				eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_MMI_CA_READY_ set mmi state to 1."); 	
				if(state != stateInserted) 
				{
					state = stateInserted;
					{
						RETURN_TYPE ret;
						trid_uint8 menu_str_len;
						ret = Trid_CI_AppInfo_GetMenuStr(app_info,&menu_str_len);
						app_info[menu_str_len] = 0;
						eDVBCI_UI::getInstance()->setAppName(getSlotID(), app_info);
						eDVBCI_UI::getInstance()->setState(getSlotID(), 2);
					}
				}
				setAppManager(1);
				setMMIManager(1);
				DVBCI_Packcaids();
				setCAManager(1);
				eDVBCIInterfaces::getInstance()->recheckPMTHandlers();
				CardStatus &= ~(1<<_TRID_CARD_MMI_CA_READY_);
			}
			if (CardStatus & (1<<_TRID_CARD_UPGRADE_START_))
			{
				eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_UPGRADE_START_<nothing>");			 
				CardStatus &= ~(1<<_TRID_CARD_UPGRADE_START_);
			}
			if (CardStatus & (1<<_TRID_CARD_UPGRADE_FINISH_))
			{
				eDebugCI("[CI] <eDVBCISlot data> CardStatusChange: _TRID_CARD_UPGRADE_FINISH_<nothing>");			 
				CardStatus &= ~(1<<_TRID_CARD_UPGRADE_FINISH_);
			}
		}
		Tridci_cb_status &= ~NOTIFY_CARD_STATUS;
	}
	if (status & NOTIFY_MENU_DATA)
	{
		MenuDataNotifyCallbackProcess(&menu_data);
		Tridci_cb_status &= ~NOTIFY_MENU_DATA;
	}
	if (status & NOTIFY_LIST_DATA)
	{
		ListDataNotifyCallbackProcess(&list_data);
		Tridci_cb_status &= ~NOTIFY_LIST_DATA;
	}
	if (status & NOTIFY_ENQ_DATA)
	{
		EnqDataNotifyCallbackProcess(&enq_data);
		Tridci_cb_status &= ~NOTIFY_ENQ_DATA;
	}
	if (status & NOTIFY_CLOSE_MMI)
	{
		CloseMMINotifyCallbackProcess();
		Tridci_cb_status &= ~NOTIFY_CLOSE_MMI;
	}
	notifier->setRequested(eSocketNotifier::Read|eSocketNotifier::Priority);
	return 0;
}
#else
void eDVBCISlot::data(int what)
{
	eDebugCI("[CI] Slot %d what %d\n", getSlotID(), what);
	if(what == eSocketNotifier::Priority) {
		if(state != stateRemoved) {
			state = stateRemoved;
			while(sendqueue.size())
			{
				delete [] sendqueue.top().data;
				sendqueue.pop();
			}
			eDVBCISession::deleteSessions(this);
			eDVBCIInterfaces::getInstance()->ciRemoved(this);
			notifier->setRequested(eSocketNotifier::Read);
			eDVBCI_UI::getInstance()->setState(getSlotID(),0);
		}
		return;
	}

	if (state == stateInvalid)
		reset();

	if(state != stateInserted) {
		eDebug("[CI] ci inserted in slot %d", getSlotID());
		state = stateInserted;
		eDVBCI_UI::getInstance()->setState(getSlotID(),1);
		notifier->setRequested(eSocketNotifier::Read|eSocketNotifier::Priority);
		/* enable PRI to detect removal or errors */
	}

	if (what & eSocketNotifier::Read) {
		uint8_t data[4096];
		int r;
		r = ::read(fd, data, 4096);
		if(r > 0) {
//			int i;
//			eDebugNoNewLineStart("> ");
//			for(i=0;i<r;i++)
//				eDebugNoNewLine("%02x ",data[i]);
//			eDebugNoNewLine("\n");
			eDVBCISession::receiveData(this, data, r);
			eDVBCISession::pollAll();
			return;
		}
	}
	else if (what & eSocketNotifier::Write) {
		if (!sendqueue.empty()) {
			const queueData &qe = sendqueue.top();
			int res = ::write(fd, qe.data, qe.len);
			if (res >= 0 && (unsigned int)res == qe.len)
			{
				delete [] qe.data;
				sendqueue.pop();
			}
		}
		else
			notifier->setRequested(eSocketNotifier::Read|eSocketNotifier::Priority);
	}
}
#endif
DEFINE_REF(eDVBCISlot);

eDVBCISlot::eDVBCISlot(eMainloop *context, int nr)
{
	char filename[128];

	application_manager = 0;
	mmi_session = 0;
	ca_manager = 0;
	cc_manager = 0;
	use_count = 0;
	linked_next = 0;
	user_mapped = false;
	plugged = true;

	slotid = nr;
#if HAVE_HYPERCUBE_DISABLED
	state = stateInvalid;
#if data_callback

#else
	fd= 0x12345678;
	eDebugCI("[CI] CI Slot %d has fd %d", getSlotID(), fd);
	if (fd >= 0)
	{
		notifier = eSocketNotifier::create(context, fd, eSocketNotifier::Read | eSocketNotifier::Priority | eSocketNotifier::Write);
		CONNECT(notifier->activated, eDVBCISlot::data);
	}
#endif
#else
	sprintf(filename, "/dev/ci%d", nr);

//	possible_caids.insert(0x1702);
//	possible_providers.insert(providerPair("PREMIERE", 0xC00000));
//	possible_services.insert(eServiceReference("1:0:1:2A:4:85:C00000:0:0:0:"));

	fd = ::open(filename, O_RDWR | O_NONBLOCK | O_CLOEXEC);

	eDebugCI("[CI] Slot %d has fd %d", getSlotID(), fd);
	state = stateInvalid;

	if (fd >= 0)
	{
		notifier = eSocketNotifier::create(context, fd, eSocketNotifier::Read | eSocketNotifier::Priority | eSocketNotifier::Write);
		CONNECT(notifier->activated, eDVBCISlot::data);
	} else
	{
		perror(filename);
	}
#endif
}

eDVBCISlot::~eDVBCISlot()
{
#if HAVE_HYPERCUBE_DISABLED
	mmi_session = 0;
	application_manager = 0;
	ca_manager = 0;
#else
	eDVBCISession::deleteSessions(this);
#endif
}
#if HAVE_HYPERCUBE_DISABLED
void eDVBCISlot::setAppManager( int session )
{
	eDebugCI("[CI] eDVBCISlot::setAppManager. %d", session);
	application_manager=session;
}

void eDVBCISlot::setMMIManager( int session )
{
	eDebugCI("[CI] eDVBCISlot::setMMIManager. %d", session);
	mmi_session = session;
}

void eDVBCISlot::setCAManager( int session )
{
	eDebugCI("[CI] eDVBCISlot::setCAManager. %d ", session);
	ca_manager = session;
}
#else
void eDVBCISlot::setAppManager( eDVBCIApplicationManagerSession *session )
{
	application_manager=session;
}

void eDVBCISlot::setMMIManager( eDVBCIMMISession *session )
{
	mmi_session = session;
}

void eDVBCISlot::setCAManager( eDVBCICAManagerSession *session )
{
	ca_manager = session;
}

void eDVBCISlot::setCCManager( eDVBCICcSession *session )
{
	cc_manager = session;
}
#endif
int eDVBCISlot::getSlotID()
{
	return slotid;
}

int eDVBCISlot::getVersion()
{
	std::string civersion = eConfigManager::getConfigValue("config.cimisc.civersion");
	if ( civersion == "legacy" )
	{
		eDebug("[CI] getVersion : legacy detected");
		return versionCI;
	}
	else if ( civersion == "ciplus1" )
	{
		eDebug("[CI] getVersion : ciplus1 detected");
		return versionCIPlus1;
	}
	else if ( civersion == "ciplus2" )
	{
		eDebug("[CI] getVersion : ciplus2 detected");
		return versionCIPlus2;
	}
	else // auto
	{
		eDebug("[CI] getVersion : auto detected");

		char lv1Info[256] = { 0 };

		if (ioctl(fd, 1, lv1Info) < 0) {
			eDebug("[CI] ioctl not supported: assume CI+ version 1");
			return versionCIPlus1;
		}

		if (strlen(lv1Info) == 0) {
			eDebug("[CI] no LV1 info: assume CI+ version 1");
			return versionCIPlus1;
		}

		const char *str1 = "$compatible[";
		int len1 = strlen(str1);
		char *compatId = 0;

		for(unsigned int i=0;i<=(sizeof(lv1Info)-len1);i++) {
			if(strncasecmp(&lv1Info[i], str1, len1) == 0) {
				i += len1;
				for(unsigned int j=i;j<=(sizeof(lv1Info)-2);j++) {
					if(strncmp(&lv1Info[j], "]$", 2) == 0) {
						lv1Info[j] = '\0';
						compatId = &lv1Info[i];
						break;
					}
				}
			}
		}

		if(!compatId) {
			eDebug("[CI] CI CAM detected");
			return versionCI;
		}

		eDebug("[CI] CI+ compatibility ID: %s", compatId);

		char *label, *id, flag = '+';
		int version = versionCI;

		while((label = strsep(&compatId, " ")) != 0) {
			if (*label == '\0')
				continue;

			if(strncasecmp(label, "ciplus", 6) == 0) {
				id = strchr(label, '=');
				if(id) {
					*id++ = '\0';
					if(*id == '-' || *id == '+' || *id == '*')
						flag = *id++;

					version = strtol(id, 0, 0);
					eDebug("[CI] CI+ %c%d CAM detected", flag, version);
					break;
				}
			}
		}
		return version;
	}
}

int eDVBCISlot::reset()
{
#if HAVE_HYPERCUBE_DISABLED
	eDebugCI("[CI] doing is trid ci has reset interface?");
#else
	eDebug("[CI] Slot %d: reset requested", getSlotID());

	if (state == stateInvalid)
	{
		unsigned char buf[256];
		eDebug("[CI] flush");
		while(::read(fd, buf, 256)>0);
		state = stateResetted;
	}

	while(sendqueue.size())
	{
		delete [] sendqueue.top().data;
		sendqueue.pop();
	}

	ioctl(fd, 0);
#endif
	return 0;
}

int eDVBCISlot::startMMI()
{
	eDebug("[CI] Slot %d: startMMI()", getSlotID());
#if HAVE_HYPERCUBE_DISABLED
	if(application_manager)
		DVBCI_StartMMI();
#else
	if(application_manager)
		application_manager->startMMI();
#endif
	return 0;
}

int eDVBCISlot::stopMMI()
{
	eDebug("[CI] Slot %d: stopMMI()", getSlotID());
#if HAVE_HYPERCUBE_DISABLED
	if(mmi_session)
		DVBCI_StopMMI();
#else
	if(mmi_session)
		mmi_session->stopMMI();
#endif
	return 0;
}

int eDVBCISlot::answerText(int answer)
{
	eDebug("[CI] Slot %d: answerText(%d)", getSlotID(), answer);
#if HAVE_HYPERCUBE_DISABLED
	if(mmi_session)
		DVBCI_AnswerText(answer);
#else
	if(mmi_session)
		mmi_session->answerText(answer);
#endif
	return 0;
}

int eDVBCISlot::getMMIState()
{
	if(mmi_session)
		return 1;

	return 0;
}

int eDVBCISlot::answerEnq(char *value)
{
	eDebug("[CI] Slot %d: answerENQ(%s)", getSlotID(), value);
#if HAVE_HYPERCUBE_DISABLED
	if(mmi_session)
		DVBCI_AnswerEnq(value);
#else
	if(mmi_session)
		mmi_session->answerEnq(value);
#endif
	return 0;
}

int eDVBCISlot::cancelEnq()
{
	eDebug("[CI] Slot %d: cancelENQ", getSlotID());
#if HAVE_HYPERCUBE_DISABLED
	if(mmi_session)
		DVBCI_CancelEnq();
#else
	if(mmi_session)
		mmi_session->cancelEnq();
#endif
	return 0;
}
#if HAVE_HYPERCUBE_DISABLED
int PackDesc(unsigned char *pack, unsigned char *Desc)
{
	int len, desclen;
	len = ((Desc[0]&0xF)<<8) | (Desc[1]);
	eDebug("[CI] Desc len is %d.\n", len);
	if (len > 0)
	{
		desclen=len-1;
		memcpy(pack+2, Desc+3, desclen);
	}
	else
	{
		desclen = 0;
	}
	pack[0]=(desclen>>8) & 0xff;
	pack[1]=desclen & 0xff;
	return len+2;
}

int PackPmtDesc(unsigned char *pRaw, int wp, unsigned char *pack_data, int pmt_version)
{
	int iPackLen=0;
	int length=0;
	unsigned char *pPack;
	pack_data[0] = 0x02;
	pack_data[3] = pRaw[1];
	pack_data[4] = pRaw[2];
	pack_data[5] = (pmt_version<<1) | 0xC1;
	pack_data[6] = 0x00;
	pack_data[7] = 0x00;
	pack_data[8] = 0x00;
	pack_data[9] = 0x00;
	iPackLen=10;
	pPack = pack_data+10;
	pRaw += 4;
	wp -= 4;
	eDebug("[CI] still %d for parse.", wp);
	length = PackDesc(pPack, pRaw);
	wp -= length;
	pRaw += length;
	length = (((pPack[0]&0xF)<<8) | pPack[1])+2;
	pPack += length;
	iPackLen += length;
	while (wp > 0)
	{
		pPack[0] = pRaw[0];
		pPack[1] = pRaw[1];
		pPack[2] = pRaw[2];
		wp-=3;
		pRaw+=3;
		pPack+=3;
		iPackLen+=3;
		length = PackDesc(pPack, pRaw);
		wp -= length;
		pRaw += length;
		length = (((pPack[0]&0xF)<<8) | pPack[1])+2;
		pPack += length;
		iPackLen += length;
	}
	iPackLen+=4;
	pack_data[1] = 0xB0 | (((iPackLen-3)>>8)&0x0F);
	pack_data[2] = (iPackLen-3)&0xFF;
	return iPackLen;
}
#endif
#if HAVE_HYPERCUBE_DISABLED
int eDVBCISlot::sendCAPMT(eDVBServicePMTHandler *pmthandler, const std::vector<uint16_t> &ids)
{
	if (!ca_manager)
	{
		eDebugCI("[CI] eDVBCISlot sendCAPMT no ca_manager (no CI plugged?). then return with nothing done.\n");
		return -1;
	}
	const std::vector<uint16_t> &caids = ids.empty() ? DVBCI_GetCAIDs() : ids;
	ePtr<eTable<ProgramMapSection> > ptr;
	if (pmthandler->getPMT(ptr))
	{
		eDebug("[CI] eDVBCISlot::sendCAPMT---->get pmt from pmthandler fail.\n");
		return -1;
	}
	else
	{
		eDVBTableSpec table_spec;
		ptr->getSpec(table_spec);
		int pmt_version = table_spec.version & 0x1F;
		eServiceReferenceDVB ref;
		pmthandler->getServiceReference(ref);
		uint16_t program_number = ref.getServiceID().get();
		std::map<uint16_t, uint8_t>::iterator it = running_services.find(program_number);
		bool sendEmpty = caids.size() == 1 && caids[0] == 0xFFFF;
		if (it != running_services.end() && (pmt_version == it->second) && !sendEmpty)
		{
			eDebug("[CI] eDVBCISlot::sendCAPMT---->don't send self capmt version twice");
			return -1;
		}
		std::vector<ProgramMapSection*>::const_iterator i=ptr->getSections().begin();
		if (i == ptr->getSections().end())
		{
			eDebug("[CI] ProgramMapSection maybe none.\n");
			return -1;
		}
		else
		{
		unsigned char pack_data[4096];
		unsigned int total=0;
		if (sendEmpty)
		{
			eDebug("[CI] SEND EMPTY CAPMT.. old version is");
		}
		else
		{
			eDebug("[CI] SEND CAPMT.. pmt version is 0x%x.", pmt_version);
		}
		if (!sendEmpty)
		{
				ProgramMapSection*pmt;
				unsigned char *buffer;
				unsigned int sectionlen;
				unsigned int programInfoLength;
				unsigned int esInfoLength=0;
				Descriptor *info;
				ElementaryStreamInfo *esinfo;
				unsigned int crc32;
				buffer = pack_data;
				pmt=*i;
				sectionlen = pmt->getSectionLength();
				total = 0;
				buffer[total++] = TID_PMT;
				buffer[total++] = (pmt->getSectionSyntaxIndicator()<<8) | ((sectionlen&0x0F00)>>8);
				buffer[total++] = (sectionlen&0xFF);
				buffer[total++] = (pmt->getTableIdExtension()>>8)& 0xff;
				buffer[total++] = pmt->getTableIdExtension() & 0xff;
				buffer[total++] = (pmt->getVersionNumber() << 1) | pmt->getCurrentNextIndicator();
				buffer[total++] = pmt->getSectionNumber();
				buffer[total++] = pmt->getLastSectionNumber();
				buffer[total++] = (pmt->getPcrPid()>>8)&0x1F;
				buffer[total++] = pmt->getPcrPid()&0xFF;
				eDebug("[CI] start to package program info total(%d) sectionlen is %d.", total, sectionlen);
				programInfoLength = 0;
				for (DescriptorConstIterator j = pmt->getDescriptors()->begin(); j != pmt->getDescriptors()->end(); ++j)
				{
					info = *j;
					eDebug("[CI] package descriptor .", programInfoLength);
					programInfoLength+=info->writeToBuffer(buffer+total+2+programInfoLength);
				}
			eDebug("[CI] programInfoLength is %d.total(%d).", programInfoLength, total);
			buffer[total++] = (programInfoLength>>8)&0xff;
			buffer[total++] = programInfoLength&0xff;
			total+=programInfoLength;
			for (ElementaryStreamInfoConstIterator e = pmt->getEsInfo()->begin(); e != pmt->getEsInfo()->end(); ++e) {
				esinfo = *e;
				buffer[total++] = esinfo->getType();
				buffer[total++] = (esinfo->getPid()>>8)&0x1F;
				buffer[total++] = esinfo->getPid()&0xFF;
				esInfoLength = 0;
				for (DescriptorConstIterator k = esinfo->getDescriptors()->begin(); k != esinfo->getDescriptors()->end(); ++k)
				{
					info = *k;
					esInfoLength+=info->writeToBuffer(buffer+total+2+esInfoLength);
				}
				eDebug("[CI] esInfoLength is %d.total(%d).", esInfoLength, total);
				buffer[total++] = (esInfoLength>>8)&0xff;
				buffer[total++] = esInfoLength&0xff;
				total+=esInfoLength;
			}
			eDebug("[CI] esInfoLength is %d.total(%d).", esInfoLength, total);
			crc32 = pmt->getCrc32();
			buffer[total++] = (crc32>>24)&0xFF;
			buffer[total++] = (crc32>>16)&0xFF;
			buffer[total++] = (crc32>>8)&0xFF;
			buffer[total++] = (crc32>>0)&0xFF;
			eDebug("[CI] crc is %x.", crc32);
		}
		else
		{
			unsigned char raw_data[1024];
			CaProgramMapSection capmt(*i++,
			it != running_services.end() ? 0x05/*update*/ : running_services.empty() ? 0x03 /*only*/ : 0x04 /*add*/, 0x01, caids);
			while (i != ptr->getSections().end())
			{
				capmt.append(*i++);
			}
			capmt.writeToBuffer(raw_data);
			int wp=0;
			int hlen;
			if (raw_data[3] & 0x80)
			{
				int i=0;
				int lenbytes = raw_data[3] & ~0x80;
				while(i < lenbytes)
				wp = (wp << 8) | raw_data[4 + i++];
				wp+=4;
				wp+=lenbytes;
				hlen = 4 + lenbytes;
			}
			else
			{
				wp = raw_data[3];
				wp+=4;
				hlen = 4;
			}
			if (sendEmpty)
			{
				eDebugNoNewLine("[CI] SEND EMPTY CAPMT.. old version is %02x", raw_data[hlen+3]);
				if (sendEmpty && running_services.size() == 1)
					raw_data[hlen] = 0x03;
				raw_data[hlen+3] &= ~0x3E;
				raw_data[hlen+3] |= ((pmt_version+1) & 0x1F) << 1;
				eDebug(" new version is %02x", raw_data[hlen+3]);
			}
			eDebug("[CI] ca_manager %p dump capmt:%d.head length %d.", ca_manager, wp, hlen);
			for(int i=0;i<wp;i++)
				eDebugNoNewLine("%02x, ", raw_data[i]);
			eDebug("");
			{
				int ipack, iraw;
				unsigned char *pPack, *pRaw;
				pRaw = raw_data+hlen;
				wp -= hlen;
				total = PackPmtDesc(pRaw, wp, pack_data, pmt_version);
			}
		}
		{
			ePtr<eDVBService> service;
			pmthandler->getService(service);
			videoPid = service->getCacheEntry(eDVBService::cVPID);
			audioPid = service->getCacheEntry(eDVBService::cAPID);
			eDebug("[CI] current video pid: 0x%x. audio pid: 0x%x.\n", videoPid, audioPid);
		}
		eDebug("[CI] total is %d", total);
		for (int f=0;f<total;f++)
		{
			eDebugNoNewLine("%02x ", pack_data[f]);
			if ((f+1)%20==0)
			{
				eDebug("");
			}
		}
		eDebug("");
		{
			eDebug("[CI] DVBCI_SendCAPMT(pack_data, total);");
			DVBCI_SendCAPMT(pack_data, total);
		}
		running_services[program_number] = pmt_version;
		}
	}
	return 0;
}
#else
int eDVBCISlot::sendCAPMT(eDVBServicePMTHandler *pmthandler, const std::vector<uint16_t> &ids)
{
	if (!ca_manager)
	{
		eDebug("[CI] no ca_manager (no CI plugged?)");
		return -1;
	}
	const std::vector<uint16_t> &caids = ids.empty() ? ca_manager->getCAIDs() : ids;
	ePtr<eTable<ProgramMapSection> > ptr;
	if (pmthandler->getPMT(ptr))
		return -1;
	else
	{
		eDVBTableSpec table_spec;
		ptr->getSpec(table_spec);
		int pmt_version = table_spec.version & 0x1F; // just 5 bits

		eServiceReferenceDVB ref;
		pmthandler->getServiceReference(ref);
		uint16_t program_number = ref.getServiceID().get();
		std::map<uint16_t, uint8_t>::iterator it =
			running_services.find(program_number);
		bool sendEmpty = caids.size() == 1 && caids[0] == 0xFFFF;

		if ( it != running_services.end() &&
			(pmt_version == it->second) &&
			!sendEmpty )
		{
			eDebug("[CI] [eDVBCISlot] dont send self capmt version twice");
			return -1;
		}

		std::vector<ProgramMapSection*>::const_iterator i=ptr->getSections().begin();
		if ( i == ptr->getSections().end() )
			return -1;
		else
		{
			unsigned char raw_data[2048];

//			eDebug("[CI] send %s capmt for service %04x to slot %d",
//				it != running_services.end() ? "UPDATE" : running_services.empty() ? "ONLY" : "ADD",
//				program_number, slotid);

			CaProgramMapSection capmt(*i++,
				it != running_services.end() ? 0x05 /*update*/ : running_services.empty() ? 0x03 /*only*/ : 0x04 /*add*/, 0x01, caids );
			while( i != ptr->getSections().end() )
			{
//				eDebug("[CI] append");
				capmt.append(*i++);
			}
			capmt.writeToBuffer(raw_data);

// begin calc capmt length
			int wp=0;
			int hlen;
			if ( raw_data[3] & 0x80 )
			{
				int i=0;
				int lenbytes = raw_data[3] & ~0x80;
				while(i < lenbytes)
					wp = (wp << 8) | raw_data[4 + i++];
				wp+=4;
				wp+=lenbytes;
				hlen = 4 + lenbytes;
			}
			else
			{
				wp = raw_data[3];
				wp+=4;
				hlen = 4;
			}
// end calc capmt length

			if (sendEmpty)
			{
//				eDebugNoNewLineStart("[CI[ SEND EMPTY CAPMT.. old version is %02x", raw_data[hlen+3]);
				if (sendEmpty && running_services.size() == 1)  // check if this is the capmt for the last running service
					raw_data[hlen] = 0x03; // send only instead of update... because of strange effects with alphacrypt
				raw_data[hlen+3] &= ~0x3E;
				raw_data[hlen+3] |= ((pmt_version+1) & 0x1F) << 1;
//				eDebugNoNewLine(" new version is %02x\n", raw_data[hlen+3]);
			}

//			eDebugNoNewLineStart("[CI[ ca_manager %p dump capmt:", ca_manager);
//			for(int i=0;i<wp;i++)
//				eDebugNoNewLine("%02x ", raw_data[i]);
//			eDebugNoNewLine("\n");

			//dont need tag and lenfield
			ca_manager->sendCAPMT(raw_data + hlen, wp - hlen);
			running_services[program_number] = pmt_version;

			std::vector<uint16_t> pids;
			int prg_info_len = ((raw_data[hlen + 4] << 8) | raw_data[hlen + 5]) & 0xfff;
			int es_info_len = 0;
			for (int jj = hlen + prg_info_len + 6; jj < wp; jj += es_info_len + 5)
			{
				uint16_t es_pid = ((raw_data[jj + 1] << 8) | raw_data[jj + 2]) & 0x1fff;
				pids.push_back( es_pid );
				es_info_len = ((raw_data[jj + 3] << 8) | raw_data[jj + 4]) & 0xfff;
			}

#if 0
			uint16_t device_ids = 0;
			ePtr<iDVBDemux> demux;
			if (!pmthandler->getDataDemux(demux))
			{
				uint8_t demux_id = 0;
				uint8_t adapter_id = 0;
				demux->getCADemuxID(demux_id);
				demux->getCAAdapterID(adapter_id);
				device_ids = (adapter_id << 8) | demux_id;
			}
#endif

			if (cc_manager)
			{
				if (!sendEmpty)
					cc_manager->addProgram(program_number, pids);
				else
					cc_manager->removeProgram(program_number, pids);
			}
		}
	}
	return 0;
}
#endif
void eDVBCISlot::removeService(uint16_t program_number)
{
	if (program_number == 0xFFFF)
		running_services.clear();  // remove all
	else
		running_services.erase(program_number);  // remove single service
}

int eDVBCISlot::setSource(const std::string &source)
{
	char buf[64];
	current_source = source;
	snprintf(buf, sizeof(buf), "/proc/stb/tsmux/ci%d_input", slotid);

	if(CFile::write(buf, source.c_str()) == -1)
	{
		eDebug("[CI] Slot: %d setSource: %s failed!", getSlotID(), source.c_str());
		return 0;
	}

	eDebug("[CI] Slot: %d setSource: %s", getSlotID(), source.c_str());
	return 0;
}

int eDVBCISlot::setClockRate(int rate)
{
	char buf[64];
	snprintf(buf, sizeof(buf), "/proc/stb/tsmux/ci%d_tsclk", slotid);
	if(CFile::write(buf, rate ? "high" : "normal") == -1)
		return -1;
	return 0;
}

#if HAVE_HYPERCUBE_DISABLED
trid_sint32 eDVBCISlot::MenuDataNotifyCallbackProcess(Trid_T_Menu* menu)
{
	unsigned char tag[3] = {0x9f, 0x88, 0x09};
	eDVBCISlot *slot;
	if (getMMIManager())
	{
		setMMIManager(1);
	}
	eDVBCI_UI::getInstance()->processMMIData(0, tag, (const void *)menu, 0);
	return 0;
}

trid_sint32 eDVBCISlot::ListDataNotifyCallbackProcess(Trid_T_List* list)
{
	unsigned char tag[3] = {0x9f, 0x88, 0x0c};
	if (!getMMIManager())
	{
		setMMIManager(1);
	}
	eDVBCI_UI::getInstance()->processMMIData(/*slot->getSlotID()*/0, tag, (const void *)list, 0);
	return 0;
}

trid_sint32 eDVBCISlot::EnqDataNotifyCallbackProcess(Trid_T_Enq* enq)
{
	unsigned char tag[3] = {0x9f, 0x88, 0x07};
	if (!getMMIManager())
	{
		setMMIManager(1);
	}
	eDVBCI_UI::getInstance()->processMMIData(0, tag, (const void *)enq, 0);
	return 0;
}

trid_sint32 eDVBCISlot::CloseMMINotifyCallbackProcess()
{
	unsigned char tag[3] = {0x9f, 0x88, 0x00};
	unsigned char data[1] = {1};
	eDVBCI_UI::getInstance()->processMMIData(/*slot->getSlotID()*/0, tag, data, 1);
	return 0;
}
#endif

eAutoInitP0<eDVBCIInterfaces> init_eDVBCIInterfaces(eAutoInitNumbers::dvb, "CI Slots");
