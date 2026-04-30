# Scripts

Helpers for the docs repo. Not part of the published site.

## `generate_screenshots.py`

Captures the RaceLink WebUI into `docs/assets/screenshots/`. Used
to keep the screenshots in
[`docs/RaceLink_Host/webui-guide.md`](../docs/RaceLink_Host/webui-guide.md)
(and any other pages illustrating the UI) consistent and
re-runnable.

Why a script:

* **Re-runnable** — after a UI change, re-run the script and the
  whole image set is refreshed in one go.
* **Consistent** — every capture uses the same viewport size and
  theme, so the docs do not look like a patchwork.
* **Pixel-accurate** — Playwright drives a headless Chromium and
  captures the actual rendered pixels (not a DOM re-render),
  which matches what an operator sees in their browser.

### One-time setup

```powershell
py -m pip install playwright
py -m playwright install chromium
```

(On Linux/macOS, replace `py` with `python3`.)

### Usage

The defaults assume the operator's own tracker on the LAN at
`http://trackerv8.local/racelink`, viewport 1920×1080, dark theme,
and the `Test2` device group selected. All of those are
overridable.

1.  Make sure the host is reachable. Either point at your tracker
    on the LAN (the default) or run the standalone demo:

    ```powershell
    racelink-standalone
    py scripts\generate_screenshots.py --base-url http://127.0.0.1:5077/racelink
    ```

    The host should have realistic content — at least a few
    discovered devices, a populated group, and one or two saved
    scenes. Empty pages produce poor documentation screenshots.

2.  Run the capture script:

    ```powershell
    py scripts\generate_screenshots.py
    ```

3.  The script writes PNGs into `docs/assets/screenshots/` at
    1920×1080. After that, `mkdocs serve` (or a `mkdocs build`)
    picks them up.

### Common arguments

| Argument | Default | Purpose |
|---|---|---|
| `--base-url URL` | `http://trackerv8.local/racelink` | Host base URL. |
| `--output DIR` | `docs/assets/screenshots` | Output directory. |
| `--width N` | `1920` | Viewport width in px. |
| `--height N` | `1080` | Viewport height in px. |
| `--theme {light,dark}` | `dark` | Browser color scheme. |
| `--group NAME` | `Test2` | Group selected on `/racelink/` before any capture that needs the group list visible. |
| `--only SUBSTR` | *(all)* | Capture only entries whose filename contains `SUBSTR`. Repeatable, e.g. `--only devices --only scenes`. |

### Captured set

Each entry in the `CAPTURES` list near the top of the script is a
small dict (`filename`, `route`, `needs_group`, `pre_action`,
`element_selector`). Out of the box the script captures:

* `devices-page.png` — Devices/Groups page with `Test2` selected.
* `scenes-page.png` — Scenes page (no group switch needed).
* `discover-dialog.png` — Discover Devices dialog.
* `firmware-update-dialog.png` — Firmware Update dialog (taken as
  an *element* screenshot so the full dialog content is captured
  even when it overflows the viewport).
* `wled-presets-dialog.png` — WLED Presets dialog (element
  screenshot, same reason).
* `rl-presets-dialog.png` — RL Presets dialog (element screenshot).
* `specials-dialog.png` — Per-device Specials dialog of the first
  device row in the selected group.

The script **never** triggers destructive actions (no firmware
upload, no `presets.json` upload, no save / re-sync / reload, no
discover). It only opens dialogs to capture them.

### Adding a new screenshot

Edit the `CAPTURES` list near the top of
`generate_screenshots.py`. The fields are:

* `filename` — written under `docs/assets/screenshots/`.
* `route` — appended to `--base-url`. Use `/` for the Devices
  page, `/scenes` for Scenes, etc.
* `needs_group` — set to `True` when the page shows the group
  list (so `Test2` is selected first), `False` for pages where
  it is irrelevant (like `/scenes`).
* `pre_action` — Python callable that takes the Playwright
  `Page` and runs *after* navigation and group selection — e.g.
  click a button to open a dialog. Use `_noop` for none.
* `element_selector` — set this to a CSS selector when the
  capture should be the element-only screenshot (e.g. for
  dialogs that overflow the viewport). Leave `None` for a
  full-viewport capture.

After adding, reference the new screenshot from the relevant docs
page:

```markdown
![Operator's view of the Devices page](
  ../../assets/screenshots/devices-page.png)
```

### Theming

The script captures in dark mode by default (the production look
of the WebUI). Pass `--theme light` for the light-mode variant.
To ship both, run twice with different output prefixes:

```powershell
py scripts\generate_screenshots.py --theme dark
py scripts\generate_screenshots.py --theme light --output docs/assets/screenshots/light
```

(For the light variant, update the Markdown image references
accordingly.)

### CI integration (later)

Once the screenshots are tracked in git, a CI step can rerun the
script on PRs that touch the WebUI source and diff the result —
catching unintended visual regressions. Skipped for v1; manual
re-runs after UI changes are good
