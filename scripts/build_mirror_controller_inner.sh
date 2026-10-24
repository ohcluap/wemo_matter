#!/bin/sh
set -eu
mkdir -p /sdk/build-output/controller
cp /work/toolchains/mirror-controller.gn /sdk/build-output/controller/args.gn
cd /sdk/examples/chip-tool
gn gen /sdk/build-output/controller
if ! ninja -C /sdk/build-output/controller -j6 chip-tool > /sdk/build-output/controller/build.log 2>&1; then
    tail -65 /sdk/build-output/controller/build.log
    exit 1
fi
strip -o /export/chip-tool /sdk/build-output/controller/chip-tool
cp /sdk/build-output/controller/build.log /export/controller-build.log
sha256sum /export/chip-tool
