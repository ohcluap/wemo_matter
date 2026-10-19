#!/bin/sh
# Builds local integration artifacts only. Contains no upload or flash action.
set -eu
cd "$(dirname "$0")/.."
mkdir -p artifacts/firmware
# Recreate only the dedicated generated payload directory in a container.
docker run --rm --network none \
 -v "$PWD/sources/openwrt-sdk/staging_dir:/opt/staging:ro" \
 -v "$PWD/artifacts/full-app/firmware:/app" \
 -v "$PWD/firmware/openwrt/wemo-matter-outlet/files:/input:ro" \
 -v "$PWD/artifacts/firmware:/out" wemo-matter-app-builder:bookworm sh -ec '
 /opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl/bin/mipsel-openwrt-linux-strip --strip-all -o /app/wemo-matter-outlet /app/chip-lighting-app
 rm -rf /out/rootfs-payload /out/roundtrip
 mkdir -p /out/rootfs-payload/usr/bin /out/rootfs-payload/etc/init.d /out/rootfs-payload/etc/config /out/rootfs-payload/etc/wemo-matter/state
 chmod 700 /out/rootfs-payload/etc/wemo-matter/state
 install -m 755 /app/wemo-matter-outlet /out/rootfs-payload/usr/bin/wemo-matter-outlet
 install -m 755 /input/wemo-matter.init /out/rootfs-payload/etc/init.d/wemo-matter
 install -m 600 /input/wemo-matter.config /out/rootfs-payload/etc/config/wemo-matter
 /opt/staging/host/bin/mksquashfs4 /out/rootfs-payload /out/rootfs-payload.squashfs -noappend -all-root -comp xz -b 262144 -no-xattrs -processors 1 -mkfs-time 0 -all-time 0
 /opt/staging/host/bin/unsquashfs4 -d /out/roundtrip /out/rootfs-payload.squashfs
 cmp /out/rootfs-payload/usr/bin/wemo-matter-outlet /out/roundtrip/usr/bin/wemo-matter-outlet
 cmp /out/rootfs-payload/etc/init.d/wemo-matter /out/roundtrip/etc/init.d/wemo-matter
 cmp /out/rootfs-payload/etc/config/wemo-matter /out/roundtrip/etc/config/wemo-matter
 '
python3 scripts/assess_fit.py
