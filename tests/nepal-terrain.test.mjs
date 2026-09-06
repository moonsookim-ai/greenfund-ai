import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {decodeElevation,elevationAt,mesh,camera,project,rayAt,intersectTriangle,pickTerrain,candidateAt,lonLat,VIEW_ZOOM,focusOn,panGround,scaleBar,contourSegments,terrainLabelVisible} from '../greenproof/web/nepal/terrain-model.mjs';

const base=new URL('../greenproof/web/nepal/data/terrain/',import.meta.url);
const read=name=>readFileSync(new URL(name,base));
const manifest=JSON.parse(read('manifest.json'));
const scenes=manifest.scenes.map(s=>JSON.parse(read(s.url)));
const buffer=bytes=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength);
const near=(actual,expected,tolerance=1e-5)=>assert.ok(Math.abs(actual-expected)<tolerance,`${actual} != ${expected}`);
const defaults={azimuth:0,pitch:90,zoom:1,exaggeration:1};
const small={extent:[-500,-500,500,500],dem:{rows:2,columns:2,minimum:100,maximum:400}};

test('terrain release files match published source lineage and fit a small first-load budget',()=>{
  for(const [file,meta] of Object.entries(manifest.files)){
    const bytes=read(file);assert.equal(bytes.length,meta.bytes,file);
    assert.equal(createHash('sha256').update(bytes).digest('hex'),meta.sha256,file);
  }
  for(const scene of scenes){
    const bytes=read(`${scene.id}.json`).length+read(scene.dem.url).length+read(scene.riverUrl).length;
    assert.ok(bytes<110000,'Selected area data remains below 110KB uncompressed');
    assert.equal(scene.dem.acquisitionYear,2000);assert.equal(scene.observedAt,'2026-08-27T05:05:00Z');
    assert.equal(scene.fieldValidated,false);assert.equal(scene.dem.nominalSourceQualityM,90);
    assert.ok(scene.dem.sourceTiles.every(t=>t.imagerySources.startsWith('srtm/')&&t.sha256.length===64));
    assert.ok(Object.values(scene.sources).every(s=>s.crs==='EPSG:4326'&&s.url.startsWith('https://ihp-wins.unesco.org/')));
  }
  for(const key of ['burialDepth','burialProbability','liveFloodExtent','safeRoutes'])assert.equal(manifest[key],null);
});

test('little-endian elevations reject truncation and out-of-range samples; no void becomes zero',()=>{
  const meta={rows:1,columns:2,minimum:100,maximum:400};
  const data=new ArrayBuffer(4);const view=new DataView(data);view.setUint16(0,256,true);view.setUint16(2,400,true);
  assert.deepEqual([...decodeElevation(data,meta)],[256,400]);
  assert.throws(()=>decodeElevation(data.slice(0,3),meta));
  view.setUint16(0,0,true);assert.throws(()=>decodeElevation(data,meta));
  for(const scene of scenes){const values=decodeElevation(buffer(read(scene.dem.url)),scene.dem);
    assert.equal(values.length,scene.dem.rows*scene.dem.columns);assert.equal(Math.min(...values),scene.dem.minimum);
    assert.equal(Math.max(...values),scene.dem.maximum);
  }
});

test('mesh samples run north to south and picking uses the same terrain diagonal',()=>{
  const values=new Float32Array([100,200,300,400]),geometry=mesh(small,values);
  assert.deepEqual([...geometry.vertices.slice(0,3)],[-500,500,0]);
  assert.deepEqual([...geometry.vertices.slice(24,27)],[500,-500,300]);
  assert.equal(elevationAt(small,values,-500,500),100);
  assert.equal(elevationAt(small,values,500,-500),400);
  assert.equal(elevationAt(small,values,0,0),250);
  assert.equal(elevationAt(small,values,501,0),null);
  const cam=camera(small,defaults,1),point=pickTerrain(0,0,cam,geometry);
  near(point[0],0);near(point[1],0);near(point[2],150);
  for(const scene of scenes){const geo=mesh(scene,decodeElevation(buffer(read(scene.dem.url)),scene.dem));
    assert.ok(scene.dem.rows*scene.dem.columns<65536);assert.ok(Math.max(...geo.indices)<scene.dem.rows*scene.dem.columns);
    assert.equal(geo.indices.length,(scene.dem.rows-1)*(scene.dem.columns-1)*6);
  }
});

test('camera preserves east/north directions, true height by default, and selected-cell focus',()=>{
  const cam=camera(small,defaults,1);
  const center=project([0,0,150],cam),east=project([100,0,150],cam),north=project([0,100,150],cam);
  near(center[0],0);near(center[1],0);assert.ok(east[0]>0);near(east[1],0);assert.ok(north[1]>0);near(north[0],0);
  const oblique=camera(small,{...defaults,pitch:45},1);
  assert.ok(project([0,0,300],oblique)[1]>project([0,0,0],oblique)[1]);
  const focused=camera(small,{...defaults,focus:[250,-250]},1);
  near(project([250,-250,150],focused)[0],0);near(project([250,-250,150],focused)[1],0);
  const ray=rayAt(.2,-.3,oblique),hit=ray.origin.map((v,i)=>v+ray.direction[i]*oblique.depth);
  const roundtrip=project(hit,oblique);near(roundtrip[0],.2);near(roundtrip[1],-.3);
});

test('terrain intersection excludes sky / behind-camera hits and obeys nearest occlusion',()=>{
  assert.equal(intersectTriangle([0,0,10],[0,0,1],[-1,-1,0],[1,-1,0],[0,1,0]),null);
  assert.equal(intersectTriangle([5,5,10],[0,0,-1],[-1,-1,0],[1,-1,0],[0,1,0]),null);
  near(intersectTriangle([0,0,10],[0,0,-1],[-1,-1,0],[1,-1,0],[0,1,0]),10);
  const geo=mesh(small,new Float32Array([100,200,300,400])),cam=camera(small,defaults,1);
  assert.equal(pickTerrain(2,2,cam,geo),null);
  for(const scene of scenes){const values=decodeElevation(buffer(read(scene.dem.url)),scene.dem),geometry=mesh(scene,values);
    // Pick each real cell from directly above; regressions catch inverted latitude / terrain UV orientation.
    const cam=camera(scene,defaults,1.5);
    for(const cell of scene.candidates){const z=elevationAt(scene,values,...cell.center)-scene.dem.minimum;
      const projected=project([...cell.center,z],cam),hit=pickTerrain(projected[0],projected[1],cam,geometry);
      near(hit[0],cell.center[0],.01);near(hit[1],cell.center[1],.01);near(hit[2],z,.02);
      assert.equal(candidateAt(scene,hit[0],hit[1])?.id,cell.id);
    }
  }
});

test('candidate grid membership reconciles to source building counts without possibly-damaged records',()=>{
  for(const scene of scenes){
    const buildings=new Map(scene.buildings.map(b=>[b.id,b]));assert.equal(buildings.size,scene.buildings.length);
    const used=new Set(),counts={};
    for(const b of scene.buildings)counts[b.grade]=(counts[b.grade]||0)+1;
    assert.deepEqual(counts,scene.buildingCounts);assert.equal(scene.sources.buildings.features,scene.buildings.length);
    let previous=null;
    for(const c of scene.candidates){
      const [x0,y0,x1,y1]=c.bounds;assert.equal(x1-x0,250);assert.equal(y1-y0,250);
      if(previous)assert.ok(c.center[1]<previous[1]||(c.center[1]===previous[1]&&c.center[0]>previous[0]));
      previous=c.center;const counts={};
      for(const id of c.buildingIds){
        assert.ok(!used.has(id),'One grid per qualifying building');used.add(id);
        const b=buildings.get(id);assert.ok(b);assert.ok(['destroyed','damaged'].includes(b.grade));
        assert.equal(candidateAt(scene,...b.xy)?.id,c.id);
        counts[b.grade]=(counts[b.grade]||0)+1;
      }
      assert.deepEqual(c.counts,counts);
      const coords=lonLat(scene,...c.center);near(coords[0],c.lonLat[0],.000006);near(coords[1],c.lonLat[1],.000006);
    }
    assert.ok(used.size<scene.buildings.length,'Not every damage label implies overlap / burial');
  }
});

test('close inspection centres each real candidate at its terrain height, even at maximum zoom and exaggerated height',()=>{
  for(const scene of scenes){
    const values=decodeElevation(buffer(read(scene.dem.url)),scene.dem);
    for(const cell of scene.candidates){
      for(const exaggeration of [1,2]){
        const state={azimuth:18,pitch:57,zoom:VIEW_ZOOM.max,exaggeration};
        focusOn(scene,values,state,...cell.center);
        const cam=camera(scene,state,.75),z=elevationAt(scene,values,...cell.center)-scene.dem.minimum;
        const p=project([...cell.center,z],cam);near(p[0],0);near(p[1],0);near(p[2],0);
      }
    }
  }
});

test('pan translates the ground with the drag, stays within measured terrain and preserves a truthful scale bar',()=>{
  const values=new Float32Array([100,100,100,100]),state={...defaults,pitch:57,zoom:VIEW_ZOOM.max};
  focusOn(small,values,state,0,0);
  const first=camera(small,state,1.5),before=project([0,0,0],first);
  panGround(small,values,state,first,20,15,600,400);
  const after=project([0,0,0],camera(small,state,1.5));
  near((after[0]-before[0])*300,20);near((before[1]-after[1])*200,15);
  panGround(small,values,state,camera(small,state,1.5),100000,-100000,600,400);
  assert.deepEqual(state.focus,[-500,-500]);assert.equal(state.focusZ,0);
  for(const zoom of [VIEW_ZOOM.min,VIEW_ZOOM.initial,VIEW_ZOOM.selected,VIEW_ZOOM.max]){
    const cam=camera(scenes[0],{...defaults,zoom},.75),scale=scaleBar(cam,360);
    near(scale.pixels*2*cam.halfHeight*cam.aspect/360,scale.metres);
    assert.ok(scale.pixels>0&&scale.pixels<=110);
  }
});

test('static page starts with the model and retains dated explanations, complete tables and accessible fallback',()=>{
  const html=readFileSync(new URL('../greenproof/web/nepal/index.html',import.meta.url),'utf8');
  assert.ok(html.indexOf('id="terrain"')<html.indexOf('id="project-preface"'));
  assert.ok(html.indexOf('id="terrain"')<html.indexOf('id="satellite-title"'));
  for(const text of ['매몰 확인·확률·구조 순위가 아닙니다.','2000년','2026.08.27','GPT-6 Astra','현재 재실·생존·미수색 여부','SRTM','250m','OSM · ODbL'])assert.ok(html.includes(text));
  assert.match(html,/<canvas[^>]*tabindex="0"[^>]*aria-describedby=/);
  assert.match(html,/<img[^>]*id="terrain-fallback"/);
  for(const scene of scenes)for(const cell of scene.candidates){
    assert.ok(html.includes(`data-terrain-cell="${cell.id}"`));
    assert.ok(html.includes(cell.lonLat[1].toFixed(5)+'°N'));
  }
  const script=readFileSync(new URL('../greenproof/web/nepal/terrain.mjs',import.meta.url),'utf8');
  assert.ok(!/setInterval|requestAnimationFrame\(draw\)/.test(script),'No idle rendering loop');
  assert.match(script,/webglcontextlost/);assert.match(script,/pointercancel/);
});

test('satellite registration maps pixels to the same ground coordinates as the DEM, without changing source dates or heights',()=>{
  const detailBase=new URL('../greenproof/web/nepal/data/map-detail/',import.meta.url);
  const manifest=JSON.parse(readFileSync(new URL('manifest.json',detailBase),'utf8'));
  for(const [file,meta] of Object.entries(manifest.files)){
    const bytes=readFileSync(new URL(file,detailBase));assert.equal(bytes.length,meta.bytes);
    assert.equal(createHash('sha256').update(bytes).digest('hex'),meta.sha256);
  }
  for(const scene of scenes){
    const detail=JSON.parse(readFileSync(new URL(scene.id+'.json',detailBase),'utf8')),image=detail.imagery;
    assert.deepEqual(detail.origin,scene.origin);assert.deepEqual(detail.extent,scene.extent);
    assert.equal(detail.terrainSceneSha256,createHash('sha256').update(read(scene.id+'.json')).digest('hex'));
    assert.equal(image.period,'pre-flood');assert.ok(image.acquiredAt.startsWith('2026-08-12'));
    assert.equal(image.sourcePixelSizeM,10);assert.equal(scene.dem.nominalSourceQualityM,90);
    const [a,b,c,d,e,f]=image.transform;
    near(b,0);near(d,0);assert.ok(a>0);assert.ok(e<0);
    const [x0,y0,x1,y1]=scene.extent;
    for(const [col,row,x,y] of [[0,0,x0,y1],[image.width,image.height,x1,y0],[image.width/2,image.height/2,(x0+x1)/2,(y0+y1)/2]]){
      const expected=lonLat(scene,x,y);near(c+a*col,expected[0],1e-9);near(f+e*row,expected[1],1e-9);
    }
    assert.ok(image.cloudFraction>=0&&image.cloudFraction<=1);assert.ok(image.maskedFraction>=image.cloudFraction);
    const photo=readFileSync(new URL(image.url,detailBase));assert.equal(photo.subarray(8,12).toString(),'WEBP');assert.ok(photo.length<100000);
    const osm=detail.osm;assert.equal(osm.license,'ODbL-1.0');assert.equal(osm.accessStatus,null);assert.equal(osm.buildingHeights,null);
    for(const road of osm.roads){assert.ok(road.osmId>0);for(const[x,y] of road.xy)assert.ok(x>=x0-.1&&x<=x1+.1&&y>=y0-.1&&y<=y1+.1);}
    for(const footprint of osm.footprints){assert.ok(!('damage' in footprint));for(const ring of footprint.rings){assert.deepEqual(ring[0],ring.at(-1));for(const[x,y] of ring)assert.ok(x>=x0-.1&&x<=x1+.1&&y>=y0-.1&&y<=y1+.1);}}
    assert.ok(osm.places.every(place=>place.label&&place.osmId>0));
  }
});

test('100m contours lie on the actual DEM triangles and labels behind ridges are hidden',()=>{
  const scene={extent:[0,0,200,200],dem:{rows:3,columns:3,minimum:0,maximum:300,gridSpacingM:[100,100]}};
  const values=new Float32Array([200,200,200,100,100,100,0,0,0]);
  const contours=contourSegments(scene,values,50);assert.ok(contours.length>0);
  for(const {z,points} of contours){assert.equal(z%50,0);for(const[x,y] of points)near(elevationAt(scene,values,x,y),z);}
  assert.throws(()=>contourSegments(scene,values,0));
  const ridge=new Float32Array([0,0,0,300,300,300,0,0,0]);
  const oblique=camera(scene,{...defaults,azimuth:0,pitch:20},1);
  assert.equal(terrainLabelVisible(scene,ridge,100,200,oblique),false,'Near ridge occludes a far valley label');
  assert.equal(terrainLabelVisible(scene,ridge,100,0,oblique),true,'Near valley has no ridge ahead');
  assert.equal(terrainLabelVisible(scene,ridge,100,200,camera(scene,defaults,1)),true,'Plan view sees the labelled ground');
});
