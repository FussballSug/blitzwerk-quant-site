"""The scene illustrates registry responsibilities, not live transfers."""
import json
from pathlib import Path


def test_scene_uses_exact_fifteen_registry_people_and_independent_controls():
    import streamlit_app as renderer
    from team_flow import scene, svg
    value = scene(renderer.CATALOG)
    assert {n['id'] for n in value['nodes']} == set(renderer.CATALOG)
    assert len(value['nodes']) == 15
    assert all(n['manager'] == renderer.CATALOG[n['id']]['manager'] for n in value['nodes'])
    assert next(n for n in value['nodes'] if n['id']=='weber')['manager'] == 'owner'
    assert next(n for n in value['nodes'] if n['id']=='schneider')['manager'] == 'owner'
    assert value['actual_transfers_verified'] is False
    assert any(e['kind']=='risk' for e in value['links'])
    assert any(e['kind']=='review' for e in value['links'])
    html = svg(value)
    assert html.count('class="flow-node"') == 15
    assert html.count('tabindex="0"') == 15
    assert 'role="button"' in html and 'Conceptual' in html
    assert '<canvas' not in html


def test_complete_document_has_static_fallback_and_motion_controls():
    import streamlit_app as renderer
    html = renderer.render_document(json.loads(Path('assets/snapshot.json').read_bytes()),page='flow')
    assert 'data-page="flow"' in html and 'href="#flow"' in html
    assert 'id="flow-map"' in html and 'id="flow-play"' in html
    assert 'id="flow-speed"' in html and 'id="flow-worker"' in html
    assert 'id="flow-mode"' in html and 'id="flow-next"' in html
    assert 'Illustration, not live activity' in html
    assert '<noscript>' in html and 'Sug' in html
    assert 'requestAnimationFrame' in html and 'prefers-reduced-motion' in html
    assert '<script src=' not in html
