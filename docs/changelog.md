# Changelog

A consolidated timeline of releases across the four RaceLink
repositories. Currently a stub — entries should be added as releases
ship. Each entry should follow the template at the bottom of this
file.

> **Source of truth.** Each repository maintains its own GitHub
> releases page; this changelog is a curated cross-repo summary.
> When the cross-repo summary and a repository's release notes
> disagree, the repository's release notes win.

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
