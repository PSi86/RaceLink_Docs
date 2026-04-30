# RaceLink WLED Usermod

A custom WLED usermod for **RaceLink wireless nodes**.

This repository contains the RaceLink-specific WLED usermod code as well as ready-to-use **build profiles** for supported hardware variants. It is intended for users who want to build WLED firmware with RaceLink support **without depending on a custom WLED fork**.

In a typical setup:

- **RaceLink_WLED** provides the wireless node firmware
- **RaceLink_Gateway** sends commands to those nodes, receives their responses, and bridges the wireless link to USB
- **RaceLink_Host** communicates with the gateway over USB and provides higher-level control logic, integrations, and web interfaces

This repository is focused on the **WLED-based node side** of the RaceLink ecosystem. It does **not** contain the gateway firmware and it does **not** contain the host-side application.

> **Status:** Testing.

---

## What this repository provides

- the **RaceLink WLED usermod**
- ready-to-use **PlatformIO build profiles** for supported hardware variants
- board-specific compile-time settings such as:
  - wireless modem selection
  - SPI pin definitions
  - LED pin and strip configuration
  - selected WLED feature flags
  - battery usermod configuration
  - optional e-paper display support

At the moment, the hardware-specific pin mappings are still defined in the build profiles. In a future revision, these settings may be moved into the WLED usermod configuration UI.

---

## Role in the RaceLink ecosystem

RaceLink_WLED provides the wireless node firmware layer of the
RaceLink system. For the system-level diagram and component table,
see the top-level [the home page](../index.md) §"System overview".

Typical responsibilities of the WLED-based node firmware:

- receiving RaceLink packets over the wireless link
- applying control and configuration commands on the node
- driving one or more LED outputs through WLED
- participating in synchronization flows
- reporting node responses and device-specific status back through the gateway to the host
- optionally supporting battery monitoring and e-paper display features on supported hardware

---

## Current project structure

The repository currently contains the RaceLink WLED usermod sources plus build-profile files for supported hardware variants:

```text
RaceLink_WLED/
└─ build_profiles/
   ├─ RaceLink_Node_v1_c3_ct62.platformio_override.ini
   ├─ RaceLink_Node_v3_s2_llcc68.platformio_override.ini
   ├─ RaceLink_Node_v3_s2_llcc68_epaper.platformio_override.ini
   ├─ RaceLink_Node_v4_s3_llcc68.platformio_override.ini
   ├─ bak_RaceLink_Node_v3_s2_llcc68.platformio_override.ini
   └─ all_profiles.platformio_override.ini
├─ library.json
├─ racelink_epaper.cpp
├─ racelink_epaper.h
├─ racelink_proto.h
├─ racelink_transport_core.h
├─ racelink_wled.cpp
├─ racelink_wled.h
└─ readme.md
```

This layout combines the usermod source itself with the hardware-specific PlatformIO override profiles required to build supported RaceLink node variants.

---

## Supported hardware profiles

The repository currently includes the following build profiles:

- `RaceLink_Node_v1_c3_ct62.platformio_override.ini`
- `RaceLink_Node_v3_s2_llcc68.platformio_override.ini`
- `RaceLink_Node_v3_s2_llcc68_epaper.platformio_override.ini`
- `RaceLink_Node_v4_s3_llcc68.platformio_override.ini`
- `bak_RaceLink_Node_v3_s2_llcc68.platformio_override.ini`
- `all_profiles.platformio_override.ini`

These profiles contain the required compile-time configuration for the currently supported RaceLink node hardware.

---

## Requirements

Before building, make sure you have:

- a local checkout of the official **WLED** repository
- **PlatformIO** installed  
  Either through **VS Code + PlatformIO extension** or a standalone PlatformIO installation
- a supported ESP32-based target board
- the matching RaceLink build profile for your hardware

For GitHub-hosted release builds, this repository now also contains a release workflow that checks out the official `wled/WLED` source tree automatically. Maintainers do not need to vendor the WLED codebase into this repository.

---

## Quick start

### 1. Get the official WLED repository

Clone or download the official WLED repository:

```bash
git clone https://github.com/wled/WLED.git
```

You can also fork it on GitHub first and then clone your fork.

### 2. Get this RaceLink repository

Clone or download this repository:

```bash
git clone https://github.com/PSi86/RaceLink_WLED.git
```

### 3. Select the matching build profile

Choose the `.platformio_override.ini` file that best matches your hardware from the `build_profiles` directory.

### 4. Copy it into the WLED root directory

Copy the selected profile into the root of your local WLED checkout and rename it to:

```text
platformio_override.ini
```

WLED loads this file automatically via its PlatformIO configuration.

### 5. Build the firmware

Run PlatformIO with the environment defined in the selected profile:

```bash
pio run -e <envname>
```

or build it directly from **VS Code / PlatformIO**.

---

## Example build commands

Depending on the selected profile, typical build commands may look like this:

```bash
pio run -e RaceLink_Node_v1_c3_ct62
pio run -e RaceLink_Node_v3_s2_llcc68
pio run -e RaceLink_Node_v3_s2_llcc68_epaper
pio run -e RaceLink_Node_v4_s3_llcc68
```

---

## GitHub release workflow

The supported path for publishing firmware artifacts is the manual GitHub Actions workflow in `.github/workflows/release.yml`.

That workflow:

- uses this repository as the canonical source for the RaceLink usermod and release version
- checks out the official `wled/WLED` repository into a temporary build directory
- defaults to the latest published WLED release unless a specific `wled_ref` is entered in the workflow UI
- stages the local RaceLink usermod into the checked-out WLED tree
- stages each shipping `platformio_override.ini` profile and builds only the `[env:...]` targets defined in that profile
- publishes the resulting firmware artifacts plus a checksum manifest into a GitHub release

### Release versioning

Release versioning follows the same pattern used by `RaceLink_Host` and `RaceLink_RH_Plugin`:

- `version.json` is the canonical source of the RaceLink_WLED release version
- the workflow accepts an optional `version` override
- if `version` is empty, the workflow increments the current patch version automatically
- the workflow commits `version.json`, creates the `v<version>` tag, pushes the selected branch and tag, and then publishes the GitHub release

### Manual release flow

1. Open GitHub Actions and run `.github/workflows/release.yml`.
2. Set `target_branch` to the branch you want to release from.
3. Optionally set `version`.
4. Optionally set `wled_ref`. If it is left empty, the workflow resolves the latest published WLED release automatically.
5. The workflow builds the shipping RaceLink profiles, uploads the firmware binaries plus a checksum manifest, commits the release metadata, creates the release tag, and publishes the GitHub release.

### Local development vs release builds

Local development builds still follow the normal manual process described earlier in this README: you work against your own WLED checkout and copy a selected profile to `platformio_override.ini`.

GitHub-hosted release builds are different:

- they always start from a fresh official WLED checkout
- they stage the current RaceLink_WLED branch contents into that checkout
- they package release-ready binaries for all shipping RaceLink profiles in one release

---

## Build profile notes

The provided build profiles currently define hardware-specific values such as:

- modem type (`RACELINK_SX1262` or `RACELINK_LLCC68`)
- SPI pin mapping for the radio
- radio parameters such as frequency, bandwidth, spreading factor, and TX power
- LED data pins and bus configuration
- battery measurement settings
- optional e-paper display pin mapping

This means that users should **start with the closest matching profile** and then adjust it if their hardware differs.

---

## Using this repository as an external usermod source

The intended usage model is:

1. keep your local WLED checkout based on the **official WLED repository**
2. reference this repository through `custom_usermods`
3. keep all RaceLink-specific board settings inside `platformio_override.ini`

This avoids the need for a dedicated WLED fork just to build RaceLink-enabled firmware.

---

## Integration with other RaceLink repositories

For the full component table and repository URLs, see the top-level
[the home page](../index.md). The official upstream WLED source is
at https://github.com/wled/WLED. For operator-side WLED-node setup,
see [`OPERATOR.md`](operator-setup.md).

---

## Customizing for your own hardware

If your hardware differs from the provided profiles, you will most likely need to adjust:

- radio SPI pins
- modem type
- LED pin definitions
- button pin
- battery measurement pin and scaling
- optional e-paper pins
- selected WLED feature flags

For derived hardware, it is usually easiest to duplicate the closest matching profile and modify only the necessary values.

---

## Troubleshooting

### Build fails because the environment name does not exist

Make sure the environment name passed to `pio run -e ...` matches the `[env:...]` section inside the selected profile.

### Usermod is not found

Verify that the selected profile contains the correct `custom_usermods` entry and that the referenced repository or local path is available.

### Wrong pin mapping or non-working radio

Check the `RACELINK_PIN_*` definitions and modem selection in the chosen build profile.

### Wrong battery reading

Review the battery measurement pin and voltage multiplier settings in the profile.

### The firmware builds but does not behave as expected in the RaceLink system

Check that the node build profile matches the actual hardware and that the gateway and host components in the rest of the system are using compatible settings and firmware versions.

---

## Intended audience

This repository is mainly intended for:

- RaceLink node firmware builds
- custom WLED-based RaceLink hardware
- development and testing of RaceLink-compatible wireless nodes
- developers building complete RaceLink systems from host to gateway to node

---

## Related repositories

See the consolidated component table in
[the home page](../index.md). Upstream WLED:
https://github.com/wled/WLED.

---

## Notes

This repository provides the **WLED-based wireless node layer** of the RaceLink project.

It does not replace the official WLED repository, but extends it with RaceLink-specific functionality and hardware profiles so that RaceLink-compatible wireless nodes can be built and integrated into the larger RaceLink system.
