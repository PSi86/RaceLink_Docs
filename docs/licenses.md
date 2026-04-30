# Licences

All four RaceLink source repositories are released under the **MIT
licence**. Each repository carries its own `LICENSE` file at the
root with byte-identical text and the same copyright line:

```text
Copyright (c) 2026 PSi86
```

## Per-component licences

| Component | Licence | Declared in |
|---|---|---|
| RaceLink_Host | MIT | [`LICENSE`](https://github.com/PSi86/RaceLink_Host/blob/main/LICENSE); also [`pyproject.toml`](https://github.com/PSi86/RaceLink_Host/blob/main/pyproject.toml) — `[project] license = { text = "MIT" }` |
| RaceLink_Gateway | MIT | [`LICENSE`](https://github.com/PSi86/RaceLink_Gateway/blob/main/LICENSE) |
| RaceLink_WLED | MIT | [`LICENSE`](https://github.com/PSi86/RaceLink_WLED/blob/main/LICENSE) |
| RaceLink_RH_Plugin | MIT | [`LICENSE`](https://github.com/PSi86/RaceLink_RH-plugin/blob/main/LICENSE); also declared in [`manifest.json`](https://github.com/PSi86/RaceLink_RH-plugin/blob/main/custom_plugins/racelink_rh_plugin/manifest.json) |

> **Authoritative source.** When this table and a repository's
> `LICENSE` file disagree, the repository wins. Open an issue
> against [`RaceLink_Docs`](https://github.com/PSi86/RaceLink_Docs)
> when you spot a drift.

## Licence of this documentation set

The consolidated copies here are derived from the source documents
listed in [`sources.md`](sources.md). New files written for this
consolidation (`README.md`, `glossary.md`, `versioning.md`,
`contributing.md`, `changelog.md`, `troubleshooting.md`, the
per-component `operator-setup.md` files, and the `reference/`
documents) are released under the same MIT licence as the four
source repositories.

## Third-party material

The third-party libraries and dependencies (RadioLib, U8g2, official
WLED, Flask, Werkzeug, etc.) carry their own licences and are NOT
redistributed by this docs set. See
[`sources.md`](sources.md) § "What was deliberately NOT included".
