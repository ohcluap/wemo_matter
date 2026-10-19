#!/usr/bin/env python3
"""Assess offline payloads against the older vendor DTS; never queries a device."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'sources/snsv2-11420'


def read_layout(name):
    path = VENDOR / 'target/linux/ramips/dts' / name
    source = path.read_text()
    memory = re.search(r'memory@0\s*{.*?reg\s*=\s*<0x0\s+(0x[0-9a-f]+)>', source, re.S)
    assert memory, 'Unrecognized vendor memory definition'
    partitions = {}
    for block in re.findall(r'partition@[^\s]+\s*{([^}]+)}', source):
        label = re.search(r'label\s*=\s*"([^"]+)"', block)
        reg = re.search(r'reg\s*=\s*<(0x[0-9a-f]+)\s+(0x[0-9a-f]+)>', block)
        assert label and reg, 'Unrecognized vendor partition definition'
        partitions[label[1]] = {'offset': int(reg[1], 16), 'bytes': int(reg[2], 16)}
    return {'source': str(path.relative_to(ROOT)), 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'ram_bytes': int(memory[1], 16), 'partitions': partitions}


def main():
    layouts = {name: read_layout(name) for name in ('MT7628snsv2.dts', 'MT7628snsv2-8M.dts')}
    payload = ROOT / 'artifacts/firmware/rootfs-payload.squashfs'
    app = ROOT / 'artifacts/full-app/firmware/wemo-matter-outlet'
    for relative in ('usr/bin/wemo-matter-outlet', 'etc/init.d/wemo-matter', 'etc/config/wemo-matter'):
        staged = ROOT / 'artifacts/firmware/rootfs-payload' / relative
        restored = ROOT / 'artifacts/firmware/roundtrip' / relative
        assert staged.read_bytes() == restored.read_bytes(), 'Payload roundtrip bytes differ'
    primary = layouts['MT7628snsv2.dts']['partitions']
    budget = min(primary[name]['bytes'] for name in ('rootfs_1', 'rootfs_2'))
    summary = {'evidence_scope': 'Vendor SNSV2 11420 source; installed 11565 and physical layout unconfirmed',
               'layouts': layouts,
               'conservative_rootfs_slot_bytes': budget,
               'vendor_generated_image_bytes': 7424 * 1024,
               'vendor_kernel_region_bytes': 0x180000,
               'payload': {'path': str(payload.relative_to(ROOT)), 'bytes': payload.stat().st_size,
                           'sha256': hashlib.sha256(payload.read_bytes()).hexdigest()},
               'stripped_app': {'bytes': app.stat().st_size,
                                'sha256': hashlib.sha256(app.read_bytes()).hexdigest()},
               'payload_alone_fits_rootfs_slot': payload.stat().st_size <= budget,
               'stripped_app_fits_writable_overlay': app.stat().st_size <= primary['rootfs_data']['bytes'],
               'complete_firmware_fit': 'unknown: no matching kernel or complete rootfs',
               'installable': False,
               'firmware_profile': {
                   'sdk_commit': '3bcdd56ba54fb88b2afb4bfef575014671df7aa7',
                   'gn_args': (ROOT / 'artifacts/full-app/firmware/args.gn').read_text(),
                   'state_directory': '/etc/wemo-matter/state',
                   'relay_backend': 'simulated', 'service_enabled_by_default': False,
                   'squashfs_roundtrip_verified_by_build_script': True,
                   'unstripped_app_sha256': hashlib.sha256((ROOT / 'artifacts/full-app/firmware/chip-lighting-app').read_bytes()).hexdigest()
               },
               'remaining_requirements': ['Confirm exact board/RAM/partition map', 'Acquire matching firmware/recovery evidence',
                                         'Validate kernel 3.18 and Wi-Fi behavior', 'Implement and verify relay/button GPIO backend',
                                         'Integrate complete rootfs and kernel within slot limits',
                                         'Production device identity and network provisioning', 'Establish authorized update/recovery path']}
    # The aggregate second slot in this old DTS overlaps rootfs_data; never treat
    # its full declared size as writable budget for an image.
    fw = primary['Firmware_2']
    data = primary['rootfs_data']
    summary['vendor_dts_aggregate_overlap_bytes'] = max(0, min(fw['offset'] + fw['bytes'], data['offset'] + data['bytes']) - max(fw['offset'], data['offset']))
    assert summary['payload_alone_fits_rootfs_slot'], 'Payload exceeds conservative rootfs slot capacity'
    (ROOT / 'research/hardware-fit.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('PASS: payload-only size/roundtrip; complete firmware fit remains unverified')


if __name__ == '__main__':
    main()
