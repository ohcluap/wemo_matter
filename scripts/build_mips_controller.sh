#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p artifacts/full-app/mips-controller
cp toolchains/mips-app.gn artifacts/full-app/mips-controller/args.gn
docker run --rm --network none -e ZAP_INSTALL_PATH=/zap \
 -e STAGING_DIR=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl \
 -v "$PWD/sources/openwrt-sdk/staging_dir:/opt/staging:ro" \
 -v "$PWD/sources/connectedhomeip:/sdk" -v "$PWD/sources/zap-linux-arm64:/zap:ro" \
 -v "$PWD/toolchains:/work/toolchains:ro" -v "$PWD/artifacts/full-app:/out" \
 wemo-matter-app-builder:bookworm sh -ec '
 cd examples/chip-tool
 gn gen /out/mips-controller
 ninja -C /out/mips-controller -j6 chip-tool
 "$STAGING_DIR/bin/mipsel-openwrt-linux-strip" --strip-all -o /out/mips-controller/wemo-chip-tool /out/mips-controller/chip-tool
 '
