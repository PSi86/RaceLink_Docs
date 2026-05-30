# STRUCTURE — code ↔ doc contract

The single index that ties every documentation file to the code it
covers and vice versa. Curated by hand. **Update this file as part
of every PR that adds, moves, or significantly reshapes a doc or
introduces a new code area.**

> Three tables. Three lookups.
>
> 1. **Topic → Document** — *"where do I read about X?"*
> 2. **Code change → Doc to update** — *"I changed Y, what docs need
>    a touch?"*
> 3. **Document → Backing code** — *"this doc claims something —
>    where is the implementation?"*
>
> The tables are not exhaustive — they list the typical entry
> points. The long tail is found via search.

---

## Audience & visibility

Two visibility tiers exist in this repo:

* **`docs/`** — public. Built by MkDocs, served at docs.racelink.dev,
  and visible in the GitHub repository.
* **`_meta/` and `_private/`** — strictly local. Both are gitignored
  and never reach GitHub:
  * `_meta/` — repo-internal working material kept on the
    maintainer's machine: audit history (`_meta/audit/`), contributor
    workflow notes (`_meta/contributor/`), maintainer notes
    (`_meta/maintainer/`), and component-repo configuration
    templates (`_meta/templates/`). Some files contain
    workstation-absolute paths and must not be published.
  * `_private/` — ADR drafts (`_private/adr-drafts/`) and the local
    plan archive (`_private/plans/`).

One file inside `docs/` is **on disk but excluded from the built
site** via `exclude_docs:` in [`mkdocs.yml`](mkdocs.yml):

* `docs/sources.md` — provenance ledger. Tracks per-file origin
  during the consolidation. Useful for AI tooling and maintainers
  rebuilding context; not useful to end users. Lives at a stable
  path so it can be referenced from `CLAUDE.md` across sessions,
  but never appears at a public URL.

The three tables below cover the navigable public set plus the
excluded-but-on-disk provenance ledger (flagged where it appears).

---

## Table 1 — Topic → Document

For *"I want to read about X, where is it?"*. Primary doc in the
middle column; cross-references in the right column.

| Topic | Primary doc | See also |
|---|---|---|
| **System overview** (architecture diagram, components) | [`docs/index.md`](docs/index.md) | `RaceLink_Host/README.md`, `RaceLink_Gateway/README.md`, `RaceLink_WLED/README.md` |
| **Glossary** (Preset / Effect / Group / Capability / Master pill / etc.) | [`docs/glossary.md`](docs/glossary.md) | — |
| **Multi-Network operator workflow** (create network, bind wizard, RF migration, channel scan, setup-change assistant) | [`docs/RaceLink_Host/multi-network.md`](docs/RaceLink_Host/multi-network.md) | reference/channels.md, RaceLink_Host/architecture.md §"Multi-Transport runtime" |
| **Broadcast scope** (BroadcastTarget, threaded fan-out, scene-derived sync scope, operator-pinned `scene.network_scope` with Auto / Explicit modes) | [`docs/RaceLink_Host/architecture.md`](docs/RaceLink_Host/architecture.md) §"Cross-network fan-out (Stage 3 Part G → BroadcastTarget refactor)" | RaceLink_Host/multi-network.md §"Scene broadcast scope"; RaceLink_Host/scene-authoring.md §"Scene scope on multi-network setups" |
| **Move groups between networks** (per-group migration, unified Manage-groups dialog, multi-group selection, offline-mode block/skip/force) | [`docs/RaceLink_Host/multi-network.md`](docs/RaceLink_Host/multi-network.md) §"Move groups between networks" | RaceLink_Host/architecture.md §"Per-group network migration"; RaceLink_Host/device-setup.md §"Manage groups (reorder + move between networks)" |
| **Channel table** (per-region channel slots, compliance) | [`docs/reference/channels.md`](docs/reference/channels.md) | RaceLink_Host/multi-network.md, reference/wire-protocol.md §`P_RfConfig` |
| **`P_RfConfig` / `OPC_RF_CONFIG` / `EV_RF_CHANGED`** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §`P_RfConfig`, §"USB-signal frames" | reference/channels.md, glossary §`P_RfConfig` |
| **Multi-Transport runtime / Bind-state machine / RF migration engine** | [`docs/RaceLink_Host/architecture.md`](docs/RaceLink_Host/architecture.md) §"Multi-Transport runtime" | RaceLink_Host/reply-matching.md, RaceLink_Host/multi-network.md |
| **Opcodes** — pragmatic OPC_CONTROL/OFFSET/SYNC explanation | [`docs/reference/opcodes.md`](docs/reference/opcodes.md) | reference/wire-protocol.md, RaceLink_Host/scene-authoring.md |
| **Host WebUI structure / lifecycle / orientation** | [`docs/RaceLink_Host/webui-overview.md`](docs/RaceLink_Host/webui-overview.md) | `RaceLink_Host/ui-conventions.md`; the task pages (device-setup, firmware-updates, rl-presets, scene-authoring) |
| **First-time operator workflow** | [`docs/RaceLink_Host/webui-overview.md`](docs/RaceLink_Host/webui-overview.md) §"A healthy-start workflow" | `RaceLink_Host/device-setup.md`, `RaceLink_Gateway/operator-setup.md`, `RaceLink_WLED/operator-setup.md` |
| **Device discovery / grouping / Specials** | [`docs/RaceLink_Host/device-setup.md`](docs/RaceLink_Host/device-setup.md) | `RaceLink_Host/multi-network.md` (move groups, channel scan); `glossary.md` §"Specials" |
| **RL Presets library** | [`docs/RaceLink_Host/rl-presets.md`](docs/RaceLink_Host/rl-presets.md) | `RaceLink_Host/scene-authoring.md`; `glossary.md` §"Preset" |
| **Standalone install (Win + Linux)** | [`docs/RaceLink_Host/standalone-install.md`](docs/RaceLink_Host/standalone-install.md) | `RaceLink_Host/README.md` |
| **RotorHazard plugin install** | [`docs/RaceLink_RH_Plugin/README.md`](docs/RaceLink_RH_Plugin/README.md) | `RaceLink_RH_Plugin/operator-setup.md` |
| **Gateway operator setup** | [`docs/RaceLink_Gateway/operator-setup.md`](docs/RaceLink_Gateway/operator-setup.md) | `RaceLink_Host/device-setup.md` |
| **WLED node operator setup** | [`docs/RaceLink_WLED/operator-setup.md`](docs/RaceLink_WLED/operator-setup.md) | `RaceLink_WLED/README.md` |
| **Headless Mode (operator)** | [`docs/RaceLink_WLED/headless-mode.md`](docs/RaceLink_WLED/headless-mode.md) | `glossary.md` §Headless Mode; `reference/wire-protocol.md` §`P_Headless` |
| **Indicators (operator + reference)** | [`docs/RaceLink_WLED/indicators.md`](docs/RaceLink_WLED/indicators.md) | `glossary.md` §Indicator; `reference/wire-protocol.md` §`P_Indicate` |
| **WLED node pin configuration** | [`docs/RaceLink_WLED/pin-config.md`](docs/RaceLink_WLED/pin-config.md) | `RaceLink_WLED/README.md` §"Build profile notes" |
| **WLED radio modules (developer)** | [`docs/RaceLink_WLED/radio-modules.md`](docs/RaceLink_WLED/radio-modules.md) | `RaceLink_WLED/operator-setup.md`, `RaceLink_WLED/README.md` |
| **RotorHazard plugin operator (panels, quickbuttons)** | [`docs/RaceLink_RH_Plugin/operator-setup.md`](docs/RaceLink_RH_Plugin/operator-setup.md) | `RaceLink_Host/architecture.md` §"UI Scope Matrix" |
| **Authoring scenes (operator)** | [`docs/RaceLink_Host/scene-authoring.md`](docs/RaceLink_Host/scene-authoring.md) | `reference/scene-format.md`; `RaceLink_Host/rl-presets.md`; `RaceLink_Host/device-setup.md` (the broader workflow) |
| **Offset Mode (operator perspective)** | [`docs/RaceLink_Host/scene-authoring.md`](docs/RaceLink_Host/scene-authoring.md) §"Working with offset mode" | `reference/wire-protocol.md` §"OPC_OFFSET"; `reference/opcodes.md` |
| **Target picker (Broadcast / Groups / Device)** | [`docs/RaceLink_Host/scene-authoring.md`](docs/RaceLink_Host/scene-authoring.md) §"The target picker" | `reference/broadcast-ruleset.md` |
| **Scene scope on multi-network (Auto / Explicit)** | [`docs/RaceLink_Host/scene-authoring.md`](docs/RaceLink_Host/scene-authoring.md) §"Scene scope on multi-network setups" | `RaceLink_Host/multi-network.md` §"Scene broadcast scope"; `RaceLink_Host/architecture.md` §"Cross-network fan-out" |
| **Cyclic-effect phase-lock pitfall** | [`docs/reference/opcodes.md`](docs/reference/opcodes.md) §"Cyclic-effect phase-lock" | `RaceLink_WLED/operator-setup.md`, `troubleshooting.md` |
| **OTA workflow + WLED presets (operator)** | [`docs/RaceLink_Host/firmware-updates.md`](docs/RaceLink_Host/firmware-updates.md) | `RaceLink_Host/developer-guide.md` §"WLED OTA gate matrix"; `reference/wled-ota-gates.md` |
| **OTA gate matrix (developer)** | [`docs/reference/wled-ota-gates.md`](docs/reference/wled-ota-gates.md) | `RaceLink_Host/firmware-updates.md`; `RaceLink_Host/developer-guide.md` §"WLED OTA gate matrix" pointer |
| **Gateway badges / master bar / gateway lifecycle** | [`docs/RaceLink_Host/webui-overview.md`](docs/RaceLink_Host/webui-overview.md) §"The master bar — gateway badges" | `RaceLink_Host/multi-network.md` §"Per-gateway pills"; `reference/wire-protocol.md` §"Gateway state machine" |
| **Wire protocol (full reference)** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) | `RaceLink_Host/architecture.md` §"Transport Interface" |
| **Opcodes** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §"Opcodes" | `glossary.md` §"Opcode" |
| **Body layouts (P_Preset, OPC_CONTROL, OPC_OFFSET, P_Sync, P_Config)** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §"Body layouts" | `reference/scene-format.md` |
| **Flags byte** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §"Flags byte" | `glossary.md` §"Flags byte" |
| **`OPC_OFFSET` strict acceptance gate** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §"Acceptance gate" | `RaceLink_Host/scene-authoring.md` §"Working with offset mode" |
| **`OPC_SYNC` 4 vs 5-byte forms** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §"OPC_SYNC variants" | — |
| **USB framing + signal frames** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §"USB framing" / §"USB-signal frames" | `RaceLink_Gateway/README.md` §"Communication overview" |
| **`EV_TX_REJECTED` reason codes** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §"EV_TX_REJECTED reason codes" | `RaceLink_Host/architecture.md` §"Transport Interface" |
| **Gateway state machine** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §"Gateway state machine" | `RaceLink_Host/webui-overview.md` §"The master bar — gateway badges" |
| **Broadcast ruleset (two-stage filter)** | [`docs/reference/broadcast-ruleset.md`](docs/reference/broadcast-ruleset.md) | `reference/opcodes.md`, `reference/scene-format.md` |
| **Per-packet wire timing** | [`docs/reference/wire-timing.md`](docs/reference/wire-timing.md) | `reference/wire-protocol.md` |
| **Threading model + locks** | [`docs/RaceLink_Host/architecture.md`](docs/RaceLink_Host/architecture.md) §"Threading Model" | `contributing.md` |
| **Locking rule (never hold across RF I/O)** | [`docs/RaceLink_Host/architecture.md`](docs/RaceLink_Host/architecture.md) §"Locking Rule" | `contributing.md` |
| **Service layer table** | [`docs/RaceLink_Host/architecture.md`](docs/RaceLink_Host/architecture.md) §"Service Layer" | `RaceLink_Host/developer-guide.md` §"Adding a new service" |
| **Reply matching (PendingMatcher)** | [`docs/RaceLink_Host/reply-matching.md`](docs/RaceLink_Host/reply-matching.md) | `RaceLink_Host/architecture.md` §"Transport Interface" |
| **State-scope tokens (FULL/DEVICES/GROUPS/RL_PRESETS/WLED_PRESETS/...)** | [`docs/RaceLink_Host/architecture.md`](docs/RaceLink_Host/architecture.md) §"UI Scope Matrix" | `reference/sse-channels.md` |
| **UI Scope Matrix (RH adapter elements)** | [`docs/RaceLink_Host/architecture.md`](docs/RaceLink_Host/architecture.md) §"UI Scope Matrix" | `RaceLink_RH_Plugin/operator-setup.md` |
| **Adding a new scene-action kind** | [`docs/RaceLink_Host/developer-guide.md`](docs/RaceLink_Host/developer-guide.md) §"Adding a new scene-action kind" | `reference/scene-format.md` |
| **Adding a new wire opcode** | [`docs/RaceLink_Host/developer-guide.md`](docs/RaceLink_Host/developer-guide.md) §"Adding a new wire opcode" | `reference/wire-protocol.md` |
| **Adding a new service** | [`docs/RaceLink_Host/developer-guide.md`](docs/RaceLink_Host/developer-guide.md) §"Adding a new service" | `RaceLink_Host/architecture.md` |
| **Adding a task-manager workflow** | [`docs/RaceLink_Host/developer-guide.md`](docs/RaceLink_Host/developer-guide.md) §"Adding a new task-manager-driven workflow" | `reference/sse-channels.md` |
| **WLED metadata regeneration** | [`docs/RaceLink_Host/developer-guide.md`](docs/RaceLink_Host/developer-guide.md) §"Regenerating WLED metadata" | `reference/deterministic-effects.md` |
| **Updating deterministic-effects list** | [`docs/RaceLink_Host/developer-guide.md`](docs/RaceLink_Host/developer-guide.md) §"Updating the WLED-deterministic effects list" | `reference/deterministic-effects.md` |
| **WebUI button vocabulary, toast/confirm conventions** | [`docs/RaceLink_Host/ui-conventions.md`](docs/RaceLink_Host/ui-conventions.md) | — |
| **Gateway hardware target / build flags** | [`docs/RaceLink_Gateway/README.md`](docs/RaceLink_Gateway/README.md) | — |
| **WLED build profiles** | [`docs/RaceLink_WLED/README.md`](docs/RaceLink_WLED/README.md) §"Supported hardware profiles" | — |
| **Deterministic effects audit (which effects sync)** | [`docs/reference/deterministic-effects.md`](docs/reference/deterministic-effects.md) | `RaceLink_Host/scene-authoring.md` §"Working with offset mode" |
| **Scene file format** (`scenes.json`) | [`docs/reference/scene-format.md`](docs/reference/scene-format.md) | `RaceLink_Host/scene-authoring.md` |
| **Web API endpoints** | [`docs/reference/web-api.md`](docs/reference/web-api.md) (stub) | `RaceLink_Host/architecture.md` §"Service Layer" |
| **SSE channels & state scopes** | [`docs/reference/sse-channels.md`](docs/reference/sse-channels.md) | `RaceLink_Host/architecture.md` §"UI Scope Matrix" |
| **Versioning policy across components** | [`docs/versioning.md`](docs/versioning.md) | `RaceLink_Host/README.md` §"Release artifacts" |
| **Contributing rules (PR, smoke tests, conventions)** | [`docs/contributing.md`](docs/contributing.md) | `RaceLink_Host/developer-guide.md` |
| **Troubleshooting index (operator)** | [`docs/troubleshooting.md`](docs/troubleshooting.md) | `RaceLink_Host/webui-overview.md` |
| **Per-component licences** | [`docs/licenses.md`](docs/licenses.md) | — |
| **Changelog** | [`docs/changelog.md`](docs/changelog.md) | — |
| **Roadmap (forward-looking commitments)** | [`docs/roadmap.md`](docs/roadmap.md) | — |
| **RH plugin manifest dependency format (decision)** | [`docs/RaceLink_RH_Plugin/adr-0001-manifest-dependency.md`](docs/RaceLink_RH_Plugin/adr-0001-manifest-dependency.md) | `RaceLink_RH_Plugin/manifest-dependency-format.md` |
| **RH plugin release flow** | [`docs/RaceLink_RH_Plugin/release-playbook.md`](docs/RaceLink_RH_Plugin/release-playbook.md) | `versioning.md` |
| **Development workflow (this repo)** | The contract is encoded directly in this `STRUCTURE.md` (the three tables below); maintainer-side workflow notes live under `_meta/contributor/` (local only, gitignored) | — |
| **Audit history (what was consolidated, what was harvested)** | [`docs/sources.md`](docs/sources.md) — provenance ledger, **excluded from the built site** (on-disk only, for AI/maintainer context); full audit + harvest notes live under `_meta/maintainer/` (local only, gitignored) | — |

---

## Table 2 — Code change → Doc to update

For *"I just changed code in X, what docs need updating?"*. Code
paths are inside the matching component repository (e.g.
`RaceLink_Host/racelink/...`).

| If you change … | Update … |
|---|---|
| `racelink_proto.h` (byte-identical across Host + Gateway + WLED) | `docs/reference/wire-protocol.md` opcode table + body layout tables; `docs/glossary.md` if a new opcode/flag is named; `docs/RaceLink_Host/developer-guide.md` §"Adding a new wire opcode" if the *process* changed |
| `racelink_headless.h` (Headless-Mode scene catalog — byte-identical across Gateway + WLED only; **not present in Host** — the Host has no Python consumer for this header) | `docs/RaceLink_WLED/headless-mode.md` → Scenes table; `docs/RaceLink_Host/developer-guide.md` §"Adding a new Headless scene to the catalog"; `docs/glossary.md` §"Headless Mode" if semantics change |
| `racelink_indicators.h` (Indicator catalog — byte-identical across Host + Gateway + WLED; Host carries it because `racelink/domain/indicators.py` is a hand-authored mirror that the drift test guards) | `docs/RaceLink_WLED/indicators.md` → Catalog table; `docs/RaceLink_Host/developer-guide.md` §"Adding a new Indicator to the catalog"; `docs/glossary.md` §"Indicator" if semantics change; `docs/reference/wire-protocol.md` §`P_Indicate` if the cancel-via-`durationSec=0` contract changes |
| `racelink_transport_core.h` (TX pipeline / LBT / CAD; byte-identical across Gateway + WLED only; **not present in Host** — same FW-only rationale as `racelink_headless.h`) | `docs/reference/wire-protocol.md` §"Host ↔ Gateway flow control" if the LBT / `scheduleSend(jitterMaxMs=0)` contract changes; `docs/RaceLink_Host/developer-guide.md` §"Time-critical TX" if the unified-bypass contract changes |
| `RaceLink_Host/racelink/protocol/{packets,codec,rules}.py` | `docs/reference/wire-protocol.md` (the rules table mirrors `rules.RULES`); cross-check that the body-builder doc matches `packets.build_*` |
| `RaceLink_Host/racelink/transport/{gateway_serial,framing}.py` | `docs/RaceLink_Host/architecture.md` §"Transport Interface" + §"Threading Model" if locks/condition variables change; `docs/reference/wire-protocol.md` §"USB framing" / §"Host ↔ Gateway flow control" |
| `RaceLink_Host/racelink/transport/broadcast_target.py` (BroadcastTarget class — scope object for multi-network broadcasts) | `docs/RaceLink_Host/architecture.md` §"Cross-network fan-out" if factory semantics change; `docs/RaceLink_Host/multi-network.md` §"Scene broadcast scope" if operator-visible behaviour changes |
| `RaceLink_Host/racelink/transport/broadcast_fanout.py` (threaded fan-out helper + `resolve_broadcast_transports`) | `docs/RaceLink_Host/architecture.md` §"Cross-network fan-out" + §"Threading Model" if locking discipline / thread model changes |
| `RaceLink_Host/racelink/services/scene_network_scope.py` (computes scene's network set from action targets, honours explicit override) | `docs/RaceLink_Host/architecture.md` §"Cross-network fan-out" (the resolution rules table); `docs/RaceLink_Host/multi-network.md` §"Scene broadcast scope" if target-kind handling changes; `docs/RaceLink_Host/scene-authoring.md` §"Scene scope on multi-network setups" if the operator-visible scope rules change |
| `RaceLink_Host/racelink/services/scenes_service.py` `_canonical_network_scope` (structural validator) | `docs/RaceLink_Host/architecture.md` §"Cross-network fan-out" if the persisted shape or validation rules change; `docs/RaceLink_Host/multi-network.md` §"Scene broadcast scope" wire-shape table |
| `RaceLink_Host/racelink/domain/network_boundary.py` `validate_scene_scope_consistency` + `SceneScopeViolation` (repository-coupled cross-validator at the API layer) | `docs/RaceLink_Host/architecture.md` §"Cross-network fan-out" violation table; `docs/RaceLink_Host/scene-authoring.md` §"Scene scope on multi-network setups" if the rejection messages change |
| `RaceLink_Host/frontend/src/components/scenes/SceneNetworkScopeWidget.vue` (scope picker chip + dialog) | `docs/RaceLink_Host/scene-authoring.md` §"Scene scope on multi-network setups" "Scope chip" subsection; `docs/RaceLink_Host/multi-network.md` §"Scene broadcast scope" UI parts |
| `RaceLink_Host/frontend/src/components/scenes/SceneTargetPicker.vue` / `MultiGroupPickerDialog.vue` (cascading scope filter for per-action target dropdowns) | `docs/RaceLink_Host/scene-authoring.md` §"Scene scope on multi-network setups" cascading-filter subsection; `docs/RaceLink_Host/architecture.md` §"Cross-network fan-out" cascade rule |
| `RaceLink_Host/racelink/services/scenes_service.py` | `docs/reference/scene-format.md` (KIND_* enum, validator invariants); `docs/RaceLink_Host/developer-guide.md` §"Adding a new scene-action kind" if the checklist changes |
| `RaceLink_Host/racelink/services/scene_runner_service.py` | `docs/RaceLink_Host/developer-guide.md` §"Adding a new scene-action kind" (dispatch contract); if behaviour changes that an operator notices, `docs/RaceLink_Host/scene-authoring.md` §"Run a scene" / §"Working with offset mode"; `docs/RaceLink_Host/architecture.md` §"Cross-network fan-out" if scene-derived sync scope changes |
| `RaceLink_Host/racelink/services/scene_cost_estimator.py` | `docs/reference/scene-format.md` (cost contract); `docs/RaceLink_Host/scene-authoring.md` §"Measured run-time alongside estimates" |
| `RaceLink_Host/racelink/services/dispatch_planner.py` (single source of truth for "what packets does this action emit" — consumed by both runner and estimator) | `docs/reference/scene-format.md` (cost contract row); `docs/RaceLink_Host/developer-guide.md` §"Adding a new scene-action kind" if the planner contract changes |
| `RaceLink_Host/racelink/services/sync_service.py` | `docs/reference/wire-protocol.md` §"OPC_SYNC variants"; `docs/RaceLink_Host/architecture.md` §"Service Layer" |
| `RaceLink_Host/racelink/services/offset_dispatch_optimizer.py` | `docs/reference/wire-protocol.md` §"OPC_OFFSET" if wire strategy changes; `docs/RaceLink_Host/scene-authoring.md` §"Working with offset mode" if user-visible |
| `RaceLink_Host/racelink/services/control_service.py` | `docs/RaceLink_Host/architecture.md` §"Service Layer" row; `docs/contributing.md` §"Boolean send contract" if the contract is touched |
| `RaceLink_Host/racelink/services/gateway_service.py` | `docs/RaceLink_Host/architecture.md` §"Service Layer" + §"Threading Model" (auto-restore executor, reconnect, pending-request registry) |
| `RaceLink_Host/racelink/services/gateway_bind_service.py` | `docs/RaceLink_Host/architecture.md` §"Multi-Transport runtime" → "Bind-state machine"; `docs/RaceLink_Host/multi-network.md` §"Conflict resolution" |
| `RaceLink_Host/racelink/services/rf_migration_service.py` | `docs/RaceLink_Host/architecture.md` §"Multi-Transport runtime" → "RF migration engine" + §"Per-group network migration"; `docs/RaceLink_Host/multi-network.md` §"RF migration" + §"Move groups between networks" |
| `RaceLink_Host/frontend/src/components/modals/ManageGroupsDialog.vue` + `DevicesSidebar.vue` (single entry point: per-group network migration with multi-select + drag-reorder in one dialog) | `docs/RaceLink_Host/device-setup.md` §"Manage groups (reorder + move between networks)"; `docs/RaceLink_Host/multi-network.md` §"Move groups between networks" |
| `RaceLink_Host/racelink/services/channel_scan_service.py` | `docs/RaceLink_Host/architecture.md` §"Multi-Transport runtime" → "Channel-Scan service"; `docs/RaceLink_Host/multi-network.md` §"Channel Scan" |
| `RaceLink_Host/racelink/domain/rf_channels.py` / `rf_policy.py` | `docs/reference/channels.md`; `docs/reference/wire-protocol.md` §`P_RfConfig` if the wire fields change |
| `RaceLink_Host/racelink/domain/network_boundary.py` | `docs/RaceLink_Host/architecture.md` §"Network-boundary enforcement"; `docs/RaceLink_Host/multi-network.md` §"Boundary enforcement" |
| `RaceLink_Host/racelink/services/ota_service.py` / `ota_workflow_service.py` | `docs/RaceLink_Host/firmware-updates.md` §"Firmware Update (OTA)"; `docs/reference/wled-ota-gates.md` if the four-gate semantics or the host-side auto-unlock contract changes; the module-docstring on `ota_workflow_service.py` carries the per-device cleanup contract (AP-Enable retry shape, conditional AP-Close, two-track error surface) |
| `RaceLink_Host/racelink/services/host_wifi_service.py` | `docs/RaceLink_Host/standalone-install.md` §"Linux first-time setup" |
| `RaceLink_Host/racelink/services/rl_presets_service.py` / `presets_service.py` | `docs/glossary.md` (Preset entry); `docs/RaceLink_Host/rl-presets.md` (RL Presets library); `docs/RaceLink_Host/firmware-updates.md` §"WLED Presets" |
| `RaceLink_Host/racelink/services/specials_service.py` | `docs/RaceLink_Host/device-setup.md` §"Configure devices (Specials)" |
| `RaceLink_Host/racelink/services/discovery_service.py` / `status_service.py` | `docs/RaceLink_Host/device-setup.md` §"Discover devices"; `docs/reference/web-api.md` |
| `RaceLink_Host/racelink/services/startblock_service.py` / `stream_service.py` | `docs/reference/wire-protocol.md` §"OPC_STREAM" if format changes; `docs/RaceLink_Host/scene-authoring.md` §"Action kinds" (Startblock Control) if operator UI changes |
| `RaceLink_Host/racelink/state/repository.py` | `docs/RaceLink_Host/architecture.md` §"Threading Model" (the lock); `docs/contributing.md` §"Locking rule" |
| `RaceLink_Host/racelink/web/api.py` | `docs/reference/web-api.md` (route list, request/response shapes); `docs/RaceLink_Host/developer-guide.md` §"Adding a new service" route conventions |
| `RaceLink_Host/racelink/web/sse.py` / `racelink/domain/state_scope.py` | `docs/reference/sse-channels.md` (token map); `docs/RaceLink_Host/architecture.md` §"UI Scope Matrix" |
| `RaceLink_Host/racelink/web/tasks.py` / `request_helpers.py` | `docs/RaceLink_Host/developer-guide.md` §"Adding a task-manager-driven workflow" |
| `RaceLink_Host/racelink/web/blueprint.py` (Flask blueprint registration; the integration edge for outer adapters via `racelink.web.register_racelink_web`) | `docs/RaceLink_Host/README.md` §"Hosting modes"; `docs/RaceLink_Host/architecture.md` §"Service Layer" |
| `RaceLink_Host/racelink/state/{persistence,migrations,defaults}.py` (v1→v2 multi-network migration lives here) | `docs/RaceLink_Host/multi-network.md` if the migration shape changes; `docs/RaceLink_Host/architecture.md` §"Threading Model" if the lock semantics change |
| `RaceLink_Host/racelink/domain/flags.py` | `docs/reference/wire-protocol.md` §"Flags byte"; `docs/glossary.md` |
| `RaceLink_Host/racelink/domain/wled_effects.py` / `wled_palettes.py` / `wled_palette_color_rules.py` | `docs/RaceLink_Host/developer-guide.md` §"Regenerating WLED metadata" — **these files are auto-generated; do not hand-edit, regenerate** |
| `RaceLink_Host/racelink/domain/wled_deterministic.py` | `docs/reference/deterministic-effects.md`; `docs/RaceLink_Host/developer-guide.md` §"Updating the WLED-deterministic effects list" |
| `RaceLink_Host/racelink/domain/state_scope.py` | `docs/reference/sse-channels.md`; `docs/RaceLink_Host/architecture.md` §"UI Scope Matrix" |
| `RaceLink_Host/racelink/domain/indicators.py` (Python mirror of the indicator catalog) | `docs/RaceLink_WLED/indicators.md`; `docs/glossary.md` §"Indicator" if semantics change |
| `RaceLink_Host/racelink/domain/capabilities.py` (caps filter for scene targets) | `docs/glossary.md` §"Capability"; `docs/RaceLink_Host/scene-authoring.md` if the cap-filter UX changes |
| `RaceLink_Host/racelink/domain/specials.py` / `models.py` | `docs/reference/wire-protocol.md` body layouts if wire-relevant |
| `RaceLink_Host/racelink/static/scenes.js` | `docs/reference/scene-format.md` (kind-to-cap mapping); `docs/RaceLink_Host/ui-conventions.md` if button vocabulary touched |
| `RaceLink_Host/racelink/static/racelink.js` | `docs/RaceLink_Host/ui-conventions.md`; `docs/reference/sse-channels.md` if the SSE consumer contract changes |
| `RaceLink_Host/racelink/static/racelink.css` | usually no doc impact unless visual conventions change → `docs/RaceLink_Host/ui-conventions.md` |
| `RaceLink_Host/racelink/pages/*.html` | `docs/RaceLink_Host/ui-conventions.md` if structure/button labels change |
| `RaceLink_Host/racelink/integrations/standalone/**` | `docs/RaceLink_Host/standalone-install.md`; `docs/RaceLink_Host/README.md` §"Hosting modes" |
| `RaceLink_Host/controller.py` | `docs/RaceLink_Host/architecture.md` §"Service Layer" if methods move; `docs/RaceLink_Host/developer-guide.md` if the wiring pattern changes |
| `RaceLink_Host/racelink/_version.py` / wheel filename pattern | `docs/RaceLink_Host/README.md` §"Release artifacts"; `docs/versioning.md`; `docs/changelog.md` |
| `RaceLink_Host/.github/workflows/release.yml` | `docs/RaceLink_Host/README.md` §"Release artifacts"; `docs/versioning.md` |
| `RaceLink_Host/scripts/setup_nmcli_polkit.sh` (or the console-script form) | `docs/RaceLink_Host/standalone-install.md` §"Linux first-time setup" |
| `RaceLink_Gateway/src/main.cpp` (state machine, USB framing, autosync) | `docs/reference/wire-protocol.md` §"Gateway state machine" / §"Host ↔ Gateway flow control"; `docs/RaceLink_Gateway/README.md` |
| `RaceLink_Gateway/src/racelink_transport_core.h` | `docs/reference/wire-protocol.md`; `docs/RaceLink_Gateway/README.md` |
| `RaceLink_Gateway/platformio.ini` (board, radio defaults) | `docs/RaceLink_Gateway/README.md` §"Hardware and build target"; `docs/RaceLink_Gateway/operator-setup.md` §"Radio defaults" |
| `RaceLink_WLED/racelink_wled.{h,cpp}` (usermod source at repo root) | `docs/RaceLink_WLED/operator-setup.md`; `docs/reference/deterministic-effects.md` if effect determinism changes |
| `RaceLink_WLED/racelink_headless.h` (Headless scene catalog) | `docs/RaceLink_WLED/headless-mode.md`; `docs/RaceLink_Host/developer-guide.md` §"Where the headless state lives"; `docs/glossary.md` if semantics change |
| `RaceLink_WLED/racelink_indicators.h` (Indicator catalog) | `docs/RaceLink_WLED/indicators.md`; `docs/glossary.md` if semantics change |
| `RaceLink_WLED/build_profiles/*.platformio_override.ini` (new or changed) | `docs/RaceLink_WLED/README.md` §"Supported hardware profiles"; `docs/RaceLink_WLED/operator-setup.md` §"Default factory state" if defaults changed; `docs/RaceLink_WLED/pin-config.md` if a profile's `-D RACELINK_PIN_*` defaults change |
| `RaceLink_WLED/racelink_epaper.{h,cpp}` (e-paper async worker; only built when `-D RACELINK_EPAPER` is set) | `docs/RaceLink_WLED/pin-config.md` if the `epaper_pins` block changes |
| `RaceLink_WLED/.github/workflows/release.yml` | `docs/RaceLink_WLED/README.md` §"GitHub release workflow"; `docs/versioning.md` |
| `RaceLink_RH_Plugin/custom_plugins/racelink_rh_plugin/manifest.json` | `docs/RaceLink_RH_Plugin/adr-0001-manifest-dependency.md`; `docs/RaceLink_RH_Plugin/manifest-dependency-format.md` |
| `RaceLink_RH_Plugin/custom_plugins/racelink_rh_plugin/plugin/ui.py` | `docs/RaceLink_Host/architecture.md` §"UI Scope Matrix"; `docs/RaceLink_RH_Plugin/operator-setup.md` |
| `RaceLink_RH_Plugin/custom_plugins/racelink_rh_plugin/plugin/actions.py` | `docs/RaceLink_RH_Plugin/operator-setup.md` (race-event integration) |
| `RaceLink_RH_Plugin/custom_plugins/racelink_rh_plugin/plugin/bootstrap.py` | `docs/RaceLink_RH_Plugin/README.md` §"Architecture" |
| `RaceLink_RH_Plugin/.github/workflows/offline-release.yaml` | `docs/RaceLink_RH_Plugin/release-playbook.md`; `docs/RaceLink_RH_Plugin/README.md` §"Release Process" |
| `RaceLink_RH_Plugin/build/deps.json` | `docs/RaceLink_RH_Plugin/README.md` §"Version Mapping" |
| **The wire format itself** (any opcode/flag/struct change) | All three: `racelink_proto.h` byte-identical, `docs/reference/wire-protocol.md`, `docs/RaceLink_Host/developer-guide.md` §"Adding a new wire opcode" if process; `docs/versioning.md` if `PROTO_VER_MAJOR/MINOR` bumped |

---

## Table 3 — Document → Backing code

For *"this doc claims something — where is the implementation?"*.
Code paths use the source-repo path. Multiple entries indicate the
authoritative file followed by supporting code.

| Document | Backing code (canonical paths in source repos) |
|---|---|
| `docs/index.md` | (overview only — no specific backing code) |
| `docs/glossary.md` | `RaceLink_Host/racelink_proto.h` (wire terms); `RaceLink_Host/racelink/services/*.py` (host-runtime terms); `RaceLink_WLED/build_profiles/` (build-profile terms) |
| `docs/contributing.md` | `RaceLink_Host/tests/test_*.py` (smoke-test gates); `RaceLink_Host/racelink/domain/flags.py` (flags-byte builder); `RaceLink_Host/racelink/services/control_service.py` (boolean send contract) |
| `docs/versioning.md` | `RaceLink_Host/racelink/_version.py`; `RaceLink_Host/racelink_proto.h` (`PROTO_VER_*`); `RaceLink_RH_Plugin/build/deps.json`; each repo's `.github/workflows/release.yml` |
| `docs/changelog.md` | each repo's GitHub releases page (manually curated mirror) |
| `docs/troubleshooting.md` | (aggregator — no single backing file) |
| `docs/licenses.md` | each repo's `LICENSE` file |
| `docs/sources.md` | (provenance ledger — no backing code; **excluded from the built site** via `exclude_docs:` in `mkdocs.yml`) |
| `docs/RaceLink_Host/README.md` | `RaceLink_Host/racelink/__init__.py` (`__version__`); `RaceLink_Host/racelink/app.py`; `RaceLink_Host/racelink/web/__init__.py` |
| `docs/RaceLink_Host/architecture.md` | `RaceLink_Host/racelink/app.py`, `controller.py`, `racelink/services/*.py`, `racelink/state/repository.py`, `racelink/web/sse.py`, `racelink/transport/gateway_serial.py` |
| `docs/RaceLink_Host/multi-network.md` | `racelink/services/{gateway_bind_service,rf_migration_service,channel_scan_service}.py`; `racelink/domain/{network_boundary,rf_channels,rf_policy}.py`; `racelink/controller.py` (transport_for_network / transport_for_device / transport_for_group); `racelink/web/api.py` `/api/networks*` + `/api/gateways*` routes; `racelink/services/scene_network_scope.py` + `racelink/transport/{broadcast_target,broadcast_fanout}.py` (scene-driven broadcast scope) |
| `docs/reference/channels.md` | `racelink/domain/rf_channels.py` (the shipped table); `racelink/domain/rf_policy.py` (validator); `tests/test_rf_channels.py` + `tests/test_rf_policy_separation.py` pin the invariants |
| `docs/RaceLink_Host/webui-overview.md` | (operator-facing orientation; backed by `racelink/static/racelink.js`, `racelink/pages/*.html`, `racelink/web/{sse,tasks,api}.py`) |
| `docs/RaceLink_Host/device-setup.md` | `racelink/services/{discovery_service,status_service,specials_service}.py`; `racelink/services/group*`/repository for grouping; `racelink/domain/{capabilities,network_boundary}.py`; frontend `ManageGroupsDialog.vue` / `DevicesSidebar.vue` |
| `docs/RaceLink_Host/firmware-updates.md` | `racelink/services/{ota_service,ota_workflow_service,presets_service}.py`; `racelink/services/host_wifi_service.py`; `reference/wled-ota-gates.md` for the gate matrix |
| `docs/RaceLink_Host/rl-presets.md` | `racelink/services/rl_presets_service.py`; the `OPC_CONTROL` mapping in `reference/opcodes.md` |
| `docs/RaceLink_Host/scene-authoring.md` | `racelink/services/scenes_service.py`, `scene_runner_service.py`, `scene_cost_estimator.py`, `scene_network_scope.py`, `dispatch_planner.py`, `offset_dispatch_optimizer.py`; firmware `racelink_wled.cpp` (offset-mode strict gate, deferred-apply); the cost-badge contract lives in `reference/scene-format.md` |
| `docs/RaceLink_Host/developer-guide.md` | `RaceLink_Host/racelink/services/scenes_service.py`, `racelink/services/scene_runner_service.py`, `racelink/services/scene_cost_estimator.py`; `RaceLink_Host/racelink_proto.h`; `RaceLink_Host/gen_wled_metadata.py` and `racelink/domain/wled_*.py`; `RaceLink_Host/racelink/services/ota_service.py` |
| `docs/reference/wire-protocol.md` | **canonical: `RaceLink_Host/racelink_proto.h`** (mirrored in Gateway + WLED). Helpers: `racelink/protocol/{packets,codec,rules}.py`, `racelink/transport/framing.py`, `racelink/racelink_proto_auto.py`, `gen_racelink_proto_py.py`, `tests/test_proto_header_drift.py` |
| `docs/reference/opcodes.md` | `racelink/services/control_service.py`, `scene_runner_service.py`, `offset_dispatch_optimizer.py`, `sync_service.py`; firmware `racelink_wled.cpp` (`handleControl`, `handleSync`, `serviceDeferredApply`, `applyPhaseOffsetToTimebase`); `racelink_proto.h` for the wire spec |
| `docs/RaceLink_Host/ui-conventions.md` | `RaceLink_Host/racelink/static/racelink.js` (`showToast`, `confirmDestructive`, `setBusy`); `racelink/static/scenes.js`; `racelink/pages/*.html` |
| `docs/RaceLink_Host/standalone-install.md` | `RaceLink_Host/racelink/integrations/standalone/`; `RaceLink_Host/scripts/setup_nmcli_polkit.sh`; the `racelink-standalone` and `racelink-setup-nmcli` console-script entry points in `pyproject.toml` |
| `docs/RaceLink_Gateway/README.md` | `RaceLink_Gateway/src/main.cpp`, `racelink_transport_core.h`, `platformio.ini` |
| `docs/RaceLink_Gateway/operator-setup.md` | (operator aggregator; OLED behaviour from `RaceLink_Gateway/src/main.cpp`) |
| `docs/RaceLink_WLED/README.md` | `RaceLink_WLED/build_profiles/*.platformio_override.ini`; `RaceLink_WLED/.github/workflows/release.yml`; `RaceLink_WLED/version.json` |
| `docs/RaceLink_WLED/operator-setup.md` | `RaceLink_WLED/racelink_wled.{h,cpp}` (factory state, pairing, `applyRaceLinkDefaults()`) |
| `docs/RaceLink_WLED/headless-mode.md` | `RaceLink_WLED/racelink_wled.{h,cpp}` (Headless Master state machine); `RaceLink_WLED/racelink_headless.h` (scene catalog + state structs) |
| `docs/RaceLink_WLED/indicators.md` | `RaceLink_WLED/racelink_wled.{h,cpp}` (`handleOverlayDraw()`); `RaceLink_WLED/racelink_indicators.h` (catalog); Host mirror `RaceLink_Host/racelink/domain/indicators.py` |
| `docs/reference/deterministic-effects.md` | upstream WLED `wled00/FX.cpp` per-effect; `RaceLink_Host/racelink/domain/wled_deterministic.py` (the host-side audited set) |
| `docs/RaceLink_RH_Plugin/README.md` | `RaceLink_RH_Plugin/custom_plugins/racelink_rh_plugin/manifest.json`; `pyproject.toml` |
| `docs/RaceLink_RH_Plugin/operator-setup.md` | `RaceLink_RH_Plugin/custom_plugins/racelink_rh_plugin/plugin/ui.py`; `actions.py`; `bootstrap.py` |
| `docs/RaceLink_RH_Plugin/manifest-dependency-format.md` | `RaceLink_RH_Plugin/custom_plugins/racelink_rh_plugin/manifest.json`; `RaceLink_RH_Plugin/scripts/verify_manifest_dependency_formats.py`; the `rhfest-action` it validates against |
| `docs/RaceLink_RH_Plugin/release-playbook.md` | `RaceLink_RH_Plugin/.github/workflows/offline-release.yaml`; `RaceLink_RH_Plugin/scripts/{build_offline_release,bump_manifest_version,resolve_racelink_host_release,sync_racelink_host_dependency}.py`; `RaceLink_RH_Plugin/build/deps.json` |
| `docs/RaceLink_RH_Plugin/adr-0001-manifest-dependency.md` | `RaceLink_RH_Plugin/custom_plugins/racelink_rh_plugin/manifest.json`; the `rhfest-action` it validates against |
| `docs/RaceLink_Host/reply-matching.md` | `RaceLink_Host/racelink/services/pending_requests.py`; `RaceLink_Host/racelink/services/gateway_service.py` `send_and_match` / `send_and_wait_with_retries` |
| `docs/RaceLink_WLED/pin-config.md` | `RaceLink_WLED/racelink_wled.{h,cpp}` (the runtime-configurable `pins` / `epaper_pins` `cfg.json` blocks); `RaceLink_WLED/build_profiles/*.platformio_override.ini` (per-target `-D RACELINK_PIN_*` defaults) |
| `docs/RaceLink_WLED/radio-modules.md` | `RaceLink_WLED/racelink_wled.cpp` (`radioInit()`); the RadioLib SX126x / SX127x class hierarchy (`-D RACELINK_SX1262` vs `-D RACELINK_LLCC68`) |
| `docs/reference/broadcast-ruleset.md` | `RaceLink_Host/racelink_proto.h` (`RULES[]`); `RaceLink_Host/racelink/protocol/rules.py`; firmware `racelink_wled.cpp` (`handlePacket` / per-opcode handlers) |
| `docs/reference/wire-timing.md` | `RaceLink_Host/racelink/transport/framing.py`; `RaceLink_Host/racelink/services/rf_timing.py`; firmware `racelink_transport_core.h` (`scheduleSend` LBT/CAD path) |
| `docs/reference/wled-ota-gates.md` | upstream WLED `wled00/wled_server.cpp` (Gates 1–3), `wled00/ota_update.cpp` + `wled_metadata.cpp` (Gate 4); `RaceLink_Host/racelink/services/ota_service.py` (`_wled_attempt_unlock`); `RaceLink_WLED/racelink_wled.cpp` (`otaSameSubnet = false` usermod override) |
| `docs/roadmap.md` | (forward-looking commitments — no backing code yet) |
