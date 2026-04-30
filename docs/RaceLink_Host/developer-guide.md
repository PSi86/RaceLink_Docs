# RaceLink Developer Guide

Checklists for the recurring "I want to add X" tasks. Each checklist
walks you through every file that needs an update so a feature
addition doesn't accidentally land half-implemented (the
`sendGroupControl` ghost-method incident, where a renamed method
hid behind a broad `except` for over a year, is the cautionary
tale here).

For the why and the wire format, see:

* [ARCHITECTURE.md](architecture.md) — package layout + threading model.
* [PROTOCOL.md](../reference/wire-protocol.md) — wire-format reference.
* [UI_CONVENTIONS.md](ui-conventions.md) — button vocabulary, toast/confirm rules.

## Adding a new scene-action kind

Scene actions are the building blocks of a scene (e.g. `wled_preset`,
`startblock`, `delay`, `sync`, `offset_group`). The kind name is the
canonical identifier across the validator, runner, and editor.

**Files to touch (in dependency order):**

1. **Constant** in [`racelink/services/scenes_service.py`](../racelink/services/scenes_service.py):
   ```python
   KIND_MY_NEW_KIND = "my_new_kind"
   ALL_KINDS = (..., KIND_MY_NEW_KIND)
   ```
2. **Validator** in the same file: add a `_canonical_my_new_kind_action`
   helper if the action has a non-trivial shape, and dispatch to it
   from `_canonical_action`. If your kind requires a target, validate
   it via the existing `_canonical_target` (group / device).
3. **Editor schema** in `get_action_kinds_metadata()`: declare the
   kind with its `vars` (UI inputs), `supports_flags_override`,
   etc. The WebUI consumes this to render the action body.
4. **Runner dispatch** in [`racelink/services/scene_runner_service.py`](../racelink/services/scene_runner_service.py):
   add `if kind == KIND_MY_NEW_KIND: return self._run_my_new_kind(...)`
   in `_dispatch_action`, and implement `_run_my_new_kind`. Return an
   `ActionResult` with `ok` / `error` / `degraded` set per the same
   contract every other `_run_*` follows. Wrap the underlying
   `control_service.send_*` call in `bool(...)` and propagate `False`
   into a degraded ActionResult.
5. **Cost estimator** in [`racelink/services/scene_cost_estimator.py`](../racelink/services/scene_cost_estimator.py):
   add a branch in `estimate_action` returning the predicted
   packets / bytes / airtime. If the new kind broadcasts, the cost
   is bounded; if it fans out per device, accumulate accordingly.
6. **Capability mapping** in [`racelink/static/scenes.js`](../racelink/static/scenes.js)
   (`requiredCapForKind`): if the new kind requires a device
   capability (WLED / STARTBLOCK / etc.), return the cap string.
   Without this entry the editor will *not* filter target
   dropdowns for the new kind — and you'll re-introduce the
   silent-success bug class C5 closed.
7. **Frontend rendering** in `scenes.js`:
   * Add `KIND_MY_NEW_KIND` (or just the string literal) to
     `SCENE_KIND_LABELS` and `SCENE_KINDS_ORDER`.
   * If the kind has parameters, add them to the editor schema in
     step 3 — the generic `buildVarsRow` will render them. Custom
     widgets (e.g. the offset_group config panel) need their own
     `buildXyz` function.
   * `defaultActionForKind(kind)`: return the seed shape for the
     editor's "+ Add" button.
8. **Tests** in [`tests/test_scenes_service.py`](../tests/test_scenes_service.py)
   (validator round-trip, edge cases) and
   [`tests/test_scene_runner_service.py`](../tests/test_scene_runner_service.py)
   (dispatch happy path + transport-missing degraded path). If the
   kind has cost characteristics worth pinning, also add a
   `test_scene_cost_estimator.py` test.
9. **Plan-file note** if the addition is significant: append to
   the active plan at
   the maintainer's internal engineering ledger so the rationale
   stays linked to the change.

**Checklist:**

```
[ ] KIND_* constant in scenes_service.py
[ ] _canonical_*_action validator (if non-trivial shape)
[ ] get_action_kinds_metadata entry
[ ] scene_runner_service.py dispatch + _run_* implementation
[ ] scene_cost_estimator.py branch
[ ] scenes.js requiredCapForKind entry (if cap-gated)
[ ] scenes.js SCENE_KIND_LABELS + SCENE_KINDS_ORDER
[ ] scenes.js defaultActionForKind seed
[ ] tests for validator + runner + (optional) cost
[ ] plan-file note (if significant)
[ ] manual smoke: editor renders the kind, save+load round-trips, run produces the expected wire trace
```

## Adding a new wire opcode

Adding an opcode means changing the wire format — coordinate across
all three repos (Host, Gateway, WLED). The `tests/test_proto_header_drift.py`
test will fail otherwise.

**Files to touch:**

1. **C header** [`racelink_proto.h`](../racelink_proto.h):
   * Add the value to the LP enum (`OPC_*`).
   * Document the body layout and response policy in a comment
     block above the matching struct (see `OPC_OFFSET` for the
     reference style).
   * Add the matching `static const uint8_t MAX_P_*` for any
     variable-length body, plus a `static_assert(MAX_P_* <= BODY_MAX)`.
   * Add a `PacketRule` entry in `RULES[]` (direction + response
     policy + max body length).
2. **Mirror in Gateway + WLED firmware repos**: copy the updated
   `racelink_proto.h` byte-identically to
   `../RaceLink_Gateway/src/racelink_proto.h` and
   `../RaceLink_WLED/racelink_proto.h`. Verify with
   `pytest tests/test_proto_header_drift.py`.
3. **Auto-generated Python mirror** [`racelink/racelink_proto_auto.py`](../racelink/racelink_proto_auto.py):
   re-run `python gen_racelink_proto_py.py` to regenerate. Don't hand-
   edit the generated file.
4. **Body builder** in [`racelink/protocol/packets.py`](../racelink/protocol/packets.py):
   add `build_my_new_opc_body(...)`. Return the body bytes
   (without the Header7); the framing code wraps it.
5. **Reply parser** in [`racelink/protocol/codec.py`](../racelink/protocol/codec.py):
   if the opcode has a reply (RESP_ACK or RESP_SPECIFIC), add the
   parse path. The dict shape returned is the event the listeners
   see.
6. **Per-opcode rule** in [`racelink/protocol/rules.py`](../racelink/protocol/rules.py):
   if you didn't include this in step 1's regen, add manually.
7. **Transport entry-point** in [`racelink/transport/gateway_serial.py`](../racelink/transport/gateway_serial.py):
   add `send_my_new_opc(...)` that calls `_send_m2n` with the
   matching `LP.make_type(LP.DIR_M2N, LP.OPC_MY_NEW)` and the body
   from step 4.
8. **Service wrapper** if the opcode needs orchestration (retries,
   reply collection, post-ACK state mutation):
   add a method to the appropriate service in `racelink/services/`,
   typically `gateway_service.py` (high-level dispatch) or a
   dedicated service if the surface is large enough.
9. **Tests** in [`tests/test_protocol.py`](../tests/test_protocol.py)
   for the body builder + parser, and in the matching service test
   file for the orchestration.
10. **Documentation** in [PROTOCOL.md](../reference/wire-protocol.md): add the opcode
    to the table and a body-layout subsection. The header is the
    source of truth, but the doc is what people read.

**Checklist:**

```
[ ] racelink_proto.h: OPC_* + PacketRule + struct/comment
[ ] Mirror to Gateway + WLED repo (byte-identical)
[ ] Re-run gen_racelink_proto_py.py
[ ] build_*_body in protocol/packets.py
[ ] reply parse path in protocol/codec.py (if reply expected)
[ ] transport.send_* in transport/gateway_serial.py
[ ] service wrapper (orchestration, retries, post-ACK)
[ ] tests/test_protocol.py round-trip
[ ] tests/test_<service>.py orchestration
[ ] tests/test_proto_header_drift.py passes (no manual change needed; just run it)
[ ] PROTOCOL.md: opcode table + body layout
[ ] firmware-side handlers in Gateway + WLED
```

## Adding a new service

A service is a stateless or small-stateful module under
[`racelink/services/`](../racelink/services/) that owns one
coherent piece of host logic.

**Files to touch:**

1. **Module** at `racelink/services/my_service.py`:
   * Module docstring (5–15 lines): purpose, public API, dependencies,
     threading expectations. Use `gateway_service.py` as the template.
   * Module logger: `logger = logging.getLogger(__name__)`.
   * Class `MyService` with `__init__(self, controller, gateway_service)`
     (or whatever dependencies it needs).
   * Public methods that return useful values (`bool` for send-style
     operations, dicts for query operations, raise `ValueError` for
     bad input).
2. **Service init** in [`racelink/services/__init__.py`](../racelink/services/__init__.py):
   re-export the class.
3. **Wire-up** in [`controller.py`](../controller.py)::`__init__`:
   ```python
   self.my_service = MyService(self, self.gateway_service)
   ```
4. **Web routes** in [`racelink/web/api.py`](../racelink/web/api.py)
   if the service is operator-facing: route handler that validates
   input via `request_helpers.require_int` (or similar), calls the
   service, returns the response. Match the existing `try / except
   RequestParseError → 400` and `try / except Exception → 500
   with type+traceback log` patterns.
5. **Tests** at `tests/test_my_service.py`:
   * Unit tests with a fake controller / fake transport.
   * Coverage for the boolean return contract (transport-missing
     returns False; happy path returns True).
   * Coverage for any error paths.
6. **ARCHITECTURE doc** at [ARCHITECTURE.md](architecture.md):
   add a row to the Service Layer table.

**Checklist:**

```
[ ] racelink/services/my_service.py with module docstring + logger
[ ] services/__init__.py re-export
[ ] controller.py wiring
[ ] web/api.py route(s) (if operator-facing)
[ ] tests/test_my_service.py
[ ] ARCHITECTURE.md service-table entry
```

## Adding a new task-manager-driven workflow

Long-running ops (multi-second, multi-stage) live in
[`racelink/web/tasks.py`](../racelink/web/tasks.py) so the web
request returns immediately and the UI can subscribe to SSE
`task` events for progress.

**Files to touch:**

1. **Service method** that does the work (likely a new service
   per "Adding a new service" above, or a method on an existing
   one). The method must accept a `task_manager` parameter and
   call `task_manager.update(meta={"stage": "...", "message": "...",
   ...})` at every stage transition. The `meta` shape is free-form
   but the existing operator-facing UI expects:
   * `stage` — short uppercase tag (e.g. `HOST_WIFI_ON`,
     `UPLOAD_FW`).
   * `message` — one-line operator-readable description.
   * `index` / `total` — for per-device fan-outs.
   * `addr` — current MAC if applicable.
2. **Web route** in `web/api.py`: validate input, then
   `ctx.tasks.start("my_task_name", target_fn, meta={...})` where
   `target_fn` is a closure that calls the service method with the
   task manager. Return `{"ok": True, "task": ctx.tasks.snapshot()}`.
3. **Frontend handler** in [`racelink/static/racelink.js`](../racelink/static/racelink.js)::`updateTask`:
   add a branch for `name === "my_task_name"` that updates the UI
   from the `meta`. Long-running ops with their own dialog (FW
   update is the reference) keep the dialog open and render the
   progress in-dialog; simpler ops can rely on the masterbar's
   `taskDetail` span.
4. **Tests**: at minimum verify the route returns immediately
   (`{"ok": True, "task": {...running...}}`); deeper integration
   tests can exercise the meta-update path with a mock task
   manager.

## Modifying threading-sensitive code

Anything that touches the gateway, the device repository, or the
SSE layer crosses a thread boundary. Before submitting:

* **Read [ARCHITECTURE.md](architecture.md) §Threading Model**.
  Confirm which thread your code runs on.
* **Confirm the lock contract**: if you're mutating shared state,
  use the existing locks (`state_repository.lock`,
  `_pending_config_lock`, `_pending_expect_lock`,
  `_tx_lock`). If you're adding a new shared field, add a
  matching lock — and add a regression test in
  [`tests/test_state_concurrency.py`](../tests/test_state_concurrency.py)
  pinning the contract.
* **Never hold `state_repository.lock` across RF I/O** — see the locking-rule note in
  ARCHITECTURE.md. The reference pattern is
  `_apply_device_meta_updates` in api.py.
* **Name your threads** (`name="rl-<purpose>"`). This is a project
  convention; new threads without a name
  pollute `threading.enumerate()` output and make py-spy traces
  illegible.
* **Daemon threads only via `ThreadPoolExecutor`** when you can
  bound concurrency (see `gateway_service._auto_restore_executor`
  for the reference). One-shot daemons are still acceptable for
  truly singleton tasks (the RX reader, the reconnect worker).

## Common patterns

### Adding a `request_helpers.require_int`-style validator

Cross-cut input validation lives in
[`racelink/web/request_helpers.py`](../racelink/web/request_helpers.py).
The pattern: a helper raises `RequestParseError` (a `ValueError`
subclass) on bad input; the route catches it once and translates
to a 400. Adding a new helper:

```python
def require_mac(body, key, *, label=None):
    name = label or key
    raw = require_str(body, key, label=name)
    raw = raw.strip().upper()
    if not _MAC12_RE.match(raw):
        raise RequestParseError(f"{name} must be a 12-char hex MAC")
    return raw
```

Then add a test in `tests/test_web_request_helpers.py` matching
the existing `RequireIntTests` style.

### Adding a `# swallow-ok:` annotation

The exception-hygiene test (`tests/test_exception_hygiene.py`)
requires every `except Exception` block to either log, re-raise,
or carry a `# swallow-ok: <reason>` comment. The reason should be
substantive — "best-effort fallback; caller proceeds with safe
default" is the bare minimum, but a one-line *why* is better.

If you're tempted to swallow at an RF/persistence boundary,
prefer a `logger.warning(..., exc_info=True)` over a silent pass.
A previous project-wide sweep went through every
broad except in the project; aim to match that quality on new
code.

### Returning a boolean from a `send_*` method

Every `send_*` method on `control_service` returns `bool`. `True`
means "the transport accepted the frame for queueing"; `False`
means "transport not ready / no target / nothing went out". The
a project-wide review traced silent-success bugs back to methods that
returned `None` instead. New send-style methods follow the
contract:

```python
def send_my_new_opc(self, ...) -> bool:
    transport = self._require_transport("sendMyNewOpc")
    if transport is None:
        return False
    transport.send_my_new_opc(...)
    return True
```

## Regenerating WLED metadata after a firmware bump

Three RaceLink modules under [`racelink/domain/`](../racelink/domain/) are
**fully auto-generated from the WLED checkout** by
[`gen_wled_metadata.py`](../gen_wled_metadata.py). They must never be
hand-edited; the file headers say so and `git blame` will land on the
generator script, not a human commit.

| Generated file | Source in WLED checkout | What it carries |
|---|---|---|
| [`wled_effects.py`](../racelink/domain/wled_effects.py) | `wled00/FX.h` (effect IDs) + `wled00/FX.cpp` (`_data_FX_MODE_*[]` strings) | Per-effect slot metadata: which sliders/toggles/colors/palette an effect uses, plus custom labels (`"Bg"`, `"Duty cycle"`, …). |
| [`wled_palettes.py`](../racelink/domain/wled_palettes.py) | `wled00/FX_fcn.cpp` (`JSON_palette_names[]`) | Palette id → display name. |
| [`wled_palette_color_rules.py`](../racelink/domain/wled_palette_color_rules.py) | `wled00/data/index.js` (`updateSelectedPalette()`) | The palette-conditional color slot rule: which built-in `* Color…` palettes (ids 2..5 in stock WLED) force-show extra color pickers regardless of effect metadata. |

The generator parses each source file with regexes pinned to the upstream
shape; if WLED ever reshapes one of them (e.g. moves
`updateSelectedPalette` or changes its `if (s > 1 && s < 6)` guard), the
generator raises `RuntimeError` with a pointer to the file/function it
failed on, rather than silently producing wrong output. The rule
extraction is also unit-tested in
[`tests/test_wled_effect_metadata.py`](../tests/test_wled_effect_metadata.py)
under `ParsePaletteColorRuleTests`.

### When to regenerate

- You bumped the bundled WLED firmware (the checkout under `../WLED LoRa/WLED`).
- A WLED contributor added/renamed/removed an effect (changes `FX.h` + `FX.cpp`).
- A WLED contributor added/renamed/removed a built-in palette (changes `FX_fcn.cpp`).
- A WLED contributor reshaped `updateSelectedPalette()` (changes the JS rule).

### How

1. Make sure the WLED checkout path matches what the generator expects.
   The default points at a maintainer-local path; always pass
   `--wled <path>` to override, pointing at the root of your
   `RaceLink_WLED` checkout (the directory containing `wled00/`).
2. Run the generator:
   ```
   py gen_wled_metadata.py
   ```
   It prints one line per output file, e.g.:
   ```
   Wrote racelink\domain\wled_effects.py (188 effects)
   Wrote racelink\domain\wled_palettes.py (72 palettes)
   Wrote racelink\domain\wled_palette_color_rules.py (palette-color rule: ...)
   ```
   If any source-file shape check fails the script aborts with
   `RuntimeError`; read the message, update the relevant regex in
   `gen_wled_metadata.py`, and rerun.
3. Run the parser tests:
   ```
   py -m pytest tests/test_wled_effect_metadata.py -q
   ```
   The `ParsePaletteColorRuleTests::test_generated_module_matches_stock_thresholds`
   pin will fire if the new firmware ships different palette
   thresholds — update the pin to match the new values *and* note the
   change in the WebUI smoke checklist below.
4. (Optional but recommended) Smoke-test the RL-preset editor in a
   browser: open it, pick effect "Traffic Light", walk the palette
   dropdown, and confirm that color-slot visibility still matches WLED's
   own webui (`* Color 1` → 1+Bg, `* Color Gradient` → 1+Bg+3, etc.).

### How the generated data reaches the UI

```
WLED source ──► gen_wled_metadata.py ──► racelink/domain/wled_*.py
                                                  │
                                                  ▼
                            racelink.domain.specials.serialize_rl_preset_editor_schema()
                                                  │
                            GET /racelink/api/rl-presets/schema
                                                  │
                                                  ▼
                            racelink.static.racelink.js :: ensureRlPresetUiSchema()
                                                  │
                                                  ▼
                            buildRlPresetForm() consumes options[].slots and
                            schema.paletteColorRules to drive the editor
```

No JS-side hardcoding remains: `paletteForcesSlot` reads the rule from
the schema (with a small literal fallback for the case where an old
backend hasn't shipped the field yet, intentionally matching the stock
values so behaviour is preserved during a rolling upgrade).

The deterministic-effects catalogue in
[`wled_deterministic.py`](../racelink/domain/wled_deterministic.py) is
the **only** WLED-derived module that is *not* auto-extracted — it
encodes a hand-audited subset of `FX.cpp` per the workflow below.

## WLED OTA gate matrix

WLED's HTTP `/update` handler runs four gates before accepting a
firmware POST: three host-recoverable HTTP-401 gates (same-subnet,
settings-PIN, OTA-lock) plus one HTTP-500 gate (firmware release-name
match). Knowing each one is the quickest path through any "why did
the OTA fail?" debugging session. References point at the upstream
WLED source layout (`wled00/wled_server.cpp` etc.); in the
RaceLink WLED fork the same files live alongside the
`racelink_wled` usermod.

### The four gates

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
to set `skipValidation=1` in the multipart body explicitly — operator
ticks the "Skip firmware-name validation" checkbox in the OTA dialog.
The checkbox is off by default because flashing a binary with the
wrong chip variant can brick a device; the gate exists for a reason.

The trap that bites a fleet OTA on AP+STA-mode nodes is Gate 1.
`inSameSubnet` masks the client's IP against the device's
`Network.localIP() & subnetMask()`. In AP+STA mode `Network.localIP()`
returns the **STA** address, not `4.3.2.1`, so an AP-side host with
a perfectly valid `4.3.2.x` DHCP lease still fails the check.
`inLocalSubnet` (`wled_server.cpp:66-72`) is broader — it explicitly
accepts `4.3.2.0/24` when `apActive` — but it's only consulted when
`otaSameSubnet=false`.

### Build flags that affect the gates

The exhaustive list, derived from
the upstream WLED source files `wled00/wled.h` and `wled00/const.h`:

| Variable | Default | Build flag | Effect on the gates |
|---|---|---|---|
| `apPass` | `DEFAULT_AP_PASS = "wled1234"` | `-D WLED_AP_PASS="..."` (requires `WLED_AP_SSID` too — `wled.h:214` has a hard `#error` if only one is set) | WiFi association layer; doesn't touch the OTA gate. |
| `otaPass` | `DEFAULT_OTA_PASS = "wledota"` (`const.h:41`) | `-D WLED_OTA_PASS="..."` | Sets the password the host POSTs to `/settings/sec` to clear `otaLock`. **Defining the macro also flips `otaLock=true`** by default (`wled.h:573-577`). |
| `otaLock` | `true` if `WLED_OTA_PASS` defined, else `false` | implicit | Gate 3. |
| `otaSameSubnet` | **`true`** unconditionally (`wled.h:584` — no `#ifdef`/`#else`) | **NONE** — there is no `WLED_OTA_SAME_SUBNET` define | Gate 1. The compiled default is hardcoded; only runtime flips it. |
| `settingsPIN` | `WLED_PIN` macro → fallback `""` (`wled.h:227-229`) | `-D WLED_PIN="1234"` (exactly 4 chars) | Bypasses Gate 1 via `!strlen(settingsPIN)` short-circuit. Sets `correctPIN=false` at boot, so Gate 2 then blocks until the PIN is entered. |

**Important non-obvious points:**

1. **`WLED_OTA_PASS` does NOT bypass same-subnet.** Gate 3 (OTA lock)
   and Gate 1 (same-subnet) are independent. The OTA password only
   clears Gate 3. A tempting reading of WLED's docs makes this
   ambiguous; the line-pinned source is unambiguous.
2. **There is no build flag for `otaSameSubnet`.** The only same-subnet
   bypass at build time is `WLED_PIN`, and that comes with the
   Gate 2 PIN-entry tax.

### Five firmware-side options to ship same-subnet=false

Ranked by friction:

#### Option 1 — `racelink_wled` usermod override (recommended)

In the usermod's `setup()`:

```cpp
// usermods/racelink_wled/racelink_wled.cpp
otaSameSubnet = false;  // RaceLink: AP+STA means inSameSubnet
                        // doesn't recognise AP-side clients.
```

Runs **after** `deserializeConfigFromFS()`, so it overrides whatever
`cfg.json` carries. Side-effect-free. Doesn't touch WLED core. One
line, contained in the usermod's git history.

#### Option 2 — patch `wled.h:584`

```c
WLED_GLOBAL bool otaSameSubnet  _INIT(false);  // was _INIT(true)
```

Equivalent to Option 1 but lives in WLED core. Pick this if your
fork policy prefers core-default changes over usermod overrides.

#### Option 3 — `WLED_PIN` build flag

`-D WLED_PIN="1234"` in `platformio_override.ini`. Bypasses Gate 1
via the `!strlen(settingsPIN)` short-circuit, **but** Gate 2 then
fires until the host enters the PIN. Host implementation: a single
POST to `/settings/sec` with `PIN=1234` form-encoded, then the OTA.
Side effect: the PIN gates ALL settings pages (`wled_server.cpp:759`),
not just `/update`, so any browser pulling up `/settings` on a
device gets prompted.

The PIN entry flow itself is straightforward (single POST handled
at `set.cpp:10-13` → `checkSettingsPIN` at `util.cpp:454-460`); the
PIN-everywhere side effect is the cost.

#### Option 4 — bake `cfg.json` into LittleFS

Ship `{"ota":{"same-subnet":false}}` in the device's filesystem,
either via a `wled00/data/cfg.json` build-time addition or a
first-boot writer in the `racelink_wled` usermod. Less robust than
Options 1 / 2 because a `/settings/sec` save by the operator can
silently flip `otaSameSubnet=true` again (the form's `SU` checkbox
is checked-by-default in WLED's UI).

#### Option 5 — host-side auto-unlock (already implemented)

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
`otaSameSubnet=false` in the device's `cfg.json`. **B is therefore a
real fix, not just a runtime mitigation** — every device that 401s
gets auto-fixed on its first OTA, future OTAs skip the auto-unlock
round-trip.

### Recommendation

Ship Option 1 (usermod override) in new firmware images so factory-
fresh nodes are OTA-friendly without the auto-unlock round-trip.
Keep Option 5 (host-side auto-unlock) in place as the safety net —
it covers existing devices flashed before Option 1 was in place,
plus any device whose `cfg.json` somehow ended up with
`otaSameSubnet=true` (factory reset, manual re-enable, etc.).

## Updating the WLED-deterministic effects list

The RL-preset editor marks "deterministic" WLED effects with a leading
`*` and sorts them to the top of the dropdown so operators picking
offset-mode-safe effects see them first. Deterministic = the effect's
pixel output depends only on synced inputs (`strip.now` + segment
params), so two nodes with synchronised `strip.timebase` render
identically. The audited set is in
[`racelink/domain/wled_deterministic.py`](../racelink/domain/wled_deterministic.py)
(currently 19 effects); the source-of-truth catalogue lives in the WLED
fork at `usermods/racelink_wled/docs/effects-deterministic.md`
(the same content is also available in this consolidation at
`concepts/deterministic-effects.md`).

**When to update**: a WLED release adds/changes an effect, or the
catalogue doc grows a new "✓" entry.

**How**:

1. Read the analysis doc, especially §"How to verify a new / unlisted
   effect". Apply its 5-step grep checklist to the effect's body in
   `wled00/FX.cpp`.
2. If passes: add the numeric ID to `WLED_DETERMINISTIC_EFFECT_IDS`
   in `wled_deterministic.py` with an inline comment naming the
   effect + FX.cpp anchor.
3. Update the pin test in
   [`tests/test_wled_effect_metadata.py`](../tests/test_wled_effect_metadata.py)::`WledDeterministicTaggingTests::test_deterministic_id_set_matches_analysis`
   — same ID + bump the `len()` assertion.
4. `py -m pytest tests/test_wled_effect_metadata.py -q` should still
   pass.
5. The frontend picks the change up automatically (no JS / CSS edit
   needed; backend ships the flag + the sort).

**When removing**: same flow in reverse — a WLED patch that introduces
RNG / `beat*`-without-timebase / per-frame `SEGENV.step` accumulation
into a previously-deterministic effect demotes it. Drop the ID from
both `wled_deterministic.py` and the pin test; update the catalogue's
table to move the effect from "✓" to "⚠ Looks deterministic but is
not" with the new failure mode.

The full step-by-step workflow (including the rationale, the
deterministic criteria, and the failure modes) lives in the module
docstring of `wled_deterministic.py` itself — anyone editing the file
sees it immediately.

## Smoke-testing your change

Before opening a PR:

1. `py -m pytest -q` — full suite must pass.
2. `node --check racelink/static/racelink.js` and
   `node --check racelink/static/scenes.js` if you touched JS.
3. `py -m pytest tests/test_no_german_in_ui.py` — confirms no
   accidental German strings in operator-facing UI.
4. `py -m pytest tests/test_proto_header_drift.py` — if you
   touched `racelink_proto.h`.
5. `py -m pytest tests/test_exception_hygiene.py` — confirms every
   `except Exception` you added is either logged or annotated.

For features the test suite can't fully cover (frontend behaviour,
RF-level interactions), add a manual smoke checklist to your PR
description. The internal engineering ledger contains good
examples — every shipped batch ends with a list of
"open the app, click X, confirm Y" steps.
