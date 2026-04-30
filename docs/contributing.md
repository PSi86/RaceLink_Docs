# Contributing to RaceLink

Conventions and PR rules that apply across the four RaceLink
repositories. Component-specific deep-dives live in the per-component
docs (see the *See also* links at the end).

## Repositories and where to push code

| Component | Repository | Open PRs against |
|---|---|---|
| Host runtime, WebUI, services | `RaceLink_Host` | the appropriate feature branch (most work today lives on `wled-advanced-control`) |
| Gateway firmware | `RaceLink_Gateway` | `continous-rx-mode` |
| WLED usermod + build profiles | `RaceLink_WLED` | `auto-identify` |
| RotorHazard adapter | `RaceLink_RH-plugin` | `adapt-host-changes` |

If a change touches the wire format, it touches all three of host,
gateway and WLED — see [`RaceLink_Host/developer-guide.md`](RaceLink_Host/developer-guide.md)
§"Adding a new wire opcode".

## Smoke tests before opening a PR

```bash
# All host PRs:
py -m pytest -q                                           # full suite
py -m pytest tests/test_no_german_in_ui.py                # no DE strings in operator UI
py -m pytest tests/test_exception_hygiene.py              # every `except Exception` is logged or annotated

# Touched racelink_proto.h?
py -m pytest tests/test_proto_header_drift.py             # three-way header parity

# Touched JS?
node --check racelink/static/racelink.js
node --check racelink/static/scenes.js
```

For features the test suite cannot fully cover (frontend behaviour,
RF interactions), include a manual smoke checklist in your PR
description.

## Coding conventions

### Boolean send contract

Every `send_*` method on `control_service` returns `bool`:

* `True` — the transport accepted the frame for queueing.
* `False` — transport not ready / no target / nothing went out.

```python
def send_my_new_opc(self, ...) -> bool:
    transport = self._require_transport("sendMyNewOpc")
    if transport is None:
        return False
    transport.send_my_new_opc(...)
    return True
```

A historical class of silent-success bugs traced back to methods
that returned `None` instead. New send-style methods follow the
contract above to prevent recurrence.

### Exception hygiene

`tests/test_exception_hygiene.py` requires every `except Exception`
block to either log, re-raise, or carry a `# swallow-ok: <reason>`
comment. The reason should be substantive — "best-effort fallback;
caller proceeds with safe default" is the bare minimum, but a
one-line *why* is better.

If you are tempted to swallow at an RF / persistence boundary,
prefer `logger.warning(..., exc_info=True)` over a silent pass.

### Locking rule

Anything that mutates shared state uses an existing lock
(`state_repository.lock`, `_pending_config_lock`,
`_pending_expect_lock`, `_tx_lock`). If you add a shared field, add a
matching lock and pin it with a regression test in
`tests/test_state_concurrency.py`.

**Never hold `state_repository.lock` across RF I/O.** This deadlocks
the gateway reader thread. Reference pattern:
`_apply_device_meta_updates` in `racelink/web/api.py`. See
[`RaceLink_Host/architecture.md`](RaceLink_Host/architecture.md) §"Locking Rule".

### Thread naming

Always pass `name="rl-<purpose>"` when creating a thread. This is
a project convention. New threads without a name make
`threading.enumerate()` and py-spy traces illegible.

### No German in operator-facing UI

`tests/test_no_german_in_ui.py` is a CI gate. Use English everywhere
in operator-visible text. Internal comments can be any language.

### Effect vs. preset terminology

Use **preset** for "WLED preset slot" (a numeric ID on a node).
Use **effect** for "WLED segment effect parameters" (mode + speed +
intensity + sliders + palette + colours). The terminology cleanup
plan renamed several legacy "effect_*" symbols that actually
referred to presets; check
[`glossary.md`](glossary.md) before introducing new symbols.

## PR description template

A good PR description includes:

* **What changed and why.** Two sentences are usually enough.
* **Wire-format impact.** "No wire change" / "Adds opcode X (bumped
  `PROTO_VER_MINOR`)" / "Reshapes struct Y (bumped
  `PROTO_VER_MAJOR`)".
* **Test impact.** New tests added; tests modified; manual smoke
  steps if needed.
* **Audit-trail note.** If the change is significant, the maintainer
  may append a note to the internal engineering ledger so the
  rationale is captured for future reference.

## Cross-repo coordination

A wire-format change is a *coordinated* PR across host + gateway +
WLED. Sequence:

1. Open a host PR with the new `racelink_proto.h` (and the matching
   transport / service additions).
2. Open the matching gateway PR using the same byte-identical
   `racelink_proto.h`.
3. Open the matching WLED PR ditto.
4. Land them in the same release window. The proto-drift test will
   start failing as soon as the headers diverge.

## See also

* [`RaceLink_Host/developer-guide.md`](RaceLink_Host/developer-guide.md) — the
  authoritative checklist set for "I want to add X" tasks (action,
  opcode, service, task workflow, WLED metadata).
* [`RaceLink_Host/architecture.md`](RaceLink_Host/architecture.md) — package layout,
  threading model, locks.
* [`RaceLink_Host/ui-conventions.md`](RaceLink_Host/ui-conventions.md) —
  button vocabulary, toast / confirm-dialog conventions.
* [`versioning.md`](versioning.md) — version-bumping rules.
