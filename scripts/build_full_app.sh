#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p artifacts/full-app
python3 scripts/configure_outlet.py
docker run --rm --network none -e ZAP_INSTALL_PATH=/zap \
 -v "$PWD/sources/connectedhomeip:/sdk" -v "$PWD/sources/zap-linux-arm64:/zap:ro" \
 -v "$PWD/artifacts/full-app:/out" wemo-matter-app-builder:bookworm sh -ec '
 python3 scripts/tools/zap/generate.py examples/lighting-app/lighting-common/lighting-app.zap --no-prettify-output
 cd examples/lighting-app/linux
 gn gen /out/native --args="is_debug=false chip_support_thread_meshcop=false symbol_level=0 matter_enable_tracing_support=false is_clang=false chip_inet_config_enable_ipv4=true chip_config_network_layer_ble=false chip_enable_wifi=false chip_enable_thread=false chip_mdns=\"minimal\""
 ninja -C /out/native -j4 chip-lighting-app
 '
