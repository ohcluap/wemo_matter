#!/usr/bin/env python3
"""Apply the offline outlet adaptation to the pinned, local SDK checkout."""
import json
from pathlib import Path
import subprocess
sdk = Path(__file__).resolve().parents[1] / 'sources/connectedhomeip'
assert subprocess.check_output(['git','-C',str(sdk),'rev-parse','HEAD'],text=True).strip() == '3bcdd56ba54fb88b2afb4bfef575014671df7aa7'
def original(path):
    return subprocess.check_output(['git','-C',str(sdk),'show',f'HEAD:{path}'],text=True)
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
                attribute['defaultValue'] = '0'
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
