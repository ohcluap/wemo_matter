"""Read advertised Wemo descriptions only; never invoke SOAP actions.

Raw device identifiers are not saved. Output records service/action schemas.
"""
import argparse
import hashlib
import ipaddress
import json
import socket
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


def field(root, name):
    return next((e.text for e in root.iter() if e.tag.split('}')[-1] == name), None)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('Redirect refused')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interface', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('Refusing to overwrite existing evidence')
    locations = set()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((args.interface, 0))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(args.interface))
        sock.settimeout(1)
        for st in ('urn:Belkin:device:controllee:1', 'urn:Belkin:service:basicevent:1'):
            request = ('M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\n'
                       'MAN: "ssdp:discover"\r\nMX: 3\r\nST: ' + st + '\r\n\r\n')
            sock.sendto(request.encode(), ('239.255.255.250', 1900))
        end = time.monotonic() + 10
        while time.monotonic() < end:
            try:
                data, peer = sock.recvfrom(65535)
            except socket.timeout:
                continue
            for line in data.decode('utf-8', 'replace').split('\r\n'):
                if not line.lower().startswith('location:'):
                    continue
                url = line.split(':', 1)[1].strip()
                p = urllib.parse.urlsplit(url)
                if (p.scheme == 'http' and p.hostname == peer[0]
                        and ipaddress.ip_address(p.hostname).is_private
                        and not p.username and not p.password
                        and p.path == '/setup.xml' and not p.query):
                    locations.add(url)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def read(url):
        with opener.open(url, timeout=5) as response:
            data = response.read(262145)
        if len(data) > 262144:
            raise RuntimeError('Descriptor too large')
        return ET.fromstring(data), hashlib.sha256(data).hexdigest()

    devices = []
    for location in sorted(locations):
        root, digest = read(location)
        if field(root, 'firmwareVersion') == 'WeMo_WW_2.00.11565.PVT-OWRT-SNSV2':
            devices.append((location, root, digest))
    if len(devices) != 1:
        raise RuntimeError('Expected one matching device, found %d' % len(devices))
    location, root, digest = devices[0]
    report = {'observed_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'firmware': field(root, 'firmwareVersion'),
              'scope': 'SSDP discovery and HTTP GET of advertised XML descriptions only',
              'setup_sha256': digest, 'services': []}
    allowed = {'/setupservice.xml', '/timesyncservice.xml', '/eventservice.xml',
               '/firmwareupdate.xml', '/rulesservice.xml', '/metainfoservice.xml',
               '/remoteaccess.xml', '/deviceinfoservice.xml', '/smartsetup.xml', '/manufacture.xml'}
    for service in root.iter():
        if service.tag.split('}')[-1] != 'service':
            continue
        url = urllib.parse.urljoin(location, field(service, 'SCPDURL'))
        p = urllib.parse.urlsplit(url)
        if p.netloc != urllib.parse.urlsplit(location).netloc or p.path not in allowed or p.query:
            raise RuntimeError('Unapproved descriptor URL')
        scpd, digest = read(url)
        actions = []
        for action in scpd.iter():
            if action.tag.split('}')[-1] != 'action':
                continue
            arguments = []
            for arg in action.iter():
                if arg.tag.split('}')[-1] == 'argument':
                    arguments.append({key: field(arg, key) for key in ('name', 'direction', 'relatedStateVariable')})
            actions.append({'name': field(action, 'name'), 'arguments': arguments})
        report['services'].append({'type': field(service, 'serviceType'),
                                   'descriptor': p.path, 'sha256': digest, 'actions': actions})
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    for service in report['services']:
        print(service['type'] + ': ' + ', '.join(a['name'] for a in service['actions']))


if __name__ == '__main__':
    main()
