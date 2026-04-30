#!/usr/bin/env python3
"""
Generate RaceLink WebUI screenshots for the documentation.

Captures each UI page that the docs reference into
``docs/assets/screenshots/``. Uses Playwright (Chromium headless)
against a running RaceLink Host instance — typically the operator's
own tracker on the LAN, e.g. ``http://trackerv8.local/racelink``,
or ``racelink-standalone`` on the developer's machine.

Why a script instead of static screenshots:

* Re-running it after a UI change keeps the docs in sync.
* Consistent viewport size and theming across all images.
* Same set of captures works whether run manually or in CI.

Usage
-----

1. Install dependencies (one-time):

   .. code-block:: powershell

       py -m pip install playwright
       py -m playwright install chromium

2. Make sure the RaceLink Host is reachable. Either point at your
   local tracker on the LAN (default,
   ``http://trackerv8.local/racelink``) or start the standalone
   demo in a separate terminal:

   .. code-block:: powershell

       racelink-standalone
       py scripts\\generate_screenshots.py --base-url http://127.0.0.1:5077/racelink

   The host should have realistic content — at least a few
   discovered devices and one saved scene. Empty pages make for
   poor documentation screenshots.

3. Run this script:

   .. code-block:: powershell

       py scripts\\generate_screenshots.py

   Optional arguments:

       --base-url   override the host URL (default
                    ``http://trackerv8.local/racelink``)
       --output     override output directory (default
                    ``docs/assets/screenshots``)
       --width      viewport width in px (default 1920)
       --height     viewport height in px (default 1080)
       --theme      ``light`` or ``dark`` (default ``dark`` —
                    the production look)
       --group      device group to select on ``/racelink/`` before
                    each capture that shows the group list
                    (default ``Test2``)
       --only       capture only entries whose filename matches
                    this substring; repeatable

The script captures the pages listed in ``CAPTURES`` below. Add new
entries when a new page or dialog enters the WebUI guide.

Safety
------

The script only reads UI state — it never triggers destructive
actions. It opens dialogs to capture them, but it does **not**:

* upload firmware,
* upload ``presets.json``,
* save / re-sync / reload device config,
* discover or pair devices.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

try:
    from playwright.sync_api import Page, sync_playwright
except ImportError:
    print(
        "playwright not installed. Run:\n"
        "  py -m pip install playwright\n"
        "  py -m playwright install chromium",
        file=sys.stderr,
    )
    sys.exit(2)


# ----------------------------------------------------------------------
# Page-state helpers
# ----------------------------------------------------------------------

def _wait_settled(page: "Page", ms: int = 600) -> None:
    """Give SSE-driven UI updates a moment to settle."""
    page.wait_for_timeout(ms)


def select_group(page: "Page", group_name: str) -> None:
    """Click the named group in the left-hand sidebar.

    The sidebar entries are list items with the group name as
    their text. Robust against layout changes; relies only on
    the visible label.
    """
    locator = page.locator(
        f"aside:has-text('Groups') >> text=/^{group_name}$/"
    )
    if locator.count() == 0:
        # Fallback: any element with exact text match. The group
        # list renders the name as its own line.
        locator = page.locator(f"text=/^{group_name}$/").first
    locator.first.click(timeout=5000)
    _wait_settled(page, 300)


def close_any_dialog(page: "Page") -> None:
    """Press Escape until no dialog is on top."""
    for _ in range(3):
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)


# ----------------------------------------------------------------------
# Capture catalogue
#
# Each entry: filename, route under base_url, optional pre-action that
# runs *after* navigation and the optional Test2-group switch, plus an
# optional `element_selector` for dialog-only locator screenshots.
# ----------------------------------------------------------------------

def _noop(_page: "Page") -> None:
    pass


def _open_discover_dialog(page: "Page") -> None:
    page.get_by_role("button", name="Discover Devices").click()
    page.wait_for_timeout(500)


def _open_firmware_update_dialog(page: "Page") -> None:
    page.get_by_role("button", name="Firmware Update").click()
    page.wait_for_timeout(500)


def _open_wled_presets_dialog(page: "Page") -> None:
    page.get_by_role("button", name="WLED Presets").click()
    page.wait_for_timeout(500)


def _open_rl_presets_dialog(page: "Page") -> None:
    page.get_by_role("button", name="RL Presets").click()
    page.wait_for_timeout(500)


def _open_specials_dialog(page: "Page") -> None:
    """Open the per-device Specials dialog for the first device row.

    The Specials button lives on each device row. We pick the
    first one — which is the first device in the currently
    selected group.
    """
    page.get_by_role("button", name="Specials").first.click()
    page.wait_for_timeout(500)


# Layout of each capture entry:
#   filename              — output PNG name
#   route                 — appended to --base-url
#   needs_group           — switch to --group on /racelink/ first
#                           (False for /racelink/scenes etc.)
#   pre_action            — Playwright callable run before capture
#   element_selector      — if set, screenshot only that element
#                           (used for dialogs to avoid scrollbar
#                           cropping when the dialog overflows
#                           the viewport)

DIALOG_SELECTOR = "dialog:visible, .modal:visible, [role='dialog']:visible"

CAPTURES = [
    {
        "filename":         "devices-page.png",
        "route":            "/",
        "needs_group":      True,
        "pre_action":       _noop,
        "element_selector": None,
    },
    {
        "filename":         "scenes-page.png",
        "route":            "/scenes",
        "needs_group":      False,
        "pre_action":       _noop,
        "element_selector": None,
    },
    {
        "filename":         "discover-dialog.png",
        "route":            "/",
        "needs_group":      True,
        "pre_action":       _open_discover_dialog,
        "element_selector": None,
    },
    {
        "filename":         "firmware-update-dialog.png",
        "route":            "/",
        "needs_group":      True,
        "pre_action":       _open_firmware_update_dialog,
        # Capture the dialog element directly so its full content
        # height is included even if it overflows the 1080-px
        # viewport.
        "element_selector": DIALOG_SELECTOR,
    },
    {
        "filename":         "wled-presets-dialog.png",
        "route":            "/",
        "needs_group":      True,
        "pre_action":       _open_wled_presets_dialog,
        "element_selector": DIALOG_SELECTOR,
    },
    {
        "filename":         "rl-presets-dialog.png",
        "route":            "/",
        "needs_group":      True,
        "pre_action":       _open_rl_presets_dialog,
        "element_selector": DIALOG_SELECTOR,
    },
    {
        "filename":         "specials-dialog.png",
        "route":            "/",
        "needs_group":      True,
        "pre_action":       _open_specials_dialog,
        "element_selector": DIALOG_SELECTOR,
    },
    # Add new captures here when the docs reference new pages.
]


# ----------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        description="Capture RaceLink WebUI screenshots into the docs "
                    "asset folder."
    )
    p.add_argument(
        "--base-url",
        default="http://trackerv8.local/racelink",
        help="Host base URL (default: %(default)s)",
    )
    p.add_argument(
        "--output",
        default="docs/assets/screenshots",
        help="Output directory (default: %(default)s)",
    )
    p.add_argument("--width",  type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument(
        "--theme",
        choices=["light", "dark"],
        default="dark",
        help="Browser color scheme to emulate (default: %(default)s).",
    )
    p.add_argument(
        "--group",
        default="Test2",
        help="Device group to select on /racelink/ before each "
             "capture that shows the group list "
             "(default: %(default)s).",
    )
    p.add_argument(
        "--only",
        action="append",
        help="Capture only entries whose filename contains this "
             "substring; repeatable.",
    )
    args = p.parse_args()

    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    base_url = args.base_url.rstrip("/")

    captures = CAPTURES
    if args.only:
        wanted = args.only
        captures = [c for c in captures if any(w in c["filename"] for w in wanted)]
        if not captures:
            print(f"No captures match --only {args.only}", file=sys.stderr)
            return 2

    print(f"Capturing {len(captures)} screenshot(s) from {base_url}")
    print(f"Viewport: {args.width}x{args.height}, theme: {args.theme}")
    print(f"Group:    {args.group} (selected before /racelink/ captures)")
    print(f"Output:   {out_dir}")
    print()

    failures = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": args.width, "height": args.height},
            color_scheme=args.theme,
            device_scale_factor=1,
        )
        page = context.new_page()

        # Reachability check.
        try:
            page.goto(base_url + "/", timeout=8000)
        except Exception as exc:  # noqa: BLE001
            print(
                f"Cannot reach {base_url}/: {exc}\n"
                f"Is the host up? Try --base-url http://127.0.0.1:5077/racelink "
                f"with `racelink-standalone` running.",
                file=sys.stderr,
            )
            browser.close()
            return 1

        for cap in captures:
            fname            = cap["filename"]
            route            = cap["route"]
            needs_group      = cap["needs_group"]
            pre_action       = cap["pre_action"]
            element_selector = cap["element_selector"]

            url = f"{base_url}{route}"
            try:
                page.goto(url, timeout=8000)
            except Exception as exc:  # noqa: BLE001
                msg = f"FAIL goto: {exc}"
                print(f"  {fname:32s} {msg}")
                failures.append(f"{fname}: {msg}")
                continue

            _wait_settled(page, 600)

            # Switch to the configured group first, so the device
            # list visible behind any dialog matches the operator's
            # working context.
            if needs_group:
                try:
                    select_group(page, args.group)
                except Exception as exc:  # noqa: BLE001
                    msg = f"FAIL group-select '{args.group}': {exc}"
                    print(f"  {fname:32s} {msg}")
                    failures.append(f"{fname}: {msg}")
                    continue

            try:
                pre_action(page)
            except Exception as exc:  # noqa: BLE001
                msg = f"FAIL pre-action: {exc}"
                print(f"  {fname:32s} {msg}")
                failures.append(f"{fname}: {msg}")
                continue

            _wait_settled(page, 500)

            target = out_dir / fname
            try:
                if element_selector:
                    # Prefer dialog-only screenshot so an overflowing
                    # dialog body is captured at its full content
                    # height, not clipped by the viewport.
                    locator = page.locator(element_selector).first
                    locator.screenshot(path=str(target))
                else:
                    page.screenshot(path=str(target), full_page=False)
                print(f"  {fname:32s} OK  ({target})")
            except Exception as exc:  # noqa: BLE001
                msg = f"FAIL screenshot: {exc}"
                print(f"  {fname:32s} {msg}")
                failures.append(f"{fname}: {msg}")

            # Reset state between captures so a stuck dialog from
            # one entry does not pollute the next.
            close_any_dialog(page)

        browser.close()

    print()
    if failures:
        print(f"Done with {len(failures)} failure(s):")
        for f in failures:
            print(f"  - {f}")
        print()
        print("Tip: open the WebUI manually and verify the button "
              "labels / dialog selectors used in this script.")
        return 1

    print("Done. Reference these images from Markdown like:")
    print("    ![Devices page](../../assets/screenshots/devices-page.png)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
