#!/usr/bin/env python3
"""Audit and package a RAM-only development image; never produce a slot installer."""
import gzip
import hashlib
import json
import lzma
from pathlib import Path
import re
import stat
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'artifacts/forensic'
FORBIDDEN = '''NET BLOCK MODULES WATCHDOG INPUT VT FB HID_SUPPORT HID SERIO USB_SUPPORT
RTC_CLASS GPIO_RALINK GPIO_MT7621 GPIO_SYSFS MTD_CFI MTD_NAND MTD_NAND_MT7620
MTD_PHYSMAP MTD_PHYSMAP_OF MTD_BLOCK MTD_BLOCK_RO MTD_UBI MTD_OOPS MTD_TESTS
PSTORE DEVMEM DEVKMEM SPI_SPIDEV I2C PWM NEW_LEDS KEXEC SQUASHFS JFFS2_FS
MTD_OF_PARTS MTD_CMDLINE_PARTS MTD_ROOTFS_ROOT_DEV MTD_SPLIT NVRAM
MAGIC_SYSRQ CRASHLOG CRASH_DUMP ALLOW_DEV_COREDUMP DEBUG_FS SYSFS DEVTMPFS CONFIGFS_FS'''.split()
REQUIRED = '''WEMO_FORENSIC_RO MTD_M25P80 MTD_SPI_NOR SPI BLK_DEV_INITRD PROC_FS
CMDLINE_OVERRIDE CMDLINE_BOOL BINFMT_ELF'''.split()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config_audit(text, variant):
    options = dict(re.findall(r'^CONFIG_(\w+)=(.*)$', text, re.M))
    for key in REQUIRED:
        if options.get(key) != 'y': raise ValueError('Required policy absent: ' + key)
    for key in FORBIDDEN:
        if options.get(key) in ('y', 'm'): raise ValueError('Unsafe policy enabled: ' + key)
    test = options.get('WEMO_FORENSIC_TEST') == 'y'
    if test != (variant == 'malta'): raise ValueError('Fake controller must be Malta-only')
    if variant == 'board' and options.get('PCI') in ('y', 'm'): raise ValueError('Board PCI must be disabled')
    return {'required_enabled': REQUIRED, 'forbidden_disabled': FORBIDDEN, 'fake_controller': test}


def cpio_entries(data):
    offset, result = 0, {}
    while True:
        if data[offset:offset+6] != b'070701': raise ValueError('Invalid newc header')
        fields = [int(data[offset+6+i*8:offset+14+i*8], 16) for i in range(13)]
        mode, size, namesize = fields[1], fields[6], fields[11]
        name = data[offset+110:offset+110+namesize-1].decode()
        if data[offset+110+namesize-1:offset+110+namesize] != b'\0': raise ValueError('Invalid name terminator')
        start = (offset+110+namesize+3) & ~3
        payload = data[start:start+size]
        if len(payload) != size or name in result: raise ValueError('Duplicate or truncated archive entry')
        if name == 'TRAILER!!!':
            if size or any(data[(start+size+3) & ~3:]): raise ValueError('Extra payload/archive after trailer')
            return result
        if name.startswith('/') or '..' in name.split('/'): raise ValueError('Unsafe archive path')
        result[name] = {'mode': mode, 'size': size, 'rdev_major': fields[9], 'rdev_minor': fields[10],
                        'sha256': hashlib.sha256(payload).hexdigest()}
        offset = (start+size+3) & ~3


def main():
    if not __debug__: raise RuntimeError('Packaging audit must not run with Python assertions disabled')
    tests = json.loads((ROOT / 'research/forensic-ram-test.json').read_text())
    assert tests['passed'] and not tests['physical_device_touched']
    assert tests['kernel_sha256'] == sha(FOLDER / 'kernel-malta/vmlinux'), 'Guest test is stale'
    assert tests['initramfs_sha256'] == sha(FOLDER / 'initramfs.cpio'), 'Guest initramfs is stale'
    entries = cpio_entries((FOLDER / 'initramfs.cpio').read_bytes())
    assert set(entries) == {'.', 'dev', 'proc', 'dev/console', 'init'}
    assert entries['init']['sha256'] == sha(FOLDER / 'init')
    assert stat.S_ISREG(entries['init']['mode']) and stat.S_ISCHR(entries['dev/console']['mode'])
    assert (entries['dev/console']['rdev_major'], entries['dev/console']['rdev_minor']) == (5, 1)
    assert all(stat.S_ISDIR(entries[name]['mode']) for name in ('.', 'dev', 'proc'))
    audits = {}
    for variant in ('board', 'malta'):
        folder = FOLDER / ('kernel-' + variant)
        audits[variant] = config_audit((folder / '.config').read_text(), variant)
        compressed = (folder / 'usr/initramfs_data.cpio.gz').read_bytes()
        assert gzip.decompress(compressed) == (FOLDER / 'initramfs.cpio').read_bytes()
        assert compressed in (folder / 'vmlinux').read_bytes(), 'Current archive not embedded in ELF'
        stubs = (folder / 'deny-stubs.asm').read_text()
        for function in ('m25p80_write_reg', 'm25p80_write', 'm25p80_erase', 'forensic_mtd_write', 'forensic_mtd_erase'):
            assert re.search(r'<'+function+r'>:', stubs), 'Missing deny routine: '+function
        assert not re.search(r'\b(jal|jalr|bal)\b', stubs), 'Deny routines must make no calls'
        symbols = (folder / 'symbols.txt').read_text()
        assert not re.search(r'\b(rt_timer_probe|mt7621_gpio_probe|mt7621_wdt_probe)\b', symbols)
        if variant == 'board':
            assert 'forensic_test' not in symbols
            assert b'wemo-fake-spi' not in (folder / 'vmlinux').read_bytes()
        audits[variant].update({'kernel_sha256': sha(folder/'vmlinux'), 'config_sha256': sha(folder/'.config'),
                               'embedded_initramfs_verified': True, 'deny_routines_have_no_calls': True})
    dtb = (FOLDER / 'forensic.dtb').read_bytes()
    expanded = (FOLDER / 'forensic-expanded.dts').read_text()
    for node in ('watchdog@', 'gpio@', 'uart1@', 'uart2@', 'ethernet@', 'esw@', 'usbphy@', 'ehci@', 'ohci@', 'pcie@', 'sdhci@'):
        assert node not in expanded, 'Forbidden board device: '+node
    assert 'partition@' not in expanded and 'gpio-leds' not in expanded and 'gpio-keys' not in expanded
    raw = bytearray((FOLDER/'kernel-board/kernel.raw').read_bytes())
    marker = raw.find(b'OWRTDTB:', 0, 16384)
    assert marker >= 0 and marker % 4 == 0 and len(dtb) <= 16376
    raw[marker+8:marker+16384] = dtb.ljust(16376, b'\0')
    compressed = bytearray(lzma.compress(bytes(raw), format=lzma.FORMAT_ALONE,
        filters=[{'id': lzma.FILTER_LZMA1, 'dict_size': 8*1024*1024, 'lc': 1, 'lp': 2, 'pb': 2}]))
    struct.pack_into('<Q', compressed, 5, len(raw))
    assert lzma.decompress(compressed, format=lzma.FORMAT_ALONE) == raw
    header = bytearray(struct.pack('>7I4B32s', 0x27051956, 0, 0, len(compressed),
        0x80000000, 0x80000000, zlib.crc32(compressed), 5, 5, 2, 3, b'F7C063 forensic RAM ONLY'))
    struct.pack_into('>I', header, 4, zlib.crc32(header))
    image = FOLDER/'wemo-f7c063-forensic-ram.uImage'
    image.write_bytes(header+compressed)
    report = {'scope': 'Storage-read-only forensic RAM candidate; not certified for physical deployment',
        'board_boot_tested': False, 'device_requests': 0, 'installation_allowed': False,
        'bootloader_side_effects_verified': False, 'zero_hardware_side_effects_claimed': False,
        'guest_run_id': tests['run_id'], 'kernel_policy': audits, 'initramfs_entries': entries,
        'physical_image_has_test_controller': False, 'flash_opcodes_allowed': ['03 read', '05 status', '9f JEDEC ID'],
        'source_fork': 'sources/linux-3.18.27-forensic; normal app source/build unmodified',
        'outputs': [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in
            (image, FOLDER/'forensic.dtb', FOLDER/'initramfs.cpio', FOLDER/'init')],
        'limitations': ['Exact bootloader/load method and its pre-entry writes remain unknown',
            'MT7688 SPI controller, electrical behavior, pinmux and inherited watchdog state are not emulated',
            'CPU, RAM, UART, clocks and controller initialization change volatile hardware state',
            'No on-device execution, recovery demonstration or blanket no-change guarantee has been established']}
    changed = ['drivers/mtd/devices/m25p80.c', 'drivers/mtd/spi-nor/spi-nor.c',
               'drivers/mtd/Kconfig', 'drivers/mtd/Makefile', 'arch/mips/ralink/Makefile',
               'drivers/gpio/gpiolib-of.c']
    report['source_fork_hashes'] = {relative: {
        'normal_sha256': sha(ROOT/'sources/linux-3.18.27-wemo'/relative),
        'forensic_sha256': sha(ROOT/'sources/linux-3.18.27-forensic'/relative)} for relative in changed}
    inputs = ['port/forensic.dts', 'port/forensic_init.c', 'port/forensic_spi_test.c',
              'scripts/prepare_forensic_kernel.py', 'scripts/configure_forensic_kernel.py',
              'scripts/prepare_forensic_initramfs.py', 'scripts/build_forensic_ram.sh']
    report['build_input_hashes'] = {relative: sha(ROOT/relative) for relative in inputs}
    (ROOT/'research/forensic-ram-build.json').write_text(json.dumps(report, indent=2)+'\n')
    print('PASS: constrained configuration, embedded initramfs, deny stubs and board DTB; packaged RAM candidate')


if __name__ == '__main__': main()
