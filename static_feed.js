/* Read-only static mirror. No credentials, storage, writer, or keepalive.
 * Constants come from the existing Python public validator during the build.
 * Unknown/extra fields must fail normalization equality before any rendering.
 */
function createStaticReader({schema:S,initial,fetch:request=globalThis.fetch,now=Date.now,
  monotonic=()=>performance.now(),setTimer=setTimeout,clearTimer=clearTimeout}){
 const BASE='https://raw.githubusercontent.com/FussballSug/blitzwerk-quant-site/refs/heads/status-data/';
 const MAX=65536, DEADLINE=5000;
 const clone=v=>JSON.parse(JSON.stringify(v));
 const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
 const own=(v,k)=>object(v)&&Object.hasOwn(v,k);
 const member=(v,items)=>typeof v==='string'&&items.includes(v);
 const epoch=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0?v:null;
 const token=v=>typeof v==='string'&&/^[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,159}$/.test(v)?v:null;
 const digest=(v,n=64)=>typeof v==='string'&&new RegExp(`^[a-f0-9]{${n}}$`).test(v)?v:null;
 const rows=(v,n=200)=>Array.isArray(v)?v.slice(0,n):[];
 const stable=v=>JSON.stringify(v,(_,x)=>object(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,x[k]])):x);
 const equal=(a,b)=>stable(a)===stable(b);
 const require=(condition)=>{if(!condition)throw Error('Invalid public snapshot');};
 function timestamp(v){
  require(typeof v==='string'&&/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:\d\d)$/.test(v));
  const p=v.slice(0,19).split(/[-T:]/).map(Number),d=new Date(0);d.setUTCFullYear(p[0],p[1]-1,p[2]);d.setUTCHours(p[3],p[4],p[5],0);
  require(d.getUTCFullYear()===p[0]&&d.getUTCMonth()===p[1]-1&&d.getUTCDate()===p[2]&&p[3]<24&&p[4]<60&&p[5]<60);
  const t=Date.parse(v),fraction=(v.match(/\.(\d+)/)?.[1]||'').padEnd(6,'0');
  require(Number.isFinite(t));
  // Integer microseconds preserve the existing exact600-second boundary.
  return t*1000+Number(fraction.slice(3));
 }
 function amount(v,nonnegative=false){
  if(v===null||v===undefined)return null;
  require(typeof v==='string'&&v.length<=64&&/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:E[+-]\d+)?$/.test(v));
  const [mant,exponent='0']=v.replace(/^-/,'').split('E'),[integer,fraction='']=mant.split('.');
  const significant=(integer+fraction).replace(/^0+/,'');
  const adjusted=Number(exponent)-fraction.length+(significant.length?significant.length-1:0);
  require(Number.isFinite(Number(v))&&Math.abs(adjusted)<=12&&(!nonnegative||Number(v)>=0));
  const digits=significant||'0',power=Number(exponent)-fraction.length,sign=v.startsWith('-')?'-':'';
  if(power>0||adjusted<-6)return sign+digits[0]+(digits.length>1?'.'+digits.slice(1):'')+'E'+(adjusted>=0?'+':'')+adjusted;
  if(power===0)return sign+digits;
  const point=digits.length+power;
  return sign+(point>0?digits.slice(0,point)+'.'+digits.slice(point):'0.'+'0'.repeat(-point)+digits);
 }
 function evidence(row,at){
  const out=clone(S.unknown),t=epoch(row.strategy_evidence_as_of);
  if(member(row.strategy_evidence_state,['stale','missing_data']))out.strategy_evidence_state=row.strategy_evidence_state;
  if(t!==null&&at!==null&&t<=at&&at-t>60)out.strategy_evidence_state='stale';
  if(row.strategy_evidence_state!=='current'||t===null||(at!==null&&(t>at||at-t>60))||row.worker_connection_verified!==false||row.execution_basis!=='recorded_evaluation_receipt')return out;
  const versions=Object.fromEntries(['strategy_version','configured_strategy_version','executed_strategy_version','manifest_sha256','strategy_evidence_reference','mandate_reference'].map(k=>[k,digest(row[k])]));
  const sources=Object.fromEntries(['configured_source_revision','executed_source_revision'].map(k=>[k,digest(row[k],40)]));
  if(Object.values({...versions,...sources}).some(v=>v===null)||versions.strategy_version!==versions.executed_strategy_version)return out;
  Object.assign(out,versions,sources,{strategy_evidence_state:'current',strategy_evidence_as_of:t,execution_basis:'recorded_evaluation_receipt',worker_connection_verified:false});
  for(const k of ['approved_universe_reference','risk_policy_reference'])out[k]=digest(row[k]);
  const pt=epoch(row.performance_as_of),basis=row.performance_basis,ref=digest(row.performance_reference),values=row.performance;
  if(pt===null||(at!==null&&(pt>at||at-pt>60))||!member(basis,['paper_local_virtual_cost_v1','broker_reported_accounting'])||ref===null||!object(values)||!equal(Object.keys(values).sort(),S.METRICS.slice().sort()))return out;
  const metrics={};for(const k of S.METRICS){try{metrics[k]=k==='sample_size'?(Number.isInteger(values[k])&&values[k]>=0&&values[k]<=1000000?values[k]:null):amount(values[k],['drawdown','exposure','fees'].includes(k));}catch{metrics[k]=null;}}
  const fees=member(row.fees_basis,['unknown','broker_observed','assumed_virtual_friction'])?row.fees_basis:'unknown';
  if(basis!=='broker_reported_accounting'||fees!=='broker_observed')metrics.fees=null;
  let costs=null;try{costs=amount(row.assumed_costs,true);}catch{}
  return Object.assign(out,{performance:metrics,performance_basis:basis,performance_as_of:pt,performance_reference:ref,assumed_costs:costs,fees_basis:fees});
 }
 function runtime(item,row,at){
  let basis=member(row.runtime_basis,S.RUNTIME_BASES)?row.runtime_basis:'responsibility_record_only';
  let fresh=member(row.runtime_freshness,['current','stale','unverified'])?row.runtime_freshness:'unverified';
  const t=epoch(row.runtime_evidence_as_of),due=epoch(row.runtime_due_at),task=token(row.last_task_reference);
  if(at!==null&&[item.heartbeat,item.updated_at,t].some(v=>v!==null&&v>at)){item.state='stale';fresh='unverified';basis='future_clock';}
  else if(item.state==='running'){fresh='unverified';basis='recorded_heartbeat_not_worker_attestation';if(at!==null&&item.heartbeat!==null&&at-item.heartbeat>60)item.state='stale';}
  else if(basis==='controller_handled_responsibility'&&fresh==='current'){
   if(t===null||task===null)fresh='unverified';
   else if(at!==null&&due!==null&&at>=due){item.state='stale';fresh='stale';basis='scheduled_task_overdue';}
   else if(at!==null&&at-t>45){item.state='stale';fresh='stale';basis='controller_heartbeat_overdue';}
  }else if(at!==null&&item.heartbeat!==null&&at-item.heartbeat>60&&['health_check','startup'].includes(item.next_trigger)){item.state='stale';fresh='stale';basis='expected_heartbeat_overdue';}
  else if(fresh==='current')fresh='unverified';
  Object.assign(item,{runtime_freshness:fresh,runtime_basis:basis,runtime_evidence_as_of:t,runtime_due_at:due,last_task_reference:task});
 }
 function normalize(value,at=null){
  const out={employees:[],workflows:[],incidents:[],improvements:[]},seen=new Set();
  for(const row of rows(value.employees,15)){
   if(!object(row))continue;const id=['alexandar','alexander'].includes(row.employee_id)?'sug':row.employee_id;
   if(!own(S.CATALOG,id)||seen.has(id))continue;seen.add(id);const item=clone(S.CATALOG[id]);
   let state=member(row.state,[...S.STATES,'unverified'])?row.state:'planned';
   const hb=epoch(row.heartbeat),task=token(row.current_task);if(state==='running'&&(hb===null||task===null))state='unverified';
   Object.assign(item,{state,current_task:task,last_useful_result:digest(row.last_useful_result),next_trigger:member(row.next_trigger,S.TRIGGERS)?row.next_trigger:null,heartbeat:hb,blocker:member(row.blocker,S.BLOCKERS)?row.blocker:null,updated_at:epoch(row.updated_at)},evidence(row,at));
   runtime(item,row,at);out.employees.push(item);
  }
  for(const row of rows(value.workflows)){
   if(!object(row)||!own(S.GRAPHS,row.kind))continue;const kind=row.kind;
   const observer=row.version===2&&row.mode==='source_receipt_observation'&&row.execution_authorized===false&&own(S.OBSERVATION_GRAPHS,kind);
   const recovery=row.version===3&&kind==='incident'&&row.mode==='finite_stopped_startup_recovery'&&row.execution_authorized===false;
   const canary=row.version===3&&kind==='improvement'&&row.mode==='finite_closed_session_canary'&&row.execution_authorized===false;
   const nodes=observer?S.OBSERVATION_GRAPHS[kind]:S.GRAPHS[kind];
   if(!token(row.run_id)||!member(row.node,nodes)||!member(row.status,S.GRAPH_STATES)||!(row.version===1||observer||recovery||canary))continue;
   const item=Object.fromEntries(['run_id','kind','version','status','node'].map(k=>[k,row[k]]));
   Object.assign(item,{updated_at:epoch(row.updated_at),deadline_at:epoch(row.deadline_at),artifact_digests:rows(row.artifact_digests,100).filter(x=>digest(x)),history:rows(row.history,100).filter(e=>object(e)&&member(e.node,nodes)&&member(e.outcome,S.OUTCOMES)&&epoch(e.at)!==null).map(e=>({node:e.node,outcome:e.outcome,at:e.at}))});
   if(observer){let t=epoch(row.evidence_as_of),fresh=member(row.current_evidence,['current','stale','unverified'])?row.current_evidence:'unverified';if(t===null||(at!==null&&t>at)){t=null;fresh='unverified';}else if(at!==null)fresh=at-t>(kind==='trading'?60:600)?'stale':'current';Object.assign(item,{mode:'source_receipt_observation',execution_authorized:false,evidence_as_of:t,current_evidence:fresh});}
   else if(recovery||canary)Object.assign(item,{mode:row.mode,execution_authorized:false});
   out.workflows.push(item);
  }
  out.improvements=out.workflows.filter(row=>row.kind==='improvement').map(clone);
  for(const row of rows(value.incidents)){
   if(!object(row)||!token(row.incident_id)||!member(row.state,['open','resolved']))continue;
   const owner=['alexandar','alexander'].includes(row.owner)?'sug':row.owner;
   out.incidents.push({incident_id:row.incident_id,state:row.state,owner:own(S.CATALOG,owner)?owner:null,first_seen:epoch(row.first_seen),last_seen:epoch(row.last_seen),reason:member(row.reason,S.REASONS)?row.reason:'evidence_private'});
  }return out;
 }
 function traders(employees){const byId=new Map(employees.map(x=>[x.employee_id,x]));return S.TRADERS.map(row=>{const employee=byId.get(row.employee_id)||{};return {...row,state:employee.state||'unverified',approved_universe:employee.approved_universe??null,...Object.fromEntries(Object.entries(S.unknown).map(([k,v])=>[k,employee[k]===undefined?v:employee[k]]))};});}
 function validate(value){
  require(object(value)&&equal(Object.keys(value).sort(),S.PUBLIC_KEYS.slice().sort())&&value.schema_version===2);
  require(member(value.freshness,['current','stale','unverified'])&&value.mode==='paper research'&&member(value.desk_state,['status unavailable','status delayed','monitoring','operational','attention','stopped for review','waiting']));
  require(value.freshness==='unverified'||value.snapshot_at!==null);require(value.desk_state!=='operational'||value.freshness==='current');
  if(value.snapshot_at!==null)timestamp(value.snapshot_at);
  const normalized=normalize(value);let expected=traders(normalized.employees);
  const legacy=Array.isArray(value.traders)&&value.traders.length===3&&value.traders.every(row=>object(row)&&equal(Object.keys(row).sort(),S.LEGACY_TRADER_KEYS.slice().sort()));
  if(legacy){const added=[...Object.keys(S.unknown).filter(k=>!['strategy_version','performance'].includes(k)),'runtime_freshness','runtime_basis','runtime_evidence_as_of','runtime_due_at','last_task_reference'];require(value.employees.every(row=>object(row)&&added.every(k=>!own(row,k))));expected=expected.map(row=>Object.fromEntries(S.LEGACY_TRADER_KEYS.map(k=>[k,row[k]])));for(const row of normalized.employees)for(const k of added)delete row[k];}
  for(const k of Object.keys(normalized))require(equal(value[k],normalized[k]));
  require(equal(value.traders,expected)&&equal(value.stages,S.stages)&&equal(value.reporting,{coordinator:'Sug',delivery_connection:'unverified'}));
  return clone(value);
 }
 function refresh(value,failed=false){
  const out=validate(value),t=out.snapshot_at===null?null:timestamp(out.snapshot_at),age=t===null?null:Math.round(now()*1000)-t;
  if(age!==null&&age<0){out.freshness='unverified';out.desk_state='status unavailable';}
  else if(failed||(age!==null&&age>600000000)){out.freshness=t===null?'unverified':'stale';out.desk_state=t===null?'status unavailable':'status delayed';}
  Object.assign(out,normalize(out,now()/1000));out.traders=traders(out.employees);return out;
 }
 let cache=validate(initial),pending=null;
 async function bounded(url,end,signal){
  const response=await request(url,{credentials:'omit',redirect:'error',cache:'no-store',signal});
  require(monotonic()<end&&response.ok&&!response.redirected);
  const length=response.headers.get('content-length');require(length===null||(/^\d+$/.test(length)&&Number(length)<=MAX));
  require(response.body&&typeof response.body.getReader==='function');const reader=response.body.getReader();let size=0,chunks=[];
  try{for(;;){require(monotonic()<end&&!signal.aborted);const {done,value}=await reader.read();require(monotonic()<end&&!signal.aborted);if(done)break;size+=value.byteLength;require(size<=MAX);chunks.push(value);}}
  finally{await reader.cancel().catch(()=>{});reader.releaseLock();}
  const bytes=new Uint8Array(size);let pos=0;for(const chunk of chunks){bytes.set(chunk,pos);pos+=chunk.byteLength;}
  return validate(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes)));
 }
 async function run(){
  const start=now(),end=monotonic()+DEADLINE,controller=new AbortController(),timer=setTimer(()=>controller.abort(),DEADLINE);
  const slot=new Date(start).toISOString().slice(0,13).replace(/[-T:]/g,'');
  const current=BASE+'slots/'+slot.slice(0,8)+'T'+slot.slice(8)+'00Z.json';
  try{for(const [i,url] of [current,BASE+'latest.json'].entries()){
   if(monotonic()>=end||controller.signal.aborted)break;
   try{const value=await bounded(url,end,controller.signal),t=value.snapshot_at===null?null:timestamp(value.snapshot_at),old=cache.snapshot_at===null?null:timestamp(cache.snapshot_at);
    require(t!==null&&t<=Math.round(now()*1000)&&(old===null||t>=old));if(i===0)require(Math.floor(t/3600000000)===Math.floor(start/3600000));
    cache=value;return refresh(cache,i!==0);
   }catch{}
  }return refresh(cache,true);}finally{clearTimer(timer);}
 }
 function load(){if(!pending)pending=run().finally(()=>{pending=null;});return pending;}
 return Object.freeze({validate,refresh,load});
}
if(typeof module!=='undefined'&&module.exports)module.exports={createStaticReader};
