# RaceLink Roadmap

Planned but not-yet-implemented features that the documentation
already cross-references. Each entry is a stable anchor that
contributors and operators can link to when describing why a
current rule exists or where the system is heading.

Entries are added when an architectural rule is locked in but
its implementation is deferred. Removing an entry implies the
feature has shipped and the surrounding docs have caught up.

## Capability-agnostic broadcast addressing

**Status.** Planned. No implementation date.

**Motivation.** RaceLink today filters broadcast packets only
by `groupId` (see [Broadcast
Ruleset](reference/broadcast-ruleset.md)). A
`recv3 = FF FF FF, groupId = 255` packet is accepted by every
device regardless of its capability — there is no way to
broadcast to "WLED nodes only" or "Startblock nodes only".

The Host's UI currently sidesteps this by labelling the
broadcast option "All Devices (Broadcast)" — capability-neutral
and honest. The RotorHazard plugin offered an "All WLED Nodes"
label, which was technically misleading on a fleet that mixes
device classes.

**Proposed change.** Add a capability-filter byte to the wire
header (or repurpose reserved bits in an existing field; the
exact placement is a wire-design decision) so the Host can
emit:

```
recv3   = FF FF FF
groupId = 255
cap     = WLED          ← new field
```

…and have only WLED-capable devices accept the packet. Other
device classes pass Stage 1 (recv3 broadcast) but reject in
Stage 2 (capability mismatch).

**Scope.** Touches:

* `OPC_PRESET`, `OPC_CONTROL`, `OPC_OFFSET` — the workhorse
  scene-playback opcodes.
* Possibly `OPC_CONFIG` once register namespaces are
  cap-scoped (today the firmware drops broadcast `OPC_CONFIG`
  outright — see the Designed-in special cases section of the
  Broadcast Ruleset).
* Wire spec (`racelink_proto.h`), Host emission, Gateway
  forwarder (already transparent — likely no change), WLED
  firmware acceptance, Host UI labels.

**Unlocks.**

* Honest capability-aware UI labels ("All WLED Nodes",
  "All Startblock Nodes") that match the wire reality.
* Single-packet broadcasts for cap-scoped commands that today
  must fan out per-device or per-group.

## Group-agnostic re-identification

**Status.** Planned. No implementation date.

**Motivation.** `OPC_DEVICES` discovery defaults to
`groupId = 0` and reaches devices in the Unconfigured group
(see the Designed-in special cases section of the [Broadcast
Ruleset](reference/broadcast-ruleset.md)). To re-poll a known
fleet on a non-zero group the operator can pick a specific
group from the Discovery panel — a choice plumbed through to
the wire.

That works for the case "the Host knows which group the device
is in". It does not solve "the device's stored `groupId` has
drifted from the Host's repository, and the Host needs to find
out". Today's only path is one `OPC_DEVICES` per known group
(254 packets in the worst case) or a manual operator
intervention.

**Proposed change.** Add a discovery mode that bypasses the
Stage-2 `groupMatch`. Three candidate mechanisms:

* A **dedicated bypass opcode** parallel to `OPC_DEVICES`.
* A **flag bit** in `OPC_DEVICES` ("ignore groupId, reply
  anyway").
* The **capability byte** from
  [Capability-agnostic broadcast
  addressing](#capability-agnostic-broadcast-addressing) — a
  zero-cap value would mean "any capability, any group".

Pick at implementation time.

**Scope.** Touches `OPC_DEVICES` (or a new opcode) on the wire,
firmware acceptance logic, Host discovery service, and the
Discovery panel UI.

**Unlocks.**

* Single-packet "re-identify the whole fleet regardless of
  group state".
* A safer recovery path when device repository drift is
  suspected.
