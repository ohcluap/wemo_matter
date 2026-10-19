#!/usr/bin/env python3
"""Read the older vendor ELF to document the relay path and branch literals."""
from pathlib import Path
import hashlib
import json
import struct

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'sources/snsv2-11420/package/belkin/WeMo_SNSV2/files/lib/libDeviceControl.so'
data=path.read_bytes()
assert data[:6]==b'\x7fELF\x01\x01'
phoff=struct.unpack_from('<I',data,28)[0];size,count=struct.unpack_from('<HH',data,42)
segments=[struct.unpack_from('<8I',data,phoff+i*size) for i in range(count)]
def offset(address):
    for kind,start,virtual,_,length,_,_,_ in segments:
        if kind==1 and virtual<=address<virtual+length:return start+address-virtual
    raise ValueError('ELF address not in file-backed load segment')
def word(address):return struct.unpack_from('<I',data,offset(address))[0]
def string(address):
    start=offset(address);return data[start:data.index(b'\0',start)].decode()
# Addresses from the pinned library's setPower disassembly. Validate the exact
# instructions before deriving the path; never run the vendor library.
assert word(0x3820)==0x24040031 and word(0x3908)==0x24040030
rodata=word(0x22430-32724)
report={'scope':'SNSV2 11420 library only; installed 11565 and physical pin mapping unverified',
        'library_sha256':hashlib.sha256(data).hexdigest(),'function':'setPower at 0x3760',
        'fopen_path':string(rodata-30296),'fopen_mode':string(rodata-30264),
        'on_branch_instruction':'0x3820: li a0,49 (ASCII 1)',
        'off_branch_instruction':'0x3908: li a0,48 (ASCII 0)',
        'hardware_path_enabled_by_default':False,'physical_gpio_touched':False}
(ROOT/'research/relay-backend-evidence.json').write_text(json.dumps(report,indent=2)+'\n')
print('Recorded read-only ELF relay evidence')
