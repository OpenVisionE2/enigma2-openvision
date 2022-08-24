#ifndef __lib_base_modelinformation_h
#define __lib_base_modelinformation_h

#include <map>
#include <string>

class eModelInformation
{
	public:
		eModelInformation();
		static eModelInformation& getInstance() { static eModelInformation m_instance; return m_instance; }
		std::string getValue(const std::string &key);
		std::string BoxType() { return getValue("model"); }
		std::string MachineBrand() { return getValue("brand"); }
		std::string Date() { return getValue("date"); }
		std::string Creator() { return getValue("creator"); }
		std::string Url() { return getValue("url"); }
	private:
		std::map<std::string,std::string> m_modelinformation;
};

#endif
