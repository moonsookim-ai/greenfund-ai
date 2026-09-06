"""Render source-backed Korean analyses without network-dependent readers."""
from html import escape as e


def render_sources(data, analysis):
    sources={s['id']:s for s in data['sources']}
    destination={key:a['id'] for a in analysis['articles'] for key in a['sourceIds']}
    assert set(sources)==set(destination), 'Every briefing source needs an on-page analysis'

    def ref(key, page=None):
        source=sources[key]
        label=source['name']+(f' · PDF {page}쪽' if page else '')
        return f'<a class="brief-source" data-analysis-link href="#analysis-{destination[key]}">{e(label)} · 한글 해설 ↓</a>'

    p=analysis['preface']
    preface=f'''<aside class="project-preface" id="project-preface" aria-labelledby="preface-title"><span>프로젝트 서문 · 텍사스 사례</span><h2 id="preface-title">{e(p['title'])}</h2><p>{e(p['body'])}</p><a class="brief-source" data-analysis-link href="#analysis-{e(p['analysisId'])}">어떤 기여가 있었는지 · 사례와 출처 읽기 ↓</a></aside>'''
    cards=[]
    for a in analysis['articles']:
        evidence=''.join(f'<li>{e(fact)}</li>' for fact in a['facts'])
        provenance=''.join(f'''<li><b>{e(sources[key]['name'])}</b><span>{e(sources[key]['date'] or '게시일 미표시')} · {e(sources[key]['locator'])}</span><a href="{e(sources[key]['url'])}" rel="noopener noreferrer">원문 대조용 링크 · {e(sources[key]['name'])}</a></li>''' for key in a['sourceIds'])
        cards.append(f'''<details class="source-analysis" id="analysis-{e(a['id'])}" data-source-analysis><summary><span>{e(a['category'])}</span><strong>{e(a['title'])}</strong><small>한국어 해설 펼치기</small></summary><div class="analysis-body"><h4>원문에서 확인한 내용</h4><ul>{evidence}</ul><div class="analysis-meaning"><h4>한국팀 브리핑에 적용하기 <small>GREEN PROOF 해석</small></h4><p>{e(a['meaning'])}</p></div><p class="analysis-limit"><b>자료의 범위</b> {e(a['limits'])}</p><details class="analysis-provenance"><summary>근거 문서·기준일 확인</summary><ul>{provenance}</ul><p>한국어 분석 갱신 {e(analysis['updatedOn'])}. 현장 상황의 기준 시점은 각 원문의 날짜·시각을 따릅니다.</p></details><a class="analysis-top" href="#korean-source-library">한글 원문 해설 목록으로 ↑</a></div></details>''')
    library=f'''<section class="section rescue-section source-library" id="korean-source-library" aria-labelledby="source-library-title"><div class="section-head"><div><span class="section-no">원문을 읽고 정리한 한국어 해설</span><h2 id="source-library-title">해외 자료도 이곳에서 읽으세요</h2><p>지역 상황·의료·접근·국제팀 운영 문서를 한국 구조대원의 관점에서 분석했습니다. 각 항목에서 원문 내용, 현장 적용을 위한 해석, 확인되지 않은 정보를 함께 볼 수 있습니다.</p></div></div><nav class="analysis-jumps" aria-label="주요 한글 해설"><a data-analysis-link href="#analysis-roads">도로 통제</a><a data-analysis-link href="#analysis-heoc">의료·시설 피해</a><a data-analysis-link href="#analysis-policy-guide">국제팀 조정 체계</a><a data-analysis-link href="#analysis-operations-guide">수색 정보 인계</a><a data-analysis-link href="#analysis-field-guide">대원 준비·교대</a><a data-analysis-link href="#analysis-texas">텍사스 사례</a></nav><div class="analysis-tools"><label for="analysis-search">해설 검색<input type="search" id="analysis-search" placeholder="예: 병원, 통제, UCC" autocomplete="off"></label><div class="actions"><button type="button" class="button" data-analysis-expand>해설 모두 펼치기</button><button type="button" class="button" data-analysis-collapse>모두 접기</button><button type="button" class="button" data-print-brief>전체 인쇄 / PDF 저장</button></div></div><p class="field-note" data-analysis-status role="status">{len(cards)}개 한국어 해설 · 핵심 내용은 외부 사이트로 이동하지 않고 읽을 수 있습니다.</p>{''.join(cards)}</section>'''
    return ref,preface,library
