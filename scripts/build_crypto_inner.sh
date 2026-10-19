#!/bin/sh
set -eu
export PATH=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl/bin:$PATH
export STAGING_DIR=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl
if [ ! -d /out/mbedtls ]; then cp -R /sdk/third_party/mbedtls/repo /out/mbedtls; fi
make -C /out/mbedtls/library -j4 CC=mipsel-openwrt-linux-gcc AR=mipsel-openwrt-linux-ar \
  CFLAGS='-Os -march=24kec -msoft-float -mabi=32 -ffunction-sections -fdata-sections' libmbedcrypto.a libmbedx509.a
mkdir -p /out/generated/asn1
python3 /sdk/src/lib/asn1/gen_asn1oid.py --output_file /out/generated/asn1/ASN1OID.h
mipsel-openwrt-linux-g++ -std=c++20 -fno-exceptions -fno-rtti -Os -static -march=24kec -msoft-float -mabi=32 \
  -ffunction-sections -fdata-sections -Wl,--gc-sections -include /work/port/OfflineConfig.h \
  -I/out/generated -I/sdk/src -I/sdk/third_party/nlio/repo/include -I/out/mbedtls/include \
  /work/port/test_matter_crypto.cpp /sdk/src/crypto/CHIPCryptoPALmbedTLS.cpp /sdk/src/crypto/CHIPCryptoPAL.cpp \
  /sdk/src/lib/support/BufferWriter.cpp /out/mbedtls/library/libmbedx509.a /out/mbedtls/library/libmbedcrypto.a -o /out/test-matter-crypto
timeout 60 qemu-mipsel -cpu 24KEc /out/test-matter-crypto
