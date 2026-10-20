// Synthetic data only. No real pilot judgments are written by these tests.
const assert = require('node:assert/strict');
const R = require('../validation/proquest_review/review.js');
const pack = {pack_id:'synthetic-only',rubric:'test',records:[{audit_id:'SYNTHETIC:1'}]};
const t0='2026-10-19T12:00:00.000Z', t1='2026-10-19T12:01:00.000Z', t2='2026-10-19T12:02:00.000Z';
let state=R.blank(pack), rec=R.record(state,'SYNTHETIC:1',t0);
assert.throws(()=>R.reveal(rec,t1),/Lock/);
assert.throws(()=>R.lock(rec,t1),/Required/);
rec.draft=Object.fromEntries(R.fields.map(k=>[k, R.enums[k]?.[0]||'synthetic evidence']));
R.lock(rec,t1);const locked=JSON.stringify(rec.first_pass);
assert.equal(rec.first_pass.elapsed_seconds,60);assert.throws(()=>R.lock(rec,t2),/already/);
assert.throws(()=>R.finish(rec,{},t2),/Reveal/);
R.reveal(rec,t2);
const comparisons=Object.fromEntries(R.finalFields.map(k=>[k,R.finalEnums[k]?.[0]||'synthetic note']));
R.finish(rec,comparisons,t2);assert.equal(JSON.stringify(rec.first_pass),locked);
assert.deepEqual(R.validate(JSON.parse(JSON.stringify(state)),pack),state);
for(const change of [s=>s.pack_id='wrong',s=>s.records['other']={},s=>s.records['SYNTHETIC:1'].first_pass.answers.realized='rise',
 s=>s.records['SYNTHETIC:1'].revealed_at=t0,s=>s.records['SYNTHETIC:1'].first_pass.elapsed_seconds=0,
 s=>delete s.records['SYNTHETIC:1'].first_pass,s=>s.records['SYNTHETIC:1'].comparison.answers.direction='invented']){
 const bad=structuredClone(state);change(bad);assert.throws(()=>R.validate(bad,pack));
}
state=R.blank(pack);rec=R.record(state,'SYNTHETIC:1',t0);
rec.draft={reviewer:'Synthetic',mapping_status:'unavailable',mapping_reason:'No source supplied',blinding:'unknown'};
R.lock(rec,t1);R.validate(state,pack);assert.throws(()=>R.reveal(rec,t2),/uniquely mapped/);
console.log('PASS: blind gating, immutable first pass, round trip, invalid imports, unresolved mapping');
