# Gateway Opcode Forwarding

The gateway bridges the host's USB-CDC link to the LoRa radio. It is
**not** a transparent byte pump in the host → node (M2N) direction:
each opcode the host can send has an explicit case in the gateway
firmware. This page documents that contract so a new wire opcode is
added in both places it needs to be.

> **Audience.** Contributors adding or changing a wire opcode. For the
> opcode catalogue and body layouts see
> [Wire protocol](../reference/wire-protocol.md); for cross-repo
> coordination rules see [Contributing](../contributing.md).

## Host → node (M2N): explicit per-opcode switch

When the gateway receives a framed M2N command over USB it dispatches
on the opcode through a `switch` in the firmware's main loop. Each
supported opcode has its own case that validates the body length,
rebuilds the LoRa frame, and schedules the transmit. The opcodes with
a forwarder case today:

`OPC_DEVICES`, `OPC_SET_GROUP`, `OPC_STATUS`, `OPC_PRESET`,
`OPC_CONFIG`, `OPC_GET_CONFIG`, `OPC_RF_CONFIG`, `OPC_GET_RF_CONFIG`,
`OPC_SYNC`, `OPC_STREAM`, `OPC_CONTROL`, `OPC_OFFSET`, `OPC_HEADLESS`,
`OPC_INDICATE`.

An opcode **without** a case falls through the switch silently: no LoRa
transmit, and — critically — **no `EV_TX_DONE` and no
`EV_TX_REJECTED`** back to the host. The host's send path waits for one
of those outcome events, so a missing case surfaces as a ~2-second
*TX outcome timeout* on the host with no other clue. (This is exactly
how the RF-config opcodes regressed before the 2026-05-27 release: the
opcodes existed in the shared protocol header and the host sent them,
but the gateway had no forwarder case, so every `OPC_RF_CONFIG` push
timed out and the node never changed channel.)

## Node → host (N2M): generic forwarding

Replies travelling the other way — `OPC_ACK`, `IDENTIFY_REPLY`,
`STATUS_REPLY`, `GET_CONFIG_REPLY`, the `OPC_GET_RF_CONFIG` read-back,
and so on — do **not** need a per-opcode case. The gateway forwards
every received N2M frame to USB through a single generic path. Adding a
new reply type therefore only touches the host-side parser, not the
gateway.

## Contract: adding a new wire opcode

A new host → node opcode must be added in **both** places, in the same
coordinated change set (see
[Contributing — cross-repo coordination](../contributing.md)):

1. The shared protocol header (opcode constant + body struct + the
   rules table), shipped to the host, the gateway, and the WLED node.
2. A forwarder case in the gateway's M2N switch — even if the body is
   opaque to the gateway, it still has to rebuild the frame and
   schedule the send so the host gets its `EV_TX_DONE`.

Skipping step 2 produces a host that "sends" the opcode with no error
at the host layer but a silent TX timeout on every attempt — the
hardest class of multi-repo bug to spot, because the host code and the
protocol header both look correct in isolation.

## Why the gateway isn't transparent

Keeping an explicit case per opcode lets the gateway enforce per-opcode
framing rules (body-length checks, broadcast-vs-unicast gating) close to
the radio, and keeps its transmit scheduler aware of what it is sending
(e.g. `OPC_SYNC` autosync origination, `OPC_STREAM` fragmentation). A
blind pass-through would move that responsibility onto every caller and
lose the single point where malformed frames are rejected before they
reach the air.
