// Minimal toast helper using Bootstrap 5 styles without JS dependency
export function showToast(message, variant = "primary") {
  const stack = document.getElementById('toast-stack');
  if (!stack) return;
  const wrap = document.createElement('div');
  wrap.innerHTML = `
  <div class="toast align-items-center text-bg-${variant} border-0 show" role="alert" aria-live="assertive" aria-atomic="true" style="min-width:260px">
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" aria-label="Close"></button>
    </div>
  </div>`;
  const el = wrap.firstElementChild;
  stack.appendChild(el);
  el.querySelector('.btn-close')?.addEventListener('click', () => el.remove());
  setTimeout(() => el.remove(), 3500);
}

// expose globally for inline handlers
window.showToast = showToast;
