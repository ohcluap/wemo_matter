#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges \
 --read-only --tmpfs /tmp:exec -v "$PWD:/work:ro" -w /work \
 wemo-matter-board-builder:bookworm sh -ec '
 gcc -Os -Wall -Wextra -Werror -Wno-unused-parameter \
  -ffunction-sections -fdata-sections -Wl,--gc-sections -DCONFIG_CRYPTO_INTERNAL \
  -Isources/wpa_supplicant-2.11/src -Isources/wpa_supplicant-2.11/src/utils \
  port/wifi_provision.c sources/wpa_supplicant-2.11/src/crypto/sha1-pbkdf2.c \
  sources/wpa_supplicant-2.11/src/crypto/sha1.c sources/wpa_supplicant-2.11/src/crypto/sha1-internal.c \
  sources/wpa_supplicant-2.11/src/utils/common.c -o /tmp/wifi-provision
 WEMO_WIFI_TEST_BINARY=/tmp/wifi-provision PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
 '
