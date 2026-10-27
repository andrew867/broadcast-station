# Running without a monitor or desktop login

Headless mode renders directly on the GPU through EGL. It does not mount an X11 socket, read a desktop authentication cookie, or connect to KDE, Wayland or PipeWire. CasparCG's HTML renderer uses its headless Chromium path with the Vulkan backend.

This mode is for network or file output. Music still mixes into the program and the output encoder still includes audio. A desktop HDMI window and desktop-speaker monitoring require desktop mode. You can watch a headless station through its encoded network output from another computer.

## Prepare and start

Use the normal [Linux installation](LINUX-DEPLOYMENT.md) prerequisites and select `--gpu nvidia` or `--gpu intel`. NVIDIA still requires the host driver and NVIDIA Container Toolkit. Intel requires access to `/dev/dri/renderD128`; this is a render device, not a desktop session.

In the station's `station.json`, set:

```json
"headless": true,
"hdmi": false,
"desktop_audio": false
```

These fields belong inside `output`. Also review `output.playout`, publishing destinations, providers and credentials as for any full station. Headless mode does not enable them for you.

From the release directory:

```sh
python3 tools/stationctl.py check /path/to/station --gpu nvidia
python3 tools/stationctl.py start /path/to/station --gpu nvidia
```

For Intel use `--gpu intel` and the accepted HD30/libx264 profile. `start` builds images; `resume` uses existing images and performs no build or download. The launcher chooses the correct Compose display profile and Intel EGL platform automatically. The supplied engine profile removes desktop variables even if they were embedded in a custom base image.

Do not combine `compose.desktop.yaml` with `compose.headless.yaml`. The launcher selects one. Direct Compose invocations must include the matching GPU and display profiles; use the launcher to avoid stale desktop mounts or mismatched settings.

## Start at boot

For an existing desktop station, first remove its desktop startup entry with `python3 tools/install_autostart.py remove /path/to/station`. Remove its old runtime services with `python3 tools/install_runtime_services.py remove /path/to/station` before reinstalling them for headless mode. This prevents the old graphical-session hooks from remaining enabled.

After a successful check and initial start:

```sh
python3 tools/install_headless_startup.py install /path/to/station --gpu nvidia
sudo loginctl enable-linger "$USER"
```

The first command installs a station-specific user service. Lingering lets that user's service manager start without an interactive login. It is a host administrator action, not a container privilege. Docker must also be enabled at boot, and the station user must already be allowed to use it.

The startup service waits for prerequisites and resumes prebuilt images. Existing Docker restart policies handle container exits. For the station's bounded output-recovery watchdog:

```sh
python3 tools/install_runtime_services.py install /path/to/station --gpu nvidia --monitor-url rtmp://192.0.2.10/program-monitor
```

Replace that documentation-only address with your separate credential-free program-monitor URL. In headless mode this watchdog follows the user service manager, not the graphical session. Do not install the desktop-display helper for this mode. A `runtime/maintenance` marker prevents automatic startup and watchdog recovery; manually stop containers before planned maintenance.

### Laptop lid policy

KDE's lid-close preference applies to its desktop session. Without that session, systemd-logind can suspend a laptop with a closed lid shortly after boot, even when the station has already started.

For a station that should keep running while plugged in, an administrator can create `/etc/systemd/logind.conf.d/70-station-ac-lid.conf` containing:

```ini
[Login]
HandleLidSwitch=suspend
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
```

Apply the change during the planned reboot test. Do not restart logind casually during active desktop use. This preserves the normal lid-close suspend action on battery; it does not replace critical-battery protection. Confirm the effective settings with `systemd-analyze cat-config systemd/logind.conf`, then verify the station remains reachable after boot without an interactive login. Keep the laptop's ventilation unobstructed.

## Check the result

Confirm current decoded video and audio at a receiver, not merely an open connection. Inspect the engine log for EGL and the expected NVIDIA or Intel OpenGL vendor. A software renderer is not a substitute for hardware acceptance.

The isolated acceptance tool can record synthetic video, HTML graphics and audio without touching the station:

```sh
python3 tools/check_native_output.py station-engine:candidate --headless --gpu nvidia --profile 2160p3000 --evidence evidence/nvidia-headless
python3 tools/check_native_output.py station-engine:candidate --headless --gpu intel --profile 1080p3000 --evidence evidence/intel-headless
```

Only run the appropriate command on its host. These bounded checks consume GPU resources alongside other work. GitHub also tests headless software EGL as a functional regression check, without claiming software-rendering speed or hardware performance.

## Return to desktop output

Remove the headless startup service with `install_headless_startup.py remove`, stop the station for the configuration change, set `output.headless` to false, then enable the desired HDMI/desktop-audio settings. Run `stationctl check` and `resume` from the logged-in desktop. Remove and reinstall runtime services for the new mode and use the normal desktop-autostart helper. The change recreates the engine; schedule it as an output interruption.

Upstream reference: [CasparCG headless Linux guide](https://casparcg.com/docs/guides/linux-headless). The station packaging additionally isolates desktop sockets and keeps provider secrets outside the image. AMD, ARM and arbitrary GPU/driver combinations have not been hardware-qualified by these checks.
