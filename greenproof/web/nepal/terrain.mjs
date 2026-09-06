import {clamp,decodeElevation,mesh,camera,project,pickTerrain,candidateAt} from './terrain-model.mjs?v=1';

const root=document.querySelector('#terrain');
if(root) init();

function init() {
  const canvas=root.querySelector('#terrain-canvas'),fallback=root.querySelector('#terrain-fallback');
  const status=root.querySelector('#terrain-status'),area=root.querySelector('#terrain-area');
  const chooser=root.querySelector('#terrain-cell'),detail=root.querySelector('#terrain-detail');
  const viewLabel=root.querySelector('#terrain-view-label'),direction=root.querySelector('#terrain-north');
  const layers={event:true,buildings:true,candidates:true,rivers:true};
  const defaults={azimuth:18,pitch:57,zoom:1,exaggeration:1};
  let state={...defaults},scene,values,rivers,geometry,cam,gl,program,indexCount,texture;
  let selected=null,request=0,frame=0,lost=false;
  const cache=new Map(),buffers=[];
  const base=new URL('./data/terrain/',import.meta.url);
  const $=id=>root.querySelector(`#${id}`);

  const shader=(type,source)=>{
    const result=gl.createShader(type);gl.shaderSource(result,source);gl.compileShader(result);
    if(!gl.getShaderParameter(result,gl.COMPILE_STATUS))throw new Error('3D 셰이더를 사용할 수 없습니다.');
    return result;
  };
  function setup() {
    gl=canvas.getContext('webgl',{alpha:false,antialias:true,powerPreference:'low-power'});
    if(!gl)throw new Error('이 기기에서 3D 표시를 사용할 수 없습니다.');
    program=gl.createProgram();
    gl.attachShader(program,shader(gl.VERTEX_SHADER,`
      attribute vec3 aPosition; attribute vec3 aNormal; attribute vec2 aUV;
      uniform vec3 uCenter,uRight,uUp,uToward; uniform vec4 uView;
      varying vec2 vUV; varying float vLight,vAltitude;
      void main(){
        vec3 p=vec3(aPosition.xy,aPosition.z*uView.w)-uCenter;
        gl_Position=vec4(dot(p,uRight)/uView.x,dot(p,uUp)/uView.y,-dot(p,uToward)/uView.z,1.0);
        vec3 normal=normalize(vec3(aNormal.xy*uView.w,aNormal.z));
        vLight=.67+.33*max(0.0,dot(normal,normalize(vec3(-.5,-.4,.85))));
        vUV=aUV; vAltitude=aPosition.z;
      }`));
    gl.attachShader(program,shader(gl.FRAGMENT_SHADER,`
      precision mediump float;
      uniform sampler2D uTexture; uniform float uHeight;
      varying vec2 vUV; varying float vLight,vAltitude;
      void main(){
        float h=clamp(vAltitude/uHeight,0.0,1.0);
        vec3 ground=mix(vec3(.55,.66,.48),vec3(.86,.83,.71),h);
        vec4 overlay=texture2D(uTexture,vUV);
        gl_FragColor=vec4(mix(ground*vLight,overlay.rgb*(.9+.1*vLight),overlay.a),1.0);
      }`));
    gl.linkProgram(program);
    if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error('3D 화면을 초기화하지 못했습니다.');
    gl.useProgram(program);gl.enable(gl.DEPTH_TEST);gl.disable(gl.CULL_FACE);
    gl.clearColor(.925,.946,.926,1);
    texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,texture);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    gl.uniform1i(gl.getUniformLocation(program,'uTexture'),0);
  }
  function upload() {
    for(const buffer of buffers)gl.deleteBuffer(buffer);
    buffers.length=0;
    const vertex=gl.createBuffer(),index=gl.createBuffer();buffers.push(vertex,index);
    gl.bindBuffer(gl.ARRAY_BUFFER,vertex);gl.bufferData(gl.ARRAY_BUFFER,geometry.vertices,gl.STATIC_DRAW);
    for(const [name,count,offset] of [['aPosition',3,0],['aNormal',3,12],['aUV',2,24]]){
      const loc=gl.getAttribLocation(program,name);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,count,gl.FLOAT,false,32,offset);
    }
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,index);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,geometry.indices,gl.STATIC_DRAW);
    indexCount=geometry.indices.length;
    gl.uniform1f(gl.getUniformLocation(program,'uHeight'),scene.dem.maximum-scene.dem.minimum);
    paintLayers();
  }
  function paintLayers() {
    if(!gl||lost||!scene)return;
    const layer=document.createElement('canvas');layer.width=1536;layer.height=1536;
    const ctx=layer.getContext('2d'),[x0,y0,x1,y1]=scene.extent;
    const xx=x=>(x-x0)/(x1-x0)*layer.width,yy=y=>(y1-y)/(y1-y0)*layer.height;
    const path=rings=>{ctx.beginPath();for(const ring of rings){ring.forEach(([x,y],i)=>i?ctx.lineTo(xx(x),yy(y)):ctx.moveTo(xx(x),yy(y)));ctx.closePath();}};
    // All layers use the same local metric coordinates as the DEM; texture is not a satellite photograph.
    if(layers.event)for(const polygon of scene.eventPolygons){path(polygon);ctx.fillStyle='#e8a057';ctx.fill('evenodd');}
    if(layers.rivers){ctx.strokeStyle='#177aad';ctx.lineWidth=3;for(const line of rivers.rivers){ctx.beginPath();line.xy.forEach(([x,y],i)=>i?ctx.lineTo(xx(x),yy(y)):ctx.moveTo(xx(x),yy(y)));ctx.stroke();}}
    ctx.strokeStyle='#314d4b';ctx.lineWidth=2;ctx.setLineDash([10,7]);for(const poly of scene.aoiPolygons){path(poly);ctx.stroke();}ctx.setLineDash([]);
    if(layers.candidates)for(const cell of scene.candidates){
      const [a,b,c,d]=cell.bounds;ctx.strokeStyle='#7746a5';ctx.lineWidth=2;
      ctx.strokeRect(xx(a),yy(d),xx(c)-xx(a),yy(b)-yy(d));
    }
    if(layers.buildings)for(const b of scene.buildings){
      const x=xx(b.xy[0]),y=yy(b.xy[1]);ctx.beginPath();
      if(b.grade==='destroyed'){ctx.fillStyle='#ae292c';ctx.fillRect(x-2.2,y-2.2,4.4,4.4);}
      else if(b.grade==='damaged'){ctx.fillStyle='#7b4216';ctx.arc(x,y,2.5,0,2*Math.PI);ctx.fill();}
      else {ctx.strokeStyle='#78453d';ctx.lineWidth=1.1;ctx.moveTo(x,y-3);ctx.lineTo(x+3,y);ctx.lineTo(x,y+3);ctx.lineTo(x-3,y);ctx.closePath();ctx.stroke();}
    }
    if(selected){const[a,b,c,d]=selected.bounds;ctx.fillStyle='#9049e03a';ctx.fillRect(xx(a),yy(d),xx(c)-xx(a),yy(b)-yy(d));ctx.lineWidth=7;ctx.strokeStyle='#fff';ctx.strokeRect(xx(a),yy(d),xx(c)-xx(a),yy(b)-yy(d));ctx.lineWidth=3;ctx.strokeStyle='#633a9b';ctx.strokeRect(xx(a),yy(d),xx(c)-xx(a),yy(b)-yy(d));}
    gl.bindTexture(gl.TEXTURE_2D,texture);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,layer);schedule();
  }
  function schedule(){if(!frame)frame=requestAnimationFrame(()=>{frame=0;draw();});}
  function draw(){
    if(!scene||!gl||lost)return;
    const rect=canvas.getBoundingClientRect();if(rect.width===0||rect.height===0)return;
    const ratio=Math.min(devicePixelRatio||1,1.75),w=Math.round(rect.width*ratio),h=Math.round(rect.height*ratio);
    if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
    gl.viewport(0,0,w,h);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
    cam=camera(scene,state,w/h);
    for(const name of ['center','right','up','toward'])gl.uniform3fv(gl.getUniformLocation(program,'u'+name[0].toUpperCase()+name.slice(1)),cam[name]);
    gl.uniform4f(gl.getUniformLocation(program,'uView'),cam.halfHeight*cam.aspect,cam.halfHeight,cam.depth,state.exaggeration);
    gl.drawElements(gl.TRIANGLES,indexCount,gl.UNSIGNED_SHORT,0);
    viewLabel.textContent=`${state.pitch===90?'위에서 보기':'입체 지형'} · 높이 ${state.exaggeration}배 · ${state.zoom.toFixed(1)}배 확대`;
    // Compass follows the same projected north vector; unlike a fixed north arrow it remains valid after rotation.
    const n=project([cam.center[0],cam.center[1]+100,cam.center[2]/state.exaggeration],cam);
    direction.style.transform=`rotate(${Math.atan2(n[0]*w,n[1]*h)*180/Math.PI}deg)`;
    const scale=$('terrain-scale');scale.style.width=`${500/(2*cam.halfHeight*cam.aspect)*rect.width}px`;
  }
  async function json(url){const response=await fetch(new URL(url,base),{signal:AbortSignal.timeout(20000)});if(!response.ok)throw new Error('자료 응답 오류');return response.json();}
  async function load(id){
    const ticket=++request;selected=null;scene=null;chooser.value='';canvas.hidden=true;fallback.hidden=false;
    root.classList.remove('terrain-ready');
    $('terrain-frame').setAttribute('aria-busy','true');
    status.textContent='지형·위성 판독 자료를 불러오고 있습니다…';
    viewLabel.textContent='위성 판독 피해 평면도 · 3D 준비 중';
    detail.textContent='선택한 지역의 자료를 불러오고 있습니다. 아래 구역 표에서도 좌표와 건물 수를 확인할 수 있습니다.';
    $('terrain-altitude').textContent='SRTM 과거 표고 기반 · 하천 선은 침수 경계가 아닙니다.';
    chooser.disabled=true;
    fallback.src=new URL(`${id}-plan.svg`,base).href;fallback.alt=`${area.selectedOptions[0].textContent} 위성 판독 피해 평면도. 입체 모델을 사용할 수 없을 때도 아래 구역 표에서 확인할 수 있습니다.`;
    root.querySelectorAll('[data-terrain-table]').forEach(table=>table.hidden=table.dataset.terrainTable!==id);
    try{
      if(!cache.has(id))cache.set(id,(async()=>{
        const s=await json(`${id}.json`);
        const [r,response]=await Promise.all([json(s.riverUrl),fetch(new URL(s.dem.url,base),{signal:AbortSignal.timeout(20000)})]);
        if(!response.ok)throw new Error('표고 응답 오류');
        const v=decodeElevation(await response.arrayBuffer(),s.dem);return {s,r,v};
      })());
      const data=await cache.get(id);if(ticket!==request)return;
      scene=data.s;rivers=data.r;values=data.v;geometry=mesh(scene,values);state={...defaults};$('terrain-height').value='1';
      chooser.replaceChildren(new Option('구역을 선택하세요 · 북→남 공간순',''));
      for(const c of scene.candidates)chooser.add(new Option(`${c.id} · 중첩 건물 ${c.buildingIds.length}개`,c.id));
      chooser.disabled=false;
      summary();
      if(!gl)setup();upload();canvas.hidden=false;fallback.hidden=true;
      root.classList.add('terrain-ready');
      canvas.setAttribute('aria-label',`${scene.name} 3D 지형. 방향키로 회전, 더하기·빼기로 확대·축소. 보라 격자를 클릭하거나 옆 구역 목록을 선택하세요.`);
      status.textContent=`${scene.name} · 위성 판독 2026.08.27 · ${scene.candidates.length}개 중첩 확인 구역 · 실시간 정보 아님`;
      schedule();
    }catch(error){
      if(ticket!==request)return;cache.delete(id);
      status.textContent='3D를 불러오지 못해 위성 판독 피해 평면도를 표시합니다. 아래 구역 표와 출처 설명을 이용하세요.';
      viewLabel.textContent='위성 판독 피해 평면도 · 2026.08.27';
      canvas.hidden=true;fallback.hidden=false;
      console.warn('Terrain model unavailable:',error.message);
    }finally{if(ticket===request)$('terrain-frame').setAttribute('aria-busy','false');}
  }
  function summary(){
    detail.replaceChildren();
    const heading=document.createElement('h3');heading.textContent=`${scene.name} · 매몰 여부 확인 후보`;
    const text=document.createElement('p');text.textContent=`토사 이동 범위와 파괴·손상 건물 ${scene.candidates.reduce((n,c)=>n+c.buildingIds.length,0)}개가 겹칩니다. 이를 포함한 250m 격자 ${scene.candidates.length}개를 표시했습니다.`;
    const guide=document.createElement('p');guide.className='terrain-detail-guide';guide.textContent='보라색 격자 또는 위 목록을 선택해 좌표와 확인할 정보를 보세요. 격자 번호는 구조 우선순위가 아닙니다.';
    detail.append(heading,text,guide);
    $('terrain-altitude').textContent=`지형 표고 ${scene.dem.minimum.toLocaleString()}–${scene.dem.maximum.toLocaleString()}m · 격자 ${scene.dem.gridSpacingM.join(' × ')}m`;
  }
  function select(id){
    selected=scene?.candidates.find(c=>c.id===id)||null;chooser.value=selected?.id||'';
    if(!selected){delete state.focus;state.zoom=1;summary();paintLayers();return;}
    state.focus=selected.center;state.zoom=Math.max(state.zoom,1.7);
    detail.replaceChildren();
    const heading=document.createElement('h3');heading.textContent=`${scene.name} ${selected.id}`;
    const count=document.createElement('p');count.className='terrain-detail-count';
    count.textContent=`토사와 중첩: 파괴 ${selected.counts.destroyed||0}개 · 손상 ${selected.counts.damaged||0}개`;
    const coords=document.createElement('p');coords.className='terrain-coordinates';coords.textContent=`격자 중심 · 북위 ${selected.lonLat[1].toFixed(5)}° / 동경 ${selected.lonLat[0].toFixed(5)}° (WGS84)`;
    const note=document.createElement('p');note.textContent='250m 격자 중심은 집결지·진입점이 아닙니다. 위성 판독 건물 점이며, 현재 건물 상태·매몰·재실 여부는 미확인입니다.';
    const title=document.createElement('h4');title.textContent='이 구역을 현지 지휘부와 대조할 순서';
    const list=document.createElement('ol');
    for(const t of ['구역 번호·좌표와 8월 27일 판독일을 함께 전달해 동일 장소인지 확인합니다.','공식 실종·재실 정보와 수색 완료 구역·기존 팀 배치를 대조합니다.','현재 도로·하천·사면 상태와 현장 확인 자료를 받아 지휘부가 임무·접근 방식을 결정합니다.']){const li=document.createElement('li');li.textContent=t;list.append(li);}
    detail.append(heading,count,coords,note,title,list);paintLayers();
  }
  area.addEventListener('change',()=>load(area.value));chooser.addEventListener('change',()=>select(chooser.value));
  root.querySelectorAll('[data-terrain-layer]').forEach(input=>input.addEventListener('change',()=>{layers[input.dataset.terrainLayer]=input.checked;paintLayers();}));
  $('terrain-height').addEventListener('change',e=>{state.exaggeration=Number(e.target.value);schedule();});
  function control(action){
    if(action==='left')state.azimuth-=15;if(action==='right')state.azimuth+=15;
    if(action==='up')state.pitch=clamp(state.pitch+10,20,90);if(action==='down')state.pitch=clamp(state.pitch-10,20,90);
    if(action==='in')state.zoom=clamp(state.zoom*1.2,.7,3);if(action==='out')state.zoom=clamp(state.zoom/1.2,.7,3);
    if(action==='top'){state.pitch=90;state.azimuth=0;}
    if(action==='reset'){state={...defaults};$('terrain-height').value='1';}
    schedule();
  }
  root.querySelectorAll('[data-terrain-control]').forEach(button=>button.addEventListener('click',()=>control(button.dataset.terrainControl)));
  canvas.addEventListener('keydown',e=>{const key={ArrowLeft:'left',ArrowRight:'right',ArrowUp:'up',ArrowDown:'down','+':'in','=':'in','-':'out',r:'reset'}[e.key];if(key){e.preventDefault();control(key);}});
  let pointer;
  canvas.addEventListener('pointerdown',e=>{if(e.button!==0)return;pointer={id:e.pointerId,x:e.clientX,y:e.clientY,total:0};canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener('pointermove',e=>{
    if(!pointer||pointer.id!==e.pointerId)return;
    const dx=e.clientX-pointer.x,dy=e.clientY-pointer.y;pointer.total+=Math.abs(dx)+Math.abs(dy);
    state.azimuth+=dx*.3;if(e.pointerType!=='touch')state.pitch=clamp(state.pitch+dy*.2,20,90);
    pointer.x=e.clientX;pointer.y=e.clientY;schedule();
  });
  canvas.addEventListener('pointerup',e=>{
    if(!pointer||pointer.id!==e.pointerId)return;
    if(pointer.total<5&&cam&&scene){const r=canvas.getBoundingClientRect();const point=pickTerrain((e.clientX-r.left)/r.width*2-1,1-(e.clientY-r.top)/r.height*2,cam,geometry);
      if(point){const cell=candidateAt(scene,point[0],point[1]);select(cell?.id||'');if(!cell)status.textContent='선택 지점에 중첩 후보가 없습니다. 미판독이거나 후보 조건 밖일 수 있으며, 안전·매몰 없음의 의미가 아닙니다.';}}
    pointer=null;
  });
  canvas.addEventListener('pointercancel',()=>pointer=null);
  root.addEventListener('click',e=>{const target=e.target.closest('[data-terrain-cell]');if(target&&scene){select(target.dataset.terrainCell);chooser.focus({preventScroll:true});}});
  canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();lost=true;canvas.hidden=true;fallback.hidden=false;root.classList.remove('terrain-ready');viewLabel.textContent='위성 판독 피해 평면도 · 2026.08.27';status.textContent='3D 표시가 중단되어 평면도로 전환했습니다. 구역 표를 계속 이용할 수 있습니다.';});
  canvas.addEventListener('webglcontextrestored',()=>{lost=false;gl=null;load(area.value);});
  if(typeof ResizeObserver!=='undefined')new ResizeObserver(schedule).observe(canvas);
  else window.addEventListener('resize',schedule);
  load(area.value);
}
