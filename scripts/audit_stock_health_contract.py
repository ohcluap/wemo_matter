"""Read archived stock startup evidence; never run vendor code or contact a device."""
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'wemo_gpl_snsv2_package-11420/'
TARGETS = {
    'package/belkin/WeMo_SNSV2/files/sbin/update_test.sh':
        ['sleep 60', '/tmp/*.starting', 'fw_setenv bootstate', 'fw_setenv check_boot'],
    'package/belkin/WeMo_SNSV2/files/etc/init.d/wemo':
        ['.starting'],
    'target/linux/ramips/mt7628/WemoSNSV2/base-files/etc/init.d/boot':
        ['checkboot=', 'checkboot}x', 'boot_state}x', '/sbin/update_test.sh',
         'mount_root', 'Belkin_settings'],
    'target/linux/ramips/dts/MT7628snsv2.dts':
        ['rootfs_data', 'Belkin_settings'],
}


def main():
    evidence = []
    with tarfile.open(ROOT / 'artifacts/vendor-inner.tar.gz', 'r:gz') as archive:
        for member in archive:
            relative = member.name.removeprefix(PREFIX)
            if relative not in TARGETS or not member.isfile():
                continue
            data = archive.extractfile(member).read()
            lines = data.decode().splitlines()
            evidence.append({
                'member': member.name,
                'sha256': hashlib.sha256(data).hexdigest(),
                'lines': [{'number': i + 1, 'text': line}
                          for i, line in enumerate(lines)
                          if any(needle in line for needle in TARGETS[relative])],
            })
    if len(evidence) != len(TARGETS):
        raise RuntimeError('Missing required archived source')
    report = {
        'scope': 'Static 11420 archive evidence; not verified on installed 11565',
        'physical_device_contacted': False,
        'source_evidence': evidence,
        'binary_evidence': {
            'file': 'artifacts/binary-analysis/libRemoteAccess.so',
            'sha256': hashlib.sha256((ROOT / 'artifacts/binary-analysis/libRemoteAccess.so').read_bytes()).hexdigest(),
            'function': 'core_init_early',
            'command_string_address': '0x32af8',
            'command': 'rm -f /tmp/*.starting',
            'call_site': 'system loaded at 0xeac8; jalr at 0xeacc; delay slot sets argument to 0x30000+0x2af8',
            'disassembly': 'artifacts/binary-analysis/core-init-startup-flags.txt',
        },
        'findings': [
            'Boot invokes update_test only with check_boot=1 and bootstate=1 or 3.',
            'update_test uses presence of startup flags after its wait, not a direct Matter or LAN reachability check.',
            'Archived core_init_early removes all matching startup flags, not just the stock app flag.',
            'A custom Matter .starting flag can therefore be removed by stock initialization; it is not an independent safety gate.',
            'The source has shared overlay/settings regions. Switching firmware slots alone does not establish removal of persistent additions stored there.',
        ],
        'next_action': 'Keep recovery independent of stock startup flags. Establish exact-version startup and an out-of-band rollback or disable mechanism before any app installation.',
        'limitations': [
            'Static call site does not prove runtime timing or reachability on the physical device.',
            'No exact bootloader, backup, restoration trial or safe shell established.',
            'No vendor code executed; no state or firmware changed on the device.',
        ],
        'recovery_verified': False,
    }
    destination = ROOT / 'research/stock-health-contract.json'
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(destination)


if __name__ == '__main__':
    main()
