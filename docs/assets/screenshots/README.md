# Screenshots

This directory holds PNG screenshots of the RaceLink WebUI used by
the documentation pages.

> **Canonical source (since 2026-05-31).** These PNGs are **generated
> by the `RaceLink_Host` screenshot generator** and copied here. The
> source repo emits the full set (one PNG per bar / page / dialog)
> plus a `manifest.json` (name → file → description) and a
> `ui_build.hash`; only the `*.png` files are copied into this folder.
> Filenames use underscores (e.g. `dialog_network_manager.png`,
> `scene_action_offset_group.png`) and match the `manifest.json`
> `name` field.

To refresh the docs screenshots: re-run the `RaceLink_Host` generator,
then from the repo root run
[`scripts/sync_screenshots.py`](../../../scripts/sync_screenshots.py)
`--prune`. It mirrors the source PNGs into this folder (ignoring
`manifest.json` / `ui_build.hash`), prunes removed ones, and prints a
**coverage report** flagging any screenshot that still needs an article.
See [`scripts/README.md`](../../../scripts/README.md) for the full
workflow.

> **Note.** The older docs-repo generator
> ([`scripts/generate_screenshots.py`](../../../scripts/generate_screenshots.py))
> referenced the previous hyphenated filenames and is now stale; the
> canonical capture list lives in the `RaceLink_Host` generator's
> `manifest.json`.

If you opened a docs page and saw a broken image link ending in
`.png`, the corresponding capture is missing from this folder — copy
it from the latest `RaceLink_Host` generator output.
