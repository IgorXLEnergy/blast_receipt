const $ = (id) => document.getElementById(id);
let currentResult = null;
const money = (v) => v == null ? "—" : `${Number(v).toFixed(2).replace('.', ',')} zł`;
const pct = (v) => `${Math.round((Number(v)||0)*100)}%`;
const decisionLabel = { accepted: "ACCEPTED", manual_review: "MANUAL REVIEW", reject_no_blast: "NO BLAST" };
const reviewLabels = { variant_unresolved: 'Opis nie pozwala potwierdzić wariantu produktu.', price_missing: 'Brakuje ceny powiązanej z produktem.', arithmetic_conflict: 'Ilość, cena i suma są niespójne.', low_variant_confidence: 'Wariant wymaga potwierdzenia.' };


function render(j){
  currentResult=j; $('emptyResult').classList.add('hidden'); $('result').classList.remove('hidden'); $('details').classList.remove('hidden');
  $('decision').textContent=decisionLabel[j.decision]||j.decision;
  $('reviewReason').textContent=(j.review_reasons||[]).map(x=>reviewLabels[x]||x).join(' ');
  $('retailer').textContent=j.retailer?.name || 'nierozpoznana';
  $('purchaseDate').textContent=j.purchase_date || '—'; $('qty').textContent=j.blast.quantity;
  $('spend').textContent=money(j.blast.spend); $('avgPrice').textContent=money(j.blast.average_effective_unit_price);
  const unresolved=(j.blast.products||[]).some(x=>x.variant_status==='unresolved');
  $('confidence').textContent=unresolved ? 'nieustalony' : pct(j.confidence); $('confidenceBar').style.width=pct(j.confidence);
  $('blastRows').innerHTML=(j.blast.products||[]).map(x=>`<tr><td><strong>${esc(x.canonical_name)}</strong><small>${esc(x.sku||'SKU nieustalone')} · ${esc((x.source_lines||[]).join(' | '))}</small></td><td>${x.quantity}</td><td>${money(x.unit_price)}</td><td>${money(x.effective_unit_price)}</td><td>${money(x.effective_total)}</td><td>${x.variant_status==='unresolved' ? 'nieustalony' : pct(x.variant_confidence??x.confidence)}<small>Odczyt marki: ${pct(x.brand_confidence??x.ocr_confidence)}</small></td></tr>`).join('') || '<tr><td colspan="6">Brak produktów BLAST.</td></tr>';
  $('basketRows').innerHTML=(j.basket_candidates||[]).map(x=>`<tr><td>${esc(x.raw_name)}</td><td>${x.quantity}</td><td>${money(x.unit_price)}</td><td>${money(x.line_total)}</td></tr>`).join('') || '<tr><td colspan="4">Brak kandydatów.</td></tr>';
  $('rawOcr').textContent=j.ocr.raw_text || '';
  $('jsonOutput').textContent=JSON.stringify(j,null,2);
}
function esc(v){ const d=document.createElement('div'); d.textContent=String(v??''); return d.innerHTML; }

