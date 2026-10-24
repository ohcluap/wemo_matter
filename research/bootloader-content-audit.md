# Local bootloader content and watchdog audit

2026-10-24. Local-only inspection of the existing SNSV2 11420 package. No GitHub, network, or device access. No vendor code executed. Does not establish installed firmware 11565 behavior.

## Broader content scan

[Machine-readable results](bootloader-content-audit.json) cover all 6,179 regular members of vendor-inner.tar.gz (340,415,788 bytes), plus all 10,588 regular members of its bundled u-boot-2014.10.tar.bz2 (58,330,536 uncompressed bytes). Searches used literal byte strings bootstate, check_boot, Ralink UBoot, SNSV2 and 11565. Other nested compressed archives were not decoded. This expands on the earlier filename/size-limited search; it does not establish absence of arbitrary encoded or differently named logic.

The nested U-Boot archive SHA-256 is d3b132a7a9b3f3182b7aad71c2dfbd4fc15bea83e12c76134eb3ffefc07d1c71. Its matches are in Samsung board helpers and generic bootstage declarations, not a Wemo rollback state machine. No SNSV2, 11565 or Ralink UBoot match was found inside that archive. Outer matches identify the already investigated application libraries and shell scripts. The source package still supplies no identified exact-device bootloader implementation.

## Hardware watchdog is a separate question from slot rollback

[Source evidence](watchdog-source-evidence.json) preserves the relevant driver patch and MT7628 configuration with hashes. The MT7628 configuration enables CONFIG_MT7621_WDT. mt7628an.dtsi declares a watchdog compatible with ralink,mt7628an-wdt and mtk,mt7621-wdt, with reset-controller index 8.

In target/linux/ramips/patches-3.18/0056-watchdog-add-MT7621-support.patch:

- Lines 113-124 implement start: configure the timer, set timeout, enable it.
- Lines 127-137 implement stop by clearing the enable bit.
- Line 150 advertises magic-close support; nowayout is a separate setting.
- Probe calls device_reset at line 177, calculates a maximum timeout of integer 65535/1000 = 65 seconds, and registers the device at line 186. This probe body does not call its start routine.

Consequently, driver availability is not evidence that a watchdog is armed before the trial kernel starts. The reset during probe also requires explicit investigation before claiming that a timer armed by the bootloader survives kernel handoff. This audit does not assert measured reset-register behavior or that every watchdog configuration stops at probe.

Even a verified watchdog reset would only restart the machine. The bootloader must independently choose the preserved working slot after the reset; otherwise the same broken image can boot repeatedly. Working Wi-Fi without working Matter is another distinct failure condition that the stock process-start checks do not cover.

## Consequence for the installer

A userspace timeout, reset button handler or recovery AP inside the trial image cannot cover failure before that code runs. A sufficient recovery design needs verified behavior outside the failing trial application: an armed reset mechanism where required, bootloader fallback semantics, safe environment writes, and a preserved original slot. None is established on this user's installed bootloader. No installation or device test is approved by this audit.
