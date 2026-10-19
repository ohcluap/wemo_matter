#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p artifacts/musl
[ "$(git -C sources/connectedhomeip rev-parse HEAD)" = 3bcdd56ba54fb88b2afb4bfef575014671df7aa7 ]
[ "$(git -C sources/connectedhomeip/third_party/nlio/repo rev-parse HEAD)" = 0e725502c2b17bb0a0c22ddd4bcaee9090c8fb5c ]
[ "$(git -C sources/connectedhomeip/third_party/mbedtls/repo rev-parse HEAD)" = 6a58fa8122c9bb8ee1644733d21b5677c93f1169 ]
# Both compiler and test execution are isolated from the LAN.
docker run --rm --platform linux/amd64 --network none --read-only --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp \
  -v "$PWD/sources/openwrt-sdk/staging_dir:/opt/staging:ro" \
  -v "$PWD/sources/connectedhomeip:/sdk:ro" \
  -v "$PWD/scripts:/work/scripts:ro" -v "$PWD/prototype:/work/prototype:ro" -v "$PWD/port:/work/port:ro" \
  -v "$PWD/artifacts/musl:/out" wemo-matter-musl-tests:bookworm sh -ec '
    ulimit -c 0
    export PATH=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl/bin:$PATH
    export STAGING_DIR=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl
    compiler=mipsel-openwrt-linux-g++
    $compiler --version | head -1
    $compiler -std=c++20 -fno-exceptions -fno-rtti -Os -static -march=24kec -msoft-float -mabi=32 -Wall -Wextra -Werror prototype/test_relay.cpp -o /out/test-relay
    mipsel-openwrt-linux-readelf -A /out/test-relay | head -18
    timeout 30 qemu-mipsel -cpu 24KEc /out/test-relay
    $compiler -std=c++20 -fno-exceptions -fno-rtti -Os -static -march=24kec -msoft-float -mabi=32 -pthread port/test_runtime.cpp -o /out/test-runtime
    timeout 30 qemu-mipsel -cpu 24KEc /out/test-runtime
    $compiler -std=c++20 -fno-exceptions -fno-rtti -Os -static -march=24kec -msoft-float -mabi=32 -ffunction-sections -fdata-sections -Wl,--gc-sections \
      -include /work/port/OfflineConfig.h -I/sdk/src -I/sdk/third_party/nlio/repo/include \
      /work/port/test_matter_tlv.cpp /sdk/src/lib/core/TLVReader.cpp /sdk/src/lib/core/TLVWriter.cpp /sdk/src/lib/core/TLVTags.cpp \
      /sdk/src/lib/support/BufferWriter.cpp /sdk/src/lib/support/utf8.cpp \
      -o /out/test-matter-tlv
    timeout 30 qemu-mipsel -cpu 24KEc /out/test-matter-tlv
    sh /work/scripts/build_crypto_inner.sh
    for executable in /out/test-relay /out/test-runtime /out/test-matter-tlv /out/test-matter-crypto; do
      mipsel-openwrt-linux-readelf -A "$executable" > /tmp/abi.txt
      grep -q "FP ABI: Soft float" /tmp/abi.txt
      mipsel-openwrt-linux-readelf -l "$executable" > /tmp/segments.txt
      if grep -q INTERP /tmp/segments.txt; then echo "Unexpected dynamic interpreter"; exit 1; fi
      echo "PASS: static soft-float ELF: $(basename "$executable")"
    done
  '
