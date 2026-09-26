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

  var makeDistribution = C.makeDistribution = S.makeDistribution;

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

  /* --- 金数 + 常驻数联合 DP（_dp_golds_full）---
   * 返回 byNs[ns][gold] = P(恰好 gold 金、其中 ns 个常驻)。 */
  C.dpGoldsFull = function (nUncertain, kMissStart) {
    var pUp = C.CAPTURE_RADIANCE_WIN_RATE;
    var maxGold = 2 * nUncertain;
    var W1 = nUncertain + 1;                 /* ns 维宽度 */
    var size = (maxGold + 1) * W1;
    var states = [null, null, null, null];
    var start = new Float64Array(size);
    start[0] = 1;
    states[kMissStart] = start;

    for (var step = 0; step < nUncertain; step++) {
      var next = [null, null, null, null];
      for (var k = 0; k < 4; k++) {
        var src = states[k];
        if (!src) continue;
        var pw = pUp[k], pl = 1 - pw;
        for (var g = 0; g <= maxGold; g++) {
          var row = g * W1;
          for (var ns = 0; ns <= nUncertain; ns++) {
            var v = src[row + ns];
            if (v === 0) continue;
            if (g + 1 <= maxGold) {
              if (!next[0]) next[0] = new Float64Array(size);
              next[0][(g + 1) * W1 + ns] += v * pw;
            }
            if (k < 3 && g + 2 <= maxGold && ns + 1 <= nUncertain) {
              if (!next[k + 1]) next[k + 1] = new Float64Array(size);
              next[k + 1][(g + 2) * W1 + ns + 1] += v * pl;
            }
          }
        }
      }
      states = next;
    }

    var byNs = [];
    for (var s = 0; s <= nUncertain; s++) byNs.push(new Float64Array(maxGold + 1));
    for (var kk = 0; kk < 4; kk++) {
      var st = states[kk];
      if (!st) continue;
      for (var g2 = 0; g2 <= maxGold; g2++) {
        for (var ns2 = 0; ns2 <= nUncertain; ns2++) {
          var val = st[g2 * W1 + ns2];
          if (val !== 0) byNs[ns2][g2] += val;
        }
      }
    }
    return byNs;
  };

  /* {n_std: P} —— 仅支持 pity = 0 */
  C.nStdDistribution = function (state, nUp) {
    if (state.pity !== 0) throw new RangeError('n_std 分布仅支持 pity = 0');
    var nUncertain = nUp - (state.guaranteed ? 1 : 0);
    if (nUncertain <= 0) return { 0: 1.0 };
    var byNs = C.dpGoldsFull(nUncertain, state.consecutiveLoss);
    var result = {};
    for (var ns = 0; ns < byNs.length; ns++) {
      var total = 0;
      for (var g = 0; g < byNs[ns].length; g++) total += byNs[ns][g];
      if (total > 0) result[ns] = total;
    }
    return result;
  };

  /* {n_std: 条件抽数分布} —— 仅支持 pity = 0 */
  C.nStdConditionalPulls = function (state, nUp) {
    if (state.pity !== 0) throw new RangeError('条件抽数分布仅支持 pity = 0');
    var nUncertain = nUp - (state.guaranteed ? 1 : 0);
    var pdfs = C.gold.getGoldPdfs('character', 3);
    var pGold = pdfs[1];

    if (nUncertain <= 0) {
      /* 无不确定部分：仅有的大保底金，抽数分布即平移后的首金
         （Python 此分支取错了金表，JS 按正确语义实现） */
      return { 0: makeDistribution(S.shiftedFirstGold(pGold, state.pity)) };
    }

    var byNs = C.dpGoldsFull(nUncertain, state.consecutiveLoss);
    var result = {};
    for (var ns = 0; ns < byNs.length; ns++) {
      var total = 0, g;
      for (g = 0; g < byNs[ns].length; g++) total += byNs[ns][g];
      if (total <= 0) continue;
      var maxGold = byNs[ns].length - 1;
      while (maxGold > 0 && byNs[ns][maxGold] === 0) maxGold--;
      var goldPdfs = C.gold.getGoldPdfs('character', maxGold);
      var pdf = new Float64Array(goldPdfs[maxGold].length);
      for (g = 1; g <= maxGold; g++) {
        if (byNs[ns][g] !== 0) S.accumulateWeighted(pdf, goldPdfs[g], byNs[ns][g] / total);
      }
      if (state.guaranteed) pdf = S.convolve(pdf, pGold);
      result[ns] = makeDistribution(pdf);
    }
    return result;
  };

  /* {radiance 次数: P} —— 仅支持 pity = 0 */
  C.radianceDistFromNUp = function (nUp, kMiss) {
    var pUp = C.CAPTURE_RADIANCE_WIN_RATE;
    var R = nUp + 1;
    var dp = new Float64Array(4 * R);
    dp[kMiss * R + 0] = 1;
    for (var step = 0; step < nUp; step++) {
      var next = new Float64Array(4 * R);
      for (var k = 0; k < 4; k++) {
        var pk = pUp[k];
        for (var r = 0; r <= step; r++) {
          var v = dp[k * R + r];
          if (v === 0) continue;
          next[r] += v * 0.5;                       /* 50/50 中 */
          next[r + 1] += v * (pk - 0.5);            /* 捕获明光 */
          if (k < 3) next[(k + 1) * R + r] += v * (1 - pk);   /* 歪 */
        }
      }
      dp = next;
    }
    var result = {}, total = 0;
    for (var r2 = 0; r2 <= nUp; r2++) {
      var acc = 0;
      for (var k2 = 0; k2 < 4; k2++) acc += dp[k2 * R + r2];
      if (acc > 0) { result[r2] = acc; total += acc; }
    }
    Object.keys(result).forEach(function (r3) { result[r3] /= total; });
    return result;
  };

  C.radianceDistribution = function (state, nUp) {
    if (state.pity !== 0) throw new RangeError('捕获明光分布仅支持 pity = 0');
    var nUncertain = nUp - (state.guaranteed ? 1 : 0);
    if (nUncertain <= 0) return { 0: 1.0 };
    return C.radianceDistFromNUp(nUncertain, state.consecutiveLoss);
  };

  /* 给定 win(1)/loss(2) 序列的明光次数分布 */
  C.radianceDistFromSeq = function (seq) {
    var pUp = C.CAPTURE_RADIANCE_WIN_RATE;
    var k = 0, probs = [];
    for (var i = 0; i < seq.length; i++) {
      if (seq[i] === 1) {
        var pk = pUp[k];
        if (pk > 0.5) probs.push((pk - 0.5) / pk);
        k = 0;
      } else if (k < 3) {
        k += 1;
      }
    }
    var dp = [1];
    for (var j = 0; j < probs.length; j++) {
      var p = probs[j];
      var next = new Float64Array(dp.length + 1);
      for (var r = 0; r < dp.length; r++) {
        next[r] += dp[r] * (1 - p);
        next[r + 1] += dp[r] * p;
      }
      dp = next;
    }
    var out = {};
    for (var r2 = 0; r2 < dp.length; r2++) if (dp[r2] !== 0) out[r2] = dp[r2];
    return out;
  };

  /* --- 5.0 前机制：纯 50/50 + 大保底（无捕获明光） --- */

  C.pre50Pdfs = function (maxN, pGold, pGold2) {
    var len = Math.max(pGold.length, pGold2.length);
    var up1 = new Float64Array(len);
    for (var i = 0; i < pGold.length; i++) up1[i] = 0.5 * pGold[i];
    for (var j = 0; j < pGold2.length; j++) up1[j] += 0.5 * pGold2[j];
    var out = new Array(maxN + 1);
    var pdf = up1;
    out[0] = new Float64Array([1.0]);
    for (var n = 1; n <= maxN; n++) {
      if (n > 1) pdf = S.convolve(pdf, up1);
      out[n] = pdf;
    }
    return out;
  };

  C.pre50Moments = function (pGold, pGold2) {
    var len = Math.max(pGold.length, pGold2.length);
    var up1 = new Float64Array(len);
    for (var i = 0; i < pGold.length; i++) up1[i] = 0.5 * pGold[i];
    for (var j = 0; j < pGold2.length; j++) up1[j] += 0.5 * pGold2[j];
    return S.moments(up1);
  };

  /* 稳态下每个 UP 的均值/方差（捕获明光，4 状态） */
  C.post50Moments = function (pGold) {
    var pUp = C.CAPTURE_RADIANCE_WIN_RATE;
    var m = S.moments(pGold);
    var muGold = m.mean, varGold = m.variance;
    var muLoss = 2 * muGold;
    var mu = 0, m2 = 0;
    for (var s = 0; s < 4; s++) {
      var pi = C.STABLE_P[s];
      var muS = pUp[s] * muGold + (1 - pUp[s]) * muLoss;
      var m2S = pUp[s] * (varGold + muGold * muGold) +
                (1 - pUp[s]) * (2 * varGold + muLoss * muLoss);
      mu += pi * muS;
      m2 += pi * m2S;
    }
    return { mean: mu, variance: m2 - mu * mu };
  };

  C.upDistributionPre50 = function (state, nUp) {
    var nUncertain = nUp - (state.guaranteed ? 1 : 0);
    var pdfs = C.gold.getGoldPdfs('character', nUncertain === 0 ? 3 : nUncertain * 2 + 3);
    var pGold = pdfs[1];

    if (nUncertain === 0) {
      if (!state.guaranteed && nUp === 0) return makeDistribution(new Float64Array([1.0]));
      return makeDistribution(S.shiftedFirstGold(pGold, state.pity));
    }

    var pGold2 = S.convolve(pGold, pGold);
    var result = C.pre50Pdfs(nUncertain, pGold, pGold2)[nUncertain];

    if (state.pity > 0) {
      var pPity = S.shiftedFirstGold(pGold, state.pity);
      var pTwo = S.convolve(pPity, pGold);
      var len = Math.max(pPity.length, pTwo.length);
      var first = new Float64Array(len);
      for (var i = 0; i < pPity.length; i++) first[i] += 0.5 * pPity[i];
      for (var j = 0; j < pTwo.length; j++) first[j] += 0.5 * pTwo[j];
      var rest = nUncertain === 1 ? new Float64Array([1.0])
                                  : C.pre50Pdfs(nUncertain - 1, pGold, pGold2)[nUncertain - 1];
      result = S.convolve(first, rest);
    }
    if (state.guaranteed) result = S.convolve(result, pGold);
    return makeDistribution(result);
  };

  C.stableUpDistributionPre50 = function (nUp) {
    return C.upDistributionPre50(C.makeCharacterState({}), nUp);
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
