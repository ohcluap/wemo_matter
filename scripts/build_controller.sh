#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
docker run --rm --network none -e ZAP_INSTALL_PATH=/zap \
 -v "$PWD/sources/connectedhomeip:/sdk" -v "$PWD/sources/zap-linux-arm64:/zap:ro" \
 -v "$PWD/artifacts/full-app:/out" wemo-matter-app-builder:bookworm sh -ec '
 cd examples/chip-tool
 gn gen /out/controller --args="is_debug=false chip_support_thread_meshcop=false symbol_level=0 is_clang=false matter_enable_tracing_support=false chip_inet_config_enable_ipv4=true chip_config_network_layer_ble=false chip_mdns=\"minimal\""
 ninja -C /out/controller -j4 chip-tool
 '
