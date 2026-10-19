import importlib.util
from pathlib import Path
import struct
import unittest
import zlib

spec = importlib.util.spec_from_file_location('candidate', Path(__file__).resolve().parents[1] / 'scripts/assemble_candidate.py')
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


def fixture_kernel(arch=5):
    data = b'fixture only, not executable'
    header = bytearray(struct.pack('>7I4B32s', 0x27051956, 0, 0, len(data), 0x80000000,
                                   0x80000000, zlib.crc32(data), 5, arch, 2, 3, b'test fixture'))
    struct.pack_into('>I', header, 4, zlib.crc32(header))
    return bytes(header) + data


def fixture_rootfs():
    data = bytearray(96)
    struct.pack_into('<I', data, 0, 0x73717368)
    struct.pack_into('<I', data, 12, 262144)
    struct.pack_into('<H', data, 20, 4)
    struct.pack_into('<HH', data, 28, 4, 0)
    struct.pack_into('<Q', data, 40, len(data))
    return bytes(data)


class CandidateImageTests(unittest.TestCase):
    def test_offsets_and_erased_padding(self):
        kernel, rootfs = fixture_kernel(), fixture_rootfs()
        image = candidate.assemble(kernel, rootfs)
        self.assertEqual(len(image), 0x740000)
        self.assertEqual(image[:len(kernel)], kernel)
        self.assertEqual(image[len(kernel):candidate.KERNEL_REGION], b'\xff' * (candidate.KERNEL_REGION - len(kernel)))
        self.assertEqual(image[candidate.KERNEL_REGION:candidate.KERNEL_REGION + len(rootfs)], rootfs)

    def test_reject_corrupt_or_wrong_kernel(self):
        valid = fixture_kernel()
        for kernel in (valid[:-1], valid[:-1] + b'X', fixture_kernel(arch=2), b'\x00' * 64,
                       b'\x00' * (candidate.KERNEL_REGION + 1)):
            with self.subTest(length=len(kernel)), self.assertRaises(ValueError):
                candidate.assemble(kernel, fixture_rootfs())

    def test_reject_rootfs_overflow_and_incompatible_format(self):
        rootfs = fixture_rootfs()
        bad_compression = bytearray(rootfs)
        struct.pack_into('<H', bad_compression, 20, 6)
        truncated = bytearray(rootfs)
        struct.pack_into('<Q', truncated, 40, 4096)
        for invalid in (rootfs + b'\x00' * candidate.ROOTFS_REGION, bytes(bad_compression), bytes(truncated), b''):
            with self.subTest(length=len(invalid)), self.assertRaises(ValueError):
                candidate.assemble(fixture_kernel(), invalid)
