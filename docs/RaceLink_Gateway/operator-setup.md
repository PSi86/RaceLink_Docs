# Gateway Operator Setup

How to connect, identify and operate a flashed RaceLink Gateway. For
firmware build / flash instructions see [`README.md`](README.md).

> **Audience.** Operators who already have a flashed gateway and want
> to use it. If you need to flash one first, start with
> [`README.md`](README.md).

## What you need

* A flashed RaceLink Gateway dongle (`DEV_TYPE_STR="RaceLink_Gateway_v4"`
  for the current build; older device-type strings work as long as
  the wire-protocol version matches).
* A USB cable connecting the gateway to the host machine.
* A running RaceLink host — either standalone
  (`racelink-standalone`) or RotorHazard with the
  [`RaceLink_RH_Plugin`](../RaceLink_RH_Plugin/README.md) loaded.

## First-time connection

1. **Plug the dongle into the host before starting the host.**
   The host auto-discovers the gateway on startup. If you plug it in
   afterwards, the host's reconnect logic finds it within a few
   seconds — but the master pill briefly shows `LINK_LOST` first.
2. **Identify the serial port.**
   * Linux: `/dev/ttyUSB0` or `/dev/ttyACM0` (run
     `ls /dev/ttyUSB* /dev/ttyACM*` to confirm).
   * Windows: a `COM` port such as `COM3` or `COM4`. Confirm in
     Device Manager.
   The host uses `serial.SerialException`'s exclusive-open mode, so
   no other process can hold the port.
3. **Confirm the master pill goes IDLE.**
   The pill in the WebUI header should turn cyan (`IDLE`) within a
   second of the page load. If it stays in `UNKNOWN`, click the **↻**
   refresh button next to it.

See [`../RaceLink_Host/operator-guide.md`](../RaceLink_Host/operator-guide.md)
§"Confirm the gateway is connected" for the full state-by-state
operator playbook.

## OLED indicator

The gateway has a small SSD1306 OLED. The current firmware shows:

* TX / RX counters since power-on.
* Recent packet debug output (transient).

The OLED is informational; the master pill in the WebUI is the
source of truth for gateway state.

## Radio defaults

The gateway operates with the following defaults (configured at
build time in `platformio.ini`; see [`README.md`](README.md) for
the full list):

| Parameter | Value |
|---|---|
| Frequency | `867 700 000 Hz` |
| Bandwidth | `125 kHz` |
| Spreading factor | `SF7` |
| Coding rate | `4/5` |
| Preamble | `8` |
| Sync word | `0x12` |

These values must match the WLED nodes' build profile; see
[`../RaceLink_WLED/README.md`](../RaceLink_WLED/README.md) §"Build profile notes".

> **Regional note.** The default frequency is in the EU 868 MHz
> ISM band. Operators outside the EU must adjust the frequency in
> the gateway's `platformio.ini` and re-flash; the WLED nodes
> need a matching change in their build profile. There is no
> runtime way to change the radio band.

## Pairing nodes to a gateway

A WLED node is paired to one gateway by MAC at first boot. To pair
a freshly-flashed node to your gateway, simply run **Discover
Devices** from the host's WebUI: the node listens for any
broadcast and pairs with whichever gateway sent the discovery.

To migrate a node between gateways, use the WebUI's **Forget master
MAC** option (in the Node Config dropdown) on the node, then
re-discover from the new gateway. See
[`../RaceLink_Host/operator-guide.md`](../RaceLink_Host/operator-guide.md)
§"Forgetting a master MAC un-pairs the device".

## Gateway ownership rules

> **Critical:** only **one** process can own the gateway USB port at a
> time. The host opens it with `exclusive=True`.

* In **standalone mode**, the host owns the gateway for the lifetime
  of the Flask app.
* In **RotorHazard plugin mode**, the plugin owns the gateway —
  RotorHazard itself never opens the dongle.
* **Never run both simultaneously** against the same dongle. The
  second process fails with `serial.SerialException` from the
  exclusive lock; the host UI surfaces this as a `PORT_BUSY` banner.

For the deeper rationale see
[`../RaceLink_Host/architecture.md`](../RaceLink_Host/architecture.md) §"Gateway
Ownership".

## Common problems

* **The OLED stays blank.** Verify the OLED pin definitions and
  display wiring. The OLED is non-essential — the gateway operates
  without it — but its absence often signals a power or wiring
  issue.
* **Master pill flips between IDLE and ERROR rapidly.** USB
  hiccup. The pill returns to IDLE within seconds; it the
  oscillation continues, swap the USB cable or try a different
  USB port (a powered hub helps on some hosts).
* **`PORT_BUSY` banner persists after closing the other process.**
  Some operating systems take a few seconds to release the device.
  Wait, then click *Retry connection*.

For the broader operator-side troubleshooting index see
[`../troubleshooting.md`](../troubleshooting.md).
