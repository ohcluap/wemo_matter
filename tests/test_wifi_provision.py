"""Run with WEMO_WIFI_TEST_BINARY set, in the isolated Linux test container.

The control socket is a deterministic fake for error/cancellation edge cases.
Real association is covered by the full MIPS guest; both suites derive keys.
"""
import hashlib
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import threading
import unittest

BINARY = os.environ.get('WEMO_WIFI_TEST_BINARY')
PSK = 'a1' * 32


class Supplicant:
    def __init__(self, path, success):
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.socket.bind(str(path))
        self.socket.settimeout(.1)
        self.commands = []
        self.selected = 0
        self.success = success
        self.stop = threading.Event()
        self.trial = threading.Event()
        self.thread = threading.Thread(target=self.serve)
        self.thread.start()

    def serve(self):
        while not self.stop.is_set():
            try:
                data, address = self.socket.recvfrom(4096)
            except socket.timeout:
                continue
            command = data.decode()
            self.commands.append(command)
            reply = 'OK\n'
            if command == 'STATUS':
                ready = self.success or self.selected == 0
                reply = f'wpa_state={"COMPLETED" if ready else "SCANNING"}\nid={self.selected}\n'
            elif command == 'ADD_NETWORK':
                reply = '1\n'
            elif command.startswith('SELECT_NETWORK '):
                self.selected = int(command.split()[1])
                if self.selected == 1:
                    self.trial.set()
            try:
                self.socket.sendto(reply.encode(), address)
            except FileNotFoundError:
                pass  # Client cancellation may remove its socket.

    def close(self):
        self.stop.set()
        self.thread.join(3)
        self.socket.close()


@unittest.skipUnless(BINARY, 'Set WEMO_WIFI_TEST_BINARY to the Linux development binary')
class ProvisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / 'state'
        self.state.mkdir(mode=0o700)
        self.config = self.state / 'wifi.conf'
        self.config.write_text('original-known-good\n')
        self.config.chmod(0o600)
        self.server = None

    def tearDown(self):
        if self.server:
            self.server.close()
        self.temp.cleanup()

    def start(self, success=True):
        self.server = Supplicant(self.root / 'control', success)

    def run_tool(self, credentials=None):
        return subprocess.run([BINARY, str(self.root / 'control'), str(self.state), '1'],
                              input=credentials or f'Lab "ssid\\#\n{PSK}\n',
                              text=True, capture_output=True, timeout=10)

    def test_hex_key_and_ssid_cannot_inject_config_or_commands(self):
        self.start()
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.config.read_text()
        self.assertIn('ssid=' + b'Lab "ssid\\#'.hex(), text)
        self.assertIn('psk=' + PSK, text)
        self.assertNotIn(PSK, result.stdout + result.stderr)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        self.assertNotIn('SAVE_CONFIG', self.server.commands)
        self.assertFalse((self.state / 'wifi.pending').exists())

    def test_timeout_preserves_config_and_restores_previous_selection(self):
        self.start(False)
        result = self.run_tool()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.config.read_text(), 'original-known-good\n')
        self.assertEqual(self.server.selected, 0)
        self.assertIn('REMOVE_NETWORK 1', self.server.commands)
        self.assertFalse((self.state / 'wifi.pending').exists())

    def test_cancel_preserves_config_and_restores_previous_selection(self):
        self.start(False)
        process = subprocess.Popen([BINARY, str(self.root / 'control'), str(self.state), '30'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            process.stdin.write(f'Lab\n{PSK}\n'.encode())
            process.stdin.close()
            self.assertTrue(self.server.trial.wait(5))
            process.send_signal(signal.SIGTERM)
            self.assertEqual(process.wait(5), 1)
            self.assertEqual(self.server.selected, 0)
            self.assertEqual(self.config.read_text(), 'original-known-good\n')
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            process.stdout.close()
            process.stderr.close()

    def test_malformed_input_never_contacts_supplicant(self):
        self.start()
        for credentials in ('Lab\nshort\n', 'X'*33 + '\n' + PSK + '\n',
                            'Lab\n' + PSK + '\nSELECT_NETWORK 0\n', 'Lab\n' + 'z'*64 + '\n'):
            with self.subTest(credentials_length=len(credentials)):
                self.assertEqual(self.run_tool(credentials).returncode, 2)
        self.assertEqual(self.server.commands, [])

    def test_symlink_config_rejected_before_radio_change(self):
        self.start()
        self.config.unlink()
        target = self.root / 'target'
        target.write_text('do-not-change')
        self.config.symlink_to(target)
        self.assertEqual(self.run_tool().returncode, 2)
        self.assertEqual(target.read_text(), 'do-not-change')
        self.assertEqual(self.server.commands, [])

    def test_permissive_state_directory_rejected(self):
        self.start()
        self.state.chmod(0o755)
        self.assertEqual(self.run_tool().returncode, 2)
        self.assertEqual(self.server.commands, [])

    def test_missing_socket_keeps_committed_config(self):
        self.assertEqual(self.run_tool().returncode, 1)
        self.assertEqual(self.config.read_text(), 'original-known-good\n')
        self.assertFalse((self.state / 'wifi.pending').exists())

    def test_stale_pending_file_cannot_become_committed(self):
        self.start()
        (self.state / 'wifi.pending').write_text('stale-unfinished-credentials')
        self.assertEqual(self.run_tool().returncode, 0)
        self.assertNotIn('stale', self.config.read_text())

    def test_special_passphrase_and_max_length_match_independent_pbkdf2(self):
        self.start()
        for password in ('offline-"lab\\#-2026', 'a'*63):
            with self.subTest(length=len(password)):
                result = self.run_tool('Lab\n' + password + '\n')
                self.assertEqual(result.returncode, 0, result.stderr)
                expected = hashlib.pbkdf2_hmac('sha1', password.encode(), b'Lab', 4096, 32).hex()
                self.assertIn('psk=' + expected, self.config.read_text())
                self.assertNotIn(password, result.stdout + result.stderr)

    def test_lock_contention_and_abrupt_stop_leave_known_good_on_disk(self):
        self.start(False)
        process = subprocess.Popen([BINARY, str(self.root / 'control'), str(self.state), '30'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            process.stdin.write(f'Lab\n{PSK}\n'.encode())
            process.stdin.close()
            self.assertTrue(self.server.trial.wait(5))
            self.assertEqual(self.run_tool().returncode, 2)
            process.kill()
            process.wait(5)
            self.assertEqual(self.config.read_text(), 'original-known-good\n')
            self.assertTrue((self.state / 'wifi.pending').exists())
            # Emulate restarting supplicant with its committed config, then
            # verify the next transaction discards the abandoned pending file.
            self.server.selected = 0
            self.server.success = True
            self.assertEqual(self.run_tool().returncode, 0)
            self.assertFalse((self.state / 'wifi.pending').exists())
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            process.stdout.close()
            process.stderr.close()
