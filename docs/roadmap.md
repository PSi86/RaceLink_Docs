# RaceLink Roadmap

This roadmap describes the intended direction of RaceLink.

It is not a complete issue tracker and it is not a promise that every listed item will be implemented in the exact order shown. Its purpose is to keep the architectural direction clear: RaceLink should remain a lightweight, robust race/event control system with LoRa-connected devices, while exposing clean interfaces so that operators can use established lighting and show-control software when their needs exceed the built-in WebUI.

## Project direction

RaceLink should be usable on its own, but it should not try to replace professional lighting software.

The built-in RaceLink WebUI should focus on what RaceLink itself must own:

- gateway discovery and status
- LoRa network and device management
- group assignment
- node configuration and maintenance
- basic scene authoring and triggering
- race-event integration
- startblock and custom-node control
- diagnostics and firmware/update workflows

External tools should be used for workflows that established lighting and show-control applications already handle better:

- complex cue lists
- timelines
- live fader operation
- MIDI/OSC control surfaces
- fixture libraries
- professional Art-Net/sACN/DMX show operation
- media/show-control workflows that can be reduced to coarse RaceLink actions

Important constraint: RaceLink is not a real-time transport for high-bandwidth show data. Upstream tools may run pixel mapping, beat analysis, audio-reactive control, or timeline playback, but RaceLink should receive only the resulting high-level actions — see the "Mapping, not streaming" principle below.

RaceLink should therefore become easy to control from external software, instead of growing the WebUI into a full lighting desk.

## Architectural principles

### 1. Host-first integrations

External software integrations should primarily live in `RaceLink_Host`.

The Host already owns the WebUI, API surface, scene execution, group/device model, repository state, and gateway routing. Protocols such as HTTP, WebSocket/SSE, OSC, MQTT, Art-Net, sACN, and OLA belong at this layer.

Gateway firmware should stay focused on deterministic USB-to-LoRa operation unless a hardware interface provides clear value that cannot reasonably be achieved at the Host layer.

### 2. Action model before adapters

All control paths should converge on a single internal action model.

The WebUI, RotorHazard plugin, and external adapters should call the same internal actions instead of duplicating command logic.

Example action vocabulary:

- `scene.start(scene_id)`
- `scene.stop(scene_id)`
- `group.set_rl_preset(group_id, preset_id)`
- `group.set_wled_preset(group_id, preset_slot)`
- `group.set_brightness(group_id, value)`
- `group.set_effect(group_id, effect_id, speed, intensity)`
- `group.blackout(group_id)`
- `node.identify(node_id)`
- `startblock.arm(block_id)`
- `startblock.trigger(block_id)`
- `sync.send(scope)`
- `system.blackout()`

This makes integrations predictable and keeps the WebUI from becoming the only supported control path.

### 3. Mapping, not streaming

RaceLink should not attempt to transport continuous DMX, Art-Net, sACN, DDP, pixel, or audio-reactive control frames over LoRa.

LoRa is suitable for compact, event-oriented commands:

- scene triggers
- preset changes
- group commands
- sync events
- status and replies
- startblock commands
- custom-node actions

It is not suitable for frame-by-frame DMX universes, high-rate pixel streaming, or continuous beat/audio-reactive parameter streams.

Art-Net/sACN input should therefore be treated as a control mapping layer: external software changes selected channels, and the Host translates meaningful changes into RaceLink actions.

A professional show-control tool may still be used for timelines, cue lists, media control, or beat-synchronized show logic. The important boundary is that RaceLink receives only the resulting high-level command, not the underlying real-time stream.

### 4. External control must be explicit and observable

Operators must be able to see when RaceLink is controlled externally.

External-control features should include:

- global enable/disable switch
- per-adapter enable/disable switch
- visible status of active external control
- last external command log
- rate-limit and rejection diagnostics
- clear ownership/priority rules
- emergency blackout path

### 5. Avoid unnecessary WebUI growth

The RaceLink WebUI may expose small configuration surfaces for integrations, but should not implement full show-control features.

Allowed WebUI scope:

- API settings
- adapter enable/disable state
- Art-Net/sACN universe and mapping setup
- OSC endpoint overview
- MQTT broker/topic configuration
- external-control status and debug log
- ownership/priority configuration

Out of scope for the RaceLink WebUI:

- full lighting desk functionality
- fixture library management
- large DMX patchbay management
- professional cue-stack editing
- timeline authoring for complex shows
- real-time pixel mapping
- beat-grid or audio-analysis tools
- complex MIDI control-surface designer

These workflows can remain in external tools. RaceLink should expose clean interfaces so those tools can trigger RaceLink actions where appropriate.

## Roadmap overview

| Stage | Theme | Main outcome |
| --- | --- | --- |
| Now | Core control API | RaceLink has a stable action model and documented external API. |
| Next | External input adapters | Professional tools can control RaceLink without using the WebUI. |
| Next | WebUI scope control | WebUI stays focused on RaceLink-specific operation and integration setup. |
| Later | Output adapters | RaceLink can trigger standard lighting systems when useful. |
| Later | Optional hardware extensions | Additional hardware interfaces are added only where Host-side adapters are insufficient. |

---

## Stage 1 — Stable internal action model and public API

Status: Planned  
Primary repository: `RaceLink_Host`

### Goal

Create a stable control foundation that all internal and external clients can use.

The RaceLink WebUI, RotorHazard plugin, and external adapters should call the same internal actions and receive consistent results.

### Work items

- Define the internal RaceLink action model.
- Ensure scene execution, group control, node actions, startblock commands, sync commands, and blackout commands are available through this model.
- Align the WebUI command path with the same action dispatcher used by external APIs.
- Provide a documented REST API for command-style interaction.
- Provide a documented live event/status stream via WebSocket or the existing SSE infrastructure.
- Add clear command result objects:
  - accepted
  - rejected
  - queued
  - sent
  - timed out
  - failed
- Add a basic external-command log for diagnostics.
- Add rate limiting at the action-dispatch layer, not separately inside each adapter.
- Add an explicit external-control enable/disable setting.

### Acceptance criteria

- A scene can be started through the WebUI, RotorHazard plugin, and REST API with the same execution behavior.
- Device/group/status information can be consumed by an external client without scraping the WebUI.
- Failed or rejected commands produce structured errors.
- External commands are visible in diagnostics.
- The public API is documented in the RaceLink docs.

---

## Stage 2 — External input adapters

Status: Planned  
Primary repository: `RaceLink_Host`

### Goal

Allow established lighting and show-control software to control RaceLink without requiring operators to use the RaceLink WebUI for advanced show operation.

RaceLink should behave like a controllable backend for LoRa-connected race/event devices.

### 2.1 OSC input adapter

OSC should be the first semantic show-control adapter after the core API is stable.

#### Why OSC

OSC maps naturally to RaceLink actions and is common in show-control environments, media-control workflows, custom controllers, and integration tools.

Example address model:

```text
/racelink/scene/start 5
/racelink/group/2/preset 12
/racelink/group/1/brightness 180
/racelink/sync/send
/racelink/startblock/arm 3
/racelink/system/blackout
```

#### Work items

- Add OSC listener configuration.
- Map OSC addresses to internal RaceLink actions.
- Document the supported OSC address space.
- Add adapter-level enable/disable state.
- Add rate limiting and diagnostics through the shared action layer.
- Add optional source filtering if needed.

#### Acceptance criteria

- An external OSC tool can trigger scenes, group presets, sync, startblock actions, and blackout.
- OSC commands appear in the external-command log.
- The WebUI does not need new show-operation screens for OSC workflows.

### 2.2 Art-Net/sACN input adapter as a virtual RaceLink fixture

Art-Net and sACN input should be implemented as a mapping layer, not as a LoRa transport for DMX frames.

#### Goal

Allow lighting software and lighting consoles to control RaceLink using a small number of channels.

Example virtual fixture layout:

| Channel | Meaning |
| ---: | --- |
| 1 | Scene ID |
| 2 | Scene trigger |
| 3 | Group ID |
| 4 | Brightness |
| 5 | RL preset ID |
| 6 | WLED preset slot |
| 7 | Effect ID |
| 8 | Effect speed |
| 9 | Effect intensity |
| 10 | Palette / color mode |
| 11 | Sync trigger |
| 12 | Blackout trigger |

The exact channel model should be versioned and documented.

#### Required behavior

- Detect meaningful changes instead of forwarding every frame.
- Treat trigger channels as edge-triggered where appropriate.
- Apply rate limits before sending LoRa commands.
- Allow per-universe and per-address configuration.
- Expose the active mapping in the WebUI.
- Keep mapping simple enough that RaceLink does not become a fixture-library manager.
- Prefer scene/preset/cue triggers over continuously changing values.

#### Non-goals

Same boundaries as the "Mapping, not streaming" principle: no frame-by-frame DMX/pixel/audio streaming over LoRa, no DMX fixture patchbay, and no attempt to emulate a lighting desk inside RaceLink.

#### Acceptance criteria

- A lighting application can trigger RaceLink scenes through Art-Net or sACN.
- Channel changes can map to RaceLink group actions.
- Continuous Art-Net/sACN input does not flood the LoRa network.
- Operators can see which universe/mapping is active.
- The mapping is documented as a virtual RaceLink fixture.

### 2.3 MQTT / Home Assistant adapter

MQTT is useful for automation and status integration, but should not be treated as the primary live show-control path.

#### Intended use

- Home Assistant integration
- Node-RED workflows
- automation dashboards
- status publishing
- simple command topics

Example topic model:

```text
racelink/status/gateway
racelink/status/devices
racelink/status/groups
racelink/event/race/start
racelink/event/race/finish
racelink/cmd/scene/start
racelink/cmd/group/1/preset
racelink/cmd/sync
racelink/cmd/system/blackout
```

#### Acceptance criteria

- RaceLink can publish gateway, device, group, and event status.
- RaceLink can accept selected command topics.
- MQTT behavior is documented as automation-oriented, not low-latency show streaming.

---

## Stage 3 — Keep the WebUI focused

Status: Planned  
Primary repository: `RaceLink_Host`

### Goal

Prevent the RaceLink WebUI from becoming a replacement for professional lighting tools.

The WebUI should provide the necessary setup, monitoring, and fallback operation, while advanced live operation can move to external tools.

### Work items

- Create a compact "External Control" page or section.
- Show enabled adapters and their status.
- Show last external commands and rejected commands.
- Configure API tokens or local-network access policy if needed.
- Configure Art-Net/sACN mapping.
- Configure OSC listener settings.
- Configure MQTT broker/topics.
- Configure ownership/priority rules.
- Add import/export for adapter mappings if useful.

### Explicit non-goals

The WebUI should not grow into a full lighting desk, fixture-library manager, DMX patchbay, timeline/cue-stack editor, pixel mapper, beat/audio-analysis tool, or MIDI control-surface designer — the full list lives under "Avoid unnecessary WebUI growth". External tools may provide these features; the RaceLink integration stays event-oriented.

---

## Stage 4 — Ownership, priorities, and safety

Status: Planned  
Primary repository: `RaceLink_Host`

### Goal

Make simultaneous control paths predictable.

RaceLink can be controlled by the WebUI, RotorHazard, REST, OSC, Art-Net/sACN, MQTT, and possibly automation systems. Without explicit ownership rules, these sources can fight each other.

### Proposed priority model

Initial priority order:

| Priority | Source |
| ---: | --- |
| 100 | Emergency / blackout |
| 90 | Safety-critical system actions |
| 80 | Race events / RotorHazard |
| 70 | Explicit external live control |
| 60 | WebUI manual operation |
| 40 | Automation / MQTT |
| 20 | Passive status/reporting |

### Work items

- Add source identity to every action.
- Add priority to every action.
- Add per-group or global ownership state.
- Add timeout for external live control.
- Add "Take over from external control" action in the WebUI.
- Make emergency blackout always available.
- Log rejected actions with a reason.

### Acceptance criteria

- Operators can understand why a command was accepted or rejected.
- External live control can time out cleanly.
- RotorHazard race events cannot be accidentally overridden by low-priority automation.
- Emergency blackout remains available from every supported control path.

---

## Stage 5 — Output adapters to standard lighting systems

Status: Later  
Primary repository: `RaceLink_Host`

### Goal

Allow RaceLink events to trigger standard lighting systems when RaceLink is used as the race/event orchestrator.

This is the reverse direction of Stage 2: instead of external software controlling RaceLink, RaceLink can trigger external lighting.

### 5.1 Art-Net/sACN output

#### Intended use

- Trigger simple DMX looks on race start/finish.
- Send blackout to standard fixtures.
- Control a small number of channels from RaceLink scenes.
- Coordinate RaceLink LoRa nodes with wired or networked lighting fixtures.

#### Non-goals

- RaceLink should not become a full Art-Net/sACN lighting engine.
- RaceLink should not manage large fixture libraries.
- RaceLink should not replace existing lighting-control applications.

### 5.2 OLA / USB-DMX backend

OLA is a good candidate for hardware DMX support because it can abstract different DMX interfaces and protocols outside RaceLink.

#### Intended architecture

```text
RaceLink_Host
    ↓
OLA daemon
    ↓
USB-DMX / Art-Net / sACN / other OLA-supported backends
```

#### Benefit

RaceLink can trigger DMX without directly supporting every USB-DMX adapter.

### 5.3 WLED JSON output

RaceLink may optionally control normal IP-based WLED devices in addition to LoRa-connected RaceLink WLED nodes.

#### Intended use

- Mixed setups with RaceLink LoRa nodes and existing Wi-Fi WLED devices.
- Simple scene/preset coordination.
- Non-critical decorative lighting.

#### Constraint

A single WLED device should not be controlled by LoRa RaceLink commands and WLED JSON realtime commands at the same time unless ownership rules make the behavior explicit.

---

## Stage 6 — Optional hardware extensions

Status: Later  
Primary repositories: `RaceLink_Gateway`, future node repositories

Hardware extensions should only be added when Host-side integrations are not enough.

### 6.1 Gateway with DMX output

A Gateway variant with DMX output is technically possible, but should not be the first integration path.

#### Potential benefit

- One physical RaceLink box can output LoRa and DMX.
- Simple race-triggered DMX looks can be generated without a separate USB-DMX interface.

#### Risks

- Gateway firmware becomes more complex.
- DMX requires continuous frame generation.
- Hardware needs proper RS-485 design, ESD protection, connector choice, and ideally galvanic isolation.
- The gateway's primary USB-to-LoRa reliability must not be compromised.

#### Decision rule

Build this only if Host + OLA/USB-DMX proves insufficient for real deployments.

### 6.2 RaceLink DMX Node

A separate LoRa-controlled DMX node may be more useful than adding DMX to the gateway.

#### Intended use

```text
RaceLink_Host → USB Gateway → LoRa → RaceLink_DMX_Node → DMX fixtures
```

#### Constraint

The node should execute local DMX cues or simple DMX looks. It should not receive continuous DMX universes over LoRa.

Good use cases:

- blackout
- fixed color scene
- dimmer level
- strobe on/off
- fixture macro
- locally stored cue

Bad use cases: full wireless DMX universes, high-rate pixel streaming, Art-Net/sACN tunneling, or continuous audio-reactive control over LoRa — see "Mapping, not streaming".

### 6.3 RaceLink IO Node

A generic IO node may be more broadly useful than DMX-specific hardware.

Possible functions:

- physical buttons
- relay outputs
- start triggers
- gate inputs
- sensor inputs
- status lamps
- auxiliary outputs for race equipment

This node type fits RaceLink's event-oriented architecture well.

### 6.4 Hardware paths to avoid initially

The following are technically possible but not recommended as early roadmap items:

- DMX input directly on the Gateway
- Art-Net/sACN over Wi-Fi directly on the Gateway
- making the Gateway a general lighting network bridge

(Tunneling DMX/pixel/beat-reactive frames over LoRa is already excluded by the "Mapping, not streaming" principle.) These paths move mapping, ownership, network configuration, and UI complexity into firmware where the Host is a better fit.

---

## Documentation roadmap

Every integration feature should ship with documentation at the same time as the implementation.

Required docs:

- external-control overview
- action model reference
- REST API reference
- event stream reference
- OSC address reference
- Art-Net/sACN virtual fixture mapping
- MQTT topic reference
- ownership/priority model
- troubleshooting guide for external control
- security/networking notes for local API exposure

---

## Compatibility and versioning

External-control interfaces must be versioned carefully.

Guidelines:

- Keep the action model stable once published.
- Version the Art-Net/sACN virtual fixture layout.
- Document breaking changes before release.
- Prefer additive API changes.
- Keep deprecated endpoints available for at least one documented transition period where feasible.
- Avoid exposing internal Python implementation details as public API contracts.

---

## Deferred engineering backlog

The following items were previously listed as the main roadmap. They are still useful engineering ideas, but they are not the primary product roadmap.

They should be promoted back into an active stage only when they directly support the integration-first direction described above.

### Capability-aware broadcast addressing

Status: Deferred. Broadcast today is group-based only; a future wire-level capability filter could target "WLED nodes only" or "Startblock nodes only", making broadcast labels and behaviour more precise in mixed fleets. **Decision:** keep deferred until mixed-capability fleets justify a wire-protocol change.

### Group-agnostic re-identification

Status: Deferred. A discovery mode that identifies devices regardless of their stored group ID would ease recovery when device and Host repository state drift apart. **Decision:** keep deferred unless field usage shows group drift is a common operator problem.

### Capability function visibility taxonomy

Status: Deferred. Capability functions could carry visibility metadata so a function appears in one UI/API surface but not another:

```python
{
    "key": "wled_preset",
    "label": "WLED Preset",
    "comm": "sendWledPreset",
    # ...
    "visibility": ["scene-editor"],   # ← new
}
```

This avoids WebUI clutter while keeping programmatic functions available to scenes or external APIs. **Decision:** the most roadmap-aligned backlog item — reconsider during Stage 1 or Stage 3 if the action model and external API need the same metadata.

### Hide "WLED Preset" from the Device Options dialog

Status: Deferred. The dialog exposes WLED preset behaviour in a way that can conflict with RaceLink presets and segment/default assumptions — a WebUI-scope cleanup. **Decision:** implement together with the capability visibility mechanism above rather than as a one-off UI deletion.

### Lean down the headless scene-execution path

Status: Deferred. Some scene-execution work runs even when no browser/SSE client is connected; avoiding it would slightly reduce overhead on headless race paths and improve code cleanliness. **Decision:** keep deferred — the operator-visible gain is small compared to integration and API work.

### Asynchronous / pipelined gateway TX

Status: Deferred. The gateway serializes transmission, leaving per-packet overhead; a non-blocking transmit path with a small queue could improve multi-packet scene wall-clock time. **Decision:** keep deferred until a measurable need appears — valuable, but should not block the external-control roadmap.

---

## Non-goals

The following are intentionally not part of the current roadmap:

- replacing professional lighting consoles
- replacing QLC+, xLights, Resolume, TouchDesigner, Companion, or similar tools
- streaming full DMX universes over LoRa
- streaming pixel data over LoRa
- transporting continuous audio-reactive or beat-synchronized control frames over LoRa
- turning the RaceLink WebUI into a full show editor
- putting Art-Net/sACN mapping logic into Gateway firmware as the default approach
- adding hardware interfaces before Host-side adapters prove insufficient
