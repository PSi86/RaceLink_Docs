# Session retrospective: V3↔V4 sync investigation (2026-05-06 / 07 / 08)

A three-day investigation into the `racelink_wled` firmware sync behaviour
across mixed V3 (ESP32-S2) and V4 (ESP32-S3) device groups. All three
symptoms turned out to be **operator-side state divergence** rather than
firmware bugs. Several speculative code-level patches landed in the
working tree during the diagnosis, none of which contributed to the
final fixes. This page is the authoritative record of what was tried,
what the actual root causes were, and which operator settings must stay
aligned across the fleet.

> **Audience.** Anyone (including a future Claude session) investigating
> any "device A behaves differently from device B" symptom on this
> fleet, evaluating which 2026-05 patches to keep or remove, or
> bootstrapping a new device into the existing group.

## Three issues, side by side

| # | Issue | Final status |
|---|---|---|
| 1 | **"Weak Breathe" on internal effect triggers** — `showPairConfirmedEffect()` rendered at near-zero amplitude on some V3+V4 devices. | **Resolved 2026-05-07 — operator-side.** Persisted `seg[0].stop` divergence after Boot Preset removal exposed historic LED-Setup divergence. |
| 2 | **Cross-fleet effect intensity divergence** — Breathe (and other effects) appeared softer on some devices than others even with identical group / preset state. | **Resolved 2026-05-08 — operator-side.** ABL (automatic brightness limiter) and Gamma correction for color were configured differently per device. Aligning both made effects match. |
| 3 | **V3↔V4 Strobe phase drift up to 180°** — Strobe specifically (no other deterministic effect) showed a wandering V3↔V4 phase offset; within-platform sync was always tight. | **Resolved 2026-05-08 — operator-side.** `Target refresh rate` was `0 (disabled)` on all devices. Each platform free-ran at its hardware-natural fps (V3 at ~240 fps, V4 at ~124 fps). Strobe is the only WLED effect whose `cycleTime` formula in `blink()` ([wled00/FX.cpp:195-218](wled00/FX.cpp#L195-L218)) embeds `FRAMETIME` (`+ FRAMETIME*2`), so different fps produced different cycle periods → wandering phase. Pinning Target refresh rate to 100 fps on all devices resolved it. |

### Issue 1 root cause (Weak Breathe, operator-identified 2026-05-07)

Earlier in the project lifecycle every device had a Boot Preset
configured. WLED's boot path applied that preset on every boot, which
carried `seg[0].stop = 9` — implicitly normalizing segment geometry on
every device every time it powered on. This silently masked historic
divergence in LED-Setup (this fleet has devices configured for
100+100=200 or 100+150=250 LEDs even though all devices physically
have 9 LEDs connected).

When the `showBootRandomColor()` boot indicator shipped earlier in this
session, the operator removed the Boot Preset because the new indicator
made the preset's "show that the device booted" purpose redundant. The
implicit segment normalization went away with it. Devices with
persisted `stop=9` from the old auto-applied preset still rendered
Breathe correctly; devices that booted with their LED-Setup default
(`stop=200/250`) rendered Breathe weakly.

Why a 200-LED segment renders Breathe weakly while a 9-LED segment
renders correctly was **not** decisively traced from code reading
alone. The fix path is operator-side (re-enable a Boot Preset, or
manually fix segment geometry per device) — not firmware.

### Issue 2 root cause (cross-fleet intensity, operator-identified 2026-05-08)

Two independent per-device LED settings were divergent across the
fleet and produced visibly different effect rendering despite identical
group/preset state:

- **Automatic Brightness Limiter (ABL)** was enabled on some devices
  with a tight `maxpwr` budget (in mA) and disabled on others. With
  ABL active and a low budget, frame brightness gets scaled down on
  bright frames, attenuating Breathe amplitude and shifting the visual
  feel of any effect that exercises the high end of the brightness
  range.
- **Gamma correction for color** (`gammaCorrectCol` /
  `light.gc.col`) was enabled on some devices and disabled on others.
  With gamma OFF, mid-range LED values render proportionally brighter
  than with gamma ON (default 2.2), making fades feel "harsher" and
  the perceived amplitude curve different.

Once both settings were aligned across the fleet, Breathe (and every
other effect) rendered visibly identically.

### Issue 3 root cause (V3↔V4 Strobe drift, identified 2026-05-08)

`Target refresh rate` (= `_targetFps` in code) was `0 (disabled)` on
every device, meaning each one free-ran at its hardware-natural frame
rate. Measured: V3 (S2, 200 LEDs) at 213-243 fps, V4 (S3, 250 LEDs)
at 123-124 fps.

The reason this only manifested on Strobe — not on any of the other
deterministic effects we'd already aligned — is that `mode_strobe()`
delegates to `blink()` ([wled00/FX.cpp:195-218](wled00/FX.cpp#L195-L218)),
whose period formula bakes `FRAMETIME` directly into the cycle:

```c
uint32_t cycleTime = (255 - SEGMENT.speed) * 20;
uint32_t onTime    = FRAMETIME;
cycleTime += FRAMETIME * 2;            // ← only Strobe has this
uint32_t it  = strip.now / cycleTime;
uint32_t rem = strip.now % cycleTime;
bool on = (it != SEGENV.step) || (rem <= onTime);
```

Compare with `mode_breath()`
([wled00/FX.cpp:432-439](wled00/FX.cpp#L432-L439)), which is a pure
function of `strip.now` and `SEGMENT.speed` only — no `FRAMETIME`
dependency. With identical `strip.timebase` (which RaceLink's
`handleSync()` enforces master-aligned), Breathe is automatically
phase-locked across platforms; Strobe is not, because its period
*itself* depends on per-device `FRAMETIME`. Any synchronized fleet
running with different `_targetFps` per device sees Strobe drift.

Pinning `Target refresh rate` to 100 fps on all devices made V3↔V4
Strobe perfectly synchronous. 100 fps is a safe value because both
platforms can sustain it (V4's natural ~124 fps cap is above 100,
V3's much higher), so neither hits the floor.

**Why the V3↔V4 fps gap exists** was not decisively isolated. Likely
factors: LED count (200 vs 250), per-chip RMT pipeline behaviour, and
incidental per-platform service-loop overhead. The platform-fixed
`MIN_FRAME_DELAY` floor in [wled00/FX.h:64-69](wled00/FX.h#L64-L69)
(2 ms on regular ESP32 + S3, 3 ms on S2/C3, 8 ms on ESP8266) is **not**
the binding cap on either platform when `_targetFps=0` — actual
service-loop time exceeds the floor on both. The floor only matters
in true unlimited mode if the rest of the pipeline is fast enough to
hit it, which neither V3 nor V4 does in this deployment.

**Latent upstream WLED bug.** The `+ FRAMETIME*2` term in `blink()`
is a real correctness issue for any synchronized fleet. Vanilla WLED
has no built-in `strip.timebase`-anchored cross-device sync (UDP-Sync
works differently), so it doesn't surface in mainline use. A clean
upstream PR would replace `FRAMETIME` with a fixed constant (e.g. 20)
in the period formula so Strobe becomes frame-rate-independent like
Breathe. Out of scope for this session.

## Source-code changes by category

All file paths are relative to the `RaceLink_WLED` source tree (i.e.
the WLED working copy at `c:/Users/psima/Dev/WLED LoRa/WLED/` for local
work, or the upstreamed `RaceLink_WLED/` repo for syncs).

### Confirmed working — keep

These changes were synced to the `RaceLink_WLED` repo on 2026-05-06.

| Change | Location | Notes / rollback |
|---|---|---|
| **ePaper async refactor** (FreeRTOS worker task; non-blocking `epaperInit` + refresh; pin re-config via `setPins()` helper class) | `usermods/racelink_wled/racelink_epaper.cpp` (rewritten) and `racelink_epaper.h` (`epaperInit` signature now takes 7 pin args) | Rollback: `git revert` the corresponding sync commit on the `RaceLink_WLED` repo. Roughly +450 lines in the .cpp; the new `epaperInit` signature is a hard API break. Caller in `racelink_wled.cpp` setup() at the ePaper allocation block must revert in lockstep. |
| **Runtime-configurable pins** (RaceLink + ePaper): pin members on `UsermodRaceLink`; `pins`/`epaper_pins` JSON in `addToConfig`/`readFromConfig`; PinManager allocation; reboot-on-pin-change. | `usermods/racelink_wled/racelink_wled.h` (pin defaults block + member fields), `racelink_wled.cpp:635` (`radioInit` reads from members + `PinManager::allocateMultiplePins`), `racelink_wled.cpp` (`addToConfig`/`readFromConfig` sections) | Rollback: revert the pin member fields + the JSON read/write blocks; `radioInit` returns to using `RACELINK_PIN_*` macros directly. PinManager allocation is independent and can be reverted separately if desired. |
| **German→English comment translations** in `racelink_wled.cpp` (~25 comment blocks). | `usermods/racelink_wled/racelink_wled.cpp` throughout. | Cosmetic; no behavior change. Roll back per-comment if needed. |
| **Operator pin-config docs + radio-modules dev guide** | `RaceLink_Docs/docs/RaceLink_WLED/pin-config.md`, `radio-modules.md` | Documentation only. |

### Speculative — no observable improvement

These patches are in the working tree but **were NOT synced to the
`RaceLink_WLED` repo**. They build cleanly on all three shipping
profiles. They are kept because they are technically correct (each
addresses a real-or-plausible concern); they did not however change
the V3↔V4 sync drift or the weak-Breathe symptom on the affected
devices. The next session should decide whether to keep, sync, or
revert these as a block.

#### S1: ISR-time `millis()` capture for SYNC RX

Hypothesis: variance in ISR-to-handler latency between platforms (S2
single-core has more Wi-Fi-induced jitter than S3 dual-core's
isolated loop, or vice versa) introduces a noise term in the soft-sync
filter at `RACELINK_SYNC_MAX_STEP_MS = 15`. Capturing `millis()` at
the DIO1 ISR instead of at handler entry should eliminate this noise
source.

| Touch point | Location | Change |
|---|---|---|
| `Core::dio1AtMs` field | `usermods/racelink_wled/racelink_transport_core.h:100` | New `volatile uint32_t dio1AtMs = 0;` next to `dio1Flag`. |
| ISR trampoline body | `racelink_transport_core.h:178` (`onDio1ISR_trampoline`) | Captures `g_rl->dio1AtMs = millis()` BEFORE setting `dio1Flag`. Both writes are volatile/atomic on Xtensa. |
| `service()` snapshot | `racelink_transport_core.h:514` | After clearing `dio1Flag`, reads `const uint32_t rxAtMs = rl.dio1AtMs;` and passes it to the callback. |
| `Callbacks::onRxPacket` typedef | `racelink_transport_core.h:72` | Signature gained a `uint32_t rxAtMs` parameter before `void* ctx`. |
| `on_rx_node` signature | `usermods/racelink_wled/racelink_wled.cpp:1883` and matching declaration in `racelink_wled.h` | Accepts `uint32_t rxAtMs`, passes through to `handlePacket`. |
| `handlePacket` signature | `usermods/racelink_wled/racelink_wled.cpp:995` | Accepts `uint32_t rxAtMs`; only the `OPC_SYNC` case forwards it to `handleSync`. |
| `handleSync` signature | `usermods/racelink_wled/racelink_wled.cpp:1746` | Accepts `uint32_t rxAtMs`; the line `const uint32_t nowMs = rxAtMs;` replaced the previous `const uint32_t nowMs = millis();`. |

**Outcome:** the existing `lastSyncTbErrMs` field exposed in the WLED
Info panel as `"TB Err (last)"` was the verification signal. Its
distribution did not visibly tighten on V4 nodes after this change.

**Rollback** is mechanical but spans both the transport header and
the usermod source/header: revert each `rxAtMs` parameter, restore
`millis()` at `handleSync` entry, drop the `dio1AtMs` field, and
restore the original ISR trampoline body. No protocol/wire changes
involved.

#### S2: `strip.trigger()` after timebase update in `handleSync`

Hypothesis: even if `strip.timebase` is sub-ms-aligned across V3 and
V4, the actual visible LED frame is rendered at each device's next
`_frametime` boundary. If frame phases drift between platforms, the
visible flash time differs by up to one `_frametime` (~20 ms at
50 fps). Calling `strip.trigger()` at SYNC reception forces the next
service() iteration to render immediately, re-aligning frame phase.

| Touch point | Location | Change |
|---|---|---|
| `strip.trigger()` call | `usermods/racelink_wled/racelink_wled.cpp:1746` (inside `handleSync`, after the timebase soft-step / hard-snap branch) | Single line; mirrors WLED's own UDP-sync pattern in `wled00/udp.cpp:450`. |

**Outcome:** no visible improvement to V3↔V4 phase offset.

**Rollback:** delete the `strip.trigger();` line plus its comment
block. Standalone change.

#### S3: Deterministic internal-effect parameters

Hypothesis: `showPairConfirmedEffect()` was setting only `mode`,
`color0`, `intensity`, `speed`, leaving `colors[1]` (background),
`palette`, `custom1..3`, `check1..3`, `opacity`, `on` to whatever the
previous effect left behind. `mode_breath()` blends `SEGCOLOR(1)` with
`color_from_palette(...)`; if `colors[1]` was non-black, Breathe
amplitude collapses. Solution: route internal triggers through a
fully-populated `AdvancedFields` struct so every segment field is
written explicitly.

| Touch point | Location | Change |
|---|---|---|
| `buildEffectFullDefaults()` static helper | `usermods/racelink_wled/racelink_wled.cpp:116` | Returns an `AdvancedFields` with every mask bit set and all values neutral (palette=Solid, color1..3=black, custom=128/0, check=false). |
| `applySegmentReplace()` member | `usermods/racelink_wled/racelink_wled.cpp:1465`, declared in `racelink_wled.h` next to `applyAdvancedFields` | Wraps `applyAdvancedFields()` with `seg.opacity = 255; seg.on = true;` plus the `startTransition(0)` cleanup (see S4). |
| `showPairConfirmedEffect()` refactor | `usermods/racelink_wled/racelink_wled.cpp:731` | Now builds a Breathe `AdvancedFields` from `buildEffectFullDefaults()` and routes through `applySegmentReplace()` with `POWER_ON | HAS_BRI | FORCE_TT0 | FORCE_REAPPLY` flags. |
| `applyCycleColor(idx, bool snap = false)` refactor | `usermods/racelink_wled/racelink_wled.cpp:773`, declaration in `racelink_wled.h` | Same pattern, `FX_MODE_STATIC`. New `snap` parameter (default false) controls whether the entry is instant (`FORCE_TT0`) or fades. |
| `showBootRandomColor()` updated caller | `usermods/racelink_wled/racelink_wled.cpp:752` | Calls `applyCycleColor(pick, /*snap=*/true)` so boot indicator is instantly visible. Old `stateChanged = true; stateUpdated(CALL_MODE_INIT);` lines removed (handled inside `applyAdvancedFields`). |
| `applyColorCycleStep()` (unchanged) | `usermods/racelink_wled/racelink_wled.cpp:793` | Still calls `applyCycleColor(idx)` with default `snap=false` so button-cycle UX preserves the smooth fade between R→G→B clicks. |

**Outcome:** the user-reported weak-Breathe symptom on the affected
devices was **not** corrected by this refactor. Operator-side state
divergence (see Issue 2 above) was the actual cause.

**Rollback:** revert all five touch points; drop
`buildEffectFullDefaults()` and `applySegmentReplace()` from `.cpp`
and `.h`; revert `showPairConfirmedEffect()` and `applyCycleColor()`
to their pre-2026-05-06 form (the simpler direct `seg.setMode()` /
`seg.setColor()` pattern). The `snap` parameter on `applyCycleColor`
goes away with the revert. Per-section revert is straightforward
because each function body is self-contained.

#### S4: `seg.startTransition(0)` cleanup in `applySegmentReplace`

Hypothesis: a stuck `_t` (transition state) carrying an `_oldSegment`
from a prior effect causes WLED's renderer to run BOTH the old and
new modes in parallel
([`WS2812FX::service()` blending block](https://github.com/wled/WLED/blob/main/wled00/FX_fcn.cpp#L1303)),
producing a heavily attenuated effect output. WLED's own preset apply
path implicitly clears this via `setGeometry()` →
[`stopTransition()` (FX_fcn.cpp:446)](https://github.com/wled/WLED/blob/main/wled00/FX_fcn.cpp#L446)
when bounds change. Internal triggers don't change geometry, so we
mark any in-flight transition for cleanup explicitly via the public
`startTransition(0)` API (same pattern as
[`json.cpp:315`](https://github.com/wled/WLED/blob/main/wled00/json.cpp#L315)).

| Touch point | Location | Change |
|---|---|---|
| `applySegmentReplace` first line | `usermods/racelink_wled/racelink_wled.cpp:1465` | `if (seg.isInTransition()) seg.startTransition(0);` immediately before opacity/on writes. |

**Outcome:** no visible improvement on the affected devices.

**Rollback:** delete that single guarded line; the rest of
`applySegmentReplace` is unaffected.

## Operator state reference: settings that MUST be aligned across the fleet

This table captures the LED-related settings whose per-device divergence
caused visible bugs in this session. **All three were verified directly
in the WLED source tree on 2026-05-08** (not guessed). When debugging
"device A behaves differently from device B" in future, dump these from
both devices and diff first.

For each setting: UI path, runtime variable in code, persistent storage
in `cfg.json`, HTTP form arg (legacy `/settings/leds`), build-time default,
and known-good value for the RaceLink fleet.

### Target refresh rate (`_targetFps`)

| Aspect | Value / Location |
|---|---|
| **UI path** | Settings → LED & Hardware → Advanced → Target refresh rate (FPS) |
| **UI HTML** | [`wled00/data/settings_leds.htm:1174`](wled00/data/settings_leds.htm#L1174) |
| **Runtime variable** | `WS2812FX::_targetFps` (uint8_t) — [`wled00/FX.h:1027`](wled00/FX.h#L1027), member-init at [`FX.h:845`](wled00/FX.h#L845) |
| **Compile-time default** | `WLED_FPS = 42` ([`wled00/FX.h:61`](wled00/FX.h#L61)) — overridable via PlatformIO build flag `-D WLED_FPS=<value>` |
| **`cfg.json` path** | `hw.led.fps` (read [`cfg.cpp:179`](wled00/cfg.cpp#L179), written [`cfg.cpp:931`-ish](wled00/cfg.cpp)) |
| **HTTP form arg** | `FR` ([`set.cpp:194`](wled00/set.cpp#L194)) — `POST /settings/leds` body |
| **Effect on runtime** | `setTargetFps()` clamps `fps ≤ 250`; if `>0` sets `_frametime = 1000/_targetFps`, else `_frametime = MIN_FRAME_DELAY` (FPS_UNLIMITED, free-running) ([`FX_fcn.cpp:1729-1732`](wled00/FX_fcn.cpp#L1729-L1732)) |
| **Why it matters for sync** | `mode_strobe()` and `mode_strobe_rainbow()` embed `FRAMETIME` in their cycle period. Different `_targetFps` per device → different cycle period → wandering V3↔V4 phase offset. |
| **Known-good value (RaceLink fleet)** | **100 FPS** (uniform across V3 + V4). Both platforms reach 100 fps comfortably, neither hits MIN_FRAME_DELAY floor. Default 42 would also work but trades visual smoothness for CPU headroom we don't need on a 9-LED strip. |

### Automatic Brightness Limiter (ABL)

| Aspect | Value / Location |
|---|---|
| **UI path** | Settings → LED & Hardware → LED setup → Enable automatic brightness limiter |
| **UI HTML** | [`wled00/data/settings_leds.htm:1032`](wled00/data/settings_leds.htm#L1032) |
| **Runtime variable** | `BusManager::_gMilliAmpsMax` (uint16_t) — [`bus_manager.h:534`](wled00/bus_manager.h#L534), accessor `setMilliampsMax()` / `ablMilliampsMax()` at [`bus_manager.h:548-549`](wled00/bus_manager.h#L548-L549) |
| **Compile-time default** | 0 (= ABL disabled). **No dedicated build flag.** `MA_FOR_ESP` ([`bus_manager.h:521-525`](wled00/bus_manager.h#L521-L525)) is unrelated — it's the assumed mA the ESP itself draws (80 mA on ESP8266, 120 mA on ESP32), used inside the ABL formula only when ABL is already enabled. |
| **`cfg.json` path** | `hw.led.maxpwr` (in mA, integer) — read [`cfg.cpp:171`](wled00/cfg.cpp#L171), written [`cfg.cpp:932`](wled00/cfg.cpp#L932) |
| **HTTP form args** | `MA` (max mA), `ABL` (checkbox), `PPL` (per-port-limiter mode) ([`set.cpp:184`](wled00/set.cpp#L184)) |
| **Convention** | `maxpwr = 0` → ABL disabled. `maxpwr > 0` → ABL enabled with that mA budget. |
| **Why it matters for sync** | When ABL is enabled and the budget is tight, frame brightness is scaled down on bright frames. Mixed enabled/disabled across the fleet produces visibly different effect intensity even with identical preset state. |
| **Known-good value (RaceLink fleet)** | Operator chose **ABL disabled** uniformly (`maxpwr = 0`). The fleet runs 9 LEDs per device, far below any practical mA budget, so ABL was never doing useful work — only causing per-device divergence. |

### Gamma correction for color (`gammaCorrectCol`)

| Aspect | Value / Location |
|---|---|
| **UI path** | Settings → LED & Hardware → Color & White → Use Gamma correction for color |
| **Runtime variables** | `gammaCorrectCol` (bool, init `true`), `gammaCorrectBri` (bool, init `false`), `gammaCorrectVal` (float, init `2.2f`) — [`wled.h:412-414`](wled00/wled.h#L412-L414) |
| **Compile-time default** | Color gamma ON, brightness gamma OFF, gamma value 2.2. **No dedicated build flag for the on/off toggle**; the `_INIT(...)` defaults bake in at link time. To override, edit `wled.h` directly (not recommended — fights upstream merges). |
| **`cfg.json` paths** | `light.gc.col` (col-gamma value: `1.0` = off, ≠`1.0` = on, encoded as the actual gamma value), `light.gc.bri` (same scheme for brightness gamma), `light.gc.val` (the gamma value applied if either is on) — [`cfg.cpp:519-531`](wled00/cfg.cpp#L519-L531), written [`cfg.cpp:1061-1063`](wled00/cfg.cpp#L1061-L1063) |
| **HTTP form args** | `GC` (col checkbox), `GB` (bri checkbox), `GV` (gamma value) — [`set.cpp:377-379`](wled00/set.cpp#L377-L379) |
| **Validation** | gamma value clamped to `[0.1, 3.0]`; outside range → reset to `1.0` (= disabled, both col and bri) ([`cfg.cpp:526-530`](wled00/cfg.cpp#L526-L530), [`set.cpp:380-384`](wled00/set.cpp#L380-L384)) |
| **Why it matters for sync** | With gamma OFF, mid-range LED values render proportionally brighter than with gamma ON (default 2.2). Mixed configurations across the fleet produce visibly different fade curves and perceived effect intensity. |
| **Known-good value (RaceLink fleet)** | Operator's choice — set both ON or both OFF uniformly. Default (gamma color ON, value 2.2) is reasonable for visual fidelity. |

### Build-flag vs persistent-cfg vs runtime — three distinct layers

Important distinction when planning fleet uniformity:

| Layer | What it controls | How to change | When it applies |
|---|---|---|---|
| Build-time `#define` | Default value compiled into firmware | `build_flags = -D WLED_FPS=100` in `platformio_override.ini` | Only on **fresh-flashed devices with no cfg.json** (factory-fresh, or after `LittleFS.format()`). Does **not** override an existing `cfg.json`. |
| Persistent `cfg.json` | Override of build defaults, persisted in LittleFS | UI Save+Reboot, or `POST /settings/leds`, or `POST /json/cfg` | All boots once written. Survives firmware upgrades. |
| Runtime `/json/state` | Live (non-persistent) value | UI sliders, OPC packets, `/json/state` API | Until next reboot or until persisted via Save. |

**Practical implication for the RaceLink fleet:** adding `-DWLED_FPS=100`
to the build flags only helps newly-flashed devices. Existing devices
already have `cfg.json` with their old `fps` value — the build flag is
ignored on them. To bring an existing device into line you must either
edit `cfg.json` (UI / API) or wipe LittleFS and let the new build flag
take effect.

### Recommended build-flag additions for fresh-flash uniformity

In each `usermods/racelink_wled/build_profiles/RaceLink_Node_v*.platformio_override.ini`:

```ini
build_flags =
  ${env:racelink_node_base.build_flags}
  ; ... existing flags ...
  -D WLED_FPS=100        ; default Target refresh rate for fresh flashes (Issue 3)
```

That is the **only** code-verified safe addition. ABL and Gamma have
no clean per-target build override; they must be aligned via
`cfg.json`. If the fleet grows or wipes/reflashes happen frequently,
consider scripting a "post-flash bootstrap" that does
`POST /settings/leds` with the desired ABL+Gamma values once the
device joins the network.

## Code-level patches that should be removed (S1–S4)

All four speculative patches under "Speculative — no observable
improvement" above are in the working tree but were never synced to
the `RaceLink_WLED` repo because they did not contribute to any of
the three fixes (which were all operator-side). They make the code
harder to read and to merge against upstream WLED. **Recommendation:
remove them as a block, one commit per S-step, before the next sync
to `RaceLink_WLED`.**

Removal order (preserves compileability between commits):

1. **S2** — single-line `strip.trigger()` deletion in `handleSync`.
   Isolated, no dependencies. Trivial revert if ever needed.
2. **S4 + S3** as one block — S4's `seg.startTransition(0)` lives
   inside `applySegmentReplace`, which goes away with S3. Reverting
   `showPairConfirmedEffect`, `applyCycleColor`, and
   `showBootRandomColor` to their pre-2026-05 direct-`seg.setMode()`
   form drops S4 automatically.
3. **S1** — ISR-timestamp + `rxAtMs` callback-chain. Revert from
   the outside in: `handleSync` signature → `handlePacket` →
   `on_rx_node` → `Callbacks::onRxPacket` typedef → `service()`
   snapshot → ISR trampoline body → `Core::dio1AtMs` field.

After removal:

- Compile all three RaceLink build profiles (V3-S2, V4-S3, any third
  variant).
- Smoke-test on V3 + V4: SYNC group running, Strobe still in phase
  (it should be — that's now an operator-state fix, independent of
  the code patches), `showPairConfirmedEffect()` Breathe pulse
  visible on a properly-configured device, `showBootRandomColor()`
  flashes on boot.

If any of these patches is needed in the future, the pre-revert
commits are the documentation. The exact line:column pointers in the
"Speculative — no observable improvement" section above stay valid
for the pre-revert tree and identify each touch point.

## What was tried that did NOT change V3↔V4 sync behavior

For reference — these were the failed code-level hypotheses during
the diagnosis phase. None of them moved the needle; the actual cause
turned out to be Operator state (`Target refresh rate = 0` plus the
`FRAMETIME` term in `mode_strobe`'s period formula). Listed here so
a future investigator doesn't repeat them:

- Moving the local timestamp from handler entry to ISR entry (S1
  above). Eliminated loop-polling latency variance as a noise source.
  No measurable improvement.
- Forcing a render at SYNC reception via `strip.trigger()` (S2 above).
  Re-aligns frame phase to broadcast-SYNC instant. No visible
  improvement.
- Setting all segment fields explicitly via `buildEffectFullDefaults()`
  (S3 above). Eliminated segment-state leakage as an explanation.
  No improvement to either sync drift OR weak-Breathe.
- Forcing transition cleanup via `seg.startTransition(0)` (S4 above).
  No improvement.

### Open hypotheses (relevant if a residual fps gap or sub-frame phase drift surfaces later)

- **NeoPixelBus RMT pipeline difference between S2 and S3** — both
  platforms use `NeoEsp32RmtHIN<X>Method` ([`wled00/bus_wrapper.h:248-253`](wled00/bus_wrapper.h#L248-L253)),
  but the underlying RMT hardware on S2 vs S3 differs (different
  generation, different FIFO depth). May explain the V3≈240 fps vs
  V4≈124 fps gap in unlimited-mode. Verifying would require reading
  the NeoPixelBus RMT driver sources directly and/or microbenchmarking
  `bus->show()` wall-clock. Out of scope for the sync issue, which is
  resolved by pinning Target refresh rate.
- **Master-side TX timing jitter** — `OPC_SYNC` packet's `ts24` is
  filled by the master at some point in its TX queue; if the master's
  TX latency varies, slaves see the same wire-content but at slightly
  shifted wire-times. Symmetric across all slaves though — wouldn't
  produce V3↔V4-asymmetric drift. Low priority.

If a *new* sync issue surfaces in the future where pinned `_targetFps`
no longer suffices, the recommended diagnostic is **hardware**, not
code: GPIO pulse at SYNC RX (ISR), second GPIO pulse at LED data line
edge, two-channel scope across V3 and V4. That isolates rendering
pipeline latency from software-visible state.

## Sync state of the RaceLink_WLED repo

As of 2026-05-08 the `RaceLink_WLED` repo is **behind** the WLED
working tree, and the recommended next sync should follow an S1–S4
cleanup pass.

**In `RaceLink_WLED` (synced 2026-05-06):**

- ePaper async refactor
- Runtime-configurable pins
- German→English comment translations

**Only in the WLED working tree (NOT synced):**

- All four speculative patches S1–S4.

**Recommended next steps before next sync:**

1. Remove S1–S4 in the order described in the
   "Code-level patches that should be removed" section above
   (one commit per S-step).
2. Optionally add `-D WLED_FPS=100` to both
   `RaceLink_Node_v3_s2_llcc68.platformio_override.ini` and
   `RaceLink_Node_v4_s3_llcc68.platformio_override.ini` for
   fresh-flash uniformity (existing devices already have their
   `cfg.json` corrected via UI).
3. Sync the cleaned tree to the `RaceLink_WLED` repo.

The detailed file:line pointers in the "Speculative — no observable
improvement" section remain the single source of truth for what each
S-patch touched, in case any of them is later wanted back.

This page is the authoritative reference for option 2. Use the
file:line pointers above and the per-section rollback notes.

## Related docs

- [Pin configuration — operator guide](pin-config.md)
- [Radio modules — developer guide](radio-modules.md)
- Project changelog: [`changelog.md`](../changelog.md) (2026-05-07
  entry summarises this session)
