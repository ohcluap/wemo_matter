# Offline build milestone — 2026-10-18

The later [runtime port milestone](runtime-port.md) resolves the initial hard-float blocker for tested components in emulation. This document preserves the initial investigation.

## Outcome and boundaries

This repository now contains a small C++ relay-control prototype and a MIPS cross-compilation/emulation harness. **It is not a Matter stack, bootable firmware, or a flashable image.** It is an independently testable application component for a possible future port. No GPIO backend is implemented and no device is contacted.

We cannot currently produce a validated firmware image for this Wemo. The missing work is substantive: a Matter platform port and compatible runtime, verified hardware support, an exact firmware comparison, and a tested boot/recovery design. CPU emulation cannot certify physical hardware safety or recoverability.

## Upstream review

Inspected official Matter SDK release `v1.6.1.0`, commit `3bcdd56ba54fb88b2afb4bfef575014671df7aa7`, using a sparse source checkout under ignored `sources/connectedhomeip`.

- [Linux compiler settings](https://github.com/project-chip/connectedhomeip/blob/3bcdd56ba54fb88b2afb4bfef575014671df7aa7/build/config/compiler/compiler.gni): Linux defaults to C++20.
- [Host builder](https://github.com/project-chip/connectedhomeip/blob/3bcdd56ba54fb88b2afb4bfef575014671df7aa7/scripts/build/builders/host.py): explicit cross-compilation handling includes ARM and ARM64; no ready Wemo/MIPS target was found in this builder.
- [Custom toolchain mechanism](https://github.com/project-chip/connectedhomeip/blob/3bcdd56ba54fb88b2afb4bfef575014671df7aa7/build/toolchain/custom/BUILD.gn): custom compilers are possible. Absence of a preconfigured MIPS target is not proof a MIPS port is impossible.
- [Linux lighting callback](https://github.com/project-chip/connectedhomeip/blob/3bcdd56ba54fb88b2afb4bfef575014671df7aa7/examples/lighting-app/linux/main.cpp): demonstrates the OnOff attribute callback boundary that a future outlet adapter can use. No SDK callback or commissioning flow has yet been integrated or compiled here.

Belkin's older source includes GCC 4.8-era configuration and uClibc 0.9.33.2. That compiler cannot compile the SDK's default C++20 code. A modern compiler plus validated runtime/sysroot is required; merely using another compiler does not prove ABI compatibility. The Debian test toolchain deliberately uses its own glibc statically and **does not reproduce stock Wemo userspace**.

Only about 17 GiB was available on the Mac at the start. This pass uses a sparse SDK checkout and a small cross-test container rather than bootstrapping the entire SDK and dependencies. No full SDK compilation was attempted, and no build failure is claimed.

## Prototype and tests

`prototype/relay.hpp` handles a proposed endpoint 1, OnOff cluster 0x0006, OnOff attribute 0x0000. It validates callback payloads, ignores unrelated endpoints/attributes, suppresses redundant writes, and commits its internal state only after successful mock hardware writes. Initial hardware state is explicitly unknown. It neither persists state nor assumes a physical GPIO polarity.

Hardware failure integration with Matter remains to be designed: a post-attribute callback occurs after a stack attribute update, so simply returning an error from this component will not itself roll back the Matter attribute. A real adapter must reconcile reported state/readback and define restart behavior.

Tests cover malformed input, unrelated routing, on/off transitions, redundant writes, failed writes and retry, and state after controller recreation. The cross-compiled executable **fails on QEMU's 24KEc CPU model with illegal instruction (exit 132)**. ELF ABI metadata identifies a hard-float runtime. It passes the same tests on the FPU-equipped 24Kf model. This is evidence that the convenient Debian runtime is unsuitable for the proposed Wemo CPU, not a successful Wemo compatibility test. A complete soft-float toolchain/runtime must be selected and tested; adding a compiler flag alone cannot convert prebuilt libraries. It is user-mode emulation on the container's host kernel, not a Wemo board/kernel emulator. Static glibc binary size is not a Matter firmware size estimate.

## Reproduce

From this repository:

```sh
docker build -f toolchains/Dockerfile.offline-tests -t wemo-matter-offline-tests:bookworm .
sh scripts/test_offline.sh
python3 -m unittest discover -s tests -v
```

Container creation downloads Debian packages. The subsequent MIPS compile/test run uses `--network none`, read-only root, dropped capabilities, a read-only prototype source mount, and a dedicated writable artifact directory. Only our own test executable runs. The native test runs without sanitizers. An initial AddressSanitizer/UndefinedBehaviorSanitizer-enabled executable hung on this Mac and was stopped; sanitizer validation is unresolved. Build products are ignored under `artifacts/prototype`. Recorded output is in `offline-tests.txt`.

## Gates before any flashable candidate

1. Verify exact hardware revision, GPIO/relay behavior, flash partition layout, bootloader, and recovery procedure from trustworthy matching materials. The older GPL tree is not enough to certify the installed board.
2. Obtain matching 11565 image/binaries where possible; compare startup and update constraints. No update-signature bypass has been established.
3. Choose stock-userspace application versus full OS replacement. These require different runtime and boot validation; replacing the OS also needs working Wi-Fi drivers and board support.
4. Port and compile the actual pinned SDK for MIPS32r2 with a compatible libc, C++ runtime, crypto, atomics, IPv6 and mDNS support. Measure RAM, flash and CPU costs.
5. Integrate a mock relay into an actual Matter On/Off Plug-in Unit endpoint (not merely a light), test commissioning, commands, subscriptions, fabrics, restart and persistence with a local controller on an isolated test network.
6. Validate the target root filesystem/kernel in an appropriate emulator where possible. QEMU user mode does not model the MT7688 Wi-Fi, flash or GPIO hardware.
7. Implement and verify board-specific relay backend and recovery on suitable hardware before proposing any deployment to the user's only plug. Offline testing cannot eliminate this hardware validation requirement.

No step here authorizes flashing, opening, resetting, or changing the Wemo. No flashing utility or device-upload command is included.
