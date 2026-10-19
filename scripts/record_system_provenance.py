#!/usr/bin/env python3
"""Refresh existing system provenance only after matching successful guest tests."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    path = ROOT / 'research/system-build-provenance.json'
    report = json.loads(path.read_text())
    guest = json.loads((ROOT / 'research/system-boot-results.json').read_text())
    build = json.loads((ROOT / 'research/system-image-build.json').read_text())
    assert guest['passed'] and not guest['physical_wemo_touched']
    for relative, digest in guest['artifacts'].items():
        assert sha(ROOT / relative) == digest, 'Guest result does not match current build'
    assert sha(ROOT / build['path']) == build['image_sha256']
    assert sha(ROOT / 'artifacts/system-image/board-rootfs.squashfs') == build['rootfs_sha256']
    assert sha(ROOT / 'artifacts/kernel-board/wemo-kernel.uImage') == build['kernel_sha256']
    paths = [entry['path'] for entry in report['outputs']]
    paths += ['artifacts/wifi/wpa_passphrase', 'artifacts/wifi/wemo-wifi-provision',
              'artifacts/kernel-board/wemo-kernel.uImage', build['path']]
    # Keep only the currently selected candidate in the manifest.
    paths = [p for p in paths if 'wemo-unsigned-development-' not in p or p == build['path']]
    report['outputs'] = [{'path': p, 'bytes': (ROOT / p).stat().st_size, 'sha256': sha(ROOT / p)}
                         for p in dict.fromkeys(paths)]
    report['successful_guest_run'] = guest['run_id']
    report['provisioning_inputs'] = [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p)} for p in [
        ROOT / 'port/wifi_provision.c', ROOT / 'scripts/build_wifi_provision.sh',
        ROOT / 'scripts/assemble_rootfs.py', ROOT / 'firmware/rootfs/usr/lib/wemo/guest-tests.sh',
        *[ROOT / 'sources/wpa_supplicant-2.11/src' / relative for relative in (
            'crypto/sha1-pbkdf2.c', 'crypto/sha1.c', 'crypto/sha1-internal.c', 'utils/common.c')]]]
    path.write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: provenance matches successful guest and selected candidate')


if __name__ == '__main__':
    main()
