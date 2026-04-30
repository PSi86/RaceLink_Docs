# SSE Channels & State Scopes

Reference for the host's Server-Sent-Events (SSE) channel and the
state-scope token system that drives selective UI updates.

> **Source of truth.** `racelink/web/sse.py` and
> `racelink/domain/state_scope.py`. This document is the readable
> summary distilled from
> [`../RaceLink_Host/architecture.md`](../RaceLink_Host/architecture.md) §"UI Scope
> Matrix".

## Channel

A single SSE endpoint at:

```
GET /racelink/sse
Accept: text/event-stream
```

The client subscribes once on page load. The host pushes events as
they happen — there is no client-driven polling.

## Event types

```
event: refresh
data: {"what": ["devices", "groups"]}

event: task
data: {"name": "fwupdate", "stage": "UPLOAD_FW", "index": 3, "total": 8, "addr": "AABBCC"}
```

| Event | Payload | Purpose |
|---|---|---|
| `refresh` | `{"what": [...]}` — list of refresh tokens | Tell the JS to reload some part of its model from the REST API. |
| `task` | `{"name", "stage", "message", "index", "total", "addr", ...}` | Long-running task progress (Discover, Status poll, OTA, presets download). The frontend's `updateTask` dispatches by `name`. |

The two event types are independent — a long-running task can
update its `task` event many times without firing any `refresh`
event, and vice versa.

## Refresh tokens (`refresh.what` payload)

The list inside `refresh.what` tells the frontend which API
calls to re-issue. Tokens are derived from state-scope tokens via
`racelink/domain/state_scope.sse_what_from_scopes`:

| Refresh token | Triggered by state-scope token | JS handler action |
|---|---|---|
| `groups` | `GROUPS`, `DEVICE_MEMBERSHIP`, `FULL` | `loadGroups()` — refetch group list |
| `devices` | `DEVICES`, `DEVICE_MEMBERSHIP`, `DEVICE_SPECIALS`, `FULL` | `loadDevices()` — refetch device list |
| `presets` | `PRESETS` | Refresh preset dropdowns |

The `NONE` scope produces an empty list — no tokens fire,
suppressing any visible refresh.

## State-scope tokens

`racelink/domain/state_scope.py` defines the token set. Every
`save_to_db(scopes={...})` call carries one or more of these:

| Token | When to use |
|---|---|
| `FULL` | Initial load (`load_from_db`) or migration boot — rebuild everything. |
| `NONE` | Pure persistence, no visible change (e.g. "Save Configuration" button just flushes the combined key). |
| `DEVICES` | A device record changed but the device did not move between groups (rename, specials struct rebuild). |
| `DEVICE_MEMBERSHIP` | A device moved to a different group — affects group counts and any list embedded per group. |
| `DEVICE_SPECIALS` | A special config byte was written on a single device (startblock slot, etc.). No cross-UI effect on RH panels. |
| `GROUPS` | Groups added / renamed / removed — group-list-backed dropdowns must refresh. |
| `PRESETS` | WLED presets file or RL preset store reloaded — preset-list-backed selects must refresh. |

## Two consumers — same scope token

The state-scope tokens drive **two** independent UI layers:

1. **The browser WebUI.** Routed via the `refresh` SSE event;
   tokens map through `sse_what_from_scopes` to refresh tokens
   (table above).
2. **The RotorHazard plugin.** Routed via the `on_persistence_changed`
   callback into `RotorHazardUIAdapter.apply_scoped_update`. The
   plugin's UI elements are bootstrapped once and then
   selectively re-registered per scope token. See
   [`../RaceLink_Host/architecture.md`](../RaceLink_Host/architecture.md) §"UI Scope
   Matrix" for the full per-element table.

Both consumers receive the same scope token set on every state
change. The dual fan-out is what makes the Host ↔ RotorHazard
plugin layout's UI-update story consistent.

## Rule of thumb for new call sites

When you call `save_to_db(args, scopes=...)`, pick the **narrowest**
token set describing what actually changed. If you genuinely don't
know, pass `{FULL}` — but prefer to refactor so you do know.

The regression tests pin the scope mapping:

* `tests/test_state_scope.py` (host) — pins token → SSE refresh
  token mapping.
* `tests/test_ui_scope_routing.py` (plugin) — pins token →
  RotorHazard panel-element refresh.

An accidental `FULL` regression in either codebase fails CI.

## Concurrency

`SSEBridge.broadcast` is the fan-out. It snapshots the registered
clients under `_clients_lock` (a `gevent.lock.Semaphore` when
running under gevent, `threading.Lock` otherwise) and then puts
into each client's queue **outside** the lock. A previous fix
established this snapshot-then-fan-out pattern so a slow client
queue cannot starve other broadcasters or new SSE registrations.

If you need to broadcast from a non-request thread (e.g. the
gateway reader thread), call `SSEBridge.broadcast` directly — it
is thread-safe.

## See also

* [`../RaceLink_Host/architecture.md`](../RaceLink_Host/architecture.md) §"UI Scope
  Matrix" — full per-element matrix.
* [`../RaceLink_Host/ui-conventions.md`](../RaceLink_Host/ui-conventions.md) —
  button vocabulary and toast / confirm conventions.
* [`WEB_API.md`](web-api.md) — the REST endpoints that
  `loadGroups()` / `loadDevices()` / preset refresh actually call.
