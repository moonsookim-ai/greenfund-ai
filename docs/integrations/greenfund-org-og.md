# 환경재단 AI환경연구소 페이지의 공유 미리보기

대상: https://greenfund.org/about/ai-environment-institute

## 현재 확인한 상태

2026-09-06에 서버가 보내는 HTML을 직접 확인했다.

- title / og:title: 환경재단
- description / og:description: 그린리더가 세상을 바꿉니다
- og:url: https://greenfund.org/
- og:image: /attached_assets/image_1762936763809.png (1024 × 512)
- 페이지의 공개 JavaScript는 https://greenfund.ai.kr/ 를 iframe으로 표시한다.
- 환경재단 서버 코드 저장소와 배포 설정은 아직 확인하지 못했다. 이 폴더는 적용용 자료이며, greenfund.org에 적용한 결과가 아니다.

## 적용할 정보

- 제목: AI환경연구소 | 환경재단
- 설명: AI와 공개 데이터로 환경 현장을 살펴봅니다. 네팔상황실, 맹그로브 성장 기록, 우리 동네 온실가스 배출을 한곳에서 확인하세요.
- 대표 주소: https://greenfund.org/about/ai-environment-institute
- 이미지: https://greenfund.ai.kr/nepal/og.png?v=1

이미지는 현재 iframe 첫 화면인 네팔상황실의 기존 1200 × 630 PNG를 재사용하는 안이다. 새로운 이미지가 생성된 것은 아니며, 기존 이미지에는 이전 GREEN PROOF 워드마크가 포함되어 있다. 연구소 전체를 대표할 새 이미지로 바꿀 때는 og:image와 twitter:image를 함께 갱신한다.

## 환경재단 홈페이지 담당자 적용 절차

1. `/about/ai-environment-institute` 경로에만 `greenfund-org-og-head.html`의 태그를 적용한다. 홈페이지 전체의 공통값을 바꾸지 않는다.
2. 해당 경로의 **최초 HTML 응답 안의 head**에 넣는다. iframe 안쪽 문서, 본문 편집 영역, React useEffect로 실행되는 코드에만 넣는 것으로 끝내지 않는다. 서버 템플릿 분기, 경로별 사전 렌더링 또는 서버의 HTML 응답 치환 중 현재 배포 구조에 맞는 방법을 사용한다.
3. 같은 이름의 기존 meta 태그와 canonical, title은 교체한다. 중복 태그를 덧붙이지 않는다. HTTP 상태 200으로 응답하며, 기존 iframe 화면은 유지한다.
4. 이미지 URL은 완전한 HTTPS 주소로 지정하고, 로그인이나 쿠키 없이 이미지 원본을 받을 수 있게 한다.
5. `/`와 다른 메뉴의 공유 정보는 기존 값인지 확인한다. 배포 후 공유 서비스에 남은 캐시는 각 서비스의 공유 디버거에서 갱신한다. iframe 내부 메뉴 이동만으로 바깥 주소의 공유 정보가 자동으로 달라지는 것은 아니다. 메뉴별 공유 카드가 필요하면 메뉴별 바깥 주소도 마련한다.

## 완료 확인

- JavaScript를 실행하지 않는 HTTP 요청에도 새 og:title / og:description / og:url / og:image가 들어 있다.
- 각 태그는 하나씩 있으며, og:url과 canonical은 대상 경로다.
- og:image와 twitter:image가 같은 공개 이미지 URL이다.
- 이미지 응답은 image/png, 1200 × 630이다.
- 카카오톡 등에서 해당 환경재단 주소를 공유했을 때 새 카드가 나온다. 페이지를 클릭하는 순간 이미지를 새로 생성하는 방식이 아니라, 공유 서비스가 미리 지정한 메타데이터와 이미지를 읽는 방식이다.

참고: https://ogp.me/ — Open Graph 메타데이터는 공유할 문서의 head에 정의한다.
