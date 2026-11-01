/* Explicit bounded-history coverage must survive the real static feed reader. */
const test = require('node:test');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const {createStaticReader} = require('./static_feed.js');
const py = process.env.PYTHON || 'python3';
const schema = JSON.parse(execFileSync(py, ['build_static.py', '--schema'], {encoding:'utf8'}));
const at = Date.parse('2026-11-01T04:10:00Z');
const legacy = JSON.parse(execFileSync(py, ['-c', [
  'import json',
  'from datetime import datetime,UTC',
  'from streamlit_app import build_public_snapshot',
  'from public_activity_projection import project_activity,fit_snapshot_activity',
  'now=datetime(2026,11,1,4,10,tzinfo=UTC)',
  "base=build_public_snapshot({'checked_at':now.isoformat(),'state':'stopped','health':'attention'},now=now)",
  'print(json.dumps(fit_snapshot_activity(base,project_activity([],now=now))))'
].join('\n')], {encoding:'utf8'}));
const copy = value => JSON.parse(JSON.stringify(value));
function bounded(){
  const value = copy(legacy);
  value.schema_version = 4;
  value.operations_coverage = {
    schema_version:1, scope:'bounded_public_operations', selection:'latest_per_kind_then_recent',
    source_counts:{workflows:0,incidents:0}, queried_counts:{workflows:0,incidents:0},
    displayed_counts:{workflows:0,incidents:0},
    workflow_kinds:Object.fromEntries(['trading','improvement','incident','publishing']
      .map(kind=>[kind,{source:0,queried:0,displayed:0}])),
    history_counts:{queried:0,displayed:0}, artifact_reference_counts:{queried:0,displayed:0},
    query_truncated:false, display_truncated:false, partial:false
  };
  return value;
}
function reader(initial=legacy, options={}){
  return createStaticReader({schema,initial,now:()=>at,...options});
}
test('schema4 retains exact explicit operational coverage and real health/activity time',()=>{
  const value = bounded();
  assert.deepEqual(reader().validate(value), value);
  const refreshed = reader().refresh(value);
  assert.deepEqual(refreshed.operations_coverage,value.operations_coverage);
  assert.deepEqual(refreshed.activity,value.activity);
  assert.equal(refreshed.snapshot_at,value.snapshot_at);
  assert.equal(refreshed.desk_state,'stopped for review');
});
test('legacy schemas still load; actual schema4 may upgrade the cache',async()=>{
  assert.deepEqual(reader().validate(legacy),legacy);
  const value=bounded();
  const loaded=await reader(legacy,{fetch:async()=>new Response(JSON.stringify(value))}).load();
  assert.equal(loaded.schema_version,4);
  assert.deepEqual(loaded.operations_coverage,value.operations_coverage);
});
for(const fault of ['bool_count','source_smaller','display_mismatch','kind_sum','history','extra','false_complete','mixed_unknown_sum','oversized_query']){
  test('coverage rejects '+fault,()=>{
    const value=bounded(),c=value.operations_coverage;
    if(fault==='bool_count')c.source_counts.workflows=false;
    if(fault==='source_smaller'){c.queried_counts.workflows=1;c.workflow_kinds.incident.queried=1;}
    if(fault==='display_mismatch'){c.displayed_counts.incidents=1;c.queried_counts.incidents=1;c.source_counts.incidents=1;}
    if(fault==='kind_sum')c.workflow_kinds.incident.source=1;
    if(fault==='history')c.history_counts.displayed=1;
    if(fault==='extra')c.private_account='forbidden';
    if(fault==='false_complete'){c.source_counts.incidents=100;c.query_truncated=true;c.partial=false;}
    if(fault==='mixed_unknown_sum'){c.workflow_kinds.incident.source=1;c.workflow_kinds.trading.source=null;c.query_truncated=true;c.partial=true;}
    if(fault==='oversized_query'){c.source_counts.workflows=1001;c.queried_counts.workflows=1001;c.workflow_kinds.incident={source:1001,queried:1001,displayed:0};c.display_truncated=true;c.partial=true;}
    assert.throws(()=>reader().validate(value));
  });
}
test('a cache with explicit coverage cannot silently downgrade to schema3',async()=>{
  const value=bounded();
  const loaded=await reader(value,{fetch:async()=>new Response(JSON.stringify(legacy))}).load();
  assert.equal(loaded.schema_version,4);
  assert.deepEqual(loaded.operations_coverage,value.operations_coverage);
  assert.equal(loaded.freshness,'stale');
});
