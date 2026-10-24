#!/bin/sh
set -eu
ln -s /sdk/openwrt/staging_dir /opt/staging
python3 /work/scripts/configure_outlet.py --sdk /sdk
python3 /work/scripts/trim_mirror_outlet.py
python3 /work/scripts/trim_mirror_diagnostics.py
python3 /work/scripts/trim_mirror_json_options.py
cd /sdk
python3 scripts/tools/zap/generate.py examples/lighting-app/lighting-common/lighting-app.zap --no-prettify-output > /export/oz-generation.log 2>&1
mkdir -p /sdk/build-output/lean
python3 - <<'PY'
from pathlib import Path
args = Path('/sdk/build-output/outlet/args.gn').read_text()
args += '\nchip_enable_transport_trace = false\ntarget_cflags += [ "-flto", "-fno-fat-lto-objects" ]\ntarget_ldflags += [ "-flto=4", "-fuse-linker-plugin" ]\ntarget_ar = "/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl/bin/mipsel-openwrt-linux-gcc-ar"\n'
args += '\ntarget_ldflags += [ \"-Oz\" ]\n'
Path('/sdk/build-output/lean/args.gn').write_text(args)
PY
cd /sdk/examples/lighting-app/linux
gn gen /sdk/build-output/lean
if ! ninja -C /sdk/build-output/lean -j4 chip-lighting-app > /sdk/build-output/lean/build.log 2>&1; then
    tail -70 /sdk/build-output/lean/build.log
    cp /sdk/build-output/lean/build.log /export/oz-build.log
    exit 1
fi
compiler=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl/bin/mipsel-openwrt-linux
$compiler-readelf -h -A /sdk/build-output/lean/chip-lighting-app > /export/oz-elf.txt
$compiler-readelf -l /sdk/build-output/lean/chip-lighting-app > /export/oz-segments.txt
grep -q 'FP ABI: Soft float' /export/oz-elf.txt
if grep -q INTERP /export/oz-segments.txt; then exit 1; fi
$compiler-strip -o /export/wemo-matter-outlet-oz /sdk/build-output/lean/chip-lighting-app
cp /sdk/build-output/lean/build.log /export/oz-build.log
wc -c /export/wemo-matter-outlet-oz
sha256sum /export/wemo-matter-outlet-oz
