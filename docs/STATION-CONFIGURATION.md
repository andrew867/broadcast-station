# Station settings and migration

The release candidate reads a versioned `station.json` when `STATION_CONFIG`
points to it. The example in `examples/station.json` starts an offline preview.
It does not inherit the commissioned station's addresses, keys or permissions.

## Settings ownership

`station.json` holds deployment settings: location/timezone, camera hub and
ADS-B endpoints, output profile, engine address, optional publishing/HDMI,
provider enablement, storage limits and secret-file references. Existing
operator settings remain under the configured data directory. Rundowns,
music, camera calibration, credits, map appearance and advertising retain
their existing schemas and stable scene IDs. Restarting does not install a
preset over an existing operator file.

Paths are relative to the directory containing station.json unless absolute.
`STATION_CONFIG` selects the file. Explicit `SKYCAM_DATA`, `SKYCAM_MUSIC`,
`SKYCAM_FEED`, `SKYCAM_METADATA_BASE`, `SKYCAM_PLAYOUT` and `STATION_BRAND_FILE`
environment values override their file equivalents. Other station fields come
from the file. `STATION_OFFLINE` defaults to 1 independently of imported state;
setting it to 0 is a separate deployment action. Do not use that switch during
a migration rehearsal.

Unknown versions/fields, invalid timezones, embedded URL credentials and
invalid secret filenames fail validation. Validation errors do not echo
submitted values. Credentials belong in files under secrets_directory with
owner-only permissions on Linux. Normal exports contain role/filename
references, not key contents. Offline previews do not read those files.
Legacy AIS/Finnhub environment keys are supported as an explicit fallback;
new deployments should use the file references.

## Supported configuration scope

Location and timezone drive solar/lunar calculations and map centres.
The native output profiles are 720p30, 720p60, 1080p30, 1080i59.94, 2160p30 and 2160p60. See [the current checklist](RELEASE-CHECKLIST.md) for workload-specific results. Profile generation
is not hardware qualification. The current image pipeline still prepares a
3840 by 2160 graphics canvas before native scaling; the Intel workload and
limits are recorded in the current checklist.

Camera and ADS-B endpoints are configurable. Existing weather, radar, airport,
tides and utility adapters are a Newfoundland regional preset, not worldwide
providers. Enable that preset explicitly before enabling those adapters.
Other regions can use cameras and aircraft with regional providers off.
Further provider adapters must declare their own data rights and freshness
rules. Storage limits are part of the configuration contract; enforcement is
part of the full-stack storage worker, not an implication of this JSON file.

Set `output.headless` to true for EGL rendering without a desktop. It cannot be combined with `output.hdmi` or `output.desktop_audio`. Encoded audio remains available. See [headless operation](HEADLESS.md) for startup and hardware requirements. The machine-readable contract is [station.schema.json](../examples/station.schema.json).

## Information providers and director access

The `providers` object enables adapters independently. Newfoundland weather, travel, marine, tides, outages, power, radar and space weather require `regional_preset` to be `newfoundland`. Preview configurations leave every provider disabled.

Provider credentials are file references under `secrets_directory`:

| Secret role | Used by | Requirement |
|---|---|---|
| `nl511` | NL Travel Now | Newfoundland and Labrador 511 developer key |
| `aisstream` | Harbour and vessel maps | AISStream API key |
| `finnhub` | Optional market quotes | Finnhub API key |
| `aeroapi` | Optional paid flight enrichment | FlightAware AeroAPI key, with local spending policy |
| `publish_url` | Encoded output | Destination URL when it is not present in station.json |
| `director_token` | Private Director page | Random token of at least 20 characters |

Create the director token without writing it to terminal history:

```sh
umask 077
python -c 'import secrets; print(secrets.token_urlsafe(24))' > /srv/station/secrets/director.key
chmod 600 /srv/station/secrets/director.key
```

Reference the filename as `"director_token": "director.key"`, restart the controller, then open `/director` from a private-network client. The controller also checks the client address. The Director page is unsupported on a public interface and has no multi-user account model.

Travel performs five documented NL511 requests every five minutes. Space weather uses the official Natural Resources Canada short-range table and needs no key. Each adapter keeps its own timestamp and unavailable state; enabling an adapter does not make its upstream data reliable.

## Validate and generate the engine configuration

Run from the repository root:

```sh
python tools/station_config.py /path/to/station.json
python tools/station_config.py /path/to/station.json --engine-output /path/to/new-casparcg.config
```

The generator refuses an existing output file. Program and scene-bank timing
match the selected format; source channels retain their resolution with the
same frame clock. Full-stack packaging must mount this generated file into
the engine. A settings edit alone does not reconfigure a running CasparCG.

## Import a legacy settings snapshot

Use a verified settings archive from the legacy backup tool, not a running
data directory. Choose a destination that does not exist:

```sh
python tools/import_station.py settings.tar.gz /srv/new-station --dry-run
python tools/import_station.py settings.tar.gz /srv/new-station \
  --deployment /path/to/deployment.json \
  --references /path/to/legacy/samples \
  --aeroapi-state /path/to/copied-accounting
```

The optional deployment file supplies location, endpoint and secret references.
No real keys belong in it. The optional references directory supplies the
catalogue's original calibration pictures. The optional accounting directory
contains policy.json and usage.sqlite; SQLite backup preserves a consistent
ledger and verifies its integrity. Reconcile any newer spending before use.

The importer verifies every archive member against its manifest, rejects path
traversal, links and duplicate files, and builds a sibling staging directory
before renaming it into place. It never replaces an existing destination.
Operator JSON/media/history are copied byte for byte. Runtime observations,
provider caches and recovery history are excluded. The report lists those
exclusions, missing reference pictures, required secret roles and the explicit
offline safety overrides. Unknown operator JSON is retained, not silently
discarded. The original snapshot and source station are untouched.

For an offline rehearsal:

```sh
STATION_CONFIG=/srv/new-station/station.json STATION_OFFLINE=1 \
  python -m uvicorn skycam.app:app --host 127.0.0.1 --port 8766
```

Use a separate port and data directory. Check the camera references, rundown,
music choices, provider settings and import report. Missing operator music,
private trust material or required provider permission remains an explicit
cutover gate. Never enable a second controller against the live engine.

## Automatic camera skipping

`GET /api/camera-rotation` reports the policy and camera eligibility.
`PUT /api/camera-rotation` accepts version 1, skip_unavailable,
unavailable_after_s and recovery_after_s through the normal operator edit
protection. Defaults are 180 seconds of lost pictures and 10 seconds of stable
recovery. Disabled cameras are always excluded from automatic full-screen
cues, including saved playlists. Quads and manual takes remain available.
The independent decoder continues reconnecting enabled sources while their
automatic cues are skipped. A connected socket alone is never readiness.

The optional `location.clock_label` overrides the short on-air clock label. With no override, the label is derived from the configured timezone. Ticker time and music quiet hours use that timezone. `output.desktop_audio` enables local listening independently of encoded programme sound; see the Linux deployment guide. Camera upstream and shared bases require RTSP because health decoding uses RTSP/TCP; the separate RTMP base accepts RTMP or RTMPS.
