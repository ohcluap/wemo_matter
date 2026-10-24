#!/usr/bin/env python3
"""Apply the offline outlet adaptation to the pinned, local SDK checkout."""
import json
from pathlib import Path
import subprocess
import argparse
import copy
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk', type=Path, default=Path(__file__).resolve().parents[1] / 'sources/connectedhomeip')
sdk = parser.parse_args().sdk.resolve()
git = ['git', '-c', f'safe.directory={sdk}', '-C', str(sdk)]
revision = subprocess.check_output([*git, 'rev-parse', 'HEAD'], text=True).strip()
assert revision in ('3bcdd56ba54fb88b2afb4bfef575014671df7aa7', 'ff2472ff8d681496bf6e01450948ac95afc8898f'), revision

def original(path):
    return subprocess.check_output([*git, 'show', f'HEAD:{path}'], text=True)

# Reset files modified by optional size experiments before selecting a profile.
if revision == 'ff2472ff8d681496bf6e01450948ac95afc8898f':
    for path in ('examples/platform/linux/Options.cpp', 'examples/lighting-app/linux/BUILD.gn'):
        (sdk / path).write_text(original(path))
relative = 'examples/lighting-app/lighting-common/lighting-app.zap'
data = json.loads(original(relative))
ep = data['endpointTypes'][1]
name = 'MA-onoffpluginunit'
ep.update(name=name, deviceTypeName=name, deviceTypeCode=266, deviceIdentifiers=[266], deviceVersions=[3])
for entry in [ep['deviceTypeRef'], *ep['deviceTypes']]:
    entry.update(code=266, name=name, label=name)
ep['clusters'] = [c for c in ep['clusters'] if c['name'] not in ('Color Control','Level Control')]
for cluster in ep['clusters']:
    if cluster['name'] == 'On/Off':
        for attribute in cluster['attributes']:
            if attribute['name'] == 'FeatureMap':
                attribute['defaultValue'] = '1' if revision.startswith('ff2472ff') else '0'
if revision == 'ff2472ff8d681496bf6e01450948ac95afc8898f':
    ep['deviceVersions'] = [5]
    template = json.loads(original('examples/lighting-app/silabs/data_model/lighting-wifi-app.zap'))
    scenes = next(c for endpoint in template['endpointTypes'] for c in endpoint['clusters'] if c['name'] == 'Scenes Management')
    ep['clusters'].append(copy.deepcopy(scenes))
    root = data['endpointTypes'][0]
    root['clusters'] = [c for c in root['clusters'] if c['name'] != 'Thread Network Diagnostics']
    for cluster in root['clusters']:
        if cluster['name'] == 'Access Control':
            extension = copy.deepcopy(next(a for a in cluster['attributes'] if a['name'] == 'ACL'))
            extension.update(name='Extension', code=1)
            cluster['attributes'].append(extension)
        elif cluster['name'] == 'Diagnostic Logs':
            cluster['commands'].append(dict(name='RetrieveLogsResponse', code=1, mfgCode=None, source='server', isIncoming=0, isEnabled=1))

data['endpoints'][1]['endpointTypeName'] = name
(sdk/relative).write_text(json.dumps(data,indent=2)+'\n')
relative = 'examples/lighting-app/linux/main.cpp'
source = original(relative)
needle = '        LightingMgr().InitiateAction(*value ? LightingManager::ON_ACTION : LightingManager::OFF_ACTION);'
assert needle in source
source = source.replace(needle, '''        if (attributePath.mEndpointId != 1 || value == nullptr || size != 1 || *value > 1)
            return;
        LightingMgr().InitiateAction(*value ? LightingManager::ON_ACTION : LightingManager::OFF_ACTION);
        ChipLogProgress(AppServer, "SIMULATED_RELAY on=%u", static_cast<unsigned>(*value));''')
source = '#include "WemoRelayBackend.h"\n' + source
source += '''
chip::Protocols::InteractionModel::Status MatterPreAttributeChangeCallback(
    const chip::app::ConcreteAttributePath & path, uint8_t type, uint16_t size, uint8_t * value)
{
    using chip::Protocols::InteractionModel::Status;
    if (path.mEndpointId == 1 && path.mClusterId == OnOff::Id && path.mAttributeId == OnOff::Attributes::OnOff::Id)
    {
        if (value == nullptr || size != 1 || *value > 1 || !WemoRelay::Apply(*value != 0))
            return Status::Failure;
    }
    return Status::Success;
}
'''
(sdk/relative).write_text(source)
(sdk/'examples/lighting-app/linux/WemoRelayBackend.h').write_text(
    (Path(__file__).resolve().parents[1]/'port/RelayBackend.h').read_text())
(sdk/'build_overrides/pigweed_environment.gni').write_text('# System-packaged compiler/Python; no CIPD toolchain.\n')
