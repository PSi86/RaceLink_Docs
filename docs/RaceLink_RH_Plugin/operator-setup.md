# RotorHazard Plugin: Operating Concept

How RaceLink shows up inside RotorHazard once the
[`RaceLink_RH_Plugin`](README.md) is installed — what each panel,
field, and action does, how race events bind to scenes, and how
the plugin coexists with RotorHazard's lifecycle.

> **Audience.** Operators running RotorHazard who want to use
> RaceLink to control their LED nodes during a race. For
> standalone-mode operation (without RotorHazard), see
> [`../RaceLink_Host/operator-guide.md`](../RaceLink_Host/operator-guide.md)
> and [`../RaceLink_Host/webui-guide.md`](../RaceLink_Host/webui-guide.md).

The plugin imports the **same** RaceLink core and the **same**
WebUI as standalone mode — it's not a fork, it's an adapter. What
the plugin adds is a small surface inside RotorHazard's settings
and run views, plus the ability to bind RotorHazard race events
(race start, heat advance, finish) to RaceLink scenes.

---

## Architecture in one paragraph

RotorHazard hosts the plugin process. The plugin loads the
`racelink-host` Python package, mounts the shared RaceLink WebUI at
`/racelink`, and registers two RotorHazard UI panels (`rl_settings`
and `rl_quickset`) plus a few ActionEffects (so that race events
can fire RaceLink scenes / presets). The host owns the gateway in
plugin mode — RotorHazard never opens the dongle.

For the deeper architecture, see
[`README.md`](README.md) §"Architecture" and the host-side
[`../RaceLink_Host/architecture.md`](../RaceLink_Host/architecture.md) §"WebUI Hosting
Model".

---

## Two surfaces, two purposes

When you install the plugin, RaceLink shows up in two places inside
RotorHazard:

1. **The RotorHazard side panels** — small, focused controls for
   the most common race-day actions (Discover, Set Defaults, Force
   Groups, the Quickset Run button). Located in RotorHazard's
   *Settings* and *Run* views.
2. **The shared WebUI** — the full RaceLink WebUI, mounted at
   `/racelink/` inside RotorHazard's webserver. Contains the Scenes
   editor, RL Preset editor, OTA dialog, Specials, and everything
   else from standalone mode.

The split is **deliberate**: the side panels are what you reach for
during a race; the shared WebUI is where you author scenes / manage
presets between races. Use one or the other depending on the task
at hand.

To get to the shared WebUI from RotorHazard:

```
http://<rotorhazard-host>:5000/racelink/
```

(Port and path may differ if RotorHazard's webserver is configured
non-default.)

---

## The `rl_settings` panel

Lives in RotorHazard's *Settings* view. Bootstrapped once on plugin
load and never re-registered (a previous selective-refresh refactor
fixed the "Redefining panel" log spam).

### Fields

| Field | Type | Purpose |
|---|---|---|
| **`rl_device_config`** | TEXT (read-only) | Shows the current RaceLink device list — one line per device with MAC, group, capability. Updates on `DEVICES` / `DEVICE_MEMBERSHIP` scope events. |
| **`rl_groups_config`** | TEXT (read-only) | Shows the current group list with member counts. Updates on `GROUPS` scope events. |
| **`rl_assignToGroup`** | SELECT | Target group for the *Assign* quickbutton. Options refresh on `GROUPS` scope events. Excludes the synthetic group 0 ("Unconfigured"). |
| **`rl_assignToNewGroup`** | TEXT | Type a new group name to create-and-assign in one action. Static; not refreshed by state-scope events. |

### Quickbuttons

These execute immediately when clicked — no follow-up dialog.

| Button | What it does | Wire impact |
|---|---|---|
| **`rl_btn_get_devices`** | Run **Discover Devices**. Same as the WebUI's Discover button. | 1× broadcast `OPC_DEVICES`, RX window collects replies. |
| **`rl_btn_force_groups`** | Re-broadcast every device's stored `groupId`. The recovery action when nodes have been reflashed or moved between gateways and their in-radio state has drifted from the host's view of them. | N× `OPC_SET_GROUP` to each device. |
| **`rl_btn_set_defaults`** | Apply the operator-configured default RL preset across the fleet. Shorthand for "everything to known-good state". | 1× `OPC_PRESET` per group / device, depending on configuration. |
| **`rl_run_autodetect`** | Trigger the auto-detect workflow (capabilities, specials defaults). | Per-device probes; mostly sequential `OPC_STATUS` and `OPC_CONFIG`. |

The four quickbuttons are **static** — they're registered once on
plugin load and never re-registered. State changes do not refresh
them.

---

## The `rl_quickset` panel

Lives in RotorHazard's *Run* view. Same bootstrap-once-then-refresh
selectively pattern as `rl_settings`.

| Field | Type | Refreshes on |
|---|---|---|
| **`rl_quickset_group`** | SELECT | `GROUPS` scope (group renamed, added, deleted) |
| **`rl_quickset_preset`** | SELECT | `PRESETS` scope (WLED preset list reloaded, RL preset CRUD) |
| **`rl_quickset_brightness`** | RANGE 0–255 | Static — never refreshed |

The `rl_quickset_group` dropdown lists every configured group plus
an **"All Devices (Broadcast)"** entry that maps to the wire
broadcast (`recv3=FFFFFF`, `groupId=255`). Selecting it sends one
packet to the whole fleet. This label is the unified vocabulary
across the WebUI scene editor and every RH-plugin group dropdown
(see [Glossary — All Devices (Broadcast)](../glossary.md#all-devices-broadcast)
and the full per-opcode rules in
[Broadcast Ruleset](../reference/broadcast-ruleset.md)).

> **Migration note.** Older plugin builds labelled this entry
> "All WLED Nodes". The string was renamed for accuracy on
> mixed-capability fleets (broadcast packets are accepted by
> every device class, not WLED only — capability-aware addressing
> is on the [Roadmap](../roadmap.md#capability-agnostic-broadcast-addressing)).
> Existing backup files keep loading; the loader recognises both
> names during the transition.

| Button | What it does |
|---|---|
| **`run_quickset`** | Apply the selected preset + brightness to the selected group (or to **All Devices (Broadcast)**). One-shot, immediate. |

The Quickset is **deliberately preset-focused** in v1. Scenes are
NOT in the Quickset panel — they live as ActionEffects (see below).
This is intentional: Quickset is "fire one effect at one group
right now"; Scenes are "play a saved sequence", which is a different
mental model.

---

## ActionEffects — binding race events to RaceLink

ActionEffects are RotorHazard's mechanism for "when this event
fires, do that thing". Each ActionEffect carries one or more
SELECT fields — RotorHazard's own UI lets the operator bind events
(race start, heat advance, etc.) to specific ActionEffect
configurations.

The plugin registers three ActionEffect kinds:

### `gcaction` — default group action

Apply a WLED preset to a group when an event fires. Two SELECT
fields: `rl_action_group` (which group) and `rl_action_effect`
(which preset).

Refreshes on `GROUPS` and `PRESETS` scope events.

Use case: "On `RACE_START`, apply preset 'Race Start' to group
'Pit Wall'."

### Per-capability special actions

Per device-capability ActionEffects (auto-generated from
`RL_SPECIALS` registry). Each capability — `WLED`, `STARTBLOCK` —
gets its own ActionEffect with capability-specific fields.

Refreshes on `GROUPS` (group-list affects target dropdown),
`DEVICES` (device-list affects target dropdown for unicast
actions), `DEVICE_MEMBERSHIP`, and `PRESETS` scope events.

Use case: "On `HEAT_ADVANCE`, send the startblock 'next-heat'
program to all `STARTBLOCK`-capable devices in 'Start Line'."

### `rl_scene_action` — RaceLink Scene

The most powerful ActionEffect: pick a saved scene and run it.
Single SELECT field: `rl_action_scene` (scene picker).

Refreshes on `SCENES` scope (scene CRUD).

Use case: "On `RACE_START`, run scene 'Race Start Cascade'."
This is how multi-action choreographies get bound to events:
author the scene in the WebUI, then bind it to the event in
RotorHazard.

---

## State refresh — what gets updated when

Each persisted state change in the host carries a **scope token**.
The plugin's `apply_scoped_update(scopes)` routes each token to
the minimal set of UI element re-registrations.

The full per-element matrix:

| RH UI element | `FULL` (boot) | `GROUPS` | `DEVICES` | `DEVICE_MEMBERSHIP` | `DEVICE_SPECIALS` | `PRESETS` | `SCENES` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Panel `rl_settings` | ✓ | | | | | | |
| Panel `rl_quickset` | ✓ | | | | | | |
| Field `rl_device_config` | ✓ | | ✓ | ✓ | | | |
| Field `rl_groups_config` | ✓ | ✓ | | ✓ | | | |
| Field `rl_assignToGroup` (dynamic) | ✓ | ✓ | | | | | |
| Field `rl_assignToNewGroup` (static) | ✓ | | | | | | |
| Field `rl_quickset_group` (dynamic) | ✓ | ✓ | | | | | |
| Field `rl_quickset_preset` (dynamic) | ✓ | | | | | ✓ | |
| Field `rl_quickset_brightness` (static) | ✓ | | | | | | |
| Quickbutton `rl_btn_*` (static, all 4) | ✓ | | | | | | |
| ActionEffect `gcaction` | ✓ | ✓ | | | | ✓ | |
| Per-capability ActionEffects | ✓ | ✓ | ✓ | ✓ | | ✓ | |
| ActionEffect `rl_scene_action` | ✓ | | | | | | ✓ |

Reading the table: when the operator renames a group, the plugin
fires the `GROUPS` scope. The plugin re-registers
`rl_groups_config`, `rl_assignToGroup`, `rl_quickset_group`,
`gcaction`, and the per-capability ActionEffects — but NOT the
quickbuttons, the device-config field, the brightness slider, or
the scene-action.

This is what fixes the cursor-position-loss / scroll-reset bug
class — pre-D4, every state change re-registered everything,
including elements RotorHazard re-renders eagerly.

For the host-side state-scope token reference, see
[`../reference/sse-channels.md`](../reference/sse-channels.md) and
[`../RaceLink_Host/architecture.md`](../RaceLink_Host/architecture.md) §"UI Scope
Matrix".

---

## Lifecycle inside RotorHazard

### Plugin startup

1. RotorHazard fires `Evt.STARTUP`. The plugin wires the host's
   `onStartup` to this event.
2. `onStartup` runs `discoverPort({})` — claims the gateway USB
   port with `exclusive=True`.
3. The plugin registers the two panels and all ActionEffects
   (`FULL` scope).
4. The plugin subscribes to the host's `on_persistence_changed`
   callback to receive scope tokens for selective refreshes.
5. The shared WebUI mounts at `/racelink/` via
   `racelink.web.register_racelink_web()`.

If `discoverPort` fails (gateway not present), the plugin still
loads. The `rl_settings` panel renders, but the device list is
empty and the master pill in the WebUI shows red. Operator
intervention required.

### Plugin shutdown

Two paths:

1. **`Evt.SHUTDOWN`** — RotorHazard fires this on graceful
   shutdown. The plugin calls `controller.shutdown()` which closes
   the transport (releases the USB port).
2. **`atexit` hook** — registered in addition to the
   `Evt.SHUTDOWN` callback. Catches Hot-Reload, SIGTERM,
   KeyboardInterrupt — situations where `Evt.SHUTDOWN` may not
   fire. Without this, the next plugin start sees `PORT_BUSY`
   because the previous instance leaked the exclusive lock.

The `controller.shutdown()` is idempotent — duplicate fires are
harmless.

### RotorHazard restart while WebUI is open

This used to be a sticky-banner trap: the WebUI showed
"RaceLink Gateway is not available" indefinitely until the operator
manually clicked **Retry connection**. Post-lifecycle-redesign:

1. Operator restarts RotorHazard.
2. RotorHazard's HTTP / SSE goes dark for ~3 s.
3. WebUI shows transient banner "RotorHazard not reachable —
   retrying …" within 3 s.
4. WebUI's SSE auto-reconnect probes `/api/health` with backoff
   (1 s → 2 s → 4 s → 8 s → 10 s clamp).
5. Once RotorHazard is back and the plugin has booted, SSE
   reconnects, banner clears, "Connection re-established" toast
   shows. Operator did nothing.

If the gateway port lock didn't release in time (`PORT_BUSY`), the
gateway-status banner stays transient with auto-retry countdown
2 s → 5 s → 10 s → 20 s → 30 s. Once the old process finally
releases the port, the next auto-retry succeeds. Operator still
did nothing.

For the full lifecycle / banner matrix see
[`../RaceLink_Host/webui-guide.md`](../RaceLink_Host/webui-guide.md)
§"Lifecycle resilience".

---

## Race-day workflow — what to do when

### Pre-race setup (between events)

Use the **shared WebUI** at `/racelink/` for setup:

1. Discover devices (also reachable via `rl_btn_get_devices`).
2. Author RL presets — *Manage RL Presets* in the WebUI.
3. Author scenes — Scenes page in the WebUI.
4. Bind events to scenes / actions — RotorHazard's settings UI,
   using the ActionEffects registered by the plugin.
5. Optional: firmware update — OTA dialog in the shared WebUI.

### Race day

Use the **side panels** for the common operations:

* **Discover** if a node was reflashed / moved → `rl_btn_get_devices`.
* **Re-sync groups** if the network state has drifted →
  `rl_btn_force_groups`.
* **Quickset preset+brightness** to a group → the `rl_quickset`
  panel.
* **Set defaults** to put everything into a known state →
  `rl_btn_set_defaults`.

Race events fire automatically via the bindings configured pre-race.

### Troubleshooting during a race

* If something visibly misbehaves, **check the master pill** in
  the shared WebUI's header. ERROR / LINK_LOST tells you where to
  look.
* Use **Get Status** (Quickbutton or WebUI) to check device
  reachability.
* If a node is stuck in offset mode (a previous cascade scene
  didn't clean up), run a `offset_group(mode=none)` scene to
  flush state. See
  [`../concepts/opcodes.md`](../concepts/opcodes.md)
  §"Leaving offset mode".

---

## Online vs. offline installation — operator notes

The plugin distributes in two forms; the runtime behaviour is
identical, only the install path differs.

| Mode | What happens at install | What changes for the operator |
|---|---|---|
| **Online** | RotorHazard fetches the plugin and resolves the host wheel from the immutable Git tag in `manifest.json`. Requires internet. | None — the plugin works the same way. |
| **Offline** | Release ZIP carries the host wheel under `custom_plugins/racelink_rh_plugin/offline_wheels/`. First plugin start unpacks and installs the bundled wheel into RotorHazard's Python environment. | First plugin start takes a moment longer (~10–20 s) while the wheel installs locally. Subsequent starts are normal. |

Both modes load `racelink-host` from the **same** RotorHazard
Python environment — there is no separate venv. Once installed,
they're indistinguishable at runtime.

For the install / release flow, see
[`README.md`](README.md) §"Installation Modes" and the
[release playbook](release-playbook.md).

---

## Limitations / known caveats

* **Quickset doesn't show scenes.** v1 design. Scenes are
  ActionEffects only; if you want a "fire scene from Run view",
  bind a scene to a custom event or use the *Run* button in the
  shared WebUI.
* **No history of run results.** Per-action SSE progress is
  emitted in real time but not persisted. Each run shows in the
  scene-editor strip, but there's no run-log audit trail.
* **`OFFSET_MODE` flag in scene-action `flags_override`** is a
  no-op until the WLED-side semantics are fully implemented. The
  flag round-trips but the device behaviour is the same as without
  it. (The *container action* `offset_group` works fully — only
  the per-action `flags_override.offset_mode` toggle is the
  no-op.)
* **One scene at a time.** Running a second scene while the first
  is still executing returns HTTP 409 Conflict. Future revision
  may queue.
* **No cross-host scene replication.** Each host owns its own
  scenes. If you have multiple RotorHazard installations, copy the
  `~/.racelink/scenes.json` manually.

---

## Common problems

### `RHUI Redefining panel/setting/quickbutton ...` log spam

Should not happen post-D4. If it does, the bootstrap-flag mechanism
in the plugin's `ui.py` is regressed — file a bug. Workaround:
restart RotorHazard.

### "RaceLink Gateway is not available" stays red after RH restart

Click **Retry connection** in the WebUI's gateway-status banner.
The plugin's startup hook claims the gateway on `Evt.STARTUP`; if
the event sequence misfires, the manual retry forces another
`discoverPort` attempt.

### `PORT_BUSY` on plugin start

Another process owns the dongle. Most commonly:

* `racelink-standalone` left running from a previous test session.
* A Hot-Reload during plugin development that didn't fire
  `Evt.SHUTDOWN`. The `atexit` hook should catch this — but if a
  crash occurred before atexit ran, the kernel may briefly hold
  the lock. Wait 30 s, **Retry connection**.

### Quickset shows stale dropdowns

A state-scope sync failure during plugin bootstrap. Trigger any
state change (e.g. a Discover) — the targeted refresh should
populate the dropdowns. If not, restart RotorHazard.

### Devices appear in the WebUI but not in the RH `rl_device_config`

Scope-routing bug: the host fired `DEVICES` but the plugin didn't
re-register `rl_device_config`. Check the plugin log for
exceptions in `apply_scoped_update`. As a workaround, restart
RotorHazard — bootstrap fires a `FULL` scope which resyncs
everything.

For the broader troubleshooting index, see
[`../troubleshooting.md`](../troubleshooting.md).

---

## See also

* [`README.md`](README.md) — installation / development setup /
  release flow.
* [`../RaceLink_Host/operator-guide.md`](../RaceLink_Host/operator-guide.md) — full
  operator workflow inside the shared WebUI.
* [`../RaceLink_Host/webui-guide.md`](../RaceLink_Host/webui-guide.md) —
  shared WebUI structure and lifecycle.
* [`../concepts/opcodes.md`](../concepts/opcodes.md) — wire-opcode
  pragmatic explanations.
* [`../RaceLink_Host/architecture.md`](../RaceLink_Host/architecture.md) §"UI Scope
  Matrix" — the full state-scope routing matrix.
* [ADR-0001](adr-0001-manifest-dependency.md)
  — why the manifest uses `git+https://`.
