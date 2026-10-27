# Electricity and utility outage coverage

The optional Newfoundland regional providers supply electricity readings and utility outage notices. Offline preview disables collection and operator writes.

Open `/power` from the Broadcast desk for electricity readings and the rendered chart preview. The scene is **Electricity / demand and generation** (`power-supply`). The default Local information block uses a 25-second electricity slide in place of the generic station-information card, keeping its total duration below the next weather slot including transition allowance.

## Readings and history

The source is NL Hydro's public Supply and Demand page: https://nlhydro.com/about-us/our-electricity-system/supply-and-demand/ . The adapter identifies each named figure and its own published timestamp. Island demand, Muskrat Falls generation and Churchill Falls generation are separate measures; they must not be added together or presented as a system-wide surplus/deficit. Island demand excludes Labrador demand and export commitments.

The station checks every five minutes and records the published observation time, not a fabricated sample time. The charts cover 24 hours, initially with only the readings collected since activation. Duplicate timestamps do not create extra points; a revised value replaces that observation. More than twenty minutes between observations leaves a visible gap. Stale or failed readings retain their last value with a last-reported label; missing values are not zero.

History lives in `history/power.sqlite3` beneath the configured data directory, with ninety-day retention. Writes occur only during polling, not during frame rendering. The normal settings backup now uses SQLite's snapshot API and integrity check to include this history safely. These are locally collected public observations, not an official historical dataset.

The power page timestamps have no explicit zone. The adapter interprets them as America/St_Johns, consistent with the island's displayed time. Ambiguous daylight-saving timestamps are rejected rather than guessed. Provider changes to labels, units, dates or plausible ranges produce an unavailable status.

## Outage policy

The outage scene and `/outages` combine four independently monitored feeds: Newfoundland Power current/planned and NL Hydro current/planned. A failed feed retains labelled last-known rows without allowing them to trigger announcements. The other utility can continue updating. Current and upcoming planned work within seven days is included in slide rotation. Elapsed planned windows are removed; elapsed unplanned restoration estimates do not prove power was restored.

Scheduled maintenance is **slide only**. It never triggers bulletin speech, music ducking, countdown summaries or the lower-third replacement. This applies even when Newfoundland Power includes Scheduled Maintenance in its current-outage layer. Matching planned/current notices for the same provider and location, with start/end times within one hour, are merged for display. Distinct utilities and differently timed jobs are not merged.

Unplanned incidents retain the existing configurable bulletin policy. Official emergency alerts retain priority. Utility notices are not presented as CAP emergency alerts, and repeat timings remain station policy rather than a compliance claim.

Hydro feeds:
- https://my.nlhydro.com/outage/json/GetOutageSummery_C.json
- https://my.nlhydro.com/outage/json/GetOutageSummery_P.json

No copied cookies or account access are needed. Hydro notice times without UTC offsets are preserved as local wall times, using the station's Newfoundland timezone for scheduling; timezone-less Labrador notices have not been independently commissioned. Hydro customer counts are displayed even though its own list UI omits that field. Zero counts are omitted from graphics, bulletin speech and the operator page; a missing count is labelled not provided. A zero count does not suppress an outage or prove that nobody is affected. Newfoundland Power's published map still has its 25-customer coverage limit. Neither feed proves complete coverage of every customer outage.

The map widens when a listed incident is in Labrador. A utility point is approximate; a listed community group is not an outage polygon. Full notice text remains available on the operator page and utility websites.

## Operation and limits

History survives controller restarts. Data fetches and map preparation run away from scene switching; the broadcast uses cached native PNG cards and no extra continuous decoder. Reload the page to refresh the studio, or use the normal controller restart procedure after code updates. CasparCG and the relay do not require a restart for this feature.

A real planned Hydro notice and all four live feeds were tested. The Hydro current feed was empty during development, so an actual Hydro unplanned incident is covered by schema/fixture tests, not a claimed live incident acceptance.

## Published report history

The Electricity page includes a separate PUB report archive with daily peaks, forecasts and validated approximate vector curves. Read [published report history](POWER-REPORTS.md) for date semantics, retained revisions, storage and on-air scenes. These reports do not backfill the live Muskrat Falls or Churchill Falls series.
