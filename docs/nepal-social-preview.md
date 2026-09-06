# 네팔상황실 공유 미리보기

- 적용 페이지: https://greenfund.ai.kr/nepal/
- 이미지: `greenproof/web/nepal/og.png` (1200 × 630, PNG)
- 공개 이미지 URL: https://greenfund.ai.kr/nepal/og.png?v=1
- OG/X 제목: 네팔상황실 | 한국 구조대원 현장 브리핑
- OG/X 설명: 3D 피해 지도와 위성 전후 비교, 지역별 접근·위험·의료·연락 정보를 한글로 확인하세요. 환경재단 AI환경연구소 GREEN PROOF.
- 생성 방식: 내장 `image_gen` 도구, 1회 생성. CLI/API 대체 경로 사용 없음.
- 후처리: 원본 1731 × 909를 1200 × 630 RGB PNG로 크기 조정. 내용 편집·재생성 없음.
- 참고 입력: `greenproof/web/nepal/data/map-detail/syapru-sentinel.webp` (2026-08-12 Sentinel-2, Copernicus/Element 84).
- 이미지의 산악·하천은 원영상에서 영감을 얻은 편집 삽화다. 실제 피해 지점·좌표·구조 경로를 표시하거나 그 정확도를 주장하지 않는다. 카드에도 ‘위성영상 기반 참고 시각화’를 명시했다. 개인 이름·이메일·GPT 배지는 넣지 않았다.
- 검증: 한국어 문구·브랜드 시각 확인, PNG 실제 크기와 메타데이터 일치, 공유 URL의 공개 HTTP 응답 및 배포 파일 체크섬 비교. 브라우저 자동화 검사는 수행하지 않았다.
- 규격 참고: https://ogp.me/ (Open Graph protocol).

## 최종 생성 프롬프트

```text
Use case: ads-marketing.
Asset type: exactly one finished Korean social-sharing Open Graph image for GREEN PROOF Nepal situation room.
Primary request: Create one complete cohesive calm, credible editorial card at 1200×630 landscape (approximately 1.905:1). If exact pixels are unavailable, preserve that aspect ratio and keep the entire design safe within a 1200×630 crop.
Input image 1: supporting visual reference only. This is a real pre-flood Sentinel-2 crop dated 2026-08-12, showing green Himalayan mountain folds and a pale branching river. Use its mountain/river character as inspiration for the RIGHT-SIDE terrain motif only. The generated card is a branded editorial illustration, NOT an operational map; precise geography must not be implied or claimed.
Style/medium: polished Korean editorial graphic design with clean professional Korean sans-serif typography and a restrained, softly dimensional satellite-inspired mountain-and-river illustration on the right. Premium public-interest research publication, calm and helpful.
Color palette: dark forest green #193b33, cream #f5f5ee, green #166b50, muted amber #d58739. Cream main background, dark-green title and text. Green terrain. Amber is only a small typographic divider/accent, never a plotted route.
Composition: Large, very legible typography on the left, taking roughly 65% of width, with a restrained atmospheric mountain-river terrain visualization on the right. The illustration gently recedes behind the right margin without competing with the text. Strong hierarchy and generous negative space. No panels, browser chrome, cards, buttons, framed UI, charts, map legends, or map pins. Keep all text and important content at least 60 pixels from the outer edges. The main title should read instantly at a 600×315 thumbnail. Align text cleanly, with enough spacing and no overlapping.
Text: Render ONLY these exact strings, with perfect Korean glyphs, preserving spelling, spaces, punctuation, and requested line breaks:
Small upper-left brand: "GREEN PROOF"
Huge main title on a single line: "네팔상황실"
Subtitle on exactly two lines:
"한국 구조대원을 위한"
"현장 브리핑"
Supporting line: "3D 피해 지도 · 위성 전후 비교 · 한글 현장 자료"
Footer: "환경재단이 운영하는 AI환경연구소"
Small domain: "greenfund.ai.kr/nepal"
Subtle caption by the right-side illustration: "위성영상 기반 참고 시각화"
Typography priority: title largest; the two-line subtitle next; supporting line and footer clearly readable; brand/domain/caption smaller but clean. Use the supporting line beneath the subtitle, footer near the bottom left, domain along the bottom, caption near the bottom of the right illustration. Do not display the input date.
Strict constraints: Do not invent or plot damage locations, victims, rescue routes, statistics, coordinates, labels for real places, or before/after changes. No destruction imagery, no emergency emblems, no flags, no person, no person's name or email, no GPT badge, no extra words or logos. No implication that the decorative terrain is a geographically precise map. Output exactly one final image.
```
