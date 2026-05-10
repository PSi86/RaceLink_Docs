# Radio Modules — Developer Guide

Why the RaceLink WLED firmware fixes the radio chip family at the
**build target** rather than offering it as a runtime selector, and
what it would take to extend support to additional chip variants or
families.

> **Audience.** Firmware contributors evaluating whether to add
> support for a new RadioLib-supported transceiver, or trying to
> understand why a single firmware image only serves one
> radio-chip family. Operator-facing pin configuration lives in
> [`pin-config.md`](pin-config.md).

## Current state

`racelink_wled` supports two transceiver classes today, selected at
compile time via mutually exclusive build flags in the relevant
`platformio_override.ini`:

* `-D RACELINK_SX1262` — used by the HT-CT62 (ESP32-C3) reference
  board.
* `-D RACELINK_LLCC68` — used by the DreamLNK-style boards (RaceLink
  Node v3 S2, v4 S3).

Both `racelink_wled.h` and `racelink_transport_core.h` carry
`#if defined(...)` guards that select the corresponding `radio`
member type and the matching `beginCommon` / `attachDio1` overload.
A firmware image always targets exactly one chip; the wrong build
flashed onto a board with the other chip will fail `radioInit()` at
boot.

## RadioLib class hierarchy

The shape of the RadioLib v7.x API drives the runtime-vs-compile-time
choice:

```
PhysicalLayer (abstract)
├── SX126x          ← shared API: setDio2AsRfSwitch, setRxBoostedGainMode,
│   │                 setDio1Action, opcode-based SPI command set
│   ├── SX1262
│   │   ├── LLCC68  (limits SF range to 7..11)
│   │   └── SX1261  (output power capped at +15 dBm)
│   └── SX1268      (sibling of SX1262 under SX126x; not derived from SX1262)
└── SX127x          ← older generation, INCOMPATIBLE API
    ├── SX1272
    └── SX1278  ←— SX1276
```

References (RadioLib v7.6, currently vendored under `.pio/libdeps/`):

* `LLCC68 : public SX1262` — `RadioLib/src/modules/LLCC68/LLCC68.h:19`
* `SX1261 : public SX1262` — `RadioLib/src/modules/SX126x/SX1261.h:22`
* `SX1268 : public SX126x` — `RadioLib/src/modules/SX126x/SX1268.h:21`
* `SX1262 : public SX126x` — `RadioLib/src/modules/SX126x/SX1262.h:22`
* `SX1272 : public SX127x` — `RadioLib/src/modules/SX127x/SX1272.h:95`
* `SX126x : public PhysicalLayer` — `RadioLib/src/modules/SX126x/SX126x.h:37`
* `SX127x : public PhysicalLayer` — `RadioLib/src/modules/SX127x/SX127x.h:583`

## Why intra-family runtime selection (SX1262 / LLCC68 / SX1261) was deliberately not added

LLCC68 and SX1261 both inherit from `SX1262`, so a single `SX1262*`
member with a runtime-chosen concrete instance would compile and
work via virtual dispatch. The reason it is **not** wired up:

* The only practical difference between these three is which **PHY
  parameters** the chip will accept (LLCC68 caps SF at 7..11; SX1261
  caps TX power at +15 dBm). Selecting the chip type at runtime
  without also exposing the PHY parameters at runtime would just
  rename the same compile-time choice.
* PHY parameters (`RACELINK_FREQ_HZ`, `RACELINK_SF`, `RACELINK_BW_KHZ`,
  `RACELINK_CR`, `RACELINK_SYNC_WORD`, `RACELINK_TX_POWER`,
  `RACELINK_PREAMBLE`) are intentionally compile-time. A heterogeneous
  fleet of nodes with mismatched PHY settings would silently fail to
  communicate, with diagnostics that look like RF noise — locking
  these at the build level is a deliberate guard rail.
* As a consequence, chip-variant choice is also kept compile-time. If
  a board ever ships with SX1261, it gets its own
  `[env:...]` profile rather than a runtime toggle.
* One firmware image per `(MCU, radio module)` combination is the
  project convention.

## What SX126x and SX127x do not share

The two RadioLib chip families derive from the abstract
`PhysicalLayer` base, but several methods that `racelink_transport_core.h::beginCommon`
and `attachDio1` rely on are SX126x-only:

* `setDio2AsRfSwitch()` — SX126x only. SX127x uses different RF-switch
  control (TX/RX-mode register bits or external GPIO).
* `setRxBoostedGainMode()` — SX126x only.
* **LoRa-mode RX-Done / TX-Done IRQ source** is **DIO1 on SX126x**,
  but **DIO0 on SX127x**. The pin field in the runtime config would
  have to rename from `pinDio1` to `pinDio0`, and the ISR-attach call
  would change from `setDio1Action(...)` to `setDio0Action(...)`.
* SPI command structure is opcode-based on SX126x, register-based on
  SX127x. RadioLib hides this internally, but the underlying timings,
  error-code values and `Module()` constructor expectations differ.

The common base `PhysicalLayer` is too abstract to bridge these
differences with a single helper — calls like `setDio2AsRfSwitch` are
not declared on `PhysicalLayer`, and any uniform abstraction would
end up branching on family at runtime anyway.

## What it would take to add SX127x support (forward-looking)

If a future board uses SX1272, SX1276, or SX1278, the cleanest
extension is **a parallel build path**, not a runtime selector:

* Add a new compile-time flag, e.g.
  `-D RACELINK_FAMILY_SX127X` (parallel to the implicit SX126x default
  the existing flags imply).
* Add a `beginCommon(SX127x&, Core&, const PhyCfg&)` overload in
  `racelink_transport_core.h` — no `setDio2AsRfSwitch`, no
  `setRxBoostedGainMode`, otherwise structurally similar to the
  current SX126x overload.
* Add an `attachDio0(SX127x&, Core&)` (or rename the helper to be
  family-neutral) that calls `setDio0Action(onDio1ISR_trampoline)` —
  the trampoline name can stay; only the chip-side hookup changes.
* Add a runtime pin field `pinDio0` in `UsermodRaceLink` (replacing
  `pinDio1` under the SX127x flag) and update the operator pin-config
  table to match.
* Switch the `radio` member type to `SX127x*` under the SX127x flag.
* Build profiles using SX127x get their own `[env:...]` entries with
  `-D RACELINK_FAMILY_SX127X` and the appropriate
  `-D RACELINK_SX1272` / `-D RACELINK_SX1276` / `-D RACELINK_SX1278`
  selector inside the family.

A single firmware image cannot serve both families — the call sites,
pin fields and config schema diverge too much. Maintain two release
artifacts.

## What it would take to add SX1268 (within the SX126x family)

SX1268 is a sibling of SX1262 under `SX126x`, **not** derived from
SX1262. Adding it requires:

* The `radio` pointer type changes from `SX1262*` (or `LLCC68*`) to
  `SX126x*`, because SX1268 is not in the SX1262 inheritance chain.
* `SX126x::begin()` is **not** declared at the base class — chip-
  specific defaults live on the derivatives. Either add a manual
  dispatch helper that branches on `radioModuleType` and calls the
  correct derived `begin()`, or keep one chip per build target.
* Cleaner: a new `-D RACELINK_SX1268` flag and a new build profile,
  matching the existing SX1262/LLCC68 split.

The same `(MCU, radio module)` per-image rule applies.

## Where the radio code lives

* [`racelink_wled.h`](https://github.com/PSi86/RaceLink_WLED/blob/main/racelink_wled.h)
  — `#if defined(RACELINK_SX1262) / RACELINK_LLCC68` selects the
  `radio` member type. Pin defaults (`RACELINK_PIN_*`) live near the
  top of the file.
* [`racelink_wled.cpp`](https://github.com/PSi86/RaceLink_WLED/blob/main/racelink_wled.cpp)
  — `radioInit()` instantiates the correct concrete class as a
  function-local static, then calls `beginCommon()` and
  `attachDio1()`. PinManager allocation happens here too.
* [`racelink_transport_core.h`](https://github.com/PSi86/RaceLink_WLED/blob/main/racelink_transport_core.h)
  — the two `beginCommon` and two `attachDio1` overloads (one per
  chip type) are guarded by the same `#if defined(...)` chain. Both
  bodies are identical today — they only call methods that exist on
  the SX126x base — but the overloads stay separated so the SX127x
  family extension above slots in cleanly.

## Related pages

* [Pin configuration — operator guide](pin-config.md) — runtime pin
  overrides via the WLED settings UI.
* [README — build profiles](README.md) — how the per-target build
  profiles select MCU and radio chip.
