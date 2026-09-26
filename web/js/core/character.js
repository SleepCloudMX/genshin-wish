/* 角色池 UP 分布 —— 对应 src/genshin_wish/character.py + _dp_golds.py
 *
 * 与 Python 的差异（有意）：pity>0 时 Python 退回 guarantee_seq 的指数枚举
 * （n_uncertain ≤ 20）；这里利用卷积的线性性，先按金数分布加权得到"后续金"
 * 的 PDF，再与平移后的首金卷积，可精算到 n_up = LIMITS.charExactNUp。
 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core = W.core || {};
  var S = C.stats;

  function makeDistribution(pdf) {
    var cdf = S.cumsum(pdf);
    return {
      pdf: pdf,
      cdf: cdf,
      method: 'exact',
      expected: S.expected(pdf),
      /* 与 np.searchsorted(cdf, q) 同义：首个 cdf[i] >= q 的抽数 */
      quantile: function (q) { return S.searchsortedLeft(cdf, q); },
      probability: function (pulls) {
        if (pulls < 0) return 0;
        return pulls >= cdf.length ? 1 : cdf[pulls];
      }
    };
  }
  C.makeDistribution = makeDistribution;

  /* {gold: p} —— DP over (k_miss, 金数)，O(n²) */
  C.dpGoldsTask1 = function (nUncertain, kMissStart) {
    var pUp = C.CAPTURE_RADIANCE_WIN_RATE;
    var maxGold = 2 * nUncertain;
    var states = [null, null, null, null];
    var start = new Float64Array(maxGold + 1);
    start[0] = 1;
    states[kMissStart] = start;

    for (var step = 0; step < nUncertain; step++) {
      var next = [null, null, null, null];
      for (var k = 0; k < 4; k++) {
        var src = states[k];
        if (!src) continue;
        var pw = pUp[k], pl = 1 - pw;
        for (var g = 0; g <= maxGold; g++) {
          var v = src[g];
          if (v === 0) continue;
          if (g + 1 <= maxGold) {
            if (!next[0]) next[0] = new Float64Array(maxGold + 1);
            next[0][g + 1] += v * pw;
          }
          if (k < 3 && g + 2 <= maxGold) {
            if (!next[k + 1]) next[k + 1] = new Float64Array(maxGold + 1);
            next[k + 1][g + 2] += v * pl;
          }
        }
      }
      states = next;
    }

    var result = new Float64Array(maxGold + 1);
    for (var i = 0; i < 4; i++) {
      if (!states[i]) continue;
      for (var g2 = 0; g2 <= maxGold; g2++) result[g2] += states[i][g2];
    }
    return result;
  };

  C.makeCharacterState = function (opts) {
    opts = opts || {};
    var pity = opts.pity || 0;
    var loss = opts.consecutiveLoss || 0;
    if (pity < 0 || pity > C.LIMITS.maxPity.character) {
      throw new RangeError('pity 必须为 0..' + C.LIMITS.maxPity.character);
    }
    if (loss < 0 || loss > 3) throw new RangeError('consecutive_loss 必须为 0..3');
    return { guaranteed: !!opts.guaranteed, pity: pity, consecutiveLoss: loss };
  };

  C.upDistribution = function (state, nUp) {
    if (nUp < 0) throw new RangeError('n_up 不能为负');
    if (nUp === 0) return makeDistribution(Float64Array.from([1.0]));

    var nUncertain = nUp - (state.guaranteed ? 1 : 0);
    var pdfs = C.gold.getGoldPdfs('character', nUncertain === 0 ? 3 : nUncertain * 2 + 3);
    var pGold = pdfs[1];

    if (nUncertain === 0) {
      return makeDistribution(S.shiftedFirstGold(pGold, state.pity));
    }

    var weights = C.dpGoldsTask1(nUncertain, state.consecutiveLoss);
    var maxGold = weights.length - 1;
    while (maxGold > 0 && weights[maxGold] === 0) maxGold--;

    var extra = new Float64Array(pdfs[maxGold - 1].length);
    for (var g = 1; g <= maxGold; g++) {
      if (weights[g] !== 0) S.accumulateWeighted(extra, pdfs[g - 1], weights[g]);
    }
    var firstGold = state.pity === 0 ? pGold : S.shiftedFirstGold(pGold, state.pity);
    var pdf = S.convolve(extra, firstGold);
    if (state.guaranteed) pdf = S.convolve(pdf, pGold);
    return makeDistribution(pdf);
  };

  /* 稳态：按 STABLE_P 加权 k_miss = 0..3 的分布，零填充到最长 */
  C.stableUpDistribution = function (nUp) {
    var dists = [], maxLen = 0, i;
    for (i = 0; i < 4; i++) {
      var d = C.upDistribution(C.makeCharacterState({ consecutiveLoss: i }), nUp);
      dists.push(d);
      if (d.pdf.length > maxLen) maxLen = d.pdf.length;
    }
    var pdf = new Float64Array(maxLen);
    for (i = 0; i < 4; i++) {
      S.accumulateWeighted(pdf, dists[i].pdf, C.STABLE_P[i]);
    }
    return makeDistribution(pdf);
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
