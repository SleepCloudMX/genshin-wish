/* 参数控件工厂：按 spec 生成 range / segmented / switch */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var UI = W.ui = W.ui || {};
  var doc = global.document;

  function labelFor(spec, valueEl) {
    var lab = doc.createElement('label');
    lab.className = 'field__label';
    lab.textContent = spec.label;
    if (spec.help) {
      var hint = doc.createElement('span');
      hint.className = 'field__help';
      hint.textContent = spec.help;
      lab.appendChild(hint);
    }
    if (valueEl) lab.appendChild(valueEl);
    return lab;
  }

  function field(spec, state, onChange) {
    var wrap = doc.createElement('div');
    wrap.className = 'field field--' + spec.type;
    var value = state[spec.key];

    if (spec.type === 'range') {
      var out = doc.createElement('output');
      out.className = 'field__value';
      out.textContent = value + (spec.unit || '');
      wrap.appendChild(labelFor(spec, out));
      var input = doc.createElement('input');
      input.type = 'range';
      input.min = spec.min;
      input.max = spec.max;
      input.step = spec.step || 1;
      input.value = value;
      input.setAttribute('aria-label', spec.label);
      input.addEventListener('input', function () {
        out.textContent = input.value + (spec.unit || '');
        onChange(spec.key, Number(input.value), true);
      });
      input.addEventListener('change', function () {
        onChange(spec.key, Number(input.value), false);
      });
      wrap.appendChild(input);
      return wrap;
    }

    if (spec.type === 'segmented') {
      wrap.appendChild(labelFor(spec, null));
      var group = doc.createElement('div');
      group.className = 'segmented';
      group.setAttribute('role', 'radiogroup');
      group.setAttribute('aria-label', spec.label);
      spec.options.forEach(function (opt) {
        var btn = doc.createElement('button');
        btn.type = 'button';
        btn.className = 'segmented__item' + (String(opt.value) === String(value) ? ' is-on' : '');
        btn.textContent = opt.label;
        btn.setAttribute('role', 'radio');
        btn.setAttribute('aria-checked', String(opt.value) === String(value));
        btn.addEventListener('click', function () {
          Array.prototype.forEach.call(group.children, function (c) {
            c.classList.remove('is-on');
            c.setAttribute('aria-checked', 'false');
          });
          btn.classList.add('is-on');
          btn.setAttribute('aria-checked', 'true');
          onChange(spec.key, opt.value, false);
        });
        group.appendChild(btn);
      });
      wrap.appendChild(group);
      return wrap;
    }

    if (spec.type === 'switch') {
      var row = doc.createElement('label');
      row.className = 'switch';
      var box = doc.createElement('input');
      box.type = 'checkbox';
      box.checked = !!value;
      box.addEventListener('change', function () {
        onChange(spec.key, box.checked, false);
      });
      var track = doc.createElement('span');
      track.className = 'switch__track';
      var text = doc.createElement('span');
      text.className = 'switch__text';
      text.textContent = spec.label;
      row.appendChild(box);
      row.appendChild(track);
      row.appendChild(text);
      wrap.appendChild(row);
      if (spec.help) {
        var h = doc.createElement('span');
        h.className = 'field__help field__help--block';
        h.textContent = spec.help;
        wrap.appendChild(h);
      }
      return wrap;
    }

    throw new Error('unknown control type: ' + spec.type);
  }

  UI.controls = {
    build: function (host, specs, state, onChange) {
      host.textContent = '';
      specs.forEach(function (spec) { host.appendChild(field(spec, state, onChange)); });
    }
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
