#!/usr/bin/env python3
"""Fetch public build inputs and extract pinned kernel/BusyBox from vendor GPL archive."""
import hashlib
from pathlib import Path
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[1]
artifacts=ROOT/'artifacts'; sources=ROOT/'sources'
records={
 'linux-3.18.27.tar.xz':('ac9d2cd940e01cb2a659831fde4976e60d0241b0374026ed2ed7036d07039f06',None,'linux-3.18.27-base'),
 'busybox-1.23.2.tar.bz2':('05a6f9e21aad8c098e388ae77de7b2361941afa7157ef74216703395b14e319a',None,'busybox-1.23.2'),
 'libnl-3.10.0.tar.gz':('49b3e2235fdb58f5910bbb3ed0de8143b71ffc220571540502eb6c2471f204f5','https://github.com/thom311/libnl/releases/download/libnl3_10_0/libnl-3.10.0.tar.gz','libnl-3.10.0'),
 'wpa_supplicant-2.11.tar.gz':('912ea06f74e30a8e36fbb68064d6cdff218d8d591db0fc5d75dee6c81ac7fc0a','https://w1.fi/releases/wpa_supplicant-2.11.tar.gz','wpa_supplicant-2.11'),
 'hostapd-2.11.tar.gz':('2b3facb632fd4f65e32f4bf82a76b4b72c501f995a4f62e330219fe7aed1747a','https://w1.fi/releases/hostapd-2.11.tar.gz','hostapd-2.11'),
 'iw-6.9.tar.xz':('3f2db22ad41c675242b98ae3942dbf3112548c60a42ff739210f2de4e98e4894','https://www.kernel.org/pub/software/network/iw/iw-6.9.tar.xz','iw-6.9')}
for name,(digest,url,destination) in records.items():
    path=artifacts/name
    if not path.exists():
        if url:subprocess.run(['curl','--fail','--location',url,'--output',str(path)],check=True)
        else:
            vendor=artifacts/'snsv2-11420-inner.tar.gz'
            assert hashlib.file_digest(vendor.open('rb'),'sha256').hexdigest()=='bef5e0a749e904b278849355dc9f5e245260350f5992c2bcd322bcba0968f122'
            with tarfile.open(vendor) as archive:
                path.write_bytes(archive.extractfile('wemo_gpl_snsv2_package-11420/dl/'+name).read())
    assert hashlib.file_digest(path.open('rb'),'sha256').hexdigest()==digest, f'Checksum mismatch: {name}'
    target=sources/destination
    if not target.exists():
        target.mkdir()
        subprocess.run(['tar','-xf',str(path),'-C',str(target),'--strip-components','1'],check=True)
subprocess.run(['python3',str(ROOT/'scripts/prepare_board_sources.py')],check=True)
print('All system source checksums verified; device not contacted')
