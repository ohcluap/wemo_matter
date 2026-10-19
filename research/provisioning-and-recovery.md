# Wi-Fi provisioning and install/recovery assessment

This milestone adds **OS-level WPA2 credential provisioning** to the development
rootfs. It does not add Google Home/BLE credential transfer or a Matter
NetworkCommissioning Wi-Fi driver. Matter still uses on-network commissioning
after Linux establishes the Wi-Fi connection. All tests use isolated virtual
radios; the physical plug has not been contacted or changed.

## Credential transaction

`port/wifi_provision.c` builds as a static MIPS24KEc soft-float executable. A local
development caller supplies the supplicant control socket, an existing private
state directory and a trial timeout. Credentials arrive on standard input as two
newline-terminated lines followed by EOF: SSID and passphrase/hex PSK. They never
appear in command-line arguments or the tool's diagnostics. This is a development
CLI, not a web service or an end-user onboarding screen.

The tool validates lengths and rejects control characters and trailing input.
SSID bytes are hex encoded; printable ASCII passphrases of 8–63 bytes are converted
to a 32-byte WPA2 PSK using the pinned wpa_supplicant 2.11 PBKDF2/HMAC-SHA1 sources.
A 64-digit hexadecimal PSK is also accepted. The supplicant's quoted passphrase
format is not shell escaping; deriving a hex key avoids ambiguous quotes,
backslashes and comment characters. The key remains a credential equivalent to
the password and must be protected. There is no encryption-at-rest claim.

The state directory must belong to the caller with no group/other permissions.
An exclusive lock prevents simultaneous transactions. The existing `wifi.conf`
must be a private regular file if present; symlinks are rejected. The tool writes
and fsyncs `wifi.pending` with mode 0600 before trying a new supplicant network.
It uses the Unix control socket directly, without a shell or `SAVE_CONFIG`.

Only `wpa_state=COMPLETED` for the exact candidate network ID permits an atomic
rename to `wifi.conf`, followed by directory fsync. Failed association, timeout
or a handled SIGINT/SIGTERM removes the candidate network, requests selection of
the prior connected network, deletes the pending file and keeps the old config.
Control-socket failure can prevent runtime rollback; the diagnostic explicitly
requires restarting supplicant from the committed config in that case. No saved
configuration is replaced merely because commands were accepted.

After SIGKILL/power loss before rename, the old committed file remains the startup
choice; the next transaction discards the stale pending file. The in-memory radio
selection might still be the trial network until supplicant restarts. After
rename but a directory-fsync error, the tool returns a separate durability-uncertain
status rather than claiming success. Atomic-rename/fsync behavior has not been
tested on the plug's actual flash filesystem or under physical power failure.

Restart supplicant with **only `wifi.conf`**, never `wifi.pending`. The generated
config uses `ctrl_interface=/tmp/wpa`, RSN/WPA-PSK and `update_config=0`.
Association verifies the Wi-Fi key, not DHCP, Internet access, DNS, IPv6 or Matter
reachability. The guest separately checks IPv6 and Matter traffic after restart.

## Offline validation

`scripts/test_provisioning.sh` runs deterministic Linux control-socket tests with
the same C source and crypto implementation. It covers independent Python PBKDF2
comparison (including punctuation and a 63-byte password), malformed inputs,
secret-free diagnostics, timeouts, cancellation, competing callers, SIGKILL,
stale transactions, private permissions, symlink rejection and missing sockets.
Together with archive/image/range tests, results are recorded in
`provisioning-unit-tests.txt`.

`scripts/test_system_boot.py` boots the **full 64 MiB MIPS Linux guest**, using
mac80211_hwsim radios in separate network namespaces. It verifies wrong-password
trial/rollback, successful atomic commit, input/path rejection, supplicant restart
from the committed configuration, IPv6 across Wi-Fi, Matter commissioning,
on/off/toggle, relay-file readback, rejection of a failed relay write and retained
commissioning after app restart. See `system-boot-results.json` for exact tests,
artifact hashes and measured runtime. This is not MT7688 board emulation.

The public test SSID is `WemoOfflineLab`; the public test password is
`offline-"lab\#-2026`. AP/station baseline fixtures store its derived hex key.
The transaction supplies the original password and checks the derived key before
restarting supplicant. These fixtures are excluded from the board rootfs.
Docker uses `--network none`; no host Wi-Fi interface is exposed.

## Vendor update and recovery findings

`install-recovery-audit.json` records hashes and line references from the **older
11420 SNSV2 GPL source**, not the installed 11565 firmware:

| Source observation | Consequence |
| --- | --- |
| `firmware_update.sh` checks GPG signatures, product name and checksum | Our unsigned candidate is not a valid stock update. Packaging a uImage/SquashFS does not provide a Belkin signature. |
| Stock states 0/1 write B and set state 3; states 2/3 write A and set state 1 | The source describes inactive-slot updates, but its fallback-to-A behavior for unknown state is unsafe for a custom installer. Our analysis helper rejects unknown states and unconfirmed trial states 1/3. |
| Slot write precedes environment updates; several environment command results are unchecked | Do not infer atomic updates or power-loss safety from the A/B layout. |
| `update_test.sh` waits for vendor startup flags and commits 1→0 or 3→2 | Our minimal rootfs does not implement that vendor health contract. A booting custom image is not evidence of safe rollback. |
| Health failure reboots with a comment saying U-Boot switches partitions | Exact bootloader behavior, retry count and power-loss handling are not established by that comment. We do not emulate or claim them. |
| SNSV2 boot script derives environment storage from `/proc/mtd` | Never assume an MTD number or copy an environment-write recipe from another board. |

The 16 MiB source layout places conservative A at `[0x50000,0x7b0000)` and B at
`[0x7c0000,0xf00000)`. The 0x740000-byte candidate fits both with 64 KiB erase
rounding. A retains an additional 128 KiB margin. The DTS aggregate `Firmware_2`
instead extends to `0xf20000`, overlapping 128 KiB of `rootfs_data`. Range tests
reject that larger B envelope and even a one-byte overflow that rounds into the
next erase block. These are **source-layout calculations**, not confirmed device
geometry. The DTS's `en25q64` identifier and 16 MiB partition span also disagree.

The [Wemo Insight port author's recovery write-up](https://sven-schwermer.de/wemo)
documents serial/TFTP and a modified `bootm` for **F7C029de/RT5350**. It is useful
background but does not verify a Mini/F7C063/MT7688 recovery path. Even a command
named `bootm` must not be assumed to perform a read-only RAM boot on this plug.
The [Mini v2 teardown](https://sternumiot.com/iot-blog/mini-smart-plug-v2-vulnerability-buffer-overflow/)
describes physical UART and flash extraction. It does not establish a remote,
no-opening installation or recovery method for our device.

## Proposed sequence before any future installation

There is **no verified safe installation procedure yet**. The following are
evidence requirements for a later hardware phase, not commands to execute now:

1. Confirm label/revision, exact flash geometry, erase size, partition offsets,
   bootloader version/help, environment and active/known-good slot. Resolve the
   8/16 MiB and aggregate-partition ambiguities first.
2. Obtain two independently read, matching complete original flash backups and
   preserve them off-device with hashes, including bootloader, environment,
   calibration, settings and identities. A downloadable stock update alone is
   not a complete backup of this device's unique data.
3. Establish and rehearse an independent recovery transport that remains usable
   when Linux and Wi-Fi fail. Verify exact-device RAM-only loading/booting if
   available; do not assume TFTP or ordinary boot commands are write-free. UART
   or direct SPI recovery may require opening the enclosure and separate later
   authorization; neither has been attempted or proven here.
4. With an independently recoverable board, test a RAM-only development boot
   before considering persistent writes. The present board rootfs is not a
   verified RAM-boot image: radio calibration and boot arguments still depend on
   actual hardware and must be reviewed.
5. Only after board boot, physical radio/relay, persistent state, identity,
   watchdog and health/rollback behavior are validated, design an installer
   restricted to the measured inactive slot. Preserve the known-good slot and
   all protected regions; verify written content before a trial boot. Rehearse
   failure at each update stage and demonstrate recovery before calling it safe.

The audit intentionally outputs `installation_allowed: false`. It provides no
device access, flash/environment-write commands or generated installer. The
board image retains development serial startup, disabled radio/physical relay
autoload and no production flash-overlay mounting. Google Home provisioning and
real hardware installation remain separate unfinished work.

## Reproduction

With the source/toolchain images prepared as in `full-system.md`:

```sh
sh scripts/test_provisioning.sh
sh scripts/build_system_rootfs.sh
python3 scripts/test_system_boot.py
python3 scripts/package_system_image.py
python3 scripts/audit_install_recovery.py
python3 scripts/record_system_provenance.py
```

All of these commands operate on local sources/artifacts or isolated guests.
