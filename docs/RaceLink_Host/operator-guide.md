# RaceLink Operator Guide

You've installed RaceLink and pointed your browser at the host's
WebUI. This guide walks you from "no devices yet" to "scenes firing
on the LED nodes" without assuming you've seen the source.

> The other docs in this folder are for *contributors*. This one
> is for *operators*. If you find yourself looking at the C header
> to understand what a button does, the WebUI has failed and the
> bug is on us.

## Glossary

The WebUI uses these terms consistently. Memorising the four
**bold** ones gets you 90% of the way through the rest of the doc.

* **Device** — one piece of RaceLink hardware (a WLED node, a
  starting-block, etc.). Identified by its 12-character MAC
  address; the host shows the last 6 in the table for
  brevity. Has a *type* (which determines what it can do — see
  *capability* below).
* **Group** — a named bucket of devices. Operators usually group
  by physical location ("Pit Wall", "Start Line", "Tower 3"). The
  group is what most scene actions target — sending a packet to
  a group broadcasts to every device whose `groupId` matches.
* **Group `0` / "Unconfigured"** — the synthetic group every
  newly-discovered device starts in. Devices in group 0 cannot
  be the target of a scene action; assign them to a real group
  before you save scenes. The scene editor automatically hides
  group 0 from its dropdowns.
* **Capability** — what a device can do, derived from its type.
  Today: `WLED` (LED control), `STARTBLOCK` (race start
  hardware). A starting-block is also `WLED`-capable; a plain
  WLED node is not `STARTBLOCK`-capable. The scene editor
  filters target dropdowns by capability so you can't pick a
  non-capable target by accident.
* **Preset** — *two distinct things* with the same word, sadly:
  * **WLED preset** — a numeric slot (0–255) on a WLED node's
    own preset list, set up via WLED's web interface. Apply via
    the `Apply WLED Preset` scene action, which sends an
    `OPC_PRESET` packet carrying just the slot number.
  * **RL preset** — a RaceLink-native named snapshot of effect
    parameters (mode, speed, intensity, colours, etc.). Stored
    on the host. Apply via `Apply RL Preset`; the host
    materialises the parameters and sends an `OPC_CONTROL`
    packet.
* **Scene** — a saved playlist of *actions* that runs in order.
  Persisted on the host; runnable via the Run button on the
  scenes page.
* **Action** — one step in a scene. Kinds:
  * `Apply WLED Preset` — load a numeric WLED preset on the
    target.
  * `Apply RL Preset` — load an RL preset (effect parameters)
    on the target.
  * `Apply WLED Control` — direct effect parameters in-line
    (no separate preset record).
  * `Startblock Control` — send a starting-block program.
  * `SYNC (fire armed)` — fire all devices waiting on
    arm-on-sync.
  * `Delay` — host-side wait between actions.
  * `Offset Group` — container action that runs its children
    with per-group time offsets (e.g. a chase / wave effect).
* **Offset Group** — the most powerful action kind: lets you
  fire the same effect on N groups but with each group offset
  by a few ms so you get a wave / cascade effect instead of a
  simultaneous fire.
* **Specials** — per-device-type configuration knobs (e.g.
  startblock display brightness, WLED-specific options). Edit
  via the device's Specials dialog.
* **Master pill** — the coloured badge in the page header
  showing the current gateway state (IDLE / TX / RX / ERROR).
  Hover for the full explanation.
* **Gateway** — the USB dongle that bridges the host to the
  LoRa fleet. The host owns it exclusively while running.

## End-to-end workflow

A first-time setup looks like this:

### 1. Confirm the gateway is connected

Before opening the WebUI, plug in the USB-LoRa dongle. The host
auto-discovers it on startup. Open the WebUI; the master pill in
the header should be **IDLE** (cyan). If it's red with a banner
saying *"RaceLink Gateway is not available"*:

* If the cause is `PORT_BUSY`: another process is using the
  dongle. Close it and click **Retry connection**.
* If the cause is `NOT_FOUND`: the dongle isn't plugged in or
  the OS hasn't enumerated it yet. Plug in or wait and click
  **Retry connection**.
* If the cause is `LINK_LOST`: the dongle was working but
  disappeared. The host auto-retries with backoff; the banner
  shows the next retry countdown.

#### Master pill states (Batch B, 2026-04-28)

The pill mirrors the gateway's reported state byte 1:1 — the host
no longer infers the state from outcome events. The five states
the pill can show:

| Pill | Meaning |
|---|---|
| **IDLE** (cyan) | Gateway is in continuous RX, ready for the next host send. |
| **TX** (purple) | Gateway is transmitting (between scheduling and tx-done; LBT backoff + airtime). |
| **RX-WIN** (yellow) | Gateway has a bounded RX window open after a unicast/stream send and is waiting for a node reply. The detail line shows `min_ms <N>` (the window size). |
| **RX** (yellow) | `setDefaultRxNone` mode only — actively receiving. The current default firmware doesn't use this state. |
| **ERROR** (red) | Gateway reported a fault. May be transient (USB hiccup) or persistent (link lost); the detail line names the cause. |
| **UNKNOWN** (muted) | Pre-`STATE_REPORT` sentinel — host hasn't received a reply yet. Click ↻ to refresh. |

Next to the pill is a small **↻** refresh button: click it to
send a `GW_CMD_STATE_REQUEST` and resync the pill from the
gateway's reply (~500 ms round-trip). Useful after a USB
reconnect or whenever the displayed state looks wrong.

### 2. Discover devices

In the page header, click **Discover Devices**. A modal opens
asking which group to assign newly-found devices to. Pick
"Unconfigured" (the default) for the first run — you'll move
them later.

Click **Start**. The host fires a broadcast and waits a few
seconds for replies. The masterbar's task line shows progress
(`discover…`). When done, the device table populates with every
node that responded.

If no devices show up:

* Check the master pill — if it cycles through TX → RX → IDLE,
  the host did transmit and the window opened, but no nodes
  replied. The devices may be off, out of range, or paired to a
  different gateway MAC.
* Each node is paired to one gateway by MAC at first boot. If a
  device used to talk to a different gateway, use **Forget master
  MAC** (Node Config dropdown → "Forget master MAC" → Send) to
  un-pair it; then re-discover.

### 3. Create groups and assign devices

* Click the **+** in the Groups sidebar to create a real group
  ("Pit Wall", "Start Line", whatever fits).
* Tick the devices you want to assign in the device table.
* In the toolbar, pick the new group from the **Move selected to
  group** dropdown and click **Move**. Confirm the prompt — the
  count and target are shown for sanity.
* Repeat per group.

Once devices are in real groups, you can use **Re-sync group
config** (header button) to broadcast every device's stored
groupId back to the network. This is the recovery action when
nodes have been reflashed or moved between gateways and their
in-radio state has drifted from the host's view of them.

### 4. Configure devices (optional)

The **Specials** column in the device table is a button you click
to open per-device options. WLED nodes have brightness defaults,
mode preferences, etc.; starting-blocks have display brightness,
slot configuration, etc. Each option carries its own help text;
edit and click **Save** within the dialog.

### 5. Author RL presets (optional but recommended)

Open the **RL Presets** dialog from either page header. Each RL
preset is a named snapshot of `(effect mode, speed, intensity,
colours, brightness, flags)`. They live on the host, can be
applied to any WLED-capable target by name in scenes, and are
much easier to tweak than passing 14 parameters in a scene
action every time.

Click **+ New** in the dialog, name your preset, dial in the
effect parameters, click **Save**. The cost-estimator badge in
the scene editor will show roughly how many bytes each
application costs; that's your guide if you need to fit a
multi-action scene under tight LoRa airtime.

### 6. Author scenes

Open the **Scenes** page (link in the header). Click **+ New**
in the sidebar to start a new draft.

* Set the **Label** (free-form text).
* Click **Add action** to append actions in order.
* Each action picks a **kind** (Apply RL Preset, Apply WLED
  Preset, Sync, Delay, Offset Group, etc.) and configures its
  target and parameters via the [unified target
  picker](#the-target-picker-broadcast--groups--device).
* The **Offset Group** action is the powerful one: drop child
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

### The target picker: Broadcast / Groups / Device { #the-target-picker-broadcast--groups--device }

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

### 6a. Working with offset mode

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

#### Important: offset mode is sticky

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

#### Clearing offset mode

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
child (e.g. `wled_control` with `mode=0`, `brightness=0` so
nothing lights up). The `OPC_OFFSET(NONE)` packet is what
clears; the placeholder child carries `F=0` to materialise the
transition.

**Sticky offset on children**: a child action's `offset_mode`
flag is decided by the parent's `mode`, not by per-child
`flags_override`. Setting `offset_mode=False` in a child's
override is a no-op — the parent's `mode != "none"` always
wins. This is intentional; mixing on/off children inside one
offset_group makes the gate arithmetic operator-hostile.

#### Operator workflow rule of thumb

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

### 7. Run a scene

With a saved scene selected in the sidebar, click **Run**. The
master pill goes to **TX**; the action rows in the editor
border-colour green (ok), red (error), or amber (degraded) as
the run progresses. Run summary lands in the **Last run**
status line.

The Run button (and Save / Duplicate / Delete) disable for the
duration of the run so you can't queue up a duplicate by
mis-clicking.

#### "Stop on error" (default ON)

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

**Measured run-time alongside estimates.** After a successful
run, the cost badges (per-action and the scene-total in the
header) extend with an "actual: NNN ms" fragment in highlighted
text:

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

## Safety rules

These are the things that go *wrong* if you skip them. None of
them require manual cleanup — the system recovers — but they cost
you minutes you don't have during a race.

### Don't unplug the gateway USB while a scene is running

The host detects the disconnect within ~50 ms and aborts the
scene; the master pill goes red with `LINK_LOST`. The fleet
continues whatever it was last asked to do (effects loop on
their own) but you can't change anything until the gateway
reconnects. Plug back in; the host auto-retries.

### Firmware updates take minutes; let them finish

The Firmware Update dialog stays open during the OTA. Per device,
the host:

1. Sends an `OPC_CONFIG` to enable the device's WLED AP and waits
   for the device to ACK it (so the host doesn't start scanning
   before the AP is actually broadcasting).
2. Scans for any of the SSIDs in the dialog's SSID field
   (default `WLED_RaceLink_AP, WLED-AP` — newer firmware
   broadcasts the first, older firmware the second; the host
   takes the first one it sees) and connects with the password
   from the dialog (default `wled1234`).
3. Verifies the node's MAC via `/json/info`.
4. Uploads the firmware binary.
5. (Optional) Uploads `presets.json` and/or a `cfg.json`.
6. Sends an `OPC_CONFIG` to disable the AP again.
7. Disconnects the host's WiFi from the WLED AP and (if you
   ticked "Restore previous host WiFi state after update")
   turns the radio back off.

No NetworkManager profile pre-creation is required — the host
talks to `nmcli` directly. On a fresh Linux machine, run
`sudo $(which racelink-setup-nmcli)` once to grant the required
permissions, then restart RotorHazard / racelink-standalone so the
running Python process re-establishes its polkit subject. The
`$(which …)` form expands to the absolute path because `sudo` strips
the venv's `bin/` from its default `secure_path`; the OTA failure
toast also prints the exact absolute command for your install if
`which` isn't on your PATH either. See `docs/standalone.md` for
details. (Source-repo users without the console script can run
`sudo bash scripts/setup_nmcli_polkit.sh` instead — the two helpers
write the same polkit rule.)

The progress panel shows which device is at which stage. **Do
not close the dialog or refresh the page during the run** —
that doesn't cancel the work (the task runs in a host-side
thread) but you'll lose the per-device progress display until
it finishes.

If the update fails for one device, the dialog shows it red in
the per-device list. The other devices continue (unless you
ticked "Stop on error"). After the run, you can re-trigger
just the failed device by selecting it and starting a new
update.

### Common OTA failure modes you might see

* **`HTTP 401 from /update`** — WLED rejected the firmware POST.
  Two device-side gates can fire this:
  * **Same-network gate** (the usual one in mixed AP+STA fleets).
    The host POSTs `/settings/sec` automatically on 401 to flip
    `otaSameSubnet=false` and clear any OTA lock; the second OTA
    attempt should then succeed. The change persists in the
    device's `cfg.json` so subsequent OTAs work without the
    auto-unlock round-trip.
  * **OTA lock with a non-default password.** Override the
    "WLED OTA password" field in the OTA dialog (default
    `wledota`) with whatever your fleet uses.
* **`AP '<SSID>': authentication failed`** — wrong WiFi PSK,
  *or* the device's hostapd is briefly rate-limiting after recent
  failed attempts. Wait ~30 s and retry once before assuming a
  configuration mistake.
* **`PIN code required`** — the device has `settingsPIN` set in
  WLED Security. Clear the PIN on the device or the OTA can't
  proceed; the host doesn't currently auto-enter the PIN.
* **`HTTP 500 from /update: Firmware release name mismatch:
  current='X', uploaded='Y'.`** — WLED rejected the binary because
  its `WLED_RELEASE_NAME` differs from the running firmware's.
  This is the common case when migrating between firmware forks
  (stock WLED → RaceLink build, or between RaceLink hardware
  variants). Tick the **"Skip firmware-name validation"** checkbox
  in the OTA dialog and retry. The check exists for a reason —
  flashing the wrong binary for the chip variant can brick a
  device — so leave the box unchecked once the fleet is on a
  consistent firmware.

> **What does NOT help:** changing the host's IP address or
> netmask. The same-network gate uses *the device's* `Network.localIP()`,
> not the host's, so no host-side IP reconfiguration brings the
> host into the device's STA subnet (the host doesn't even know
> what STA network the device is on, and isn't connected to it).
> The host-side auto-unlock is the only way to clear that gate
> without reconfiguring each device by hand. See
> `docs/DEVELOPER_GUIDE.md` § "WLED OTA gate matrix" for the
> full picture.

### Don't share the gateway between processes

Only one process can own the USB-LoRa dongle at a time. The host
opens it with `exclusive=True`. If you try to run RotorHazard +
the standalone host against the same dongle, the second one will
fail with `PORT_BUSY`. Pick one.

### When the master pill says ERROR

Hover for the explanation. The two common ones:

* **USB hiccup** — transient, auto-recovers. The pill returns to
  IDLE within seconds.
* **Gateway disconnected** — the dongle was unplugged or
  unresponsive. The banner shows the auto-retry countdown.

If the pill stays ERROR for more than a minute and the banner
doesn't show a retry countdown, click **Retry connection** in the
banner. If that doesn't recover, the dongle has likely crashed —
unplug, wait 5 seconds, plug back in, click Retry.

### Effect parameters are silently rejected if the device can't do them

The scene editor's capability filter (C5) prevents this on save:
you can't target a non-WLED group with a WLED preset action,
because the dropdown filters them out. But if you bypass the
editor (e.g. by editing the JSON manually or running an
old scene saved before the filter shipped), the runner may send
a packet that the target devices ignore. The post-run summary
flags actions with zero matching devices.

### Forgetting a master MAC un-pairs the device

The "Forget master MAC" config option (Node Config dropdown)
makes the target device drop its bond with the current gateway.
The next time you discover, the device will reply (it's
listening for any broadcast) and pair to whichever gateway sent
the discovery. Useful when migrating devices between gateways;
gratuitously confusing if you click it during a race.

## Common things that go wrong

### "Discovered 0 devices"

* Devices off / out of range / paired to a different gateway →
  see step 2.
* Gateway transmitting but no replies → check the master pill;
  if RX never opens, the gateway is in a bad state. Reconnect.

### "Run reports OK but nothing happens"

* The action targeted a group with no capable devices. The
  editor's cap filter prevents this in new scenes, but old
  scenes may not have been edited since C5 shipped. Re-edit
  the scene; the dropdown will tell you which groups have
  the capability.
* The target devices are offline (red pill in the device
  table). The runner doesn't know that — it just sends the
  packet. Refresh the device table (Get Status) to see who's
  actually reachable.

### "Bulk set group failed"

* The bulk-set operation sends a `SET_GROUP` packet to each
  selected device and waits for an ACK. If a device is
  offline, the ACK times out and that device's reassignment
  is recorded as failed. The other devices continue. Check
  the masterbar's task summary for the per-device count.

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

## Where the limits are

* **Devices per gateway**: practically unlimited (the protocol
  is broadcast-heavy), but the LoRa airtime limit means
  scenes targeting all-of-N devices scale linearly with N if
  you use per-device actions. Use group / broadcast actions
  for fan-out; the offset_group container's broadcast formula
  modes are the cheapest wire path for cascade effects.
* **Actions per scene**: 20 (configurable in `scenes_service.py`
  if you have a reason).
* **Children per offset_group**: 16.
* **OTA concurrency**: 1 device at a time (per-device WiFi
  flip-flop is the bottleneck).
* **Brightness**: 0–255.
* **Effect parameters**: 0–255 each.
* **Group ids**: 1–254 (0 is Unconfigured, 255 is broadcast).
* **Preset ids**: 0–255.

## Getting help

* Check the WebUI's banners and toasts first — most operator
  errors get explicit feedback there.
* Check the host's diagnostic log (where it goes depends on
  how you run the host — RotorHazard plugin: in the RH log;
  standalone: stderr). Every broad-except path logs the
  exception type + traceback now (post-2026-04-27 sweep), so
  the log is genuinely useful.
* Wire-level questions: see [PROTOCOL.md](../reference/wire-protocol.md).
* Code questions: see [`developer-guide.md`](developer-guide.md)
  and [`architecture.md`](architecture.md).
