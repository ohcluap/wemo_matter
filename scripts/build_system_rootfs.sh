#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
# Refresh the stripped firmware app, including its value-file backend.
scripts/build_firmware_payload.sh > artifacts/firmware-payload-build.log 2>&1
python3 scripts/assemble_rootfs.py
docker run --rm --network none \
 -v "$PWD/sources/openwrt-sdk/staging_dir:/opt/staging:ro" \
 -v "$PWD/artifacts/system-image:/out" wemo-matter-board-builder:bookworm sh -ec '
 /opt/staging/host/bin/mksquashfs4 /out/board-rootfs /out/board-rootfs.squashfs -noappend -all-root -comp xz -b 262144 -no-xattrs -processors 1 -mkfs-time 0 -all-time 0 -p "dev/console c 600 0 0 5 1"
 '
