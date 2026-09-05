"""Check the static release without installing browser or frontend dependencies."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote
from collections import Counter
import json
import re
import subprocess
import tempfile

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

pages = [WEB/'index.html',WEB/'emissions/index.html',WEB/'nepal/index.html',WEB/'nepal/field/index.html']
for file in pages:
    source = file.read_text(encoding='utf-8')
    page = Page()
    page.feed(source)
    duplicates = [i for i,n in Counter(page.ids).items() if n>1]
    assert not duplicates, (file,duplicates)
    assert '환경재단이 운영하는 AI환경연구소' in source, file
    assert 'mskim@ceobizschool.kr' in source and '김문수 교수' in source, file
    assert 'href="/nepal/"' in source or 'href="https://greenfund.ai.kr/nepal/"' in source, file
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
