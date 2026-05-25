# Region & Channels — the shipped channel tables

RaceLink's host carries a small per-region lookup table of named
channel slots. The multi-network UI binds against this table rather
than against raw `P_RfConfig` values; the operator picks a channel
by name, and the host resolves the seven wire-format fields at
apply-time.

The table is shipped as code constants (not operator-editable) so
that every entry is pre-audited for compliance, has a stable
name-to-frequency mapping, and clears the cross-channel separation
validator out of the box.

For the operator-facing flows that consume this table (Network
Manager dialog, bind wizard, RF migration, Channel Scan), see
[`../RaceLink_Host/multi-network.md`](../RaceLink_Host/multi-network.md).
For the wire format the table maps to, see
[`../reference/wire-protocol.md`](../reference/wire-protocol.md)
§`P_RfConfig`.

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
channel_id)` lookup.

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
like noise to each other's receiver. The 500 kHz threshold leaves
headroom for transient drift on 125 kHz channels. The validator
lives in `racelink/domain/rf_policy.py::validate_networks_separation`
and is exercised by the channel-edit save path as well as the
bind / migrate flows in
[`../RaceLink_Host/multi-network.md`](../RaceLink_Host/multi-network.md).

## Compliance disclaimer

The shipped channels are picked to fit common operator deployments
in EU and US ISM bands and pass a desk review against the relevant
ETSI / FCC documents. **Operators are responsible for verifying
their own deployment is legal** — duty cycles, power limits, and
antenna conventions vary by country, local frequency coordination,
and the actual deployment context (indoor vs outdoor, fixed vs
mobile). RaceLink does not enforce duty-cycle limits in firmware;
the operator stays within the ceiling by configuring scenes that
don't saturate the airtime budget.
