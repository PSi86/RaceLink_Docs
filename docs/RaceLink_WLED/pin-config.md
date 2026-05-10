# Pin Configuration (RaceLink WLED node)

Runtime configuration of the radio and ePaper pins on a flashed
RaceLink WLED node. Build profiles still ship a per-target *default*
set of pins so first boot picks the right wiring automatically; this
page is for operators who need to override those defaults — typically
on a custom or rewired board.

> **Audience.** Operators of flashed RaceLink WLED nodes who already
> have the firmware running and want to relocate pins via the WLED
> settings UI instead of reflashing. For build-from-source
> instructions see [`README.md`](README.md). For first-time pairing
> and basic operation see [`operator-setup.md`](operator-setup.md).

## When you need this page

The compile-time defaults baked into each shipping build profile match
the reference hardware they target. You should only change pins if:

* you built or modified a board with non-standard wiring,
* you swapped a module variant whose pin breakout differs,
* a pin conflicts with another WLED feature (e.g. an LED bus you
  configured later) and the radio or ePaper stops working.

If your hardware matches one of the supported reference boards and
the firmware was flashed with the matching build profile, leave this
page alone — the defaults are correct.

## Where the settings live

Open the WLED Web UI → **Config → Usermod Settings → RaceLink**. Two
sub-objects expose the pins:

* **`pins`** — the radio control pins (always present).
* **`epaper_pins`** — the ePaper bus and control pins (only present
  on builds compiled with `-D RACELINK_EPAPER`).

Each pin is a numeric input expecting a GPIO number. Set `-1` if the
pin is not wired (only meaningful for `MISO`, which most e-paper
panels do not expose).

After saving, the node **reboots automatically** to re-init SPI on
the new pins. The reboot only fires when at least one pin actually
changes; saving the settings unchanged does not reboot.

## Default pin assignments per supported build profile

The values below are the defaults compiled into each shipping
profile. They become the starting point in the UI on first boot or
after a factory reset.

### Radio control pins (`pins`)

| Pin   | HT-CT62 (`v1_c3_ct62`) | RaceLink Node v3 S2 (`v3_s2_llcc68`) | RaceLink Node v3 S2 + ePaper (`v3_s2_llcc68_epaper`) | RaceLink Node v4 S3 (`v4_s3_llcc68`) |
|-------|------------------------|--------------------------------------|------------------------------------------------------|--------------------------------------|
| SCK   | 10                     | 10                                   | 10                                                   | 10                                   |
| MISO  | 6                      | 6                                    | 6                                                    | 6                                    |
| MOSI  | 7                      | 7                                    | 7                                                    | 7                                    |
| NSS   | 8                      | 8                                    | 8                                                    | 8                                    |
| DIO1  | 3                      | 3                                    | 3                                                    | 3                                    |
| BUSY  | 4                      | 4                                    | 4                                                    | 4                                    |
| RST   | 5                      | 5                                    | 5                                                    | 5                                    |

> The defaults match HT-CT62 (ESP32-C3 + SX1262) wiring; per-target
> profiles override individual values via `-D RACELINK_PIN_*=...` in
> their `platformio_override.ini` if a board needs a different pin.
> Check the relevant build profile in
> [`build_profiles/`](https://github.com/PSi86/RaceLink_WLED/tree/main/build_profiles)
> for the authoritative numbers if you suspect a mismatch.

### ePaper bus and control pins (`epaper_pins`)

Only present when the firmware was built with
`-D RACELINK_EPAPER` (currently the
`v3_s2_llcc68_epaper` profile).

| Pin  | Default |
|------|---------|
| SCK  | 12      |
| MISO | -1 *(unused)* |
| MOSI | 11      |
| CS   | 10      |
| DC   | 9       |
| RST  | 46      |
| BUSY | 3       |

The ePaper SPI bus is dedicated (HSPI on supported MCUs), separate
from the radio bus, so SCK/MOSI/CS may freely overlap with the radio
pins on different physical wires.

## Reboot behavior

* Changing **any** pin in either group triggers a reboot.
* The first-boot deserialize that loads `cfg.json` does **not**
  trigger a reboot (it only reads the persisted values into the
  runtime members; nothing has changed).
* The reboot is the standard WLED `doReboot` path — the same one used
  by the *Settings → Reboot* button. Allow ~5–10 seconds for the node
  to come back up; existing pairings are kept (master MAC stays
  persisted if `MAC filter persist` is on).

## PinManager conflict troubleshooting

WLED uses an internal **PinManager** to prevent two subsystems from
fighting over the same GPIO. If you assign a pin that is already
claimed by another feature — most commonly the LED data bus —
`radioInit()` (or `epaperInit()`) refuses to allocate and the
subsystem fails to start.

Symptoms:

* **Info panel → "RaceLink Init" reads `FAIL`** with a non-zero
  init code, and no on-air RaceLink traffic happens.
* The serial log carries:
  `[RaceLink] PinManager allocation failed (LED bus conflict?)`
* For ePaper:
  `[RaceLink] ePaper PinManager allocation failed — display disabled`
  — the radio still works, but the panel stays blank.

Resolution:

1. Open **Config → LED Preferences** and check which GPIOs your LED
   bus(es) use.
2. Open **Config → Usermod Settings → RaceLink → pins** (or
   `epaper_pins`).
3. Move the conflicting pin to a free GPIO. Save → reboot.

Other common conflicts: button pin, IR pin, DMX pin. The
*Settings → Time & Macros* page typically lists these. Free GPIOs
depend on the SoC variant — see your board's datasheet for the
output-capable pin set.

## Related pages

* [README — building RaceLink WLED firmware](README.md) — flashing
  and build profiles.
* [Operator setup](operator-setup.md) — pairing, recovery, factory
  state.
* [Radio modules — developer guide](radio-modules.md) — why the radio
  chip family is fixed at the build target rather than at runtime,
  and how to extend the firmware to support other chip families.
