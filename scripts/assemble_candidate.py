#!/usr/bin/env python3
"""Assemble an unsigned offline image using the older vendor's layout.

Requires a real Linux/MIPS/LZMA uImage and complete XZ SquashFS. Header/size
validation does not establish board compatibility. Never contacts a device.
"""
import argparse
from pathlib import Path
import struct
import zlib

KERNEL_REGION = 0x180000
IMAGE_BYTES = 7424 * 1024
ROOTFS_REGION = IMAGE_BYTES - KERNEL_REGION


def assemble(kernel, rootfs):
    if len(kernel) < 64 or len(kernel) > KERNEL_REGION:
        raise ValueError('Kernel must include a uImage header and fit its 1.5 MiB region')
    header = bytearray(kernel[:64])
    magic, header_crc, _, size, load, entry, data_crc, os_id, arch, image_type, compression, _ = struct.unpack('>7I4B32s', header)
    struct.pack_into('>I', header, 4, 0)
    if magic != 0x27051956 or zlib.crc32(header) != header_crc:
        raise ValueError('Invalid uImage magic or header CRC')
    if size != len(kernel) - 64 or zlib.crc32(kernel[64:]) != data_crc:
        raise ValueError('Invalid uImage payload size or CRC')
    if (os_id, arch, image_type, compression) != (5, 5, 2, 3):
        raise ValueError('Expected Linux/MIPS/kernel/LZMA uImage')
    if (load, entry) != (0x80000000, 0x80000000):
        raise ValueError('Load/entry addresses differ from the inspected vendor recipe')
    if len(rootfs) < 96 or len(rootfs) > ROOTFS_REGION:
        raise ValueError('Rootfs must fit the conservative 5.75 MiB region')
    if struct.unpack_from('<I', rootfs)[0] != 0x73717368:
        raise ValueError('Expected little-endian SquashFS')
    if struct.unpack_from('<HH', rootfs, 28) != (4, 0):
        raise ValueError('Expected SquashFS 4.0')
    if struct.unpack_from('<H', rootfs, 20)[0] != 4 or struct.unpack_from('<I', rootfs, 12)[0] != 262144:
        raise ValueError('Expected vendor-compatible XZ compression and 256 KiB blocks')
    bytes_used = struct.unpack_from('<Q', rootfs, 40)[0]
    if not 96 <= bytes_used <= len(rootfs):
        raise ValueError('Invalid or truncated SquashFS bytes_used')
    return kernel.ljust(KERNEL_REGION, b'\xff') + rootfs.ljust(ROOTFS_REGION, b'\xff')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel', required=True, type=Path)
    parser.add_argument('--rootfs', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    image = assemble(args.kernel.read_bytes(), args.rootfs.read_bytes())
    # No overwrite of existing artifacts; no Belkin signature or update wrapper.
    with args.output.open('xb') as output:
        output.write(image)
    print('Created unsigned OFFLINE CANDIDATE; board compatibility and installability unverified')


if __name__ == '__main__':
    main()
