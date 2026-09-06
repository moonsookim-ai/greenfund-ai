import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
const read=path=>readFileSync(new URL('../greenproof/web/nepal/'+path,import.meta.url),'utf8');
const data=JSON.parse(read('data/responder-briefing.json'));
const analysis=JSON.parse(read('data/source-analyses.json'));

test('responder facts have known sources and operational unknowns never become available assets',()=>{
  const ids=new Set(data.sources.map(s=>s.id));
  assert.ok(data.audience.includes('한국 구조대원'));
  for(const region of data.regions){
    assert.ok(region.unknown&&region.implication&&region.counterpart);
    for(const fact of region.facts)assert.ok(ids.has(fact.source));
  }
  for(const hospital of data.medical){assert.ok(ids.has(hospital.source));assert.equal(hospital.capacity,null);assert.ok(hospital.english&&hospital.place);}
  assert.ok(data.operationalUnknowns.some(s=>s.includes('한국 구조대')));
  assert.ok(data.operationalUnknowns.some(s=>s.includes('병상')));
  for(const source of data.sources)assert.ok(source.url.startsWith('https://')&&source.locator);
});

test('primary pages provide Korean responder information without an intake form',()=>{
  for(const path of ['index.html','field/index.html']){
    const html=read(path);
    assert.ok(html.includes('<html lang="ko">'));
    assert.ok(html.includes('한국 구조대원'));
    assert.ok(!/<(?:div|section)\b[^>]*\bdata-field-tool/.test(html));
    assert.ok(!html.includes('먼저 신고하세요'));
    for(const key of ['responder-safety','medical-brief','emergency-contacts'])assert.ok(html.includes(`id="${key}"`));
    for(const number of ['1234','1115','+97715370172'])assert.ok(html.includes(`tel:${number}`));
  }
  assert.ok(read('handoff/index.html').includes('data-field-tool'));
});

test('both published briefs retain the same regional evidence and no invented medical capacity',()=>{
  for(const file of ['index.html','field/index.html']){
    const html=read(file);
    for(const region of data.regions)for(const fact of region.facts)assert.ok(html.includes(fact.text));
    for(const hospital of data.medical)assert.ok(html.includes(hospital.english));
    assert.ok(html.includes('현재 수용'));
    assert.ok(html.includes('보고서의 진료 인원이나 퇴원 수를 남은 병상 수로 계산하지 않습니다.'));
    assert.equal((html.match(/data-brief-region=/g)||[]).length,3);
  }
});

test('all source references resolve to Korean analyses available in both saved and main pages',()=>{
  const ids=new Set(analysis.articles.map(a=>a.id));
  assert.equal(ids.size,analysis.articles.length);
  const covered=new Set(analysis.articles.flatMap(a=>a.sourceIds));
  for(const s of data.sources)assert.ok(covered.has(s.id),s.id+' lacks Korean analysis');
  for(const a of analysis.articles){
    assert.ok(a.facts.length&&a.meaning&&a.limits);
    for(const id of a.sourceIds)assert.ok(data.sources.some(s=>s.id===id));
  }
  const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#x27;');
  for(const file of ['index.html','field/index.html']){
    const html=read(file);
    assert.ok(html.includes('id="project-preface"'));
    assert.ok(html.includes(analysis.preface.body));
    for(const a of analysis.articles){
      assert.ok(html.includes(`id="analysis-${a.id}"`));
      for(const fact of a.facts)assert.ok(html.includes(escape(fact)));
      assert.ok(html.includes(escape(a.limits)));
    }
    for(const match of html.matchAll(/href="#analysis-([^"]+)"/g))assert.ok(ids.has(match[1]));
    for(const match of html.matchAll(/<a\b[^>]*class="brief-source"[^>]*>/g)){
      assert.match(match[0],/href="#analysis-/);
      assert.ok(!match[0].includes('target='));
    }
  }
  const texas=analysis.articles.find(a=>a.id==='texas');
  assert.ok(texas.limits.includes('독립 검증된 구조 성과'));
  assert.ok(texas.sourceIds.includes('palantir-texas'));
  assert.ok(analysis.articles.find(a=>a.id==='roads').limits.includes('구조차 예외'));
});

test('source links reveal filtered or collapsed analysis; printing restores the prior reading state',()=>{
  const events={};
  const element=(props={})=>Object.assign({hidden:false,open:false,listeners:{},addEventListener(type,fn){this.listeners[type]=fn;},querySelector(){return {focus(){}};}},props);
  const panels=[element({id:'analysis-heoc',textContent:'병원 의료'}),element({id:'analysis-texas',textContent:'텍사스 공동 상황판'})];
  const nested=element();
  const search=element({value:''}),status=element(),expand=element(),collapse=element();
  const document={
    querySelectorAll(s){return ({'[data-brief-region]':[],'[data-brief-filter]':[],'[data-print-brief]':[],'[data-source-analysis]':panels,'[data-analysis-expand]':[expand],'[data-analysis-collapse]':[collapse],'details':[...panels,nested]})[s]||[];},
    querySelector(s){return ({'#analysis-search':search,'[data-analysis-status]':status})[s]||null;},
    addEventListener(type,fn){events['document:'+type]=fn;}
  };
  const window={location:{hash:'#analysis-texas'},addEventListener(type,fn){events[type]=fn;}};
  runInNewContext(read('briefing.mjs'),{document,window});
  assert.equal(panels[1].open,true,'direct fragment reveals its analysis');
  search.value='병원';search.listeners.input();
  assert.equal(panels[1].hidden,true);
  collapse.listeners.click();
  events['document:click']({target:{closest(){return {getAttribute(){return '#analysis-texas';}};}}});
  assert.equal(panels[1].hidden,false);
  assert.equal(panels[1].open,true);
  assert.equal(search.value,'');
  search.value='병원';search.listeners.input();
  expand.listeners.click();
  const before=panels.map(p=>[p.open,p.hidden]);
  events.beforeprint();events.beforeprint();
  assert.ok(panels.every(p=>p.open&&!p.hidden));assert.equal(nested.open,true);
  events.afterprint();
  assert.deepEqual(panels.map(p=>[p.open,p.hidden]),before);
  assert.equal(nested.open,false);
  search.value='없는 검색어';search.listeners.input();
  assert.ok(status.textContent.startsWith('0개'));
});
