# Reply Matching — `PendingMatcher`

The host owns the *"is this inbound frame the reply I'm waiting for?"*
decision. The Gateway firmware sits in **Continuous RX** and forwards
every matching frame over USB; the host's matcher layer routes each
inbound event to whichever caller registered an expectation that
accepts it.

This page documents the unified mechanism shipped under Option D
(2026-05). The earlier split — a `PendingRequestRegistry` for unicast
1-reply waits next to an `add_listener`-backed collector for N-reply
broadcasts — has been retired.

## Why one mechanism

Both legacy paths were doing the same thing in different words: *wait
for matching RX events until N collected or timeout*. They differed
only in their lookup strategy and their wait loop, not in what
information they needed from the caller. Folding them together:

* Removes the *"choose the right primitive"* burden when adding new
  request/response paths.
* Eliminates a class of misleading log lines
  (`MISS opc=ACK ... pending_keys=0`) that appeared on every legitimate
  stream / discovery / status ACK because the registry never knew the
  collector had a parallel listener for it.
* Halves the conceptual surface of `racelink/services/pending_requests.py`
  (one dataclass + one registry, one wait loop).

## Components

| Type | Lives in | Responsibility |
|---|---|---|
| `PendingMatcher` | `racelink/services/pending_requests.py` | Per-call expectation: filters (sender / opcode / ack_of / discriminator), collection semantics (count / idle / max), and a `threading.Condition` for the waiter. |
| `PendingMatcherRegistry` | same | Thread-safe routing of inbound events to matching matchers. Unicast bucket (O(1)) plus a small broadcast list (linear scan). |
| `GatewayService.send_and_match(send_fn, matcher)` | `racelink/services/gateway_service.py` | Public primitive: register the matcher, invoke `send_fn`, block on the matcher's condition until done / idle / ceiling, always cancel in the `finally`. |
| `GatewayService.send_and_wait_with_retries(...)` | same | Thin retry wrapper on top of `send_and_match` for unicast paths that need bounded retransmits. |

## Matcher fields

A `PendingMatcher` carries four kinds of state:

### Filters (what counts as a match)

| Field | Meaning | Wildcard value |
|---|---|---|
| `sender_filter` | Set of accepted sender-last3 addresses (3-byte tail of the device MAC). Singleton sets enable the fast-bucket lookup. | `None` — any sender |
| `expected_opcode` | For specific-reply paths (`GET_CONFIG_REPLY`, `STATUS_REPLY`, `IDENTIFY_REPLY`). | `None` — any opcode |
| `expected_ack_of` | For ACK paths: the original request's opcode7 that an `OPC_ACK` echoes back via the `ack_of` field. Implies `opc == OPC_ACK`. | `None` — not an ACK waiter |
| `discriminator_field` / `discriminator_value` | Final equality gate against an arbitrary parsed-event field. Used today for `option` (`GET_CONFIG_REPLY` per-option routing) and `reply` (`IDENTIFY_REPLY` / `STATUS_REPLY` string markers). | `None` — no discriminator |

Filters are AND-combined: every set field must hold. Unset fields are
wildcard. A fully wildcard matcher accepts every event — useful for a
"catch the first thing that comes in" test, less so in production.

Exactly one of `expected_opcode` and `expected_ack_of` should be set;
the registry's fast-bucket key uses whichever the matcher advertises.

### Collection semantics (when to stop)

| Field | Meaning |
|---|---|
| `expected_count` | Stop after collecting this many matching events (`reason="count"`). For unicast 1-reply this is 1; for an N-device group ACK it equals `len(target_last3)`; for open-ended discovery sweeps a large sentinel (e.g. `2**31`) disables count-based exit and relies on idle/max only. |
| `idle_timeout_s` | Once the first match has arrived, exit if no further match shows up for this many seconds (`reason="idle"`). `0.0` disables — the matcher uses `max_timeout_s` only (legacy unicast semantics). |
| `max_timeout_s` | Hard ceiling from `register()`. Exits as `"max_timeout"` if at least one match arrived, `"no_reply"` if none. |

### Mutable state (registry-managed)

| Field | Notes |
|---|---|
| `collected` | List of matched events in arrival order. Read it after `wait()` returns. |
| `last_match_ts` | `time.monotonic()` of the most recent match — drives the idle window. |
| `_cond` / `_done` | Internal `threading.Condition` and flag. The registry signals on each match; the wait loop re-checks idle/max-timeout each time it wakes. |

## Lookup strategy

`PendingMatcherRegistry.try_match(ev)` walks two lookup paths per event:

1. **Fast unicast bucket** — for matchers with exactly one sender in
   `sender_filter` and a concrete `expected_opcode` or
   `expected_ack_of`. Keyed by `(sender_last3, opcode_or_ack_of)` and
   queried in O(1).
2. **Broadcast list** — every other matcher (wildcard sender, multi-
   sender set, wildcard opcode). Scanned linearly. Production has at
   most a handful of outstanding ops at any time, so the scan is
   negligible.

The first matcher whose full `matches(ev)` returns `True` consumes the
event (appends, signals its condition) and `try_match` returns it. We
do not fan out to multiple matchers on the same event — this preserves
the historical "ACK wakes exactly one waiter" semantics.

## Wait loop

`PendingMatcher.wait()` (called by `send_and_match`) implements a
three-phase timeout:

```
                                    +----------------+
register()  →  send_fn()  →         |   wait loop    |
                                    +----------------+
                                            │
                       ┌────────────────────┴────────────────────┐
                       │                                         │
                   first match?                         hard ceiling reached?
                       │                                         │
                 ┌─────┴─────┐                            ┌──────┴──────┐
                 no          yes                          0 collected   ≥1 collected
                 │           │                              │              │
        hard ceiling     start idle timer                no_reply      max_timeout
                 │       (last_match_ts + idle_s)
              no_reply       │
                       ┌─────┴─────┐
                  count reached?   another match arrives → reset idle window
                       │
                     count
```

`reason="count"` is the success path the unicast caller expects.
`reason="idle"` and `reason="max_timeout"` both mean "we got some
replies but the operation ended on a timeout"; the caller decides
whether to treat the partial result as success.

## Typical matcher constructions

### Unicast OPC_CONFIG → ACK

```python
matcher = PendingMatcher(
    sender_filter=frozenset({recv3_bytes}),
    expected_ack_of=int(LP.OPC_CONFIG) & 0x7F,
    expected_count=1,
    idle_timeout_s=0.0,
    max_timeout_s=rf_timing.UNICAST_ATTEMPT_TIMEOUT_S,
)
```

Used internally by `send_and_wait_with_retries`; callers normally use
that helper instead of constructing the matcher by hand.

### Unicast OPC_GET_CONFIG → GET_CONFIG_REPLY with option discriminator

```python
matcher = PendingMatcher(
    sender_filter=frozenset({recv3_bytes}),
    expected_opcode=int(LP.OPC_GET_CONFIG) & 0x7F,
    discriminator_field="option",
    discriminator_value=opt_byte,
    expected_count=1,
    max_timeout_s=rf_timing.UNICAST_ATTEMPT_TIMEOUT_S,
)
```

Two concurrent `read_config()` calls on the same device but for
different options route their replies to the right caller because the
codec sets `ev["option"]` on the parsed reply and the matcher checks
it.

### Group OPC_STREAM → N ACKs

```python
matcher = PendingMatcher(
    sender_filter=frozenset(target_last3_set),
    expected_ack_of=int(LP.OPC_STREAM) & 0x7F,
    expected_count=len(target_last3_set),
    idle_timeout_s=rf_timing.COLLECT_IDLE_TIMEOUT_S,
    max_timeout_s=...,  # scaled by target count
)
```

The startblock service uses this per retry attempt, shrinking
`sender_filter` to the still-unacked subset on each retry so a flaky
device cannot waste budget on already-acked targets.

### Wildcard OPC_DEVICES discovery

```python
matcher = PendingMatcher(
    sender_filter=None,                                  # any device may answer
    expected_opcode=int(LP.OPC_DEVICES) & 0x7F,
    discriminator_field="reply",
    discriminator_value="IDENTIFY_REPLY",
    expected_count=2**31,                                # idle/max only
    idle_timeout_s=rf_timing.COLLECT_IDLE_TIMEOUT_S,
    max_timeout_s=rf_timing.COLLECT_MAX_CEILING_S,
)
```

Discovery cannot know how many devices will reply, so the count gate is
effectively disabled and the matcher terminates when the last
late-comer goes quiet for the idle window.

## Diagnostic logging

The registry emits debug-level messages on three events:

* `matcher.register` — sender filter, opcode/ack_of, expected count,
  idle/max timeouts, total outstanding matchers.
* `matcher.cancel` — collected count, done flag, elapsed time.
* `matcher.try_match HIT` — when an event is consumed.

It also emits a `matcher.try_match NO_MATCH` line — but **only** when at
least one matcher was a candidate (same bucket key) yet its full
`matches()` check rejected the event. That is the genuinely
diagnostic case: an ACK arrived with the right sender + opcode but the
discriminator disagreed (e.g. wrong `option` byte), suggesting a race
or a codec bug. The plain *"no waiter cared about this event"* path
no longer logs — that fires on every unsolicited STATUS_REPLY or
untracked broadcast and would only flood the log.

## Threading

* The registry's internal `_lock` is held only for bucket lookups and
  membership changes — never across `matcher.matches(ev)` or
  `cond.notify_all()`.
* Each matcher owns its own `Condition`, so two matchers can be
  signalled in parallel without contending on a single registry-level
  condition.
* `send_and_match` registers the matcher *before* invoking `send_fn`.
  The Gateway's RX reader thread cannot deliver a reply before
  `send_fn` returns (the reply is causally posterior to the request),
  so the registration-then-send ordering is sufficient — there is no
  separate "drain stale events" race window to defend against.

## Locking interaction with the state repository

The rule on
[Architecture → "Never hold `state_repository.lock` across RF I/O"](architecture.md)
applies unchanged. `send_and_match` is RF I/O; callers must release
the state lock before invoking it.

## Migration history (for context)

The unified matcher landed in three reviewable phases under the plan
file `aktuell-teste-ich-den-lazy-willow.md`:

1. **Phase 1** introduced `PendingMatcher` / `PendingMatcherRegistry` /
   `send_and_match` and turned the old `send_and_wait_for_reply` and
   `send_and_collect` into thin adapters. Every test stayed green
   without modification.
2. **Phase 2** migrated each call site (`config_service`,
   `gateway_service.send_stream`, `discovery_service`, `status_service`)
   to build a structured matcher and call `send_and_match` directly.
   Adapters remained in place for any code path not yet touched.
3. **Phase 3** removed the adapters, retired the `custom_pred` closure
   hook from `PendingMatcher`, and updated the test suite to construct
   matchers directly. `send_and_wait_with_retries` was kept because it
   adds genuine retry semantics on top of the primitive — it is now a
   short retry loop over `send_and_match`, not an alias.

There are no compatibility shims left. New code should build a
`PendingMatcher` and call `send_and_match` (or use
`send_and_wait_with_retries` for unicast with retries).
