# Changelog

A consolidated timeline of releases across the four RaceLink
repositories. Currently a stub — entries should be added as releases
ship. Each entry should follow the template at the bottom of this
file.

> **Source of truth.** Each repository maintains its own GitHub
> releases page; this changelog is a curated cross-repo summary.
> When the cross-repo summary and a repository's release notes
> disagree, the repository's release notes win.

## 2026-05-22 — Multi-network reconnect hardening + UX polish

Stage 5 (2026-05-21) shipped the end-to-end multi-USB-gateway plan;
six bench-test rounds against two physical gateways on a Pi exposed
follow-up issues. This entry covers the surgical fixes that closed
each round.

* **RaceLink_Host** (commit `494ecee` on `ui-new-features`) —
  1024 pytest pass (+42 vs Stage-5 baseline), 61 vitest, vue-tsc
  clean, new frontend bundle `index-txAhTpSa.js`.
* **Wire protocol** — `PROTO_VER_MAJOR/MINOR` unchanged (host + UI
  + docs only).

### Operator-visible behaviour changes

* **Central master pill is gone.** The header's master bar now
  carries one pill **per attached gateway** instead of a single
  pill driven by the primary slot. Each pill colour-codes the
  combined Bind + RF state (TX = blue, IDLE = green, RX_WINDOW =
  warm yellow, ERROR = red, conflict = amber border, unbound =
  red border, pending = grey). Hover for full details.
* **GatewayRfConfigDialog removed.** The 📡 header button is gone.
  NetworkManagerDialog's channel-edit flow with the new
  Migrate-prompt covers the operator-visible RF-config use case;
  backend `/api/gateway/rf_config` + per-gateway
  `/api/gateways/<ident_mac>/rf_config` routes stay for debugging
  / external scripts.
* **Per-network reconnect banner.** When a gateway disappears
  mid-session only that one transport drops out — sibling gateways
  stay fully online. A red banner lists every missing network's
  gateway with a live 5s countdown, per-row Cancel, global "Cancel
  all", and an "Open Pair Assistant" button. The countdown ticks
  locally and resyncs on every SSE update.
* **Pair Assistant is no longer auto-open.** Replaces the prior
  "popup on every USB flicker" model. Reachable via the new
  reconnect banner, the `⚠ Pair…` header button (visible while any
  gateway needs attention), or the host-settings menu.
* **Hot-reconnect for known gateways.** A new
  `MissingTransportTracker` polls every 5s while any persisted
  `RL_Network.gateway_mac` is missing from `controller._transports`.
  Replug → next poll attaches it → pill comes back. No host
  restart needed.
* **Pair Assistant gains "Re-discover now"** — operator-driven
  trigger that runs the soft rediscover immediately + clears any
  per-MAC cancels.
* **Bind-wizard "all dashes" mismatch fixed.** When GET_RF_CONFIG
  returned no readback the wizard used to pop with every "Gateway
  reports" cell blank. Bind eval now parks the record at PENDING
  (grey pill) instead of CONFLICT, no spurious wizard.
* **Pair Assistant title** changed from "Pair Assistant (Single
  Gateway)" to "Pair Assistant" — the Single-Gateway constraint is
  documented in the dialog description, not the title.

### Backend internals

* **GatewayService listener install fix** — every attached transport
  now actually gets the `gateway_service.on_transport_event`
  listener installed (pre-fix, secondary transport was silent on
  RX, IDENTIFY_REPLY, and disconnect detection).
* **Per-transport detach** at any N when `gateway_id` is known —
  fires `gateway_detached` SSE, no nuclear `_close_all_transports`
  cycle. The single-transport case used to take the global path,
  which left the dead transport in `_transports` and stuck
  `controller.ready` at False.
* **`schedule_reconnect` now graceful** — when at least one
  transport is still attached, calls `controller.soft_rediscover()`
  instead of tearing every transport down. Nuclear path reserved
  for N=0 only (e.g. boot-time no-gateway).
* **`enumerate_all(exclude_ports=...)`** — soft_rediscover passes
  the currently-attached port set so the IDENTIFY probe never
  lands on a live gateway's USB-CDC stream. Eliminated the
  bench-test #6 cascade pattern (one disconnect causing the
  sibling to flap-cycle every 5s).
* **`_attach_transport` idempotency** — duplicate ident_mac drops
  the latecomer (closes it async); existing transport stays.
* **`_attach_transport` clears global retry timer** — prevents the
  scheduled `discoverPort` retry from nuking the freshly-attached
  transport seconds later.
* **`_attach_transport` fires `send_state_request`** after the
  bind eval so the per-gateway pill flips to its real RF state
  immediately instead of sitting at grey/UNKNOWN until the
  operator clicks ↻.
* **GET_RF_CONFIG settle** — default timeout 0.5s → 1.5s with one
  retry after 200ms; handles freshly-opened transports where
  USB-CDC needs a moment to surface the first reply.
* **`_clear_gateway_error` semantic fix** — also sets
  `self.ready = True` so the legacy global banner clears properly
  on re-attach.
* **`_action_accept_host` actually migrates** — kicks the
  rf_migration TaskManager job server-side and returns the
  `task_id` so the wizard can subscribe to live phase progress.
  Used to just set `migration_pending=True` and walk away.
* **`_action_create_network` rejects silent failure** — raises a
  clear error when GET_RF_CONFIG returned no readback instead of
  creating a network with `rf_config=None`.

### REST routes

* `POST /api/gateways/query-state` — fanout state-request over
  every attached transport, returns one row per gateway.
* `POST /api/gateway/rediscover` — manual trigger for
  `soft_rediscover` + clears the tracker's cancel list.
* `POST /api/gateway/cancel-reconnect` — suppress the reconnect
  poll for a specific `ident_mac` (or every currently-missing
  transport when body's `ident_mac` is null).
* `GET/POST /api/gateways/<ident_mac>/rf_config` — per-gateway
  RF-config addressing (the legacy `/api/gateway/rf_config`
  routes stay as primary-transport wrappers).

### Logging

Every high-volume gateway-related debug line now carries a
gateway label prefix so multi-gateway traces are scannable:

* `[#0 1C:10/Pit-Lane]` from `controller.format_gateway_label` for
  gateway_service-level lines (state changes, EV_TX_DONE, ACK,
  STATUS, IDENTIFY, RX, send_and_wait, send_and_match).
* `[1C:10]` from `GatewaySerialTransport._log_label` for
  transport-level TX lines (TX GW_CMD_*, TX M2N, TX outcome
  timeout, USB serial disconnected, USB low-latency mode).
* `[1C:10]` from `_gw_short` in pending_requests for matcher
  lines (matcher.register / matcher.cancel / matcher.try_match).

The bracket suffix correlates lines across the three log streams
without cross-referencing a separate boot line.

Notes:

* No on-disk migration step required.
* No wire-protocol or firmware change.
* `racelink/static/dist/` was rebuilt with the new frontend; the
  Pi needs the new bundle deployed (the old `index-Cn2sNh4I.js`
  doesn't carry any of these fixes).

## 2026-05-21 — Multi-USB-gateway support (Host + Docs)

The multi-USB-gateway plan landed end-to-end: one host can now drive
several attached gateways, each carrying its own LoRa channel and its
own subset of networks/devices. Stage 0/1/1.5 (pre-sync + wire
protocol + single-gateway onboarding) shipped earlier — this
changelog covers Stage 2/3/4/5 in one block since they all moved
together.

### Stage 2 — host-side multi-transport runtime

Eight commits, four landed on `ui-new-features` between
`76b3d46..1102176`:

* **Schema v2** (`76b3d46`): new `RL_Network` domain model with
  `id` / `name` / `gateway_mac` / `region` / `channel_id` /
  `rf_config` / `created_ts`; `network_id` field on every
  `RL_Device` and `RL_DeviceGroup`; idempotent v1→v2 persistence
  migration that synthesises the default network and back-fills
  every device + group.
* **Transport list foundation** (`69bbe1c`): `controller.transport`
  is now a property over the primary slot of
  `controller._transports`; new `transport_for_network` /
  `transport_for_device` helpers route by `RL_Network.gateway_mac`
  ↔ `transport.ident_mac`; `PendingMatcher.gateway_id` filter
  field; `GatewaySerialTransport.enumerate_all()` classmethod
  walks every USB port + returns `(port, ident_mac)` per
  responding gateway.
* **Per-gateway send-path routing + per-network SSE master +
  `enumerate_all` boot** (`1102176`):
    * Transport `_emit` / `_emit_tx` tag every event with
      `gateway_id = self.ident_mac`.
    * `PendingMatcherRegistry` split into a per-`ident_mac` dict;
      `controller._pending_expect` keyed by `gateway_id`;
      hook installation tracked per transport.
    * `setNodeGroupId` + `send_and_wait_with_retries` route via
      `transport_for_device`.
    * New `MasterStateMap` (one `MasterState` per network) backs
      `SSEBridge.masters`; `/api/master` returns
      `{networks, default_network_id}`; the SSE `master` event
      carries the unified shape; the WebUI's gateway store reads
      `networks[0]` for back-compat.
    * `discoverPort` walks `GatewaySerialTransport.enumerate_all()`
      when `psi_comms_port` isn't pinned; `_attach_transport`
      orchestrates `start` + auto-bind + per-id hook install.
    * `_close_all_transports` cleans up the whole list on shutdown
      / reconnect.

At N=1 every helper falls back to the singleton path — the
single-gateway UX is byte-identical to the pre-Stage-2 host.

### Stage 3 — channels, policy, bind state machine, migration, fan-out

Seven parts (A-G), four commits on `ui-new-features` between
`c6f462d..2fa24a8`:

* **Part A — RF channels + policy** (`c6f462d`):
  `racelink/domain/rf_channels.py` ships max-five-per-region
  channel tables for EU868 + US915 (≥500 kHz separation between
  every same-SyncWord pair, validated at import).
  `racelink/domain/rf_policy.py` exposes
  `validate_networks_separation` (returns conflict dicts; used
  server-side at every network mutation).
* **Part B — Hard network-boundary enforcement** (`c6f462d`):
  `racelink/domain/network_boundary.py::validate_group_membership`
  rejects bulk regroups that span networks. `POST
  /api/devices/update-meta` returns HTTP 400 with a structured
  detail payload before the TaskManager job runs. New groups
  inherit the default network's id.
* **Part C — PendingMatcher gateway_id required** (`aac678f`):
  `PendingMatcherRegistry.register` raises `ValueError` for
  concrete-sender matchers without `gateway_id`. Every send-path
  service (`config_service`, `status_service`, `send_and_wait_with_retries`)
  stamps the routed transport's `ident_mac`.
* **Part D — Gateway-bind state machine** (`aac678f`):
  `racelink/services/gateway_bind_service.py` classifies every
  attached transport as `pending` / `bound` / `conflict` /
  `unbound` after querying its NVS RF config via
  `GW_CMD_GET_RF_CONFIG`. SSE emits
  `gateway_bound` / `gateway_conflict` / `gateway_unbound` with the
  full `BindRecord` payload. `POST
  /api/gateways/{ident_mac}/resolve` takes one of
  `accept_gateway` / `accept_host` / `create_network` / `rebind`
  (token-gated).
* **Part E — RF migration engine** (`aac678f`):
  `racelink/services/rf_migration_service.py::migrate_network_to`
  runs the four-phase "Devices ZUERST, Gateway DANACH" pipeline
  (pre-check → device push via `OPC_RF_CONFIG` → gateway switch
  via `GW_CMD_SET_RF_CONFIG(persist=True)` → verification via
  discovery). Triggered by the bind wizard's `accept_host` flow
  or by `POST /api/networks/{network_id}/migrate`.
* **Part F — Channel-scan service** (`2fa24a8`):
  `racelink/services/channel_scan_service.py::scan_region`
  walks a region's channel table on one gateway (volatile-switch
  → settle → broadcast `OPC_DEVICES` → dwell → partition into
  known/unknown). `try/finally` restores the pre-scan config
  even on mid-channel failure. `POST
  /api/gateways/{ident_mac}/channel-scan` spawns the task.
* **Part G — Cross-network fan-out** (`2fa24a8`):
  `GatewayService.send_sync` broadcast fans out across every
  transport; `ControlService.send_group_preset` / `send_offset` /
  `send_control` / `send_device_preset` / `send_device_indicate`
  route via `controller.transport_for_group` /
  `transport_for_device`.

### Stage 4 — frontend multi-network UX

Three blocks on `ui-new-features` between `532a89e..6d0cf93`:

* **Block 1 — Foundation** (`532a89e`): backend `serialize_device`
  + `/api/groups` now return `network_id` + `last_known_rf_config`;
  new `/api/channels` exposes the shipped region table; new
  `frontend/src/stores/networks.ts` with deterministic-by-hash
  badge colours; DeviceTable gains a "Network" column with a
  tooltip showing the device's last-known RF settings; sidebar
  gains a network-filter dropdown that's hidden at N=1.
* **Block 2 — Wizards** (`4ffa3da`): new `frontend/src/stores/gateways.ts`
  hydrated from `/api/gateways` + kept live by the SSE
  `gateway_*` events; **GatewayBindWizard.vue** auto-opens on
  conflict/unbound and renders the per-field diff + resolve
  options; **ChannelScanDialog.vue** offers the form / running /
  result views with per-channel responder partitioning into
  known + unknown.
* **Block 3 — Network Manager + Setup-Change Assistant + scene
  picker** (`6d0cf93`): backend `PUT /api/networks/{id}` (rename +
  region/channel + rf_config; runs `validate_networks_separation`
  and returns HTTP 400 on conflict) and `DELETE /api/networks/{id}`
  (refuses when last-remaining / still-referenced).
  **NetworkManagerDialog.vue** is the two-pane CRUD UI with an
  inline live-bind-state callout. **SetupChangeAssistant.vue**
  auto-opens once per session when its client-side diff finds
  anything actionable (gateway missing / gateway unbound / gateway
  conflict / device RF stale) and offers one-click hand-offs to
  the right wizard. **MultiGroupPickerDialog.vue** anchors on the
  first selected group's network and disables cross-network
  selections with an "other net" pill.

### Stage 5 — documentation (this repo)

Lands in the same commit as this changelog entry:

* `docs/concepts/channels.md` — region/channel tables + separation
  rule + Advanced custom-mode + compliance disclaimer.
* `docs/RaceLink_Host/multi-network.md` — operator-facing guide
  covering bind wizard, RF migration, Channel Scan, Setup-Change
  Assistant, boundary enforcement, single-gateway back-compat.
* `docs/reference/wire-protocol.md` — new `P_RfConfig` body
  section, new rows in the opcode table for `OPC_RF_CONFIG` /
  `OPC_GET_RF_CONFIG`, new USB-only command rows for
  `GW_CMD_SET_RF_CONFIG` / `GW_CMD_GET_RF_CONFIG`, new
  `EV_RF_CHANGED` (`0xF6`) row.
* `docs/RaceLink_Host/architecture.md` — new "Multi-Transport
  runtime (Stage 2 / Stage 3)" section with the transport list /
  PendingMatcher gateway_id contract / MasterStateMap /
  enumerate_all boot / bind-state machine / RF migration engine /
  channel scan / cross-network fan-out / network-boundary
  enforcement subsections.
* `docs/glossary.md` — eleven new entries: `Network`, `Channel`,
  `Bind state`, `gateway_mac`, `last_known_rf_config`, `RF
  migration`, `Channel Scan`, `Stranded device`, `OPC_RF_CONFIG`
  / `OPC_GET_RF_CONFIG`, `P_RfConfig`, `EV_RF_CHANGED`. Updated
  the existing Opcode entry to mention the new opcodes.
* `STRUCTURE.md` Tables 1/2/3 — five new topic rows, six new
  code→doc rows, two new doc→backing-code rows.
* `mkdocs.yml` nav — entries for both new docs.

### Non-changes

* No changes to single-gateway behaviour. Every Stage-2/3 helper
  falls back to the singleton transport / default network when
  N=1 attached — a pre-Stage-2 host upgrades transparently.
* No wire-format breakage. `OPC_RF_CONFIG` / `OPC_GET_RF_CONFIG`
  / `GW_CMD_*_RF_CONFIG` / `EV_RF_CHANGED` are additive — older
  WLED + Gateway firmware that pre-dates Stage 1 PR-1 will not
  recognise them and (per the protocol's forward-compat rule)
  silently ignore them.
* No persistence-format breakage from the migration engine —
  v1→v2 is idempotent + back-compatible on the down-migrate path
  (Stage 2 Part 1's tests pin this).

### Test counts at end-of-shipping

* `RaceLink_Host/`: 982 pytest pass + 9 subtests (one deselected
  — the pre-existing OTA failure documented in earlier
  changelogs); vue-tsc clean; 61 vitest pass.
* `RaceLink_Docs/`: `mkdocs build --strict` green.

## 2026-05-20 — Host WebUI: Brand visual identity port from racelink.dev

End-to-end visual sweep that ports the [racelink.dev](https://racelink.dev)
brand language into the Host WebUI without restructuring components or
operator flows. Two-axis change: a new token / font / surface layer
*plus* a small button-variant taxonomy that ties the existing verb
vocabulary (Save / Run / Delete / …) to consistent visual styles.

### Brand surface

* **Wordmark.** Replaced the plain `<h1>RaceLink</h1>` in
  [AppHeader.vue](https://github.com/PSi86/RaceLink_Host/blob/main/frontend/src/components/AppHeader.vue)
  with the racelink.dev wordmark: pink-glowing dot + "RACE" in
  off-white + "LINK" with a pink→cyan gradient text-clip. New helper
  classes `.rl-brand`, `.rl-brand__dot`, `.rl-brand__g` in
  [racelink.css](https://github.com/PSi86/RaceLink_Host/blob/main/frontend/src/styles/racelink.css)
  back it. Header is the only site that uses the wordmark.
* **Fonts.** Self-hosted Chakra Petch (display, 4 weights) + Sora
  (body, 3 weights) as GDPR-friendly WOFF2 in `frontend/public/fonts/`.
  Wired through `--font-display` / `--font-body` + `--font-sans` so
  every `font-sans` utility and every form-control (after a
  `font-family: inherit` reset — Preflight is off) lands on Sora.
* **Background.** Body now layers two radial glows (pink top-left,
  cyan top-right, both ~12% opacity, `background-attachment: fixed`)
  over a faint 64 px speed-grid that fades out toward the bottom via a
  radial mask on `body::before`.
* **Favicon.** Was 404-ing because no `<link rel="icon">` was
  declared and the browser default-fetched `/favicon.ico` against the
  blueprint root. Now wired through Vite's `public/` →
  `<link rel="icon" href="{{ rl_static_path }}/dist/favicon.svg">` in
  [index.html](https://github.com/PSi86/RaceLink_Host/blob/main/frontend/index.html);
  Flask substitutes the Jinja placeholder at request time so the icon
  resolves under any prefix.

### Token reorganisation

The full token set lives in
[frontend/src/styles/tailwind.css](https://github.com/PSi86/RaceLink_Host/blob/main/frontend/src/styles/tailwind.css)
inside `@theme`. Key shifts:

* `--color-accent`: `#4c8bf5` (blue) → `#1fe6d6` (neon brand cyan) →
  `#2aa599` (medium teal). The bright cyan was too loud on links,
  checkbox/radio fills, and focus rings; the medium teal stays
  recognisable as the brand colour family without screaming.
* `--color-primary-foreground`: `#ffffff` → `#07080D`. Dark-on-teal
  for `bg-primary` surfaces — the white-on-teal combination was
  failing both WCAG and the eye-strain test.
* `--color-card`: `#17171c` (light gray) → `#0c0e16` → `#07080D` →
  `#07080d1f`. Final step takes it to alpha 0x1F so panels read as
  glass plates over the body atmosphere.
* `--color-popover` was previously aliased to `--color-card`; now
  pinned to `#07080D` solid. Dialogs/popovers need readable opaque
  surfaces — the transparent card colour is for in-page panels only.
* New brand tokens: `--color-brand-pink #ff2e6e`, `--color-brand-cyan
  #1fe6d6` (kept neon, opt-in for wordmark and CTA outlines only),
  `--color-brand-gradient`, `--gradient-run`, `--shadow-brand-glow`,
  `--shadow-brand-cta`. All consumable as Tailwind utilities.
* Native form controls (`<input type="checkbox|radio|range">`,
  `<progress>`, `<meter>`, `<select>`) now declare `accent-color:
  var(--color-accent)` in
  [racelink.css](https://github.com/PSi86/RaceLink_Host/blob/main/frontend/src/styles/racelink.css)
  — UA defaults (Edge cyan, Firefox blue) no longer leak through.

### Button variant taxonomy

Added two new variants to
[Button.vue](https://github.com/PSi86/RaceLink_Host/blob/main/frontend/src/components/ui/button/Button.vue)
and restyled `destructive` to fit the outline language. Mapping to the
existing button-vocabulary verbs (canonical doc:
[ui-conventions.md](RaceLink_Host/ui-conventions.md#button-visual-variants-2026-05-20)):

| Variant       | Verbs                                          | Style                                                  |
|---------------|------------------------------------------------|--------------------------------------------------------|
| `brand`       | Save, Create, Apply, Confirm                   | Cyan outline + faint cyan fill + cyan text             |
| `run`         | Run, Start, Re-sync, Send, Start update        | Pink→cyan gradient fill + cyan border + light text     |
| `destructive` | Delete + destructive confirm CTAs              | Pink outline + faint pink fill + pink text             |

* Smooth hover for `run` is via `filter: brightness()` (declared in
  the `@utility btn-run-bg` block in
  [tailwind.css](https://github.com/PSi86/RaceLink_Host/blob/main/frontend/src/styles/tailwind.css))
  — `background-image` can't interpolate between two `linear-gradient()`
  functions, so the gradient itself stays fixed and brightness shifts
  on hover instead.
* `destructive` lost its solid red fill; the outline form matches the
  brand/run outline language and reuses `--color-brand-pink` instead
  of the generic error red so the danger signal stays brand-aligned.
* `useConfirm({ variant: 'destructive', … })` consumers — currently
  device-removal in [DevicesSidebar](https://github.com/PSi86/RaceLink_Host/blob/main/frontend/src/components/DevicesSidebar.vue),
  scene-discard prompts in
  [scenes.ts](https://github.com/PSi86/RaceLink_Host/blob/main/frontend/src/stores/scenes.ts),
  and the destructive-action confirm in [SpecialsActionRow](https://github.com/PSi86/RaceLink_Host/blob/main/frontend/src/components/modals/SpecialsActionRow.vue) —
  inherit the new pink-outline style automatically.
* The "Reset to RaceLink defaults" Send button
  (key `wled_reset_overrides`) is the one outlier: data-driven, it
  picks `brand` over `run` because operators perceive it as a
  commit-state action even though the underlying packet is a wipe.
  Pattern documented for re-use.

### Documentation

* **New** [`RaceLink_Host/docs/webui-styling-tips.md`](https://github.com/PSi86/RaceLink_Host/blob/main/docs/webui-styling-tips.md):
  contributor-facing playbook for the design system — where tokens
  live, Tailwind v4 specifics (Preflight off, `@utility` for
  layer-correct custom classes, `@theme` auto-generated utilities),
  the variant taxonomy, anti-patterns. First port of call for the
  next theming round.
* **Updated** [`RaceLink_Host/ui-conventions.md`](RaceLink_Host/ui-conventions.md):
  new section "Button visual variants" cross-references the verb
  vocabulary with the new variant names.

### Non-changes

* No protocol, API, or operator-flow changes. Same buttons in the
  same places fire the same packets.
* No new dependencies. Self-hosted fonts + `accent-color` + Tailwind
  v4 `@utility` are platform features, not packages.
* No light-mode support. The reference racelink.dev site has none, so
  none was ported. Adding one would be a token-layer rebuild —
  separate task.

## 2026-05-19 — WLED: Headless reliability + SYNC precision + headless refactor into header

Field-testing pass that surfaced four issues in the prior 2026-05-18 Headless
landing, fixed all four, and finished with a structural cleanup that moves
all WLED-neutral headless state into `racelink_headless.h`. No wire-protocol
or operator-action changes; firmware-internal only.

### Re-bind reliability (bug 1 — first slave silently dropped)

* **Symptom**: on Headless-master reboot with two persisted slaves, only the
  second slave received its `OPC_SET_GROUP`. First slave stayed at
  `groupId = 0`, no Pair-Confirmed blink.
* **Root cause**: `serviceHeadlessReassign()` advanced the cursor
  unconditionally after each iteration, even when `scheduleSend()` returned
  `false` because the post-promotion scene/SYNC broadcast was still
  occupying the single-slot TX queue (`rl.txPending == true`). Cursor
  advance on a dropped TX = silent skip of that slave.
* **Fix** (two layers):
  - **Retry-on-busy**: when `headlessSendTx()` returns `false`,
    `deferReassignRetry()` keeps the same cursor and just reschedules the
    next attempt. The slave is never silently skipped.
  - **Grace delay**: `startHeadlessReassign()` now seeds
    `nextSendAtMs = millis() + HEADLESS_REASSIGN_INTERVAL_MS` instead of
    `millis()`. Gives the preceding scene/SYNC broadcast time to clear the
    queue before the first SET_GROUP attempt — eliminates the noisy
    retry-on-first-try case.
* **Interval bumped** from 50 ms → 500 ms
  (`HEADLESS_REASSIGN_INTERVAL_MS`). 50 ms left no channel-free window for
  the addressed slave to send its `OPC_ACK` back before the master's next
  SET_GROUP, causing CAD-busy backoffs on slaves (visible as `rl.debug`
  counter incrementing). 500 ms gives full ACK round-trip headroom at
  SF7/BW250. A 40-slave sweep now takes ~20 s — long but reliable.

### Master-side ACK telemetry (bug 1, support diagnostic)

* New pre-switch handler on the master for N2M `OPC_ACK` packets — slaves'
  ACKs to `OPC_SET_GROUP` were previously dropped silently at the
  direction filter, leaving the master blind to whether the re-bind sweep
  actually landed. Now logged as `[RaceLink] Headless: RX ACK from
  XXXXXX echoOpcode=0x03 status=0` and counted in `rxAccepted`. No visual
  indicator (logged-only by design — pairing-TX flash already covers the
  per-send case).
* Side benefit: the missing-slave debugging in the field can now be done
  by observing master serial output instead of slave-side instrumentation.

### Master timebase drift on offset scenes (bug 2)

* **Symptom**: on `SCENE_OFFSET_BREATHE` (and other offset scenes), slaves
  stayed synchronised with each other but the master drifted away — even
  though the master IS the timebase reference.
* **Root cause**: slaves re-anchor `strip.timebase` on every received SYNC
  via `handleSync()` (`desiredTb = M − S − activePhaseOffsetMs`). The
  master never re-anchored its own `strip.timebase` after the initial
  `setActivePhaseOffsetMs()` delta-adjustment, so any WLED-internal
  perturbation (effect transition, `setMode` reset, boot init) drifted
  the master out of the slave's reference frame.
* **Fix**: `headlessBroadcastSync()` now re-asserts the invariant
  `strip.timebase = -activePhaseOffsetMs` after every successful SYNC send
  (M=S degenerate case of the slave-side `handleSync` math). Also asserted
  once in `enterHeadlessMode()` before the first scene/SYNC broadcast so
  the master renders the right phase from frame 1.

### SYNC precision via `scheduleSend(jitterMaxMs=0)` (bug 3)

* **Symptom**: slaves' `lastSyncTbErrMs` was ±240 ms when synced from a
  Headless master vs. ±15 ms when synced from the regular Gateway dongle.
* **Root cause**: `scheduleSend()`'s LBT branch hard-overwrites
  `jitterMaxMs` to a 50..300 ms random delay before the actual TX. The
  `ts24` timestamp in the SYNC body was sampled at caller's `millis()`
  but actually transmitted up to 300 ms later, inflating slaves'
  drift-correction error.
* **Fix**: extended `scheduleSend()` itself so `jitterMaxMs == 0` is a
  universal "skip LBT entirely" bypass regardless of `lbtEnable`. The
  Gateway has had a separate `rl_queueTxNoCad()` toggle workaround for
  the same bug (explicitly documented in `main.cpp:992-998`); the WLED
  side now uses the same code path via the unified bypass. A brief
  `scheduleSendNoLbt()` parallel function (introduced earlier this week)
  was rolled back in favor of the unified contract.
* **Cross-repo invariant**: `racelink_transport_core.h` is byte-identical
  across Gateway/Host/WLED. The unified bypass must be replayed into the
  Gateway and Host copies for `tests/test_proto_header_drift.py` to stay
  green; Gateway's `rl_queueTxNoCad()` can then simplify to just call
  `scheduleSend(rl, buf, len, 0)`.
* `headlessBroadcastSync()` now passes `jitterMaxMs=0` and bypasses
  `headlessSendTx` entirely (SYNC is routine traffic, no pairing
  indicator).

### Pairing-TX indicator narrowed to SET_GROUP only (bug 4)

* **Operator feedback** during testing: the IND_TX_BLIP "every Headless TX"
  visual fired for routine SYNC keepalive (every 30 s) and scene
  broadcasts, drowning out the user-relevant "I'm pairing a device" cue.
* **Fix**: `IND_TX_BLIP` renamed to `IND_PAIRING_TX` (enum value 5
  unchanged — wire-stable). Catalog label "Pairing TX". Only SET_GROUP
  sends arm the indicator (`armBlip=true` in `headlessAssignGroupTo` and
  `serviceHeadlessReassign`); all other paths (probe / scene / SYNC /
  brightness broadcast) pass `armBlip=false`. Throttle and duration
  constants renamed in lockstep (`HEADLESS_PAIRING_INDICATOR_*`).
* Operator-visible: a green-cyan flash on the master now reliably means
  "this device is configuring a slave right now."

### Auto-scene-rebroadcast after pairing (new behaviour)

* When a slave joins (proactive boot-burst OR individual reactive pairing)
  the master now automatically broadcasts the current scene once, 1 s
  after the last successful `SET_GROUP` in the burst. Freshly bound
  slaves snap to the master's visual state instead of staying on their
  boot color until the operator next changes the scene.
* Debounced (1 s window) so a burst of pairings collapses to a single
  `OPC_HEADLESS` packet — a 10-slave boot burst produces one scene
  packet, not ten.
* No-op when the master has no current scene yet
  (`currentSceneIdx == 0xFF`) — operator picks a scene via 1-click first.
* New state struct `RaceLinkHeadless::SceneRebroadcastState` + helpers
  `scheduleSceneRebroadcast` / `sceneRebroadcastReady` /
  `sceneRebroadcastConsumed` (header-side).

### Header refactor — `racelink_headless.h` is the WLED-neutral home

A second pass after the bug fixes moves all WLED-neutral headless
operations into `racelink_headless.h` as `RaceLinkHeadless::` free
functions + state structs. The `UsermodRaceLink` wrappers in
`racelink_wled.cpp` become thin — they consult the header decision
helpers and execute the WLED-coupled side-effects (`configNeedsWrite`,
`applyLocalIndicatorMs`, `headlessBroadcastCurrentScene`, segment
writes). Specific moves:

| Header export | Replaces |
|---|---|
| `findSlaveIdx` / `upsertSlave` / `clearSlaveTable` (free fns on caller-owned array) | `UsermodRaceLink::findSlaveIdx` / `upsertSlave` / `clearSlaveTable` methods |
| `PersistState` + `markPersistDirty` / `persistDebounceElapsed` / `persistConsumed` | bare `headlessPersistDirty` + `lastSlaveTableMutMs` fields |
| `SceneRebroadcastState` + `scheduleSceneRebroadcast` / `sceneRebroadcastReady` / `sceneRebroadcastConsumed` | bare `pendingSceneRebroadcastAtMs` field |
| `ReassignState` + `startReassign` / `pickReassignTarget` / `reassignSweepCompleted` / `confirmReassignSent` / `deferReassignRetry` / `abortReassign` | bare `reassignCursor` + `reassignNextSendAtMs` fields |
| `shouldFirePairingBlip(lastAtMs, now, throttleMs)` | inline ternary in `headlessSendTx` |
| `reserveNextGroupId(counter)` | inline clamp + bump in `headlessAssignGroupTo` Case B |

External Gateway-side software (FPVGate etc.) can include
`racelink_headless.h` and reuse the same state machines byte-identically.
No API changes for WLED-side callers; the methods that survived
(`headlessAssignGroupTo`, `serviceHeadlessReassign`, etc.) keep their
signatures.

### Wire protocol

* `PROTO_VER_MAJOR/MINOR` unchanged. All changes are firmware-internal
  behaviour fixes + a renamed (but wire-stable) indicator ID.

### Docs

* Updated: [`RaceLink_WLED/operator-setup.md`](RaceLink_WLED/operator-setup.md)
  §"Persistence" → 500 ms re-bind interval explanation, retry-on-busy
  guarantee, new "Auto-scene-rebroadcast after pairing" paragraph, new
  "Master self-sync on broadcast" paragraph. Indicator catalog row for
  `IND_PAIRING_TX` clarified (discrete flashes per SET_GROUP given the
  current 500 ms spacing).
* Updated: [`RaceLink_Host/developer-guide.md`](RaceLink_Host/developer-guide.md)
  §"Persisting Headless-Master state across reboots" — interval bump,
  scene-rebroadcast rule, master self-sync invariant, "Where the headless
  state lives" table mapping each `racelink_headless.h` export to its
  purpose. **New section**: §"Time-critical TX via
  `scheduleSend(rl, buf, len, jitterMaxMs=0)`" documents the unified
  bypass contract + cross-repo invariant.

Notes:

* **No operator action required.** Existing devices upgrade transparently.
* **Coordinated firmware sync recommended** for the SYNC-precision fix
  to benefit cross-repo: the Gateway + Host copies of
  `racelink_transport_core.h` need the same `scheduleSend()` body sync,
  and Gateway's `rl_queueTxNoCad()` can simplify to a one-liner once
  done. WLED-side changes work standalone.

## 2026-05-19 — Host: faster OTA error path + live error detail + Total-Time badge

Field feedback on the firmware-update workflow surfaced three
operator pain-points after a device fails: the WebUI took ~11 s
to move on after an unresponsive device, the live row only said
"error" with no clue *why*, and the post-run summary line started
with `RuntimeError:` (a Python class-name that read as a separate
kind of failure). The summary phase also lacked a final total-time
readout, and the live ETA timer started ahead of 0:00 on hosts
without NTP sync. All five fixed in one pass, no wire-protocol or
operator-action changes.

### Faster failure path (was ~11 s, now ~3 s)

* **AP-Enable retries**: the per-device `OPC_CONFIG 0x04 data0=1`
  ACK wait switched from a single 8 s attempt to `1.5 s × 2`
  attempts (1 retry). Healthy devices ACK in < 1 s on the first
  attempt; the retry recovers a single dropped frame without paying
  the legacy 8 s penalty. On a fully unreachable device the
  workflow now gives up after ~3 s instead of 8 s.
* **AP-Close gated on the error-after-AP-open case only.** A
  successful firmware POST triggers a WLED reboot that drops the
  AP automatically — sending an explicit AP-Close into the reboot
  window timed out for 3 s per device for nothing. The cleanup
  call is now wired to a local `ap_opened` flag and a check on
  `dev_res["ok"]`: it runs **only** when AP-Enable ACKed *and* a
  later step failed (wrong OTA password, bad firmware binary,
  HTTP 401 / 500 / timeout, …) so the device's still-broadcasting
  AP doesn't leak its credentials. Clean-success and never-opened
  paths both skip it. The AP-Close itself was also tightened to
  the same `1.5 s × 2` shape.

### Live error detail (no more waiting for the summary to find out why)

* **`device_messages` meta companion to `deviceState`.** The OTA
  workflow now publishes a parallel MAC → message map every time
  it emits a stage event. On the per-device `except` path the map
  gets the concrete failure string (e.g. `Timeout waiting for
  CONFIG ACK from <MAC> (AP-enable)`); `FwProgressPanel.vue` reads
  it directly and shows the message inline on the red row instead
  of the generic "error" label. The end-of-run `result.errors[]`
  overlay is still applied at task end as a defence-in-depth fallback,
  but it's no longer the *only* surface that carries the detail.
* **`RuntimeError:` class-name prefix dropped** from operator-
  visible strings (`dev_res["error"]`, `result.errors[]`, the
  `DEVICE_ERROR` SSE event). All four sites in
  `ota_workflow_service.py` now use `str(ex) or type(ex).__name__`
  — same fallback for exceptions with an empty `__str__` (rare;
  some C-API errors), without the Python-jargon prefix on the
  common case.

### Total-time + timer-start fixes

* **`Total time: M:SS` badge** in the summary panel, computed from
  the task snapshot's `started_ts` / `ended_ts` via the existing
  `formatMmSs` helper. Hidden if either edge is missing.
* **Server-computed `elapsed_s`** added to every task snapshot
  (`TaskManager.snapshot()` in `racelink/web/tasks.py`). Frontend
  `useFwLiveTimer` switched from `Date.now()/1000 - started_ts`
  (which exposed host-vs-browser clock skew as a constant offset
  on the live ETA) to anchoring on the server-supplied `elapsed_s`
  + local-tick accumulation between SSE pushes. Hosts without NTP
  sync no longer make the timer start at "0:07 · ~0:23 left" on a
  single-device run. The change is generic (not OTA-specific) —
  any future long-running task gets the field for free.

### Files

* **RaceLink_Host (OTA workflow)** —
  [`racelink/services/ota_workflow_service.py`](https://github.com/PSi86/RaceLink_Host/blob/main/racelink/services/ota_workflow_service.py):
  AP-Enable retry loop, `ap_opened` flag + conditional AP-Close
  block, `device_messages` dict + `_meta_base` snapshot field,
  `str(ex) or type(ex).__name__` at all four error sites.
* **RaceLink_Host (task framework)** —
  [`racelink/web/tasks.py`](https://github.com/PSi86/RaceLink_Host/blob/main/racelink/web/tasks.py):
  `snapshot()` adds the top-level `elapsed_s` field.
* **RaceLink_Host (WebUI)** —
  [`frontend/src/composables/useFwTimer.ts`](https://github.com/PSi86/RaceLink_Host/blob/main/frontend/src/composables/useFwTimer.ts):
  `useFwLiveTimer` rewired to consume `serverElapsedS` (anchor +
  1 Hz local ticks). [`FwProgressPanel.vue`](https://github.com/PSi86/RaceLink_Host/blob/main/frontend/src/components/modals/FwProgressPanel.vue):
  `meta.deviceMessages` overlay on `state === 'error'` rows, timer
  wiring updated.
  [`FwUpdateDialog.vue`](https://github.com/PSi86/RaceLink_Host/blob/main/frontend/src/components/modals/FwUpdateDialog.vue):
  `summaryDurationLabel` computed + Total time badge.
  [`api/types.ts`](https://github.com/PSi86/RaceLink_Host/blob/main/frontend/src/api/types.ts):
  `TaskSnapshot.elapsed_s` and `TaskMeta.deviceMessages` declared.
* **Docs** —
  [operator-guide § Firmware updates](RaceLink_Host/operator-guide.md#firmware-updates-take-minutes-let-them-finish)
  documents the new AP-Enable retry semantics, conditional AP-Close,
  live error messages, and Total-time badge.
  [developer-guide § Host-side per-device cleanup contract](RaceLink_Host/developer-guide.md#host-side-per-device-cleanup-contract)
  pins the three semantics (retries, conditional close, two-track
  error surface).
  [reference/sse-channels § task event](reference/sse-channels.md)
  updated with the `elapsed_s` and `deviceMessages` shapes.

### Operator action

None. Existing fleets work unchanged; the changes are pure
backend/frontend polish.

## 2026-05-18 — WLED: persistent boot colour + Headless-master slave registry + pairing-TX indicator

Three coordinated WLED-firmware changes that close long-standing gaps
in node identity persistence and Headless-Mode reboot behaviour, plus
a visible "I'm transmitting" cue for the Headless Master. All entries
are additive in cfg.json (new keys default to safe values) and wire-
neutral; mixed pre/post fleets interoperate byte-for-byte.

### Persistent per-device boot colour

* The boot-time R/G/B pick is now rolled **once** on the very first
  boot (`esp_random() % 3`) and immediately persisted to `cfg.json`
  under four new `RaceLink.overrides` keys: `Boot Color Mode`
  (0 = red, 1 = green, 2 = blue, 3 = stored RGB),
  `Boot Color R`/`G`/`B`. Every subsequent boot reuses the stored
  value — a device always lights up in the same colour until the
  operator changes it.
* The physical-button click cycle now **double-duties as a boot-
  colour editor**: 10 s after the last click, the currently-
  displayed colour is written back as the new boot colour. A random
  RGB picked at the end of the cycle is stored verbatim as a 3-byte
  triple and re-applied exactly at the next boot. Mode 3 is the
  "stored random" path.
* `SCENE_RESTORE_BOOT_COLOR` (Headless catalog row, `OPC_HEADLESS`
  scene id 4) replays the persisted colour via the same code path
  used at boot, dropping the previous "re-roll if uninitialized"
  fallback — `setup()` now guarantees the mode is always in 0..3.
* New helper `applyBootColor()` replaces the previous
  `showBootRandomColor()` (which was "roll + paint + remember for
  this session"); the new helper is purely "paint the persisted
  colour".
* Operator-visible side effect on fleet identity: 10 devices flashed
  at the same time, even if their first-boot rolls were biased
  (`esp_random()` quality early in `setup()` before WiFi/BT is
  active is undefined per ESP-IDF), now lock in their colours
  permanently after the first power-up. Operators can re-balance
  the fleet manually via the button cycle.

### Headless Master — persistent slave registry + Group-id layout

* The Headless Master now keeps a **persistent registry of up to 40
  `(addr3, groupId)` records** in `cfg.json` under new key
  `RaceLink.overrides["Headless Slaves"]` (JSON array of
  `{"a": "AABBCC", "g": 2..254}` objects). Survives reboot and
  battery swap; cleared by `exitHeadlessMode()`.
* **Group-id layout fix.** `HEADLESS_FIRST_GROUP_ID` was 1; the
  master conceptually owned no group. Now: `HEADLESS_MASTER_GROUP_ID
  = 1` (set on entry, cleared on exit), `HEADLESS_FIRST_GROUP_ID =
  2` (first id ever assigned to a slave). Group 0 = unconfigured
  pool, Group 255 = broadcast pseudo-group — both unchanged.
* **Proactive re-bind on resume.** After auto-resume probe + `enter
  HeadlessMode()`, the master sweeps its registry and sends one
  `OPC_SET_GROUP` per known slave with 50 ms spacing
  (`HEADLESS_REASSIGN_INTERVAL_MS`). Slaves that did not power-cycle
  alongside the master (typical: battery-powered race lights staying
  on through a master swap) regain their pairing without having to
  re-emit `IDENTIFY_REPLY`. A full 40-slave sweep takes ~2 s, visible
  to the operator as a continuous green-cyan `IND_PAIRING_TX` overlay.
* **`headlessAssignGroupTo()` rewrite.** Two clean cases:
  Case A (slave already has a non-zero groupId): mirror into the
  registry, send no packet — overwriting a working pairing would
  risk collisions. Case B (slave reports `groupId = 0`): if the MAC
  is already in the registry, recycle the stored id without bumping
  the counter; otherwise pull the next free counter slot and store
  the pair.
* **Flash-wear debounce.** Pairing-burst events used to fire one
  `cfg.json` save per slave (40 slaves → ~80 saves / 30 s). The new
  `markHeadlessPersistDirty()` / `serviceHeadlessPersist()` pump
  collapses a 40-slave burst into a single save 5 s after the last
  mutation (`HEADLESS_PERSIST_DEBOUNCE_MS`). Other save paths
  (`OPC_CONFIG`, WebUI Save, `exitHeadlessMode`) continue to write
  synchronously.
* **`exitHeadlessMode()`** now clears `Headless Group Counter`,
  `current.groupId`, and the entire slave registry, and forces a
  synchronous write so a battery pull immediately after the 5-click
  cannot leave stale state on flash. Runtime-override paths
  (Gateway takeover, autosync detection) leave the registry intact —
  involuntary demotions preserve the data for a possible later
  manual re-promotion.

### Pairing-TX indicator (`IND_PAIRING_TX`)

* New entry in the indicator catalog (`racelink_indicators.h`),
  append-only ID `5`. Green-cyan STROBE `0x00FF40`, speed 248
  (between informational 245 and alert 250), intensity 96 / brightness
  200 (shorter on-pulse, lower glare during 40-slave re-bind bursts).
* **Local-only** — never wire-triggered. Fires through a single
  chokepoint wrapper `headlessSendTx()` with a 200 ms throttle
  (`HEADLESS_PAIRING_INDICATOR_THROTTLE_MS`) and a 1500 ms display
  window (`HEADLESS_PAIRING_INDICATOR_DURATION_MS`).
* **Trigger scope is narrowed to SET_GROUP sends only.** The
  indicator fires for new-device pairings (`headlessAssignGroupTo`)
  AND for every send during the post-reboot re-bind sweep
  (`serviceHeadlessReassign`) — both are SET_GROUP TXes that the
  operator reads as "the master is configuring a slave right now."
  Routine traffic (scene broadcast, brightness broadcast, 30 s SYNC
  keepalive, IDENTIFY_REPLY probes) explicitly passes
  `armBlip = false` and produces no flash. This keeps the visual
  signal semantically clean: a blink means pairing, silence means
  routine operation.
* The 200 ms throttle prevents back-to-back SET_GROUPs from re-
  extending the indicator deadline into a sustained overlay; a
  40-slave re-bind sweep reads as one continuous flash rather than
  a flicker storm. An isolated single-slave pairing reads as one
  visible 1.5 s flash.
* New helper `applyLocalIndicatorMs(type, durationMs)` added on the
  WLED side for sub-second triggers; the seconds variant
  `applyLocalIndicator()` remains and is still used by the five
  existing indicators.

### Wire protocol

* `PROTO_VER_MAJOR/MINOR` unchanged. `IND_PAIRING_TX` is append-only and
  never travels on the wire; older firmware silently drops unknown
  indicator types. The new `Headless Slaves` cfg.json key is read-as-
  empty by pre-change firmware (treated as "no registry"), so a
  mixed-firmware operator path is benign.

### Docs

* New: [`RaceLink_WLED/operator-setup.md` §"Persistent boot colour"](RaceLink_WLED/operator-setup.md#persistent-boot-colour)
  and §"Group-id layout".
* Updated: [`RaceLink_WLED/operator-setup.md`](RaceLink_WLED/operator-setup.md)
  §"Boot effect", §"Click colour cycle" (save-on-idle), §"Indicators"
  → Catalog (added `IND_PAIRING_TX` row), §"Headless Mode" → Activating,
  Pairing slaves, Stepping down, Persistence (added `Headless Slaves`
  row + debounce + proactive re-bind paragraphs).
* Updated: [`RaceLink_Host/developer-guide.md`](RaceLink_Host/developer-guide.md)
  §"Adding a new Indicator to the catalog" (sub-second triggers +
  throttle pattern). New: §"Persisting Headless-Master state across
  reboots" — the five cardinal rules for the slave-registry / debounce
  / sync-exit / proactive-rebind / group-id discipline patterns.
* Updated: [`glossary.md`](glossary.md) §"Boot effect" (persistence)
  and §"Headless Mode" (Group 1 = master, Group 2 = first slave,
  persistent registry, proactive re-bind).

Notes:

* **No operator action required for existing fleets.** A previously
  flashed device upgraded to this firmware reads defaults for all new
  cfg.json keys (`Boot Color Mode = 0xFF` → first boot is treated as
  fresh and rolls + saves; `Headless Slaves = []` → registry empty,
  next promotion starts from a clean slate). The first slave paired
  under the new firmware on an upgraded master will be assigned to
  Group 2 (was Group 1 under the previous firmware). Pre-existing
  pairings continue to work via the idempotent Case A path; the
  in-flight group id is whatever was assigned originally.
* **Coordinated flash not required.** Slaves are agnostic to the
  master-side changes — `OPC_SET_GROUP` semantics on the wire are
  unchanged. A mixed-firmware fleet (new master, old slaves) operates
  identically to a full-new fleet for everything visible on the wire.

## 2026-05-17 — Indicator catalog + overlay-rendering refactor + host UI polish

A multi-thread session that landed the operator-facing
"Click-to-Locate" feature on the host, then iteratively cleaned
up rendering side effects, naming collisions, and a couple of
unrelated UX papercuts. All entries below ship from the same
date.

### Indicator catalog — standardisation
* **STROBE-only.** Every catalog row now uses fxMode 23 (STROBE);
  BREATH retired for indicators (too subtle in race environments).
* **Urgency-coded speed (3 tiers within WLED-effective range 235..252):**
  235 = slow / positive event, 245 = medium / informational /
  operator action, 250 = fast / error.
* **Semantic colour palette** (channel-dominance scheme):
  `IND_PAIR_CONFIRMED` → bright teal `0x00FFAA` (success),
  `IND_HEADLESS_ENTER` → ice cyan `0x00CCFF` (promotion),
  `IND_HEADLESS_EXIT` → amber `0xFFAA00` (demotion),
  `IND_IDENTIFY` → magenta `0xFF00CC` (operator-locate, new row),
  `IND_PROBE_REJECTED` → red-orange `0xFF3300` (error).
* `IndicatorDef.intensity` and `.brightness` pinned to 128 / 230
  for every row. New rows must obey the same spec, documented in
  the header comment above `INDICATOR_CATALOG[]`.

### Indicator rendering — frame-buffer overlay
* The WLED usermod now renders indicators via
  `Usermod::handleOverlayDraw()` (called by `setShowCallback`
  after every segment effect has been blended into the strip
  frame-buffer, immediately before `strip.show()`).
* The previous implementation `setMode(STROBE)` + snapshot/restore
  is **gone**. Three prior bug-fix layers are obsoleted by the
  rewrite:
  - palette / `colors[1]` / `colors[2]` leak from the prior
    effect (FX.cpp `mode_strobe` resolves the on-phase via
    `color_from_palette`);
  - `SEGENV` reset on `setMode()` — time-driven effects like
    Traffic Light lost their phase reference;
  - `SEGENV.data` heap lifecycle on mode-switch.
* Overlay writes go through `strip.setPixelColor(absolute_idx, c)`
  not `seg.setPixelColor` — segment-relative writes after
  `blendSegment` land in a dead buffer that is never pushed to
  hardware (one-iteration debug detour worth remembering).
* `IndicatorState` shrank from 13 snapshot fields to 5 runtime
  fields (`active`, `expiresAtMs`, `activeColor1`,
  `activeSpeed`, `activeBrightness`).
* `applyLocalIndicator()` and `serviceIndicator()` no longer
  touch the segment at all; preemption is just an `active = false`.
* **Fleet phase sync is preserved automatically** — the
  underlying effect is never interrupted, so `SEGENV.step` /
  `aux0` advance during the overlay and the device is in fleet
  phase the instant the overlay clears.

### Host — `OPC_INDICATE` end-to-end
* New `racelink/domain/indicators.py` Python mirror of the
  catalog `IndicatorType` IntEnum (`IDENTIFY = 4`) plus
  `DEFAULT_INDICATE_DURATION_SEC = 5`.
* New endpoint **`POST /api/devices/indicate`** (was briefly
  named `/api/devices/identify` earlier the same day — renamed
  to avoid colliding with `OPC_DEVICES` RF-discovery
  terminology; operator-facing UI verb is "Locate").
* Service hook: `ControlService.send_device_indicate()` →
  `GatewaySerialTransport.send_indicate()` →
  `_send_m2n(OPC_INDICATE, recv3, body)` via the standard
  preset/control pipeline.
* Wire-builder: `racelink/protocol/packets.py::build_indicate_body()`.
* UI: clicking the device name in `DeviceTable.vue` (when not in
  rename-edit mode) and the per-row "Locate" button in
  `BatteryDevicesDialog.vue` both POST the new endpoint. Both
  sites share an `indicating: Set<string>` debouncer and the
  same "Locating …" / "Locate failed …" toast wording.
* UI conventions doc (`RaceLink_Host/ui-conventions.md`) gained
  a new "Click-to-locate (Indicate)" section and a `Locate`
  entry in the verb vocabulary.

### Host — Gateway-banner / MasterBar UX cleanup
* The MasterBar pill now shows `ERROR` (red) whenever
  `gateway.gateway.ready === false`, even if no firmware-side
  `STATE_REPORT` reached the host. Eliminates the desync where
  the red banner said "Gateway link lost" while the pill still
  showed `IDLE` from before the disconnect.
* The `err:` detail field in MasterBar is now reliably cleared:
  - backend: `TaskManager` clears `master.last_error` on
    successful `TASK_*_DONE` (mirrors `TX_DONE` / device-reply
    semantics elsewhere in `sse.py`);
  - frontend: `gateway.applyGateway()` clears
    `master.last_error` optimistically on a false→true `ready`
    transition.

### Host — Python transport refactor (`LP`)
* `racelink/transport/gateway_events.py::LP` was a hand-maintained
  shadow class over `racelink_proto_auto`; new opcodes silently
  fell out of `LP` until two manual edits per constant were made
  (surfaced at runtime as
  `AttributeError: type object 'LP' has no attribute 'OPC_INDICATE'`).
* Replaced the ~80-line class + override-block with a single-line
  module alias: `from .. import racelink_proto_auto as LP`.
  Every wire-protocol constant + the `make_type` helper that
  ships in the auto-mirror is now automatically visible — adding
  a new opcode requires only the
  `gen_racelink_proto_py.py` regen, no Python-side edit.
* `tests/test_lp_matches_proto_auto.py` pins the contract so a
  future refactor that re-introduces a class shadow without
  mirroring the auto-symbols fails fast in CI.

### Host — FW update timer
* Per-device estimate bumped from 21 s to **30 s** to match what
  operators consistently observe in the field (slower nmcli
  reconnects + occasional reflash retries push the realistic
  mean higher than the historical median suggested).
* Fixed the post-first-device countdown bug: the previous
  `avg = elapsed / completed` recalculation each tick caused the
  remaining time to **count up** (the still-running current
  device's accruing time bled into the average). The observed
  average is now **frozen at each `deviceIndex` advance** in a
  `watch`, so `remaining = avg × total - elapsed` counts down
  monotonically at 1 s/s between completion boundaries.

### Cross-repo drift
* `tests/test_proto_header_drift.py` was already extended to
  cover `racelink_headless.h` and `racelink_indicators.h`
  alongside `racelink_proto.h`; all four sibling-repo copies
  ride the same hash through every iteration of this session.

## 2026-05-17 — Wire: rename `OPC_SCENE` → `OPC_HEADLESS`

Identifier-only rename of yesterday's new opcode and its body struct.
**The wire byte value (`0x0B`) and body layout are unchanged** — mixed
binaries built before and after this rename interoperate byte-for-byte.

* **All three component repos must sync `racelink_proto.h`** so the C
  identifier matches; the Host's `gen_racelink_proto_py.py` re-run will
  bubble the new constant into `racelink_proto_auto.py` automatically.
* **Body struct renamed in lockstep**: `struct P_Scene` →
  `struct P_Headless`. Field name `sceneId` is **kept** (catalog rows
  are internally still called "Headless scenes").
* **Builder function renamed**: `RaceLinkHeadless::buildScenePacket()`
  → `RaceLinkHeadless::buildHeadlessPacket()`. Same signature, same
  emitted bytes.
* **Internal catalog terminology unchanged**: `HeadlessSceneId`,
  `HeadlessScene` struct, `SCENE_CATALOG[]`, `SCENE_OFFSET_BREATHE` /
  `SCENE_SOLID_RED` / … enum values, `SCENE_FLAG_*`, `findSceneById`,
  `nextSceneIdx`, the cpp methods `applyLocalScene` /
  `headlessBroadcastCurrentScene` / `headlessAdvanceScene` and the
  cfg.json keys (`"Headless Current Scene"` etc.) all keep their
  current names. The rename is scoped to the wire surface — the
  Headless module's internal vocabulary stays as "scene" because each
  catalog row IS a "Headless scene", and the namespacing
  (`RaceLinkHeadless::…`) already disambiguates it from any future
  host-level RaceLink-Scene concept.

**Motivation.** Today's host-side **RaceLink Scenes** travel as
`OPC_CONTROL` on the wire. A future refactor may give them a dedicated
opcode named `OPC_SCENE` — exactly the name yesterday's Headless-Mode
trigger had grabbed. Renaming today removes the collision before either
side has shipped to operators, so the eventual host-side `OPC_SCENE`
can adopt that wire surface without further churn.

**Coordinated update required across the three repos**:

* WLED: header rename + dispatcher + helper call sites + comments;
  4 builds (V1/C3, V3/S2, V3/S2-Epaper, V4/S3) verified clean.
* Gateway + Host: pending — see the follow-up plan in
  `_private/plans/headless-indicators-sync.md` §Step 1 (header sync)
  and §Step 2 (Gateway `OPC_INDICATE` / `OPC_HEADLESS` passthrough).

**Wire protocol** — `PROTO_VER_MAJOR/MINOR` unchanged. Pure
source-level rename; on-wire bytes identical.

## 2026-05-16 — WLED: Headless Mode + central Indicator system

Two coordinated feature waves on the WLED node. **Headless Mode** lets one
physical device be promoted to act as a minimal master for the rest of the
fleet (group assignment, broadcast scenes, brightness control) so a
session can run without a Gateway+Host pair. **Indicators** is the new
centralised, animated, time-limited status-notification mechanism that
now drives every visual status cue on the node (pair-confirmation, probe
rejection, headless enter/exit) via a single shared catalog + overlay
machine.

Both features add new wire opcodes (`OPC_HEADLESS = 0x0B`, `OPC_INDICATE =
0x0C`) and two new shared header files (`racelink_headless.h`,
`racelink_indicators.h`) — WLED-neutral by design so the Gateway, Host
and external Gateway-side software (e.g. FPVGate) can include them
unchanged.

### Headless Mode

* **RaceLink_WLED** — five-click on the boot/user button promotes the
  device to Headless Master after a 1.5-second IDENTIFY_REPLY probe.
  Any incoming M2N traffic during the probe (typically `OPC_SET_GROUP`
  in response to the broadcast) refuses the promotion (red strobe
  indicator). Persisted across reboots: a power-cycled headless master
  re-runs the probe at boot, so a real Gateway that came back up
  while the device was off correctly overrides the headless mode via
  `OPC_SET_GROUP` (or via any subsequent `OPC_SYNC` it autosyncs).
* **Wire surface** — `OPC_HEADLESS` carries `{type: u8, brightness: u8}`;
  receivers expand the scene-id via the shared catalog in
  `racelink_headless.h` (`SCENE_OFFSET_BREATHE`, `SCENE_SOLID_RED`,
  `SCENE_SOLID_GREEN`, `SCENE_ALL_OFF`, `SCENE_RESTORE_BOOT_COLOR`).
  Per-group phase offset for staggered scenes (offset breathe) is
  computed receiver-side from `base + groupId * step` so only one
  packet flies per scene click — no separate `OPC_OFFSET` pre-emit.
* **Master role on the device** — group assignment is automatic
  (counter persisted in `cfg.json`, wraps at 254); a 30-second
  `OPC_SYNC` autosync keepalive anchors slave timebases and keeps the
  fleet's master-quiet gate closed. Long-press on the headless master
  drives a non-linear S-curve brightness fade locally; the final value
  is broadcast exactly once on release as `OPC_CONTROL` with
  `RL_CTRL_F_BRIGHTNESS`. No per-tick TX during the fade.
* **Gateway always wins (runtime override)** — the master-alive
  detector in `handlePacket` treats any M2N packet from a non-self
  sender as proof that a real master is on the channel. During
  probing → refuse promotion. During active headless → step down
  immediately (preempts the OPC_HEADLESS keepalive, the device becomes
  a regular slave again). Removes the previously possible "two
  simultaneous masters on the channel" race window.
* **Click dispatch** tightened: `clicks == 3` is now exact for AP
  recovery (was `>= 3`, which let an overshot 6-click accidentally
  open the AP instead of toggling headless). `clicks == 4` and
  `clicks >= 6` are explicit typo-guards.

### Indicators

* **RaceLink_WLED** — new central status-notification mechanism.
  `OPC_INDICATE` carries `{type: u8, durationSec: u8}`; receivers
  look the type up in the shared catalog (`racelink_indicators.h`),
  snapshot the segment, overlay the indicator's mode/speed/intensity/
  color/brightness for the requested duration, and restore the
  snapshot at expiry. New wire commands during the overlay (`OPC_HEADLESS`,
  `OPC_CONTROL`, `OPC_PRESET`) preempt the indicator without restore —
  what comes last wins.
* **Catalog (initial)** — `IND_PAIR_CONFIRMED` (hot pink BREATH, spd
  220), `IND_PROBE_REJECTED` (vivid orange STROBE, spd 240),
  `IND_HEADLESS_ENTER` (ice cyan BREATH, spd 220), `IND_HEADLESS_EXIT`
  (golden yellow BREATH, spd 220). All animated, no pure R/G/B/W —
  project rule. Locally triggered indicators (pair-confirm, probe
  reject, headless enter/exit) run for **5 seconds**; wire-triggered
  duration is whatever the sender carries in the packet.
* **Migration** — `showPairConfirmedEffect()` (persistent white breath
  on `OPC_SET_GROUP`) replaced by `applyLocalIndicator(IND_PAIR_CONFIRMED,
  5)`. The previous 1 Hz red/black probe-reject blink mechanism
  (`btn.blinkFeedbackUntilMs` + `serviceProbeFeedback`) is gone —
  replaced by the indicator system. Net dead-code removal: one
  service method, three `BtnState` fields, one loop call.
* **Duration `0` = cancel** — wire-level escape hatch: a Host can
  send `OPC_INDICATE(any_type, 0)` to clear an active indicator
  without showing a new one.

### Wire protocol

* `PROTO_VER_MAJOR/MINOR` unchanged. Both new opcodes are **additive**
  (`OPC_HEADLESS = 0x0B`, `OPC_INDICATE = 0x0C`) — older firmware not
  built with the catalog headers silently drops the packets via the
  RULES-table length check; no crash, no compatibility break.
* `racelink_proto.h` gains `OPC_HEADLESS`, `OPC_INDICATE`, `P_Headless`,
  `P_Indicate`, two RULES entries and two `static_assert` size checks.
  Two new headers live alongside it: `racelink_headless.h` and
  `racelink_indicators.h` (both WLED-neutral, includable from
  Gateway/Host/FPVGate without pulling in WLED). All three headers
  remain byte-identical across the three component repos —
  `tests/test_proto_header_drift.py` will catch drift once Host +
  Gateway repos sync (planned follow-up).

Notes:

* **No operator-visible behaviour change for Gateway+Host fleets.** A
  device that has never been promoted to headless operates exactly as
  before. The only externally observable wire delta is the new
  pair-confirm indicator's 5-second hot-pink breath replacing the
  previous indefinite white breath. Operators using the visual cue to
  confirm pairing will need to glance within ~5 s rather than rely on
  the cue persisting until the next host command.
* **Coordinated implementation pending** — Gateway-side passthrough
  for `OPC_INDICATE` (USB → LoRa) and Host-side UI triggers (click on
  the low-battery banner, click on a device-name row when not in edit
  mode) are tracked as a follow-up; today only the WLED firmware
  consumes and emits the new opcodes. The plan with concrete touch
  points and a verification matrix is in
  `_private/plans/headless-indicators-sync.md`.
* **Docs.** New: `RaceLink_WLED/operator-setup.md` §"Headless Mode",
  §"Indicators". Updated: `reference/wire-protocol.md` opcode table +
  body layouts; `glossary.md` (Headless Mode, Indicator, OPC_HEADLESS,
  OPC_INDICATE); `STRUCTURE.md` Table 2 + Table 3 for the two new
  shared headers.

## 2026-05-15 — Host: firmware-update workflow stabilised + live ETA

Multi-device OTA used to fail intermittently on the 2nd or 3rd
device of a fleet (NetworkManager re-binding to a previous device's
BSSID, RaceLink radio race between auto-restore and the next
device's AP-Open). The workflow now synchronises around the
standard auto-restore path instead of bypassing it, locks the
WiFi connect to the predicted SoftAP BSSID, and drops stale scan-
cache entries from the BSSID-fallback so NM can't pick a previously-
flashed node's dead AP. A 10-device fleet now finishes in ~3:30 min
with zero retries or recoveries needed.

* **RaceLink_Host (OTA workflow)** — full rewrite of the
  per-device sync sequence: post-upload host disconnect with
  `nmcli -w 0`, wait for `IDENTIFY_REPLY` after the reboot, wait
  for the standard `_restore_known_device_group` worker to push
  `SET_GROUP` and ACK, only then send AP-Close. AP-Close is now
  ACK-blocked instead of fire-and-forget. New workflow-end log
  line `fw-update workflow finished: N/M ok` mirrors the existing
  start line; full per-device result moves to DEBUG.
* **RaceLink_Host (host WiFi)** — `connect_ap` got a 3-stage
  BSSID-selection cascade (predicted → freshly-appeared single
  non-avoid → legacy any-match), driven by a per-call initial
  scan-cache snapshot so stale entries never feed the fallback.
  Pre-emptive `_disconnect_iface_from_ssid` runs once at the top
  of `connect_ap` to release NM's scan-throttle for the duration
  of the scan loop. New `wifi_state_snapshot(iface, candidates)`
  helper logs adapter state + visible APs around every connect
  attempt to make error-path diagnosis tractable.
* **RaceLink_Host (WebUI)** — Firmware Update dialog shows an
  estimated duration next to the Start button before commit
  (`~21 s × <target count>`). The progress panel adds a live
  `elapsed · ~remaining left` timer that self-refines once one
  device completes. The status pill at the top right now reads a
  single-line summary (`fwupdate done · (211.4s) · 10/10 ok`)
  instead of dumping the full per-device JSON.
* **Docs** — [operator-guide § Firmware updates](RaceLink_Host/operator-guide.md#firmware-updates-take-minutes-let-them-finish)
  now lists the full per-device phase breakdown with timings; the
  [webui-guide OTA section](RaceLink_Host/webui-guide.md#firmware-update-ota-dialog)
  documents the new `REANNOUNCE_WAIT` / `AUTORESTORE_WAIT` /
  `AP_CLOSE` stages and the live timer.

## 2026-05-15 — Host: modal-locked long-running dialogs + cooperative task cancel

Long-running operations that previously left the operator without a
status view if the dialog was dismissed mid-flight now lock their
dialog and expose an explicit Cancel button that shows a per-device
summary before allowing the dialog to close. The Wi-Fi-stranding risk
on accidental dismiss / browser back during a firmware update is
eliminated.

* **RaceLink_Host (TaskManager)** — new cooperative-cancel API in
  [`racelink/web/tasks.py`](RaceLink_Host/architecture.md):
  `request_cancel()` sets a `threading.Event` on the currently
  running task, `is_cancel_requested()` is polled by long workers at
  their own cancel points. Snapshot grows a `cancel_requested: bool`
  field so SSE consumers can flip a button to "Cancelling…" without
  waiting for the next state transition. New REST route
  `POST /api/task/cancel` is the single generic cancel endpoint
  (TaskManager runs one task at a time, so no per-task plumbing
  needed).
* **RaceLink_Host (OTA workflow)** —
  [`run_firmware_update`](RaceLink_Host/architecture.md) checks the
  cancel flag **only at device-loop entry** ("finish current device
  cleanly, then break") so the cancel never leaves a half-flashed
  node. The Wi-Fi-restore in the `finally` block runs regardless,
  so cancel cannot strand the host on the device AP. The result
  shape gains `cancelled: bool` and `cancelled_after: int|null`
  (1-based index of the last device that ran to completion).
  `download_presets` gets two cancel-check points (before Wi-Fi
  setup and after AP-connect, before the HTTP GET) and the same
  `cancelled` result field.
* **Frontend (dialog framework)** — new `lockClose` prop on
  `DialogContent` (reka-ui wrapper): when `true`,
  `interactOutside` and `escapeKeyDown` are `preventDefault`-ed and
  the corner X button is hidden. The only way out is an explicit
  in-dialog action (Cancel button, or a Close button on a finished
  summary). Used by all three long-running dialogs.
* **Frontend (composable)** — new
  `useTaskNavigationGuard(isBusy, { reason })` wraps the existing
  `useBeforeUnloadGuard` plus an `onBeforeRouteLeave` hook so
  browser navigation (back/forward, refresh, tab close, in-app
  routes) prompts via the native confirm with the caller's
  reason string while the task is running.
* **Frontend (FwUpdateDialog)** — three-phase state machine
  (`config` → `progress` → `summary`). The progress phase is
  modal-locked; only a Cancel button reaches the close path.
  Summary phase renders ✓ successful / ✗ failed / ⏭ skipped
  device lists, host-Wi-Fi-restore status and workflow-level
  errors. The dialog auto-flips to summary when the task lands in
  `done` or `error`.
* **Frontend (WledPresetsDialog)** — same lockdown pattern for the
  "Download from device" path. Cancel button next to Download
  while running; result line shows the cancelled state inline
  with Wi-Fi-restore note.
* **Frontend (DiscoverDialog)** — lighter variant: outside-click /
  Esc / browser-navigation blocked, but no dedicated Cancel
  button (the scan is 5-30 s and touches no Wi-Fi). Close button
  in the footer is disabled while the scan runs.
* **Wire protocol** — `PROTO_VER_MAJOR/MINOR` unchanged. No
  firmware-side changes.

Notes:

* **No operator action.** Existing saved configs, scenes and Specials
  bindings interoperate unchanged. The only operator-visible delta
  is that "click outside the FW dialog mid-update" no longer
  silently dismisses the status view.
* **Cancel granularity is deliberate.** Cancel waits for the
  current device's flash + verify + reconnect to finish before
  breaking out of the per-device loop, so no node is left in a
  half-flashed bootloader state. Worst-case operator wait after
  clicking Cancel is ~60-90 s (one full per-device round-trip).
* **Test surface.** 748 host tests (12 new); frontend type-check
  / Vitest (61) / production build all clean.

## 2026-05-14 — Host: unified RX reply matcher + single-packet OPC_STREAM

Two coordinated changes that fix the "Startblock Control on a device
with empty slots is silently rejected" bug and clean up the host's
internal split between unicast and broadcast reply-matching primitives.

* **RaceLink_Gateway + RaceLink_WLED firmware** — `OPC_STREAM` now
  accepts a single-packet stream (`totalPackets >= 1`) on both sender
  and receiver. Previously `scheduleStreamSend()` rejected anything
  shorter than two 8-byte chunks (9 B payload), which is exactly the
  region the startblock per-slot payload falls into when a slot has no
  pilot assigned (`[ver][slot][chan2][name_len=0]` = 5 B). The result
  was `EV_TX_REJECTED reason=0xFF` retries for every empty slot in the
  current heat. The fix loosens the sender guard to `totalPackets >= 1`
  and lets the receiver finalize a stream when `start && stop &&
  packets_left == 0` arrive in one frame. Saves ~30-50 ms of time-on-air
  per empty slot at typical LoRa settings (SF7 / BW250).
* **RaceLink_Host (services)** — `PendingRequestRegistry` and the
  parallel `send_and_collect` listener-chain are unified into a single
  `PendingMatcher` + `PendingMatcherRegistry`. One data structure, one
  wait loop, one primitive (`GatewayService.send_and_match`). Covers
  unicast 1-reply, multi-sender N-reply collectors, and wildcard
  discovery via structured filters (sender_filter / expected_opcode /
  expected_ack_of / discriminator). All four call sites
  (`config_service.read_config`, `gateway_service.send_stream`,
  `discovery_service`, `status_service`) and the retry wrapper
  `send_and_wait_with_retries` migrated to it; the legacy
  `send_and_wait_for_reply` and `send_and_collect` methods are removed.
  New developer-guide page:
  [Reply Matching (PendingMatcher)](RaceLink_Host/reply-matching.md).
* **RaceLink_Host (diagnostics)** — the long-standing
  `registry.try_match MISS opc=ACK ... pending_keys=0` debug log that
  fired on every legitimate stream / discovery / status ACK is gone.
  The replacement `NO_MATCH` line only fires when a matcher actually
  had the right bucket key but its full filter rejected the event
  (e.g. a `GET_CONFIG_REPLY` with the wrong `option` byte) — a
  genuinely diagnostic signal.
* **Wire protocol** — `PROTO_VER_MAJOR/MINOR` unchanged. The
  OPC_STREAM ctrl-byte encoding is identical; only the accept/reject
  predicate on both endpoints widened. Mixed-firmware fleets must
  coordinate: old gateway + new node loses 1-packet sends at the
  gateway TX gate; new gateway + old node loses them at the node's RX
  state machine (`start && stop` was a hard error before).

Notes:

* **Coordinated flash required.** The OPC_STREAM single-packet support
  depends on matching firmware on both sides. Roll Gateway and all
  WLED-startblock nodes together. Hosts on either matcher generation
  continue to interoperate with both firmwares (the host change is
  purely internal refactoring).
* **No operator action.** No saved scenes, presets, Specials configs
  or RotorHazard bindings change shape. The MISS-log noise reduction
  is visible to anyone running with DEBUG-level logs; INFO/WARN logs
  are unaffected.
* **Test surface.** 736 host tests; the migration touched the
  registry-internal tests (now exercising the matcher's filters,
  multi-sender collector, idle-timeout, and discriminator routing
  directly) and three integration tests in `test_gateway_service.py`
  that previously called `send_and_collect` or `send_and_wait_for_reply`
  directly.

## 2026-05-07 — RaceLink_WLED: V3↔V4 sync investigation retrospective

A two-day investigation into V3 (ESP32-S2) ↔ V4 (ESP32-S3) phase-sync
drift on sharp-edged effects (Strobe), plus a related "weak Breathe"
symptom on internally-triggered pair-confirmation effects. **Several
speculative code-level patches were tried; none demonstrably solved
the V3↔V4 drift.** The weak-Breathe symptom was identified as
operator-side state divergence (segment geometry on devices was
historically normalized by an auto-applied Boot Preset; removing the
preset exposed the underlying divergence) — a firmware fix is not
needed.

The full retrospective with per-change rollback pointers is at
[`RaceLink_WLED/dev-session-2026-05-sync-investigation.md`](RaceLink_WLED/dev-session-2026-05-sync-investigation.md).

**Speculative patches in the WLED working tree but NOT synced to
`RaceLink_WLED`:**

* ISR-time `millis()` capture in the DIO1 trampoline + propagation as
  `rxAtMs` through the callback chain to `handleSync`. Hypothesis:
  loop-polling latency variance was injecting jitter into the
  soft-sync filter. Hypothesis was wrong — `lastSyncTbErrMs`
  distribution unchanged on affected devices.
* `strip.trigger()` after timebase update in `handleSync` to force
  render-phase realignment to SYNC reception. No visible improvement.
* `buildEffectFullDefaults()` + `applySegmentReplace()` deterministic
  refactor of `showPairConfirmedEffect()` and `applyCycleColor()` —
  every segment field written explicitly to eliminate state leakage
  from prior effects. Did not fix weak-Breathe (operator-side cause).
* `seg.startTransition(0)` cleanup in `applySegmentReplace()` to
  prevent stuck `_oldSegment` blending. No improvement.

**Open hypotheses for future investigation** (if V3↔V4 drift resurfaces):
NeoPixelBus driver / pipeline-latency difference between S2 and S3,
segment-length-dependent rendering anomaly on long-but-mostly-unconnected
strips, master-side TX jitter. Recommended next step: GPIO pulse at
DIO1 ISR + at LED data line edge, two-channel scope between V3 and V4.

## 2026-05-06 — RaceLink_WLED: async ePaper + runtime-configurable pins

Two RaceLink_WLED firmware changes that improve operator ergonomics
without changing the wire protocol or any cross-component contract.

* **Async ePaper rendering.** The GxEPD2 e-paper driver is now driven
  from a dedicated FreeRTOS worker task. Both `epaperInit()` (boot
  screen, ~1 s) and every refresh (~1 s per cycle on the GDEY037T03
  panel) used to block WLED's main loop, freezing LED effects, the
  web UI and LoRa servicing for the duration. The async refactor
  pushes all GxEPD2 calls off the main loop:
  - On ESP32-S3 (dual-core profiles) the worker is pinned to core 0
    so rendering happens fully in parallel with WLED's core-1 loop.
  - On ESP32-S2 (single-core profile, `v3_s2_llcc68_epaper`) the
    worker time-slices with the Arduino loop at the same priority;
    the GxEPD2 BUSY-pin wait already calls `yield()` internally, so
    the loop runs during the dominant ~800 ms panel-busy phase
    instead of being frozen.
  - Public `racelink_epaper.h` API surface (`epaperInit`,
    `setDisplayLayout`, `setPilotSlotData`, `service_epaper`)
    keeps its names; the only signature change is on `epaperInit()`
    (see below).
* **Runtime-configurable pins.** The radio control pins (SCK, MISO,
  MOSI, NSS, DIO1, BUSY, RST) and — on builds compiled with
  `-D RACELINK_EPAPER` — the ePaper bus and control pins
  (SCK, MISO, MOSI, CS, DC, RST, BUSY) can now be overridden via the
  WLED **Config → Usermod Settings → RaceLink** UI. The previous
  `-D RACELINK_PIN_*` and `-D RACELINK_EPAPER_*` build flags become
  *defaults* per build profile rather than hard-coded values, so
  first-boot behavior on every shipping target is unchanged. A
  saved pin change triggers an automatic reboot to re-init SPI on
  the new pins. Pins are now allocated through WLED's PinManager,
  so a conflict with an LED-bus pin fails loudly at `radioInit()`
  time instead of silently breaking SPI.
* **Radio chip family stays compile-time.** SX1262 vs LLCC68 (and
  any future chip choice) is still selected at build time via
  `-D RACELINK_SX1262` / `-D RACELINK_LLCC68` in the relevant build
  profile. Rationale: the underlying RadioLib chip-family APIs
  (SX126x vs SX127x) are not interchangeable at the abstract base,
  and the only intra-family difference between SX1262 and LLCC68 is
  PHY parameter range — which is also intentionally compile-time to
  keep a fleet's PHY settings homogeneous. See the new
  [Radio modules developer guide](RaceLink_WLED/radio-modules.md)
  for the chip-family hierarchy and the path to extend support.

**What breaks.** The `epaperInit()` C++ signature changed from
no-argument to seven pin arguments. Only one in-tree caller exists
(in `racelink_wled.cpp`); no external callers. Operators flashing
the new firmware on top of an existing install keep their
`cfg.json` — pin values fall back to the build-time defaults via
`getJsonValue(...)` when a `pins` / `epaper_pins` block is absent,
matching the previous hard-coded behavior 1:1.

**Documentation.** Two new pages:

* [RaceLink_WLED → Pin configuration](RaceLink_WLED/pin-config.md) —
  operator guide: where the fields appear, default tables per build
  profile, reboot semantics, PinManager conflict troubleshooting.
* [RaceLink_WLED → Radio modules](RaceLink_WLED/radio-modules.md) —
  developer guide: RadioLib class hierarchy, what differs between
  SX126x and SX127x, what an SX127x or SX1268 extension would look
  like.

## 2026-05-04 — Preset terminology cleanup (BREAKING)

Disambiguates the long-standing "WLED Control" vs RL-preset confusion in
the source code. The wire protocol (`OPC_PRESET`, `OPC_CONTROL`) is
unchanged — this release renames host-side / WebUI surfaces only.

* **RaceLink_Host (Specials function)** — the `wled_control` Specials
  function (which was actually the RL-preset picker — operator picks a
  RaceLink-native preset id and the host emits `OPC_CONTROL` with the
  resolved snapshot) is renamed to `rl_preset`. Its operator-facing
  label changes from "WLED Control" to "RaceLink Preset". The classical
  WLED-preset picker (`wled_preset`, `OPC_PRESET`) is unchanged.
* **RaceLink_Host (scene action kind)** — the `wled_control` scene
  action kind (inline effect parameters, no preset id, emits
  `OPC_CONTROL`) is renamed to `rl_effect`. Its `vars` set now mirrors
  the 14-field RL-preset editor schema (`mode`, `speed`, `intensity`,
  `custom1..3`, `check1..3`, `palette`, `color1..3`, `brightness`)
  instead of the misleading `presetId`/`brightness` pair it carried
  before. `rl_preset` (host-side preset lookup) and `wled_preset`
  (classical) are unchanged.
* **RaceLink_Host (service method)** — `ControlService.send_wled_control`
  → `send_control` (matches the `OPC_CONTROL` opcode; not WLED-specific).
  `send_wled_preset` is unchanged (matches `OPC_PRESET`).
* **RaceLink_Host (controller method)** — `Controller.sendWledControl`
  → `sendRlPreset` (Specials/WebUI entry point for the renamed
  `rl_preset` function). The Specials `comm` field now reads
  `sendRlPreset`.
* **RaceLink_Host + RaceLink_RH_Plugin (state_scope tokens)** — the
  legacy union token `state_scope.PRESETS` (and its SSE topic
  `presets`) is removed. Callers must use the §1-introduced
  `state_scope.RL_PRESETS` / `state_scope.WLED_PRESETS` tokens
  instead. Topics fanned out: `rl_presets` and `wled_presets`.

**What breaks.** The on-disk shape of operator-saved scenes and
device-Specials configs changes:

* Saved scenes containing `{"kind": "wled_control"}` actions fail to
  load. Operators must re-save those scenes after the upgrade — the
  WebUI scene editor now offers `Apply RL Effect` (with the 14-field
  parameter form) in their place.
* Saved Specials configs referencing the `wled_control` function key
  fail to load. Operators must re-configure the affected device's
  Specials → WLED → RaceLink Preset entry.
* Any third-party SSE consumer subscribed to the `presets` topic must
  switch to `rl_presets` (RL preset CRUD) and/or `wled_presets`
  (WLED preset upload/select).
* Plugins or scripts that called `Controller.sendWledControl` /
  `ControlService.send_wled_control` must update their call sites to
  `sendRlPreset` / `send_control`. RotorHazard plugin shipping with
  this release is updated in lockstep.

**What does not break.** Wire-format opcodes, body layouts, and packet
identifiers (`OPC_PRESET`, `OPC_CONTROL`, etc.) are unchanged —
RaceLink_Gateway and RaceLink_WLED firmwares interoperate
byte-for-byte with both pre- and post-rename hosts.

## 2026-05-04 — Sidebar group rows: live counts + flash

* **RaceLink_Host (WebUI)** — the sidebar's group list now shows
  **`M / N`** per row — devices currently online out of total
  devices in the group — with a hover tooltip explaining what
  "online" means in this context (replied to the last status
  query or sent an unsolicited `IDENTIFY_REPLY` recently). The
  number is computed client-side from `state.devices`'s
  `online` flag in a single pass; falls back to the server-side
  `device_count` when the device list hasn't loaded yet on
  first render.
* **RaceLink_Host (WebUI)** — group rows now **flash** the same
  way the device-table rows do when any of their devices receives
  data. Driven by the per-group max `last_seen_ts` snapshot, with
  the same first-render-doesn't-flash semantics so a fresh page
  load doesn't strobe the sidebar. CSS `@keyframes rl-row-flash`
  is reused; the new rule is scoped to `.rl-groups li`.
* **Wire protocol** — unchanged (UI-only change).

Notes:

* `loadDevices()` now calls `renderGroups()` alongside
  `renderTable()` so the sidebar tracks SSE refreshes the same
  way the device table does — no extra API calls.

## 2026-05-03 — WebUI: Chrome SSE slot-pool stall fix

* **RaceLink_Host (WebUI)** — fixes a 20–50 s UI freeze that hit
  Chrome (and other Chromium-based browsers) after roughly 5 quick
  switches between `/racelink/` and `/racelink/scenes` via the
  in-page navigation links. The freeze also affected any parallel
  RotorHazard tab on the same origin. F5 reload was always fine;
  Firefox was never affected.
* **Root cause** — Chrome's link-click unload path closed the JS
  `EventSource` but parked the underlying TCP socket "half-finished"
  in its per-origin keep-alive pool (limit 6 sockets). After
  ~5 page switches the pool was saturated; the server's `gen()`
  loop had no quick way to notice that the peer was gone, since
  yielding 7-byte ping frames into a kernel send buffer never
  surfaced a `BrokenPipeError`.
* **Fix is three layers, all in `racelink/`:**
    * `racelink/static/racelink.js` — registers a `pagehide`
      listener that calls `_es.close()` synchronously, forcing the
      browser to release the SSE socket before unload.
    * `racelink/web/sse.py` — the SSE generator's idle ping cadence
      drops from 15 s to **2 s**, so kernel-level disconnects
      surface within seconds on the rare paths where the client
      did not close cleanly.
    * `racelink/web/sse.py` — the SSE response now sends
      `Connection: close` instead of `keep-alive`, signalling
      Chrome to release the socket slot deterministically once the
      stream ends.
* **Wire protocol** — unchanged.

Notes:

* Per-tab egress for the new ping cadence is ~7 B every 2 s
  (≈ 17 B/s for 5 open tabs) — negligible.
* `pagehide` is bfcache-aware: a tab restored from the back/forward
  cache opens a fresh `EventSource` on its normal page-load path.
* See [`reference/sse-channels.md`](reference/sse-channels.md)
  §"Connection lifecycle and Chrome HTTP/1.1 slot pool" for the
  full technical write-up.

## 2026-05-03 — Groups target picker: search dialog

* **RaceLink_Host (WebUI)** — the inline checkbox grid for the
  unified target picker's **Groups** mode is replaced by a
  compact summary chip + a modal selection dialog. The summary
  shows the selected groups in small text together with the
  total group count and total device count across the
  selection, so the operator can scan an action without
  opening the picker. **Edit groups…** opens a dialog with a
  search field (filters by name or id), a scrollable result
  list, and three batch buttons that act on the currently-
  visible hits: **Select all hits**, **Deselect all hits**,
  **Invert hits**. Designed for fleets with many groups where
  the previous flat checkbox row became unwieldy. The save-
  time broadcast-collapse hint moved into the dialog footer.
* **Wire protocol** — unchanged (UI-only change).

Notes:

* No on-disk migration required — scene format unchanged.
* No estimator / runner behaviour change; the dialog edits the
  same `target.kind = "groups"` shape the planner consumes.

## 2026-05-02 — Estimator ↔ runner structural sync

* **RaceLink_Host** — extracted a new pure module
  `racelink/services/dispatch_planner.py` that is now the
  **single source of truth** for "what packets would the runner
  emit for this action". Both the cost estimator and the scene
  runner consume `plan_action_dispatch(action, …) →
  ActionDispatchPlan{ops: List[WireOp], …}`; the runner
  iterates `plan.ops` and dispatches each via a small
  `_dispatch_op` adapter, the estimator iterates the same plan
  and sums `body_bytes` per op. Per-kind logic that used to
  live in two parallel implementations
  (`_resolve_target` / `_resolve_offset_group_child_target` /
  `_send_with_fanout` / `_merge_flags_into_params` /
  `_lookup_rl_preset` / `_dispatch_offset_group_child` on the
  runner; `_target_packet_multiplier` /
  `_estimate_offset_group_cost` /
  `_materialize_rl_preset_params` /
  `_estimate_control_body_len` on the estimator) is now in one
  place. New parity test suite
  (`tests/test_dispatch_parity.py`) runs every action shape
  through (planner, estimator, runner-with-recording-stubs)
  and asserts identical packet counts + per-op senders + per-op
  addressing — any future drift is caught at CI time.
* **RaceLink_Host** — bug fix: the API's
  `_known_group_ids_from_ctx()` had a stray `.controller`
  indirection that silently returned `[]`, closing the
  optimizer's Strategy-C gate and making the cost badge
  under-report by reaching for Strategy B (per-group EXPLICIT)
  where the runtime actually emitted Strategy C (broadcast
  formula + sparse NONE overrides). Reproducer scene from the
  bug report — 7-of-10 sparse linear `offset_group` with one
  broadcast child — pre-fix reported 8 packets / 121 B;
  post-fix correctly reports 5 packets matching the wire.
* **Wire protocol** — unchanged. `WireOp` was extended with
  optional `sender` and `detail` fields (additive, default-
  valued, back-compat).
* **Sync body sizing** — incidental fix surfaced by the
  unification: the estimator was sizing OPC_SYNC with
  `flags=0` (4-byte legacy form). The runner has always sent
  `trigger_armed=True` (5-byte form). The planner now sizes
  with `SYNC_FLAG_TRIGGER_ARMED` so the cost badge matches the
  wire.

Notes:

* No on-disk migration required — scene format unchanged.
* Operator-visible behaviour change: the cost badge in the
  scene editor is now accurate for sparse-subset offset_group
  containers. No other UI changes.

## 2026-05-01 — Broadcast / target-picker unification

* **Docs** — new
  [Broadcast Ruleset](reference/broadcast-ruleset.md) page (full
  per-opcode rules across Host / Gateway / WLED) and a
  [Roadmap](roadmap.md) page recording the two future-feature
  commitments (capability-agnostic broadcast addressing,
  group-agnostic re-identification). Glossary, scene-format,
  operator-guide, webui-guide, RH-plugin operator-setup,
  opcodes, and contributing all updated to the unified
  vocabulary.
* **RaceLink_Host** — unified `target` shape across every action:
  `{kind: "broadcast"} | {kind: "groups", value: [...]} |
  {kind: "device", value: "<MAC>"}`. The pre-unification
  shapes (`scope`, singular `group`, standalone `groups` field
  on `offset_group`) are migrated on read. Save-time
  canonicalisation collapses "every known group selected" →
  `broadcast` so the runtime / cost-estimator pair agrees on
  optimizer Strategy A. Scene-editor exposes the unified
  three-radio picker (Broadcast / Groups / Device) everywhere,
  replacing the previous mix of "Group/Device" radios + "All
  groups" checkbox + multi-select + "Scope (broadcast)" radio.
  Tests cover the migration shims and the
  `device.groupId`-pinned single-device emission rule.
* **Wire protocol** — `PROTO_VER_MAJOR/MINOR` unchanged; this
  is a host + UI change only.

Notes:

* No on-disk migration step required — old persisted scenes
  load as-is and are rewritten on next save.
* Operator-visible behaviour change: top-level effect actions
  now offer a **Broadcast** option that wasn't there before.
  Selecting every known group in the **Groups** picker shows a
  hint that it will save as Broadcast (so a future-added group
  is also hit) — see
  [operator-guide §"The target picker"](RaceLink_Host/operator-guide.md#the-target-picker-broadcast--groups--device).

## 2026-04-30 — Documentation consolidation

* New: consolidated `RaceLink_Docs` collection (this set).
* No code or wire-protocol changes.

## Unreleased / in progress

* (placeholder)

---

## Template for new entries

```markdown
## YYYY-MM-DD — <release name or component>

* **<Component>** vX.Y.Z — <one-line summary>
  * <bullet of what changed>
  * <bullet of what changed>
* **Wire protocol** — `PROTO_VER_MAJOR/MINOR = X.Y` (no change / +N)

Notes:

* <any cross-component coordination required>
* <any breaking change or migration step the operator must take>
```

## Useful queries

GitHub releases per repository (manual links):

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
