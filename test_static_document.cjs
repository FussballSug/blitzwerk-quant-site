/* Generated-document integration with a synthetic DOM, not a browser claim. */
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {execFileSync}=require('node:child_process');

test('actual generated scripts render offline snapshot, roster, traders, graphs and navigation',async()=>{
 const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'blitzwerk-static-test-'));
 try{
  const output=path.join(temporary,'site');
  execFileSync(process.env.PYTHON||'python3',['build_static.py','--output',output]);
  const html=fs.readFileSync(path.join(output,'index.html'),'utf8');
  const elements=new Map();
  function element(id=''){
   let text='',inner='';
   return {id,hidden:false,dataset:{page:'home'},style:{},classList:{toggle(){},add(){},remove(){}},
    get textContent(){return text},set textContent(value){text=String(value);inner=text.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')},
    get innerHTML(){return inner},set innerHTML(value){inner=value},
    addEventListener(){},querySelector:()=>({style:{}}),parentElement:{querySelector:()=>({style:{}})}};
  }
  for(const match of html.matchAll(/\bid="([^"]+)"/g))elements.set(match[1],element(match[1]));
  const sections=[...html.matchAll(/<section[^>]*\bid="([^"]+)"/g)].map(m=>elements.get(m[1]));
  const intervals=[],requests=[];
  class ObservedDate extends Date{static now(){return Date.parse('2026-10-31T23:00:00Z')}}
  const context={Date:ObservedDate,Intl,TextDecoder,Uint8Array,AbortController,performance,
   setTimeout,clearTimeout,setInterval:(callback,ms)=>intervals.push({callback,ms}),scrollTo(){},
   fetch:async(url,options)=>{requests.push({url,options});throw Error('synthetic offline')},
   document:{getElementById:id=>{assert.ok(elements.has(id),id);return elements.get(id)},
    createElement:()=>element(),querySelectorAll:selector=>selector==='main > section'?sections:[],body:element()}};
  context.window=context;vm.createContext(context);
  for(const [,script] of html.matchAll(/<script>([\s\S]*?)<\/script>/g))vm.runInContext(script,context,{timeout:1000});
  await context.BLITZWERK_STATIC.load();await new Promise(resolve=>setImmediate(resolve));
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
  vm.runInContext("showPage('#team')",context,{timeout:1000});
  assert.equal(elements.get('team').hidden,false);assert.ok(sections.filter(x=>x.id!=='team').every(x=>x.hidden));
 }finally{fs.rmSync(temporary,{recursive:true,force:true});}
});
