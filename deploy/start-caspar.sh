#!/usr/bin/env bash
echo "Legacy reference script: portable launch is not implemented. Do not run this candidate on production." >&2
exit 2
set -euo pipefail
cd /srv/station
nvidia-smi >/dev/null || { echo 'NVIDIA driver mismatch: load the matching driver before starting CasparCG.' >&2; exit 1; }
display_auth=$(systemctl --user show-environment | sed -n 's/^XAUTHORITY=//p')
test -r "$display_auth"
mkdir -p logs media templates data deploy /run/station/skycam-runtime
cp skycam/deploy/casparcg.config casparcg.config
if docker ps -a --format '{{.Names}}' | grep -qx skycam-caspar; then
  echo 'skycam-caspar already exists. Inspect its logs before recreating it.' >&2
  exit 1
fi
gcc -shared -fPIC -O2 -Wall -Wextra skycam/deploy/cef-mallinfo-compat.c -o deploy/cef-mallinfo-compat.so
gcc -shared -fPIC -O2 -Wall -Wextra skycam/deploy/nvdec-prefer.c -ldl -o deploy/nvdec-prefer.so
gcc -shared -fPIC -O3 -Wall -Wextra skycam/deploy/uc-image-copy.c -ldl -o deploy/uc-image-copy.so
docker run -d --restart unless-stopped --name skycam-caspar --log-opt max-size=20m --log-opt max-file=3 --network host --device nvidia.com/gpu=all \
  --user "$(id -u):$(id -g)" --shm-size=4g \
  -e MALLOC_ARENA_MAX=4 -e MALLOC_TRIM_THRESHOLD_=262144 \
  -e PULSE_PROP=application.name=SkyCam-CasparCG -e PULSE_SERVER=unix:/tmp/skycam-pulse -e ALSOFT_DRIVERS=pulse \
  -v /run/station/pulse/native:/tmp/skycam-pulse \
  -v /run/dbus/system_bus_socket:/run/dbus/system_bus_socket \
  -e LD_PRELOAD=/workspace/deploy/cef-mallinfo-compat.so:/workspace/deploy/nvdec-prefer.so:/workspace/deploy/uc-image-copy.so -e DISPLAY=:0 -e XAUTHORITY=/tmp/skycam.xauthority \
  -v /run/station/skycam-runtime:/workspace/runtime \
  -v /tmp/.X11-unix:/tmp/.X11-unix:ro -v "$display_auth:/tmp/skycam.xauthority:ro" \
  -v /srv/station:/workspace \
  "${SKYCAM_CASPAR_IMAGE:-skycam-caspar:2.5.1-idle-cache}"
