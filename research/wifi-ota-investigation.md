# Wi-Fi-only installation and recovery investigation

Date: 2026-10-24. Repository examined: `4bbc08a5ec86d472b4350fb72b25a514ccafd244`.

## Decision

**No verified procedure currently meets the requested combination of native Matter, Wi-Fi-only installation, and reliable recovery without opening the plug.** This is a bounded investigation, not proof that such a procedure cannot be developed.

The user permits firmware replacement over Wi-Fi only if reliable recovery is established. A failed attempt that requires UART or a flash programmer would not meet that condition. No Wemo requests, resets, uploads, exploit tests, environment changes, or flash writes were performed. This report and its evidence were added to a local checkout; nothing was pushed to GitHub.

The repository identifies F7C063 with firmware `WeMo_WW_2.00.11565.PVT-OWRT-SNSV2`. This identity was not re-read from the physical plug today. The official source package available for this investigation is the older 11420 release.

## Fresh verification

Downloaded the [official SNSV2 11420 GPL package](https://s3.belkin.com/support/assets/wemo/gpl/wemo_gpl_snsv2_package-11420.tar.gz) and independently matched its SHA-256 to the repository's recorded `4f4648e8765a891bc995c868a6ebeb835a5d4c1e8d92f4fcd1e0162d9a1955e6`. Read selected regular archive members without executing vendor code. Matching a recorded hash is not vendor signature verification.

Exact file hashes, line-numbered excerpts and validation results are in [wifi-ota-investigation-evidence.json](wifi-ota-investigation-evidence.json). The firmware updater and health-script hashes match the earlier install audit.

| Route or property | Verified evidence | Assessment |
| --- | --- | --- |
| Local firmware upload | The [pywemo firmware documentation](https://github.com/pywemo/pywemo/wiki/WeMo-Firmware) describes a local `UpdateFirmware` action. | An upload endpoint is not permission to run arbitrary firmware or a recovery transport after Linux fails. |
| `WithUnsignedImage` | Present in the older product's `firmwareupdate.xml`. Its `firmware_update.sh`, lines 39–92, nevertheless requires a validated signature. | An interesting unresolved handler-level lead, not a confirmed switch that disables verification. The compiled handler and exact 11565 execution path still need analysis. No claim that every possible update path has been ruled out. |
| A/B slots | Updater selects the other slot using `bootstate`; unknown state defaults to A. | Preserving a working slot is necessary, but does not prove the bootloader will return to it. |
| Watchdog during update | Lines 184–185 kill the watchdog process and write its disable character before the flash write. | Cannot assume a watchdog will rescue a hung update. Re-enable/boot-time behavior needs exact-device verification. |
| Boot selection | Flash write precedes separate environment updates. A comment at lines 202–203 explicitly accommodates older WNC bootloaders. | Exact bootloader version matters. Source does not establish atomic power-loss recovery. |
| Health check | `update_test.sh` waits for startup flags to disappear, then commits the trial slot. The boot script invokes it only for the expected trial/check state. | Copying this script alone is insufficient: absent flags can mean success without any Wi-Fi/Matter reachability check. |
| Current candidate | `firmware/rootfs/init` ends in a development shell. `scripts/assemble_rootfs.py` deliberately omits physical radio autoload, credentials and relay activation. | Not ready for remote-only use. A successful boot could still leave the plug unreachable. |
| Current forensic image | Repository documents an identification-only image without networking or a shell. | It neither supplies an over-Wi-Fi loader nor repairs an unbootable device. |

The stock source's signature-chain handling was inspected, not exhaustively audited or emulated. No signing key, matching signed 11565 update, complete device backup, or verified restore image was acquired.

## Published installation leads

- [Sternum's F7C063 research](https://sternumiot.com/iot-blog/mini-smart-plug-v2-vulnerability-buffer-overflow/) demonstrates a remote command-execution vulnerability after physical debugging and firmware analysis. It is a relevant lead for obtaining an execution path; it does not demonstrate reliable 11565 installation or recovery. A crash-based entry point also cannot help if Linux or Wi-Fi no longer boots. No payload was run.
- [OpenWrt on Wemo Insight](https://sven-schwermer.de/wemo) demonstrates custom firmware with physical serial access on F7C029de/RT5350. It is a different board. Its bootloader has modified boot-command behavior; its procedure cannot be used as an F7C063 Wi-Fi recovery recipe.
- [CVE-2023-33768's researcher repository](https://github.com/purseclab/CVE-2023-33768) concerns WSP080 and firmware-induced denial of service. It is neither an F7C063 installer nor a recovery solution.
- Targeted searches for F7C063 recovery and the exact 11565 firmware string did not yield an authenticated matching image or demonstrated Wi-Fi-only restore procedure. This does not prove that private dumps or unindexed mirrors do not exist.

## What would change the decision

The most promising architecture remains a trial image in a confirmed inactive slot, with the original working image preserved and rollback enforced outside the trial application's control. It requires evidence of all of the following before a flash attempt:

1. Exact 11565 update-handler behavior, an established installation entry point, and the actual bootloader/state machine. Start with matching firmware or an existing exact-board dump/transcript; do not substitute another model's offsets.
2. A verified flash map and preserved device-specific identity/calibration data, plus a usable recovery copy. A downloaded firmware file alone does not preserve all device-specific state.
3. Automatic return to the original slot when the trial cannot boot, cannot mount its filesystem, hangs, or boots without working Wi-Fi. Recovery must not require commands through the failed trial OS. Power interruption and environment-write failures also need assessment.
4. A board-ready image with working physical Wi-Fi, startup, persistent settings, relay control and a health contract that checks actual management/Matter reachability. A recovery access point inside the trial image is useful only when that image and radio can boot; it is not independent recovery.
5. Evidence that these failure cases recover on the exact hardware/bootloader, ideally from an existing qualified test or a separate recoverable lab unit. The user's only plug should not be used to discover whether rollback exists.

Until then, modifying the image packager or adding an upload command would not satisfy the recovery condition. Further emulator work alone cannot validate the missing physical bootloader and radio behavior.

## Validation and limits

Freshly ran the existing four `test_install_recovery.py` tests and three `test_recovery_sources.py` tests: **7 passed**. They validate conservative ranges, trial-state rejection and partition alias handling. They do not execute the vendor updater, emulate its bootloader, test physical power loss, or demonstrate rollback. Full Matter/QEMU builds were not rerun for this documentation investigation.

Belkin's [shutdown notice](https://www.belkin.com/support-article/?articleNum=335419) confirms loss of the original cloud-based Google/Alexa integration. That does not mean every local capability is gone: the [pywemo community's direct test reports](https://github.com/pywemo/pywemo/issues/773) include local setup/control on F7C063/11565 (a reported v3 unit, not a test of this user's plug). This is a possible occasional computer-control fallback, not the requested direct Google Home integration and not a reason to add a persistent bridge.


## Follow-up binary evidence

[Offline handler analysis](update-handler-analysis.md) traces the 11420 update-script call, userspace boot-slot toggle, and factory reset. Neither the unsigned flag nor these reset controls establishes the required Wi-Fi-only install/recovery path. This evidence is not from installed firmware 11565.
