# Broadcast desk browser acceptance, 21 October 2026

> Historical test record. For current limits and remaining work, use the [release checklist](RELEASE-CHECKLIST.md).

The candidate was exercised at 1366x900, 1024x768 and 768x900. Graphics, rundown duration and music drafts survived page changes. Applying graphics and music saved to an isolated disposable data directory. Internal navigation sent no modifying requests. Scene search, keyboard navigation and unload protection worked. One preview frame remained mounted throughout. Screenshots of Live, Graphics, Rundown and System were reviewed. No browser script errors were recorded in those checks.

These checks used outbound-blocked data and no engine connection. They establish desk behavior, not production frame rate, native output or hardware qualification.

A later fault check blocked the controller status request, verified the visible connection-lost message, then restored the request and observed recovery without another preview frame. A blocked initial scene-list request also recovered through the normal status poll. Deliberately aborted requests generate expected browser network errors; they are not counted as script exceptions.
