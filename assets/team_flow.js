/* Finite illustrative animation. No network, persistence or execution controls. */
function createFlowMotion({request,cancel,draw}){
 const state={visible:false,documentVisible:true,playing:true,reduced:false,mode:'conceptual',speed:1};
 let pending=null,disposed=false,last=null,drawn=null,phase=0,routes=[];
 const active=()=>!disposed&&state.visible&&state.documentVisible&&state.playing&&!state.reduced&&state.mode==='conceptual';
 function clear(){draw({particles:[],phase});}
 function sync(){
  if(active()){if(pending===null){last=null;drawn=null;pending=request(frame);}}
  else{if(pending!==null)cancel(pending);pending=null;last=null;drawn=null;clear();}
 }
 function frame(now){
  pending=null;if(!active())return;
  if(last!==null)phase=(phase+Math.min(.1,Math.max(0,(now-last)/1000))*.13*state.speed)%1;
  last=now;
  if(drawn===null||now-drawn>=1000/30){
   drawn=now;const particles=[];
   for(const [i,route] of routes.entries())for(let j=0;j<2;j++){
    const t=(phase+j*.5+i*.071)%1,u=1-t,m=route.middle??(route.y1+route.y2)/2;
    particles.push({x:u*u*u*route.x1+3*u*u*t*route.x1+3*u*t*t*route.x2+t*t*t*route.x2,y:u*u*u*route.y1+3*u*u*t*m+3*u*t*t*m+t*t*t*route.y2,kind:route.kind||'reporting',opacity:Math.min(1,t*8,(1-t)*8)});
   }
   draw({particles,phase});
  }
  if(active())pending=request(frame);
 }
 return Object.freeze({setVisible(v){state.visible=!!v;sync()},setDocumentVisible(v){state.documentVisible=!!v;sync()},setPlaying(v){state.playing=!!v;sync()},setReducedMotion(v){state.reduced=!!v;sync()},setMode(v){state.mode=v==='verified'?'verified':'conceptual';sync()},setSpeed(v){state.speed=Number.isFinite(v)?Math.min(1.5,Math.max(.5,v)):1},setRoutes(v){routes=v.slice(0,12)},state:()=>({...state}),dispose(){disposed=true;sync()}});
}
function verifiedFlowEvents(snapshot,now=Date.now()){
 const rows=Array.isArray(snapshot?.employees)?snapshot.employees:[];
 const at=typeof snapshot?.snapshot_at==='string'?Date.parse(snapshot.snapshot_at):NaN;
 const valid=Number.isFinite(at)&&at>0&&at<=now;
 const freshness=!valid?'unverified':snapshot?.freshness!=='current'||now-at>600000?'stale':'current';
 return {transfers:[],transfer_evidence_available:false,freshness,observations:valid?rows.filter(row=>typeof row.last_useful_result==='string'&&/^[a-f0-9]{64}$/.test(row.last_useful_result)&&typeof row.updated_at==='number'&&Number.isFinite(row.updated_at)&&row.updated_at>0&&row.updated_at*1000<=at).map(row=>({worker_id:row.employee_id,receipt:row.last_useful_result,observed_at:row.updated_at})):[]};
}
function mountTeamFlow(document,environment,scene){
 const el=id=>document.getElementById(id),byId=new Map(scene.nodes.map(n=>[n.id,n]));
 let step=0,selected=null,snapshot={},mode='conceptual';
 const safe=value=>{const span=document.createElement('span');span.textContent=String(value);return span.innerHTML};
 const motion=createFlowMotion({request:fn=>environment.requestAnimationFrame(fn),cancel:id=>environment.cancelAnimationFrame(id),draw:({particles})=>{
  for(let i=0;i<24;i++){const point=particles[i],dot=el('flow-particle-'+i);dot.setAttribute('visibility',point?'visible':'hidden');if(point){dot.setAttribute('transform',`translate(${point.x.toFixed(2)} ${point.y.toFixed(2)})`);dot.setAttribute('opacity',point.opacity.toFixed(2));dot.setAttribute('class','flow-particle '+point.kind);}}
 }});
 const preference=environment.matchMedia?.('(prefers-reduced-motion: reduce)');
 function update(){
  const tour=scene.tours[step],verified=verifiedFlowEvents(snapshot);
  const routes=mode==='verified'?[]:scene.links.filter(e=>selected?(e.source===selected||e.target===selected):tour.kinds.includes(e.kind));
  motion.setRoutes(routes);
  const routeIDs=new Set(routes.map(e=>e.id)),participants=new Set(routes.flatMap(e=>[e.source,e.target]));
  for(const edge of scene.links)el('flow-route-'+edge.id).classList.toggle('active',routeIDs.has(edge.id));
  for(const node of scene.nodes){const target=el('flow-node-'+node.id);target.classList.toggle('selected',node.id===selected);target.classList.toggle('participating',mode==='conceptual'&&participants.has(node.id));target.setAttribute('aria-pressed',String(node.id===selected));}
  el('flow-worker').value=selected||'all';el('flow-mode').value=mode;
  el('flow-step').textContent=`0${step+1} / 0${scene.tours.length}`;
  el('flow-tour-title').textContent=tour.title;el('flow-tour-description').textContent=tour.description;
  el('flow-asof').textContent=`PAPER / SIMULATED · Reported state: ${snapshot.desk_state||'unknown'} · As of ${snapshot.snapshot_at||'not supplied'} · ${verified.freshness.toUpperCase()}. ${verified.freshness==='current'?'This illustration grants no trading permission.':'Current engine state is unknown.'}`;
  el('flow-proof-state').textContent=mode==='conceptual'?'ILLUSTRATION — no observed transfers are implied':`${verified.freshness.toUpperCase()} REPORT — no verified transfer events supplied`;
  el('flow-evidence-gap').textContent=mode==='conceptual'?'Routes show possible evidence handoffs within the defined organization. They do not show live agents, messages or market activity.':'The public feed contains result references and workflow checkpoints, but no receipt binds a transfer’s sender, receiver and time. Animated transfers are therefore unavailable.';
  const n=selected?byId.get(selected):null;
  el('flow-role-name').textContent=n?n.name:'The coordination layer';
  el('flow-role-purpose').textContent=n?n.purpose:'Select any role to trace its defined reporting and conceptual evidence handoffs.';
  const row=n?(snapshot.employees||[]).find(e=>e.employee_id===n.id):null;
  el('flow-role-details').innerHTML=n?`<dl><dt>Reports to</dt><dd>${safe(n.manager==='owner'?'Owner / CEO':byId.get(n.manager)?.name||n.manager)}</dd><dt>Responsibilities</dt><dd>${safe(n.responsibilities.join(', ').replaceAll('_',' '))}</dd><dt>Observed saved state</dt><dd>${safe(row?.state||'No evidence supplied')}</dd><dt>Worker connection</dt><dd>Unverified</dd></dl>`:'<p>Risk and independent validation report to the owner. A review never removes the deterministic risk gate or grants trading authority.</p>';
  const observations=verified.observations.filter(e=>!selected||e.worker_id===selected);
  el('flow-observations').innerHTML=mode==='verified'?(observations.length?observations.slice(0,15).map(e=>`<article><b>${safe(byId.get(e.worker_id)?.name||'Unassigned')}</b><p>Recorded result reference; not a transfer attestation.</p><code>${safe(e.receipt)}</code></article>`).join(''):'<p>No verified worker result references are supplied for this selection.</p>'):routes.slice(0,8).map(e=>`<p><b>${safe(byId.get(e.source)?.name||'Owner')} → ${safe(byId.get(e.target)?.name||'Owner')}</b><br>${safe(e.label)}<br><small>${safe(e.relationship)}</small></p>`).join('');
  const state=motion.state();el('flow-play').textContent=state.playing?'Pause motion':'Play illustration';el('flow-play').disabled=state.reduced||mode==='verified';
  el('flow-motion-note').textContent=state.reduced?'Reduced motion enabled — static map.':'Illustrated motion pauses when this tab or browser page is hidden. Maximum 24 particles / 30 visual updates per second.';
 }
 function select(id){selected=byId.has(id)?id:null;update()}
 el('flow-worker').innerHTML='<option value="all">All roles / guided tour</option>'+scene.nodes.map(n=>`<option value="${safe(n.id)}">${safe(n.name)}</option>`).join('');
 el('flow-worker').addEventListener('change',e=>select(e.target.value));
 el('flow-mode').addEventListener('change',e=>{mode=e.target.value==='verified'?'verified':'conceptual';motion.setMode(mode);update()});
 el('flow-play').addEventListener('click',()=>{motion.setPlaying(!motion.state().playing);update()});
 el('flow-speed').addEventListener('change',e=>motion.setSpeed(Number(e.target.value)));
 for(const [id,delta] of [['flow-prev',-1],['flow-next',1]])el(id).addEventListener('click',()=>{step=(step+delta+scene.tours.length)%scene.tours.length;selected=null;update()});
 for(const [i,node] of scene.nodes.entries()){
  const target=el('flow-node-'+node.id);target.addEventListener('click',()=>select(node.id));
  target.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(node.id)}else if(['ArrowRight','ArrowDown','ArrowLeft','ArrowUp'].includes(e.key)){e.preventDefault();const next=(i+(['ArrowLeft','ArrowUp'].includes(e.key)?-1:1)+scene.nodes.length)%scene.nodes.length;el('flow-node-'+scene.nodes[next].id).focus();select(scene.nodes[next].id)}});
 }
 function reduced(){motion.setReducedMotion(!!preference?.matches);update()}
 preference?.addEventListener?.('change',reduced);
 document.addEventListener('visibilitychange',()=>motion.setDocumentVisible(!document.hidden));
 motion.setDocumentVisible(!document.hidden);reduced();
 return Object.freeze({setVisible:value=>motion.setVisible(value),update(value){snapshot=value;update()},dispose:()=>motion.dispose()});
}
if(typeof module!=='undefined'&&module.exports)module.exports={createFlowMotion,verifiedFlowEvents,mountTeamFlow};
