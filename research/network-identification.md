# Read-only network identification — 2026-10-19

The user authorized read-only checks against the Wemo. Belkin-scoped SSDP located
one responding controllee. Its device description, ten advertised service
descriptors, four metadata getters and HomeKit mDNS advertisement were inspected.
See [sanitized request/results record](network-identification.json).

| Item | Live result | Confidence |
| --- | --- | --- |
| Product family | Wemo Mini | Confirmed by metadata prefix and HomeKit `md=Wemo Mini` |
| Hardware revision | `v2` | Reported by device description and GetInformation |
| Firmware | `WeMo_WW_2.00.11565.PVT-OWRT-SNSV2` | Reported by description, metadata, firmware getter and GetInformation |
| UPnP model number | `1.0` | Generic value; not a retail part number |
| SKU getter | `Plugin Device` | Generic value; not a retail part number |
| Retail part number | F7C063 remains inferred | No exact retail part number in checked live identity responses |
| Bootloader version | Unknown | Not returned by checked metadata or advertisement |

Only `GetMetaInfo`, `GetExtMetaInfo`, `GetFirmwareVersion` and `GetInformation`
were invoked. Each is an advertised metadata getter with output-only arguments.
UPnP encodes these reads as HTTP POST; no set/control/update action was sent.
Opaque extended-metadata numbers were not interpreted as bootloader versions.
The public HTTP `SERVER` description is generic, not a U-Boot version.

The advertised `GetManufactureData` action was intentionally skipped. Static
inspection of the older source package's `libUPnPHndlr.so` finds
`CreateManufactureData`, a manufacturing XML path and file-writing error strings.
That does not prove the installed handler writes on each call, but its lack of
side effects is not established, so it is unsuitable for this strictly read-only
pass. Log-generation/export and diagnostic execution actions were also excluded.

No device logins, commands, exploit attempts, pairing, relay controls, settings
changes, reset/reboot, firmware uploads or flash/environment operations were
performed. This is not a claim that a normally handled request causes no internal
logging or runtime counters; it means no state-changing device operation was
requested. Home Assistant configuration was read locally only to look for cached
device connection information; it was not changed.

Raw responses contain device identifiers and setup information and remain in
ignored private local artifacts. Committed evidence omits these values.

These checks improve identification to a network-confirmed Mini v2/SNSV2 family;
they do not resolve the exact retail variant, flash map, bootloader version or
recovery behavior needed before installing custom firmware. Absence from the
checked interfaces does not prove that every possible network path lacks this
information. No additional access or invasive probing was attempted.
