# Authoring scenes & RL presets

The companion to [`operator-guide.md`](operator-guide.md). Once your
devices are discovered, grouped, and any per-device Specials are
configured, this guide walks the scene-editor side: building RL
presets, composing scenes, the target picker, offset mode, the
run flow, and the scope-on-multi-network behaviour.

> **Audience.** Operators who already have devices on the wire
> (steps 1–4 of the operator guide) and now want to author the
> effects they fire during a race.

For the on-disk shape of `scenes.json` see
[`../reference/scene-format.md`](../reference/scene-format.md).
For the WebUI's "what's on screen" tour see
[`webui-guide.md`](webui-guide.md).

## Author RL presets

Open the **RL Presets** dialog from either page header. RL presets
are host-stored named snapshots of effect parameters — definition in
[`../glossary.md`](../glossary.md#preset) §"Preset". Compared with
inlining 14 parameters into every scene action, an RL preset is
named, reusable across scenes, and easier to tweak.

Click **+ New** in the dialog, name your preset, dial in the
effect parameters, click **Save**. The cost-estimator badge in
the scene editor will show roughly how many bytes each
application costs; that's your guide if you need to fit a
multi-action scene under tight LoRa airtime.

RL presets are referenced by name from scene actions; renaming a
preset re-points every scene action that uses it automatically —
the host re-writes scene records when the preset record changes.

## Author scenes

Open the **Scenes** page (link in the header). Click **+ New**
in the sidebar to start a new draft.

* Set the **Label** (free-form text).
* Click **Add action** at the bottom of the list to append a new
  action. To insert an action in the middle of an existing scene,
  hover the gap between two rows — a thin **+ Insert action** chip
  appears in the gap; clicking it opens a compact kind picker right
  there, so you don't have to append at the bottom and drag the
  new row up.
* Use the **Duplicate** icon on any action row to clone it directly
  below the original. Handy for repeating a preset with a different
  target, or building chains of similar steps without re-entering
  every field. Inside an `Offset Group`, the same Duplicate button
  is available on each child row.
* Each action picks a **kind** (Apply RL Preset, Apply WLED
  Preset, Sync, Delay, Offset Group, etc.) and configures its
  target and parameters via the [unified target
  picker](#the-target-picker-broadcast--groups--device).
* The **Offset Group** action is the container action: drop child
  actions inside it (`Apply RL Preset`, etc.), pick which groups
  participate (via the same target picker), and configure the
  per-group offset (linear, v-shape, modulo). The cost badge
  updates to reflect the wire-optimisation strategy the runner
  will pick at run time.
* The cost badge under each action shows packets / bytes /
  airtime; the scene-total badge in the header shows the sum.
  The tooltip explains the LoRa parameters used for the airtime
  estimate.
* Click **Save** (or **Create** for a new scene). Drafts are
  preserved across page reloads as long as you don't close the
  tab — but the unsaved-changes warning fires on
  refresh / close / nav-away if you have edits.

## The target picker: Broadcast / Groups / Device { #the-target-picker-broadcast--groups--device }

Every action that targets devices uses the same picker — three
radios with the matching value picker below:

* **Broadcast** — every device on the wire receives the packet.
  No value picker; one packet hits the whole fleet (`recv3=FFFFFF`,
  `groupId=255`). The cheapest wire path; pick this when the
  effect is meant for everyone.
* **Groups** — pick one or more groups via a search dialog.
  Length-1 is the common case (a single group); longer lists
  fan out one packet per group at the wire. The action body
  shows a compact summary — `N groups · M devices` plus the
  selected group names in small text — and an **Edit groups…**
  button opens the dialog. Inside the dialog:
    * a **search field** filters the list by name or id (live);
    * three batch buttons act on the currently-visible
      *hits*: **Select all hits**, **Deselect all hits**,
      **Invert hits**. Combined with the search, this is how
      you do bulk operations on large fleets ("everything
      starting with `tower-`", "everything except group 7", …);
    * **Apply** writes the selection back; **Cancel** drops
      the edit. The footer shows the total before you confirm
      and warns if you've selected every known group — the
      host's save-time canonicaliser then rewrites the persisted
      target to **Broadcast** so the runtime and the cost
      badge agree on the wire path. If you want a *frozen*
      subset (one that will *not* automatically include any
      group added later), un-check at least one group.
* **Device** — pick one device from a MAC dropdown. The host
  sends with the device's stored `groupId`, surfacing any drift
  between the host's repository and the device's actual state
  (a misconfigured device drops the packet rather than the host
  silently masking the inconsistency — see the [Single-device
  pinned rule](../reference/broadcast-ruleset.md#single-device-pinned-rule)
  in the Broadcast Ruleset).

The picker hides **Device** at the **Offset Group** container
level — the offset formula is per-group, so a single-device
container target is invalid. Children inside an Offset Group
get the full picker again, with **Groups** filtered to the
parent's participating set.

The cost badge below each action shows packets / bytes / airtime.
For Offset Group containers it also reports the optimizer's
chosen wire path (Strategy A / B / C) so you can see whether the
broadcast formula or per-group fan-out won.

## Working with offset mode { #working-with-offset-mode }

The **Offset Group** action is the right tool when you want
different groups to start the same effect at different moments
(typical use: a "wave" or "cascade" along a row of gates). The
container has three configuration parts:

* **Participants** (target picker, Broadcast / Groups): which
  groups receive the offset. **Broadcast** covers every known
  group (cheapest wire path); **Groups** picks a subset.
* **Mode**: the formula that turns each device's groupId into a
  per-device delay in milliseconds. Five options:
  * **`linear`** — `offset = base + groupId × step`. A straight
    cascade: group 0 fires first, group 5 fires `5 × step` ms
    later.
  * **`vshape`** — `offset = base + |groupId − center| × step`.
    A V around `center`: groups closest to the center fire first.
  * **`modulo`** — `offset = base + (groupId % cycle) × step`.
    Repeating cycle of length `cycle`.
  * **`explicit`** — give each participating group its own
    `offset_ms` value. Most flexible, most setup.
  * **`none`** — clear any previously-configured offset on the
    participants. The children inside the container then play
    immediately with no offset shift. This is the "deactivate
    offset mode" workflow.
* **Children**: actions to dispatch with the offset applied.
  Children typically have `arm_on_sync` enabled; they queue on
  the device, then fire all at once (offset-shifted) when the
  next `Sync` action runs.

### Important: offset mode is sticky

Once a device has executed an `Offset Group` action with a
non-`none` mode, it is **in offset mode** until you explicitly
take it out. The firmware enforces this rule strictly:

* Normal (non-`offset_group`) actions are **silently dropped**
  on devices in offset mode. The masterbar shows TX activity
  but the devices don't react.
* `Offset Group` actions with a non-`none` mode reach those
  devices (and reach exactly them — the broadcast targeting
  optimisation depends on this).
* Only an `Offset Group` action with `mode=none` transitions
  the device out of offset mode.

This is by design: state changes between "in offset mode" and
"not in offset mode" are explicit operator actions, not
side-effects of regular dispatch. Without this rule the
broadcast targeting (one wire packet hitting only the
offset-configured groups) wouldn't work.

### Clearing offset mode

An `Offset Group` action with `mode=none` and at least one
child does **two things in one scene**:

1. Sends `OPC_OFFSET(NONE)` to the participants. This sets
   `pendingChange.mode = NONE` on each device.
2. Sends each child with the `OFFSET_MODE` flag set to `0`.
   The strict gate accepts these (because pending=NONE matches
   `F=0`), and on materialisation (PRESET dispatch, or SYNC
   after an `arm_on_sync` CONTROL child) the active state
   transitions to `NONE` too.

After this action runs, the participants are out of offset
mode and accept normal (non-`offset_group`) packets again.

**You cannot clear offset mode with a normal action.** If your
scene has e.g. a plain `Apply WLED Preset` after an
`Offset Group(linear)`, the preset is silently dropped on the
offset-configured devices. The fix is to insert an
`Offset Group(mode=none, children=[…])` before the preset.

**Pure clear without an effect**: if you want to clear without
playing anything visible, use `mode=none` with a placeholder
child (e.g. `rl_effect` with `mode=0`, `brightness=0` so
nothing lights up). The `OPC_OFFSET(NONE)` packet is what
clears; the placeholder child carries `F=0` to materialise the
transition.

**Sticky offset on children**: a child action's `offset_mode`
flag is decided by the parent's `mode`, not by per-child
`flags_override`. Setting `offset_mode=False` in a child's
override is a no-op — the parent's `mode != "none"` always
wins. This is intentional; mixing on/off children inside one
offset_group makes the gate arithmetic operator-hostile.

### Operator workflow rule of thumb

Run scenes in this order when mixing offset and normal
effects:

1. `Offset Group(mode=linear/etc.)` — set up offset for the
   targeted groups, queue effects, fire SYNC.
2. (Optional) more `Offset Group` scenes — change the formula
   or the queued effect; offset mode stays.
3. `Offset Group(mode=none, children=[…])` — exit offset mode.
4. Normal scenes — work as expected on the now-cleared
   devices.

If a normal scene "doesn't do anything" but the masterbar
shows TX activity, the targets are probably still in offset
mode. Run an `Offset Group(mode=none)` first.

## Run a scene

With a saved scene selected in the sidebar, click **Run**. The
master pill goes to **TX**; the action rows in the editor
border-colour green (ok), red (error), or amber (degraded) as
the run progresses. Run summary lands in the **Last run**
status line.

The Run button (and Save / Duplicate / Delete) disable for the
duration of the run so you can't queue up a duplicate by
mis-clicking.

### "Stop on error" (default ON)

Each scene carries a **Stop on error** checkbox in its meta
row, default checked. Behaviour:

* **Checked (default)**: the runner aborts the scene the
  moment any action fails. Remaining actions are marked
  **skipped** (greyed pips in the run-progress strip) and the
  status line reads e.g.
  *"Last run: aborted at action #3 (tx_rejected: txPending).
  Remaining actions skipped — uncheck 'Stop on error' to play
  through."*
  This is the safer default: a half-failed sequence usually
  leaves the network in a state that doesn't match operator
  intent, so further sends just waste air-time.
* **Unchecked**: legacy behaviour. Every action runs regardless
  of earlier failures. Useful for scenes where each action is
  independent (e.g. a snapshot dump where you want every device
  reached even if a few don't ACK).

A `degraded` outcome (e.g. an action targets a device the host
doesn't know) does **not** trigger the abort — degraded means
"ran with caveats", not "didn't run". Only outright `ok=False`
terminates.

### Scene scope on multi-network setups

When you have multiple gateways attached, every scene carries a
**Scope** chip in the editor header (next to "Stop on first
error"). Click it to choose between **Auto** and **Explicit**:

* **Auto** (default) — the host computes the scope from the
  scene's other action targets at runtime. The chip shows what
  Auto currently resolves to (e.g. *"Auto · TrackA + TrackB"*).
  The displayed preview updates live as you edit actions.
* **Explicit** — pin the scope to a specific set of networks via
  the dialog's checkbox list. The chip then shows the pinned
  names (e.g. *"Explicit: TrackA"*). Per-action target pickers
  immediately filter their group/device dropdowns to in-scope
  networks only — out-of-scope choices disappear.

**When to use Explicit:**

* A "fleet trigger" scene that should only fire on one race's
  network even though devices on neighbouring networks exist.
* A `broadcast`-target action (group 255) that you want to scope
  to a subset of networks instead of letting it reach the whole
  fleet (Auto sends a `broadcast` target to all persisted networks).
* Anti-mistake: if your scene already targets a single network's
  groups, Explicit-pin it so a future edit that adds an action
  for another network can't silently expand the scope.

**What happens if you switch from Auto to a smaller Explicit
scope and existing actions now target out-of-scope devices?** The
editor flags those rows with an *"out of scope"* warning chip and
a red border on the target picker. Save is allowed to attempt —
the server returns HTTP 400 with the offending action's row
highlighted; either widen the scope or fix the action.

**What happens if you delete a network that a scene's Explicit
scope still references?** The sidebar shows a small amber dot
next to that scene's name. Opening it surfaces the stale id with
a remove-X. The runtime soft-filters the missing id; if all ids
in the scope were stale, the scene's broadcasts are recorded as
degraded (`error="scope_resolved_empty"`) rather than silently
widening back to "every gateway".

**Fan-out indicator.** When a scene's broadcasts will hit 2+
gateways (Auto or Explicit), a small green *"Fan-out: 2
gateways"* pill appears under the header. Hover for the network
names. The LoRa airtime cost stays the same as a single-network
broadcast — workers run in parallel, so wall-clock airtime is
bounded by the slowest single radio.

For the wire-format details + degradation rules table see
[`multi-network.md` §"Scene broadcast scope"](multi-network.md#scene-broadcast-scope).

### Measured run-time alongside estimates

After a successful run, the cost badges (per-action and the
scene-total in the header) extend with an "actual: NNN ms"
fragment in highlighted text:

```
≈ 3 pkts · 84 B · 12 ms · actual: 47 ms
```

The "≈ X ms" is the *estimated LoRa airtime* (Semtech
AN1200.13). The "actual: NNN ms" is the *measured wall-clock
duration* of that action on the most recent run, including USB
latency, gateway LBT random backoff, and any host-side runner
overhead. The two numbers are not directly comparable — the
delta is the cost of going through the radio stack rather than
just transmitting bits — but a hover tooltip shows the
breakdown:

```
Last run: 47 ms wall-clock (estimate 12 ms · +35 ms overhead).
```

The actual values stick to the badges until you load a different
scene, create a new draft, or run the same scene again (which
overwrites them). Edits to the draft do not invalidate the
measurements; the cost-estimate side updates live, but "actual"
keeps showing the last run's data so you can compare before/after
tweaks.

## Common scene-editor pitfalls

### "Run reports OK but nothing happens"

* The action targeted a group with no capable devices. The
  editor's cap filter prevents this in new scenes, but old
  scenes may not have been edited since the filter shipped.
  Re-edit the scene; the dropdown will tell you which groups
  have the capability.
* The target devices are offline (red pill in the device
  table). The runner doesn't know that — it just sends the
  packet. Refresh the device table (Get Status) to see who's
  actually reachable.
* The target devices are still **in offset mode** from a
  previous `Offset Group(linear/etc.)` and the current action
  is a normal (non-`offset_group`) action. Insert an
  `Offset Group(mode=none, children=[…])` to clear — see
  [§"Clearing offset mode"](#clearing-offset-mode).

### "Scene editor says I have unsaved changes but I just saved"

A successful save resets the unsaved-changes flag. If the prompt
fires anyway, you've changed something since the save (added a
character, dragged an action, etc.). The dirty check is byte-
exact on the canonical scene shape; even whitespace in the
label counts.

### "The cost badge says ≈ 50 ms airtime but my scene takes 5 seconds"

The cost badge shows *radio airtime* — how long the LoRa packets
spend in the air. Delays (`Delay` action) and host-side waits
(scene runner inter-action gaps) aren't included. The sum of
delays + airtime is roughly your end-to-end run time.

## Limits

* **Actions per scene**: 20 (configurable in `scenes_service.py`
  if you have a reason).
* **Children per offset_group**: 16.
* **Brightness**: 0–255.
* **Effect parameters**: 0–255 each.
* **Group ids**: 1–254 (0 is Unconfigured, 255 is broadcast).
* **Preset ids**: 0–255.

For the gateway / OTA / network-level limits see
[`operator-guide.md` §"Where the limits are"](operator-guide.md#where-the-limits-are).
