#!/usr/bin/env bash
echo "Legacy reference script: portable launch is not implemented. Do not run this candidate on production." >&2
exit 2
set -euo pipefail
cd /srv/station
runtime=/run/user/$(id -u)/skycam-runtime
mkdir -p "$runtime"
test -w "$runtime" || { echo "Runtime folder must be writable by $(id -un): $runtime" >&2; exit 1; }
docker image inspect skycam-web:local >/dev/null
private_env=()
trust_mount=()
if test -f "$HOME/.config/skycam/issuer-trust/policy.json"; then
 trust_mount=(-v "$HOME/.config/skycam/issuer-trust:/issuer-trust:ro" -e SKYCAM_ISSUER_TRUST=/issuer-trust/policy.json)
fi
if test -f "$HOME/.config/skycam/alert-resources.env"; then
 private_env+=(--env-file "$HOME/.config/skycam/alert-resources.env")
fi
if test -f "$HOME/.config/skycam/aisstream.env"; then
 private_env+=(--env-file "$HOME/.config/skycam/aisstream.env")
fi
if test -f "$HOME/.config/skycam/finnhub.env"; then
 private_env+=(--env-file "$HOME/.config/skycam/finnhub.env")
fi
previous=""
if docker inspect skycam-web >/dev/null 2>&1; then
 previous="skycam-web-backup-$(date -u +%Y%m%dT%H%M%SZ)"
 docker stop skycam-web >/dev/null
 docker rename skycam-web "$previous"
 docker update --restart=no "$previous" >/dev/null
fi
rollback() {
 if test -n "$previous"; then
  docker rm -f skycam-web >/dev/null 2>&1 || true
  docker rename "$previous" skycam-web
  docker update --restart=unless-stopped skycam-web >/dev/null
  docker start skycam-web >/dev/null
 fi
}
if ! docker run -d --name skycam-web --restart unless-stopped --log-opt max-size=10m --log-opt max-file=3 --network host "${private_env[@]}" "${trust_mount[@]}" \
 --user "$(id -u):$(id -g)" -e SKYCAM_PLAYOUT=1 -e SKYCAM_MUSIC=/music \
 -e SKYCAM_LISTEN_ADDRESSES="${SKYCAM_LISTEN_ADDRESSES:-127.0.0.1,192.0.2.20}" \
 -v "$PWD/skycam:/app:ro" -v "$PWD/data-web:/app/data" -v "$runtime:/app/data/runtime" \
 -v "$PWD/media/music:/music:ro" skycam-web:local python -m skycam.serve; then rollback;exit 1;fi
for attempt in $(seq 1 30); do
 if curl -fsS --max-time 2 http://127.0.0.1:8765/api/health >/dev/null; then
  echo "Studio ready. Previous container retained: ${previous:-none}";exit 0
 fi
 sleep 1
done
echo 'Studio did not start; restoring previous container.' >&2
rollback
exit 1
