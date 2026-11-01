/* Generated-document integration with a synthetic DOM, not a browser claim. */
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {execFileSync}=require('node:child_process');

for(const [initialFragment,interaction] of [['',''],['#flow',''],['#flow','wheel'],['#flow','navigation']])test('actual generated scripts settle '+(initialFragment||'home')+' / '+(interaction||'untouched'),async()=>{
 const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'blitzwerk-static-test-'));
 try{
  const output=path.join(temporary,'site');
  execFileSync(process.env.PYTHON||'python3',['build_static.py','--output',output]);
  const html=fs.readFileSync(path.join(output,'index.html'),'utf8');
  const elements=new Map();
  function element(id=''){
   let text='',inner='';const attributes=new Map(),listeners={};
   return {id,hidden:false,dataset:{page:'home'},style:{},listeners,attributes,value:'',classList:{toggle(){},add(){},remove(){}},
    get textContent(){return text},set textContent(value){text=String(value);inner=text.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')},
    get innerHTML(){return inner},set innerHTML(value){inner=value},
    addEventListener(type,fn){listeners[type]=fn},setAttribute(k,v){attributes.set(k,String(v))},getAttribute:k=>attributes.get(k),focus(){},querySelector:()=>({style:{}}),parentElement:{querySelector:()=>({style:{}})}};
  }
  for(const match of html.matchAll(/\bid="([^"]+)"/g))elements.set(match[1],element(match[1]));
  const sections=[...html.matchAll(/<section[^>]*\bid="([^"]+)"/g)].map(m=>elements.get(m[1]));
  const intervals=[],requests=[],frames=new Map(),documentListeners={},windowListeners={},scrolls=[],motionPreference={matches:false,listener:null,addEventListener(type,fn){this.listener=fn}};let frameID=0;
  class ObservedDate extends Date{static now(){return Date.parse('2026-11-01T02:00:00Z')}}
  const context={Date:ObservedDate,Intl,TextDecoder,Uint8Array,AbortController,performance,
   setTimeout,clearTimeout,setInterval:(callback,ms)=>intervals.push({callback,ms}),location:{hash:initialFragment},scrollY:0,addEventListener:(type,fn)=>windowListeners[type]=fn,scrollTo(value){scrolls.push(value);context.scrollY=value.top},
   requestAnimationFrame:fn=>{const id=++frameID;frames.set(id,fn);return id},cancelAnimationFrame:id=>frames.delete(id),matchMedia:()=>motionPreference,
   fetch:async(url,options)=>{requests.push({url,options});throw Error('synthetic offline')},
   document:{readyState:'loading',hidden:false,addEventListener:(type,fn)=>documentListeners[type]=fn,getElementById:id=>{assert.ok(elements.has(id),id);return elements.get(id)},
    createElement:()=>element(),querySelectorAll:selector=>selector==='main > section'?sections:[],body:element()}};
  context.window=context;vm.createContext(context);
  for(const [,script] of html.matchAll(/<script>([\s\S]*?)<\/script>/g))vm.runInContext(script,context,{timeout:1000});
  if(initialFragment){assert.equal(typeof windowListeners.load,'function');if(interaction==='wheel')windowListeners.wheel();if(interaction==='navigation')vm.runInContext("showPage('#team')",context);context.scrollY=301;windowListeners.load();}
  await context.BLITZWERK_STATIC.load();await new Promise(resolve=>setImmediate(resolve));
  if(initialFragment){assert.equal(context.scrollY,interaction?301:0,'restore after initial render only if user has not navigated or interacted');assert.equal(scrolls.at(-1).behavior,'instant');}
  assert.equal(elements.get('freshness').textContent,'STALE');
  assert.equal(elements.get('offline-warning').hidden,false);
  assert.match(elements.get('offline-warning').textContent,/last verified snapshot/);
  assert.match(elements.get('snapshot-time').textContent,/Oct 31/);
  assert.equal((elements.get('employees').innerHTML.match(/class="employee"/g)||[]).length,15);
  assert.equal((elements.get('traders').innerHTML.match(/class="trader"/g)||[]).length,3);
  assert.match(elements.get('workflow-runs').innerHTML,/runtime-graph/);
  assert.match(elements.get('incident-list').innerHTML,/component:ops-monitor:cpu_budget_exhausted/);
  assert.match(elements.get('sug-connection').textContent,/unverified/);
  assert.equal(requests.length,2);assert.ok(requests.every(x=>x.url.startsWith('https://raw.githubusercontent.com/FussballSug/blitzwerk-quant-site/refs/heads/status-data/')));
  assert.deepEqual(intervals.map(x=>x.ms),[1000,30000]);
  assert.equal(frames.size,initialFragment&&interaction!=='navigation'?1:0,'only active flow may animate');
  vm.runInContext("showPage('#activity')",context,{timeout:1000});
  assert.equal(elements.get('activity').hidden,false);
  assert.equal((elements.get('activity-workers').innerHTML.match(/class="activity-worker"/g)||[]).length,15);
  assert.match(elements.get('activity-asof').textContent,/STALE REPORT/);
  elements.get('activity-worker').listeners.change({target:{value:'sug'}});
  assert.equal((elements.get('activity-workers').innerHTML.match(/class="activity-worker"/g)||[]).length,1);
  assert.match(elements.get('activity-workers').innerHTML,/No verified hourly accomplishment/);
  vm.runInContext("showPage('#flow')",context,{timeout:1000});
  assert.equal(elements.get('flow').hidden,false);assert.equal(frames.size,1);
  assert.match(elements.get('flow-asof').textContent,/PAPER \/ SIMULATED.*Current engine state is unknown/);
  motionPreference.matches=true;motionPreference.listener();assert.equal(frames.size,0);assert.equal(elements.get('flow-play').disabled,true);
  motionPreference.matches=false;motionPreference.listener();assert.equal(frames.size,1);
  elements.get('flow-node-schneider').listeners.keydown({key:'Enter',preventDefault(){}});
  assert.match(elements.get('flow-role-name').textContent,/Anna Schneider/);
  elements.get('flow-node-weber').listeners.click();
  assert.match(elements.get('flow-role-name').textContent,/Friedrich Weber/);
  assert.match(elements.get('flow-role-details').innerHTML,/Owner \/ CEO/);
  elements.get('flow-mode').listeners.change({target:{value:'verified'}});
  assert.equal(frames.size,0);assert.match(elements.get('flow-proof-state').textContent,/STALE.*no verified transfer/);
  elements.get('flow-mode').listeners.change({target:{value:'conceptual'}});assert.equal(frames.size,1);
  context.document.hidden=true;documentListeners.visibilitychange();assert.equal(frames.size,0);
  context.document.hidden=false;documentListeners.visibilitychange();assert.equal(frames.size,1);
  vm.runInContext("showPage('#team')",context,{timeout:1000});
  assert.equal(frames.size,0);
  assert.equal(elements.get('team').hidden,false);assert.ok(sections.filter(x=>x.id!=='team').every(x=>x.hidden));
 }finally{fs.rmSync(temporary,{recursive:true,force:true});}
});
