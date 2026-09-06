"""Check the static release without installing browser or frontend dependencies."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote
from collections import Counter
import json
import re
import subprocess
import tempfile
from site_header import site_header

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'greenproof/web'
snapshot=json.loads((WEB/'nepal/data/snapshot.json').read_text(encoding='utf-8'))
dynamic_nepal_ids = {f"source-{s['id']}" for s in snapshot['sources']} | {f"region-{r['id']}" for r in snapshot['regions']} | {f"urgent-{r['id']}" for r in snapshot['focus']['regions']}

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.refs = [], []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        for field in ('href','src'):
            if field in attrs:
                self.refs.append(attrs[field])

entry = (WEB/'index.html').read_text(encoding='utf-8')
redirects = (WEB/'_redirects').read_text(encoding='utf-8')
assert re.search(r'^/ /nepal/ 302$', redirects, re.M)
assert 'http-equiv="refresh" content="0; url=/nepal/"' in entry
assert 'href="https://greenfund.ai.kr/nepal/"' in entry
assert 'https://greenfund.ai.kr/nepal/og.png?v=3' in entry
assert '<script' not in entry and '<header' not in entry
print('PASS homepage redirects directly to Nepal, with matching static fallback and sharing image')

pages = [WEB/'mangrove/index.html',WEB/'emissions/index.html',WEB/'nepal/index.html',WEB/'nepal/field/index.html',WEB/'nepal/handoff/index.html']
for file in pages:
    source = file.read_text(encoding='utf-8')
    page = Page()
    page.feed(source)
    duplicates = [i for i,n in Counter(page.ids).items() if n>1]
    assert not duplicates, (file,duplicates)
    assert 'mskim@ceobizschool.kr' in source and '김문수 교수' in source, file
    assert 'href="/nepal/"' in source or 'href="https://greenfund.ai.kr/nepal/"' in source, file
    current='mangrove' if file==WEB/'mangrove/index.html' else 'emissions' if file==WEB/'emissions/index.html' else 'nepal'
    offline=file.parent.name in ('field','handoff')
    header=re.search(r'<header\b[^>]*>.*?</header>',source,re.S).group()
    assert header==site_header(current,absolute=offline), (file,'shared header differs')
    assert '<small' not in header and '<span>AI</span>환경연구소' in header, (file,'new name without logo subtitle')
    assert 'GREEN PROOF' not in source and 'GREEN <' not in source, (file,'previous name remains')
    assert not re.search(r'href="(?:https://greenfund\.ai\.kr)?/#app"',source), (file,'old mangrove route')
    shared_css=(WEB/'site-header.css').read_text(encoding='utf-8')
    if offline:
        assert shared_css in source, (file,'missing bundled shared header CSS')
    else:
        assert '/site-header.css?v=3' in source, (file,'missing common stylesheet')
    assert not re.search(r'ocean\.js|startOcean|paintSim|id="ocean"',source), file
    # Ignore literal template expressions in inline scripts, but check every static local asset.
    for ref in page.refs:
        parsed=urlparse(ref)
        if not parsed.path and parsed.fragment and '${' not in ref:
            possible_ids = set(page.ids) | (dynamic_nepal_ids if file == WEB/'nepal/index.html' else set())
            assert unquote(parsed.fragment) in possible_ids, (file,ref,'missing page anchor')
        if parsed.scheme or parsed.netloc or not parsed.path or '${' in ref:
            continue
        target=(WEB/parsed.path.lstrip('/')) if parsed.path.startswith('/') else file.parent/parsed.path
        target=Path(unquote(str(target)))
        if target.is_dir(): target=target/'index.html'
        assert target.is_file(), (file,ref)
    for script in re.findall(r'<script\b[^>]*>(.*?)</script>',source,re.S):
        if not script.strip(): continue
        with tempfile.TemporaryDirectory(prefix='greenproof-check-') as task_temp:
            check=Path(task_temp)/'inline.mjs'
            check.write_text(script,encoding='utf-8')
            subprocess.run(['node','--check',str(check)],check=True,capture_output=True)
    print(f'PASS HTML, branding, contact, local references, inline JS: {file.relative_to(ROOT)}')

mangrove=(WEB/'mangrove/index.html').read_text(encoding='utf-8')
assert 'https://greenfund.ai.kr/mangrove/' in mangrove
assert not re.search(r'(?:fetch\(["`]|=> [`"]|href=")data/',mangrove), 'Mangrove data URLs must resolve at the site root'
assert 'fetch("/data/index.json"' in mangrove
assert 'fetch(`/data/${id}/report.json`' in mangrove
index=json.loads((WEB/'data/index.json').read_text(encoding='utf-8'))
for site in index['sites']:
    data_path=WEB/'data'/site['id']
    report=json.loads((data_path/'report.json').read_text(encoding='utf-8'))
    for asset in report['frames']+report.get('frames_raw',[])+([report['video']] if report.get('video') else []):
        assert (data_path/asset).is_file(), (site['id'],asset)
print('PASS moved mangrove page and all referenced reports, satellite frames and videos')

for file in (WEB/'nepal').glob('*.mjs'):
    subprocess.run(['node','--check',str(file)],check=True,capture_output=True)
    for ref in re.findall(r"from\s+['\"]([^'\"]+)['\"]",file.read_text(encoding='utf-8')):
        if ref.startswith('.'):
            assert (file.parent/ref.split('?')[0]).is_file(), ref
    print(f'PASS ES module syntax and imports: {file.name}')

snapshot=json.loads((WEB/'nepal/data/snapshot.json').read_text(encoding='utf-8'))
for src in snapshot['sources']:
    assert urlparse(src['url']).scheme=='https', src['id']
assert not (WEB/'ocean.js').exists()
assert not any(p.stat().st_size>25*1024*1024 for p in WEB.rglob('*') if p.is_file()), 'Cloudflare Pages per-file size limit'
print('PASS public source URLs, removed ocean file, static asset size limits')

field_kit=(WEB/'nepal/field/index.html').read_text(encoding='utf-8')
assert not re.search(r'<(?:img|link)\b[^>]*(?:src=|stylesheet)|<script\b[^>]+src=',field_kit), 'Offline kit must be standalone'
assert not re.search(r'\b(?:fetch|localStorage|sessionStorage|indexedDB)\b',field_kit), 'No background requests or persistent personal records'
assert len(field_kit.encode('utf-8')) < 100_000, 'Keep field kit lightweight'
print('PASS standalone field kit: no asset dependencies, network fetches or automatic record storage')
handoff=(WEB/'nepal/handoff/index.html').read_text(encoding='utf-8')
assert not re.search(r'<script\b[^>]+src=',handoff), 'Secondary handoff must remain standalone'
assert '<html lang="ko">' in field_kit and not re.search(r'<form\b',field_kit), 'Primary offline page is a Korean information brief'
