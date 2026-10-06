let currentFile = null;
async function health(){
  try { const r = await fetch('/health'); const j = await r.json(); $('health').textContent = `${j.ocr_version} · ${j.ocr_lang.toUpperCase()} · online`; $('health').className='pill ok'; }
  catch(e){ $('health').textContent='OCR offline'; $('health').className='pill bad'; }
}

function setFile(file){
  currentFile=file; $('analyzeBtn').disabled=!file; $('error').classList.add('hidden');
  if(!file){ $('previewWrap').classList.add('hidden'); return; }
  $('fileName').textContent=file.name; $('fileSize').textContent=`${(file.size/1024/1024).toFixed(2)} MB`;
  $('preview').src=URL.createObjectURL(file); $('previewWrap').classList.remove('hidden');
}
$('file').addEventListener('change', e=>setFile(e.target.files[0]));
const dz=$('dropzone');
['dragenter','dragover'].forEach(ev=>dz.addEventListener(ev,e=>{e.preventDefault();dz.classList.add('drag')}));
['dragleave','drop'].forEach(ev=>dz.addEventListener(ev,e=>{e.preventDefault();dz.classList.remove('drag')}));
dz.addEventListener('drop',e=>{ const f=e.dataTransfer.files[0]; if(f) setFile(f); });

$('analyzeBtn').addEventListener('click', async ()=>{
  if(!currentFile) return;
  const btn=$('analyzeBtn'); btn.disabled=true; btn.textContent='Analizuję…'; $('error').classList.add('hidden');
  try{
    const fd=new FormData(); fd.append('file',currentFile);
    const r=await fetch('/v1/analyze',{method:'POST',body:fd});
    const j=await r.json(); if(!r.ok) throw new Error(j.detail || `HTTP ${r.status}`);
    render(j); saveHistory(j,currentFile.name);
  }catch(e){ $('error').textContent=e.message; $('error').classList.remove('hidden'); }
  finally{ btn.disabled=false; btn.textContent='Analizuj paragon'; }
});

$('copyJson').addEventListener('click', async ()=>{ if(currentResult) await navigator.clipboard.writeText(JSON.stringify(currentResult,null,2)); });
function saveHistory(j,filename){
  const h=JSON.parse(localStorage.getItem('blastReceiptHistory')||'[]');
  h.unshift({ts:new Date().toISOString(),filename,decision:j.decision,retailer:j.retailer?.name||'?',qty:j.blast.quantity,spend:j.blast.spend});
  localStorage.setItem('blastReceiptHistory',JSON.stringify(h.slice(0,20))); renderHistory();
}
function renderHistory(){
  const h=JSON.parse(localStorage.getItem('blastReceiptHistory')||'[]');
  $('history').innerHTML=h.map(x=>`<div class="history-item"><strong>${esc(x.filename)}</strong><span>${esc(x.retailer)}</span><span>${x.qty} szt.</span><span>${money(x.spend)}</span><span>${new Date(x.ts).toLocaleString('pl-PL')}</span></div>`).join('') || '<p>Brak testów w tej przeglądarce.</p>';
}
$('clearHistory').addEventListener('click',()=>{localStorage.removeItem('blastReceiptHistory');renderHistory();});
health(); renderHistory();
