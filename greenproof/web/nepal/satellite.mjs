const after=document.querySelector('#satellite-after');
const before=document.querySelector('#satellite-before');
const divider=document.querySelector('#comparison-divider');
const control=document.querySelector('#comparison-control');
const slider=document.querySelector('#image-divider');
const status=document.querySelector('#image-status');
const error=document.querySelector('#satellite-error');
const original=document.querySelector('#satellite-original');
const buttons=[...document.querySelectorAll('[data-image-mode]')];
let request=0,mode='after';

function moveDivider() {
  const value=Number(slider.value);
  before.style.clipPath=`inset(0 ${100-value}% 0 0)`;
  divider.style.left=`${value}%`;
  document.querySelector('#divider-value').textContent=`${value}%`;
}
function show(next) {
  mode=next;
  before.hidden=mode==='after';
  divider.hidden=control.hidden=mode!=='compare';
  if(mode==='compare') moveDivider();
  else before.style.clipPath='none';
  status.textContent=mode==='after' ? '홍수 다음 날 · 2026.08.27 촬영' : mode==='before' ? '홍수 이전 · 2026.08.12 촬영' : '왼쪽 8월 12일 / 오른쪽 8월 27일';
  original.href=mode==='compare' ? 'https://www.esa.int/ESA_Multimedia/Images/2026/08/Sentinel-2_captures_before_and_after_Nepal_flash_flood' : mode==='before' ? before.dataset.src : after.getAttribute('src');
  original.textContent=mode==='compare' ? '두 사진 원문 보기 ↗' : '사진 크게 보기 ↗';
  if(mode==='after'&&after.complete&&!after.naturalWidth) error.hidden=false;
  buttons.forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.imageMode===mode)));
}
async function choose(next) {
  const thisRequest=++request;
  error.hidden=true;
  if(next!=='after') {
    try {
      if(!before.getAttribute('src')) before.src=before.dataset.src;
      if(!before.complete||!before.naturalWidth) {
        status.textContent='8월 12일 사진을 불러오는 중입니다.';
        await before.decode();
      }
    } catch {
      if(thisRequest!==request) return;
      before.removeAttribute('src');
      show(mode);
      error.hidden=false;
      return;
    }
  }
  // Rapid button changes cannot let a late image load replace the chosen view.
  if(thisRequest!==request) return;
  show(next);
}
buttons.forEach(button=>button.addEventListener('click',()=>choose(button.dataset.imageMode)));
slider.addEventListener('input',moveDivider);
after.addEventListener('error',()=>{error.hidden=false;});
if(after.complete&&!after.naturalWidth) error.hidden=false;
