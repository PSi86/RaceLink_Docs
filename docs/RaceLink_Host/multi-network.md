# Multi-Network operator guide

Connect more than one RaceLink gateway to the same host, drive each
on its own LoRa channel, and keep their device sets cleanly
separated. This guide walks the flows an operator interacts with:
creating a network, the bind wizard, RF migration after a channel
change, the per-network reconnect banner, and Channel Scan to
recover stranded devices.

For the underlying wire formats, see
[`reference/wire-protocol.md`](../reference/wire-protocol.md) §
`P_RfConfig` and §`OPC_RF_CONFIG`. For the channel table itself,
see [`concepts/channels.md`](../concepts/channels.md).

## When you'd reach for this

* **Two parallel races, one host.** Each gateway carries its own
  set of devices on a non-overlapping channel; scenes and group
  ops fan out per-network without crossing.
* **Hardware swap.** A failed gateway is replaced with an
  identical one; the new ident_mac re-binds to the existing
  network and you keep the device pairings, group ids, and
  scene history.
* **Channel change.** A frequency planning audit moves the
  whole network to a different channel slot; the migration
  engine pushes the new config to every device first, then
  switches the gateway last.
* **Recover stranded devices.** A botched migration left some
  nodes on an old channel. Channel Scan sweeps the region and
  reports who's listening on which slot.

## Concept refresher

* A **Network** (`RL_Network`) is the operator-visible bundle of
  a name, a `gateway_mac` binding, and an `rf_config`. Groups
  and devices belong to exactly one network at a time. The
  host's v1→v2 migration creates a default network on first
  boot so single-gateway deployments inherit the multi-network
  data model transparently.
* A **Channel** is a named slot in the host's region table
  (max five per region — see
  [`concepts/channels.md`](../concepts/channels.md)). Picking
  a channel for a network resolves to the seven wire-format
  `P_RfConfig` fields.
* **Bind state** per attached gateway: `pending`, `bound`,
  `conflict`, or `unbound`. The bind state machine inspects
  every gateway as it attaches. The bind wizard auto-opens
  for `conflict` / `unbound` only — the broader
  SetupChangeAssistant is operator-triggered (see
  [Reconnect banner](#per-network-reconnect-banner) below).
* **RF state** per attached gateway: `IDLE`, `TX`, `RX_WINDOW`,
  `RX`, `ERROR`, or `UNKNOWN`. Mirrored from the gateway's
  spontaneous `EV_STATE_CHANGED` events. The per-gateway pill
  in the header colour-codes Bind + RF state together (see
  [Per-gateway pills](#per-gateway-pills) below).

## Day-to-day: the Devices page with two gateways

After a successful boot with two gateways attached:

* The **Network filter dropdown** appears above the Groups
  sidebar — only visible at N>1, so single-gateway deployments
  see no UX change. "All Networks" is the default.
* The **Device Table** gains a "Network" column with a
  coloured badge per row (deterministic palette by network id;
  "Track A" is always the same colour across reloads).
* **Hover the badge** for the device's last-known `freq_hz` /
  SF / BW / SyncWord — a quick read of "is this node where the
  network expects it to be".
* **Group filter** still works the same; combined with the
  network filter, the table shows the intersection.

## Create a network

The Network Manager dialog covers CRUD on existing networks.
The flow for creating a fresh network starts from the
**GatewayBindWizard** when an unknown gateway attaches:

1. Plug a previously-unknown gateway into the host's USB port.
2. The wizard auto-opens with state `unbound` once the gateway's
   identity reaches the host (~1–2 s after plug). It shows the
   `ident_mac` and the RF settings the gateway is broadcasting
   on.
3. Pick **"Create a new network for this gateway"**. The form
   inline:
     * **Name** — free-text label ("Pit-Lane", "Track A", …).
     * **Region** — `EU868` / `US915` / whatever the host's
       channel table carries.
4. The network is created with `rf_config` seeded from the
   gateway's reported settings, the transport is bound to it,
   and the SSE `gateway_bound` event closes the dialog.

The other unbound-flow option, **"Bind to an existing
network"**, is the hardware-swap path — pick an existing
network and the new ident_mac takes over its binding. If the
existing network's persisted `rf_config` disagrees with the
new gateway's NVS, the bind wizard immediately re-opens in
**`conflict`** mode so you can resolve.

## Conflict resolution

State `conflict` means: the gateway is bound to a known
network, but its NVS RF settings disagree with what the
network expects. The wizard renders a per-field diff
("Host expects" vs "Gateway reports") and asks for one of:

* **Accept the gateway's settings.** Updates the network
  record to match the gateway. No migration, no device
  reboots. Use this when you flashed or re-tuned the gateway
  intentionally.
* **Push the host's settings (migrate).** Runs the four-phase
  RF migration: push `OPC_RF_CONFIG` to every device, then
  persist-switch the gateway, then verify via discovery. See
  [Migration](#rf-migration) below.

The wizard stays open while a migration is in flight (the
state stays at `conflict` with `migration_pending=true` until
the engine flips it back to `bound`).

## RF migration

Three operator paths trigger an RF migration; they all run the
same four-phase TaskManager job:

* **Bind wizard → "Push the host's settings"** when the gateway
  comes back in a `conflict` state. The wizard stays open and
  switches to a `migrating` step that subscribes to the task's
  live phase / index / total / current MAC and shows a progress
  bar. When the task completes, the wizard flips to `done` (or
  `error`) with a Close button.
* **NetworkManagerDialog → edit channel → Save.** If the new RF
  config differs from what the gateway is actually broadcasting
  (`gateways.get(mac).rf_config_actual`), a confirmation prompt
  asks whether to push to the gateway. Choosing **Migrate**
  kicks the same TaskManager job; progress shows in the master
  bar's task line.
* **NetworkManagerDialog → "Custom RF" → Save.** Same flow as
  the channel edit, just with raw P_RfConfig values from the
  channel-table's "unchanged" option.

A single migration job at a time — the host returns `409 busy`
if another long-running task (firmware update, channel scan)
is already in flight.

The four phases:

1. **Pre-check** — list every device on the network. Skip
   those already on the target config (their
   `last_known_rf_config` matches). Optionally skip offline
   devices; the operator can override that from the wizard.
2. **Phase 1 — Device push.** For each remaining device the
   host sends `OPC_RF_CONFIG(target)` via the current
   (old-config) gateway. Each device validates, persists to
   NVS, ACKs, then reboots ~50 ms later onto the new settings.
   They become invisible to the current gateway — expected.
3. **Phase 2 — Gateway switch.** After every device push
   completes (or the operator overrides on a partial), the
   host sends `GW_CMD_SET_RF_CONFIG(target, persist=true)`.
   The gateway writes NVS + reboots onto the new settings.
   The host's reconnect machinery re-opens the USB device
   automatically.
4. **Phase 3 — Verification.** Post-reboot discovery on the
   new channel. Devices that respond have their
   `last_known_rf_config` updated. Devices that don't are
   marked **stranded** — see Channel Scan below.

A successful migration flips the bind state back to `bound`
on the SSE channel; the wizard closes itself.

## Channel Scan (stranded-device recovery)

Open with the 🔎 wrench-menu button in the header (or via the
SetupChangeAssistant's per-row "Run channel scan" action).

1. Pick the gateway to scan from (single-gateway deployments
   default to the only one).
2. Pick the region. Defaults from the chosen gateway's network.
3. Tick the channels to walk; defaults to every channel in
   the region.
4. Set the per-channel dwell. The default 2 s catches the
   discovery-default reply window with margin.
5. Hit **Start scan**. The gateway volatile-switches onto each
   channel (no NVS write), broadcasts `OPC_DEVICES`, dwells,
   then moves on. After every channel the gateway is restored
   to its pre-scan settings via another volatile switch.

The result panel shows a per-channel table:

* **Known** devices: name + MAC + which network they
  currently belong to. Their `last_known_rf_config` is updated
  in-place so a follow-up migration can skip them.
* **Unknown** devices: MAC only, tagged amber. These are nodes
  the host's repo doesn't know about; you'd typically run the
  discovery dialog with the scanned channel as the active one,
  or migrate them in via a temporary network.

The scan is read-only at the device level — it doesn't push
any settings, only observes. Stranded devices stay on their
own NVS-persisted channels until you explicitly migrate them.

## Per-gateway pills

The header's master bar carries one pill per attached gateway
instead of the pre-multi-network single master pill. Each pill
combines the two state machines via colour:

| Bind state | RF state (when `bound`) | Colour | Meaning |
|---|---|---|---|
| `bound` | `IDLE` | green | Ready for next send. |
| `bound` | `TX` | blue | Transmitting on the LoRa wire. |
| `bound` | `RX` / `RX_WINDOW` | warm yellow | RX window open waiting for a node reply. |
| `bound` | `ERROR` | red | Gateway reported a fault. |
| `bound` | `UNKNOWN` | grey | No spontaneous state event yet — click ↻ to query. |
| `conflict` | — | amber border | Bind wizard wanted: RF config disagrees with the network. |
| `unbound` | — | red border | No matching network — operator must create or rebind. |
| `pending` | — | grey | Mid-handshake, or last GET_RF_CONFIG didn't reply. |

The label inside each pill is the network name (`Pit-Lane`,
`Default`, …) plus the last 4 hex of the gateway's `ident_mac`
to disambiguate two gateways on the same network. Hover reveals
the full ident_mac, bind state, RF state and any conflict
fields.

The **↻** button next to the pills fans a `GW_CMD_STATE_REQUEST`
out to every attached gateway in parallel and refreshes every
pill in one round-trip. Used right after a reconnect when a
pill is still grey but you want confirmation it's actually
back on the wire.

A `⚠ Pair…` button appears in the header whenever any
gateway is in `conflict` or `unbound` — clicking it re-opens
the bind wizard for the affected gateway without needing a
USB reconnect.

## Per-network reconnect banner

When a gateway disappears mid-session (USB cable yanked,
adapter glitch, intentional unplug), only that one transport
drops out — sibling gateways stay fully online and keep their
device traffic flowing.

What the operator sees:

1. The disappearing gateway's per-gateway pill vanishes from
   the master bar.
2. A red **reconnect banner** appears below the header listing
   every persisted network whose `gateway_mac` is not currently
   attached, with a per-row live countdown:

       ⚠ Pit-Lane (9C:13:9E:9E:1C:10) — retry in 4s     [Cancel]
       ⚠ Default  (48:CA:43:3C:D4:E0) — retry in 2s     [Cancel]

       [Open Pair Assistant]   [Cancel all]

3. The host's background **reconnect tracker** polls every 5s
   for the missing MACs. The probe enumerates only ports that
   are NOT currently in use, so no healthy transport is ever
   disturbed.
4. As soon as the operator plugs the gateway back in, the next
   poll tick discovers it, attaches it, sends a state-request
   to seed the pill colour, and removes the row from the banner.

**Cancel** drops a single MAC out of the tracker until the
operator opts back in. Useful for an intentionally-retired
gateway you don't want to keep seeing in the banner — the
network row stays in the database, just isn't being polled
for. The `Open Pair Assistant` button reaches the broader
diff view (see below).

**Reconnect on host restart.** When the host process itself
restarts, both gateways attach during the normal `discoverPort`
boot path; the tracker only fires if a persisted network has
no matching transport after that boot.

## Setup-Change Assistant

The assistant catalogues every operator-actionable diff across
the networks + gateways + devices repos. It used to auto-open
once per session — that was disabled to stop dialog-spam during
USB flicker. The assistant is now reached via:

* The reconnect-banner's **Open Pair Assistant** button (covers
  the missing-transport case),
* The header's `⚠ Pair…` button (covers `conflict` / `unbound`),
* The host-settings menu (operator-driven inspection at any time).

Surfaced diff categories:

* **Gateway not attached** — a configured network's
  `gateway_mac` isn't currently visible on USB. The reconnect
  tracker is already polling for it; the assistant offers
  per-MAC cancel + a global "Re-discover now" trigger that
  forces an immediate enumeration (useful when you've just
  plugged the cable in and don't want to wait for the next
  5s tick).
* **Unknown gateway** — an attached gateway whose ident_mac
  doesn't match any network. Open the bind wizard.
* **RF mismatch** — bind state is `conflict`. Open the bind
  wizard.
* **Devices on stale RF** — at least one device's
  `last_known_rf_config` disagrees with the bound network's.
  Run a Channel Scan or trigger a migration to bring them in
  line.

Each row has a one-click follow-up button that hands off to
the right wizard.

## Boundary enforcement

A scene action or bulk regroup that would mix devices from
different networks is **rejected by the host** with HTTP 400:

* The **MultiGroupPickerDialog** in the scene editor anchors
  on the first selected group's network; groups on other
  networks get a disabled checkbox + an "other net" pill.
* The **bulk regroup** endpoint
  (`POST /api/devices/update-meta` with a `groupId`) runs the
  same validator server-side before the TaskManager job
  kicks off — the WebUI shows the structured error in a
  toast.
* Moving devices into the **Unconfigured** group (id 0) is
  always allowed; it's the cross-network sink.

The validator lives in
`RaceLink_Host/racelink/domain/network_boundary.py`. Two
boundary violations it detects:

* `devices_span_multiple_networks` — the operator selected
  devices that don't share a network. Move them one network at
  a time.
* `group_network_mismatch` — the devices agree on a network,
  but the target group is somewhere else. Migrate the devices
  to the target network first, then re-run the regroup.

## Single-gateway operators

If you only have one gateway attached, the Stage-2/3 multi-network
groundwork is transparent:

* The default network created by the v1→v2 migration absorbs
  every device and group automatically; the badge in the
  Device Table reads "Default".
* The Network filter dropdown stays hidden (the sidebar
  doesn't render it at N=1).
* The bind wizard auto-pops on first attach (state `unbound`
  if there's no `gateway_mac` yet; otherwise immediately
  `bound`). The Stage-2 single-transport + unbound-network
  auto-bind handles this silently — you may never see the
  wizard.

## See also

* [`concepts/channels.md`](../concepts/channels.md) — the
  shipped region/channel table.
* [`reference/wire-protocol.md`](../reference/wire-protocol.md)
  §`P_RfConfig`, §`OPC_RF_CONFIG`, §`EV_RF_CHANGED`,
  §`GW_CMD_*_RF_CONFIG`.
* [`RaceLink_Host/architecture.md`](architecture.md)
  §"Multi-Transport runtime" for the host-side data flow
  (transport list, per-network PendingMatcherRegistry,
  bind-state machine).
* [`troubleshooting.md`](../troubleshooting.md) — common
  multi-network operator failure modes (gateway stuck on
  PORT_BUSY, migration aborted before Phase 2, …).
