"""Offline MIPS decoder checks in a bounded temporary filesystem, never a device."""
import hashlib
import json
from pathlib import Path
import subprocess
import argparse
import lzma

parser = argparse.ArgumentParser()
parser.add_argument('--minimal', action='store_true')
args = parser.parse_args()

root = Path('/input')
decoder = root / ('ram-unpack/wemo-unpack' if args.minimal else 'ram-unpack/wemo-xzdec')
compressed = root / 'ram-unpack/app-dict-1MiB.xz'
original = root / 'wemo-matter-outlet-compact'
report = {'physical_device_tested': False, 'tests': [], 'passed': False}


def decode(path, label, success):
    output = Path('/tmp') / (label + '.out')
    with output.open('wb') as stream:
        result = subprocess.run(['qemu-mipsel', '-cpu', '24KEc', str(decoder), str(path)],
                                stdout=stream, stderr=subprocess.PIPE, timeout=30)
    if success:
        assert result.returncode == 0, result.stderr
        assert hashlib.sha256(output.read_bytes()).digest() == hashlib.sha256(original.read_bytes()).digest()
    else:
        assert result.returncode != 0, 'Invalid input was accepted'
    if args.minimal:
        assert output.stat().st_size <= 2 * 1024 * 1024, 'Output bound exceeded'
    report['tests'].append({'name': label, 'returncode': result.returncode,
                            'output_bytes': output.stat().st_size,
                            'stderr': result.stderr.decode(errors='replace')})
    output.unlink()


decode(compressed, 'valid-exact-executable', True)
decode(root / 'compact/app.xz', 'reject-64MiB-dictionary', False)
data = compressed.read_bytes()
damaged = Path('/tmp/damaged.xz')
damaged.write_bytes(data[:-16])
decode(damaged, 'reject-truncated-stream', False)
data = bytearray(data)
data[len(data)//2] ^= 0x80
damaged.write_bytes(data)
decode(damaged, 'reject-corrupted-stream', False)
if args.minimal:
    for label, payload in [
        ('reject-trailing-byte', compressed.read_bytes() + b'X'),
        ('reject-second-stream', compressed.read_bytes() * 2),
        ('reject-empty-input', b''),
        ('reject-output-over-limit', lzma.compress(b'A' * (2 * 1024 * 1024 + 1),
            check=lzma.CHECK_CRC32, filters=[{'id': lzma.FILTER_LZMA2, 'dict_size': 1024 * 1024}])),
        ('reject-no-integrity-check', lzma.compress(b'A', check=lzma.CHECK_NONE,
            filters=[{'id': lzma.FILTER_LZMA2, 'dict_size': 1024 * 1024}])),
    ]:
        damaged.write_bytes(payload)
        decode(damaged, label, False)
    with open('/dev/full', 'wb', buffering=0) as full:
        failure = subprocess.run(['qemu-mipsel', '-cpu', '24KEc', str(decoder), str(compressed)],
                                 stdout=full, stderr=subprocess.PIPE, timeout=30)
    assert failure.returncode != 0, 'Output failure was ignored'
    report['tests'].append({'name': 'reject-output-write-failure', 'returncode': failure.returncode})
report['decoder_bytes'] = decoder.stat().st_size
report['decoder_sha256'] = hashlib.sha256(decoder.read_bytes()).hexdigest()
report['package_bytes'] = decoder.stat().st_size + compressed.stat().st_size
report['cgroup_memory_peak_bytes'] = int(Path('/sys/fs/cgroup/memory.peak').read_text())
report['cgroup_memory_limit_bytes'] = int(Path('/sys/fs/cgroup/memory.max').read_text())
report['passed'] = True
report['limitations'] = [
    'QEMU user emulation on modern Linux, not exact stock kernel or actual hardware.',
    'Decoder may produce partial output before rejecting bad data; no output was executed.',
    'A future loader must validate completion and executable hash before execution.',
    'Size excludes startup code, pairing state, filesystem overhead and reserve.',
    'An archived decoder is an experiment, not a security-reviewed production loader.',
]
Path('/export/' + ('tiny-decoder-test.json' if args.minimal else 'decoder-test.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
