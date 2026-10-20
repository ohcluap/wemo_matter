# F7C063 bootloader, flash and recovery research — 2026-10-19

**Outcome:** better evidence for the 16 MiB model family and two additional
recovery hazards, but no verified exact-device bootloader version or safe
installation/recovery procedure. This pass made **zero requests to the Wemo**.
It used public research and local source/artifact reads only. No reboot, reset,
diagnostic action, login, physical access, firmware upload or flash operation
was attempted. Local reports/scripts were updated; device state was not changed.

## Identity and sources

The user's exterior label confirms **F7C063 / K7SF7C063**. Prior read-only network
queries report `hwVersion=v2` and installed firmware
`WeMo_WW_2.00.11565.PVT-OWRT-SNSV2`. The available GPL package is **11420**, not
the installed release. Model-family evidence is not a measurement of the user's
individual flash or bootloader.

| Primary evidence | What it supports | What it does not establish |
| --- | --- | --- |
| [Sternum's F7C063 teardown](https://sternumiot.com/iot-blog/mini-smart-plug-v2-vulnerability-buffer-overflow/) | Researchers describe an MT7688AN board, MX25L12835F flash extraction and physical UART access. | A verified stock-restoration procedure, the user's exact board or its bootloader banner. Their password-reset/debug procedure changes device state and is excluded here. |
| [Macronix MX25L12835F datasheet](https://www.macronix.com/Lists/Datasheet/Attachments/8653/MX25L12835F%2C%203V%2C%20128Mb%2C%20v1.6.pdf) | This part has 128 megabits = **16,777,216 bytes / 16 MiB**, with 2.7–3.6 V specified operation. | That this exact chip is fitted to every F7C063. The teardown's “128MB” capacity wording should not be copied. |
| [Belkin-filed K7SF7C063 internal-photo exhibit 3170788](https://fcc.report/FCC-ID/K7SF7C063/3170788.pdf) | A matching FCC hardware-photo filing exists. | Chip markings were **not visually verified in this pass**: direct downloads from FCC/mirrors returned HTTP 403, and the web tool's screenshots did not expose pixels to the execution interface. No interpretation of those photos is used as hardware proof. |
| [Belkin's F7C063 generation guidance](https://www.belkin.com/support-article?articleNum=288072) | Belkin distinguishes retail generations using the HomeKit-code label. | The UPnP string `v2` or product suffix `SNSV2` alone is not a definitive retail-generation or PCB-revision identifier. |
| Official SNSV2 11420 source and the existing rebuilt board-kernel source/config | Explicit partition declarations, image recipe, environment handling and flash-driver behavior. | Exact installed 11565 bootloader, measured geometry or tested physical recovery. |

The FCC exhibit is linked for future inspection; no downloaded PDF or page image
was acquired successfully or committed. The user's label photo and its unique
identifiers remain outside the repository.

## Bootloader: family evidence, version unresolved

The vendor source uses a `Uboot` partition, `Uboot_env`, `fw_printenv`/`fw_setenv`,
and `bootstate`/`check_boot`. This supports a U-Boot-based boot flow. It does not
identify the exact build/version installed on this plug.

An inventory of all 7,688 source-archive entries found generic OpenWrt U-Boot
packages, other boards' support files, and `dl/u-boot-2014.10.tar.bz2`. None is a
verified SNSV2 bootloader image or exact-board source implementation. The generic
download's version must **not** be reported as this Wemo's bootloader version.
Path inventory does not exclude code embedded under unrelated filenames.

Exact-model web and GitHub code searches did not locate a usable F7C063 boot
banner or independently verified recovery transcript during this bounded pass.
No new matching 11565 bootloader/flash dump was acquired. Public results for
“Wemos D1 Mini” describe unrelated ESP8266 hardware and were excluded.

[The Insight port author's boot transcript](https://sven-schwermer.de/wemo)
demonstrates a modified boot command on **F7C029de/RT5350**, a different device.
Its commands, offsets and version are not an F7C063 recipe. Generic MT7688
bootloader projects likewise do not establish what Belkin shipped or whether a
given load/boot operation changes environment or flash.

## Flash: source map and a packaging inconsistency

The older normal SNSV2 device tree defines the following byte ranges, using
end-exclusive offsets. These are source facts, **not approved write addresses**.

| Region | Start | End |
| --- | --- | --- |
| Uboot aggregate | `0x000000` | `0x050000` |
| Uboot_env, alias within aggregate | `0x030000` | `0x040000` |
| Factory, alias within aggregate | `0x040000` | `0x050000` |
| kernel_1 | `0x050000` | `0x1d0000` |
| rootfs_1 | `0x1d0000` | `0x7b0000` |
| homekit | `0x7b0000` | `0x7c0000` |
| kernel_2 | `0x7c0000` | `0x940000` |
| rootfs_2 | `0x940000` | `0xf00000` |
| rootfs_data | `0xf00000` | `0xf50000` |
| Belkin_settings | `0xf50000` | `0xfe0000` |
| nvram | `0xfe0000` | `0xff0000` |
| User_Factory | `0xff0000` | `0x1000000` |

The previously identified aggregate `Firmware_2` overlap into `rootfs_data`
remains unresolved. Overlapping aliases must not be concatenated to produce a
“full backup”; their offsets refer to the same physical bytes.

**New finding:** the `WemoSNSV2-8M` profile expands the normal
`BuildFirmware/OF/WeMo` recipe, which preallocates **0x740000 bytes**. Its separate
8 MiB device tree has only one firmware slot, with **0x6b0000 bytes** before
shared data. Writing that template at its declared kernel start would cross
**0x90000 bytes / 576 KiB** of shared settings/identity regions. A smaller generic
`WeMo-8M` recipe exists, but that SNSV2 profile does not select it. This is an
offline source inconsistency, not evidence that the user's plug has 8 MiB.
There is no B slot in that 8 MiB source layout, so A/B assumptions do not apply.

The DTS's `en25q64` name is not sufficient to decide physical capacity. The
actual SPI-NOR driver reads JEDEC ID and overrides a mismatched platform name.
That explains how a stale 8 MiB name could coexist with a 16 MiB layout; it does
not resolve the actual chip ID. Nor should the driver silently accepting the
partition table be mistaken for validation of its boundaries.

The teardown's published firmware scan starts with a kernel header at offset
zero and rootfs at `0x180000`, matching offsets *within a firmware image*. It
cannot be treated as a verified complete-flash partition map containing a
bootloader at physical zero. No original raw dump was available for resolving
that distinction.

## A RAM boot is not inherently read-only

**New finding:** the current board configuration enables `CONFIG_MTD_M25P80=y`
and `CONFIG_MTD_SPI_NOR=y`. The `m25p80` probe calls `spi_nor_scan()`. In that
function, the Macronix branch calls `write_enable(nor)` and `write_sr(nor, 0)`.
Thus this kernel can issue a **flash status-register write during probing**, even
when the kernel itself was loaded into RAM and no filesystem is mounted writable.
The intended branch clears protection status; actual effects depend on the chip.
This is source analysis only—no SPI operation was performed on the plug.

Partition read-only flags or a read-only rootfs do not suppress that early probe
operation. A future forensic RAM image must explicitly audit/remove mutating
probe paths and expose only the required reads before being described as
non-mutating. Board pinmux, LED/button, radio, watchdog and init behavior also
need review; this finding is not a complete side-effect audit.

Separately, the *vendor* startup script changes `bootdelay` to 1 if it differs.
Our development init does not run that vendor script, but booting a stock/rootfs
recovery environment must not be presumed read-only either.

See [reproducible source audit](recovery-source-audit.json) for hashes, line
references, both layout tables and computed overlaps. It contains no device
access or install commands.

## Recovery candidates and the evidence still required

| Candidate | Current assessment |
| --- | --- |
| Stock signed updater | Does not accept our unsigned image; not a recovery method when the normal OS is unbootable. |
| Normal factory reset | Clears setup/settings; no evidence that it reconstructs a damaged bootloader or replaces arbitrary firmware. Not an independent restore path. |
| Existing A/B mechanism | Source evidence only. Exact bootloader trial/rollback behavior and custom-rootfs health contract remain unverified. |
| Passive serial evidence acquisition | F7C063 researchers demonstrated physical UART. A separately authorized, electrically reviewed acquisition could identify boot version and geometry, but no new power cycle, wiring or console interaction is authorized/performed here. |
| Serial RAM load / boot | Potential future test only after exact boot-command semantics and a non-mutating RAM image are established. Not verified on this plug. |
| TFTP recovery | Generic/other-board examples are insufficient. No verified F7C063 transfer path exists here; a Wi-Fi connection in Linux does not establish a pre-OS network loader. |
| Independent SPI restore | External flash reading is documented on another F7C063. That is evidence for a backup route, **not a demonstrated complete restore**. Chip identity, board isolation, original backups, status/OTP protection and exact restore behavior still need validation in a later hardware phase. |

A main-array dump is not necessarily a complete record of all chip state: the
datasheet also describes separate security/OTP and protection state. A later
backup plan must account for those without attempting to erase or rewrite
irreversible/locked state. No chip-programmer, UART or bootloader commands are
provided for execution in this read-only phase.

The useful next evidence is an existing exact-board boot transcript/original
dump, or a separately authorized physical acquisition plan. Re-reading the same
UPnP model getters would not supply a measured flash map or bootloader version,
so no further live device requests were made. Actual recovery restoration would
necessarily require a later, explicit authorization to write; it cannot be
demonstrated under the present no-change constraint.

## Reproduce the offline checks

```sh
python3 scripts/audit_recovery_sources.py
python3 -m unittest discover -s tests -p 'test_*recovery*.py' -v
```

The audit needs the already prepared vendor/kernel sources, inventory and board
configuration. Both commands operate locally without network/device access.
