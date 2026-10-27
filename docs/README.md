# Documentation

See the [project overview](../README.md) and [programme and operator screenshots](SCREENSHOTS.md) for an introduction.

## Operate a station

- [Operator guide](STUDIO-GUIDE.md): broadcast desk, scenes, schedules, music, news, alerts and monitoring. The same guide is available at `/guide` on the station.
- [Standby operation](STANDBY.md): independent configuration, publishing routes and failover.
- [Support](../SUPPORT.md): reporting faults and collecting safe diagnostics.

## Install and administer

- [Linux deployment](LINUX-DEPLOYMENT.md): prerequisites, startup, services, recovery and updates.
- [Versioned bundle installation](RELEASE-INSTALLATION.md): verify and load the fixed alpha images without a native build.
- [Headless operation](HEADLESS.md): EGL rendering without a desktop session.
- [Station configuration and migration](STATION-CONFIGURATION.md): settings ownership, credentials and import.
- [Branding](BRANDING.md): identity configuration and asset constraints.
- [Security policy](../SECURITY.md): supported exposure and vulnerability reporting.
- [Dependency maintenance](DEPENDENCY-MAINTENANCE.md): update review, compatibility exceptions and reporting activation.
- [Hardware acceptance procedure](HARDWARE-ACCEPTANCE.md) and [Intel commissioning](LAPTOP-ACCEPTANCE.md): qualify a new installation.

## Data and providers

- [Electricity and outages](POWER-SYSTEM.md): readings, freshness, outage presentation and customer counts.
- [Published electricity reports](POWER-REPORTS.md): PDF extraction, history and approximate chart data.

Regional weather, radar, airport, tides and utility adapters target Newfoundland. Other regions require suitable providers; changing the station location does not change those feeds automatically.

## Build and release

- [Contributing](../CONTRIBUTING.md) and [build inputs](BUILD-INPUTS.md).
- [CI and deployment](CI-CD.md).
- [Licensing](../LICENSING.md), [component notices](../THIRD_PARTY_NOTICES.md) and [source delivery](SOURCE-AND-LICENCES.md).
- [Native dependencies](NATIVE-DEPENDENCIES.md) and [binary distribution checklist](BINARY-RELEASE-CHECKLIST.md).
- [Current release checklist](RELEASE-CHECKLIST.md): the authoritative list of remaining requirements and deferred features.
- [Release validation](RELEASE-VALIDATION.md): extended observation, physical power-off/on recovery and clean GPU installation.

## Test records

The [acceptance register](ACCEPTANCE-STATUS.md) links dated measurements, failure investigations and installation evidence. A test record applies to its stated revision, hardware and workload. Statements about unfinished work in a historical record describe the test date; use the current release checklist for present status.
