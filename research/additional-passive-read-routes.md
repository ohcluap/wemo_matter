# Additional Wi-Fi read-route investigation — 2026-10-24

No installed firmware or bootloader was recovered in this investigation. No
device requests, installation, flashing, reset, setting changes, or exploit
probes were performed during this pass. Static conclusions below concern the
archived **11420** package, not the unavailable installed **11565** implementation.

## Storage daemons

The names `NvramDaemon` and `HomekitStoreDaemon` suggested possible export
services. Static inspection instead identifies process-local access to shared
memory. `libNvramInit` loads `shm_open` at 0x4c34, `mmap` at 0x5388, and
`sem_init` at 0x5460 (pshared argument 1). `libhomekitstoreInit` loads
`shm_open` at 0x1b40 and `mmap` at 0x241c. These are instruction addresses in
the archived ELF libraries, not addresses on the running plug.

Neither library nor either command-line client imports the selected socket
functions. Raw syscalls and indirect wrappers remain possible; import absence
is not a proof of complete network isolation. No network-callable wrapper that
exports firmware or bootloader bytes was established by this inspection.

Reproduce the hash and import inventory with
`python scripts/audit_storage_read_transports.py`; it reads local artifacts only.
Results: [storage transport inventory](storage-read-transport-inventory.json).
Disassemblies can be regenerated with `scripts/inspect_vendor_function.py`.

## HTTP XML alias and range handling

The reconstructed vendor-patched `webserver.c` SHA-256 is
`f8bc2e2c5ceb92622d2914c111ee497b69653cdd5c46bc6dc152241cb9d6a187`.
The locally extracted `httpreadwrite.c` SHA-256 is
`f8e78dd5c35752e70ddb10c0cfa95275f203dd640c9db84a71551361e2b43226`.
Both are retained under ignored `artifacts/http-audit/`.

The XML alias is attached to a supplied memory buffer and its recorded length
(`web_server_set_alias`, lines 430–458). `RESP_XMLDOC` passes that buffer and
length to `http_SendMessage` using `Ibb`. The `b` branch in `httpreadwrite.c`
lines 528–534 sends the supplied length; it does not apply a client-selected
range offset to the XML pointer. The file branch uses `fopen` and `fseeko` on
the already selected filename (lines 418–443).

This trace does not identify an arbitrary-memory or flash read through XML
range requests. It is not a general parser-security proof: malformed-input,
integer-overflow and concurrency behavior have not been exhaustively tested.
No malformed range requests were sent to the device.

## Existing files under the HTTP root

The reproducible inventory scanned 155 text files up to 300,000 bytes in the
SNSV2 product files, shared base files, ramips base files and SNSV2 board base
files. It found no `core_pattern`, `coredump`, or `/proc/kcore` references in
that bounded scope. It records source hashes and line numbers without
redistributing the full source.

The board boot script mounts the settings partition at `/tmp/Belkin_settings`
(lines 100–104); `startWemo.sh` serves that directory. The updater's
`Belkin_settings/last_update` reference records update metadata, not a firmware
copy. No startup-created firmware or bootloader export was identified. This
does not enumerate current runtime files or prove that compiled code cannot
create other files. See also the earlier
[cached update path audit](cached-update-path-audit.json).

## Published disclosure lead

The IMC 2023 paper
[In the Room Where It Happens](https://dspace.networks.imdea.org/bitstream/handle/20.500.12761/1746/IMC-181-accepted.pdf?isAllowed=y&sequence=1)
mentions WeMo DNS information disclosure on page 9. It concerns recently
resolved domain names, not firmware memory; the authors explicitly did not
validate that attack's feasibility. Its reference 93 is
[Tenable plugin 12217](https://www.tenable.com/plugins/nessus/12217), which
describes DNS cache snooping. Neither source supplies a firmware-dump route.
No DNS snooping probe was sent.

A separate current F7C063 local-control blog appeared in search results, but
its full article/feed could not be retrieved (empty rendered index, unavailable
feed, direct HTTPS 403). Its snippet is not treated as evidence of shell access
or recovery. No linked third-party GitHub repository was accessed.

## Remaining evidence gap

These leads do not establish a safe Wi-Fi-only read primitive or independent
recovery. A dump alone would also be insufficient: restoring it must remain
possible when the modified application or ordinary Linux network stack fails.
Further progress requires a demonstrable network read/export path, exact
11565 implementation evidence, or documented independent Wi-Fi recovery.
Do not convert this negative result into an experimental on-device exploit or
install permission. The no-install/no-flash gate remains closed.
