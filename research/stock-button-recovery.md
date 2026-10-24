# Stock button recovery: a separate application-only candidate

2026-10-24. Local source and binary inspection only. No GitHub, network, button, power-cycle, reset or device operation occurred. Sources are from SNSV2 11420, not a verified image of installed 11565.

## New source chain

[Reset source evidence](button-reset-source-evidence.json) and [callers](button-reset-callers.json) preserve full relevant source members and SHA-256 hashes.

1. MT7628snsv2.dts declares gpio-keys-polled, BTN_0, GPIO23 active-low, Linux key code 0x100. The DTS is captured in stock-application-source-evidence.json.
2. gpio-button-hotplug.c maps BTN_0 to index 0 at lines 84-85. gpio_button_get_value returns the physical value XOR active_low at lines 268-277.
3. The polled probe, lines 604-620, includes a WEMO modification. For button index 0 with logical pressed value 1, it invokes /bin/sh /sbin/factoryreset through call_usermodehelper with UMH_WAIT_EXEC. The preceding comment describes a /proc marker, but the actual code directly launches the shell helper. The implementation, not that stale comment, is the evidence.
4. factoryreset waits, removes gpio_button_hotplug, exports GPIO23 and checks the raw input again. If released it restores the driver and exits. If still pressed it proceeds through nvram restore/commit, jffs2reset -y, mtd erase Belkin_settings and reboot. This is destructive to settings; it must not be used as a casual probe.
5. The normal hotplug configuration instead launches resetwifi on BTN_0 pressed and triggerswitch on released. Do not confuse Wi-Fi reset with full settings removal.
6. The SNSV2 rc.button/failsafe script explicitly disables generic OpenWrt button failsafe. An OpenWrt failsafe guide is therefore not evidence that the shipped vendor profile exposes that route.

The libDeviceControl PowerButtonTask examined separately polls a button path and toggles power. ResetSensor2Default resets sensor configuration for a selected device type; its name does not identify factory recovery. Neither disassembly is a substitute for the driver-to-shell chain above.

## What this changes

The factory-reset trigger is outside a separately installed Matter process. Preserving the stock kernel, driver, shell, reset script and required utilities could therefore leave a recovery route for some added-application failures even without normal Wi-Fi. This supports evaluating an application-only installation before full kernel/rootfs replacement.

It is NOT independent of Linux boot: the kernel must initialize, the correct driver must load/probe, the shell and script must remain accessible, required utilities must work, and storage operations must complete. The helper's UMH_WAIT_EXEC flag is not proof of successful reset completion. This source does not demonstrate that the installed 11565 kernel contains the same modification.

It also requires physical access to the exterior button and power/startup sequence. It is not a purely remote Wi-Fi recovery transport and must not silently be treated as satisfying the user's Wi-Fi-only requirement. No enclosure opening is implied, but this remains a scope distinction to resolve if a concrete installer becomes possible.

## Conditions before this can support any deployment

- Match this chain to installed 11565 binaries/kernel and confirm its startup ordering.
- Keep every dependency of the reset path intact; avoid shadowing stock shell, boot scripts, driver or reset tools through the overlay.
- Establish an installation entry point that does not itself destroy recovery, without experimenting on the user's sole plug.
- Verify that the contemplated persistent application writes can be removed by this reset and cannot prevent its prerequisites from loading.
- Assess resource exhaustion and filesystem failure, not just an app exiting unsuccessfully.
- Demonstrate the relevant failure/recovery cases on matching hardware or obtain equivalent trustworthy existing evidence before changing this plug.

This is a concrete candidate mechanism for a narrower failure envelope, not an approved recovery procedure. Full-image replacement still lacks verified bootloader fallback; no upload or physical test is justified by this report.
