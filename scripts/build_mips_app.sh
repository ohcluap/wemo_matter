#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
variant=mips
if [ "${1:-}" = --firmware ]; then variant=firmware; shift; fi
[ "$#" = 0 ] || { echo 'Usage: build_mips_app.sh [--firmware]' >&2; exit 2; }
mkdir -p "artifacts/full-app/$variant"
python3 scripts/write_mips_args.py "$variant"
python3 scripts/configure_outlet.py
[ "$(git -C sources/connectedhomeip/third_party/mbedtls/repo rev-parse HEAD)" = 6a58fa8122c9bb8ee1644733d21b5677c93f1169 ]
docker run --rm --network none -e ZAP_INSTALL_PATH=/zap -e BUILD_VARIANT="$variant" \
 -e STAGING_DIR=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl \
 -v "$PWD/sources/openwrt-sdk/staging_dir:/opt/staging:ro" \
 -v "$PWD/sources/connectedhomeip:/sdk" -v "$PWD/sources/zap-linux-arm64:/zap:ro" \
 -v "$PWD/toolchains:/work/toolchains:ro" \
 -v "$PWD/artifacts/full-app:/out" wemo-matter-app-builder:bookworm sh -ec '
 python3 scripts/tools/zap/generate.py examples/lighting-app/lighting-common/lighting-app.zap --no-prettify-output
 cd examples/lighting-app/linux
 gn gen /out/$BUILD_VARIANT
 ninja -C /out/$BUILD_VARIANT -j8 chip-lighting-app
 "$STAGING_DIR/bin/mipsel-openwrt-linux-readelf" -h -A /out/$BUILD_VARIANT/chip-lighting-app > /out/$BUILD_VARIANT/elf-abi.txt
 grep -q "FP ABI: Soft float" /out/$BUILD_VARIANT/elf-abi.txt
 grep -q "mips32r2" /out/$BUILD_VARIANT/elf-abi.txt
 "$STAGING_DIR/bin/mipsel-openwrt-linux-readelf" -l /out/$BUILD_VARIANT/chip-lighting-app > /out/$BUILD_VARIANT/elf-segments.txt
 if grep -q INTERP /out/$BUILD_VARIANT/elf-segments.txt; then echo "Unexpected dynamic interpreter"; exit 1; fi
 echo "PASS: full app is static MIPS32r2 soft-float"
 '
