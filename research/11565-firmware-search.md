# Exact 11565 firmware and bootloader acquisition follow-up

Date: 2026-10-24. Builds on [the Wi-Fi-only investigation](wifi-ota-investigation.md).

## Result

No exact 11565 image or F7C063 bootloader binary/banner was acquired. This pass did find a concrete exact-model dump lead and recovered historical vendor firmware directory listings, improving on the earlier archive timeout. No device was contacted or modified; no person was contacted; no GitHub changes were published.

## Strongest new lead: an existing F7C063 flash read

Repository: [protectivedad/hardware_hacking_Wemo_Mini_F7C063](https://github.com/protectivedad/hardware_hacking_Wemo_Mini_F7C063), inspected at `3fc27f5db7005cd80e578cc3f9d4e0701e134081`. The [stump-creek organization copy](https://github.com/stump-creek-technical-services-llc/hardware_hacking_Wemo_Mini_F7C063) has the same tree commit.

- `log/firmware.log` records SPI reads over `0x00000000..0x00ffffff`, including first/verification passes and a final “Good read.” This is reported acquisition evidence, not our independent verification of the bytes.
- `firmware-images/Makefile` places the original dump and verification copy outside the repository. Its README explicitly excludes non-free images from Git. The inspected tree and release collection contain no downloadable dump. Three listed commits concern the template, photos, and write-up/log; no release assets or issues were returned.
- The README identifies MT7688AN and a 16 MiB Macronix flash family. It also reports possible physical damage during the author's work. A complete-looking read log does not establish trustworthy contents or successful restoration.
- There is no recorded firmware version or U-Boot banner in the inspected log. It might be older than 11565. Do not represent this as a matching firmware dump or a demonstrated recovery method.

An existing dump could supply bootloader code for offline comparison without opening this user's plug. Its exact board/revision, firmware identity, matching read hashes, and read quality need confirmation first. Device-specific identity, credentials and calibration must not be published. Even a genuine matching donor image must not be flashed wholesale onto another plug.

A [draft request](11565-maintainer-request-draft.md) asks for the minimum useful evidence. It has not been sent.

## Archive investigation

[Machine-readable request results](11565-acquisition-attempts.json) record HTTP outcomes, response hashes, relevant filenames and parsed archive results. Full response bodies remain in ignored local artifacts.

1. [Historical app analysis](https://github.com/chorankates/h4ck/blob/7f2e0aee15d9985fd9819af41362749a5ebbe94d/weemo/README.md) identifies `/wemo/NewFirmware.txt` on `fw.xbcs.net`. Its live host failed DNS resolution today. Exact-path CDX returned no successful captures; the availability API also returned no snapshot.
2. A broader successful CDX query returned old feed/directory captures. Retrieved the [2013 manifest](https://web.archive.org/web/20130330190652id_/https://fw.xbcs.net/plugin/device/firmware.txt), which names **2176 SNS**, not SNSV2/11565.
3. Retrieved `/wemo/owrt/` listings at **2018-01-25, 2021-05-31, 2022-12-19 and 2023-01-17**. The later listings contain 1,465 href entries and SNSV2 filenames through **11059**, with no 11565 entry. These are directory listings, not downloaded firmware images. [Latest inspected listing](https://web.archive.org/web/20230117025750id_/http://fw.xbcs.net/wemo/owrt/).
4. The observed naming convention is `WeMo_WW_2.00.<build>.OWRT.PVT_SNSV2.bin.gpg`, with additional `OWRT-SC` variants. The advertised runtime version string uses a different ordering. Two **inferred, unverified** 11565 filenames based on that convention returned no snapshot from the availability API. No claimed real 11565 download URL was recovered.
5. Some wildcard CDX requests returned HTTP 503 or timed out, especially the alternate `firmware.xbcs.net` hostname. These are unresolved queries, not proof of absence. The successful broad `fw.xbcs.net` query was under its 1,000-result limit.
6. Internet Archive item search for F7C063/SNSV2/exact runtime string returned zero records. The 36 results for “wemo firmware” were Tasmota/krackinfo mirrors, not a usable Mini image. Search coverage is limited to the queried indexes.
7. Re-read the live [Belkin GPL catalog](https://www.belkin.com/support-article/?articleNum=51238): the F7C063 source/license links still identify **11420**. This does not supply the 11565 update or this plug's installed bootloader.

## Other searches and limits

GitHub repository searches for F7C063 found the hardware-dump lead above. Targeted code searches for the exact 11565 runtime string returned no code match; broader model searches contained many irrelevant matches. Code search is not a complete binary/release inventory. Web results confirm people running 11565 but do not supply the image. In particular, [pywemo issue 773](https://github.com/pywemo/pywemo/issues/773) reports an update to 11565 on a v3 unit, which could be a secondary source of a saved update file or packet capture; it is not proof of this user's v2 bootloader.

The [Capture paper](https://www.cs.cmu.edu/~mfredrik/papers/zhang21a.pdf) includes F7C063 in its library survey, but the inspected [project README](https://github.com/synergylabs/iot-capture) describes framework/demo code, not a 11565 download. It is not a validated acquisition source.

## How a useful artifact would be evaluated

- **Signed update:** preserve original bytes and SHA-256, inspect signature/product metadata and embedded version without executing vendor code. Confirm it is 11565 SNSV2, then compare update handlers and image layout with 11420. A signed update may contain only kernel/rootfs; do not assume it contains the installed bootloader.
- **Full flash dump:** confirm acquisition provenance, actual capacity and matching independent reads; inspect bootloader/version, partition geometry and boot environment offline. Compare donor hardware with F7C063/K7SF7C063/v2. Keep unique data private.
- **Bootloader evidence:** resolve the actual transition rules for `bootstate`, `bootpart` and `check_boot`, boot failures and hangs, how a trial is confirmed, and what happens after interrupted environment writes. Establish whether any pre-OS recovery transport is Wi-Fi-capable; TFTP support alone does not establish Wi-Fi support.
- **Decision:** proceed toward a Wi-Fi-only installer only if rollback survives loss of the trial OS/radio and preserves the known-good firmware and unique data. Neither an entry-point vulnerability nor a donor dump alone meets this requirement.

No full builds or hardware recovery tests were run in this acquisition-only follow-up. The earlier seven range/parser tests remain evidence only for those helpers. The current candidate is still not deployable.


## Follow-up binary evidence

[Offline handler analysis](update-handler-analysis.md) traces the 11420 update-script call, userspace boot-slot toggle, and factory reset. Neither the unsigned flag nor these reset controls establishes the required Wi-Fi-only install/recovery path. This evidence is not from installed firmware 11565.


## Final archive and research-repository follow-up (2026-10-24)

The previously failing alternate-host CDX request now returned HTTP 200 with `[]` for `firmware.xbcs.net/*` (successful captures, collapsed by URL key, limit 500). The `fw.xbcs.net/*11565*` query likewise returned HTTP 200 with `[]`. Both raw response bodies have SHA-256 `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570`. This resolves those particular transport failures into empty index results; it does not prove that no copy exists anywhere. Request details are preserved in [the follow-up evidence](11565-remaining-leads.json).

Inspected the complete recursive tree of `synergylabs/iot-capture` at `53327bb6415048dfd2aeb1328f0d162d6732d218`: 1,227 entries, `truncated=false`. Wemo-named paths contain a controller package and two controller Python files. Filename screening for Wemo, Belkin, F7C063, firmware, dataset, U-Boot and `.bin` did not reveal an image or bootloader. The releases collection was empty. This is a tree/release inventory, not a complete content audit of every source file or historical commit.

A fresh scan of the 11420 package's application/shared-library printable strings found no concrete firmware-download URL. This bounded scan covered regular `.so`, `wemoApp`, and `wemoAPP` members smaller than 15 MB outside `dl/`; it cannot exclude dynamically constructed URLs, app-side feeds, compressed data, or other filenames.

The matching-model unpublished-dump lead remains the strongest concrete acquisition opportunity. Explicit authorization to send the prepared maintainer request has been requested; nothing has been posted. Recovery remains unverified and the device remains untouched by this investigation.
