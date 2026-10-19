#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
docker run --rm --network none -e STAGING_DIR=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl \
 -v "$PWD/sources/openwrt-sdk/staging_dir:/opt/staging:ro" \
 -v "$PWD/artifacts/wifi:/out" -v "$PWD/port:/port:ro" \
 -v "$PWD/sources/wpa_supplicant-2.11:/wpa:ro" wemo-matter-board-builder:bookworm sh -ec '
 export PATH="$STAGING_DIR/bin:$PATH"
 mipsel-openwrt-linux-gcc -Os -Wall -Wextra -Werror -static -march=24kec -msoft-float -mabi=32 \
  -Wno-unused-parameter -ffunction-sections -fdata-sections -Wl,--gc-sections -DCONFIG_CRYPTO_INTERNAL \
  -I/wpa/src -I/wpa/src/utils /port/wifi_provision.c /wpa/src/crypto/sha1-pbkdf2.c \
  /wpa/src/crypto/sha1.c /wpa/src/crypto/sha1-internal.c /wpa/src/utils/common.c -o /out/wemo-wifi-provision
 mipsel-openwrt-linux-strip --strip-all /out/wemo-wifi-provision
 '
