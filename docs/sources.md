# Sources — Provenance of the documents

This file records **where each Markdown file** in this directory came
from. The originals remain in their respective source repositories and
are the canonical version there — this collection is a
**consolidation copy** intended for a central public documentation
site.

## File-by-file directory

### Top level

| Consolidated path | Origin | Note |
|---|---|---|
| `README.md` | new, written for this consolidation | Top-level index and navigation |
| `sources.md` | new | This provenance file |
| `glossary.md` | new | Single canonical glossary spanning all audiences |
| `licenses.md` | new | Reconciled per-component licence list |
| `versioning.md` | new | Cross-component compatibility |
| `contributing.md` | new | PR rules, smoke tests |
| `changelog.md` | new (initially empty) | Release timeline |
| `troubleshooting.md` | new | Operator-side index aggregating all sub-doc tips |

### `RaceLink_Host/` — Python host

| Consolidated path | Source path | Note |
|---|---|---|
| `RaceLink_Host/README.md` | `RaceLink_Host/README.md` | Cleaned: fixed Windows-absolute path, trimmed duplicated system overview |
| `RaceLink_Host/architecture.md` | `RaceLink_Host/ARCHITECTURE.md` | Cleaned: includes the content of `docs/repo_split_map.md` as a "Repo split history" subsection |
| `RaceLink_Host/operator-guide.md` | `RaceLink_Host/docs/OPERATOR_GUIDE.md` | Cleaned: cross-links updated; cyclic-effect phase-lock note added |
| `RaceLink_Host/developer-guide.md` | `RaceLink_Host/docs/DEVELOPER_GUIDE.md` | **Fixed** the "three vs four gates" wording contradiction (audit C1); replaced workstation paths with upstream-WLED references |
| `reference/wire-protocol.md` | `RaceLink_Host/docs/PROTOCOL.md` | Verbatim |
| `RaceLink_Host/ui-conventions.md` | `RaceLink_Host/docs/UI_CONVENTIONS.md` | Verbatim |
| `RaceLink_Host/standalone-install.md` | `RaceLink_Host/docs/standalone.md` | Verbatim |
| `host/docs/repo_split_map.md` | (folded into `ARCHITECTURE.md`) | Original retained in the source repo |

### `RaceLink_Gateway/` — gateway firmware

| Consolidated path | Source path | Note |
|---|---|---|
| `RaceLink_Gateway/README.md` | `RaceLink_Gateway/readme.md` | Cleaned: dropped duplicated system overview (now lives in root README) |
| `RaceLink_Gateway/operator-setup.md` | new (gap G2) | Operator setup that did not exist in the source |

### `RaceLink_WLED/` — WLED usermod + build profiles

| Consolidated path | Source path | Note |
|---|---|---|
| `RaceLink_WLED/README.md` | `RaceLink_WLED/readme.md` | Cleaned: dropped duplicated system overview |
| `RaceLink_WLED/operator-setup.md` | new (gap G3) | Operator setup that did not exist in the source |
| `concepts/deterministic-effects.md` | `RaceLink_WLED/docs/effects-deterministic.md` | Verbatim |

### `RaceLink_RH_Plugin/` — RotorHazard adapter

| Consolidated path | Source path | Note |
|---|---|---|
| `RaceLink_RH_Plugin/README.md` | `RaceLink_RH_Plugin/README.md` | Cleaned: trimmed duplicated system overview |
| `RaceLink_RH_Plugin/operator-setup.md` | new (gap G4) | Operator setup inside RotorHazard |
| `RaceLink_RH_Plugin/release-playbook.md` | `RaceLink_RH_Plugin/docs/release-playbook.md` | Verbatim |
| `RaceLink_RH_Plugin/manifest-dependency-format.md` | `RaceLink_RH_Plugin/docs/manifest-dependency-format.md` | Verbatim — see also `RaceLink_RH_Plugin/adr-0001-manifest-dependency.md` |
| `RaceLink_RH_Plugin/adr-0001-manifest-dependency.md` | rephrased from `RaceLink_RH_Plugin/manifest-dependency-format.md` | First ADR in canonical Context/Decision/Consequence format |

### `reference/` — cross-component reference

| Consolidated path | Origin | Note |
|---|---|---|
| `reference/scene-format.md` | new (gap G10) | Distilled from `RaceLink_Host/operator-guide.md` and the `scene-manager-feature` plan |
| `reference/sse-channels.md` | new (gap G12) | Distilled from `RaceLink_Host/architecture.md` § UI Scope Matrix |
| `reference/web-api.md` | new (gap G11; **closed 2026-04-30**) | Filled in from `RaceLink_Host/racelink/web/{api,request_helpers,blueprint,dto}.py` with full request/response shapes for all 49 endpoints |

## What was deliberately NOT included

The following Markdown files exist in the source repositories but
were not pulled in, because they are not RaceLink-specific
documentation:

* **Third-party libraries** under
  `RaceLink_Gateway/.pio/libdeps/**` (RadioLib, U8g2 — their
  `README.md`, `contributing.md`, `SECURITY.md` etc. belong to those
  upstream projects).
* **PyPI cache and build artefacts** under
  `RaceLink_RH_Plugin/.tmp/**`, `.venv/**`, `.tools/**`, `dist/**`
  (Flask, Werkzeug, idna, offline staging copies of the plugin).
* **Pytest cache** (`.pytest_cache/README.md` in several repos).
* **Maintainer-local working notes** — session logs and per-project
  memo files held outside any of the four source repositories;
  these are private to the maintainer's workstation and not
  documentation.
* **The internal engineering ledger** — a set of plan / design /
  audit documents held outside the source repositories. It is
  internal working material; its public-relevant content has been
  **folded** into the appropriate documents in this consolidation.

The exclusion can be reproduced with:

```bash
# Inside each source repo:
find . -name "*.md" -not -path "*/.pio/*" \
  -not -path "*/.venv/*" -not -path "*/.tmp/*" \
  -not -path "*/.tools/*" -not -path "*/dist/*" \
  -not -path "*/.pytest_cache/*"
```

## Keeping this collection in sync

When a source document changes, the copy here goes stale. Update
procedure:

1. Identify the changed document in the relevant source repository.
2. Copy the file from the source path to the consolidated path
   listed above (e.g.
   `cp RaceLink_Host/docs/PROTOCOL.md RaceLink_Docs/docs/reference/wire-protocol.md`).
3. Re-apply any consolidation fixes for that file. The git history
   of this docs repo is the record of what was normalised last time
   the file was synced from source.
4. For structural changes (new file, removed file, renamed path)
   also update the file-by-file table here and the navigation in
   [`index.md`](index.md).

## Known limitations of the copies

* **Source-code cross-references do not resolve.** Many of the
  original documents reference source files relatively (e.g.
  `../racelink/services/foo.py`). This consolidation contains no
  source code — those links work only inside the source repository.
  For source-code references, see the matching source repository.
* **Cross-repo workstation paths do not resolve.** For example,
  `RaceLink_Host/developer-guide.md` originally referenced
  `../../WLED LoRa/WLED/...`; those paths are workstation-specific
  and not part of this set. Where they were essential, the
  references have been replaced with text references to the upstream
  WLED source layout (`wled00/wled_server.cpp`, etc.).
* **Markdown-to-Markdown links inside the same sub-project still
  work** (e.g. `RaceLink_Host/operator-guide.md` → `reference/wire-protocol.md`),
  because the original directory structure is preserved per-repo.
* **The source repository remains the source of truth.** When a
  copy here and the source disagree, the source wins.
