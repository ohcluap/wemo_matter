#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p artifacts/full-app
python3 scripts/configure_outlet.py
[ "$(git -C sources/connectedhomeip/third_party/mbedtls/repo rev-parse HEAD)" = 6a58fa8122c9bb8ee1644733d21b5677c93f1169 ]
docker run --rm --network none -e ZAP_INSTALL_PATH=/zap \
 -e STAGING_DIR=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl \
 -v "$PWD/sources/openwrt-sdk/staging_dir:/opt/staging:ro" \
 -v "$PWD/sources/connectedhomeip:/sdk" -v "$PWD/sources/zap-linux-arm64:/zap:ro" \
 -v "$PWD/toolchains:/work/toolchains:ro" \
 -v "$PWD/artifacts/full-app:/out" wemo-matter-app-builder:bookworm sh -ec '
 python3 scripts/tools/zap/generate.py examples/lighting-app/lighting-common/lighting-app.zap --no-prettify-output
 cd examples/lighting-app/linux
 gn gen /out/mips --args="target_os=\"linux\" target_cpu=\"mipsel\" custom_toolchain=\"custom\" target_cc=\"$STAGING_DIR/bin/mipsel-openwrt-linux-gcc\" target_cxx=\"$STAGING_DIR/bin/mipsel-openwrt-linux-g++\" target_ar=\"$STAGING_DIR/bin/mipsel-openwrt-linux-ar\" target_cflags=[\"-march=24kec\",\"-msoft-float\",\"-mabi=32\"] enable_pie=false target_ldflags=[\"-static\",\"-specs=/work/toolchains/mips-static.specs\",\"-march=24kec\",\"-msoft-float\",\"-mabi=32\"] chip_crypto=\"mbedtls\" is_debug=false chip_support_thread_meshcop=false symbol_level=0 matter_enable_tracing_support=false is_clang=false chip_inet_config_enable_ipv4=true chip_config_network_layer_ble=false chip_enable_wifi=false chip_enable_thread=false chip_mdns=\"minimal\""
 ninja -C /out/mips -j8 chip-lighting-app
 "$STAGING_DIR/bin/mipsel-openwrt-linux-readelf" -h -A /out/mips/chip-lighting-app > /out/mips/elf-abi.txt
 grep -q "FP ABI: Soft float" /out/mips/elf-abi.txt
 grep -q "mips32r2" /out/mips/elf-abi.txt
 "$STAGING_DIR/bin/mipsel-openwrt-linux-readelf" -l /out/mips/chip-lighting-app > /out/mips/elf-segments.txt
 if grep -q INTERP /out/mips/elf-segments.txt; then echo "Unexpected dynamic interpreter"; exit 1; fi
 echo "PASS: full app is static MIPS32r2 soft-float"
 '
