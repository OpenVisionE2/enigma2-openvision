/* DVB CI Host Language and Country Manager */

#include <lib/base/eerror.h>
#include <lib/base/nconfig.h>
#include <lib/dvb_ci/dvbci_hlcmgr.h>

int eDVBCIHostLanguageAndCountrySession::receivedAPDU(const unsigned char *tag,const void *data, int len)
{
	int ret = 0;

	eDebugNoNewLine("SESSION(%d)/HLC %02x %02x %02x: ", session_nb, tag[0], tag[1], tag[2]);
	for (int i=0; i<len; i++)
		eDebugNoNewLine("%02x ", ((const unsigned char*)data)[i]);
	eDebug(" ");
	if ((tag[0]==0x9f) && (tag[1]==0x81))
	{
		switch (tag[2])
		{
		case 0x00:  // country enquiry
			eDebug("Host country enquiry:");
			state=stateCountryEnquiry;
			ret = 1;
			break;
		case 0x10:  // language enquiry
			eDebug("Host language enquiry:");
			state=stateLanguageEnquiry;
			ret = 1;
			break;
		default:
			eDebug("unknown APDU tag 9F 80 %02x", tag[2]);
			state = stateFinal;
			break;
		}
	}

	return ret;
}

std::map<std::string, std::string> eDVBCIHostLanguageAndCountrySession::createLanguageMap()
{
	std::map<std::string, std::string> m;
	m["ar_AE"] = "ara";
	m["bg_BG"] = "bul";
	m["ca_AD"] = "cat";
	m["cs_CZ"] = "ces";
	m["da_DK"] = "dan";
	m["de_DE"] = "deu";
	m["el_GR"] = "ell";
	m["en_GB"] = "eng";
	m["en_US"] = "eng";
	m["es_ES"] = "spa";
	m["et_EE"] = "est";
	m["fa_IR"] = "fas";
	m["fi_FI"] = "fin";
	m["fr_FR"] = "fra";
	m["fy_NL"] = "fry";
	m["he_IL"] = "heb";
	m["hr_HR"] = "hrv";
	m["hu_HU"] = "hun";
	m["is_IS"] = "isl";
	m["it_IT"] = "ita";
	m["lt_LT"] = "lit";
	m["lv_LV"] = "lav";
	m["nb_NO"] = "nob";
	m["nl_NL"] = "nld";
	m["no_NO"] = "nor";
	m["pl_PL"] = "pol";
	m["pt_BR"] = "por";
	m["pt_PT"] = "por";
	m["ro_RO"] = "ron";
	m["ru_RU"] = "rus";
	m["sk_SK"] = "slk";
	m["sl_SI"] = "slv";
	m["sr_YU"] = "srp";
	m["sv_SE"] = "swe";
	m["th_TH"] = "tha";
	m["tr_TR"] = "tur";
	m["uk_UA"] = "ukr";
	return m;
}

const std::map<std::string, std::string> eDVBCIHostLanguageAndCountrySession::m_languageMap = eDVBCIHostLanguageAndCountrySession::createLanguageMap();

int eDVBCIHostLanguageAndCountrySession::doAction()
{
	switch (state)
	{
	case stateCountryEnquiry:
	{
		const unsigned char tag[] = {0x9F, 0x81, 0x01};
		sendAPDU(tag, "DEU", 3); // XXX
		break;
	}
	case stateLanguageEnquiry:
	{
		const unsigned char tag[] = {0x9F, 0x81, 0x11};
		std::string language = eConfigManager::getConfigValue("config.osd.language");
		std::map<std::string, std::string>::const_iterator it = m_languageMap.find(language);
		if (it != m_languageMap.end())
			sendAPDU(tag, it->second.c_str(), 3);
		else
			sendAPDU(tag, "eng", 3);
		break;
	}
	default:
		eDebug("unknown state");
		break;
	}

	return 0;
}

