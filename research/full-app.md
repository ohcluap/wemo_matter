# Complete native Matter outlet simulator — tested 2026-10-18 EDT

**Built and successfully commissioned a complete Matter On/Off Plug-in Unit simulator and controlled it using the real SDK `chip-tool`.** This is a Linux ARM64 build for the Mac's Docker environment. It is not a full MIPS build, firmware image, or evidence that the application runs on the Wemo.

## Verified result

[Machine-readable results](commissioning-results.json) record the integration run. The test verified:

1. On-network discovery using discriminator 3840, followed by successful commissioning with the SDK's test credentials.
2. Endpoint 1 reports device type 266 (0x010A), On/Off Plug-in Unit.
3. Off command succeeds and the OnOff attribute reads false.
4. On command succeeds and the OnOff attribute reads true.
5. Toggle command succeeds and the OnOff attribute returns to false.
6. The application's simulated relay callback logs both on and off transitions.
7. After restarting the device process/container while retaining its test storage, the controller reads and controls the outlet again without recommissioning.
8. The temporary Docker network is internal with IPv6 enabled, and is removed along with the simulator/controller containers after testing.

The restart test verifies retained commissioning and subsequent control, not a guaranteed relay startup-state policy. The relay is an in-memory mock. No electrical switching occurs.

Pairing uses the SDK's test attestation trust store and test device credentials. No attestation-bypass option is passed. This is development interoperability testing, not Matter certification or a production identity/provisioning solution.

## Implementation

The [app adaptation](../app/README.md) changes the pinned SDK Linux lighting example's model to an outlet, removes its Level/Color Control clusters, disables its lighting feature, and adds explicit simulated-relay logging. The upstream binary filename remains `chip-lighting-app`. `scripts/configure_outlet.py` records the changes reproducibly and verifies the SDK commit before applying them.

ZAP regenerates the `.matter` description and endpoint C++ from the edited model. Generated device metadata was also checked to contain `{0x0000010A,3}`. The native application uses the SDK's full server, commissioning, secure-channel, persistence, discovery and Interaction Model paths; this is not a replacement protocol or a hand-written imitation.

The previously developed small relay component and MIPS TLV/crypto tests remain independent. This simulator uses the upstream example's in-memory manager, not a physical GPIO driver.

## Isolation

Builds use `--network none` after dependency preparation. Runtime tests create a uniquely named `docker network --internal --ipv6`, use two separate containers without published ports, drop capabilities, and use read-only roots. The test verifies the network's isolation flag through Docker inspection. Its only mutable mounts are dedicated test-state directories under `artifacts/full-app/tests/`.

The network is private to these test containers. No home-device discovery, Wemo API requests, settings changes, opening, flashing, or firmware uploads occur. Existing Home Assistant and unrelated containers are untouched.

Raw logs and generated fabric/commissioning credentials remain ignored locally. Only the summary, source scripts and build metadata are committed. Do not publish the detailed generated state as production credentials.

## Reproduce on this Apple Silicon Mac

```sh
sh scripts/prepare_full_app.sh
sh scripts/build_full_app.sh
sh scripts/build_controller.sh
python3 scripts/test_commissioning.py
```

Preparation requires network access to download build dependencies. Compilation and the integration run do not need Internet access. The runtime test is offline relative to the home network and Internet; the two simulated devices communicate on their private virtual network.

- App binary: `artifacts/full-app/native/chip-lighting-app`
- Controller: `artifacts/full-app/controller/chip-tool`
- Local detailed logs/state: `artifacts/full-app/tests/<run-id>/`
- Sanitized result: `research/commissioning-results.json`
- Input/output provenance: [full-app-build.json](full-app-build.json)

The scripts target Linux ARM64 Docker on this Mac and use an ARM64 ZAP executable. They are not a portable cross-compilation recipe for MIPS or an Intel-host recipe. The full SDK checkout and builds use additional disk space; all downloaded/generated material stays in ignored directories.

## Remaining Wemo work

A subsequent [full MIPS build](full-mips-app.md) now passes commissioning, on/off/toggle and retained-commissioning restart checks under QEMU 24KEc. Those results do not establish compatibility with the actual Wemo kernel/board, physical relay, memory limits or CPU timing. Hardware resource assessment, exact hardware/firmware and recovery validation remain required before considering any physical deployment.
