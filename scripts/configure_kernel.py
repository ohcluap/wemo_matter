#!/usr/bin/env python3
"""Apply explicit old-kernel toolchain adaptations and build configuration."""
from pathlib import Path
import subprocess
import sys
source, variant = Path(sys.argv[1]), sys.argv[2]
# Linux 3.18 only names GCC 3/4/5 headers; GCC >= 5 uses its GCC 5 definitions.
compiler = source / 'include/linux/compiler-gcc.h'
s = compiler.read_text()
if '#if __GNUC__ >= 5' not in s:
    s = s.replace('#include gcc_header(__GNUC__)', '#if __GNUC__ >= 5\n#include <linux/compiler-gcc5.h>\n#else\n#include gcc_header(__GNUC__)\n#endif')
if compiler.read_text() != s:
    compiler.write_text(s)
log2 = source / 'include/linux/log2.h'
s = log2.read_text().replace('__attribute__((const, noreturn))', '__attribute__((noreturn))')
if log2.read_text() != s:
    log2.write_text(s)
kbuild = source / 'arch/mips/Kbuild'
s = kbuild.read_text().replace('subdir-ccflags-y := -Werror', 'subdir-ccflags-y := -Wno-error')
if kbuild.read_text() != s:
    kbuild.write_text(s)
if variant == 'malta':
    subprocess.run(['make','-C',str(source),'O=/out','ARCH=mips','CROSS_COMPILE=mipsel-linux-gnu-', 'malta_defconfig'],check=True)
else:
    import re
    config = {}
    for name in ('generic/config-3.18','ramips/mt7628/config-3.18'):
        for line in (Path('/vendor/target/linux')/name).read_text().splitlines():
            m=re.match(r'(CONFIG_\w+)=|# (CONFIG_\w+) is not set',line)
            if m: config[m[1] or m[2]]=line
    Path('/out/.config').write_text('\n'.join(config.values())+'\n')
# Shared userspace essentials and observable kernel configuration.
settings = {'CPU_LITTLE_ENDIAN':'y','CPU_BIG_ENDIAN':'n','BLK_DEV_INITRD':'y','RD_GZIP':'y',
            'DEVTMPFS':'y','DEVTMPFS_MOUNT':'y','PROC_FS':'y','SYSFS':'y','TMPFS':'y',
            'IPV6':'y','IKCONFIG':'y','IKCONFIG_PROC':'y','SQUASHFS':'y','SQUASHFS_XZ':'y',
            'INET':'y','UNIX':'y','PACKET':'y','FUTEX':'y','EPOLL':'y','TIMERFD':'y',
            'EVENTFD':'y','BINFMT_ELF':'y','MODULES':'y','MODVERSIONS':'n','DEBUG_INFO':'n',
            'CC_OPTIMIZE_FOR_SIZE':'y','NETFILTER':'n','SOUND':'n','DRM':'n'}
if variant == 'malta':
    settings.update({'CPU_MIPS32_R2':'y','CPU_MIPS32_R1':'n','MIPS_FPU_EMULATOR':'y',
                     'SERIAL_8250_CONSOLE':'y','PCNET32':'y','CMDLINE_BOOL':'n',
                     'WIRELESS':'y','WLAN':'y','CFG80211':'y','CFG80211_WEXT':'y','MAC80211':'y',
                     'MAC80211_HWSIM':'y','RFKILL':'y','HW_RANDOM':'y','HW_RANDOM_VIRTIO':'y','VIRTIO_PCI':'y'})
else:
    settings.update({'RALINK':'y','SOC_MT7620':'y',
                     'KALLSYMS':'y','GPIO_SYSFS':'y','MTD':'y','MTD_M25P80':'y','MTD_SPI_NOR':'y',
                     'JFFS2_FS':'y','CMDLINE_BOOL':'y','CMDLINE':'"rootfstype=squashfs,jffs2 console=ttyS0,57600"'})
for key,value in settings.items():
    option='--disable' if value=='n' else '--enable' if value=='y' else '--set-str'
    args=[str(source/'scripts/config'),'--file','/out/.config',option,key]
    if option=='--set-str': args.append(value.strip('"'))
    subprocess.run(args,check=True)
