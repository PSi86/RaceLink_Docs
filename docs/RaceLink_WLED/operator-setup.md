# WLED Node Operator Setup

How to identify, pair, configure and recover a flashed RaceLink WLED
node. For build-from-source instructions see [`README.md`](README.md).

> **Audience.** Operators who have one or more flashed RaceLink WLED
> nodes and want to use them on a race. If you need to flash a node,
> start with [`README.md`](README.md).

## Identifying a node

A RaceLink WLED node is a WLED-based wireless device augmented with
the `racelink_wled` usermod. You can identify one by:

* **`/json/info` endpoint** while connected to the node's Wi-Fi
  AP. The `vid` field carries the WLED build identifier and the
  `arch` field shows the SoC variant (`esp32-c3`, `esp32-s2`,
  `esp32-s3` for current build profiles).
* **Web UI title** while in AP mode usually reads "WLED" — the
  RaceLink-specific functionality lives in the wireless control
  path, not the WLED web UI.
* **MAC address** (12-char hex). The host's WebUI shows the last
  six characters in the device table for brevity.

## Default factory state

After a fresh flash, a RaceLink WLED node boots with:

| Aspect | Default |
|---|---|
| Wi-Fi AP SSID | `WLED_RaceLink_AP` (newer firmware) or `WLED-AP` (older firmware) |
| AP password | `wled1234` |
| AP IP | `4.3.2.1` |
| OTA password | `wledota` (`DEFAULT_OTA_PASS`) |
| OTA lock | off (`otaLock=false` because the build does not define `WLED_OTA_PASS`) |
| Same-subnet OTA gate | **on** (`otaSameSubnet=true`) — the host's OTA workflow flips this off automatically; see [`../RaceLink_Host/operator-guide.md`](../RaceLink_Host/operator-guide.md) §"Common OTA failure modes" |
| Settings PIN | unset |
| Master MAC binding | unset (will pair to the first gateway it discovers) |
| Group ID | unset (lands in group 0 "Unconfigured" on the host) |
| Boot effect | random Solid color when WLED's *Apply preset at boot* is `0`; otherwise the configured boot preset wins (see [§"Boot effect"](#boot-effect)) |
| LED runtime settings | re-applied on every boot from the RaceLink defaults; see [§"RaceLink-enforced LED defaults"](#racelink-enforced-led-defaults) |

## RaceLink-enforced LED defaults

The `racelink_wled` usermod re-applies a small set of WLED LED settings
on every boot, **after** WLED has finished deserialising `cfg.json`. The
point is to keep these settings identical across every node in a fleet
— divergence here was the root cause of the V3↔V4 Strobe phase drift
identified on 2026-05-08 and the fleet-wide effect-intensity mismatches
earlier the same week (see
[`dev-session-2026-05-sync-investigation.md`](dev-session-2026-05-sync-investigation.md)
for the investigation that motivated this enforcement).

### What is enforced

| WLED setting | RaceLink default | Reason for enforcement |
|---|---|---|
| Target refresh rate (`hw.led.fps`) | **75 fps** | V3 (ESP32-S2) and V4 (ESP32-S3) both reach 75 fps comfortably. Pinning prevents per-platform free-running rates (V3≈240 fps vs V4≈124 fps when uncapped) that cause `mode_strobe`'s cycle period to differ across platforms — the canonical V3↔V4 Strobe-drift trigger. |
| Automatic Brightness Limiter (`hw.led.maxpwr`) | **0 mA (disabled)** | ABL caps the per-frame current draw by globally scaling brightness down whenever the rendered frame would exceed the configured budget. Per-device variations in that budget (PSU headroom, cable losses, ABL setting) cause visible intensity divergence on bright frames across the fleet. Enable ABL deliberately on individual nodes that need it — typically nodes driving more than ~120 LEDs, where strip current draw on full-white frames can exceed the PSU or wiring rating. |
| Gamma correction for color (`light.gc.col`) | **on** | Per-device on/off mismatches produce visibly different fade curves and perceived effect intensity. |
| Gamma correction for brightness (`light.gc.bri`) | **off** | Matches WLED's own default. |
| Gamma value (`light.gc.val`) | **2.2** | WLED's standard, visually correct on WS2812-class strips. |
| AP open behaviour (`nw.ins[0].ap.behav`) | **3 (Never)** | After a factory reset WLED defaults to behaviour `0` ("No connection after boot"), which auto-opens the node's WiFi AP on every boot when no STA is configured. RaceLink fleets keep the AP closed and reach nodes via the triple-tap recovery gesture (see [§"Physical button"](#physical-button-bootuser-button)) — auto-opening on every boot is chatty RF and breaks the "node is silent until I want to talk to it" property. |

UI paths for the same settings (in the WLED web UI):

* **Target refresh rate** → Settings → LED & Hardware → Advanced
* **Brightness limiter** → Settings → LED & Hardware → LED setup → Enable automatic brightness limiter
* **Gamma correction for color** → Settings → LED & Hardware → Color & White → Use Gamma correction for color
* **AP open behaviour** → Settings → WiFi Setup → AP opens (select "Never (not recommended)")

> **Triple-tap recovery still works.** The usermod's triple-tap gesture
> opens the AP via `WLED::instance().initAP(true)` directly, which
> bypasses `apBehavior`. Setting `apBehavior=3` ("Never") therefore only
> disables WLED's *automatic* AP-opening paths; the operator-driven
> recovery path is unaffected.

### Boot-time behaviour

On every boot, the usermod's `applyRaceLinkDefaults()` runs once near
the start of `setup()`:

1. WLED has already loaded `cfg.json`. The relevant globals
   (`_targetFps`, `BusManager::_gMilliAmpsMax`, `gammaCorrect*`)
   hold whatever the saved configuration carried.
2. For each enforced setting, `applyRaceLinkDefaults()` compares the
   loaded value against the RaceLink default.
3. If they differ:
   * The runtime value is overwritten with the default.
   * A `[RaceLink] enforcing <setting> default <new> (was <old>)` line
     is written to the serial debug log.
   * The internal `configNeedsWrite` flag is raised.
4. If any drift was corrected, WLED's main loop calls
   `serializeConfigToFS()` on its next iteration and persists the
   corrected values back into `cfg.json`. This is the same write path
   WLED uses when the operator hits *Save* in the web UI; nothing
   special happens here.

After this first self-healing boot, `cfg.json` matches the RaceLink
defaults exactly. Subsequent boots are silent: no log line, no
`cfg.json` write.

### Consequence for operator UI changes

Operators **can still change these values from the WLED web UI**.
*Save* accepts the change and writes `cfg.json` exactly as before, and
the change takes effect immediately and lives until the next reboot.

On the next boot, however, `applyRaceLinkDefaults()` detects the drift,
overrides the runtime value back to the RaceLink default, and re-saves
`cfg.json` with the default. **UI changes to these specific settings
do not survive a reboot.** This is intentional — these settings are
part of the wire-level synchronisation contract for a RaceLink fleet,
and per-device divergence breaks fleets visibly (V3↔V4 Strobe drift,
mismatched effect intensity, etc.).

If you need to deviate from the defaults for a node, do not change
them via the WLED UI — change them through one of the paths in
[§"Changing RaceLink defaults"](#changing-racelink-defaults) below.

### Changing RaceLink defaults

#### Per-build override (compile-time)

Edit the matching `*.platformio_override.ini` build profile and add
the relevant `RACELINK_DEFAULT_*` flags to its `build_flags` block:

```ini
build_flags =
  ; ... existing flags ...
  -D RACELINK_DEFAULT_FPS=60
  -D RACELINK_DEFAULT_ABL_MAX_MA=500
  -D RACELINK_DEFAULT_GAMMA_COL=false
```

Re-flash. On the next boot, `applyRaceLinkDefaults()` enforces the new
values; existing devices upgrading to a build with different defaults
get their `cfg.json` corrected on first boot.

This path is appropriate when an entire hardware variant needs a
different value (for example, a profile with longer LED strips that
benefits from a lower FPS cap to keep the per-frame render budget in
check).

The compile-time defaults live in
[`usermods/racelink_wled/racelink_wled.h`](https://github.com/PSi86/RaceLink_WLED/blob/main/racelink_wled.h)
under the `Fleet-uniformity defaults` section. All five macros are
`#ifndef`-guarded so a build-flag override always wins.

#### Per-device override at runtime (`OPC_CONFIG`)

The host (gateway) can push a persistent per-device override for any
of the LED settings the usermod manages, via `OPC_CONFIG` option
codes `0x05..0x0A`. The override is stored in `cfg.json` under
`RaceLink.overrides.*` and survives reboots; from that point on,
`applyRaceLinkDefaults()` enforces the host-authorised value rather
than the compile-time default.

The available options as of 2026-05-09:

| OPC_CONFIG option | Setting | Wire payload (LE) |
|---|---|---|
| `0x05` | Target refresh rate | `data0` = uint8 fps |
| `0x06` | Segment 0 geometry | `data0..1` = uint16 start, `data2..3` = uint16 stop |
| `0x07` | Segment 1 geometry | as `0x06` (device appends seg[1] if missing) |
| `0x08` | ABL max mA | `data0..1` = uint16 mA (`0` = ABL disabled) |
| `0x09` | Default brightness (`briS`) | `data0` = uint8 |
| `0x0A` | Transition duration | `data0..1` = uint16 ms |
| `0x0F` | Clear all overrides | `data0..3` = 0 |

The semantic model (Policy A vs Policy B), persistence path, and
host-side implementation notes live in
[`../concepts/opcodes.md` §"OPC_CONFIG — device configuration"](../concepts/opcodes.md#opc_config-device-configuration).
The byte-level wire format is in
[`../reference/wire-protocol.md` §`P_Config`](../reference/wire-protocol.md#p_config-configuration-body-opc_config-opc_get_config-5-b-fixed).

The WLED web UI is **not** the right place to deviate from a
RaceLink default — UI changes to the affected settings are reverted
by `applyRaceLinkDefaults()` on the next reboot, regardless of
override status. Use the host UI (or send the OPC_CONFIG packet
directly during development) so the override is recorded.

The current overrides for a given device are visible in
`GET /json/cfg` under the `RaceLink.overrides` object — absence of a
key means "no override". This HTTP path remains as an out-of-band
debug fallback.

The **primary read path** is the wire opcode `OPC_GET_CONFIG`, which
the host's Device Options dialog uses automatically when opened.
For each property option (`0x05`–`0x0A`, plus STARTBLOCK `0x8C`/`0x8D`)
the dialog issues one read, compares the device's live value against
the host's stored intent, and surfaces any mismatch as a *device:
&lt;value&gt; ⚠* badge with **Push host** / **Import device** buttons —
see [`../concepts/opcodes.md` §"Live read and divergence
resolution"](../concepts/opcodes.md#live-read-and-divergence-resolution)
for the operator workflow.

#### Reset to RaceLink defaults

The destructive maintenance action **Reset to RaceLink defaults**,
exposed in the WLED tab of the Device Options dialog, sends
`OPC_CONFIG` option `0x0F`. The device clears every host-set
RaceLink override **and applies the RaceLink baseline values
immediately at runtime** — no reboot required:

* **FPS** → `RACELINK_DEFAULT_FPS` (75 unless build-flag overridden).
* **ABL max mA** → `RACELINK_DEFAULT_ABL_MAX_MA` (0, ABL disabled).
* **Default brightness `briS`** → `RACELINK_DEFAULT_BRIS` (128).
* **Transition duration** → `RACELINK_DEFAULT_TRANSITION_MS` (700 ms).
* **Segments** → single `seg[0]` spanning the full strip; any
  extra segments are removed.

The new values are written into `cfg.json` on the next main-loop
iteration so the change persists across reboots.

**Host side**: the dialog resets `dev.specials[wled_*]` to the
host's schema defaults and re-reads each property from the device.
Policy A rows and the briS / transition rows match the device
immediately. **Segment rows show a divergence warning** — the
host has no way to know the device's strip length, so the
operator clicks **Import device** on each segment row to adopt
the device's actual seg geometry into the host database. This is
the only manual step after a reset.

The action is gated behind a destructive-confirm dialog. Use it
when commissioning a fresh device that previously held overrides
from a different fleet, or when intentionally returning a device
to its build-profile baseline.

### Verifying what a node is currently enforcing

* **Live values.** Open `http://<node-ip>/json/info` and inspect the
  `fps` field (current measured FPS). For the persisted ABL and gamma
  settings, open `http://<node-ip>/json/cfg` and read `hw.led.maxpwr`
  and `light.gc.*`.
* **Drift events.** If a node has a serial console attached, the boot
  output includes `[RaceLink] enforcing …` lines for every setting
  that was corrected on that boot. A clean device prints none of them.
  After a successful self-heal, the next reboot is silent.
* **What this build expects.** Check the active build profile
  (`platformio_override.ini` for the env you flashed) for any
  `RACELINK_DEFAULT_*` `-D` flags. If none are present, the
  compile-time defaults from `racelink_wled.h` apply: FPS 75, ABL
  disabled, gamma color on, gamma brightness off, gamma value 2.2,
  AP open behaviour "Never" (3).

### Settings that are *not* enforced

The usermod deliberately stays out of these settings. They remain
operator-controlled:

* LED Setup (bus configuration, pin assignments, total LED count).
* Segment geometry (`seg[].start/stop`). This is planned to move
  under RaceLink control as part of the future two-segment routing
  feature.
* Boot preset (`Apply preset at boot`). See [§"Boot effect"](#boot-effect).
* Wi-Fi, OTA, security, time/timezone.
* Effect parameters at runtime (mode, color, palette, etc.). These
  are driven by the RaceLink wire protocol; the WLED web UI is a
  viewer for the current state, not a sanctioned editor.

## Boot effect

When the node boots, the `racelink_wled` usermod inspects WLED's
*LED & Hardware → General settings → Apply preset at boot* value:

* **`0` (default)** — usermod paints a **persisted Solid colour** on
  the main segment so an operator can confirm the node has booted even
  before any gateway is in range and can visually identify a specific
  device across power cycles. No WLED preset is loaded; the colour
  simply replaces the dark default.
* **non-zero** — WLED's standard boot-preset path runs untouched.
  Use this slot to call a macro, a playlist, or any preset of your
  choice; the usermod stays out of the way.

This makes the boot animation an operator-controlled choice rather
than a fixed firmware behavior.

### Persistent boot colour

The boot colour is **rolled once on the very first boot** of a freshly
flashed device — `esp_random() % 3` picks red, green or blue — and
immediately written to `cfg.json`. Every subsequent boot reuses the
stored value, so the same device always lights up in the same colour
until the operator changes it.

The operator changes it by walking the [§"Click colour cycle"](#click-colour-cycle):
each short press of the button advances along R → G → B → random RGB.
**10 seconds after the last click** the currently-displayed colour is
written back to `cfg.json` as the new boot colour. A random RGB picked
at the end of the cycle is stored verbatim (3-byte R/G/B triple) and
re-applied exactly at the next boot — it is not re-rolled.

> **Storage location.** `RaceLink.overrides.Boot Color Mode` (0 = red,
> 1 = green, 2 = blue, 3 = stored RGB) plus `Boot Color R/G/B` in
> `cfg.json`. Visible and editable via the WLED **Config → Usermod
> Settings → RaceLink** UI for diagnostic purposes.

The boot pick also seeds the physical-button colour-cycle position so
the first click advances along the R → G → B sequence instead of
repeating the boot colour (see [§"Click colour cycle"](#click-colour-cycle)).

## Pairing with a gateway

A node pairs with the first gateway that broadcasts `OPC_DEVICES`
during a discovery. To pair:

1. Power up the node within radio range of your gateway.
2. From the host's WebUI, click **Discover Devices**, choose
   "Unconfigured" as the assignment group, click **Start**.
3. The node responds with its `IDENTIFY_REPLY` and the gateway's
   MAC is recorded as the node's master MAC.

## Pairing visual feedback

Once the node accepts an `OPC_SET_GROUP` from the gateway (i.e. it
has been confirmed and configured), it plays the `IND_PAIR_CONFIRMED`
indicator: a **5-second bright-teal STROBE overlay** on the main
segment. After the 5 seconds elapse, the indicator restores whatever
the strip was showing before — typically the boot colour for a
freshly-flashed node. The gateway is expected to send a scene or
preset within that window, which preempts the indicator without
restore.

The pair feedback is rendered via direct effect calls; **no WLED
preset slot is reserved**, so the operator can freely use all
preset slots (1–250) for race content.

See [§"Indicators"](#indicators) below for the full catalog of
indicator visuals and what each one means.

## Re-pairing to a different gateway

If a node was previously bound to a different gateway:

1. From the host's WebUI device list, open the **Node Config**
   dropdown for the node and pick **Forget master MAC** → **Send**.
   The node clears its bound master MAC.
2. Re-run **Discover Devices** from the new gateway. The node
   responds and binds to the new master MAC.

This is the standard migration path between gateways. Use it when
moving fleets between events or replacing a damaged dongle.

## Switching between AP and STA mode

WLED nodes can run in pure AP mode, pure STA mode, or AP+STA mode.
RaceLink fleets default to **AP mode** for OTA reachability and
**no STA configured** so the device is self-contained.

To configure STA, connect to the node's AP, open the WLED web UI,
go to *Wi-Fi Settings*, and enter the SSID and password of your
LAN. Save. The node reboots into AP+STA: it advertises
`WLED_RaceLink_AP` *and* connects to your LAN.

> **AP+STA OTA caveat.** In AP+STA mode `Network.localIP()`
> returns the **STA** address, so an AP-side OTA host's
> `inSameSubnet` check fails even with a valid `4.3.2.x` DHCP
> lease from the node's AP. The host's OTA workflow detects the
> resulting HTTP 401, POSTs `/settings/sec` to flip
> `otaSameSubnet=false`, and retries — see
> [`../RaceLink_Host/developer-guide.md`](../RaceLink_Host/developer-guide.md)
> §"WLED OTA gate matrix" for the full picture.

## Physical button (boot/user button)

RaceLink WLED nodes built on HT-CT62 / similar ESP32-Cx boards
expose a single physical push button on GPIO 0 (the SoC boot
button). The usermod replaces WLED's default short/long/double
button mapping with the gestures below.

| Gesture | Action | Master-quiet gate? |
|---|---|---|
| Single short press | When idle: step through a colour cycle (Solid mode): red → green → blue → random → random → … See [§"Click colour cycle"](#click-colour-cycle) for details. When Headless Master: advance to the next scene in the catalog and broadcast it to the fleet. | yes when idle; no when Headless Master |
| Press-and-hold | Brightness fades up and down (ping-pong: bounces off the min and max levels) for as long as the button is held; the starting direction flips on each new hold. **S-curve**: speed slows near 0 and 255 so the operator can comfortably dial in min/max. When Headless Master: the final brightness is broadcast to the fleet exactly once on release (no per-tick TX during the fade). | yes when idle; no when Headless Master |
| Two short presses | Reserved (no action) — intentional accidental-press safety gap between single-click and the AP / Headless gestures. | n/a |
| Three short presses (within 500 ms of each other) | Open the Wi-Fi access point (`4.3.2.1`) | no — always works |
| Four short presses | Reserved (no action) — typo guard so a slipped 4-click between AP and Headless does not accidentally trigger AP. | n/a |
| Five short presses | Toggle [Headless Mode](#headless-mode). When idle: run the IDENTIFY_REPLY probe and promote on success (ice-cyan STROBE indicator) or refuse on conflict (red-orange STROBE indicator). When already Headless Master: step down (amber STROBE indicator). | no — always works |
| Six or more short presses | Reserved (no action) — typo guard so an overshoot 6-click does not accidentally re-open the AP. | n/a |

### Click colour cycle

A single short press walks the three primary colours as a **ring
buffer over the fixed order red(0) → green(1) → blue(2)**, then
switches to random RGB. The starting position is randomised so the
first click is always a visible change — but the ring guarantees
that all three primaries are reachable within the first three
displayed colours regardless of where the cycle started.

**Boot interaction.** When [§"Boot effect"](#boot-effect) fires
(no boot preset configured), the boot colour is the **persisted**
value (rolled once on first boot, then locked in) and seeds the ring
at `(boot + 1) mod 3`. Two more clicks therefore cover the remaining
two primaries before the cycle drops to random:

| Boot picks | Click 1 | Click 2 | Click 3 onwards |
|---|---|---|---|
| red | green | blue | random RGB |
| green | blue | red | random RGB |
| blue | red | green | random RGB |

When no boot effect runs (`Apply preset at boot` is non-zero), the
ring starts fresh with no boot pick — the first three clicks then
cover all three primaries in the fixed order before going random.

**Idle reset.** If the operator does not press the button for
**10 seconds**, the next click re-seeds the ring with a new random
starting index and resets the count, so the next three clicks
again cover all three primaries before going random. Idle reset is
not advertised by any LED change — it manifests only on the next
click.

**Boot-colour save.** The same 10-second idle window persists the
currently-displayed colour back to `cfg.json` as the new boot
colour (see [§"Persistent boot colour"](#persistent-boot-colour)).
The save fires exactly once per click burst — clicking again within
the 10 s window restarts the timer without writing.

**Master-quiet gate.** The first two gestures are intentionally
inert when a paired gateway is currently talking to the node:
they only fire if the node has not received any packet from the
paired master MAC for at least **60 seconds**. This prevents the
button from interfering with a live race; once the gateway falls
silent (operator turns it off, node leaves radio range, etc.),
the gestures re-arm automatically.

**Triple-tap hotspot recovery.** The triple-press gesture deliberately
ignores the quiet gate — it is the always-available fallback for
operators who need to reach the node's Wi-Fi UI to fix a
misconfiguration, regardless of radio activity. After the AP
opens, connect to `WLED_RaceLink_AP` and browse to `4.3.2.1`.

## Factory reset

WLED's web UI has a *Reset* button under *Security & Updates* that
returns most settings to defaults. To wipe RaceLink-specific state
(master MAC binding, group ID), use the host-side **Forget master
MAC** action — that is the canonical way; a WLED-side reset alone
may leave the binding in flash.

To erase the entire WLED filesystem (presets, segments, settings),
flash the node with `pio run -t uploadfs` or the equivalent
PlatformIO action. This is destructive — use only when re-purposing
a node.

## Battery-powered nodes

Some build profiles (e.g. `RaceLink_Node_v3_s2_llcc68`) include
battery measurement. The voltage threshold and scaling are
compile-time constants in the build profile; if your battery shows
incorrect voltage, check the profile's measurement-pin and
voltage-multiplier settings (see [`README.md`](README.md)
§Troubleshooting).

## Cyclic-effect phase-lock note

Cyclic WLED effects (Breathe, Pacifica — anything that renders as a
direct function of `strip.now`) used to collapse to zero phase
difference in offset mode. Recent WLED-usermod firmware fixes this
via a persistent per-device phase offset re-asserted after every
SYNC; if you observe the collapse, your node firmware is too old.
The full explanation lives in
[`../concepts/opcodes.md`](../concepts/opcodes.md) §"Cyclic-effect phase-lock".

For the catalogue of which WLED effects are deterministic (and
therefore safe to use in offset mode) see
[`../concepts/deterministic-effects.md`](../concepts/deterministic-effects.md).

## Indicators

A central, animated, time-limited notification mechanism. Whenever a
RaceLink WLED node needs to show the operator a status event, it plays
a short overlay on the main segment for a fixed number of seconds,
then yields back to whatever the strip was showing before.
Indicators are **always animated (STROBE)** and **never pure red /
green / blue / white**, so an indicator visual cannot be confused
with a normal scene colour. The 2026-05-17 standardisation
retired BREATH for indicators (too subtle for race-environment
visibility) and pinned every catalog row to STROBE.

### Catalog

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

### Rendering: frame-buffer overlay

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

### Preemption

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

## Headless Mode

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

### Activating

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

### Group-id layout

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

### Pairing slaves to a Headless Master

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

### Scenes

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

### Brightness

Long-press on the Headless Master fades the strip with an S-curve
(slower near 0 and 255, faster in the middle). The local fade is
visible on the master's strip live; the **final brightness is
broadcast to the fleet exactly once on button release** via
`OPC_CONTROL` with `RL_CTRL_F_BRIGHTNESS`. No per-tick TX during the
fade — the LoRa channel stays uncongested.

### Stepping down

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

### Persistence

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

### Probe collision (two devices simultaneously)

If two persisted-headless devices boot at the same time, both schedule
their probe with random jitter (500–2000 ms). Whichever one finishes
its probe first promotes, then answers the other one's probe with
`OPC_SET_GROUP` — so the second device demotes to a normal slave of
the first. The race is decided by jitter, never produces two masters,
and both devices end up in a consistent state.

## Common problems

* **Node does not appear in Discover.** Check the gateway is
  connected, the node is powered, and the node is in radio range.
  If the node was previously bound to a different gateway, the
  node ignores the new gateway's broadcast — use **Forget master
  MAC** to clear the binding.
* **Wrong LED count or layout.** Open the WLED web UI, go to
  *LED Preferences*, set the right strip length and pin.
* **Wrong battery reading.** Check the voltage multiplier in your
  build profile; flash a corrected profile.
* **OTA fails with 401.** See the failure-mode index in
  [`../troubleshooting.md`](../troubleshooting.md) or the
  operator-side detail in
  [`../RaceLink_Host/operator-guide.md`](../RaceLink_Host/operator-guide.md)
  §"Common OTA failure modes".
* **Physical button does nothing on short press / hold.** A paired
  master is currently transmitting to the node; the button's
  master-quiet gate suppresses color and brightness gestures while
  the gateway is active. Wait ≥60 seconds of radio silence (or
  power off the gateway) and try again. The triple-press hotspot
  gesture is unaffected and always opens the AP — use it for
  recovery if needed. See [§"Physical button"](#physical-button-bootuser-button).
