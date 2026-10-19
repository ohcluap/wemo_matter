#!/usr/bin/env python3
"""Prepare pinned vendor kernel sources offline, without any device access."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
vendor = ROOT / 'sources/snsv2-11420'
archives = {'linux-3.18.27.tar.xz': 'ac9d2cd940e01cb2a659831fde4976e60d0241b0374026ed2ed7036d07039f06',
            'busybox-1.23.2.tar.bz2': '05a6f9e21aad8c098e388ae77de7b2361941afa7157ef74216703395b14e319a'}
for name, expected in archives.items():
    path = ROOT / 'artifacts' / name
    assert hashlib.file_digest(path.open('rb'), 'sha256').hexdigest() == expected
    destination = ROOT / 'sources' / ('linux-3.18.27-base' if name.startswith('linux') else 'busybox-1.23.2')
    if not destination.exists():
        destination.mkdir()
        subprocess.run(['tar', '-xf', str(path), '-C', str(destination), '--strip-components', '1'], check=True)
board = ROOT / 'sources/linux-3.18.27-wemo'
ready = board / '.wemo-vendor-patches-ready'
if board.exists() and not ready.exists():
    raise RuntimeError('Incomplete board source preparation; do not reuse an unverified partial tree')
if not board.exists():
    shutil.copytree(ROOT / 'sources/linux-3.18.27-base', board, symlinks=True)
    for directory in ('generic', 'ramips'):
        shutil.copytree(vendor / f'target/linux/{directory}/files', board, dirs_exist_ok=True, symlinks=True)
    records = []
    for directory in ('generic', 'ramips'):
        for patch in sorted((vendor / f'target/linux/{directory}/patches-3.18').glob('*.patch')):
            result = subprocess.run(['patch', '-p1', '--batch', '--forward', '-i', str(patch)], cwd=board,
                                    capture_output=True, text=True)
            with (ROOT / 'artifacts/board-patches.log').open('a') as log:
                log.write(str(patch.relative_to(ROOT)) + '\n' + result.stdout + result.stderr)
            if result.returncode:
                raise RuntimeError(f'Patch failed: {patch.name}; remove only the incomplete board tree before retrying')
            records.append({'path': str(patch.relative_to(ROOT)), 'sha256': hashlib.sha256(patch.read_bytes()).hexdigest()})
    (ROOT / 'research/board-patch-inputs.json').write_text(json.dumps({'archives': archives, 'patches': records}, indent=2)+'\n')
    ready.write_text('SNSV2 11420 generic + ramips patch series applied\n')
print('Prepared pinned board and emulator kernel sources')
