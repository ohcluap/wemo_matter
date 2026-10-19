#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p artifacts/wifi
docker run --rm --network none \
 -e STAGING_DIR=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl \
 -v "$PWD/sources/openwrt-sdk/staging_dir:/opt/staging:ro" \
 -v "$PWD/sources/libnl-3.10.0:/libnl" -v "$PWD/sources/wpa_supplicant-2.11:/wpa" \
 -v "$PWD/sources/hostapd-2.11:/hostapd" -v "$PWD/artifacts/wifi:/out" \
 wemo-matter-board-builder:bookworm sh -ec '
 export PATH="$STAGING_DIR/bin:$PATH"
 export CC=mipsel-openwrt-linux-gcc AR=mipsel-openwrt-linux-ar RANLIB=mipsel-openwrt-linux-ranlib
 export CFLAGS="-Os -march=24kec -msoft-float -mabi=32"
 cd /libnl
 if [ ! -f Makefile ]; then ./configure --host=mipsel-openwrt-linux --prefix=/out/sysroot --disable-shared --enable-static --disable-cli --disable-pthreads; fi
 make -j4
 make install
 export PKG_CONFIG_LIBDIR=/out/sysroot/lib/pkgconfig
 cd /wpa/wpa_supplicant
 printf "%s\n" "CONFIG_DRIVER_NL80211=y" "CONFIG_DRIVER_WEXT=y" "CONFIG_LIBNL32=y" "CONFIG_CTRL_IFACE=y" "CONFIG_BACKEND=file" "CONFIG_TLS=internal" "CONFIG_INTERNAL_LIBTOMMATH=y" "CONFIG_INTERNAL_LIBTOMMATH_FAST=y" "CONFIG_DEBUG_FILE=y" "CFLAGS += -I/out/sysroot/include/libnl3" "LIBS += -L/out/sysroot/lib" "LDFLAGS += -static" > .config
 make CC="$CC" -j4 wpa_supplicant wpa_cli wpa_passphrase
 cp wpa_supplicant wpa_cli wpa_passphrase /out/
 cd /hostapd/hostapd
 printf "%s\n" "CONFIG_DRIVER_NL80211=y" "CONFIG_LIBNL32=y" "CONFIG_CTRL_IFACE=y" "CONFIG_TLS=internal" "CONFIG_INTERNAL_LIBTOMMATH=y" "CONFIG_INTERNAL_LIBTOMMATH_FAST=y" "CONFIG_NO_RADIUS=y" "CFLAGS += -I/out/sysroot/include/libnl3" "LIBS += -L/out/sysroot/lib" "LDFLAGS += -static" > .config
 make CC="$CC" -j4 hostapd hostapd_cli
 cp hostapd hostapd_cli /out/
 mipsel-openwrt-linux-strip --strip-all /out/wpa_supplicant /out/wpa_cli /out/wpa_passphrase /out/hostapd /out/hostapd_cli
 '
