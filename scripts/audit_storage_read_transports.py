"""Offline evidence inventory; never imports or executes vendor code.

Requires the locally extracted 11420 libraries and pyelftools under artifacts.
Dynamic imports alone cannot rule out indirect calls or raw syscalls.
"""
import hashlib
import json
import pathlib
import re
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'artifacts/analysis-tools'))
from elftools.elf.elffile import ELFFile

WATCH = {'socket', 'bind', 'listen', 'accept', 'connect', 'recvfrom',
         'sendto', 'shm_open', 'shm_unlink', 'mmap', 'sem_init', 'syscall'}


def startup_inventory():
    """Record references, not full vendor source or data from a live plug."""
    roots = ('package/belkin/WeMo_SNSV2/files/',
             'package/base-files/files/',
             'target/linux/ramips/base-files/',
             'target/linux/ramips/mt7628/WemoSNSV2/base-files/')
    categories = {'http_root': r'Belkin_settings',
                  'dump': r'core_pattern|coredump|/proc/kcore',
                  'flash_device': r'/dev/mtd'}
    hits = []
    checked = 0
    with tarfile.open(ROOT / 'artifacts/vendor-inner.tar.gz', 'r:gz') as archive:
        for member in archive:
            relative = member.name.partition('/')[2]
            if not relative.startswith(roots) or not member.isfile() or member.size > 300000:
                continue
            data = archive.extractfile(member).read()
            if b'\0' in data:
                continue
            checked += 1
            lines = data.decode('utf-8', 'replace').splitlines()
            references = {key: [i + 1 for i, line in enumerate(lines)
                                if re.search(pattern, line)]
                          for key, pattern in categories.items()}
            references = {k: v for k, v in references.items() if v}
            if references:
                hits.append({'member': member.name,
                             'sha256': hashlib.sha256(data).hexdigest(),
                             'line_references': references})
    return {'scope': list(roots), 'text_files_checked': checked,
            'maximum_file_size': 300000, 'hits': hits,
            'limitation': 'Text/reference inventory only; not a complete runtime '
                          'filesystem or binary dataflow audit.'}


def inspect(name):
    path = ROOT / 'artifacts/binary-analysis' / name
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        dynamic = next(s for s in elf.iter_segments()
                       if s['p_type'] == 'PT_DYNAMIC')
        imports = sorted(s.name for s in dynamic.iter_symbols()
                         if s['st_shndx'] == 'SHN_UNDEF' and s.name in WATCH)
    return {'file': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'selected_undefined_symbols': imports}


if __name__ == '__main__':
    report = {
        'source_version': '11420 SNSV2 vendor binaries; NOT installed 11565',
        'method': 'Static ELF dynamic-symbol inventory, no vendor code execution',
        'files': [inspect(n) for n in
                  ['nvram', 'hkstore', 'libbelkin_nvram.so', 'libhkstore.so']],
        'interpretation': 'Both libraries import POSIX shared-memory functions. '
                          'None of these four binaries imports the selected '
                          'socket functions. This is not proof that the entire '
                          'firmware has no network-accessible wrapper.',
        'device_requests_sent': 0,
        'startup_inventory': startup_inventory(),
    }
    output = ROOT / 'research/storage-read-transport-inventory.json'
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(output)
