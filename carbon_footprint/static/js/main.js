/*
  main.js
  ─────────────────────────────────────────────────────────────
  Global JavaScript loaded on every page.
  ─────────────────────────────────────────────────────────────
*/

/* ── Auto-dismiss flash alerts after 5 seconds ──────────── */
document.addEventListener('DOMContentLoaded', function () {
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      alert.style.opacity = '0';
      alert.style.transition = 'opacity 0.5s';
      setTimeout(() => alert.remove(), 500);
    }, 5000);
  });
});
