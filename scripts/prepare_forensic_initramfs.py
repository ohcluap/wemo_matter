#!/usr/bin/env python3
"""Construct a tiny initramfs with one static PID 1 and a serial console node."""
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / 'artifacts/forensic'
folder.mkdir(exist_ok=True)
output = bytearray()


def entry(name, mode, data=b'', major=0, minor=0):
    values = [1, mode, 0, 0, 1, 0, len(data), 0, 0, major, minor, len(name.encode())+1, 0]
    output.extend(b'070701' + ''.join(f'{v:08x}' for v in values).encode())
    output.extend(name.encode() + b'\0'); output.extend(b'\0' * (-len(output) % 4))
    output.extend(data); output.extend(b'\0' * (-len(output) % 4))


for name in ('.', 'dev', 'proc'):
    entry(name, stat.S_IFDIR | 0o555)
entry('dev/console', stat.S_IFCHR | 0o600, major=5, minor=1)
entry('init', stat.S_IFREG | 0o500, (folder/'init').read_bytes())
entry('TRAILER!!!', 0)
(folder/'initramfs.cpio').write_bytes(output)
print('Built identification-only initramfs; no shell, services or device tools')
