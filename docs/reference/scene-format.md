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
  "target": { "kind": "broadcast" },
  "offset": { "mode": "linear", "base_ms": 0, "step_ms": 200 },
  "children": [
    { "kind": "rl_preset", "preset_key": "RL:breathe_blue", ... }
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `target` | object | Unified target (see [Target discriminator](#target-discriminator)). Container scope only allows `broadcast` or `groups` — `device` is invalid because the offset formula is per-group. |
| `offset` | object | `{mode, ...}`. See "Offset modes" below. |
| `children` | list of actions | Up to 16 children. Children inherit the parent's offset semantics; their `flags_override.offset_mode` is decided by the parent's `mode` (see *flags_override semantics* below). |

> **Legacy shape.** Pre-2026-05 scenes used a standalone
> `groups` field (`"all"` or `[<int>, ...]`). The loader migrates
> it to the unified `target` shape on read; saved scenes always
> use `target`. See [Target discriminator](#target-discriminator)
> for the migration table.

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

Every action that touches a device target uses the same
discriminated-union shape — top-level effects, `offset_group`
containers, and `offset_group` children all read from the same
schema. See [Broadcast Ruleset](broadcast-ruleset.md) for the
end-to-end rules per OpCode.

```json
// Every device on the wire (recv3=FFFFFF, groupId=255):
"target": { "kind": "broadcast" }

// One or more specific groups:
"target": { "kind": "groups", "value": [3] }
"target": { "kind": "groups", "value": [1, 3, 5] }

// Single device by MAC:
"target": { "kind": "device", "value": "AABBCCDDEEFF" }
```

| `kind` | Required fields | Notes |
|---|---|---|
| `broadcast` | — | `recv3=FFFFFF`, body `groupId=255`. Every device acts. |
| `groups` | `value` — non-empty list of int group ids in 1..254 | Each id is `recv3=FFFFFF` + body `groupId=id` (group-scoped broadcast at the wire). Length-1 is the common case ("send to one group"). Lists are sorted and de-duplicated on save. |
| `device` | `value` — 12-char MAC hex (no colons) | Host normalises to upper-case. The wire emission keeps the device's stored `groupId` from the Host repository — `groupId=255` is **not** used as a fallback (see [Single-device pinned rule](broadcast-ruleset.md#single-device-pinned-rule)). |

Group `0` ("Unconfigured") is forbidden as a productive scene
target — the editor's group dropdowns hide it.

`sync` and `delay` actions have no `target`. The `offset_group`
container has a `target` of its own (broadcast / groups only —
no `device`); each child action also carries its own target.

### Save-time canonicalisation

Two rewrites run when a scene is saved through the host's API:

1. **Selected-equals-known-all → broadcast.** When a `groups`
   target's `value` covers every currently-known group id, the
   shape is rewritten to `{ "kind": "broadcast" }`. This makes
   the runtime / cost-estimator pair unambiguous (both pick
   optimizer Strategy A) and removes the visual ambiguity the
   editor had pre-unification, where "All groups" checkbox vs.
   "every group manually checked" produced different cost
   estimates for the same wire path. The editor surfaces a
   "(All groups selected → will save as Broadcast.)" hint when
   this collapse is about to fire.

2. **Legacy migrations.** Pre-unification shapes are migrated
   on load (the canonical output is always the unified shape):

   | Legacy in JSON | Canonical shape |
   |---|---|
   | `target.kind == "scope"` (offset_group child) | `{ "kind": "broadcast" }` |
   | `target.kind == "group", value: <int>` | `{ "kind": "groups", "value": [<int>] }` |
   | `offset_group.groups == "all"` | `target: { "kind": "broadcast" }` (the standalone `groups` field is removed) |
   | `offset_group.groups == [<int>, ...]` | `target: { "kind": "groups", "value": [<int>, ...] }` |

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

## Migration shims

Two on-load migrations keep older persisted scenes loadable:

* **Pre-hierarchy `groups_offset` action.** A flat
  `groups_offset` kind bundled the offset configuration and the
  effect parameters in one action. The loader rewrites it into
  the current `offset_group` container with a single child.
* **Pre-unification target shapes.** `target.kind == "scope"` →
  `"broadcast"`; singular `target.kind == "group"` → `"groups"`
  length-1 list; `offset_group.groups` → `target` field. See
  the table in [Save-time canonicalisation](#save-time-canonicalisation).

Both shims log one line per rewritten action. Removal target:
2026-Q3.

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
          "target": { "kind": "broadcast" },
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
