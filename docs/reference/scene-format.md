# Scene File Format

On-disk reference for `~/.racelink/scenes.json`. Distilled from the
operator guide ([`../RaceLink_Host/operator-guide.md`](../RaceLink_Host/operator-guide.md)),
the developer guide
([`../RaceLink_Host/developer-guide.md`](../RaceLink_Host/developer-guide.md))
and the source-repo Scene-Manager design (`plans/scene-manager-feature.md`,
not part of this consolidation).

> **Source of truth.** The validator in
> `racelink/services/scenes_service.py` is the canonical authority on
> the on-disk shape. When this document and the validator disagree,
> the validator wins.

## File location

```text
~/.racelink/scenes.json     (Linux)
C:\Users\<username>\.racelink\scenes.json   (Windows)
```

The host loads `scenes.json` on startup and writes it back on every
scene save / delete. Hand-editing the file is supported but
discouraged; the WebUI editor performs validation that the file
loader does not (the loader is permissive of legacy shapes via the
migration shim).

## Top-level shape

```json
{
  "version": 1,
  "scenes": [
    { ... scene 1 ... },
    { ... scene 2 ... }
  ]
}
```

* `version` (int) — schema version. Currently `1`. Bump on
  breaking schema changes.
* `scenes` (list of objects) — see below.

## Scene object

```json
{
  "key": "intro_effects",
  "label": "Intro Effects",
  "stop_on_error": true,
  "actions": [ ... ]
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `key` | string | yes | Stable identifier, used in URLs. Auto-generated from `label` on create; rename does not change `key`. |
| `label` | string | yes | Free-form display text. |
| `stop_on_error` | bool | optional, default `true` | When `true` the scene runner aborts at the first failed action and marks the rest "skipped". When `false`, every action runs regardless of earlier failures. |
| `actions` | list | yes | Up to 20 actions. Empty list is valid (scene is a no-op). |

## Action object — common fields

Every action has at minimum:

```json
{
  "kind": "wled_preset",
  "target": { ... },
  ...kind-specific vars...
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `kind` | string | yes | One of: `wled_preset`, `rl_preset`, `wled_control`, `startblock`, `sync`, `delay`, `offset_group`. |
| `target` | object | depends on kind | See "Target discriminator" below. |
| `flags_override` | object | optional | Sparse override of the canonical flags byte; see "flags_override semantics" below. |

## Action kinds

### `wled_preset` — apply a WLED preset

Sends `OPC_PRESET` carrying a 4-byte body with the preset slot
number. Cap-gated to `WLED`.

```json
{ "kind": "wled_preset", "target": { ... }, "preset_id": 42, "brightness": 200 }
```

| Field | Type | Range | Notes |
|---|---|---|---|
| `preset_id` | int | 0–255 | The numeric WLED preset slot |
| `brightness` | int | 0–255 | 0 = use stored brightness |

### `rl_preset` — apply a RaceLink preset

Sends `OPC_CONTROL` with the materialised effect parameters from a
named host-side RL preset.

```json
{ "kind": "rl_preset", "target": { ... }, "preset_key": "RL:fast_rainbow" }
```

| Field | Type | Notes |
|---|---|---|
| `preset_key` | string | Stable preset key. RL presets use `RL:<slug>`; numeric WLED presets accessed by slot use `WLED:<int>`. |

### `wled_control` — direct effect parameters

Sends `OPC_CONTROL` with effect parameters supplied inline. Useful
when you don't want the indirection of a saved preset.

```json
{
  "kind": "wled_control",
  "target": { ... },
  "mode": 35,
  "speed": 128,
  "intensity": 200,
  "brightness": 220,
  "palette": 6,
  "colors": ["FF0000", "FFAA00", "00FF00"],
  "custom1": 32, "custom2": 0, "custom3": 0,
  "check1": false, "check2": false, "check3": false
}
```

The full parameter list and bit-mask encoding are documented in
[`../reference/wire-protocol.md`](wire-protocol.md) §"`OPC_CONTROL`".
Fields that are absent are omitted from the wire body — the
receiver retains its current value for those fields.

### `startblock` — starting-block program

Cap-gated to `STARTBLOCK`. Sends a starting-block program payload
via `OPC_STREAM`.

```json
{ "kind": "startblock", "target": { ... }, "program": "...", ... }
```

The program-payload shape is application-specific; refer to the
host's `services/startblock_service.py` for the current layout.

### `sync` — fire armed effects

Sends `OPC_SYNC` (5-byte / flag-bearing form, with
`SYNC_FLAG_TRIGGER_ARMED=1`). Materialises any pending arm-on-sync
state across the fleet and adjusts `strip.timebase`.

```json
{ "kind": "sync" }
```

Has no target — `OPC_SYNC` is broadcast.

### `delay` — host-side wait

Pause the scene runner for the specified duration. No wire traffic.

```json
{ "kind": "delay", "ms": 2000 }
```

| Field | Type | Range | Notes |
|---|---|---|---|
| `ms` | int | ≥ 0 | Wait in milliseconds. |

### `offset_group` — container with per-group offsets

Container action that runs its children with a per-group time
offset, producing wave / cascade effects.

```json
{
  "kind": "offset_group",
  "groups": "all",
  "offset": { "mode": "linear", "base_ms": 0, "step_ms": 200 },
  "children": [
    { "kind": "rl_preset", "preset_key": "RL:breathe_blue", ... }
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `groups` | `"all"` or list of int | Which groups participate. |
| `offset` | object | `{mode, ...}`. See "Offset modes" below. |
| `children` | list of actions | Up to 16 children. Children inherit the parent's offset semantics; their `flags_override.offset_mode` is decided by the parent's `mode` (see *flags_override semantics* below). |

#### Offset modes

| `mode` | Extra fields | Per-device offset formula |
|---|---|---|
| `none` | — | 0 (cleared). Children play immediately with no offset shift. |
| `explicit` | `{group_id: offset_ms}` per participating group | Explicit per-group offset value. |
| `linear` | `base_ms`, `step_ms` | `base + groupId × step` |
| `vshape` | `base_ms`, `step_ms`, `center` | `base + abs(groupId − center) × step` |
| `modulo` | `base_ms`, `step_ms`, `cycle` | `base + (groupId mod cycle) × step` |

`base_ms` and `step_ms` are signed 16-bit; `cycle` is 1..255;
`center` is 0..254.

## Target discriminator

The `target` object follows a discriminated-union pattern:

```json
// All devices in a group:
"target": { "kind": "group", "group_id": 3 }

// Single device by MAC:
"target": { "kind": "device", "mac": "AA:BB:CC:DD:EE:FF" }

// Broadcast:
"target": { "kind": "broadcast" }
```

| `kind` | Required fields | Notes |
|---|---|---|
| `group` | `group_id` (1–254) | Group `0` ("Unconfigured") is forbidden as a scene target. |
| `device` | `mac` (12-char hex with colons) | Host normalises to upper-case. |
| `broadcast` | — | `groupId=255`. Some action kinds (e.g. `wled_preset`) accept broadcast; ACK-bearing kinds expect a unicast or group target instead. |

`sync` and `delay` actions have no `target`. `offset_group` does
not have a top-level `target` either; each child action carries
its own.

## `flags_override` semantics

Each non-container action may carry a `flags_override` block that
overrides parts of the canonical flags byte:

```json
"flags_override": {
  "arm_on_sync": true,
  "force_tt0": false,
  "force_reapply": false
}
```

Fields not listed in `flags_override` use the canonical default
(computed by `racelink/domain/flags.py::build_flags_byte`). The
following keys are recognised:

| Key | Maps to flag bit | Notes |
|---|---|---|
| `arm_on_sync` | `RL_FLAG_ARM_ON_SYNC` | Defer apply until the next `OPC_SYNC` |
| `force_tt0` | `RL_FLAG_FORCE_TT0` | Force transition time 0 (no fade) |
| `force_reapply` | `RL_FLAG_FORCE_REAPPLY` | Re-apply even if state hasn't changed |
| `offset_mode` | `RL_FLAG_OFFSET_MODE` | Inside an `offset_group` container the parent's `mode` decides this — setting `offset_mode=False` here on a child is a no-op |

`RL_FLAG_POWER_ON` and `RL_FLAG_HAS_BRI` are auto-derived from
`brightness` and not user-overridable.

## Validation invariants

The `SceneService.create_or_update` validator enforces:

1. `key` is unique within the file.
2. `label` is non-empty.
3. `actions` length ≤ 20.
4. Each action's `kind` is one of the recognised values.
5. Cap-gated actions only target capability-matching devices /
   groups (the editor's dropdowns enforce this; legacy scenes with
   non-matching targets log a warning at load time).
6. `offset_group` children list length ≤ 16.
7. `delay.ms ≥ 0`.
8. Numeric fields in `wled_control` (mode, speed, brightness, …)
   are in their byte ranges (0–255 each).

## Migration shim

Older scenes used a flat `groups_offset` action kind that bundled
both the offset configuration and the effect parameters. The
loader recognises this shape and rewrites it on read into the
current `offset_group` container. The shim is permanent until at
least 2026-Q3 and produces a one-line
log entry on each rewrite.

## Example scene

```json
{
  "version": 1,
  "scenes": [
    {
      "key": "race_start_cascade",
      "label": "Race Start Cascade",
      "stop_on_error": true,
      "actions": [
        {
          "kind": "offset_group",
          "groups": "all",
          "offset": { "mode": "linear", "base_ms": 0, "step_ms": 200 },
          "children": [
            {
              "kind": "rl_preset",
              "target": { "kind": "broadcast" },
              "preset_key": "RL:breathe_green",
              "flags_override": { "arm_on_sync": true }
            }
          ]
        },
        { "kind": "delay", "ms": 1000 },
        { "kind": "sync" }
      ]
    }
  ]
}
```
