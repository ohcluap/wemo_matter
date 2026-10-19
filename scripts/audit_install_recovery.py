#!/usr/bin/env python3
"""Offline range/evidence audit. Contains no device access or installation path.

All offsets describe the older SNSV2 11420 source, not measured hardware.
Even a passing range check never authorizes an installation.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'sources/snsv2-11420'
IMAGE_BYTES = 0x740000
ERASE_BYTES = 0x10000
SLOTS = {'A': (0x50000, 0x7b0000), 'B': (0x7c0000, 0xf00000)}
PROTECTED = {
    'bootloader/environment/factory': (0, 0x50000),
    'homekit': (0x7b0000, 0x7c0000),
    'shared-overlay/settings/identities': (0xf00000, 0x1000000),
}


def overlap(a, b):
    return max(a[0], b[0]) < min(a[1], b[1])


def range_check(slot, size):
    if slot not in SLOTS or not isinstance(size, int) or size <= 0:
        raise ValueError('Invalid slot or image length')
    start, limit = SLOTS[slot]
    end = start + ((size + ERASE_BYTES - 1) // ERASE_BYTES) * ERASE_BYTES
    if end > limit or any(overlap((start, end), r) for r in PROTECTED.values()):
        raise ValueError('Write/erase envelope crosses the conservative slot boundary')
    return {'start': start, 'erase_end': end, 'limit': limit, 'bytes': size}


def inactive_slot(bootstate):
    # More conservative than the stock updater: never overwrite the fallback
    # during an unconfirmed trial and never default an unknown state to A.
    if type(bootstate) is not int or bootstate not in (0, 2):
        raise ValueError('Unknown or unconfirmed boot state; no target can be selected')
    return 'B' if bootstate == 0 else 'A'


def evidence(relative, phrases):
    path = VENDOR / relative
    data = path.read_bytes()
    lines = data.decode(errors='replace').splitlines()
    matches = {}
    for phrase in phrases:
        found = [i + 1 for i, line in enumerate(lines) if phrase in line]
        if not found:
            raise ValueError(f'Missing expected source evidence: {relative}: {phrase}')
        matches[phrase] = found
    return {'path': relative, 'sha256': hashlib.sha256(data).hexdigest(), 'lines': matches}


def main():
    files = 'package/belkin/WeMo_SNSV2/files/'
    sources = [
        evidence(files + 'sbin/firmware_update.sh', [
            'gpg --verify', 'Signature test failed.', 'verify product name',
            'Invalid Boot partition', 'mtd write $FIRMWARE_NAME $mtd_other',
            'fw_setenv bootstate $newstate', 'fw_setenv bootpart $newpart']),
        evidence(files + 'sbin/update_test.sh', [
            'sleep 60', '/tmp/*.starting', 'alternate partition by uboot',
            'fw_setenv bootstate 0', 'fw_setenv bootstate 2']),
        evidence(files + 'sbin/go_dummy.sh', ['fw_setenv bootstate 2', 'fw_setenv bootstate 0']),
        evidence('target/linux/ramips/mt7628/WemoSNSV2/base-files/etc/init.d/boot', [
            'grep -i Uboot_env /proc/mtd', '0x0 0x1000 00010000',
            'checkboot=', '/sbin/update_test.sh 0 &']),
    ]
    dts_path = 'target/linux/ramips/dts/MT7628snsv2.dts'
    text = (VENDOR / dts_path).read_text()
    partitions = {name: (int(start, 16), int(start, 16) + int(length, 16))
                  for name, start, length in re.findall(
                      r'label\s*=\s*"([^"]+)";\s*reg\s*=\s*<(0x[0-9a-f]+)\s+(0x[0-9a-f]+)>;', text)}
    assert partitions['kernel_1'][0] == SLOTS['A'][0]
    assert partitions['rootfs_1'][1] == SLOTS['A'][1]
    assert partitions['kernel_2'][0] == SLOTS['B'][0]
    assert partitions['rootfs_2'][1] == SLOTS['B'][1]
    sources.append(evidence(dts_path, ['label = "Firmware_2"', 'label = "rootfs_data"']))
    build = json.loads((ROOT / 'research/system-image-build.json').read_text())
    image = ROOT / build['path']
    assert hashlib.sha256(image.read_bytes()).hexdigest() == build['image_sha256']
    assert image.stat().st_size == IMAGE_BYTES
    report = {
        'scope': 'Offline analysis of SNSV2 11420 sources; installed firmware 11565 differs',
        'physical_device_touched': False,
        'installation_allowed': False,
        'image_sha256': build['image_sha256'],
        'source_evidence': sources,
        'source_layout_only': True,
        'conservative_slot_checks': {s: range_check(s, image.stat().st_size) for s in SLOTS},
        'aggregate_B_overlap_shared_overlay_bytes': max(0, min(partitions['Firmware_2'][1],
            partitions['rootfs_data'][1]) - max(partitions['Firmware_2'][0], partitions['rootfs_data'][0])),
        'stock_update_states': {'0_or_1': 'write B, then bootstate=3', '2_or_3': 'write A, then bootstate=1',
                                'unknown': 'stock script defaults to A; unsafe to emulate'},
        'stock_health_commit': {'1': 0, '3': 2},
        'bootloader_rollback_emulated': False,
        'blockers': [
            'Exact physical model, flash geometry, partition map and bootloader not confirmed',
            'Candidate has no Belkin signature; stock updater is not an installation route',
            'No verified exact-device RAM boot or independent recovery transport',
            'No verified complete original flash backup or restore rehearsal',
            'MT7688 board boot, vendor radio ABI/calibration and physical relay remain untested',
            'Persistent flash overlay, production identity and Matter-managed Wi-Fi provisioning incomplete',
        ],
    }
    (ROOT / 'research/install-recovery-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: conservative offline ranges and source evidence; INSTALLATION REMAINS BLOCKED')


if __name__ == '__main__':
    main()
