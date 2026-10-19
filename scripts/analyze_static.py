#!/usr/bin/env python3
"""Collect selected static evidence without loading or executing vendor binaries."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct


def analyze(root):
    result = {'scope': 'Older SNSV2 11420 release; not installed 11565', 'files': []}
    product = root / 'package/belkin/WeMo_SNSV2/files'
    for path in sorted(product.rglob('*')):
        if not path.is_file():
            continue
        data = path.read_bytes()
        if data[:4] != b'\x7fELF':
            continue
        result['files'].append({
            'path': str(path.relative_to(root)), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(),
            'elf_class': data[4], 'elf_endianness': data[5],
            'elf_machine': struct.unpack('<H' if data[5] == 1 else '>H', data[18:20])[0],
            'selected_strings': sorted(set(s.decode('ascii') for s in re.findall(rb'[ -~]{6,}', data)
                if re.search(rb'telnetd|tftpd|dropbear|StartIperf|/tmp/[^ ]*\.sh|^system$|^popen$|^dlopen$|ld-uClibc', s)))
        })
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_root', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(analyze(args.source_root), indent=2) + '\n')
