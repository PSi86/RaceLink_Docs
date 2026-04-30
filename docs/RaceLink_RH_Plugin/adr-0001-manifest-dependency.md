# ADR-0001: RH plugin manifest dependency format

## Status

Accepted (2026-04 — see also the source document
[`../../RaceLink_RH_Plugin/manifest-dependency-format.md`](manifest-dependency-format.md)
which preceded this ADR formalisation).

## Context

`RaceLink_RH_Plugin` declares its dependency on `RaceLink_Host` in
`custom_plugins/racelink_rh_plugin/manifest.json`. That manifest
is validated by **RHFest**, the validator that gates RotorHazard
plugin manifests in the official store.

RHFest v3 accepts dependency entries in only two shapes
(implemented in `RotorHazard/rhfest-action` under `rhfest/const.py`,
consumed by `rhfest/checks/manifest.py`):

* a **package name** with an optional version specifier, e.g.
  `racelink-host==0.1.0`;
* a **`git+https://...` URL** with an optional `@<tag>` suffix.

`RaceLink_Host` is *not* published on PyPI. A direct PyPI dependency
would not work. A direct wheel-URL dependency in PEP-508 form
(`racelink-host @ https://example.invalid/racelink_host-1.2.3-py3-none-any.whl`)
is rejected by RHFest's validator.

The plugin maintainer also wants the choice to be reproducible:
the spike `scripts/verify_manifest_dependency_formats.py` runs the
same RHFest validator locally so a contributor can confirm any
change before opening a PR.

## Decision

For online installations, the plugin uses:

```text
git+https://github.com/PSi86/RaceLink_Host.git@v<version>
```

The `@v<version>` suffix is an immutable Git tag, pinned per
plugin release. Local development and CI use the **same** pinned
host version, but consume it through the immutable GitHub-release
wheel URL declared in `pyproject.toml` (because `racelink-host` is
not on PyPI).

For offline installations, the manifest's `dependencies` field is
**cleared** in the offline-release ZIP so RotorHazard does not try
to fetch packages during installation. The bundled wheel under
`custom_plugins/racelink_rh_plugin/offline_wheels/` is installed
locally on the first plugin start, after which the plugin loads
normally from the RotorHazard Python environment.

## Consequences

* **Reliable RHFest validation.** Both shapes (package-name with
  version specifier and `git+https://`) pass; the plugin uses the
  Git URL because `racelink-host` is not on PyPI.
* **Immutable references only.** A floating `git+https://...@main`
  reference is rejected by policy; only an immutable tag may be
  used.
* **Online and offline both work.** The two installation modes
  resolve to the same host wheel for a given plugin release —
  online fetches it during install, offline ships it inside the
  ZIP.
* **No PEP-508 wheel-URL form.** A direct
  `racelink-host @ https://...whl` reference must not be used
  unless RHFest broadens its dependency validation rules. The
  spike test (`verify_manifest_dependency_formats.py`) regression-
  guards this rule.
* **Version coupling per release.** Each plugin release pins one
  immutable host tag; the version-mapping is documented in the
  release playbook
  ([`../../RaceLink_RH_Plugin/release-playbook.md`](release-playbook.md)).
* **Future PyPI publication of `racelink-host`** — if the host is
  later published on PyPI, the plugin can switch to
  `racelink-host==<version>` with a single manifest edit. This ADR
  would then move to *Superseded* with a successor ADR documenting
  the switch.
