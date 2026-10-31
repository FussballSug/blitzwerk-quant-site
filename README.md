# Blitzwerk Kapital public site

This is the existing sanitized Streamlit deployment mirror layout for
`FussballSug/blitzwerk-quant-site`. The authoritative source is the private
engineering repository. This package contains presentation assets and a standalone
schema validator; it has no broker client, private platform imports, credentials,
raw account records, operational controls or notification sender.

Run `streamlit run streamlit_app.py`. The bundled `assets/snapshot.json` is the
fallback. Its original observation timestamp determines freshness; missing metrics
remain UNKNOWN. A role name or workflow definition is not deployed activity.

When both `PUBLIC_STATUS_URL` and `PUBLIC_STATUS_URL_TEMPLATE` are absent, this
renderer reads only the fixed existing `FussballSug/blitzwerk-quant-site`
`status-data` current-UTC-slot URL and its `latest.json` fallback described below.
This source-only default requires no interactive hosting configuration. Publish
and verify the truthful initial slot before enabling it, to avoid requesting an
unpublished path and priming a negative cache.

An explicit setting keeps the existing configuration behavior: `PUBLIC_STATUS_URL`
alone selects its validated credential-free HTTPS JSON endpoint, while an explicit
empty setting preserves local-only fallback. Invalid or mixed settings fail closed
and are never silently replaced by defaults. Every endpoint serves the exact
version 2 public schema. No credential, writer, schedule or account is added.
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

## Static report in the same repository

`python build_static.py --output _site` creates a self-contained `index.html`
and a build receipt. It uses this renderer's existing validator, roster, scorecards,
workflow graphs and styles. Build time is never substituted for observation time.
The bundled fallback is the already public, verified October 31 05:00 UTC report.
The page ages that report when viewed, so a stopped publisher remains visibly stale.
JavaScript must be enabled for the dashboard; its initial warning remains unverified
until the reader renders a validated snapshot.

The browser reads only the existing `status-data` current-hour and latest URLs,
with the same two-request, five-second, 64 KiB, no-redirect limits. Requests omit
credentials. A failed current-hour read forces the latest fallback stale. Invalid,
future or older data cannot replace the last valid memory cache. No browser storage,
writer, operational control, background keepalive or additional publisher is added.
The existing 30-second refresh runs only while the page is open. Existing 600-second
report, 45-second controller and 60-second heartbeat/evidence thresholds remain.
An hourly snapshot will normally become stale before the next hourly report.

The `Static public report` workflow tests and builds on PRs and main pushes using
standard public GitHub-hosted runners. **Deployment runs only on an explicit
workflow dispatch from main**, after Pages is configured for GitHub Actions.
Merging the code alone neither enables Pages nor deploys it. No schedule or workflow
is added to the JSON-only `status-data` branch. The published page reads subsequent
JSON updates without a site rebuild. GitHub documents Pages for public repositories
on its free tier; this is an informational project report with no transactions or
paid-hosting settings. Apply `docs/AUTOMATED_ENGINEERING.md` in the engineering repo
for independent review and actual post-deployment URL/readback verification.

The proposed URL is `https://fussballsug.github.io/blitzwerk-quant-site/`.
The existing `https://blitzwerk-quant.streamlit.app/` entry remains compatible and
unchanged; the static report links back to it. A static mirror cannot redirect a
sleeping Streamlit host. Deployment and user-facing primary-link adoption are
separate from implementation/CI. The engineering export does not yet include these
static files: preserve them when updating this public mirror.

Local checks: `python -m pytest -q` and
`node --test test_static_feed.cjs test_static_document.cjs` (Python 3.12, Node 24).
Python/JavaScript parity includes real public evidence, synthetic strategy metrics,
workflow variants and the unchanged freshness boundaries. No Streamlit dependency
is needed to build or test the static report; the existing Streamlit requirement
continues to serve the existing hosted app.
