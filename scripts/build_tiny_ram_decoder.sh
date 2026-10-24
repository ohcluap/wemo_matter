#!/bin/sh
set -eu
ln -s /sdk/openwrt/staging_dir /opt/staging
toolchain=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl/bin/mipsel-openwrt-linux
export STAGING_DIR=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl
$toolchain-gcc -Wall -Wextra -Werror -Os -msoft-float -march=24kc -static \
 -ffunction-sections -fdata-sections -Wl,--gc-sections \
 -I/sdk/ram-decoder/source/src/liblzma/api /work/port/ram_unpack.c \
 /sdk/ram-decoder/build/src/liblzma/.libs/liblzma.a -o /sdk/ram-decoder/tiny
$toolchain-strip -o /export/wemo-unpack /sdk/ram-decoder/tiny
$toolchain-readelf -h -A -l /export/wemo-unpack > /export/tiny-decoder-elf.txt
if grep -q INTERP /export/tiny-decoder-elf.txt; then exit 1; fi
wc -c /export/wemo-unpack
sha256sum /export/wemo-unpack
