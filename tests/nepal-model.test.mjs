import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {FIELDS, assess, evaluateRegions, sensitivity, normaliseWeights, PRESETS} from '../greenproof/web/nepal/model.mjs';

// Invented fixtures are used only in tests. They are never published as Nepal data.
const household = {affected:100,severe:30,needs:80,served:20,vulnerable:40};
const row = (id,inputs=household) => ({id,name:id,inputs:{...inputs}});
const reviewed = id => ({...row(id),review:{approved:true,asOf:'2026-09-05',cohort:'same assessment protocol'},inputSources:Object.fromEntries(FIELDS.map(f=>[f,'verified field ledger, row 1']))});
const close = (actual,expected)=>assert.ok(Math.abs(actual-expected)<1e-9,`${actual} != ${expected}`);

test('known calculation preserves denominator definitions and score contributions',()=>{
  const r=assess(household);
  assert.equal(r.status,'ready');assert.equal(r.unmet,60);
  assert.deepEqual(r.components,[.3,.75,.5]);close(r.score,155/3);
  close(assess(household,PRESETS.gap).score,57.5);
});
test('missing values do not become zeros or trigger partial scoring',()=>{
  for(const f of FIELDS) for(const missing of [null,undefined,'']){
    const r=assess({...household,[f]:missing},[0,1,0]);
    assert.equal(r.status,'missing');assert.equal(r.score,null);assert.ok(r.missing.includes(f));
  }
  assert.equal(assess({...household,severe:0,vulnerable:0,served:0}).status,'ready');
});
test('invalid inputs and inconsistent household subsets cannot receive scores',()=>{
  for(const bad of [-1,1.5,NaN,Infinity,'10',true,9007199254740992]) assert.equal(assess({...household,affected:bad}).status,'invalid');
  for(const bad of [{severe:101},{needs:101},{served:81},{vulnerable:81}]) assert.equal(assess({...household,...bad}).status,'invalid');
});
test('no WASH need and fully supported households are not in active aid rank',()=>{
  const results=evaluateRegions([row('zero',Object.fromEntries(FIELDS.map(f=>[f,0]))),row('covered',{...household,served:80}),row('active')],PRESETS.balanced,{mode:'scenario'});
  assert.deepEqual(results.map(r=>r.status),['no_need','covered','ready']);
  assert.deepEqual(results.map(r=>r.rank),[null,null,1]);
  assert.equal(results[0].score,null);assert.equal(results[1].score,null);
});
test('weights normalise without changing ratios; invalid totals are rejected',()=>{
  assert.deepEqual(normaliseWeights([10,20,10]),[.25,.5,.25]);
  for(const w of [[0,0,0],[-1,1,1],[NaN,1,1],[1,2],['1',1,1],[1e308,1e308,1e308]]) assert.throws(()=>normaliseWeights(w));
  close(assess(household,[1,2,1]).score,assess(household,[10,20,10]).score);
});
test('scores stay bounded; larger unmet need cannot lower the score',()=>{
  let previous=Infinity;
  for(let served=0;served<=79;served++){
    const r=assess({...household,served});
    assert.ok(r.score>=0&&r.score<=100);assert.ok(r.score<=previous);previous=r.score;
  }
  close(assess({affected:10,severe:10,needs:10,served:0,vulnerable:10}).score,100);
});
test('rank ties use competition ranks and exclude incomplete regions',()=>{
  const results=evaluateRegions([row('a'),row('b'),row('c',{...household,severe:0}),row('missing',{})],PRESETS.balanced,{mode:'scenario'});
  assert.deepEqual(results.map(r=>r.rank),[1,1,3,null]);
  assert.throws(()=>evaluateRegions([row('a'),row('a')]));
});
test('complete but unreviewed public inputs do not become official results',()=>{
  assert.equal(evaluateRegions([row('a')])[0].status,'review_needed');
  assert.equal(evaluateRegions([reviewed('a')])[0].rank,1);
  for(const review of [{approved:'true'},{cohort:' '},{asOf:'2026-02-31'},{asOf:'yesterday'}]){
    const r=reviewed('a');Object.assign(r.review,review);assert.equal(evaluateRegions([r])[0].score,null);
  }
  const r=reviewed('a');delete r.inputSources.served;assert.equal(evaluateRegions([r])[0].rank,null);
});
test('public comparisons require one common date and cohort definition',()=>{
  for(const key of ['asOf','cohort']){
    const a=reviewed('a'),b=reviewed('b');b.review[key]=key==='asOf'?'2026-09-04':'different scope';
    assert.deepEqual(evaluateRegions([a,b]).map(r=>r.status),['incomparable','incomparable']);
  }
});
test('sensitivity reveals policy-dependent reversals without inventing confidence intervals',()=>{
  const a=row('a',{affected:100,severe:100,needs:100,served:80,vulnerable:0});
  const b=row('b',{affected:100,severe:0,needs:100,served:0,vulnerable:20});
  assert.equal(evaluateRegions([a,b],PRESETS.damage,{mode:'scenario'})[0].rank,1);
  assert.equal(evaluateRegions([a,b],PRESETS.gap,{mode:'scenario'})[0].rank,2);
  const ranges=sensitivity([a,b,row('unknown',{})],{mode:'scenario'});
  assert.deepEqual(ranges,[{id:'a',best:1,worst:2},{id:'b',best:1,worst:2},{id:'unknown',best:null,worst:null}]);
});
test('published snapshot keeps all unknown inputs null and links evidence to registered primary sources',async()=>{
  const data=JSON.parse(await readFile(new URL('../greenproof/web/nepal/data/snapshot.json',import.meta.url),'utf8'));
  assert.equal(data.asOf,'2026-09-05');assert.equal(data.regions.length,6);
  const ids=new Set(data.sources.map(s=>s.id));assert.equal(ids.size,data.sources.length);
  for(const r of data.regions){assert.deepEqual(Object.keys(r.inputs),FIELDS);for(const f of FIELDS) assert.equal(r.inputs[f],null);r.evidence.forEach(e=>assert.ok(ids.has(e.source)));}
  data.context.forEach(c=>assert.ok(ids.has(c.source)));
  evaluateRegions(data.regions).forEach(r=>{assert.equal(r.status,'missing');assert.equal(r.rank,null);assert.equal(r.score,null);});
});
