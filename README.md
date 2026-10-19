# Wemo Matter feasibility research

Offline investigation of running a Matter application on a stock Wemo, without opening the enclosure or flashing firmware. Research date: 2026-10-18.

**Result: no verified way to load and run our code has been found. The exact installed firmware has not been acquired.** This is a bounded preliminary assessment, not proof that a network execution path cannot exist.

## Device and acquisition

Prior read-only device observations identify firmware `WeMo_WW_2.00.11565.PVT-OWRT-SNSV2` and hardware revision `v2`. F7C063 Mini is the inferred retail model; the label has not been confirmed. The API's model number `1.0` is generic. See [sanitized device record](research/device.json).

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
