import {FIELDS, LABELS, PRESETS, assess, evaluateRegions, normaliseWeights, sensitivity} from './model.mjs?v=2';

const $ = s => document.querySelector(s);
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num = (value, digits=0) => value == null ? '—' : value.toLocaleString('ko-KR',{maximumFractionDigits:digits,minimumFractionDigits:digits});
const emptyInputs = () => Object.fromEntries(FIELDS.map(f => [f,null]));
const states = {missing:'입력 대기', invalid:'입력 오류', ready:'계산 가능', covered:'지원 완료', no_need:'필요 가구 없음', review_needed:'근거 검토 필요', incomparable:'비교 기준 불일치'};
const componentNames = ['주거 피해','지원 공백','취약가구'];
let snapshot, rows = [], weights = [...PRESETS.balanced], metadata = null;

function sourceRef(id) {
  const source = snapshot.sources.find(s=>s.id===id);
  return `<a class="source-ref" href="#source-${esc(id)}">[${esc(source.publisher)}]</a>`;
}
function renderFocus() {
  if (!$('#urgent-regions')) return;
  $('#urgent-regions').innerHTML = snapshot.focus.regions.map(f => {
    const region = snapshot.regions.find(r=>r.id===f.id);
    return `<article class="urgent-region" id="urgent-${esc(f.id)}"><div class="urgent-region-top"><h3>${esc(region.name)}</h3><a href="#region-${esc(f.id)}">지역 상세 ↓</a></div><div class="need-tags">${f.needs.map(n=>`<span>${esc(n)}</span>`).join('')}</div><p>${esc(f.summary)} ${f.sources.map(sourceRef).join(' ')}</p><small>${esc(f.action)}</small></article>`;
  }).join('');
}
function renderEvidence() {
  const results = evaluateRegions(snapshot.regions);
  $('#context').innerHTML = snapshot.context.map(c=>`<article class="metric"><div class="label">${esc(c.label)}</div><div class="number"><small>${esc(c.qualifier)}</small> ${num(c.value)}<small> ${esc(c.unit)}</small></div><div class="source">${esc(c.date)} ${sourceRef(c.source)}</div></article>`).join('') + `<article class="metric"><div class="label">지원 순위를 계산할 수 있는 지역</div><div class="number">${results.filter(r=>r.status==='ready').length}<small> / ${results.length}개 지구</small></div><div class="source">지역별 가구 수와 집계 기준 확인이 필요합니다</div></article>`;
  $('#regions').innerHTML = snapshot.regions.map(r=>`<article class="region-card" id="region-${esc(r.id)}"><div class="region-top"><div><h3>${esc(r.name)}</h3><small>${esc(r.nameEn)} · ${esc(r.province)}</small></div><span class="pending">자료 확인 중</span></div><ul>${r.evidence.map(e=>`<li>${esc(e.text)} ${sourceRef(e.source)}</li>`).join('')}</ul><div class="field-task"><b>현장에서 확인할 내용</b>${esc(r.question)}</div><p class="access">접근성 · ${esc(r.access)}</p><button type="button" data-region="${esc(r.id)}">이 지역의 지원 순위 계산해 보기 ↗</button></article>`).join('');
  $('#coverage-rows').innerHTML = snapshot.regions.map(r=>`<tr><th scope="row">${esc(r.name)}</th>${FIELDS.map(f=>`<td class="${r.inputs[f] == null ? 'missing' : ''}" aria-label="${esc(LABELS[f])}: ${r.inputs[f] == null ? '미확인' : num(r.inputs[f])+'가구'}">${num(r.inputs[f])}</td>`).join('')}</tr>`).join('');
  const available = snapshot.regions.reduce((n,r)=>n+FIELDS.filter(f=>r.inputs[f] != null).length,0);
  $('#coverage-total').textContent = `${available} / ${snapshot.regions.length*FIELDS.length}개 항목 확인`;
  $('#source-list').innerHTML = snapshot.sources.map((s,i)=>`<article class="source-item" id="source-${esc(s.id)}"><div class="source-meta">${String(i+1).padStart(2,'0')} / ${esc(s.type)} · ${s.date ? '발표 '+esc(s.date) : '게시일 미표시 · 확인 '+esc(s.retrieved)}</div><h3><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)} ↗</a></h3><p>${esc(s.note)}</p><p>확인 위치: ${esc(s.locator)}</p></article>`).join('');
}
function loadRegion() {
  const row = rows.find(r=>r.id===$('#region-select').value);
  FIELDS.forEach(f=>{$(`#input-${f}`).value = row.inputs[f] ?? '';});
  $('#form-message').textContent = `${row.name} · 가구 수를 입력한 뒤 ‘입력 저장·계산’을 눌러주세요.`;
}
function syncMetadataLock() {
  const hasInputs = rows.some(r=>FIELDS.some(f=>r.inputs[f]!==null));
  ['assessment-date','cohort','package'].forEach(id=>{$(`#${id}`).readOnly=hasInputs;});
  if (!hasInputs) metadata = null;
}
function renderResults() {
  const results = evaluateRegions(rows,weights,{mode:'scenario'});
  const ranges = sensitivity(rows,{mode:'scenario'});
  const ranked = results.filter(r=>r.rank!==null).sort((a,b)=>a.rank-b.rank);
  const complete = results.filter(r=>['ready','covered','no_need'].includes(r.status)).length;
  $('#result-status').textContent = `자료 입력 완료 ${complete} / ${rows.length}개 지역 · 순위 비교 가능 ${ranked.length}개 지역. ${metadata ? `${metadata.asOf} · ${metadata.cohort}. ` : ''}${ranked.length ? '미입력 지역은 비교에 포함되지 않습니다. 저장한 입력값으로 계산했습니다.' : '지역별 가구 수와 공통 집계 기준을 입력하면 계산합니다.'}`;
  $('#result-rows').innerHTML = results.map(r=>{
    const range = ranges.find(x=>x.id===r.id);
    return `<tr><th scope="row">${esc(r.name)}</th><td>${states[r.status]}</td><td>${num(r.score,1)}</td><td>${r.rank==null ? '—' : r.rank+'위'}</td><td>${num(r.unmet)}</td><td>${range.best==null ? '—' : range.best===range.worst ? range.best+'위 (동일)' : range.best+'~'+range.worst+'위'}</td></tr>`;
  }).join('');
  $('#result-chart').innerHTML = ranked.length ? `<div class="chart-legend">${componentNames.map(n=>`<span><i></i>${n} 기여점수</span>`).join('')}<span>막대 전체 길이 = 100점</span></div>`+ranked.map(r=>{
    const contributions = r.components.map((v,i)=>v*r.weights[i]*100);
    const description = `${r.name}: ${num(r.score,1)}점. ${contributions.map((v,i)=>`${componentNames[i]} ${num(v,1)}점`).join(', ')}`;
    return `<div class="chart-row"><span>${esc(r.name)}</span><div class="chart-track" role="img" aria-label="${esc(description)}" title="${esc(description)}">${contributions.map(v=>`<span class="chart-segment" style="width:${v}%"></span>`).join('')}</div><b class="chart-value">${num(r.score,1)}점</b></div>`;
  }).join('') : '';
  $('#download-scenario').disabled = !rows.some(r=>FIELDS.some(f=>r.inputs[f]!==null));
}
function renderWeights() {
  const w = normaliseWeights(weights);
  w.forEach((v,i)=>{$(`#weight-label-${i}`).textContent = `${num(v*100,1)}%`;});
  $('#weight-message').textContent = '세 기준의 비중은 합계 100%로 계산합니다. 균형·지원 공백·주거 피해·취약가구 중시 설정에서 순위가 얼마나 달라지는지도 보여줍니다.';
  renderResults();
}
function initScenario() {
  rows = snapshot.regions.map(r=>({id:r.id,name:r.name,inputs:emptyInputs()}));
  $('#region-select').innerHTML = rows.map(r=>`<option value="${esc(r.id)}">${esc(r.name)} (${esc(snapshot.regions.find(x=>x.id===r.id).nameEn)})</option>`).join('');
  $('#input-fields').innerHTML = FIELDS.map(f=>`<label>${LABELS[f]}<input id="input-${f}" type="number" min="0" max="9007199254740991" step="1" inputmode="numeric" placeholder="미확인" aria-describedby="form-message"></label>`).join('');
  $('#weight-inputs').innerHTML = componentNames.map((name,i)=>`<div class="weight-row"><label for="weight-${i}">${name}<span id="weight-label-${i}"></span></label><input id="weight-${i}" type="range" min="0" max="10" step="1" value="1"></div>`).join('');
  $('#region-select').addEventListener('change',loadRegion);
  $('#regions').addEventListener('click',event=>{
    const button = event.target.closest('[data-region]');
    if (!button) return;
    $('#region-select').value = button.dataset.region; loadRegion();
    $('#simulator').scrollIntoView(); $('#region-select').focus({preventScroll:true});
  });
  $('#scenario-form').addEventListener('submit',event=>{
    event.preventDefault();
    const inputs = Object.fromEntries(FIELDS.map(f=>[f,$(`#input-${f}`).value==='' ? null : $(`#input-${f}`).valueAsNumber]));
    const result = assess(inputs,weights);
    if (result.errors.length) { $('#form-message').textContent = result.errors.join(' '); return; }
    const cohort = $('#cohort').value.trim(), supportPackage = $('#package').value.trim();
    if (!cohort || !supportPackage) {$('#form-message').textContent='조사한 지역과 대상, 지원 완료로 보는 기준을 입력하세요.';return;}
    const row = rows.find(r=>r.id===$('#region-select').value);
    row.inputs = inputs;
    metadata = {asOf:$('#assessment-date').value,cohort,supportPackage};
    syncMetadataLock(); renderResults();
    $('#form-message').textContent = result.status==='missing' ? `${row.name} 입력을 저장했습니다. ${result.missing.length}개 항목이 아직 확인되지 않아 점수를 계산하지 않았습니다.` : `${row.name} 입력을 저장했습니다. ${states[result.status]}. 공통 집계 기준을 바꾸려면 전체 초기화를 사용하세요.`;
  });
  $('#scenario-form').addEventListener('input',event=>{if(event.target.id.startsWith('input-')) $('#form-message').textContent='아직 저장하지 않은 입력입니다. ‘입력 저장·계산’을 눌러 결과에 반영하세요.';});
  $('#clear-region').addEventListener('click',()=>{rows.find(r=>r.id===$('#region-select').value).inputs=emptyInputs();syncMetadataLock();loadRegion();renderResults();});
  $('#preset').addEventListener('change',()=>{weights=[...PRESETS[$('#preset').value]];weights.forEach((v,i)=>{$(`#weight-${i}`).value=v;});renderWeights();});
  componentNames.forEach((_,i)=>{$(`#weight-${i}`).addEventListener('input',()=>{
    const next = componentNames.map((_,j)=>Number($(`#weight-${j}`).value));
    if(next.every(v=>v===0)){ $(`#weight-${i}`).value=weights[i];$('#weight-message').textContent='세 기준의 비중을 모두 0으로 설정할 수는 없습니다. 이전 설정을 유지합니다.';return; }
    weights=next;$('#preset').value='custom';renderWeights();
  });});
  $('#reset').addEventListener('click',()=>{
    rows.forEach(r=>{r.inputs=emptyInputs();});metadata=null;syncMetadataLock();$('#scenario-form').reset();
    weights=[...PRESETS.balanced];$('#preset').value='balanced';weights.forEach((v,i)=>{$(`#weight-${i}`).value=v;});loadRegion();renderWeights();$('#form-message').textContent='입력한 가구 수와 집계 기준을 모두 지웠습니다.';
  });
  $('#download-scenario').addEventListener('click',()=>{
    const output={type:'USER_SCENARIO_NOT_OFFICIAL',label:'사용자 입력 시나리오 · 공식 피해 현황·지원 결정 아님',modelVersion:'A-1.0',createdAt:new Date().toISOString(),publicSnapshotDate:snapshot.asOf,metadata,weights:normaliseWeights(weights),regions:rows,results:evaluateRegions(rows,weights,{mode:'scenario'}),sensitivity:sensitivity(rows,{mode:'scenario'})};
    const url=URL.createObjectURL(new Blob([JSON.stringify(output,null,2)],{type:'application/json;charset=utf-8'}));
    const a=document.createElement('a');a.href=url;a.download='nepal-model-a-USER-SCENARIO.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  loadRegion();renderWeights();
}
try {
  const response=await fetch('./data/snapshot.json?v=2',{cache:'no-cache'});
  if(!response.ok) throw new Error(`HTTP ${response.status}`);
  snapshot=await response.json();
  if(!Array.isArray(snapshot.regions)||snapshot.regions.length===0||!Array.isArray(snapshot.sources)) throw new Error('공개 자료 형식 오류');
  renderFocus();renderEvidence();initScenario();
} catch(error) {
  console.error('Nepal situation room:',error);
  $('#context').textContent='자료를 불러오지 못했습니다.';
  if ($('#urgent-regions')) $('#urgent-regions').textContent='지역별 상세 자료를 불러오지 못했습니다. 위의 IFRC 보고서에서 피해 상황을 확인할 수 있습니다.';
  $('#load-error').hidden=false;
  $('#load-error').textContent='지역별 자료를 불러오지 못했습니다. 연결을 확인하고 새로고침해 주세요. 문제가 계속되면 페이지 하단의 문의처로 알려 주세요.';
  $('#scenario-form').querySelectorAll('input,select,button').forEach(el=>{el.disabled=true;});
  ['preset','download-scenario','reset'].forEach(id=>{$(`#${id}`).disabled=true;});
}
