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
    rows = {event['event_id']: event for event in value['events']}
    original = [event for event in value['events'] if event['source_revision'] == '522e435518989e88d2868ee6eb16c8c1150dff66']
    assert len(original) == 2
    assert all(event['observed_at'] == '2026-10-31T23:27:59.426525+00:00' for event in original)
    assert all(event['receipt_sha256'] == 'b4dff2b313cdeffce52e809c46c6eb70768cfd8035ac11ff0db17f34e60d0881' for event in original)
    expected = {
        'hourly-activity-pr7-remote-observation': ('a33b8265676f9edb1bfad66d613346f7886a2a45', 'pushed', 'hourly_activity_view', '2026-11-01T01:56:49.946426+00:00', '14b6b13fefae007dfee5e2768beca426d6274652c07193c0ebe937d740d0ea3b'),
        'hourly-activity-pages-41262131000': ('a33b8265676f9edb1bfad66d613346f7886a2a45', 'deployed', 'hourly_activity_view', '2026-11-01T01:42:56.041649+00:00', '2442869ccef299bc87219a21910ad5711f7847211ad0bd8975313b2bb311cddc'),
        'reporting-reliability-pr8-remote-observation': ('eeed56feda0bbc73878ec996cf8ea30a76bc9deb', 'pushed', 'reporting_reliability', '2026-11-01T02:38:04.029015+00:00', 'c93aec79cdf5230fc732c0ed6904297cced74cf7306eb9fbda9a8d6771c3d69f'),
        'reporting-reliability-pages-41266019682': ('eeed56feda0bbc73878ec996cf8ea30a76bc9deb', 'deployed', 'reporting_reliability', '2026-11-01T02:40:13.962626+00:00', 'c2e1ccdbcb16885bc615ffbc12a281d2db47d344f0cd237f718c3db0e5d95ace'),
    }
    assert len(rows) == 6
    for identity, expected_fields in expected.items():
        row = rows[identity]
        assert tuple(row[key] for key in ('source_revision', 'stage', 'change', 'observed_at', 'receipt_sha256')) == expected_fields
        if row['stage'] == 'pushed':
            assert row['reference_url'] == 'https://github.com/FussballSug/blitzwerk-quant-site/commit/' + row['source_revision']
            assert row['deployment_url'] is None
        else:
            run = identity.rsplit('-', 1)[-1]
            assert row['reference_url'] == 'https://github.com/FussballSug/blitzwerk-quant-site/actions/runs/' + run
            assert row['deployment_url'] == 'https://fussballsug.github.io/blitzwerk-quant-site/'
