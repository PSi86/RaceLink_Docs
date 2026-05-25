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

The `racelink_wled` usermod re-applies a small set of WLED LED
settings on every boot so they stay identical across every node in
a fleet. Divergence in this exact set (Target refresh rate, ABL,
Gamma correction) was the root cause of the V3↔V4 Strobe phase
drift and fleet-wide effect-intensity mismatches identified in
early-May 2026 field testing.

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

> **The WLED web UI is not the right place to deviate from these
> defaults.** Manual changes survive only until the next reboot;
> `applyRaceLinkDefaults()` reverts them. To deviate intentionally,
> use one of the paths in [§"Changing defaults / under the
> hood"](#changing-defaults-under-the-hood) below.

> **Triple-tap recovery still works.** The usermod's triple-tap
> gesture opens the AP via `WLED::instance().initAP(true)` directly,
> which bypasses `apBehavior`. Setting `apBehavior=3` ("Never")
> therefore only disables WLED's *automatic* AP-opening paths; the
> operator-driven recovery path is unaffected.

### Verifying what a node is currently enforcing

* **Live values.** Open `http://<node-ip>/json/info` and inspect the
  `fps` field (current measured FPS). For the persisted ABL and gamma
  settings, open `http://<node-ip>/json/cfg` and read `hw.led.maxpwr`
  and `light.gc.*`.
* **Drift events.** If a node has a serial console attached, the
  boot output includes `[RaceLink] enforcing …` lines for every
  setting that was corrected on that boot. A clean device prints
  none of them. After a successful self-heal, the next reboot is
  silent.
* **What this build expects.** Check the active build profile
  (`platformio_override.ini` for the env you flashed) for any
  `RACELINK_DEFAULT_*` `-D` flags. If none are present, the
  compile-time defaults apply: FPS 75, ABL disabled, gamma color on,
  gamma brightness off, gamma value 2.2, AP open behaviour
  "Never" (3).

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

### Per-device override at runtime (`OPC_CONFIG`)

The host (gateway) can push a persistent per-device override for
any of the LED settings the usermod manages, via `OPC_CONFIG`
option codes `0x05..0x0A`. The override is stored in `cfg.json`
under `RaceLink.overrides.*` and survives reboots; from that point
on, `applyRaceLinkDefaults()` enforces the host-authorised value
rather than the compile-time default.

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
[`../reference/opcodes.md` §"OPC_CONFIG — device configuration"](../reference/opcodes.md#opc_config-device-configuration).
The byte-level wire format is in
[`../reference/wire-protocol.md` §`P_Config`](../reference/wire-protocol.md#p_config-configuration-body-opc_config-opc_get_config-5-b-fixed).

The current overrides for a given device are visible in
`GET /json/cfg` under the `RaceLink.overrides` object — absence of
a key means "no override". This HTTP path remains as an
out-of-band debug fallback.

The **primary read path** is the wire opcode `OPC_GET_CONFIG`,
which the host's Device Options dialog uses automatically when
opened. For each property option (`0x05`–`0x0A`, plus STARTBLOCK
`0x8C`/`0x8D`) the dialog issues one read, compares the device's
live value against the host's stored intent, and surfaces any
mismatch as a *device: &lt;value&gt; ⚠* badge with **Push host** /
**Import device** buttons — see [`../reference/opcodes.md` §"Live
read and divergence resolution"](../reference/opcodes.md#live-read-and-divergence-resolution)
for the operator workflow.

### Reset to RaceLink defaults

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

### Changing defaults / under the hood

The remainder of this section is firmware-internal background and
the per-build (compile-time) override path. Operators on a
correctly-flashed fleet typically do not need any of it — the
information above covers the day-to-day reads, host-side overrides,
and the reset path.

#### Boot-time behaviour

On every boot, the usermod's `applyRaceLinkDefaults()` runs once
near the start of `setup()`:

1. WLED has already loaded `cfg.json`. The relevant globals
   (`_targetFps`, `BusManager::_gMilliAmpsMax`, `gammaCorrect*`)
   hold whatever the saved configuration carried.
2. For each enforced setting, `applyRaceLinkDefaults()` compares
   the loaded value against the RaceLink default.
3. If they differ:
   * The runtime value is overwritten with the default.
   * A `[RaceLink] enforcing <setting> default <new> (was <old>)`
     line is written to the serial debug log.
   * The internal `configNeedsWrite` flag is raised.
4. If any drift was corrected, WLED's main loop calls
   `serializeConfigToFS()` on its next iteration and persists the
   corrected values back into `cfg.json`. Same write path WLED
   uses when the operator hits *Save* in the web UI.

After this first self-healing boot, `cfg.json` matches the
RaceLink defaults exactly. Subsequent boots are silent: no log
line, no `cfg.json` write.

#### Why UI changes don't survive a reboot

Operators **can still change these values from the WLED web UI**.
*Save* accepts the change and writes `cfg.json` exactly as before;
the change takes effect immediately and lives until the next
reboot. On the next boot, however, `applyRaceLinkDefaults()`
detects the drift, overrides the runtime value back to the
RaceLink default, and re-saves `cfg.json` with the default. **UI
changes to these specific settings do not survive a reboot.**
This is intentional — these settings are part of the wire-level
synchronisation contract for a RaceLink fleet, and per-device
divergence breaks fleets visibly (V3↔V4 Strobe drift, mismatched
effect intensity, etc.).

#### Per-build override (compile-time)

Edit the matching `*.platformio_override.ini` build profile and
add the relevant `RACELINK_DEFAULT_*` flags to its `build_flags`
block:

```ini
build_flags =
  ; ... existing flags ...
  -D RACELINK_DEFAULT_FPS=60
  -D RACELINK_DEFAULT_ABL_MAX_MA=500
  -D RACELINK_DEFAULT_GAMMA_COL=false
```

Re-flash. On the next boot, `applyRaceLinkDefaults()` enforces the
new values; existing devices upgrading to a build with different
defaults get their `cfg.json` corrected on first boot.

This path is appropriate when an entire hardware variant needs a
different value (for example, a profile with longer LED strips
that benefits from a lower FPS cap to keep the per-frame render
budget in check).

The compile-time defaults live in
[`usermods/racelink_wled/racelink_wled.h`](https://github.com/PSi86/RaceLink_WLED/blob/main/racelink_wled.h)
under the `Fleet-uniformity defaults` section. All five macros are
`#ifndef`-guarded so a build-flag override always wins.

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
[`../reference/opcodes.md`](../reference/opcodes.md) §"Cyclic-effect phase-lock".

For the catalogue of which WLED effects are deterministic (and
therefore safe to use in offset mode) see
[`../reference/deterministic-effects.md`](../reference/deterministic-effects.md).

## Indicators

The WLED node uses short STROBE overlays (5 s, 1.5 s for
pairing-TX) to signal status events — pair confirmation, probe
rejection, headless enter/exit, operator-initiated locate. Every
catalog row, the rendering model (frame-buffer overlay via
`handleOverlayDraw()`), and preemption rules live in
[`indicators.md`](indicators.md). The wire-level packet is in
[`../reference/wire-protocol.md` §`P_Indicate`](../reference/wire-protocol.md#p_indicate-status-indicator-overlay-opc_indicate-2-b-fixed).

## Headless Mode

A five-click on the boot/user button promotes the device to
Headless Master after a 1.5 s `IDENTIFY_REPLY` probe — letting a
session run without a Gateway+Host pair. A real Gateway always
wins (any M2N traffic from a non-self sender forces step-down).
The full workflow (activation, pairing slaves, scene catalog,
brightness, stepping down, persistence + proactive re-bind, probe
collision) lives in [`headless-mode.md`](headless-mode.md).

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
