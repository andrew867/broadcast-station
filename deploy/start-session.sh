#!/usr/bin/env bash
echo "Legacy reference script: portable launch is not implemented. Do not run this candidate on production." >&2
exit 2
set -euo pipefail
cd /srv/station
for attempt in $(seq 1 60); do
 display_auth=$(systemctl --user show-environment | sed -n 's/^XAUTHORITY=//p')
 if test -n "$display_auth" && test -r "$display_auth" && test -S /run/user/$(id -u)/pulse/native && nvidia-smi >/dev/null 2>&1 && docker info >/dev/null 2>&1;then break;fi
 if test "$attempt" = 60;then echo 'Desktop, PipeWire, Docker or NVIDIA is not ready.' >&2;exit 1;fi
 sleep 1
done
mkdir -p /run/user/$(id -u)/skycam-runtime
if test "${1:-}" = --check;then echo 'Desktop, audio, GPU, Docker and runtime folder are ready.';exit 0;fi
if docker inspect skycam-web >/dev/null 2>&1;then docker start skycam-web >/dev/null;else bash skycam/deploy/start-web.sh;fi
current_auth=$(docker inspect skycam-caspar --format '{{range .Mounts}}{{if eq .Destination "/tmp/skycam.xauthority"}}{{.Source}}{{end}}{{end}}' 2>/dev/null || true)
running=$(docker inspect skycam-caspar --format '{{.State.Running}}' 2>/dev/null || true)
if test "$current_auth" != "$display_auth" || test "$running" != true;then
 bash skycam/deploy/skycamctl recreate-server
fi
# These units can be ordered after this oneshot. Queue them without waiting
# for their completion, otherwise startup waits on itself until timeout.
systemctl --user --no-block start skycam-sources skycam-display skycam-watchdog
echo 'SkyCam desktop services are ready. Check program output before starting rotation.'
