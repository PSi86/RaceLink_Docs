# RaceLink Wire Protocol Reference

The single source of truth for the wire format is
[`racelink_proto.h`](../racelink_proto.h) — that file is duplicated
byte-identically in the Gateway and WLED firmware repos and pinned by
`tests/test_proto_header_drift.py`. This document is the human-friendly
reading of the same content, oriented at:

* engineers reading a wire trace and trying to identify what they see;
* contributors adding a new opcode (cross-reference with
  [`docs/DEVELOPER_GUIDE.md`](../RaceLink_Host/developer-guide.md));
* anyone debugging a host ↔ gateway ↔ node interaction.

If this document and the header disagree, the **header wins**. File a
bug.

## Layers

```
+------------------+
|  Host (Python)   |  racelink/services/* + racelink/transport/*
+------------------+
        | USB CDC, 921600 baud
+------------------+
|     Gateway      |  ESP32 + SX1262
+------------------+
        | LoRa SX1262, SF7/250 kHz/CR4:5 default
+------------------+
|   WLED node(s)   |
+------------------+
```

Two distinct wire formats are in play:

1. **Host ↔ Gateway** — USB CDC, 921600 baud, byte-stuffed framing
   (sentinel + length + payload). Carries the LoRa traffic plus
   USB-only signal frames (TX done, RX window state, errors).
2. **Gateway ↔ Node** — LoRa, packets are the same `Header7 + Body`
   structure that travels over USB but without the USB framing
   wrapper.

The structure below covers both — every packet on USB that is
**not** a USB-signal frame is exactly the LoRa packet that went on
(or came off) the radio.

## USB framing

Each frame on the host ↔ gateway link is:

```
0x00  LEN  TYPE  DATA[LEN-1]
```

* `0x00` — frame sentinel.
* `LEN` — total bytes after `0x00 LEN`, i.e. `1 + len(DATA)`.
* `TYPE` — first payload byte. Either:
  * an LP type from
    [`racelink_proto.h`](../racelink_proto.h)::`LP::OPC_*` combined
    with a direction bit (top bit), or
  * one of the USB-signal type bytes (`EV_*`).

## Direction byte

The high bit of `TYPE` distinguishes host→node and node→host:

| Constant | Value | Meaning |
|---|---:|---|
| `DIR_M2N` | `0x00` | Master → Node (host outgoing) |
| `DIR_N2M` | `0x80` | Node → Master (node reply) |

`make_type(dir, opc7)` is just `dir | opc7` (opc7 = the 7-bit opcode
constant below).

## Header7

Every LoRa-bearing frame's body starts with a 7-byte header:

```
sender3 (3) | receiver3 (3) | type_full (1) | <Body>
```

* `sender3` / `receiver3` are the last 3 bytes of the MAC address.
  `b"\xFF\xFF\xFF"` is broadcast (and indeed every node's mask
  matches it).
* `type_full = make_type(direction, opcode7)`. The receiver checks
  the direction first; the wrong direction silently drops.

The ASCII-only constants are below; on USB they appear after the
`0x00 LEN TYPE` framing, on LoRa they are the entire payload.

## Opcodes (M2N + replies)

| Opcode | Hex | Direction | Reply | Body | Notes |
|---|---:|---|---|---|---|
| `OPC_DEVICES` | `0x01` | M2N | `IDENTIFY_REPLY` | get_devices body | Discovery broadcast |
| `OPC_SET_GROUP` | `0x02` | M2N | `OPC_ACK` | `set_group body` | Move a node into a group |
| `OPC_STATUS` | `0x03` | M2N | `STATUS_REPLY` | `status body` | Poll device state |
| `OPC_PRESET` | `0x04` | M2N | none | `P_Preset` (4 B) | Apply a numeric WLED preset |
| `OPC_CONFIG` | `0x05` | M2N | `OPC_ACK` | `P_Config` (5 B) | Configuration change (option + data) |
| `OPC_SYNC` | `0x06` | M2N | RESP_NONE | `P_Sync` (4 B) | Fire armed effects at `ts24` |
| `OPC_STREAM` | `0x07` | M2N | `OPC_ACK` | up to 128 B logical | Gateway fragments + reassembles |
| `OPC_CONTROL` | `0x08` | M2N | `OPC_ACK` | variable (3..21 B) | Direct effect parameters |
| `OPC_OFFSET` | `0x09` | M2N | RESP_NONE | variable (2..7 B) | Configure offset for ARM_ON_SYNC / OFFSET_MODE |
| `OPC_GET_CONFIG` | `0x0A` | M2N | same opcode N→M | `P_GetConfig` (1 B) → `P_Config` (5 B) | Read-back of an `OPC_CONFIG`-style property |
| `OPC_HEADLESS` | `0x0B` | M2N | RESP_NONE | `P_Headless` (2 B) | Headless-Mode catalog trigger; receivers expand via the shared catalog in `racelink_headless.h`. Broadcast-shaped. Renamed from `OPC_SCENE` on 2026-05-17 to keep the `OPC_SCENE` name free for a future host-level RaceLink-Scene opcode; wire byte value `0x0B` is unchanged. |
| `OPC_INDICATE` | `0x0C` | M2N | RESP_NONE | `P_Indicate` (2 B) | Short-lived status-indicator overlay; receivers expand via the shared catalog in `racelink_indicators.h`. Broadcast or unicast. |
| `OPC_ACK` | `0x7E` | both | — | `ack body` (4 B) | Used as a reply only |

`BODY_MAX` is 22 bytes; `OPC_CONTROL` is the first opcode that pushes
that bound (its largest body is 21 B). The receiver enforces
`BODY_MAX` and rejects oversize bodies as malformed.

`Phase D rename note (2026-04-25):` what is now `OPC_PRESET` (0x04)
was historically called `OPC_CONTROL`, and what is now `OPC_CONTROL`
(0x08) was `OPC_CONTROL_ADV`. The opcode *values* did not change —
older firmware still interoperates byte-for-byte. Only the C
identifiers were renamed for clarity.

## Body layouts

### `P_Preset` — apply a WLED preset (`OPC_PRESET`, 4 B fixed)

```
groupId (1) | flags (1) | presetId (1) | brightness (1)
```

* `groupId` — `0xFF` (255) for broadcast; otherwise a specific group.
* `flags` — see the **flags byte** section below.
* `presetId` — WLED preset slot to apply.
* `brightness` — `0..255`.

Reply: **none** for both unicast and broadcast — `OPC_PRESET` is
RESP_NONE in `racelink_proto_auto.py::RULES` and the firmware
dispatcher (`case OPC_PRESET` in `racelink_wled.cpp`) does not
emit `sendAckTo`. The host therefore treats the wire send as
fire-and-forget; the operator sees the new state via the next
`OPC_STATUS` poll, the host's own optimistic local mirror in
`send_device_preset` / `_update_group_preset_cache`, or both.

### `OPC_CONTROL` — direct effect parameters (variable, 3..21 B)

The first variable-length packet in the protocol. Layout:

```
groupId (1) | flags (1) | fieldMask (1)
   [ tail_main bytes per fieldMask bits 0..6, in fixed order ]
   [ extMask (1) | tail_ext bytes per extMask bits, if fieldMask bit 7 set ]
```

`fieldMask` bits (LSB first):

| Bit | Constant | Adds | Meaning |
|---|---:|---|---|
| 0 | `RL_CTRL_F_BRIGHTNESS` | +1 B u8 | Brightness 0–255 |
| 1 | `RL_CTRL_F_MODE` | +1 B u8 | WLED effect-mode index |
| 2 | `RL_CTRL_F_SPEED` | +1 B u8 | Effect speed 0–255 |
| 3 | `RL_CTRL_F_INTENSITY` | +1 B u8 | Effect intensity 0–255 |
| 4 | `RL_CTRL_F_CUSTOM1` | +1 B u8 | Effect custom 1 |
| 5 | `RL_CTRL_F_CUSTOM2` | +1 B u8 | Effect custom 2 |
| 6 | `RL_CTRL_F_CUSTOM3_CHECKS` | +1 B packed | bits 0–4 = `custom3` (0–31), bits 5/6/7 = `check1` / `check2` / `check3` |
| 7 | `RL_CTRL_F_EXT` | extMask byte + extended payload | Has extended block |

`extMask` bits (LSB first):

| Bit | Constant | Adds | Meaning |
|---|---:|---|---|
| 0 | `RL_CTRL_E_PALETTE` | +1 B u8 | Palette index |
| 1 | `RL_CTRL_E_COLOR1` | +3 B RGB | Slot 1 color |
| 2 | `RL_CTRL_E_COLOR2` | +3 B RGB | Slot 2 color |
| 3 | `RL_CTRL_E_COLOR3` | +3 B RGB | Slot 3 color |

Fields are emitted **only if their mask bit is set**. The receiver
keeps existing values for fields whose bit is 0 — this is what makes
"send only the changed bits" wire-efficient.

Worst case: all 7 main bits + extMask + palette + 3 colours =
2 (group/flags) + 1 (fieldMask) + 7 (main fields, one of which is the
custom3_checks byte) + 1 (extMask) + 1 + 9 (palette + 3×RGB) = **21 B**.

### `OPC_OFFSET` — configure offset (variable, 2..7 B)

Tagged-union body; the second byte selects the variant:

```
groupId (1) | mode (1)
   [ mode-specific payload ]
```

| Mode | Hex | Adds | Layout |
|---|---:|---|---|
| `OFFSET_MODE_NONE` | `0x00` | — | Just `groupId, mode`. Clears stored offset config; effective offset = 0 |
| `OFFSET_MODE_EXPLICIT` | `0x01` | +2 B | `offset_ms` (uint16 LE, clamped 0..65535) |
| `OFFSET_MODE_LINEAR` | `0x02` | +4 B | `base_ms` (int16 LE) + `step_ms` (int16 LE). Each device computes `base + groupId * step` |
| `OFFSET_MODE_VSHAPE` | `0x03` | +5 B | `base_ms` + `step_ms` + `center` (uint8 0..254). Computes `base + abs(groupId − center) * step` |
| `OFFSET_MODE_MODULO` | `0x04` | +5 B | `base_ms` + `step_ms` + `cycle` (uint8 1..255). Computes `base + (groupId % cycle) * step` |

`groupId == 255` broadcasts the formula to every device; combined
with the formula modes (LINEAR / VSHAPE / MODULO) this is the
"strategy A" wire path the optimizer chooses for all-groups
participation — one packet configures the whole fleet.

Receivers store the offset as a *pending change* that materialises
on the next accepted `OPC_PRESET` (immediate-apply path) or on the
`OPC_SYNC` that fires a queued arm-on-sync effect (deferred-apply
path). See the `OPC_OFFSET` comment block in `racelink_proto.h`
for the full state machine.

#### Acceptance gate (strict symmetric, 2026-04-30)

Every `OPC_CONTROL` and `OPC_PRESET` packet is filtered by a gate
that compares the packet's `OFFSET_MODE` flag against the
receiver's *effective* offset state (`pendingChange` if valid,
else `active`). The gate is strict in both directions:

| Packet `OFFSET_MODE` | Receiver `eff.mode` | Gate result |
|---|---|---|
| `1` | `!= NONE` | **accept** (apply with stored offset) |
| `0` | `NONE`    | **accept** (normal immediate apply) |
| `1` | `NONE`    | **drop** (use-offset request without configured offset is a no-op) |
| `0` | `!= NONE` | **drop** (device stays in offset mode; `OPC_OFFSET(NONE)` is the only exit) |

The two `accept` rows fire when the sender's intent matches the
receiver's stored state. The two `drop` rows fire on mismatches —
they are *features*, not bugs:

* The `F=1 + E=NONE` drop gives Strategy A (broadcast `OPC_CONTROL`
  with `F=1`) its scope filter — a single broadcast lands on
  exactly the offset-configured devices.
* The `F=0 + E=non-NONE` drop is the **state-stickiness rule**.
  Once a device has been transitioned into "offset mode" via
  `OPC_OFFSET(formula)` + materialisation, it stays there until
  it receives `OPC_OFFSET(NONE)` + materialisation. Random
  `F=0` packets do not implicitly transition the device out —
  they're silently dropped. State transitions are explicit,
  not implicit.

**Leaving offset mode** (the only valid sequence):

1. Send `OPC_OFFSET(NONE)` to the target. Sets `pendingChange.mode
   = NONE`, `pendingChangeValid = true`. Effective config is now
   NONE; `F=0` packets will match the gate.
2. Send a packet that materialises pending into active. Two
   options:
   * An `OPC_PRESET` with `F=0` (the dispatch case calls
     `materialisePendingChange()` after the gate accepts).
   * An `ARM_ON_SYNC` `OPC_CONTROL` with `F=0`, followed by
     `OPC_SYNC` (the SYNC handler materialises pending then
     fires the queued effect).
3. After step 2, `active.mode = NONE`, `pendingChangeValid =
   false`. The device is fully out of offset mode.

The host-side scene_runner's `offset_group(mode=none)` container
performs steps 1 + 2 in one operator action: Phase-1 sends
`OPC_OFFSET(NONE)` to the participants, Phase-2 sends each child
with `F=0` (mode-conditional, see [scene_runner_service.py](../racelink/services/scene_runner_service.py)).

**Operator discipline**: a normal (non-offset_group) scene's
children fly with `F=0`. If the targeted devices are still in
offset mode (i.e., the operator didn't clear first), the strict
gate drops every child silently. Visible symptom: the masterbar
shows TX activity but the devices don't react. Fix: run an
`offset_group(mode=none, children=[…])` scene first to transition
the devices out of offset mode.

### `P_Sync` — fire armed effects (`OPC_SYNC`, 4 B fixed)

```
ts24_le_b0 (1) | ts24_le_b1 (1) | ts24_le_b2 (1) | brightness (1)
```

* `ts24` — gateway-relative 24-bit timestamp at which the receiver
  should fire its queued `arm_on_sync` effect. The gateway's `ts24`
  clock is exposed via `EV_TX_DONE` events; the host treats it as
  opaque and just echoes back numbers it has seen.
* `brightness` — overrides any per-device brightness for this fire.
  `0` means "use stored brightness".

### `P_Config` — configuration body (`OPC_CONFIG` + `OPC_GET_CONFIG`, 5 B fixed)

```
option (1) | data0 (1) | data1 (1) | data2 (1) | data3 (1)
```

`P_Config` is the body for **both** the `OPC_CONFIG` write request
(M2N) and the `OPC_GET_CONFIG` reply (N2M). The reply mirrors the
write layout per option, so the host's existing `OPC_CONFIG` codec
parses both directions unchanged.

`OPC_CONFIG` is **unicast-only** — the device rejects broadcast
receivers. Reply is always `OPC_ACK` (sent before the option is
applied, since some options take time).

Multi-byte values are little-endian.

#### Properties vs Methods

The option codes split into two semantic categories. The split is
not visible on the wire (every option uses the same 5-byte body),
but it drives both the host UX and the read-back support:

* **Properties** are persistent values stored on the device. The
  host can read them back via `OPC_GET_CONFIG` (see below). The
  Device Options dialog renders them as input rows with a Save
  button and a divergence badge that compares the host-stored
  intent against the live device value.
* **Methods** are one-shot side-effecting commands. There is no
  meaningful "current value" to read; once invoked, the device
  performs the action and ACKs. The dialog renders them as action
  buttons (with a confirm prompt for destructive ones).
* **Hybrid** options (`0x01`, `0x03`, `0x04`) are persistent like
  properties but their state is exposed via `STATUS_REPLY`'s
  `configByte` rather than `OPC_GET_CONFIG`. From the operator UX
  they behave like methods (toggle commands).

| Hex | Name | Category | Read path |
|---|---|---|---|
| `0x01` | MAC filter enable | Method (toggle) | `STATUS_REPLY.configByte` bit 0 |
| `0x02` | Clear master MAC | Method (one-shot) | — |
| `0x03` | MAC filter persist | Method (toggle) | `STATUS_REPLY.configByte` bit 1 |
| `0x04` | WLAN AP open/closed | Method (toggle) | `STATUS_REPLY.configByte` bit 2 |
| `0x05` | Target FPS | Property | `OPC_GET_CONFIG` |
| `0x06` | Segment 0 geometry | Property (uint16 pair) | `OPC_GET_CONFIG` |
| `0x07` | Segment 1 geometry | Property (uint16 pair) | `OPC_GET_CONFIG` |
| `0x08` | ABL max mA | Property | `OPC_GET_CONFIG` |
| `0x09` | Default brightness `briS` | Property | `OPC_GET_CONFIG` |
| `0x0A` | Transition duration | Property | `OPC_GET_CONFIG` |
| `0x0F` | Clear all overrides | Method (destructive — "Reset to RaceLink defaults") | — |
| `0x80` | Forget master MAC | Method (destructive) | — |
| `0x81` | Reboot node | Method (destructive) | — |
| `0x8C` | STARTBLOCK number of slots (DEV_TYPE 50) | Property | `OPC_GET_CONFIG` |
| `0x8D` | STARTBLOCK first slot (DEV_TYPE 50) | Property | `OPC_GET_CONFIG` |

#### Identity / wireless config (0x01..0x04)

| Option | Hex | Wire | Meaning |
|---|---:|---|---|
| MAC filter enable | `0x01` | `data0`: 0 disable / 1 enable | Toggle the per-node sender MAC allowlist. |
| Clear learned master MAC | `0x02` | `data0`: any (typically 1) | Forget the bound master, return the node to "unconfigured" so it accepts the next discovery. |
| MAC filter persist | `0x03` | `data0`: 0 disable / 1 enable | Whether the bound master MAC survives reboots. |
| WLAN AP open/closed | `0x04` | `data0`: 0 closed / 1 open | Open or close the node's WiFi AP on demand. |

#### RaceLink-authorised LED-config overrides (0x05..0x0A, 0x0F)

These option codes set persistent host-authorised overrides of the
device's compile-time RaceLink defaults. See
[`../concepts/opcodes.md` §"OPC_CONFIG — device configuration"](../concepts/opcodes.md#opc_config-device-configuration)
for the override semantics, persistence, and Policy A vs Policy B
distinction.

| Option | Hex | Wire | Meaning |
|---|---:|---|---|
| Set FPS override | `0x05` | `data0`: uint8 fps (0–250) | Policy A: override `RACELINK_DEFAULT_FPS`. Persisted in `cfg.json` as `RaceLink.overrides.fps`. |
| Set Segment 0 geometry | `0x06` | `data0..1`: uint16 LE start; `data2..3`: uint16 LE stop | Policy B: set seg[0] start/stop. Persisted as `RaceLink.overrides.seg0={start,stop}`. |
| Set Segment 1 geometry | `0x07` | `data0..1`: uint16 LE start; `data2..3`: uint16 LE stop | Policy B: set seg[1] start/stop. Device appends seg[1] if missing. Persisted as `RaceLink.overrides.seg1={start,stop}`. |
| Set ABL max mA override | `0x08` | `data0..1`: uint16 LE mA (0 = ABL disabled) | Policy A: override `RACELINK_DEFAULT_ABL_MAX_MA`. Persisted as `RaceLink.overrides.abl`. |
| Set default brightness override | `0x09` | `data0`: uint8 briS (0–255) | Policy B: override the persisted boot brightness. Persisted as `RaceLink.overrides.bri`. |
| Set transition duration override | `0x0A` | `data0..1`: uint16 LE ms | Policy B: override `transitionDelayDefault`. Persisted as `RaceLink.overrides.tt`. |
| Clear all RaceLink overrides | `0x0F` | `data0..3`: 0 | **Method (destructive)** — surfaced in the Device Options dialog as "Reset to RaceLink defaults". Resets every `*Set` flag to false. Compile-time defaults re-take effect on next boot (Policy A) or operator-saved values are honoured again (Policy B). |

#### System commands (0x80..0x8F)

| Option | Hex | Wire | Meaning |
|---|---:|---|---|
| Reboot node | `0x81` | `data0`: 1 to reboot | Sets `doReboot = true`; reboot happens in main loop. |
| Number of slots (DEV_TYPE=50 only) | `0x8C` | `data0`: 1–8 | ePaper layout slot count. |
| First slot (DEV_TYPE=50 only) | `0x8D` | `data0`: 1–8 | ePaper layout starting slot. |

Unknown option codes hit the `else` branch silently (no NACK) — the
ACK was already sent. Senders should not rely on unknown-option
detection; verify support out-of-band.

### `P_GetConfig` — read-back request (`OPC_GET_CONFIG`, 1 B fixed)

```
option (1)
```

`OPC_GET_CONFIG` (opcode `0x0A`) requests the device's live value
for one **property**-class option (see *Properties vs Methods*
above). Reply uses the same opcode with the N→M direction bit and a
`P_Config`-shaped 5-byte body — the data bytes carry the live value
packed per-option in the same little-endian layout as the matching
`OPC_CONFIG` write command.

* **Unicast-only.** Different device classes interpret options
  differently, so a broadcast read would be ambiguous. Senders MUST
  use a concrete `recv3`; the firmware drops broadcast receivers.
* **Property-only.** Method codes (`0x01`–`0x04`, `0x0F`,
  `0x80`–`0x81`) are write-only; sending `OPC_GET_CONFIG` for them
  produces **no reply** and the host's `send_and_match` waiter times
  out gracefully. The dialog renders the row's device-side value as
  `device: ?` with a Retry button.
* **Reply timing.** The firmware reads the property's *live*
  runtime value (not the override slot). For Policy A overrides
  this equals "override-or-compile-default"; for Policy B it equals
  "override-or-operator-cfg". Either way the host gets the answer
  to "what is the device using right now", which is what the
  Device Options dialog's divergence check needs.
* **Codec note.** The host's `parse_reply_event` decodes a 5-byte
  reply for opcode `0x0A` into a `GET_CONFIG_REPLY` event carrying
  `option`, `data0..3`. The `PendingMatcher` matches on
  `(sender, expected_opcode, discriminator_field="option")` so two
  simultaneous reads for different options on the same device cannot
  wake each other's waiter (the secondary-discriminator field
  preserves the iteration-3 fix under the unified matcher).

### `P_Headless` — Headless-Mode catalog trigger (`OPC_HEADLESS`, 2 B fixed)

```
sceneId (1) | brightness (1)
```

> **Naming note.** Renamed from `OPC_SCENE` / `P_Scene` on 2026-05-17
> so the bare term "Scene" stays free for a future host-level
> RaceLink-Scene opcode (today's host-side RaceLink Scenes travel as
> `OPC_CONTROL`; the host-level rename is a separate, later step).
> Wire byte value `0x0B` and body layout are unchanged. The field
> name `sceneId` and the receiver-side helper / enum names keep
> "scene" terminology because each catalog row is internally still
> called a "Headless scene".

* `sceneId` — wire-stable identifier from the shared Headless catalog
  in `racelink_headless.h::HeadlessSceneId` (`SCENE_OFFSET_BREATHE = 0`,
  `SCENE_SOLID_RED = 1`, `SCENE_SOLID_GREEN = 2`, `SCENE_ALL_OFF = 3`,
  `SCENE_RESTORE_BOOT_COLOR = 4`). Unknown ids on a receiver that
  pre-dates the catalog row are silently dropped via
  `findSceneById() == nullptr` — forward-compatible.
* `brightness` — desired strip brightness while the scene runs.

Receivers expand the row locally (fxMode, speed, intensity, color1,
plus a per-group phase offset `base + groupId * step` for rows that
declare `SCENE_FLAG_USE_OFFSET`). There is **no separate** `OPC_OFFSET`
on the wire for Headless catalog triggers — the offset formula is
part of the catalog row and applied receiver-side, which keeps the
wire to a single packet per Headless trigger and avoids the
single-slot TX queue race the naïve pre-emit would trigger.

Reply: **none** (`RESP_NONE`). Always broadcast (`recv3 = FFFFFF`);
group filtering does not apply — every receiver expands the row.

`OPC_HEADLESS` is emitted exclusively by a device running in Headless
Master mode (or by external Gateway-side software that includes
`racelink_headless.h`). The wire body is identical regardless of
which side built it.

### `P_Indicate` — status-indicator overlay (`OPC_INDICATE`, 2 B fixed)

```
type (1) | durationSec (1)
```

* `type` — wire-stable identifier from the shared indicator catalog
  in `racelink_indicators.h::IndicatorType`
  (`IND_PAIR_CONFIRMED = 0`, `IND_PROBE_REJECTED = 1`,
  `IND_HEADLESS_ENTER = 2`, `IND_HEADLESS_EXIT = 3`,
  `IND_IDENTIFY = 4`). Unknown types are silently dropped —
  forward-compatible.
* `durationSec` — how long the overlay runs, in seconds (`0..255`).
  **`durationSec == 0` is a cancel signal**: the receiver clears any
  active indicator without showing a new one. Use it to abort a
  long-running indicator from the Host without waiting for it to
  expire.

Receivers render the indicator as a **frame-buffer overlay** via
WLED's `Usermod::handleOverlayDraw()` callback (fires after every
segment effect has rendered and blended, immediately before
`strip.show()`). The underlying effect's segment mode, palette,
colour slots, and `SEGENV` runtime state stay untouched — the
strobe is purely a pixel-level overwrite for the duration of the
overlay. Consequences:

* **Fleet phase sync is preserved automatically.** Time-driven
  effects (Traffic Light, etc.) continue advancing their phase
  during the overlay; on indicator expiry the device is in the
  exact phase its fleet-mates are in, with zero catch-up cycling.
* **No snapshot / restore.** The pre-indicator visual reappears
  the instant `active` flips back to `false` — there's nothing
  saved that needs restoring.
* **New wire commands during the overlay** (`OPC_HEADLESS`,
  `OPC_CONTROL`, `OPC_PRESET`) take over the segment normally;
  the host can also preempt by re-issuing `OPC_INDICATE` with a
  new catalog row or with `durationSec == 0` to cancel.

The catalog is **STROBE-only** (fxMode 23) by design and pinned to
the WLED-effective speed range `235..252` on a 3-tier urgency
code: 235 = slow / positive, 245 = medium / informational /
operator action, 250 = fast / error. Colour encodes the event
category via channel dominance (green = success, blue =
promotion, red = error, red+blue = operator-locate, mixed warm =
demotion). Pure red / green / blue / white are deliberately
avoided so an indicator cannot be confused with a normal scene
colour. See
[`RaceLink_WLED/operator-setup.md` §Indicators](../RaceLink_WLED/operator-setup.md#indicators)
for the full catalog table and rendering details.

Reply: **none** (`RESP_NONE`). Wire shape is identical for broadcast
(`recv3 = FFFFFF`, e.g. fleet-wide IDENTIFY pulse) and unicast (a
Host pinging one specific device); the firmware does not distinguish.

### Other bodies

`get_devices`, `set_group`, `status`, `stream`, `ack` body layouts
are documented inline in
[`racelink/protocol/packets.py`](../racelink/protocol/packets.py)
via `build_*_body` and the matching parsers in
[`racelink/protocol/codec.py`](../racelink/protocol/codec.py).

## Flags byte

Six user-intent flags share the same byte across `OPC_PRESET` and
`OPC_CONTROL` (and the persisted form on RL presets):

| Bit | Constant | Meaning |
|---|---:|---|
| 0 | `RL_FLAG_POWER_ON` | Brightness > 0 (auto-derived) |
| 1 | `RL_FLAG_ARM_ON_SYNC` | Defer apply until next `OPC_SYNC` |
| 2 | `RL_FLAG_HAS_BRI` | Brightness field is meaningful |
| 3 | `RL_FLAG_FORCE_TT0` | Force transition time 0 (no fade) |
| 4 | `RL_FLAG_FORCE_REAPPLY` | Re-apply even if state hasn't changed |
| 5 | `RL_FLAG_OFFSET_MODE` | Use the device's stored offset (gates participation) |

Construction is always via
[`racelink/domain/flags.py::build_flags_byte`](../racelink/domain/flags.py)
on the host side — never hand-assemble the byte.

## USB-signal frames (gateway → host only)

These frames carry no LoRa payload; they are gateway-internal
notifications. Batch B (2026-04-28) consolidated the pre-existing
`EV_RX_WINDOW_OPEN/CLOSED` pair into `EV_STATE_CHANGED` and added
two new events for the synchronous-send contract:

| Constant | Hex | Body | Meaning |
|---|---:|---|---|
| `EV_ERROR` | `0xF0` | UTF-8 reason / reason byte(s) | The gateway hit a fault |
| `EV_STATE_CHANGED` | `0xF1` | `[state_byte, [metadata]]` | Gateway's internal state machine transitioned (see *Gateway state machine* below) |
| `EV_TX_DONE` | `0xF3` | `last_len` (uint8) | Outcome event: a host-initiated frame completed transmission |
| `EV_TX_REJECTED` | `0xF4` | `[type_full, reason_byte]` | Outcome event: the gateway refused a host-initiated send (see *Reason codes* below) |
| `EV_STATE_REPORT` | `0xF5` | `[state_byte, [metadata]]` | Reply to `GW_CMD_STATE_REQUEST`; same body shape as `EV_STATE_CHANGED` |

Retired (do not use, byte values reused):

* `EV_RX_WINDOW_OPEN` (was `0xF1`) — replaced by `EV_STATE_CHANGED`.
* `EV_RX_WINDOW_CLOSED` (was `0xF2`) — subsumed by `EV_STATE_CHANGED(IDLE)` /
  `EV_STATE_CHANGED(RX)` depending on default RX mode.
* `EV_IDLE` (was `0xF4`) — the byte was repurposed as `EV_TX_REJECTED`.

`EV_TX_DONE` / `EV_TX_REJECTED` are **outcome events** — paired 1:1
with the host's `_send_m2n` synchronous wait. `EV_STATE_CHANGED` is
the **transition event** for the gateway's state machine; it drives
the master pill verbatim with no host-side derivation.

### Gateway state machine

The gateway runs a finite state machine (see
`RaceLink_Gateway/src/main.cpp`'s `setGatewayState`). The state set
depends on the gateway's `setDefault*` mode at boot:

| State | Byte | Meaning (default mode) |
|---|---:|---|
| `IDLE` | `0x00` | `setDefaultRxContinuous`: in continuous RX, ready for next host TX |
| `TX` | `0x01` | Transmitting (between scheduling and tx-done) |
| `RX_WINDOW` | `0x02` | Bounded RX window open. Metadata = `min_ms` (uint16 LE) |
| `RX` | `0x03` | `setDefaultRxNone` only: actively receiving |
| `ERROR` | `0xFE` | Gateway hit a fault. Metadata = reason byte(s) or empty |

`UNKNOWN (0xFF)` is a host-only sentinel used between USB connect
and the first `EV_STATE_REPORT` reply.

Typical transitions under `setDefaultRxContinuous` (the gateway's
current setup):

```
[IDLE] ──host TX accepted──► [TX]
[TX] ──TX completes──► [IDLE]              (also emits EV_TX_DONE)
[IDLE] ──host TX rejected──► [IDLE]        (also emits EV_TX_REJECTED; state byte unchanged)
[IDLE] ──open bounded RX window──► [RX_WINDOW]
[RX_WINDOW] ──window expires / close──► [IDLE]
[any] ──fault──► [ERROR]                   (also emits EV_ERROR)
[ERROR] ──recovery──► [IDLE]
```

The gateway emits **exactly one `EV_STATE_CHANGED`** per actual
transition (idempotent sets are deduplicated). Outcome events
(`EV_TX_DONE`, `EV_TX_REJECTED`) are emitted *in addition to* the
state transition they cause.

### `EV_TX_REJECTED` reason codes

Body byte 1 of `EV_TX_REJECTED`. Body byte 0 echoes the rejected
packet's `type_full` so the host can match the NACK to the offending
send.

| Constant | Hex | Meaning |
|---|---:|---|
| `TX_REJECT_TXPENDING` | `0x01` | Gateway already transmitting (single-slot scheduler busy) |
| `TX_REJECT_OVERSIZE` | `0x02` | Body exceeded `sizeof(rl.txBuf)` |
| `TX_REJECT_ZEROLEN` | `0x03` | Body empty / zero-length (host-side framing bug) |
| `TX_REJECT_UNKNOWN` | `0xFF` | Defence-in-depth fallback |

### Host → Gateway commands (USB-only)

Sent as the TYPE byte in `[0x00][LEN][TYPE][DATA]` framing; never
travel on the LoRa wire.

| Command | Hex | Payload | Meaning |
|---|---:|---|---|
| `GW_CMD_IDENTIFY` | `0x01` | (none, 1-byte payload `[0x01]`) | Port-discovery ping; gateway replies with its identity string |
| `GW_CMD_STATE_REQUEST` | `0x7F` | (none, 1-byte payload `[0x7F]`) | Ask gateway for current state; reply is `EV_STATE_REPORT` |

## Host ↔ Gateway flow control

The gateway's TX scheduler (`RaceLinkTransport::scheduleSend` in
the gateway firmware) is still **single-slot, no queue**, but Batch
B (2026-04-28) added a typed NACK on every rejection:

```cpp
bool ok = RaceLinkTransport::scheduleSend(rl, buf, len, jitterMaxMs);
if (!ok) {
  usb_send_tx_rejected(type_full, /* reason byte */);
}
```

The wrapper `try_schedule_or_nack(...)` in
`RaceLink_Gateway/src/main.cpp` pre-checks the same conditions
(`txPending`, oversize, zero-length) and emits the matching reason
code so the host always gets either a `TX_DONE` (success) or a
`TX_REJECTED` (refusal) for every host-initiated frame.

The host's send path is now **synchronous** — see
[`racelink/transport/gateway_serial.py`](../racelink/transport/gateway_serial.py):

```python
def _send_m2n(...) -> SendOutcome:
    """SendOutcome ∈ { SUCCESS, REJECTED(reason), TIMEOUT, USB_ERROR }.
    Synchronous: writes the frame, blocks on a Condition until the
    matching outcome arrives or the 2 s deadlock guard fires."""
```

Guarantees:

* **Exactly one outcome per call.** No "did my packet make it?"
  guesswork — the gateway either sent it (`TX_DONE`) or refused it
  (`TX_REJECTED` with reason).
* **Bounded latency.** Capped at `SEND_OUTCOME_TIMEOUT_S = 2.0` s,
  typically <500 ms with a healthy gateway under SF7.
* **One in flight at a time.** The host's `_tx_lock` /
  `_tx_outcome_cv` pair enforces 1-in-flight; pipelining isn't
  supported.

This collapses the pre-Batch-B body-length-scaled TX barrier
(`TX_BARRIER_FLOOR_S` etc.) into a single 2 s deadlock guard — the
barrier was a workaround for the silent-drop hazard that
`EV_TX_REJECTED` now eliminates.

### State queries (`GW_CMD_STATE_REQUEST` → `EV_STATE_REPORT`)

The host can ask the gateway for its current state at any time via
`gateway_service.query_state()` (which writes `[0x00][0x01][0x7F]`
and waits for the matching `EV_STATE_REPORT`, bounded to 500 ms).

Used at:

* **Startup**: pill seeds from the reply (otherwise it sits in
  `UNKNOWN` until the next spontaneous transition).
* **After USB reconnect**: re-syncs the host mirror.
* **Operator request**: the master-pill `↻` button calls
  `POST /api/gateway/query-state`.
* **Internal recovery**: after a `_send_m2n` `TIMEOUT` outcome, a
  follow-up state query is a useful diagnostic to verify the
  gateway is alive before the next send.

### Open future work (firmware)

* **Buffered burst tolerance.** A small queue (e.g. 4 entries)
  inside `scheduleSend` would let the gateway absorb LBT-window
  bursts without surfacing `TX_REJECTED` to the host. Trade-off:
  introduces ordering + fairness concerns and a small memory cost;
  keep deferred until a workload actually needs it. The
  per-rejection NACK already prevents silent drops.
* **Host-driven auto-sync.** Today's gateway emits a periodic
  auto-sync TX every 30 s when idle; if it fires while a host
  send is staged, the host sees an unexpected `EV_TX_REJECTED`.
  Migrating auto-sync to host-scheduled would close that small
  race. Currently mitigated by the host retrying on
  `REJECTED(txPending)` outcomes. The protocol-level race that
  blocked an earlier migration attempt — interval autosync
  materialising armed effects ahead of the scene's deliberate
  sync — is now resolved by the `SYNC_FLAG_TRIGGER_ARMED`
  semantics described below; only the timer itself remains as
  follow-up work.

### OPC_SYNC variants

`OPC_SYNC` is variable-length (4 or 5 bytes) and serves two
distinct roles, distinguished by the optional flags byte:

* **4 B (legacy / clock-tick form).** `ts24_0..2` + `brightness`.
  The device unwraps the 24-bit master timestamp and adjusts its
  `strip.timebase`. Pending arm-on-sync state stays armed —
  `pending.valid` is **not** materialised. This is the form used
  by autosync (today gateway-driven, eventually host-driven).
* **5 B (flag-bearing / deliberate-fire form).** Same first four
  bytes plus a trailing `flags` byte. Bit 0
  (`SYNC_FLAG_TRIGGER_ARMED = 0x01`) tells the device to
  materialise any pending arm-on-sync state in addition to the
  unconditional timebase adjustment. Used by the scene runner's
  `_run_sync` and any operator-driven manual fire.

Bits 1-7 are reserved. Bit 1 is earmarked for a future
`HAS_GROUP_MASK` extension carrying a per-group selector that
would let one SYNC fire armed effects on a subset of groups
without disturbing the rest.

The device-side `RULES` table has `req_len = 0` for `OPC_SYNC`
so both lengths pass the dispatch length check; the body is
validated inline (`bodyLen >= 4 && bodyLen <= sizeof(P_Sync)`).
The gateway also accepts both lengths from the host and passes
the flags byte through its re-stamp so the trigger bit reaches
the nodes end-to-end. **Synchronised rollout is required**: an
old-firmware node has `req_len = 4` strict and rejects the 5 B
deliberate-fire packet; flash every node before deploying a new
host. The gateway-side `WAIT_HOST_TRIGGER` inhibit stays as
defence-in-depth.

### USB latency tuning (host)

The USB-CDC bridge chip on the gateway (CP210x / FTDI / CH340)
defaults to a **16 ms latency_timer** that buffers small RX bursts
before flushing to the host. For RaceLink's interactive
small-frame traffic this dominates per-packet wall-clock —
empirical baseline was ~25 ms per send before tuning.

The host transport
([`gateway_serial.py`](../racelink/transport/gateway_serial.py))
mitigates this in three ways automatically on every open:

1. **`set_low_latency_mode(True)`** — pyserial >= 3.4, Linux only.
   Writes `ASYNC_LOW_LATENCY` via `TIOCSSERIAL` so the kernel
   USB-serial driver shrinks the bridge's effective poll interval
   to ~1 ms. Largest single impact (~8-16 ms saved per send).
2. **`ser.flush()` after every write** — forces the OS USB-serial
   buffer onto the wire instead of waiting for it to coalesce
   with a follow-up write. ~1-3 ms saved.
3. **Chunked `read(in_waiting)` in `_reader`** — pulls every byte
   already buffered in one syscall instead of `read(1)` per byte.
   ~2-5 ms saved at the next syscall boundary.

The gateway firmware also
([`main.cpp`](../../RaceLink_Gateway/src/main.cpp)`::usb_send_frame`)
coalesces the 4-part USB event (`SOF + LEN + TYPE + DATA`) into
a single buffered `Serial.write(buf, len)` so the bridge sees one
USB transaction per event instead of four. ~2-5 ms saved on the
gateway → host path.

**Operational fallback** (e.g. running on Windows where
`set_low_latency_mode` is a no-op, or where the user can't
upgrade pyserial): on Linux, the latency_timer can be tuned
manually via sysfs (requires root or a udev rule):

```bash
# One-shot:
echo 1 | sudo tee /sys/bus/usb-serial/devices/ttyUSB0/latency_timer

# Persistent via udev (replace 10c4:ea60 with your bridge's VID:PID
# from `lsusb`):
sudo tee /etc/udev/rules.d/99-racelink-low-latency.rules <<'EOF'
SUBSYSTEM=="usb-serial", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", \
  ATTR{latency_timer}="1"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
```

The host's `set_low_latency_mode` call achieves the same effect
without sudo; the manual sysfs route is the fallback when that
call is unavailable.

## Direction + response policies

Every opcode has a `(direction, response)` rule in
[`racelink/protocol/rules.py`](../racelink/protocol/rules.py)::`RULES`.
The host reads this rule to decide whether `send_*_and_wait` is
applicable. Possible response policies:

* `RESP_NONE` — fire and forget (broadcasts; `OPC_SYNC`; `OPC_OFFSET`).
* `RESP_ACK` — receiver replies with `OPC_ACK` (most M2N unicasts).
* `RESP_SPECIFIC` — receiver replies with a specific opcode (e.g.
  `OPC_DEVICES` → `IDENTIFY_REPLY`).

The host's `send_and_wait_with_retries` / `send_and_match` use this
rule to populate the right `PendingMatcher` field
(`expected_ack_of` for `RESP_ACK`, `expected_opcode` for
`RESP_SPECIFIC`) — see
[Reply Matching (PendingMatcher)](../RaceLink_Host/reply-matching.md).

## Versioning

```
PROTO_VER_MAJOR = 2
PROTO_VER_MINOR = 0
```

Defined in `racelink_proto.h`. Bump `MINOR` for backward-compatible
additions (new opcodes, new optional flag bits); bump `MAJOR` for
breaking changes (struct reshapes, opcode reuses). The proto-drift
test (`tests/test_proto_header_drift.py`) catches accidental
divergence; intentional changes still need a coordinated commit
across all three repos (Host, Gateway, WLED).

## Where things live in code

| Layer | Path |
|---|---|
| C header (source of truth) | [`racelink_proto.h`](../racelink_proto.h) |
| Auto-generated Python mirror | [`racelink/racelink_proto_auto.py`](../racelink/racelink_proto_auto.py) |
| Generator | [`gen_racelink_proto_py.py`](../gen_racelink_proto_py.py) |
| Body builders | [`racelink/protocol/packets.py`](../racelink/protocol/packets.py) |
| Reply parsers | [`racelink/protocol/codec.py`](../racelink/protocol/codec.py) |
| Per-opcode rules | [`racelink/protocol/rules.py`](../racelink/protocol/rules.py) |
| USB framing | [`racelink/transport/framing.py`](../racelink/transport/framing.py) |
| Transport sender / reader | [`racelink/transport/gateway_serial.py`](../racelink/transport/gateway_serial.py) |
| Drift regression test | [`tests/test_proto_header_drift.py`](../tests/test_proto_header_drift.py) |
