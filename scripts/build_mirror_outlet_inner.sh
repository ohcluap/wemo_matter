#!/bin/sh
set -eu
cd /sdk
[ "$(git -c safe.directory=/sdk rev-parse HEAD)" = ff2472ff8d681496bf6e01450948ac95afc8898f ]
[ -x /sdk/.zap/zap-cli ]
ln -s /sdk/openwrt/staging_dir /opt/staging
python3 /work/scripts/configure_outlet.py --sdk /sdk
python3 scripts/tools/zap/generate.py examples/lighting-app/lighting-common/lighting-app.zap --no-prettify-output > /export/outlet-generation.log 2>&1
mkdir -p /sdk/build-output/outlet
python3 - <<'PY'
from pathlib import Path
args = Path('/work/toolchains/mips-app.gn').read_text()
args += '\nchip_enable_all_clusters = false\nchip_detail_logging = false\nchip_progress_logging = false\nchip_automation_logging = false\nchip_config_short_error_str = true\n'
Path('/sdk/build-output/outlet/args.gn').write_text(args)
PY
cd examples/lighting-app/linux
gn gen /sdk/build-output/outlet
if ! ninja -C /sdk/build-output/outlet -j6 chip-lighting-app > /sdk/build-output/outlet/build.log 2>&1; then
    tail -70 /sdk/build-output/outlet/build.log
    cp /sdk/build-output/outlet/build.log /export/outlet-build.log
    exit 1
fi
compiler=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl/bin/mipsel-openwrt-linux
$compiler-readelf -h -A /sdk/build-output/outlet/chip-lighting-app > /export/outlet-elf.txt
$compiler-readelf -l /sdk/build-output/outlet/chip-lighting-app > /export/outlet-segments.txt
grep -q 'FP ABI: Soft float' /export/outlet-elf.txt
if grep -q INTERP /export/outlet-segments.txt; then exit 1; fi
$compiler-strip -o /export/wemo-matter-outlet /sdk/build-output/outlet/chip-lighting-app
cp /sdk/build-output/outlet/build.log /export/outlet-build.log
wc -c /export/wemo-matter-outlet
sha256sum /export/wemo-matter-outlet
