// Theme toggle, guardian checkbox and multi-step questionnaire.
(function () {
  var root = document.documentElement;
  try { var saved = localStorage.getItem('pt_theme'); if (saved) root.dataset.theme = saved; } catch (e) {}
  var tb = document.getElementById('theme');
  if (tb) tb.onclick = function () {
    var cur = root.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    var next = cur === 'dark' ? 'light' : 'dark'; root.dataset.theme = next;
    try { localStorage.setItem('pt_theme', next); } catch (e) {}
  };
  var age = document.getElementById('age'), guard = document.getElementById('guardian');
  if (age && guard) {
    var sync = function () { guard.hidden = !(age.value !== '' && +age.value < 18); };
    age.oninput = sync; sync();
  }
  var form = document.getElementById('quiz');
  if (!form) return;
  var steps = form.querySelectorAll('.qstep'), i = 0;
  var next = document.getElementById('qnext'), back = document.getElementById('qback');
  var err = document.getElementById('qerr');
  function show() {
    steps.forEach(function (s, n) { s.hidden = n !== i; });
    document.getElementById('qbar').style.width = (i + 1) * 20 + '%';
    document.getElementById('qlabel').textContent = 'Step ' + (i + 1) + ' of 5';
    back.hidden = i === 0; next.textContent = i === 4 ? 'Build my plan' : 'Next';
    err.textContent = '';
  }
  function valid() {
    var s = steps[i], ok = true;
    s.querySelectorAll('input:not([type=radio]):not([type=checkbox])[required]').forEach(function (el) { if (!el.checkValidity()) ok = false; });
    ['body', 'level', 'goal', 'time'].forEach(function (n) {
      if (s.querySelector('input[name=' + n + ']') && !s.querySelector('input[name=' + n + ']:checked')) ok = false;
    });
    return ok;
  }
  next.onclick = function () {
    if (!valid()) { err.textContent = 'Please answer the questions on this step.'; return; }
    if (i === 4) form.submit(); else { i++; show(); }
  };
  back.onclick = function () { i--; show(); };
  show();
})();
