# Reference

Formal specifications — wire format, REST endpoints, event channels,
file formats. The byte-level / interface-level truth that backs the
narrative docs.

* [**Wire protocol**](wire-protocol.md) — packet headers, opcode
  bodies, per-direction rules, framing, gateway state machine.
* [**Web API**](web-api.md) — REST endpoints exposed by the host
  (consumed by the WebUI; sometimes by external scripts).
* [**SSE channels & state scopes**](sse-channels.md) — the
  Server-Sent-Events stream the WebUI subscribes to, plus the
  state-scope tokens that determine which UI elements refresh.
* [**Scene file format**](scene-format.md) — on-disk shape of
  `scenes.json` (action kinds, params, flags-overrides).

For pragmatic ("how do I use this") explanations rather than wire
truth, see [`concepts/`](../concepts/index.md).
