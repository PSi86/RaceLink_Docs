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
