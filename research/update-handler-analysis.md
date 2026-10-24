# Offline update and recovery binary analysis

Date: 2026-10-24. Scope: binaries from Belkin SNSV2 GPL package **11420**, not the user's installed **11565**. No vendor code was executed and no device was contacted. The recovery gate remains closed.

## Provenance and reproduction

Package SHA-256: `4f4648e8765a891bc995c868a6ebeb835a5d4c1e8d92f4fcd1e0162d9a1955e6`.

| ELF | SHA-256 |
| --- | --- |
| libUPnPHndlr.so | 8873584413902933a19a7de5de7a00c9a6276df9fc53fa55b08d174eb51a239d |
| libDeviceControl.so | 3d7981d2df7e1038425ee64abca88888edd651daed624106b40cc0d7d352239a |
| libbelkin_api.so | 75b01a17e1b870435d62a76eb72add2119a47ecd6e3184485037d3d49f7c0417 |

The [offline disassembler](../scripts/inspect_update_binary.py) uses Capstone 5.0.6 and pyelftools 0.32 to disassemble named dynamic symbols, annotate MIPS GOT references, and list read-only strings. It never executes the input. Local ignored outputs under `artifacts/binary-analysis/` are `update-trace.asm.txt`, `belkin-api.asm.txt`, `boot-toggle.asm.txt`, and `reset-trace.asm.txt`. Addresses below are ELF virtual addresses, not device flash offsets. MIPS branch delay slots were included in the manual interpretation.

## Unsigned-image flag does not establish a signature bypass

`UpdateFirmware` at `0x23b78` reads `WithUnsignedImage` (string `0x5026c`) using `Util_GetFirstDocumentItem` at `0x23cdc`. It parses the nonempty value with `atoi`, stores it at stack offset `0x114` (`0x23eac`), and passes it as the second argument to `StartFirmwareUpdate` (`0x23ef4..0x23f08`). This confirms a real handler field, not merely an unused XML string.

`firmwareUpdateTh` calls `New_Firmware_Update` at `0x24614`, after selecting its second argument from a flag at stack offset `0x114`. A subsequent offline pass traced the intermediate StartFirmwareUpdate/FirmwareUpdateStart transfer; see the continuation below. This is static dataflow evidence for this binary, not a device execution test.

The defined `New_Firmware_Update` function in libbelkin_api.so is at `0x1c08`, size 208 bytes. At `0x1c84..0x1c98`, its second argument selects between these format strings:

- Nonzero: `sh -x /sbin/firmware_update.sh %s` (string `0x5024`).
- Zero: `mv %s /tmp/firmware.img; sh -x /sbin/firmware_update.sh /tmp/firmware.img` (string `0x5060`).

Both paths invoke the same signature-verifying script analyzed in [the earlier assessment](wifi-ota-investigation.md). The flag changes file handling; these branches do not skip signature verification. The older `Firmware_Update` function at `0x1b44` also invokes that script. This excludes this particular flag/callee branch as evidence of a simple unsigned-image bypass in the supplied 11420 files. It is not a security audit of all inputs or proof about 11565.

## Boot-slot toggle is an operating-system operation

`toggleBootState` in libDeviceControl.so (`0x4ff4`, size 864) calls `popen` on `fw_printenv -n bootstate` and parses the output with `atoi`. Its branches select:

- Parsed state 0: `fw_setenv bootstate 2` (`0x51b8..0x51cc`, string `0x92c0`).
- Parsed state 2: `fw_setenv bootstate 0` (`0x5228..0x5238`, string `0x92d8`).
- Other parsed states: logs invalid state and returns -1.

It calls `system` on the selected command at `0x5250`, then on `reboot` at `0x52bc`. The shown function does not check the first system call's result before continuing. This is a userspace slot switch, not evidence of pre-OS Wi-Fi recovery or automatic rollback. It requires enough of the OS/application to run. Callers and physical-button timing remain unaudited; this report does not provide a button procedure. Never invoke this on the user's device based on this analysis.

## Factory reset is not firmware restoration

`ResetToFactoryDefault` in libbelkin_api.so (`0x2e28`, size 220) invokes `nvram restore`, writes the `restore_state` parameter, invokes `/sbin/jffs2reset -y` and `/sbin/mtd erase Belkin_settings`, sleeps, and invokes `reboot`. These strings are at `0x54bc`, `0x54cc`, `0x54dc`, `0x54f0`, and `0x5510`, respectively. This function clears settings/overlay state; it contains no firmware-image restore or bootloader recovery transport. It also performs flash changes, so it is not a harmless diagnostic.

## Remaining evidence needed

Exact 11565 binaries and the matching bootloader are still missing. The userspace toggle and update-test scripts do not establish what happens when the kernel fails, the trial hangs, the radio fails, or environment writes lose power. Continue artifact acquisition and bootloader analysis; do not flash the candidate or use the physical plug to discover recovery behavior. Existing emulator and parser tests cannot close these gaps.


## Local continuation: complete flag transfer and update-monitor side effects

User constraint: no external GitHub activity except in the user's own repositories. The proposed external maintainer request is cancelled and remains unsent. This pass used local files only; no device or network requests were made.

Additional disassembly: `artifacts/binary-analysis/update-monitor.asm.txt`, generated with the same offline helper and same libUPnPHndlr.so hash above.

### Intermediate transfer now traced

`StartFirmwareUpdate` saves its incoming second argument at `sp+0x3c` (`0x2399c`). It allocates a 0x108-byte argument structure, copies this flag to structure offset 4 (`0x23aa0..0x23ab0`), and passes the structure as the fourth argument to `pthread_create` for `FirmwareUpdateStart` (`0x23aec..0x23af4`).

`FirmwareUpdateStart` preserves the incoming structure pointer in s3 (`0x231ac`), reads its offset-4 flag into s6 (`0x231f4`), and subsequently supplies the same pointer to the firmwareUpdateTh thread (`0x233d4..0x233dc`). The latter copies 0x108 bytes to `sp+0x110` (`0x23fe8..0x23ff8`), placing the flag at `sp+0x114`. This closes the earlier intermediate dataflow gap.

At `0x245f8..0x24614`, zero flag selects New_Firmware_Update's second argument 1; nonzero selects 0. Combining this with the already examined callee:

- WithUnsignedImage parsed as zero: invoke firmware_update.sh with the existing temporary image path.
- WithUnsignedImage parsed as nonzero: rename the temporary image to /tmp/firmware.img, then invoke the same script.

These normal branches provide no signature-check bypass in the supplied 11420 files. This remains a bounded static analysis, not proof about installed 11565 or every possible exploit path.

### An update request is not a read-only diagnostic

Before launching the actual update worker, FirmwareUpdateStart calls SetBelkinParameter for FirmwareUpURL (`0x23270..0x2327c`), sets FirmwareUpUnsigned to string 1 or 0 (`0x232dc..0x23304`), and calls AsyncSaveData (`0x2330c..0x23314`). Both string values were checked directly at ELF addresses 0x513c8 and 0x50dac. These calls request configuration mutation/persistence before worker creation. Exact flash-write timing inside AsyncSaveData was not audited, so this is not a claim about when physical bytes are written.

The monitor also contains a path for update-state values 1 or 3 that waits for the worker handle or a timeout and proceeds to `system("jffs2reset -y")`, `system("sync")`, then `system("reboot")` (`0x23690..0x236e0`). The command strings were resolved directly from ELF addresses 0x50050, 0x4f3bc and 0x4cf0c. Numeric state names and all state-setting callers are not yet mapped; do not infer that every request executes this path. It is enough to reject using this endpoint as a harmless capability probe.

None of this demonstrates independent bootloader rollback. No upload, configuration request, reset or reboot was attempted.
