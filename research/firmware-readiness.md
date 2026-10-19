# Wemo firmware fit and integration assessment

The full MIPS Matter app now has a firmware integration profile, stripped payload packaging, bounded-memory protocol tests, and an unsigned candidate-image assembler. **Compatibility with the user's physical Wemo and complete firmware fit remain unconfirmed.** This work never contacts or modifies the Wemo.

## Hardware evidence and confidence

The previously observed installed release is SNSV2 11565, hardware revision v2. The retail F7C063 model is inferred, not label-confirmed. The available official Belkin source package is the older SNSV2 11420 release. Its normal `configs/snsv2` selects `WemoSNSV2`, whose image rule uses `MT7628snsv2.dts`:

- RAM configured by DTS: `0x4000000`, **64 MiB**.
- Partition address span: **16 MiB**. This is source configuration, not a measurement of the installed flash chip.
- Kernel region: `0x180000`, **1.5 MiB**.
- Rootfs A: `0x5e0000`, **5.875 MiB**; rootfs B: `0x5c0000`, **5.75 MiB**.
- Shared writable rootfs overlay: `0x50000`, **320 KiB**.
- Kernel source selection: **3.18.27**; the target config enables IPv6 and GPIO sysfs.

The normal DTS also retains an `en25q64` flash-compatible string despite its 16 MiB partition span, another reason to avoid treating this source as a hardware measurement. An 8 MiB flash DTS/profile also exists and uses different partitions. Its presence prevents assuming the normal profile is a verified map of this individual plug. Neither board identification nor physical RAM/flash limits were re-probed.

The independent [F7C063 teardown](https://sternumiot.com/iot-blog/mini-smart-plug-v2-vulnerability-buffer-overflow/) reports MT7688AN/24KEc and Linux 3.18.27, consistent with the source. Its storage capacity labels confuse bits with bytes: the named MX25L12835F is **128 Mbit = 16 MiB**, as the [manufacturer datasheet](https://www.macronix.com/Lists/Datasheet/Attachments/9173/MX25L12835F%2C%203V%2C%20128Mb%2C%20v1.7.pdf) states. Do not use that article's “128MB” flash or “512MB” DRAM wording as capacity evidence for this device.

## Flash layout discrepancy

The old DTS's aggregate `Firmware_2` region overlaps the start of `rootfs_data` by `0x20000`. Its `BuildFirmware/OF/WeMo` rule actually emits **7424 KiB (`0x740000`)** images, with the rootfs at image offset **`0x180000`**. That yields the conservative **`0x5c0000`** common rootfs budget and avoids the overlap.

`scripts/assemble_candidate.py` follows this smaller image size. It checks uImage header/data CRCs, Linux/MIPS/kernel/LZMA type and the vendor load/entry addresses. It checks the rootfs's SquashFS version, compression, block size, declared used length and size limit, then places both components at the vendor offsets with erased-flash (`0xff`) padding. These are format/size checks; they do not establish that the components boot on the Wemo. Tests reject corruption, wrong architecture, incompatible/truncated rootfs and overflow.

A real matching kernel and complete board rootfs have not been acquired or built. No synthetic fixture is presented as usable firmware. The assembler creates no Belkin update wrapper/signature and contains no device write command.

## Runtime measurements

[Bounded-memory results](mips-fit-results.json) test the stripped static MIPS outlet through commissioning, on/off/toggle, readbacks, callbacks and control after restart. Docker enforces **64 MiB with swap disabled**. Peak memory is recorded from the app container's cgroup, including the emulator and test-process overhead. `/proc/1/status` describes the host QEMU process; its multi-gigabyte reserved virtual address space is not guest RAM use.

The persistent-storage firmware profile also passed all 12 protocol/control checks with time64 fault injection, a 64 MiB no-swap limit, and a fresh `/tmp` on restart. Its measured peak app-container usage was **21,508,096 bytes (about 20.5 MiB)**. The retained test settings occupied 1,938 file bytes across four files before restart; filesystem allocation/eraseblock overhead and other device files are additional. See [firmware test results](firmware-commissioning-results.json).

Passing this test is encouraging capacity evidence under a modern host kernel. It does not account for the Wemo's kernel, Wi-Fi driver, vendor processes, filesystem caches or real CPU timings. It does not measure peak guest heap/stack separately or validate a stock-firmware coexistence configuration. The full Linux server uses an already working network interface; Wi-Fi credential setup is not implemented by this build.

[Time fallback results](legacy-time-results.json) run the same protocol tests with a locally patched QEMU returning MIPS `ENOSYS` for the Linux 5.1 time64 syscall range. The trace shows failed `clock_gettime64` calls followed by successful `clock_gettime` calls. This verifies musl's exercised fallback, not compatibility with every Linux 3.18 syscall. The [sanitized syscall audit](syscall-audit.json) records counts, memory peaks and emulator provenance. Builds/downloads are pinned; the QEMU archive's detached signature was not verified.

## Firmware integration artifacts

The `--firmware` MIPS build profile places the Linux factory, config and counters files in **`/etc/wemo-matter/state`**. The integration service uses the same directory for the Matter KVS. This deliberately avoids volatile `/tmp` and OpenWrt's frequently volatile `/var` path.

The OpenWrt recipe lives under `firmware/openwrt/wemo-matter-outlet/`. It takes an explicitly supplied prebuilt binary and SHA-256, then stages the executable, disabled UCI configuration and procd service. The service additionally requires a development-mode marker because this build retains SDK development identities and a simulated relay. No boot-enablement link or firmware installer is generated. The recipe has not yet been compiled as an OpenWrt package in a complete board build.

`scripts/build_firmware_payload.sh` strips the firmware-profile binary, stages these files, builds an XZ SquashFS 4.0 payload using 256 KiB blocks, unpacks it and compares the executable/config/service bytes. The resulting **`rootfs-payload.squashfs` is a component payload**, not a complete bootable rootfs. It lacks the kernel, init/base system, network setup and Wi-Fi integration. `research/hardware-fit.json` compares its size to the source layouts and explicitly leaves complete firmware fit unknown.

The measured firmware-profile executable is **2,088,300 bytes stripped**; the packaged XZ payload is **655,360 bytes (640 KiB)**. The conservative rootfs budget is **6,029,312 bytes (5.75 MiB)**. This leaves 5,373,952 bytes when considering the component alone, but shared compression and a complete rootfs build determine the real final size. No complete-image fit conclusion follows from that subtraction.

The app itself cannot fit in the 320 KiB writable overlay. It must be integrated into a rebuilt rootfs or another independently validated storage arrangement. Persistent settings must share whatever writable-overlay space remains after other files; a small test state size does not prove available space on the user's plug.

## Reproduce

After the existing SDK/toolchain preparation:

```sh
sh scripts/build_mips_app.sh --firmware
sh scripts/build_firmware_payload.sh
sh scripts/prepare_legacy_qemu.sh
python3 scripts/test_commissioning.py --target mips --fit-check --legacy-time --firmware
python3 scripts/audit_syscalls.py
python3 -m unittest discover -s tests -v
```

The final commissioning test mounts persistent state separately and gives the restarted container a fresh `/tmp`. It checks the temporary-file reset and subsequent Matter control without recommissioning. All networking is confined to an internal Docker network, with no published ports or home-device requests. Raw test state, protocol logs, downloaded sources and binary artifacts remain ignored locally.

## Remaining deployment blockers

1. Confirm exact board identity, RAM, flash map and matching 11565 firmware/recovery details.
2. Build and boot-test the actual board kernel/rootfs, including Wi-Fi and kernel/API compatibility.
3. Determine and verify relay/button pin mapping and active polarity. Vendor strings mention GPIO19/18 and legacy `/proc/GPIO*` paths; that is not sufficient evidence to drive a pin.
4. Measure real boot, runtime memory, timing and remaining persistent-storage space.
5. Implement production device identity, credential storage and network onboarding.
6. Establish an authorized, recoverable installation path. The inspected vendor updater verifies signatures; this repository does not have Belkin's signing key or a verified signed-update path.

Work can continue on offline component integration. A claim that this build will run on this exact Wemo, or that there is currently an installable update, would go beyond the evidence.

## Subsequent complete development image

The [full-system milestone](full-system.md) now supplies a real rebuilt board kernel and complete development rootfs with size-checked unsigned assembly. A separate Linux 3.18.27 MIPS guest passes Wi-Fi, Matter and relay-file tests. This advances the earlier component-only result; it does not resolve the physical board, production provisioning or installation/recovery requirements.
