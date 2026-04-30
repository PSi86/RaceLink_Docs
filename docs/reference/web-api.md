# Web API Reference

The host exposes a JSON HTTP API that the WebUI and the RotorHazard
plugin call. Everything is mounted under the WebUI's prefix (default
`/racelink`):

```text
http://<host>:5077/racelink/api/...     (standalone)
http://<host>:5000/racelink/api/...     (RotorHazard plugin, default port)
```

For the SSE channel and state-scope tokens that complement these
endpoints, see [SSE channels](sse-channels.md). For the wire-format
constants (`OPC_*`, flags byte, P_Config option codes) referenced
below, see [Wire protocol](wire-protocol.md).

> **Source.** Everything in this page is derived from
> `RaceLink_Host/racelink/web/api.py`,
> `RaceLink_Host/racelink/web/blueprint.py`,
> `RaceLink_Host/racelink/web/request_helpers.py`, and
> `RaceLink_Host/racelink/web/dto.py`. When the source and this page
> disagree, the source wins.

## Conventions

* All POST/PUT bodies are JSON. Empty / non-JSON bodies are tolerated
  (treated as `{}`); the route then either applies defaults or
  returns a 400 if a required field is missing.
* Validation errors raise `RequestParseError`
  (a `ValueError` subclass, in `request_helpers.py`), which the route
  handler catches and translates to **HTTP 400** with a body of
  `{"ok": false, "error": "<message>"}`.
* Routes that kick off a long-running operation use the **task
  manager**: only one task can run at a time. While a task is
  running, conflicting routes return **HTTP 409**:
  ```json
  { "ok": false, "busy": true, "task": <task snapshot> }
  ```
* Long-running routes return immediately with
  `{"ok": true, "task": <snapshot>}`. Progress is delivered over SSE
  on the `task` event — see [SSE channels](sse-channels.md).
* Routes that depend on a service which isn't wired up
  (`scenes_service`, `rl_presets_service`, `scene_runner_service`)
  return **HTTP 503** with `{"ok": false, "error": "<service> not available"}`.
* All other unhandled exceptions are caught at the top of each
  handler, logged with type + traceback, and translated to
  **HTTP 500** with `{"ok": false, "error": "<TypeName>: <message>"}`.

## Common shapes

### Task snapshot

Returned by every route that starts a task-manager job (under the
`task` key) and by `GET /api/task`. Source:
`RaceLink_Host/racelink/web/tasks.py`.

```jsonc
{
  "id": 42,                    // monotonic, per-process
  "name": "discover",          // see "task names" below
  "state": "running",          // running | done | error
  "started_ts": 1714498220.13,
  "ended_ts": null,            // unix ts when state became done/error
  "meta": { /* task-specific; see per-task notes */ },
  "rx_replies": 0,
  "rx_window_events": 0,
  "rx_count_delta_total": 0,
  "last_error": null,          // string when state="error"
  "result": null               // task return value when state="done"
}
```

Task `name` values currently emitted by the API:
`discover`, `status`, `bulk_set_group`, `force_groups`,
`special_config`, `presets_download`, `fwupdate`.

### Gateway readiness snapshot

Returned by `/api/gateway` and as the `gateway` field of `/api/master`.
Source: `_gateway_status()` in `api.py` + `Controller.gateway_status`.

```jsonc
{
  "ready": true,
  "last_error": null,         // string | null
  "failure_count": 0
  // additional fields when the controller's getter is wired:
  // port, baud, state, etc.
}
```

### Master snapshot

Source: `MasterState.snapshot()` in
`RaceLink_Host/racelink/web/sse.py`.

```jsonc
{
  "state": "IDLE",            // mirrored from gateway EV_STATE_*
  "state_byte": 0,
  "state_metadata_ms": 0,
  "last_event": "CONTROL_SENT",
  "last_event_ts": 1714498220.13,
  "last_error": null
}
```

### Device row

Returned by `/api/devices` and inside the `master` blob. Source:
`serialize_device()` in `RaceLink_Host/racelink/web/dto.py`.

```jsonc
{
  "addr": "AABBCC",            // MAC suffix (last 3 bytes hex)
  "name": "Pit-1",
  "dev_type": 2,               // see GLOSSARY § "Capability"
  "dev_type_name": "RL_Node_v4_S3",
  "dev_type_caps": ["WLED"],
  "caps": 2,
  "groupId": 1,
  "flags": 0,
  "configByte": 0,
  "presetId": 3,
  "effectId": 0,
  "brightness": 200,
  "specials": { /* per-capability */ },
  "voltage_mV": 4012,
  "node_rssi": -67,
  "node_snr": 8,
  "host_rssi": -69,
  "host_snr": 7,
  "version": 4,
  "last_seen_ts": 1714498220.13,
  "last_ack": null,
  "online": true
}
```

### Group row

Returned by `/api/groups`.

```jsonc
{
  "id": 0,
  "name": "Unconfigured",
  "static": false,            // true for system groups (e.g. group 0)
  "dev_type": 0,              // capability filter (0 = mixed)
  "device_count": 3,
  "caps_in_group": { "WLED": 3, "STARTBLOCK": 0 }
}
```

---

## Health & state

### `GET /api/health`

Cheap liveness probe used by the WebUI's auto-reconnect loop.

**Response 200**:

```jsonc
{ "ok": true, "ts": 1714498220.13, "phase": "ready" }
```

`phase` is `"booting"` until the controller finishes
startup, then `"ready"`.

### `GET /api/master`

Full master snapshot (state mirror, in-flight task, gateway status).

**Response 200**:

```jsonc
{
  "ok": true,
  "master":  <master snapshot>,
  "task":    <task snapshot> | null,
  "gateway": <gateway snapshot>
}
```

### `GET /api/task`

Current in-flight task only. Returns `null` for the `task` field when
no task has run yet; otherwise the most recent snapshot (running, done,
or error).

**Response 200**: `{ "ok": true, "task": <task snapshot> | null }`

### `GET /api/gateway`

**Response 200**: `{ "ok": true, "gateway": <gateway snapshot> }`

### `POST /api/gateway/retry`

Retry the gateway connection (port reopen + state reset).

**Request body**: ignored.

**Response 200**: `{ "ok": <bool>, "gateway": <gateway snapshot> }` —
`ok` mirrors `gateway.ready`.

### `POST /api/gateway/query-state`

Send `GW_CMD_STATE_REQUEST`; await the matching `EV_STATE_REPORT`;
return the resolved state. Used by the master-pill ↻ refresh button.
Bounded by a ~500 ms timeout so a stalled gateway doesn't block the
WebUI thread.

**Request body**: ignored.

**Response 200** (gateway available):
```jsonc
{
  "ok": true,
  "state": "IDLE",
  "state_byte": 0,
  "state_metadata_ms": 0
}
```

**Response 503** (gateway service unavailable):
```jsonc
{
  "ok": false,
  "state": "UNKNOWN",
  "state_byte": 255,
  "state_metadata_ms": 0,
  "error": "gateway_service unavailable"
}
```

### `GET /api/options`

Returns the WLED-preset dropdown options for the WebUI's
`<select>` widgets.

**Response 200**: `{ "ok": true, "presets": [{"value": "...", "label": "..."}] }`

---

## Devices

### `GET /api/devices`

**Response 200**: `{ "ok": true, "devices": [<device row>, ...] }`

### `POST /api/discover`

Run device discovery. Newly-found devices land in `targetGroupId`
(or in a freshly-created group named `newGroupName`).

**Request body**:
```jsonc
{
  "targetGroupId": 1,         // optional; default 0 (Unconfigured)
  "newGroupName":  "Pit-A"    // optional; if set, a new group is created and used
}
```

**Response 200** (task started):
```jsonc
{ "ok": true, "task": <task snapshot> }
```

Task result: `{ "found": <int>, "createdGroupId": <int|null>, "targetGroupId": <int|null> }`.

**Response 409** if a task is already running.

### `POST /api/status`

Run a fleet status poll. `selection`/`macs` and `groupId` are mutually
exclusive — when both are absent, the broadcast group filter (`255`)
is used.

**Request body**:
```jsonc
{
  "selection": ["AABBCC", "DDEEFF"],   // optional; alias: "macs"
  "groupId": 1                          // optional
}
```

**Response 200** (task started):
```jsonc
{ "ok": true, "task": <task snapshot> }
```

Task result: `{ "updated": <int>, "groupId": <int|null>, "selectionCount": <int> }`.

### `POST /api/devices/update-meta`

Bulk rename / regroup. Two paths:

* **Pure rename** (no `groupId` field, single MAC, `name` set):
  synchronous, no RF I/O. Returns the result inline.
* **Group change** (`groupId` set): wrapped in a TaskManager job
  named `bulk_set_group`. Already-offline devices skip the SET_GROUP
  wire send (auto-restore handles them on next IDENTIFY/STATUS).

**Request body**:
```jsonc
{
  "macs":    ["AABBCC", "DDEEFF"],
  "groupId": 2,                         // optional; triggers async path when present
  "name":    "Pit-1"                    // optional
}
```

**Response 200, sync**:
```jsonc
{
  "ok": true,
  "changed": 1,
  "skipped_offline": 0,
  "timed_out": 0,
  "total": 1
}
```

**Response 200, async**: `{ "ok": true, "task": <task snapshot> }`.
Task `meta` carries `{stage, index, total, addr, groupId, message}`.

### `POST /api/devices/control`

Send `OPC_CONTROL` to a group or to a list of devices.

**Request body**:
```jsonc
{
  "macs":      ["AABBCC"],     // EITHER macs (per-device unicast)
  "groupId":   1,               //  OR groupId (broadcast within group)
  "flags":     0,
  "presetId":  3,
  "brightness": 200
}
```

* Exactly one of `macs` / `groupId` must be present (else 400).
* `flags`, `presetId`, `brightness` are required (else 400).
* For body field semantics see Glossary § "Flags byte" and
  [Wire protocol](wire-protocol.md) § "P_Preset".

**Response 200**:
```jsonc
{
  "ok": true,
  "changed": 1                  // # of frames the transport accepted (0
                                //   when the gateway is offline)
}
```

### `GET /api/specials`

**Response 200**: `{ "ok": true, "specials": <SpecialsService config> }` —
shape is the per-capability "specials" form schema. See
`RaceLink_Host/racelink/services/specials_service.py`.

### `POST /api/specials/config`

Send an `OPC_CONFIG` packet that updates a single per-device "special"
knob (e.g. an LED count, a panel mode). Wrapped in a TaskManager job.

**Request body**:
```jsonc
{
  "mac":   "AABBCC",
  "key":   "ledCount",          // capability-specific knob name
  "value": 60                    // integer
}
```

The `key` → `option` byte mapping is resolved by `SpecialsService`.

**Response 200**: `{ "ok": true, "task": <task snapshot> }`.

Task `meta` carries `{mac, key, message}`. The task itself waits for
ACK with a 6 s timeout; on ACK it updates the in-memory `specials`
dict and persists with scope `DEVICE_SPECIALS`.

### `POST /api/specials/action`

Trigger a one-shot per-device action (e.g. a startblock identify
beep). Synchronous; ACK is not awaited inside the route.

**Request body**:
```jsonc
{
  "mac":      "AABBCC",
  "function": "startblock_control",   // capability-specific function key
  "params":   { /* per-function */ }   // optional
}
```

**Response 200**:
```jsonc
{
  "ok": true,
  "result":  <comm-handler return value>,
  "function": "startblock_control",
  "params":   { /* coerced */ }
}
```

**Errors**: 400 (missing/invalid mac/function, broadcast not allowed,
unsupported function, params coercion failed); 404 (device not found);
500 (action failed).

### `POST /api/specials/get`

**Response 501**: `{ "ok": false, "error": "not implemented" }`. Reserved.

### `POST /api/config`

Send a raw `OPC_CONFIG` packet to a single device. Lower-level than
`/api/specials/config` — the client is responsible for the
`option` byte and four data bytes; no host-side state mirror is
updated.

**Request body**:
```jsonc
{
  "mac":   "AABBCC",            // alias: "macs": ["AABBCC"] (must be exactly 1)
  "option": 1,                   // see wire-protocol.md § "P_Config"
  "data0": 0, "data1": 0, "data2": 0, "data3": 0   // optional, default 0
}
```

`option` must be one of `{0x01, 0x03, 0x04, 0x80, 0x81}` (else 400).
Broadcast (`mac == "FFFFFF"`) is rejected (else 400).

**Response 200**:
```jsonc
{
  "ok": true, "sent": 1, "recv3": "AABBCC", "option": 1,
  "data0": 0, "data1": 0, "data2": 0, "data3": 0
}
```

---

## Groups

### `GET /api/groups`

**Response 200**: `{ "ok": true, "groups": [<group row>, ...] }`.

The synthetic group `id=0` ("Unconfigured") is always included. The
legacy "All WLED Nodes" entry is filtered out.

### `POST /api/groups/create`

**Request body**:
```jsonc
{
  "name":     "Track-A",
  "dev_type": 0                  // optional; 0 = mixed; alias: "device_type"
}
```

**Response 200**: `{ "ok": true, "id": <new gid> }`.

**Errors**: 400 (`name` empty/missing).

### `POST /api/groups/rename`

**Request body**:
```jsonc
{ "id": 2, "name": "New name" }
```

`id` validated by `require_int(label="group id")`.

**Response 200**: `{ "ok": true }`. **Errors**: 400 (missing id, invalid
group id, static group).

### `POST /api/groups/delete`

Devices in the deleted group move to `groupId=0`; devices in
higher-indexed groups have their `groupId` decremented. Scene actions
referencing the deleted group are renumbered via
`SceneService.renumber_group_references()`.

**Request body**: `{ "id": 2 }`.

**Response 200**:
```jsonc
{
  "ok": true,
  "moved_devices": 3,
  "renumbered_devices": 5,
  "renumbered_scenes": 2
}
```

**Errors**: 400 (missing id, invalid group id, static group).

### `POST /api/groups/force`

Re-broadcast every device's stored `groupId` to the network
(SET_GROUP per device). Wrapped in a TaskManager job named
`force_groups`.

**Request body**:
```jsonc
{ "skipOffline": false }    // optional; default false
```

* `skipOffline=false` (default): pushes SET_GROUP to *every* device,
  including offline ones — the operator's "re-sync ALL" semantic.
* `skipOffline=true`: skips offline devices; auto-restore handles
  them on next IDENTIFY/STATUS.

**Response 200**: `{ "ok": true, "task": <task snapshot> }`.
Task `meta` carries `{stage, index, total, addr, message, skipOffline}`.

---

## Persistence

### `POST /api/save`

Manual save of the in-memory state (devices, groups, presets,
scenes) to disk.

**Request body**: ignored.

**Response 200**: `{ "ok": true }`. **Errors**: 500 (DB lock, disk
full, etc.) — body includes `"error": "<TypeName>: <message>"`.

### `POST /api/reload`

Re-load state from disk. Pushes a `FULL` SSE refresh on success.

**Request body**: ignored.

**Response 200**: `{ "ok": true }`. **Errors**: 500.

---

## Firmware uploads

### `POST /api/fw/upload`

Upload a firmware binary (multipart/form-data — *not* JSON).

**Form fields**:

| Field  | Type | Notes |
|---|---|---|
| `file` | binary | the firmware payload |
| `kind` | string | `"firmware"` or `"cfg"` |

**Response 200**:
```jsonc
{
  "ok": true,
  "file": {
    "id": "<opaque>", "kind": "firmware", "name": "wled.bin",
    "size": 1234567, "sha256": "...", "uploaded_ts": 1714498220.13
  }
}
```

`file.id` is later passed as `fwId` / `cfgId` in `POST /api/fw/start`.

**Errors**: 400 (validation: missing file, wrong kind, size, MIME).
409 if a task is running.

### `GET /api/fw/uploads`

**Response 200**: `{ "ok": true, "files": [<file info>, ...] }`.

### `POST /api/fw/start`

Start an OTA workflow. Wrapped in a TaskManager job named `fwupdate`.

**Request body**:
```jsonc
{
  "macs":          ["AABBCC", "DDEEFF"],   // required; non-empty
  "doFirmware":    true,                   // optional; default true
  "doPresets":     false,                  // optional; default false
  "doCfg":         false,                  // optional; default false
  "fwId":          "<from fw/upload>",     // required when doFirmware
  "presetsName":   "race-event.json",      // required when doPresets
  "cfgId":         "<from fw/upload>",     // required when doCfg
  "retries":       3,                      // optional; clamp 1..10
  "stopOnError":   false,                  // optional; default false
  "skipValidation": false,                 // optional; default false
  "wifi": {                                // see "WiFi sub-body" below
    "ssids":       ["WLED_RaceLink_AP"],
    "password":    "wled1234",
    "iface":       "wlan0",
    "bssid":       "",
    "timeoutS":    20,
    "otaPassword": "wledota",
    "hostWifiEnable": true,
    "hostWifiRestore": true
  },
  "baseUrl":       "http://4.3.2.1"        // optional; OTA targets default to wled.local
}
```

At least one of `doFirmware` / `doPresets` / `doCfg` must be true
(else 400). `skipValidation=true` is forwarded as
`skipValidation=1` in WLED's `/update` form, bypassing WLED's
release-name check — used when migrating between firmware forks.

**Response 200**: `{ "ok": true, "task": <task snapshot> }`. Task
`meta` carries `{stage, index, total, retries, addr, message, baseUrl}`.

#### WiFi sub-body shape

Resolved by `parse_wifi_options()` in `request_helpers.py`. All
fields are optional; any can also live at the body root with a
`wifi`-prefixed alias (`wifiSsid`, `wifiPassword`, `wifiIface`,
`wifiBssid`, `wifiTimeoutS`, `wifiOtaPassword`).

| Field | Type | Default | Notes |
|---|---|---|---|
| `ssids` | `string[]` | `["WLED_RaceLink_AP", "WLED-AP"]` | candidate APs (newer firmware first); singular `ssid` (comma-split) accepted for back-compat |
| `password` | `string` | `"wled1234"` | WLED AP password |
| `iface` | `string` | `"wlan0"` | host wireless interface |
| `bssid` | `string` | `""` | pin to a specific BSSID |
| `timeoutS` | `number` | `20` | overall scan+connect budget |
| `otaPassword` | `string` | `"wledota"` | WLED OTA password (for the auto-unlock POST on 401 from `/update`) |
| `hostWifiEnable` | `bool` | `true` | enable host's WiFi radio for the workflow |
| `hostWifiRestore` | `bool` | `true` | restore host's WiFi radio afterwards |

If the resolved SSID list is empty after normalisation, the route
returns 400 (the workflow has no AP to look for). The legacy
`connName` field is silently ignored.

---

## WLED preset files

### `POST /api/presets/upload`

Upload a `presets.json` from the operator's machine.
multipart/form-data; field `file`.

**Response 200**:
```jsonc
{
  "ok": true,
  "file":  { "name": "x.json", "size": 1234, "saved_ts": 1714498220.13 },
  "files": [<file info>, ...]
}
```

**Errors**: 400 (validation); 409 (busy).

### `GET /api/presets/list`

**Response 200**: `{ "ok": true, "files": [<file info>, ...], "current": "<name>" }`.

### `POST /api/presets/select`

Activate one of the uploaded preset files for the host's "current"
preset slot.

**Request body**: `{ "name": "race-event.json" }`.

**Response 200**: `{ "ok": true, "current": "race-event.json" }`.
**Errors**: 404 (file not found); 400 (parse failed); 409 (busy).

### `POST /api/presets/download`

Download a node's `presets.json` to the host. Wrapped in a
TaskManager job named `presets_download`. Same WiFi sub-body as
`/api/fw/start`.

**Request body**:
```jsonc
{
  "mac":     "AABBCC",
  "baseUrl": "http://4.3.2.1",     // optional
  "wifi":    { /* as above */ }
}
```

**Response 200**: `{ "ok": true, "task": <task snapshot> }`.
**Errors**: 400 (missing/invalid mac, empty SSID list); 409.

---

## RaceLink-native presets (RL presets)

RL presets are parameter snapshots driven by `OPC_CONTROL_ADV`.
See Glossary § "Preset" for the disambiguation between RL preset
and WLED preset.

### `GET /api/rl-presets`

**Response 200**: `{ "ok": true, "presets": [<RL preset>, ...] }`.

`<RL preset>` shape: `{key, label, params, flags, ...}` — see
`RaceLink_Host/racelink/services/rl_presets_service.py`.

### `GET /api/rl-presets/schema`

Return the 14-field editor schema with select-option generators
resolved (effects metadata, palette list, palette-color rules). The
WebUI's `ensureRlPresetUiSchema` consumes this.

**Response 200**: `{ "ok": true, "schema": <RL_PRESET_EDITOR_SCHEMA> }`.

### `POST /api/rl-presets`

Create an RL preset.

**Request body**:
```jsonc
{
  "label":  "Track sweep",
  "params": { /* per-effect */ },         // optional
  "flags":  0,                             // optional
  "key":    "track-sweep"                  // optional; auto-generated if omitted
}
```

**Response 200**: `{ "ok": true, "preset": <RL preset> }`.
**Errors**: 400 (missing/empty label, invalid params).

### `GET /api/rl-presets/<key>`

**Response 200**: `{ "ok": true, "preset": <RL preset> }`.
**Errors**: 404.

### `PUT /api/rl-presets/<key>`

Update an existing RL preset. All body fields are optional — pass
only what's changing.

**Request body**:
```jsonc
{ "label": "...", "params": {...}, "flags": 0 }
```

**Response 200**: `{ "ok": true, "preset": <RL preset> }`.
**Errors**: 400 (validation); 404.

### `DELETE /api/rl-presets/<key>`

**Response 200**: `{ "ok": true }`. **Errors**: 404.

### `POST /api/rl-presets/<key>/duplicate`

**Request body**: `{ "label": "Copy of …" }` (optional).

**Response 200**: `{ "ok": true, "preset": <RL preset> }`.
**Errors**: 400 (validation); 404 (source not found).

---

## Scenes

For the on-disk scene format (the actions list shape), see
[Scene file format](scene-format.md).

### `GET /api/scenes`

**Response 200**: `{ "ok": true, "scenes": [<scene>, ...] }`.

### `GET /api/scenes/editor-schema`

Per-action-kind UI hints + LoRa parameters for the cost-estimator
tooltip. Used by the scene editor frontend.

**Response 200**:
```jsonc
{
  "ok": true,
  "kinds": [
    {
      "kind": "rl_preset",
      "ui": {
        "presetId":  { "widget": "select", "options": [...] },
        "brightness":{ "widget": "slider", "min": 0, "max": 255 }
      },
      /* + canonical kind metadata: label, target_kinds, defaults, ... */
    },
    /* wled_preset, wled_control, startblock, delay, sync, offset_group */
  ],
  "flag_keys":     ["arm", "armOnSync", "applyOnSync", ...],
  "target_kinds":  ["group", "device"],
  "offset_group": {
    "max_groups":   16,
    "max_children": 4,
    "group_id":     { "min": 0, "max": 254 },
    "offset_ms":    { "min": -32768, "max": 32767 },
    "modes":        ["stagger_ms", "stagger_seq", "stagger_offset"],
    "base_ms":      { "min": -32768, "max": 32767 },
    "step_ms":      { "min": -32768, "max": 32767 },
    "center":       { "min": 0, "max": 254 },
    "cycle":        { "min": 1, "max": 255 },
    "supports_all_groups": true,
    "child_kinds":         ["wled_preset", "rl_preset", "wled_control"],
    "child_target_kinds":  ["scope", "group", "device"]
  },
  "lora": { /* SF, BW, CR, preamble, sync byte */ }
}
```

### `GET /api/scenes/<key>`

**Response 200**: `{ "ok": true, "scene": <scene> }`. **Errors**: 404.

### `POST /api/scenes`

Create a scene.

**Request body**:
```jsonc
{
  "label":         "Race start",
  "actions":       [ /* per scene-format.md */ ],
  "key":           "race-start",     // optional; auto-generated if omitted
  "stop_on_error": true              // optional; default true
}
```

**Response 200**: `{ "ok": true, "scene": <scene> }`. Emits SSE
refresh with scope `SCENES`. **Errors**: 400 (validation: missing
label, invalid actions).

### `PUT /api/scenes/<key>`

Update a scene. All body fields optional.

**Request body**: `{ "label": "...", "actions": [...], "stop_on_error": true }`.

**Response 200**: `{ "ok": true, "scene": <scene> }`. Emits SSE
`SCENES` refresh. **Errors**: 400; 404.

### `DELETE /api/scenes/<key>`

**Response 200**: `{ "ok": true }`. Emits SSE `SCENES` refresh.
**Errors**: 404.

### `POST /api/scenes/<key>/duplicate`

**Request body**: `{ "label": "Copy of …" }` (optional).

**Response 200**: `{ "ok": true, "scene": <scene> }`. Emits SSE
`SCENES` refresh.

### `GET /api/scenes/<key>/estimate`

Projected wire cost for a saved scene (packets, bytes, airtime).

**Response 200**:
```jsonc
{
  "ok": true,
  "total":      { "packets": 12, "bytes": 192, "airtime_ms": 740, "wall_clock_ms": 760 },
  "per_action": [
    { "packets": 1, "bytes": 16, "airtime_ms": 60, "wall_clock_ms": 60, "detail": {} },
    /* ... */
  ],
  "lora": { /* see editor-schema */ }
}
```

**Errors**: 404.

### `POST /api/scenes/estimate`

Estimate cost for an unsaved draft. Validates `actions` through
`SceneService._canonical_actions()` before estimating.

**Request body**:
```jsonc
{ "label": "draft", "actions": [...] }    // label optional
```

**Response 200**: same shape as `/api/scenes/<key>/estimate`.
**Errors**: 400 (validation).

### `POST /api/scenes/<key>/run`

Run a scene synchronously. The HTTP response holds open until the
runner finishes (worst-case ~20 minutes for 20 actions × 60 s
delays; realistic scenes finish in seconds). Per-action progress is
broadcast on the SSE bus on the `scene_progress` topic before/after
each action — see [SSE channels](sse-channels.md).

**Ephemeral-draft path:** when the body contains an `actions` list,
the runner executes that list instead of the persisted scene; the
saved scene is untouched.

**Request body** (optional):
```jsonc
{
  "label":         "...",       // optional; default "draft"
  "actions":       [ ... ],     // optional; triggers draft path
  "stop_on_error": true         // optional; falls back to saved scene's setting
}
```

**Response 200**:
```jsonc
{
  "ok": true,
  "result": {
    /* SceneRunResult.to_dict():
       ok, error, actions: [{ok, error, ...}], started_ts, ended_ts, ... */
  }
}
```

**Response 404**: when neither the saved scene nor a draft body
exists (`error: "scene_not_found"`). **Errors**: 400 (draft validation).

---

## WiFi (host)

### `GET /api/wifi/interfaces`

Probe the host's wireless interfaces (used by the OTA workflow's
"select interface" dropdown).

**Response 200**:
```jsonc
{ "ok": true, "ifaces": [{ "name": "wlan0", "state": "up", ...}] }
```

Shape per `HostWifiService.wifi_interfaces()`.

---

## Error responses summary

| Status | Triggers |
|---|---|
| 400 | request validation (missing/invalid field, empty body where required, scene-action validator failure, file-upload validation, broadcast not allowed for unicast op) |
| 404 | resource not found (preset, scene, group id, device address) |
| 409 | task busy — body carries the running task's snapshot |
| 500 | unhandled exception (incl. transport errors, persistence failures) — body carries `"<TypeName>: <message>"` |
| 501 | reserved (`/api/specials/get`) |
| 503 | service not wired up (`scenes`, `rl_presets`, `scene_runner`); gateway service unavailable |

Error body shape is consistently
`{"ok": false, "error": "<message>" /* + extras for some routes */}`.
