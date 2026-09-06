// Pure geographic/camera math. Distances in metres; X east, Y north, Z up.
export const radians = degrees => degrees * Math.PI / 180;
export const clamp = (x, low, high) => Math.max(low, Math.min(high, x));
export const VIEW_ZOOM = Object.freeze({initial:2,selected:4.5,min:.7,max:10});
const dot = (a,b) => a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const sub = (a,b) => a.map((v,i)=>v-b[i]);
const cross = (a,b) => [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];

export function decodeElevation(buffer, meta) {
  if (buffer.byteLength !== meta.rows*meta.columns*2) throw new Error('표고 파일 크기가 맞지 않습니다.');
  const view=new DataView(buffer), values=new Float32Array(meta.rows*meta.columns);
  for(let i=0;i<values.length;i++) {
    values[i]=view.getUint16(i*2,true);
    if(values[i]<meta.minimum || values[i]>meta.maximum) throw new Error('표고 범위를 확인할 수 없습니다.');
  }
  return values;
}

export function elevationAt(scene, values, x, y) {
  const [x0,y0,x1,y1]=scene.extent, {rows,columns}=scene.dem;
  if(x<x0||x>x1||y<y0||y>y1) return null;
  const col=(x-x0)/(x1-x0)*(columns-1),row=(y1-y)/(y1-y0)*(rows-1);
  const c=Math.min(columns-2,Math.floor(col)),r=Math.min(rows-2,Math.floor(row)),fx=col-c,fy=row-r;
  const a=values[r*columns+c],b=values[r*columns+c+1],d=values[(r+1)*columns+c],e=values[(r+1)*columns+c+1];
  // Matches the triangle diagonal used by the renderer, not a different surface.
  return fx+fy<=1 ? a+(b-a)*fx+(d-a)*fy : e+(d-e)*(1-fx)+(b-e)*(1-fy);
}

export function mesh(scene, values) {
  const {rows,columns,minimum}=scene.dem, [x0,y0,x1,y1]=scene.extent;
  const vertices=new Float32Array(rows*columns*8), indices=new Uint16Array((rows-1)*(columns-1)*6);
  const dx=(x1-x0)/(columns-1),dy=(y1-y0)/(rows-1);
  for(let r=0;r<rows;r++) for(let c=0;c<columns;c++) {
    const i=r*columns+c,west=Math.max(0,c-1),east=Math.min(columns-1,c+1),north=Math.max(0,r-1),south=Math.min(rows-1,r+1);
    const dzdx=(values[r*columns+east]-values[r*columns+west])/((east-west)*dx);
    const dzdy=(values[north*columns+c]-values[south*columns+c])/((south-north)*dy);
    vertices.set([x0+c*dx,y1-r*dy,values[i]-minimum,-dzdx,-dzdy,1,c/(columns-1),r/(rows-1)],i*8);
  }
  let k=0;
  for(let r=0;r<rows-1;r++) for(let c=0;c<columns-1;c++) {
    const a=r*columns+c,b=a+1,d=a+columns,e=d+1;
    indices.set([a,d,b,b,d,e],k); k+=6;
  }
  return {vertices,indices};
}

export function camera(scene, state, aspect) {
  const [x0,y0,x1,y1]=scene.extent, a=radians(state.azimuth),e=radians(state.pitch);
  const size=Math.max(x1-x0,y1-y0,scene.dem.maximum-scene.dem.minimum);
  return {
    right:[Math.cos(a),Math.sin(a),0],
    up:[-Math.sin(a)*Math.sin(e),Math.cos(a)*Math.sin(e),Math.cos(e)],
    toward:[Math.sin(a)*Math.cos(e),-Math.cos(a)*Math.cos(e),Math.sin(e)],
    center:[state.focus?.[0]??(x0+x1)/2,state.focus?.[1]??(y0+y1)/2,(state.focusZ??(scene.dem.maximum-scene.dem.minimum)/2)*state.exaggeration],
    halfHeight:size*.62/Math.min(aspect,1)/state.zoom, aspect, depth:size*4,
    exaggeration:state.exaggeration
  };
}

export function focusOn(scene,values,state,x,y) {
  const [x0,y0,x1,y1]=scene.extent;
  state.focus=[clamp(x,x0,x1),clamp(y,y0,y1)];
  state.focusZ=elevationAt(scene,values,...state.focus)-scene.dem.minimum;
}

export function panGround(scene,values,state,cam,dx,dy,width,height) {
  const mx=dx/width*2*cam.halfHeight*cam.aspect,my=dy/height*2*cam.halfHeight;
  const upLengthSquared=cam.up[0]**2+cam.up[1]**2;
  focusOn(scene,values,state,
    cam.center[0]-cam.right[0]*mx+cam.up[0]*my/upLengthSquared,
    cam.center[1]-cam.right[1]*mx+cam.up[1]*my/upLengthSquared);
}

export function scaleBar(cam,width) {
  const metresPerPixel=2*cam.halfHeight*cam.aspect/width;
  const choices=[10,20,50,100,200,500,1000];
  const metres=choices.filter(m=>m/metresPerPixel<=110).at(-1)??10;
  return {metres,pixels:metres/metresPerPixel};
}

export function project(point, cam) {
  const d=sub([point[0],point[1],point[2]*cam.exaggeration],cam.center);
  return [dot(d,cam.right)/(cam.halfHeight*cam.aspect),dot(d,cam.up)/cam.halfHeight,-dot(d,cam.toward)/cam.depth];
}

export function rayAt(nx,ny,cam) {
  return {origin:cam.center.map((v,i)=>v+cam.right[i]*nx*cam.halfHeight*cam.aspect+cam.up[i]*ny*cam.halfHeight+cam.toward[i]*cam.depth),
    direction:cam.toward.map(v=>-v)};
}

export function intersectTriangle(origin,direction,a,b,c) {
  const edge1=sub(b,a),edge2=sub(c,a),h=cross(direction,edge2),det=dot(edge1,h);
  if(Math.abs(det)<1e-8) return null;
  const s=sub(origin,a),u=dot(s,h)/det;
  if(u<0||u>1) return null;
  const q=cross(s,edge1),v=dot(direction,q)/det;
  if(v<0||u+v>1) return null;
  const t=dot(edge2,q)/det;
  return t>=0?t:null;
}

export function pickTerrain(nx,ny,cam,geometry) {
  const {origin,direction}=rayAt(nx,ny,cam), {vertices,indices}=geometry;
  const point=i=>[vertices[i*8],vertices[i*8+1],vertices[i*8+2]*cam.exaggeration];
  let closest=Infinity;
  for(let i=0;i<indices.length;i+=3) {
    const t=intersectTriangle(origin,direction,point(indices[i]),point(indices[i+1]),point(indices[i+2]));
    if(t!==null && t<closest) closest=t;
  }
  return Number.isFinite(closest)?origin.map((v,i)=>v+direction[i]*closest):null;
}

export function candidateAt(scene,x,y) {
  return scene.candidates.find(c=>x>=c.bounds[0] && x<c.bounds[2] && y>=c.bounds[1] && y<c.bounds[3]) || null;
}

export function lonLat(scene,x,y) {
  const [lon,lat]=scene.origin, metresPerDegree=6378137*Math.PI/180;
  return [lon+x/(metresPerDegree*Math.cos(radians(lat))),lat+y/metresPerDegree];
}
