"""Statically annotate a section-stripped MIPS daemon using ELF program headers."""
import sys, struct, pathlib, hashlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'artifacts/analysis-tools'))
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN
root=pathlib.Path(__file__).resolve().parents[1]
p=pathlib.Path(sys.argv[1]); function=sys.argv[2]; output=pathlib.Path(sys.argv[3])
with p.open('rb') as f:
 e=ELFFile(f); segments=list(e.iter_segments()); dyn=next(s for s in segments if s['p_type']=='PT_DYNAMIC'); syms=list(dyn.iter_symbols())
 tags={t.entry.d_tag:t.entry.get('d_val',t.entry.get('d_ptr')) for t in dyn.iter_tags()}
 def read(addr,n):
  s=next(s for s in segments if s['p_type']=='PT_LOAD' and s['p_vaddr']<=addr and addr+n<=s['p_vaddr']+s['p_memsz'])
  f.seek(s['p_offset']+addr-s['p_vaddr']); return f.read(min(n, s['p_filesz']-(addr-s['p_vaddr']))).ljust(n,b'\0')
 gp=struct.unpack('<6I',next(s for s in segments if s['p_type']==0x70000000).data())[-1]
 got=tags['DT_PLTGOT']; local=tags['DT_MIPS_LOCAL_GOTNO']; first=tags['DT_MIPS_GOTSYM']; count=local+tags['DT_MIPS_SYMTABNO']-first
 words=struct.unpack('<'+'I'*count,read(got,count*4))
 symbol=next(s for s in syms if s.name==function and s['st_info']['type']=='STT_FUNC' and s['st_size'])
 start=symbol['st_value']; length=symbol['st_size']
 seg=next(s for s in segments if s['p_type']=='PT_LOAD' and s['p_flags']&1)
 relocs = {r['r_offset']: dyn.get_symbol(r['r_info_sym']).name
           for tab in dyn.get_relocation_tables().values() for r in tab.iter_relocations()}
 plt = {}
 code = read(start, seg['p_vaddr'] + seg['p_filesz'] - start)
 for offset in range(0, len(code)-8, 4):
  hi, lo = struct.unpack_from('<II', code, offset)
  if hi >> 16 == 0x3c0f and lo >> 16 == 0x8df9:
   addr = ((hi & 65535) << 16) + struct.unpack('<h',struct.pack('<H',lo & 65535))[0]
   if addr in relocs: plt[start + offset] = relocs[addr]
 lines=[]
 dis = Cs(CS_ARCH_MIPS,CS_MODE_MIPS32|CS_MODE_LITTLE_ENDIAN); dis.skipdata = True
 for i in dis.disasm(read(start,length),start):
  a=''
  if i.mnemonic=='lw' and '($gp)' in i.op_str:
   idx=(gp+int(i.op_str.split(', ')[1].split('(')[0],0)-got)//4
   if 0<=idx<len(words): a=' ; '+(syms[first+idx-local].name if idx>=local else hex(words[idx]))
  if i.mnemonic == 'jal':
   target = int(i.op_str, 0)
   a += ' ; call ' + plt[target] if target in plt else ''.join(' ; call ' + sym.name for sym in syms if sym['st_value'] == target and sym.name)
  lines.append(f'{i.address:08x}: {i.mnemonic} {i.op_str}{a}')
output.write_text('\n'.join(lines))

