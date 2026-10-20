#!/usr/bin/env python3
"""Boot the real forensic driver stack on Malta with a kernel fake SPI controller."""
import hashlib
import json
from pathlib import Path
import re
import selectors
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
run_id = uuid.uuid4().hex[:8]
name = 'wemo-forensic-test-' + run_id
folder = ROOT / 'artifacts/forensic/tests' / run_id
folder.mkdir(parents=True)
command = ['docker', 'run', '--rm', '--name', name, '--network', 'none', '--cap-drop', 'ALL',
    '--security-opt', 'no-new-privileges', '--read-only', '--tmpfs', '/tmp',
    '-v', f'{ROOT}/artifacts/forensic/kernel-malta:/kernel:ro',
    'wemo-matter-board-builder:bookworm', 'qemu-system-mipsel',
    '-M', 'malta', '-cpu', '24KEc', '-m', '64M', '-nographic', '-monitor', 'none',
    '-vga', 'none', '-nic', 'none', '-no-reboot', '-kernel', '/kernel/vmlinux',
    '-append', 'init=/bin/sh root=/dev/mtdblock0 rw panic=1']
report = {'run_id': run_id, 'passed': False, 'physical_device_touched': False,
    'machine': 'Malta, 24KEc, 64MiB; not an MT7688 hardware emulator',
    'spi': 'Kernel fake controller; actual patched m25p80 + spi-nor + MTD stack',
    'network': 'none', 'host_storage_device_attached': False, 'tests': []}
process = None
start = time.monotonic()
try:
    with (folder / 'console.log').open('wb') as log:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        selector = selectors.DefaultSelector(); selector.register(process.stdout, selectors.EVENT_READ)
        buffer = b''; transcript = b''; ready_at = None
        while process.poll() is None:
            if time.monotonic() - start > 180: raise TimeoutError('Forensic boot exceeded three minutes')
            for key, _ in selector.select(timeout=.5):
                data = key.fileobj.read1(65536)
                if not data: continue
                log.write(data); log.flush(); transcript += data; buffer += data
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    marker = re.search(rb'WEMO_FORENSIC_TEST_PASS=([\w-]+)', line)
                    if marker:
                        label = marker[1].decode()
                        if label not in report['tests']: report['tests'].append(label); print('PASS:', label, flush=True)
            if b'WEMO_FORENSIC_TEST_FAIL=' in transcript or b'WEMO_FORENSIC_INIT_FAIL=' in transcript:
                raise RuntimeError('Forensic guest failure; inspect local console')
            if b'WEMO_FORENSIC_SUITE_PASS' in transcript and b'WEMO_FORENSIC_READY=' in transcript:
                if ready_at is None: ready_at = time.monotonic()
                if time.monotonic() - ready_at >= 3: break
        text = transcript.decode(errors='replace')
        actual = re.search(r'Kernel command line: ([^\r\n]+)', text)
        assert actual and actual[1] == 'console=ttyS0,115200 rdinit=/init init=/init panic=0', 'Firmware command line was not overridden'
        assert b'WEMO_FORENSIC_SUITE_PASS' in transcript and b'WEMO_FORENSIC_READY=' in transcript
        traffic = re.search(rb'WEMO_FORENSIC_SUITE_PASS calls=(\d+) forbidden=0', transcript)
        assert traffic, 'Forbidden SPI traffic observed'
        report['tests'].append('unsafe-bootloader-arguments-overridden')
        report['passed'] = True
        report['wall_seconds'] = round(time.monotonic() - start, 2)
        report['embedded_initramfs'] = True
        report['allowed_spi_transactions'] = int(traffic[1])
        report['forbidden_spi_transactions'] = 0
        report['register_write_opcodes_rejected'] = 256
        report['command_line'] = actual[1]
        report['kernel_sha256'] = hashlib.sha256((ROOT/'artifacts/forensic/kernel-malta/vmlinux').read_bytes()).hexdigest()
        report['initramfs_sha256'] = hashlib.sha256((ROOT/'artifacts/forensic/initramfs.cpio').read_bytes()).hexdigest()
finally:
    subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if process is not None and process.poll() is None: process.wait(timeout=10)
    (folder/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    if report['passed']: (ROOT/'research/forensic-ram-test.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Local console:', folder/'console.log', flush=True)
