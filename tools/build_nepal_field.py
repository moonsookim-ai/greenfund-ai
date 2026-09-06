"""Build source-backed contact cards and a standalone, offline-capable field tool.

No runtime bundler/dependencies. The generated HTML is committed and deployable.
Run after changing field contacts, either field module, or either bundled stylesheet.
"""
from pathlib import Path
from html import escape
import json
import re
from site_header import site_header

ROOT = Path(__file__).resolve().parents[1]
NEPAL = ROOT/'greenproof/web/nepal'
registry = json.loads((NEPAL/'data/field-contacts.json').read_text(encoding='utf-8'))

def contacts(lang):
    suffix = 'Ko' if lang == 'ko' else 'En'
    cards = []
    for row in registry['contacts']:
        alternate = ''
        if 'alternate' in row:
            alternate = f'<a class="alternate" href="tel:{escape(row["alternateDial"])}">{escape(row["alternate"])}</a>'
        cards.append(f'''<article class="contact-card"><h3>{escape(row['name'+suffix])}</h3><small>{escape(row['scope'+suffix])}</small><a class="contact-number" href="tel:{escape(row['dial'])}" aria-label="{'전화' if lang == 'ko' else 'Call'} {escape(row['name'+suffix])} {escape(row['number'])}">{escape(row['number'])}</a>{alternate}<p>{escape(row['purpose'+suffix])}</p><small><a href="{escape(row['source'])}" target="_blank" rel="noopener noreferrer">{escape(row['publisher'])} ↗</a> · {registry['verifiedOn']}</small></article>''')
    return '<div class="contact-grid">\n'+'\n'.join(cards)+'\n</div>'

css = '\n'.join((NEPAL/name).read_text(encoding='utf-8') for name in ['style.css','rescue.css'])
css += '\n'+(NEPAL.parent/'site-header.css').read_text(encoding='utf-8')
modules = []
for name in ['field-model.mjs','field.mjs']:
    module = (NEPAL/name).read_text(encoding='utf-8')
    module = re.sub(r'^import .*?;\n', '', module, flags=re.M)
    module = re.sub(r'^export ', '', module, flags=re.M)
    modules.append(module)
script = '\n'.join(modules)
assert '</script' not in script.lower()
page = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nepal flood · Field handoff kit | GREEN PROOF</title><meta name="description" content="Official contacts and a private, offline-capable rescue handoff draft. No automatic dispatch. GREEN PROOF, Korea Green Foundation.">
<link rel="canonical" href="https://greenfund.ai.kr/nepal/handoff/"><meta name="theme-color" content="#123c35">
<style>__CSS__</style></head><body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header"><div class="header-inner"><a class="brand" href="https://greenfund.ai.kr/">GREEN <span>PROOF</span><small lang="ko">환경재단이 운영하는 AI환경연구소</small></a><nav aria-label="Main navigation"><a href="https://greenfund.ai.kr/nepal/">네팔상황실</a><a href="https://greenfund.ai.kr/#app">맹그로브 성장 기록</a><a href="https://greenfund.ai.kr/emissions/">우리 동네 온실가스 배출</a></nav></div></header>
<main id="main" class="field-page">
<section class="response-intro"><p class="field-note">GREEN PROOF · AI Environmental Research Institute operated by Korea Green Foundation</p><h1>Nepal flood<br>Field handoff kit</h1><p>Contact an agency, describe the location and situation, then confirm receipt. This tool prepares a draft. It does not submit a rescue request or dispatch responders.</p>
<div class="actions"><a class="button primary" href="#contacts">Emergency contacts</a><a class="button" href="#field-support">Prepare handoff</a><a class="button" href="https://greenfund.ai.kr/nepal/#strategy" lang="ko">한국어 실행안</a></div>
</section>
<div class="offline-note"><strong>Low bandwidth / offline use</strong><p>This page has no images, external fonts or background data requests. <a href="https://greenfund.ai.kr/nepal/handoff/index.html" download="greenproof-nepal-handoff.html">Save the standalone HTML file</a> while connected, then open that file to write drafts offline. Telephone service, official updates and external maps still need connectivity. Device location and automatic copy may be unavailable in a local file; manual entry and text download remain available.</p><p>Entries are not saved automatically. Download your text or JSON before closing or reloading. Share exported location and contact information only with responders who need it.</p></div>
<section id="contacts" class="section rescue-section"><h2>Official contacts</h2><p class="field-note">Public numbers checked 5 September 2026. No test calls made. Short codes are for use within Nepal; availability depends on the network and local services.</p>
__CONTACTS__
<div class="official-updates"><strong>Recheck current conditions with local authorities.</strong><p><a href="https://www.dhm.gov.np/">DHM weather / flood advice</a> · <a href="https://daorasuwa.moha.gov.np/en/post/sa-cana-b-dha-sadaka-mara-mata-ka-ra-yaka-l-ga-sava-ra-aava-gamana-aa-sha-ka-ra">Rasuwa partial traffic closure notice, 5 September</a> · <a href="https://daonuwakot.moha.gov.np/">Nuwakot district updates and disaster contact notice</a></p><p>Read the original closure notice for affected sections and times, then confirm with the local agency. This is not a live road or evacuation map.</p></div>
<p>If a call fails, try another appropriate official contact or ask a reachable local partner to relay it. Confirm receipt and agree on a next contact time.</p>
</section>
<section class="section"><h2>What to do first</h2><ol><li><strong>Report immediate danger first.</strong> Give a place or landmark, when the situation was observed, people needing help if known, and observed isolation or injury. Unknown details should not delay the call.</li><li><strong>Confirm who received the request.</strong> Record the agency and its reference or response. Distinguish attempted contact from acknowledged receipt. Check possible duplicate reports with the receiving agency.</li><li><strong>Coordinate movement and handover.</strong> Ask the responsible local authority and trained responders about access, current warnings, medical or shelter acceptance, and team communications. Do not enter floodwater or damaged structures to collect information.</li><li><strong>Follow through on relief.</strong> Confirm safe water and hygiene needs, actual receipt of supplies, and who will arrange the next delivery. Aid scores do not determine rescue or medical priority.</li></ol><p class="field-note">Suggested coordination workflow by GREEN PROOF. Local authorities and trained responders make operational decisions. No arrival time, capacity or route clearance is confirmed by this page.</p></section>
<section id="field-support" class="section rescue-section"><h2>Record and share what you know</h2><div data-field-tool data-lang="en"><p>Loading the draft tool. Official contacts above work without JavaScript.</p></div><noscript><p>JavaScript is needed for the draft tool. Over the phone, give location, observation time, situation, people needing help, requested support and a callback contact. Confirm the agency received it.</p></noscript></section>
<footer><div><strong>GREEN PROOF</strong><p class="field-note">Research, model design and implementation with GPT-6 Astra.<br>Official contact sources checked 2026-09-05. Records are user-entered.</p></div><!--email_off--><small class="research-contact" lang="ko">연구 문의 · 연구책임자 김문수 교수 · <a href="mailto:mskim@ceobizschool.kr">mskim@ceobizschool.kr</a></small><!--/email_off--></footer>
</main><script type="module">__SCRIPT__</script></body></html>
'''
page = page.replace('__CSS__', css).replace('__CONTACTS__', contacts('en')).replace('__SCRIPT__', script)
page = re.sub(r'<header\b[^>]*>.*?</header>',site_header('nepal',absolute=True),page,count=1,flags=re.S)
(NEPAL/'handoff').mkdir(exist_ok=True)
(NEPAL/'handoff/index.html').write_text(page, encoding='utf-8')
print(f'Built secondary handoff tool ({len(page.encode("utf-8")):,} bytes).')
