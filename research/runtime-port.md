# Soft-float runtime and real Matter SDK components

## Result

The OpenWrt 24.10.4 ramips/mt76x8 SDK provides a **candidate GCC 13.3.0 + musl soft-float runtime that passes our MIPS 24KEc user-mode emulation tests**. The previous floating-point ABI blocker is resolved for these test executables. This does not establish compatibility with the stock Wemo kernel, drivers, bootloader, memory limits, or application ABI.

The tests now compile and execute actual, unmodified Matter SDK v1.6.1.0 TLV and cryptographic implementation sources. This is partial port validation, **not a working Matter device/server or firmware image**. The complete SDK's GN build and Linux application have not been built.

## Provenance

- [OpenWrt official SDK directory](https://downloads.openwrt.org/releases/24.10.4/targets/ramips/mt76x8/)
- SDK filename: `openwrt-sdk-24.10.4-ramips-mt76x8_gcc-13.3.0_musl.Linux-x86_64.tar.zst`
- SHA-256 verified against the official directory's checksum: `036230a0197b586459565d0e349c7d4ee66c92d111991d874d63c66a6c0451a3`.
- Matter: [v1.6.1.0 / 3bcdd56ba54fb88b2afb4bfef575014671df7aa7](https://github.com/project-chip/connectedhomeip/tree/3bcdd56ba54fb88b2afb4bfef575014671df7aa7).
- SDK-pinned mbedTLS: `6a58fa8122c9bb8ee1644733d21b5677c93f1169` (2.28.10).
- SDK-pinned nlio: `0e725502c2b17bb0a0c22ddd4bcaee9090c8fb5c`.
- Compiler flags: C++20, MIPS 24KEc, o32, soft float, static linking, exceptions and RTTI disabled. No flags disable test assertions.
- Builds run in a Debian amd64 container on the Apple Silicon Mac, using the official OpenWrt host tools. The toolchain directory and SDK are mounted read-only.

The OpenWrt download is a build SDK, not a Wemo firmware image. We have not downloaded or selected a router firmware image to install on the outlet.

## Tested under QEMU `-cpu 24KEc`

| Executable | What actually runs | Verified behavior |
| --- | --- | --- |
| `test-relay` | Our mock relay controller | On/off, routing, invalid inputs, redundant commands, failed writes, retry and restart state |
| `test-runtime` | C++/musl/POSIX runtime | Software floating point, pthread creation/join, mutexes, 32-bit atomics, monotonic clock, entropy and IPv6 socket creation |
| `test-matter-tlv` | SDK TLVReader, TLVWriter, TLVTags and supporting code | Exact expected wire bytes, encode/decode roundtrip, truncated input rejection and bounded output |
| `test-matter-crypto` | SDK CHIPCryptoPAL and mbedTLS backend | 53 upstream AES-CCM known-answer/error vectors; SHA-256 known answer; AES-CCM roundtrip and tag tamper rejection; P-256 signing, verification and modified-message rejection |

All four executable ELF files are checked for soft-float ABI and absence of a dynamic interpreter. Static musl avoids depending on stock Wemo uClibc shared libraries; it still depends on kernel syscalls and resource availability. ELF metadata and QEMU execution do not replace a test on the real kernel.

See [recorded output](musl-tests.txt) and [artifact hashes/sizes](musl-artifacts.json). The sizes describe test programs, not a complete Matter application's flash/RAM requirements.

## Implementation details and discoveries

- A Bootlin musl toolchain was evaluated first. Its startup objects advertised hard-float despite compiling our source with `-msoft-float`. It was rejected. Passing one small program is insufficient proof of ABI consistency.
- OpenWrt's static C++ runtime did not satisfy exception-unwinding symbols pulled in by an initial `std::thread` probe. The test now exercises pthreads directly with exceptions disabled, consistent with this component build. This does **not** claim general exception-enabled libstdc++ support.
- No Matter or crypto functions are mocked. The tests link the upstream implementations. Our `OfflineConfig.h` only sets a minimal component-test configuration, with logging disabled, POSIX/socket settings, and little-endian memory settings; it is not a finished Linux platform configuration.
- The crypto build uses the pinned mbedTLS default configuration, not an optimized shipping configuration. No security/certification or side-channel claims are made.
- Crypto entropy is supplied by the emulated process's host environment. Actual Wemo entropy behavior remains untested.
- QEMU user mode forwards syscalls to the modern container host kernel. IPv6 socket creation does not prove multicast discovery, routing, firewall rules, old-kernel compatibility, or commissioning. Nothing binds a service or sends device traffic.

## Reproduce

```sh
sh scripts/prepare_musl.sh
sh scripts/test_musl.sh
```

Preparation downloads pinned sources and build tools. After preparation, compilation and execution run inside `--network none` containers with a read-only root, dropped capabilities and no privileged/device mounts. Inputs are read-only; output is restricted to the local `artifacts/musl` directory and temporary files. Execution has per-test timeouts.

For a clean crypto dependency rebuild, rename the local generated `artifacts/musl/mbedtls` directory before running the test script. It caches the pinned dependency's build outputs; it is not committed. `sources/`, binaries, generated headers and downloaded archives remain ignored. No Wemo vendor executable is executed.

## Remaining work toward an actual Matter port

1. Integrate this toolchain with the full SDK build graph and Linux platform configuration. Resolve its platform dependencies with soft-float target libraries; do not silently mix host or hard-float libraries.
2. Build an On/Off Plug-in Unit endpoint with a mock relay backend. Test the real Interaction Model, attribute reporting and relay failure reconciliation rather than equating local TLV tests to end-to-end commands.
3. Run controller/device commissioning and encrypted commands in an isolated virtual network. Validate persistent fabrics/keys, restart behavior, PASE/CASE and mDNS. None of these paths are tested yet.
4. Measure full application's RAM, stack, CPU, flash and startup requirements; evaluate the exact stock kernel's syscalls and network capabilities.
5. Only after board identification, exact-image analysis and recovery design can a hardware backend or bootable image be evaluated. Kernel, Wi-Fi, partitioning and relay mapping remain independent blockers. No flashing is proposed or performed.
