// USAMIS client-side helpers (progressive enhancement only; never a security
// boundary). Server-side validation and authorization are authoritative.

document.addEventListener('DOMContentLoaded', function () {
  // Auto-dismiss success/info flashes after a while.
  document.querySelectorAll('.flash-success, .flash-info').forEach(function (el) {
    setTimeout(function () {
      el.style.transition = 'opacity .4s';
      el.style.opacity = '0';
      setTimeout(function () { el.remove(); }, 400);
    }, 4000);
  });

  // Confirm consequential actions that opted in via data-confirm.
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (event) {
      if (!window.confirm(el.getAttribute('data-confirm'))) {
        event.preventDefault();
      }
    });
  });
});
