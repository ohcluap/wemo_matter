"""Remove optional features from the offline SDK only."""
import json
from pathlib import Path
p = Path('/sdk/examples/lighting-app/lighting-common/lighting-app.zap')
d = json.loads(p.read_text())
r = d['endpointTypes'][0]
r['clusters'] = [c for c in r['clusters'] if c['name'] not in (
    'OTA Software Update Provider', 'OTA Software Update Requestor', 'Diagnostic Logs', 'User Label')]
keep = [i for i, code in enumerate(r['deviceIdentifiers']) if code != 18]
for field in ('deviceIdentifiers', 'deviceVersions'):
    r[field] = [r[field][i] for i in keep]
r['deviceTypes'] = [t for t in r['deviceTypes'] if t['code'] != 18]
p.write_text(json.dumps(d, indent=2) + '\n')
print('Remaining root clusters:', [c['name'] for c in r['clusters']])
