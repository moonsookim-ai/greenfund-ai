// Read-only HTTP release verification; no calls to emergency agencies or browser APIs.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const origin=process.argv[2] || 'https://greenfund.ai.kr';
const commonHeaderCSS='/site-header.css?v=3';
const terrainManifest=JSON.parse(readFileSync(new URL('../greenproof/web/nepal/data/terrain/manifest.json',import.meta.url),'utf8'));
const detailManifest=JSON.parse(readFileSync(new URL('../greenproof/web/nepal/data/map-detail/manifest.json',import.meta.url),'utf8'));
const terrainPaths=['/nepal/terrain.mjs?v=3','/nepal/terrain-model.mjs?v=3','/nepal/terrain.css?v=3',...['manifest.json',...Object.keys(terrainManifest.files)].map(f=>'/nepal/data/terrain/'+f),...['manifest.json',...Object.keys(detailManifest.files)].map(f=>'/nepal/data/map-detail/'+f)];
const paths=['/','/mangrove/','/emissions/','/nepal/','/nepal/field/','/nepal/field/index.html','/nepal/handoff/','/nepal/app.mjs?v=4','/nepal/briefing.mjs?v=2','/nepal/briefing.css?v=2','/nepal/field.mjs?v=1','/nepal/field-model.mjs?v=1','/nepal/rescue.css?v=1','/nepal/response.css?v=3','/nepal/satellite.mjs?v=2','/lab.css?v=3','/nepal/data/responder-briefing.json','/nepal/data/source-analyses.json','/nepal/data/field-contacts.json','/nepal/data/snapshot.json?v=2','/nepal/images/sentinel2-2026-08-27.jpg'];
const results=await Promise.allSettled([...paths,commonHeaderCSS,...terrainPaths,'/nepal/og.png?v=1'].map(async path=>{
  if(path==='/'){
    const entry=await fetch(origin+'/',{redirect:'manual',signal:AbortSignal.timeout(25000),cache:'no-cache'});
    assert.equal(entry.status,302,'Homepage redirects before serving HTML');
    assert.equal(new URL(entry.headers.get('location'),origin).pathname,'/nepal/');
  }
  const response=await fetch(origin+path,{signal:AbortSignal.timeout(25000),cache:'no-cache'});
  assert.equal(response.status,200,path);
  const type=response.headers.get('content-type') || '';
  if(path==='/nepal/og.png?v=1'){
    assert.match(type,/image\/png/);
    const bytes=Buffer.from(await response.arrayBuffer());
    assert.equal(bytes.subarray(1,4).toString(),'PNG');
    assert.equal(bytes.readUInt32BE(16),1200);assert.equal(bytes.readUInt32BE(20),630);
    const local=readFileSync(new URL('../greenproof/web/nepal/og.png',import.meta.url));
    assert.equal(createHash('sha256').update(bytes).digest('hex'),createHash('sha256').update(local).digest('hex'));
    return `${path}: 1200 × 630 PNG, verified ${bytes.length} bytes`;
  }
  if(path.startsWith('/nepal/data/terrain/') || path.startsWith('/nepal/data/map-detail/')){
    const bytes=new Uint8Array(await response.arrayBuffer());
    const local=readFileSync(new URL('../greenproof/web'+path,import.meta.url));
    assert.equal(createHash('sha256').update(bytes).digest('hex'),createHash('sha256').update(local).digest('hex'),path+' exact terrain data deployed');
    if(path.endsWith('.u16'))assert.match(type,/application\/octet-stream/);
    if(path.endsWith('.webp'))assert.match(type,/image\/webp/);
    return `${path}: verified ${bytes.length} bytes`;
  }
  if(path.endsWith('.jpg')){
    assert.match(type,/image\/jpeg/);
    const bytes=new Uint8Array(await response.arrayBuffer());
    assert.equal(bytes[0],255);assert.equal(bytes[1],216);return `${path}: JPEG ${bytes.length} bytes`;
  }
  const text=await response.text();
  if(path.endsWith('/') || path.endsWith('index.html')){
    assert.match(type,/text\/html/);
    assert.equal((text.match(/김문수/g)||[]).length,1);
    assert.ok(text.indexOf('김문수')>text.indexOf('<footer'));
    const nav=/<nav\b[^>]*aria-label="(?:주 메뉴|Main navigation)"[^>]*>([\s\S]*?)<\/nav>/.exec(text)?.[1];
    assert.ok(nav,path+' navigation');
    assert.ok(nav.indexOf('네팔상황실')<nav.indexOf('맹그로브 성장 기록'));
    assert.ok(nav.indexOf('맹그로브 성장 기록')<nav.indexOf('우리 동네 온실가스 배출'));
    const header=/<header\b[^>]*>[\s\S]*?<\/header>/.exec(text)?.[0];
    const pagePath=path==='/'?'/nepal/':path;
    const localPage=readFileSync(new URL('../greenproof/web'+pagePath+(pagePath.endsWith('/')?'index.html':''),import.meta.url),'utf8');
    assert.equal(header,/<header\b[^>]*>[\s\S]*?<\/header>/.exec(localPage)?.[0],'Exact shared header deployed');
    assert.ok(header.includes('class="gp-site-header"'));
    assert.ok(!header.includes('<small') && header.includes('<span>AI</span>환경연구소'),'New name without logo subtitle');
    assert.ok(!text.includes('GREEN PROOF') && !text.includes('GREEN <'),'Previous site name removed');
    assert.ok(nav.includes('/mangrove/#app'),'Mangrove menu points to its new page');
    const active=[...nav.matchAll(/<a\b[^>]*aria-current="page"[^>]*>(.*?)<\/a>/g)];
    assert.equal(active.length,1,'One selected main menu');
    assert.equal(active[0][1],path==='/mangrove/'?'맹그로브 성장 기록':path==='/emissions/'?'우리 동네 온실가스 배출':'네팔상황실');
    if(['/','/mangrove/','/emissions/','/nepal/'].includes(path))assert.ok(text.includes(commonHeaderCSS));
    if(pagePath==='/nepal/'||path.startsWith('/nepal/field/')){
      const analyses=JSON.parse(readFileSync(new URL('../greenproof/web/nepal/data/source-analyses.json',import.meta.url),'utf8'));
      assert.ok(text.includes(analyses.preface.body));
      for(const item of analyses.articles)assert.ok(text.includes(`id="analysis-${item.id}"`));
      assert.ok(text.includes('data-analysis-expand'));
      assert.ok(!/<a\b[^>]*class="brief-source"[^>]*target=/.test(text));
    }
    if(pagePath==='/nepal/'){
      const metadata=page=>[...page.matchAll(/<meta\s+(?:property|name)="((?:og:|twitter:)[^"]+)"\s+content="([^"]*)"/g)].map(m=>[m[1],m[2]]);
      assert.deepEqual(metadata(text),metadata(localPage),'Exact Nepal sharing metadata deployed');
      const meta=Object.fromEntries(metadata(text));
      assert.equal(meta['og:image'],'https://greenfund.ai.kr/nepal/og.png?v=1');
      assert.equal(meta['twitter:image'],meta['og:image']);
      assert.equal(meta['twitter:card'],'summary_large_image');
      assert.equal(meta['twitter:title'],meta['og:title']);assert.equal(meta['twitter:description'],meta['og:description']);
      assert.ok(text.indexOf('id="terrain"')<text.indexOf('id="project-preface"'));
      assert.ok(text.includes('id="terrain-canvas"'));
      assert.ok(text.includes('data-terrain-basemap="satellite"'));
      assert.ok(text.includes('id="terrain-fullscreen"'));
      for(const area of terrainManifest.scenes)assert.ok(text.includes(`data-terrain-table="${area.id}"`));
      for(const id of ['strategy','regional-actions','emergency-contacts','field-support','satellite-after'])assert.ok(text.includes(`id="${id}"`),id);
      assert.ok(text.includes('tel:1234'));assert.ok(text.includes('briefing.mjs?v=2'));
      assert.ok(text.includes('한국 구조대원'));
      assert.ok(!/<(?:div|section)\b[^>]*\bdata-field-tool/.test(text));
      assert.ok(text.indexOf('id="strategy"')<text.indexOf('id="method"'));
    }
    if(path==='/mangrove/'){
      assert.ok(text.includes('fetch("/data/index.json"'));
      assert.ok(text.includes('fetch(`/data/${id}/report.json`'));
      assert.ok(text.includes('href="https://greenfund.ai.kr/mangrove/"'));
      const indexResponse=await fetch(origin+'/data/index.json',{signal:AbortSignal.timeout(25000)});
      assert.equal(indexResponse.status,200);
      const index=await indexResponse.json();
      for(const site of index.sites){
        const dataRoot=origin+'/data/'+site.id+'/';
        const reportResponse=await fetch(dataRoot+'report.json',{signal:AbortSignal.timeout(25000)});
        assert.equal(reportResponse.status,200);
        const report=await reportResponse.json();
        const frame=await fetch(dataRoot+report.frames.at(-1),{method:'HEAD',signal:AbortSignal.timeout(25000)});
        assert.equal(frame.status,200);assert.match(frame.headers.get('content-type'),/image\//);
      }
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
