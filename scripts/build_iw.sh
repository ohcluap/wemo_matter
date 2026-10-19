#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
docker run --rm --network none -e STAGING_DIR=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl \
 -v "$PWD/sources/openwrt-sdk/staging_dir:/opt/staging:ro" -v "$PWD/sources/iw-6.9:/iw" \
 -v "$PWD/artifacts/wifi:/out" -v "$PWD/port:/port:ro" wemo-matter-board-builder:bookworm sh -ec '
 export PATH="$STAGING_DIR/bin:$PATH"
 export PKG_CONFIG_LIBDIR=/out/sysroot/lib/pkgconfig
 make -C /iw CC=mipsel-openwrt-linux-gcc CFLAGS="-Os -march=24kec -msoft-float -mabi=32 -I/out/sysroot/include/libnl3 -DCONFIG_LIBNL30" LDFLAGS="-static -L/out/sysroot/lib" -j4
 cp /iw/iw /out/iw
 mipsel-openwrt-linux-gcc -Os -static -march=24kec -msoft-float -mabi=32 /port/netns_exec.c -o /out/netns-exec
 mipsel-openwrt-linux-strip --strip-all /out/iw /out/netns-exec
 '
