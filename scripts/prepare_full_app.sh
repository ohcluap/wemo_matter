#!/bin/sh
# Fetches SDK/build dependencies. Does not discover or contact home devices.
set -eu
cd "$(dirname "$0")/.."
mkdir -p artifacts sources
if [ ! -d sources/connectedhomeip ]; then
  git clone --depth 1 --filter=blob:none --branch v1.6.1.0 https://github.com/project-chip/connectedhomeip.git sources/connectedhomeip
fi
[ "$(git -C sources/connectedhomeip rev-parse HEAD)" = 3bcdd56ba54fb88b2afb4bfef575014671df7aa7 ]
git -C sources/connectedhomeip sparse-checkout disable
git -C sources/connectedhomeip submodule update --init --depth 1 \
  third_party/pigweed/repo third_party/nlassert/repo third_party/nlio/repo \
  third_party/jsoncpp/repo examples/common/QRCode/repo third_party/nanopb/repo \
  third_party/uriparser/repo third_party/editline/repo third_party/perfetto/repo \
  third_party/libwebsockets/repo third_party/mbedtls/repo
if [ ! -f artifacts/zap-linux-arm64.zip ]; then
  curl --fail --location https://github.com/project-chip/zap/releases/download/v2026.05.12-nightly/zap-linux-arm64.zip --output artifacts/zap-linux-arm64.zip
fi
python3 - <<'PY'
import hashlib
with open('artifacts/zap-linux-arm64.zip', 'rb') as source:
    digest = hashlib.file_digest(source, 'sha256').hexdigest()
assert digest == 'a6774a14a0fa957d8d830f6517140c3dd949531c1b1696fda0b52688c0566984', 'ZAP checksum mismatch'
PY
if [ ! -d sources/zap-linux-arm64 ]; then
  mkdir sources/zap-linux-arm64
  unzip -q artifacts/zap-linux-arm64.zip -d sources/zap-linux-arm64
fi
docker build -f toolchains/Dockerfile.matter-app -t wemo-matter-app-builder:bookworm .
