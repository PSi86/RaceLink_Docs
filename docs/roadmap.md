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

## Capability function visibility taxonomy

**Status.** Planned. Identified 2026-05-09 (deferred from the
UI-cleanup iteration that day) and re-prioritised when the
WLED-Preset-removal item below was scheduled for the next
release. The visibility mechanism is the preferred
implementation path for that removal and for any future
"capability function ships in the wire layer but should not
appear in every UI surface" use case.

**Motivation.**

Today the `RL_SPECIALS[<cap>]["functions"]` schema in
`racelink/domain/specials.py` is consumed uniformly: the
Device Options dialog renders **every** entry as an
``Action`` row in the cap's tab; the Scene Editor's action
picker renders a **separately maintained** hardcoded list of
``KIND_*`` constants. There is no single source of truth that
expresses *where* a capability function should be visible,
and no way to register a function that is meant to be reached
only by other code paths (e.g. a scene-runner step that
consumes it via the ``comm`` method, but which should not
appear as an operator-clickable button).

Two concrete problems that the lack of this mechanism creates:

1. **WLED Preset is exposed in the dialog despite being
   problematic** — the removal item below has been blocked
   on "we'd like to keep `sendWledPreset` reachable from
   scenes but not from the dialog". Today the only way to
   hide it from the dialog is to delete the schema entry
   entirely, which also breaks any service-layer caller.
2. **The Scene Editor's action picker drifts from the
   capability schema** — adding a new device cap function
   today requires touching `RL_SPECIALS` (for the dialog) and
   the editor's `SceneActionKind` list (for the scene
   picker). The two surfaces are kept in sync by hand.

**Proposed change.**

Add an optional `visibility` field per function entry:

```python
{
    "key": "wled_preset",
    "label": "WLED Preset",
    "comm": "sendWledPreset",
    # ...
    "visibility": ["scene-editor"],   # ← new
}
```

Field semantics:

* **List of UI surface tokens.** A function appears on a
  surface only if the surface's token is in the list.
* **Omitted = visible everywhere** (backwards-compatible
  default; existing entries don't need touching).
* **Empty list `[]`** = "internal only", never rendered in any
  UI surface; reachable only by code-path callers.
* **Initial token vocabulary**:
  - ``"device-options-dialog"`` — the Specials dialog action
    row (`SpecialsDialog.vue`).
  - ``"scene-editor"`` — the Scene Editor action picker.
* New tokens are added when a new UI surface starts consuming
  the capability schema. Unknown tokens are ignored by
  consumers (forwards-compatible additions).

**Scope.**

* `racelink/domain/specials.py` — add `visibility` field type
  + validation in the schema constructor; default `None` →
  treated as "everywhere".
* `racelink/services/specials_service.py` — `get_serialized_config()`
  passes the field through unchanged.
* `frontend/src/api/types.ts` — extend `SpecialFunctionMeta`
  with `visibility?: string[]`.
* `frontend/src/components/modals/SpecialsDialog.vue` — filter
  the rendered action rows: include only entries whose
  ``visibility`` is omitted OR contains ``"device-options-dialog"``.
* `frontend/src/components/scenes/...` — where the editor's
  action-kind picker lives, apply the same filter against the
  ``"scene-editor"`` token. (Long-term: replace the hardcoded
  `SceneActionKind` constant list with the schema-derived
  list. That's a bigger refactor; this entry's first delivery
  only adds the filter.)
* `RaceLink_Docs/docs/RaceLink_Host/architecture.md` — document
  the visibility contract under the existing "Specials schema"
  section. Token vocabulary lives next to the schema docs so
  contributors discover it when adding a new function.

**Unlocks.**

* WLED-Preset-removal-from-dialog (next entry) lands as a
  one-line schema change instead of a multi-file deletion.
* Future device caps (e.g. a debug-only "Reboot at next
  packet" function) can ship without polluting every UI.
* A future "expose capability functions to RotorHazard
  effect-mapping" feature gets a clean way to mark which ones
  RH should pick up, distinct from operator-facing UI.
* The "scene editor uses a hardcoded list" code-smell becomes
  fixable in a follow-up that's strictly smaller than today
  (the visibility filter is the prerequisite).

**Risks.**

* Mis-tagging during the migration: silently making a function
  invisible everywhere by setting `"visibility": []` when
  ``["scene-editor"]`` was meant. Mitigation: add a unit test
  that asserts at least one function exists for each surface
  token after the schema is loaded (regression guard).
* Adding a third UI surface later means touching every filter
  site to add the token. Mitigation: extract a single helper
  ``isVisibleOn(fn, "scene-editor")`` so the surface-token
  comparison is centralised.

## Remove "WLED Preset" action from the Device Options dialog

**Status.** Planned. Triggered 2026-05-08 after the iteration-8
RL-preset tracking fix exposed the long-standing operator UX
problem.

**Note (2026-05-09).** The preferred implementation path is
now the **Capability function visibility taxonomy** above
rather than a wholesale deletion: tag `wled_preset` with
`visibility: ["scene-editor"]` so it disappears from the
dialog but stays available to scenes (and to any future
caller of `sendWledPreset` / `send_device_preset`). This
turns this entry from a deletion into a one-field schema
edit, and lands the visibility mechanism as a
forwards-compatible side-effect.

**Why this is on the list.**

The Device Options dialog's WLED-tab `functions` block currently
exposes two preset paths side-by-side:

* **WLED Preset** — applies a numeric WLED-preset slot
  (`OPC_PRESET`, host's `send_wled_preset` →
  `send_device_preset`). The preset content is whatever the
  operator saved into the node's `presets.json` via WLED's own
  web UI.
* **RaceLink Preset** — applies a host-side RL preset
  (`OPC_CONTROL` with the saved 14-field parameter snapshot,
  host's `send_rl_preset_by_id`).

Two problems:

1. **Segment reconfiguration.** A WLED preset can carry segment
   geometry that overrides whatever the host's "Segment 0/1
   Geometry" rows or the "Reset to RaceLink defaults" action
   established. Operators see segments silently rearrange after
   applying a WLED preset, contradicting the host's stated
   intent. The override layer (`OPC_CONFIG` 0x06/0x07) only
   enforces geometry on boot via `applyRaceLinkDefaults` — a
   live `OPC_PRESET` bypasses it.
2. **`presetId` overload.** Both actions seed their dropdown
   from `dev.presetId`. The host writes the WLED-preset slot
   number from `send_device_preset` and the RL-preset stable id
   from `send_rl_preset_by_id` into the same field. Whichever
   was applied last wins; the *other* dropdown then renders
   empty (RL-preset id rarely matches a WLED-preset slot and
   vice versa). The iteration-8 fix made the RL-preset dropdown
   correct at the cost of leaving the WLED-preset dropdown
   empty after every RL apply — operator-visible churn.

**Proposed change.** Tag the `wled_preset` entry with
`visibility: ["scene-editor"]` (using the new mechanism in the
preceding entry). Result: the function disappears from the
Device Options dialog while staying registered in
`RL_SPECIALS["WLED"]["functions"]` so the Scene Editor and
any future programmatic caller of `sendWledPreset` /
`send_device_preset` / `send_group_preset` can still reach it.
RL Presets become the single preset-style surface in the
dialog.

**Scope.**

* Schema: one-field edit in `racelink/domain/specials.py` —
  `"visibility": ["scene-editor"]` on the `wled_preset` entry.
  Depends on the visibility-taxonomy entry above shipping
  first (or in the same release).
* Frontend: `SpecialsDialog.vue` already filters by
  `visibility` (per the new mechanism); no further change at
  the dialog. The `SpecialsActionRow` row count for the WLED
  tab drops from 3 to 2 automatically.
* Backend: no service-layer change. `dev.presetId` becomes
  unambiguously "last applied RL preset id" because the only
  caller that writes WLED-preset slot numbers into it is the
  dialog row — the scene-editor path stamps an RL-preset id
  via `send_rl_preset_by_id` regardless.
* Migration note for `RaceLink_Docs/RaceLink_WLED/operator-setup.md`:
  operators who relied on WLED presets transcribe the preset's
  effect parameters into a new RL preset via the RL Preset
  editor. Document the parameter mapping (mode, speed, intensity,
  custom1–3, palette, color1–3) — every WLED-preset field has an
  RL-preset equivalent.

**Unlocks.**

* The "Effect" column and the RL-preset dropdown stop
  contradicting each other.
* The "Reset to RaceLink defaults" + segment-override flow
  becomes authoritative — no other dialog action can silently
  rearrange segments behind the operator's back.

## Lean down the headless scene-execution path

**Status.** Planned. Identified 2026-05-09 during the WTIME
diagnostic session; quantified but not yet implemented because
the gain is sub-millisecond per scene.

**Motivation.** During a race event, scenes are triggered
**without an open browser tab** — `controller.runScene(key)` is
invoked directly by the RotorHazard plugin and `progress_cb`
is `None`. The current Host code runs a small amount of work
on every scene execution that only matters when at least one
SSE client is connected. The work is not wrong, just wasted on
the headless production path.

Two concrete spots:

1. **Per-action payload dict allocation in
   [`scene_runner_service.py::run`](https://github.com/PSi86/RaceLink_Host/blob/main/racelink/services/scene_runner_service.py).**
   `_emit_progress(progress_cb, {…})` builds a 4–6 key dict
   *before* the helper checks `if progress_cb is None: return`.
   With `progress_cb=None` (headless path) the dict is allocated
   and discarded twice per action (start + terminal events).
2. **Master-state snapshot copy in
   [`web/sse.py::MasterState.set`](https://github.com/PSi86/RaceLink_Host/blob/main/racelink/web/sse.py).**
   Every `EV_TX_DONE` / `EV_STATE_CHANGED` / reply event triggers
   `master.set(last_event=…)` → `snapshot()` (`dict(self._state)`,
   6–7 fields). The subsequent `_broadcast` already has an
   `if not clients_snapshot: return` early-return, but the
   snapshot dict is allocated *before* that check.

**Proposed change.**

* Helper-extract the runner's `_emit_progress` to construct the
  payload only when `progress_cb is not None`. Two callsites,
  one helper.
* In `MasterState.set`, gate `self._broadcast(...)` on
  `if self._clients:` so the snapshot allocation only runs when
  at least one SSE client is connected.

**Scope.** Host-only, no protocol or firmware change.

* `racelink/services/scene_runner_service.py` — refactor the
  two `_emit_progress(progress_cb, {…})` calls.
* `racelink/web/sse.py` — gate the snapshot in `MasterState.set`.
* `racelink/services/scene_cost_estimator.py` — once the
  measurement above shifts the per-packet wire overhead by ≥
  3 ms, recalibrate `WIRE_OVERHEAD_MS_PER_PACKET` from `12.0`
  toward the new mean (2026-05-09 measurement: ~14 ms; below
  the 3 ms recalibration threshold so it stays at 12.0 for now).

**Unlocks.**

* Sub-millisecond reduction in per-scene wall-clock for the
  headless production path. **Not operator-visible** in any
  practical race scenario — the entry exists to keep the
  micro-optimisation discoverable so it isn't reinvented from
  scratch later.
* Cleaner separation between "what only the WebUI consumer
  cares about" and "what the wire path needs unconditionally".

**Reference.** Per-packet wall-clock decomposition and the
2026-05-09 baseline measurement live in
[Wire timing](reference/wire-timing.md). Open before re-measuring
or before deciding whether to recalibrate
`WIRE_OVERHEAD_MS_PER_PACKET`.

## Asynchronous / pipelined gateway TX

**Status.** Planned. Identified 2026-05-09 alongside the
headless-path lean-down; the dominant lever for *measurable*
per-packet wall-clock savings.

**Motivation.** Per-packet wire overhead today is ~14 ms above
pure LoRa airtime (see [Wire timing](reference/wire-timing.md)).
Decomposed:

* ~2 ms USB-CDC submission Host → Gateway
* ~1 ms host-side RX-reader wakeup latency
* **~11 ms Gateway-firmware:** `radio->standby()` + radio
  mode-switch + RadioLib `radio->transmit()` setup + TX_DONE
  interrupt + USB submission Gateway → Host

The 11 ms gateway-side block is dominated by RadioLib's
**blocking** `transmit()` call in
[`scheduleSend / service`](https://github.com/PSi86/RaceLink_Gateway/blob/main/src/racelink_transport_core.h)
(line ~648 at the time of writing): the call returns only after
the LoRa TXDONE IRQ fires. The single-slot `txPending` design
prevents pipelining — the host can have at most one frame in
flight on the wire even though the gateway could already be
preparing the next frame's modem state during the previous
frame's airtime.

**Proposed change.** Replace the blocking transmit with
RadioLib's non-blocking `startTransmit() / DIO1 IRQ →
finishTransmit()` pattern, and grow the TX scheduler to a small
queue (e.g. 4 slots). The host can then submit the next frame
before the previous one's TXDONE arrives; the gateway's
mode-switch and modem-setup overlap with the prior frame's
tail.

This was already flagged as future work in the comment block at
the top of `scheduleSend` ("Buffered burst tolerance: a small TX
queue (e.g. 4 entries) inside `scheduleSend` would let the
gateway absorb bursts during the LBT 50–300 ms backoff window
without surfacing TX_REJECTED to the host").

**Scope.**

* `RaceLink_Gateway/src/racelink_transport_core.h` — replace
  `radio->transmit(...)` with the start/finish pair, wire DIO1
  IRQ handler to fulfil per-slot completions; grow the
  `txBuf`/`txLen` single-slot to a small ring buffer (size and
  ordering to be decided alongside the LBT backoff interaction).
* `RaceLink_Gateway/src/main.cpp` — adjust `try_schedule_or_nack`
  rejection logic: `TX_REJECT_TXPENDING` only fires when the
  ring is full, not on every back-to-back send.
* Host-side: `_send_m2n` already uses a `Condition.wait_for`
  per outcome slot — grows naturally to multiple in-flight
  outcomes if `_pending_send_outcome` becomes a list keyed by
  some monotone tx-id. **Not** a backwards-incompatible wire
  change; the gateway emits the same `EV_TX_DONE` per frame.

**Unlocks.**

* Per-packet wall-clock drops from ~airtime + 14 ms to
  ~airtime + 5–7 ms (recovers the 7–9 ms gateway housekeeping
  that today serialises with the next frame's submission).
* Multi-packet scenes (offset_group fan-out, scene runs with
  many small actions) gain proportionally more — a 5-packet
  action saves 35–45 ms scene-wall-clock.
* Necessary stepping-stone for any future "true parallel
  fan-out per device-group" feature.

**Risks / open questions.**

* LBT (Listen Before Talk) interaction: the firmware currently
  runs `lbtEnable=false` on the master gateway. If LBT is ever
  enabled, the queue+pipeline interacts with the per-frame
  CAD scan in ways that need careful design — Mexican standoff
  between "next frame is queued" and "current frame is doing
  CAD backoff".
* Order guarantees: the host's protocol assumes a strict TX
  order matching submission order. The ring must preserve FIFO
  even if RadioLib's IRQ fires out of order (it shouldn't —
  TXDONE is for one frame at a time — but the design must not
  rely on that being absolute).

**Reference.** Per-packet wall-clock decomposition with
attribution lives in [Wire timing](reference/wire-timing.md).
