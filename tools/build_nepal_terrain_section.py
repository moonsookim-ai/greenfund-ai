"""Render the accessible, source-backed 3D section and fallback tables."""
import json
import re
from pathlib import Path
from html import escape as h

ROOT=Path(__file__).resolve().parents[1]
PAGE=ROOT/'greenproof/web/nepal/index.html'
DATA=PAGE.parent/'data/terrain'
scenes=[json.loads((DATA/f'{name}.json').read_text(encoding='utf-8')) for name in ('syapru','timure')]

def table(s):
    rows=[]
    for c in s['candidates']:
        rows.append(f'<tr><th scope="row"><button type="button" data-terrain-cell="{c["id"]}">{c["id"]}</button></th><td>{c["counts"].get("destroyed",0)}</td><td>{c["counts"].get("damaged",0)}</td><td>{c["lonLat"][1]:.5f}°N<br>{c["lonLat"][0]:.5f}°E</td></tr>')
    return f'''<div data-terrain-table="{s['id']}"><h4>{s['name']} · 중첩 후보 {len(s['candidates'])}개 격자</h4><div class="terrain-table-scroll"><table><caption>250m 격자별 토사 이동 범위 안의 파괴·손상 건물 점. 북→남, 서→동 공간순이며 구조 우선순위가 아닙니다. 좌표는 격자 중심입니다.</caption><thead><tr><th scope="col">구역</th><th scope="col">파괴 건물</th><th scope="col">손상 건물</th><th scope="col">중심 좌표 · WGS84</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></div>'''

html='''<!-- TERRAIN_MODEL_START -->
<section id="terrain" class="terrain-section" aria-labelledby="terrain-title">
  <div class="terrain-heading"><div><span class="terrain-kicker">현장을 입체적으로 · 구조 참고 모델</span><h2 id="terrain-title">홍수 피해 지형과 매몰 검토 구역</h2><p>위성에서 판독한 토사 이동과 피해 건물을 실제 표고 위에서 대조하세요.</p></div><a href="#terrain-method">자료·판독 기준 ↓</a></div>
  <div class="terrain-date-line"><strong>피해 판독 2026.08.27</strong><span>과거 지형: SRTM 2000년 기반</span><span>모델 작성: 2026.09.06</span></div>
  <div class="terrain-layout">
    <div class="terrain-map-column" id="terrain-map-column">
      <div class="terrain-toolbar"><label for="terrain-area">대상 지역 <select id="terrain-area"><option value="syapru">샤프루베시 · Syapru Besi</option><option value="timure">티무레 · Timure</option></select></label><div class="terrain-view-buttons"><button type="button" id="terrain-fullscreen">전체 화면</button><button type="button" data-terrain-control="overview">전체 보기</button><button type="button" data-terrain-control="top">위에서 보기</button><button type="button" data-terrain-control="reset">처음 시점</button></div></div>
      <div class="terrain-basemaps" role="group" aria-label="지도 배경"><button type="button" data-terrain-basemap="satellite" aria-pressed="true">실제 위성영상</button><button type="button" data-terrain-basemap="relief" aria-pressed="false">표고 지형</button><span>위성 배경 8월 12일 · 피해 판독 8월 27일</span></div>
      <div class="terrain-frame" id="terrain-frame" aria-busy="true">
        <img id="terrain-fallback" src="./data/terrain/syapru-plan.svg" width="600" height="560" alt="샤프루베시 위성 판독 피해 평면도. 주황 면은 토사 이동, 점은 피해 건물, 보라 격자는 중첩 확인 후보입니다.">
        <canvas id="terrain-canvas" width="1000" height="600" tabindex="0" hidden aria-describedby="terrain-gestures terrain-limit">3D를 사용할 수 없는 환경에서는 아래 평면도와 구역 표를 이용하세요.</canvas><canvas id="terrain-labels" aria-hidden="true" hidden></canvas>
        <div class="terrain-map-label"><b id="terrain-view-label">피해 평면도 · 3D 준비 중</b><small id="terrain-background-status">배경: 홍수 전 위성 · 2026.08.12 · 10m 픽셀</small><small>실시간 침수·매몰 예측 아님</small></div>
        <div class="terrain-compass" aria-label="현재 시점의 북쪽 방향"><span id="terrain-north">↑</span><b>N</b></div>
        <div class="terrain-map-scale"><span id="terrain-scale"></span><small id="terrain-scale-label">가로 방향 500m · 3D 기준</small></div>
        <div class="terrain-zoom"><button type="button" data-terrain-control="in" aria-label="지형 확대">＋</button><button type="button" data-terrain-control="out" aria-label="지형 축소">−</button></div>
      </div>
      <div class="terrain-detail-controls"><div role="group" aria-label="지도 조작 방식"><button type="button" data-terrain-navigation="rotate" aria-pressed="true">회전</button><button type="button" data-terrain-navigation="pan" aria-pressed="false">지도 이동</button></div><label for="terrain-zoom-range">확대<input id="terrain-zoom-range" type="range" min="0.7" max="10" step="0.1" value="2" aria-label="3D 지도 확대 배율"><output id="terrain-zoom-value" for="terrain-zoom-range">2.0배</output></label></div>
      <div class="terrain-controls"><div role="group" aria-label="3D 시점 조절"><button type="button" data-terrain-control="left" aria-label="왼쪽으로 회전">↶</button><button type="button" data-terrain-control="right" aria-label="오른쪽으로 회전">↷</button><button type="button" data-terrain-control="up">더 위에서</button><button type="button" data-terrain-control="down">더 낮게</button></div><label for="terrain-height">높이 배율 <select id="terrain-height"><option value="1">1배 · 실제 비율</option><option value="1.5">1.5배 · 과장</option><option value="2">2배 · 과장</option></select></label></div>
      <p id="terrain-gestures" class="terrain-hint">2배로 시작 · 최대 10배 확대 · 지도 선택 후 휠로 확대 · ‘지도 이동’에서 끌어 이동 · 구역 선택 시 4.5배 확대</p>
      <div class="terrain-legend" role="group" aria-label="지도에 표시할 자료">
        <label><input type="checkbox" data-terrain-layer="event" checked><span class="terrain-symbol soil">▰</span>토사 이동 면</label>
        <label><input type="checkbox" data-terrain-layer="candidates" checked><span class="terrain-symbol cell">▣</span>매몰 검토 격자</label>
        <label><input type="checkbox" data-terrain-layer="buildings" checked><span class="terrain-symbol building">■</span>피해 건물</label>
        <label><input type="checkbox" data-terrain-layer="rivers" checked><span class="terrain-symbol river">━</span>하천 위치</label>
        <label><input type="checkbox" data-terrain-layer="roads" checked><span class="terrain-symbol road">━</span>도로·탐방로</label>
        <label><input type="checkbox" data-terrain-layer="footprints" checked>▱ 건물 외곽</label>
        <label><input type="checkbox" data-terrain-layer="labels" checked>지명·구역 번호</label>
        <label><input type="checkbox" data-terrain-layer="contours">100m 등고선</label>
      </div>
      <div class="terrain-sublegend"><span class="terrain-destroyed">■ 파괴</span><span class="terrain-damaged">● 손상</span><span>◇ 손상 가능성</span><span>┄ 위성 판독 범위</span></div>
      <p id="terrain-altitude" class="terrain-hint">실제 표고를 이용한 지형 모델 · 하천 선은 침수 경계가 아닙니다.</p>
      <p class="terrain-hint">Copernicus Sentinel (2026) / Element 84 · CEMS EMSR927 © European Union · SRTM/USGS via Mapzen · <a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors · ODbL</a></p>
    </div>
    <aside class="terrain-inspector" aria-label="매몰 검토 구역 정보">
      <label for="terrain-cell">매몰 여부를 확인할 구역<select id="terrain-cell" disabled><option value="">지형 자료 불러오는 중</option></select></label>
      <div id="terrain-detail" aria-live="polite"><h3>현장 확인이 필요한 곳을 대조하세요</h3><p>위성 판독 토사 이동 범위에 파괴·손상 건물이 놓인 곳을 250m 격자로 묶었습니다. 각 격자의 좌표와 건물 수를 아래 표에서도 확인할 수 있습니다.</p></div>
      <p id="terrain-limit" class="terrain-caution"><strong>매몰 확인·확률·구조 순위가 아닙니다.</strong> 토사 이동에는 침식도 포함됩니다. 건물 점은 사람 위치가 아니며, 현재 재실·생존·미수색 여부는 확인되지 않았습니다.</p>
      <a class="button primary" href="#emergency-contacts">현지 지휘·조정 연락망 ↓</a>
    </aside>
  </div>
  <p id="terrain-status" class="terrain-status" role="status">샤프루베시 피해 평면도 · 3D 자료 준비 중</p>
  <noscript><p>자바스크립트가 꺼져 있습니다. 평면도와 아래 두 지역의 구역 표·자료 설명을 이용하세요.</p></noscript>
  <details class="terrain-table-details"><summary>매몰 검토 구역 전체 · 좌표와 건물 수</summary>'''+''.join(table(s) for s in scenes)+'''</details>
  <details id="terrain-method" class="terrain-method"><summary>이 3D 모델의 근거 · 무엇을 알 수 있고, 무엇을 알 수 없나요?</summary>
    <div class="terrain-method-grid"><article><h3>1. 실제 표고를 입체 지형으로</h3><p>SRTM 표고를 Mapzen Terrain Tiles에서 받아 지형을 구성했습니다. SRTM은 2000년 관측 기반으로, 이번 홍수 이후의 토사 높이나 붕괴 지형을 나타내지 않습니다. 원자료의 명목 품질은 약 90m이며, 확대 배율이나 더 촘촘한 표시 격자가 원자료의 정확도를 높이지는 않습니다. 기본 높이 배율은 1배입니다.</p><p>기본 배경은 Sentinel-2가 2026년 8월 12일 촬영한 10m 픽셀의 실제 위성영상입니다. 원영상 좌표를 지형 격자에 맞춰 재투영했습니다. 홍수 전 영상이므로 당시 건물이 보이더라도 현재 남아 있다는 뜻은 아닙니다. 구름·결측 영역은 지형색으로 표시합니다. 표고 지형 모드에서는 녹색·갈색이 표고와 음영을 나타냅니다.</p><p>10m는 위성영상의 픽셀 크기이며 지형 표고의 정확도는 아닙니다. 100m 등고선은 기존 표고 격자에서 계산한 참고선입니다.</p></article>
    <article><h3>2. 8월 27일 위성 판독 피해를 겹침</h3><p>Copernicus EMSR927 AOI01 샤프루베시·AOI02 티무레의 Grading v1 자료를 사용했습니다. 기준 영상 시각은 2026년 8월 27일 05:05 UTC(네팔 10:50)입니다. 주황 면은 원자료의 ‘Mass Movement / Landslide’를 옮긴 것으로, 토사 퇴적 두께나 정확한 침수 범위는 아닙니다. 현장 검증은 완료되지 않은 판독 자료입니다.</p><p>샤프루베시 토사 이동 111.08ha·피해 건물 점 433개, 티무레 125.88ha·431개입니다. 건물 수에는 ‘손상 가능성’이 포함됩니다. 이 수는 전체 건물·피해 가구·실종자 수가 아닙니다. 점선 밖은 이 제품의 판독 범위 밖입니다.</p></article>
    <article><h3>3. 매몰 여부 확인 후보의 계산</h3><p>원본 토사 이동 면 안에 있는 ‘파괴’ 또는 ‘손상’ 건물 점을 추려, 그 점을 포함하는 250m 격자를 표시했습니다. 샤프루베시는 건물 점 335개·19개 격자, 티무레는 403개·27개 격자입니다. ‘손상 가능성’ 점은 후보 계산에서 제외했습니다. 격자 전체가 매몰됐다는 뜻이 아닙니다.</p><p>번호는 북→남, 서→동 공간순입니다. 매몰 가능성·시급성 점수는 산출하지 않았습니다. 토사 두께, 사람의 재실, 현재 수색 상태가 없어 매몰·생존 확률을 계산할 수 없습니다.</p></article>
    <article><h3>4. 한국팀 브리핑에서 활용하는 방법</h3><p>구역 번호·좌표·판독 날짜로 장소를 먼저 일치시키고, 현지 지휘기관의 수색 이력·실종 및 재실 정보와 대조하세요. 접근·장비·팀 배치는 현장 확인 결과를 바탕으로 지휘부가 결정해야 합니다. 이 화면의 중심 좌표는 집결지·안전한 진입점이 아닙니다.</p><p>OpenStreetMap의 도로·탐방로·건물 외곽·지명을 함께 표시했습니다(지도 자료 2026.09.06 기준). 선은 도로의 위치일 뿐 현재 통행 가능·교량 존치·구조 접근 경로를 뜻하지 않습니다. 건물 외곽은 OSM 자료이고 색으로 표시한 피해 점은 CEMS 판독입니다. 서로 다른 자료이므로 외곽에 피해 등급이나 높이를 자동으로 부여하지 않았습니다. OSM 하천 선도 현재 유로·수위를 보여주지 않습니다. 현장 사면 변화나 위성에서 보이지 않는 피해가 있을 수 있어 표시가 없는 곳을 안전한 곳으로 볼 수 없습니다.</p></article></div>
    <p class="terrain-attribution">Contains modified Copernicus Sentinel data (2026), via Element 84 Earth Search. Contains modified Copernicus Emergency Management Service information (2026), EMSR927 AOI01/02 GRA v1. © European Union. SRTM data courtesy of the U.S. Geological Survey, via Mapzen Terrain Tiles. © OpenStreetMap contributors.</p>
    <div class="terrain-source-links"><a href="https://registry.opendata.aws/sentinel-2-l2a-cogs/">Sentinel-2 영상 출처</a><a href="./data/map-detail/manifest.json">상세 지도 자료·체크섬</a><a href="https://ihp-wins.unesco.org/en/dataset/damage-grading-syapru-besi-and-timure-rasuwa-district-nepal-27-august-2026">UNESCO 배포 원자료</a><a href="https://mapping.emergency.copernicus.eu/activations/EMSR927/">Copernicus EMSR927</a><a href="https://mapping.emergency.copernicus.eu/terms-and-conditions/">CEMS 이용 조건</a><a href="https://github.com/tilezen/joerd/blob/master/docs/data-sources.md">지형 출처·품질</a><a href="https://www.openstreetmap.org/copyright">OSM · ODbL</a><a href="./data/terrain/manifest.json">모델 자료·체크섬</a></div>
  </details>
</section>
<!-- TERRAIN_MODEL_END -->'''
source=PAGE.read_text(encoding='utf-8')
if '<!-- TERRAIN_MODEL_START -->' in source:
    source=re.sub(r'<!-- TERRAIN_MODEL_START -->.*?<!-- TERRAIN_MODEL_END -->',lambda _:html,source,flags=re.S)
else:
    # Keep the Texas preface, but place it after the working map to expose the model first.
    preface=re.search(r'<!-- PROJECT_PREFACE_START -->.*?<!-- PROJECT_PREFACE_END -->',source,re.S).group()
    source=source.replace(preface,'')
    intro_end=source.index('</section>',source.index('<section class="response-intro'))+len('</section>')
    source=source[:intro_end]+'\n'+html+'\n'+preface+source[intro_end:]
    source=source.replace('<link rel="stylesheet" href="./briefing.css?v=2">','<link rel="stylesheet" href="./briefing.css?v=2">\n  <link rel="stylesheet" href="./terrain.css?v=3">')
    source=source.replace('</body>','<script type="module" src="./terrain.mjs?v=3"></script>\n</body>')
    source=source.replace('<nav class="rescue-jumps" aria-label="구조대원 참고정보">','<nav class="rescue-jumps" aria-label="구조대원 참고정보"><a href="#terrain">3D 피해 지형</a>')
    source=source.replace('fetchpriority="high" alt="2026년 8월 27일','loading="lazy" alt="2026년 8월 27일')
PAGE.write_text(source,encoding='utf-8')
print('Rendered terrain model, source explanations and fallback tables.')
