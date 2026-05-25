# Reference

Formal specifications — vocabulary, wire format, REST endpoints, event
channels, file formats. The byte-level / interface-level truth that
backs the narrative docs.

* [**Glossary**](../glossary.md) — canonical terminology used across
  every other doc.
* [**Wire protocol**](wire-protocol.md) — packet headers, opcode
  bodies, per-direction rules, framing, gateway state machine.
* [**Opcodes (CONTROL / OFFSET / SYNC)**](opcodes.md) —
  pragmatic "when do I use which opcode?" explanation that sits
  alongside the wire-level spec.
* [**Region & Channels**](channels.md) — shipped EU868 / US915
  channel tables, table-shape schema, separation rule, compliance
  disclaimer.
* [**Deterministic WLED effects**](deterministic-effects.md) —
  which effects render identically across nodes when only the
  timebase is synced (prerequisite for offset mode).
* [**Broadcast ruleset**](broadcast-ruleset.md) — two-stage filter
  pipeline (wire recv3 → per-opcode groupId) and per-opcode accept
  matrix.
* [**Wire timing**](wire-timing.md) — per-packet wall-clock breakdown
  from host enqueue through USB to RF transmit.
* [**Scene file format**](scene-format.md) — on-disk shape of
  `scenes.json` (action kinds, params, flags-overrides).
* [**Web API**](web-api.md) — REST endpoints exposed by the host
  (consumed by the WebUI; sometimes by external scripts).
* [**SSE channels & state scopes**](sse-channels.md) — the
  Server-Sent-Events stream the WebUI subscribes to, plus the
  state-scope tokens that determine which UI elements refresh.
