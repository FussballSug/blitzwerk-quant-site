"""Keep the static-browser projection aligned with the existing strict reader."""
import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import streamlit_app as renderer


def cases():
    original=json.loads(Path('test_fixtures/observed_public_snapshot.json').read_bytes())
    observed=renderer._timestamp(original['snapshot_at'])
    employee={**renderer.CATALOG['braun'],'state':'waiting','current_task':'evaluation',
        'heartbeat':observed.timestamp(),'updated_at':observed.timestamp(),
        'strategy_evidence_state':'current','strategy_evidence_as_of':observed.timestamp(),
        'execution_basis':'recorded_evaluation_receipt','worker_connection_verified':False,
        **{key:'a'*64 for key in ('strategy_version','configured_strategy_version','executed_strategy_version',
            'manifest_sha256','strategy_evidence_reference','mandate_reference','approved_universe_reference','risk_policy_reference')},
        'configured_source_revision':'b'*40,'executed_source_revision':'b'*40,
        'performance_as_of':observed.timestamp(),'performance_basis':'broker_reported_accounting',
        'performance_reference':'c'*64,'performance':{'realized_pnl':'1.25','unrealized_pnl':'1E-9',
            'drawdown':'0.00','exposure':'1E+10','fees':'0.10','sample_size':3},
        'fees_basis':'broker_observed','assumed_costs':'0.00',
        'runtime_basis':'controller_handled_responsibility','runtime_freshness':'current',
        'runtime_evidence_as_of':observed.timestamp(),'last_task_reference':'synthetic-record',
        'runtime_due_at':observed.timestamp()+90}
    workflows=[]
    for kind,mode,version in [('trading','source_receipt_observation',2),('publishing','source_receipt_observation',2),
        ('incident','finite_stopped_startup_recovery',3),('improvement','finite_closed_session_canary',3)]:
        nodes=renderer.OBSERVATION_GRAPHS[kind] if version==2 else renderer.GRAPHS[kind]
        workflows.append({'run_id':'synthetic-'+kind,'kind':kind,'mode':mode,'version':version,'execution_authorized':False,
            'status':'waiting','node':nodes[0],'updated_at':observed.timestamp(),'deadline_at':observed.timestamp()+30,
            'artifact_digests':['d'*64],'history':[{'node':nodes[0],'outcome':'passed','at':observed.timestamp()}],
            **({'current_evidence':'current','evidence_as_of':observed.timestamp()} if version==2 else {})})
    rich={**original,**renderer.sanitize_operations({'employees':[employee],'workflows':workflows})}
    rich['traders']=renderer._traders(rich['employees'])
    renderer.validate_public_snapshot(rich)
    result=[]
    for value in (original,rich):
        for seconds in (0,45,46,60,61,90,600,601):
            now=observed+timedelta(seconds=seconds)
            result.append({'input':value,'now':now.timestamp()*1000,'expected':renderer.refresh_public_snapshot(value,now=now)})
    for key,value in [('realized_pnl','1E+0'),('fees','01'),('sample_size',True),('exposure','1E+13')]:
        malformed=json.loads(json.dumps(rich));malformed['employees'][0]['performance'][key]=value
        malformed['traders']=renderer._traders(malformed['employees'])
        try:renderer.validate_public_snapshot(malformed)
        except ValueError:result.append({'input':malformed,'reject':True})
        else:raise AssertionError('Adverse fixture must be rejected by authoritative reader')
    return result


def test_browser_projection_matches_authoritative_python_with_real_and_rich_evidence():
    node=os.environ.get('NODE','node')
    result=subprocess.run([node,'-e',"""
const {createStaticReader}=require('./static_feed.js');
const input=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
for(const [index,row] of input.cases.entries()){
 const reader=createStaticReader({schema:input.schema,initial:input.initial,now:()=>row.now||0});
 if(row.reject){require('node:assert/strict').throws(()=>reader.validate(row.input));continue;}
 const actual=reader.refresh(row.input);
 if(!require('node:util').isDeepStrictEqual(actual,row.expected)){
  const differences=Object.keys(row.expected).filter(k=>!require('node:util').isDeepStrictEqual(actual[k],row.expected[k]));
  throw Error('Parity case '+index+' differs in '+differences.join(','));
 }
}
console.log(input.cases.length);
"""],input=json.dumps({'schema':json.loads(__import__('build_static').encoded(__import__('build_static').schema())),
    'initial':json.loads(Path('test_fixtures/observed_public_snapshot.json').read_bytes()),'cases':cases()}),capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
    assert result.stdout.strip()=='20'
