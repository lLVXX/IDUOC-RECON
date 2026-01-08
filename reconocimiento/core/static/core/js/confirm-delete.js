document.addEventListener('DOMContentLoaded', () => {
  const modalEl = document.getElementById('confirmDeleteModal');
  modalEl.addEventListener('show.bs.modal', event => {
    const button = event.relatedTarget;
    const url    = button.getAttribute('data-delete-url');
    const msg    = button.getAttribute('data-delete-msg');

    modalEl.querySelector('#confirmDeleteMessage').textContent = msg;
    modalEl.querySelector('#confirmDeleteForm').action = url;
  });
});