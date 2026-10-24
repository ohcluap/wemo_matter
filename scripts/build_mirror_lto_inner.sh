#!/bin/sh
set -eu
ln -s /sdk/openwrt/staging_dir /opt/staging
mkdir -p /sdk/build-output/lto
python3 - <<'PY'
from pathlib import Path
args = Path('/sdk/build-output/outlet/args.gn').read_text()
args += '\ntarget_cflags += [ "-flto", "-fno-fat-lto-objects" ]\ntarget_ldflags += [ "-flto=4", "-fuse-linker-plugin" ]\ntarget_ar = "/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl/bin/mipsel-openwrt-linux-gcc-ar"\n'
Path('/sdk/build-output/lto/args.gn').write_text(args)
PY
cd /sdk/examples/lighting-app/linux
gn gen /sdk/build-output/lto
if ! ninja -C /sdk/build-output/lto -j4 chip-lighting-app > /sdk/build-output/lto/build.log 2>&1; then
    tail -70 /sdk/build-output/lto/build.log
    cp /sdk/build-output/lto/build.log /export/lto-build.log
    exit 1
fi
compiler=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl/bin/mipsel-openwrt-linux
$compiler-readelf -h -A /sdk/build-output/lto/chip-lighting-app > /export/lto-elf.txt
$compiler-readelf -l /sdk/build-output/lto/chip-lighting-app > /export/lto-segments.txt
grep -q 'FP ABI: Soft float' /export/lto-elf.txt
if grep -q INTERP /export/lto-segments.txt; then exit 1; fi
$compiler-strip -o /export/wemo-matter-outlet-lto /sdk/build-output/lto/chip-lighting-app
cp /sdk/build-output/lto/build.log /export/lto-build.log
wc -c /export/wemo-matter-outlet-lto
sha256sum /export/wemo-matter-outlet-lto
