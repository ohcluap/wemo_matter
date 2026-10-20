from pathlib import Path
import stat
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from package_forensic_ram import REQUIRED, config_audit, cpio_entries


def entry(name, mode=0, payload=b''):
    values = [1, mode, 0, 0, 1, 0, len(payload), 0, 0, 0, 0, len(name)+1, 0]
    data = b'070701' + ''.join(f'{v:08x}' for v in values).encode() + name.encode() + b'\0'
    data += b'\0' * (-len(data) % 4)
    data += payload
    return data + b'\0' * (-len(data) % 4)


class ForensicPolicyTests(unittest.TestCase):
    def config(self):
        return '\n'.join('CONFIG_' + key + '=y' for key in REQUIRED)

    def test_mutating_or_escape_interfaces_fail_closed(self):
        for key in ('BLOCK', 'WATCHDOG', 'GPIO_SYSFS', 'SPI_SPIDEV', 'MODULES', 'MAGIC_SYSRQ', 'CRASHLOG'):
            for value in ('y', 'm'):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    config_audit(self.config() + '\nCONFIG_' + key + '=' + value, 'board')

    def test_ro_gate_is_mandatory_and_test_controller_must_not_ship(self):
        self.assertFalse(config_audit(self.config(), 'board')['fake_controller'])
        with self.assertRaises(ValueError):
            config_audit(self.config().replace('CONFIG_WEMO_FORENSIC_RO=y', ''), 'board')
        with self.assertRaises(ValueError):
            config_audit(self.config() + '\nCONFIG_WEMO_FORENSIC_TEST=y', 'board')

    def test_archive_metadata_and_hidden_second_archive(self):
        raw = entry('init', stat.S_IFREG | 0o500, b'init-code') + entry('TRAILER!!!')
        self.assertEqual(cpio_entries(raw)['init']['size'], 9)
        with self.assertRaises(ValueError):
            cpio_entries(raw + entry('bin/sh', stat.S_IFREG | 0o755, b'shell'))

    def test_archive_traversal_duplicates_and_truncation(self):
        for raw in (entry('../escape') + entry('TRAILER!!!'),
                    entry('init') + entry('init') + entry('TRAILER!!!'),
                    entry('init', stat.S_IFREG, b'bytes')[:-3]):
            with self.assertRaises(ValueError):
                cpio_entries(raw)
