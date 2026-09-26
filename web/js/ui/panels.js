/* 模块共用的展示片段：数据条、图表容器、说明行 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var UI = W.ui = W.ui || {};
  var doc = global.document;

  var P = UI.panels = {
    /* items: [[指标, 数值], ...]，数值列自动等宽对齐 */
    statRow: function (items) {
      var wrap = doc.createElement('div');
      wrap.className = 'statrow';
      items.forEach(function (it) {
        var cell = doc.createElement('div');
        cell.className = 'stat';
        var k = doc.createElement('span');
        k.className = 'stat__k';
        k.textContent = it[0];
        var v = doc.createElement('span');
        v.className = 'stat__v';
        v.innerHTML = it[1];
        cell.appendChild(k);
        cell.appendChild(v);
        wrap.appendChild(cell);
      });
      return wrap;
    },

    chart: function (host, modifier) {
      var node = doc.createElement('div');
      node.className = 'chart' + (modifier ? ' chart--' + modifier : '');
      host.appendChild(node);
      return node;
    },

    /* 返回说明节点，由调用方决定插入位置 */
    note: function (text) {
      var node = doc.createElement('p');
      node.className = 'chartnote';
      node.innerHTML = text;
      return node;
    },

    error: function (host, msg) {
      host.innerHTML = '<p class="viewerror">' + msg + '</p>';
    },

    /* 悬浮框内容：标题 + 两列读数 */
    tip: function (title, rows) {
      var html = '<p class="tip__t">' + title + '</p><table class="tip__table">';
      rows.forEach(function (r) {
        html += '<tr><th>' + r[0] + '</th><td>' + r[1] + '</td></tr>';
      });
      return html + '</table>';
    },

    /* 悬浮框：读数行 + 分位区间行。
     * 上下界各占一列（右对齐、等宽数字），比「85.3 – 93.3」整串文本对得齐；
     * 色块取自图中对应的区间颜色。bands: [{label, color, lo, hi}] */
    tipBands: function (title, rows, bands) {
      var html = '<p class="tip__t">' + title + '</p>';
      if (rows.length) {
        html += '<table class="tip__table">';
        rows.forEach(function (r) {
          html += '<tr><th>' + r[0] + '</th><td>' + r[1] + '</td></tr>';
        });
        html += '</table>';
      }
      html += '<div class="tip__bands">';
      bands.forEach(function (b) {
        html += '<span class="tip__sw" style="background:' + b.color + '"></span>' +
                '<span class="tip__band-k">' + b.label + '</span>' +
                '<span class="tip__num">' + b.lo + '</span>' +
                '<span class="tip__dash">–</span>' +
                '<span class="tip__num">' + b.hi + '</span>';
      });
      return html + '</div>';
    },

    pct: function (v, d) { return (v * 100).toFixed(d === undefined ? 1 : d) + '%'; },

    /* 概率百分数：越靠近 0 或 100 越需要有效位数——
     * 0.2% 与 99.8% 之外各加一位小数，0.02% / 99.98% 再加一位，最多 4 位 */
    pctAdaptive: function (v, maxDigits) {
      var p = v * 100;
      var d = 1, lim = 0.2;
      var max = maxDigits === undefined ? 4 : maxDigits;
      while (d < max && (p < lim || p > 100 - lim)) { d++; lim /= 10; }
      return p.toFixed(d) + '%';
    },

    /* 数值 → 保留 d 位、带千分位 */
    num: function (v, d) {
      return Number(v).toFixed(d === undefined ? 1 : d).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
