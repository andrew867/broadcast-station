# Information screens and automatic programming

The station provides full-screen information scenes alongside cameras, maps and quad views. Every provider-backed scene carries a current, cached or unavailable state. Automatic playout can skip a scene whose required data is unavailable. A manual take remains available and shows the scene's unavailable presentation instead of refusing the operator action.

## Scene catalogue

| Scene | Purpose | Primary inputs |
|---|---|---|
| Weather Timeline | Current observation and the next three forecast periods | Environment and Climate Change Canada city page data |
| NL Travel Now | Exceptional road, ferry, wind and advisory items | Newfoundland and Labrador 511 developer API |
| Harbour Watch | Received vessel positions, predicted tides and coastal forecast | AISStream, CHS IWLS and ECCC marine data |
| Tonight's Sky | Sunset, Moon times, viewing conditions and geomagnetic activity | Local astronomical calculations, ECCC weather and optional Natural Resources Canada forecast |
| Morning Briefing | Current weather, forecast, travel and power summary | The current provider states at playout time |
| Evening Briefing | Tonight and tomorrow summary with travel and power context | The current provider states at playout time |
| Community Calendar | Approved notices and events within the next 21 days | Operator-managed notice board |
| Last Hour | Four received pictures sampled from the selected camera's bounded one-hour history | Independent decoded source pictures |

The Last Hour screen does not interpolate video or invent missing periods. Its footer identifies the received range and states that gaps reflect source availability.

Radar-history frames store a bounded aircraft snapshot when each changed radar file is received. Replay uses those saved reports, not current aircraft. This is still not a synchronized reconstruction because the radar observation time is the time printed by the provider. The screen identifies aircraft timing as radar-file receipt time.

## Automatic conditions

Each rundown cue has one of four automatic policies:

- `auto` applies the source policy for that scene.
- `always` presents the scene even when its source is unavailable.
- `when-current` requires current usable data.
- `when-exception` requires an active exception, such as a travel disruption or current outage.

These policies apply to automatic rotation and scheduled blocks. They do not prevent a manual take. Camera readiness remains separate and continues to use recent decoded pictures rather than connection state. Automatic single-camera cues use the latest independent confidence picture: a fresh picture is current, a picture up to three minutes old is held as cached, and an older or disabled source is skipped. Quad scenes remain eligible while at least one enabled member has a current or held picture; unavailable members keep their loading panels. Manual takes remain available.

Program clock rules can be limited to selected local hours and can require current power outages, weather alerts, travel exceptions or degraded cameras. Coincident rules use priority. A missed slot is recorded and is not replayed late.

The installed default clock uses short and extended weather blocks, morning and evening briefings, travel exceptions, community calendar pages, local information and conditional outage updates. Review the generated rules before applying the format to a commissioned station.

## NL511 configuration

The travel adapter is disabled by default and requires the Newfoundland and Labrador 511 regional preset and a developer key. Store the key in an owner-readable file, reference it with the `nl511` secret role and enable the `travel` provider. The adapter requests five documented endpoints once every five minutes, which stays below the published limit of ten calls per 60 seconds.

If the key is absent, rejected or stale, the scene reports that travel data is unavailable. It never substitutes a general web search or an inferred road condition.

## Space weather

The optional `spaceweather` provider reads the official Natural Resources Canada short-range geomagnetic table every 15 minutes. A failed or changed upstream table leaves the geomagnetic portion unavailable. The astronomical part of Tonight's Sky remains available because it is calculated locally from the configured location and time.

## Community calendar

Calendar entries come from approved notice-board records. The screen includes active and future approved entries within 21 days, ordered by start time. Expired, unapproved or structurally invalid entries are excluded. Adding an item does not approve it.

## Private director remote

`/director` is a compact phone and tablet control surface for the private operator network. It shows programme state, rotation state, scene buttons and non-current data sources. It can start, advance or hold rotation and take the safe map.

The remote requires a `director_token` secret of at least 20 characters and rejects clients outside private or loopback address space. The token is kept in browser session storage and is sent with each director request. The remote has no TLS termination or multi-user accounts. Keep it on a trusted private LAN or reach it through a protected tunnel. Internet-facing access is unsupported.

## Data limits

Provider availability is an operating condition, not a software guarantee. NL511 requires an account key. AIS reception is incomplete and must not be used for navigation. Tide data is predicted rather than observed. The alert receiver still requires independently authenticated issuer material and local acceptance before it can be relied on for public warning. These limits remain visible even when the graphical scene can be rendered.
