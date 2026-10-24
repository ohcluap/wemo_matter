"""Locate MIPS PIC call-site candidates by exact GOT load (static evidence only)."""
import sys,struct,json,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'artifacts/analysis-tools'))
from elftools.elf.elffile import ELFFile
with open(sys.argv[1],'rb') as f:
 e=ELFFile(f);d=next(s for s in e.iter_segments() if s['p_type']=='PT_DYNAMIC');syms=list(d.iter_symbols());tags={t.entry.d_tag:t.entry.get('d_val',t.entry.get('d_ptr')) for t in d.iter_tags()};gp=struct.unpack('<6I',next(s for s in e.iter_segments() if s['p_type']==0x70000000).data())[-1]
 out={}
 for name in sys.argv[2:]:
  idx=next(i for i,s in enumerate(syms) if s.name==name);off=tags['DT_PLTGOT']+4*(tags['DT_MIPS_LOCAL_GOTNO']+idx-tags['DT_MIPS_GOTSYM'])-gp;pattern=struct.pack('<I',0x8f990000|(off&65535));out[name]=[]
  for seg in e.iter_segments():
   if seg['p_type']!='PT_LOAD' or not seg['p_flags']&1:continue
   data=seg.data();start=0
   while True:
    at=data.find(pattern,start)
    if at<0:break
    addr=seg['p_vaddr']+at;out[name].append({'address':hex(addr),'enclosing_functions':[s.name for s in syms if s['st_info']['type']=='STT_FUNC' and s['st_value']<=addr<s['st_value']+s['st_size']]});start=at+4
 print(json.dumps(out,indent=2))
