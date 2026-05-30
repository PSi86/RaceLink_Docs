# Changelog

A consolidated timeline of operator- and contributor-visible changes
across the four RaceLink repositories. Format inspired by
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) — each
release is grouped into **Added** / **Changed** / **Fixed** /
**Removed** / **Breaking** sections.

> **Source of truth.** Each repository maintains its own GitHub
> releases page (see [Useful queries](#useful-queries) below); this
> changelog is a curated cross-repo summary for operators and
> contributors. Engineering detail (commit SHAs, test counts,
> internal symbol renames, stage-by-stage commit breakdowns) lives
> in the maintainer-internal engineering ledger and never reaches
> this file.

## 2026-05-27 — Network-move end-to-end + parallel multi-gateway status

The per-group network move shipped its UI in the previous release, but
several layers had to line up before a move actually relocated a node.
This release closes those gaps so moving a group to another network
works without any manual master-clear or Channel-Scan, and makes the
multi-gateway status poll fast.

### Fixed

* **Moving a group to another network now completes end-to-end.** From
  the operator's side: after the move the node briefly reboots (~5 s
  offline), comes up on the target network's radio settings, and
  re-binds to the target gateway on its own — no manual re-pair. Under
  the hood three layers were fixed: the gateway firmware now forwards
  the RF-config opcodes it previously dropped silently; the WLED node
  clears its master persistence on an RF change so it accepts the new
  gateway; and the host marks the device offline during the reboot and
  routes the follow-up group assignment through the target gateway
  instead of the old one. See
  [WLED master pairing](RaceLink_WLED/master-pairing.md).
* **Node config / stream / RF read-back reach the right gateway.** On a
  multi-gateway setup, per-device actions like *WLAN AP open* (Node
  Config), preset streaming, and the RF read-back used by the
  Setup-Change-Assistant were always sent through the first gateway and
  timed out for any device on a second gateway. They now route to the
  gateway that owns the device's network.
* **A moved node is no longer shown online by mistake.** A status reply
  arriving via a gateway that doesn't own the device's network no
  longer flips the device to "online" — the operator sees the true
  state during a migration instead of a misleading green dot.
* **Scene network scope is honored on a draft Run.** Running an
  unsaved scene from the editor now respects the scene's network scope.
  Previously the draft Run fell back to auto-mode and a broadcast
  action could reach every network even when the scope pinned one.

### Changed

* **`Get Status (all)` polls every gateway in parallel.** Each gateway
  is queried on its own with an independent reply collector, so the
  wall-clock cost is bounded by the slowest single gateway's reply
  window rather than the sum across gateways. The result is identical,
  just faster, and a device on a second gateway no longer needs a
  per-device retry pass.
* **Pair Assistant uses the region + channel picker.** The "migrate to
  new settings" (B) and "align gateway to devices" (C) flows now pick a
  **Region** and **Channel** from the shipped channel table — the same
  picker the Network Manager uses — instead of raw frequency / spreading
  factor / bandwidth number fields. See
  [Region & Channels](reference/channels.md).
* **Scene editor footer is pinned.** The cost-estimator **Total** badge
  and the Delete / Duplicate / Save / Run buttons stay fixed at the
  bottom of the editor, so they're reachable without scrolling past a
  long action list. The Pair Assistant dialog is also wider so the
  region + channel dropdowns fit without a horizontal scrollbar.

### Wire protocol

Unchanged. `OPC_RF_CONFIG` carries the same 12-byte body; its node-side
behaviour was extended to also clear master persistence before the
reboot (see
[Wire protocol — RF configuration](reference/wire-protocol.md) and
[WLED master pairing](RaceLink_WLED/master-pairing.md)).

---

## 2026-05-27 — BroadcastTarget + scene-derived sync scope

### Changed

* **SYNC fires only on involved networks.** A scene whose non-sync
  actions resolve to a strict subset of networks (e.g. target group
  on network A only) now scopes its `sync` action to that subset.
  Uninvolved networks see no SYNC traffic and cannot accidentally
  fire pre-loaded `arm_on_sync` effects.
* **Multi-gateway SYNC is fast again.** Two-gateway setups were
  measured ~104 ms `OPC_SYNC` USB round-trip before this release;
  the threaded fan-out brings it back to ~52 ms, bounded by the
  slowest gateway's air time rather than the sum. Three or more
  gateways scale the same way.
* **Sync-only scenes fall back to all-attached.** Scenes containing
  only `sync` / `delay` actions can't derive a scope from action
  targets — they keep the conservative pre-refactor "fire on every
  attached gateway" behaviour. A deprecation warning is logged so
  the fallback can be tightened to an error in a future release.

### Added — operator-pinned `scene.network_scope` (follow-up iteration)

* **Scope chip in the scene editor header.** Click to open an Auto
  / Explicit picker with a checkbox list of networks. Auto-mode
  chip shows the live server-resolved preview ("Auto · TrackA +
  TrackB"); Explicit pins a specific set.
* **Per-action target filter cascade.** When the scope is Explicit,
  the action's group / device dropdown filters to in-scope networks
  only. Out-of-scope choices disappear from the editor.
* **Out-of-scope warning chip.** Switching to a smaller Explicit
  scope marks any now-out-of-scope action with an *"out of scope"*
  warning + red border on the target picker. Saving is rejected
  with HTTP 400.
* **Sidebar scope badge.** Scenes with Explicit scope show a small
  "N nets" badge next to the label; an amber dot appears when one
  of the scope's networks no longer exists.
* **Fan-out pill in the editor.** When the scene's broadcasts reach
  2+ gateways, a green *"Fan-out: 2 gateways"* pill surfaces above
  the action list. The cost-estimator's airtime figure stays
  single-network (parallel airtime; wall-clock is bounded by the
  slowest radio, not summed).

### Fixed

* Broadcast `PRESET` / `CONTROL` / `OFFSET` fan-out on multi-
  gateway setups — previously only `SYNC` honoured scene scope, so
  broadcast ops with `target_group == 255` failed routing at N≥2
  gateways.

### Wire protocol

Unchanged.

---

## 2026-05-27 — Per-group network migration + unified Manage-groups dialog

A group ended up on the wrong network and the operator had no UI
path to fix it — the bulk-regroup endpoint actively refused
cross-network moves, so the only recovery was NVS-reset + complete
re-discovery. This release adds a group-granular migration path and
consolidates the WebUI surface into a single dialog.

### Added

* **Manage groups dialog** (sidebar ↕ button, formerly "Reorder
  groups") bundles drag-reorder with multi-group network migration.
  Pick rows via checkboxes, choose a Target network, click **Move N
  selected**. Reorder + move are independent Apply buttons —
  operator can do either, both, or several moves in a row without
  closing the dialog.
* **Offline-mode dialog flow:** default **Move** uses *block* —
  refuses if any device is offline and reveals **Skip offline** /
  **Force offline** buttons. Skip flips metadata only for offline
  devices (Channel Scan recovers physically); Force attempts the
  wire push anyway.

### Changed

* **Network badge** moved out of the DeviceTable column (now
  removed) into the sidebar group rows and the header band above
  the device table for the currently-selected group. Read-only in
  both places.

### Removed

* `ResortGroupsDialog.vue` + `NetworkMoveDialog.vue` — replaced by
  `ManageGroupsDialog.vue`.

### Wire protocol

Unchanged.

---

## 2026-05-22 — Multi-network reconnect hardening + UX polish

Stage 5 (2026-05-21) shipped the end-to-end multi-USB-gateway plan.
Six bench-test rounds against two physical gateways on a Pi exposed
follow-up issues. This release covers the surgical fixes that
closed each round.

### Changed

* **Central master pill is gone.** The header's master bar now
  carries one pill **per attached gateway** instead of a single
  pill driven by the primary slot. Each pill colour-codes the
  combined Bind + RF state (TX = blue, IDLE = green, RX_WINDOW =
  warm yellow, ERROR = red, conflict = amber border, unbound = red
  border, pending = grey). Hover for full details.
* **Pair Assistant is no longer auto-open.** Replaces the prior
  "popup on every USB flicker" model. Reachable via the new
  reconnect banner, the `⚠ Pair…` header button (visible while any
  gateway needs attention), or the host-settings menu.

### Added

* **Per-network reconnect banner.** When a gateway disappears
  mid-session only that one transport drops out — sibling gateways
  stay fully online. A red banner lists every missing network's
  gateway with a live 5 s countdown, per-row Cancel, global "Cancel
  all", and an "Open Pair Assistant" button. The countdown ticks
  locally and resyncs on every SSE update.
* **Hot-reconnect for known gateways.** The host polls every 5 s
  while any persisted `gateway_mac` is missing from the transport
  list. Replug → next poll attaches it → pill comes back. No host
  restart needed.
* **"Re-discover now"** button in Pair Assistant — operator-driven
  trigger that runs the soft rediscover immediately + clears any
  per-MAC cancels.

### Removed

* **GatewayRfConfigDialog.** The 📡 header button is gone — the
  NetworkManagerDialog channel-edit flow with the Migrate prompt
  covers the operator-visible RF-config use case.

### Fixed

* **Bind-wizard "all dashes" mismatch.** When `GET_RF_CONFIG`
  returned no readback, the wizard used to pop with every "Gateway
  reports" cell blank. Bind eval now parks the record at PENDING
  (grey pill) instead of CONFLICT, no spurious wizard.
* **Pair Assistant title** changed from "Pair Assistant (Single
  Gateway)" to "Pair Assistant" — the Single-Gateway constraint is
  documented in the dialog description, not the title.
* Secondary transport silent on RX, IDENTIFY_REPLY, and disconnect
  detection (listener was not installed).
* Single-transport disconnect leaving a dead transport in the
  controller's transport list with `controller.ready = False`.
* Cascade where one disconnect caused the sibling to flap-cycle
  every 5 s (the soft-rediscover IDENTIFY probe was landing on the
  live sibling's USB-CDC stream).

### Wire protocol

`PROTO_VER_MAJOR/MINOR` unchanged (host + UI only).

---

## 2026-05-21 — Multi-USB-gateway support

The multi-USB-gateway plan landed end-to-end: one host can now drive
several attached gateways, each carrying its own LoRa channel and
its own subset of networks/devices. Single-gateway operators see no
behaviour change.

### Added

* **`RL_Network` domain model** — the operator-visible bundle of a
  name, a `gateway_mac` binding, and an `rf_config`. Groups and
  devices belong to exactly one network at a time. The v1→v2
  persistence migration synthesises a default network on first
  boot so single-gateway deployments inherit the data model
  transparently.
* **Region + channel tables.** EU868 and US915 each ship five
  named channel slots (≥500 kHz separation between every
  same-SyncWord pair). The Network Manager dialog binds against
  the table; the host resolves the seven wire-format `P_RfConfig`
  fields at apply-time. See
  [`reference/channels.md`](reference/channels.md).
* **Gateway-bind state machine.** Per attached gateway:
  `pending` / `bound` / `conflict` / `unbound`. The
  **GatewayBindWizard** auto-opens for `conflict` / `unbound` and
  renders the per-field diff with resolve options
  (accept_gateway / accept_host / create_network / rebind).
* **RF migration engine.** Four-phase pipeline (pre-check → device
  push → gateway switch → verification). Triggered by the bind
  wizard's `accept_host` flow or by `POST
  /api/networks/{id}/migrate`. Stranded devices land in Channel
  Scan recovery.
* **Channel Scan service.** Walks a region's channel table on one
  gateway (volatile-switch → settle → broadcast `OPC_DEVICES` →
  dwell → partition into known/unknown). `try/finally` restores
  the pre-scan config even on mid-channel failure.
* **Cross-network fan-out** — `OPC_SYNC` and broadcast
  `PRESET` / `CONTROL` / `OFFSET` route via per-network helpers
  (`transport_for_group` / `transport_for_device`).
* **Network Manager + Setup-Change Assistant + scene picker.** A
  two-pane CRUD UI plus a session-once auto-open assistant that
  diffs against the persisted setup and offers one-click hand-offs
  to the right wizard.

### Changed

* **Network-boundary enforcement.** Bulk regroups that span
  networks now return HTTP 400 with a structured detail payload
  before the TaskManager job runs. New groups inherit the default
  network's id.

### Wire protocol

`PROTO_VER_MAJOR/MINOR` unchanged. New opcodes are **additive**:
`OPC_RF_CONFIG` / `OPC_GET_RF_CONFIG` / `GW_CMD_SET_RF_CONFIG` /
`GW_CMD_GET_RF_CONFIG` / `EV_RF_CHANGED` (`0xF6`). Pre-Stage-1
firmware silently ignores them per the protocol's forward-compat
rule. No persistence-format breakage from the v1→v2 migration
engine.

### Docs touched (new)

* [`reference/channels.md`](reference/channels.md) — region/channel
  tables.
* [`RaceLink_Host/multi-network.md`](RaceLink_Host/multi-network.md) —
  operator-facing guide covering bind wizard, RF migration,
  Channel Scan, Setup-Change Assistant, boundary enforcement.

---

## 2026-05-20 — Host WebUI: brand visual identity

End-to-end visual sweep that ports the
[racelink.dev](https://racelink.dev) brand language into the Host
WebUI without restructuring components or operator flows.

### Added

* **RaceLink wordmark** in the header (pink-glowing dot + "RACE" in
  off-white + "LINK" with a pink→cyan gradient text-clip).
* **Self-hosted fonts.** Chakra Petch (display) + Sora (body) as
  GDPR-friendly WOFF2 — no third-party font CDN calls.
* **Brand background.** Two radial glows (pink top-left, cyan
  top-right, both ~12 % opacity) layered over a faint 64 px
  speed-grid that fades out toward the bottom.
* **Button variant taxonomy** — `brand` (Save / Create / Apply /
  Confirm), `run` (Run / Start / Re-sync / Send / Start update),
  `destructive` (Delete + destructive confirm CTAs). Restyled
  `destructive` to fit the outline language.

### Changed

* `--color-accent` tuned blue → neon cyan → medium teal so links,
  checkbox/radio fills, and focus rings stop screaming.
* `--color-card` moved to a semi-transparent dark surface so panels
  read as glass plates over the body atmosphere.
* Native form controls (`<input type="checkbox|radio|range">`,
  `<progress>`, `<meter>`, `<select>`) declare `accent-color:
  var(--color-accent)` — UA defaults (Edge cyan, Firefox blue) no
  longer leak through.

### Fixed

* Favicon was 404-ing because no `<link rel="icon">` was declared.
  Now wired through Vite's `public/` directory so it resolves under
  any URL prefix.

### Docs touched

* **New** contributor playbook: `RaceLink_Host/docs/webui-styling-tips.md`.
* **Updated** `RaceLink_Host/ui-conventions.md` §"Button visual
  variants" cross-references the verb vocabulary with the new
  variant names.

### Non-changes

No protocol, API, or operator-flow changes. Same buttons in the
same places fire the same packets. No new dependencies. No
light-mode support (the reference site has none).

---

## 2026-05-19 — WLED: Headless reliability + SYNC precision

Field-testing pass after the 2026-05-18 Headless landing surfaced
four issues; all four fixed plus a structural cleanup. No wire-
protocol or operator-action changes.

### Fixed

* **First slave silently dropped on Headless-master reboot.** With
  two persisted slaves, only the second received its
  `OPC_SET_GROUP`. Retry-on-busy + 500 ms inter-send grace delay
  ensure the slave is never silently skipped. A 40-slave sweep now
  takes ~20 s, reliable.
* **Master timebase drift on offset scenes.** Slaves stayed in
  sync; the master drifted because it never re-anchored its own
  `strip.timebase` after `setActivePhaseOffsetMs()`. The master
  now re-asserts the invariant after every SYNC.
* **SYNC precision ±240 ms** (Headless-master) vs ±15 ms (regular
  Gateway). The LBT branch hard-overwrote `jitterMaxMs` to a
  50..300 ms random delay, so the `ts24` body field was sampled at
  caller's `millis()` but transmitted up to 300 ms later. Headless
  SYNC now bypasses LBT.
* **Pairing-TX indicator firing for routine SYNC keepalive.**
  Renamed `IND_TX_BLIP` → `IND_PAIRING_TX` (catalog ID 5
  unchanged — wire-stable). Only `SET_GROUP` sends arm the
  indicator; routine traffic produces no flash.

### Added

* **Auto-scene-rebroadcast after pairing.** When a slave joins
  (proactive boot-burst OR individual reactive pairing) the master
  broadcasts the current scene once, 1 s after the last successful
  `SET_GROUP` in the burst. Freshly bound slaves snap to the
  master's visual state instead of staying on their boot colour.
  Debounced (1 s window) so a 10-slave burst collapses to one
  packet. No-op when the master has no current scene yet —
  operator picks a scene first.

### Master-side ACK telemetry (diagnostic only)

Slaves' ACKs to `OPC_SET_GROUP` are now logged on the master
(`RX ACK from XXXXXX echoOpcode=0x03 status=0`) and counted in
`rxAccepted`. No visual indicator — the pairing-TX flash already
covers the per-send case.

### Wire protocol

`PROTO_VER_MAJOR/MINOR` unchanged. Firmware-internal behaviour
fixes + a renamed (but wire-stable) indicator ID.

### Coordinated firmware sync (recommended)

The Gateway + Host copies of `racelink_transport_core.h` need the
same `scheduleSend()` body sync for the SYNC-precision fix to
benefit cross-repo; Gateway's `rl_queueTxNoCad()` can simplify to
a one-liner once done. WLED-side changes work standalone.

---

## 2026-05-19 — Host: faster OTA error path + live error detail + Total-Time badge

Field feedback on the firmware-update workflow surfaced three
operator pain-points after a device fails. All fixed in one pass.
No wire-protocol or operator-action changes.

### Fixed

* **Failure path ~11 s → ~3 s.** AP-Enable per-device ACK wait
  switched from a single 8 s attempt to `1.5 s × 2`. Healthy
  devices ACK in <1 s; the retry recovers a single dropped frame
  without paying the 8 s penalty.
* **AP-Close skipped on the clean-success path.** A successful
  firmware POST triggers a WLED reboot that drops the AP
  automatically — sending an explicit AP-Close into the reboot
  window timed out 3 s per device for nothing. AP-Close now fires
  **only** when AP-Enable ACKed *and* a later step failed (wrong
  OTA password, bad firmware binary, HTTP 401 / 500 / timeout, …),
  so the device's still-broadcasting AP doesn't leak its
  credentials.
* **Live error detail in the per-device row.** The OTA workflow
  publishes a parallel MAC → message map every time it emits a
  stage event. `FwProgressPanel.vue` reads it directly and shows
  the message inline on the red row (e.g. `Timeout waiting for
  CONFIG ACK from <MAC> (AP-enable)`).
* **`RuntimeError:` Python class-name prefix dropped** from all
  operator-visible error strings.
* **Live ETA timer no longer starts at "0:07"** on hosts without
  NTP sync — the timer now anchors on a server-supplied
  `elapsed_s` field instead of `Date.now()/1000 - started_ts`.

### Added

* **Total time: M:SS** badge in the OTA summary panel.

---

## 2026-05-18 — WLED: persistent boot colour + Headless slave registry + pairing-TX indicator

Three coordinated WLED-firmware changes that close long-standing
gaps in node identity persistence and Headless-Mode reboot
behaviour, plus a visible "I'm transmitting" cue for the Headless
Master.

### Added

* **Persistent per-device boot colour.** The boot-time R/G/B pick
  is now rolled once on the very first boot and immediately
  persisted to `cfg.json`. Every subsequent boot reuses the stored
  value — a device always lights up in the same colour until the
  operator changes it. The physical-button click cycle doubles as
  a boot-colour editor: 10 s after the last click, the currently-
  displayed colour is written back.
* **Headless Master persistent slave registry.** Up to 40
  `(addr3, groupId)` records persisted in `cfg.json`. Survives
  reboot and battery swap. After auto-resume probe the master
  sweeps its registry and sends one `OPC_SET_GROUP` per known
  slave so slaves that did not power-cycle alongside the master
  regain their pairing without having to re-emit `IDENTIFY_REPLY`.
  A full 40-slave sweep reads as a continuous green-cyan flash on
  the master.
* **`IND_PAIRING_TX` indicator.** Local-only (never wire-
  triggered). Fires on `SET_GROUP` sends; routine traffic (scene
  broadcast, brightness, 30 s SYNC keepalive, IDENTIFY probes)
  produces no flash. 200 ms throttle prevents back-to-back sends
  from extending the indicator deadline into a sustained overlay;
  a 40-slave re-bind sweep reads as one continuous flash rather
  than a flicker storm.

### Changed

* **Group-id layout.** `HEADLESS_FIRST_GROUP_ID` was 1; the master
  conceptually owned no group. Now: master = group 1 (set on entry,
  cleared on exit), first slave = group 2. Group 0 = unconfigured
  pool, group 255 = broadcast pseudo-group.

### Fixed

* **Flash-wear from pairing-burst saves.** Used to fire one
  `cfg.json` save per slave (40 slaves → ~80 saves / 30 s). A 5 s
  debounce now collapses a 40-slave burst into a single save.

### Wire protocol

`PROTO_VER_MAJOR/MINOR` unchanged. `IND_PAIRING_TX` is append-only
and never travels on the wire; older firmware silently drops
unknown indicator types. The new `Headless Slaves` cfg.json key is
read-as-empty by pre-change firmware, so a mixed-firmware operator
path is benign.

### Non-changes

No operator action required for existing fleets. Coordinated flash
not required — slaves are agnostic to the master-side changes;
`OPC_SET_GROUP` semantics on the wire are unchanged. The first
slave paired under the new firmware on an upgraded master will be
assigned to Group 2 (was Group 1); pre-existing pairings continue
to work via the idempotent Case A path.

---

## 2026-05-17 — Indicator catalog + overlay-rendering refactor + host UI polish

A multi-thread session that landed the operator-facing **Click-to-
Locate** feature, then iteratively cleaned up rendering side
effects.

### Added

* **Click-to-Locate.** Clicking a device name in `DeviceTable.vue`
  (when not in rename-edit mode) and the per-row "Locate" button
  in `BatteryDevicesDialog.vue` both POST `/api/devices/indicate`
  to fire a magenta strobe on the targeted node for 5 s. UI verb
  is "Locate". Toast wording: "Locating …" / "Locate failed …".
* **`IND_IDENTIFY`** (catalog row, magenta `0xFF00CC`,
  operator-locate trigger).

### Changed

* **Indicator catalog standardisation.** STROBE-only (BREATH
  retired for indicators — too subtle in race environments).
  Urgency-coded speed: 235 = slow / positive event, 245 = medium /
  informational / operator action, 250 = fast / error.
* **Indicator rendering — frame-buffer overlay.** The previous
  `setMode(STROBE)` + snapshot/restore approach is gone; indicators
  now render via `Usermod::handleOverlayDraw()` after every segment
  effect has been blended into the strip frame-buffer. The
  underlying effect is never interrupted, so `SEGENV.step` /
  `aux0` advance during the overlay and the device returns to
  fleet phase the instant the overlay clears.

### Fixed

* **MasterBar pill staying IDLE while the banner said "Gateway
  link lost."** The pill now shows `ERROR` (red) whenever
  `gateway.gateway.ready === false`, even if no firmware-side
  `STATE_REPORT` reached the host.
* **`err:` detail field reliably cleared** on the false→true
  `ready` transition.
* **Per-device OTA estimate** bumped 21 s → 30 s to match field
  observations.
* **Post-first-device countdown counting up** instead of down.
  Observed average is now frozen at each `deviceIndex` advance, so
  `remaining = avg × total - elapsed` counts down monotonically at
  1 s/s.

---

## 2026-05-17 — Wire: rename `OPC_SCENE` → `OPC_HEADLESS`

### Changed

* **Identifier-only rename.** The wire byte value (`0x0B`) and body
  layout are **unchanged** — mixed binaries built before and after
  this rename interoperate byte-for-byte.
* `struct P_Scene` → `struct P_Headless` in lockstep.
* `RaceLinkHeadless::buildScenePacket()` →
  `RaceLinkHeadless::buildHeadlessPacket()`. Same signature, same
  emitted bytes.

### Motivation

Today's host-side **RaceLink Scenes** travel as `OPC_CONTROL` on
the wire. A future refactor may give them a dedicated opcode
named `OPC_SCENE` — exactly the name yesterday's Headless-Mode
trigger had grabbed. Renaming today removes the collision before
either side has shipped to operators.

### Coordinated update required across the three repos

The Host's `gen_racelink_proto_py.py` re-run bubbles the new
constant into `racelink_proto_auto.py` automatically. Gateway- and
Host-side passthrough is pending follow-up.

---

## 2026-05-16 — WLED: Headless Mode + central Indicator system

Two coordinated feature waves on the WLED node.

### Added — Headless Mode

* **Five-click on the boot/user button** promotes the device to
  Headless Master after a 1.5-second IDENTIFY_REPLY probe. Any
  incoming M2N traffic during the probe (typically `OPC_SET_GROUP`)
  refuses the promotion (red strobe indicator).
* **Persisted across reboots.** A power-cycled headless master
  re-runs the probe at boot, so a real Gateway that came back up
  while the device was off correctly overrides the headless mode.
* **Master role on the device** — automatic group assignment
  (counter persisted in `cfg.json`, wraps at 254); 30-second
  `OPC_SYNC` autosync keepalive; long-press drives a non-linear
  S-curve brightness fade locally, final value broadcast once on
  release.
* **Gateway always wins (runtime override).** Any M2N packet from
  a non-self sender during active headless triggers immediate
  step-down. Removes the previously possible "two simultaneous
  masters on the channel" race window.

### Added — Indicators

* New central status-notification mechanism. `OPC_INDICATE` carries
  `{type: u8, durationSec: u8}`; receivers look the type up in a
  shared catalog (`racelink_indicators.h`), overlay the indicator
  for the requested duration, restore the underlying segment at
  expiry.
* Initial catalog: `IND_PAIR_CONFIRMED`, `IND_PROBE_REJECTED`,
  `IND_HEADLESS_ENTER`, `IND_HEADLESS_EXIT`. All animated, no pure
  R/G/B/W — project rule.
* **Duration `0` = cancel.** A Host can send `OPC_INDICATE
  (any_type, 0)` to clear an active indicator without showing a
  new one.

### Changed

* **Pair-confirmation visual.** The previous indefinite white
  breath after `OPC_SET_GROUP` is replaced by a 5-second hot-pink
  breath (`IND_PAIR_CONFIRMED`). Operators using the visual cue to
  confirm pairing will need to glance within ~5 s.
* **Probe-reject visual.** The previous 1 Hz red/black blink
  mechanism replaced by an indicator overlay.

### Wire protocol

`PROTO_VER_MAJOR/MINOR` unchanged. Both new opcodes are
**additive** (`OPC_HEADLESS = 0x0B`, `OPC_INDICATE = 0x0C`) — older
firmware silently drops the packets via the RULES-table length
check.

### Non-changes

No operator-visible behaviour change for Gateway+Host fleets. A
device that has never been promoted to headless operates exactly
as before.

---

## 2026-05-15 — Host: firmware-update workflow stabilised + live ETA

Multi-device OTA used to fail intermittently on the 2nd or 3rd
device of a fleet. A 10-device fleet now finishes in ~3:30 min with
zero retries or recoveries needed.

### Fixed

* **Per-device sync sequence rewritten.** Post-upload host
  disconnect with `nmcli -w 0`, wait for `IDENTIFY_REPLY` after the
  reboot, wait for the standard `_restore_known_device_group`
  worker to push `SET_GROUP` and ACK, only then send AP-Close.
  AP-Close is now ACK-blocked instead of fire-and-forget.
* **BSSID selection cascade** drops stale scan-cache entries so
  NetworkManager can't pick a previously-flashed node's dead AP.

### Added

* **Pre-commit ETA next to Start button** (`~21 s × <target
  count>`).
* **Live `elapsed · ~remaining left` timer** in the progress panel
  that self-refines once one device completes.
* **Single-line summary in the status pill** (`fwupdate done ·
  (211.4s) · 10/10 ok`) instead of the full per-device JSON dump.

---

## 2026-05-15 — Host: modal-locked long-running dialogs + cooperative task cancel

Long-running operations that previously left the operator without a
status view if the dialog was dismissed mid-flight now lock their
dialog and expose an explicit Cancel button.

### Added

* **`POST /api/task/cancel`** — single generic cancel endpoint.
* **Cancel button** in the Firmware Update dialog. Cancel waits
  for the current device's flash + verify + reconnect to finish
  before breaking out of the per-device loop, so no node is left
  in a half-flashed bootloader state. Worst-case operator wait
  after clicking Cancel is ~60-90 s (one full per-device round-
  trip).
* **`lockClose` prop** on dialogs — `interactOutside` and
  `escapeKeyDown` are blocked; the corner X button is hidden. The
  only way out is an explicit in-dialog action.
* **Browser navigation guard** during long-running tasks (back /
  forward, refresh, tab close, in-app routes) prompts via the
  native confirm.
* **Three-phase Firmware Update state machine** (`config` →
  `progress` → `summary`). Summary phase renders successful /
  failed / skipped device lists, host-Wi-Fi-restore status and
  workflow-level errors.

### Changed

* Same lockdown pattern applied to **WledPresetsDialog**
  (download path) and a lighter variant in **DiscoverDialog**.

### Non-changes

The Wi-Fi-restore in the `finally` block runs regardless, so
cancel cannot strand the host on a device AP.

### Wire protocol

Unchanged.

---

## 2026-05-14 — Host: unified RX reply matcher + single-packet OPC_STREAM

### Fixed

* **Startblock Control on a device with empty slots silently
  rejected.** `OPC_STREAM` now accepts single-packet streams
  (`totalPackets >= 1`) on both sender and receiver. Previously
  anything shorter than two 8-byte chunks was rejected, which is
  exactly the region the startblock per-slot payload falls into
  when a slot has no pilot assigned. Saves ~30-50 ms of time-on-
  air per empty slot at SF7 / BW250.
* **Noisy `try_match MISS opc=ACK ... pending_keys=0` debug
  log** on every legitimate stream / discovery / status ACK. The
  replacement `NO_MATCH` line only fires when a matcher actually
  had the right bucket key but its full filter rejected the event
  — a genuinely diagnostic signal.

### Changed

* **Reply-matching primitive unified.** Host-internal cleanup
  merges the previous unicast and broadcast matchers into one
  data structure (`PendingMatcher`). One wait loop, one primitive
  (`GatewayService.send_and_match`). New developer-guide page:
  [Reply Matching (PendingMatcher)](RaceLink_Host/reply-matching.md).

### Wire protocol

`PROTO_VER_MAJOR/MINOR` unchanged. The `OPC_STREAM` ctrl-byte
encoding is identical; only the accept/reject predicate on both
endpoints widened.

### Coordinated flash required

OPC_STREAM single-packet support depends on matching firmware on
both sides. Roll Gateway and all WLED-startblock nodes together.
Hosts on either matcher generation continue to interoperate with
both firmwares (the host change is purely internal refactoring).

---

## 2026-05-07 — RaceLink_WLED: V3↔V4 sync investigation retrospective

A two-day investigation into V3 (ESP32-S2) ↔ V4 (ESP32-S3) phase-
sync drift on sharp-edged effects (Strobe), plus a related "weak
Breathe" symptom on internally-triggered pair-confirmation effects.

**Several speculative code-level patches were tried; none
demonstrably solved the V3↔V4 drift.** The weak-Breathe symptom was
identified as operator-side state divergence (segment geometry on
devices was historically normalized by an auto-applied Boot Preset;
removing the preset exposed the underlying divergence) — a firmware
fix is not needed.

The full retrospective with per-change rollback pointers lives in
the maintainer-internal session archive at
`_private/sessions/dev-session-2026-05-sync-investigation.md`
(gitignored, local-only — relocated from the published docs in
Gruppe 6).

---

## 2026-05-06 — RaceLink_WLED: async ePaper + runtime-configurable pins

### Changed

* **Async ePaper rendering.** The GxEPD2 e-paper driver is now
  driven from a dedicated FreeRTOS worker task. Both `epaperInit()`
  (boot screen, ~1 s) and every refresh (~1 s on the GDEY037T03
  panel) used to block WLED's main loop, freezing LED effects, the
  web UI and LoRa servicing for the duration. The async refactor
  pushes all GxEPD2 calls off the main loop.
* **Runtime-configurable radio + ePaper pins.** Configurable via
  **Config → Usermod Settings → RaceLink** in the WLED Web UI.
  The previous `-D RACELINK_PIN_*` and `-D RACELINK_EPAPER_*`
  build flags become *defaults* per build profile rather than
  hard-coded values, so first-boot behavior on every shipping
  target is unchanged. A saved pin change triggers an automatic
  reboot to re-init SPI on the new pins. Pins are now allocated
  through WLED's PinManager — a conflict with an LED-bus pin fails
  loudly at `radioInit()` time instead of silently breaking SPI.

### Non-changes

* **Radio chip family stays compile-time.** SX1262 vs LLCC68 (and
  any future chip choice) is still selected at build time via
  `-D RACELINK_SX1262` / `-D RACELINK_LLCC68`. Rationale: the
  underlying RadioLib chip-family APIs (SX126x vs SX127x) are not
  interchangeable at the abstract base.

### Breaking — for external embedders only

`epaperInit()` C++ signature changed from no-argument to seven pin
arguments. Only one in-tree caller exists; no external callers.
Operators flashing the new firmware on top of an existing install
keep their `cfg.json` — pin values fall back to the build-time
defaults when a `pins` / `epaper_pins` block is absent.

### Docs touched (new)

* [RaceLink_WLED → Pin configuration](RaceLink_WLED/pin-config.md)
  — operator guide.
* [RaceLink_WLED → Radio modules](RaceLink_WLED/radio-modules.md) —
  developer guide.

---

## 2026-05-04 — Preset terminology cleanup

**Breaking.** Disambiguates the long-standing "WLED Control" vs
RL-preset confusion in operator-saved data and the SSE topic
vocabulary. Wire protocol unchanged.

### Breaking

* **Saved scenes containing `{"kind": "wled_control"}` actions fail
  to load.** Operators must re-save those scenes — the WebUI scene
  editor now offers `Apply RL Effect` (with the 14-field parameter
  form) in their place.
* **Saved Specials configs referencing the `wled_control`
  function key fail to load.** Operators must re-configure the
  affected device's Specials → WLED → RaceLink Preset entry.
* **Third-party SSE consumers subscribed to the `presets` topic
  must switch** to `rl_presets` (RL preset CRUD) and/or
  `wled_presets` (WLED preset upload/select). The legacy union
  topic is gone.
* **Plugins / scripts calling `Controller.sendWledControl` or
  `ControlService.send_wled_control`** must update their call sites
  (renames listed in the maintainer-internal engineering ledger).
  RotorHazard plugin shipping with this release is updated in
  lockstep.

### Removed

* `state_scope.PRESETS` token (and SSE topic `presets`). Callers
  must use `state_scope.RL_PRESETS` / `state_scope.WLED_PRESETS`.

### Changed

* `wled_control` Specials function renamed to `rl_preset`.
  Operator-facing label "WLED Control" → "RaceLink Preset".
* `wled_control` scene action kind renamed to `rl_effect`.
* Classical `wled_preset` (WLED's per-device numeric preset slot,
  `OPC_PRESET`) and host-side `rl_preset` (lookup of a named RL
  preset, emits `OPC_CONTROL`) are unchanged.

### Wire protocol

`OPC_PRESET`, `OPC_CONTROL`, and packet identifiers are unchanged.
RaceLink_Gateway and RaceLink_WLED firmwares interoperate
byte-for-byte with both pre- and post-rename hosts.

---

## 2026-05-04 — Sidebar group rows: live counts + flash

### Added

* **`M / N` per row** — devices currently online out of total
  devices in the group — with a hover tooltip explaining what
  "online" means (replied to the last status query or sent an
  unsolicited `IDENTIFY_REPLY` recently). Falls back to the
  server-side `device_count` when the device list hasn't loaded
  yet on first render.
* **Group rows now flash** the same way the device-table rows do
  when any of their devices receives data. First-render-doesn't-
  flash semantics so a fresh page load doesn't strobe the sidebar.

### Wire protocol

Unchanged (UI-only change).

---

## 2026-05-03 — WebUI: Chrome SSE slot-pool stall fix

### Fixed

* **20–50 s UI freeze in Chrome after ~5 quick switches between
  `/racelink/` and `/racelink/scenes` via in-page links.** The
  freeze also affected any parallel RotorHazard tab on the same
  origin. F5 reload was always fine; Firefox was never affected.
  The fix is three layers (explicit `pagehide` close on the
  client, shorter SSE idle-ping cadence on the server,
  `Connection: close` on the SSE response) — full technical
  write-up in
  [`reference/sse-channels.md`](reference/sse-channels.md)
  §"Connection lifecycle and Chrome HTTP/1.1 slot pool".

### Wire protocol

Unchanged.

---

## 2026-05-03 — Groups target picker: search dialog

### Changed

* **Groups target picker** in the scene editor's unified target
  picker replaces the inline checkbox grid with a compact summary
  chip + a modal selection dialog. The summary shows the selected
  groups in small text together with the total group count and
  total device count across the selection, so the operator can
  scan an action without opening the picker. **Edit groups…**
  opens a dialog with a search field (filters by name or id), a
  scrollable result list, and three batch buttons (Select all
  hits, Deselect all hits, Invert hits). Designed for fleets
  with many groups.

### Wire protocol

Unchanged (UI-only change). No on-disk migration — scene format
unchanged.

---

## 2026-05-02 — Estimator ↔ runner structural sync

### Fixed

* **Cost-badge under-report on sparse-subset `offset_group`
  containers.** A stray `.controller` indirection in the API's
  group-id resolution silently returned `[]`, closing the
  optimizer's Strategy-C gate. Pre-fix reported 8 packets / 121 B;
  post-fix correctly reports 5 packets matching the wire.
* **SYNC body sizing.** The estimator was sizing `OPC_SYNC` with
  `flags=0` (4-byte legacy form); the runner has always sent
  `trigger_armed=True` (5-byte form). The planner now sizes with
  `SYNC_FLAG_TRIGGER_ARMED` so the cost badge matches the wire.

### Changed

* **Single source of truth for dispatch planning.** A new pure
  module is now consulted by both the cost estimator and the
  scene runner — per-kind logic that used to live in two parallel
  implementations is now in one place. A parity test suite runs
  every action shape through (planner, estimator, runner-with-
  recording-stubs) and asserts identical packet counts.

### Wire protocol

Unchanged.

---

## 2026-05-01 — Broadcast / target-picker unification

### Changed

* **Unified `target` shape across every scene action:**
  `{kind: "broadcast"} | {kind: "groups", value: [...]} | {kind:
  "device", value: "<MAC>"}`. The scene editor exposes the
  unified three-radio picker (Broadcast / Groups / Device)
  everywhere, replacing the previous mix of "Group/Device" radios
  + "All groups" checkbox + multi-select + "Scope (broadcast)"
  radio. Pre-unification shapes (`scope`, singular `group`,
  standalone `groups` field on `offset_group`) are migrated on
  read; save-time canonicalisation collapses "every known group
  selected" → `broadcast` so future-added groups are also hit.

### Added

* **Broadcast option** on top-level effect actions (was not
  available before).
* **New** [Broadcast Ruleset](reference/broadcast-ruleset.md)
  reference page (full per-opcode rules across Host / Gateway /
  WLED).
* **New** [Roadmap](roadmap.md) page recording two future-feature
  commitments (capability-agnostic broadcast addressing, group-
  agnostic re-identification).

### Wire protocol

`PROTO_VER_MAJOR/MINOR` unchanged; host + UI change only. Old
persisted scenes load as-is and are rewritten on next save.

---

## 2026-04-30 — Documentation consolidation

### Added

* **`RaceLink_Docs` repository** — the consolidated public
  documentation collection.

### Non-changes

No code or wire-protocol changes.

---

## Unreleased / in progress

* (placeholder)

---

## Template for new entries

```markdown
## YYYY-MM-DD — <release name or component>

### Added
* <operator-facing or contributor-facing addition>

### Changed
* <behaviour or naming change>

### Fixed
* <bug fix>

### Removed
* <surface that was deleted>

### Breaking
* <on-disk shape change, public-API rename, …>

### Wire protocol
<unchanged / additive / `PROTO_VER_MAJOR/MINOR` bump>
```

Engineering trail (commit SHAs, test counts, internal renames,
stage-by-stage breakdown) goes into the maintainer-internal
engineering ledger, not here.

---

## Useful queries

GitHub releases per repository:

* https://github.com/PSi86/RaceLink_Host/releases
* https://github.com/PSi86/RaceLink_Gateway/releases
* https://github.com/PSi86/RaceLink_WLED/releases
* https://github.com/PSi86/RaceLink_RH-plugin/releases

The wire-protocol version pair lives in `racelink_proto.h`:

```c
#define PROTO_VER_MAJOR 2
#define PROTO_VER_MINOR 0
```

A drift in any of the three byte-identical copies fails
`tests/test_proto_header_drift.py`.
