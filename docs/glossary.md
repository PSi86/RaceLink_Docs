# RaceLink Glossary

Single canonical reference for every RaceLink term that an operator,
contributor, firmware developer or plugin maintainer might encounter.
Where a term has both an operator-friendly meaning and a wire-level
definition, both are given; cross-link to the deeper reference at the
end of each entry.

## Operator-facing concepts

### Device

One piece of RaceLink hardware (a WLED node, a starting block, …).
Identified by its 12-character MAC address; the host shows the last
six in the device table for brevity. Has a *type* that determines its
*capability*.

### Group

A named bucket of devices. Operators usually group by physical
location ("Pit Wall", "Start Line", "Tower 3"). The group is what most
scene actions target — sending a packet to a group broadcasts to every
device whose `groupId` matches.

Group ids are `1..254`. Group `0` is the synthetic "Unconfigured"
group every newly-discovered device starts in. Group `255` is the
broadcast id (sent to every device). The full per-opcode rules
for who-acts-on-what are in the
[Broadcast Ruleset](reference/broadcast-ruleset.md).

### Group 0 / "Unconfigured"

The synthetic group that newly-discovered devices land in. Devices in
group 0 cannot be the target of a scene action; assign them to a real
group before saving scenes. The scene editor hides group 0 from
target dropdowns.

### All Devices (Broadcast)

The user-facing label for the wire broadcast option in every
scene-editor target picker and every RH-plugin group dropdown. On
the wire it maps to `recv3 = FFFFFF` plus `groupId = 255` — every
device parses the packet and (for the workhorse opcodes
`OPC_PRESET` / `OPC_CONTROL` / `OPC_OFFSET`) accepts it. Selecting
every currently-known group manually canonically *is* a broadcast:
the host's save-time canonicaliser rewrites the persisted scene to
`{"kind": "broadcast"}` so the runtime and the cost estimator agree
on the wire path. Full per-opcode rules live in the
[Broadcast Ruleset](reference/broadcast-ruleset.md). The internal
JSON discriminator was previously called `scope` (offset_group
children only) — that name now refers exclusively to SSE channel
scopes; persisted `"scope"` shapes are migrated to `"broadcast"`
on read.

### Capability

What a device can do, derived from its type. Today: `WLED` (LED
control) and `STARTBLOCK` (race-start hardware). A starting block is
also `WLED`-capable; a plain WLED node is not `STARTBLOCK`-capable.
The scene editor filters target dropdowns by capability so a
non-capable target cannot be selected by accident.

### Preset

The word "preset" refers to **two distinct things** in RaceLink — a
historical artefact that the codebase was cleaned up to
disambiguate (the 2026-04-25 protocol-naming cleanup):

* **WLED preset** — a numeric slot (0–255) on a WLED node's own
  preset list, configured via WLED's web UI. Applied by the
  `Apply WLED Preset` scene action, which sends an `OPC_PRESET`
  packet carrying just the slot number. Wire form: 4-byte
  `P_Preset` body.
* **RL preset** — a RaceLink-native named snapshot of effect
  parameters (mode, speed, intensity, colours, etc.) stored on the
  host. Applied by `Apply RL Preset`; the host materialises the
  parameters and sends an `OPC_CONTROL` packet (variable-length, up
  to 21 B body).

### Effect

The word "effect" has been disambiguated from "preset". An **effect**
is the set of WLED parameters that drive a segment's appearance:
`mode` (the effect-mode index, e.g. *Breathe* or *Rainbow Cycle*),
`speed`, `intensity`, custom sliders, palette, colours. Sent live via
`OPC_CONTROL` (the `Apply WLED Control` scene action).

A historical maintenance plan (the "effect vs. preset" cleanup) renamed
several misleading symbols in the source code so that "effect" now
means strictly "WLED segment effect parameters" and never "WLED preset
list". A few internal symbols still use the legacy term where renaming
is a public-API change; flag B1/B2 in the cleanup plan if you intend
to refactor further.

### Scene

A saved playlist of *actions* that runs in order. Persisted on the
host, runnable via the **Run** button on the Scenes page. See
[`reference/scene-format.md`](reference/scene-format.md) for the
on-disk format.

### Action

One step in a scene. Action kinds:

* `wled_preset` — `Apply WLED Preset` — load a numeric WLED preset
  on the target.
* `rl_preset` — `Apply RL Preset` — apply an RL preset (effect
  parameters) on the target.
* `wled_control` — `Apply WLED Control` — direct effect parameters
  in-line, no separate preset record.
* `startblock` — `Startblock Control` — send a starting-block
  program.
* `sync` — fire all devices waiting on arm-on-sync.
* `delay` — host-side wait between actions.
* `offset_group` — container action that runs its children with
  per-group time offsets (e.g. a chase / wave effect).

Each action carries an optional `flags_override` block that overrides
parts of the canonical flags byte; see *Flags* below.

### Offset Group

The container action that lets the same effect fire on N groups with
each group offset by a few ms — producing a wave or cascade effect
instead of a simultaneous fire. Configured via *Mode* (the formula
that turns each device's `groupId` into a per-device delay) plus
*Participants* and *Children*. See
[`RaceLink_Host/operator-guide.md`](RaceLink_Host/operator-guide.md) §6a for
the full operator workflow.

### Specials

Per-device-type configuration knobs (e.g. starting-block display
brightness, WLED-specific options). Edited via the device's
**Specials** dialog.

### Master pill

The coloured badge in the page header showing the current gateway
state (`IDLE` / `TX` / `RX-WIN` / `RX` / `ERROR` / `UNKNOWN`). The
host receives the state byte directly from the gateway via
`EV_STATE_CHANGED` events — it never infers state from outcome
events. Hover for the full explanation; click ↻ to refresh.

### Gateway

The USB dongle that bridges the host to the LoRa fleet. The host
opens it with `exclusive=True` so only one process can hold the
port at a time.

## Wire-protocol terms

### Header7

Every LoRa-bearing packet's 7-byte prefix: `sender3 (3) | receiver3
(3) | type_full (1)`. `sender3` and `receiver3` are the last 3 bytes
of the MAC address; `type_full` combines the direction bit and the
7-bit opcode.

### Direction byte

`DIR_M2N = 0x00` (Master → Node, host outgoing) and `DIR_N2M = 0x80`
(Node → Master, node reply). The high bit of `type_full` selects
direction; the receiver checks direction first and silently drops
wrong-direction frames.

### Opcode (`OPC_*`)

7-bit identifier of the packet type. Defined in `racelink_proto.h`.
The current set includes:
`OPC_DEVICES`, `OPC_SET_GROUP`, `OPC_STATUS`, `OPC_PRESET`,
`OPC_CONFIG`, `OPC_SYNC`, `OPC_STREAM`, `OPC_CONTROL`, `OPC_OFFSET`,
plus `OPC_ACK` used as a reply only. See
[`reference/wire-protocol.md`](reference/wire-protocol.md) §Opcodes for the full
table.

### Flags byte

A single byte shared across `OPC_PRESET` and `OPC_CONTROL` (and the
persisted RL-preset form):

| Bit | Constant | Meaning |
|---|---|---|
| 0 | `RL_FLAG_POWER_ON` | Brightness > 0 (auto-derived) |
| 1 | `RL_FLAG_ARM_ON_SYNC` | Defer apply until next `OPC_SYNC` |
| 2 | `RL_FLAG_HAS_BRI` | Brightness field is meaningful |
| 3 | `RL_FLAG_FORCE_TT0` | Force transition time 0 (no fade) |
| 4 | `RL_FLAG_FORCE_REAPPLY` | Re-apply even if state hasn't changed |
| 5 | `RL_FLAG_OFFSET_MODE` | Use the device's stored offset (gates participation) |

Always built via `racelink/domain/flags.py::build_flags_byte` on the
host side — never hand-assemble.

### `ARM_ON_SYNC`

A flag bit that defers an action's apply until the next `OPC_SYNC`.
Used to fire effects on multiple devices simultaneously (with offset
mode adjusting the per-device delay).

### `OFFSET_MODE`

A flag bit that says "use the device's stored offset configuration".
When set, the device participates in offset mode (the effect plays
with its per-device delay); when unset, the device plays the effect
without offset.

The acceptance gate is **strict and symmetric**: a packet with
`OFFSET_MODE=1` is dropped if the device has no offset configured
(`pendingChange.mode == NONE` and no active offset); a packet with
`OFFSET_MODE=0` is dropped if the device is currently in offset
mode. See [`reference/wire-protocol.md`](reference/wire-protocol.md)
§"Acceptance gate" for the full table.

### Pending change / pending-deferred

Receivers store a configuration change (e.g. an `OPC_OFFSET` packet)
as a *pending change* until it is *materialised* — either by the
next accepted `OPC_PRESET`/`OPC_CONTROL` (immediate-apply path) or by
`OPC_SYNC` (deferred-apply path).

The materialisation step writes the pending state into the active
state and clears the pending flag. The split exists so an operator
can configure offsets first and fire the effects later, rather than
having to atomically push everything in one packet.

### Strip timebase / `strip.now`

WLED maintains a per-segment time base
(`strip.now = millis() + strip.timebase`) that effects use to compute
their animation. RaceLink synchronises `strip.timebase` across nodes
via `OPC_SYNC`, so deterministic effects render identically — a
prerequisite for offset mode and ARM-on-SYNC.

The phase-lock issue (covered in
[`concepts/opcodes.md`](concepts/opcodes.md) §"Cyclic-effect
phase-lock") is what happens when this synchronisation also makes
time-dependent cyclic effects
phase-lock instead of staying offset; the firmware applies a
persistent per-device phase offset to `strip.timebase` to keep cyclic
effects offset.

### `EV_TX_DONE` / `EV_TX_REJECTED`

Outcome events emitted by the gateway for every host-initiated
frame. Exactly one outcome arrives per call: `EV_TX_DONE` for a
successful transmit, `EV_TX_REJECTED` (with a reason byte —
`TX_REJECT_TXPENDING`, `TX_REJECT_OVERSIZE`, `TX_REJECT_ZEROLEN`,
`TX_REJECT_UNKNOWN`) for a refusal.

### `EV_STATE_CHANGED` / `EV_STATE_REPORT`

Transition event (`STATE_CHANGED`) and reply to a manual query
(`STATE_REPORT`). Both carry the gateway's state byte and any state
metadata. The host's master pill mirrors this state byte 1:1.

### Response policy (`RESP_*`)

Each opcode has a `(direction, response)` rule in
`racelink/protocol/rules.py::RULES`. Possible policies are
`RESP_NONE` (fire-and-forget; broadcasts, `OPC_SYNC`, `OPC_OFFSET`),
`RESP_ACK` (receiver replies with `OPC_ACK`; most M2N unicasts) and
`RESP_SPECIFIC` (receiver replies with a specific opcode, e.g.
`OPC_DEVICES` → `IDENTIFY_REPLY`).

## Host-runtime terms

### `state_repository.lock`

The single state lock (`RLock`) protecting device + group repository
mutations and iterations. **Never hold across RF I/O** — that
deadlocks the gateway reader thread. See `RaceLink_Host/architecture.md` §
"Locking Rule".

### `_tx_lock` / `_tx_outcome_cv`

Pair of primitives (`Lock` + `Condition`) inside
`gateway_serial.py` that serialises USB writes and pairs each
`_send_m2n` call with its outcome event. The `Condition`'s
`_tx_in_flight` predicate is the lost-wakeup-safe replacement for
the older `Event` pattern.

### Pending request registry

`racelink/services/pending_requests.py`. Tracks unicast requests
that expect a reply, matched by `(sender, ack_of_or_opc)`. Replaces
the deprecated `wait_rx_window` helper for the host's
synchronous-reply contract.

### State scope token

A token from `racelink/domain/state_scope.py` (`FULL`, `NONE`,
`DEVICES`, `DEVICE_MEMBERSHIP`, `DEVICE_SPECIALS`, `GROUPS`,
`PRESETS`) that names the kind of state change a `save_to_db(...)`
call represents. Drives selective UI updates in both the
RotorHazard adapter and the SSE-fed browser WebUI.

### Standalone mode

A hosting mode where RaceLink runs as its own Flask app with the
shared RaceLink WebUI mounted at `/racelink`. The packaged entry
point is `racelink-standalone`. Default bind:
`http://127.0.0.1:5077/racelink`.

### Plugin mode (RotorHazard)

A hosting mode where the `RaceLink_RH-plugin` adapter installs into
RotorHazard, imports `racelink-host` as a package, and mounts the
shared WebUI inside the RotorHazard process. The plugin owns the
gateway in this mode (RotorHazard itself does not open the dongle).

## Build / release terms

### Build profile (WLED)

A `.platformio_override.ini` file under `RaceLink_WLED/build_profiles/`
that captures the per-hardware-variant compile-time settings (modem,
SPI pins, LED pins, battery measurement, optional e-paper). Profiles
shipped today: `RaceLink_Node_v1_c3_ct62`,
`RaceLink_Node_v3_s2_llcc68`, `RaceLink_Node_v3_s2_llcc68_epaper`,
`RaceLink_Node_v4_s3_llcc68`.

### `cfg.json`

WLED's persistent configuration file under LittleFS. Contains the
effective values of `otaSameSubnet`, `otaLock`, `otaPass` and so on.
A `/settings/sec` POST writes back to it.

### `WLED_RELEASE_NAME`

A compile-time string that WLED stamps into its firmware binary; used
by Gate 4 of the OTA acceptance check (a binary's `WLED_RELEASE_NAME`
must match the running firmware unless the operator ticks "Skip
firmware-name validation"). See
[`RaceLink_Host/developer-guide.md`](RaceLink_Host/developer-guide.md) § "WLED
OTA gate matrix".

### `RHFest`

The RotorHazard-Fest validator that gates plugin manifests on
RotorHazard's plugin store. Accepts dependency entries either as a
package name with optional version specifier, or as a `git+https://…`
URL (the format RaceLink_RH_Plugin uses). See ADR-0001 in
[`RaceLink_RH_Plugin/adr-0001-manifest-dependency.md`](RaceLink_RH_Plugin/adr-0001-manifest-dependency.md).
