"""Discover exact firmware, then send ONE TFTP RRQ for /etc/ver.txt only.

Never uploads, executes commands, changes configuration or reads flash nodes.
No retries; only accepts one small data block. No identifiers in the report.
"""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import socket
import struct
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--interface', required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
assert not args.output.exists(), 'Do not overwrite earlier evidence'
firmware = 'WeMo_WW_2.00.11565.PVT-OWRT-SNSV2'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError('Redirect refused')


opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
locations = {}
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.bind((args.interface, 0))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(args.interface))
    sock.settimeout(1)
    sock.sendto(b'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\n'
                b'MAN: "ssdp:discover"\r\nMX: 2\r\n'
                b'ST: urn:Belkin:device:controllee:1\r\n\r\n', ('239.255.255.250', 1900))
    end = time.monotonic() + 6
    while time.monotonic() < end:
        try:
            data, peer = sock.recvfrom(8192)
        except socket.timeout:
            continue
        for line in data.decode(errors='replace').splitlines():
            if line.lower().startswith('location:'):
                url = line.split(':', 1)[1].strip()
                u = urllib.parse.urlsplit(url)
                if (u.scheme == 'http' and u.hostname == peer[0]
                        and ipaddress.ip_address(peer[0]).is_private
                        and not u.username and not u.password and not u.query
                        and not u.fragment and u.path == '/setup.xml'):
                    locations[url] = peer[0]
targets = []
for url, host in locations.items():
    with opener.open(url, timeout=4) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        continue
    root = ET.fromstring(raw)
    value = next((e.text for e in root.iter() if e.tag.split('}')[-1] == 'firmwareVersion'), None)
    if value == firmware:
        targets.append((host, hashlib.sha256(raw).hexdigest()))
assert len(targets) == 1, 'Exactly one matching device required; no TFTP sent'
host, setup_digest = targets[0]
report = {'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
          'firmware': firmware, 'setup_sha256': setup_digest,
          'request': 'One TFTP RRQ /etc/ver.txt octet to UDP 69, no options or retries',
          'uploads': 0, 'device_commands': 0, 'firmware_or_bootloader_read': False}
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.bind((args.interface, 0))
    sock.settimeout(4)
    sock.sendto(b'\x00\x01/etc/ver.txt\x00octet\x00', (host, 69))
    try:
        data, peer = sock.recvfrom(517)
        if peer[0] != host or len(data) < 4:
            report['result'] = 'Unrelated or malformed reply; no followup sent'
        else:
            opcode, number = struct.unpack('!HH', data[:4])
            report.update(reply_opcode=opcode, reply_code_or_block=number)
            if opcode == 3 and number == 1 and len(data) < 516:
                sock.sendto(b'\x00\x04\x00\x01', peer)
                report.update(result='Small version-file read succeeded', bytes=len(data)-4,
                              content_sha256=hashlib.sha256(data[4:]).hexdigest(),
                              matches_expected_firmware=firmware.encode() in data[4:])
            elif opcode == 5:
                report['result'] = 'TFTP error response; no data acquired'
            else:
                sock.sendto(b'\x00\x05\x00\x00Read limit\x00', peer)
                report['result'] = 'Unexpected transfer; stopped at first packet'
    except socket.timeout:
        report['result'] = 'No TFTP response within four seconds'
    except ConnectionResetError:
        report['result'] = 'UDP request rejected (connection reset)'
report['limits'] = 'No reply cannot distinguish absent service from filtering. No bootloader or recovery claim.'
args.output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
