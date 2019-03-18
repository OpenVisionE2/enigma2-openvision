#ifndef __RES_CONTENT_CTRL_H
#define __RES_CONTENT_CTRL_H

#include <vector>

#include <openssl/x509.h>
#include <openssl/rsa.h>

class eDVBCICcSession;

class eDVBCICcSessionImpl
{
	eDVBCICcSession *session;
	int slot_index;
	int version;

	int desc_fd;

	// CI+ credentials
	enum {
		BRAND_ID = 1,

		HOST_ID = 5,
		CICAM_ID = 6,
		HOST_BRAND_CERT = 7,
		CICAM_BRAND_CERT = 8,

		KP = 12,
		DHPH = 13,
		DHPM = 14,
		HOST_DEV_CERT = 15,
		CICAM_DEV_CERT = 16,
		SIGNATURE_A = 17,
		SIGNATURE_B = 18,
		AUTH_NONCE = 19,
		NS_HOST = 20,
		NS_MODULE = 21,
		AKH = 22,
		AKM = 23,

		URI_MESSAGE = 25,
		PROGRAM_NUMBER = 26,
		URI_CONFIRM = 27,
		KEY_REGISTER = 28,
		URI_VERSIONS = 29,
		STATUS_FIELD = 30,
		SRM_DATA = 31,
		SRM_CONFIRM = 32,

		MAX_ELEMENTS = 33
	};

	struct element {
		uint8_t *data;
		uint32_t size;
		bool valid;
	} elements[MAX_ELEMENTS];

	/* DHSK */
	uint8_t dhsk[256];

	/* KS_host */
	uint8_t ks_host[32];

	/* derived keys */
	uint8_t sek[16];
	uint8_t sak[16];

	/* AKH checks - module performs 5 tries to get correct AKH */
	unsigned int akh_index;

	/* Root CA */
	X509_STORE *store;

	/* Host certificates */
	X509 *cust_cert;
	X509 *device_cert;

	/* Module certificates */
	X509 *ci_cust_cert;
	X509 *ci_device_cert;

	/* private key of device-cert */
	RSA *rsa_device_key;

	/* DH parameters */
	DH *dh;

	static const uint32_t datatype_sizes[MAX_ELEMENTS];

	struct element *element_get(unsigned int id);
	void element_invalidate(unsigned int id);
	void element_init();
	bool element_set(unsigned int id, const uint8_t *data, uint32_t size);
	bool element_set_certificate(unsigned int id, X509 *cert);
	bool element_set_hostid_from_certificate(unsigned int id, X509 *cert);
	bool element_valid(unsigned int id);
	unsigned int element_get_buf(uint8_t *dest, unsigned int id);
	unsigned int element_get_req(uint8_t *dest, unsigned int id);
	uint8_t *element_get_ptr(unsigned int id);

	void generate_key_seed();
	void generate_ns_host();
	int generate_SAK_SEK();
	X509 *import_ci_certificates(unsigned int id);
	int check_ci_certificates();
	int generate_akh();
	bool check_dh_challenge();
	int compute_dh_key();
	int generate_dh_key();
	int generate_sign_A();
	int restart_dh_challenge();
	int generate_uri_confirm();
	void check_new_key();

	bool sac_check_auth(const uint8_t *data, unsigned int len);
	int sac_gen_auth(uint8_t *out, uint8_t *in, unsigned int len);
	int sac_crypt(uint8_t *dst, const uint8_t *src, unsigned int len, int encrypt);

	int data_req_handle_new(unsigned int id);
	int data_get_handle_new(unsigned int id);

	int data_req_loop(uint8_t *dest, unsigned int dest_len, const uint8_t *data, unsigned int data_len, unsigned int items);
	int data_get_loop(const uint8_t *data, unsigned int datalen, unsigned int items);

	void cc_open_req();
	void cc_data_req(const uint8_t *data, unsigned int len);
	void cc_sync_req(const uint8_t *data, unsigned int len);

	void cc_sac_send(const uint8_t *tag, uint8_t *data, unsigned int pos);
	void cc_sac_data_req(const uint8_t *data, unsigned int len);
	void cc_sac_sync_req(const uint8_t *data, unsigned int len);

public:
	eDVBCICcSessionImpl(eDVBCICcSession *session_, int slot_index_, int version_);
	~eDVBCICcSessionImpl();

	int receiveAPDU(const unsigned char *tag, const void *data, int len);
	int addProgram(uint16_t program_number, std::vector<uint16_t>& pids);
	int removeProgram(uint16_t program_number, std::vector<uint16_t>& pids);
};

#endif
