# Configurable identity

`examples/branding.json` is a neutral example, not a chosen product name. Copy it into operator configuration and set `STATION_BRAND_FILE` to its path. Validation rejects unknown fields, control characters, oversized text, invalid colours and unsafe logo names. A bad file fails visibly rather than silently replacing the operator's identity.

Product name belongs to the studio and browser title. Station name/short name belong to the on-air identity. Tagline and website may be blank. The accent is an RGB hex colour. Optional `logo_asset` names a PNG/JPEG beneath `branding-assets/` alongside the config file; no network logo URL or executable SVG is accepted. The maximum is 2 MB and 4096 pixels per dimension. Leave it empty for the generic mark.

Text is escaped for server HTML and set as text in the browser. Native graphics and ticker read the same configuration. Saved headlines, credits and programme text retain their own values. Changing branding does not rewrite those fields. Review them separately when changing station identity.

Visible identity can change without renaming the application package. Avoid renaming internal module identifiers, scene IDs or settings keys merely to change the visible name. Fonts and provider credits retain their separate notices. Some graphics retain fixed colours; the accent field does not recolour every element. After changing branding, restart the station as described in [Linux deployment](LINUX-DEPLOYMENT.md) and review both the desk and rendered output. Live branding reload is not supported.
