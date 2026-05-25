# Headless Mode

A mode in which a single WLED node temporarily takes on the master
role for the rest of the fleet — assigning groups to incoming
unpaired nodes, broadcasting a small catalog of scenes, and driving
fleet-wide brightness — so a session can run without a Gateway+Host
pair. Useful for trade-show demos, field testing, and emergency
fallback when the dongle or laptop is unavailable.

> **A real Gateway always wins.** Headless Mode is a low-priority
> fallback. Any time a real Gateway is on the channel — whether
> answering the promotion probe or showing up later via an autosync
> `OPC_SYNC` — the headless node steps down and resumes normal slave
> behaviour. There is no scenario where a Headless Master continues
> to fight a real Gateway for the fleet.

For the wire-level packet that carries the headless catalog row, see
[`../reference/wire-protocol.md` §`P_Headless`](../reference/wire-protocol.md#p_headless-headless-mode-catalog-trigger-opc_headless-2-b-fixed).
The glossary entry for Headless Mode is in
[`../glossary.md` §Headless Mode](../glossary.md#headless-mode).

## Activating

1. On the node you want to use as the master, **five-click** the
   boot/user button (5 short presses within 500 ms of each other).
2. The node sends an `IDENTIFY_REPLY` broadcast as a probe. If any
   master (a Gateway or another Headless Master) answers within ~1.5
   seconds with an `OPC_SET_GROUP` or any other M2N traffic, the
   promotion is refused: the node plays `IND_PROBE_REJECTED`
   (vivid-orange STROBE for 5 s), then resumes normal slave
   operation. **No two masters can ever run simultaneously by
   accident.**
3. If no answer arrives, the node enters Headless Master mode: it
   plays `IND_HEADLESS_ENTER` (ice-cyan STROBE for 5 s), starts a
   30-second `OPC_SYNC` autosync keepalive on the channel, and is
   ready to assign groups + broadcast scenes. The master also
   **self-assigns Group 1** on entry — see
   [§"Group-id layout"](#group-id-layout) below.

The persisted flag `headlessPersistedActive` in `cfg.json` is set on
entry, so a power-cycle re-runs the probe at boot — the device tries
to re-claim the role unless a real Gateway has come back online in the
meantime. If a persisted slave registry exists (see
[§"Persistence"](#persistence) below), the resumed master also pushes a
**proactive SET_GROUP sweep** to every known slave so devices that did
not reboot alongside the master regain their pairing without having to
re-emit `IDENTIFY_REPLY` themselves.

## Group-id layout

Headless Mode uses the following Group-id contract:

| Group | Meaning |
|---:|---|
| **0** | Unconfigured pool — never assigned by the master. A slave with `groupId = 0` is "unpaired" and a candidate for assignment. |
| **1** | The Headless Master itself. Set on `enterHeadlessMode()`, cleared back to 0 on `exitHeadlessMode()`. |
| **2 .. 254** | Assigned to slaves, in counter order. |
| 255 | Reserved as the broadcast pseudo-group on the wire (never assigned). |

`HEADLESS_FIRST_GROUP_ID = 2` is the first id handed out, so a freshly
promoted master with no prior slave registry assigns the first joining
device to Group 2.

## Pairing slaves to a Headless Master

A new (unpaired) slave node sends its boot-time `IDENTIFY_REPLY`
broadcasts. The Headless Master receives the broadcast and follows a
two-case decision:

* **Slave reports `groupId = 0`** (genuinely unpaired or factory-reset).
  * If the slave's 3-byte address is **already in the registry**
    (a previously paired device that lost its config), the master
    **recycles the stored group id** — the slave returns to the
    same group it had before, without burning a fresh counter slot.
  * Otherwise the master pulls the next free id from
    `Headless Group Counter` (starting at 2), stores the
    `(addr3, groupId)` pair in the registry, and sends
    `OPC_SET_GROUP` back.
* **Slave reports `groupId != 0`** (already paired, possibly to a
  different master historically). The master **mirrors that
  pairing into its registry without sending any packet** — overwriting
  a working pairing would risk group collisions. The slave keeps its
  id; the master simply now knows where to find it for a future
  proactive re-bind.

Either way the slave plays `IND_PAIR_CONFIRMED` (bright-teal STROBE
for 5 s) on receipt of a `OPC_SET_GROUP`. Identical behaviour to
pairing with a real Gateway — the slave has no idea its master is
"headless".

The master flashes its own `IND_PAIRING_TX` (green-cyan STROBE,
1.5 s) each time it actually sends a `OPC_SET_GROUP` packet —
both for a new pairing and for every send during the post-reboot
re-bind sweep. Throttled to 200 ms so a 40-slave sweep reads as
a single continuous flash rather than a flicker storm. Routine
scene / sync / brightness broadcasts do **not** trigger this
indicator; the visual signal is specifically "the master is
configuring a slave right now."

## Scenes

The Headless Master cycles through a small catalog of scenes via
single-click on its button. Each click advances to the next row and
broadcasts a 2-byte `OPC_HEADLESS` packet to the fleet. Per-group phase
offset for staggered scenes (Offset Breathe) is computed
receiver-side from the catalog row's `base + groupId * step` formula
— no separate `OPC_OFFSET` packet flies.

| Scene id | Catalog row | Effect |
|---:|---|---|
| 0 | `SCENE_OFFSET_BREATHE` | BREATH staggered across groups (linear formula, 400 ms per group) |
| 1 | `SCENE_SOLID_RED` | Solid red |
| 2 | `SCENE_SOLID_GREEN` | Solid green |
| 3 | `SCENE_ALL_OFF` | Brightness = 0 (everything dark) |
| 4 | `SCENE_RESTORE_BOOT_COLOR` | Each device returns to its own boot-time random R/G/B pick |

The catalog is wire-stable and lives in `racelink_headless.h`;
extending it requires firmware update on every node, since unknown
scene ids are silently dropped on receivers that pre-date the row.

## Brightness

Long-press on the Headless Master fades the strip with an S-curve
(slower near 0 and 255, faster in the middle). The local fade is
visible on the master's strip live; the **final brightness is
broadcast to the fleet exactly once on button release** via
`OPC_CONTROL` with `RL_CTRL_F_BRIGHTNESS`. No per-tick TX during the
fade — the LoRa channel stays uncongested.

## Stepping down

Three independent paths exit Headless Mode:

1. **Manual 5-click.** Press the button five times again. The node
   plays `IND_HEADLESS_EXIT` (amber STROBE for 5 s) and clears
   `headlessPersistedActive` so the next reboot will not re-claim the
   role.
2. **A real Gateway claims the device.** When the headless node
   receives `OPC_SET_GROUP` from a non-self sender, it steps down
   and accepts the new pairing — same code path as a normal slave
   accepting a new master.
3. **Runtime master detected via autosync.** When the headless node
   receives **any** M2N packet from a non-self sender (most commonly
   the 30-second `OPC_SYNC` autosync from a Gateway that came back
   up after the headless promotion), it steps down. In the rare
   case where the Gateway didn't respond to the boot-time probe but
   is alive, this is the safety net that ensures the fleet
   re-converges within at most ~30 seconds.

In all three cases the indicator `IND_HEADLESS_EXIT` (amber STROBE)
plays for 5 s, then the strip restores its pre-indicator visual —
typically the last scene the headless master was running, which is
the same visual the slaves are still showing.

**Manual exit resets the pairing context.** `exitHeadlessMode()`
clears `Headless Group Counter` back to 0, drops `current.groupId`
back to 0 (the unconfigured pool), and **wipes the persistent slave
registry**. The next promotion therefore starts from a clean slate
with the first new slave assigned to Group 2. This write is
synchronous (no debounce) so a battery pull immediately after the
5-click cannot leave a stale registry on flash. Runtime-override
paths (2) and (3) leave the registry intact — they are involuntary
demotions where the operator may want the data preserved for a later
manual re-promotion.

## Persistence

The headless state survives reboots via five fields in
`RaceLink.overrides` in `cfg.json`:

| Field | Meaning |
|---|---|
| `Headless Active` | `true` if this device should re-claim the role at boot |
| `Headless Group Counter` | Next free group id to assign (so a power-cycle does not collide with already-paired slaves). Counter range 2..254; reset to 0 by `exitHeadlessMode()`. |
| `Headless Current Scene` | Last scene id broadcast (so the master can re-emit it on auto-resume) |
| `Headless Broadcast Bri` | Last brightness broadcast on long-press release |
| `Headless Slaves` | JSON array, up to 40 entries `{a: "AABBCC", g: 2..254}` — the master's record of which 3-byte address is on which group. Drives the proactive re-bind sweep on auto-resume and the recycle-by-MAC path in [§"Pairing slaves to a Headless Master"](#pairing-slaves-to-a-headless-master). |

All fields are visible in the WLED **Config → Usermod Settings →
RaceLink** UI, so an operator can manually clear `Headless Active`
to defuse a stuck headless master or inspect the slave registry
for diagnostic purposes.

**Flash-wear debounce.** Pairing-burst events (e.g. powering on 40
slaves at once) used to fire one `cfg.json` save per slave. The
slave registry now uses a **5-second debounce**: the master accumulates
registry mutations in RAM and writes them out in a single save after
5 s of pairing silence. A typical event therefore costs 2–3 saves
in total instead of ~80, comfortably staying within the LittleFS
wear-leveling headroom. `Headless Active`, `OPC_CONFIG` writes and
`exitHeadlessMode()` continue to save synchronously (rare events
where "save now" is the correct UX).

**Proactive re-bind on resume.** If `Headless Active = true` and
`Headless Slaves` is non-empty at boot, the master — after a clean
probe — sweeps the registry and sends one `OPC_SET_GROUP` per known
slave with **500 ms spacing**. The interval was tuned to leave enough
channel-free time between consecutive master TXs for the addressed
slave to run CAD + send its `OPC_ACK` back without colliding with
the next master `SET_GROUP` (earlier 50 ms spacing caused CAD-busy
backoffs visible as `rl.debug` climbing on the slaves). Each send is
visible as a brief `IND_PAIRING_TX` flash on the master plus
`IND_PAIR_CONFIRMED` on the receiving slave. A 40-slave sweep takes
~20 seconds — long, but reliable. Slaves accept `OPC_SET_GROUP`
idempotently, so devices that already had the correct group simply
see a brief Pair-Confirmed blink (useful as a "roll-call" cue) without
any functional disruption. If the master's TX queue is still busy when
a sweep tick comes due (e.g. the post-promotion SYNC broadcast is
still in flight), the sweep **retries the same slot** on the next
interval instead of advancing — so the first slave in the registry
is never silently skipped.

**Auto-scene-rebroadcast after pairing.** When a slave joins (proactive
boot-burst or individual reactive pairing) the master automatically
broadcasts the current scene **once, 1 second after the last successful
`SET_GROUP`** in the burst, so freshly-bound slaves snap to the
master's visual state instead of staying on their boot color until
the operator next changes the scene. Successive pairings within the
1-second debounce window collapse to a single rebroadcast — a 10-slave
boot burst produces one `OPC_HEADLESS` packet at the end, not ten.
The rebroadcast is a no-op while the master is on the "no scene yet"
default (currentSceneIdx == 0xFF) — operator picks a scene via 1-click
first.

**Master self-sync on broadcast.** The master re-asserts the invariant
`strip.timebase = -activePhaseOffsetMs` on every SYNC keepalive
(30 s) and on Headless Mode entry. Without this re-anchor the master's
own `strip.timebase` could drift away from the value the slaves
adopt via `handleSync()`, producing visible phase drift on offset
scenes (e.g. SCENE_OFFSET_BREATHE) even though slaves stayed
synchronised with each other. The fix keeps the master phase-locked
to its own broadcast clock continuously.

## Probe collision (two devices simultaneously)

If two persisted-headless devices boot at the same time, both schedule
their probe with random jitter (500–2000 ms). Whichever one finishes
its probe first promotes, then answers the other one's probe with
`OPC_SET_GROUP` — so the second device demotes to a normal slave of
the first. The race is decided by jitter, never produces two masters,
and both devices end up in a consistent state.
