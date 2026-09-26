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

    pct: function (v, d) { return (v * 100).toFixed(d === undefined ? 1 : d) + '%'; },

    /* 数值 → 保留 d 位、带千分位 */
    num: function (v, d) {
      return Number(v).toFixed(d === undefined ? 1 : d).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
