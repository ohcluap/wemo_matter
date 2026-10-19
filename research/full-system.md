# Complete kernel/rootfs development build and offline system testing

This milestone builds a real vendor-profile board kernel and a complete minimal development rootfs, and boots a separate MIPS test system to exercise Linux 3.18.27, Wi-Fi, Matter and the relay value-file backend together. **The Wemo's MT7688 board and physical radio/relay remain untested. No device was contacted, flashed or changed.**

## What was built

- **Board kernel:** Linux 3.18.27 from the official SNSV2 11420 GPL archive, with the vendor's generic and ramips patch series and its normal SNSV2 device tree. The source profile describes MT7688/MT7628, 64 MiB RAM and the 16 MiB dual-slot flash layout. It is still not a confirmed hardware map for the user's installed 11565 device.
- **Board filesystem:** a complete minimal BusyBox-based development OS with `/init`, shell, mounts, device nodes, network/diagnostic commands, the static Matter outlet, WPA supplicant/WEXT support, `iw`, and the supplied MT7628/helper module files. No radio module autoload, home-network credentials, pin activation or Matter daemon startup is enabled. The default boot enters a serial development shell. Production provisioning and persistent flash-overlay initialization remain unimplemented.
- **Offline candidate:** a real kernel uImage plus the complete XZ SquashFS, assembled with erased padding at the inspected vendor offsets. It is unsigned, has no Belkin update wrapper and is not an installable stock-firmware update. See [image sizes/hashes](system-image-build.json) and [kernel packaging](board-kernel-build.json).
- **Guest test kernel/rootfs:** a separate Malta kernel, full initramfs, native MIPS `chip-tool`, hostapd and virtual Wi-Fi radios. The app and controller both run as MIPS processes under this kernel, rather than translating syscalls into the Mac/Docker host kernel.

The board and test kernels are different builds of 3.18.27. The board kernel is compiled/packaged, not booted in an MT7688 emulator. [QEMU's documented MIPS machines](https://www.qemu.org/docs/master/system/target-mips.html) include Malta, not this Wemo/MT7688 board.

## Offline protocol and Wi-Fi test

The guest has **64 MiB of emulated physical RAM** and a 24KEc CPU. Its Docker container uses `--network none`; QEMU's user network is restricted, has no host forwarding, and is not used for the Wi-Fi test. The AP and station use Linux `mac80211_hwsim` radios in **different guest network namespaces**. There is no local-loopback path between their IP stacks.

The test creates its own lab SSID and fixed development WPA2 key. It associates the station using nl80211, reconnects using legacy WEXT, verifies IPv6 delivery over the virtual radio link, then runs the Matter device in the station namespace and the controller in the AP namespace. Commissioning and subsequent encrypted controls traverse that virtual Wi-Fi connection.

Wi-Fi is established by the OS-level supplicant. The Matter app still uses its on-network commissioning configuration (`chip_enable_wifi=false`); Matter-managed Wi-Fi scanning/credential provisioning and BLE onboarding are not implemented or tested.

The test verifies Linux release and RAM envelope, both radios, WPA2 association through both interfaces, IPv6 delivery, Matter commissioning, outlet descriptor, on/off/toggle commands, OnOff readbacks, corresponding relay-file contents, rejection when the relay file is missing without changing the attribute, and retained commissioning/control after an app process restart. This last check retains guest files; it is not a flash-persistence or power-loss test.

The initial system milestone passed **16 recorded checks** and powered down cleanly in about **31 seconds** on the emulator host. The [subsequent provisioning milestone](provisioning-and-recovery.md) extends this to 20 checks, including credential rollback, commit and reconnect after supplicant restart. See the current [successful boot results](system-boot-results.json) and [complete build provenance](system-build-provenance.json) for exact runtime, memory observations and artifact hashes. These are not peak-memory or physical-CPU timing measurements. Raw console/protocol output remains under ignored `artifacts/system-tests/`. Full boot/control testing cannot validate radio calibration, RF performance, the physical button, relay switching, recovery or actual CPU timing on the plug.

## Kernel compatibility fixes found by boot testing

The old kernel build needs explicit modern-toolchain adaptations: select its GCC 5 compiler definitions for later GCC, remove a contradictory function attribute, and retain warnings without making newer warning categories fatal in the MIPS subtree. These adaptations do not replace kernel synchronization or cryptography with stubs. BusyBox uses large-file support for modern musl, explicit shell alias/arithmetic/builtins, and its halt/poweroff applet family.

A first full boot failed in the futex initialization self-check. Modern MIPS binutils inserted a `sync` before a labelled `ll`, so the exception-table entry pointed at the wrong instruction. The build now passes `-mno-fix-loongson3-llsc` to the assembler, as [upstream Linux does for this problem](https://code.googlesource.com/linux/torvalds/linux/+/9f7853d7609d59172eecfc5e7ccf503bc1b690bd/arch/mips/Makefile). This Loongson workaround is not required by the targeted 24KEc CPU. [The regression check](kernel-futex-validation.json) verifies that both kernels' futex exception entries point at their LL/SC instructions.

The freestanding kernels use Debian's native-host MIPS GCC 12 cross-compiler. They link no userspace libc. Matter, BusyBox and Wi-Fi tools retain the OpenWrt GCC 13.3/musl soft-float runtime. Build input hashes and the full vendor patch list are recorded in [board-patch-inputs.json](board-patch-inputs.json).

## Physical Wi-Fi support: evidence and remaining limits

The supplied `mt7628.ko` imports 92 symbols. All are available from the rebuilt kernel plus the supplied `myadd.ko` helper, whose own imports are also available. See [the static module audit](wifi-module-audit.json). This is a necessary linking check, not a test of structure layouts, calling ABI, driver initialization or RF operation. The vendor configuration deliberately strips module metadata/vermagic checks; successful symbol resolution alone cannot certify module compatibility.

An initial metadata-layout mismatch was corrected by enabling `CONFIG_KALLSYMS`, which the supplied modules' structure geometry requires. Both now have 328-byte module metadata, matching init/exit pointer offsets, and available imports. This checks selected module metadata only; other kernel/driver structure ABIs remain unverified.

These are the older package's compiled modules, not newly rebuilt Wi-Fi drivers. They are staged without autoload. The test radios use mac80211_hwsim, not the proprietary MT7628 implementation. The WEXT test covers the intended legacy userspace interface but does not validate every MediaTek private ioctl, AP-client setup requirement or calibration path. Actual board Wi-Fi support remains a hardware validation item. Factory calibration data must be preserved; this build does not fabricate or overwrite it.

## Relay backend

[Static ELF evidence](relay-backend-evidence.json) identifies the older vendor `setPower()` path as `/sys/class/gpio/gpio19/value`, with ASCII `1` for on and `0` for off. This strengthens the earlier string-only finding but does not confirm the user's physical revision/polarity.

The app's pre-change callback calls `port/RelayBackend.h` and rejects an attribute change if the selected backend fails. The default remains the original in-memory simulator. The offline file mode accepts only `/tmp/wemo-relay/value`. The physical sysfs path additionally requires an explicit environment flag and a `verified-gpio19` marker; neither is enabled in the image. No pin export/direction operation is performed. Standalone tests reject missing files, symlinks, unauthorized paths and the disabled physical path; full guest Matter tests verify on/off/toggle file writes and a missing-file command failure.

The physical backend is development scaffolding. Pin direction/startup policy, ownership, real readback behavior and recovery after a partial physical write still need validation before enabling it. File-backend tests do not operate an electrical relay.

## Reproduce

After the existing firmware/Matter source preparation:

```sh
python3 scripts/prepare_system_sources.py
docker build -f toolchains/Dockerfile.board-build -t wemo-matter-board-builder:bookworm .
sh scripts/build_kernel.sh board
sh scripts/build_kernel.sh malta
sh scripts/build_busybox.sh
sh scripts/build_wifi_tools.sh
sh scripts/build_iw.sh
sh scripts/build_mips_app.sh --firmware
sh scripts/build_mips_controller.sh
sh scripts/package_board_kernel.sh
sh scripts/build_system_rootfs.sh
python3 scripts/package_system_image.py
python3 scripts/check_kernel_futex.py
python3 scripts/audit_wifi_module.py
python3 scripts/test_system_boot.py
python3 -m unittest discover -s tests -v
```

Downloads/package installation occur only during preparation. Builds and guest execution use no external network. The scripts target this Apple Silicon Mac/Docker setup; sources, objects, emulator logs and binary images stay ignored locally. A fresh complete build uses additional disk space. Existing Home Assistant and unrelated containers are not changed.

The packaged board kernel is **1,245,074 bytes** against a 1,572,864-byte kernel region. The complete development SquashFS remains below its 6,029,312-byte budget; [current image evidence](system-image-build.json) records its exact size after provisioning changes. The padded unsigned candidate is **7,602,176 bytes**. These budgets come from the older source profile, not a readout of the user's flash.

The next requirements for physical deployment are still exact board/partition and recovery confirmation, actual board boot/radio/relay validation, completed persistent-storage/provisioning policy and an authorized recoverable installation path. The vendor updater's signature requirement is not bypassed by assembling an unsigned image.
