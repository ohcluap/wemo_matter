#!/usr/bin/env python3
"""Offline-only recovery evidence audit. No networking, device I/O or write plan."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'sources/snsv2-11420'


def layout(text):
    result = {}
    for name, offset, size in re.findall(
            r'label\s*=\s*"([^"]+)";\s*reg\s*=\s*<(0x[\da-f]+)\s+(0x[\da-f]+)>;', text):
        start, length = int(offset, 16), int(size, 16)
        if name in result or length <= 0:
            raise ValueError('Ambiguous or empty partition')
        result[name] = {'start': start, 'size': length, 'end': start + length}
    if not result:
        raise ValueError('No partition declarations found')
    return result


def overlaps(start, size, partitions, names):
    return {name: amount for name in names if (amount := max(0,
        min(start + size, partitions[name]['end']) - max(start, partitions[name]['start']))) > 0}


def evidence(path, needles):
    data = path.read_bytes()
    lines = data.decode(errors='replace').splitlines()
    found = {needle: [i + 1 for i, line in enumerate(lines) if needle in line] for needle in needles}
    if not all(found.values()):
        raise ValueError(f'Expected evidence missing: {path}')
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(data).hexdigest(), 'lines': found}


def main():
    dts = VENDOR / 'target/linux/ramips/dts'
    normal = layout((dts / 'MT7628snsv2.dts').read_text())
    small = layout((dts / 'MT7628snsv2-8M.dts').read_text())
    recipe = VENDOR / 'target/linux/ramips/image/Makefile'
    make = recipe.read_text()
    profile = re.search(r'^Image/Build/Profile/WemoSNSV2-8M=(.+)$', make, re.M).group(1)
    assert 'BuildFirmware/OF/WeMo,' in profile and 'WeMo-8M,' not in profile
    template = re.search(r'define BuildFirmware/OF/WeMo\n(.*?)\nendef', make, re.S).group(1)
    template_bytes = int(re.search(r'ibs=1k count=(\d+)', template).group(1)) * 1024
    assert template_bytes == 0x740000
    small_limit = small['rootfs_data']['start'] - small['kernel_1']['start']
    kernel = ROOT / 'sources/linux-3.18.27-wemo'
    nor = kernel / 'drivers/mtd/spi-nor/spi-nor.c'
    code = nor.read_text()
    scan = code[code.index('int spi_nor_scan('):code.index('EXPORT_SYMBOL_GPL(spi_nor_scan)')]
    write_branch = re.search(r'if\s*\((JEDEC_MFR.*?CFI_MFR_MACRONIX.*?)\)\s*\{\s*write_enable\(nor\);\s*write_sr\(nor, 0\);', scan, re.S)
    assert write_branch, 'Re-evaluate probe side effects if kernel code changes'
    config = (ROOT / 'artifacts/kernel-board/.config').read_text()
    assert 'CONFIG_MTD_M25P80=y\n' in config and 'CONFIG_MTD_SPI_NOR=y\n' in config
    inventory = json.loads((ROOT / 'research/inner-inventory.json').read_text())
    uboot_entries = [e['path'] for e in inventory['entries']
                     if re.search(r'uboot|u-boot|bootloader', e['path'], re.I)]
    evidence_files = [
        evidence(dts / 'MT7628snsv2.dts', ['compatible = "en25q64"', 'label = "Uboot"', 'label = "Firmware_2"']),
        evidence(dts / 'MT7628snsv2-8M.dts', ['label = "Firmware_1"', 'label = "rootfs_data"']),
        evidence(recipe, ['count=7424', 'count=6848', 'Image/Build/Profile/WemoSNSV2-8M=']),
        evidence(nor, ['JEDEC knows better', 'CFI_MFR_MACRONIX ||', 'write_sr(nor, 0);']),
        evidence(kernel / 'drivers/mtd/devices/m25p80.c', ['spi_nor_scan(nor, flash_name, mode)']),
        evidence(ROOT / 'artifacts/kernel-board/.config', ['CONFIG_MTD_M25P80=y', 'CONFIG_MTD_SPI_NOR=y']),
        evidence(VENDOR / 'target/linux/ramips/mt7628/WemoSNSV2/base-files/etc/init.d/boot',
                 ['fw_printenv bootdelay', '/usr/sbin/fw_setenv bootdelay 1']),
    ]
    report = {
        'date': '2026-10-19', 'scope': 'Older SNSV2 11420 source and existing rebuilt kernel; not a live flash measurement',
        'device_requests_this_research_pass': 0, 'physical_access_attempted': False,
        'installation_allowed': False, 'recovery_proven': False,
        'bootloader_family': 'U-Boot indicated by vendor environment tools and partition labels; exact installed build unknown',
        'bootloader_version': None,
        'source_layout_16MiB': normal, 'source_layout_8MiB': small,
        'source_8MiB_recipe_issue': {
            'profile_expansion': profile, 'template_bytes': template_bytes,
            'single_slot_bytes_before_shared_data': small_limit,
            'overflow_bytes': template_bytes - small_limit,
            'data_overlaps_if_template_written_at_kernel_start': overlaps(small['kernel_1']['start'],
                template_bytes, small, ('rootfs_data', 'nvram', 'User_Factory', 'Belkin_settings')),
            'means_user_has_8MiB': False,
        },
        'ram_boot_read_only_audit': {
            'current_candidate_is_strictly_read_only': False,
            'finding': 'Enabled m25p80 probe calls spi_nor_scan, which issues write-enable and write-status-register(0) for Macronix; no hardware execution performed',
            'other_unaudited_effects': 'Board pinmux, LED/button drivers, watchdog, radio and init paths also need review before claiming a non-mutating temporary boot',
            'dts_capacity_note': 'JEDEC detection overrides a mismatched platform chip name; en25q64 in DTS alone does not prove an 8MiB physical chip',
        },
        'archive_bootloader_named_paths': uboot_entries,
        'archive_limits': 'Named entries are generic OpenWrt boot packages/other targets and an upstream u-boot-2014.10 download, not a verified SNSV2 bootloader image. Path inspection does not exclude embedded blobs under unrelated names.',
        'source_evidence': evidence_files,
        'next_required_evidence': ['Actual boot banner/help without rebooting or changing environment in this phase',
            'Exact chip ID and measured partition map from a separately authorized read-only acquisition',
            'Matching independent full original backups and an exact-board recovery demonstration before writes'],
    }
    (ROOT / 'research/recovery-source-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: source-layout and probe audit; 8MiB recipe hazard and RAM-boot writes detected; no device access')


if __name__ == '__main__':
    main()
