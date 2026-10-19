#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p artifacts/prototype
c++ -std=c++20 -Wall -Wextra -Werror prototype/test_relay.cpp -o artifacts/prototype/test-native
artifacts/prototype/test-native
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp \
  -v "$PWD/prototype:/work/prototype:ro" -v "$PWD/artifacts/prototype:/out" \
  wemo-matter-offline-tests:bookworm sh -ec '
    mipsel-linux-gnu-g++ --version | head -1
    mipsel-linux-gnu-g++ -std=c++20 -Os -Wall -Wextra -Werror -static -march=mips32r2 -mabi=32 prototype/test_relay.cpp -o /out/test-mipsel
    mipsel-linux-gnu-readelf -h /out/test-mipsel
    mipsel-linux-gnu-readelf -A /out/test-mipsel
    ulimit -c 0
    status=0
    qemu-mipsel -cpu 24KEc /out/test-mipsel || status=$?
    echo "24KEc compatibility probe exit: $status (132 = illegal instruction; incompatible runtime)"
    if [ "$status" != 0 ] && [ "$status" != 132 ]; then exit "$status"; fi
    echo "Functional test on FPU-equipped 24Kf; this is NOT the Wemo CPU:"
    qemu-mipsel -cpu 24Kf /out/test-mipsel
  '
