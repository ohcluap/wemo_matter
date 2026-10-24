#!/bin/sh
# Offline experiment only; does not install on or contact a Wemo.
set -eu
ln -s /sdk/openwrt/staging_dir /opt/staging
mkdir -p /sdk/ram-decoder/source /sdk/ram-decoder/build
tar -xf /work/artifacts/xz-5.2.1-vendor.tar.bz2 -C /sdk/ram-decoder/source --strip-components=1
python3 - <<'PY'
from pathlib import Path
p = Path('/sdk/ram-decoder/source/src/xzdec/xzdec.c')
s = p.read_text()
old = 'lzma_stream_decoder(strm, UINT64_MAX, LZMA_CONCATENATED)'
assert s.count(old) == 1
p.write_text(s.replace(old, 'lzma_stream_decoder(strm, 4U * 1024U * 1024U, LZMA_CONCATENATED)'))
PY
cd /sdk/ram-decoder/build
toolchain=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl/bin/mipsel-openwrt-linux
export STAGING_DIR=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl
CC=$toolchain-gcc AR=$toolchain-ar RANLIB=$toolchain-ranlib \
CFLAGS='-Os -msoft-float -march=24kc -ffunction-sections -fdata-sections' \
LDFLAGS='-static -Wl,--gc-sections' \
../source/configure --host=mipsel-openwrt-linux --disable-shared --enable-static \
 --disable-encoders --enable-decoders=lzma1,lzma2 --enable-small --disable-threads \
 --disable-xz --enable-xzdec --disable-lzmadec --disable-lzmainfo \
 --disable-scripts --disable-doc --disable-nls > /export/decoder-configure.log 2>&1
make -j4 > /export/decoder-build.log 2>&1
# Libtool consumes -static for its own library selection; explicitly link libc.
$toolchain-gcc -Os -msoft-float -march=24kc -static -Wl,--gc-sections \
 -o src/xzdec/xzdec-static src/xzdec/xzdec-xzdec.o \
 src/xzdec/xzdec-tuklib_progname.o src/xzdec/xzdec-tuklib_exit.o \
 src/liblzma/.libs/liblzma.a
$toolchain-strip -o /export/wemo-xzdec src/xzdec/xzdec-static
$toolchain-readelf -h -A -l /export/wemo-xzdec > /export/decoder-elf.txt
if grep -q INTERP /export/decoder-elf.txt; then exit 1; fi
wc -c /export/wemo-xzdec
sha256sum /export/wemo-xzdec
