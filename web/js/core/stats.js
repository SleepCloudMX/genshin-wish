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

  /* 截断卷积：只保留前 limit 项。下限项只依赖下限项，故结果与全卷积一致，
     供「只关心 ≤ N 抽的累积量」的场合省一半以上运算。 */
  S.convolveTrunc = function (a, b, limit) {
    var la = Math.min(a.length, limit), lb = b.length;
    var out = new Float64Array(Math.min(la + lb - 1, limit));
    for (var i = 0; i < la; i++) {
      var ai = a[i];
      if (ai === 0) continue;
      var jmax = out.length - i;
      if (jmax > lb) jmax = lb;
      for (var j = 0; j < jmax; j++) out[i + j] += ai * b[j];
    }
    return out;
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

  /* --- 分布对象：与 Python 的 UpDistribution 同接口 --- */
  S.makeDistribution = function (pdf, method) {
    var cdf = S.cumsum(pdf);
    return {
      pdf: pdf,
      cdf: cdf,
      method: method || 'exact',
      expected: S.expected(pdf),
      /* 与 np.searchsorted(cdf, q) 同义：首个 cdf[i] >= q 的抽数 */
      quantile: function (q) { return S.searchsortedLeft(cdf, q); },
      probability: function (pulls) {
        if (pulls < 0) return 0;
        return pulls >= cdf.length ? 1 : cdf[pulls];
      }
    };
  };

  S.moments = function (pdf) {
    var m1 = 0, m2 = 0;
    for (var i = 0; i < pdf.length; i++) { m1 += i * pdf[i]; m2 += i * i * pdf[i]; }
    return { mean: m1, variance: m2 - m1 * m1 };
  };

  /* --- 标准正态：erfc 用级数（|x|<1）+ 连分式（|x|≥1），双精度 --- */
  function erfSeries(x) {
    var x2 = x * x, term = x, sum = x;
    for (var n = 1; n < 200; n++) {
      term *= -x2 / n;
      var add = term / (2 * n + 1);
      sum += add;
      if (Math.abs(add) < 1e-18 * Math.abs(sum)) break;
    }
    return 2 / Math.sqrt(Math.PI) * sum;
  }

  function erfcCF(x) {
    /* erfc(x) = e^{-x²}/√π · 1/(x + 1/2/(x + 1/(x + 3/2/(x + ...))))
     * 连分式本身是分母，Lentz 法求出后再取倒数 */
    var tiny = 1e-300;
    var f = x, C = x, D = 0;
    for (var i = 1; i < 500; i++) {
      var a = i / 2, b = x;
      D = b + a * D; if (Math.abs(D) < tiny) D = tiny; D = 1 / D;
      C = b + a / C; if (Math.abs(C) < tiny) C = tiny;
      var delta = C * D;
      f *= delta;
      if (Math.abs(delta - 1) < 1e-17) break;
    }
    return Math.exp(-x * x) / Math.sqrt(Math.PI) / f;
  }

  function erfc(x) {
    if (x < 0) return 2 - erfc(-x);
    if (x < 1) return 1 - erfSeries(x);
    if (x > 30) return 0;
    return erfcCF(x);
  }

  /* 标准正态 CDF */
  S.normCdf = function (z) { return 0.5 * erfc(-z / Math.SQRT2); };

  /* 标准正态分位数：二分求解，机器精度（用于 CLT 通道的上下界） */
  S.normPpf = function (p) {
    if (p <= 0) return -Infinity;
    if (p >= 1) return Infinity;
    var lo = -40, hi = 40;
    for (var i = 0; i < 200; i++) {
      var mid = (lo + hi) / 2;
      if (S.normCdf(mid) < p) lo = mid; else hi = mid;
    }
    return (lo + hi) / 2;
  };

})(typeof globalThis !== 'undefined' ? globalThis : this);
