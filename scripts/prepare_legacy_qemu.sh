#!/bin/sh
# Fetch/build a test emulator. No Wemo communication.
set -eu
cd "$(dirname "$0")/.."
archive=artifacts/qemu-7.2.22.tar.xz
if [ ! -f "$archive" ]; then
  curl --fail --location https://download.qemu.org/qemu-7.2.22.tar.xz --output "$archive"
fi
python3 - <<'PY'
import hashlib
from pathlib import Path
assert hashlib.file_digest(Path('artifacts/qemu-7.2.22.tar.xz').open('rb'), 'sha256').hexdigest() == 'c74b398c1950526686cb7784e23bd8945ef138b0e6541ba0495015aad3ac9532'
PY
if [ ! -d sources/qemu-7.2.22 ]; then
  mkdir sources/qemu-7.2.22
  tar -xf "$archive" -C sources/qemu-7.2.22 --strip-components 1
fi
if ! rg -q WEMO_TEST_NO_TIME64 sources/qemu-7.2.22/linux-user/syscall.c; then
  patch -d sources/qemu-7.2.22 -p1 < port/qemu/no-time64.patch
fi
mkdir -p artifacts/qemu-legacy-build
docker run --rm --network none \
 -v "$PWD/sources/qemu-7.2.22:/qemu:ro" -v "$PWD/artifacts/qemu-legacy-build:/build" \
 -w /build wemo-matter-app-builder:bookworm sh -ec '
 /qemu/configure --target-list=mipsel-linux-user --disable-system --disable-docs --disable-tools --disable-guest-agent --disable-werror
 ninja -j8 qemu-mipsel
 '
