#!/bin/sh
# Downloads build inputs only. Does not contact or modify a Wemo.
set -eu
cd "$(dirname "$0")/.."
mkdir -p artifacts sources
archive=artifacts/openwrt-sdk.tar.zst
url=https://downloads.openwrt.org/releases/24.10.4/targets/ramips/mt76x8/openwrt-sdk-24.10.4-ramips-mt76x8_gcc-13.3.0_musl.Linux-x86_64.tar.zst
if [ ! -f "$archive" ]; then curl --fail --location "$url" --output "$archive"; fi
python3 - <<'PY'
import hashlib
from pathlib import Path
path = Path('artifacts/openwrt-sdk.tar.zst')
h = hashlib.sha256()
with path.open('rb') as stream:
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        h.update(block)
assert h.hexdigest() == '036230a0197b586459565d0e349c7d4ee66c92d111991d874d63c66a6c0451a3', 'SDK checksum mismatch'
print('OpenWrt SDK checksum verified')
PY
if [ ! -d sources/openwrt-sdk ]; then
  mkdir sources/openwrt-sdk
  tar -xf "$archive" -C sources/openwrt-sdk --strip-components 1
fi
if [ ! -d sources/connectedhomeip ]; then
  git clone --depth 1 --filter=blob:none --sparse --branch v1.6.1.0 https://github.com/project-chip/connectedhomeip.git sources/connectedhomeip
fi
sdk_commit=$(git -C sources/connectedhomeip rev-parse HEAD)
[ "$sdk_commit" = 3bcdd56ba54fb88b2afb4bfef575014671df7aa7 ] || { echo 'Unexpected Matter SDK revision' >&2; exit 1; }
# Preserve an existing full SDK checkout used by the complete application.
if [ "$(git -C sources/connectedhomeip config --bool core.sparseCheckout || true)" = true ]; then
  git -C sources/connectedhomeip sparse-checkout add src/lib src/system src/ble src/inet src/crypto third_party/nlio third_party/mbedtls
fi
git -C sources/connectedhomeip submodule update --init --depth 1 third_party/nlio/repo third_party/mbedtls/repo
docker build --platform linux/amd64 -f toolchains/Dockerfile.musl-tests -t wemo-matter-musl-tests:bookworm .
