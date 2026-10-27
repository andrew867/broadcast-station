# Linux station installation and operation

The offline preview remains `docker compose up --build`. Full playout uses the separate files below. The NVIDIA station has migrated and passed automatic reboot recovery. The T480s runs the accepted limited HD30 standby workload. Use [the current checklist](RELEASE-CHECKLIST.md) for clean-install and distribution gates.

## Prepare a machine

Use x86_64 Linux and Docker Engine with Compose and Buildx. NVIDIA installations require a working NVIDIA driver and NVIDIA Container Toolkit. Intel installations use the `--gpu intel` profile and an accessible `/dev/dri` render device; the accepted Intel output encoder is software H.264. Desktop output also needs xauth and an X11 or Xwayland session with working OpenGL. For a station without a monitor or desktop login, use [headless operation](HEADLESS.md), which renders directly through EGL. Do not use `xhost +`, privileged containers or a Docker socket inside the application.

Verify `docker compose version` and `docker buildx version` before building. Ubuntu distribution packages may require installing `docker-buildx` separately; Docker's official repository names it `docker-buildx-plugin`. Use the package matching your Docker installation. Existing-image resume does not require Buildx. The source-build launcher requires Buildx and reports a missing plugin before starting.

Prepare a new directory outside the checkout:

```sh
python3 tools/stationctl.py init "$HOME/station"
```

Edit `station.json`: choose location/timezone and HD30 or UHD30, set the upstream camera server, select the needed providers and set `output.playout` to true. Sources, publishing and HDMI are separate choices. The default cameras are disabled demonstration fixtures. Edit or add actual cameras in Studio after startup. For local HDMI set `output.hdmi`, the display index and rectangle. For operation without a desktop set `output.headless` to true and disable HDMI and desktop audio. Streamed music and encoded audio remain available.

Keep the Compose internal service names `engine`, port 5250 and `http://studio:8765`. The upstream RTSP base must differ from `rtsp://source-hub:8554`. The latter is the private fan-out service, with no host listener. A saved `shared_camera_inputs` value of false explicitly bypasses fan-out.

Place music in `music/`. Put only the required credentials in `secrets/` as owner-readable files, chmod 600, and refer to their filenames in the station config. A publish URL containing a stream key belongs in the `publish_url` secret file. Provider groups are opt-in. The importer intentionally turns them off.

```sh
python3 tools/stationctl.py check "$HOME/station"
python3 tools/stationctl.py start "$HOME/station"
```

The start command builds both images, validates settings, generates matching native channel clocks, and launches the Compose stack. The first native build is substantial. It uses the checked-in CasparCG patch series and checksum-pinned dependencies. The application image includes checksum-pinned MediaMTX 1.21.2 and its licence.

Studio is at http://127.0.0.1:8765/studio. For another computer, use an SSH tunnel to that address. The controller has operator write protections but no multi-user authentication; do not publish the port to the Internet. AMCP is bound to host loopback. No source-hub ports are published. Use `status`, `logs` or `stop` in place of `start` for routine operations.

For an existing station on a trusted private LAN, set `STATION_HTTP_BIND` to the machine's specific private IPv4 address before `check` or `start`. The helper saves that choice for subsequent launches and the watchdog uses the same address. Loopback remains the default. Wildcard, public and link-local addresses are rejected. This option does not add authentication; use it only where every client on that network is trusted to operate the station.

## What is bounded

Container logs rotate at three 10 MB files per service. The generated native configuration disables duplicate file logging, using CasparCG's supported log-path disabled attribute; its console remains in the rotating Docker log. Camera readers reconnect independently and expose recent decoded-frame health. Confidence pictures use the same health readers. The maintenance service removes only old expendable map tiles. The configured cache budget applies to those tiles, not all station files. Indexed camera and radar histories retain their existing per-history count, age and size limits; a second process does not delete files behind their indexes. It never prunes user music, ads, references, station settings, alert records or paid-API accounting. Low disk space is reported at `/api/storage-health`; protected files are not silently deleted to satisfy a quota. Native runtime caches have their existing individual bounds.

## Recovery and acceptance limits

Compose restarts exited processes. That does not prove recovery from a live-but-hung process. The Compose host wrapper is `tools/station_watchdog.py`. It reuses the tested recovery guard, resolves containers through the candidate project, preserves deliberate stops, and limits recovery to three attempts per hour with a three-minute cooldown. Run it with a separate, credential-free program monitor URL. Without `--recover` it only reports proposed actions. With `--recover`, it restarts only the affected candidate services. It needs host Docker access and FFprobe, never a Docker socket inside a container. Touch `runtime/maintenance` to suspend recovery during planned work; remove that file when finished. The isolated NVIDIA candidate passed source/relay and engine/controller hang drills; see the dated acceptance record.

```sh
python3 tools/station_watchdog.py "$HOME/station" --monitor-url rtmp://your-relay:1935/program --recover
```

Only one watchdog may watch a station directory. A second instance exits without changing recovery history. The process lock is released when the watcher exits. Follow [hardware acceptance](HARDWARE-ACCEPTANCE.md) for the recording and failure checks before migration.

After a manual launch passes, install persistent recovery:

```sh
python3 tools/install_runtime_services.py install "$HOME/station" --monitor-url rtmp://your-relay:1935/program
```

This installs and starts a station-specific user service, with the same recovery limits and maintenance switch. Add `--display` on KDE to keep HDMI awake only while this station's engine runs; that option requires the host Python D-Bus package. It respects deliberate stops and maintenance, and does not change the desktop's permanent power settings. Add `--gpu intel` for that profile. `--no-start` installs services for the next graphical session without starting them now. Use `remove` instead of `install` to stop and remove only this station's services. Desktop installations also need the login launcher below to refresh display/audio bindings. Headless installations use the service setup in [headless operation](HEADLESS.md).

The isolated candidate passed NVIDIA OpenGL, HD30 encoded picture/audio and bounded source/relay/hang recovery checks. Production migration subsequently passed physical HDMI, operator playback and rollback checks, followed by a 24-hour observation with steady sampled program output but intermittent camera delivery. Automatic production desktop-login/reboot recovery passed on 24 October; see the current checklist for recorded and operator-confirmed scope. See [current acceptance](ACCEPTANCE-STATUS.md) for measured scope. Do not run a second GPU stack against the existing engine or publish destination.

For an Intel development machine use `--gpu intel` with HD30 and `libx264`. This mounts `/dev/dri` and uses VAAPI for health decoding. Software output encoding is explicit; QSV encoding is not qualified; the T480s has measured workload limits in the current checklist. The graphics canvas remains UHD before the native HD output scaling. The tested laptop is a limited standby profile; do not infer unrestricted quad or 60 fps performance.

Use `python3 tools/stationctl.py init "$HOME/station-laptop" --gpu intel` to create those Intel defaults without enabling outputs. Follow [laptop acceptance](LAPTOP-ACCEPTANCE.md), starting with the read-only `tools/host_readiness.py` report.

On a machine with NVIDIA plus an Intel or AMD integrated GPU, set `STATION_HEALTH_DEVICE=/dev/dri/renderD128` before `check` or `start`, choosing the actual integrated GPU render node. This mounts only that render device into source-health and leaves the engine on NVIDIA. The controller image includes Mesa and Intel VAAPI drivers. The helper saves the selected device for subsequent launches. Check actual decoder operation and fresh camera frames before accepting this configuration; a device path alone does not prove working hardware acceleration. Omit the setting for software health decoding, or set it to an empty string during the next `check` or `start` to clear it.

For an imported snapshot, `prepare` creates missing runtime folders without replacing station settings. Review the imported disabled provider/output switches before launch. Keep the snapshot and import manifest for rollback; migration does not alter the old installation.

## Desktop sound and startup after login

Set `output.desktop_audio` to true for sound through the logged-in user's default PulseAudio or PipeWire pulse sink. This is independent of encoded programme audio and the HDMI picture switch. The launch helper validates the user-owned socket and adds the audio Compose override. KDE's sound settings can select the HDMI sink and set the application's local listening volume. No anonymous PulseAudio server is enabled. The actual listening sink and end-to-end delay still need a migration-window check. Select the application named Station-Program in KDE; changing that stream does not need to change the desktop default sink.

Once a manual start has passed acceptance, install desktop startup:

```sh
python3 tools/install_autostart.py install "$HOME/station"
```

Add `--gpu intel` to both launch and autostart commands for that profile. Keep the checkout in place. At each desktop login the helper waits up to four minutes for Docker, the GPU and display credentials. It resumes existing images without building or downloading. Only the engine is recreated to refresh display and audio socket bindings; current controller data is preserved. The bounded status file is `runtime/login-start.json`. A `runtime/maintenance` file suppresses login startup and watchdog recovery. Remove it when ready to resume. The normal `stop` command holds services stopped during that session; installed autostart resumes them at the next login.

Remove startup with `python3 tools/install_autostart.py remove "$HOME/station"`. This leaves running services alone. Desktop login is required, so a machine must have a usable desktop session before this mechanism can restore playout after power loss. It does not configure automatic login or replace the host's Docker service. Reboot/login must be qualified for each installation; the production and T480s results are recorded in the current checklist.

On KDE, saved-session restoration can reopen unrelated applications over the HDMI programme window. For a station desktop, select **Start with an empty session** in Desktop Session settings. On Plasma 6 the equivalent command is:

```sh
kwriteconfig6 --file ksmserverrc --group General --key loginMode emptySession
```

This leaves automatic login and explicit autostart entries enabled. It takes effect at the next login; existing application windows remain open until closed. See [KDE session management](https://docs.kde.org/stable_kf6/en/plasma-desktop/kcontrol/kcmsmserver/index.html). The setting and subsequent programme visibility passed the [controlled startup check](POWER-CYCLE-20261026.md).

The desktop entry follows the [freedesktop Exec quoting rules](https://specifications.freedesktop.org/desktop-entry-spec/latest/exec-variables.html). Startup paths and credentials are not passed through a shell. If you use alternate host ports, set `STATION_HTTP_PORT` and `STATION_AMCP_PORT` before the first check/start; they are retained in the station's Compose environment and used by the watchdog.

Display authentication is copied into an owner-readable `display.xauthority` in the station directory. Only the current display cookie is retained, with the Xauthority family adjusted for the container hostname. The original desktop cookie file is unchanged. Keep the generated file private and out of source archives. Login resume replaces it and recreates the engine binding.

After changing station configuration or branding, run `python3 tools/stationctl.py restart "$HOME/station"`. It validates and regenerates native settings, then recreates the candidate services from existing images so every process reads the same configuration. This briefly interrupts that candidate station. Use `start` to rebuild images and apply configuration; `resume` is intended for desktop-login recovery with the same settings.

## Collect a support report

Run `python3 tools/support_bundle.py "$HOME/station" support.zip --runtime`. Add `--gpu intel` for that profile. The report contains selected configuration flags, counts, storage/watchdog measurements and container states. It omits raw logs, endpoint addresses, location, names, credentials, pictures, music and accounting. Its manifest records the report hash. It refuses to replace an existing archive. Review it before sharing; this is a diagnostic summary, not a station backup. Run without `--runtime` if Docker is unavailable.

## Request and host limits

Control request bodies are limited to 2 MiB before JSON parsing. Reference images and notice images are limited to 16 MiB; commercial assets to 100 MiB. Upload, image dimension and video duration/codec limits also apply. For a deliberate private DNS hostname, set `STATION_ALLOWED_HOSTS` to a comma-separated list of exact hostnames when launching Compose. Numeric private addresses, loopback, the container hostname and the internal `studio` name work by default. Do not use a wildcard or expose the service publicly. See [security policy](../SECURITY.md).
