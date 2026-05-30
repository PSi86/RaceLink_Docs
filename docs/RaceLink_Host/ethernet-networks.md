# Ethernet networks (Draft)

!!! warning "Draft — unreleased, hardware bring-up pending"
    Ethernet networks are an **experimental proof-of-concept**. The
    host-side transport (now carrying the **full opcode set**, not just
    discovery/status/preset) and the **device firmware**
    (`RaceLink_Ethernet`, an Ethernet variant of the RaceLink_WLED
    usermod) are both implemented and **compile-verified**, but the
    firmware has **not yet been validated on real W5500 hardware**, and
    the feature is **not part of a released build**. Treat everything
    below as a preview of the intended operator experience. Remove this
    banner and fold the matching [changelog](../changelog.md) block into a
    dated release once the on-device bring-up is signed off.

RaceLink networks come in two **kinds**. The default kind is **RF**:
a LoRa channel bound to a USB gateway (covered in the
[Multi-Network operator guide](multi-network.md)). The second kind is
**Ethernet**: an IP/LAN network where the host's own network interface
is the transport — there is no separate gateway box, and devices are
reached over UDP instead of LoRa. The two kinds are parallel options,
not successive ones — RF is not being replaced.

Everything the rest of RaceLink already does — groups, the device
table, per-network isolation, scene targeting — works the same for an
Ethernet network, because those layers only ever cared about a device's
`network_id`, never about *how* it is reached.

## How an Ethernet network differs from an RF network

| | RF network | Ethernet network |
|---|---|---|
| Transport | USB gateway → LoRa radio | Host NIC → UDP/IP |
| "Gateway" | a separate hardware unit (its MAC binds the network) | the host interface itself (no gateway MAC) |
| Discovery | `OPC_DEVICES` broadcast over LoRa | `OPC_DEVICES` broadcast over UDP on the LAN |
| RF settings | region + channel + `rf_config` | not applicable — UDP port / bind settings instead |
| Master pill | TX / IDLE / RX_WINDOW from the radio state machine | constant **IDLE** (the link has no LoRa state machine) |
| Bind wizard | yes (channel conflict resolution) | not applicable — created directly |

The same RaceLink wire opcodes travel over both: an Ethernet device
speaks the **full opcode set** — discovery/status/preset plus
`OPC_CONTROL`, `OPC_CONFIG` / `OPC_GET_CONFIG`, `OPC_SYNC`, `OPC_OFFSET`,
`OPC_INDICATE`, `OPC_SET_GROUP` and streaming — with the same `groupId` /
broadcast semantics and the same MAC-based addressing, just framed in UDP
datagrams instead of LoRa packets. (The LoRa-only `OPC_RF_CONFIG` PHY
tuning has no Ethernet meaning and is rejected.)

## Adding an Ethernet network

1. Open the **Network Manager** (host-settings menu → *Open Network
   Manager*).
2. Click **+ Add Ethernet network**.
3. Give it a name (e.g. *Wired*) and set the **device UDP port** the
   nodes listen on (default `5078`). The advanced section exposes the
   host reply port, bind host, and broadcast host if you need them.
4. Click **Create network**. The Ethernet transport binds immediately —
   no gateway rediscover needed — and the network appears as a ready
   gateway pill in the master bar (green, **IDLE**).

RF networks are still created the other way around — plug in a gateway
and use the [bind wizard](multi-network.md#conflict-resolution). Only
Ethernet networks are created from the Network Manager.

!!! note "API equivalent"
    The button posts to `POST /api/networks` with
    `{"name": "...", "kind": "ethernet", "node_port": 5078}`. RF
    networks cannot be created through this endpoint (they need a probed
    `rf_config`); it rejects any `kind` other than `ethernet`.

## How it presents in the UI

* **Master bar pill.** The Ethernet network shows a per-network pill
  exactly like a gateway, sitting at **IDLE** (green) once attached.
  The ↻ refresh leaves it at IDLE — there is no LoRa state to poll.
* **Network badge.** Wherever a network badge appears (device-view
  header, sidebar group rows, the Network Manager list) the badge
  carries a small **kind icon** — a radio glyph for RF, a network
  glyph for Ethernet — so the two kinds are distinguishable at a
  glance.
* **Network Manager editor.** Selecting an Ethernet network shows its
  name (editable) and a read-only transport summary (UDP ports, bind /
  broadcast host) in place of the RF region / channel / RF-preview
  panels.

## Isolation between kinds

The existing [network-boundary enforcement](multi-network.md#boundary-enforcement)
already prevents mixing devices from different networks in one group —
it compares `network_id`, so an Ethernet device simply cannot join an
RF group. On top of that, **migrating a group or device across network
*kinds* (RF ↔ Ethernet) is rejected** with HTTP 400
`network_kind_mismatch`: the two transports are physically different, so
there is nothing to migrate.

## Device firmware (RaceLink_Ethernet)

The Ethernet node firmware is **not a separate project** — it is the
existing **RaceLink_WLED usermod** built with `-D RACELINK_ETH`, which
swaps the LoRa/RadioLib transport for a UDP/W5500 backend behind the same
internal API. Every RaceLink feature (groups, presets, control, sync,
indicators, headless, OTA, boot colour) behaves identically; only the
medium changes.

* **Board.** ESP32-S3 + a Wiznet **W5500** Ethernet module over SPI
  (e.g. Waveshare ESP32-S3-ETH). Build target `RaceLink_Node_v5_s3_eth`,
  device type **13** (`NODE_WLED_REV5`).
* **W5500 driver.** A self-contained SPI/UDP driver ships in the usermod
  (`racelink_w5500_udp.h`) — no external Ethernet library, because the
  pinned WLED core (Tasmota Arduino-ESP32 2.0.18) has no usable W5500
  path. Default SPI pins: MISO 12, MOSI 11, SCLK 13, CS 14, RST 9, INT 10.
* **Addressing.** The node listens for UDP on port **5078** and replies
  to the host on **5079** (learned from the inbound datagram's source).
  Its identity is the EFUSE MAC last-3, exactly like a LoRa node.
* **IP config.** **DHCP by default** (non-blocking — the node keeps
  serving WLED while it acquires a lease) with a build-time **static-IP
  fallback**; set `-D RACELINK_ETH_DHCP=0` to force static.

The firmware reuses `racelink_proto.h` unchanged, so the wire opcodes are
identical to RF — there is no Ethernet-specific protocol version. The
WLED web UI shows the Ethernet link/IP and W5500 pin map in place of the
LoRa radio-status and RF-config fields.

## Testing without hardware (mock node)

The host ships a stdlib-only UDP **mock node** for end-to-end testing on
a LAN or loopback without flashing a device — and it stays the
byte-level contract reference for the firmware:

```bash
python scripts/mock_ethernet_node.py --mac AABBCCDDEE01 --group 1 --node-port 5078
```

It answers discovery with `IDENTIFY_REPLY`, reports telemetry on
`OPC_STATUS`, and applies `OPC_PRESET`. Run several instances with
different `--mac` / `--node-port` to emulate a small fleet. With the
mock node running, adding the matching Ethernet network and running
discovery finds it as a device; status polling shows its telemetry; and
a preset is applied.

## Current scope and limitations (PoC)

* **Hardware bring-up pending.** The `RaceLink_Ethernet` firmware is
  implemented and compile-verified but has **not** yet been run on real
  W5500 hardware — the DHCP lease, discovery → control → sync against a
  live host, broadcast RX and reset timing still need an on-device pass.
* **Full opcode parity (host + firmware).** Control, config / get-config,
  sync, offset, indicate, set-group and streaming now travel over UDP in
  addition to discovery/status/preset: the firmware's `handlePacket` is
  transport-agnostic and the host's `EthernetTransport` sends the full
  set. (The **mock node** still implements only the discovery/status/
  preset/set-group subset.)
* **No runtime Ethernet config.** UDP ports, DHCP-vs-static and the W5500
  SPI pins are compile-time build flags (DHCP on by default); a runtime
  "ETH config" opcode pair — the Ethernet equivalent of `OPC_RF_CONFIG` —
  is deferred.
* **One Ethernet network per host interface.** Multiple logical
  Ethernet networks on the same NIC (VLAN / multicast group) are a
  later option; the routing model already allows for it.
* **No time sync.** LoRa `arm_on_sync` coordination relies on
  overlapping airtime; the equivalent for Ethernet (NTP / PTP /
  broadcast latency) is out of scope for the PoC.

See the [Multi-Network operator guide](multi-network.md) for the RF
side, and the [glossary](../glossary.md) for the **Network kind** and
**Ethernet network** terms.
