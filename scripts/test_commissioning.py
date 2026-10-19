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
parser.add_argument('--fit-check', action='store_true',
                    help='Test stripped MIPS payload under a 64 MiB cgroup with syscall tracing')
parser.add_argument('--legacy-time', action='store_true', help='Inject ENOSYS for time64 syscalls in the test emulator')
parser.add_argument('--firmware', action='store_true', help='Test persistent-storage firmware payload with a fresh /tmp on restart')
args = parser.parse_args()
if (args.legacy_time or args.firmware) and not args.fit_check:
    parser.error('--legacy-time and --firmware require --fit-check')
if args.fit_check and args.target != 'mips':
    parser.error('--fit-check requires --target mips')
app_image = IMAGE if args.target == 'native' else 'wemo-matter-offline-tests:bookworm'
runner = [] if args.target == 'native' else ['qemu-mipsel', '-cpu', '24KEc']
if args.fit_check:
    runner += ['-strace']
app_filename = 'wemo-matter-outlet' if args.fit_check else 'chip-lighting-app'
app_directory = 'firmware' if args.firmware else args.target
app_binary = BUILD / app_directory / app_filename
if args.legacy_time:
    app_image = IMAGE
    runner[0] = '/qemu-runtime/qemu-mipsel'
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
    sample_resources(label)
    print('PASS:', label, flush=True)
    return text


def sample_resources(label):
    if not args.fit_check:
        return
    result = docker('exec', app_name, 'sh', '-c',
                    'cat /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.peak /proc/1/status')
    lines = result.stdout.splitlines()
    report.setdefault('resource_samples', []).append({
        'label': label, 'cgroup_current_bytes': int(lines[0]), 'cgroup_peak_bytes': int(lines[1]),
        'process_status': [line for line in lines[2:] if line.startswith(('VmPeak:', 'VmSize:', 'VmHWM:', 'VmRSS:', 'Threads:'))]
    })


def start_app():
    docker('run', '-d', '--name', app_name,
           *(['--memory', '64m', '--memory-swap', '64m'] if args.fit_check else []), '--network', network, '--ip6', address,
           '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--read-only',
           '-v', f'{BUILD}/{app_directory}:/bin-output:ro',
           *(['-v', f'{run_dir}/device:/etc/wemo-matter/state', '--tmpfs', '/tmp'] if args.firmware else
             ['-v', f'{run_dir}/device:/tmp']),
           *(['-v', f'{ROOT}/artifacts/qemu-legacy-build:/qemu-runtime:ro',
              '-e', 'WEMO_TEST_NO_TIME64=1'] if args.legacy_time else []), app_image, *runner,
           '/bin-output/' + app_filename, '--KVS', ('/etc/wemo-matter/state/wemo.kvs' if args.firmware else '/tmp/wemo-simulator.kvs'),
           '--discriminator', '3840', '--passcode', '20202021', '--interface-id', 'eth0')
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        logs = docker('logs', app_name).stdout
        if 'Server initialization complete' in logs or 'Server Listening...' in logs:
            if args.fit_check:
                host = json.loads(docker('inspect', app_name).stdout)[0]['HostConfig']
                assert host['Memory'] == 64 * 1024 * 1024 and host['MemorySwap'] == host['Memory']
                report['memory_limit_bytes'] = host['Memory']
                report['swap_disabled'] = True
                sample_resources('startup')
            return
        time.sleep(0.3)
    raise RuntimeError('Simulator failed to start')


try:
    assert app_binary.is_file(), 'Build outlet first'
    report['persistent_storage_profile'] = args.firmware
    report['time64_enosys_injection'] = args.legacy_time
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
    device_logs = docker('logs', app_name)
    logs = device_logs.stdout
    assert 'SIMULATED_RELAY on=1' in logs and 'SIMULATED_RELAY on=0' in logs
    (run_dir / 'device-before-restart.log').write_text(logs + device_logs.stderr)
    report['tests'].append('simulated-relay-callbacks')
    if args.firmware:
        files = {p.name: p.stat().st_size for p in (run_dir / 'device').iterdir() if p.is_file()}
        assert 'wemo.kvs' in files and 'chip_counters.ini' in files and 'chip_factory.ini' in files
        report['persistent_files_bytes'] = files
        docker('exec', app_name, 'touch', '/tmp/wemo-reboot-probe')
    docker('rm', '-f', app_name)
    start_app()
    if args.firmware:
        docker('exec', app_name, 'test', '!', '-e', '/tmp/wemo-reboot-probe')
        report['fresh_tmp_after_restart_verified'] = True
    tool('restart-session-read', 'onoff', 'read', 'on-off', '1', '1')
    tool('restart-on-command', 'onoff', 'on', '1', '1')
    tool('restart-on-readback', 'onoff', 'read', 'on-off', '1', '1', expected=r'OnOff:\s*(TRUE|1)\b')
    if args.fit_check:
        assert max(s['cgroup_peak_bytes'] for s in report['resource_samples']) <= report['memory_limit_bytes']
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
                 ('research/firmware-commissioning-results.json' if args.firmware else
                  'research/legacy-time-results.json' if args.legacy_time else
                  'research/mips-fit-results.json' if args.fit_check else
                  'research/mips-commissioning-results.json'))).write_text(json.dumps(report, indent=2) + '\n')
    print('Local logs:', run_dir, flush=True)
