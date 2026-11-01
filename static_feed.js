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
 // Pure SHA-256 over canonical ASCII JSON; no async/network dependency.
 function sha256(text){
  const bytes=new TextEncoder().encode(text),length=bytes.length,padded=new Uint8Array(Math.ceil((length+9)/64)*64);padded.set(bytes);padded[length]=128;
  const view=new DataView(padded.buffer);view.setUint32(padded.length-4,length*8);view.setUint32(padded.length-8,Math.floor(length/536870912));
  const h=[],k=[];for(let n=2;k.length<64;n++){let prime=true;for(let d=2;d*d<=n;d++)if(n%d===0){prime=false;break;}if(prime){if(h.length<8)h.push((Math.sqrt(n)%1*4294967296)|0);k.push((Math.cbrt(n)%1*4294967296)|0);}}
  const ro=(v,n)=>(v>>>n)|(v<<(32-n)),w=new Int32Array(64);
  for(let start=0;start<padded.length;start+=64){for(let i=0;i<16;i++)w[i]=view.getInt32(start+i*4);for(let i=16;i<64;i++){const a=w[i-15],b=w[i-2];w[i]=(w[i-16]+(ro(a,7)^ro(a,18)^(a>>>3))+w[i-7]+(ro(b,17)^ro(b,19)^(b>>>10)))|0;}
   let [a,b,c,d,e,f,g,z]=h;for(let i=0;i<64;i++){const t1=(z+(ro(e,6)^ro(e,11)^ro(e,25))+((e&f)^(~e&g))+k[i]+w[i])|0,t2=((ro(a,2)^ro(a,13)^ro(a,22))+((a&b)^(a&c)^(b&c)))|0;z=g;g=f;f=e;e=(d+t1)|0;d=c;c=b;b=a;a=(t1+t2)|0;}[a,b,c,d,e,f,g,z].forEach((v,i)=>h[i]=(h[i]+v)|0);
  }return h.map(v=>(v>>>0).toString(16).padStart(8,'0')).join('');
 }
 const asciiJSON=v=>stable(v).replace(/[\u007f-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));
 function validateActivity(v,at=null){
  const A=S.ACTIVITY,keys=(o,k)=>object(o)&&equal(Object.keys(o).sort(),k.slice().sort());
  const time=x=>{require(typeof x==='string'&&/^(?:19[7-9]\d|[2-9]\d{3})-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)$/.test(x));return timestamp(x);};
  const hour=t=>Math.floor(t/3600000000)*3600000000;
  const id=x=>sha256(asciiJSON(x)),sameId=e=>{const copy={...e};delete copy.event_id;return digest(e.event_id)&&id(copy)===e.event_id;};
  require(keys(v,A.ACTIVITY_KEYS)&&v.schema_version===1&&v.scope==='public_activity_projection');
  const first=time(v.window_from),last=time(v.window_until),collected=time(v.collected_at);
  require(first===hour(last)-23*3600000000&&first<=last&&last===collected&&(at===null||collected<=at));
  require(member(v.coverage,['complete_query','partial','unavailable'])&&typeof v.truncated==='boolean'&&Array.isArray(v.hours)&&Array.isArray(v.events)&&v.hours.length<=24&&v.hours.length+v.events.length<=48);
  if(v.coverage==='unavailable')require(v.hours.length===0&&v.events.length===0);else if(!v.truncated)require(v.hours.length===24);
  const seenHours=new Set();let previous=Infinity,total=0;
  for(const row of v.hours){require(keys(row,['hour_start','evidence_reference',...A.COUNTS]));const t=time(row.hour_start);require(t>=first&&t<=last&&hour(t)===t&&!seenHours.has(t)&&t<previous&&digest(row.evidence_reference));seenHours.add(t);previous=t;
   for(const key of A.COUNTS){require(Array.isArray(row[key])&&row[key].length===15&&row[key].every(n=>Number.isInteger(n)&&n>=0&&n<=512));if(key!=='no_change')total+=row[key].reduce((a,b)=>a+b,0);}
   require(row.no_change.every((n,i)=>n<=row.results[i]+row.controller_results[i]));
  }require(total<=512);
  const seen=new Set();let previousEvent=null;
  for(const e of v.events){require(keys(e,A.EVENT_KEYS)&&sameId(e)&&!seen.has(e.event_id));seen.add(e.event_id);
   require(own(A.KINDS,e.kind)&&own(A.KINDS[e.kind],e.stage));const worker=e.employee_id,basis=e.attribution_basis;
   require(worker===null||member(worker,A.WORKERS));
   if(e.kind==='review')require(worker===null&&basis==='unknown'&&(e.subject_employee_id===null||member(e.subject_employee_id,A.WORKERS)));
   else {require(e.subject_employee_id===null);require(worker===null?basis===(e.kind==='engineering'?'unknown':'historical_role_unmapped'):basis===(e.kind==='controller_result'?'controller_responsibility':'assigned_role'));}
   const historical=worker===null&&['result','controller_result'].includes(e.kind);
   require(historical?e.stage==='recorded'&&e.summary_code==='historical_'+e.kind+'_recorded':e.summary_code===A.KINDS[e.kind][e.stage]||e.kind==='controller_result'&&e.stage==='recorded'&&member(e.summary_code,A.CONTROLLER_SUMMARIES));
   const t=time(e.observed_at);require(t>=first&&t<=last&&seenHours.has(hour(t))&&/\+00:00$/.test(e.observed_at));
   const fraction=e.observed_at.match(/\.(\d+)/);require(!fraction||fraction[1].length===6&&fraction[1]!=='000000');
   require(previousEvent===null||previousEvent.t>t||previousEvent.t===t&&previousEvent.id>e.event_id);previousEvent={t,id:e.event_id};
   for(const key of ['task_reference','result_reference','evidence_reference'])require(digest(e[key]));require(e.source_revision===null||digest(e.source_revision,40));
   if(e.kind==='engineering'){
    require(worker===null&&basis==='unknown');
    require(digest(e.source_revision,40)&&own(A.CHANGES,e.change_code)&&member(e.repository_code,['platform','website']));
    if(e.repository_code==='platform')require(e.public_reference===null&&e.stage==='pushed'&&e.release_target==='branch');
    else {require(typeof e.public_reference==='string'&&e.public_reference.length<=200);require(e.stage==='pushed'?e.public_reference==='https://github.com/FussballSug/blitzwerk-quant-site/commit/'+e.source_revision&&member(e.release_target,['branch','default_branch']):/^https:\/\/github\.com\/FussballSug\/blitzwerk-quant-site\/actions\/runs\/[1-9][0-9]{0,19}$/.test(e.public_reference)&&e.release_target==='website');}
   }else require(e.public_reference===null&&e.change_code===null&&e.repository_code===null&&e.release_target===null);
  }
  for(const row of v.hours){const start=time(row.hour_start),items=v.events.filter(e=>hour(time(e.observed_at))===start),counts=Object.fromEntries(A.COUNTS.map(k=>[k,Array(15).fill(0)]));
   for(const e of items){const worker=e.kind==='review'?e.subject_employee_id:e.employee_id;if(worker===null)continue;const i=A.WORKERS.indexOf(worker),key={result:'results',controller_result:'controller_results',review:'reviews_received'}[e.kind];if(key)counts[key][i]++;if(e.stage==='no_change')counts.no_change[i]++;}
   for(const key of A.COUNTS)require(row[key].every((n,i)=>v.truncated?n>=counts[key][i]:n===counts[key][i]));
   if(!v.truncated)require(row.evidence_reference===id(items.map(e=>e.event_id).sort()));
  }require(asciiJSON(v).length<=24576);return clone(v);
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
 function validateOperationsCoverage(value){
  const c=value.operations_coverage,kinds=['trading','improvement','incident','publishing'];
  const count=n=>typeof n==='number'&&Number.isInteger(n)&&n>=0&&n<=1000000000;
  const keys=(v,expected)=>object(v)&&equal(Object.keys(v).sort(),expected.slice().sort());
  require(keys(c,['schema_version','scope','selection','source_counts','queried_counts','displayed_counts','workflow_kinds','history_counts','artifact_reference_counts','query_truncated','display_truncated','partial']));
  require(c.schema_version===1&&c.scope==='bounded_public_operations'&&c.selection==='latest_per_kind_then_recent');
  for(const name of ['source_counts','queried_counts','displayed_counts'])require(keys(c[name],['workflows','incidents']));
  require(keys(c.workflow_kinds,kinds));
  let unknown=false,queryOmission=false,displayOmission=false,sourceSum=0,allSources=true;
  const bound=(source,queried,displayed)=>{
   require((source===null||count(source))&&count(queried)&&count(displayed)&&displayed<=queried&&(source===null||queried<=source));
   unknown ||= source===null;queryOmission ||= source!==null&&queried<source;displayOmission ||= displayed<queried;
  };
  for(const key of ['workflows','incidents']){bound(c.source_counts[key],c.queried_counts[key],c.displayed_counts[key]);require(c.queried_counts[key]<=1000);}
  require(c.displayed_counts.workflows===value.workflows.length&&c.displayed_counts.incidents===value.incidents.length);
  let queriedSum=0,displayedSum=0;
  for(const kind of kinds){
   const row=c.workflow_kinds[kind];require(keys(row,['source','queried','displayed']));bound(row.source,row.queried,row.displayed);
   require(row.displayed===value.workflows.filter(w=>w.kind===kind).length);
   if(row.source===null)allSources=false;else sourceSum+=row.source;
   queriedSum+=row.queried;displayedSum+=row.displayed;
  }
  require(queriedSum<=c.queried_counts.workflows&&displayedSum===c.displayed_counts.workflows);
  if(c.source_counts.workflows!==null)require(sourceSum<=c.source_counts.workflows&&(!allSources||sourceSum===c.source_counts.workflows));
  for(const [field,array] of [['history_counts','history'],['artifact_reference_counts','artifact_digests']]){
   const row=c[field];require(keys(row,['queried','displayed'])&&count(row.queried)&&count(row.displayed)&&row.displayed<=row.queried);
   require(row.displayed===value.workflows.reduce((n,w)=>n+w[array].length,0));displayOmission ||= row.displayed<row.queried;
  }
  for(const flag of ['query_truncated','display_truncated','partial'])require(typeof c[flag]==='boolean');
  require((!queryOmission||c.query_truncated)&&c.display_truncated===displayOmission&&c.partial===(unknown||c.query_truncated||c.display_truncated));
 }
 function validate(value){
  require(object(value)&&[2,3,4].includes(value.schema_version)&&equal(Object.keys(value).sort(),(value.schema_version===4?[...S.PUBLIC_KEYS,'activity','operations_coverage']:value.schema_version===3?[...S.PUBLIC_KEYS,'activity']:S.PUBLIC_KEYS).slice().sort()));
  if(value.schema_version>=3){validateActivity(value.activity);require(asciiJSON(value).length<=MAX);}
  require(member(value.freshness,['current','stale','unverified'])&&value.mode==='paper research'&&member(value.desk_state,['status unavailable','status delayed','monitoring','operational','attention','stopped for review','waiting']));
  require(value.freshness==='unverified'||value.snapshot_at!==null);require(value.desk_state!=='operational'||value.freshness==='current');
  if(value.snapshot_at!==null)timestamp(value.snapshot_at);
  const normalized=normalize(value);let expected=traders(normalized.employees);
  const legacy=Array.isArray(value.traders)&&value.traders.length===3&&value.traders.every(row=>object(row)&&equal(Object.keys(row).sort(),S.LEGACY_TRADER_KEYS.slice().sort()));
  if(legacy){const added=[...Object.keys(S.unknown).filter(k=>!['strategy_version','performance'].includes(k)),'runtime_freshness','runtime_basis','runtime_evidence_as_of','runtime_due_at','last_task_reference'];require(value.employees.every(row=>object(row)&&added.every(k=>!own(row,k))));expected=expected.map(row=>Object.fromEntries(S.LEGACY_TRADER_KEYS.map(k=>[k,row[k]])));for(const row of normalized.employees)for(const k of added)delete row[k];}
  for(const k of Object.keys(normalized))require(equal(value[k],normalized[k]));
  require(equal(value.traders,expected)&&equal(value.stages,S.stages)&&equal(value.reporting,{coordinator:'Sug',delivery_connection:'unverified'}));
  if(value.schema_version===4)validateOperationsCoverage(value);
  return clone(value);
 }
 function refresh(value,failed=false){
  if(value.schema_version>=3)validateActivity(value.activity,Math.round(now()*1000));
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
    if(value.schema_version>=3)validateActivity(value.activity,Math.round(now()*1000));
    require(t!==null&&t<=Math.round(now()*1000)&&(old===null||t>=old));if(i===0)require(Math.floor(t/3600000000)===Math.floor(start/3600000));
    if(cache.schema_version>=3)require(value.schema_version>=cache.schema_version&&timestamp(value.activity.collected_at)>=timestamp(cache.activity.collected_at));
    cache=value;return refresh(cache,i!==0);
   }catch{}
  }try{return refresh(cache,true);}catch(error){
   // A backward local clock must not leave an old green render on screen.
   // Keep cached bytes; omit future activity only from this failed view.
   if(cache.schema_version<3)throw error;
   const base=clone(cache);delete base.activity;delete base.operations_coverage;base.schema_version=2;return refresh(base,true);
  }}finally{clearTimer(timer);}
 }
 function load(){if(!pending)pending=run().finally(()=>{pending=null;});return pending;}
 return Object.freeze({validate,refresh,load});
}
if(typeof module!=='undefined'&&module.exports)module.exports={createStaticReader};
