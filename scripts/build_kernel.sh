#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
variant=${1:-malta}
case "$variant" in malta|board) ;; *) exit 2;; esac
mkdir -p "artifacts/kernel-$variant"
docker run --rm --network none -e VARIANT="$variant" \
 -e STAGING_DIR=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl \
 -v "$PWD/sources/openwrt-sdk/staging_dir:/opt/staging:ro" \
 -v "$PWD/sources/linux-3.18.27-base:/linux-base" \
 -v "$PWD/sources/linux-3.18.27-wemo:/linux-board" \
 -v "$PWD/sources/snsv2-11420:/vendor:ro" \
 -v "$PWD/scripts:/scripts:ro" -v "$PWD/artifacts/kernel-$variant:/out" \
 wemo-matter-board-builder:bookworm sh -ec '
 export PATH="$STAGING_DIR/bin:$PATH"
 source=/linux-base
 if [ "$VARIANT" = board ]; then source=/linux-board; fi
 python3 /scripts/configure_kernel.py "$source" "$VARIANT"
 make -C "$source" O=/out ARCH=mips CROSS_COMPILE=mipsel-linux-gnu- HOSTCFLAGS="-O2 -fcommon" olddefconfig
 targets=vmlinux
 if [ "$VARIANT" = board ]; then targets="vmlinux modules"; fi
 make -C "$source" O=/out ARCH=mips CROSS_COMPILE=mipsel-linux-gnu- HOSTCFLAGS="-O2 -fcommon" KCFLAGS="-fcommon -fno-pie -Wno-error=attribute-alias -Wa,-mno-fix-loongson3-llsc" KAFLAGS="-Wa,-mno-fix-loongson3-llsc" -j6 $targets
 '
