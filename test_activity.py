"""Public activity is evidence presentation, never inferred worker accomplishment."""
import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest


def ledger():
    return {
        'schema_version': 1, 'scope': 'reviewed_public_activity',
        'reviewed_at': '2026-11-01T01:00:00+00:00',
        'events': [{
            'event_id': 'synthetic-static-push', 'observed_at': '2026-10-31T23:00:00+00:00',
            'worker_id': None, 'change': 'static_public_report', 'stage': 'pushed',
            'source_revision': 'a'*40, 'receipt_sha256': 'b'*64,
            'reference_url': 'https://github.com/FussballSug/blitzwerk-quant-site/commit/'+'a'*40,
            'deployment_url': None,
        }],
    }


def test_ledger_keeps_exact_observation_and_unassigned_attribution():
    from public_activity import validate
    value = ledger()
    assert validate(value, now=datetime(2026,11,1,2,tzinfo=UTC)) == value
    assert value['events'][0]['worker_id'] is None


@pytest.mark.parametrize('fault', [
    'extra', 'bool', 'future_review', 'future_event', 'unknown_worker', 'unknown_stage',
    'private_url', 'wrong_commit', 'missing_receipt', 'deployment_without_url',
    'push_without_revision', 'duplicate', 'oversize', 'naive', 'private_field',
])
def test_invalid_activity_cannot_enter_public_build(fault):
    from public_activity import validate
    value = ledger(); event = value['events'][0]
    if fault == 'extra': value['raw_messages'] = 'private'
    elif fault == 'bool': value['schema_version'] = True
    elif fault == 'future_review': value['reviewed_at'] = '2027-01-01T00:00:00Z'
    elif fault == 'future_event': event['observed_at'] = '2026-11-01T01:00:01Z'
    elif fault == 'unknown_worker': event['worker_id'] = 'invented-agent'
    elif fault == 'unknown_stage': event['stage'] = 'profitable'
    elif fault == 'private_url': event['reference_url'] = 'file:///private/tmp/evidence.json'
    elif fault == 'wrong_commit': event['reference_url'] = event['reference_url'][:-1]+'c'
    elif fault == 'missing_receipt': event['receipt_sha256'] = None
    elif fault == 'deployment_without_url': event['stage'] = 'deployed'
    elif fault == 'push_without_revision': event['source_revision'] = None
    elif fault == 'duplicate': value['events'].append(copy.deepcopy(event))
    elif fault == 'oversize': value['events'] = [copy.deepcopy(event) for _ in range(49)]
    elif fault == 'naive': event['observed_at'] = '2026-10-31T23:00:00'
    elif fault == 'private_field': event['account'] = 'never public'
    with pytest.raises((ValueError, TypeError)):
        validate(value, now=datetime(2026,11,1,2,tzinfo=UTC))


def test_no_change_requires_an_explicit_evidence_record():
    from public_activity import validate
    value = ledger(); event = value['events'][0]
    event.update(stage='no_change', source_revision=None, reference_url=None)
    assert validate(value)['events'][0]['stage'] == 'no_change'
    event['receipt_sha256'] = None
    with pytest.raises(ValueError): validate(value)


def test_generated_pages_share_activity_tab_without_changing_feed_schema(tmp_path):
    import streamlit_app as renderer
    from build_static import build
    raw = Path('assets/snapshot.json').read_bytes()
    output = tmp_path/'site'
    build(output, raw)
    static = (output/'index.html').read_text()
    legacy = renderer.render_document(json.loads(raw), page='activity')
    for html in (static, legacy):
        assert 'href="#activity"' in html and 'id="activity"' in html
        assert 'id="activity-worker"' in html and 'id="activity-hour"' in html
        assert 'id="activity-zone"' in html and 'BLITZWERK_ACTIVITY' in html
        assert 'No result recorded' in html
    assert 'data-page="activity"' in legacy
    assert set(json.loads(raw)) == renderer.PUBLIC_KEYS
    assert renderer.MAX_BYTES == 65536 and renderer.MAX_FEED_REQUESTS == 2
    assert renderer.FETCH_TIMEOUT_SECONDS == 5


def test_ledger_read_rejects_duplicate_keys_and_oversized_input(tmp_path):
    from public_activity import MAX_ACTIVITY_BYTES, read_ledger
    path = tmp_path/'activity.json'
    path.write_text('{"scope":"reviewed_public_activity","scope":"replacement"}')
    with pytest.raises(ValueError): read_ledger(path)
    path.write_bytes(b' '*(MAX_ACTIVITY_BYTES+1))
    with pytest.raises(ValueError): read_ledger(path)


def test_reviewed_public_notes_do_not_attribute_an_unproven_worker():
    from public_activity import read_ledger
    value = read_ledger(Path('assets/activity.json'))
    assert {event['stage'] for event in value['events']} == {'pushed', 'deployed'}
    assert all(event['worker_id'] is None for event in value['events'])
    assert all(event['source_revision'] == '522e435518989e88d2868ee6eb16c8c1150dff66' for event in value['events'])
    assert all(event['observed_at'] == '2026-10-31T23:27:59.426525+00:00' for event in value['events'])
    assert all(event['receipt_sha256'] == 'b4dff2b313cdeffce52e809c46c6eb70768cfd8035ac11ff0db17f34e60d0881' for event in value['events'])
