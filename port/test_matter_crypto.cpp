#include <crypto/CHIPCryptoPAL.h>
#include <crypto/tests/AES_CCM_128_test_vectors.h>
#include <cstdlib>
#include <cassert>
#include <cstdio>
#include <cstring>
int main() {
  using namespace chip;
  using namespace chip::Crypto;
  unsigned vectors = 0;
  for (const auto *v : ccm_128_test_vectors) {
    Aes128KeyHandle vectorKey;
    assert(v->key_len == vectorKey.Size());
    std::memcpy(vectorKey.AsMutable<Symmetric128BitsKeyByteArray>(), v->key, v->key_len);
    auto *out = static_cast<uint8_t *>(std::calloc(v->ct_len + 1, 1));
    auto *outTag = static_cast<uint8_t *>(std::calloc(v->tag_len + 1, 1));
    assert(out && outTag);
    const auto err = AES_CCM_encrypt(v->pt, v->pt_len, v->aad, v->aad_len, vectorKey,
      v->nonce, v->nonce_len, v->ct_len ? out : nullptr, outTag, v->tag_len);
    assert(err == v->result);
    if (err == CHIP_NO_ERROR) {
      assert(v->ct_len == 0 || std::memcmp(out, v->ct, v->ct_len) == 0);
      assert(std::memcmp(outTag, v->tag, v->tag_len) == 0);
    }
    std::free(out); std::free(outTag); ++vectors;
  }
  std::printf("PASS: %u upstream AES-CCM known-answer/error vectors\n", vectors);
  const uint8_t message[] = {'a', 'b', 'c'};
  const uint8_t expected[] = {0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad};
  uint8_t digest[32];
  assert(Hash_SHA256(message, sizeof(message), digest) == CHIP_NO_ERROR);
  assert(std::memcmp(digest, expected, sizeof(digest)) == 0);
  // Synthetic test key only; directly exercise the raw-key mbedTLS backend.
  Aes128KeyHandle key;
  auto &rawKey = key.AsMutable<Symmetric128BitsKeyByteArray>();
  for (unsigned i = 0; i < sizeof(rawKey); ++i) rawKey[i] = static_cast<uint8_t>(i);
  uint8_t nonce[13] = {};
  uint8_t aad[] = {1,2,3};
  uint8_t ciphertext[3], plaintext[3], tag[16];
  assert(AES_CCM_encrypt(message, sizeof(message), aad, sizeof(aad), key, nonce, sizeof(nonce), ciphertext, tag, sizeof(tag)) == CHIP_NO_ERROR);
  assert(AES_CCM_decrypt(ciphertext, sizeof(ciphertext), aad, sizeof(aad), tag, sizeof(tag), key, nonce, sizeof(nonce), plaintext) == CHIP_NO_ERROR);
  assert(std::memcmp(plaintext, message, sizeof(message)) == 0);
  tag[0] ^= 1;
  assert(AES_CCM_decrypt(ciphertext, sizeof(ciphertext), aad, sizeof(aad), tag, sizeof(tag), key, nonce, sizeof(nonce), plaintext) != CHIP_NO_ERROR);
  P256Keypair signer;
  assert(signer.Initialize(ECPKeyTarget::ECDSA) == CHIP_NO_ERROR);
  P256ECDSASignature signature;
  assert(signer.ECDSA_sign_msg(message, sizeof(message), signature) == CHIP_NO_ERROR);
  assert(signer.Pubkey().ECDSA_validate_msg_signature(message, sizeof(message), signature) == CHIP_NO_ERROR);
  const uint8_t wrong[] = {'a', 'b', 'd'};
  assert(signer.Pubkey().ECDSA_validate_msg_signature(wrong, sizeof(wrong), signature) != CHIP_NO_ERROR);
  std::puts("PASS: real Matter crypto PAL SHA-256 known answer, AES-CCM roundtrip, tampered tag rejection, P256 sign/verify and tamper rejection");
}
