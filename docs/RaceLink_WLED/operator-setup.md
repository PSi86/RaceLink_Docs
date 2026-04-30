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

## Pairing with a gateway

A node pairs with the first gateway that broadcasts `OPC_DEVICES`
during a discovery. To pair:

1. Power up the node within radio range of your gateway.
2. From the host's WebUI, click **Discover Devices**, choose
   "Unconfigured" as the assignment group, click **Start**.
3. The node responds with its `IDENTIFY_REPLY` and the gateway's
   MAC is recorded as the node's master MAC.

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

When using offset mode with a *cyclic* WLED effect (Breathe,
Pacifica, anything that renders as a direct function of
`strip.now`), the start-stagger works but every node reaches the
same point of the cycle simultaneously — the phase difference
collapses to zero. The fix is in firmware: a persistent per-device
phase offset on `strip.timebase`, re-asserted after every SYNC.

If you observe this, ensure your node firmware is up to date — the
phase-lock fix is part of the WLED-usermod release stream. See
[`../concepts/opcodes.md`](../concepts/opcodes.md) §"Cyclic-effect phase-lock" for
the deeper background.

For the catalogue of which WLED effects are deterministic (and
therefore safe to use in offset mode) see
[`docs/effects-deterministic.md`](../concepts/deterministic-effects.md).

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
