# Region & Channels — how the host pre-defines RF settings

RaceLink's wire layer carries a 12-byte `P_RfConfig` block whenever
the operator changes the gateway's NVS settings or pushes a new
configuration to a node. Five fields define what the modem actually
does (`freq_hz`, `bw_khz_x10`, `sf`, `cr_den`, `sync_word`) plus two
operator-tuning knobs (`tx_power_dbm`, `preamble`). Picking those
seven values by hand for every network is both error-prone and a
**legal-compliance topic** — the ISM band and per-region duty-cycle
ceilings differ. So the host ships a small **lookup table** of named
channel slots per region, and the multi-network UI works against the
table rather than against raw values.

For the wire format the table maps to, see
[`reference/wire-protocol.md`](../reference/wire-protocol.md). For
the operator workflow that uses the table, see
[`RaceLink_Host/multi-network.md`](../RaceLink_Host/multi-network.md).

## Why a fixed table

Three reasons the table is shipped as code constants (not
operator-editable):

* **Compliance.** EU868 and US915 differ in legal sub-bands, duty
  cycles, and effective radiated power. Hard-coding the "OK"
  combinations means the WebUI's channel dropdown only offers
  values the maintainer audited against the relevant regulations.
* **Stable name → frequency mapping.** Operators talk about
  "Channel 2" in the pit lane, not about "867.7 MHz SF7 BW125 SW
  0x12". The id ↔ name pair is the operator-visible handle the
  Network Manager dialog binds to; the underlying `P_RfConfig` is
  resolved at apply-time.
* **Conflict detection.** The frequency-separation validator (see
  [`reference/broadcast-ruleset.md`](../reference/broadcast-ruleset.md))
  checks that two networks the host is asked to drive
  simultaneously don't overlap. Because every channel is
  pre-validated, the operator can pick any two from the table and
  trust that they won't collide — the validator only kicks in for
  Advanced-mode custom configs.

Stage-3 Part A introduces the table and the validator together —
the test suite (`tests/test_rf_channels.py`,
`tests/test_rf_policy_separation.py` in `RaceLink_Host/`) pins both
the shape and the cross-channel separation rule.

## Table shape

Per region, the host ships at most **5 channels**. Each entry
carries:

| Field | Type | Purpose |
|---|---|---|
| `id` | `int` (1..5) | Stable operator-visible id, 1-based dense |
| `name` | `str` | Short label ("Default", "Alt-1", "High") |
| `freq_hz` | `uint32` | Carrier frequency in Hz |
| `bw_khz_x10` | `uint16` | Bandwidth × 10 (1250 = 125.0 kHz) |
| `sf` | `uint8` | Spreading factor (5..12) |
| `cr_den` | `uint8` | Coding rate denominator (5..8 ⇒ 4/CR) |
| `sync_word` | `uint8` | LoRa SyncWord (PHY-level discriminator) |
| `tx_power_dbm` | `int8` | TX power (-9..22, signed) |
| `preamble` | `uint16` | Preamble symbols |

The `id` is what `RL_Network.channel_id` stores; the seven
wire-format fields below it are what flows into `OPC_RF_CONFIG`
/ `GW_CMD_SET_RF_CONFIG` after a `channel_rf_config(region,
channel_id)` lookup. The Network Manager dialog's "Custom" option
lets the operator clear the `channel_id` and keep a hand-typed
`rf_config` — the host doesn't re-resolve it from the table on
boot, so a future channel-table change does not silently rewrite
the network.

### EU868 — shipped slots

EU868 sits in the 863-870 MHz ISM band. The shipped table picks
five widely-separated 125-kHz / SF7 anchors that span the most-used
sub-bands so the operator has visible spread without needing
custom configs.

| Id | Name | Frequency | SF | BW | SyncWord | TX | Sub-band note |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | Default | 867.700 MHz | 7 | 125 kHz | `0x12` | 14 dBm | The build-flag default. Devices ship on this; matches the pre-Stage-3 deployment. |
| 2 | Alt-1 | 868.200 MHz | 7 | 125 kHz | `0x12` | 14 dBm | 1 % duty cycle band. |
| 3 | Alt-2 | 868.700 MHz | 7 | 125 kHz | `0x12` | 14 dBm | 0.1 % duty cycle band. |
| 4 | Alt-3 | 869.200 MHz | 7 | 125 kHz | `0x12` | 14 dBm | 0.1 % duty cycle band. |
| 5 | High | 869.700 MHz | 7 | 125 kHz | `0x12` | 14 dBm | 1 % duty cycle band. |

### US915 — shipped slots

US915 is the 902-928 MHz band. The five slots sit inside the
902.3-914.9 MHz LoRaWAN uplink range; ≥500 kHz separation between
every same-SyncWord pair.

| Id | Name | Frequency | SF | BW | SyncWord | TX |
|---:|---|---:|---:|---:|---:|---:|
| 1 | Default | 904.300 MHz | 7 | 125 kHz | `0x12` | 14 dBm |
| 2 | Alt-1 | 905.300 MHz | 7 | 125 kHz | `0x12` | 14 dBm |
| 3 | Alt-2 | 906.300 MHz | 7 | 125 kHz | `0x12` | 14 dBm |
| 4 | Alt-3 | 907.300 MHz | 7 | 125 kHz | `0x12` | 14 dBm |
| 5 | High | 908.300 MHz | 7 | 125 kHz | `0x12` | 14 dBm |

## Separation rule

Two networks the host drives simultaneously must satisfy at least
one of:

* `abs(freq_a - freq_b) >= 500 kHz`, **or**
* `sync_word_a != sync_word_b`.

The SyncWord short-circuit is the LoRa PHY's native discriminator;
two transmitters on the same frequency but different SyncWords look
like noise to each other's receiver. The 500 kHz threshold is
deliberately conservative for 125 kHz channels — a real BW125
spread spectrum signal needs ~250 kHz of band, and the validator's
floor leaves headroom for transient drift.

The validator lives in
`RaceLink_Host/racelink/domain/rf_policy.py::validate_networks_separation`.
It returns a structured conflict list rather than raising so the
WebUI can render a "these networks would collide" preview before
the operator commits to a save.

## Custom-mode (Advanced)

For the operator who wants to type raw values — typically a
bench-test on an unusual frequency, or a region the shipped table
doesn't yet cover — the Network Manager dialog's channel dropdown
includes a "— Custom / unchanged —" option. With it:

* The network keeps its current `rf_config` untouched (or starts
  empty, depending on whether one is already set).
* The operator can edit the seven fields directly via the same
  `PUT /api/networks/{id}` endpoint (the body accepts a literal
  `rf_config` dict).
* The separation validator still runs — a custom config that would
  collide with another live network is rejected with HTTP 400.

Custom-mode is intentionally not exposed in the channel dropdown's
fast-pick list; it's a deliberate "I know what I'm doing"
escape-hatch.

## Compliance disclaimer

The shipped channels are picked to fit common
operator deployments in EU and US ISM bands and pass a desk
review against the relevant ETSI / FCC documents. **Operators are
responsible for verifying their own deployment is legal** — duty
cycles, power limits and antenna conventions vary by country,
local frequency coordination, and the actual deployment context
(indoor vs outdoor, fixed vs mobile). RaceLink does not enforce
duty-cycle limits in firmware; the operator stays within the
ceiling by configuring scenes that don't saturate the airtime
budget.
