#!/usr/bin/env python3
"""Regression check for assembler-inserted sync breaking old MIPS futex fixups."""
import json
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[1]

def validate(path):
    data=path.read_bytes()
    assert data[:6]==b'\x7fELF\x01\x01', 'Expected little-endian ELF32'
    soff=struct.unpack_from('<I',data,32)[0]
    size,count,names_index=struct.unpack_from('<HHH',data,46)
    sections=[struct.unpack_from('<10I',data,soff+i*size) for i in range(count)]
    names=data[sections[names_index][4]:sections[names_index][4]+sections[names_index][5]]
    def name(section): return names[section[0]:].split(b'\0')[0].decode()
    by_name={name(s):s for s in sections}
    table=by_name['.symtab'];strings=sections[table[6]]
    symbol_names=data[strings[4]:strings[4]+strings[5]]
    function=None
    for offset in range(table[4],table[4]+table[5],16):
        n,value,length,info,other,shndx=struct.unpack_from('<IIIBBH',data,offset)
        if symbol_names[n:symbol_names.index(b'\0',n)]==b'cmpxchg_futex_value_locked':function=(value,length)
    assert function, 'Futex helper symbol missing'
    exception=by_name['__ex_table']
    entries=list(struct.iter_unpack('<II',data[exception[4]:exception[4]+exception[5]]))
    checked=[]
    for address,fixup in entries:
        if function[0]<=address<sum(function):
            section=next(s for s in sections if s[3]<=address<s[3]+s[5] and s[2]&2 and s[1]!=8)
            instruction=struct.unpack_from('<I',data,section[4]+address-section[3])[0]
            assert instruction>>26 in (0x30,0x38), f'Futex fixup points at non-LL/SC instruction {instruction:08x}'
            checked.append({'address':hex(address),'instruction':hex(instruction),'fixup':hex(fixup)})
    assert len(checked)>=2
    return checked

if __name__=='__main__':
    result={variant:validate(ROOT/f'artifacts/kernel-{variant}/vmlinux') for variant in ('board','malta')}
    (ROOT/'research/kernel-futex-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS: board and guest futex exception entries point at LL/SC instructions')
