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

The three tables below cover only `docs/` (the public set).

---

## Table 1 — Topic → Document

For *"I want to read about X, where is it?"*. Primary doc in the
middle column; cross-references in the right column.

| Topic | Primary doc | See also |
|---|---|---|
| **System overview** (architecture diagram, components) | [`docs/index.md`](docs/index.md) | host/README, gateway/README, wled/README |
| **Glossary** (Preset / Effect / Group / Capability / Master pill / etc.) | [`docs/glossary.md`](docs/glossary.md) | — |
| **Concepts** — pragmatic OPC_CONTROL/OFFSET/SYNC explanation | [`docs/concepts/opcodes.md`](docs/concepts/opcodes.md) | PROTOCOL.md, OPERATOR_GUIDE.md |
| **Host WebUI structure / lifecycle** | [`docs/RaceLink_Host/webui-guide.md`](docs/RaceLink_Host/webui-guide.md) | UI_CONVENTIONS.md, OPERATOR_GUIDE.md |
| **First-time operator workflow** | [`docs/RaceLink_Host/operator-guide.md`](docs/RaceLink_Host/operator-guide.md) | gateway/OPERATOR, wled/OPERATOR |
| **Standalone install (Win + Linux)** | [`docs/RaceLink_Host/standalone-install.md`](docs/RaceLink_Host/standalone-install.md) | host/README |
| **RotorHazard plugin install** | [`docs/RaceLink_RH_Plugin/README.md`](docs/RaceLink_RH_Plugin/README.md) | rh-plugin/OPERATOR |
| **Gateway operator setup** | [`docs/RaceLink_Gateway/operator-setup.md`](docs/RaceLink_Gateway/operator-setup.md) | host/docs/OPERATOR_GUIDE |
| **WLED node operator setup** | [`docs/RaceLink_WLED/operator-setup.md`](docs/RaceLink_WLED/operator-setup.md) | wled/README |
| **RotorHazard plugin operator (panels, quickbuttons)** | [`docs/RaceLink_RH_Plugin/operator-setup.md`](docs/RaceLink_RH_Plugin/operator-setup.md) | host/ARCHITECTURE §"UI Scope Matrix" |
| **Authoring scenes (operator)** | [`docs/RaceLink_Host/operator-guide.md`](docs/RaceLink_Host/operator-guide.md) §"Author scenes" | reference/SCENE_FORMAT |
| **Offset Mode (operator perspective)** | [`docs/RaceLink_Host/operator-guide.md`](docs/RaceLink_Host/operator-guide.md) §6a | host/docs/PROTOCOL §"OPC_OFFSET" |
| **Cyclic-effect phase-lock pitfall** | [`docs/troubleshooting.md`](docs/troubleshooting.md) | wled/OPERATOR, HARVEST |
| **OTA workflow (operator)** | [`docs/RaceLink_Host/operator-guide.md`](docs/RaceLink_Host/operator-guide.md) §"Firmware updates" | host/docs/DEVELOPER_GUIDE §"WLED OTA gate matrix" |
| **OTA gate matrix (developer)** | [`docs/RaceLink_Host/developer-guide.md`](docs/RaceLink_Host/developer-guide.md) §"WLED OTA gate matrix" | host/docs/OPERATOR_GUIDE |
| **Master pill states / gateway lifecycle** | [`docs/RaceLink_Host/operator-guide.md`](docs/RaceLink_Host/operator-guide.md) §"Master pill states" | host/docs/PROTOCOL §"Gateway state machine" |
| **Wire protocol (full reference)** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) | host/ARCHITECTURE §"Transport Interface" |
| **Opcodes** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §"Opcodes" | GLOSSARY §"Opcode" |
| **Body layouts (P_Preset, OPC_CONTROL, OPC_OFFSET, P_Sync, P_Config)** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §"Body layouts" | reference/SCENE_FORMAT |
| **Flags byte** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §"Flags byte" | GLOSSARY §"Flags byte" |
| **`OPC_OFFSET` strict acceptance gate** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §"Acceptance gate" | host/docs/OPERATOR_GUIDE §6a |
| **`OPC_SYNC` 4 vs 5-byte forms** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §"OPC_SYNC variants" | — |
| **USB framing + signal frames** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §"USB framing" / §"USB-signal frames" | gateway/README §"USB side" |
| **`EV_TX_REJECTED` reason codes** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §"EV_TX_REJECTED reason codes" | host/ARCHITECTURE §"Transport Interface" |
| **Gateway state machine** | [`docs/reference/wire-protocol.md`](docs/reference/wire-protocol.md) §"Gateway state machine" | host/docs/OPERATOR_GUIDE §"Master pill" |
| **Threading model + locks** | [`docs/RaceLink_Host/architecture.md`](docs/RaceLink_Host/architecture.md) §"Threading Model" | CONTRIBUTING |
| **Locking rule (never hold across RF I/O)** | [`docs/RaceLink_Host/architecture.md`](docs/RaceLink_Host/architecture.md) §"Locking Rule" | CONTRIBUTING |
| **Service layer table** | [`docs/RaceLink_Host/architecture.md`](docs/RaceLink_Host/architecture.md) §"Service Layer" | host/docs/DEVELOPER_GUIDE §"Adding a new service" |
| **State-scope tokens (FULL/DEVICES/GROUPS/PRESETS/...)** | [`docs/RaceLink_Host/architecture.md`](docs/RaceLink_Host/architecture.md) §"UI Scope Matrix" | reference/SSE_CHANNELS |
| **UI Scope Matrix (RH adapter elements)** | [`docs/RaceLink_Host/architecture.md`](docs/RaceLink_Host/architecture.md) §"UI Scope Matrix" | rh-plugin/OPERATOR |
| **Adding a new scene-action kind** | [`docs/RaceLink_Host/developer-guide.md`](docs/RaceLink_Host/developer-guide.md) §"Adding a new scene-action kind" | reference/SCENE_FORMAT |
| **Adding a new wire opcode** | [`docs/RaceLink_Host/developer-guide.md`](docs/RaceLink_Host/developer-guide.md) §"Adding a new wire opcode" | host/docs/PROTOCOL |
| **Adding a new service** | [`docs/RaceLink_Host/developer-guide.md`](docs/RaceLink_Host/developer-guide.md) §"Adding a new service" | host/ARCHITECTURE |
| **Adding a task-manager workflow** | [`docs/RaceLink_Host/developer-guide.md`](docs/RaceLink_Host/developer-guide.md) §"Adding a new task-manager-driven workflow" | reference/SSE_CHANNELS |
| **WLED metadata regeneration** | [`docs/RaceLink_Host/developer-guide.md`](docs/RaceLink_Host/developer-guide.md) §"Regenerating WLED metadata" | wled/docs/effects-deterministic |
| **Updating deterministic-effects list** | [`docs/RaceLink_Host/developer-guide.md`](docs/RaceLink_Host/developer-guide.md) §"Updating the WLED-deterministic effects list" | wled/docs/effects-deterministic |
| **WebUI button vocabulary, toast/confirm conventions** | [`docs/RaceLink_Host/ui-conventions.md`](docs/RaceLink_Host/ui-conventions.md) | — |
| **Gateway hardware target / build flags** | [`docs/RaceLink_Gateway/README.md`](docs/RaceLink_Gateway/README.md) | — |
| **WLED build profiles** | [`docs/RaceLink_WLED/README.md`](docs/RaceLink_WLED/README.md) §"Supported hardware profiles" | — |
| **Deterministic effects audit (which effects sync)** | [`docs/concepts/deterministic-effects.md`](docs/concepts/deterministic-effects.md) | host/docs/OPERATOR_GUIDE §6a |
| **Scene file format** (`scenes.json`) | [`docs/reference/scene-format.md`](docs/reference/scene-format.md) | host/docs/OPERATOR_GUIDE |
| **Web API endpoints** | [`docs/reference/web-api.md`](docs/reference/web-api.md) (stub) | host/ARCHITECTURE §"Service Layer" |
| **SSE channels & state scopes** | [`docs/reference/sse-channels.md`](docs/reference/sse-channels.md) | host/ARCHITECTURE §"UI Scope Matrix" |
| **Versioning policy across components** | [`docs/versioning.md`](docs/versioning.md) | host/README §"Release artifacts" |
| **Contributing rules (PR, smoke tests, conventions)** | [`docs/contributing.md`](docs/contributing.md) | host/docs/DEVELOPER_GUIDE |
| **Troubleshooting index (operator)** | [`docs/troubleshooting.md`](docs/troubleshooting.md) | host/docs/OPERATOR_GUIDE |
| **Per-component licences** | [`docs/licenses.md`](docs/licenses.md) | — |
| **Changelog** | [`docs/changelog.md`](docs/changelog.md) | — |
| **RH plugin manifest dependency format (decision)** | [`docs/RaceLink_RH_Plugin/adr-0001-manifest-dependency.md`](docs/RaceLink_RH_Plugin/adr-0001-manifest-dependency.md) | rh-plugin/docs/manifest-dependency-format |
| **RH plugin release flow** | [`docs/RaceLink_RH_Plugin/release-playbook.md`](docs/RaceLink_RH_Plugin/release-playbook.md) | VERSIONING |
| **Development workflow (this repo)** | The contract is encoded directly in this `STRUCTURE.md` (the three tables below); maintainer-side workflow notes live under `_meta/contributor/` (local only, gitignored) | — |
| **Audit history (what was consolidated, what was harvested)** | [`docs/sources.md`](docs/sources.md) — public provenance ledger; full audit + harvest notes live under `_meta/maintainer/` (local only, gitignored) | — |

---

## Table 2 — Code change → Doc to update

For *"I just changed code in X, what docs need updating?"*. Code
paths are inside the matching component repository (e.g.
`RaceLink_Host/racelink/...`).

| If you change … | Update … |
|---|---|
| `racelink_proto.h` (any of the 3 byte-identical copies — Host, Gateway, WLED) | `docs/reference/wire-protocol.md` opcode table + body layout tables; `docs/glossary.md` if a new opcode/flag is named; `docs/RaceLink_Host/developer-guide.md` §"Adding a new wire opcode" if the *process* changed |
| `RaceLink_Host/racelink/protocol/{packets,codec,rules}.py` | `docs/reference/wire-protocol.md` (the rules table mirrors `rules.RULES`); cross-check that the body-builder doc matches `packets.build_*` |
| `RaceLink_Host/racelink/transport/{gateway_serial,framing}.py` | `docs/RaceLink_Host/architecture.md` §"Transport Interface" + §"Threading Model" if locks/condition variables change; `docs/reference/wire-protocol.md` §"USB framing" / §"Host ↔ Gateway flow control" |
| `RaceLink_Host/racelink/services/scenes_service.py` | `docs/reference/scene-format.md` (KIND_* enum, validator invariants); `docs/RaceLink_Host/developer-guide.md` §"Adding a new scene-action kind" if the checklist changes |
| `RaceLink_Host/racelink/services/scene_runner_service.py` | `docs/RaceLink_Host/developer-guide.md` §"Adding a new scene-action kind" (dispatch contract); if behaviour changes that an operator notices, `docs/RaceLink_Host/operator-guide.md` §"Run a scene" / §6a |
| `RaceLink_Host/racelink/services/scene_cost_estimator.py` | `docs/reference/scene-format.md` (cost contract); `docs/RaceLink_Host/operator-guide.md` §"Cost badge" |
| `RaceLink_Host/racelink/services/offset_dispatch_optimizer.py` | `docs/reference/wire-protocol.md` §"OPC_OFFSET" if wire strategy changes; `docs/RaceLink_Host/operator-guide.md` §6a if user-visible |
| `RaceLink_Host/racelink/services/control_service.py` | `docs/RaceLink_Host/architecture.md` §"Service Layer" row; `docs/contributing.md` §"Boolean send contract" if the contract is touched |
| `RaceLink_Host/racelink/services/gateway_service.py` | `docs/RaceLink_Host/architecture.md` §"Service Layer" + §"Threading Model" (auto-restore executor, reconnect, pending-request registry) |
| `RaceLink_Host/racelink/services/ota_service.py` / `ota_workflow_service.py` | `docs/RaceLink_Host/operator-guide.md` §"Firmware updates"; `docs/RaceLink_Host/developer-guide.md` §"WLED OTA gate matrix" |
| `RaceLink_Host/racelink/services/host_wifi_service.py` | `docs/RaceLink_Host/standalone-install.md` §"Linux first-time setup" |
| `RaceLink_Host/racelink/services/rl_presets_service.py` / `presets_service.py` | `docs/glossary.md` (Preset entry); `docs/RaceLink_Host/operator-guide.md` §"Author RL presets" |
| `RaceLink_Host/racelink/services/specials_service.py` | `docs/RaceLink_Host/operator-guide.md` §"Configure devices (Specials)" |
| `RaceLink_Host/racelink/services/discovery_service.py` / `status_service.py` | `docs/RaceLink_Host/operator-guide.md` §"Discover devices"; `docs/reference/web-api.md` |
| `RaceLink_Host/racelink/services/startblock_service.py` / `stream_service.py` | `docs/reference/wire-protocol.md` §"OPC_STREAM" if format changes; `docs/RaceLink_Host/operator-guide.md` if operator UI changes |
| `RaceLink_Host/racelink/state/repository.py` | `docs/RaceLink_Host/architecture.md` §"Threading Model" (the lock); `docs/contributing.md` §"Locking rule" |
| `RaceLink_Host/racelink/web/api.py` | `docs/reference/web-api.md` (route list, request/response shapes); `docs/RaceLink_Host/developer-guide.md` §"Adding a new service" route conventions |
| `RaceLink_Host/racelink/web/sse.py` / `racelink/domain/state_scope.py` | `docs/reference/sse-channels.md` (token map); `docs/RaceLink_Host/architecture.md` §"UI Scope Matrix" |
| `RaceLink_Host/racelink/web/tasks.py` / `request_helpers.py` | `docs/RaceLink_Host/developer-guide.md` §"Adding a task-manager-driven workflow" |
| `RaceLink_Host/racelink/domain/flags.py` | `docs/reference/wire-protocol.md` §"Flags byte"; `docs/glossary.md` |
| `RaceLink_Host/racelink/domain/wled_effects.py` / `wled_palettes.py` / `wled_palette_color_rules.py` | `docs/RaceLink_Host/developer-guide.md` §"Regenerating WLED metadata" — **these files are auto-generated; do not hand-edit, regenerate** |
| `RaceLink_Host/racelink/domain/wled_deterministic.py` | `docs/concepts/deterministic-effects.md`; `docs/RaceLink_Host/developer-guide.md` §"Updating the WLED-deterministic effects list" |
| `RaceLink_Host/racelink/domain/state_scope.py` | `docs/reference/sse-channels.md`; `docs/RaceLink_Host/architecture.md` §"UI Scope Matrix" |
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
| `RaceLink_WLED/usermods/racelink_wled/racelink_wled.{h,cpp}` | `docs/RaceLink_WLED/operator-setup.md`; `docs/concepts/deterministic-effects.md` if effect determinism changes |
| `RaceLink_WLED/build_profiles/*.platformio_override.ini` (new or changed) | `docs/RaceLink_WLED/README.md` §"Supported hardware profiles"; `docs/RaceLink_WLED/operator-setup.md` §"Default factory state" if defaults changed |
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
| `docs/sources.md` | (provenance ledger — no backing code) |
| `docs/RaceLink_Host/README.md` | `RaceLink_Host/racelink/__init__.py` (`__version__`); `RaceLink_Host/racelink/app.py`; `RaceLink_Host/racelink/web/__init__.py` |
| `docs/RaceLink_Host/architecture.md` | `RaceLink_Host/racelink/app.py`, `controller.py`, `racelink/services/*.py`, `racelink/state/repository.py`, `racelink/web/sse.py`, `racelink/transport/gateway_serial.py` |
| `docs/RaceLink_Host/operator-guide.md` | (operator-facing aggregator, no single backing file; section §6a backed by `racelink/services/scene_runner_service.py` + WLED usermod) |
| `docs/RaceLink_Host/developer-guide.md` | `RaceLink_Host/racelink/services/scenes_service.py`, `racelink/services/scene_runner_service.py`, `racelink/services/scene_cost_estimator.py`; `RaceLink_Host/racelink_proto.h`; `RaceLink_Host/gen_wled_metadata.py` and `racelink/domain/wled_*.py`; `RaceLink_Host/racelink/services/ota_service.py` |
| `docs/reference/wire-protocol.md` | **canonical: `RaceLink_Host/racelink_proto.h`** (mirrored in Gateway + WLED). Helpers: `racelink/protocol/{packets,codec,rules}.py`, `racelink/transport/framing.py`, `racelink/racelink_proto_auto.py`, `gen_racelink_proto_py.py`, `tests/test_proto_header_drift.py` |
| `docs/concepts/opcodes.md` | `racelink/services/control_service.py`, `scene_runner_service.py`, `offset_dispatch_optimizer.py`, `sync_service.py`; firmware `racelink_wled.cpp` (`handleControl`, `handleSync`, `serviceDeferredApply`, `applyPhaseOffsetToTimebase`); `racelink_proto.h` for the wire spec |
| `docs/RaceLink_Host/webui-guide.md` | `racelink/static/racelink.js`, `scenes.js`; `racelink/pages/*.html`; `racelink/web/sse.py`, `tasks.py`, `api.py` |
| `docs/RaceLink_Host/ui-conventions.md` | `RaceLink_Host/racelink/static/racelink.js` (`showToast`, `confirmDestructive`, `setBusy`); `racelink/static/scenes.js`; `racelink/pages/*.html` |
| `docs/RaceLink_Host/standalone-install.md` | `RaceLink_Host/racelink/integrations/standalone/`; `RaceLink_Host/scripts/setup_nmcli_polkit.sh`; the `racelink-standalone` and `racelink-setup-nmcli` console-script entry points in `pyproject.toml` |
| `docs/RaceLink_Gateway/README.md` | `RaceLink_Gateway/src/main.cpp`, `racelink_transport_core.h`, `platformio.ini` |
| `docs/RaceLink_Gateway/operator-setup.md` | (operator aggregator; OLED behaviour from `RaceLink_Gateway/src/main.cpp`) |
| `docs/RaceLink_WLED/README.md` | `RaceLink_WLED/build_profiles/*.platformio_override.ini`; `RaceLink_WLED/.github/workflows/release.yml`; `RaceLink_WLED/version.json` |
| `docs/RaceLink_WLED/operator-setup.md` | `RaceLink_WLED/usermods/racelink_wled/racelink_wled.{h,cpp}` (factory state, pairing) |
| `docs/concepts/deterministic-effects.md` | upstream WLED `wled00/FX.cpp` per-effect; `RaceLink_Host/racelink/domain/wled_deterministic.py` (the host-side audited set) |
| `docs/RaceLink_RH_Plugin/README.md` | `RaceLink_RH_Plugin/custom_plugins/racelink_rh_plugin/manifest.json`; `pyproject.toml` |
| `docs/RaceLink_RH_Plugin/operator-setup.md` | `RaceLink_RH_Plugin/custom_plugins/racelink_rh_plugin/plugin/ui.py`; `actions.py`; `bootstrap.py` |
| `docs/RaceLink_RH_Plugin/manifest-dependency-format.md` | `RaceLink_RH_Plugin/custom_plugins/racelink_rh_plugin/manifest.json`; `RaceLink_RH_Plugin/scripts/verify_manifest_dependency_formats.py`; the `rhfest-action` it validates against |
| `docs/RaceLink_RH_Plugin/release-playbook.md` | `RaceLi
