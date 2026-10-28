# Operator guide

Use this guide for everyday operation. Installation, provider credentials and service management are covered in the Linux deployment manual.

[The broadcast desk](#desk) | [Scenes and rundowns](#rundown) | [Scheduled blocks](#clock) | [Graphics and maps](#graphics) | [Music and local listening](#music) | [News crawl](#news) | [Weather alerts and power outages](#alerts) | [Information slides](#information) | [Confidence and fault diagnosis](#monitoring) | [Startup, recovery and updates](#recovery)

<a id="desk"></a>

## The broadcast desk

The desk has seven pages: Live, Rundown, Graphics, Music, News, System and Setup. Moving between them preserves draft edits and does not change the programme. The status strip remains visible on every page.

Use Live to select and preview a scene, then Take to put it on air. A manual take pauses automatic rotation. Loading a saved rundown only copies it into the editor; use its apply and playback controls to change the running programme.

The private Director page provides compact scene takes and rotation controls for a phone or tablet. It requires a separate director key and a private-network client; it is not an Internet-facing control service.

The orange unapplied-changes notice names pages with unsaved edits. Apply wanted changes before reloading the browser or updating the server. A browser draft is not a saved station setting.

<a id="rundown"></a>

## Scenes and rundowns

Use Rundown to arrange scenes, set their durations and save named lists. Check the preview and durations before starting a list. Keep a saved copy of a working schedule before changing it.

Camera acquisition runs independently of scene selection. Disabled cameras are excluded from automatic full-screen cues. By default, an enabled camera is skipped after 180 seconds without a decoded picture and returns after 10 seconds of stable recovery. Manual camera selections and quad scenes remain available with fallback graphics.

Each cue can use the scene policy, always play, require current data or require an exceptional condition. These choices affect automatic rotation only. Manual takes remain available and show the selected scene with an unavailable message when its provider is down.

A preview is not proof that the encoded programme reached a viewer. Confirm transitions and audio on HDMI or an independent stream receiver.

<a id="clock"></a>

## Scheduled blocks

The clock combines a repeating background rundown with scheduled blocks. Use short blocks for regular forecasts and longer blocks for detailed weather, alerts or local information. Times follow the configured station timezone.

Each rule has an interval, an offset within that interval and a priority. Where rules coincide, the higher-priority rule takes precedence. An active block finishes before another begins; missed slots are not queued for later playback. A manual hold takes priority over automatic scheduling.

The default format schedules short and extended weather, morning and evening briefings, travel exceptions, community events, local information and conditional outage updates. Briefings are restricted to configured local hours. Applying the default format replaces the running loop and clock, saves a backup and starts automatic rotation.

Review the saved clock rules and block durations on the scheduling page before enabling the clock. Keep enough time between slots for the complete block and its transitions. The editor displays the installed defaults; saved operator schedules are not replaced by a software update.

<a id="graphics"></a>

## Graphics and maps

Use Graphics to change the lower third, ticker speed, map theme and optional information bugs. Apply settings to save and send the changes. Day, Night and Auto map themes are available; Auto follows the configured location and solar times.

Camera credits can be enabled and edited per source. Quad scenes place credits in their description bars. Reference stills are for calibration; they do not replace live video. Confirm image dimensions and surveyed landmarks before relying on aircraft alignment.

Older aircraft positions use a faded icon without changing the callsign label. Vessel identity messages do not establish a current location; only valid position reports can place a vessel on the map. Harbour clusters on the island map reduce label crowding without removing individual positions.

Radar images and aircraft reports have independent timestamps. Current aircraft over a radar image are not a historical reconstruction. Radar-history playback hides current aircraft rather than placing them on an earlier weather image.

<a id="music"></a>

## Music and local listening

Use Music to select disk playback or generated music, choose tracks, skip forward or back, set shuffle and adjust the programme level. Save settings with the page controls. Volume changes do not require restarting the current track.

Store disk tracks in the station music directory. Finish copying a file before making it available for playback. Generated music changes at musical boundaries; a saved change may not be audible immediately.

Desktop listening volume and encoded programme volume are separate. KDE or PipeWire controls affect the local listening route; use the desk for broadcast music level. Check the outgoing stream before concluding that a muted local monitor means the programme is silent. Alert speech can temporarily reduce the music level.

<a id="news"></a>

## News crawl

Use News to select sources and review available headlines. Source selections and freshness determine what enters the crawl. Headlines retain their source attribution; the station does not rewrite a negative story as positive news.

Most sources retain items for 36 hours. The good-news group allows 72 hours and the positive-news group allows seven days. French-language items are excluded. A source failure or an empty eligible list does not stop the programme.

Choose a mix of local reporting and positive-news sources for a balanced crawl. Ticker speed is controlled in Graphics. Review the actual crawl after changing sources or speed.

<a id="alerts"></a>

## Weather alerts and power outages

Eligible English-language weather alerts appear on the alert pages. Immediate alert presentation can replace the full bottom information area, including the news crawl and clock, while the main programme continues. Between full presentations, an abbreviated message and repeat countdown may be shown according to station policy.

Alert speech temporarily reduces music. Expiry and authenticated cancellation determine removal of official alerts. A successful connection alone does not establish trusted issuer identity. Independently authenticated issuer certificates and local commissioning are required before relying on the receiver; this software is not a certified public-warning receiver.

Utility outages are separate from official emergency alerts. Unplanned outages can use the configured bulletin policy; official alerts retain priority. Scheduled maintenance appears on outage slides only and does not trigger speech, music reduction or a lower-third interruption.

A zero customer count hides only the count, not the outage. A missing count is not evidence that no customers are affected. Estimated restoration times are estimates; an elapsed estimate does not establish that an outage has ended.

<a id="information"></a>

## Information slides

Weather, electricity, tides, airport and utility adapters use the Newfoundland regional preset. Provider timestamps and unavailable labels distinguish current observations from older or missing data. A missing reading is never displayed as zero.

Weather Timeline, NL Travel Now, Harbour Watch, Tonight's Sky, Morning Briefing, Evening Briefing, Community Calendar and Last Hour are available as normal rundown scenes. Scene cards show current, cached or unavailable data before an operator schedules them.

Sun and Moon positions are calculated for the configured location and time. Tide values are predictions relative to chart datum, not observed water levels. Market arrows describe the displayed comparison; quote timestamps, session labels and delayed or last-known states remain part of the reading.

Upload advertisements or sponsor artwork through the relevant setup page, then explicitly enable and schedule them. Uploading an asset alone does not put it on air. Check placement, duration and content rights before use.

<a id="monitoring"></a>

## Confidence and fault diagnosis

Use System and Confidence for source thumbnails, audio meters, output health and recovery history. Confidence pictures are sampled images, not continuous programme monitors. Some independently rendered layers may not appear in a prepared-scene still.

An open camera connection is not proof of usable video. Check recent decoded pictures separately from the programme frame counter. A camera reconnecting while the programme advances is a source problem; it does not by itself mean the renderer has failed.

Compare the original encoded programme with the downstream receiver when investigating freezes or audio gaps. Advancing packet timestamps can contain repeated pictures. Audio meters report signal level before downstream encoding, not perceived loudness or successful receiver playback.

Retain the affected scene, time and timezone, output format, workload and recovery history when reporting a problem. Use the allowlisted support report instead of sharing raw settings, keys or logs.

<a id="recovery"></a>

## Startup, recovery and updates

Use the Linux installation manual for stationctl commands, persistent services and the maintenance switch. Status and logs inspect a station; stop deliberately stops it. Restart reapplies configuration using existing images and briefly interrupts output. Start builds images before launch.

Desktop output needs a working graphical session and refreshed display credentials after login. Headless output uses EGL without HDMI or desktop audio. Encoded music remains available in headless mode. Qualify recovery on the actual hardware and listening route.

Keep known working images and a verified settings backup before upgrading. Store credentials separately from source archives. Do not run two controllers against one engine or publish two stations to the same destination.

## Related manuals

[Linux deployment](LINUX-DEPLOYMENT.md), [headless operation](HEADLESS.md), [station configuration](STATION-CONFIGURATION.md), [standby operation](STANDBY.md), [support](../SUPPORT.md) and [release checklist](RELEASE-CHECKLIST.md).
