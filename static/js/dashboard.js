(() => {
  const monthly = JSON.parse(document.querySelector('#monthly-data').textContent);
  const categories = JSON.parse(document.querySelector('#category-data').textContent);
  const chartColors = ['#73c6a4', '#5f8fc1', '#d6b36b', '#b787d4', '#e18c74', '#7aa6a1'];
  const money = (value, decimals = true) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: decimals ? 2 : 0, maximumFractionDigits: decimals ? 2 : 0 }).format(value || 0);

  const barChart = document.querySelector('#bar-chart');
  const max = Math.max(1, ...monthly.flatMap((item) => [item.receita, item.despesa]));
  barChart.innerHTML = monthly.map((item) => `<div class="bar-group" title="${item.label}: receitas ${money(item.receita)}, despesas ${money(item.despesa)}"><span class="bar income" style="height:${Math.max(1, item.receita / max * 100)}%"></span><span class="bar expense" style="height:${Math.max(1, item.despesa / max * 100)}%"></span><span class="bar-label">${item.label}</span></div>`).join('');

  const donut = document.querySelector('#category-donut');
  const total = categories.reduce((sum, item) => sum + item.valor, 0);
  document.querySelector('#donut-total').textContent = money(total, false);
  const legend = document.querySelector('#category-legend');
  if (!total) {
    donut.style.background = 'conic-gradient(#26324a 0 100%)';
    legend.innerHTML = '<span class="metric-caption">Cadastre despesas para visualizar.</span>';
    return;
  }
  let cursor = 0;
  donut.style.background = `conic-gradient(${categories.map((item, index) => { const start = cursor; cursor += item.valor / total * 100; return `${chartColors[index % chartColors.length]} ${start}% ${cursor}%`; }).join(',')})`;
  legend.innerHTML = categories.slice(0, 6).map((item, index) => `<div class="category-row"><i style="background:${chartColors[index % chartColors.length]}"></i><span>${item.categoria}</span><strong>${Math.round(item.valor / total * 100)}%</strong></div>`).join('');
})();
