# RaceLink Documentation

Single source of truth for the **RaceLink** project documentation —
operator guide, developer guide, wire-protocol reference, glossary,
and maintainer ADRs for all four RaceLink components
(`RaceLink_Host`, `RaceLink_Gateway`, `RaceLink_WLED`,
`RaceLink_RH_Plugin`).

* **Published site:** https://psi86.github.io/RaceLink_Docs/ *(after
  the GitHub Pages deploy is wired up)*.
* **Component repositories:**
  [Host](https://github.com/PSi86/RaceLink_Host) ·
  [Gateway](https://github.com/PSi86/RaceLink_Gateway) ·
  [WLED](https://github.com/PSi86/RaceLink_WLED) ·
  [RH plugin](https://github.com/PSi86/RaceLink_RH-plugin)

The component repos hold **only code** plus a minimal `README.md`.
All narrative documentation lives here.

## Repository layout

```text
RaceLink_Docs/
├── README.md          (this file)
├── STRUCTURE.md       (developer contract: code ↔ doc mapping — three tables)
├── mkdocs.yml         (MkDocs Material configuration)
├── requirements.txt   (pip deps for building the site)
│
├── docs/                  (published documentation — built by MkDocs)
│   ├── index.md               (homepage)
│   ├── glossary.md, contributing.md, versioning.md,
│   │   troubleshooting.md, sources.md, changelog.md,
│   │   licenses.md
│   ├── concepts/              (cross-component user concepts)
│   ├── reference/             (cross-component formal specs)
│   ├── RaceLink_Host/         (Host-specific docs)
│   ├── RaceLink_Gateway/      (Gateway-specific docs)
│   ├── RaceLink_WLED/         (WLED-specific docs)
│   └── RaceLink_RH_Plugin/    (RotorHazard plugin docs)
│
├── _meta/                 (gitignored — local only, never on GitHub)
│   ├── audit/                 (original audit and structure proposal)
│   ├── contributor/           (DEV_WORKFLOW, legacy German notes)
│   ├── maintainer/            (HARVEST, AUDIT_RESPONSE)
│   └── templates/             (component-repo configuration templates)
│
└── _private/              (gitignored — strictly private, never on GitHub)
    ├── adr-drafts/            (ADR drafts before publication)
    └── plans/                 (local plan archive)
```

## Build the site locally

=== "Windows (PowerShell)"

    ```powershell
    py -m venv .venv
    .venv\Scripts\Activate.ps1
    py -m pip install -r requirements.txt

    mkdocs serve                        # http://127.0.0.1:8000
    mkdocs build --strict               # → site/  (static HTML; CI uses --strict)
    ```

    On Windows the [Python launcher](https://docs.python.org/3/using/windows.html#python-launcher-for-windows)
    `py` is the recommended way to invoke Python. `py -3.12 -m …` pins
    to a specific version if multiple are installed.

=== "Linux / macOS"

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    python3 -m pip install -r requirements.txt

    mkdocs serve                        # http://127.0.0.1:8000
    mkdocs build --strict               # → site/  (static HTML; CI uses --strict)
    ```

`--strict` makes `mkdocs build` fail on broken internal links — it
is the lightweight quality gate for PRs.

## Working on the docs

* **Editing existing docs.** Open
  [`STRUCTURE.md`](STRUCTURE.md), find the topic, jump to the file.
  Conventions live in [`docs/contributing.md`](docs/contributing.md)
  and [`docs/glossary.md`](docs/glossary.md).
* **Updating docs because code changed.** Open
  [`STRUCTURE.md`](STRUCTURE.md) **Table 2** ("If you change …
  update …") and update every doc it lists.
* **Reading docs to prepare a code change.** Open
  [`STRUCTURE.md`](STRUCTURE.md) **Table 3** ("Document → Backing
  code") to find which file documents the area you intend to
  touch.

