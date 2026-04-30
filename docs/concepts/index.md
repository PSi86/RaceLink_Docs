# Concepts

Cross-component user-facing concepts — the bits an operator or
contributor needs to understand before authoring scenes, picking
effects, or reading wire traces.

* [**Opcodes — `OPC_CONTROL`, `OPC_OFFSET`, `OPC_SYNC`**](opcodes.md) —
  pragmatic explanation of the three opcodes operators interact with
  most often: what they do, when to use them, how they compose.
* [**Deterministic effects catalogue**](deterministic-effects.md) —
  which WLED effects render identically across nodes when only
  `strip.timebase` is synced. Prerequisite knowledge for offset-mode
  cascades and ARM-on-SYNC choreographies.

For the bit-level wire format that backs these concepts see
[`reference/wire-protocol.md`](../reference/wire-protocol.md).
For terminology see [`glossary.md`](../glossary.md).
