# RaceLink Broadcast Ruleset

This page is the canonical reading of how RaceLink decides
**which devices act on a given M2N packet**. It captures the
two-stage filter pipeline (wire `recv3` → per-opcode body
checks), per-opcode behaviour, the combined accept matrix, and
the deliberate exceptions that exist by design.

If this page and `racelink_proto.h` disagree, the **header
wins** — file a bug. See also [Wire protocol
reference](wire-protocol.md), [Opcodes](../concepts/opcodes.md)
and [Scene format](scene-format.md) for adjacent material.

## Two-stage filter pipeline

Every M2N (master → node) packet is filtered in two stages
before any application code runs.

### Stage 1 — wire-level `recv3` (header)

Source: `RaceLink_WLED/src/racelink_transport_core.h`,
`receiverMatches()`.

```cpp
inline bool receiverMatches(receiver3, myLast3) {
  return isBroadcast3(receiver3) || same3(receiver3, myLast3);
}
```

* `recv3 == FF FF FF` — **wire broadcast.** Every device on the
  air parses the packet (it enters the per-opcode dispatcher).
* `recv3 == this device's last-3-MAC` — **wire unicast.** Only
  that device parses the packet.
* anything else — silently dropped before the dispatcher runs.

The Gateway forwards both `recv3` and `groupId` through verbatim;
it never inspects or rewrites them on the inbound path. On the
outbound path (LoRa → Host) the Gateway forwards N2M replies
whose `recv3` is the broadcast sentinel or the Gateway's own
last-3-MAC, and drops everything else. See [Gateway
role](#gateway-role) below.

### Stage 2 — per-opcode body filter

After Stage 1 passes, each opcode handler decides whether to
apply a `groupMatch` lambda on the body's `groupId` byte:

```cpp
auto groupMatch = [&](uint8_t inGroup) {
  return (inGroup == current.groupId || inGroup == 255);
};
```

Stage 2 is **opcode-specific**. Some opcodes apply the filter,
some skip it, and one (`OPC_CONFIG`) actively rejects broadcasts
in Stage 1 (see "Designed-in special cases" below). The full
table is in [Per-opcode rules](#per-opcode-rules) below.

## Per-opcode rules

| OpCode | Stage 1 (`recv3`) | Stage 2 (body `groupId` filter) | Reply policy | Notes |
|---|---|---|---|---|
| `OPC_DEVICES` (0x01) | accept broadcast or unicast | `groupMatch` applied | `RESP_SPECIFIC` (IDENTIFY_REPLY) | Host default emission `groupId=0` deliberately targets unconfigured devices. See [Designed-in special cases](#designed-in-special-cases). |
| `OPC_SET_GROUP` (0x02) | unicast only (Host always sends as unicast) | **none** — body's `groupId` is the **assignment value**, not a filter | `RESP_ACK` | Always acts. |
| `OPC_STATUS` (0x03) | accept broadcast or unicast | `groupMatch` applied | `RESP_SPECIFIC` (STATUS_REPLY) | Reply unicast back to sender. |
| `OPC_PRESET` (0x04) | accept broadcast or unicast | `groupMatch` + offset-mode gate | `RESP_NONE` | The offset-mode gate is asymmetric — see [OPC_PRESET / OPC_CONTROL gate](#opc-preset-control-offset-mode-gate). |
| `OPC_CONFIG` (0x05) | **broadcast actively rejected** in Stage 1 (firmware drops `recv3 == FF FF FF`) | none | `RESP_ACK` | See [Designed-in special cases](#designed-in-special-cases). |
| `OPC_SYNC` (0x06) | accept broadcast or unicast | none — no `groupId` byte in body | `RESP_NONE` | Global timebase + arm-on-sync flag. |
| `OPC_STREAM` (0x07) | accept broadcast or unicast | none | `RESP_NONE` (streaming) | Stream RX-window sized by `isBroadcast3(recv3)` alone — see [Edge cases](#edge-cases-to-revisit). |
| `OPC_CONTROL` (0x08) | accept broadcast or unicast | `groupMatch` + offset-mode gate | `RESP_NONE` | Same gate as `OPC_PRESET`. |
| `OPC_OFFSET` (0x09) | accept broadcast or unicast | `groupMatch` applied | `RESP_NONE` | Stored as `pendingChange`; materialises on next CONTROL/PRESET when the gate aligns. |

## Combined accept matrix (`PRESET` / `CONTROL` / `OFFSET`) { #combined-accept-matrix }

These three opcodes are the workhorse path for scene playback.
Their accept logic is the same:

| `recv3` | body `groupId` | Outcome |
|---|---|---|
| `FF FF FF` | `255` | All devices act. **True broadcast.** |
| `FF FF FF` | `N ∈ 1..254` | Devices with `current.groupId == N` act; others parse + drop. **Group-scoped broadcast.** |
| `FF FF FF` | `0` | Devices in group 0 (Unconfigured) act. *Used by `OPC_DEVICES` discovery — see exceptions.* |
| device MAC | matching `N` | The targeted device acts. **Standard unicast.** |
| device MAC | `255` | The targeted device acts regardless of its current group. **Single-device, group-bypass.** Reserved — used only when bypass is genuinely needed. |
| device MAC | non-matching `N` | The targeted device **drops** — even though Stage 1 matched. *Surfaces a Host-side ↔ device-side group divergence — by design (see [Single-device pinned rule](#single-device-pinned-rule)).* |

## OPC_PRESET / OPC_CONTROL offset-mode gate { #opc-preset-control-offset-mode-gate }

For `OPC_PRESET` and `OPC_CONTROL` the firmware applies a second
gate after `groupMatch`: the `RACELINK_FLAG_OFFSET_MODE` bit
(`F`) in the packet flags must equal whether the device
currently has an active offset configuration (`E`).

| Packet `F` | Device `E` | Outcome |
|---:|---:|---|
| 0 | 0 | **ACCEPT** — normal immediate apply. |
| 1 | 1 | **ACCEPT** — apply via the stored offset formula. |
| 0 | 1 | **DROP** — device is offset-locked; immediate request not allowed. |
| 1 | 0 | **DROP** — device has no offset; offset-mode request not allowed. |

The gate is the firmware mechanism behind Strategy A
("broadcast formula") in
[concepts/opcodes.md](../concepts/opcodes.md): one broadcast
`OPC_OFFSET` configures every offset-eligible device, and the
follow-up broadcast `OPC_CONTROL(F=1)` is then accepted only by
those same devices because their `E` bit was raised by the
formula install. Devices with no offset see `F=1, E=0` and drop.

`OPC_OFFSET` itself does **not** apply the offset-mode gate —
the offset configuration arrives as `pendingChange` and is
allowed to land regardless of the current `E`.

## Designed-in special cases

Three opcodes deviate from the "Stage 1 + groupMatch" pattern.
They are **intentional**, not bugs.

### OPC_CONFIG — broadcast forbidden

Different device classes (WLED, startblock, future capabilities)
can re-interpret the same config-register address according to
their capability. A global broadcast would collide. The firmware
therefore drops `OPC_CONFIG` packets with `recv3 == FF FF FF`
before any handler runs.

The Host is required to send `OPC_CONFIG` only to devices whose
capability is known to handle the targeted register. In
practice this means **always passing an explicit `recv3`** for
config writes — the unicast path is the only valid one.

### OPC_DEVICES — discovery defaults to `groupId = 0`

After boot, every device sits in group 0 (Unconfigured). The
original purpose of `OPC_DEVICES` discovery is to find those
freshly-booted devices so the Host can assign them a group via
`OPC_SET_GROUP`. With the body filter applying `groupMatch`,
the broadcast `groupId=0` reaches exactly the devices that
haven't been claimed yet.

Modern devices also send `IDENTIFY_REPLY` proactively on boot,
so the everyday flow is "device powers on → Host receives the
unsolicited reply → Host issues `OPC_SET_GROUP` from its stored
mapping". Discovery on a *non-zero* group — to re-poll a known
fleet — is a deliberate operator choice exposed via the
discovery panel's group selector, not a default. See
[Roadmap](#roadmap) for the planned group-agnostic
re-identification flow.

### Single-device PRESET / CONTROL / OFFSET pinned rule { #single-device-pinned-rule }

When the Host targets a single device with `OPC_PRESET`,
`OPC_CONTROL`, or `OPC_OFFSET`, it emits:

```
recv3   = device's last-3-MAC
groupId = device.groupId  (from the Host's repository)
```

Note that `groupId = 255` is **not** used as a fallback. This is
deliberate. The Host is the absolute master of the system and
its repository is the source of truth for every device's
`groupId`. Emitting the *expected* `groupId` rather than the
bypass value `255` makes drift between the Host's view and the
device's actual state immediately observable: a misconfigured
device drops the packet (and the missing effect is visible in
the field). A `255`-bypass would mask the inconsistency and let
the wrong picture persist.

`groupId = 255` for unicast (the "single-device, group-bypass"
row in the [combined accept matrix](#combined-accept-matrix))
is reserved for cases where the bypass is genuinely intended —
typically diagnostic or recovery flows.

## Gateway role

Source: `RaceLink_Gateway/src/main.cpp` and
`racelink_transport_core.h`.

* **Inbound (Host → LoRa).** Transparent forwarder. `recv3` and
  `groupId` are passed through verbatim for every opcode. No
  mutation, no per-opcode special cases on either field.
* **Outbound (LoRa → Host).** N2M replies are filtered by
  `recv3` only — forward if `recv3 == FF FF FF` or
  `recv3 == gateway's last-3-MAC`, drop otherwise. `groupId` is
  not inspected.
* **Originated by the Gateway.** `OPC_SYNC` autosync only,
  every 30 s of idle, with `recv3 = FF FF FF` and `flags = 0`
  (the autosync must never fire armed effects ahead of a
  deliberate sync — keeping `flags = 0` is the invariant).

The Gateway is therefore a transparent L2 forwarder for
addressing decisions; all rule enforcement lives in the device
firmware (Stage 1 + Stage 2) and on the Host (emission
discipline).

## Edge cases to revisit

* **OPC_STREAM RX-window with `recv3 = specific + groupId =
  255`.** The Gateway sizes its RX window from `isBroadcast3
  (recv3)` alone (broadcast: 2 s window, multiple replies;
  unicast: 1 s window, single reply). A unicast stream that
  sets `groupId = 255` (single device, group-bypass) would size
  as unicast even though the operator semantically targeted the
  device's all-group state. Not exercised today; flag if/when
  streams are exercised this way.

## Forbidden combinations

| Combination | Failure mode |
|---|---|
| `OPC_CONFIG` with `recv3 = FF FF FF` | Stage 1 reject inside the firmware's `OPC_CONFIG` handler — packet is silently dropped by every device. Always send `OPC_CONFIG` unicast. |
| `OPC_PRESET` / `OPC_CONTROL` with `F = 1` to a device whose `E = 0` | Drops at the offset-mode gate. Either: (a) install an `OPC_OFFSET` first to raise `E`, or (b) clear `F` for an immediate apply. |
| `OPC_PRESET` / `OPC_CONTROL` with `F = 0` to a device whose `E = 1` | Drops at the offset-mode gate. Either: (a) clear the device's offset with `OPC_OFFSET(NONE, …)` first, or (b) set `F = 1` to apply via the stored offset. |
| Unicast `recv3` with non-matching `groupId` | Drops at `groupMatch`. Surfaces drift between the Host repo and the device — fix the drift; do not "patch" by switching to `groupId = 255` (see [Single-device pinned rule](#single-device-pinned-rule)). |
| Any `recv3` neither broadcast nor the device's last-3-MAC | Stage 1 reject — silent pre-dispatcher drop. |

## Roadmap

Two enhancements are planned but **not implemented today**. They
are recorded here so contributors hitting the rules above know
the planned evolution.

* **Capability-agnostic broadcast addressing.** Add a
  capability-filter byte to the wire header (or repurpose
  reserved bits) so a Host can emit `recv3 = FF FF FF`,
  `groupId = 255`, `cap = WLED` and have only WLED-capable
  devices accept. This unlocks honest capability-aware UI
  labels ("All WLED Nodes", "All Startblock Nodes") and
  eliminates per-device fan-out for cap-scoped commands.
  Covers `OPC_PRESET`, `OPC_CONTROL`, `OPC_OFFSET`, and —
  once register namespaces are cap-scoped — potentially
  `OPC_CONFIG`.
* **Group-agnostic re-identification.** Discovery currently
  reaches devices in `groupId = 0` (Unconfigured). To
  forcibly re-identify a device whose stored `groupId` may
  have drifted from the Host's repository, without sending one
  `OPC_DEVICES` per group, add a discovery mode that bypasses
  the Stage-2 `groupMatch`. Possible mechanisms: a dedicated
  bypass opcode, a flag bit in `OPC_DEVICES`, or the
  capability-byte from the previous bullet. Decision deferred
  to the implementation PR.

## Cross-references

* [Wire protocol reference](wire-protocol.md) — header layout,
  USB framing, opcode constants.
* [Opcodes (concepts)](../concepts/opcodes.md) — Strategy A / B
  / C for `OPC_OFFSET`, `OPC_CONTROL` semantics.
* [Scene format](scene-format.md) — how scene-action `target`
  fields map onto the rules above.
* [Glossary](../glossary.md) — short definitions for "All
  Devices (Broadcast)", `groupId = 255`, etc.
