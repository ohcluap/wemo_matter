# Read-only forensic RAM image

This milestone builds a separate **storage-read-only RAM-boot candidate** and
tests its actual MIPS kernel/MTD/SPI-NOR/m25p80 stack offline. It does not certify
an untested physical boot as having zero side effects. No Wemo network requests,
physical access, reboot, flash operation or settings change was performed.

The local artifact is
`artifacts/forensic/wemo-f7c063-forensic-ram.uImage`: **522,951 bytes**, SHA-256
`6fb929578887943b670ba1a8d0b9eb52bf5054f7f7d33cbb9eb05caec41eb805`.
It contains the vendor-profile board kernel, a constrained embedded device tree
and its identification-only initramfs. It is not a padded firmware-slot image,
stock signed update or installer. Binary artifacts stay ignored locally.

## What “read-only” means here

The contract is **no flash program, erase, status/configuration write or
persistent-filesystem write by this image**, and no relay/network-control
application. Sending a read command over SPI necessarily transmits command bytes;
the allowed flash commands are ordinary READ `0x03`, RDSR `0x05` and RDID `0x9f`.
CPU/RAM/UART, clocks, interrupts, pinmux and controller initialization still
change volatile machine state. Bootloader actions before kernel entry are
outside the image's control and remain unknown for this physical plug.

Accordingly, `installation_allowed` remains false. No absolute “nothing on the
hardware can change” or safe-deployment guarantee is made. No new hardware
execution is authorized by producing this artifact.

## Separate source fork and flash-driver protections

`scripts/prepare_forensic_kernel.py` prepares
`sources/linux-3.18.27-forensic` from the already patched SNSV2 11420 source.
It leaves the normal Matter/vendor source and built images unchanged. A dedicated
`CONFIG_WEMO_FORENSIC_RO` policy has no runtime switch or module parameter.

- The SPI-NOR probe skips the status-register clearing previously found for
  Macronix and related manufacturers. Chips needing more than 24-bit addressing
  are rejected before mode changes. Normal single-lane reads are forced; quad,
  dual and four-byte configuration changes are excluded.
- The m25p80 register-write callback always returns `-EROFS`. Program callbacks
  transfer zero bytes, and erase callbacks return `-EROFS`. Chunked writes are
  also blocked, preventing their original retry loop from issuing writes.
- Register reads accept only the exact JEDEC-ID/status shapes used by this
  driver. Data reads require opcode `0x03`, three address bytes, no dummy cycles
  and an in-range address. A program opcode cannot be passed through the read
  path. SPI read errors are propagated rather than reported as valid data.
- Before registration, MTD writeability is cleared. Direct MTD write/erase
  callbacks are denial routines, and lock/unlock callbacks are removed. This is
  stronger than a read-only filesystem mount or partition flag alone.

The underlying SPI controller is still required for actual reads. The offline
tests exercise the generic driver stack through a fake controller, not an
emulation of MT7688 electrical/MMIO behavior.

## Constrained startup

The embedded 38,684-byte initramfs contains only a static 37,976-byte `/init`,
three directories and a console device with verified major/minor **5:1**. There
is no shell, BusyBox, interpreter, network client, flashing utility, firmware
updater, environment tool, Matter app, relay backend or home Wi-Fi credential.

PID 1 mounts proc read-only, prints kernel identification and `/proc/mtd`, then
waits indefinitely. It does not read console commands, invoke a shell, dump
private flash contents, remount flash, synchronize storage or initiate a reboot.
The embedded command line overrides firmware-provided root/init options and
sets `panic=0` so a kernel panic does not schedule an automatic software reboot.
An inherited hardware watchdog could still reset a real board; that state has
not been measured or controlled.

The device tree includes one serial port and one SPI flash target, without a
hardcoded partition map. The whole flash size is obtained from JEDEC detection.
This would not reconstruct the installed firmware's partition map by itself.
GPIO banks, LEDs/buttons, watchdog, Ethernet/switch, USB, PCIe and SD nodes are
excluded. Unneeded I2C/PWM/etc. drivers are disabled. The older base DTS still
produces inherited structural/pinctrl naming warnings from `dtc`; compilation
and structural checks pass, but this is not hardware-binding validation.

Compiled configuration disables networking, block devices, modules, writable
flash filesystems, GPIO export/control drivers, watchdog, LED/input/framebuffer
support, raw memory access, spidev, configfs, sysfs/debugfs, crash logging, kexec
and serial Magic SysRq. The vendor's unconditional PWM/LED timer and DT GPIO
export registrations are excluded in this fork; their code is not re-enabled to
work around compile errors in the restricted configuration.

## Offline tests and artifact audit

[Guest results](forensic-ram-test.json) record run `f10c5a20`: **23 recorded checks**
in about 5.43 seconds on a 64 MiB, 24KEc Malta guest. Both its drivers and PID 1
are actual MIPS executables. Docker has no network or host storage devices;
QEMU has no NIC or disk and boots the embedded initramfs directly.

The kernel fake controller models a protected 16 MiB Macronix chip and generates
read data. It rejects and counts any command outside its read allowlist. The
test verifies:

- Actual JEDEC probe, read-only MTD registration, data read correctness, and
  propagation of a simulated SPI read error.
- Rejection through normal MTD write/erase APIs, direct MTD callbacks, lower
  program/erase hooks, **all 256 register-write opcodes**, non-whitelisted
  register-read opcodes, write-opcode misuse of the read path and four-byte mode.
- Unchanged protection status and **zero forbidden SPI transactions**. Six
  allowed transactions reached the fake bus.
- Embedded PID 1 startup despite deliberately unsafe firmware arguments
  (`init=/bin/sh`, flash root and writable-root options), which the compiled
  command-line override replaces.

The fake controller exists only in the Malta test kernel. Packaging verifies
that the board kernel has neither its configuration flag nor test symbols/data.
The board kernel is compiled and packaged but has **not been booted**.

[Build evidence](forensic-ram-build.json) records image/source/configuration
hashes and checks that both ELFs embed the current initramfs, the archive has no
extra payload or second archive, console identity is correct, forbidden options
are disabled, the board DTB omits unwanted devices, and compiled deny routines
make no function calls. The LZMA payload is round-trip checked; the RAM uImage
has normal header/data checksums. These checks do not create a vendor signature.

Four Python policy/archive tests also pass, covering unsafe configurations,
absence of the RO gate, accidental inclusion of the test controller, traversal,
duplicates, truncation and an appended second archive. The prior normal Matter
image remains byte-for-byte unchanged; its flash driver is still the normal
development variant, not this forensic fork.

## Reproduce

With the existing vendor/OpenWrt sources and local builder image prepared:

```sh
sh scripts/build_forensic_ram.sh malta
sh scripts/build_forensic_ram.sh board
python3 scripts/test_forensic_ram.py
sh scripts/package_forensic_ram.sh
python3 -m unittest discover -s tests -p test_forensic_policy.py -v
```

Build/test containers use `--network none`. The test runner terminates the
emulator from the host after success rather than making the guest reboot. The
packager checks that successful test hashes match the selected guest kernel and
initramfs, and refuses to run with Python assertions disabled. Build procedure
and inputs are recorded; whole-kernel byte-identical reproducibility across build
times/hosts is not claimed.

The remaining prerequisites for a physical experiment are an exact bootloader
transcript and proven RAM-load semantics, review of pre-entry environment writes
and inherited watchdog/relay state, and validation of the actual SPI controller,
pinmux and board behavior. That is a later, separately authorized hardware phase.
No device-loading instructions or automatic installer are supplied here.
