/* Pure evidence and DST tests; no browser/network/worker activity fabricated. */
const test=require('node:test'),assert=require('node:assert/strict');
const {createActivityModel}=require(require('node:fs').existsSync('./assets/activity.js')?'./assets/activity.js':'./activity_assets/activity.js');
const catalog={hoffmann:{employee_id:'hoffmann',name:'Stefan Hoffmann'},sug:{employee_id:'sug',name:'Sug'}};
const model=createActivityModel(catalog);
const snapshot=()=>({snapshot_at:'2026-11-01T07:05:00Z',freshness:'stale',employees:[],workflows:[]});
const empty={schema_version:1,scope:'reviewed_public_activity',reviewed_at:'2026-11-01T08:00:00Z',events:[]};
const now=Date.parse('2026-11-01T09:00:00Z');

test('DST repeated Chicago hours keep distinct UTC keys and offsets',()=>{
 const early=model.hourKey('2026-11-01T06:30:00Z'),late=model.hourKey('2026-11-01T07:30:00Z');
 assert.notEqual(early,late);
 assert.match(model.hourLabel(early,'America/Chicago'),/CDT/);
 assert.match(model.hourLabel(late,'America/Chicago'),/CST/);
 assert.match(model.hourLabel(early,'America/Chicago'),/06:00/);
 assert.match(model.hourLabel(late,'America/Chicago'),/07:00/);
});
test('each defined worker remains visible when accomplishments are absent',()=>{
 const value=model.build(snapshot(),empty,now);
 assert.equal(model.workerRows(value,'all','all').length,2);
 assert.ok(model.workerRows(value,'all','all').every(r=>r.evidence===null));
 assert.equal(value.freshness,'stale');
 assert.equal(value.events.filter(e=>e.kind==='engineering').length,0);
});
test('worker reference is a recorded observation, never an inferred completion or push',()=>{
 const data=snapshot();data.employees=[{employee_id:'hoffmann',updated_at:Date.parse('2026-11-01T06:30:00Z')/1000,last_useful_result:'a'.repeat(64),state:'waiting'}];
 const value=model.build(data,empty,now),event=value.events.find(e=>e.kind==='worker');
 assert.equal(event.stage,'recorded_reference');assert.equal(event.worker_id,'hoffmann');
 assert.match(event.summary,/not supplied/);assert.equal(event.release,null);
 assert.equal(model.filter(value,'sug','all').length,0);
 assert.equal(model.workerRows(value,'hoffmann','2026-11-01T07:00:00Z')[0].evidence,null);
});
test('zero/future/invalid worker evidence is not backfilled into an hour',()=>{
 for(const at of [0,NaN,Date.parse('2026-11-01T08:00:00Z')/1000]){
  const data=snapshot();data.employees=[{employee_id:'hoffmann',updated_at:at,last_useful_result:'a'.repeat(64)}];
  assert.equal(model.build(data,empty,now).events.filter(e=>e.kind==='worker').length,0);
 }
});
test('workflow promotion never claims an actual git push or deployment',()=>{
 const data=snapshot();data.workflows=[{kind:'improvement',run_id:'synthetic',node:'authorized_promotion',status:'completed',artifact_digests:['b'.repeat(64)],history:[{node:'authorized_promotion',outcome:'passed',at:Date.parse('2026-11-01T06:30:00Z')/1000}]}];
 const value=model.build(data,empty,now),event=value.events.find(e=>e.kind==='workflow');
 assert.equal(event.worker_id,null);assert.equal(event.stage,'checkpoint_passed');
 assert.match(event.summary,/push.*not established/i);
 assert.equal(event.release,null);assert.equal(value.events.filter(e=>e.stage==='pushed'||e.stage==='deployed').length,0);
});
test('explicit reviewed engineering stages stay separate and support worker/hour filters',()=>{
 const ledger=structuredClone(empty);ledger.events=['proposed','validated','pushed','deployed','no_change'].map((stage,i)=>({event_id:'event-'+i,observed_at:'2026-11-01T06:30:00Z',worker_id:i===0?'hoffmann':null,change:'static_public_report',stage,source_revision:'a'.repeat(40),receipt_sha256:'b'.repeat(64),reference_url:null,deployment_url:null}));
 const value=model.build(snapshot(),ledger,now);
 assert.deepEqual(value.events.filter(e=>e.kind==='engineering').map(e=>e.stage).sort(),['deployed','no_change','proposed','pushed','validated']);
 assert.equal(model.filter(value,'hoffmann','2026-11-01T06:00:00Z').length,1);
 assert.equal(model.filter(value,'unassigned','2026-11-01T06:00:00Z').length,4);
 assert.equal(model.filter(value,'all','2026-11-01T07:00:00Z').length,1);
});
test('missing hour is a gap rather than no-change or a new successful update',()=>{
 const value=model.build(snapshot(),empty,now);
 assert.equal(model.filter(value,'all','2026-11-01T05:00:00Z').length,0);
 assert.ok(model.workerRows(value,'all','2026-11-01T05:00:00Z').every(r=>r.evidence===null));
 assert.equal(value.events.filter(e=>e.stage==='no_change').length,0);
});
test('future report and future ledger observations do not become verified events',()=>{
 const data=snapshot();data.snapshot_at='2027-01-01T00:00:00Z';
 const value=model.build(data,{...empty,reviewed_at:'2027-01-01T00:00:00Z'},now);
 assert.equal(value.freshness,'unverified');assert.equal(value.events.length,0);
});

test('rolling history is independent of old health and reviews received are not worker execution',()=>{
 const data=snapshot();data.schema_version=3;
 data.activity={collected_at:'2026-11-01T08:30:00+00:00',coverage:'complete_query',truncated:false,
 hours:[{hour_start:'2026-11-01T08:00:00+00:00',results:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],controller_results:[0,0,1,0,0,0,0,0,0,0,0,0,0,0,0],reviews_received:[0,0,1,0,0,0,0,0,0,0,0,0,0,0,0],no_change:Array(15).fill(0)}],
 events:[{event_id:'a'.repeat(64),kind:'review',employee_id:null,subject_employee_id:'hoffmann',observed_at:'2026-11-01T08:10:00+00:00',stage:'accepted',summary_code:'review_accepted',evidence_reference:'b'.repeat(64),source_revision:null,public_reference:null},
 {event_id:'c'.repeat(64),kind:'controller_result',employee_id:'hoffmann',subject_employee_id:null,observed_at:'2026-11-01T08:05:00+00:00',stage:'recorded',summary_code:'incident_diagnosis_recorded',evidence_reference:'d'.repeat(64),source_revision:null,public_reference:null}]};
 const value=model.build(data,empty,now),row=model.workerRows(value,'hoffmann','2026-11-01T08:00:00Z')[0];
 assert.equal(value.freshness,'stale');assert.equal(value.activity_collected_at,data.activity.collected_at);
 assert.equal(row.counts.results,0);assert.equal(row.counts.controller_results,1);assert.equal(row.counts.reviews_received,1);assert.equal(row.evidence,null);
 const review=model.filter(value,'hoffmann','all').find(e=>e.kind==='review');assert.equal(review.worker_id,null);assert.equal(review.subject_id,'hoffmann');
 assert.match(review.summary,/review.*accepted/i);assert.equal(value.partial_hour,'2026-11-01T08:00:00Z');
});
test('private platform push has meaningful note but no invented public link or adoption',()=>{
 const data=snapshot();data.schema_version=3;data.activity={collected_at:'2026-11-01T08:30:00Z',coverage:'partial',truncated:true,hours:[],events:[{event_id:'a'.repeat(64),kind:'engineering',employee_id:null,subject_employee_id:null,observed_at:'2026-11-01T08:20:00Z',stage:'pushed',change_code:'reporting_reliability',repository_code:'platform',release_target:'branch',evidence_reference:'b'.repeat(64),source_revision:'c'.repeat(40),public_reference:null}]};
 const value=model.build(data,empty,now),event=value.events.find(e=>e.kind==='engineering');
 assert.equal(event.link,null);assert.equal(event.worker_id,null);assert.match(event.summary,/reporting reliability/i);assert.equal(event.release_target,'branch');assert.equal(event.stage,'pushed');
 assert.equal(value.coverage,'partial');assert.equal(value.truncated,true);
});
