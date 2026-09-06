"""Build Korean responder briefing content for the situation room and offline page."""
from pathlib import Path
from html import escape as e
import json, re
from nepal_sources import render_sources

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'greenproof/web'
NEPAL=WEB/'nepal'
data=json.loads((NEPAL/'data/responder-briefing.json').read_text(encoding='utf-8'))
sources={s['id']:s for s in data['sources']}
analysis=json.loads((NEPAL/'data/source-analyses.json').read_text(encoding='utf-8'))
ref,preface,library=render_sources(data,analysis)

region_cards=[]
for r in data['regions']:
    facts=''.join(f'<li>{e(f["text"])} {ref(f["source"])}</li>' for f in r['facts'])
    region_cards.append(f'''<article class="responder-region" data-brief-region="{r['id']}"><div class="responder-region-title"><div><span>{e(r['english'])}</span><h3>{e(r['name'])} · {e(r['headline'])}</h3></div><span class="brief-status">공개 보고</span></div><p class="place-names">{e(r['places'])}</p><div class="region-brief-grid"><div><h4>자료에 나온 사실</h4><ul>{facts}</ul></div><div><h4>대원이 알아둘 의미 <small>GREEN PROOF 해석</small></h4><p>{e(r['implication'])}</p><div class="brief-unknown"><b>현재 확인되지 않은 작전 정보</b><p>{e(r['unknown'])}</p></div><p class="brief-contact"><b>연락 체계</b> {e(r['counterpart'])}</p></div></div></article>''')

medical=''.join(f'<tr><th scope="row">{e(m["name"])}<small>{e(m["english"])}</small></th><td>{e(m["place"])}</td><td>{e(m["note"])}</td><td>미확인</td></tr>' for m in data['medical'])
source_list=''.join(f'<li>{ref(s["id"])}<p>{e(s["locator"])}</p></li>' for s in data['sources'])
contact_items=[
 ('국가 수색·구조·항공 이동 조정','NDRRMA','1234','1234','네팔 내 단축번호 · HEOC 9.4 보고','수색·구조 및 항공 이동 요청 창구로 안내됨. 헬기 가용·탑승·착륙 승인을 의미하지 않음.',sources['heoc']['url']+'#page=8'),
 ('의료 구조 조정·병상 문의','보건당국 / HEOC','1115','1115','네팔 내 단축번호 · HEOC 9.4 보고','환자 인계·병상 문의를 조정하는 창구. 보고서에 나온 병원이 현재 수용 가능한지는 별도 답변 필요.',sources['heoc']['url']+'#page=8'),
 ('라수와 지구 재난상황실','Rasuwa DEOC','+977-10-540131','+97710540131','공식 사이트에 24시간 안내','대체 번호 +977-10-540019. 지구 내 현장 지휘기관·접근 상황 연결.', 'https://daorasuwa.moha.gov.np/en'),
 ('대한민국 대사관','주네팔 대한민국 대사관','+977-1-537-0172','+97715370172','근무시간 대표전화 · 현지 월–금 09:00–12:00 / 13:30–17:00','한국팀 연락 창구 협의에 참고. 공식 연락처 페이지 검색 색인 확인; 실제 연결 여부는 미확인.',sources['embassy']['url']),
 ('한국인 사건·사고 영사 지원','영사안전콜센터','+82-2-3210-0404','+82232100404','서울 · 24시간 안내','한국인 대원의 사건·사고 관련 영사 지원 창구. 현지 구조 작전 지휘기관은 아님.',sources['embassy']['url']),
 ('기상·홍수 안내','네팔 DHM','1155','1155','네팔 내 단축번호','1번 기상, 2번 홍수 조기경보 안내. 경보 감시 담당자가 최신 발표를 확인할 공식 창구.','https://www.dhm.gov.np/')
]
contact_source_ids=['heoc','heoc','rasuwa-deoc','embassy','embassy','dhm']
contacts=''.join(f'<article class="contact-card"><h3>{e(name)}</h3><small>{e(org)}</small><a class="contact-number" href="tel:{dial}">{number}</a><small>{e(scope)}</small><p>{e(note)}</p>{ref(key)}</article>' for (name,org,number,dial,scope,note,url),key in zip(contact_items,contact_source_ids))

content='''
  <section id="evidence" class="section rescue-section" aria-labelledby="responder-area-title"><span id="regional-actions"></span>
    <div class="section-head"><div><span class="section-no">지역 브리핑</span><h2 id="responder-area-title">어느 지역에서 무엇이 문제가 되는가</h2><p>피해가 보고된 장소와 접근·의료 제약을 한국 구조대원의 관점에서 정리했습니다. 아래 배열은 수색 우선순위나 한국팀의 임무 배정이 아닙니다.</p></div></div>
    <div class="brief-filters" role="group" aria-label="지역 브리핑 선택"><button type="button" data-brief-filter="all" aria-pressed="true">전체</button><button type="button" data-brief-filter="rasuwa" aria-pressed="false">라수와</button><button type="button" data-brief-filter="nuwakot" aria-pressed="false">누와코트</button><button type="button" data-brief-filter="dhading" aria-pressed="false">다딩</button></div><p class="field-note" data-brief-filter-status aria-live="polite">3개 지역 브리핑</p>
    __REGIONS__
    <p class="field-note">고르카·타나훈·치트완도 WHO의 영향 지역 목록에 있으나, 이 브리핑에는 대원 투입 판단에 쓸 구체적인 지역 정보가 부족합니다. 정보 부족을 피해가 적다는 뜻으로 해석하지 않습니다.</p>
  </section>
  <section id="responder-safety" class="section rescue-section" aria-labelledby="safety-title"><div class="section-head"><div><span class="section-no">대원 안전·접근</span><h2 id="safety-title">이번 홍수에서 특히 볼 위험 요소</h2><p>아래는 사고 당시 보고된 위험과 그에 따른 검토사항입니다. 현재 위험 등급·철수 수위·차량 운행 가능 여부는 제공하지 않습니다.</p></div></div>
    <div class="risk-grid">
      <article><span>상류·하류 연계</span><h3>추가 유출과 토사·암석</h3><p>ICIMOD는 토사·암석을 동반한 급격한 유출과 상류 하천 막힘 가능성을 설명했습니다. 당시 일부 수위 관측소 피해도 보고됐습니다.</p><p class="risk-meaning"><b>대원 브리핑에 포함:</b> 경보 수신 담당, 현지 지휘부가 정한 작업 중지·철수 기준, 통신 단절 시 연락 계획.</p>__ICIMOD__</article>
      <article><span>지상 접근</span><h3>도로·교량과 이동 구간</h3><p>9월 5일 라수와 공지는 다음 날부터 지정 구간을 현지 07:00–11:00, 14:00–17:00에 통제한다고 안내합니다. 이후 변경과 차종별 통행은 현지 확인이 필요합니다.</p><p class="risk-meaning"><b>대원 브리핑에 포함:</b> 구간별 통제와 확인 시각, 차량 종류, 지휘부가 승인한 접근·복귀 계획.</p>__ROADS__</article>
      <article><span>의료·노출 관리</span><h3>의료 거점 피해와 위생 환경</h3><p>HEOC는 보건시설 피해·접근 제약과 대피 거점의 위장염·발열·호흡기 증상 감시 사례를 보고했습니다.</p><p class="risk-meaning"><b>대원 브리핑에 포함:</b> 팀 의료책임자의 노출·개인보호·식수 계획, 대원 부상 시 이송·수용기관 연락.</p>__HEOC3__</article>
    </div><p class="field-note">급류 진입·로프·보트·잠수·붕괴 구조물 작업은 소속기관의 훈련과 현장 지휘체계에 따릅니다. 이 정보 페이지는 해당 전술이나 안전 수치를 지정하지 않습니다.</p>
  </section>
  <section id="medical-brief" class="section rescue-section" aria-labelledby="medical-title"><div class="section-head"><div><span class="section-no">의료 이송 참고</span><h2 id="medical-title">보고서에 등장하는 병원과 지명</h2><p>HEOC 10호의 2026년 9월 4일 17:00 환자 현황에 포함된 기관입니다. 현재 병상·진료과·접근 가능 여부를 확인한 수용 병원 목록은 아닙니다.</p></div></div>
    <div class="table-wrap"><table class="medical-brief-table"><caption>병원명 대조용 · 인계 전 의료 조정 창구 1115와 수용기관 답변 필요</caption><thead><tr><th scope="col">병원</th><th scope="col">보고서상 위치</th><th scope="col">확인한 정보</th><th scope="col">현재 수용</th></tr></thead><tbody>__MEDICAL__</tbody></table></div>
    <p class="field-note">__HEOC1__</p><div class="decision-note"><b>환자 인계에 필요한 답변</b><p>수용기관·연락 담당, 필요한 의료 기능, 인계 장소, 이송 수단과 구간, 수용 답변 시각. 보고서의 진료 인원이나 퇴원 수를 남은 병상 수로 계산하지 않습니다.</p></div>
  </section>
  <section id="strategy" class="section rescue-section" aria-labelledby="strategy-title"><div class="section-head"><div><span class="section-no">한국팀 지휘·연락 참고</span><h2 id="strategy-title">출국 전부터 교대까지, 받아야 할 정보</h2><p>한국팀 지휘관·연락관이 브리핑을 구성할 때 참고할 항목입니다. 한국 구조대의 실제 파견 여부·임무·집결지는 확인된 자료가 없습니다.</p></div></div>
    <div class="strategy-grid">
      <article class="strategy-card"><span class="strategy-step">출국 전 · 팀 준비</span><h3>수용 창구와 임무 조건</h3><ul><li>파견기관 승인·현지 수용 창구·연락 담당</li><li>팀 역량·인원·장비 목록과 통관·반입 협의</li><li>통역·자체 통신·의료·식수·전원·보급 계획</li></ul><p class="field-note">대사관·파견기관 및 현지 조정 창구와 공유할 팀 정보를 준비합니다.</p></article>
      <article class="strategy-card"><span class="strategy-step">현지 도착 · 임무 조정</span><h3>실제 지휘체계와 작업 구역</h3><ul><li>현지 재난관리 책임기관(LEMA)과 연락관</li><li>국제팀 접수·조정소가 설치됐다면 등록·브리핑</li><li>배정 구역·중복 수색 방지·보고 주기·의료 인계</li></ul><p class="field-note">RDC·UCC·OSOCC는 일반적인 국제 조정 용어입니다. 이번 현장의 설치 위치는 확인되지 않았습니다.</p></article>
      <article class="strategy-card"><span class="strategy-step">작업 전·교대 · 상황 공유</span><h3>팀이 함께 알아야 할 변경점</h3><ul><li>접근·복귀·기상·상류 경보의 마지막 확인 시각</li><li>현장 위험·작업 중지·철수·연락 두절 계획</li><li>완료·미완료 구역, 환자 인계, 남은 자원</li></ul><p class="field-note">앞 교대조의 정보와 현지 지휘부의 변경 지시를 한 기준 시각으로 맞춥니다.</p></article>
    </div><p class="field-note">국제팀 조정 참고: __GUIDE__. INSARAG 지침은 주로 도시탐색구조(USAR)를 다루며, 여기서는 파견·연락·정보 인계에 관한 일반 참고로 사용했습니다.</p>
  </section>
  <section id="emergency-contacts" class="section rescue-section" aria-labelledby="contact-title"><div class="section-head"><div><span class="section-no">지휘·의료·한국 측 연락망</span><h2 id="contact-title">업무에 맞는 조정 창구</h2><p>공개 연락처 확인일 2026.09.05. 단축번호는 네팔 내 사용 기준이며, 실제 연결·가용 자원은 확인하지 않았습니다.</p></div></div><div class="contact-grid responder-contacts">__CONTACTS__</div>
    <details><summary>보조 연락처와 공식 상황판</summary><p>경찰 <a href="tel:100">100</a> · 구급차 <a href="tel:102">102</a> · 네팔적십자 <a href="tel:1130">1130</a> · 라수와 DEOC 대체 <a href="tel:+97710540019">+977-10-540019</a></p><p><a data-analysis-link href="#analysis-dhm">DHM 기상·홍수 해설</a> · <a data-analysis-link href="#analysis-heoc">HEOC 보건 상황보고 해설</a></p><p class="field-note"><a href="./data/field-contacts.json">보조 연락처 출처 기록</a>. 일반 신고 번호와 구조대 임무 조정 창구를 구분해 사용하세요.</p></details>
  </section>
  <section id="field-support" class="section rescue-section" aria-labelledby="field-title"><div class="section-head"><div><span class="section-no">한국어 현장 참고자료</span><h2 id="field-title">대원이 들고 갈 브리핑</h2><p>지역·위험·의료·연락망을 사진 없는 한국어 문서로 저장할 수 있습니다. 저장 뒤에도 경보·도로·병상은 현지에서 새로 확인해야 합니다.</p></div></div>
    <div class="field-callout"><div><h3>한국 구조대원용 오프라인 브리핑</h3><p>지역별 상황과 한글 해설을 함께 읽고 저장할 수 있습니다.</p></div><div class="actions"><a class="button" href="https://greenfund.ai.kr/nepal/field/">한국어 브리핑 열기 ↗</a><a class="button" href="https://greenfund.ai.kr/nepal/field/index.html" download="nepal-korean-responder-briefing.html">HTML 저장 ↓</a></div></div>
    <div class="brief-basics"><p><b>시차</b> 네팔 UTC+05:45 · 한국보다 3시간 15분 느림. 예: 한국 12:00 → 네팔 08:45.</p><p><b>지명·좌표</b> 한국어 발음 옆의 영문 철자를 함께 사용합니다. 좌표를 전달할 때 WGS84·위도/경도 순서와 취득 시각을 명시합니다.</p></div>
    <details><summary>현지 연락관에게 바로 보여줄 영문 질문</summary><div class="table-wrap"><table><thead><tr><th>확인할 정보</th><th>English</th></tr></thead><tbody><tr><td>한국팀 임무를 배정할 기관</td><td lang="en">Which agency assigns sectors to incoming international rescue teams?</td></tr><tr><td>차종별 접근 가능 여부와 시각</td><td lang="en">Is this road section open to our vehicle type? When was it last checked?</td></tr><tr><td>환자 수용을 확인한 기관</td><td lang="en">Which facility has confirmed it can receive this patient?</td></tr><tr><td>연락 두절 시 대체 연락</td><td lang="en">What is the fallback contact if radio communication fails?</td></tr><tr><td>팀이 감시할 공식 홍수 경보</td><td lang="en">Which official flood warning source should our team monitor?</td></tr></tbody></table></div></details>
    <p><a class="button" data-analysis-link href="#analysis-field-guide">국제 지침의 대원 준비·교대 해설 읽기 ↓</a></p><p class="field-note">정책·운영·현장 지침의 필요한 내용을 위 한국어 해설에 정리했습니다. 2020판의 적용 범위와 새 지침 발효일도 이곳에서 확인할 수 있습니다. __INSARAG__</p>
    <details><summary>추가 도구 · 현지 기관에 전달할 내용을 정리할 때</summary><p><a href="https://greenfund.ai.kr/nepal/handoff/">영문 인계 내용 작성 양식 ↗</a>. 입력이 필요한 경우에만 사용하는 보조 도구입니다.</p></details>
  </section>
  <details class="briefing-sources"><summary>구조대원 브리핑의 출처·기준일·한계</summary><p>자료를 열어 본 날짜와 현장 상황이 관측된 시각은 다릅니다. 각 문서의 시점을 표시했고, 확인되지 않은 현장 작전 정보는 채우지 않았습니다.</p><ul>__SOURCES__</ul><p><a href="https://greenfund.ai.kr/nepal/data/responder-briefing.json" download>브리핑 근거 JSON ↓</a></p></details>
'''
for key,value in {'__REGIONS__':'\n'.join(region_cards),'__ICIMOD__':ref('icimod'),'__ROADS__':ref('roads'),'__HEOC3__':ref('heoc',3),'__HEOC1__':ref('heoc',1),'__GUIDE__':ref('field-guide',9),'__MEDICAL__':medical,'__CONTACTS__':contacts,'__KOREAN_GUIDE__':data['koreanGuideUrl'],'__INSARAG__':ref('insarag'),'__SOURCES__':source_list}.items():content=content.replace(key,value)
content=content.replace('  <section id="field-support"',library+'\n  <section id="field-support"')

path=NEPAL/'index.html'
html=path.read_text(encoding='utf-8')
preface_block='<!-- PROJECT_PREFACE_START -->'+preface+'<!-- PROJECT_PREFACE_END -->'
if '<!-- PROJECT_PREFACE_START -->' in html:
    html,n=re.subn(r'<!-- PROJECT_PREFACE_START -->.*?<!-- PROJECT_PREFACE_END -->',preface_block,html,flags=re.S)
    assert n==1
else:
    html=html.replace('    <div class="response-date">',preface_block+'\n    <div class="response-date">',1)
html,n=re.subn(r'<!-- RESPONDER_BRIEFING_START -->.*?<!-- RESPONDER_BRIEFING_END -->','<!-- RESPONDER_BRIEFING_START -->'+content+'\n<!-- RESPONDER_BRIEFING_END -->',html,flags=re.S)
assert n==1
path.write_text(html,encoding='utf-8')

css='\n'.join((NEPAL/name).read_text(encoding='utf-8') for name in ['style.css','rescue.css','briefing.css'])
script=(NEPAL/'briefing.mjs').read_text(encoding='utf-8')
offline_content=content.replace('href="./data/field-contacts.json"','href="https://greenfund.ai.kr/nepal/data/field-contacts.json"')
page=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>한국 구조대원 현장 브리핑 · 네팔 | GREEN PROOF</title><meta name="description" content="한국 구조대원을 위한 네팔 홍수 지역별 위험·접근·의료·현지 연락망. 공개 자료 확인 2026-09-05."><link rel="canonical" href="https://greenfund.ai.kr/nepal/field/"><style>{css}</style></head><body class="responder-offline"><header class="site-header"><div class="header-inner"><a class="brand" href="https://greenfund.ai.kr/">GREEN <span>PROOF</span><small>환경재단이 운영하는 AI환경연구소</small></a><nav aria-label="주 메뉴"><a href="https://greenfund.ai.kr/nepal/">네팔상황실</a><a href="https://greenfund.ai.kr/#app">맹그로브 성장 기록</a><a href="https://greenfund.ai.kr/emissions/">우리 동네 온실가스 배출</a></nav></div></header><main id="main"><section class="response-intro"><p class="eyebrow">한국 구조대원 현장 참고자료</p><h1>네팔 홍수<br>한국팀 현장 브리핑</h1><p>지역별 접근 제약·대원 위험·의료 이송·현지 조정 창구를 정리했습니다.</p><p class="field-note">자료 확인 2026.09.05 · 공개 자료 기반 · 실시간 작전정보 아님 · GPT-6 Astra 활용</p><div class="actions"><button class="button primary" type="button" data-print-brief>전체 브리핑 인쇄 / PDF 저장</button><a class="button" href="#emergency-contacts">조정 연락망</a></div><p class="field-note">이 HTML은 별도 파일·통신 없이 읽을 수 있습니다. 외부 출처와 전화는 연결이 필요합니다. 지역을 선택하면 해당 지역 브리핑만 표시됩니다.</p></section>{offline_content}</main><footer><div><strong>GREEN PROOF</strong><p>환경재단이 운영하는 AI환경연구소 · GPT-6 Astra로 자료 검토·구현</p></div><!--email_off--><small class="research-contact">연구 문의 · 연구책임자 김문수 교수 · <a href="mailto:mskim@ceobizschool.kr">mskim@ceobizschool.kr</a></small><!--/email_off--></footer><script type="module">{script}</script></body></html>'''
page=page.replace('</section>'+offline_content,'</section>'+preface+offline_content,1)
page=page.replace('자료 확인 2026.09.05 · 공개 자료 기반','상황 자료 확인 2026.09.05 · 한국어 해설 갱신 2026.09.06 · 공개 자료 기반')
(NEPAL/'field/index.html').write_text(page,encoding='utf-8')
print(f'Built Korean responder briefing and standalone HTML ({len(page.encode("utf-8")):,} bytes).')
