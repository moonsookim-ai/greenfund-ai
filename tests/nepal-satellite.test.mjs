import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// Event-contract test without opening a browser or contacting imagery services.
function harness(){
  class Element{
    constructor(){this.listeners={};this.attrs={};this.style={};this.hidden=false;this.value='50';this.dataset={};this.complete=true;this.naturalWidth=960;this.classes=new Set();this.capture=null;
      this.classList={toggle:(s,on)=>on?this.classes.add(s):this.classes.delete(s),add:s=>this.classes.add(s),remove:s=>this.classes.delete(s)};}
    addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);}
    async fire(type,event={}){for(const fn of this.listeners[type]||[])await fn(event);}
    setAttribute(key,value){this.attrs[key]=value;} getAttribute(key){return this.attrs[key];} removeAttribute(key){delete this.attrs[key];}
    getBoundingClientRect(){return {left:100,width:400};}
    setPointerCapture(id){this.capture=id;}hasPointerCapture(id){return this.capture===id;}releasePointerCapture(){this.capture=null;}
  }
  const ids=['satellite-after','satellite-before','comparison-divider','comparison-control','image-divider','image-status','satellite-error','satellite-original','satellite-view','divider-value'];
  const elements=Object.fromEntries(ids.map(id=>[id,new Element()]));
  elements['satellite-before'].dataset.src='before.jpg';elements['satellite-after'].attrs.src='after.jpg';
  const buttons=['after','before','compare'].map(mode=>{const el=new Element();el.dataset.imageMode=mode;return el;});
  const document={querySelector:selector=>elements[selector.slice(1)],querySelectorAll:()=>buttons};
  vm.runInNewContext(readFileSync(new URL('../greenproof/web/nepal/satellite.mjs',import.meta.url),'utf8'),{document});
  return {elements,buttons};
}

test('image drag stays inactive for a single image and synchronizes photo clip, range and accessible values in compare mode',async()=>{
  const {elements:e,buttons}=harness(),view=e['satellite-view'];
  await view.fire('pointerdown',{button:0,pointerId:1,clientX:200});assert.equal(e['image-divider'].value,'50');
  await buttons[2].fire('click');assert.ok(view.classes.has('is-comparing'));
  await view.fire('pointerdown',{button:0,pointerId:1,clientX:200});
  assert.equal(e['image-divider'].value,'25');assert.equal(e['satellite-before'].style.clipPath,'inset(0 75% 0 0)');
  assert.equal(e['comparison-divider'].attrs['aria-valuenow'],'25');
  await view.fire('pointermove',{pointerId:2,clientX:400});assert.equal(e['image-divider'].value,'25');
  await view.fire('pointermove',{pointerId:1,clientX:900});assert.equal(e['image-divider'].value,'100');
  await view.fire('pointerup',{pointerId:1,clientX:0});assert.equal(e['image-divider'].value,'0');assert.equal(view.capture,null);
});

test('canceled touch and view changes release the comparison drag; handle also works from keyboard',async()=>{
  const {elements:e,buttons}=harness(),view=e['satellite-view'];await buttons[2].fire('click');
  await view.fire('pointerdown',{button:0,pointerId:1,clientX:200});await view.fire('pointercancel');
  await view.fire('pointermove',{pointerId:1,clientX:400});assert.equal(e['image-divider'].value,'25');
  await view.fire('pointerdown',{button:0,pointerId:2,clientX:300});await buttons[0].fire('click');assert.equal(view.capture,null);
  assert.equal(e['comparison-divider'].hidden,true);
  await buttons[2].fire('click');let prevented=false;
  await e['comparison-divider'].fire('keydown',{key:'End',preventDefault(){prevented=true;}});
  assert.equal(e['image-divider'].value,'100');assert.ok(prevented);
  await e['comparison-divider'].fire('keydown',{key:'ArrowLeft',preventDefault(){}});assert.equal(e['image-divider'].value,'99');
});
