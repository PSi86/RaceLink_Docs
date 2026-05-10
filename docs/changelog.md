# Changelog

A consolidated timeline of releases across the four RaceLink
repositories. Currently a stub — entries should be added as releases
ship. Each entry should follow the template at the bottom of this
file.

> **Source of truth.** Each repository maintains its own GitHub
> releases page; this changelog is a curated cross-repo summary.
> When the cross-repo summary and a repository's release notes
> disagree, the repository's release notes win.

## 2026-05-07 — RaceLink_WLED: V3↔V4 sync investigation retrospective

A two-day investigation into V3 (ESP32-S2) ↔ V4 (ESP32-S3) phase-sync
drift on sharp-edged effects (Strobe), plus a related "weak Breathe"
symptom on internally-triggered pair-confirmation effects. **Several
speculative code-level patches were tried; none demonstrably solved
the V3↔V4 drift.** The weak-Breathe symptom was identified as
operator-side state divergence (segment geometry on devices was
historically normalized by an auto-applied Boot Preset; removing the
preset exposed the underlying divergence) — a firmware fix is not
needed.

The full retrospective with per-change rollback pointers is at
[`RaceLink_WLED/dev-session-2026-05-sync-investigation.md`](RaceLink_WLED/dev-session-2026-05-sync-investigation.md).

**Speculative patches in the WLED working tree but NOT synced to
`RaceLink_WLED`:**

* ISR-time `millis()` capture in the DIO1 trampoline + propagation as
  `rxAtMs` through the callback chain to `handleSync`. Hypothesis:
  loop-polling latency variance was injecting jitter into the
  soft-sync filter. Hypothesis was wrong — `lastSyncTbErrMs`
  distribution unchanged on affected devices.
* `strip.trigger()` after timebase update in `handleSync` to force
  render-phase realignment to SYNC reception. No visible improvement.
* `buildEffectFullDefaults()` + `applySegmentReplace()` deterministic
  refactor of `showPairConfirmedEffect()` and `applyCycleColor()` —
  every segment field written explicitly to eliminate state leakage
  from prior effects. Did not fix weak-Breathe (operator-side cause).
* `seg.startTransition(0)` cleanup in `applySegmentReplace()` to
  prevent stuck `_oldSegment` blending. No improvement.

**Open hypotheses for future investigation** (if V3↔V4 drift resurfaces):
NeoPixelBus driver / pipeline-latency difference between S2 and S3,
segment-length-dependent rendering anomaly on long-but-mostly-unconnected
strips, master-side TX jitter. Recommended next step: GPIO pulse at
DIO1 ISR + at LED data line edge, two-channel scope between V3 and V4.

## 2026-05-06 — RaceLink_WLED: async ePaper + runtime-configurable pins

Two RaceLink_WLED firmware changes that improve operator ergonomics
without changing the wire protocol or any cross-component contract.

* **Async ePaper rendering.** The GxEPD2 e-paper driver is now driven
  from a dedicated FreeRTOS worker task. Both `epaperInit()` (boot
  screen, ~1 s) and every refresh (~1 s per cycle on the GDEY037T03
  panel) used to block WLED's main loop, freezing LED effects, the
  web UI and LoRa servicing for the duration. The async refactor
  pushes all GxEPD2 calls off the main loop:
  - On ESP32-S3 (dual-core profiles) the worker is pinned to core 0
    so rendering happens fully in parallel with WLED's core-1 loop.
  - On ESP32-S2 (single-core profile, `v3_s2_llcc68_epaper`) the
    worker time-slices with the Arduino loop at the same priority;
    the GxEPD2 BUSY-pin wait already calls `yield()` internally, so
    the loop runs during the dominant ~800 ms panel-busy phase
    instead of being frozen.
  - Public `racelink_epaper.h` API surface (`epaperInit`,
    `setDisplayLayout`, `setPilotSlotData`, `service_epaper`)
    keeps its names; the only signature change is on `epaperInit()`
    (see below).
* **Runtime-configurable pins.** The radio control pins (SCK, MISO,
  MOSI, NSS, DIO1, BUSY, RST) and — on builds compiled with
  `-D RACELINK_EPAPER` — the ePaper bus and control pins
  (SCK, MISO, MOSI, CS, DC, RST, BUSY) can now be overridden via the
  WLED **Config → Usermod Settings → RaceLink** UI. The previous
  `-D RACELINK_PIN_*` and `-D RACELINK_EPAPER_*` build flags become
  *defaults* per build profile rather than hard-coded values, so
  first-boot behavior on every shipping target is unchanged. A
  saved pin change triggers an automatic reboot to re-init SPI on
  the new pins. Pins are now allocated through WLED's PinManager,
  so a conflict with an LED-bus pin fails loudly at `radioInit()`
  time instead of silently breaking SPI.
* **Radio chip family stays compile-time.** SX1262 vs LLCC68 (and
  any future chip choice) is still selected at build time via
  `-D RACELINK_SX1262` / `-D RACELINK_LLCC68` in the relevant build
  profile. Rationale: the underlying RadioLib chip-family APIs
  (SX126x vs SX127x) are not interchangeable at the abstract base,
  and the only intra-family difference between SX1262 and LLCC68 is
  PHY parameter range — which is also intentionally compile-time to
  keep a fleet's PHY settings homogeneous. See the new
  [Radio modules developer guide](RaceLink_WLED/radio-modules.md)
  for the chip-family hierarchy and the path to extend support.

**What breaks.** The `epaperInit()` C++ signature changed from
no-argument to seven pin arguments. Only one in-tree caller exists
(in `racelink_wled.cpp`); no external callers. Operators flashing
the new firmware on top of an existing install keep their
`cfg.json` — pin values fall back to the build-time defaults via
`getJsonValue(...)` when a `pins` / `epaper_pins` block is absent,
matching the previous hard-coded behavior 1:1.

**Documentation.** Two new pages:

* [RaceLink_WLED → Pin configuration](RaceLink_WLED/pin-config.md) —
  operator guide: where the fields appear, default tables per build
  profile, reboot semantics, PinManager conflict troubleshooting.
* [RaceLink_WLED → Radio modules](RaceLink_WLED/radio-modules.md) —
  developer guide: RadioLib class hierarchy, what differs between
  SX126x and SX127x, what an SX127x or SX1268 extension would look
  like.

## 2026-05-04 — Preset terminology cleanup (BREAKING)

Disambiguates the long-standing "WLED Control" vs RL-preset confusion in
the source code. The wire protocol (`OPC_PRESET`, `OPC_CONTROL`) is
unchanged — this release renames host-side / WebUI surfaces only.

* **RaceLink_Host (Specials function)** — the `wled_control` Specials
  function (which was actually the RL-preset picker — operator picks a
  RaceLink-native preset id and the host emits `OPC_CONTROL` with the
  resolved snapshot) is renamed to `rl_preset`. Its operator-facing
  label changes from "WLED Control" to "RaceLink Preset". The classical
  WLED-preset picker (`wled_preset`, `OPC_PRESET`) is unchanged.
* **RaceLink_Host (scene action kind)** — the `wled_control` scene
  action kind (inline effect parameters, no preset id, emits
  `OPC_CONTROL`) is renamed to `rl_effect`. Its `vars` set now mirrors
  the 14-field RL-preset editor schema (`mode`, `speed`, `intensity`,
  `custom1..3`, `check1..3`, `palette`, `color1..3`, `brightness`)
  instead of the misleading `presetId`/`brightness` pair it carried
  before. `rl_preset` (host-side preset lookup) and `wled_preset`
  (classical) are unchanged.
* **RaceLink_Host (service method)** — `ControlService.send_wled_control`
  → `send_control` (matches the `OPC_CONTROL` opcode; not WLED-specific).
  `send_wled_preset` is unchanged (matches `OPC_PRESET`).
* **RaceLink_Host (controller method)** — `Controller.sendWledControl`
  → `sendRlPreset` (Specials/WebUI entry point for the renamed
  `rl_preset` function). The Specials `comm` field now reads
  `sendRlPreset`.
* **RaceLink_Host + RaceLink_RH_Plugin (state_scope tokens)** — the
  legacy union token `state_scope.PRESETS` (and its SSE topic
  `presets`) is removed. Callers must use the §1-introduced
  `state_scope.RL_PRESETS` / `state_scope.WLED_PRESETS` tokens
  instead. Topics fanned out: `rl_presets` and `wled_presets`.

**What breaks.** The on-disk shape of operator-saved scenes and
device-Specials configs changes:

* Saved scenes containing `{"kind": "wled_control"}` actions fail to
  load. Operators must re-save those scenes after the upgrade — the
  WebUI scene editor now offers `Apply RL Effect` (with the 14-field
  parameter form) in their place.
* Saved Specials configs referencing the `wled_control` function key
  fail to load. Operators must re-configure the affected device's
  Specials → WLED → RaceLink Preset entry.
* Any third-party SSE consumer subscribed to the `presets` topic must
  switch to `rl_presets` (RL preset CRUD) and/or `wled_presets`
  (WLED preset upload/select).
* Plugins or scripts that called `Controller.sendWledControl` /
  `ControlService.send_wled_control` must update their call sites to
  `sendRlPreset` / `send_control`. RotorHazard plugin shipping with
  this release is updated in lockstep.

**What does not break.** Wire-format opcodes, body layouts, and packet
identifiers (`OPC_PRESET`, `OPC_CONTROL`, etc.) are unchanged —
RaceLink_Gateway and RaceLink_WLED firmwares interoperate
byte-for-byte with both pre- and post-rename hosts.

## 2026-05-04 — Sidebar group rows: live counts + flash

* **RaceLink_Host (WebUI)** — the sidebar's group list now shows
  **`M / N`** per row — devices currently online out of total
  devices in the group — with a hover tooltip explaining what
  "online" means in this context (replied to the last status
  query or sent an unsolicited `IDENTIFY_REPLY` recently). The
  number is computed client-side from `state.devices`'s
  `online` flag in a single pass; falls back to the server-side
  `device_count` when the device list hasn't loaded yet on
  first render.
* **RaceLink_Host (WebUI)** — group rows now **flash** the same
  way the device-table rows do when any of their devices receives
  data. Driven by the per-group max `last_seen_ts` snapshot, with
  the same first-render-doesn't-flash semantics so a fresh page
  load doesn't strobe the sidebar. CSS `@keyframes rl-row-flash`
  is reused; the new rule is scoped to `.rl-groups li`.
* **Wire protocol** — unchanged (UI-only change).

Notes:

* `loadDevices()` now calls `renderGroups()` alongside
  `renderTable()` so the sidebar tracks SSE refreshes the same
  way the device table does — no extra API calls.

## 2026-05-03 — WebUI: Chrome SSE slot-pool stall fix

* **RaceLink_Host (WebUI)** — fixes a 20–50 s UI freeze that hit
  Chrome (and other Chromium-based browsers) after roughly 5 quick
  switches between `/racelink/` and `/racelink/scenes` via the
  in-page navigation links. The freeze also affected any parallel
  RotorHazard tab on the same origin. F5 reload was always fine;
  Firefox was never affected.
* **Root cause** — Chrome's link-click unload path closed the JS
  `EventSource` but parked the underlying TCP socket "half-finished"
  in its per-origin keep-alive pool (limit 6 sockets). After
  ~5 page switches the pool was saturated; the server's `gen()`
  loop had no quick way to notice that the peer was gone, since
  yielding 7-byte ping frames into a kernel send buffer never
  surfaced a `BrokenPipeError`.
* **Fix is three layers, all in `racelink/`:**
    * `racelink/static/racelink.js` — registers a `pagehide`
      listener that calls `_es.close()` synchronously, forcing the
      browser to release the SSE socket before unload.
    * `racelink/web/sse.py` — the SSE generator's idle ping cadence
      drops from 15 s to **2 s**, so kernel-level disconnects
      surface within seconds on the rare paths where the client
      did not close cleanly.
    * `racelink/web/sse.py` — the SSE response now sends
      `Connection: close` instead of `keep-alive`, signalling
      Chrome to release the socket slot deterministically once the
      stream ends.
* **Wire protocol** — unchanged.

Notes:

* Per-tab egress for the new ping cadence is ~7 B every 2 s
  (≈ 17 B/s for 5 open tabs) — negligible.
* `pagehide` is bfcache-aware: a tab restored from the back/forward
  cache opens a fresh `EventSource` on its normal page-load path.
* See [`reference/sse-channels.md`](reference/sse-channels.md)
  §"Connection lifecycle and Chrome HTTP/1.1 slot pool" for the
  full technical write-up.

## 2026-05-03 — Groups target picker: search dialog

* **RaceLink_Host (WebUI)** — the inline checkbox grid for the
  unified target picker's **Groups** mode is replaced by a
  compact summary chip + a modal selection dialog. The summary
  shows the selected groups in small text together with the
  total group count and total device count across the
  selection, so the operator can scan an action without
  opening the picker. **Edit groups…** opens a dialog with a
  search field (filters by name or id), a scrollable result
  list, and three batch buttons that act on the currently-
  visible hits: **Select all hits**, **Deselect all hits**,
  **Invert hits**. Designed for fleets with many groups where
  the previous flat checkbox row became unwieldy. The save-
  time broadcast-collapse hint moved into the dialog footer.
* **Wire protocol** — unchanged (UI-only change).

Notes:

* No on-disk migration required — scene format unchanged.
* No estimator / runner behaviour change; the dialog edits the
  same `target.kind = "groups"` shape the planner consumes.

## 2026-05-02 — Estimator ↔ runner structural sync

* **RaceLink_Host** — extracted a new pure module
  `racelink/services/dispatch_planner.py` that is now the
  **single source of truth** for "what packets would the runner
  emit for this action". Both the cost estimator and the scene
  runner consume `plan_action_dispatch(action, …) →
  ActionDispatchPlan{ops: List[WireOp], …}`; the runner
  iterates `plan.ops` and dispatches each via a small
  `_dispatch_op` adapter, the estimator iterates the same plan
  and sums `body_bytes` per op. Per-kind logic that used to
  live in two parallel implementations
  (`_resolve_target` / `_resolve_offset_group_child_target` /
  `_send_with_fanout` / `_merge_flags_into_params` /
  `_lookup_rl_preset` / `_dispatch_offset_group_child` on the
  runner; `_target_packet_multiplier` /
  `_estimate_offset_group_cost` /
  `_materialize_rl_preset_params` /
  `_estimate_control_body_len` on the estimator) is now in one
  place. New parity test suite
  (`tests/test_dispatch_parity.py`) runs every action shape
  through (planner, estimator, runner-with-recording-stubs)
  and asserts identical packet counts + per-op senders + per-op
  addressing — any future drift is caught at CI time.
* **RaceLink_Host** — bug fix: the API's
  `_known_group_ids_from_ctx()` had a stray `.controller`
  indirection that silently returned `[]`, closing the
  optimizer's Strategy-C gate and making the cost badge
  under-report by reaching for Strategy B (per-group EXPLICIT)
  where the runtime actually emitted Strategy C (broadcast
  formula + sparse NONE overrides). Reproducer scene from the
  bug report — 7-of-10 sparse linear `offset_group` with one
  broadcast child — pre-fix reported 8 packets / 121 B;
  post-fix correctly reports 5 packets matching the wire.
* **Wire protocol** — unchanged. `WireOp` was extended with
  optional `sender` and `detail` fields (additive, default-
  valued, back-compat).
* **Sync body sizing** — incidental fix surfaced by the
  unification: the estimator was sizing OPC_SYNC with
  `flags=0` (4-byte legacy form). The runner has always sent
  `trigger_armed=True` (5-byte form). The planner now sizes
  with `SYNC_FLAG_TRIGGER_ARMED` so the cost badge matches the
  wire.

Notes:

* No on-disk migration required — scene format unchanged.
* Operator-visible behaviour change: the cost badge in the
  scene editor is now accurate for sparse-subset offset_group
  containers. No other UI changes.

## 2026-05-01 — Broadcast / target-picker unification

* **Docs** — new
  [Broadcast Ruleset](reference/broadcast-ruleset.md) page (full
  per-opcode rules across Host / Gateway / WLED) and a
  [Roadmap](roadmap.md) page recording the two future-feature
  commitments (capability-agnostic broadcast addressing,
  group-agnostic re-identification). Glossary, scene-format,
  operator-guide, webui-guide, RH-plugin operator-setup,
  opcodes, and contributing all updated to the unified
  vocabulary.
* **RaceLink_Host** — unified `target` shape across every action:
  `{kind: "broadcast"} | {kind: "groups", value: [...]} |
  {kind: "device", value: "<MAC>"}`. The pre-unification
  shapes (`scope`, singular `group`, standalone `groups` field
  on `offset_group`) are migrated on read. Save-time
  canonicalisation collapses "every known group selected" →
  `broadcast` so the runtime / cost-estimator pair agrees on
  optimizer Strategy A. Scene-editor exposes the unified
  three-radio picker (Broadcast / Groups / Device) everywhere,
  replacing the previous mix of "Group/Device" radios + "All
  groups" checkbox + multi-select + "Scope (broadcast)" radio.
  Tests cover the migration shims and the
  `device.groupId`-pinned single-device emission rule.
* **Wire protocol** — `PROTO_VER_MAJOR/MINOR` unchanged; this
  is a host + UI change only.

Notes:

* No on-disk migration step required — old persisted scenes
  load as-is and are rewritten on next save.
* Operator-visible behaviour change: top-level effect actions
  now offer a **Broadcast** option that wasn't there before.
  Selecting every known group in the **Groups** picker shows a
  hint that it will save as Broadcast (so a future-added group
  is also hit) — see
  [operator-guide §"The target picker"](RaceLink_Host/operator-guide.md#the-target-picker-broadcast--groups--device).

## 2026-04-30 — Documentation consolidation

* New: consolidated `RaceLink_Docs` collection (this set).
* No code or wire-protocol changes.

## Unreleased / in progress

* (placeholder)

---

## Template for new entries

```markdown
## YYYY-MM-DD — <release name or component>

* **<Component>** vX.Y.Z — <one-line summary>
  * <bullet of what changed>
  * <bullet of what changed>
* **Wire protocol** — `PROTO_VER_MAJOR/MINOR = X.Y` (no change / +N)

Notes:

* <any cross-component coordination required>
* <any breaking change or migration step the operator must take>
```

## Useful queries

GitHub releases per repository (manual links):

* https://github.com/PSi86/RaceLink_Host/releases
* https://github.com/PSi86/RaceLink_Gateway/releases
* https://github.com/PSi86/RaceLink_WLED/releases
* https://github.com/PSi86/RaceLink_RH-plugin/releases

The wire-protocol version pair lives in `racelink_proto.h`:

```c
#define PROTO_VER_MAJOR 2
#define PROTO_VER_MINOR 0
```

A drift in any of the three byte-identical copies fails
`tests/test_proto_header_drift.py`.
