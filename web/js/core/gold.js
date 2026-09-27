/* 出金 PDF —— 对应 src/genshin_wish/_gold.py
 * 索引语义：pdf[i] = 恰好 i 抽出金；index 0 恒为 0（占位）。
 * 单金数组长度 hardPity+1，k 金数组长度 k*hardPity+1。
 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core = W.core || {};
  var S = C.stats;

  var G = C.gold = {};

  G.buildGoldPdf = function (pool) {
    var hard = pool.hardPity;
    var arr = [0];
    var nConst = pool.softPityStart - 1;
    for (var i = 0; i < nConst; i++) arr.push(pool.baseRate);

    if (pool.softPityStart2 === null) {
      var nRamp = hard - pool.softPityStart;
      for (var j = 1; j <= nRamp; j++) arr.push(pool.baseRate + pool.softPityStep * j);
    } else {
      var nRamp1 = pool.softPityStart2 - pool.softPityStart;
      for (var a = 1; a <= nRamp1; a++) arr.push(pool.baseRate + pool.softPityStep * a);
      var ramp1End = pool.baseRate + pool.softPityStep * nRamp1;
      var nRamp2 = hard - pool.softPityStart2;
      for (var b = 1; b <= nRamp2; b++) arr.push(ramp1End + pool.softPityStep2 * b);
    }
    arr.push(1.0);
    return Float64Array.from(arr);
  };

  var cache = {};   /* poolKey -> {pdfs: Float64Array[]} */

  function buildFirstGold(pool) {
    /* pdfs[1][i] = P(首金恰好第 i 抽)，由生存概率递推 */
    var single = G.buildGoldPdf(pool);
    var pdf = new Float64Array(single.length);
    var survive = 1.0;
    for (var i = 0; i < single.length; i++) {
      pdf[i] = survive * single[i];
      survive *= 1.0 - single[i];
    }
    return pdf;
  }

  G.getGoldPdfs = function (poolKey, minGold) {
    minGold = minGold || 0;
    var pool = C.POOLS[poolKey];
    if (!pool) throw new Error('unknown pool: ' + poolKey);

    var entry = cache[poolKey];
    if (!entry) {
      entry = cache[poolKey] = { pdfs: [Float64Array.from([1.0]), buildFirstGold(pool)] };
    }
    if (minGold > C.LIMITS.goldTableMax) {
      throw new RangeError('超出金表上限 ' + C.LIMITS.goldTableMax + ' 金（请求 ' + minGold + '）');
    }
    while (entry.pdfs.length <= minGold) {
      entry.pdfs.push(S.convolve(entry.pdfs[1], entry.pdfs[entry.pdfs.length - 1]));
    }
    return entry.pdfs;
  };

  /* P(恰好 g 金 | pulls 抽)，g = 0..gMax（尾部概率 < eps 时截断）。
     P(恰好 g 金) = P(T_g ≤ P) − P(T_{g+1} ≤ P)，T_g 由单金 PDF 逐次卷积得到
     （首金按当前 pity 平移）；只对 t ≤ pulls 求和，卷积可截断到 pulls+1 项。 */
  G.goldCountPmf = function (poolKey, pity, pulls, eps) {
    if (eps === undefined) eps = 1e-15;
    var pFirst = G.getGoldPdfs(poolKey)[1];
    var dist = pity > 0 ? S.shiftedFirstGold(pFirst, pity) : Float64Array.from(pFirst);
    var out = [], prev = 1.0;
    for (var g = 0; g <= pulls + 1; g++) {
      var n = Math.min(dist.length, pulls + 1), cur = 0;
      for (var i = 0; i < n; i++) cur += dist[i];
      out.push(Math.max(prev - cur, 0));
      if (cur < eps) break;
      dist = S.convolveTrunc(dist, pFirst, pulls + 1);
      prev = cur;
    }
    return out;
  };

  G.clearCache = function () { cache = {}; };
})(typeof globalThis !== 'undefined' ? globalThis : this);
