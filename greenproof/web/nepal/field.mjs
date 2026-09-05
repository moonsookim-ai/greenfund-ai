import {buildHandoff, renderHandoff, nepalNow} from './field-model.mjs?v=1';

const wording = {
  ko: {
    draft: '구조 요청 내용 정리', lead: '아는 내용부터 적어 전화나 메시지로 전달하세요. 긴급 신고를 이 양식 작성 때문에 늦추지 마세요.',
    privacy: '입력은 이 화면에만 유지됩니다. 새로고침하면 사라지며, 서버로 전송되지 않습니다. 이름·신분증·환자 상세정보는 적지 마세요.',
    ref: '내 기록 번호 · 공식 접수번호 아님', area: '1. 위치와 관찰한 상황', district: '지구 / District', place: '마을·행정구역·찾기 쉬운 지형물',
    observed: '상황을 확인한 시각 · 네팔 시간', now: '현재 네팔 시각 넣기', unknown: '미확인', time: '모든 시각은 네팔 현지 시간(UTC+05:45)입니다. 확인하지 못한 시각과 인원은 비워 두세요.',
    basis: '정보를 알게 된 경위', onsite: '현장에서 직접 확인', relayed: '다른 사람에게 전달받음', people: '도움이 필요하다고 파악한 인원',
    situation: '관찰한 상황', situationHint: '고립된 장소, 물이 차오르는지, 다친 사람이 있는지 등 관찰한 사실. 추측은 구분해서 적으세요.',
    support: '요청할 도움 · 여러 개 선택 가능', rescue: '전문 구조팀 확인', medical: '의료 평가·구급차', water: '식수·위생', shelter: '대피소', access: '접근·운송 지원',
    location: '좌표가 있으면 추가하기', lat: '위도 / Latitude', lon: '경도 / Longitude', locType: '이 좌표가 가리키는 곳', incident: '도움이 필요한 현장', reporter: '제보자인 내 위치',
    geo: '내 위치 확인', geoNote: '버튼을 누르면 기기가 위치 사용 허용을 요청할 수 있습니다. 이 위치는 제보자의 위치이며, 구조 대상의 위치로 자동 지정하지 않습니다.',
    coordSource: '좌표 출처·정확도·확인 시각', map: '좌표 위치만 지도에서 확인 ↗', mapNote: '외부 지도에 좌표가 전달됩니다. 길 안내나 통행 가능 여부를 뜻하지 않습니다.',
    callback: '다시 연락할 팀의 연락처 · 선택', follow: '2. 기관에 연락한 뒤 기록', followNote: '아래 상태는 사용자가 직접 기록한 내용입니다. 이 사이트는 기관의 접수·출동 현황을 조회하지 않습니다.',
    status: '연락 상태', attempted: '연락을 시도했으나 접수 확인 전', acknowledged: '기관으로부터 접수 확인을 받음', agency: '연락한 기관·부서', contactTime: '연락한 시각 · 네팔 시간', receipt: '기관 접수번호 또는 수신 확인 내용', next: '다음 연락·재확인 시각 · 네팔 시간',
    checks: '3. 이동·인계 전 확인표', checksNote: '통행이 가능하다고 자동 판단하지 않습니다. 확인 기관, 구간 또는 시설, 확인 내용을 적고 시각을 남기세요.',
    weather: '기상·홍수 안내', route: '이동할 도로·교량·구간', receiving: '인계할 의료시설·대피소의 수용 여부', communications: '팀 연락 방법·연결이 끊겼을 때 연락 계획',
    recorded: '관련 기관에 확인한 내용 있음', blocked: '통제·수용 불가·문제 보고됨', detail: '확인 기관 / 구간·시설 / 답변 내용', checkedTime: '확인 시각 · 네팔 시간',
    submit: '전달용 영문 초안 만들기', clear: '입력 지우고 새 기록', output: '전달용 영문 초안', outputNote: '영문 항목명으로 정리하며 직접 쓴 문장은 번역하지 않습니다. 현지에 보낼 내용은 영어 또는 상대가 읽을 수 있는 언어로 적어 주세요.',
    copy: '초안 복사', download: '텍스트로 저장', json: '기록 JSON 저장', print: '초안 인쇄', edited: '내용을 바꿨습니다. 초안을 다시 만들어 반영하세요.',
    ready: '초안을 만들었습니다. 아직 기관에 전송되지 않았습니다. 복사하거나 전화로 전달한 뒤 접수 여부를 확인하세요.',
    missing: '위치 설명 또는 좌표가 없습니다. 알고 있는 지형물부터 전달하고 기관과 위치를 확인하세요.', outside: '좌표가 네팔 주변 범위를 벗어납니다. 위도·경도 순서와 숫자를 다시 확인하세요.',
    noClearance: '항목에 확인 기록이 있어도 통행 허가나 출동 승인을 뜻하지 않습니다.', pending: '확인 기록이 없는 항목', blockedItems: '통제·수용 불가·문제가 기록된 항목',
    copied: '초안을 복사했습니다. 필요한 기관에 직접 전달하세요.', copyFail: '자동 복사가 되지 않았습니다. 아래 초안을 선택해 복사하세요.', saved: '다운로드를 요청했습니다. 파일에는 입력한 위치·연락처가 포함될 수 있습니다.',
    cleared: '입력을 지웠습니다. 새 기록 번호를 만들었습니다.', geoWait: '기기 위치를 확인하고 있습니다.', geoFail: '기기 위치를 얻지 못했습니다. 알고 있는 장소나 좌표를 직접 적어 주세요.', geoSuccess: '제보자의 위치를 넣었습니다. 구조 대상의 위치인지 별도로 확인하세요.',
    errors: {time:'날짜와 시각을 확인하세요.',future:'관찰·연락·확인 시각은 미래일 수 없습니다. 네팔 현지 시간을 확인하세요.',coordinates:'위도(-90~90)와 경도(-180~180)를 십진수로 함께 입력하거나 둘 다 비워 두세요.',people:'인원은 0 이상의 정수로 적거나 비워 두세요.',acknowledgment:'접수 확인으로 기록하려면 기관, 연락 시각, 접수번호 또는 확인 내용을 적어 주세요.',verification:'확인 기록이 있는 항목에는 기관·답변 내용과 확인 시각이 필요합니다.'}
  },
  en: {
    draft:'Prepare a rescue handoff', lead:'Write what you know, then call or share it with the appropriate agency. Do not delay an urgent call to complete this form.',
    privacy:'Entries stay in this page and disappear on reload. They are not sent to a server. Do not include names, identity documents or detailed medical records.',
    ref:'Your local reference — not an official incident ID', area:'1. Location and observed situation', district:'District', place:'Village / ward / recognizable landmark',
    observed:'Time observed — Nepal time', now:'Insert current Nepal time', unknown:'Unknown', time:'All times use Nepal time (UTC+05:45). Leave unconfirmed times and counts blank.',
    basis:'Information source', onsite:'Observed on site', relayed:'Relayed by another person', people:'People reported needing help',
    situation:'Observed situation', situationHint:'Where people are isolated, whether water is rising, any observed injuries. Separate observations from assumptions.',
    support:'Help requested — select all that apply', rescue:'Professional rescue assessment', medical:'Medical assessment / ambulance', water:'Safe water / hygiene', shelter:'Shelter', access:'Access / logistics',
    location:'Add coordinates if known', lat:'Latitude', lon:'Longitude', locType:'These coordinates represent', incident:'Incident location', reporter:'My location as reporter',
    geo:'Get my location', geoNote:'Your device may ask for location permission. This records the reporter’s position, not automatically the location of people needing rescue.',
    coordSource:'Coordinate source / accuracy / time', map:'Check coordinate location on map ↗', mapNote:'Coordinates will be shared with the external map service. This is not routing or road clearance.',
    callback:'Team callback contact — optional', follow:'2. Record agency contact', followNote:'This is your own contact log. The tool does not check agency receipt or dispatch status.',
    status:'Contact status', attempted:'Contact attempted; receipt unconfirmed', acknowledged:'Agency acknowledged receipt', agency:'Agency / unit contacted', contactTime:'Contact time — Nepal time', receipt:'Agency reference or acknowledgment details', next:'Next contact / check time — Nepal time',
    checks:'3. Confirm before movement and handover', checksNote:'This tool does not determine whether a route is passable. Record who confirmed what, for which section or facility, and when.',
    weather:'Weather / flood advice', route:'Planned road / bridge / route section', receiving:'Receiving medical facility / shelter acceptance', communications:'Team communications and fallback contact plan',
    recorded:'Confirmation recorded from relevant agency', blocked:'Closure / no capacity / issue reported', detail:'Agency / section or facility / response', checkedTime:'Checked at — Nepal time',
    submit:'Prepare English handoff draft', clear:'Clear entries / new record', output:'English handoff draft', outputNote:'Labels are in English. Your free text is preserved as entered, not translated. Use a language your recipient understands.',
    copy:'Copy draft', download:'Save text', json:'Save JSON record', print:'Print draft', edited:'Entries changed. Prepare a new draft to include your changes.',
    ready:'Draft prepared. NOT sent to an agency. Copy it or read it over the phone, then confirm receipt with the agency.',
    missing:'No place description or coordinates supplied. Share any known landmark and confirm the location with the agency.', outside:'Coordinates are outside a broad Nepal vicinity box. Recheck the latitude, longitude and their order.',
    noClearance:'Confirmation records do not constitute permission to travel or dispatch.', pending:'Items without confirmation records', blockedItems:'Items with a reported closure / no capacity / issue',
    copied:'Draft copied. Send it to the appropriate agency yourself.', copyFail:'Automatic copy unavailable. Select and copy the draft below.', saved:'Download requested. The file may contain location and contact details you entered.',
    cleared:'Entries cleared. A new local reference has been created.', geoWait:'Getting device location…', geoFail:'Device location unavailable. Enter a known place or coordinates manually.', geoSuccess:'Reporter location added. Confirm the incident location separately.',
    errors:{time:'Check dates and times.',future:'Observed, contacted and checked times cannot be in the future. Check Nepal local time.',coordinates:'Enter both decimal latitude (-90 to 90) and longitude (-180 to 180), or leave both blank.',people:'Enter a non-negative whole count, or leave it blank.',acknowledgment:'For acknowledged receipt, enter the agency, contact time, and reference or acknowledgment details.',verification:'For a confirmation record, supply the agency / response and check time.'}
  }
};
const newReference = () => `NP-${(globalThis.crypto?.randomUUID?.().slice(0, 8) || `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`).toUpperCase()}`;

export function initFieldTool(root) {
  const t = wording[root.dataset.lang === 'en' ? 'en' : 'ko'];
  const input = (name, title, type = 'text', extra = '') => `<label>${title}<input name="${name}" type="${type}" ${extra}></label>`;
  const options = entries => entries.map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
  const select = (name, title, entries) => `<label>${title}<select name="${name}">${options(entries)}</select></label>`;
  root.innerHTML = `<form class="handoff-form" autocomplete="off" novalidate>
    <div class="field-tool-head"><h3>${t.draft}</h3><p>${t.lead}</p></div><p class="field-note">${t.privacy}</p>
    ${input('reference', t.ref, 'text', 'maxlength="70" readonly')}
    <fieldset><legend>${t.area}</legend><div class="field-pair">${input('district', t.district, 'text', 'maxlength="120"')}${input('place', t.place, 'text', 'maxlength="240"')}</div>
    <div class="field-pair"><div>${input('observedAt', t.observed, 'datetime-local')}<button type="button" class="field-small" data-now="observedAt">${t.now}</button></div>${select('basis', t.basis, [['unknown',t.unknown],['on-site',t.onsite],['relayed',t.relayed]])}</div>
    <p class="field-note">${t.time}</p>${input('people', t.people, 'text', 'inputmode="numeric" maxlength="10"')}
    <label>${t.situation}<textarea name="observation" rows="3" maxlength="800" placeholder="${t.situationHint}"></textarea></label>
    <fieldset class="support-choices"><legend>${t.support}</legend>${['rescue','medical','water','shelter','access'].map(id => `<label><input type="checkbox" name="support" value="${id}">${t[id]}</label>`).join('')}</fieldset>
    <details><summary>${t.location}</summary><div class="field-pair">${input('latitude',t.lat,'text','inputmode="decimal" maxlength="20"')}${input('longitude',t.lon,'text','inputmode="decimal" maxlength="20"')}</div>
    ${select('locationType',t.locType,[['unknown',t.unknown],['incident',t.incident],['reporter',t.reporter]])}
    <button type="button" class="button" data-geo>${t.geo}</button><p class="field-note">${t.geoNote}</p><p data-geo-status role="status"></p>
    ${input('coordinateSourceNote',t.coordSource,'text','maxlength="240"')}<a data-map hidden target="_blank" rel="noopener noreferrer">${t.map}</a><p class="field-note">${t.mapNote}</p></details>
    ${input('callback',t.callback,'text','maxlength="180"')}
    </fieldset>
    <details><summary>${t.follow}</summary><p class="field-note">${t.followNote}</p>
    ${select('contactStatus',t.status,[['unknown',t.unknown],['attempted',t.attempted],['acknowledged',t.acknowledged]])}
    <div class="field-pair">${input('agency',t.agency,'text','maxlength="180"')}${input('contactedAt',t.contactTime,'datetime-local')}</div>
    ${input('receipt',t.receipt,'text','maxlength="240"')}${input('nextCheckAt',t.next,'datetime-local')}</details>
    <details><summary>${t.checks}</summary><p class="field-note">${t.checksNote}</p>
    ${['weather','route','receiving','communications'].map(id => `<fieldset class="verification-row"><legend>${t[id]}</legend>${select(id+'Status',t.status,[['unknown',t.unknown],['recorded',t.recorded],['blocked',t.blocked]])}${input(id+'Detail',t.detail,'text','maxlength="800"')}${input(id+'Time',t.checkedTime,'datetime-local')}</fieldset>`).join('')}</details>
    <div class="actions field-actions"><button class="button primary" type="submit">${t.submit}</button><button class="button" type="reset">${t.clear}</button></div>
    <p data-field-status role="status" aria-live="polite"></p>
    </form>
    <section class="handoff-output" hidden><h3>${t.output}</h3><p class="field-note">${t.outputNote}</p><p data-validation-note></p>
    <div class="actions"><button type="button" class="button" data-copy>${t.copy}</button><button type="button" class="button" data-text>${t.download}</button><button type="button" class="button" data-json>${t.json}</button><button type="button" class="button" data-print>${t.print}</button></div>
    <textarea data-draft readonly rows="24" aria-label="English handoff draft" spellcheck="false"></textarea><pre class="print-draft" lang="en"></pre><p class="field-note">${t.noClearance}</p></section>`;
  const $ = selector => root.querySelector(selector), form = $('form');
  const field = name => form.elements.namedItem(name);
  const status = $('[data-field-status]'), out = $('.handoff-output');
  let record = null, geoRequest = 0;
  field('reference').value = newReference();
  function invalidate() {record = null; out.hidden = true; $('[data-map]').hidden = true; status.textContent = t.edited;}
  form.addEventListener('input', event => {invalidate(); if (['latitude','longitude'].includes(event.target.name)) {geoRequest++; field('coordinateSourceNote').value=''; field('locationType').value='unknown'; $('[data-geo-status]').textContent=''; $('[data-geo]').disabled=false;}});
  root.querySelectorAll('[data-now]').forEach(button => button.addEventListener('click', () => {field(button.dataset.now).value=nepalNow(); invalidate();}));
  $('[data-geo]').addEventListener('click', () => {
    const request = ++geoRequest; const button = $('[data-geo]');
    if (!navigator.geolocation) {$('[data-geo-status]').textContent=t.geoFail;return;}
    button.disabled=true; $('[data-geo-status]').textContent=t.geoWait;
    navigator.geolocation.getCurrentPosition(position => {
      if (request !== geoRequest) return;
      invalidate(); field('latitude').value=position.coords.latitude.toFixed(6); field('longitude').value=position.coords.longitude.toFixed(6);
      field('locationType').value='reporter';
      field('coordinateSourceNote').value=`Device position; accuracy ±${Math.ceil(position.coords.accuracy)} m; captured ${nepalNow(new Date(position.timestamp)).replace('T',' ')} Nepal UTC+05:45`;
      $('[data-geo-status]').textContent=t.geoSuccess;button.disabled=false;
    }, () => {if(request===geoRequest){$('[data-geo-status]').textContent=t.geoFail;button.disabled=false;}}, {enableHighAccuracy:true,timeout:12000,maximumAge:0});
  });
  form.addEventListener('submit', event => {
    event.preventDefault(); record=null;out.hidden=true;
    if (!form.reportValidity()) return;
    const data = new FormData(form), raw = Object.fromEntries(data); raw.support=data.getAll('support');
    try {record=buildHandoff(raw);} catch(error) {status.textContent=t.errors[error.message] || t.errors.time;return;}
    const draft=renderHandoff(record); $('[data-draft]').value=draft;$('.print-draft').textContent=draft;
    $('[data-validation-note]').textContent=[!record.place&&!record.coordinates?t.missing:'',record.coordinates?.outsideNepalVicinity?t.outside:'',`${t.pending}: ${record.verification.pending.length}/4.`,record.verification.blocked.length?`${t.blockedItems}: ${record.verification.blocked.map(id=>t[id]).join(', ')}.`:''].filter(Boolean).join(' ');
    const map=$('[data-map]');map.hidden=!record.coordinates;
    if(record.coordinates) {const {latitude,longitude}=record.coordinates;map.href=`https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=15/${latitude}/${longitude}`;}
    status.textContent=t.ready;out.hidden=false;
    $('[data-draft]').focus({preventScroll:true});out.scrollIntoView({behavior:'auto',block:'start'});
  });
  form.addEventListener('reset', () => {geoRequest++;record=null;out.hidden=true;setTimeout(()=>{field('reference').value=newReference();$('[data-geo-status]').textContent='';$('[data-map]').hidden=true;$('[data-geo]').disabled=false;status.textContent=t.cleared;},0);});
  $('[data-copy]').addEventListener('click', async () => {
    if(!record)return;
    try{await navigator.clipboard.writeText(renderHandoff(record));status.textContent=t.copied;}
    catch{$('[data-draft]').focus();$('[data-draft]').select();status.textContent=t.copyFail;}
  });
  function download(json=false) {
    if(!record)return;
    const data=json?JSON.stringify(record,null,2):renderHandoff(record);
    const url=URL.createObjectURL(new Blob([data],{type:json?'application/json;charset=utf-8':'text/plain;charset=utf-8'}));
    const link=document.createElement('a');link.href=url;link.download=`nepal-handoff-${record.localReference.replace(/[^A-Z0-9-]/gi,'').slice(0,70)||'draft'}.${json?'json':'txt'}`;
    link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);status.textContent=t.saved;
  }
  $('[data-text]').addEventListener('click',()=>download());$('[data-json]').addEventListener('click',()=>download(true));
  $('[data-print]').addEventListener('click',()=>{if(record){document.body.classList.add('print-handoff');window.print();document.body.classList.remove('print-handoff');}});
}

document.querySelectorAll('[data-field-tool]').forEach(initFieldTool);
