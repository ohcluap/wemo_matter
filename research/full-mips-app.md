# Full MIPS Matter application

This work cross-compiles the complete SDK outlet server for little-endian MIPS32r2 with the soft-float ABI, using OpenWrt GCC 13.3.0 and musl. It uses the same outlet adaptation as the native simulator, with mbedTLS selected for cryptography and static linking. The relay remains simulated.

## Verified result — 2026-10-18 EDT

The complete MIPS application passed all 12 commissioning/control checks on QEMU's 24KEc CPU model. The native ARM64 controller discovered and commissioned the MIPS device, verified endpoint 1 as an On/Off Plug-in Unit (266), sent off/on/toggle commands and read back their expected states. The MIPS application's simulated relay callbacks recorded both transitions. After restarting the MIPS process with its retained storage, the controller could read and switch it on without pairing again.

[Test results](mips-commissioning-results.json) include the tested binary's SHA-256 and successful network cleanup. [Build provenance](full-mips-build.json) records compiler/SDK inputs, GN flags, ELF headers, image identities and binary hash. The executable is 8,774,268 bytes before stripping; its text/data/BSS sections total 2,153,788 bytes. Neither figure establishes actual peak RAM requirements or a fit within the Wemo's firmware partitions.

## Reproduce

On this Apple Silicon Mac with Docker Desktop and x86-64 executable support:

```sh
sh scripts/prepare_musl.sh
sh scripts/prepare_full_app.sh
# ARM64 QEMU runtime; separate from the native controller image.
docker build -f toolchains/Dockerfile.offline-tests -t wemo-matter-offline-tests:bookworm .
sh scripts/build_controller.sh
sh scripts/build_mips_app.sh
python3 scripts/test_commissioning.py --target mips
```

For a fresh checkout, the full-app preparation expands the component preparation's sparse SDK checkout. Component preparation preserves an already complete checkout. Downloads occur only during preparation. The full MIPS build runs with networking disabled. Its cross-compiler is an x86-64 host executable invoked from the ARM64 build container through Docker's executable emulation; its output is MIPS.

The build checks the SDK and mbedTLS revisions, verifies the output's soft-float ABI and MIPS32r2 flags, and rejects a dynamic interpreter. ZAP and SDK pins are shared with the [native build](full-app-build.json); the OpenWrt archive checksum is verified by `prepare_musl.sh`.

## Static C++ runtime correction

The first full link exposed missing `_Unwind_*` symbols from the SDK's `libstdc++.a`. The OpenWrt compiler's shipped `*libgcc` specs select only `-lgcc` for static links, even though the SDK supplies the matching `libgcc_eh.a` containing these symbols. `toolchains/mips-static.specs` includes that archive in the compiler's normal static runtime group. It does not replace unwinding with stubs or suppress unresolved symbols. The application still uses the Matter SDK's default disabled C++ exceptions.

`enable_pie=false` avoids combining the SDK's default PIE link flag with the explicitly static executable. Position-independent object compilation remains enabled. The SDK's relocated host wrapper emits `runas.so` preload warnings on this Docker setup; these do not stop compilation. ELF validation and execution tests check the resulting target binary independently.

## Emulator scope

The device command is `qemu-mipsel -cpu 24KEc /bin-output/chip-lighting-app`. The controller remains native Linux ARM64. Both processes communicate only over a temporary internal IPv6-enabled Docker network; there are no published ports, host networking, home-network discovery, or Wemo requests.

QEMU user emulation executes MIPS instructions and translates Linux system calls into the Docker VM's modern host kernel. It does not emulate the Wemo's board, original kernel, flash layout, Wi-Fi, GPIO, RAM capacity or timing. Static musl linking avoids dependence on the stock uClibc loader but does not establish old-kernel compatibility. This is an executable, not an installable firmware image or a validated deployment path.

Commissioning uses SDK test identities and the controller's development trust store. Physical relay controls, production attestation/provisioning, hardware resource validation, exact firmware acquisition, recovery and deployment remain outside this test. No Wemo changes are made.

## Subsequent firmware integration

The [firmware readiness assessment](firmware-readiness.md) adds stripped payload measurements, bounded-memory protocol tests, tested clock fallback and a persistent-storage firmware profile. It records remaining board, kernel, Wi-Fi, relay and installation requirements.
