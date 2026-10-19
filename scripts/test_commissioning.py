#!/usr/bin/env python3
"""Commission and control only a simulated outlet on an internal Docker network."""
import argparse
import hashlib
import datetime
import json
from pathlib import Path
import re
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'wemo-matter-app-builder:bookworm'
BUILD = ROOT / 'artifacts/full-app'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--target', choices=['native', 'mips'], default='native')
args = parser.parse_args()
app_image = IMAGE if args.target == 'native' else 'wemo-matter-offline-tests:bookworm'
runner = [] if args.target == 'native' else ['qemu-mipsel', '-cpu', '24KEc']
app_binary = BUILD / args.target / 'chip-lighting-app'
run_id = uuid.uuid4().hex[:8]
network = 'wemo-matter-test-' + run_id
app_name = network + '-app'
controller_name = network + '-controller'
subnet = f'fd7e:ca71:{run_id[:4]}:{run_id[4:]}::/64'
address = subnet.replace('::/64', '::2')
run_dir = BUILD / 'tests' / run_id
(run_dir / 'device').mkdir(parents=True)
(run_dir / 'controller').mkdir()
report = {'run_id': run_id, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'target': ('Linux arm64 simulated outlet' if args.target == 'native' else
                     'MIPS32r2 soft-float full outlet under QEMU 24KEc user emulation'),
          'physical_device_tested': False, 'tests': [], 'passed': False}


def docker(*args, timeout=90, check=True):
    result = subprocess.run(['docker', *map(str, args)], capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f'Docker command failed ({result.returncode}): {result.stderr[-1500:]}')
    return result


def tool(label, *args, expected=None):
    result = docker('run', '--rm', '--name', controller_name, '--network', network, '--cap-drop', 'ALL',
                    '--security-opt', 'no-new-privileges', '--read-only', '--tmpfs', '/tmp',
                    '-v', f'{BUILD}/controller:/bin-output:ro',
                    '-v', f'{run_dir}/controller:/state', IMAGE,
                    '/bin-output/chip-tool', *args, '--storage-directory', '/state',
                    timeout=120, check=False)
    text = result.stdout + result.stderr
    (run_dir / (label + '.log')).write_text(text)
    if result.returncode != 0 or (expected and not re.search(expected, text, re.I)):
        raise RuntimeError(f'{label} failed; inspect local log {run_dir / (label + ".log")}')
    report['tests'].append(label)
    print('PASS:', label, flush=True)
    return text


def start_app():
    docker('run', '-d', '--name', app_name, '--network', network, '--ip6', address,
           '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--read-only',
           '-v', f'{BUILD}/{args.target}:/bin-output:ro', '-v', f'{run_dir}/device:/tmp', app_image, *runner,
           '/bin-output/chip-lighting-app', '--KVS', '/tmp/wemo-simulator.kvs',
           '--discriminator', '3840', '--passcode', '20202021', '--interface-id', 'eth0')
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        logs = docker('logs', app_name).stdout
        if 'Server initialization complete' in logs or 'Server Listening...' in logs:
            return
        time.sleep(0.3)
    raise RuntimeError('Simulator failed to start')


try:
    assert app_binary.is_file(), 'Build outlet first'
    report['app_sha256'] = hashlib.sha256(app_binary.read_bytes()).hexdigest()
    assert (BUILD / 'controller/chip-tool').is_file(), 'Build controller first'
    docker('network', 'create', '--internal', '--ipv6', '--subnet', subnet, network)
    info = json.loads(docker('network', 'inspect', network).stdout)[0]
    assert info['Internal'] and info['EnableIPv6'], 'Network isolation not enabled'
    report['internal_network_verified'] = True
    start_app()
    tool('commissioning', 'pairing', 'onnetwork-long', '1', '20202021', '3840',
         expected='Device commissioning completed with success')
    descriptor = tool('outlet-device-type', 'descriptor', 'read', 'device-type-list', '1', '1')
    assert re.search(r'DeviceType:\s*(266|0x0*10a)\b', descriptor, re.I), 'Expected On/Off Plug-in Unit'
    tool('off-command', 'onoff', 'off', '1', '1')
    tool('off-readback', 'onoff', 'read', 'on-off', '1', '1', expected=r'OnOff:\s*(FALSE|0)\b')
    tool('on-command', 'onoff', 'on', '1', '1')
    tool('on-readback', 'onoff', 'read', 'on-off', '1', '1', expected=r'OnOff:\s*(TRUE|1)\b')
    tool('toggle-command', 'onoff', 'toggle', '1', '1')
    tool('toggle-readback', 'onoff', 'read', 'on-off', '1', '1', expected=r'OnOff:\s*(FALSE|0)\b')
    logs = docker('logs', app_name).stdout
    assert 'SIMULATED_RELAY on=1' in logs and 'SIMULATED_RELAY on=0' in logs
    (run_dir / 'device-before-restart.log').write_text(logs)
    report['tests'].append('simulated-relay-callbacks')
    docker('rm', '-f', app_name)
    start_app()
    tool('restart-session-read', 'onoff', 'read', 'on-off', '1', '1')
    tool('restart-on-command', 'onoff', 'on', '1', '1')
    tool('restart-on-readback', 'onoff', 'read', 'on-off', '1', '1', expected=r'OnOff:\s*(TRUE|1)\b')
    report['passed'] = True
finally:
    logs = docker('logs', app_name, check=False)
    (run_dir / 'device-final.log').write_text(logs.stdout + logs.stderr)
    docker('rm', '-f', controller_name, check=False)
    docker('rm', '-f', app_name, check=False)
    cleanup = docker('network', 'rm', network, check=False)
    report['network_removed'] = cleanup.returncode == 0
    (run_dir / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    if report['passed']:
        (ROOT / ('research/commissioning-results.json' if args.target == 'native' else
                 'research/mips-commissioning-results.json')).write_text(json.dumps(report, indent=2) + '\n')
    print('Local logs:', run_dir, flush=True)
