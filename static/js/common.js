(() => {
  document.querySelectorAll('[data-delete-form]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!window.confirm('Excluir esta movimentação? Essa ação não poderá ser desfeita.')) event.preventDefault();
    });
  });
})();
