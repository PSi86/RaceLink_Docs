# Troubleshooting

Operator-side index of common problems and where the answer lives.
Each entry links to the page that has the substantive explanation —
this page is a **navigation aid**, not the source of truth.

## Gateway connection

### The master pill is red and the banner says "Gateway not available"

* `PORT_BUSY` — another process is using the dongle. Close it and
  click *Retry connection*.
  → [`RaceLink_Host/operator-guide.md`](RaceLink_Host/operator-guide.md)
  §"Confirm the gateway is connected".
* `NOT_FOUND` — the dongle is not plugged in or the OS has not
  enumerated it.
* `LINK_LOST` — the dongle was working but disappeared. The host
  auto-retries with backoff.
  → [`RaceLink_Host/operator-guide.md`](RaceLink_Host/operator-guide.md)
  §"When the master pill says ERROR".

### The master pill stays in `UNKNOWN`

The host has not received a state report yet. Click ↻ next to the
pill to send a `GW_CMD_STATE_REQUEST`. Useful after a USB reconnect.
→ [`RaceLink_Host/operator-guide.md`](RaceLink_Host/operator-guide.md) §"Master
pill states".

### Two processes can't share the gateway

Only one process can own the USB-LoRa dongle at a time
(`exclusive=True`). If you try to run RotorHazard + standalone
against the same dongle, the second one fails with `PORT_BUSY`.
→ [`RaceLink_Host/architecture.md`](RaceLink_Host/architecture.md) §"Gateway Ownership".

## Discovery / device list

### "Discovered 0 devices"

* Devices off / out of range / paired to a different gateway.
* Each node is paired to one gateway by MAC at first boot. Use
  *Forget master MAC* on the node to un-pair.
  → [`RaceLink_Host/operator-guide.md`](RaceLink_Host/operator-guide.md) §"Discover
  devices" and § "Forgetting a master MAC un-pairs the device".

### "Bulk set group failed"

The bulk-set sends `OPC_SET_GROUP` to each selected device and waits
for an ACK. Offline devices time out individually; the others
continue. Check the masterbar's task summary for the per-device count.
→ [`RaceLink_Host/operator-guide.md`](RaceLink_Host/operator-guide.md)
§"Common things that go wrong".

## Scenes

### "Run reports OK but nothing happens"

* Targeted group has no capable devices (the editor's cap filter
  prevents this in new scenes; old scenes may not have been edited
  since C5 shipped).
* Targeted devices are offline.
* Targeted devices are still in offset mode and the action carries
  `OFFSET_MODE=0`. The strict gate drops these silently.
  → [`RaceLink_Host/operator-guide.md`](RaceLink_Host/operator-guide.md)
  §"Common things that go wrong" and §6a "Important: offset mode is
  sticky".

### "Scene editor says I have unsaved changes but I just saved"

The dirty check is byte-exact on the canonical scene shape. Even
whitespace in the label counts.
→ [`RaceLink_Host/operator-guide.md`](RaceLink_Host/operator-guide.md)
§"Common things that go wrong".

### "Cost badge says ≈ 50 ms but my scene takes 5 seconds"

The cost badge shows *radio airtime* — how long the LoRa packets
spend in the air. Delays (`Delay` action) and host-side runner
overhead are not included.
→ [`RaceLink_Host/operator-guide.md`](RaceLink_Host/operator-guide.md)
§"Common things that go wrong".

### Cyclic effects (Breathe, Pacifica, …) phase-lock across groups

A *cyclic* effect (one whose render is a direct function of
`strip.now`) used to collapse to zero phase difference in offset
mode. Recent WLED-usermod firmware fixes this via a persistent
per-device phase offset re-asserted after every SYNC — flash the
node. For older firmware, prefer state-machine effects
(*Traffic Light*, *Color Wipe*, *Scan*) when authoring offset scenes.
→ [`concepts/opcodes.md`](concepts/opcodes.md) §"Cyclic-effect phase-lock"
(canonical explanation);
[`concepts/deterministic-effects.md`](concepts/deterministic-effects.md);
[`RaceLink_Host/operator-guide.md`](RaceLink_Host/operator-guide.md) §6a.

## WebUI

### "The whole UI freezes for 20–50 seconds after switching pages a few times in Chrome"

Specifically: switching between *Devices* (`/racelink/`) and
*Scenes* (`/racelink/scenes`) using the in-page links, in Chrome
or another Chromium-based browser. After roughly 5 switches in
quick succession, the next page load — and *every* request to the
same host, including a parallel RotorHazard tab — stalls for tens
of seconds.

This is fixed in current builds by the host's three-layer SSE
connection-lifecycle handling (explicit `pagehide` close,
2 s server-side ping, `Connection: close` on the SSE response).
If you can still reproduce it, you are probably running a build
from before the fix.
→ [`reference/sse-channels.md`](reference/sse-channels.md) §"Connection lifecycle and Chrome HTTP/1.1 slot pool".

Workarounds for older builds: use F5 to navigate (it tears the
SSE socket down hard) or use Firefox (its connection pool
semantics differ and never exhibited the symptom).

## OTA / firmware update

### "HTTP 401 from `/update`"

WLED rejected the firmware POST. Possible causes:

* **Same-network gate.** Most common cause on AP+STA fleets. The
  host POSTs `/settings/sec` automatically on 401 to flip
  `otaSameSubnet=false` and clear any OTA lock. The change persists
  in the device's `cfg.json`.
* **OTA lock with a non-default password.** Override the
  "WLED OTA password" field in the OTA dialog (default `wledota`).
  → [`RaceLink_Host/operator-guide.md`](RaceLink_Host/operator-guide.md)
  §"Common OTA failure modes".

### `"AP '<SSID>': authentication failed"`

Wrong WiFi PSK, **or** the device's hostapd is briefly rate-limiting
after recent failed attempts. Wait ~30 s and retry once before
assuming a configuration mistake.
→ [`RaceLink_Host/operator-guide.md`](RaceLink_Host/operator-guide.md)
§"Common OTA failure modes".

### `"PIN code required"`

The device has `settingsPIN` set in WLED Security. Clear the PIN on
the device or the OTA cannot proceed (the host does not currently
auto-enter the PIN).

### `"Firmware release name mismatch"`

WLED rejected the binary because its `WLED_RELEASE_NAME` differs
from the running firmware's. Tick "Skip firmware-name validation" in
the OTA dialog and retry. Leave the box unchecked once the fleet is
on a consistent firmware.
→ [`RaceLink_Host/developer-guide.md`](RaceLink_Host/developer-guide.md) §"WLED
OTA gate matrix" — Gate 4.

### "What does NOT help: changing the host's IP/netmask"

The same-network gate uses *the device's* `Network.localIP()`, not
the host's. No host-side IP reconfiguration brings the host into the
device's STA subnet. The host-side auto-unlock POST is the fix.
→ [`RaceLink_Host/operator-guide.md`](RaceLink_Host/operator-guide.md);
[`RaceLink_Host/developer-guide.md`](RaceLink_Host/developer-guide.md) §"WLED
OTA gate matrix".

## WLED node operation

### Physical button on WLED node does not respond

The single short-press (colour change) and the press-and-hold
(brightness fade) gestures are gated behind a 60-second
master-quiet timer: while a paired gateway is talking to the
node, both gestures are suppressed so the button cannot interfere
with a live race. Either wait for ≥60 s of radio silence or power
off the gateway. The triple short press (open hotspot) ignores
the gate and always works.
→ [`RaceLink_WLED/operator-setup.md`](RaceLink_WLED/operator-setup.md) §"Physical button"
and §"Common problems".

## Linux first-time setup

### `nmcli` permission errors during OTA

Run the bundled setup helper once as root:

```bash
sudo $(which racelink-setup-nmcli)
```

Then restart RotorHazard or `racelink-standalone`. The
`$(which …)` form is required because `sudo` strips the venv's
`bin/` from `secure_path`.
→ [`RaceLink_Host/standalone-install.md`](RaceLink_Host/standalone-install.md) §"Linux
first-time setup for firmware updates".

## Build / development

### Gateway: build fails because a pin definition is missing

Check the build flags in `platformio.ini`. The source explicitly
requires several radio and OLED pin definitions at compile time.
→ [`RaceLink_Gateway/README.md`](RaceLink_Gateway/README.md) §Troubleshooting.

### WLED node: build fails because the environment name does not exist

Make sure the env name passed to `pio run -e ...` matches the
`[env:...]` section inside the selected profile.
→ [`RaceLink_WLED/README.md`](RaceLink_WLED/README.md) §Troubleshooting.

### WLED node: wrong pin mapping or non-working radio

Check the `RACELINK_PIN_*` definitions and modem selection in the
chosen build profile.
→ [`RaceLink_WLED/README.md`](RaceLink_WLED/README.md) §Troubleshooting.

## Diagnostic logs

* The host's diagnostic log goes either to the RotorHazard log
  (plugin mode) or to stderr (standalone mode).
* Every broad-except path logs the exception type + traceback now
  so the log is genuinely useful.
* For wire-level questions see
  [`reference/wire-protocol.md`](reference/wire-protocol.md).
* For code questions see
  [`RaceLink_Host/developer-guide.md`](RaceLink_Host/developer-guide.md) and
  [`RaceLink_Host/architecture.md`](RaceLink_Host/architecture.md).
