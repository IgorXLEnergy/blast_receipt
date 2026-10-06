let examples = null;

function selectExample(id) {
  const sample = examples[id];
  render(sample.result);
  $('sampleDescription').textContent = sample.description;
  $('receiptText').textContent = sample.result.ocr.lines.map(x => x.text).filter(Boolean).join('\n');
  $('confirmedProducts').textContent = sample.confirmed.join(' · ');
  $('beforeAfter').textContent = sample.change;
  document.querySelectorAll('[data-case]').forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.case === id));
  });
}

document.querySelectorAll('[data-case]').forEach(button => {
  button.disabled = true;
  button.addEventListener('click', () => selectExample(button.dataset.case));
});

$('copyJson').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(JSON.stringify(currentResult, null, 2));
    $('copyJson').textContent = 'Skopiowano';
    setTimeout(() => { $('copyJson').textContent = 'Kopiuj JSON'; }, 1500);
  } catch (_) {
    $('error').textContent = 'Nie udało się skopiować. Pełny JSON jest dostępny poniżej.';
    $('error').classList.remove('hidden');
  }
});

fetch('/static/data.json').then(response => {
  if (!response.ok) throw new Error('Nie udało się wczytać zapisanych przykładów.');
  return response.json();
}).then(data => {
  examples = data;
  selectExample('second');
  document.querySelectorAll('[data-case]').forEach(button => { button.disabled = false; });
}).catch(error => {
  $('emptyResult').textContent = 'Nie udało się wczytać demo.';
  $('error').textContent = error.message;
  $('error').classList.remove('hidden');
});
