#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p artifacts/busybox
docker run --rm --network none \
 -e STAGING_DIR=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl \
 -v "$PWD/sources/openwrt-sdk/staging_dir:/opt/staging:ro" \
 -v "$PWD/scripts:/scripts:ro" \
 -v "$PWD/sources/busybox-1.23.2:/source" -v "$PWD/artifacts/busybox:/out" \
 wemo-matter-board-builder:bookworm sh -ec '
 export PATH="$STAGING_DIR/bin:$PATH"
 make -C /source O=/out allnoconfig
 python3 /scripts/configure_busybox.py
 yes "" | make -C /source O=/out oldconfig >/out/oldconfig.log
 make -C /source O=/out CROSS_COMPILE=mipsel-openwrt-linux- EXTRA_CFLAGS="-fcommon -march=24kec -msoft-float -mabi=32" -j4
 '
