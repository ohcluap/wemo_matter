# Offline Matter outlet simulator

The full application is built from the pinned connectedhomeip Linux example, with a small reproducible adaptation applied by `scripts/configure_outlet.py`:

- Endpoint 1 identifies as On/Off Plug-in Unit (0x010A), revision 3, matching the pinned SDK device definition.
- Level Control and Color Control clusters are removed from the endpoint model.
- The OnOff lighting feature is disabled.
- The existing in-memory manager remains the simulated relay. On/off attribute callbacks validate the endpoint/value and emit `SIMULATED_RELAY on=0/1`.
- There is no GPIO implementation, Wemo API call, firmware upload, or flash-writing code in the adaptation.

The model's `.matter` file and generated C++ are regenerated with the SDK's pinned ZAP version. The upstream SDK's application filename remains `chip-lighting-app`; its generated endpoint model is the outlet described above. Do not infer the device type from that filename.

The source adaptation intentionally operates in the ignored SDK checkout. The checked-in Python script is the authoritative patch, and refuses to run against a different SDK commit. Downloads, generated binaries, detailed protocol logs, and generated test credentials stay under ignored `sources/` and `artifacts/`.

The native simulator is a Linux arm64 application for offline protocol testing, not a MIPS executable or Wemo firmware. The earlier MIPS component tests remain separate.
