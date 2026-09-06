"""One header for every GREEN PROOF page, including standalone briefs."""

MENU=(('nepal','/nepal/','네팔상황실'),('mangrove','/mangrove/#app','맹그로브 성장 기록'),('emissions','/emissions/','우리 동네 온실가스 배출'))

def site_header(current, absolute=False):
    assert current in {item[0] for item in MENU}
    origin='https://greenfund.ai.kr' if absolute else ''
    links=''.join(f'<a href="{origin}{path}"'+(' aria-current="page"' if key==current else '')+f'>{label}</a>' for key,path,label in MENU)
    return f'''<header class="gp-site-header" lang="ko"><div class="gp-header-inner"><a class="gp-brand" href="{origin}/">GREEN <span>PROOF</span></a><nav class="gp-main-nav" aria-label="주 메뉴">{links}</nav></div></header>'''
