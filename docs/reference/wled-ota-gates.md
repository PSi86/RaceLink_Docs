# WLED OTA gate matrix

WLED's HTTP `/update` handler runs four gates before accepting a
firmware POST: three host-recoverable HTTP-401 gates (same-subnet,
settings-PIN, OTA-lock) plus one HTTP-500 gate (firmware
release-name match). Knowing each one is the quickest path through
any "why did the OTA fail?" debugging session. References point at
the upstream WLED source layout (`wled00/wled_server.cpp` etc.); in
the RaceLink WLED fork the same files live alongside the
`racelink_wled` usermod.

The operator-facing failure-mode catalog is in
[`../RaceLink_Host/operator-guide.md`](../RaceLink_Host/operator-guide.md)
§"Firmware updates" / §"Common OTA failure modes"; the live wire of
the workflow lives in `racelink/services/ota_workflow_service.py`
and `racelink/services/ota_service.py`.

## The four gates

```
POST /update
  │
  ├─ Gate 1: same-subnet  (wled_server.cpp:529, returns 401)
  │    if otaSameSubnet=true:
  │      reject if !inSameSubnet(client) AND !strlen(settingsPIN)
  │    else:
  │      reject if !inLocalSubnet(client)
  │
  ├─ Gate 2: settings PIN (wled_server.cpp:535, returns 401)
  │    reject if !correctPIN
  │
  ├─ Gate 3: OTA lock     (wled_server.cpp:540, returns 401)
  │    reject if otaLock
  │
  └─ Gate 4: release-name (ota_update.cpp:139-143 + wled_metadata.cpp:153-157,
                           returns 500 with body "Firmware release name
                           mismatch: current='X', uploaded='Y'.")
       reject if uploaded firmware's WLED_RELEASE_NAME doesn't match the
       running build's, UNLESS the POST carries `skipValidation=1` in
       the multipart body.
```

Gates 1-3 produce HTTP **401** and can be auto-recovered host-side
via `OTAService._wled_attempt_unlock` (POST `/settings/sec` with
`OP=<otaPass>`). Gate 4 produces HTTP **500** and requires the host
to set `skipValidation=1` in the multipart body explicitly —
operator ticks the "Skip firmware-name validation" checkbox in the
OTA dialog. The checkbox is off by default because flashing a
binary with the wrong chip variant can brick a device; the gate
exists for a reason.

The trap that bites a fleet OTA on AP+STA-mode nodes is Gate 1.
`inSameSubnet` masks the client's IP against the device's
`Network.localIP() & subnetMask()`. In AP+STA mode `Network.localIP()`
returns the **STA** address, not `4.3.2.1`, so an AP-side host with
a perfectly valid `4.3.2.x` DHCP lease still fails the check.
`inLocalSubnet` (`wled_server.cpp:66-72`) is broader — it explicitly
accepts `4.3.2.0/24` when `apActive` — but it's only consulted when
`otaSameSubnet=false`.

## Build flags that affect the gates

The exhaustive list, derived from the upstream WLED source files
`wled00/wled.h` and `wled00/const.h`:

| Variable | Default | Build flag | Effect on the gates |
|---|---|---|---|
| `apPass` | `DEFAULT_AP_PASS = "wled1234"` | `-D WLED_AP_PASS="..."` (requires `WLED_AP_SSID` too — `wled.h:214` has a hard `#error` if only one is set) | WiFi association layer; doesn't touch the OTA gate. |
| `otaPass` | `DEFAULT_OTA_PASS = "wledota"` (`const.h:41`) | `-D WLED_OTA_PASS="..."` | Sets the password the host POSTs to `/settings/sec` to clear `otaLock`. **Defining the macro also flips `otaLock=true`** by default (`wled.h:573-577`). |
| `otaLock` | `true` if `WLED_OTA_PASS` defined, else `false` | implicit | Gate 3. |
| `otaSameSubnet` | **`true`** unconditionally (`wled.h:584` — no `#ifdef`/`#else`) | **NONE** — there is no `WLED_OTA_SAME_SUBNET` define | Gate 1. The compiled default is hardcoded; only runtime flips it. |
| `settingsPIN` | `WLED_PIN` macro → fallback `""` (`wled.h:227-229`) | `-D WLED_PIN="1234"` (exactly 4 chars) | Bypasses Gate 1 via `!strlen(settingsPIN)` short-circuit. Sets `correctPIN=false` at boot, so Gate 2 then blocks until the PIN is entered. |

**Important non-obvious points:**

1. **`WLED_OTA_PASS` does NOT bypass same-subnet.** Gate 3 (OTA
   lock) and Gate 1 (same-subnet) are independent. The OTA
   password only clears Gate 3. A tempting reading of WLED's docs
   makes this ambiguous; the line-pinned source is unambiguous.
2. **There is no build flag for `otaSameSubnet`.** The only
   same-subnet bypass at build time is `WLED_PIN`, and that comes
   with the Gate 2 PIN-entry tax.

## Five firmware-side options to ship same-subnet=false

Ranked by friction:

### Option 1 — `racelink_wled` usermod override (recommended)

In the usermod's `setup()`:

```cpp
// usermods/racelink_wled/racelink_wled.cpp
otaSameSubnet = false;  // RaceLink: AP+STA means inSameSubnet
                        // doesn't recognise AP-side clients.
```

Runs **after** `deserializeConfigFromFS()`, so it overrides whatever
`cfg.json` carries. Side-effect-free. Doesn't touch WLED core. One
line, contained in the usermod's git history.

### Option 2 — patch `wled.h:584`

```c
WLED_GLOBAL bool otaSameSubnet  _INIT(false);  // was _INIT(true)
```

Equivalent to Option 1 but lives in WLED core. Pick this if your
fork policy prefers core-default changes over usermod overrides.

### Option 3 — `WLED_PIN` build flag

`-D WLED_PIN="1234"` in `platformio_override.ini`. Bypasses Gate 1
via the `!strlen(settingsPIN)` short-circuit, **but** Gate 2 then
fires until the host enters the PIN. Host implementation: a single
POST to `/settings/sec` with `PIN=1234` form-encoded, then the OTA.
Side effect: the PIN gates ALL settings pages
(`wled_server.cpp:759`), not just `/update`, so any browser pulling
up `/settings` on a device gets prompted.

The PIN entry flow itself is straightforward (single POST handled
at `set.cpp:10-13` → `checkSettingsPIN` at `util.cpp:454-460`); the
PIN-everywhere side effect is the cost.

### Option 4 — bake `cfg.json` into LittleFS

Ship `{"ota":{"same-subnet":false}}` in the device's filesystem,
either via a `wled00/data/cfg.json` build-time addition or a
first-boot writer in the `racelink_wled` usermod. Less robust than
Options 1 / 2 because a `/settings/sec` save by the operator can
silently flip `otaSameSubnet=true` again (the form's `SU` checkbox
is checked-by-default in WLED's UI).

### Option 5 — host-side auto-unlock (already implemented)

[`OTAService._wled_attempt_unlock`](../racelink/services/ota_service.py)
on a 401 from `/update`: POSTs `/settings/sec` with `OP=<otaPass>`.
Two effects via WLED's settings handler:

* `OP=<password>` → if `otaLock=true` AND password matches, clears
  `otaLock` ([set.cpp:651](../../WLED%20LoRa/WLED/wled00/set.cpp#L651)).
* `SU` argument absent → `otaSameSubnet = false` unconditionally
  ([set.cpp:669](../../WLED%20LoRa/WLED/wled00/set.cpp#L669)).

The second effect is what fixes Gate 1, and it doesn't depend on
the password matching. For a default-config device (`otaLock=false`,
no PIN) the auto-unlock POST always succeeds and persistently sets
`otaSameSubnet=false` in the device's `cfg.json`. **B is therefore
a real fix, not just a runtime mitigation** — every device that
401s gets auto-fixed on its first OTA, future OTAs skip the
auto-unlock round-trip.

## Recommendation

Ship Option 1 (usermod override) in new firmware images so
factory-fresh nodes are OTA-friendly without the auto-unlock
round-trip. Keep Option 5 (host-side auto-unlock) in place as the
safety net — it covers existing devices flashed before Option 1
was in place, plus any device whose `cfg.json` somehow ended up
with `otaSameSubnet=true` (factory reset, manual re-enable, etc.).
