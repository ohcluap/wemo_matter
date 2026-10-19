#!/usr/bin/env python3
"""Summarize ignored emulator traces without exposing commissioning credentials."""
import collections
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
summary = {}
for name in ('mips-fit-results.json', 'legacy-time-results.json', 'firmware-commissioning-results.json'):
    path = ROOT / 'research' / name
    if not path.exists():
        continue
    report = json.loads(path.read_text())
    calls, enosys = collections.Counter(), collections.Counter()
    for log in (ROOT / 'artifacts/full-app/tests' / report['run_id']).glob('device-*.log'):
        for line in log.read_text().splitlines():
            match = re.match(r'\d+ (\w+)\(', line)
            if match:
                calls[match[1]] += 1
                # QEMU's MIPS target errno ENOSYS is 89.
                if 'errno=89 (Function not implemented)' in line:
                    enosys[match[1]] += 1
    if report.get('time64_enosys_injection'):
        assert enosys['clock_gettime64'] > 0 and calls['clock_gettime'] > 0
    summary[name] = {'run_id': report['run_id'], 'syscall_counts': dict(sorted(calls.items())),
                     'enosys_counts': dict(sorted(enosys.items())),
                     'peak_container_bytes': max(s['cgroup_peak_bytes'] for s in report['resource_samples'])}
qemu = ROOT / 'artifacts/qemu-legacy-build/qemu-mipsel'
summary['fault_injection'] = {
    'scope': 'Only time64 syscall absence; does not emulate the complete Linux 3.18 kernel or Wemo board',
    'source_url': 'https://download.qemu.org/qemu-7.2.22.tar.xz',
    'source_archive_sha256': 'c74b398c1950526686cb7784e23bd8945ef138b0e6541ba0495015aad3ac9532',
    'source_authentication': 'Official HTTPS download, observed hash pinned; detached signature not verified',
    'patch_sha256': hashlib.sha256((ROOT / 'port/qemu/no-time64.patch').read_bytes()).hexdigest(),
    'emulator_sha256': hashlib.sha256(qemu.read_bytes()).hexdigest()
}
(ROOT / 'research/syscall-audit.json').write_text(json.dumps(summary, indent=2) + '\n')
print('PASS: summarized syscall traces and verified time64 fallback observations')
