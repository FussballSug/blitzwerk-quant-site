# Blitzwerk Kapital public site

This is the existing sanitized Streamlit deployment mirror layout for
`FussballSug/blitzwerk-quant-site`. The authoritative source is the private
engineering repository. This package contains presentation assets and a standalone
schema validator; it has no broker client, private platform imports, credentials,
raw account records, operational controls or notification sender.

Run `streamlit run streamlit_app.py`. The bundled `assets/snapshot.json` is the
fallback. Its original observation timestamp determines freshness; missing metrics
remain UNKNOWN. A role name or workflow definition is not deployed activity.

An approved administrator may configure `PUBLIC_STATUS_URL` to an existing,
credential-free HTTPS JSON endpoint serving the exact version 2 public schema.
The app uses a five-second network timeout, a 64 KiB response limit, no redirects,
30-second refresh while viewed, and a session-memory cache of the last valid
snapshot. A malformed, oversized or unreachable feed cannot replace that cache.
Failures prominently show stale/offline reporting and unknown current engine state.
This allows hourly JSON publishing without rebuilding or redeploying website code.
No remote endpoint or upload authority is created by setting a local file.

Prepare a package from the engineering checkout with
`python site/public_mirror/streamlit_app.py --export-directory <empty-directory>`.
Only the fixed asset allowlist, this renderer, pinned requirements and this README
are copied. Packaging does not push, deploy, connect a feed or verify a public URL.
Apply the engineering repository's `docs/AUTOMATED_ENGINEERING.md` for review and
operational acceptance. The owner's actual Sug delivery connection remains
unverified until separately configured and tested.

For a separately approved finite data-only pilot, the optional
`PUBLIC_STATUS_URL_TEMPLATE` accepts only
`https://raw.githubusercontent.com/FussballSug/blitzwerk-quant-site/refs/heads/status-data/slots/{utc_slot}.json`.
The current UTC-hour URL is tried first; the same branch's `latest.json` is the
fallback (also accepted as the paired `PUBLIC_STATUS_URL`). A missing current slot
always labels fallback data stale, including for a new visitor with an empty
cache. No historical slot is relabeled current. At most two bounded requests
share the five-second request/deadline budget. DNS/socket behavior and actual CDN
propagation still need measurement; there is no 60-second propagation guarantee.
The reader contains no Git writer or credential. The private engineering
proposal limits a candidate writer to 168 lifetime slots and requires separate
activation and headless-authentication acceptance; none is started by this package.
