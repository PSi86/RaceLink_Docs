# Wire timing — per-packet wall-clock breakdown

Reference for the per-packet wall-clock cost of a host-initiated send,
from `_send_m2n` entry through the gateway's LoRa transmit cycle and
back to the host's `EV_TX_DONE` wakeup. Distilled from a 2026-05-09
diagnostic instrumentation run; the absolute numbers serve as a
baseline for future regression checks.

> **Source of truth.** `racelink/transport/gateway_serial.py::_send_m2n`,
> `racelink/services/scene_runner_service.py::run`, and the firmware-
> side TX path in
> [`RaceLink_Gateway/src/racelink_transport_core.h::scheduleSend / service`](../RaceLink_Gateway/README.md).
> The Semtech AN1200.13 airtime formula lives in
> `racelink/services/scene_cost_estimator.py::lora_airtime_ms`.

## Per-packet wall-clock decomposition

Every host-initiated unicast or broadcast frame passes through the
following stages. The columns below name the WTIME diagnostic labels
(used inside `gateway_serial.py` during the 2026-05-09 instrumentation
run); the labels are no longer in the source but they remain useful
shorthand for the breakdown.

| Stage  | Definition                                                                                 | Typical cost                     | Notes |
|--------|--------------------------------------------------------------------------------------------|----------------------------------|-------|
| `build`| Frame assembly (`bytes([type_full]) + recv3 + body`) and acquiring `_tx_outcome_cv`.       | ~30 µs                           | Pure Python; sub-millisecond on a Pi 4. |
| `write`| `ser.write(frame)` followed by `ser.flush()`.                                              | ~1.4 – 2.7 ms                    | USB-CDC submission + kernel flush. Linux honours `set_low_latency_mode(True)` on FTDI/CP210x; ESP32-S3 native CDC uses the URB poll defined by the device's `bInterval`. |
| `wait` | `Condition.wait_for(TX_DONE)` — covers the gateway service-loop pickup, radio mode-switch, LoRa airtime, TX_DONE interrupt, USB return, and the host RX-reader wakeup. | LoRa airtime + ~14 ms gateway/USB overhead | Dominant component. |
| `txev` | `_emit_tx(TX_M2N)` — fires the listener fan-out (master state update, gateway-service hooks). | ~30 µs                         | All listeners use non-blocking `put_nowait` for SSE distribution. |
| `outc` | `_emit_tx(TX_OUTCOME)` — final outcome event (SUCCESS / REJECTED / TIMEOUT / USB_ERROR).   | ~20 µs                           | Same fan-out path as `txev`. |

`build` + `write` + `wait` + `txev` + `outc` is the full wall-clock the
caller of `transport.send_*` observes. The runner's
`ActionResult.duration_ms` field measures `_dispatch` start to end and
therefore covers exactly this span (plus the trivial Python wrapping
in `_run_*` and `_execute_plan`).

## Reference values — 2026-05-09

**Hardware:** RotorHazard plugin on Raspberry Pi 4 (Linux); Heltec WiFi
LoRa 32 V3 gateway (ESP32-S3, native USB-CDC enumerated as
`/dev/ttyACM*` via the `cdc_acm` kernel driver); WLED node with
SF7 / BW125 kHz / CR4:5 / explicit-header / CRC-on / preamble = 8 sym.

### Per-packet WTIME breakdown

Six consecutive packets within a single scene execution, mixed action
kinds, no SSE clients connected:

```
opcode         body_len  build  write   wait    txev  outc  total
OPC_OFFSET     7         34 µs  2681 µs 53967 µs 39 µs 25 µs 56748 µs
OPC_OFFSET     2         36 µs  2372 µs 50951 µs 31 µs 17 µs 53409 µs
OPC_OFFSET     2         23 µs  1454 µs 53237 µs 22 µs 12 µs 54749 µs
OPC_OFFSET     2         23 µs  1380 µs 52350 µs 21 µs 12 µs 53789 µs
OPC_CONTROL  21          24 µs  1977 µs 77724 µs 25 µs 16 µs 79768 µs
OPC_SYNC       5         23 µs  2209 µs 51931 µs 76 µs 17 µs 54259 µs
```

* Average per-packet `total` (this run): **~58.7 ms**
* Average per-packet `wait` (this run): **~57.0 ms**
* Variance across `wait` for same-size packets: **±2 ms** (consistent
  with normal scheduler jitter)

### Per-action SceneRunner timestamps

Single OPC_SYNC action, idx = 2, no SSE clients:

```
start_emit         19 µs   (no-op when progress_cb is None / no clients)
dispatch        54 672 µs   (= the OPC_SYNC packet's _send_m2n cost)
terminal_emit      29 µs
duration_ms_field  55       (= dispatch time, rounded)
wall_total_us   54 721 µs   (start_emit → terminal_emit return)
```

Action wrap-overhead is ≤ 50 µs for headless runs — negligible
compared to the wire path.

## Comparison vs. theoretical LoRa airtime

For SF7 / BW125 / CR4:5 / CRC-on / explicit-header / preamble = 8 sym,
[`lora_airtime_ms`](https://github.com/PSi86/RaceLink_Host/blob/main/racelink/services/scene_cost_estimator.py)
computes pure Time-on-Air. Subtracting from the observed `wait`
isolates the per-packet wire overhead (USB submission, gateway radio
setup, TX_DONE return).

| Frame size                                     | Theoretical airtime | Observed `wait` | Per-packet overhead |
|------------------------------------------------|--------------------:|----------------:|--------------------:|
| 9 B (Header7 + 2 B body, OPC_OFFSET tail)      | ~36 ms              | ~52 ms          | **~16 ms**          |
| 12 B (Header7 + 5 B body, OPC_SYNC)            | ~41 ms              | ~52 ms          | **~11 ms**          |
| 14 B (Header7 + 7 B body, OPC_OFFSET head)     | ~41 ms              | ~54 ms          | **~13 ms**          |
| 28 B (Header7 + 21 B body, OPC_CONTROL)        | ~62 ms              | ~78 ms          | **~16 ms**          |

The mean per-packet wire overhead in this run is **~14 ms**, which sits
~2 ms above the calibration constant baked into the cost estimator
(`WIRE_OVERHEAD_MS_PER_PACKET = 12.0` in
`racelink/services/scene_cost_estimator.py`). The variance from packet
to packet is small enough that the constant remains a reasonable
predictor; recalibrate only after a hardware or firmware change that
shifts the mean by more than ~3 ms.

## The estimator's two prediction columns

`scene_cost_estimator.py::ActionCost` publishes two time fields per
action and per scene total:

* `airtime_ms` — pure LoRa Time-on-Air (Semtech AN1200.13). Useful as a
  diagnostic ("how many ms of radio resource does this action use?").
* `wall_clock_ms` — `airtime_ms + N × WIRE_OVERHEAD_MS_PER_PACKET`. The
  predictor against which the runner's measured `actual: NNN ms`
  should be compared.

When eyeballing run results, always compare `actual` against
`wall_clock_ms` (or add `N × 14 ms` to `airtime_ms` manually as a
quick mental check). Comparing `actual` against `airtime_ms` will
always look like a regression — by construction, the wall-clock
includes the wire overhead the airtime does not.

## Recalibration procedure

If the gateway, host hardware, or LoRa parameters change materially
(different SF/BW, different USB chip, different host platform):

1. Re-instrument `_send_m2n` with per-stage timestamps (the WTIME
   labels above are the canonical breakdown).
2. Run a representative scene 2–3 times and capture the per-packet
   `wait` values for at least three frame sizes.
3. Compute the per-packet overhead = `wait − lora_airtime_ms(frame)`
   averaged across the captured packets.
4. Update `WIRE_OVERHEAD_MS_PER_PACKET` in
   `racelink/services/scene_cost_estimator.py` with the new mean.
5. Run `pytest tests/test_scene_cost_estimator.py` — at least one
   round-trip test pins the constant in a fixture.

The constant is also surfaced via `lora_parameters()` so the editor's
cost-badge tooltip stays in sync without any extra plumbing.
