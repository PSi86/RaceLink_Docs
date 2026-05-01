# RaceLink Concepts — How the wire opcodes work in practice

This page explains the three opcodes that operators interact with most
often — `OPC_CONTROL`, `OPC_OFFSET`, `OPC_SYNC` — from a **practical**
standpoint: what each one does, when to use it, what its quirks are,
and how the pieces compose when you author scenes.

For the bit-level wire format, see
[`PROTOCOL.md`](../reference/wire-protocol.md). For terminology, see
[`../../glossary.md`](../glossary.md).

> **Three opcodes, three jobs.**
>
> | Opcode | What it does (operator's view) |
> |---|---|
> | `OPC_CONTROL` | "Apply these effect parameters now (or arm them for SYNC)." |
> | `OPC_OFFSET` | "Configure how this group should delay its next ARM_ON_SYNC effect." |
> | `OPC_SYNC` | "Fire all armed effects across the fleet at once." |
>
> All three respect a small **flags byte** (power, arm-on-sync,
> brightness-meaningful, force-tt0, force-reapply, offset-mode). The
> flags decide *when* and *how* an effect lands, not *what* it does.

---

## OPC_CONTROL — direct effect control

### What it is

`OPC_CONTROL` carries **effect parameters** directly on the wire —
mode, speed, intensity, custom sliders, palette, three colours,
brightness — without requiring a pre-staged WLED preset on the node.

Compare to `OPC_PRESET`:

| Aspect | `OPC_PRESET` (WLED preset) | `OPC_CONTROL` (direct effect) |
|---|---|---|
| Body size | 4 bytes fixed | 3–21 bytes (fieldMask-driven) |
| Pre-staging | Preset must exist on every node (numeric slot 0–255 in node's WLED preset list) | None — parameters are sent in-band |
| Use case | "Apply Preset 12 to group 3" — preset library is curated and deployed | Ad-hoc parameter combinations, especially during a race |
| Wire efficiency | Smallest packet | Carries only changed fields |
| WLED-ID lookup | Node looks up its local preset slot | Node merges parameters into the active segment |

### The "merge semantics" trick

This is what makes `OPC_CONTROL` cheap on the wire even though it
*could* carry 14 parameters. The fieldMask byte indicates which
fields are present in this packet. **Fields that are absent retain
their previous value on the node.** Effectively the wire format is a
diff against the current state.

In practice, when you tweak just the `speed` of a running effect:

* Body grows by 1 byte (the new speed value).
* The fieldMask has only the `speed` bit set.
* The receiver overwrites `speed` and leaves `mode`, `intensity`,
  palette, colours, and the rest untouched.

A typical small change (speed + one custom slider) is 5 bytes of
body. A full effect specification (mode + speed + intensity + 3
customs + 3 checks + palette + 3 colours + brightness) is 21 bytes.
The packet ranges between **3 bytes** (no field changes — just
flags) and **21 bytes** (everything).

### Field set

What you can send (and the operator-facing dialog calls each one):

| Field | Range | What it does |
|---|---|---|
| `brightness` | 0–255 | Segment brightness. 0 implicitly turns the segment off (`RL_FLAG_POWER_ON` is auto-derived from this). |
| `mode` | 0–219 | WLED effect-mode index. 0 = Solid, 2 = Breathe, 35 = Traffic Light, etc. |
| `speed` | 0–255 | Effect speed. Per-effect meaning. |
| `intensity` | 0–255 | Effect intensity. Per-effect meaning. |
| `custom1`, `custom2` | 0–255 | Per-effect sliders. Label varies by effect. |
| `custom3` | 0–31 | Per-effect slider (5 bits). |
| `check1`, `check2`, `check3` | bool | Per-effect toggles. Label varies by effect. |
| `palette` | 0–~131 | Palette index. 0–71 are built-in WLED palettes; 72+ are user-defined. |
| `color1`, `color2`, `color3` | RGB triples | Three colour slots. Per-effect role. |

### Per-effect labels

The same field has different meanings across effects:

* `check1` is "Reverse" on Color Wipe but "Use Color 2" on Plasma.
* `custom2` is "Fade time" on Fade but "Density" on Twinkle.

The Host's RL Preset editor reads each effect's label string from
the WLED firmware's effect metadata (`FX.cpp` `_data_FX_MODE_*`
strings) and:

1. Renames the input fields when you switch the effect.
2. **Hides** fields the active effect doesn't use.
3. Shows the generic name (`Speed`, `Intensity`) when the effect
   uses the WLED default for that slot.

This is why the editor's Speed field might be called "Cycle speed"
on a Rainbow effect and "Pulse rate" on a Breath effect — the
firmware is telling the host what each slot means for that effect.

For the catalogue of which effects render **identically across nodes
when only `strip.timebase` is synced** (a prerequisite for offset
mode), see
[`../../concepts/deterministic-effects.md`](deterministic-effects.md).

### The flags byte (shared with `OPC_PRESET`)

Six user-intent flag bits ride along with every `OPC_CONTROL` and
`OPC_PRESET`:

| Flag | Bit | What it does |
|---|---:|---|
| `RL_FLAG_POWER_ON` | 0 | Auto-derived from brightness > 0. Turns the segment on/off. |
| `RL_FLAG_ARM_ON_SYNC` | 1 | **Defer apply until the next `OPC_SYNC`.** This is how multi-device choreographies fire on the same wall-clock instant. |
| `RL_FLAG_HAS_BRI` | 2 | Brightness field is meaningful. Auto-set if you supply a brightness. |
| `RL_FLAG_FORCE_TT0` | 3 | Force transition time 0 — no fade between effects. Useful for sharp colour changes. |
| `RL_FLAG_FORCE_REAPPLY` | 4 | Re-apply even if the parameters haven't changed (useful after a node was reflashed and lost state). |
| `RL_FLAG_OFFSET_MODE` | 5 | Use the device's stored offset configuration. Gates participation in offset mode (see below). |

The flags byte is built host-side via
`racelink/domain/flags.py::build_flags_byte` — never assemble it by
hand, because `RL_FLAG_POWER_ON` and `RL_FLAG_HAS_BRI` are
auto-derived and easy to get wrong.

### Operator workflow — the typical OPC_CONTROL sends

When you click `Apply RL Preset` on the Scenes page, the host:

1. Looks up the named RL preset from `~/.racelink/rl_presets.json`
   (operator-defined effect snapshot).
2. Materialises the parameters into a fieldMask + payload.
3. Sends one `OPC_CONTROL` to the target group (or device).

When you click `Apply WLED Control` (the inline-parameter scene
action), the host:

1. Reads the parameters from the action's `params` block.
2. Builds the same fieldMask + payload.
3. Sends one `OPC_CONTROL` (no preset lookup involved).

### What is *not* in `OPC_CONTROL`

* **No status reply.** `OPC_CONTROL` is fire-and-acknowledge (ACK
  only). The node does not echo back its current state. The host
  trusts its own send-cache. To re-read the device, send
  `OPC_STATUS`.
* **No segment selector** (yet). The current implementation applies
  to segment 0 (the whole strip). Multi-segment work is a v2 topic.

---

## OPC_OFFSET — configuring per-group time offsets

### What it is

`OPC_OFFSET` configures a **per-device delay** that takes effect on
the next `ARM_ON_SYNC` effect. The wire format is a tagged union:
one byte selects the *mode*, the body bytes that follow encode the
parameters for that mode.

Five modes ship today:

| Mode | Wire size | Per-device offset formula |
|---|---:|---|
| `none` | 2 B (header only) | 0 — clears the stored offset; device leaves offset mode |
| `explicit` | 4 B | Constant `offset_ms` (operator-supplied) |
| `linear` | 6 B | `base_ms + groupId × step_ms` |
| `vshape` | 7 B | `base_ms + abs(groupId − center) × step_ms` |
| `modulo` | 7 B | `base_ms + (groupId mod cycle) × step_ms` |

`base_ms` and `step_ms` are signed `int16` (negative steps produce
reverse cascades — group 5 fires first, group 0 last). The
firmware clamps the final per-device value to `[0, 65535]` ms.

### The two wire paths the host can take

For the same operator-visible scene, the runner picks between two
strategies depending on the participating groups:

**Strategy A — broadcast formula.** When the operator picks
**Broadcast** (or selects every currently-known group, which the
save-time canonicaliser collapses to broadcast — see
[scene-format.md](../reference/scene-format.md#save-time-canonicalisation))
together with a formula mode (linear / vshape / modulo), the host
sends **one** `OPC_OFFSET` to the broadcast address
(`groupId = 255`) with the formula. Every node evaluates the
formula against its own `groupId` and stores the result. One
packet configures the whole fleet.

**Strategy B — per-group explicit.** When the operator selects a
sparse list of groups (`target.kind == "groups"` with a strict
subset of the known set), or chose `explicit` mode, the host
evaluates the formula host-side and sends **N** `OPC_OFFSET`
packets — one per group, in `explicit` mode with the resolved
`offset_ms`. The host pays the airtime in exchange for per-group
precision.

**Strategy C — broadcast formula + sparse NONE overrides.**
When the participants are a *majority* of the known fleet and
the mode is a formula, the host sends one broadcast formula
packet plus one `OPC_OFFSET(NONE)` per non-participating group
to deactivate them. The optimizer picks this over Strategy B
when `1 + |non-participants| < |participants|`. See
[Broadcast Ruleset](../reference/broadcast-ruleset.md) for the
end-to-end wire rules.

The runner makes this decision automatically. The cost-estimator
badge in the scene editor shows what wire path will be taken
("≈ 3 pkts" vs "≈ 12 pkts"). Operators don't pick — they author
the intent (Broadcast / Groups / per-group explicit), and the
runner picks the shortest wire encoding.

### The strict acceptance gate

This is the part that confuses operators on first contact, so it's
worth a careful explanation.

Every device has two pieces of state:

* **Active offset** — what the device is currently using. `NONE`
  means "no offset, segment plays immediately on receipt".
* **Pending change** — a fresh offset configuration that has not
  yet been *materialised* into the active offset. Materialisation
  happens when the next `OPC_PRESET` / `OPC_CONTROL` packet that
  sets `OFFSET_MODE=1` arrives, OR when an `OPC_SYNC` fires
  against an `ARM_ON_SYNC` queued effect.

The device's *effective* offset is `pendingChange` if it's valid,
else `active`. Now the gate logic:

| Packet's `OFFSET_MODE` | Receiver's effective offset | Gate result |
|---|---|---|
| 1 (use offset) | non-NONE (offset configured) | **accept** — apply with stored offset |
| 0 (no offset) | NONE (no offset configured) | **accept** — apply normally |
| 1 | NONE | **drop silently** — packet asks to use offset, but no offset is configured |
| 0 | non-NONE | **drop silently** — device is in offset mode; only `OPC_OFFSET(NONE)` exits it |

The two "drop" rows are **features**, not bugs:

1. **Strategy-A scope filter.** Strategy A broadcasts a single
   `OPC_CONTROL` with `OFFSET_MODE=1` to *every* device on the
   fleet. Devices that aren't in the offset set drop the packet.
   Result: one broadcast, scope-filtered to exactly the devices
   that should respond.
2. **State-stickiness.** Once a device has been transitioned into
   offset mode, it stays there until you explicitly send
   `OPC_OFFSET(NONE)` and materialise the change. Random `F=0`
   packets cannot accidentally take the device out of offset mode
   — that would silently break choreographies.

### Leaving offset mode — the only valid sequence

You **must** send `OPC_OFFSET(NONE)` and then materialise it. Two
materialisation paths:

1. **Immediate-apply path:** `OPC_OFFSET(NONE)` followed by an
   `OPC_PRESET` with `F=0`. The preset is the materialisation
   trigger.
2. **Deferred-apply path:** `OPC_OFFSET(NONE)` followed by an
   `OPC_CONTROL` with `ARM_ON_SYNC=1` and `F=0`, followed by
   `OPC_SYNC`. The SYNC handler materialises the pending NONE.

The host's scene runner does both in one operator action: the
`offset_group` container action with `mode=none` sends
`OPC_OFFSET(NONE)` to the participants in Phase 1, then sends each
child action with `F=0` in Phase 2. After the scene runs, the
participants are out of offset mode and accept normal packets
again.

### Operator pitfall — "I ran a normal scene but nothing happened"

If the targeted devices are still in offset mode (a prior
`offset_group(linear/...)` scene didn't get cleaned up), a normal
scene's children fly with `F=0`. The strict gate drops every
child silently. The masterbar shows TX activity, but the devices
don't react.

Fix: insert an `offset_group(mode=none, children=[…])` scene
before the normal scene. The placeholder children carry `F=0` to
materialise the NONE transition.

### Pure clear without an effect

If you want to clear offset mode without playing any visible
effect, use `mode=none` with a placeholder child like
`wled_control` with `mode=0` (Solid) and `brightness=0`. The
`OPC_OFFSET(NONE)` packet does the work; the placeholder child
just carries `F=0` to trigger materialisation.

---

## OPC_SYNC — fire armed effects + adjust timebase

### What it is

`OPC_SYNC` is the broadcast packet that does two distinct jobs at
once:

1. **Adjust `strip.timebase`.** The packet carries a 24-bit
   gateway-relative timestamp. Every receiver sets its
   `strip.timebase` so that `strip.now` equals the master time.
   This synchronises the time base of all WLED segments — required
   for deterministic effects to render identically across nodes.
2. **Materialise armed effects.** Devices with an `ARM_ON_SYNC`
   queued effect fire it now (with the configured offset, if any).

### Two forms — autosync vs deliberate fire

`OPC_SYNC` is variable-length: 4 bytes (legacy / autosync form) or
5 bytes (deliberate-fire form).

| Form | Body | Triggers ARM_ON_SYNC? | Used by |
|---|---|:---:|---|
| 4 B | `ts24 + brightness` | **No** | The gateway's autosync timer (every 30 s while idle). Device only adjusts `strip.timebase`; pending arm-on-sync state stays armed. |
| 5 B | `ts24 + brightness + flags` | **Yes** if `SYNC_FLAG_TRIGGER_ARMED` is set | The scene runner's `_run_sync` action. Device adjusts timebase **and** materialises pending arm-on-sync state. |

`SYNC_FLAG_TRIGGER_ARMED` (bit 0 of the trailing flags byte, value
`0x01`) is the only flag bit currently defined. Bit 1 is reserved
for a future "per-group selector" extension.

### Why the split?

Two needs:

* **Continuous timebase synchronisation.** Without periodic
  timebase nudges, each node's `millis()` drifts independently;
  cyclic effects slowly de-sync. The autosync timer keeps
  `strip.timebase` aligned without disturbing user-armed effects.
* **Deliberate, atomic multi-device fire.** The scene author wants
  to say "all five groups, fire your queued effect *now*, on this
  exact LoRa tick". The 5-byte form does that.

The two roles MUST stay separated. If autosync triggered armed
effects, every 30 s the fleet would fire whatever was queued,
which is operator-hostile.

### Synchronised rollout caveat

A node flashed with old firmware has `req_len = 4` strict and
**rejects** the 5-byte deliberate-fire packet. **Flash every node
before deploying a new host**, or you get a fleet that won't
respond to deliberate sync fires.

The gateway accepts both lengths from the host and passes the
flags byte through end-to-end.

### What the operator sees

When an operator clicks **Run** on a scene that ends with a `Sync`
action:

1. The scene's `arm_on_sync` children land on the targeted devices
   (via `OPC_PRESET` or `OPC_CONTROL` with `ARM_ON_SYNC=1`). Each
   device queues the effect, doesn't render it yet.
2. The `Sync` action sends one 5-byte broadcast `OPC_SYNC` with
   `SYNC_FLAG_TRIGGER_ARMED=1`.
3. Every armed device fires its queued effect on the same LoRa
   tick — modulo each device's stored offset (see
   `OPC_OFFSET` above).

Visually: the operator sees the cascade pattern fire across the
fleet at once.

### "Stop on error" interaction

Each scene carries a **Stop on error** checkbox (default ON). If a
preceding `arm_on_sync` action fails on some device, the runner
aborts before reaching the `Sync` action — and any devices that
*did* arm successfully sit there forever with their armed effect
unfired. Behaviour:

* On the next operator action that materialises arm state (a fresh
  `Sync` or any `OPC_PRESET` / `OPC_CONTROL` with `F=0` after a
  cleanup), the old armed state will fire / clear.
* In practice, run a `offset_group(mode=none)` scene to flush
  state before the next race.

If you want a scene to forge ahead despite individual failures,
uncheck *Stop on error* — armed actions still queue, the `Sync` at
the end still fires the ones that did arm, and the failed actions
are recorded in the run summary.

---

## How the three opcodes compose — three operator workflows

### Workflow 1: Plain scene, no offset, no SYNC

The simplest case — apply a preset to a group right now.

```
[Apply RL Preset] → group 3 → preset "Race Start"
```

Wire: 1× `OPC_CONTROL` (or `OPC_PRESET` if it's an RL preset that
maps to a numeric WLED slot). Flags `F=0`. Device renders
immediately.

### Workflow 2: Multi-group simultaneous fire

Operator wants groups 1, 2, 3 to all start the same effect on the
same instant.

```
[Apply RL Preset, arm_on_sync] → group 1 → preset "Go"
[Apply RL Preset, arm_on_sync] → group 2 → preset "Go"
[Apply RL Preset, arm_on_sync] → group 3 → preset "Go"
[Sync]
```

Wire: 3× `OPC_CONTROL` with `ARM_ON_SYNC=1` (or 1× broadcast if all
groups want the same effect; the runner can choose), then 1×
5-byte `OPC_SYNC`. Devices queue, then fire on the SYNC tick.

### Workflow 3: Cascade across all groups (offset mode)

Operator wants a "wave" — group 0 fires first, group 1 fires 200 ms
later, etc.

```
[Offset Group, "All groups", linear, base=0, step=200 ms]
  └─ [Apply RL Preset, arm_on_sync, OFFSET_MODE=1] → preset "Go"
[Sync]
```

Wire (chosen by runner — Strategy A):

1. 1× `OPC_OFFSET(linear, broadcast)` — every device evaluates
   `base + groupId * step` and stores the result.
2. 1× broadcast `OPC_CONTROL(arm_on_sync=1, OFFSET_MODE=1)` — only
   devices with offset configured accept (others are filtered by
   the strict gate).
3. 1× 5-byte `OPC_SYNC(trigger_armed=1)` — every armed device
   fires after its stored offset.

Result: 3 packets on the wire, fleet-wide cascade.

### Workflow 4: Exit offset mode after the cascade

After Workflow 3, every device is in offset mode. Run a clean-up
scene:

```
[Offset Group, "All groups", mode=none]
  └─ [Apply WLED Control, arm_on_sync, mode=0, brightness=0]
[Sync]
```

Wire:

1. 1× `OPC_OFFSET(NONE, broadcast)` — clears stored offset.
2. 1× broadcast `OPC_CONTROL(arm_on_sync=1, F=0)` — placeholder,
   carries `F=0` to materialise the NONE transition.
3. 1× 5-byte `OPC_SYNC(trigger_armed=1)`.

After this, the fleet is back to normal mode. Subsequent normal
scenes work as expected.

---

## Cyclic-effect phase-lock — the subtle detail

This is a firmware detail every operator running offset-mode
cascades needs to know about, but you only run into it when you
pick the wrong effect.

**The catch.** Cyclic effects (Breathe, Pacifica, Sinelon — any
effect whose render is `f(strip.now)`) compute their brightness
curve directly from `strip.now`. After `OPC_SYNC` aligns
`strip.timebase` across the fleet, every node has the *same*
`strip.now`. So Breathe on group 0 and Breathe on group 4 both hit
peak brightness at the same wall-clock instant — even though they
"started" 800 ms apart. The visual phase difference collapses to
zero. The cascade you intended turns into a synchronous pulse.

**Why state-machine effects aren't affected.** Traffic Light, Color
Wipe, Scan — these effects compute their phase relative to their
own *start time*, stored in `SEGENV.step`. The offset shifts when
each device starts; their internal phase shifts accordingly.

**The fix (in firmware).** The WLED usermod maintains a persistent
per-device `activePhaseOffsetMs`, subtracted from `strip.timebase`
after every SYNC. Concretely: device 4 with a 800 ms offset has its
`strip.timebase` set such that *its* `strip.now` runs 800 ms
behind master. Breathe on device 4 hits peak brightness 800 ms
later than on device 0. The offset that was originally just a
*start* delay becomes a *phase* delay too.

The fix is transparent to the operator — flash recent firmware and
cyclic effects work in offset mode like state-machine effects.

**Practical guidance.** When picking effects for offset cascades,
prefer the **deterministic effects catalogue**
([../../concepts/deterministic-effects.md](deterministic-effects.md))
either way — only those effects render identically across nodes
under any synchronisation regime. If you observe phase-lock on a
deterministic cyclic effect, your node firmware is too old; flash
it.

**For firmware contributors.** The usermod tracks two variables:

* `activePhaseOffsetMs` — the currently-active per-device phase
  shift (set when an effect is applied via the offset-mode path,
  cleared when a non-offset effect is applied).
* `pendingDeferredOffsetMs` — captured at deferral time so that
  `serviceDeferredApply()` can update `activePhaseOffsetMs`
  consistently.

After every `OPC_SYNC` the firmware:

1. Computes the drift error against the **logical** (master-aligned)
   timebase, i.e. `(int32_t)strip.timebase + activePhaseOffsetMs`.
   Without this term, a non-zero `activePhaseOffsetMs` would always
   look like an `err == activePhaseOffsetMs` and trigger endless
   hard-resyncs.
2. Applies the drift correction to `strip.timebase`.
3. Re-asserts the offset by subtracting `activePhaseOffsetMs` from
   `strip.timebase`. The device's `strip.now` then runs
   `activePhaseOffsetMs` ms behind master, which produces the
   intended phase shift in any time-based effect.

The `applyPhaseOffsetToTimebase()` helper centralises the
subtraction and is called after every `strip.timebase` write
(drift correction, hard resync, inline-apply, deferred-apply). The
drift-correction error is computed against
`strip.timebase + activePhaseOffsetMs` — i.e. the *logical*
timebase as if the offset were zero — so the correction tracks
master-relative drift, not the offset itself.

---

## Putting it together — the airtime budget

LoRa airtime at SF7/250 kHz/CR4:5 is roughly **6 ms per 10 bytes
of payload**. A typical race-start scene:

| Wire op | Body | Estimated airtime |
|---|---:|---:|
| 1× `OPC_OFFSET(linear, broadcast)` | 6 B | 8 ms |
| 1× broadcast `OPC_CONTROL(arm)` | 5 B | 8 ms |
| 1× 5-byte `OPC_SYNC` | 5 B | 8 ms |
| **Total** | | **≈ 24 ms airtime** |

Plus host-side overhead (LBT random backoff, USB framing, runner
dispatch) — typically 30–50 ms of wall clock per packet. So the
above scene runs in ~150 ms wall clock, with 24 ms of actual
airtime.

The **cost-estimator badge** in the scene editor shows the
estimated airtime per action and the scene total. After a
successful run, the badge also shows the *measured* wall-clock
duration. The two are not directly comparable — the delta is the
overhead — but a sustained 10× ratio means something is wrong
(slow USB, retry storm, etc.).

For tuning, see
[`PROTOCOL.md`](../reference/wire-protocol.md) §"USB latency tuning".
