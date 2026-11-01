"""Build one self-contained public report; never fetch or publish.

Apply docs/AUTOMATED_ENGINEERING.md. Pages consumes the same sanitized public
snapshot and validator as Streamlit. A browser reads only the existing feed.
"""
import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import streamlit_app as renderer


def schema():
    names=('CATALOG','PUBLIC_KEYS','STATES','TRIGGERS','BLOCKERS','GRAPHS','METRICS',
           'LEGACY_TRADER_KEYS','OBSERVATION_GRAPHS','RUNTIME_BASES','GRAPH_STATES','OUTCOMES','REASONS','TRADERS')
    return {**{name:getattr(renderer,name) for name in names},'unknown':renderer.unknown(),'stages':renderer._stages(), 'ACTIVITY': {name:getattr(renderer._render_helper('public_activity_projection'),name) for name in ('WORKERS','COUNTS','EVENT_KEYS','ACTIVITY_KEYS','KINDS','CHANGES','CONTROLLER_SUMMARIES')}}


def encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False,
                      default=lambda value:sorted(value) if isinstance(value,(set,frozenset)) else value)


def build(directory,raw,*,now=None):
    now=now or datetime.now(UTC)
    if type(raw) is not bytes or len(raw)>renderer.MAX_BYTES:
        raise ValueError('Bounded exact public snapshot required')
    original=renderer.validate_public_snapshot(json.loads(raw))
    if original['snapshot_at'] is not None and renderer._timestamp(original['snapshot_at'])>now:
        raise ValueError('Future observation cannot seed a static report')
    snapshot=renderer.refresh_public_snapshot(original,now=now)
    # Keep as-of source bytes in the browser cache so evidence ages on every view.
    html=renderer.render_document(original)
    marker='async function load(){'
    if html.count(marker)!=1:
        raise ValueError('Expected exact renderer entry required')
    html=html.replace(marker,marker+'if(window.BLITZWERK_STATIC){render(await window.BLITZWERK_STATIC.load());return}',1)
    client=(Path(__file__).with_name('static_feed.js')).read_text()
    setup=(client+'\nwindow.BLITZWERK_STATIC=createStaticReader({schema:'+encoded(schema())+
           ',initial:window.BLITZWERK_DATA});')
    marker='</script><script>'
    if html.count(marker)!=1:
        raise ValueError('Expected single embedded snapshot boundary required')
    html=html.replace(marker,'</script><script>'+setup.replace('</',r'<\/')+'</script><script>',1)
    receipt={'schema_version':1,'scope':'static_public_reporting_build','built_at':now.isoformat(),
             'snapshot_at':original['snapshot_at'],'snapshot_sha256':hashlib.sha256(raw).hexdigest(),
             'freshness_at_build':snapshot['freshness'],'source_observation_rewritten':False,
             'data_fetch_during_build':False,'mode':'paper research','html_sha256':hashlib.sha256(html.encode()).hexdigest()}
    directory=Path(directory);directory.mkdir(parents=False,exist_ok=False)
    (directory/'index.html').write_text(html)
    (directory/'build.json').write_text(encoded(receipt)+'\n')
    return receipt


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--schema',action='store_true')
    parser.add_argument('--snapshot',type=Path,default=Path(__file__).with_name('assets')/'snapshot.json')
    parser.add_argument('--output',type=Path,default=Path('_site'))
    args=parser.parse_args()
    if args.schema:
        print(encoded(schema()));return
    with args.snapshot.open('rb') as source:
        raw=source.read(renderer.MAX_BYTES+1)
    print(encoded(build(args.output,raw)))


if __name__=='__main__':
    main()
