#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
docker run --rm --network none -v "$PWD/artifacts/forensic:/out" \
 -v "$PWD/sources/snsv2-11420:/vendor:ro" -v "$PWD/port:/port:ro" \
 wemo-matter-board-builder:bookworm sh -ec '
 mipsel-linux-gnu-objcopy -O binary -R .reginfo -R .note -R .comment -R .mdebug -R .MIPS.abiflags -S /out/kernel-board/vmlinux /out/kernel-board/kernel.raw
 dtc -I dts -O dtb -i /vendor/target/linux/ramips/dts -o /out/forensic.dtb /port/forensic.dts
 dtc -I dtb -O dts -o /out/forensic-expanded.dts /out/forensic.dtb
 for variant in board malta; do
  mipsel-linux-gnu-nm -n /out/kernel-$variant/vmlinux > /out/kernel-$variant/symbols.txt
  for function in m25p80_write_reg m25p80_write m25p80_erase forensic_mtd_write forensic_mtd_erase; do
   mipsel-linux-gnu-objdump -d --disassemble=$function /out/kernel-$variant/vmlinux
  done > /out/kernel-$variant/deny-stubs.asm
 done
 '
python3 scripts/package_forensic_ram.py
