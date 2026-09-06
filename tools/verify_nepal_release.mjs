// Read-only HTTP release verification; no calls to emergency agencies or browser APIs.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const origin=process.argv[2] || 'https://greenfund.ai.kr';
const commonHeaderCSS='/site-header.css?v=1';
const paths=['/','/emissions/','/nepal/','/nepal/field/','/nepal/field/index.html','/nepal/handoff/','/nepal/app.mjs?v=4','/nepal/briefing.mjs?v=2','/nepal/briefing.css?v=2','/nepal/field.mjs?v=1','/nepal/field-model.mjs?v=1','/nepal/rescue.css?v=1','/nepal/response.css?v=2','/lab.css?v=3','/nepal/data/responder-briefing.json','/nepal/data/source-analyses.json','/nepal/data/field-contacts.json','/nepal/data/snapshot.json?v=2','/nepal/images/sentinel2-2026-08-27.jpg'];
const results=await Promise.allSettled([...paths,commonHeaderCSS].map(async path=>{
  const response=await fetch(origin+path,{signal:AbortSignal.timeout(25000),cache:'no-cache'});
  assert.equal(response.status,200,path);
  const type=response.headers.get('content-type') || '';
  if(path.endsWith('.jpg')){
    assert.match(type,/image\/jpeg/);
    const bytes=new Uint8Array(await response.arrayBuffer());
    assert.equal(bytes[0],255);assert.equal(bytes[1],216);return `${path}: JPEG ${bytes.length} bytes`;
  }
  const text=await response.text();
  if(path.endsWith('/') || path.endsWith('index.html')){
    assert.match(type,/text\/html/);
    assert.ok(text.includes('환경재단이 운영하는 AI환경연구소'));
    assert.equal((text.match(/김문수/g)||[]).length,1);
    assert.ok(text.indexOf('김문수')>text.indexOf('<footer'));
    const nav=/<nav\b[^>]*aria-label="(?:주 메뉴|Main navigation)"[^>]*>([\s\S]*?)<\/nav>/.exec(text)?.[1];
    assert.ok(nav,path+' navigation');
    assert.ok(nav.indexOf('네팔상황실')<nav.indexOf('맹그로브 성장 기록'));
    assert.ok(nav.indexOf('맹그로브 성장 기록')<nav.indexOf('우리 동네 온실가스 배출'));
    const header=/<header\b[^>]*>[\s\S]*?<\/header>/.exec(text)?.[0];
    const localPage=readFileSync(new URL('../greenproof/web'+path+(path.endsWith('/')?'index.html':''),import.meta.url),'utf8');
    assert.equal(header,/<header\b[^>]*>[\s\S]*?<\/header>/.exec(localPage)?.[0],'Exact shared header deployed');
    assert.ok(header.includes('class="gp-site-header"'));
    const active=[...nav.matchAll(/<a\b[^>]*aria-current="page"[^>]*>(.*?)<\/a>/g)];
    assert.equal(active.length,1,'One selected main menu');
    assert.equal(active[0][1],path==='/'?'맹그로브 성장 기록':path==='/emissions/'?'우리 동네 온실가스 배출':'네팔상황실');
    if(path==='/'||path==='/emissions/'||path==='/nepal/')assert.ok(text.includes(commonHeaderCSS));
    if(path==='/nepal/'||path.startsWith('/nepal/field/')){
      const analyses=JSON.parse(readFileSync(new URL('../greenproof/web/nepal/data/source-analyses.json',import.meta.url),'utf8'));
      assert.ok(text.includes(analyses.preface.body));
      for(const item of analyses.articles)assert.ok(text.includes(`id="analysis-${item.id}"`));
      assert.ok(text.includes('data-analysis-expand'));
      assert.ok(!/<a\b[^>]*class="brief-source"[^>]*target=/.test(text));
    }
    if(path==='/nepal/'){
      for(const id of ['strategy','regional-actions','emergency-contacts','field-support','satellite-after'])assert.ok(text.includes(`id="${id}"`),id);
      assert.ok(text.includes('tel:1234'));assert.ok(text.includes('briefing.mjs?v=2'));
      assert.ok(text.includes('한국 구조대원'));
      assert.ok(!/<(?:div|section)\b[^>]*\bdata-field-tool/.test(text));
      assert.ok(text.indexOf('id="strategy"')<text.indexOf('id="method"'));
    }
    if(path.includes('/field/') || path.includes('/handoff/')){
      if(path.includes('/field/')) {
        assert.ok(text.includes('<html lang="ko">'));
        assert.ok(text.includes('data-brief-filter'));
        assert.ok(!/<form\b/.test(text));
      } else assert.ok(text.includes('NOT_SENT_BY_THIS_TOOL'));
      assert.ok(!/<script\b[^>]*\bsrc=/.test(text),'Saved field tool must not depend on injected scripts');
      assert.ok(!/\bdata-cfemail=/.test(text),'Offline contact must not need email decode script');
      assert.ok(text.includes('mailto:mskim@ceobizschool.kr'));
      const servedScript=/<script type="module">([\s\S]*?)<\/script>/.exec(text)?.[1];
      const localHTML=readFileSync(new URL(`../greenproof/web/nepal/${path.includes('/handoff/')?'handoff':'field'}/index.html`,import.meta.url),'utf8');
      const localScript=/<script type="module">([\s\S]*?)<\/script>/.exec(localHTML)?.[1];
      assert.equal(servedScript?.replace(/\r\n/g,'\n'),localScript?.replace(/\r\n/g,'\n'),'Exact bundled logic deployed');
    }
  }else if(path.includes('.mjs') || path.includes('.css')){
    assert.match(type,path.includes('.mjs')?/javascript/:/text\/css/);
    const local=readFileSync(new URL('../greenproof/web'+path.split('?')[0],import.meta.url),'utf8');
    assert.equal(text.replace(/\r\n/g,'\n'),local.replace(/\r\n/g,'\n'),path+' deployed source');
  }else if(path.includes('field-contacts')){
    const data=JSON.parse(text);assert.equal(data.verifiedOn,'2026-09-05');assert.equal(data.contacts.length,5);
  }else if(path.includes('responder-briefing')){
    const data=JSON.parse(text);assert.ok(data.audience.includes('한국 구조대원'));assert.ok(data.medical.every(m=>m.capacity===null));
  }else if(path.includes('source-analyses')){
    const local=JSON.parse(readFileSync(new URL('../greenproof/web/nepal/data/source-analyses.json',import.meta.url),'utf8'));
    assert.deepEqual(JSON.parse(text),local);
  }else if(path.includes('snapshot')){
    const data=JSON.parse(text);assert.ok(data.regions.every(r=>Object.values(r.inputs).every(v=>v===null)));
  }
  return path;
}));
let failed=false;
for(const result of results){if(result.status==='fulfilled')console.log('PASS',result.value);else{failed=true;console.error('FAIL',result.reason);}}
if(failed)process.exitCode=1;
