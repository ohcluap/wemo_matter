# Wemo Matter feasibility research

Offline investigation of running a Matter application on a stock Wemo, without opening the enclosure or flashing firmware. Research date: 2026-10-18.

**Result: no verified way to load and run our code has been found. The exact installed firmware has not been acquired.** This is a bounded preliminary assessment, not proof that a network execution path cannot exist.

## Device and acquisition

Prior read-only device observations identify firmware `WeMo_WW_2.00.11565.PVT-OWRT-SNSV2` and hardware revision `v2`. The user-supplied exterior-label photo on 2026-10-19 confirms **Wemo Mini, model F7C063** (FCC ID `K7SF7C063`). The label does not identify its bootloader or flash layout. The API's model number `1.0` is generic. See [sanitized device record](research/device.json).

Read-only network checks on 2026-10-19 confirmed the **Wemo Mini** product family through metadata and HomeKit advertising. The retail part number and bootloader version were not exposed by the checked identity interfaces. See [network identification evidence and limits](research/network-identification.md). No device settings or firmware were changed.

[Belkin's official GPL catalog](https://www.belkin.com/it/support-article/?articleNum=51238) provides an F7C063 **2.00.11420** source package. We downloaded and statically inspected that older same-family release. It is **not** a matching 11565 update image, and should not be installed on this device based on this research.

| Artifact | Provenance / identity |
| --- | --- |
| Official package | [wemo_gpl_snsv2_package-11420.tar.gz](https://s3.belkin.com/support/assets/wemo/gpl/wemo_gpl_snsv2_package-11420.tar.gz) |
| Outer bytes | 307286090 |
| Outer SHA-256 | `4f4648e8765a891bc995c868a6ebeb835a5d4c1e8d92f4fcd1e0162d9a1955e6` |
| Nested source archive SHA-256 | `bef5e0a749e904b278849355dc9f5e245260350f5992c2bcd322bcba0968f122` |
| Exact 11565 image | Not located |

The outer package contains a license PDF, README, and nested source archive. The inner archive has 7688 entries, including compiled vendor application binaries and libraries. Artifact hashes record the downloaded bytes; they are not independent vendor signature verification.

The legacy firmware host failed DNS resolution on this Mac. A Wayback CDX request timed out, so archived availability remains unknown. Exact-version web/GitHub searches did not locate a matching download. See [acquisition checks](research/acquisition-checks.json). These observations do not establish that all firmware mirrors are unavailable.

## Static findings

Paths below are relative to the extracted 11420 source tree, locally `sources/snsv2-11420/`. Findings are limited to that release unless explicitly identified as prior device observations.

| Finding | Evidence | Implication |
| --- | --- | --- |
| MT7688 platform | `target/linux/ramips/mt7628/profiles/01-wemo.mk:9`; binary ELF headers | Existing vendor binaries are 32-bit little-endian MIPS, dynamically linked against uClibc. A Mac/ARM or ordinary desktop Linux Matter executable cannot simply run here. |
| SSH excluded from normal product profile | `01-wemo.mk:10`; `GNUmakefile:20–41` | Development build explicitly adds Dropbear; production recipe does not. A build option is not a way to enable SSH on the installed device. |
| Ordinary Telnet installation disabled | `package/utils/busybox/Makefile:113` | Telnet init-script installation is commented out. Generic failsafe Telnet code also exists, but this does not establish normal LAN access or a safe way to enter it. |
| TFTP utilities configured | `configs/snsv2:31–37` | Presence of utilities does not demonstrate a listening server, upload permissions, or code execution. The prior TCP-only check says nothing about UDP TFTP. |
| Fixed vendor startup | `package/belkin/WeMo_SNSV2/files/etc/init.d/wemo:27`; `files/sbin/startWemo.sh:3–5` | Startup launches vendor processes. No user application/plugin launch interface was identified in the inspected startup files. |
| Firmware updater verifies signatures, then writes flash | `files/sbin/firmware_update.sh:39–100,187,201` | This is a firmware-replacement path, not a RAM-only application loader. No signature bypass is established. |
| Diagnostic action exists | `files/sbin/web/eventservice.xml:502`; `files/lib/libUPnPHndlr.so` strings | `StartIperf` exists as an action/symbol. That does not imply arbitrary command execution; production build recipe also removes iperf. |
| Vendor application uses shared libraries | `files/sbin/wemoApp`, `files/lib/*.so` | Binary strings include command-execution imports and internal file paths. Imports alone do not establish remotely controllable arguments or an exploitable path. |

The package includes a 20919-byte `wemoApp` ELF and vendor libraries, with no ELF section-header table reported by `file`. This pass examined ELF identification, selected strings, startup/build/update scripts, and the archive inventory. It did **not** disassemble all functions, emulate the application, audit every dependency, or test exploitation. See [binary metadata and selected evidence](research/binary-evidence.json).

Prior targeted device port checks found only port 49153 reachable among eight tested TCP ports. SSH/Telnet were not reachable in that check. This is not a full port scan or proof of the running service configuration.

## What this means for Matter

Running a Matter process directly on the Wemo would first require an authorized mechanism to place and execute a compatible binary. None is verified here. A RAM-only launch, even if eventually found, would disappear on reboot unless an additional startup/persistence mechanism existed. A practical port would also need measured free RAM/storage, working IPv6/mDNS, a compatible toolchain and crypto stack, relay integration, and safe coexistence with vendor processes. This pass establishes none of those resource requirements.

The [published Mini v2 security research](https://sternumiot.com/iot-blog/mini-smart-plug-v2-vulnerability-buffer-overflow/) is a lead for further offline comparison, not evidence that our installed version can run code. Its physical debugging workflow does not satisfy the current no-opening constraint. No published payload was used against the device.

The next useful input is an authentic **11565 SNSV2 image** or vendor-supplied matching binaries/source. With that, compare action handlers and service configuration offline and evaluate potential launch paths. Do not substitute a different model/version, initiate a downgrade, or infer code execution from diagnostic action names. A separate Matter bridge remains a different architecture; this repository does not implement one or claim native Matter support.

## Reproduce the offline inspection

Requires Python 3, curl, and standard `file`/`strings` tools. Never execute downloaded scripts, binaries, or make targets.

```sh
mkdir -p artifacts sources
curl --fail --location 'https://s3.belkin.com/support/assets/wemo/gpl/wemo_gpl_snsv2_package-11420.tar.gz' --output artifacts/wemo_gpl_snsv2_package-11420.tar.gz
python3 scripts/inspect_archive.py artifacts/wemo_gpl_snsv2_package-11420.tar.gz --output research/source-inventory.json
```

Check the outer SHA-256 above before continuing. Copy only the nested archive stream (without extracting paths):

```sh
python3 - <<'PY'
import shutil
import tarfile
with tarfile.open('artifacts/wemo_gpl_snsv2_package-11420.tar.gz') as archive:
    entry = next(e for e in archive if e.isfile() and e.name.endswith('.tar.gz'))
    with archive.extractfile(entry) as source, open('artifacts/snsv2-11420-inner.tar.gz', 'xb') as output:
        shutil.copyfileobj(source, output)
PY
python3 scripts/inspect_archive.py artifacts/snsv2-11420-inner.tar.gz --output research/inner-inventory.json
python3 scripts/extract_sources.py artifacts/snsv2-11420-inner.tar.gz sources/snsv2-11420
python3 scripts/analyze_static.py sources/snsv2-11420 --output research/binary-evidence.json
python3 -m unittest discover -s tests -v
```

Extraction requires a new destination, rejects traversal/absolute paths and links, skips dependency downloads and files over 4 MiB, limits total output, and removes executable permissions. This is partial extraction for inspection, not a buildable reconstruction. Inventory preserves the full listing. Treat downloaded content as untrusted.

## Scope and validation

No device commands, firmware updates, resets, exploitation, or uploads were performed during this offline task. No vendor code was executed. Source/archive downloads remain local and ignored by Git; the repository records research, hashes, and inspection tools. Device addresses, serials, MAC addresses, pairing codes, and credentials are omitted.

Validation: synthetic archive test checks traversal, absolute paths, symbolic links, skipped dependencies, non-executable output, and refusal to reuse an existing extraction directory. Static analysis successfully processed the downloaded product binaries. The unrelated parent project's Bun/Jest suite does not apply to this standalone Python research repository.

## Complete offline simulator

A full Linux ARM64 Matter outlet app now passes discovery, commissioning, on/off/toggle readbacks, simulated relay callbacks, and control after restart without re-pairing. See the [full-app report](research/full-app.md) and [test results](research/commissioning-results.json). Testing uses an isolated internal Docker network, with no Wemo changes. The complete MIPS32r2 soft-float app now also passes the same 12 checks under QEMU 24KEc. See the [full MIPS report](research/full-mips-app.md) and [MIPS test results](research/mips-commissioning-results.json). Neither build is an installable Wemo firmware image.

## MIPS component port milestone

The [soft-float runtime and Matter component report](research/runtime-port.md) supersedes the initial runtime blocker below. An OpenWrt GCC 13.3.0/musl toolchain now produces static soft-float binaries that pass on QEMU's 24KEc model. Actual Matter SDK TLV and crypto implementations run, including 53 upstream AES-CCM vectors and P-256 signing/verification. See [test output](research/musl-tests.txt).

These component tests are separate from the full MIPS server and commissioning milestone above. They are not a firmware image. Compatibility with the physical Wemo is unverified. All testing stays offline with no flashing or device changes.

## Initial offline development prototype (historical)

The [build feasibility milestone](research/build-feasibility.md) records the pinned Matter SDK review, runtime/toolchain gaps, and testable C++ relay component. This is **not yet Matter firmware**. The mock component was cross-compiled for MIPS and tested in QEMU without network access. It passes on 24Kf but fails on the Wemo-like 24KEc model because the selected runtime is unsuitable; target compatibility remains blocked. It has no physical device backend. See [recorded test output](research/offline-tests.txt).

## Firmware fit and integration milestone

The [firmware readiness report](research/firmware-readiness.md) assesses the older vendor's 64 MiB RAM / 16 MiB flash source profile while preserving uncertainty about this physical device. The stripped app passes commissioning/control in a 64 MiB no-swap emulator container and with time64 calls unavailable. A persistent-storage firmware profile, disabled OpenWrt service, tested XZ rootfs payload and bounded unsigned-image assembler now support further offline integration. The payload alone is 640 KiB; complete firmware fit and an installation path remain unverified. See [hardware/payload evidence](research/hardware-fit.json).

## Complete offline system milestone

A real vendor-profile Linux 3.18.27 kernel and complete minimal development rootfs now assemble into a size-checked unsigned candidate. A separate 64 MiB MIPS guest boots the full system and passes WPA2 through nl80211/WEXT, IPv6 over virtual Wi-Fi between network namespaces, Matter commissioning/control and relay-file/error handling. See the [full-system report](research/full-system.md), [successful boot results](research/system-boot-results.json) and [candidate image evidence](research/system-image-build.json). The physical Wemo board/radio/relay and an installable signed update remain unverified.

## Wi-Fi provisioning and recovery milestone

The MIPS rootfs now includes transactional OS-level WPA2 provisioning: private credential input, derived hex keys, association before commit, rollback to the previous connection and restart from the committed configuration. Offline fault tests cover cancellation, abrupt process termination and malformed/path inputs. See [provisioning and recovery findings](research/provisioning-and-recovery.md). Matter/BLE-managed Wi-Fi onboarding remains incomplete.

The source-based install audit identifies an aggregate B-partition overlap with shared data and checks conservative erase boundaries. **No safe installation/recovery method is verified for this exact plug.** The unsigned image remains blocked from installation; no device settings, firmware or flash were changed.

The [F7C063-specific follow-up](research/f7c063-bootloader-recovery.md) strengthens the 16 MiB model-family evidence and identifies two further hazards: the older SNSV2 8 MiB profile selects an oversized image recipe, and the normal Matter kernel can write a flash status register while probing. A RAM-loaded kernel is therefore not inherently read-only. That research pass made no requests to the Wemo; exact bootloader and recovery remain unverified.

## Read-only forensic RAM candidate

A separate [forensic RAM image](research/forensic-ram-image.md) now removes probe writes and denies flash program/erase/register writes at the driver boundary. It includes only an identification program, with networking, shell, writable storage and GPIO/relay controls excluded. The actual MIPS driver stack passes 23 emulator checks, including all 256 register-write opcodes being rejected and zero forbidden SPI transactions. The 522,951-byte board RAM image is packaged locally; [build evidence](research/forensic-ram-build.json) records hashes and configuration/binary audits.

This verifies a constrained storage-read-only software path offline. Exact bootloader behavior and physical MT7688 controller/board effects remain unverified; it is **not certified for deployment or for zero hardware side effects**. No Wemo was contacted, rebooted, flashed or changed.
