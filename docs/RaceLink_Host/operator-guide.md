# RaceLink Operator Guide

You've installed RaceLink and pointed your browser at the host's
WebUI. This guide walks you from "no devices yet" to "scenes firing
on the LED nodes" without assuming you've seen the source.

> The other docs in this folder are for *contributors*. This one
> is for *operators*. If you find yourself looking at the C header
> to understand what a button does, the WebUI has failed and the
> bug is on us.

## Glossary

Four terms are needed before the next section makes sense:

* **Device** — one piece of RaceLink hardware (a WLED node, a
  starting-block, etc.). Identified by its 12-character MAC
  address; the host shows the last 6 in the table for brevity.
* **Group** — a named bucket of devices. Operators usually group
  by physical location ("Pit Wall", "Start Line", "Tower 3"). The
  group is what most scene actions target — sending a packet to
  a group broadcasts to every device whose `groupId` matches.
* **Scene** — a saved playlist of *actions* that runs in order.
  Persisted on the host; runnable via the Run button on the
  scenes page.
* **Action** — one step in a scene (apply a preset, fire SYNC,
  delay, run an offset group, etc.).

The full vocabulary (Preset variants, Capability, Specials,
Master pill, Offset Group, Group 0 / Unconfigured, Headless Mode,
Indicator, Gateway) is in the [Glossary](../glossary.md).

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

#### Move groups to a different network

When you run multiple gateways and one or more groups ended up on
the wrong network, open the **Manage groups** dialog from the
sidebar toolbar (the ↕ button next to **+** above the groups
list). The dialog combines drag-reorder with multi-group
network migration so the operator never juggles two windows for
related housekeeping.

Network membership lives at the group level (one network per
group), so the move is always group-granular — individual
devices are never moved across networks on their own; they
follow their group. Static groups (`Unconfigured`, `All WLED
Nodes`) are network-agnostic by design and are not selectable
for moves.

To move one or more groups:

* In the **Manage groups** dialog, tick the checkbox on the
  groups you want to move (the row's current network badge is
  shown on the right so you can verify before acting).
* Pick a **Target** network from the dropdown.
* Click **Move N selected**.

The dialog uses *block* mode by default — if any member device
in the move set is offline, the server refuses with a clear
message and reveals two fallback buttons:

* **Skip offline** — migrate the online devices' RF config + flip
  metadata; offline devices have their network membership flipped
  in memory only. The next Channel Scan recovers them physically.
* **Force offline** — same as skip but additionally attempts the
  wire push for offline devices (usually times out — the device
  isn't reachable). Used as a last resort.

In both fallback modes every device's `network_id` flips
immediately so the host's view matches operator intent — the
same pattern the existing **Move selected to group** uses for
offline devices. The group's own `network_id` flips together
with its members, even if individual wire pushes failed; failed
members surface in Channel Scan with their now-known-good
`last_known_rf_config` for a one-click reassign.

The dialog stays open after a successful move so you can pick
the next batch without re-opening — handy when reorganising
several groups across networks in one sitting.

### 4. Configure devices (optional)

The **Specials** column in the device table is a button you click
to open the per-device **Device Options** dialog. The dialog
groups settings into per-capability tabs: WLED nodes show LED
properties (FPS, ABL, segment geometry, default brightness,
transition); starting-blocks show slot layout; etc. Each option
carries its declared schema default as italic helper text.

#### Live read on open + divergence resolution

Whenever the dialog opens, the host issues one
[`OPC_GET_CONFIG`](../reference/wire-protocol.md#p_getconfig-read-back-request-opc_get_config-1-b-fixed)
per property in the active tab and shows the device's live value
under each row:

* `device: <value> ✓` — the live value matches the host's stored
  intent. Nothing to do.
* `device: <value> ⚠` — the device disagrees with the host's
  stored value. Two compact buttons let you resolve it:
  * **Push host** — re-sends the host's stored value to the
    device, overwriting the device-side state.
  * **Import device** — adopts the device's reported value into
    the host's database (no wire packet sent).
* `device: ?` plus a Retry button — the live read timed out (no
  reply from the device within ~1.5 s). Retry sends a fresh
  `OPC_GET_CONFIG`.

#### Save

Edit a value and click **Save**. The host sends `OPC_CONFIG`,
waits for the device's ACK, and persists the new value in its
own database. **No follow-up read is needed** — the ACK proves the
device stored the value.

**Every property change applies at runtime — no reboot required.**
The device updates the matching runtime variable immediately:
`strip.setTargetFps()` for FPS, `BusManager::setMilliampsMax()`
for ABL, segment `setGeometry()` for the geometry rows,
`transitionDelayDefault` for the transition row. The
**Default Brightness (briS)** row also propagates to the live
brightness so the strip visibly snaps to the new value (this can
still be overridden by the next `OPC_CONTROL` / `OPC_SYNC` packet
— `briS` is just the at-save snapshot). The cfg.json is updated
on the next main-loop iteration so the change persists across
reboots.

While the save is in flight (typically ~500 ms between the device
ACK and the host's SSE refresh) the row's device-value indicator
shows a small **circular spinner** next to the just-saved value
— no ⚠ badge, no Push/Import buttons. Once the host's database
catches up, the spinner switches to *device: &lt;value&gt; ✓*. If the
save genuinely fails (ACK timeout, device offline) you'll see a
task-error toast and the spinner resolves to whatever the next
state actually is; close + reopen the dialog to re-read the
actual device state.

#### WLED Properties vs Methods

The WLED tab carries two kinds of entries (see
[`../reference/opcodes.md` §"Properties vs Methods"](../reference/opcodes.md#properties-vs-methods)
for the wire-protocol view):

* **Properties** are persistent values: `Target Refresh Rate`,
  `ABL Max Current`, `Default Brightness (briS)`,
  `Transition Duration`, `Segment 0/1 Geometry`. These are the
  rows with input fields and Save buttons.
* **Methods** are one-shot actions. The WLED tab currently lists:
  * **WLED Preset** — apply a numeric WLED-preset slot.
  * **RaceLink Preset** — apply a host-side RL-preset id.
  * **Reset to RaceLink defaults** — destructive maintenance
    action that clears every host-set RaceLink override AND
    applies the RaceLink baseline values at runtime (no reboot
    required): FPS=75, ABL=0, briS=128, transition=700 ms,
    segments collapsed to a single `seg[0]` spanning the full
    strip. Confirm-gated; after success the dialog re-reads
    every property so you see the post-reset state immediately.
    All rows match the new defaults except **the segment rows** —
    the host has no way to know the device's strip length, so
    after a reset you click **Import device** on each segment
    row to adopt the device's actual seg geometry into the host
    database.

### 5. Author RL presets and scenes

Once devices are in real groups and any per-device Specials are
configured, the scene-editor side of the WebUI is its own guide:
[`scene-authoring.md`](scene-authoring.md) walks RL presets, scene
composition, the target picker, offset mode, scene-scope on
multi-network setups, and the run flow with its Stop-on-error /
fan-out / measured-runtime semantics. The remainder of this guide
covers the safety rules and recovery paths that apply
*regardless* of scene content.

<!--
The §5 / §6 / §6a / §7 content used to live here. It moved out
in the 2026-05 Gruppe 7 split because the scene-editor surface
had grown large enough to be a separate topic.
-->

### 6. Run a scene

With a saved scene selected on the **Scenes** page, click
**Run**. The master pill goes to **TX**; action rows
border-colour green / red / amber as the run progresses; the
**Last run** status line shows the summary. The Run button (plus
Save / Duplicate / Delete) is disabled for the duration of the
run so you can't queue up a duplicate by mis-clicking.

Authoring scenes (RL presets, action kinds, target picker, offset
mode), the **Stop on error** semantics, multi-network scene scope
(Auto vs Explicit), and the live `actual: NNN ms` measurement
that follows a successful run all live in
[`scene-authoring.md`](scene-authoring.md).

<!-- The old §"Author scenes" / §"The target picker" / §6a
     "Working with offset mode" / §7 Stop-on-error+Scope+Measured
     content used to live here. It moved to scene-authoring.md
     in the 2026-05 Gruppe 7 split. -->

<!-- DEFER_TO_NEXT_SECTION -->
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

**Plan ~30 seconds per device.** A 10-board fleet finishes in
~5 min, a 4-board fleet in ~2 min. The dialog shows this estimate
next to the **Start update** button so you can plan around it;
during the run the progress panel ticks a live `elapsed ·
~remaining left` counter that self-refines from observed times
once at least one device has completed (then counts down
monotonically at 1 s/s until the next refinement). The 30 s
default reflects what operators consistently observe in the
field; the per-phase breakdown below sums to a lower number, but
the spread on `nmcli connect`, the rare reflash retry, and an
occasional slow post-reboot identify shift the realistic mean
higher.

The Firmware Update dialog stays open during the OTA. Per device,
the host:

1. Sends an `OPC_CONFIG` to enable the device's WLED AP and waits
   for the device to ACK it (so the host doesn't start scanning
   before the AP is actually broadcasting). The wait is **1.5 s
   with one automatic retry** — a frame lost in the radio is
   recovered without the legacy 8 s timeout penalty. If both
   attempts time out, the device is marked failed and the workflow
   moves on within ~3 s.
2. Scans for any of the SSIDs in the dialog's SSID field
   (default `WLED_RaceLink_AP, WLED-AP` — newer firmware
   broadcasts the first, older firmware the second; the host
   takes the first one it sees) and connects with the password
   from the dialog (default `wled1234`). The host locks the
   connect to the device's predicted AP-BSSID (ESP32 default
   `STA_MAC + 1`) so it doesn't grab a previously-flashed node's
   AP that's still in `nmcli`'s scan cache.
3. Verifies the node's MAC via `/json/info`.
4. Uploads the firmware binary.
5. (Optional) Uploads `presets.json` and/or a `cfg.json`.
6. Disconnects the host's WiFi from the rebooting device (with
   `nmcli -w 0` — no wait for the 802.11 deactivation, the
   device is already gone).
7. Waits for the device to re-announce on the RaceLink radio
   after its reboot, then waits for the standard auto-restore
   path to push its old group ID back.
8. **AP-Close cleanup is conditional.** On a clean upload the WLED
   reboot drops the AP automatically, so the host doesn't send a
   separate AP-disable. The AP-disable `OPC_CONFIG` (1.5 s × 2
   attempts) only fires when AP-enable succeeded *but* a later
   step failed (wrong OTA password, bad firmware binary,
   HTTP 401 / 500 / timeout, …) — in that case the device is
   still alive on LoRa, the AP is still broadcasting, and
   leaving it up would expose the WLED AP credentials. If
   AP-enable itself never ACKed there's nothing to close, so
   the cleanup is skipped.

After the last device, the host's WiFi radio is turned back off
if you ticked **Restore previous host WiFi state after update**.

#### Where the time goes (per device, typical)

| Phase | Duration |
|---|---|
| RaceLink AP-enable round-trip | ~0.3 s (single attempt) / up to 3 s on retry+fail |
| Wait for AP to appear in scan | ~5 s |
| `nmcli` connect (auth + DHCP) | ~2 s typical, up to ~10 s on Channel-6 contention |
| Firmware HTTP `/update` (1.1 MB binary) | ~10 s |
| Post-upload host-WiFi disconnect | ~0.1 s |
| Device reboot → `IDENTIFY_REPLY` on radio | ~2 s |
| Auto-restore `SET_GROUP` ACK | ~0.5 s |
| AP-Close ACK (only on the *error-after-AP-open* path) | ~0.3 s typical, up to 3 s on retry+fail |
| **Per-device subtotal (success path)** | **~20 s** |

The estimate scales linearly. Larger fleets don't slow each device
down — NM's scan-cache ages stale BSSIDs out at roughly the same
rate they get added, so the per-device cost is independent of the
fleet size for at least the first ~20 boards.

No NetworkManager profile pre-creation is required — the host
talks to `nmcli` directly. On a fresh Linux machine, the one-time
polkit-grant step (`sudo $(which racelink-setup-nmcli)`, then restart
the host) is documented in
[`standalone-install.md`](standalone-install.md#linux-first-time-setup-for-firmware-updates)
§"Linux first-time setup for firmware updates".

The progress panel shows which device is at which stage. **Do
not close the dialog or refresh the page during the run** —
that doesn't cancel the work (the task runs in a host-side
thread) but you'll lose the per-device progress display until
it finishes.

If the update fails for one device, the dialog shows it red in
the per-device list **with the concrete failure message inline**
(e.g. `Timeout waiting for CONFIG ACK from <MAC> (AP-enable)` or
`HTTP 500 from /update: Firmware release name mismatch …`) — you
no longer have to wait for the final summary to find out *why* a
specific device failed. The other devices continue (unless you
ticked "Stop on error"). After the run, you can re-trigger just
the failed device by selecting it and starting a new update.

When the run finishes, the summary panel shows a **Total time:
M:SS** badge alongside the success / failed / skipped counts so
you can compare actual versus estimated duration at a glance.
The live timer during the run is anchored to the host's clock
(server-computed `elapsed_s`) rather than to the browser's, so
hosts without NTP sync no longer make the timer start ahead of
0:00.

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
> See [`../reference/wled-ota-gates.md`](../reference/wled-ota-gates.md)
> for the full four-gate breakdown.

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

### "Bulk set group failed"

* The bulk-set operation sends a `SET_GROUP` packet to each
  selected device and waits for an ACK. If a device is
  offline, the ACK times out and that device's reassignment
  is recorded as failed. The other devices continue. Check
  the masterbar's task summary for the per-device count.

### Scene-editor pitfalls

The scene-editor-side pitfalls ("Run reports OK but nothing
happens" / "Scene editor says I have unsaved changes but I just
saved" / "Cost badge says X but the scene takes Y") moved to
[`scene-authoring.md` §"Common scene-editor pitfalls"](scene-authoring.md#common-scene-editor-pitfalls)
in the Gruppe 7 split.

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
* Wire-level questions: see [wire-protocol.md](../reference/wire-protocol.md).
* Code questions: see [`developer-guide.md`](developer-guide.md)
  and [`architecture.md`](architecture.md).
