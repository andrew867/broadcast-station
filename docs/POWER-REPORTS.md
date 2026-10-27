# PUB electricity report archive

The Electricity page combines live Hydro readings with a separate archive of published Island Supply and Demand reports. The PDF history is not a backfill of Muskrat Falls or Churchill Falls generation.

## What is collected

The importer discovers links from the PUB report index and recent monthly pages. Every six hours it checks for new material. Initial backfill covers the past 90 days, in batches of 16 with a 15-minute pause while more documents are pending. Existing documents are revisited at most once per day for revisions. Requests are sequential and require no account or copied cookies.

Exact printed fields include daily island peak demand and its local time, exports at that peak, daily LIL net-import energy, six outlook figures and seven daily forecasts with adjusted values. MW and MWh remain distinct. A dash in an outlook field means unavailable, not zero. Parenthesised net imports remain negative. Forecasts are stored by both issue/report date and target date, so a newer forecast never overwrites what an older report predicted.

Some weekend reports are filed on Monday. The filename/report day, printed filing date and actual observation day are stored separately and checked against the forecast dates. Reports outside the accepted relationship are rejected. Times are Newfoundland local wall times; nominal chart minutes are not converted into fabricated UTC telemetry on daylight-saving days.

## Reading the graphs

The supported PDF family contains four coloured vector paths. The importer reads the original path coordinates, calibrates their vertical scale against printed axis labels and checks the demand curve against the printed daily peak and peak time. It accepts only the verified 289-point, uniformly spaced template, with recognised legends and colours. Values are rounded to whole MW and labelled approximate. This is graph digitisation, not original SCADA data, and no claim of exact five-minute measurements is made.

Changed layouts, scanned graphs, missing paths or failed cross-checks leave the graph unavailable while valid printed tables remain usable. No OCR guess enters an on-air graphic. Gaps in daily history are left visible. The operator page lists document and chart rejections separately.

## On-air scenes

- **Electricity / demand and generation** (`power-supply`): the existing live figures and locally collected 24-hour history.
- **Electricity / daily peak history** (`power-history`): recent daily peaks, latest peak, exports at that peak and daily LIL energy.
- **Electricity / daily report and outlook** (`power-report`): latest accepted report's approximate daily curves and its dated forecast table.

The reusable **Electricity update** block contains all three scenes, lasting 90 seconds before transitions. It is available to add to a clock or rundown. Installing this feature does not replace the operator's running camera loop or schedule a new recurring interruption.

## Storage, API and analysis

All data is in `history/power.sqlite3` beneath the configured data directory, already included in the consistent settings backup. Existing `readings` records remain untouched. New tables:

| Table | Contents |
|---|---|
| `pub_reports` | Current accepted version per report day, source URL, SHA-256, parser version and parsed JSON |
| `pub_revisions` | Original PDF bytes and parsed payload for every distinct accepted content hash |
| `pub_values` | Normalised dated MW/MWh fields, kind, metric, report version and target/observation day |
| `pub_curves` | Approximate graph points by report, series and nominal local minute |
| `pub_attempts` | Last check and rejection reason per source document |

`GET /api/power/reports` returns history, latest report and import status. Add `?report_date=2026-10-16` to inspect a retained report, including its forecast and graph arrays. A missing requested date returns `latest: null`. The default view retains up to 370 recent reports in memory; older accepted data remains in SQLite. The archive pauses new storage at a 250 MB original-PDF budget and reports an error for operator review rather than deleting provenance silently.

Example read-only analysis against a copy of the database:

```sql
SELECT day, value AS peak_mw, report_date
FROM pub_values WHERE metric = 'daily-peak' ORDER BY day;
SELECT report_date, day AS forecast_for, value AS forecast_mw
FROM pub_values WHERE metric = 'forecast' ORDER BY report_date, day;
SELECT report_date, minute, mw FROM pub_curves
WHERE series = 'island-demand' ORDER BY report_date, minute;
```

PDF downloads are bounded at 4 MB. The parser runs in a separate low-priority process with a 30-second timeout; Linux adds a 20-second CPU and 768 MB address-space limit. Import errors preserve prior accepted data and never trigger a video-engine restart. Cancellation terminates the parser child.

## Initial acceptance, 21 October 2026

The source listed 86 reports within the initial window, covering actual days July 22 through October 15. All 86 supplied validated table values, totalling 1,978 dated fields. Sixty-five supplied supported curves, totalling 75,140 approximate points. Twenty-one graphs used an unsupported vector structure and remain unavailable. Latest listed report: October 16, not a claim that the utility issued no later report elsewhere. Source PDF pages and regenerated graphics were visually compared. No archived PDF or production database belongs in the public release candidate.

Sources: http://www.pub.nf.ca/applications/IslandInterconnectedSystem/DemandStatusReports.php and its linked monthly reports. Fetching these public files does not establish any additional redistribution licence; retain provider attribution and review provider terms before a public dataset release.

Deployment checks: 474 passing Linux tests, 482 passing release-candidate Windows tests, browser previews reviewed without console errors, and a verified database backup retaining live readings plus all 86 reports. The native engine was not restarted.
