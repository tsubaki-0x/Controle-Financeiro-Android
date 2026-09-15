(() => {
  const categories = JSON.parse(document.querySelector('#categories-data').textContent);
  const category = document.querySelector('#categoria');
  const amount = document.querySelector('#valor');
  const error = document.querySelector('#amount-error');
  const form = document.querySelector('#transaction-form');
  const selectedInitial = category.dataset.selected;

  function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value;
    return div.innerHTML;
  }

  function updateCategories(keepSelection = true) {
    const type = document.querySelector('input[name="tipo"]:checked').value;
    const current = keepSelection ? (category.value || selectedInitial) : '';
    category.innerHTML = categories[type]
      .map((item) => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`)
      .join('');
    if (categories[type].includes(current)) category.value = current;
  }

  function parseAmountToCents(raw) {
    const text = String(raw || '').trim();
    if (!text || !/^\d[\d.,]*$/.test(text)) return null;

    let normalized = '';
    if (text.includes('.') && text.includes(',')) {
      if (text.lastIndexOf(',') > text.lastIndexOf('.')) {
        if (!/^\d{1,3}(?:\.\d{3})+,\d{1,2}$/.test(text)) return null;
        normalized = text.replace(/\./g, '').replace(',', '.');
      } else {
        if (!/^\d{1,3}(?:,\d{3})+\.\d{1,2}$/.test(text)) return null;
        normalized = text.replace(/,/g, '');
      }
    } else if (text.includes(',')) {
      if (/^\d+,\d{1,2}$/.test(text)) {
        normalized = text.replace(',', '.');
      } else if (/^\d{1,3}(?:,\d{3})+$/.test(text)) {
        normalized = text.replace(/,/g, '');
      } else return null;
    } else if (text.includes('.')) {
      if (/^\d+\.\d{1,2}$/.test(text)) {
        normalized = text;
      } else if (/^\d{1,3}(?:\.\d{3})+$/.test(text)) {
        normalized = text.replace(/\./g, '');
      } else return null;
    } else normalized = text;

    const value = Number(normalized);
    if (!Number.isFinite(value) || value <= 0) return null;
    return Math.round(value * 100);
  }

  function formatCents(cents) {
    return (cents / 100).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  document.querySelectorAll('input[name="tipo"]').forEach((input) => {
    input.addEventListener('change', () => updateCategories(false));
  });

  amount.addEventListener('beforeinput', (event) => {
    if (event.inputType === 'insertText' && event.data && /[^0-9.,]/.test(event.data)) {
      event.preventDefault();
      error.textContent = 'Use somente números, ponto ou vírgula.';
    }
  });

  amount.addEventListener('input', () => {
    const cleaned = amount.value.replace(/[^0-9.,]/g, '');
    if (cleaned !== amount.value) {
      amount.value = cleaned;
      error.textContent = 'Use somente números, ponto ou vírgula.';
      return;
    }
    error.textContent = '';
  });

  amount.addEventListener('blur', () => {
    if (!amount.value.trim()) return;
    const cents = parseAmountToCents(amount.value);
    if (cents === null) {
      error.textContent = 'Valor inválido. Exemplos: 5000, 5.000 ou 5.000,50.';
      return;
    }
    amount.value = formatCents(cents);
    error.textContent = '';
  });

  form.addEventListener('submit', (event) => {
    const cents = parseAmountToCents(amount.value);
    if (cents === null) {
      event.preventDefault();
      error.textContent = 'Informe um valor válido usando somente números, ponto ou vírgula.';
      amount.focus();
    }
  });

  updateCategories();
})();
