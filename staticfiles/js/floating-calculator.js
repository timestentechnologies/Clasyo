(function () {
  const SEL = {
    root: '#floatingCalculator',
    toggle: '[data-fc-toggle]',
    close: '[data-fc-close]',
    expr: '[data-fc-expr]',
    result: '[data-fc-result]',
    btn: '[data-fc-btn]',
    mode: '[data-fc-mode]',
  };

  function clampNumberString(s) {
    if (!isFinite(Number(s))) return 'Error';
    const n = Number(s);
    if (Math.abs(n) >= 1e12 || (Math.abs(n) > 0 && Math.abs(n) < 1e-9)) {
      return n.toExponential(10).replace(/0+e/, 'e').replace(/\.(?=e)/, '');
    }
    const str = String(n);
    if (str.length > 16) return n.toPrecision(12);
    return str;
  }

  function factorial(x) {
    if (!isFinite(x)) return NaN;
    if (x < 0) return NaN;
    if (Math.floor(x) !== x) return NaN;
    if (x > 170) return Infinity;
    let r = 1;
    for (let i = 2; i <= x; i++) r *= i;
    return r;
  }

  function nPr(n, r) {
    if (r > n) return 0;
    return factorial(n) / factorial(n - r);
  }

  function nCr(n, r) {
    if (r > n) return 0;
    return factorial(n) / (factorial(r) * factorial(n - r));
  }

  function degToRad(x) {
    return (x * Math.PI) / 180;
  }

  function radToDeg(x) {
    return (x * 180) / Math.PI;
  }

  function buildEvalContext(getMode) {
    const trig = (fn) => (x) => {
      const mode = getMode();
      const v = mode === 'DEG' ? degToRad(x) : x;
      return fn(v);
    };

    const atrig = (fn) => (x) => {
      const v = fn(x);
      const mode = getMode();
      return mode === 'DEG' ? radToDeg(v) : v;
    };

    return {
      pi: Math.PI,
      e: Math.E,
      abs: Math.abs,
      sqrt: Math.sqrt,
      cbrt: Math.cbrt,
      exp: Math.exp,
      pow: Math.pow,
      ln: Math.log,
      log: (x) => Math.log10(x),
      floor: Math.floor,
      ceil: Math.ceil,
      round: Math.round,
      max: Math.max,
      min: Math.min,
      sin: trig(Math.sin),
      cos: trig(Math.cos),
      tan: trig(Math.tan),
      asin: atrig(Math.asin),
      acos: atrig(Math.acos),
      atan: atrig(Math.atan),
      factorial,
      nPr,
      nCr,
    };
  }

  function sanitizeExpression(raw) {
    let s = raw;

    s = s.replace(/×/g, '*').replace(/÷/g, '/');
    s = s.replace(/\^/g, '**');

    s = s.replace(/\bπ\b/g, 'pi');

    s = s.replace(/%/g, '*0.01');

    s = s.replace(/\s+/g, '');

    return s;
  }

  function safeEvaluate(expr, ctx) {
    const s = sanitizeExpression(expr);

    if (!s) return { ok: true, value: 0 };

    if (!/^[0-9a-zA-Z_\.\+\-\*\/\(\),!%\s]*$/.test(expr)) {
      return { ok: false, error: 'Invalid' };
    }

    const replaced = s.replace(/(\d+(?:\.\d+)?)!/g, 'factorial($1)');

    const args = Object.keys(ctx);
    const vals = Object.values(ctx);

    try {
      const fn = new Function(...args, `"use strict"; return (${replaced});`);
      const out = fn(...vals);
      if (typeof out !== 'number' || Number.isNaN(out)) return { ok: false, error: 'Error' };
      return { ok: true, value: out };
    } catch (e) {
      return { ok: false, error: 'Error' };
    }
  }

  function init() {
    const root = document.querySelector(SEL.root);
    if (!root) return;

    const toggleBtn = root.querySelector(SEL.toggle);
    const closeBtn = root.querySelector(SEL.close);
    const exprEl = root.querySelector(SEL.expr);
    const resEl = root.querySelector(SEL.result);
    const modeBtn = root.querySelector(SEL.mode);

    let mode = 'DEG';
    let memory = 0;

    const ctx = buildEvalContext(() => mode);

    function setMode(next) {
      mode = next;
      if (modeBtn) modeBtn.textContent = mode;
      preview();
    }

    function open() {
      root.classList.add('floating-calculator--open');
      try { exprEl && exprEl.focus(); } catch (_) {}
    }

    function close() {
      root.classList.remove('floating-calculator--open');
    }

    function toggle() {
      if (root.classList.contains('floating-calculator--open')) close();
      else open();
    }

    function getExpr() {
      return (exprEl && exprEl.value) ? exprEl.value : '';
    }

    function setExpr(v) {
      if (!exprEl) return;
      exprEl.value = v;
      preview();
    }

    function setResult(v) {
      if (!resEl) return;
      resEl.value = v;
    }

    function append(token) {
      setExpr(getExpr() + token);
    }

    function backspace() {
      const s = getExpr();
      setExpr(s.slice(0, -1));
    }

    function clearAll() {
      setExpr('');
      setResult('0');
    }

    function preview() {
      const s = getExpr();
      const r = safeEvaluate(s, ctx);
      if (!s) {
        setResult('0');
        return;
      }
      if (r.ok) setResult(clampNumberString(String(r.value)));
      else setResult(r.error);
    }

    function equals() {
      const s = getExpr();
      const r = safeEvaluate(s, ctx);
      if (r.ok) {
        setExpr(clampNumberString(String(r.value)));
      } else {
        setResult(r.error);
      }
    }

    function applyUnary(fnName) {
      const s = getExpr();
      if (!s) return;
      setExpr(fnName + '(' + s + ')');
    }

    function handleAction(action) {
      switch (action) {
        case 'OPEN':
          open();
          break;
        case 'CLOSE':
          close();
          break;
        case 'TOGGLE':
          toggle();
          break;
        case 'AC':
          clearAll();
          break;
        case 'BS':
          backspace();
          break;
        case 'EQ':
          equals();
          break;
        case 'MODE':
          setMode(mode === 'DEG' ? 'RAD' : 'DEG');
          break;
        case 'ANS':
          append(resEl ? resEl.value : '0');
          break;
        case 'MC':
          memory = 0;
          break;
        case 'MR':
          append(String(memory));
          break;
        case 'M+':
          memory += Number(resEl ? resEl.value : 0) || 0;
          break;
        case 'M-':
          memory -= Number(resEl ? resEl.value : 0) || 0;
          break;
        case 'SIN':
          applyUnary('sin');
          break;
        case 'COS':
          applyUnary('cos');
          break;
        case 'TAN':
          applyUnary('tan');
          break;
        case 'ASIN':
          applyUnary('asin');
          break;
        case 'ACOS':
          applyUnary('acos');
          break;
        case 'ATAN':
          applyUnary('atan');
          break;
        case 'LOG':
          applyUnary('log');
          break;
        case 'LN':
          applyUnary('ln');
          break;
        case 'SQRT':
          applyUnary('sqrt');
          break;
        case 'CBRT':
          applyUnary('cbrt');
          break;
        case 'ABS':
          applyUnary('abs');
          break;
        case 'EXP':
          applyUnary('exp');
          break;
        case 'FACT':
          append('!');
          break;
        case 'POW':
          append('^');
          break;
        case 'PI':
          append('π');
          break;
        case 'E':
          append('e');
          break;
        case 'NCR':
          append('nCr(');
          break;
        case 'NPR':
          append('nPr(');
          break;
        default:
          append(action);
      }
    }

    root.addEventListener('click', function (e) {
      const t = e.target;
      const btn = t && t.closest ? t.closest(SEL.btn) : null;
      if (!btn) return;
      const action = btn.getAttribute('data-fc-btn');
      if (!action) return;
      handleAction(action);
    });

    if (toggleBtn) toggleBtn.addEventListener('click', toggle);
    if (closeBtn) closeBtn.addEventListener('click', close);
    if (modeBtn) modeBtn.addEventListener('click', function () { handleAction('MODE'); });

    document.addEventListener('keydown', function (e) {
      if (!root.classList.contains('floating-calculator--open')) {
        if (e.altKey && e.key.toLowerCase() === 'c') {
          e.preventDefault();
          open();
        }
        return;
      }

      if (e.key === 'Escape') {
        e.preventDefault();
        close();
        return;
      }

      const k = e.key;
      if ((k >= '0' && k <= '9') || ['+', '-', '*', '/', '(', ')', '.', ','].includes(k)) {
        e.preventDefault();
        append(k === ',' ? ',' : k);
        return;
      }
      if (k === 'Enter' || k === '=') {
        e.preventDefault();
        equals();
        return;
      }
      if (k === 'Backspace') {
        e.preventDefault();
        backspace();
        return;
      }
      if (k === 'Delete') {
        e.preventDefault();
        clearAll();
        return;
      }
    });

    if (exprEl) {
      exprEl.addEventListener('input', preview);
      exprEl.addEventListener('focus', preview);
    }

    setMode('DEG');
    setExpr('');
    setResult('0');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
