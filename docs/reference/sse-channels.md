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
data: {
  "name": "fwupdate",
  "state": "running",
  "meta": {
    "stage": "UPLOAD_FW",
    "index": 3, "total": 8,
    "addr": "AABBCC",
    "macs": ["AABBCC", "DDEEFF", "112233", ...],
    "deviceState": {
      "AABBCC": "running",
      "DDEEFF": "ok",
      "112233": "queued"
    }
  }
}
```

| Event | Payload | Purpose |
|---|---|---|
| `refresh` | `{"what": [...]}` — list of refresh tokens | Tell the JS to reload some part of its model from the REST API. |
| `task` | `{"name", "state", "meta": {...}, ...}` | Long-running task progress (Discover, Status poll, OTA, presets download). The frontend's `updateTask` dispatches by `name`. The `fwupdate` task's `meta` additionally carries `macs[]` (planned targets, captured at Start) and `deviceState` (per-device row state map) — see [`web-api.md` `POST /api/fw/start`](web-api.md#post-apifwstart) for the full shape and §9 in `frontend/POST_MIGRATION_CLEANUP.md` for the rationale. |

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
| `presets` | `PRESETS` (legacy alias — see note below) | Refresh classical-WLED preset dropdowns |
| `rl_presets` | `RL_PRESETS` | Refresh RL-preset list + schema; cascade to Specials so the `rl_preset` preset picker refreshes |
| `wled_presets` | `WLED_PRESETS` | Refresh WLED preset file registry; cascade to Specials so the `wled_preset` dropdown refreshes |
| `scenes` | `SCENES` | `loadScenes()` — refetch the scenes list |

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
| `PRESETS` | Legacy alias — historically covered both classical WLED presets and RL presets. Kept for backwards compatibility; new call sites should pick `WLED_PRESETS` or `RL_PRESETS` directly. Slated for collapse with the §2 terminology rename. |
| `RL_PRESETS` | RaceLink-native preset CRUD (the 14-field `OPC_CONTROL` parameter snapshots). Triggered by `/api/rl-presets/*` mutating routes. |
| `WLED_PRESETS` | Classical `presets.json` upload / select / download. Triggered synchronously by `/api/presets/upload` and `/api/presets/select`; for `/api/presets/download` the broadcast fires from inside the task thread once the file lands on disk (workflow success path). |
| `SCENES` | Scene CRUD — scene list / individual scene record changed. |

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

## Connection lifecycle and Chrome HTTP/1.1 slot pool

Browser-driven SSE connections share the same per-origin connection
pool as the rest of the page. Chrome (and Chromium-based browsers)
limit that pool to **6 sockets per origin** under HTTP/1.1. Each
open EventSource consumes one slot for the duration of the stream.
A `text/event-stream` response never terminates regularly, which
makes the lifecycle of those sockets tricky around page navigation.

**The failure mode the host guards against.** When the operator
clicks an in-page link (e.g. *Scenes* on `/racelink/`, or
*← Devices* on `/racelink/scenes`) instead of pressing F5, Chrome
runs the unload sequence "gracefully": it closes the JS
`EventSource` object but parks the underlying TCP socket in a
half-finished state inside its connection pool because the
response stream is still open from the server's perspective. The
server's `gen()` loop has no way to find out that the peer is
gone — `yield`ing 7-byte ping frames into a kernel send buffer
that has 64 KB of headroom won't surface a `BrokenPipeError` for
hours. Meanwhile Chrome counts the half-finished socket against
its 6-slot budget. After ~5 quick page switches, the pool is full
and the next batch of API requests stalls until something gives —
typical observed wait was 20–47 seconds before the fix.

**The host's three-layer mitigation:**

1. **Client-side explicit `pagehide` close.** `racelink/static/racelink.js`
   registers a `pagehide` listener that calls `_es.close()` on the
   active `EventSource` before the page actually unloads. This
   forces the browser to release the underlying socket synchronously
   instead of relying on the implicit, deferred unload-time cleanup.
   `pagehide` (rather than `beforeunload`) is the correct hook —
   it runs while JS is still alive and is bfcache-aware, so a tab
   restored from the back/forward cache simply re-opens an
   `EventSource` on its own normal page-load path.
2. **Short server-side ping cadence.** `gen()` in `racelink/web/sse.py`
   ticks every **2 s** (was 15 s) so that, in the rare cases where
   the client *does* drop without our explicit close path running
   (browser crash, hard kill, network drop), the next yield runs
   often enough that a kernel-level `BrokenPipeError` will be
   observed within seconds. Cost: ~7 B every 2 s per active tab —
   negligible.
3. **`Connection: close` on the SSE response.** Tells Chrome that
   the socket may not be retained in the keep-alive pool after the
   stream ends. Defense in depth — irrelevant on the happy path
   (where (1) closes the socket cleanly anyway), but it nudges
   Chrome's connection-pool accounting toward "release this slot"
   on edge cases.

**Why F5 was always fine.** A browser reload tears down the JS
context and the underlying network stack hard — Chrome typically
ends up sending a TCP `RST` on the SSE socket, which causes the
server's next yield to fail immediately and the slot to release.
The graceful-FIN path that link-click takes was the one that
needed help.

**Firefox is unaffected.** Its connection pool semantics around
EventSource lifecycle are different; the original 15 s ping was
sufficient there. Both browsers continue to work under the new
configuration.

## See also

* [`../RaceLink_Host/architecture.md`](../RaceLink_Host/architecture.md) §"UI Scope
  Matrix" — full per-element matrix.
* [`../RaceLink_Host/ui-conventions.md`](../RaceLink_Host/ui-conventions.md) —
  button vocabulary and toast / confirm conventions.
* [`WEB_API.md`](web-api.md) — the REST endpoints that
  `loadGroups()` / `loadDevices()` / preset refresh actually call.
