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
    return { guaranteed: !!opts.guaranteed, pity: pity, consecutiveLoss: loss,
             stable: !!opts.stable };
  };

  C.upDistribution = function (state, nUp) {
    if (nUp < 0) throw new RangeError('n_up 不能为负');
    if (nUp === 0) return makeDistribution(Float64Array.from([1.0]));
    if (state.stable) {
      return C.stableUpDistribution(nUp, {
        pity: state.pity, guaranteed: state.guaranteed
      });
    }

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

  /* 稳态：连歪次数未知，按 STABLE_P 加权 k_miss = 0..3 的分布，零填充到最长。
     opts 的 pity / guaranteed 是已知的当前状态，照常施加（缺省即 pity=0、非大保底）。 */
  C.stableUpDistribution = function (nUp, opts) {
    opts = opts || {};
    var dists = [], maxLen = 0, i;
    for (i = 0; i < 4; i++) {
      var d = C.upDistribution(C.makeCharacterState({
        guaranteed: !!opts.guaranteed, pity: opts.pity || 0, consecutiveLoss: i
      }), nUp);
      dists.push(d);
      if (d.pdf.length > maxLen) maxLen = d.pdf.length;
    }
    var pdf = new Float64Array(maxLen);
    for (i = 0; i < 4; i++) {
      S.accumulateWeighted(pdf, dists[i].pdf, C.STABLE_P[i]);
    }
    return makeDistribution(pdf);
  };

  /* --- 给定抽数下（限定数, 常驻数）的联合分布 ---
   * 出金时刻由 pity 过程决定，与「每金是 UP 还是常驻」相互独立，故可分解为
   * P(恰好 g 金 | P 抽) ⊗ 标记链 D[g][u]。对应 character.py 的 pulls_joint_distribution。 */

  /* P(恰好 g 金 | pulls 抽)，g = 0..gMax（尾部概率 < eps 时截断）。
     P(恰好 g 金) = P(T_g ≤ P) − P(T_{g+1} ≤ P)，T_g 由单金 PDF 逐次卷积得到。 */
  C.goldCountPmf = function (pulls, pity, eps) {
    if (eps === undefined) eps = 1e-15;
    var pFirst = C.gold.getGoldPdfs('character')[1];
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

  /* D[g][u] = P(前 g 个金中恰有 u 个 UP)。weights 非空时按 k_miss = 0..3 加权（稳态）。 */
  C.labelChain = function (gMax, kMiss, guaranteed, weights) {
    var pUp = C.CAPTURE_RADIANCE_WIN_RATE;
    var D = [];
    for (var g0 = 0; g0 <= gMax; g0++) D.push(new Float64Array(gMax + 1));
    D[0][0] = 1.0;

    for (var k0 = 0; k0 < 4; k0++) {
      var w = weights ? weights[k0] : (k0 === kMiss ? 1.0 : 0.0);
      if (w === 0) continue;
      var A = [];
      for (var s0 = 0; s0 < 4; s0++) {
        A.push([new Float64Array(gMax + 1), new Float64Array(gMax + 1)]);
      }
      A[k0][guaranteed ? 1 : 0][0] = w;
      for (var g = 1; g <= gMax; g++) {
        var B = [];
        for (var s1 = 0; s1 < 4; s1++) {
          B.push([new Float64Array(gMax + 1), new Float64Array(gMax + 1)]);
        }
        for (var k = 0; k < 4; k++) {
          for (var pend = 0; pend < 2; pend++) {
            var src = A[k][pend];
            if (pend) {
              for (var u1 = 0; u1 < gMax; u1++) B[k][0][u1 + 1] += src[u1];
            } else {
              var pw = pUp[k], pl = 1 - pw;
              for (var u2 = 0; u2 < gMax; u2++) B[0][0][u2 + 1] += src[u2] * pw;
              if (k < 3) for (var u3 = 0; u3 <= gMax; u3++) B[k + 1][1][u3] += src[u3] * pl;
            }
          }
        }
        A = B;
        for (var k2 = 0; k2 < 4; k2++) {
          for (var p2 = 0; p2 < 2; p2++) {
            var row = A[k2][p2], dst = D[g];
            for (var u4 = 0; u4 <= g; u4++) dst[u4] += row[u4];
          }
        }
      }
    }
    return D;
  };

  /* → { matrix[u][s], upMarginal[u] } */
  C.pullsJointDistribution = function (state, pulls) {
    if (pulls < 0) throw new RangeError('pulls 不能为负');
    var pmf = C.goldCountPmf(pulls, state.pity || 0);
    var gMax = pmf.length - 1;
    var chain = C.labelChain(gMax, state.consecutiveLoss,
                             state.guaranteed, state.stable ? C.STABLE_P : null);

    var M = [];
    for (var u = 0; u <= gMax; u++) M.push(new Float64Array(gMax + 2));
    for (var g = 0; g <= gMax; g++) {
      if (pmf[g] === 0) continue;
      for (var u2 = 0; u2 <= g; u2++) {
        if (chain[g][u2] !== 0) M[u2][g - u2] += pmf[g] * chain[g][u2];
      }
    }

    var marg = new Float64Array(gMax + 1);
    for (var u3 = 0; u3 <= gMax; u3++) {
      var row = M[u3], tot = 0;
      for (var s = 0; s < row.length; s++) tot += row[s];
      marg[u3] = tot;
    }
    return { matrix: M, upMarginal: marg };
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
    if (state.stable) {
      var mixed = {};
      for (var kk = 0; kk < 4; kk++) {
        var part = C.nStdDistribution(C.makeCharacterState({
          pity: 0, consecutiveLoss: kk, guaranteed: state.guaranteed
        }), nUp);
        Object.keys(part).forEach(function (ns) {
          mixed[ns] = (mixed[ns] || 0) + C.STABLE_P[kk] * part[ns];
        });
      }
      return mixed;
    }
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
    if (state.stable) {
      /* 混合：各状态的条件分布按 STABLE_P × P(n_std | 该状态) 加权，再各自归一 */
      var acc = {};
      for (var kk = 0; kk < 4; kk++) {
        var sub = C.makeCharacterState({
          pity: 0, consecutiveLoss: kk, guaranteed: state.guaranteed
        });
        var marg = C.nStdDistribution(sub, nUp);
        var maps = C.nStdConditionalPulls(sub, nUp);
        Object.keys(maps).forEach(function (ns) {
          var w = C.STABLE_P[kk] * (marg[ns] || 0);
          if (w === 0) return;
          var pdf = maps[ns].pdf;
          var cur = acc[ns] || (acc[ns] = []);
          for (var i = 0; i < pdf.length; i++) cur[i] = (cur[i] || 0) + w * pdf[i];
        });
      }
      var out = {};
      Object.keys(acc).forEach(function (ns) {
        var arr = acc[ns], total = 0, i;
        for (i = 0; i < arr.length; i++) total += arr[i] || 0;
        if (total <= 0) return;
        var dense = new Float64Array(arr.length);
        for (i = 0; i < arr.length; i++) dense[i] = (arr[i] || 0) / total;
        out[ns] = makeDistribution(dense);
      });
      return out;
    }
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
