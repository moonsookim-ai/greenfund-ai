import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=path=>readFileSync(new URL('../greenproof/web/nepal/'+path,import.meta.url),'utf8');
const data=JSON.parse(read('data/responder-briefing.json'));

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
