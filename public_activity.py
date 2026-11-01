"""Bounded, reviewed public notes; no network, private discovery or authority.

Apply docs/AUTOMATED_ENGINEERING.md. This ledger is curated from retained public
evidence. Its shape cannot authenticate an author or prove a push/deployment;
independent source review must check those facts before publication.
"""
import json
import re
from datetime import UTC, datetime

MAX_ACTIVITY_BYTES = 24 * 1024
MAX_EVENTS = 48
WORKERS = {'sug', 'reinhardt', 'hoffmann', 'weber', 'schneider', 'vogel', 'fischer',
           'johanna', 'braun', 'hartmann', 'krueger', 'mueller', 'adler', 'richter', 'bergmann'}
CHANGES = {
    'static_public_report': 'Static public reporting',
    'hourly_activity_view': 'Hourly activity and worker evidence',
    'reporting_reliability': 'Reporting reliability',
    'bounded_performance': 'Measured engineering performance',
    'evidence_validation': 'Evidence validation',
}
STAGES = {'proposed', 'validated', 'pushed', 'deployed', 'no_change'}
PUBLIC_REPO = 'https://github.com/FussballSug/blitzwerk-quant-site/'
PUBLIC_SITE = 'https://fussballsug.github.io/blitzwerk-quant-site/'
EVENT_KEYS = {'event_id', 'observed_at', 'worker_id', 'change', 'stage', 'source_revision',
              'receipt_sha256', 'reference_url', 'deployment_url'}


def need(value):
    if not value:
        raise ValueError('Exact bounded public activity evidence required')


def timestamp(value):
    need(type(value) is str)
    parsed = datetime.fromisoformat(value)
    need(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0)
    return parsed


def validate(value, *, now=None):
    now = now or datetime.now(UTC)
    need(type(value) is dict and set(value) == {'schema_version', 'scope', 'reviewed_at', 'events'})
    need(type(value['schema_version']) is int and value['schema_version'] == 1
         and value['scope'] == 'reviewed_public_activity')
    need(type(value['events']) is list and len(value['events']) <= MAX_EVENTS)
    reviewed = timestamp(value['reviewed_at']) if value['reviewed_at'] is not None else None
    need((reviewed is not None and reviewed <= now) or (reviewed is None and not value['events']))
    seen = set()
    for event in value['events']:
        need(type(event) is dict and set(event) == EVENT_KEYS)
        identity = event['event_id']
        need(type(identity) is str and re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}', identity)
             and identity not in seen)
        seen.add(identity)
        need(reviewed is not None and timestamp(event['observed_at']) <= reviewed)
        need(event['worker_id'] is None or type(event['worker_id']) is str and event['worker_id'] in WORKERS)
        need(type(event['change']) is str and event['change'] in CHANGES
             and type(event['stage']) is str and event['stage'] in STAGES)
        revision, receipt = event['source_revision'], event['receipt_sha256']
        need(revision is None or type(revision) is str and re.fullmatch('[a-f0-9]{40}', revision))
        need(type(receipt) is str and re.fullmatch('[a-f0-9]{64}', receipt))
        link, deployed = event['reference_url'], event['deployment_url']
        need(link is None or type(link) is str and re.fullmatch(
            re.escape(PUBLIC_REPO) + r'(?:commit/[a-f0-9]{40}|pull/[1-9][0-9]*|actions/runs/[1-9][0-9]*)', link))
        need(deployed is None or deployed == PUBLIC_SITE)
        if event['stage'] == 'pushed':
            need(revision is not None and link == PUBLIC_REPO + 'commit/' + revision and deployed is None)
        elif event['stage'] == 'deployed':
            need(revision is not None and deployed == PUBLIC_SITE and type(link) is str
                 and re.fullmatch(re.escape(PUBLIC_REPO) + r'actions/runs/[1-9][0-9]*', link))
        else:
            need(deployed is None)
    need(len(json.dumps(value, ensure_ascii=False).encode()) <= MAX_ACTIVITY_BYTES)
    return json.loads(json.dumps(value))


def read_ledger(path):
    with path.open('rb') as stream:
        raw = stream.read(MAX_ACTIVITY_BYTES + 1)
    need(len(raw) <= MAX_ACTIVITY_BYTES)
    def pairs(items):
        result = {}
        for key, item in items:
            need(key not in result)
            result[key] = item
        return result
    return validate(json.loads(raw, object_pairs_hook=pairs))
