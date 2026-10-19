#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
docker run --rm --network none -v "$PWD/artifacts/kernel-board:/out" \
 -v "$PWD/sources/snsv2-11420:/vendor:ro" wemo-matter-board-builder:bookworm sh -ec '
 mipsel-linux-gnu-objcopy -O binary -R .reginfo -R .note -R .comment -R .mdebug -R .MIPS.abiflags -S /out/vmlinux /out/kernel.raw
 dtc -I dts -O dtb -i /vendor/target/linux/ramips/dts -o /out/wemo.dtb /vendor/target/linux/ramips/dts/MT7628snsv2.dts
 '
python3 scripts/package_board_kernel.py
