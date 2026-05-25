# Indicators

A central, animated, time-limited notification mechanism. Whenever a
RaceLink WLED node needs to show the operator a status event, it
plays a short overlay on the main segment for a fixed number of
seconds, then yields back to whatever the strip was showing before.

Indicators are **always animated (STROBE)** and **never pure red /
green / blue / white**, so an indicator visual cannot be confused
with a normal scene colour. The 2026-05-17 standardisation retired
BREATH for indicators (too subtle for race-environment visibility)
and pinned every catalog row to STROBE.

For the wire-level packet that carries the indicator, see
[`../reference/wire-protocol.md` §`P_Indicate`](../reference/wire-protocol.md#p_indicate-status-indicator-overlay-opc_indicate-2-b-fixed).
The glossary entry for Indicator is in
[`../glossary.md` §Indicator](../glossary.md#indicator).

## Catalog

All entries use **fxMode 23 (STROBE)**. Most rows pin **intensity 128**
and **brightness 230**; the `IND_PAIRING_TX` row deliberately deviates
(see footnote). Speed encodes a 3-tier urgency code; colour encodes
the event category.

| Indicator | Visual | Speed | Default duration | Trigger |
|---|---|---:|---:|---|
| `IND_PAIR_CONFIRMED` | Bright-teal STROBE (`0x00FFAA`) | 235 (slow) | 5 s | Slave received and applied `OPC_SET_GROUP` |
| `IND_HEADLESS_ENTER` | Ice-cyan STROBE (`0x00CCFF`) | 245 (medium) | 5 s | Promotion to Headless Master succeeded |
| `IND_HEADLESS_EXIT` | Amber STROBE (`0xFFAA00`) | 245 (medium) | 5 s | Step-down from Headless Master (manual 5-click or runtime override by a real Gateway) |
| `IND_IDENTIFY` | Magenta STROBE (`0xFF00CC`) | 245 (medium) | 5 s | Operator clicked the device name (or "Locate" in the low-battery dialog) in the host UI — physically locate this device |
| `IND_PROBE_REJECTED` | Red-orange STROBE (`0xFF3300`) | 250 (fast) | 5 s | Headless promotion refused — a real master is on the channel |
| `IND_PAIRING_TX` | Green-cyan STROBE (`0x00FF40`) | 248 (medium-fast) | 1.5 s | Headless Master sent a `OPC_SET_GROUP` packet — pairing TX. Fires both for a new-device pairing (slave reports `groupId = 0`) and for every send of the post-reboot re-bind sweep over the persistent slave registry. **Does NOT fire** for routine scene / sync / brightness broadcasts. **Local-only** (never wire-triggered), **throttled to 200 ms** between successive triggers so back-to-back sends don't extend the deadline into a sustained overlay. With the current 500 ms re-bind spacing the operator sees discrete flashes per slave (one ~1.5 s blip per `SET_GROUP`); the throttle still prevents accidental retrigger storms if the interval is ever reduced. Intensity 96 / brightness 200 (shorter on-pulse, lower glare). |

Speeds are confined to the WLED-effective STROBE range 235..252;
the 3 tiers (235 / 245 / 250) are far enough apart to be
distinguishable but never feel sluggish or seizure-inducing.
Colours follow a channel-dominance scheme: green-dominant =
success, blue-dominant = promotion, red-dominant = error,
red+blue = operator-locate, mixed warm = demotion.

When triggered remotely via `OPC_INDICATE`, the duration is whatever
the sender writes into the 2-byte body. `durationSec == 0` is a cancel
signal — the receiver clears any active indicator without showing a
new one. See
[`../reference/wire-protocol.md` §`P_Indicate`](../reference/wire-protocol.md#p_indicate-status-indicator-overlay-opc_indicate-2-b-fixed)
for the wire detail.

## Rendering: frame-buffer overlay

Indicators render via WLED's `Usermod::handleOverlayDraw()`
callback, which fires after every segment effect has been
rendered and blended into the strip frame-buffer, immediately
before pixels are pushed to hardware. The RaceLink usermod writes
its strobe pixels directly into the frame-buffer (via
`strip.setPixelColor()`); the underlying effect's segment mode,
palette, colour slots, `SEGENV` runtime state, and any heap
allocated via `SEGENV.data` are **never touched** for the
duration of the indicator. The off-phase of the strobe paints
the segment range black (covered overlay) so the indicator is
visually identical to the legacy `setMode(STROBE)` behaviour
without any of the side effects.

Consequences:

* **Fleet phase sync is preserved automatically.** Time-driven
  effects (e.g. Traffic Light, which stores its phase in
  `SEGENV.aux0`/`step`) keep their pre-indicator phase clock
  because the effect engine never sees the indicator — it
  continues advancing as if no overlay existed. On indicator
  expiry the device is therefore in the exact phase its
  fleet-mates are in, with no catch-up cycling.
* **No snapshot / restore** is involved on the WLED side; the
  catalog values for the active indicator are held by the
  usermod's `IndicatorState` only as long as the overlay needs
  them to repaint each frame.

## Preemption

A new wire command during an active indicator (`OPC_HEADLESS`,
`OPC_CONTROL`, `OPC_PRESET`) preempts the overlay by clearing the
active flag — the new state takes over the segment, and the
overlay stops overwriting the frame-buffer on the next frame.
Waiting for the indicator to expire would feel laggy when the
operator or host has explicitly asked for a new state.

If a second indicator triggers while the first is still running,
the active indicator's catalog values are simply replaced — the
overlay keeps painting, just with the new colour/speed/duration.
The underlying effect is unaffected either way.
