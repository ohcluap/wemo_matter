# Matter application on preserved stock firmware

2026-10-24. Local-only continuation. No device requests or GitHub activity.

## Why examine this route

Running Matter on the plug itself while retaining its Linux kernel, radio driver and vendor management processes still meets the no-external-bridge objective. It could reduce dependence on full-image replacement. It does not automatically provide installation access, persistence, resource capacity or recovery.

The existing [MIPS application report](full-mips-app.md) records a statically linked MIPS32r2/soft-float build. Static musl avoids the stock uClibc loader dependency. Prior QEMU protocol tests do not prove coexistence with stock processes or compatibility with the installed kernel. The measured application-container memory usage cannot be treated as spare RAM on a live plug.

## Storage check

The [recorded payload measurements](firmware-readiness.md) are 2,088,300 bytes stripped and 655,360 bytes for the packaged XZ SquashFS payload. These are historical build measurements in the repo, not a new local build or measurements from this plug.

The older 11420 DTS supplies a 327,680-byte rootfs_data region and a 589,824-byte Belkin_settings region. Neither individually holds that recorded packaged payload, before accounting for existing files and filesystem overhead. The normal startup script explicitly mounts Belkin_settings as JFFS2 at /tmp/Belkin_settings: a path under /tmp is therefore not necessarily volatile. [Captured source and hashes](stock-application-source-evidence.json) preserve the inputs.

The combined nominal capacity is 917,504 bytes. This arithmetic does not establish free space, support for a split payload, or a safe place to install one. Splitting payload data across these filesystems would couple the application to both configuration stores and still require an installation entry point and an audited startup/recovery design. Neither firmware slot nor identity/calibration regions may be assumed available as generic application storage.

## Recovery requirements for this alternative

- Preserve the original kernel/rootfs and stock networking startup. The candidate must not replace vendor Wi-Fi control just to launch Matter.
- First execution, if eventually authorized by verified recovery evidence, should be volatile and not automatically start again after reboot. A volatile proof alone does not meet persistent operation.
- Persistent launch must fail open for stock management: missing, corrupt or crashing Matter code must leave normal Wi-Fi and controls usable. A timeout inside a shell script does not prove recovery from earlier overlay or kernel failures.
- Verify where the vendor reset path obtains its code and whether reset still works after every contemplated persistent change. The known settings-reset function cannot be assumed callable without a working OS.
- Establish local execution access on installed 11565. The update unsigned flag is not such an entry point; no authenticated shell or supported third-party-app install interface is established by the existing evidence.
- Validate physical relay control, app coexistence, resources, persistence and Google Home commissioning. Existing mock-relay/dev-attestation emulator tests do not satisfy these requirements.

## Assessment

This route deserves consideration before a kernel replacement, but is not currently a verified safe installer. Storage capacity alone does not rule out a smaller or differently packaged application; neither does it establish a working persistent design. Exact installed behavior and a non-destructive execution/persistence route remain unresolved. No application was loaded or launched on the plug.
