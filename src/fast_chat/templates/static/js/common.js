const TOAST_DURATION_MS = 3500;

function escapeHtml(text) {
  const entities = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return String(text ?? '').replace(/[&<>"']/g, (ch) => entities[ch]);
}

function showToast(message, type = 'info') {
  const toaster = document.getElementById('toaster');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  const icon = document.createElement('span');
  icon.textContent = icons[type] ?? 'ℹ';
  const text = document.createElement('span');
  text.textContent = message;
  toast.append(icon, text);

  toaster.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('toast-out');
    toast.addEventListener('animationend', () => toast.remove(), { once: true });
  }, TOAST_DURATION_MS);
}

let refreshPromise = null;

function refreshSession() {
  refreshPromise ??= fetch('/v1/auth/refresh', { method: 'POST', credentials: 'include' })
    .then((response) => response.ok || response.status === 409)
    .catch(() => false)
    .finally(() => { refreshPromise = null; });
  return refreshPromise;
}

async function apiFetch(url, options) {
  let response = await fetch(url, options);
  if (response.status === 401 || response.redirected) {
    if (!(await refreshSession())) {
      window.location.href = '/login';
      return response;
    }
    response = await fetch(url, options);
  }
  return response;
}
