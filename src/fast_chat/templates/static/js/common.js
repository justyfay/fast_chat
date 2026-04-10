const TOAST_DURATION_MS = 3500;

function showToast(message, type = 'info') {
  const toaster = document.getElementById('toaster');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  toast.innerHTML = `<span>${icons[type] ?? 'ℹ'}</span><span>${message}</span>`;

  toaster.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('toast-out');
    toast.addEventListener('animationend', () => toast.remove(), { once: true });
  }, TOAST_DURATION_MS);
}
