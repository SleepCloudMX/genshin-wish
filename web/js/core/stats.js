/* 数值工具 —— 对应 numpy 的 convolve / cumsum / searchsorted */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core = W.core || {};

  var S = C.stats = {};

  /* 与 np.convolve(a, b, 'full') 同定义，结果长度 len(a)+len(b)-1 */
  S.convolve = function (a, b) {
    var la = a.length, lb = b.length;
    var out = new Float64Array(la + lb - 1);
    for (var i = 0; i < la; i++) {
      var ai = a[i];
      if (ai === 0) continue;
      for (var j = 0; j < lb; j++) out[i + j] += ai * b[j];
    }
    return out;
  };

  /* 累加式卷积：dst[i] += w * (a ⊗ b)[i]，省一次分配 */
  S.convolveInto = function (dst, a, b, w) {
    if (w === 0) return dst;
    var la = a.length, lb = b.length;
    for (var i = 0; i < la; i++) {
      var ai = a[i] * w;
      if (ai === 0) continue;
      for (var j = 0; j < lb; j++) dst[i + j] += ai * b[j];
    }
    return dst;
  };

  S.cumsum = function (a) {
    var out = new Float64Array(a.length), acc = 0;
    for (var i = 0; i < a.length; i++) { acc += a[i]; out[i] = acc; }
    return out;
  };

  /* np.searchsorted(arr, v, side='left')：第一个 arr[i] >= v 的下标，可返回 arr.length */
  S.searchsortedLeft = function (arr, v) {
    var lo = 0, hi = arr.length;
    while (lo < hi) {
      var mid = (lo + hi) >>> 1;
      if (arr[mid] < v) lo = mid + 1; else hi = mid;
    }
    return lo;
  };

  /* cdf 首次达到 1 的下标（尾部可能带 padding） */
  S.supportEnd = function (cdf, eps) {
    if (eps === undefined) eps = 1e-12;
    return S.searchsortedLeft(cdf, 1 - eps);
  };

  S.sum = function (a) {
    var acc = 0;
    for (var i = 0; i < a.length; i++) acc += a[i];
    return acc;
  };

  S.expected = function (pdf) {
    var acc = 0;
    for (var i = 0; i < pdf.length; i++) acc += i * pdf[i];
    return acc;
  };

  S.maxIndex = function (a) {
    var best = 0;
    for (var i = 1; i < a.length; i++) if (a[i] > a[best]) best = i;
    return best;
  };

  /* 把 arr 按权重 w 累加进 dst（长度不足时忽略溢出部分，与 Python 的切片累加同义） */
  S.accumulateWeighted = function (dst, arr, w) {
    var n = Math.min(dst.length, arr.length);
    for (var i = 0; i < n; i++) dst[i] += arr[i] * w;
    return dst;
  };

  /* 首金 pity 平移：pGold[pity+1:] 归一化后前插 0，对应 np.insert(p_gold[pity+1:]/sum, 0, 0) */
  S.shiftedFirstGold = function (pGold, pity) {
    var tail = pGold.subarray(pity + 1);
    var total = S.sum(tail);
    var out = new Float64Array(tail.length + 1);
    for (var i = 0; i < tail.length; i++) out[i + 1] = tail[i] / total;
    return out;
  };

  /* 在 0..1 之间按色带取色（用于热力表底纹） */
  S.ramp = function (stops, t) {
    if (t <= 0) return stops[0];
    if (t >= 1) return stops[stops.length - 1];
    var pos = t * (stops.length - 1);
    var i = Math.floor(pos), f = pos - i;
    return S.mixHex(stops[i], stops[Math.min(i + 1, stops.length - 1)], f);
  };

  S.mixHex = function (h1, h2, f) {
    var a = parseInt(h1.slice(1), 16), b = parseInt(h2.slice(1), 16);
    var r = Math.round(((a >> 16) & 255) * (1 - f) + ((b >> 16) & 255) * f);
    var g = Math.round(((a >> 8) & 255) * (1 - f) + ((b >> 8) & 255) * f);
    var bl = Math.round((a & 255) * (1 - f) + (b & 255) * f);
    return '#' + ((1 << 24) + (r << 16) + (g << 8) + bl).toString(16).slice(1);
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
