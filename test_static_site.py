"""Static delivery must retain the existing validator and truthful observations."""
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import streamlit_app as renderer


def test_static_build_is_self_contained_and_retains_snapshot_and_notice(tmp_path):
    from build_static import build
    now=datetime(2026,10,31,23,tzinfo=UTC)
    raw=Path('assets/snapshot.json').read_bytes()
    output=tmp_path/'site'
    build(output,raw,now=now)
    html=(output/'index.html').read_text()
    assert set(p.name for p in output.iterdir())=={'index.html','build.json'}
    assert 'BLITZWERK_STATIC' in html and 'REPORT AS OF' in html
    assert 'Public reports are scheduled hourly.' in html
    assert 'STALE / OFFLINE REPORTING' in html
    assert 'https://blitzwerk-quant.streamlit.app/' in html
    assert '<script src=' not in html and '<link rel="stylesheet"' not in html
    receipt=json.loads((output/'build.json').read_bytes())
    assert receipt['snapshot_at']==json.loads(raw)['snapshot_at']
    assert receipt['freshness_at_build']=='stale'
    assert receipt['source_observation_rewritten'] is False
    assert receipt['data_fetch_during_build'] is False


@pytest.mark.parametrize('fault',['private_field','invalid_json','oversized','future','mutated_catalog'])
def test_invalid_static_input_cannot_create_or_replace_site(tmp_path,fault):
    from build_static import build
    now=datetime(2026,10,31,23,tzinfo=UTC)
    value=json.loads(Path('assets/snapshot.json').read_bytes())
    if fault=='private_field':value['account_id']='synthetic forbidden field'
    elif fault=='future':value['snapshot_at']=(now+timedelta(seconds=1)).isoformat()
    elif fault=='mutated_catalog':value['employees'][0]['authority']=['trade_live']
    raw=b'{' if fault=='invalid_json' else b'x'*65537 if fault=='oversized' else json.dumps(value).encode()
    output=tmp_path/'site'
    with pytest.raises((ValueError,TypeError)):build(output,raw,now=now)
    assert not output.exists()


def test_static_build_refuses_existing_destination(tmp_path):
    from build_static import build
    output=tmp_path/'site';output.mkdir();(output/'index.html').write_text('retained')
    with pytest.raises(FileExistsError):build(output,Path('assets/snapshot.json').read_bytes())
    assert (output/'index.html').read_text()=='retained'
