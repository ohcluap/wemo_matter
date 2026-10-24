"""Run in the existing offline build container; writes only /export artifacts."""
import hashlib
import json
from pathlib import Path
import subprocess

source = Path('/input/wemo-matter-outlet-compact')
destination = Path('/export')
original = source.read_bytes()
records = []
for dictionary in ['256KiB', '512KiB', '1MiB', '2MiB', '4MiB']:
    path = destination / ('app-dict-' + dictionary + '.xz')
    with path.open('wb') as output:
        subprocess.run(['xz', '-c', '-9', '--check=crc32', '--lzma2=dict=' + dictionary,
                        str(source)], stdout=output, check=True)
    decoded = subprocess.run(['xz', '-dc', '--memlimit-decompress=8MiB', str(path)],
                             capture_output=True, check=True).stdout
    if decoded != original:
        raise RuntimeError('Decompressed executable differs from tested app')
    listing = subprocess.check_output(['xz', '--robot', '--list', '-vv', str(path)], text=True)
    summary = next(line.split('\t') for line in listing.splitlines() if line.startswith('summary\t'))
    records.append({'dictionary': dictionary, 'file': path.name, 'compressed_bytes': path.stat().st_size,
                    'xz_reported_decoder_memory_bytes': int(summary[1]),
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'round_trip_verified': True, 'decoder_8MiB_limit_passed': True,
                    'xz_listing': listing})
report = {'scope': 'Offline host xz decompression; not a MIPS or physical Wemo execution test',
          'executable_bytes': len(original), 'executable_sha256': hashlib.sha256(original).hexdigest(),
          'check': 'CRC32', 'variants': records,
          'limitations': ['Decoder memory estimate excludes output tmpfs, loader executable and OS.',
                          'Stock decoder availability and exact firmware free RAM/storage remain unverified.',
                          'No startup hooks or device installation performed.']}
(destination / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
for record in records:
    print(record['dictionary'], record['compressed_bytes'], record['xz_reported_decoder_memory_bytes'], flush=True)
