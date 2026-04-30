# RaceLink Documentation

Consolidated public documentation of the **RaceLink** ecosystem — a
wireless LED-control system for drone racing and similar live events.

The project is split across four repositories. This documentation set
gathers the Markdown documents from all four projects in one place,
organised for public consumption.

> **Source of truth.** Files in this directory are **English copies**
> derived from the source repositories. Originals remain canonical;
> see [`sources.md`](sources.md) for the per-file provenance. When a
> source repository changes, this consolidated copy may lag.

## System overview

```text
RaceLink_Host  <--USB-->  RaceLink_Gateway  <--LoRa-->  RaceLink nodes
                                                        ├─ RaceLink_WLED
                                                        ├─ Startblocks
                                                        └─ Custom nodes

(optional: RaceLink_RH_Plugin → embeds RaceLink_Host into RotorHazard)
```

| Component | Role | Repository |
|---|---|---|
| **RaceLink_Host** | Python host: runtime, WebUI, services, standalone Flask | [PSi86/RaceLink_Host](https://github.com/PSi86/RaceLink_Host) |
| **RaceLink_Gateway** | ESP32-S3 firmware: USB ↔ LoRa bridge | [PSi86/RaceLink_Gateway](https://github.com/PSi86/RaceLink_Gateway) |
| **RaceLink_WLED** | WLED usermod + build profiles for RaceLink nodes | [PSi86/RaceLink_WLED](https://github.com/PSi86/RaceLink_WLED) |
| **RaceLink_RH_Plugin** | RotorHazard adapter; embeds RaceLink_Host as a plugin | [PSi86/RaceLink_RH-plugin](https://github.com/PSi86/RaceLink_RH-plugin) |

## Repository layout

```text
docs/
├── index.md                     (this document)
├── sources.md                   (file-by-file provenance)
├── glossary.md                  (canonical term reference)
├── licenses.md                  (per-component licence list)
├── versioning.md                (cross-component compatibility)
├── contributing.md              (PR rules, smoke tests, conventions)
├── changelog.md                 (release timeline)
├── troubleshooting.md           (operator-side index)
│
├── concepts/                    Cross-component user concepts
│   ├── index.md
│   ├── opcodes.md               (OPC_CONTROL / OPC_OFFSET / OPC_SYNC)
│   └── deterministic-effects.md
│
├── reference/                   Cross-component formal specs
│   ├── index.md
│   ├── wire-protocol.md
│   ├── web-api.md
│   ├── sse-channels.md
│   └── scene-format.md
│
├── RaceLink_Host/               RaceLink_Host (Python)
│   ├── README.md
│   ├── operator-guide.md
│   ├── webui-guide.md
│   ├── architecture.md
│   ├── developer-guide.md
│   ├── ui-conventions.md
│   └── standalone-install.md
│
├── RaceLink_Gateway/            RaceLink_Gateway (firmware)
│   ├── README.md
│   └── operator-setup.md
│
├── RaceLink_WLED/               RaceLink_WLED (usermod)
│   ├── README.md
│   └── operator-setup.md
│
└── RaceLink_RH_Plugin/          RaceLink_RH_Plugin (RotorHazard adapter)
    ├── README.md
    ├── operator-setup.md
    ├── release-playbook.md
    ├── manifest-dependency-format.md
    └── adr-0001-manifest-dependency.md
```

The `host/docs/repo_split_map.md` file from the source has been folded
into `RaceLink_Host/architecture.md` (its content is small and reads as a
historical note alongside the architecture description). The
`plans/` archive in the source is **not** mirrored here — it is an
internal engineering ledger; relevant content has been folded into
the appropriate documents.

## Recommended entry points by audience

### Operators (setting up an event)

1. [`RaceLink_Host/standalone-install.md`](RaceLink_Host/standalone-install.md) — install
   and run the host on Windows / Linux.
2. [`RaceLink_Host/operator-guide.md`](RaceLink_Host/operator-guide.md) —
   end-to-end workflow, safety rules, offset-mode operator view,
   troubleshooting.
3. [`RaceLink_Gateway/operator-setup.md`](RaceLink_Gateway/operator-setup.md) — connect the USB
   gateway, identify it on the host, OLED indicators.
4. [`RaceLink_WLED/operator-setup.md`](RaceLink_WLED/operator-setup.md) — pair a node, factory
   reset, default Wi-Fi AP and OTA password.
5. [`RaceLink_WLED/README.md`](RaceLink_WLED/README.md) — pick the right build profile
   for your hardware.
6. [`RaceLink_RH_Plugin/operator-setup.md`](RaceLink_RH_Plugin/operator-setup.md) — operator view
   inside RotorHazard if you run the plugin.
7. [`troubleshooting.md`](troubleshooting.md) — single index of
   common problems and where to find them.

### Contributors (code changes or extensions)

1. [`RaceLink_Host/architecture.md`](RaceLink_Host/architecture.md) — package layout,
   threading model, locking rules, UI scope matrix.
2. [`RaceLink_Host/developer-guide.md`](RaceLink_Host/developer-guide.md) —
   checklists for "I want to add X": new scene action, new opcode,
   new service, WLED metadata regeneration.
3. [`reference/wire-protocol.md`](reference/wire-protocol.md) — wire-format
   reference (USB framing, Header7, opcodes, body layouts, gateway
   state machine).
4. [`RaceLink_Host/ui-conventions.md`](RaceLink_Host/ui-conventions.md) —
   button vocabulary, toast / confirm-dialog conventions.
5. [`contributing.md`](contributing.md) — PR rules, smoke-test
   commands, exception-hygiene convention, the `bool` send contract.
6. [`versioning.md`](versioning.md) — version compatibility across
   Host / Gateway / WLED / RH plugin.

### Firmware developers (gateway / WLED nodes)

1. [`RaceLink_Gateway/README.md`](RaceLink_Gateway/README.md) — PlatformIO setup,
   hardware targets, build flags, USB framing.
2. [`RaceLink_WLED/README.md`](RaceLink_WLED/README.md) — build profiles per hardware
   variant, release workflow.
3. [`concepts/deterministic-effects.md`](concepts/deterministic-effects.md) —
   which WLED effects render identically when only `strip.timebase`
   is synced (prerequisite for offset mode + ARM-on-SYNC).
4. [`reference/wire-protocol.md`](reference/wire-protocol.md) — the wire format
   that the firmware must respect.

### Plugin maintainers (RotorHazard integration)

1. [`RaceLink_RH_Plugin/README.md`](RaceLink_RH_Plugin/README.md) — scope, online vs.
   offline installation, version mapping between plugin and host.
2. [`RaceLink_RH_Plugin/release-playbook.md`](RaceLink_RH_Plugin/release-playbook.md) —
   step-by-step maintainer release.
3. [`RaceLink_RH_Plugin/manifest-dependency-format.md`](RaceLink_RH_Plugin/manifest-dependency-format.md) —
   why the `git+https://` dependency format is required by RHFest.

## A note on cross-references

The source documents contain links that originally pointed into the
respective source repository's source code (`racelink/services/foo.py`,
`racelink_proto.h`, etc.). Those links cannot resolve in this
documentation-only consolidation. For source-code references, see
the matching source repository — the canonical paths are recorded in
[`sources.md`](sources.md).

Markdown-to-Markdown links **within** a sub-project's directory still
work, because each repository's original folder layout is preserved
under its sub-directory.

## Licence

Each source repository carries its own
