# AI네팔상황실 정방형 썸네일

- 용도: 네이버 프리미엄콘텐츠에 게시할 제작 취지 아티클의 1:1 썸네일.
- 원고: [AI네팔상황실을 만든 이유](nepal-situation-room-purpose.md).
- 이미지 파일: `greenproof/web/nepal/images/ai-nepal-square.png`.
- 공개 주소: https://greenfund.ai.kr/nepal/images/ai-nepal-square.png
- 제작 방식: 내장 `image_gen` 도구로 기존 가로형 OG 이미지의 구성을 정방형으로 재편집했다. CLI/API 대체 경로는 사용하지 않았다.
- 명칭: 아티클에 맞춰 ‘AI네팔상황실’을 사용하고 기관명과 개인 이름은 넣지 않았다.
- 산악·하천은 기존 카드의 편집 삽화를 사용한 참고 시각화이며, 실제 피해 위치나 구조 경로를 표시하지 않는다.
- 정방형은 별도 PNG로 제공하며, 웹페이지의 OG에는 가로형 이미지를 사용한다.
- 최신 요청에 따라 가로형과 정방형 모두 이미지 안의 URL 및 ‘위성영상 기반 참고 시각화’ 문구를 제거했다.
- 규격: 1254 × 1254, RGB PNG. 생성 도구가 반환한 파일을 추가 리사이즈 없이 사용했다.

## 최종 URL·캡션 삭제 프롬프트

```text
Use case: precise-object-edit / text removal. Input image is the edit target.
Keep the image perfectly square 1:1, same square size as the input.
Make ONLY these two removals:
- Remove the URL text "greenfund.ai.kr/nepal" completely.
- Remove the caption "위성영상 기반 참고 시각화" completely.
Fill those small text areas seamlessly with their existing cream background or existing mountain-and-river illustration.
Do not replace them with any other text, badge or symbol. Do not introduce a border or frame.
Preserve ALL other text exactly, preserving its font, position, size and color. Preserve the original main title, subtitle, supporting lines, any remaining original organization text, orange divider, image crop, terrain illustration, lighting and overall design. Do not change the names or wording anywhere else. Output one finished edited PNG.
```

## 정방형 재구성 프롬프트 (이력)

```text
Use case: text-localization / editorial thumbnail adaptation.
Input image 1 is the existing landscape social card to adapt.
Create exactly ONE square 1:1 image, ideally 1200 x 1200 pixels, for a Naver Premium Content article thumbnail. Recompose the design for a square; do not stretch it or crop away the words. Preserve the supplied card's calm, serious editorial style, cream background, dark forest-green Korean typography, green Himalayan mountain folds and pale branching river illustration, and small restrained orange line accent. The terrain is an editorial reference illustration, not a precise rescue map.
The accompanying article is now named "AI네팔상황실"; omit every institute/organization name and every GREEN PROOF label.
Text to render, and ONLY this text:
Largest main title, upper area: "AI네팔상황실"
Large supporting subtitle on two lines:
"한국 구조대원을 위한"
"현장 브리핑"
Smaller supporting text:
"3D 피해 지도 · 위성 전후 비교"
"한글 현장 자료"
Small domain at bottom: "greenfund.ai.kr/nepal"
Small illustration caption: "위성영상 기반 참고 시각화"
Composition: Make the main title read immediately at a small square thumbnail size. Keep all typography in a comfortable 7% inset safe area. Use ample cream space behind the title and subtitle in the upper and left areas, and mountain-and-river illustration in the lower and right areas. Typography must not be covered by the mountains. No outer border, no browser UI, no rounded card frame, no added icons.
Preserve the exact Korean spelling. Do not use "환경재단", "AI환경연구소", "GREEN PROOF", personal names, email, GPT badges, or any additional words. Do not depict or invent victims, damage locations, rescue routes, data points, or geographic coordinates. Output a finished, polished square PNG.
```
