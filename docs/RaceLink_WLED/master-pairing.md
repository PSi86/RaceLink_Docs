# WLED Master Pairing & MAC Filter

A RaceLink WLED node only acts on packets from **one** gateway at a
time — its *master*. This page explains how a node learns, keeps, and
re-learns its master, why moving a node between networks re-pairs it
automatically, and which options change that behaviour.

> **Audience.** Operators who run more than one gateway (or move nodes
> between gateways), and contributors touching the node-side accept
> path. For the wire-level RF-config opcode see
> [Wire protocol — RF configuration](../reference/wire-protocol.md).

## What "master" means

Every node carries a MAC filter. When it is on (the default), the node
accepts control packets only from the gateway it is currently paired
to — the master. This stops two gateways on overlapping radio settings
from fighting over the same node, and keeps a node on network A from
reacting to a broadcast meant for network B.

Two settings govern the filter, both visible in the node's config:

| Setting | Default | Meaning |
|---|---|---|
| **MAC filter** | **on** | When off, the node accepts packets from any sender (no master concept). When on, the rules below apply. |
| **Master persistence** | **off** | When off, the learned master is forgotten on reboot. When on, the master is restored from flash on the next boot. |

## How a node learns its master

With the filter on, the accept rule is:

* **No master learned yet** → the node accepts only *discovery* and
  *group-assignment* packets (`OPC_DEVICES` / `OPC_SET_GROUP`) from
  **any** gateway. Everything else is ignored. This is the "open to
  pairing" state.
* **Master learned** → the node accepts packets **only** from that
  master. Packets from any other gateway — including discovery — are
  ignored.

A node learns (or re-learns) its master from the sender of an
`OPC_SET_GROUP`. That is why assigning a group is also the pairing
action: the host's discovery → group-assignment sweep both places the
node in a group and binds it to the gateway that ran the sweep.

## Persistence: the stored slot vs the live master

The learned master lives in two places:

* the **live** master — what the filter checks right now;
* a **stored** master slot in flash — independent of the live value.

When **master persistence is off** (the default), a reboot starts the
node with no live master, so it is open to pairing again. The stored
slot is left untouched on disk either way.

When **master persistence is on**, the stored slot is restored into the
live master on boot, so the node comes back paired to the same gateway
without re-discovery. The stored slot is refreshed (pinned to whatever
master is live) at the moment the operator turns persistence on, and
again whenever the node learns a master while persistence is on. The
stored value is never wiped automatically — turning persistence off and
on again re-arms the previously pinned binding.

## Moving a node to another network re-pairs it automatically

Relocating a group to a different network sends the node a new RF
configuration. Applying that configuration is, by definition, moving
the node to a different radio network — the old master does not exist
there. So on an RF-config change the node **disables master
persistence before it reboots**:

1. The node persists the new radio settings.
2. It clears master persistence (the stored slot is left intact).
3. It reboots onto the new settings with **no live master**.
4. On the new network it is open to pairing again, so the target
   gateway's group-assignment binds it as the new master.

The operator sees a brief outage (~5 s) and then the node online on the
target network, paired to the target gateway — no manual *Forget master
MAC* step. See
[Move groups between networks](../RaceLink_Host/multi-network.md#move-groups-between-networks).

## Manual control: Forget master MAC

The **Forget master MAC** option (host WebUI → Node Config) clears the
node's live master immediately, putting it back in the open-to-pairing
state without changing its radio settings. The next discovery from any
gateway can then pair it. Use it when re-homing a node between gateways
on the *same* radio settings; avoid clicking it mid-race, where it
gratuitously un-pairs a working node. Because it only clears the live
master, a node with persistence on will restore the old master on its
next reboot unless it re-pairs first.

## Quick reference

| Situation | Live master after | Re-pair needed? |
|---|---|---|
| Fresh flash | none | yes — first discovery + group assign |
| Reboot, persistence **off** | none | yes |
| Reboot, persistence **on** | restored from flash | no |
| RF-config change (network move) | none (persistence disabled pre-reboot) | no — target gateway re-pairs it |
| *Forget master MAC* | none | yes — next discovery |
