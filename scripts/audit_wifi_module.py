#!/usr/bin/env python3
"""Check vendor module import availability without loading a driver."""
import hashlib
import json
from pathlib import Path
import subprocess
import struct

ROOT=Path(__file__).resolve().parents[1]
base='sources/snsv2-11420/package/belkin/WeMo_SNSV2/files/lib/modules/3.18.27'
# GNU nm runs in a no-network container and only reads the ELF objects.
command=['docker','run','--rm','--network','none','-v',f'{ROOT}/sources/snsv2-11420:/vendor:ro',
         'wemo-matter-board-builder:bookworm','mipsel-linux-gnu-nm']
def module_geometry(path):
    data=path.read_bytes()
    offset=struct.unpack_from('<I',data,32)[0]
    size,count,names_index=struct.unpack_from('<HHH',data,46)
    sections=[struct.unpack_from('<10I',data,offset+i*size) for i in range(count)]
    name_section=sections[names_index]
    names=data[name_section[4]:name_section[4]+name_section[5]]
    named={names[s[0]:names.index(b'\0',s[0])].decode():s for s in sections}
    metadata=named['.gnu.linkonce.this_module']
    relocation=named['.rel.gnu.linkonce.this_module']
    symbols=sections[relocation[6]];strings=sections[symbols[6]]
    pool=data[strings[4]:strings[4]+strings[5]]
    pointers={}
    for place,info in struct.iter_unpack('<II',data[relocation[4]:relocation[4]+relocation[5]]):
        symbol=struct.unpack_from('<I',data,symbols[4]+(info>>8)*16)[0]
        name=pool[symbol:pool.index(b'\0',symbol)].decode()
        if name in ('init_module','cleanup_module'):pointers[name]=place
    return {'metadata_bytes':metadata[5],'function_pointer_offsets':pointers}

exports={line.split()[-1][len('__ksymtab_'):] for line in (ROOT/'artifacts/kernel-board/System.map').read_text().splitlines()
         if line.split()[-1].startswith('__ksymtab_')}
modules={}
for module in ('myadd.ko','mt7628.ko'):
    path=f'/vendor/package/belkin/WeMo_SNSV2/files/lib/modules/3.18.27/{module}'
    symbols=subprocess.check_output([*command,path],text=True)
    imported={line.split()[-1] for line in symbols.splitlines() if line.split()[0]=='U'}
    provided={line.split()[-1][len('__ksymtab_'):] for line in symbols.splitlines()
              if line.split()[-1].startswith('__ksymtab_')}
    modules[module]={'imports':sorted(imported),'exports':sorted(provided),
                     'sha256':hashlib.sha256((ROOT/base/module).read_bytes()).hexdigest(),
                     'metadata_geometry':module_geometry(ROOT/base/module)}
all_exports=exports|set(modules['myadd.ko']['exports'])
for module,record in modules.items():record['unresolved_imports']=sorted(set(record['imports'])-all_exports)
kernel_geometry=module_geometry(ROOT/'artifacts/kernel-board/drivers/usb/core/usbcore.ko')
report={'kernel_module_metadata_geometry':kernel_geometry,
        'module_metadata_layout_matches':all(r['metadata_geometry']==kernel_geometry for r in modules.values()),
        'scope':'Symbol availability only; modules were not loaded and structure/calling ABI and radio operation are unverified',
        'module_loading_vermagic_check':'Vendor CONFIG_MODULE_STRIPPED=y omits vermagic checks; absence of an error is not ABI validation',
        'modules':modules,'all_imports_available':all(not r['unresolved_imports'] for r in modules.values()),
        'physical_radio_tested':False}
(ROOT/'research/wifi-module-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('All driver/helper imports available:',report['all_imports_available'])
print('Module metadata size and init/exit offsets match:',report['module_metadata_layout_matches'])
