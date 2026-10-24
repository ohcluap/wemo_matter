"""Smoke-test the MIPS app on container loopback, never a physical device."""
import argparse
import json
import pathlib
import signal
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('binary')
parser.add_argument('report')
args = parser.parse_args()
report_path = pathlib.Path(args.report)
log_path = report_path.with_suffix('.log')
result = {'test': 'MIPS loopback startup and SIGTERM shutdown', 'commissioning_tested': False,
          'physical_device_tested': False, 'passed': False}
with log_path.open('w') as log:
    process = subprocess.Popen(['qemu-mipsel', '-cpu', '24KEc', args.binary,
                                '--interface-id', 'lo'], stdout=log, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 20
        bound = False
        peak_rss = 0
        while time.monotonic() < deadline and process.poll() is None:
            status = pathlib.Path(f'/proc/{process.pid}/status').read_text()
            for line in status.splitlines():
                if line.startswith('VmRSS:'):
                    peak_rss = max(peak_rss, int(line.split()[1]))
            for table in ('/proc/net/udp', '/proc/net/udp6'):
                bound |= any(row.split()[1].endswith(':15A4')
                             for row in pathlib.Path(table).read_text().splitlines()[1:])
            if bound:
                time.sleep(3)
                break
            time.sleep(0.2)
        result.update(udp_5540_bound=bound, stayed_running=process.poll() is None,
                      qemu_peak_sampled_rss_kib=peak_rss,
                      memory_note='QEMU host RSS is not device RAM usage')
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
        result['exit_code'] = process.wait(timeout=10)
        result['passed'] = bound and result['stayed_running'] and result['exit_code'] == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        report_path.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
raise SystemExit(0 if result['passed'] else 1)
