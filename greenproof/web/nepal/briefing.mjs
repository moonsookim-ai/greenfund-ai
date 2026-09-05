// Reading controls only. No incident intake, network requests or stored records.
const briefCards=[...document.querySelectorAll('[data-brief-region]')];
const briefFilters=[...document.querySelectorAll('[data-brief-filter]')];
function selectBriefRegion(id) {
  for(const card of briefCards)card.hidden=id!=='all'&&card.dataset.briefRegion!==id;
  for(const button of briefFilters)button.setAttribute('aria-pressed',String(button.dataset.briefFilter===id));
  const message=document.querySelector('[data-brief-filter-status]');
  if(message)message.textContent=`${briefCards.filter(card=>!card.hidden).length}개 지역 브리핑 · 공개 자료 기준`;
}
for(const button of briefFilters)button.addEventListener('click',()=>selectBriefRegion(button.dataset.briefFilter));
for(const button of document.querySelectorAll('[data-print-brief]'))button.addEventListener('click',()=>window.print());
