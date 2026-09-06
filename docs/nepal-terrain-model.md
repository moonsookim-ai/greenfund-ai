# 네팔 3D 지형 · 구조 참고 모델

## 시각화 계약

- 목적: 한국 구조대원이 라수와의 샤프루베시·티무레 지형과 위성 판독 피해를 같은 위치에서 대조한다. 첫 화면에 배치한다.
- 지형: Mapzen Terrarium의 SRTM 표고를 지역 좌표(동·북 방향, m)로 재표본화한다. 원래 지형은 2000년 관측 기반이며 2026년 홍수 뒤 지형이 아니다. 격자 간격과 원자료의 명목 품질 약 90m를 구분한다. 기본 수직 배율은 1배다.
- 상세 배경: Sentinel-2C `S2C_45RUM_20260812_0_L2A`의 10m TCI를 EPSG:32645에서 기존 지역 격자에 맞는 EPSG:4326 영상으로 재투영한다. 색상은 bilinear, 20m SCL 마스크는 nearest로 처리한다. 구름(8/9/10)·결측(0)·불량(1)은 투명 처리하며 지형을 복원하지 않는다. 두 장면에서 구름·결측 비율 0%를 확인했다. 2026-08-12 홍수 전 배경과 2026-08-27 피해 판독을 화면에서 별도로 명시한다. 10m 영상 픽셀은 표고 정확도가 아니다.
- 지도 맥락: 2026-09-06 OSM 도로·탐방로·건물 외곽·지명을 별도 ODbL 데이터로 제공한다. 통행 상태·건물 높이는 null이다. CEMS 건물 피해 점과 OSM 외곽을 자동 연결하거나 외곽에 피해 등급을 부여하지 않는다. 불완전한 OSM 건물 폴리곤은 제외한다.
- 관측: Copernicus EMSR927 AOI01/02 Grading v1의 2026-08-27 위성 판독 토사 이동 폴리곤, 피해 건물 점, 판독 범위. 건물 점은 건물 외곽선·사람 위치가 아니다. 위성 원영상 자체는 재배포하지 않는다.
- 분석: 원본 토사 폴리곤과 Destroyed/Damaged 건물 점의 공간 중첩을 계산하고, 해당 점을 포함한 250m 격자를 표시한다. Possibly damaged는 후보 계산에서 제외하되 별도 기호로 표시한다. 격자 번호는 북→남, 서→동 공간순이며 순위가 아니다. 매몰·재실·생존·미수색 여부는 모두 미확인이다. 토사의 퇴적과 침식을 구별하지 못한다.
- 색과 형태: 주황 면=위성 판독 토사 이동, 빨강 사각=파괴 건물, 갈색 원=손상 건물, 빈 마름모=손상 가능성, 보라 격자=중첩 확인 후보, 파랑 선=OSM 하천 위치, 점선=판독 범위. 색만으로 구분하지 않는다.
- 상호작용: 기본 2배·선택 구역 4.5배·최대 10배 확대, 회전·지도 이동·수직 배율·위에서 보기·지역 선택·레이어 토글·격자 선택. 근접 시에는 해당 지점 표고에 카메라 중심을 맞춘다. 표시 텍스처는 기본 2048px, 3배 이상에서 최대 4096px(기기 한도 적용)으로 그리며 원자료의 해상도나 정확도는 바꾸지 않는다. 후보를 선택하면 중첩 건물 수, 중심 좌표, 대조할 현장 정보가 나타난다. 방향·거리·기준일을 함께 표시한다.
- 한계: 실시간 침수 범위·수심·토사 두께·매몰 확률·안전 경로를 추정하지 않는다. 영역 밖은 미판독이다. 관측 피해가 많다는 이유로 구조 순위를 매기지 않는다.
- 접근성·성능: 네트워크 없이도 설명·후보 표를 읽을 수 있도록 HTML로 제공한다. WebGL 실패 시 정적 평면도와 표로 전환한다. 외부 지도 SDK·자동 회전·연속 렌더링 없이 사용자 조작 시에만 그린다. 지역 자료는 선택 시 불러온다.

## 재생성

`python tools/build_nepal_terrain.py` (Python, requests, numpy, Pillow, shapely, pyshp 필요). `out/terrain`에 공개 원자료를 캐시한다. 첫 실행은 공개 다운로드를 수행하며, 이후 캐시를 사용한다. 릴리스 파일과 원본 체크섬·시점·변환 방식은 `greenproof/web/nepal/data/terrain/manifest.json`에 기록한다.

`python tools/build_nepal_map_detail.py` (추가 의존성 rasterio)로 상세 배경과 OSM 도형을 생성하고, `python tools/build_nepal_terrain_section.py`로 한글 설명을 갱신한다. 출력은 `data/map-detail/`에 분리한다. 영상 좌표·원본 URL·장면 식별자·잘라낸 배열의 체크섬·구름 비율을 각 지역 JSON에 기록한다. HTTP Range 기반 원본 읽기로 전체 위성 장면을 내려받지 않는다. 표시용 영상은 약 75KB WebP이며, 지도·건물 외곽은 정적 벡터로 제공한다.

전체 폭의 지도, 전체 화면 보기, 화면 크기를 유지하는 구역·지명 라벨을 제공한다. 라벨은 지형에 가려지는 위치와 겹치는 라벨을 제외한다. 선택한 구역부터 표시한다. 100m 등고선은 실제 렌더링과 같은 DEM 삼각형의 교차선으로 계산하며 선택적으로 표시한다.

공간 중첩은 단순화 전 원본 도형으로 계산한다. 화면용 토사 도형만 3m 허용오차로 단순화한다. DEM의 RGB 표고 변환, 원본 좌표계, 중복 건물 좌표, 결측·범위, 후보 제외 규칙과 표/모델 집계를 검사한다. 빌드 스크립트와 테스트가 재현 가능한 분석 기록이다.

## 출처·권리

- CEMS 원제품: https://mapping.emergency.copernicus.eu/activations/EMSR927/
- UNESCO IHP-WINS 공개 배포: https://ihp-wins.unesco.org/en/dataset/damage-grading-syapru-besi-and-timure-rasuwa-district-nepal-27-august-2026
- CEMS 이용 조건: https://mapping.emergency.copernicus.eu/terms-and-conditions/
- DEM 출처와 품질: https://github.com/tilezen/joerd/blob/master/docs/data-sources.md
- 표고 인코딩: https://github.com/tilezen/joerd/blob/master/docs/formats.md
- OSM: https://www.openstreetmap.org/copyright (ODbL). 하천 레이어는 별도 파일로 배포한다.
- Sentinel-2 COG: https://registry.opendata.aws/sentinel-2-l2a-cogs/
- 사용 장면: https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2C_45RUM_20260812_0_L2A

Contains modified Copernicus Emergency Management Service information (2026), EMSR927 AOI01/02 GRA v1. © European Union. SRTM data courtesy of the U.S. Geological Survey, via Mapzen Terrain Tiles. © OpenStreetMap contributors.

Contains modified Copernicus Sentinel data (2026), via Element 84 Earth Search.
