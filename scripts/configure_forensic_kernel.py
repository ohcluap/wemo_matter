#!/usr/bin/env python3
"""Separate constrained kernel configuration; never alter normal app builds."""
from pathlib import Path
import subprocess
import sys

source, variant = Path(sys.argv[1]), sys.argv[2]
subprocess.run(['python3', '/scripts/configure_kernel.py', str(source), variant], check=True)
settings = {
    'EXPERT': 'y', 'VT': 'n', 'FB': 'n', 'HID_SUPPORT': 'n', 'HID': 'n', 'SERIO': 'n',
    'SCSI': 'n', 'ATA': 'n', 'FIREWIRE': 'n', 'IMAGE_CMDLINE_HACK': 'n',
    'MAGIC_SYSRQ': 'n',
    'CRASHLOG': 'n', 'CRASH_DUMP': 'n', 'ALLOW_DEV_COREDUMP': 'n',
    'DEBUG_FS': 'n', 'DEBUG_PINCTRL': 'n',
    'CONFIGFS_FS': 'n',
    'WEMO_FORENSIC_RO': 'y', 'WEMO_FORENSIC_TEST': 'y' if variant == 'malta' else 'n',
    'MTD': 'y', 'SPI': 'y', 'MTD_M25P80': 'y', 'MTD_SPI_NOR': 'y',
    'MTD_CFI': 'n', 'MTD_PHYSMAP': 'n', 'MTD_PHYSMAP_OF': 'n', 'MTD_NAND_MT7620': 'n',
    'MTD_NAND': 'n', 'MTD_ONENAND': 'n', 'MTD_UBI': 'n', 'MTD_TESTS': 'n',
    'MTD_ROOTFS_ROOT_DEV': 'n', 'MTD_ROOTFS_SPLIT': 'n', 'MTD_SPLIT_FIRMWARE': 'n',
    'MTD_SPLIT': 'n', 'MTD_CMDLINE_PARTS': 'n', 'MTD_OF_PARTS': 'n',
    'MTD_SPLIT_SQUASHFS_ROOT': 'n', 'MTD_SPLIT_UIMAGE_FW': 'n', 'MTD_SPLIT_SEAMA_FW': 'n',
    'MTD_SPLIT_FIT_FW': 'n', 'MTD_SPLIT_LZMA_FW': 'n', 'MTD_SPLIT_TPLINK_FW': 'n', 'MTD_SPLIT_TRX_FW': 'n',
    'BLOCK': 'n', 'MODULES': 'n', 'NET': 'n', 'WIRELESS': 'n', 'WLAN': 'n',
    'USB_SUPPORT': 'n', 'USB': 'n', 'USB_GADGET': 'n', 'WATCHDOG': 'n',
    'INPUT': 'n', 'NEW_LEDS': 'n', 'LEDS_CLASS': 'n', 'GPIO_SYSFS': 'n',
    'GPIO_RALINK': 'n', 'GPIO_MT7621': 'n', 'HWMON': 'n', 'RTC_CLASS': 'n',
    'I2C': 'n', 'PWM': 'n', 'NVRAM': 'n', 'MTD_OOPS': 'n', 'PSTORE': 'n',
    'DEVMEM': 'n', 'DEVKMEM': 'n', 'SPI_SPIDEV': 'n', 'KEXEC': 'n',
    'JFFS2_FS': 'n', 'SQUASHFS': 'n', 'NETWORK_FILESYSTEMS': 'n',
    'DEVTMPFS': 'n', 'SYSFS': 'n', 'TMPFS': 'n', 'PROC_FS': 'y',
    'BLK_DEV_INITRD': 'y', 'INITRAMFS_SOURCE': '"/inputs/initramfs.cpio"',
    'INITRAMFS_COMPRESSION_GZIP': 'y', 'CMDLINE_BOOL': 'y', 'CMDLINE_OVERRIDE': 'y',
    'CMDLINE': '"console=ttyS0,' + ('115200' if variant == 'malta' else '57600') + ' rdinit=/init init=/init panic=0"',
    'UEVENT_HELPER': 'n', 'FW_LOADER': 'n', 'BINFMT_MISC': 'n', 'HW_RANDOM': 'n',
}
if variant == 'board': settings['PCI'] = 'n'
for key, value in settings.items():
    option = '--disable' if value == 'n' else '--enable' if value == 'y' else '--set-str'
    args = [str(source/'scripts/config'), '--file', '/out/.config', option, key]
    if option == '--set-str': args.append(value.strip('"'))
    subprocess.run(args, check=True)
