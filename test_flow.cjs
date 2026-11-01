const test=require('node:test'),assert=require('node:assert/strict');
const {createFlowMotion,verifiedFlowEvents}=require('./assets/team_flow.js');
function setup(){
 let next=0;const queued=new Map(),cancelled=[],frames=[];
 const motion=createFlowMotion({request:fn=>{const id=++next;queued.set(id,fn);return id},cancel:id=>{cancelled.push(id);queued.delete(id)},draw:frame=>frames.push(frame)});
 return {motion,queued,cancelled,frames,tick(t){const [id,fn]=queued.entries().next().value;queued.delete(id);fn(t)}};
}
test('no animation is scheduled while the tab is hidden',()=>{
 const s=setup();assert.equal(s.queued.size,0);s.motion.setVisible(false);assert.equal(s.queued.size,0);
 s.motion.setVisible(true);assert.equal(s.queued.size,1);s.motion.setVisible(true);assert.equal(s.queued.size,1);
 s.motion.setVisible(false);assert.equal(s.queued.size,0);
});
test('document hiding, pause and reduced motion cancel the single pending frame',()=>{
 for(const stop of [m=>m.setDocumentVisible(false),m=>m.setPlaying(false),m=>m.setReducedMotion(true)]){
  const s=setup();s.motion.setVisible(true);stop(s.motion);assert.equal(s.queued.size,0);
 }
});
test('verified mode cannot animate conceptual transfers',()=>{
 const s=setup();s.motion.setVisible(true);s.motion.setMode('verified');assert.equal(s.queued.size,0);
 s.motion.setPlaying(true);assert.equal(s.queued.size,0);
 s.motion.setMode('conceptual');assert.equal(s.queued.size,1);
});
test('frames are rate bounded and particle count never exceeds24',()=>{
 const s=setup();s.motion.setRoutes(Array.from({length:50},(_,i)=>({id:String(i),x1:0,y1:0,x2:100,y2:100})));
 s.motion.setVisible(true);s.tick(0);s.tick(10);s.tick(20);s.tick(34);
 assert.equal(s.frames.length,2);assert.ok(s.frames.every(f=>f.particles.length<=24));
 assert.equal(s.queued.size,1);
});
test('speed clamps invalid or excessive values and disposal ends scheduling',()=>{
 const s=setup();s.motion.setSpeed(999);assert.equal(s.motion.state().speed,1.5);
 s.motion.setSpeed(NaN);assert.equal(s.motion.state().speed,1);
 s.motion.setVisible(true);s.motion.dispose();assert.equal(s.queued.size,0);
 s.motion.setVisible(true);assert.equal(s.queued.size,0);
});
test('stale references are historical observations, not actual handoff events',()=>{
 const value=verifiedFlowEvents({snapshot_at:'2026-11-01T00:00:00Z',freshness:'stale',employees:[{employee_id:'hoffmann',last_useful_result:'a'.repeat(64),updated_at:1}],workflows:[{history:[{node:'authorized_promotion',outcome:'passed',at:1}]}]});
 assert.deepEqual(value.transfers,[]);assert.equal(value.transfer_evidence_available,false);
 assert.equal(value.freshness,'stale');assert.equal(value.observations.length,1);
});
test('verified result references require a real nonfuture observation within the report',()=>{
 const at=Date.parse('2026-11-01T00:00:00Z')/1000;
 const rows=[0,null,at+1].map((updated_at,i)=>({employee_id:'worker'+i,last_useful_result:'a'.repeat(64),updated_at}));
 const value=verifiedFlowEvents({snapshot_at:'2026-11-01T00:00:00Z',freshness:'stale',employees:rows},(at+10)*1000);
 assert.deepEqual(value.observations,[]);
 const future=verifiedFlowEvents({snapshot_at:'2026-11-01T00:00:00Z',freshness:'current',employees:[{employee_id:'sug',last_useful_result:'a'.repeat(64),updated_at:at}]},(at-10)*1000);
 assert.deepEqual(future.observations,[]);assert.equal(future.freshness,'unverified');
});
