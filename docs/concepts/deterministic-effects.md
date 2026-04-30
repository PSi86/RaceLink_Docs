# WLED Effects: Determinism for RaceLink Sync

**Question:** Which WLED effects play back identically across multiple devices when only `strip.timebase` (→ `strip.now`) and the effect parameters (`mode`, `speed`, `intensity`, `custom1/2/3`, `check1/2/3`, `palette`, `colors[]`, `length`, `brightness`) are kept in sync — i.e. without each device receiving identical pixel bytes streamed from the master?

**Use case:** RaceLink offset mode + ARM-on-SYNC. The master only sends the effect configuration plus a SYNC pulse; each node renders locally. Only **deterministic** effects can run visually in sync under these conditions — every other effect will look different on each node.

---

## Determinism Criteria

An effect qualifies as **deterministic** if its rendered pixel output at any given `strip.now` depends *only* on:

- `strip.now` (= the synchronised master time)
- segment parameters (see above)
- compile-time constants

and **NOT** on:

| Source | Why it disqualifies the effect |
|---|---|
| `random8/16()`, `hw_random8/16()` etc. in the render path | RNG sequences differ per device/boot |
| `SEGENV.aux0 += …`, `SEGENV.step += …` per frame | Per-call accumulation is FPS-dependent — devices with different load diverge |
| Audio data (`getAudioData()`, `getAudioData()`-fallback `simulateSound()`) | See "Audio is never deterministic" below |
| Sensor reads, external inputs | Per-device |
| `beatsin*_t()` / `beat*()` **without an explicit `timebase` argument** | See "The `beat*` pitfall" below |

**Helper functions that are safe** (deterministic given deterministic inputs): `sin8_t`, `cos8_t`, `sin16_t`, `cos16_t`, `triwave8/16`, `quadwave8`, `cubicwave8`, `square8`, `perlin8`, `perlin16`, `inoise8`, `inoise16`, `color_from_palette`, `color_wheel`, `color_blend`, `scale8`, `scale16`.

---

## The `beat*` pitfall (single most common reason for false positives)

```cpp
// wled00/util.cpp:483
uint16_t beat88(uint16_t bpm, uint32_t timebase) {
  return ((millis() - timebase) * bpm * 280) >> 16;
}
```

`beat88` (and through it `beat16`, `beat8`, `beatsin88_t`, `beatsin16_t`, `beatsin8_t`) uses `millis() - timebase`. The signatures default `timebase = 0` ([`fcn_declare.h:456-461`](../../wled00/fcn_declare.h#L456-L461)).

`millis()` is the time **since this device booted**. Two devices booted at different wall-clock times have different `millis()` values — even when `strip.timebase` (and therefore `strip.now = millis() + strip.timebase`) is RaceLink-synced.

**Consequence:** every effect that calls `beatsin*_t(bpm, lo, hi)` or `beat*(bpm)` *without* explicitly passing `-strip.timebase` (or some other globally-shared offset) is **NOT deterministic across devices**. This includes `mode_juggle`, `mode_bpm`, `mode_sinelon`, `mode_pride_2015`, `mode_colorwaves`, `mode_pacifica` and many others that look like they should sync.

In principle a future patch could pass `(0 - (uint32_t)strip.timebase)` as the timebase argument to make these effects sync — but that is a WLED-core change, out of scope for this analysis.

---

## Audio is never deterministic (with or without AUDIOREACTIVE)

`getAudioData()` ([`FX.cpp:121-128`](../../wled00/FX.cpp#L121-L128)) returns either real microphone data (when the AUDIOREACTIVE usermod is built into the firmware) or simulated data via `simulateSound(SEGMENT.soundSim)` ([`util.cpp:541`](../../wled00/util.cpp#L541)).

- Real audio: per-device microphone input → never identical across nodes. ✗
- Simulated audio: implementation uses `millis()` directly (line 581) and feeds it into `beatsin8_t(...)` calls without a `timebase` argument (lines 587, 625, 630). The `UMS_WeWillRockYou` mode additionally calls `hw_random8()` (lines 593, 603, 613, 635). None of these are device-synchronised. ✗

**There is no SEGMENT parameter that turns a WLED audio-reactive effect into a deterministic effect.** The `SEGMENT.soundSim` parameter only chooses *which* simulator is used — none of the simulators are cross-device deterministic.

---

## ✓ Deterministic — directly verified

These have been audited in the source: no `random*`, no per-frame `SEGENV` accumulation, no `beat*`/`beatsin*` calls without explicit timebase, no audio. They sync on devices that share `strip.timebase`.

| ID | Effect | Anchor | Notes |
|---:|---|---|---|
| 0 | Solid (`mode_static`) | [FX.cpp:136](../../wled00/FX.cpp#L136) | Pure colour fill. No time dependency. |
| 1 | Blink (`mode_blink`) | [FX.cpp:224](../../wled00/FX.cpp#L224) | `strip.now / cycleTime` phase. `SEGENV.step` is an iteration marker, not an accumulator. |
| 2 | Breathe (`mode_breath`) | [FX.cpp:432](../../wled00/FX.cpp#L432) | `sin16_t(strip.now * speed_factor)`. **End-to-end tested with offset mode — phase-stable across groups.** |
| 3 | Wipe (`mode_color_wipe`) | [FX.cpp:316](../../wled00/FX.cpp#L316) | `strip.now % cycleTime` position. `SEGENV.step` is a direction flag. |
| 6 | Sweep (`mode_color_sweep`) | [FX.cpp:325](../../wled00/FX.cpp#L325) | Same as Wipe. |
| 8 | Colorloop / Rainbow (`mode_rainbow`) | [FX.cpp:514](../../wled00/FX.cpp#L514) | `color_wheel((strip.now * speed_factor) >> 8)`. |
| 9 | Rainbow Cycle (`mode_rainbow_cycle`) | [FX.cpp:530](../../wled00/FX.cpp#L530) | Per-pixel `color_wheel` indexed from `strip.now` + pixel position. |
| 10 | Scan (`mode_scan`) | [FX.cpp:496](../../wled00/FX.cpp#L496) | Position from `strip.now % cycleTime`. |
| 11 | Scan Dual (`mode_dual_scan`) | [FX.cpp:505](../../wled00/FX.cpp#L505) | Same as Scan. |
| 12 | Fade (`mode_fade`) | [FX.cpp:453](../../wled00/FX.cpp#L453) | `triwave16(strip.now * speed_factor)`. |
| 15 | Running (`mode_running_lights`) | [FX.cpp:594](../../wled00/FX.cpp#L594) (via `running_base`) | `counter = (strip.now * speed) >> 9`, then per-pixel `sin8_t(i*x_scale - counter)`. |
| 16 | Saw (`mode_saw`) | [FX.cpp:594](../../wled00/FX.cpp#L594) (`running_base(saw=true)`) | Same engine as Running. |
| 23 | Strobe (`mode_strobe`) | [FX.cpp:242](../../wled00/FX.cpp#L242) | Delegates to `blink()` — see Blink. |
| 35 | Traffic Light (`mode_traffic_light`) | [FX.cpp:1050](../../wled00/FX.cpp#L1050) | State machine driven by `strip.now - SEGENV.step > mdelay`. **End-to-end tested with offset mode.** |
| 52 | Running Dual (`mode_running_dual`) | [FX.cpp:627](../../wled00/FX.cpp#L627) | `running_base(saw=false, dual=true)`. |
| 65 | Palette (`mode_palette`) | [FX.cpp:2029](../../wled00/FX.cpp#L2029) | Pure rotation/translation maths over the palette. See parametrisation below. |
| 83 | Solid Pattern (`mode_static_pattern`) | [FX.cpp:2869](../../wled00/FX.cpp#L2869) | Static, no `strip.now` at all. Output is purely a function of `speed`/`intensity`. |
| 84 | Solid Pattern Tri (`mode_tri_static_pattern`) | [FX.cpp:2888](../../wled00/FX.cpp#L2888) | Static, no time. |
| 115 | Blends (`mode_blends`) | [FX.cpp:4658](../../wled00/FX.cpp#L4658) | `shift = (strip.now * (speed >> 3 + 1)) >> 8` + `quadwave8`. Persistent buffer in `SEGENV.data`, but only ever written from this strip.now-derived shift. |

---

## Per-effect parametrisation notes

The deterministic effects above remain deterministic for *all* combinations of their parameters. Where a parameter changes the visual style (without introducing RNG, audio or per-frame accumulation), it is called out below.

### `mode_palette` (65)

Two `check` flags toggle between static and animated rendering — **both branches are deterministic**:

| Param | Off | On |
|---|---|---|
| `check1` (Animate Shift) | Palette is statically shifted by `SEGMENT.speed` | Shift animates: `((strip.now * (speed >> 3 + 1)) & 0xFFFF) >> 8` |
| `check2` (Animate Rotation) | Rotation angle from `SEGMENT.custom1` | Rotation angle animates: `(strip.now * (custom1 >> 4 + 1)) & 0xFFFF` |
| `check3` (Assume Square) | Output stretched anamorphically | Output assumes square pixels |

All four combinations of `check1`/`check2` use only `strip.now`, `sin16_t`/`cos16_t`, and palette lookups — deterministic. `check3` only changes geometry, no time impact.

**Recommended for offset demos** when both `check1` and `check2` are on: rotation and shift both animate from `strip.now`, so two groups with different `strip.timebase` show the same pattern at different rotation phases.

### `mode_traffic_light` (35)

`SEGMENT.intensity > 140` skips Red+Amber to produce a US-style sequence. Both branches deterministic. Already verified end-to-end with offset mode.

### `mode_scan` (10) / `mode_dual_scan` (11)

`SEGMENT.check2` controls whether the background is filled with `SEGCOLOR(1)` or left untouched. Both branches deterministic.

### `mode_rainbow` (8)

`SEGMENT.intensity < 128` blends the rainbow towards white based on `(128 - intensity)`. Both branches deterministic.

### `mode_running_lights` (15) / `mode_saw` (16) / `mode_running_dual` (52)

`SEGMENT.intensity` scales pixel spacing (`x_scale`); both shapes deterministic.

### `mode_color_wipe` (3) / `mode_color_sweep` (6)

These are the *non-random* IDs. The "random" siblings (`mode_color_wipe_random` id 4, `mode_color_sweep_random` id 36) call `hw_random8()` and are NOT deterministic — they are separate effect IDs, not just parametrisations.

---

## ⚠ Looks deterministic but is not (the false-positive trap)

The following effects use only `strip.now`/`beatsin`/Trig and *appear* deterministic — but each falls into one of the three pitfalls below. They are listed here so they don't sneak into the "✓" list later.

| Effect | ID | Why it's NOT deterministic | Pitfall |
|---|---:|---|---|
| Sinelon, Sinelon Dual, Sinelon Rainbow | 92, 93, 94 | `pos = beatsin16_t(speed/10, 0, SEGLEN-1)` — `beatsin*` uses `millis()` | beat-pitfall |
| Juggle | 64 | `beatsin88_t(...)` × 8 in render loop | beat-pitfall |
| Bpm | 68 | `beatsin8_t(SEGMENT.speed, 64, 255)` | beat-pitfall |
| Pride 2015 | 63 | `beatsin88_t` × 5; also `sPseudotime += duration*msmultiplier` per frame | beat + accumulation |
| Colorwaves | 67 | Same engine as Pride 2015 | beat + accumulation |
| Pacifica | 101 | `beatsin16_t/beatsin88_t` + `SEGENV.aux0/aux1/step` accumulators | beat + accumulation |
| Heartbeat | 100 | Per-frame decay of `SEGENV.aux1` (FPS-dependent envelope) | accumulation |
| Sinewave | 108 | `SEGENV.step += SEGMENT.speed/16` per frame | accumulation |
| Fill Noise | 69 | `SEGENV.step += beatsin8_t(...)` per frame | accumulation |
| Noise 16 (1–4) | 70–73 | `SEGENV.step += (1 + speed/16)` per frame | accumulation |
| Theater Chase, Theater Chase Rainbow | 13, 14 | `SEGENV.step += SEGMENT.speed` per frame | accumulation |

---

## ✗ Non-deterministic — categories (no per-effect breakdown)

These are dismissed wholesale; they cannot be made deterministic by any SEGMENT-parameter change.

- **All `mode_*_random` variants and any effect calling `hw_random*` in its render path.** Examples: Sparkle, Twinkle, Twinklefox, Twinklecat, Glitter, Color Wipe Random, Color Sweep Random, Random Color, Dynamic, Dissolve, Dissolve Random, Running Random, Spots, Meteor, Railway, ICU, Oscillate, Plasma, Tetrix.
- **All particle physics effects** (every `mode_particle*`): random initial positions/velocities, RNG-driven physics. ~40+ effects.
- **All audio-reactive effects**: see "Audio is never deterministic" above. Examples: every `mode_freq*`, `mode_2DGEQ`, `mode_pixelwave`, `mode_plasmoid`, `mode_DJLight`, `mode_gravcenter*`, `mode_puddles`, `mode_pixels`, `mode_blurz`, `mode_ripplepeak`, `mode_2DAkemi`, `mode_2DFunkyPlank`, `mode_2DSwirl`, `mode_2DWaverly`.
- **All fire/flicker effects** (`mode_fire_2012`, `mode_fire_flicker`, `mode_candle*`, `mode_lightning`).
- **Most 2D effects** — even those without RNG typically use `beatsin*` without timebase or accumulate `SEGENV.step` per frame. A potentially-deterministic 2D subset (Lissajous, Julia, Sindots, Wavingcell, Tartan, Metaballs, Squaredswirl) was checked — all use `beatsin*` or `perlin8` against `strip.now` *plus* `SEGENV.step`-style accumulation, so none qualify out of the box.

---

## Recommendation for offset-mode demos

The most visually striking deterministic effects for showing per-group phase offsets:

1. **Breathe (2)** — slow and obvious, the textbook offset demo.
2. **Traffic Light (35)** — discrete state staggering, easy to count.
3. **Rainbow Cycle (9)** — moving colour wave; phase clearly visible on long strips.
4. **Scan / Scan Dual (10/11)** — racing dot, intuitive timing.
5. **Palette (65)** with `check1`+`check2` on — rotating + shifting palette; very pretty, phase-shifts cleanly.
6. **Running (15) / Running Dual (52)** — flowing waves, good for groups arranged in a line.
7. **Blends (115)** — slow palette blending; subtle phase shift visible as a colour offset.

For static scenes (no animation needed, but useful as known-deterministic baselines): **Solid (0)**, **Solid Pattern (83)**, **Solid Pattern Tri (84)**.

---

## How to verify a new / unlisted effect

When WLED adds a new effect or a release modifies an existing one, run the following grep-checklist against its function body in `wled00/FX.cpp`:

1. `grep -nE "random|hw_random"` → any hit in the render path → **NOT deterministic** (Pitfall A).
2. `grep -nE "getAudioData|USERMOD_ID_AUDIOREACTIVE"` → any hit → **NOT deterministic** (audio).
3. `grep -nE "beat[0-9]+|beatsin[0-9]+_t"` → any hit *without* an explicit timebase argument (4th positional arg) → **NOT deterministic** (Pitfall B).
4. `grep -nE "SEGENV\.(step|aux0|aux1)\s*\+="` or `… *=` → per-frame accumulation → **NOT deterministic** (Pitfall C — FPS-dependent).
5. If the effect uses `if (SEGENV.call == 0) { … }` for initialisation, inspect the init body: any RNG → NOT deterministic; pure snapshot of `strip.now` or constants → ✓ (1-frame settling tolerated).
6. Otherwise, if the rendering uses only `strip.now`, segment params, pure trig (`sin*_t`, `cos*_t`, `triwave*`, `quadwave*`, `cubicwave*`, `square*`), Perlin (`perlin8/16`, `inoise8/16`), and palette helpers (`color_from_palette`, `color_wheel`, `color_blend`, `scale*`) → **deterministic** ✓.

---

## Status / open items

- The "✓" list above (19 effects) is exhaustively verified by direct inspection of FX.cpp.
- The non-deterministic catalogue is intentionally kept coarse — the user-facing question is "what works", not "exactly why each one doesn't".
- 2D effects were spot-checked. None passed the `beat*`/accumulation filters; the determinism story for 2D effects would require a per-effect refactor of WLED core to thread `strip.timebase` into `beat*` calls.
- If WLED's `beat*` API is ever updated to accept a "global timebase override", many more effects would qualify with a one-line WLED-core patch — that's the highest-leverage change for expanding this list.
