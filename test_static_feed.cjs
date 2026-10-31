const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {execFileSync} = require('node:child_process');
const {createStaticReader} = require('./static_feed.js');
const schema=JSON.parse(execFileSync(process.env.PYTHON || 'python3',['build_static.py','--schema'],{encoding:'utf8'}));
const original=JSON.parse(fs.readFileSync('assets/snapshot.json','utf8'));
const at=Date.parse(original.snapshot_at);
const copy=x=>JSON.parse(JSON.stringify(x));
const response=value=>new Response(JSON.stringify(value));
function reader(options={}){return createStaticReader({schema,initial:copy(original),now:()=>at+30000,fetch:async()=>response(original),...options});}

test('retains exact valid public feed and static observation timestamp',async()=>{
 const r=reader();assert.deepEqual(r.validate(original),original);
 const value=await r.load();assert.equal(value.snapshot_at,original.snapshot_at);assert.equal(value.freshness,'current');
});
for(const [name,mutate] of Object.entries({
 private_top:v=>v.account_id='synthetic',live_mode:v=>v.mode='live',bool_version:v=>v.schema_version=true,
 forged_route:v=>v.reporting.delivery_connection='verified',catalog_authority:v=>v.employees[0].authority=['trade_live'],
 duplicate_employee:v=>v.employees.push(copy(v.employees[0])),extra_nested:v=>v.employees[0].raw_log='synthetic',
 forged_trader:v=>v.traders[0].performance.realized_pnl='1000',graph_mutation:v=>v.stages[0].state='running',
 nonnumeric_time:v=>v.employees[0].heartbeat='now',invalid_status:v=>v.freshness='online',
 missing_time:v=>v.snapshot_at=null,malformed_time:v=>v.snapshot_at='yesterday',
 }))test('rejects '+name,()=>{const v=copy(original);mutate(v);assert.throws(()=>reader().validate(v));});

test('current hour missing forces latest stale and never writes a new observation',async()=>{
 const urls=[];const r=reader({fetch:async url=>{urls.push(url);return urls.length===1?new Response('',{status:404}):response(original)}});
 const v=await r.load();assert.equal(urls.length,2);assert.match(urls[0],/slots\/[0-9]{8}T[0-9]{4}Z\.json$/);assert.match(urls[1],/latest\.json$/);
 assert.equal(v.freshness,'stale');assert.equal(v.desk_state,'status delayed');assert.equal(v.snapshot_at,original.snapshot_at);
});
test('remote malformed, private or oversized bytes retain valid memory cache but mark stale',async()=>{
 for(const body of ['{',JSON.stringify({...original,secret:'synthetic'}),'x'.repeat(65537)]){
  const r=reader({fetch:async()=>new Response(body)});const v=await r.load();assert.equal(v.freshness,'stale');assert.equal(v.snapshot_at,original.snapshot_at);assert.equal(v.secret,undefined);
 }
});
test('redirect, failed content length and nonstream response fail closed',async()=>{
 for(const fetch of [async()=>({ok:true,redirected:true}),async()=>new Response('{}',{headers:{'Content-Length':'65537'}}),async()=>({ok:true,headers:new Headers(),body:null})]){
  const v=await reader({fetch}).load();assert.equal(v.freshness,'stale');
 }
});
test('future and regression cannot replace known newer data',async()=>{
 const older=copy(original);older.snapshot_at=new Date(at-3600000).toISOString();
 const future=copy(original);future.snapshot_at=new Date(at+3600000).toISOString();
 for(const value of [older,future]){const result=await reader({fetch:async()=>response(value)}).load();assert.equal(result.snapshot_at,original.snapshot_at);assert.equal(result.freshness,'stale');}
});
test('aging keeps600seconds and current cached labels cannot stay green',()=>{
 assert.equal(reader({now:()=>at+600000}).refresh(original).freshness,'current');
 assert.equal(reader({now:()=>at+600001}).refresh(original).freshness,'stale');
 assert.equal(reader({now:()=>at-1}).refresh(original).freshness,'unverified');
});
test('both requests share5seconds and cancellation covers streamed body',async()=>{
 let tick=0,calls=0;const r=reader({monotonic:()=>tick,fetch:async(url,options)=>{
  calls++;assert.equal(options.credentials,'omit');assert.equal(options.redirect,'error');
  tick=5001;return response(original);
 }});const v=await r.load();assert.equal(calls,1);assert.equal(v.freshness,'stale');
});
test('simultaneous view refreshes share one in-flight request',async()=>{
 let finish,calls=0;const r=reader({fetch:()=>{calls++;return new Promise(resolve=>finish=()=>resolve(response(original)))}});
 const a=r.load(),b=r.load();finish();await Promise.all([a,b]);assert.equal(calls,1);
});
test('deadline abort reaches stalled response body and retains cached snapshot',async()=>{
 let trigger,cancelled=false,cleared=false;
 const r=reader({setTimer:callback=>{trigger=callback;return 1},clearTimer:()=>{cleared=true},
  fetch:async(url,{signal})=>({ok:true,headers:new Headers(),body:{getReader:()=>({
   read:()=>new Promise((resolve,reject)=>{signal.addEventListener('abort',()=>reject(Error('aborted')),{once:true});queueMicrotask(trigger)}),
   cancel:async()=>{cancelled=true},releaseLock(){}})}})});
 const value=await r.load();assert.equal(value.freshness,'stale');assert.equal(cancelled,true);assert.equal(cleared,true);
});
test('malformed UTF8 cannot replace the cache',async()=>{
 const value=await reader({fetch:async()=>new Response(new Uint8Array([0xc3,0x28]))}).load();
 assert.equal(value.snapshot_at,original.snapshot_at);assert.equal(value.freshness,'stale');
});
