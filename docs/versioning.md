# Versioning & Compatibility

RaceLink is split across four source repositories, each of which has
its own version stream:

* `racelink-host` — Python wheel, version exposed as
  `racelink.__version__` and via `racelink-host-version`.
* `RaceLink_Gateway` — ESP32-S3 firmware. Version reported in the
  device's identification string.
* `RaceLink_WLED` — WLED usermod + build profiles. Version stored
  in `version.json`; firmware artefacts published per profile.
* `RaceLink_RH_Plugin` — RotorHazard plugin. Plugin version stored in
  `custom_plugins/racelink_rh_plugin/manifest.json`; the embedded
  host wheel is pinned per release.

## Wire-protocol version

The wire format carries a separate, **wire-only** version pair in
`racelink_proto.h`:

```c
PROTO_VER_MAJOR = 2
PROTO_VER_MINOR = 0
```

Bump rules:

* **Bump `MINOR`** for backward-compatible additions: a new opcode
  whose absence is harmless, a new optional flag bit, etc.
* **Bump `MAJOR`** for breaking changes: a struct reshape, an opcode
  reused with new semantics, etc.

`tests/test_proto_header_drift.py` in the host repository verifies
that the three byte-identical copies of `racelink_proto.h` (Host,
Gateway, WLED) agree. An intentional protocol change still requires
a coordinated commit across all three repositories.

## Cross-component compatibility

The components do **not** share a version number — there is no
"RaceLink 1.0" stream. Compatibility is established at the wire-
protocol layer (a host targeting `PROTO_VER_MAJOR=2` interoperates
with any gateway/WLED that also targets `PROTO_VER_MAJOR=2`).

A practical rule of thumb:

| Direction | Compatibility expectation |
|---|---|
| Host ↔ Gateway | Major-version-aligned. `OPC_SYNC` extends from 4 → 5 bytes; older gateways accept the 5 B form, but a node flashed with old firmware rejects the trailing flags byte. **Synchronised rollout required** for the 5-byte SYNC form. |
| Host ↔ WLED node | Major-version-aligned. Older nodes silently drop unknown opcodes; new opcodes on a host running an old node fleet are no-ops. |
| Gateway ↔ WLED node | Same. |
| Host ↔ RH plugin | Plugin imports `racelink-host` as a package; the plugin manifest pins an immutable host wheel. The plugin's own version moves independently. |

## Release flows

* **Host wheel.** `.github/workflows/release.yml` (Actions UI). See
  [`RaceLink_Host/README.md`](RaceLink_Host/README.md) §Release artifacts. Output:
  `racelink_host-<version>-py3-none-any.whl`,
  `racelink-host-<version>.tar.gz`,
  `racelink-host-<version>-sha256.txt`.
* **Gateway firmware.** Built locally with PlatformIO; release flow
  is currently undocumented in the source.
* **WLED firmware.** `.github/workflows/release.yml` in
  `RaceLink_WLED`. Resolves the latest official WLED release unless
  a `wled_ref` override is supplied; bakes `version.json` into the
  build artefacts. See [`RaceLink_WLED/README.md`](RaceLink_WLED/README.md)
  §"GitHub release workflow".
* **RH plugin.** `.github/workflows/offline-release.yaml` in
  `RaceLink_RH_Plugin`. Resolves the latest published `RaceLink_Host`
  release (or an explicit override), bumps the manifest version,
  builds the offline ZIP. See
  [`RaceLink_RH_Plugin/release-playbook.md`](RaceLink_RH_Plugin/release-playbook.md).

## Gateway / firmware version reporting

* The **gateway** identifies itself via `GW_CMD_IDENTIFY` (a
  USB-only command); the reply carries an identity string with the
  device type (`DEV_TYPE_STR="RaceLink_Gateway_v4"`).
* **WLED nodes** carry `WLED_RELEASE_NAME` baked at build time. WLED's
  `/json/info` endpoint returns it; the host's OTA workflow uses it
  to validate firmware compatibility (Gate 4 of the OTA acceptance
  check — see
  [`RaceLink_Host/developer-guide.md`](RaceLink_Host/developer-guide.md) §"WLED
  OTA gate matrix").

## When to bump what

| Change | Bump |
|---|---|
| Add a new opcode (backward compatible) | `PROTO_VER_MINOR` + the patch version of the originator (host or firmware that introduces it); coordinated PR across the three repos |
| Reshape a struct or reuse an opcode value | `PROTO_VER_MAJOR` + matching synchronised release of all three repos |
| Add a host-only feature (no wire change) | host patch version |
| Fix a host-only bug | host patch version |
| WLED usermod-only change | RaceLink_WLED patch version |
| Gateway firmware-only change | gateway patch version |
| RH plugin glue change | plugin patch version (host wheel pin can stay the same) |
