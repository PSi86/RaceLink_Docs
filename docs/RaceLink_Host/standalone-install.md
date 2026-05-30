# RaceLink Standalone Guide

This guide explains how to install and run `racelink-host` in standalone mode on Windows and Linux.

Standalone mode runs the RaceLink host runtime and the shared RaceLink WebUI without RotorHazard. It is intended for gateway-backed operation, so a connected RaceLink Gateway is expected for normal use.

## Requirements

- Python `3.10` or newer
- A terminal or shell
- A RaceLink Gateway connected by USB for normal operation
- Network access to install Python packages

The packaged standalone entrypoint is:

```bash
racelink-standalone
```

Default standalone URL:

```text
http://127.0.0.1:5077/racelink
```

## Get the release wheel

`racelink-host` is published as a GitHub release artifact (not on PyPI).
Download the wheel for the version you want from the project's releases
page:

```text
https://github.com/PSi86/RaceLink_Host/releases
```

Save `racelink_host-<version>-py3-none-any.whl` and note its path — the
install commands below reference that file. (For the offline `.tar.gz`
bundle and the release/build flow, see the Host README.)

## Windows installation and usage

These steps use a folder named `RaceLink` in your user directory
(`C:\Users\<your-name>\RaceLink`). You can pick another location — just
use the same folder for every command.

**Step 1 — Create the folder and put the wheel in it.**
Open File Explorer, go to your user folder, create a new folder named
`RaceLink`, and move the downloaded
`racelink_host-<version>-py3-none-any.whl` ([from the releases
page](#get-the-release-wheel)) into it.

**Step 2 — Open PowerShell inside that folder.**
Open the `RaceLink` folder in File Explorer, click the address bar, type
`powershell`, and press Enter. PowerShell opens already pointed at the
folder.

!!! important "Edit the command before running it"
    In the block below, replace **`<version>`** with the version you
    downloaded — e.g. for `racelink_host-0.1.6-py3-none-any.whl` use
    `0.1.6`. If you chose a folder other than
    `C:\Users\<your-name>\RaceLink`, also adjust the `cd` path.

**Step 3 — Install:**

```powershell
cd $env:USERPROFILE\RaceLink
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .\racelink_host-<version>-py3-none-any.whl
```

`racelink-host` is distributed as a GitHub release artifact (not PyPI),
so this installs the downloaded `.whl` directly; its runtime
dependencies (Flask, pyserial) come from PyPI.

!!! note "If activation is blocked by the execution policy"
    On a fresh Windows install the default PowerShell execution policy
    blocks `Activate.ps1` with a security error. Allow signed scripts for
    the current session, then re-run the whole block from Step 3:

    ```powershell
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
    ```

**Step 4 — Start RaceLink and open the UI:**

```powershell
racelink-standalone --open-browser
```

`--open-browser` opens `http://127.0.0.1:5077/racelink` in your default
browser once the server is ready. Leave the PowerShell window open while
you use RaceLink; press `Ctrl+C` (or close the window) to stop it.

**On later runs** you only re-activate and start — no reinstall:

```powershell
cd $env:USERPROFILE\RaceLink
.venv\Scripts\Activate.ps1
racelink-standalone --open-browser
```

### Create a desktop shortcut (Windows)

So you can launch RaceLink with a double-click, create a file
`RaceLink.bat` in your `RaceLink` folder. In Notepad, paste the lines
below, then **Save As** → set *Save as type* to **All files** → name it
`RaceLink.bat`:

```bat
@echo off
cd /d "%USERPROFILE%\RaceLink"
call .venv\Scripts\activate.bat
racelink-standalone --open-browser
```

Double-clicking `RaceLink.bat` now starts the server and opens the WebUI
automatically (the `.bat` uses the cmd activation, so the PowerShell
execution-policy note above does not apply). To put it on the desktop,
right-click `RaceLink.bat` → **Show more options → Send to → Desktop
(create shortcut)**. A small console window stays open while RaceLink
runs — closing it stops the server.

Windows notes:

- The RaceLink Gateway appears as a `COM` port, typically a `Silicon Labs CP210x USB to UART Bridge` (for example `COM12`); check Device Manager if you are unsure which port it is
- You normally do not need to configure the port. On startup the host probes every USB serial port and auto-attaches any gateway that answers the identify handshake — see [Gateway detection and reconnect](#gateway-detection-and-reconnect)
- Set `rl_comms_port` (see [Configuration file](#configuration-file)) only to pin one specific device, for example when several serial adapters are attached

### Windows firmware updates (WLED OTA)

WLED node firmware updates are supported on Windows. The host drives its
own WiFi via `netsh wlan` to connect to each node's SoftAP, push the
firmware/config over HTTP, and disconnect again — the Windows equivalent
of the Linux `nmcli` flow.

!!! warning "Prerequisite: enable Windows Location Services"
    On Windows 10/11 the `netsh wlan` APIs **only expose WiFi network
    names (SSIDs) when Location Services is enabled** — this applies to
    both scanning *and* reading the currently-connected SSID. With
    Location off, the host can neither find the WLED access point nor
    confirm a connection, and the update fails with *"could not connect …
    no association within window"* even though Windows briefly associates.

    Enable it once under **Settings → Privacy & security → Location**
    (shortcut: paste `ms-settings:privacy-location` into the address bar
    or the **Win+R** Run box): turn on **Location services** *and* **Let
    desktop apps access your location**. RaceLink detects this state and
    fails fast with the same instruction (including the shortcut) instead
    of timing out.

    This is a global / device-level Windows setting — it cannot be granted
    to RaceLink alone. Per-app location toggles only exist for Store/UWP
    apps; classic desktop apps (like `racelink-standalone`) are all
    covered by the single "Let desktop apps access your location" switch.

Other Windows specifics:

- **The WLAN adapter must be enabled.** The host connects using the
  already-on adapter. If the adapter is disabled, enabling it from within
  RaceLink requires running the host as Administrator — easier to just
  switch WiFi on in Windows first.
- **A "sign in to the network" / captive-portal browser tab may pop up.**
  When Windows joins the WLED AP it probes for internet, finds none, and
  may open a browser (e.g. an MSN sign-in page). This is normal Windows
  behaviour and does **not** affect the update — the host still reaches
  the node at its AP address. You can close the tab.
- **No BSSID targeting.** `netsh` connects by SSID only and cannot pin a
  specific access point. If several nodes broadcast the *same* AP SSID,
  Windows may associate with the wrong one. Flash such fleets **one node
  at a time**, or give each node a unique AP SSID. (Single-node OTA is
  unaffected.)
- **Tip:** if your node uses only one of the default SSIDs, set that one
  explicitly in the Firmware Update dialog. The host tries each candidate
  SSID in turn, so trimming the list skips a wasted connect attempt on
  the SSID your node doesn't broadcast.
- The Firmware Update dialog's WLED-AP SSID/password defaults
  (`WLED_RaceLink_AP, WLED-AP` / `wled1234`) apply the same as on Linux;
  both WPA2 and open WLED APs are handled.

!!! note "Connecting to a WLED AP and other network traffic"
    Joining a WLED SoftAP (which has no internet) can make Windows
    juggle connections: you may see the WiFi status flip between
    *connecting* / *available* / *disconnected*, and historically — when
    the RaceLink WebUI was served from a **separate** machine (e.g. a
    RotorHazard Raspberry Pi on Ethernet) — the operator PC connecting
    its WiFi to a WLED hotspot could stall that remote WebUI until the
    WiFi was disconnected. Running `racelink-standalone` **locally** on
    the same PC avoids this: the WebUI is served over loopback
    (`127.0.0.1`) and is unaffected by WiFi routing. If association
    still won't hold, temporarily disconnect/forget any nearby
    internet WiFi so Windows can't roam away from the no-internet WLED
    AP during the update.

## Linux installation and usage

These steps use a folder named `racelink` in your home directory
(`~/racelink`). You can pick another location — just use the same folder
for every command.

**Step 1 — Create the folder and put the wheel in it.**

```bash
mkdir -p ~/racelink
```

Then download / move `racelink_host-<version>-py3-none-any.whl`
([from the releases page](#get-the-release-wheel)) into `~/racelink`.

!!! important "Edit the command before running it"
    In the block below, replace **`<version>`** with the version you
    downloaded — e.g. for `racelink_host-0.1.6-py3-none-any.whl` use
    `0.1.6`. If you chose a folder other than `~/racelink`, also adjust
    the paths.

**Step 2 — Install:**

```bash
cd ~/racelink
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ./racelink_host-<version>-py3-none-any.whl
```

`racelink-host` is distributed as a GitHub release artifact (not PyPI),
so this installs the downloaded `.whl` directly; its runtime
dependencies (Flask, pyserial) come from PyPI.

**Step 3 — Start RaceLink and open the UI:**

```bash
racelink-standalone --open-browser
```

`--open-browser` opens `http://127.0.0.1:5077/racelink` in your default
browser once the server is ready. Leave the terminal open while you use
RaceLink; press `Ctrl+C` to stop it.

**On later runs** you only re-activate and start — no reinstall:

```bash
cd ~/racelink
source .venv/bin/activate
racelink-standalone --open-browser
```

### Create a desktop shortcut (Linux)

Create a launcher script `~/racelink/racelink.sh`:

```bash
cat > ~/racelink/racelink.sh <<'EOF'
#!/usr/bin/env bash
cd "$HOME/racelink" || exit 1
source .venv/bin/activate
exec racelink-standalone --open-browser
EOF
chmod +x ~/racelink/racelink.sh
```

Then create a desktop entry so it shows up in your application menu.
Replace `YOUR_HOME` with the output of `echo $HOME` (desktop files do not
expand `$HOME` in `Exec`):

```bash
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/racelink.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=RaceLink Host
Comment=Start RaceLink Host and open the WebUI
Exec=YOUR_HOME/racelink/racelink.sh
Terminal=true
Categories=Utility;
EOF
```

`Terminal=true` keeps a window open showing logs; closing it stops the
server. Most desktops also let you copy the `.desktop` file to your
Desktop to get a clickable icon there.

Linux notes:

- The RaceLink Gateway usually appears as a serial device such as `/dev/ttyUSB0` or `/dev/ttyACM0`
- If RaceLink cannot open the gateway, check user permissions for serial devices
- On some systems you may need to add the user to a group such as `dialout`
- Wi-Fi helper features that depend on `nmcli` only work in environments where NetworkManager and `nmcli` are installed

### Linux first-time setup for firmware updates

The OTA flow connects the host's WiFi directly to a WLED node's AP via
`nmcli dev wifi connect <SSID> password <PASS>` and disconnects it
afterwards. No pre-created NetworkManager profile is required — NM
creates one persistent profile per SSID on first connect and reuses it
on subsequent runs.

The `nmcli` command needs polkit authorisation. On a fresh Linux host,
run the bundled setup helper once as root to grant the running user
unattended access:

```bash
sudo apt install network-manager       # Debian/Ubuntu/Pi OS only
sudo $(which racelink-setup-nmcli)     # absolute path; see below
# restart the host (RotorHazard or racelink-standalone) so the running
# Python process re-establishes its polkit subject
```

`racelink-setup-nmcli` is shipped as a console script alongside
`racelink-standalone`, so a `pip install racelink-host` puts it on the
host's `PATH`. **Use `sudo $(which racelink-setup-nmcli)` rather than
the bare command** — `sudo`'s default `secure_path` strips the venv's
`bin/` directory, so `sudo racelink-setup-nmcli` fails with
``command not found`` on piwheel / venv installs (the typical
RotorHazard plugin layout). The OTA failure dialog also surfaces the
exact absolute command for the install you're running, so you can
copy-paste it directly from the toast if `which` isn't on your PATH
either.

The helper is idempotent: adds the user to the `netdev` (or `wheel`
on Fedora/RHEL) group and installs a polkit rule at
`/etc/polkit-1/rules.d/49-racelink-nmcli.rules` that authorises
`org.freedesktop.NetworkManager.*` actions for that specific user.
Verify with `nmcli dev wifi list` — if it lists nearby APs without
prompting for a password, the host is ready.

If you've cloned the source repo instead of installing via `pip`, the
equivalent bash variant lives at `scripts/setup_nmcli_polkit.sh` and
writes the same polkit rule.

The Firmware Update dialog ships sensible defaults (SSID list
`WLED_RaceLink_AP, WLED-AP`, password `wled1234`). Override per-OTA if
your fleet uses a custom WLED AP password.

## Configuration file

Standalone mode stores its local configuration in:

```text
~/.racelink/rl_standalone_config.json
```

On Windows this usually expands to something like:

```text
%USERPROFILE%\.racelink\rl_standalone_config.json
```

On Linux this usually expands to something like:

```text
$HOME/.racelink/rl_standalone_config.json
```

!!! note "Upgrading from an older install"
    Earlier versions used unprefixed names (`standalone_config.json`,
    `scenes.json`, and a `presets/` folder). On first start the host
    renames them to the `rl_`-prefixed scheme automatically — no manual
    migration needed.

Example configuration:

```json
{
  "host": "127.0.0.1",
  "port": 5077,
  "debug": false,
  "options": {
    "rl_comms_port": "COM3"
  }
}
```

Useful fields:

- `host`: bind address for the standalone Flask server
- `port`: TCP port for the standalone Flask server
- `debug`: Flask debug mode
- `options`: persisted RaceLink options used by the host runtime
- `options.rl_comms_port`: **optional** serial-port pin. Leave it unset
  to use automatic gateway discovery. Accepts:
    - a single port (`"COM12"` on Windows, `"/dev/ttyUSB0"` on Linux) —
      pins that one device and skips the discovery probe
    - a comma-separated list (`"COM12,COM13"`) — multi-gateway pin:
      discovery runs, but only the listed ports are attached. Use this
      to bind a specific set of gateways in a multi-gateway rig and
      ignore any other RaceLink gateway that happens to be plugged in

To change the bind address or port, edit the config file before starting `racelink-standalone`.

The file is created automatically on first run, so you usually do not
need to write it by hand. `rl_comms_port` is shown above only to
illustrate the optional pin — it is not required for normal operation.

## File locations

All persistent data lives under the per-user RaceLink directory
`~/.racelink/`. `~` expands to `%USERPROFILE%` on Windows and `$HOME` on
Linux.

| Contents | Path (under `~/.racelink/`) |
|---|---|
| Standalone configuration | `rl_standalone_config.json` |
| Scenes | `rl_scenes.json` |
| RaceLink presets | `rl_presets.json` |
| Uploaded WLED preset files | `rl_wled_presets/` |

Uploaded firmware (`.bin`) and config/preset files for OTA are **not**
kept under `~/.racelink/`. They are staged in the operating system's
temporary directory and are disposable (cleared on reboot / temp
cleanup):

```text
Windows:  %TEMP%\racelink_uploads\
Linux:    /tmp/racelink_uploads/
```

Logs: standalone mode logs to the terminal (stdout/stderr) where you
started `racelink-standalone` at `INFO` level — it does not write a log
file. Set `RACELINK_LOG_LEVEL=DEBUG` for verbose traces (useful when
diagnosing gateway or OTA issues). To keep a log, redirect the console
output yourself, for example:

```powershell
$env:RACELINK_LOG_LEVEL="DEBUG"; racelink-standalone *> racelink.log   # Windows PowerShell
```

```bash
RACELINK_LOG_LEVEL=DEBUG racelink-standalone > racelink.log 2>&1       # Linux
```

(When RaceLink runs as the RotorHazard plugin instead of standalone,
logging is handled by RotorHazard's own logging system.)

## Verifying that standalone mode works

After starting the server:

1. Open `http://127.0.0.1:5077/`
2. Confirm it redirects to `/racelink`
3. Confirm the RaceLink WebUI loads successfully
4. Watch the terminal output for gateway startup messages

Expected behavior:

- Without a connected gateway, the UI can still load, but gateway communication will not be ready
- With a connected gateway, standalone mode should report that the communicator is ready and the WebUI should be able to interact with RaceLink services

## Gateway detection and reconnect

The host finds the gateway automatically: on startup it probes every
USB serial port, sends an identify handshake, and attaches any port that
answers as a RaceLink gateway. Every responding gateway is attached, so
a multi-gateway setup works out of the box. When it succeeds, the WebUI
shows the gateway as connected (state `bound`) and the master bar
reports the network as ready.

To restrict which gateways are attached, set `rl_comms_port` (see
[Configuration file](#configuration-file)): a single port pins exactly
that device and skips the probe; a comma-separated list (`"COM12,COM13"`)
attaches only the listed gateways while ignoring any others.

!!! note "If the gateway is not detected right after startup"
    Opening the USB serial port toggles the adapter's reset line, which
    reboots the gateway. If the startup probe lands while the gateway is
    still booting, the first attempt reports
    `No RaceLink Gateway module discovered or configured`. A missing
    gateway (`NOT_FOUND`) is **not** retried automatically, because that
    state normally means no hardware is present. Once the gateway has
    finished booting, trigger a manual reconnect from the WebUI (the
    gateway/reconnect control in the master bar) and it attaches within
    a second. This is expected on the first launch after plugging in the
    gateway.

## Manual validation checklist

- Create a fresh virtual environment
- Install `racelink-host` from the release wheel
- Start `racelink-standalone`
- Open the browser at `/racelink`
- Confirm `/` redirects to `/racelink`
- Confirm the shared RaceLink WebUI loads
- Confirm the gateway is reported as unavailable when no gateway is connected
- Connect the gateway and confirm it is auto-detected (or attaches after a manual reconnect if the first startup probe caught it mid-boot)
