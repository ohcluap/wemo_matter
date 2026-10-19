#!/usr/bin/env python3
"""Stage a minimal complete development rootfs plus a separate guest test image."""
import gzip
import json
from pathlib import Path
import shutil
import stat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/system-image'
OUT.mkdir(exist_ok=True)


def install(source, target, mode=0o755):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    target.chmod(mode)


def stage(name, guest=False):
    destination = OUT / name
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(ROOT / 'firmware/rootfs', destination)
    for directory in ('bin','sbin','usr/bin','usr/sbin','proc','sys','dev','dev/pts','tmp','run','root','etc/wemo-matter/state','lib/modules/3.18.27'):
        (destination / directory).mkdir(parents=True, exist_ok=True)
    install(ROOT/'artifacts/busybox/busybox', destination/'bin/busybox')
    # Applets required by init, diagnostic shell, DHCP, and the test runner.
    applets = 'sh mount umount mkdir mknod cat echo printf sleep grep cut awk sed cp mv rm ln chmod chown sync test true false ip ifconfig route udhcpc hostname kill killall halt reboot poweroff ps free dmesg uname readlink env ls touch mdev insmod lsmod rmmod modprobe nc ping ping6 find wc head tail tr sort stty'.split()
    for applet in applets:
        (destination/'bin'/applet).symlink_to('/bin/busybox')
    install(ROOT/'artifacts/full-app/firmware/wemo-matter-outlet', destination/'usr/bin/wemo-matter-outlet')
    for binary in ('wpa_supplicant','wpa_cli','wpa_passphrase','iw','netns-exec','wemo-wifi-provision'):
        install(ROOT/'artifacts/wifi'/binary, destination/'usr/bin'/binary)
    install(ROOT/'sources/wpa_supplicant-2.11/README',
            destination/'usr/share/licenses/wpa_supplicant/README', 0o644)
    if guest:
        for binary in ('hostapd','hostapd_cli'):
            install(ROOT/'artifacts/wifi'/binary,destination/'usr/bin'/binary)
        install(ROOT/'artifacts/full-app/mips-controller/wemo-chip-tool',destination/'usr/bin/wemo-chip-tool')
    else:
        # Vendor module retained for ABI inspection/manual development only.
        # No autoload, fabricated calibration, credentials, or GPIO enablement.
        for module in ('mt7628.ko','myadd.ko'):
            install(ROOT/'sources/snsv2-11420/package/belkin/WeMo_SNSV2/files/lib/modules/3.18.27'/module,
                    destination/'lib/modules/3.18.27'/module,0o644)
        for relative in ('usr/lib/wemo/guest-tests.sh','etc/offline-ap.conf','etc/offline-station.conf'):
            (destination/relative).unlink()
    for script in ('init','usr/lib/wemo/guest-tests.sh'):
        if (destination/script).exists(): (destination/script).chmod(0o755)
    (destination/'sbin/init').symlink_to('/init')
    (destination/'etc/wemo-matter/state').chmod(0o700)
    (destination/'etc/passwd').write_text('root:x:0:0:root:/root:/bin/sh\n')
    (destination/'etc/group').write_text('root:x:0:\n')
    (destination/'etc/fstab').write_text('# Development rootfs; flash overlay mapping is not activated.\n')
    return destination


def cpio(root):
    output = bytearray()
    def entry(name, mode, data=b'', major=0, minor=0):
        values=[1, mode,0,0,1,0,len(data),0,0,major,minor,len(name.encode())+1,0]
        output.extend(b'070701'+''.join(f'{v:08x}' for v in values).encode())
        output.extend(name.encode()+b'\0'); output.extend(b'\0'*(-len(output)%4))
        output.extend(data); output.extend(b'\0'*(-len(output)%4))
    entry('.',stat.S_IFDIR|0o755)
    for path in sorted(root.rglob('*')):
        info=path.lstat(); name=str(path.relative_to(root)); data=b''
        if path.is_symlink(): data=path.readlink().as_posix().encode()
        elif path.is_file(): data=path.read_bytes()
        entry(name, info.st_mode, data)
    for name,major,minor in [('console',5,1),('null',1,3),('random',1,8),('urandom',1,9),('tty',5,0)]:
        entry('dev/'+name,stat.S_IFCHR|0o600,b'',major,minor)
    entry('TRAILER!!!',0)
    return bytes(output)


board=stage('board-rootfs')
guest=stage('guest-rootfs',guest=True)
(OUT/'guest-initramfs.cpio.gz').write_bytes(gzip.compress(cpio(guest),mtime=0))
print('Staged complete development board rootfs and guest initramfs')
