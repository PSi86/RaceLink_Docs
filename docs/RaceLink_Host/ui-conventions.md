# RaceLink UI Conventions

One-page contributor reference for the conventions used across the
RaceLink WebUI ([racelink.html](../racelink/pages/racelink.html), the
scene editor at [scenes.html](../racelink/pages/scenes.html), and any
future pages). Pinning these here so a contributor adding a button
doesn't have to reverse-engineer the existing pages to stay
consistent.

An internal review flagged button labels as the single most-mixed
operator-facing surface in the project. This doc is the response.

## Button vocabulary

Pick the most specific verb that fits. Don't invent new verbs without
adding them here.

| Verb         | Use when                                                             | Example                          |
|--------------|----------------------------------------------------------------------|----------------------------------|
| **Save**     | Persist edits to an *existing* record. Stays on the page / dialog.   | Save scene, Save preset          |
| **Create**   | Make a *new* record. Pair with a "+" affordance on toolbars.         | `+ New` group, `+ New` preset    |
| **Move**     | Mutate group / category membership of a selected set.                | Move selected to group           |
| **Send**     | Dispatch a single command to one device and wait for ACK.            | Send (Node Config), Send special |
| **Locate**   | Fire a transient visual indicator on a device so the operator can spot it physically. | Locate (Battery dialog row)      |
| **Run**      | Execute a saved scene end-to-end.                                    | Run scene                        |
| **Start**    | Begin a long-running workflow (multi-stage, multi-second, async).    | Start (Discover), Start Update   |
| **Re-sync**  | Re-broadcast existing host state to the radio fleet.                 | Re-sync group config             |
| **Apply**    | Settle a configuration change without persistence semantics.         | Apply WLED preset (scene action) |
| **Upload**   | File from the operator's machine to the host.                        | Upload (firmware, presets, cfg)  |
| **Download** | File from a connected device to the host.                            | Download from device             |
| **Delete**   | Destructive remove of a record. Always pair with `confirmDestructive`. | Delete preset, Delete scene    |
| **Remove**   | Take an item out of an *in-memory* list (no persistence yet).        | Remove action from scene draft   |
| **Close**    | Dismiss a modal that has saved or applied; no data loss.             | Close (FW dialog after Done)     |
| **Cancel**   | Abandon a modal in progress; data not yet committed.                 | Cancel (Discover dialog)         |
| **Refresh** / **Reload** | Re-fetch state from disk / device.                       | Reload (Devices page)            |

### Save vs Create

If the same form can do both — like the scene editor — toggle the
button label based on whether the draft has a key:

```js
saveBtn.textContent = draft.key ? "Save" : "Create";
```

### Send vs Run vs Start

* **Send** dispatches one packet to one target and waits for the
  ACK. Operator gets immediate feedback (success / fail toast).
* **Run** is for *scenes*: a saved sequence of actions that fires
  end-to-end.
* **Start** is for long-running multi-stage workflows that have a
  visible progress UI (Discover, Firmware Update). The dialog
  stays open after Start; closing the dialog doesn't cancel the
  task.

### Apply vs Move vs Re-sync

`Apply` lost its grip on a clear meaning during the offset-mode
refactor — too many things were "Apply X". As of the C9 sweep:

* **Move** is for membership changes (devices into groups).
* **Re-sync** is for "broadcast existing config to the network".
* **Apply** is reserved for scene-action *kinds* that semantically
  apply a preset/effect (`Apply WLED Preset`, `Apply RL Preset`).
  These are scene-editor labels, not buttons.

If you find yourself reaching for `Apply` on a button, consider
whether `Send` (single command), `Move` (membership), or `Save`
(persistence) fits better.

## Button visual variants (2026-05-20)

Verbs map to a small set of `<Button variant="…">` styles defined in
[Button.vue](https://github.com/PSi86/RaceLink_Host/blob/main/frontend/src/components/ui/button/Button.vue).
The visual split is intentional: an operator scanning a dialog row
should recognise the action class at a glance.

| Variant       | Used by verbs                                  | Look                                                   |
|---------------|------------------------------------------------|--------------------------------------------------------|
| `brand`       | Save · Create · Apply · Confirm                | Cyan outline, faint cyan fill, cyan text               |
| `run`         | Run · Start · Re-sync · Send · Start update    | Pink→cyan gradient fill, cyan border, light text       |
| `destructive` | Delete (and the confirm CTA of `useConfirm({ variant: 'destructive' })`) | Pink outline, faint pink fill, pink text |
| `secondary`   | Cancel · Close                                 | Neutral filled, low-emphasis                           |
| `ghost`       | Toolbar icon buttons, in-row affordances       | Transparent → secondary on hover                       |
| `outline`     | Rare neutral bordered                          | Border + transparent fill                              |
| `default`     | Fallback (rarely needed now)                   | Solid `bg-primary`                                     |

Rules of thumb when wiring a new button:

* **Pick by verb.** The table above is canonical — if your verb is in
  the [Button vocabulary](#button-vocabulary) section, it has a
  variant. Don't pick by aesthetic.
* **Save and Delete in the same footer** is the canonical pairing —
  cyan outline next to pink outline reads as "commit vs discard".
* **Run / Send share the gradient fill.** They're the only filled
  brand variants. Use the gradient when the operator initiates a
  transient remote operation (RF dispatch, OTA, broadcast). Don't use
  it for persistence operations even if technically they also send to
  the device (operator semantics, not implementation, decides).
* **Data-driven actions** — pick the variant from a `computed()` based
  on the action's stable key, not from the displayed label. See
  [`SpecialsActionRow.vue`](https://github.com/PSi86/RaceLink_Host/blob/main/frontend/src/components/modals/SpecialsActionRow.vue)
  for the pattern (the "Reset to RaceLink defaults" Send button is a
  commit-state action keyed `wled_reset_overrides` and renders as
  `brand` even though every other entry in the same component
  renders as `run`).
* **Variant ≠ confirm flow.** Visual destructiveness (`variant="destructive"`)
  is independent of `useConfirm({ variant: 'destructive', … })`. A
  Delete button is always both; a Re-sync button is `run` visually but
  also triggers a destructive confirm. Don't conflate them.

The full token system, font stack, gradient-hover transition pattern,
and the `--color-card` / `--color-popover` split that supports this
visual language are documented in the Host repo at
[docs/webui-styling-tips.md](https://github.com/PSi86/RaceLink_Host/blob/main/docs/webui-styling-tips.md).

## Modal-locked dialogs (long-running operations)

Dialogs that wrap a multi-second background task which mutates
operator-affecting state (host Wi-Fi switched to a device AP, partial
multi-device flash, etc.) **lock close** while the task runs. The
operator cannot accidentally dismiss the status view via outside-click,
Esc, the corner X, browser back/forward, refresh, or tab close.

The pattern has three pieces:

* **`<DialogContent :lock-close="<busy>">`** — outside-click + Esc are
  `preventDefault`-ed, X button hidden. Reusable across all dialogs.
* **`useTaskNavigationGuard(() => <busy>, { reason })`** — combines
  `useBeforeUnloadGuard` with `onBeforeRouteLeave`. Native confirm
  while busy; styled in-app modal is not technically possible for
  `beforeunload` (browser limitation).
* **Cancel button + summary phase** — the only close path. The
  button calls `gateway.cancelTask()` (`POST /api/task/cancel`).
  After the task lands in `done`/`error` the dialog auto-flips to a
  summary phase that renders the result breakdown; a Close button
  appears only there.

Shipped users: firmware update (full pattern), presets download
(full pattern), discovery (lighter variant: lock only, no Cancel
button — the scan is short and Wi-Fi-free). The developer-guide
section ["Modal-locked dialogs"](developer-guide.md#modal-locked-dialogs-cancel-with-summary-pattern)
has the wiring checklist.

## Click-to-locate (Indicate)

Operators need a way to physically spot a device after the host has
already paired it (e.g. "which of these 12 RaceLink Nodes is the one
showing low battery on the screen?"). The host wires this via the
`OPC_INDICATE` opcode + `IND_IDENTIFY` indicator catalog row — a
short magenta strobe (~5 s) that the receiver overlays on its segment
and then restores the prior state. Two click sites trigger it; both
funnel through `POST /api/devices/indicate`.

**Naming note**: the wire opcode and the host route both use *indicate*;
*identify* is reserved for the RF-discovery opcode `OPC_DEVICES`
(pairing flow). The operator-facing verb in the UI is **Locate**, which
is what shows up on buttons, tooltips and toasts.

| Site                                                | Affordance                              |
|-----------------------------------------------------|-----------------------------------------|
| Device-name text in `DeviceTable.vue` (Devices page) | Clickable span on hover (`cursor: pointer` + underline), but only when the row is **not** in rename-edit mode. The Pencil button keeps owning the rename gesture; the bare name owns Locate. |
| "Locate" button per row in `BatteryDevicesDialog.vue` | Explicit button at the right edge of each weak-battery row.                              |

Wording conventions for both sites:

* **Tooltip on hover** — context-rich, names the device:
  * Name span: `Click to locate '<name-or-mac>' — flashes its LEDs ~5 s`
  * Locate button: `Flash <name-or-mac>'s LEDs to locate it physically`
* **Toast on click** — present-progressive, `useToast().show()`:
  * `Locating <name-or-mac>…`
* **Toast on backend failure** — `useToast().error()`:
  * `Locate failed: <reason>`

Implementation rules a new caller should follow:

* **Debounce** repeated clicks on the same device with an `indicating`
  `ref<Set<string>>()` — add `addr` on click-start, delete in
  `finally`. A second click while the first is in flight is a no-op.
  Prevents stacking duplicate frames on the gateway queue.
* **Single-device call by default** — `apiPost('/api/devices/indicate', { macs: [addr] })`. The endpoint accepts `macs: [...]` (plural) so it scales to a "blink all weak devices" broadcast in the future, but per-row UX is the established pattern.
* **No local state mutation** — the indicator is a transient visual
  overlay; the device restores its pre-indicator state when
  `durationSec` expires. Do **not** mark the device "identified" in
  the store.
* **No completion feedback expected** — the gateway never reports
  whether the receiver applied the indicator. The toast on click is
  the only sender-side affordance; the operator confirms visually.

If a future click site wants a *different* indicator (e.g. a long
"pair confirm" strobe), pass `indicator_type` + `duration_sec` to the
same endpoint — they default to `IDENTIFY` (4) and 5 s respectively.
The indicator catalog lives in `racelink_indicators.h` (synced across
all four repos) with a hand-authored Python mirror in
`racelink/domain/indicators.py`.

## Confirmation dialogs

Destructive actions confirm via the shared `confirmDestructive(message)`
helper (defined in [racelink.js](../racelink/static/racelink.js),
re-exported on `window.RL`). Wording template:

> "{Verb} {subject}? {Consequence sentence.}"

Examples shipped:

* "Delete scene 'Intro Effects'? This cannot be undone."
* "Re-broadcast every device's group assignment to the network now? This sends RF traffic for every known node."
* "Move 5 devices to 'Pit Wall'? This sends a SET_GROUP packet to each one."

The wrapper currently routes to native `confirm()` — accessible,
keyboard-friendly, and zero-dependency. A future swap to a custom
modal is one-line.

## Toast feedback

Two flavours, defined in [racelink.js](../racelink/static/racelink.js)
and exposed on `window.RL`:

* `showToast(msg)` — green, 3 s default. Success / busy info.
* `showToastError(msg)` — red, 5 s default. Validation errors,
  server errors, "select exactly one device" hints.

Native `alert()` is **not** used in the operator-facing UI. If you
catch yourself reaching for it, route through a toast instead.

## Pending state

Long-running ops (anything that hits the gateway or the network)
disable their initiator button and show progress via:

* `setBusy(true/false)` in racelink.js (top-level pages — disables
  the discover/status/save/reload bar wholesale).
* Per-page busy helpers for editors that have their own toolbars
  (e.g. the scene editor's run button).

When a long op completes, fade a `showToast` summary in. When it
fails, fade a `showToastError`.

## Page-level navigation

Header bars use plain `<a class="rl-nav-link">` for navigation
between top-level pages (e.g. Devices ↔ Scenes). The scene editor
warns about unsaved drafts via a `beforeunload` listener.

## Inline hints

`<span class="muted">…</span>` next to a control gives a one-line
explanation. `title=` attributes on buttons give a longer hover
tooltip — use these for any button whose label can't fit the
operator's mental model in 1-3 words. `Re-sync group config` and
`Move` both carry tooltips for exactly this reason.

---

When in doubt, grep this doc for the verb you want and check
whether its role is already taken. If you genuinely need a new
verb, add it here in the same row, or PR a discussion about what
distinction it carries from the existing vocabulary.
