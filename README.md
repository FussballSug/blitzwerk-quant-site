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
Only fixed public assets, this renderer, pinned requirements, static support,
public tests/workflow and this README are copied. Packaging does not push, deploy, connect a feed or verify a public URL.
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
Default exports retain the legacy unverified fallback. To preserve a newer already
public snapshot, explicitly pass `--public-snapshot <retained-public-json>` to the
export command. The bounded strict validator rejects private fields and future
observations before any output is written; exact accepted bytes are retained. The
exporter never fetches data or overwrites an existing public checkout. Copy the
reviewed package only through the normal source/deployment review process. The page
ages every report when viewed, so a stopped publisher remains visibly stale.
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

The existing static URL is `https://fussballsug.github.io/blitzwerk-quant-site/`.
The existing `https://blitzwerk-quant.streamlit.app/` entry remains compatible and
available as a secondary view with a link to the primary website. A static mirror cannot redirect a
sleeping Streamlit host. Deployment and user-facing primary-link adoption are
separate from implementation/CI. The engineering export includes the static support and workflow by a fixed
allowlist. `test_fixtures/observed_public_snapshot.json` is historical already-public
October31 evidence used only by tests; it never becomes the runtime fallback
unless explicitly selected. The legacy source fixture is preserved.

Local checks: `python -m pytest -q` and
`node --test test_static_feed.cjs test_static_document.cjs test_activity.cjs test_flow.cjs` (Python 3.12, Node 24).
Python/JavaScript parity includes real public evidence, synthetic strategy metrics,
workflow variants and the unchanged freshness boundaries. No Streamlit dependency
is needed to build or test the static report; the existing Streamlit requirement
continues to serve the existing hosted app.

## Hourly activity and Team Flow

The Hourly Activity tab groups observations by unique UTC hour, with a choice of
America/Chicago or UTC display. Chicago daylight-saving repeated hours retain
separate UTC keys and timezone labels. Every registry worker remains visible,
including workers with no verified accomplishment. A recorded result digest is
shown as a reference, not an inferred completion. Missing evidence is not a
no-change report. Saved workflow checkpoints do not establish a Git push or deploy.

`assets/activity.json` is a separately reviewed public engineering ledger, embedded
at build time: at most48 exact-schema events /24KiB, fixed public repository links,
release and receipt digests, and optional known-worker attribution. It adds no
browser request. Initial entries retain the actual observation of remote release
522e4355 and successful Pages deployment41252580820. Their observed time is not
claimed to be the exact push time. Worker attribution is unknown. Engineering
notes never refresh the operational snapshot or imply a running PAPER session.
A future change needs its own factual source review; a commit is not deployment.

The Team Flow tab uses the same fifteen registry identities and reporting lines.
It illustrates possible evidence handoffs, not deployed workers or observed
messages. Independent Schneider review and Weber risk veto remain distinct gates.
The guided tour, role focus, keyboard selection, pause/speed and reduced-motion
static map have no execution controls. Motion uses one requestAnimationFrame chain,
at most24 particles /30 visual updates per second, and runs only while that tab
and document are visible. Verified-events mode never animates conceptual routes.
No CDN, extra dependency, background keepalive or persistence is introduced.

The public schema currently lacks complete hourly worker accomplishment histories,
per-event author attribution, and sender/receiver/time-bound transfer attestations.
The tabs display those gaps explicitly; they do not reconstruct them from names,
workflow topology or receipt hashes. The existing64KiB/two-request/five-second
feed and freshness thresholds remain unchanged. Both tabs work in the static
build and existing Streamlit renderer; no static-site deploy updates Streamlit
until the existing host actually adopts the corresponding repository version.

Additional local checks: `node --test test_activity.cjs test_flow.cjs`; all Node
checks use `PYTHON=/path/to/python3.12` when the default interpreter is older.
Apply the private engineering repository's `docs/AUTOMATED_ENGINEERING.md` for
independent source review, required CI and actual deployment/readback acceptance.

The authoritative mirror stores the reviewed UI and activity assets in
`activity_assets/`; exports assemble them into `assets/` alongside the preserved
legacy snapshot, or the existing explicitly supplied validated public snapshot.
The existing private dashboard UI and legacy snapshot remain byte-for-byte unchanged.
Rendering helpers resolve fixed sibling modules without altering the import path.

Rolling evidence compatibility: this reader accepts both legacy schema2 reports
and schema3 reports with a bounded `activity` envelope. The existing two fixed
feed URLs, shared five-second fetch deadline, 64 KiB total response bound, and
600/45/60-second operational freshness rules are unchanged. The extra envelope
holds at most48 combined hour/detail records and24 KiB; counts may outlive
trimmed detail records, which are labeled. Activity collection time does not
refresh operational health. UTC hour keys distinguish the repeated Chicago DST
hour, and the current hour is partial.

`complete_query` means a complete query of recorded evidence within the bounded
window, not all work or verified worker connectivity. Missing historical source
receipts remain partial coverage. Reviews received by a task owner do not credit
that owner with performing a review. Historical unmapped roles remain anonymous.
Engineering events use reviewed categories and exact observed stages; private
platform branch pushes expose only the sanitized repository code and source hash,
never a private URL. Branch presence does not establish merge or runtime adoption.
The explicit completion hook must record independently reviewed observations;
this website does not discover Git history, create reviews, or perform deployments.

The GitHub Pages URL is the main website. Streamlit displays a secondary-view
link to that same primary site; both continue to use the existing public feed.
