# Changelog

A consolidated timeline of releases across the four RaceLink
repositories. Currently a stub — entries should be added as releases
ship. Each entry should follow the template at the bottom of this
file.

> **Source of truth.** Each repository maintains its own GitHub
> releases page; this changelog is a curated cross-repo summary.
> When the cross-repo summary and a repository's release notes
> disagree, the repository's release notes win.

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
