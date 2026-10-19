#!/usr/bin/env python3
"""Write pinned cross-build arguments, optionally with persistent firmware storage."""
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
variant = sys.argv[1]
assert variant in ('mips', 'firmware')
args = (root / 'toolchains/mips-app.gn').read_text()
if variant == 'firmware':
    definitions = [f'{name}="/etc/wemo-matter/state"' for name in
                   ('FATCONFDIR', 'SYSCONFDIR', 'LOCALSTATEDIR')]
    args += '\ntarget_defines = ' + json.dumps(definitions) + '\n'
(root / 'artifacts/full-app' / variant).mkdir(parents=True, exist_ok=True)
(root / 'artifacts/full-app' / variant / 'args.gn').write_text(args)
