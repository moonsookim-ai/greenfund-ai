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

const analyses=[...document.querySelectorAll('[data-source-analysis]')];
const analysisSearch=document.querySelector('#analysis-search');
const analysisStatus=document.querySelector('[data-analysis-status]');
function filterAnalyses(query='') {
  const term=query.trim().toLocaleLowerCase('ko-KR');
  for(const panel of analyses)panel.hidden=!panel.textContent.toLocaleLowerCase('ko-KR').includes(term);
  if(analysisStatus)analysisStatus.textContent=`${analyses.filter(p=>!p.hidden).length}개 한국어 해설${term?' · 검색 결과':' · 전체'}`;
}
analysisSearch?.addEventListener('input',()=>filterAnalyses(analysisSearch.value));
function revealAnalysis(hash, focus=false) {
  if(!hash.startsWith('#analysis-'))return;
  const panel=analyses.find(p=>'#'+p.id===hash);
  if(!panel)return;
  if(analysisSearch)analysisSearch.value='';
  filterAnalyses();
  panel.open=true;
  if(focus)panel.querySelector('summary')?.focus({preventScroll:true});
}
document.addEventListener('click',event=>{
  const anchor=event.target.closest('a[href^="#analysis-"]');
  if(anchor)revealAnalysis(anchor.getAttribute('href'),true);
});
window.addEventListener('hashchange',()=>revealAnalysis(window.location.hash));
revealAnalysis(window.location.hash);
for(const button of document.querySelectorAll('[data-analysis-expand]'))button.addEventListener('click',()=>{
  for(const panel of analyses)if(!panel.hidden)panel.open=true;
});
for(const button of document.querySelectorAll('[data-analysis-collapse]'))button.addEventListener('click',()=>{
  for(const panel of analyses)panel.open=false;
});

// Print every analysis, including filtered and closed panels; then restore the reader's state.
let printState=null;
window.addEventListener('beforeprint',()=>{
  if(printState)return;
  const details=[...document.querySelectorAll('details')];
  printState={details:details.map(p=>[p,p.open]),panels:analyses.map(p=>[p,p.hidden])};
  for(const panel of details)panel.open=true;
  for(const panel of analyses)panel.hidden=false;
});
window.addEventListener('afterprint',()=>{
  if(!printState)return;
  for(const [panel,open] of printState.details)panel.open=open;
  for(const [panel,hidden] of printState.panels)panel.hidden=hidden;
  printState=null;
});
