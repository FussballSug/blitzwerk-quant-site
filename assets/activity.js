/* Presentation only. Snapshot references are not completion or push attestations. */
function createActivityModel(catalog){
 const owns=(value,key)=>Object.prototype.hasOwnProperty.call(value,key);
 const digest=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
 const titles={static_public_report:'Static public reporting',hourly_activity_view:'Hourly activity and worker evidence',reporting_reliability:'Reporting reliability',bounded_performance:'Measured engineering performance',evidence_validation:'Evidence validation'};
 function instant(value){
  const n=typeof value==='number'?value*1000:typeof value==='string'?Date.parse(value):NaN;
  return Number.isFinite(n)&&n>0?n:null;
 }
 function hourKey(value){const n=instant(value);return n===null?null:new Date(Math.floor(n/3600000)*3600000).toISOString().replace('.000Z','Z');}
 function displayTime(value,zone='America/Chicago'){
  const n=instant(value);if(n===null)return 'Not supplied';
  return new Intl.DateTimeFormat('en-US',{timeZone:zone==='UTC'?'UTC':'America/Chicago',year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',timeZoneName:'short'}).format(new Date(n));
 }
 function hourLabel(key,zone='America/Chicago'){
  return `${displayTime(key,zone)} · ${key.slice(0,16)}Z`;
 }
 function build(snapshot,ledger,now=Date.now()){
  const at=instant(snapshot.snapshot_at),validAt=at!==null&&at<=now;
  const freshness=!validAt?'unverified':snapshot.freshness!=='current'||now-at>600000?'stale':'current';
  const events=[],workers=Object.values(catalog).map(row=>({...row}));
  if(validAt)events.push({id:'report:'+snapshot.snapshot_at,kind:'report',stage:'observed',at:snapshot.snapshot_at,hour:hourKey(snapshot.snapshot_at),worker_id:null,summary:'Public report observed. Current operational freshness is assessed separately.',receipt:null,release:null,link:null});
  for(const row of Array.isArray(snapshot.employees)?snapshot.employees:[]){
   const t=instant(row.updated_at);
   if(!validAt||!owns(catalog,row.employee_id)||t===null||t>at||!digest(row.last_useful_result))continue;
   events.push({id:'worker:'+row.employee_id+':'+row.last_useful_result+':'+t,kind:'worker',stage:'recorded_reference',at:new Date(t).toISOString(),hour:hourKey(row.updated_at),worker_id:row.employee_id,summary:'Result reference recorded; accomplishment details and completion time are not supplied.',receipt:row.last_useful_result,release:null,link:null,task:row.last_task_reference||row.current_task||null});
  }
  for(const run of Array.isArray(snapshot.workflows)?snapshot.workflows:[]){
   for(const [i,event] of (Array.isArray(run.history)?run.history:[]).entries()){
    const t=instant(event.at);if(!validAt||t===null||t>at)continue;
    events.push({id:'workflow:'+run.run_id+':'+i,kind:'workflow',stage:'checkpoint_'+event.outcome,at:new Date(t).toISOString(),hour:hourKey(event.at),worker_id:null,summary:`${run.kind} / ${String(event.node).replaceAll('_',' ')}: ${event.outcome}. Git push and deployment are not established by a workflow checkpoint.`,receipt:null,release:null,link:null,run:run.run_id,run_receipts:(run.artifact_digests||[]).filter(digest).slice(0,5)});
   }
  }
  const reviewed=instant(ledger?.reviewed_at);
  if(reviewed!==null&&reviewed<=now)for(const event of ledger.events||[]){
   const t=instant(event.observed_at);if(t===null||t>reviewed||!owns(titles,event.change))continue;
   events.push({id:'engineering:'+event.event_id,kind:'engineering',stage:event.stage,at:event.observed_at,hour:hourKey(event.observed_at),worker_id:event.worker_id,summary:titles[event.change],receipt:event.receipt_sha256,release:event.source_revision,link:event.reference_url,deployment_url:event.deployment_url});
  }
  events.sort((a,b)=>instant(b.at)-instant(a.at)||a.id.localeCompare(b.id));
  return {snapshot_at:validAt?snapshot.snapshot_at:null,freshness,workers,events,hours:[...new Set(events.map(e=>e.hour))].sort().reverse(),ledger_reviewed_at:reviewed!==null&&reviewed<=now?ledger.reviewed_at:null};
 }
 function filter(value,worker='all',hour='all'){
  return value.events.filter(e=>(worker==='all'||worker==='unassigned'&&e.worker_id===null||e.worker_id===worker)&&(hour==='all'||e.hour===hour));
 }
 function workerRows(value,worker='all',hour='all'){
  return value.workers.filter(row=>worker==='all'||row.employee_id===worker).map(row=>({...row,evidence:filter(value,row.employee_id,hour).find(e=>e.kind==='worker')||null}));
 }
 return Object.freeze({hourKey,hourLabel,displayTime,build,filter,workerRows});
}
if(typeof module!=='undefined'&&module.exports)module.exports={createActivityModel};
