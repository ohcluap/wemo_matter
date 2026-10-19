#!/usr/bin/env python3
"""Package the rebuilt board kernel using the inspected vendor's image format."""
from pathlib import Path
import hashlib
import json
import lzma
import struct
import zlib

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'artifacts/kernel-board'
kernel=bytearray((folder/'kernel.raw').read_bytes())
dtb=(folder/'wemo.dtb').read_bytes()
marker=kernel.find(b'OWRTDTB:',0,16384)
assert marker>=0 and marker%4==0 and len(dtb)+8<=16384, 'Vendor DTB reservation not found or too small'
start=marker+8
kernel[start:start+16376]=dtb.ljust(16376,b'\x00')
(folder/'kernel-with-dtb.raw').write_bytes(kernel)
compressed=bytearray(lzma.compress(bytes(kernel),format=lzma.FORMAT_ALONE,
    filters=[{'id':lzma.FILTER_LZMA1,'dict_size':8*1024*1024,'lc':1,'lp':2,'pb':2}]))
# Encode actual output size as the vendor LZMA utility does.
struct.pack_into('<Q',compressed,5,len(kernel))
assert lzma.decompress(compressed,format=lzma.FORMAT_ALONE)==kernel
header=bytearray(struct.pack('>7I4B32s',0x27051956,0,0,len(compressed),0x80000000,0x80000000,
                            zlib.crc32(compressed),5,5,2,3,b'Wemo Matter dev Linux-3.18.27'))
struct.pack_into('>I',header,4,zlib.crc32(header))
image=header+compressed
(folder/'wemo-kernel.uImage').write_bytes(image)
report={'kernel_release':'3.18.27','compiler':'Debian MIPS cross GCC 12; freestanding kernel, no libc',
        'vendor_profile':'SNSV2 11420 source, normal 16 MiB layout; physical board unconfirmed',
        'kernel_bytes':len(image),'kernel_region_bytes':0x180000,'fits_kernel_region':len(image)<=0x180000,
        'dtb_bytes':len(dtb),'dtb_marker_offset':marker,'lzma_roundtrip_verified':True,
        'board_boot_tested':False,'uimage_sha256':hashlib.sha256(image).hexdigest(),
        'config_sha256':hashlib.sha256((folder/'.config').read_bytes()).hexdigest()}
(ROOT/'research/board-kernel-build.json').write_text(json.dumps(report,indent=2)+'\n')
print('Board kernel bytes:',len(image),'slot limit:',0x180000)
