#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
variant=${1:-malta}
case "$variant" in malta|board) ;; *) exit 2;; esac
python3 scripts/prepare_forensic_kernel.py
mkdir -p artifacts/forensic "artifacts/forensic/kernel-$variant"
docker run --rm --network none -e STAGING_DIR=/opt/staging/toolchain-mipsel_24kc_gcc-13.3.0_musl \
 -v "$PWD/sources/openwrt-sdk/staging_dir:/opt/staging:ro" -v "$PWD/port:/port:ro" \
 -v "$PWD/artifacts/forensic:/out" wemo-matter-board-builder:bookworm sh -ec '
 export PATH="$STAGING_DIR/bin:$PATH"
 mipsel-openwrt-linux-gcc -Os -Wall -Wextra -Werror -static -march=24kec -msoft-float -mabi=32 /port/forensic_init.c -o /out/init
 mipsel-openwrt-linux-strip --strip-all /out/init
 '
python3 scripts/prepare_forensic_initramfs.py
docker run --rm --network none -e VARIANT="$variant" \
 -v "$PWD/sources/linux-3.18.27-forensic:/linux" \
 -v "$PWD/sources/snsv2-11420:/vendor:ro" -v "$PWD/scripts:/scripts:ro" \
 -v "$PWD/artifacts/forensic:/inputs:ro" -v "$PWD/artifacts/forensic/kernel-$variant:/out" \
 wemo-matter-board-builder:bookworm sh -ec '
 python3 /scripts/configure_forensic_kernel.py /linux "$VARIANT"
 make -C /linux O=/out ARCH=mips CROSS_COMPILE=mipsel-linux-gnu- HOSTCFLAGS="-O2 -fcommon" olddefconfig
 make -C /linux O=/out ARCH=mips CROSS_COMPILE=mipsel-linux-gnu- HOSTCFLAGS="-O2 -fcommon" KCFLAGS="-fcommon -fno-pie -Wno-error=attribute-alias -Wa,-mno-fix-loongson3-llsc" KAFLAGS="-Wa,-mno-fix-loongson3-llsc" -j6 vmlinux
 '
