# RaceLink Architecture

## Repository Scope

`RaceLink_Host` now contains only the host-owned parts of the system:

- core runtime wiring
- transport, protocol, state, and service layers
- the shared RaceLink WebUI
- standalone Flask hosting

RotorHazard-specific adapter code is no longer part of this repository. That adapter belongs in the separate `RaceLink_RH-plugin` repository.

## Stable Host Entry Points

External adapters should depend on the host through these stable entry points:

- `racelink.app.create_runtime(...)`
- `racelink.web.register_racelink_web(...)`

This keeps plugin repositories from reaching deeply into host internals.

## Package Layout

- `racelink/app.py`
  Runtime container and host-owned runtime factory.
- `racelink/core/`
  Cross-cutting contracts and null source/sink defaults.
- `racelink/domain/`
  Device models, metadata, and specials helpers.
- `racelink/protocol/`
  Protocol constants, rule helpers, and packet support.
- `racelink/transport/`
  Serial gateway transport and framing.
- `racelink/state/`
  Runtime repositories and persistence helpers.
- `racelink/services/`
  Host business workflows.
- `racelink/web/`
  Shared RaceLink WebUI registration, API, SSE, DTOs, and task state.
- `racelink/integrations/standalone/`
  Canonical standalone Flask bootstrap using the same host runtime and WebUI.
- `pages/` and `static/`
  Shared RaceLink WebUI assets that remain in the host repository.

## WebUI Hosting Model

There is one RaceLink WebUI.

- In standalone mode, the standalone Flask app mounts that UI through `register_racelink_web(...)`.
- In RotorHazard mode, the external adapter plugin is expected to mount that same UI through the same host-owned registration entry.
- The packaged standalone user entrypoint is `racelink-standalone`, which boots the host-owned standalone integration under `racelink.integrations.standalone`.

`pages/` and `static/` stay in the host repository so both hosting modes use the same UI implementation.

## Layer Boundaries

- `domain` stays framework-agnostic.
- `protocol` and `transport` do not depend on web-hosting concerns.
- `state` owns repositories and persistence.
- `services` implement host workflows and should not depend on external adapters.
- `web` adapts HTTP and SSE traffic to host services.
- `integrations/standalone` depends inward on host modules and does not define separate UI behavior.

## Service Layer

The host's business logic is split across the modules below. Each
service has a 5–15 line module docstring (`racelink/services/*.py`)
that names its public API, dependencies, and threading expectations.
This table is the at-a-glance index; open the file for the contract.

| Module | Owns | Called from |
|---|---|---|
| `gateway_service` | Pending-request registry, TX/RX listener wiring, reconnect lifecycle, auto-restore worker pool, high-level dispatch (`send_config` / `send_sync` / `send_stream` / `send_and_wait_for_reply`) | Everything that talks to the gateway |
| `control_service` | OPC_PRESET / OPC_CONTROL builders, return-value contract (`bool` for every `send_*`), per-group cache update | Web routes, scene runner, RotorHazard adapter |
| `config_service` | Post-ACK application of OPC_CONFIG changes (state mutation after the gateway confirms) | RX-thread ACK handler via `controller._apply_config_update` |
| `sync_service` | Thin wrapper for OPC_SYNC broadcast | Scene runner |
| `discovery_service` | OPC_DEVICES broadcast + reply collection | Web `/api/discover`, task manager |
| `status_service` | OPC_STATUS poll + reply reconciliation | Web `/api/status`, task manager |
| `stream_service` | OPC_STREAM payload submission | Startblock service |
| `startblock_service` | Startblock-program payload assembly + dispatch | Web `/api/specials/*`, scene runner |
| `specials_service` | Per-capability device option metadata | Web editor schema, options dialog |
| `presets_service` | WLED `presets.json` file store + minimal parser | OTA workflow, web `/api/presets/*` |
| `rl_presets_service` | RaceLink-native preset store (CRUD, persistence) | Web, scene runner, scene cost estimator |
| `ota_service` | File staging + WLED HTTP transfer (low-level) | OTA workflow |
| `ota_workflow_service` | Multi-step firmware-update / presets-download orchestration | Web `/api/fw/start`, `/api/presets/download` |
| `host_wifi_service` | NetworkManager `nmcli` wrapper for OTA | OTA workflow |
| `pending_requests` | `PendingRequestRegistry` for unicast match-and-set on the RX path | `gateway_service` |
| `scenes_service` | Scene store (CRUD + canonical validator + legacy migration shim) | Web, scene runner |
| `scene_runner_service` | Sequential dispatcher for scenes, including offset_group container expansion | Web `/api/scenes/<key>/run`, RotorHazard quickset |
| `scene_cost_estimator` | Predicted wire cost (packets, bytes, airtime) for a scene before it runs | Web `/api/scenes/<key>/estimate`, web editor |
| `offset_dispatch_optimizer` | Wire-path planner for `offset_group` actions (formula vs explicit vs broadcast+overrides) | Scene runner, cost estimator |

`controller.py` is the historical "RaceLink_Host" class that all
services attach to. New work generally adds a service module rather
than extending the controller; the controller's role has shrunk to
"composition root + a handful of lifecycle methods + two
`_pending_*` state slots that bridge the TX↔RX threads".

## Threading Model

The host is multithreaded by necessity: the serial RX reader can't
block on web requests, the scene runner has to fire from its own
thread so a Run doesn't block the SSE stream, and OTA workflows run
in task-manager threads so the WebUI stays responsive during a
multi-minute firmware roll-out.

### Threads in a running host

| Thread name (`rl-…` prefix) | Owner | Lifetime |
|---|---|---|
| Main / web request threads | Flask / WSGI server | Per-request |
| `rl-serial-rx-<port>` | `GatewaySerialTransport._reader` | Lives for the duration of one transport session; replaced on reconnect |
| `rl-task-<name>` | `TaskManager` | Per task (discover / status / fwupdate / presets_download) |
| `rl-reconnect` | `GatewayService.schedule_reconnect` | Per reconnect attempt |
| `rl-gateway-retry` | `controller._gateway_retry_timer` | Per scheduled auto-retry; `Timer` subclass |
| `rl-auto-restore-N` | `GatewayService._auto_restore_executor` (`ThreadPoolExecutor`, max_workers=8) | Pool, threads reused; idle pool holds 0 active |
| Scene runner (anonymous) | `SceneRunnerService.run` | Per scene run |
| SSE generator threads | `SSEBridge.gen()` | One per connected SSE client |
| gevent monkey-patched workers (when running under gunicorn-gevent) | gevent | One per request hub |

### Locks

| Lock | Module | Protects |
|---|---|---|
| `state_repository.lock` (RLock) | `racelink/state/repository.py` | Device + group repository mutations and iterations. Reentrant so a save-path that walks the device list can be called from another locked path without deadlocking. **Critical rule: never held across RF I/O — see "Locking Rule" section below.** |
| `_tx_lock` (Lock) + `_tx_done_cv` (Condition) | `transport/gateway_serial.py` | Concurrency fix. Serializes USB writes so concurrent senders cannot interleave bytes mid-frame; the Condition's predicate (`_tx_in_flight`) is the lost-wakeup-safe replacement for the previous `Event.wait` + `Event.clear` pair. |
| `_pending_config_lock` (Lock) | `controller.py` | Concurrency fix. Pairs `stash_pending_config` (TX path) with `take_pending_config` (RX path) atomically. Distinct from `state_repository.lock` so a slow ConfigService callback can't delay TX-side stashes. |
| `_pending_expect_lock` (Lock) | `controller.py` | Concurrency fix. Pairs `set_pending_expect` (TX path) with `read_pending_expect` + `clear_pending_expect_if` (RX path) — the `_if` variant is compare-and-clear semantics so a stale RX matcher cannot wipe a freshly-stamped TX expectation. |
| `_clients_lock` (gevent Semaphore by default, threading.Lock fallback) | `web/sse.py` | Concurrency fix. Snapshot-then-fan-out for `broadcast` so a slow client queue doesn't starve other broadcasters or new SSE registrations. |
| `_auto_reassign_lock` (Lock) | `services/gateway_service.py` | The auto-reassign-recently-seen cache + the in-flight futures list for the auto-restore executor. |

`gevent.lock.Semaphore` is used by `web/sse.py` only when the host
runs under gevent (gunicorn -k gevent). Standalone Flask falls back
to `threading.Lock` automatically. The fallback chain is in
[racelink/web/sse.py](racelink/web/sse.py#L14-L26).

### Atomicity guarantees

| Operation | Atomic with respect to | Notes |
|---|---|---|
| `_send_m2n` USB write | Concurrent senders | full body of `_send_m2n` runs under `_tx_lock`. Listener fan-out (`_emit_tx`) happens *outside* the lock so a slow TX listener cannot stall subsequent senders. |
| Gateway TX-DONE acknowledgement | The matching `_tx_in_flight = True` flip | the RX reader's `_tx_lock` acquisition guarantees it observes the flag set by the TX thread that wrote the matching frame. |
| `_pending_config` stash + pop | Cross-thread mutations of the dict |  |
| `_pending_expect` set + clear | Cross-thread restamps + matches | compare-and-clear via `clear_pending_expect_if`. |
| Device-repo iteration in the cache update + send_stream paths | Concurrent appends / removals | `with state_repository.lock:` wraps the iteration; the inner work (or the snapshot built inside) is what runs lock-free. |

### Shutdown

`RaceLink_Host.shutdown()` is the canonical teardown path. In order:

1. Cancel the gateway-retry timer (`_cancel_gateway_retry`).
2. Close the transport (`transport.close()` → joins the RX thread, closes the serial port).
3. Cancel the task manager.
4. Persist final state (`save_to_db(scopes={NONE})`).
5. Shutdown the auto-restore executor (`gateway_service.shutdown()` → `executor.shutdown(wait=False, cancel_futures=True)`).

Daemon threads not explicitly shut down (SSE generators, etc.) are
torn down by Python's exit. Steps 1–5 cover the threads that hold
file descriptors or in-flight RF state.

### Audit trail

The detailed reasoning and regression tests behind each threading
fix live in the maintainer's internal engineering ledger and are
not part of this public consolidation. New threading contributions
should land regression tests in
`tests/test_state_concurrency.py` or
`tests/test_transport_tx_barrier.py` matching the existing pattern.

## Documentation map

Other user-facing and contributor-facing docs in this repo:

| File | Audience | Content |
|---|---|---|
| [`operator-guide.md`](operator-guide.md) | Operators setting up a race | Glossary, end-to-end workflow, safety rules |
| [`developer-guide.md`](developer-guide.md) | Contributors adding a feature | Checklists for action kinds, opcodes, services |
| [`ui-conventions.md`](ui-conventions.md) | Contributors writing WebUI | Button vocabulary, toast / confirm conventions |
| [`reference/wire-protocol.md`](../reference/wire-protocol.md) | Anyone reading wire traces | Wire format reference (M2N/N2M, opcodes, body layouts) |
| [`standalone-install.md`](standalone-install.md) | Standalone-host operators | Install + run instructions |
| §"Repo Split History" (below) | Contributors crossing repos | Where Host / Gateway / WLED / RH-plugin code lives |

## Current Notes

- `controller.py` remains a compatibility-oriented host controller, but it now only coordinates host runtime behavior.
- Standalone support continues to use the shared WebUI and host services.
- `pages/` and `static/` are intentionally retained here and are not plugin leftovers.

## Gateway Ownership

Only **one** process must hold the USB-serial connection to the RaceLink_Gateway dongle at a time. The host enforces this by opening the port with `exclusive=True` in `racelink/transport/gateway_serial.py`.

Ownership rules:

- **Standalone mode** (`racelink-standalone`): the host owns the gateway for the lifetime of the Flask app. `run_standalone()` calls `onStartup({})` which triggers `discoverPort({})`.
- **RotorHazard plugin mode**: the plugin owns the gateway. RotorHazard itself does **not** open the dongle. When the plugin's `initialize()` runs, the Host's `onStartup` is wired to `Evt.STARTUP`; `discoverPort` then claims the port.
- **Never run both simultaneously** against the same dongle. The second process will see `serial.SerialException` from the exclusive lock and log it via `_record_gateway_error`; the UI banner  surfaces this to the operator.
- **Release on shutdown**: `RaceLink_Host.shutdown()`  calls `transport.close()` so the port is released before the process exits. The plugin registers this on `Evt.SHUTDOWN` where available.

If you ever need to share a gateway between processes (e.g. dev tooling + live host), serialize access at the process level -- there is no in-transport multiplexing today.

## Transport Interface (post-redesign)

The Gateway firmware keeps the SX1262 in **Continuous RX** as its default state. After each TX the Core reverts to Continuous automatically; no Timed-RX window is opened for unicast request/response flows. This was the original cause of the "No ACK_OK for ..." timeout-despite-ACK bug: the Host used to block until the firmware's `EV_RX_WINDOW_CLOSED` event arrived, but that event can be delayed by ESP32 USB CDC buffering.

Host-side matching is therefore owned entirely by `racelink/services/pending_requests.py` and the two entry points in `GatewayService`:

| Call pattern | Helper | Completion signal |
|---|---|---|
| Unicast request → single ACK or specific reply | `send_and_wait_for_reply` | `PendingRequestRegistry` matches `(sender, ack_of_or_opc)` and sets the per-request event |
| Broadcast / group → N replies within a window | `send_and_collect` | Host wall clock (`duration_s`) with early-exit on `expected` count |

The old `wait_rx_window` helper remains for backwards compatibility but is deprecated. New code should not call it.

`EV_RX_WINDOW_OPEN` / `EV_RX_WINDOW_CLOSED` stay in the wire format (the Core header is frozen) but are debug-only from the Host's perspective.

## Locking Rule: Never hold `state_repository.lock` across RF I/O

The state-repository lock (`state_repository.lock`, surfaced as `ctx.rl_lock` in the web layer) is taken by:

1. **Web handlers** that read/mutate device or group state.
2. **The gateway reader thread**, inside `GatewayService.handle_ack_event`, `on_transport_event` (status/identify branches), and `pending_*` bookkeeping.

Both paths must acquire the **same** lock so a request thread and the reader thread see a consistent view of the device list. That is the whole point of a single state lock .

Consequence: **a handler that holds the state lock while waiting for a reply over RF will deadlock the reader**. The reader thread stalls in `handle_ack_event` for the reply that just arrived -- and because it is stalled, it cannot pull the *next* USB frame out of pyserial's RX buffer. USB frames for subsequent devices queue up; the next `send_and_wait_for_reply` times out even though the ACK is sitting unread in the OS buffer. Symptoms:

- First unicast call in a bulk returns promptly.
- Every subsequent unicast call in the same bulk times out at exactly the wait budget (e.g. 8.000 s).
- Immediately after the timeout releases the lock, a flood of queued USB events drains into the log (TX\_DONE, RX window OPEN, late ACK).

The rule, therefore, is:

> **Never call `setNodeGroupId`, `sendConfig(..., wait_for_ack=True)`, `sendRaceLink`, `sendGroupPreset`, `send_stream`, `discover_devices`, or `get_status` while holding `state_repository.lock` / `ctx.rl_lock`.**

In practice this means bulk loops must release and re-acquire the lock around each iteration's RF call. See `_apply_device_meta_updates` in `racelink/web/api.py` for the reference pattern (acquire → read/mutate in-memory → release → blocking RF → repeat).

A regression test (`tests/test_web_handler_helpers.py::ApplyDeviceMetaUpdatesDoesNotHoldLockAcrossBlockingIO`) exercises this rule by simulating a second thread that must acquire the lock mid-bulk.

## UI Scope Matrix

State mutations travel to the UI layer via two paths: the in-process RotorHazard UI (through `on_persistence_changed` → `RotorHazardUIAdapter.apply_scoped_update`) and the browser WebUI (through the SSE `refresh` channel mapped by `racelink/domain/state_scope.sse_what_from_scopes`). Both consume the same scope tokens so that a single `save_to_db(scopes=...)` call fans out consistently.

**Authoritative scope tokens** are defined in [racelink/domain/state_scope.py](racelink/domain/state_scope.py):

| Token | When to use |
|---|---|
| `FULL` | Initial load (`load_from_db`) or migration boot -- rebuild everything. |
| `NONE` | Pure persistence, no visible change (e.g. "Save Configuration" button just flushes the combined key). |
| `DEVICES` | Device record changed that does not move it between groups (rename, specials struct rebuild). |
| `DEVICE_MEMBERSHIP` | Device moved to a different group -- affects group counts and any list embedded per group. |
| `DEVICE_SPECIALS` | A special config byte was written on a single device (startblock slot, etc.). No cross-UI effect on the RH panels. |
| `GROUPS` | Groups added / renamed / removed -- group-list-backed dropdowns must refresh. |
| `PRESETS` | WLED presets file or RL preset store reloaded -- preset-list-backed selects must refresh. |

**RotorHazard adapter (`custom_plugins/racelink_rh_plugin/plugin/ui.py`)** reacts as follows. Elements in the "Once" column are bootstrapped on first sync and then guarded by the `_settings_panel_bootstrapped` / `_quickset_panel_bootstrapped` flags; calling `sync_rotorhazard_ui` repeatedly therefore no longer produces `RHUI Redefining ...` log spam.

| RH UI element | Once (bootstrap) | GROUPS | DEVICES | DEVICE_MEMBERSHIP | DEVICE_SPECIALS | PRESETS |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Panel `rl_settings` | ✓ | | | | | |
| Panel `rl_quickset` | ✓ | | | | | |
| Option `rl_device_config` | ✓ | | | | | |
| Option `rl_groups_config` | ✓ | | | | | |
| Option `rl_assignToNewGroup` | ✓ | | | | | |
| Quickbutton `rl_btn_set_defaults` | ✓ | | | | | |
| Quickbutton `rl_btn_force_groups` | ✓ | | | | | |
| Quickbutton `rl_btn_get_devices` | ✓ | | | | | |
| Quickbutton `rl_run_autodetect` | ✓ | | | | | |
| Option `rl_quickset_brightness` | ✓ | | | | | |
| Quickbutton `run_quickset` | ✓ | | | | | |
| Option `rl_assignToGroup` (dynamic) | | ✓ | | | | |
| Option `rl_quickset_group` (dynamic) | | ✓ | | | | |
| Option `rl_quickset_preset` (dynamic) | | | | | | ✓ |
| Default `ActionEffect` `gcaction` | | ✓ | | | | ✓ |
| Per-capability special `ActionEffect`s | | ✓ | ✓ | ✓ | | ✓ |

**SSE topics (`racelink/domain/state_scope.sse_what_from_scopes`)** drive the browser WebUI:

| Token | SSE `refresh.what` payload | JS handler action |
|---|---|---|
| `FULL` | `["groups", "devices"]` | `loadGroups()` + `loadDevices()` |
| `NONE` | `[]` | no-op |
| `DEVICES` | `["devices"]` | `loadDevices()` |
| `DEVICE_MEMBERSHIP` | `["devices", "groups"]` | both (membership affects per-group counts) |
| `DEVICE_SPECIALS` | `["devices"]` | `loadDevices()` |
| `GROUPS` | `["groups"]` | `loadGroups()` |
| `PRESETS` | `["presets"]` | preset dropdown refresh |

**Rule of thumb for new call sites.** When you call `save_to_db(args, scopes=...)`, pick the narrowest token set describing what actually changed. If you genuinely don't know, pass `{FULL}` -- but prefer to refactor so you do know. The RH adapter and SSE scope map are both designed around this precision, and the regression tests in `tests/test_ui_scope_routing.py` (plugin) and `tests/test_state_scope.py` (host) pin the mapping so an accidental FULL-regression surfaces in CI.

## Repo Split History

This section folds in the content of the former `docs/repo_split_map.md`
(retained in the source repository) for completeness.

### Host-Owned Import Edge

These entry points stay in `RaceLink_Host` and are the supported
surface for external adapters:

- `racelink.app:create_runtime`
- `racelink.web:register_racelink_web`
- `racelink.web:RaceLinkWebRuntime`

### Already moved out of Host

The following paths used to live in this repository and now belong in
the separate `RaceLink_RH-plugin` repository:

| Previous Host path | Target in plugin repo | Note |
|---|---|---|
| `__init__.py` | plugin repo root `__init__.py` | RotorHazard loader shim now belongs with the plugin |
| `racelink/integrations/rotorhazard/__init__.py` | `racelink_rh_plugin/integrations/rotorhazard/__init__.py` | Plugin package edge |
| `racelink/integrations/rotorhazard/plugin.py` | `racelink_rh_plugin/integrations/rotorhazard/plugin.py` | Adapter bootstrap for RH |
| `racelink/integrations/rotorhazard/ui.py` | `racelink_rh_plugin/integrations/rotorhazard/ui.py` | RotorHazard UI adapter |
| `racelink/integrations/rotorhazard/actions.py` | `racelink_rh_plugin/integrations/rotorhazard/actions.py` | RH action registration |
| `racelink/integrations/rotorhazard/dataio.py` | `racelink_rh_plugin/integrations/rotorhazard/dataio.py` | RH import/export adapter |
| `racelink/integrations/rotorhazard/source.py` | `racelink_rh_plugin/integrations/rotorhazard/source.py` | RH event source adapter |

### Files that stay in Host

| Host path | Why it stays |
|---|---|
| `racelink/app.py` | Owns the host runtime factory and service wiring |
| `racelink/web/**` | Owns the shared RaceLink WebUI registration, API, SSE, task state |
| `racelink/integrations/standalone/**` | Hosts the standalone Flask mode |
| `racelink/pages/**` and `racelink/static/**` | Shared RaceLink WebUI assets for all hosting modes |
| `controller.py` | Host controller and runtime coordinator |
