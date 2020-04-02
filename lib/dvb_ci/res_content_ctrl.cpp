#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <time.h>

#include <openssl/pem.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>
#include <openssl/sha.h>
#include <openssl/aes.h>
#include <openssl/evp.h>

#include <lib/base/eerror.h>
#include <lib/dvb_ci/dvbci_ccmgr.h>
#include <lib/dvb_ci/res_content_ctrl.h>
#include <lib/dvb_ci/descrambler.h>
#include <lib/dvb_ci/aes_xcbc_mac.h>

// based on dream_ciplus_helper

namespace {
	#include <lib/dvb_ci/_dh_params.h>

	// misc helper functions

	/*
	void hexdump(const uint8_t *data, unsigned int len)
	{
		while (len--)
			eDebugNoNewLine("%02x ", *data++);
		eDebugNoNewLineEnd(" ");
	}
	*/

	int get_random(uint8_t *dest, int len)
	{
		int fd;
		const char *urnd = "/dev/urandom";

		fd = open(urnd, O_RDONLY);
		if (fd <= 0) {
			eWarning("[res_content_ctrl] cannot open %s", urnd);
			return -1;
		}

		if (read(fd, dest, len) != len) {
			eWarning("[res_content_ctrl] cannot read from %s", urnd);
			close(fd);
			return -2;
		}

		close(fd);

		return len;
	}

	int add_padding(uint8_t *dest, unsigned int len, unsigned int blocklen)
	{
		uint8_t padding = 0x80;
		int count = 0;

		while (len & (blocklen - 1)) {
			*dest++ = padding;
			++len;
			++count;
			padding = 0;
		}

		return count;
	}

	int get_bin_from_nibble(int in)
	{
		if ((in >= '0') && (in <= '9'))
			return in - 0x30;

		if ((in >= 'A') && (in <= 'Z'))
			return in - 0x41 + 10;

		if ((in >= 'a') && (in <= 'z'))
			return in - 0x61 + 10;

		eWarning("[res_content_ctrl] unsupported chars in device id");

		return 0;
	}

	void str2bin(uint8_t *dst, char *data, int len)
	{
		int i;

		for (i = 0; i < len; i += 2)
			*dst++ = (get_bin_from_nibble(data[i]) << 4) | get_bin_from_nibble(data[i + 1]);
	}

	uint32_t UINT32(const uint8_t *in, unsigned int len)
	{
		uint32_t val = 0;
		unsigned int i;

		for (i = 0; i < len; i++) {
			val <<= 8;
			val |= *in++;
		}

		return val;
	}

	int BYTE32(uint8_t *dest, uint32_t val)
	{
		*dest++ = val >> 24;
		*dest++ = val >> 16;
		*dest++ = val >> 8;
		*dest++ = val;

		return 4;
	}

	int BYTE16(uint8_t *dest, uint16_t val)
	{
		*dest++ = val >> 8;
		*dest++ = val;
		return 2;
	}

	// storage & load of authenticated data (HostID & DHSK & AKH)

#ifndef FILENAME_MAX
#define FILENAME_MAX 256
#endif
#define MAX_PAIRS 10
#define PAIR_SIZE (8 + 256 + 32)

	void get_authdata_filename(char *dest, size_t len, unsigned int slot)
	{
		snprintf(dest, len, "/etc/enigma2/ci_auth_slot_%u.bin", slot);
	}

	bool get_authdata(uint8_t *host_id, uint8_t *dhsk, uint8_t *akh, unsigned int slot, unsigned int index)
	{
		char filename[FILENAME_MAX];
		int fd;
		uint8_t chunk[PAIR_SIZE];
		unsigned int i;

		if (index >= MAX_PAIRS)
			return false;

		get_authdata_filename(filename, sizeof(filename), slot);

		fd = open(filename, O_RDONLY);
		if (fd <= 0) {
			eDebug("[res_content_ctrl] can not open %s", filename);
			return false;
		}

		for (i = 0; i <= index; i++) {
			if (read(fd, chunk, sizeof(chunk)) != sizeof(chunk)) {
				eDebug("[res_content_ctrl] can not read auth_data");
				close(fd);
				return false;
			}
		}

		close(fd);

		memcpy(host_id, chunk, 8);
		memcpy(dhsk, &chunk[8], 256);
		memcpy(akh, &chunk[8 + 256], 32);

		return true;
	}

	bool write_authdata(unsigned int slot, const uint8_t *host_id, const uint8_t *dhsk, const uint8_t *akh)
	{
		char filename[FILENAME_MAX];
		int fd;
		uint8_t buf[PAIR_SIZE * MAX_PAIRS];
		int entries;

		for (entries = 0; entries < MAX_PAIRS; entries++) {
			int offset = PAIR_SIZE * entries;
			if (!get_authdata(&buf[offset], &buf[offset + 8], &buf[offset + 8 + 256], slot, entries))
				break;

			/* check if we got this pair already */
			if (!memcmp(&buf[offset + 8 + 256], akh, 32)) {
				eDebug("[res_content_ctrl] data already stored");
				return true;
			}
		}

		if (entries > 0) {
			if (entries == MAX_PAIRS)
				entries--;

			memmove(buf + PAIR_SIZE, buf, PAIR_SIZE * entries);
		}

		memcpy(buf, host_id, 8);
		memcpy(buf + 8, dhsk, 256);
		memcpy(buf + 8 + 256, akh, 32);
		entries++;

		eDebug("[res_content_ctrl] %d entries for writing", entries);

		get_authdata_filename(filename, sizeof(filename), slot);
		fd = open(filename, O_CREAT | O_WRONLY | O_TRUNC, S_IRUSR | S_IWUSR);
		if (fd < 0) {
			eWarning("[res_content_ctrl] can not open %s", filename);
			return false;
		}

		if (write(fd, buf, PAIR_SIZE * entries) != PAIR_SIZE * entries)
			eWarning("[res_content_ctrl] error in write");

		close(fd);

		return true;
	}

	// CI+ certificates

	RSA *rsa_privatekey_open(const char *filename)
	{
		FILE *fp;
		RSA *r = NULL;

		fp = fopen(filename, "r");
		if (!fp) {
			eWarning("[res_content_ctrl] can not open %s", filename);
			return NULL;
		}

		PEM_read_RSAPrivateKey(fp, &r, NULL, NULL);
		if (!r)
			eWarning("[res_content_ctrl] can not read %s", filename);

		fclose(fp);

		return r;
	}

	X509 *certificate_open(const char *filename)
	{
		FILE *fp;
		X509 *cert;

		fp = fopen(filename, "r");
		if (!fp) {
			eWarning("[res_content_ctrl] can not open %s", filename);
			return NULL;
		}

		cert = PEM_read_X509(fp, NULL, NULL, NULL);
		if (!cert)
			eWarning("[res_content_ctrl] can not read %s", filename);

		fclose(fp);

		return cert;
	}

	int verify_cb(int ok, X509_STORE_CTX *ctx)
	{
		if (X509_STORE_CTX_get_error(ctx) == X509_V_ERR_CERT_NOT_YET_VALID) {
			time_t now = time(NULL);
			struct tm *t = localtime(&now);
			if (t->tm_year < 2015) {
				eDebug("[res_content_ctrl] seems our system clock is wrong - ignore!");
				return 1;
			}
		}

		if (X509_STORE_CTX_get_error(ctx) == X509_V_ERR_CERT_HAS_EXPIRED)
			return 1;

		return 0;
	}

	bool certificate_validate(X509_STORE *store, X509 *cert)
	{
		X509_STORE_CTX *store_ctx;
		int ret;

		store_ctx = X509_STORE_CTX_new();

		X509_STORE_CTX_init(store_ctx, store, cert, NULL);
		X509_STORE_CTX_set_verify_cb(store_ctx, verify_cb);
		X509_STORE_CTX_set_flags(store_ctx, X509_V_FLAG_IGNORE_CRITICAL);

		ret = X509_verify_cert(store_ctx);

		if (ret != 1)
#ifdef HAVE_NEWOE
			eWarning(X509_verify_cert_error_string(X509_STORE_CTX_get_error(store_ctx)));
#else
			eWarning(X509_verify_cert_error_string(store_ctx->error));
#endif

		X509_STORE_CTX_free(store_ctx);

		return ret == 1;
	}

	X509 *certificate_load_and_check(X509_STORE *store, const char *filename)
	{
		X509 *cert;

		cert = certificate_open(filename);
		if (!cert) {
			eWarning("[res_content_ctrl] can not open %s", filename);
			return NULL;
		}

		if (!certificate_validate(store, cert)) {
			eWarning("[res_content_ctrl] can not validate %s", filename);
			X509_free(cert);
			return NULL;
		}

		X509_STORE_add_cert(store, cert);

		return cert;
	}

	X509 *certificate_import_and_check(X509_STORE *store, const uint8_t *data, int len)
	{
		X509 *cert;

		cert = d2i_X509(NULL, &data, len);
		if (!cert) {
			eWarning("[res_content_ctrl] can not read certificate");
			return NULL;
		}

		if (!certificate_validate(store, cert)) {
			eWarning("[res_content_ctrl] can not vaildate certificate\n");
			X509_free(cert);
			return NULL;
		}

		X509_STORE_add_cert(store, cert);

		return cert;
	}

}

/* CI+ credentials */

const uint32_t eDVBCICcSessionImpl::datatype_sizes[MAX_ELEMENTS] = {
	0, 50, 0, 0, 0, 8, 8, 0,
	0, 0, 0, 0, 32, 256, 256, 0,
	0, 256, 256, 32, 8, 8, 32, 32,
	0, 8, 2, 32, 1, 32, 1, 0,
	32
};

struct eDVBCICcSessionImpl::element *eDVBCICcSessionImpl::element_get(unsigned int id)
{
	if ((id < 1) || (id >= MAX_ELEMENTS)) {
		eWarning("[res_content_ctrl] invalid id %u", id);
		return NULL;
	}

	return &elements[id];
}

void eDVBCICcSessionImpl::element_invalidate(unsigned int id)
{
	struct element *e;

	e = element_get(id);
	if (e) {
		free(e->data);
		e->data = NULL;
		e->size = 0;
		e->valid = false;
	}
}

void eDVBCICcSessionImpl::element_init()
{
	unsigned int i;

	for (i = 1; i < MAX_ELEMENTS; i++)
		element_invalidate(i);
}

bool eDVBCICcSessionImpl::element_set(unsigned int id, const uint8_t *data, uint32_t size)
{
	struct element *e;

	e = element_get(id);
	if (!e)
		return false;

	if ((datatype_sizes[id] != 0) && (datatype_sizes[id] != size)) {
		eWarning("[res_content_ctrl] size %u of id %u doesn't match", size, id);
		return false;
	}

	free(e->data);
	e->data = (uint8_t *)malloc(size);
	if (e->data) {
		memcpy(e->data, data, size);
		e->size = size;
		e->valid = true;
	} else {
		e->size = 0;
		e->valid = false;
	}

	return e->valid;
}

bool eDVBCICcSessionImpl::element_set_certificate(unsigned int id, X509 *cert)
{
	unsigned char *cert_der = NULL;
	int cert_len;

	cert_len = i2d_X509(cert, &cert_der);
	if (cert_len <= 0) {
		eWarning("[res_content_ctrl] can not encode certificate");
		return false;
	}

	if (!element_set(id, cert_der, cert_len)) {
		eWarning("[res_content_ctrl] can not store certificate id %u", id);
		return false;
	}

	OPENSSL_free(cert_der);

	return true;
}

bool eDVBCICcSessionImpl::element_set_hostid_from_certificate(unsigned int id, X509 *cert)
{
	X509_NAME *subject;
	char hostid[16 + 1];
	uint8_t bin_hostid[8];

	if ((id != 5) && (id != 6)) {
		eWarning("[res_content_ctrl] wrong datatype_id %u for device id", id);
		return false;
	}

	subject = X509_get_subject_name(cert);
	X509_NAME_get_text_by_NID(subject, NID_commonName, hostid, sizeof(hostid));

	if (strlen(hostid) != 16) {
		eWarning("[res_content_ctrl] bad device id");
		return false;
	}

	//eDebug("DEVICE_ID: %s", hostid);

	str2bin(bin_hostid, hostid, 16);

	if (!element_set(id, bin_hostid, sizeof(bin_hostid))) {
		eWarning("[res_content_ctrl] can not store device id %u", id);
		return false;
	}

	return true;
}

bool eDVBCICcSessionImpl::element_valid(unsigned int id)
{
	struct element *e;

	e = element_get(id);

	return e && e->valid;
}

unsigned int eDVBCICcSessionImpl::element_get_buf(uint8_t *dest, unsigned int id)
{
	struct element *e;

	e = element_get(id);
	if (e == NULL)
		return 0;

	if (!e->valid) {
		eWarning("[res_content_ctrl] %u not valid", id);
		return 0;
	}

	if (!e->data) {
		eWarning("[res_content_ctrl] %d doesn't exist", id);
		return 0;
	}

	if (dest)
		memcpy(dest, e->data, e->size);

	return e->size;
}

unsigned int eDVBCICcSessionImpl::element_get_req(uint8_t *dest, unsigned int id)
{
	unsigned int len = element_get_buf(&dest[3], id);

	if (len == 0) {
		eWarning("[res_content_ctrl] can not get %u", id);
		return 0;
	}

	dest[0] = id;
	dest[1] = len >> 8;
	dest[2] = len;

	return 3 + len;
}

uint8_t *eDVBCICcSessionImpl::element_get_ptr(unsigned int id)
{
	struct element *e;

	e = element_get(id);
	if (e == NULL)
		return NULL;

	if (!e->valid) {
		eWarning("[res_content_ctrl] %u not valid", id);
		return NULL;
	}

	if (!e->data) {
		eWarning("[res_content_ctrl] %u doesn't exist", id);
		return NULL;
	}

	return e->data;
}


// content_control commands

bool eDVBCICcSessionImpl::sac_check_auth(const uint8_t *data, unsigned int len)
{
	struct aes_xcbc_mac_ctx ctx;
	uint8_t calced_signature[16];

	if (len < 16) {
		eWarning("[res_content_ctrl] signature too short");
		return false;
	}

	aes_xcbc_mac_init(&ctx, sak);
	aes_xcbc_mac_process(&ctx, (uint8_t *)"\x04", 1); /* header len */
	aes_xcbc_mac_process(&ctx, data, len - 16);
	aes_xcbc_mac_done(&ctx, calced_signature);

	if (memcmp(&data[len - 16], calced_signature, 16)) {
		eWarning("[res_content_ctrl] signature wrong");
		return false;
	}

	//eDebug("auth ok!");

	return true;
}

int eDVBCICcSessionImpl::sac_gen_auth(uint8_t *out, uint8_t *in, unsigned int len)
{
	struct aes_xcbc_mac_ctx ctx;

	aes_xcbc_mac_init(&ctx, sak);
	aes_xcbc_mac_process(&ctx, (uint8_t *)"\x04", 1); /* header len */
	aes_xcbc_mac_process(&ctx, in, len);
	aes_xcbc_mac_done(&ctx, out);

	return 16;
}

void eDVBCICcSessionImpl::generate_key_seed()
{
	SHA256_CTX sha;

	SHA256_Init(&sha);
	SHA256_Update(&sha, &dhsk[240], 16);
	SHA256_Update(&sha, element_get_ptr(AKH), element_get_buf(NULL, AKH));
	SHA256_Update(&sha, element_get_ptr(NS_HOST), element_get_buf(NULL, NS_HOST));
	SHA256_Update(&sha, element_get_ptr(NS_MODULE), element_get_buf(NULL, NS_MODULE));
	SHA256_Final(ks_host, &sha);
}

void eDVBCICcSessionImpl::generate_ns_host()
{
	uint8_t buf[8];
	get_random(buf, sizeof(buf));
	element_set(NS_HOST, buf, sizeof(buf));
}

int eDVBCICcSessionImpl::generate_SAK_SEK()
{
	AES_KEY key;
	uint8_t key_data[16] = { 0xea, 0x74, 0xf4, 0x71, 0x99, 0xd7, 0x6f, 0x35, 0x89, 0xf0, 0xd1, 0xdf, 0x0f, 0xee, 0xe3, 0x00 };
	uint8_t dec[32];
	int i;

	AES_set_encrypt_key(key_data, 128, &key);

	for (i = 0; i < 2; i++)
		AES_ecb_encrypt(&ks_host[16 * i], &dec[16 * i], &key, 1);

	for (i = 0; i < 16; i++)
		sek[i] = ks_host[i] ^ dec[i];

	for (i = 0; i < 16; i++)
		sak[i] = ks_host[16 + i] ^ dec[16 + i];

	return 0;
}

int eDVBCICcSessionImpl::sac_crypt(uint8_t *dst, const uint8_t *src, unsigned int len, int encrypt)
{
	uint8_t iv[16] = { 0xf7, 0x70, 0xb0, 0x36, 0x03, 0x61, 0xf7, 0x96, 0x65, 0x74, 0x8a, 0x26, 0xea, 0x4e, 0x85, 0x41 };
	AES_KEY key;

	if (encrypt)
		AES_set_encrypt_key(sek, 128, &key);
	else
		AES_set_decrypt_key(sek, 128, &key);

	AES_cbc_encrypt(src, dst, len, &key, iv, encrypt);

	return 0;
}

X509 *eDVBCICcSessionImpl::import_ci_certificates(unsigned int id)
{
	X509 *cert;

	if (!element_valid(id)) {
		eWarning("[res_content_ctrl] %u not valid", id);
		return NULL;
	}

	cert = certificate_import_and_check(store, element_get_ptr(id), element_get_buf(NULL, id));
	if (!cert) {
		eWarning("[res_content_ctrl] can not verify certificate %u", id);
		return NULL;
	}

	return cert;
}

int eDVBCICcSessionImpl::check_ci_certificates()
{
	if (!element_valid(CICAM_BRAND_CERT))
		return -1;

	if (!element_valid(CICAM_DEV_CERT))
		return -1;

	if ((ci_cust_cert = import_ci_certificates(CICAM_BRAND_CERT)) == NULL) {
		eWarning("[res_content_ctrl] can not import CICAM brand certificate");
		return -1;
	}

	if ((ci_device_cert = import_ci_certificates(CICAM_DEV_CERT)) == NULL) {
		eWarning("[res_content_ctrl] can not import CICAM device certificate");
		return -1;
	}

	if (!element_set_hostid_from_certificate(CICAM_ID, ci_device_cert)) {
		eWarning("[res_content_ctrl] can not store CICAM_ID");
		return -1;
	}

	return 0;
}

int eDVBCICcSessionImpl::generate_akh()
{
	uint8_t akh[32];
	SHA256_CTX sha;

	SHA256_Init(&sha);
	SHA256_Update(&sha, element_get_ptr(CICAM_ID), element_get_buf(NULL, CICAM_ID));
	SHA256_Update(&sha, element_get_ptr(HOST_ID), element_get_buf(NULL, HOST_ID));
	SHA256_Update(&sha, dhsk, 256);
	SHA256_Final(akh, &sha);

	element_set(AKH, akh, sizeof(akh));

	return 0;
}

int eDVBCICcSessionImpl::compute_dh_key()
{
	int len = DH_size(dh);
	if (len > 256) {
		eWarning("[res_content_ctrl] too long shared key");
		return -1;
	}

	BIGNUM *bn_in = BN_bin2bn(element_get_ptr(DHPM), 256, NULL);

#if 0
	// verify DHPM
	BN_CTX *ctx = BN_CTX_new();
	BIGNUM *out = BN_new();

	if (BN_cmp(BN_value_one(), bn_in) >= 0) {
		eWarning("DHPM <= 1!!!");
	}
	if (BN_cmp(bn_in, dh->p) >= 0) {
		eWarning("DHPM >= dh_p!!!");
	}
	BN_mod_exp(out, bn_in, dh->q, dh->p, ctx);
	if (BN_cmp(out, BN_value_one()) != 0) {
		eWarning("DHPM ^ dh_q mod dh_p != 1!!!");
	}

	BN_free(out);
	BN_CTX_free(ctx);
#endif

	int codes = 0;
	int ok = DH_check_pub_key(dh, bn_in, &codes);
	if (ok == 0)
		eDebug("[res_content_ctrl] check_pub_key failed");
	if (codes & DH_CHECK_PUBKEY_TOO_SMALL)
		eDebug("[res_content_ctrl] too small public key");
	if (codes & DH_CHECK_PUBKEY_TOO_LARGE)
		eDebug("[res_content_ctrl] too large public key");

	int gap = 256 - len;
	memset(dhsk, 0, gap);
	DH_compute_key(dhsk + gap, bn_in, dh);

	BN_free(bn_in);

	return 0;
}

bool eDVBCICcSessionImpl::check_dh_challenge()
{
	//eDebug("checking ...");

	if (!element_valid(AUTH_NONCE))
		return false;

	if (!element_valid(CICAM_ID))
		return false;

	if (!element_valid(DHPM))
		return false;

	if (!element_valid(SIGNATURE_B))
		return false;

	// TODO verify Signature_B

	compute_dh_key();
	generate_akh();

	akh_index = 5;

	eDebug("[res_content_ctrl] writing...");
	write_authdata(slot_index, element_get_ptr(HOST_ID), dhsk, element_get_ptr(AKH));

	return true;
}

int eDVBCICcSessionImpl::generate_dh_key()
{
	uint8_t dhph[256];
	int len;
	unsigned int gap;
#ifdef HAVE_NEWOE
	dh = DH_new();
	BIGNUM *p, *g, *q;
	const BIGNUM *pub_key;
	p = BN_bin2bn(dh_p, sizeof(dh_p), 0);
	g = BN_bin2bn(dh_g, sizeof(dh_g), 0);
	q = BN_bin2bn(dh_q, sizeof(dh_q), 0);
	// Deprecated!   dh->flags |= DH_FLAG_NO_EXP_CONSTTIME;
	DH_set0_pqg(dh, p, q, g);
#else
	dh->p = BN_bin2bn(dh_p, sizeof(dh_p), 0);
	dh->g = BN_bin2bn(dh_g, sizeof(dh_g), 0);
	dh->q = BN_bin2bn(dh_q, sizeof(dh_q), 0);
	dh->flags |= DH_FLAG_NO_EXP_CONSTTIME;
#endif
	DH_generate_key(dh);
#ifdef HAVE_NEWOE
	DH_get0_key(dh, &pub_key, NULL);
	len = BN_num_bytes(pub_key);
#else
	len = BN_num_bytes(dh->pub_key);
#endif
	if (len > 256) {
		eWarning("[res_content_ctrl] too long public key");
		return -1;
	}

#if 0
	// verify DHPH
	BN_CTX *ctx = BN_CTX_new();
	BIGNUM *out = BN_new();

	if (BN_cmp(BN_value_one(), dh->pub_key) >= 0) {
		eWarning("DHPH <= 1!!!");
	}
	if (BN_cmp(dh->pub_key, dh->p) >= 0) {
		eWarning("DHPH >= dh_p!!!");
	}
	BN_mod_exp(out, dh->pub_key, dh->q, dh->p, ctx);
	if (BN_cmp(out, BN_value_one()) != 0) {
		eWarning("DHPH ^ dh_q mod dh_p != 1!!!");
	}

	BN_free(out);
	BN_CTX_free(ctx);
#endif

	gap = 256 - len;
	memset(dhph, 0, gap);
#ifdef HAVE_NEWOE
	BN_bn2bin(pub_key, &dhph[gap]);
#else
	BN_bn2bin(dh->pub_key, &dhph[gap]);
#endif
	element_set(DHPH, dhph, sizeof(dhph));
	return 0;
}

int eDVBCICcSessionImpl::generate_sign_A()
{
	unsigned char dest[302];
	uint8_t hash[20];
	unsigned char dbuf[256];
	unsigned char sign_A[256];

	if (!element_valid(AUTH_NONCE))
		return -1;

	if (!element_valid(DHPH))
		return -1;

	dest[0x00] = 0x00; /* version */
	dest[0x01] = 0x00;
	dest[0x02] = 0x08; /* len (bits) */
	dest[0x03] = 0x01; /* version data */

	dest[0x04] = 0x01; /* msg_label */
	dest[0x05] = 0x00;
	dest[0x06] = 0x08; /* len (bits) */
	dest[0x07] = 0x02; /* message data */

	dest[0x08] = 0x02; /* auth_nonce */
	dest[0x09] = 0x01;
	dest[0x0a] = 0x00; /* len (bits) */
	memcpy(&dest[0x0b], element_get_ptr(AUTH_NONCE), 32);

	dest[0x2b] = 0x04; /* DHPH */
	dest[0x2c] = 0x08;
	dest[0x2d] = 0x00; /* len (bits) */
	memcpy(&dest[0x2e], element_get_ptr(DHPH), 256);

	SHA1(dest, 0x12e, hash);

	rsa_device_key = rsa_privatekey_open("/etc/ssl/certs/device.pem");
	if (!rsa_device_key) {
		eWarning("[res_content_ctrl] can not read private key");
		return -1;
	}

	RSA_padding_add_PKCS1_PSS(rsa_device_key, dbuf, hash, EVP_sha1(), 20);
	RSA_private_encrypt(sizeof(dbuf), dbuf, sign_A, rsa_device_key, RSA_NO_PADDING);

	element_set(SIGNATURE_A, sign_A, sizeof(sign_A));

	return 0;
}

int eDVBCICcSessionImpl::restart_dh_challenge()
{
	if (!element_valid(AUTH_NONCE))
		return -1;

	//eDebug("rechecking...");

	store = X509_STORE_new();
	if (!store) {
		eWarning("[res_content_ctrl] can not create root_ca");
		return -1;
	}

	if (X509_STORE_load_locations(store, "/etc/ssl/certs/root.pem", NULL) != 1) {
		eWarning("[res_content_ctrl] can not load root_ca");
		return -1;
	}

	cust_cert = certificate_load_and_check(store, "/etc/ssl/certs/customer.pem");
	device_cert = certificate_load_and_check(store, "/etc/ssl/certs/device.pem");

	if (!cust_cert || !device_cert) {
		eWarning("[res_content_ctrl] can not check loader certificates");
		return -1;
	}

	if (!element_set_certificate(HOST_BRAND_CERT, cust_cert))
		eWarning("[res_content_ctrl] can not store brand certificate");

	if (!element_set_certificate(HOST_DEV_CERT, device_cert))
		eWarning("[res_content_ctrl] can not store device certificate");

	if (!element_set_hostid_from_certificate(HOST_ID, device_cert))
		eWarning("[res_content_ctrl] can not store HOST_ID");

	element_invalidate(CICAM_ID);
	element_invalidate(DHPM);
	element_invalidate(SIGNATURE_B);
	element_invalidate(AKH);

	generate_dh_key();
	generate_sign_A();

	return 0;
}

int eDVBCICcSessionImpl::generate_uri_confirm()
{
	SHA256_CTX sha;
	uint8_t uck[32];
	uint8_t uri_confirm[32];

	//eDebug("uri_confirm...");

	// UCK
	SHA256_Init(&sha);
	SHA256_Update(&sha, sak, 16);
	SHA256_Final(uck, &sha);

	// uri_confirm
	SHA256_Init(&sha);
	SHA256_Update(&sha, element_get_ptr(URI_MESSAGE), element_get_buf(NULL, URI_MESSAGE));
	SHA256_Update(&sha, uck, 32);
	SHA256_Final(uri_confirm, &sha);

	element_set(URI_CONFIRM, uri_confirm, 32);

	return 0;
}

void eDVBCICcSessionImpl::check_new_key()
{
	const uint8_t s_key[16] = { 0x3e, 0x20, 0x15, 0x84, 0x2c, 0x37, 0xce, 0xe3, 0xd6, 0x14, 0x57, 0x3e, 0x3a, 0xab, 0x91, 0xb6 };
	AES_KEY aes_ctx;
	uint8_t dec[32];
	uint8_t *kp;
	uint8_t slot;
	unsigned int i;

	if (!element_valid(KP))
		return;

	if (!element_valid(KEY_REGISTER))
		return;

	//eDebug("key checking...");

	kp = element_get_ptr(KP);
	element_get_buf(&slot, KEY_REGISTER);

	AES_set_encrypt_key(s_key, 128, &aes_ctx);
	for (i = 0; i < 32; i += 16)
		AES_ecb_encrypt(&kp[i], &dec[i], &aes_ctx, 1);

	for (i = 0; i < 32; i++)
		dec[i] ^= kp[i];

	if (slot != 0 && slot != 1)
		slot = 1;

	descrambler_set_key(desc_fd, slot_index, slot, dec);

	element_invalidate(KP);
	element_invalidate(KEY_REGISTER);
}

int eDVBCICcSessionImpl::data_get_handle_new(unsigned int id)
{
	switch (id) {
	case CICAM_BRAND_CERT:
	case DHPM:
	case CICAM_DEV_CERT:
//	case CICAM_ID:
	case SIGNATURE_B:
		if (check_ci_certificates())
			break;

		check_dh_challenge();
		break;

	case AUTH_NONCE:
		restart_dh_challenge();
		break;

	case NS_MODULE:
		generate_ns_host();
		generate_key_seed();
		generate_SAK_SEK();
		break;

	case CICAM_ID:
	case KP:
	case KEY_REGISTER:
		check_new_key();
		break;

	case PROGRAM_NUMBER:
	case URI_MESSAGE:
		generate_uri_confirm();
		break;

	default:
		eWarning("[res_content_ctrl] unhandled id %u", id);
		break;
	}

	return 0;
}

int eDVBCICcSessionImpl::data_req_handle_new(unsigned int id)
{
	switch (id) {
	case 22:
	{
		uint8_t akh[32], host_id[8];

		memset(akh, 0, sizeof(akh));

		if (akh_index != 5) {
			if (!get_authdata(host_id, dhsk, akh, slot_index, akh_index++))
				akh_index = 5;

			if (!element_set(AKH, akh, 32))
				eWarning("[res_content_ctrl] can not set AKH in elements");

			if (!element_set(HOST_ID, host_id, 8))
				eWarning("[res_content_ctrl] can not set host_id in elements");
		}
		break;
	}

	default:
		break;
	}

	return 0;
}

int eDVBCICcSessionImpl::data_get_loop(const uint8_t *data, unsigned int datalen, unsigned int items)
{
	unsigned int i;
	int dt_id, dt_len;
	unsigned int pos = 0;

	for (i = 0; i < items; i++) {
		if (pos + 3 > datalen)
			return 0;

		dt_id = data[pos++];
		dt_len = data[pos++] << 8;
		dt_len |= data[pos++];

		if (pos + dt_len > datalen)
			return 0;

		//eDebugNoNewLineStart("set element %d: ", dt_id);
		//hexdump(&data[pos], dt_len);

		element_set(dt_id, &data[pos], dt_len);

		data_get_handle_new(dt_id);

		pos += dt_len;
	}

	return pos;
}

int eDVBCICcSessionImpl::data_req_loop(uint8_t *dest, unsigned int dest_len, const uint8_t *data, unsigned int data_len, unsigned int items)
{
	int dt_id;
	unsigned int i;
	int pos = 0;
	unsigned int len;

	if (items > data_len)
		return -1;

	for (i = 0; i < items; i++) {
		dt_id = data[i];
		data_req_handle_new(dt_id);    /* check if there is any action needed before we answer */

		len = element_get_buf(NULL, dt_id);
		if ((len + 3) > dest_len) {
			eWarning("[res_content_ctrl] req element %d: not enough space", dt_id);
			return -1;
		}

		len = element_get_req(dest, dt_id);
		//eDebugNoNewLineStart("req element %d: ", dt_id);
		//hexdump(&dest[3], len - 3);

		pos += len;
		dest += len;
		dest_len -= len;
	}

	return pos;
}

void eDVBCICcSessionImpl::cc_open_req()
{
	const uint8_t tag[3] = { 0x9f, 0x90, 0x02 };
	const uint8_t bitmap = 0x01;
	session->send(tag, &bitmap, 1);
}

void eDVBCICcSessionImpl::cc_data_req(const uint8_t *data, unsigned int len)
{
	uint8_t cc_data_cnf_tag[3] = { 0x9f, 0x90, 0x04 };
	uint8_t dest[BUFSIZ];
	int dt_nr;
	int id_bitmask;
	int answ_len;
	unsigned int rp = 0;

	if (len < 2) {
		eWarning("[res_content_ctrl] too short data");
		return;
	}

	id_bitmask = data[rp++];

	dt_nr = data[rp++];
	rp += data_get_loop(&data[rp], len - rp, dt_nr);

	if (len < rp + 1)
		return;

	dt_nr = data[rp++];

	unsigned int dest_len = sizeof(dest);
	if (dest_len < 2) {
		eWarning("[res_content_ctrl] not enough space");
		return;
	}

	dest[0] = id_bitmask;
	dest[1] = dt_nr;

	answ_len = data_req_loop(&dest[2], dest_len - 2, &data[rp], len - rp, dt_nr);
	if (answ_len <= 0) {
		eWarning("[res_content_ctrl] can not get data");
		return;
	}

	answ_len += 2;

	session->send(cc_data_cnf_tag, dest, answ_len);
}

void eDVBCICcSessionImpl::cc_sac_send(const uint8_t *tag, uint8_t *data, unsigned int pos)
{
	if (pos < 8) {
		eWarning("[res_content_ctrl] too short data");
		return;
	}

	pos += add_padding(&data[pos], pos - 8, 16);
	BYTE16(&data[6], pos - 8);      /* len in header */

	pos += sac_gen_auth(&data[pos], data, pos);
	sac_crypt(&data[8], &data[8], pos - 8, AES_ENCRYPT);

	session->send(tag, data, pos);

	return;
}

void eDVBCICcSessionImpl::cc_sac_data_req(const uint8_t *data, unsigned int len)
{
	const uint8_t data_cnf_tag[3] = { 0x9f, 0x90, 0x08 };
	uint8_t dest[BUFSIZ];
	uint8_t tmp[len];
	int id_bitmask, dt_nr;
	unsigned int serial;
	int answ_len;
	int pos = 0;
	unsigned int rp = 0;

	if (len < 10)
		return;

	//eDebugNoNewLineStart("cc_sac_data_req: ");
	//hexdump(data, len);

	memcpy(tmp, data, 8);
	sac_crypt(&tmp[8], &data[8], len - 8, AES_DECRYPT);
	data = tmp;

	if (!sac_check_auth(data, len)) {
		eWarning("[res_content_ctrl] check_auth of message failed");
		return;
	}

	serial = UINT32(&data[rp], 4);
	//eDebug("%u\n", serial);

	/* skip serial & header */
	rp += 8;

	id_bitmask = data[rp++];

	/* handle data loop */
	dt_nr = data[rp++];
	rp += data_get_loop(&data[rp], len - rp, dt_nr);

	if (len < rp + 1) {
		eWarning("[res_content_ctrl] check_auth of message too short");
		return;
	}

	dt_nr = data[rp++];

	/* create answer */
	unsigned int dest_len = sizeof(dest);

	if (dest_len < 10) {
		eWarning("[res_content_ctrl] not enough space");
		return;
	}

	pos += BYTE32(&dest[pos], serial);
	pos += BYTE32(&dest[pos], 0x01000000);

	dest[pos++] = id_bitmask;
	dest[pos++] = dt_nr;    /* dt_nbr */

	answ_len = data_req_loop(&dest[pos], dest_len - 10, &data[rp], len - rp, dt_nr);
	if (answ_len <= 0) {
		eWarning("[res_content_ctrl] can not get data");
		return;
	}
	pos += answ_len;

	cc_sac_send(data_cnf_tag, dest, pos);
}

void eDVBCICcSessionImpl::cc_sac_sync_req(const uint8_t *data, unsigned int len)
{
	const uint8_t sync_cnf_tag[3] = { 0x9f, 0x90, 0x10 };
	uint8_t dest[64];
	unsigned int serial;
	int pos = 0;

	//eDebugNoNewLineStart("cc_sac_sync_req: ");
	//hexdump(data, len);

	serial = UINT32(data, 4);
	//eDebug("%u\n", serial);

	pos += BYTE32(&dest[pos], serial);
	pos += BYTE32(&dest[pos], 0x01000000);

	/* status OK */
	dest[pos++] = 0;

	cc_sac_send(sync_cnf_tag, dest, pos);
}

void eDVBCICcSessionImpl::cc_sync_req(const uint8_t *data, unsigned int len)
{
	const uint8_t tag[3] = { 0x9f, 0x90, 0x06 };
	const uint8_t status = 0x00;    /* OK */

	session->send(tag, &status, 1);
}

eDVBCICcSessionImpl::eDVBCICcSessionImpl(eDVBCICcSession *session_, int slot_index_, int version_)
		: session(session_), slot_index(slot_index_), version(version_), akh_index(0),
		  store(0), cust_cert(0), device_cert(0), ci_cust_cert(0), ci_device_cert(0),
		  rsa_device_key(0), dh(0)
{
	uint8_t buf[32], host_id[8];
	unsigned int i;

	for (i = 0; i < MAX_ELEMENTS; i++) {
		elements[i].data = 0;
		elements[i].size = 0;
		elements[i].valid = false;
	}

	memset(buf, 0, 1);
	if (!element_set(STATUS_FIELD, buf, 1)) {
		eWarning("[res_content_ctrl] can not set status");
	}

	memset(buf, 0, 32);

#define CI_CC_URI_PROTOCOL_V1	0x01
#define CI_CC_URI_PROTOCOL_V2	0x02

	buf[31] = CI_CC_URI_PROTOCOL_V1;
	if (version == 2)
		buf[31] |= CI_CC_URI_PROTOCOL_V2;

	if (!element_set(URI_VERSIONS, buf, 32)) {
		eWarning("[res_content_ctrl] can not set uri_versions");
	}

	if (!get_authdata(host_id, dhsk, buf, slot_index, akh_index)) {
		memset(buf, 0, sizeof(buf));
		akh_index = 5;
	}

	if (!element_set(AKH, buf, 32)) {
		eWarning("[res_content_ctrl] can not set AKH");
	}

	if (!element_set(HOST_ID, host_id, 8)) {
		eWarning("[res_content_ctrl] can not set host_id");
	}

	desc_fd = descrambler_init();
}

eDVBCICcSessionImpl::~eDVBCICcSessionImpl()
{
	descrambler_deinit(desc_fd);

	if (store)
		X509_STORE_free(store);

	if (cust_cert)
		X509_free(cust_cert);

	if (device_cert)
		X509_free(device_cert);

	if (ci_cust_cert)
		X509_free(ci_cust_cert);

	if (ci_device_cert)
		X509_free(ci_device_cert);

	if (rsa_device_key)
		RSA_free(rsa_device_key);

	if (dh)
		DH_free(dh);

	element_init();
}

int eDVBCICcSessionImpl::receiveAPDU(const unsigned char *tag, const void *data, int len)
{
	if ((tag[0] == 0x9f) && (tag[1] == 0x90)) {
		switch (tag[2]) {
		case 0x01: cc_open_req(); break;
		case 0x03: cc_data_req((const uint8_t *)data, len); break;
		case 0x05: cc_sync_req((const uint8_t *)data, len); break;
		case 0x07: cc_sac_data_req((const uint8_t *)data, len); break;
		case 0x09: cc_sac_sync_req((const uint8_t *)data, len); break;
		default:
			eWarning("[res_content_ctrl] unknown APDU tag %02x", tag[2]);
			break;
		}
	}

	return 0;
}

int eDVBCICcSessionImpl::addProgram(uint16_t program_number, std::vector<uint16_t>& pids)
{
	for (std::vector<uint16_t>::iterator it = pids.begin(); it != pids.end(); ++it)
		descrambler_set_pid(desc_fd, slot_index, 1, *it);

	return 0;
}

int eDVBCICcSessionImpl::removeProgram(uint16_t program_number, std::vector<uint16_t>& pids)
{
	for (std::vector<uint16_t>::iterator it = pids.begin(); it != pids.end(); ++it)
		descrambler_set_pid(desc_fd, slot_index, 0, *it);

	return 0;
}
