/* 武器池 / 常驻池 / 联合分布 / 十连多金 —— 对应 weapon.py、standard.py、joint.py */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core = W.core || {};
  var S = C.stats;
  var makeDistribution = S.makeDistribution;

  /* --- 武器池：定轨（不取消目标） --- */

  /* 单把 A 所需的金数分布，按 [金数, 概率] 返回 */
  function singleCopyWeights(ep, prevStd) {
    if (ep === 1) return [[1, 1.0]];
    if (prevStd) return [[1, 0.5], [2, 0.5]];
    return [[1, 0.375], [2, 0.625]];
  }

  /* count_a 把 A 的金数分布：每把获得后状态重置 */
  C.weaponTargetWeights = function (countA, ep, prevStd) {
    var maxGold = 2 * countA;
    var w = new Float64Array(maxGold + 1);
    w[0] = 1;
    var e = ep, ps = prevStd;
    for (var n = 0; n < countA; n++) {
      var single = singleCopyWeights(e, ps);
      var next = new Float64Array(maxGold + 1);
      for (var g1 = 0; g1 <= maxGold; g1++) {
        if (w[g1] === 0) continue;
        for (var j = 0; j < single.length; j++) {
          next[g1 + single[j][0]] += w[g1] * single[j][1];
        }
      }
      w = next;
      e = 0;
      ps = false;
    }
    return w;
  };

  C.makeWeaponState = function (opts) {
    opts = opts || {};
    var pity = opts.pity || 0;
    if (pity < 0 || pity > C.LIMITS.maxPity.weapon) {
      throw new RangeError('pity 必须为 0..' + C.LIMITS.maxPity.weapon);
    }
    return {
      pity: pity,
      epitomizedPoints: opts.epitomizedPoints ? 1 : 0,
      prevStandard: !!opts.prevStandard
    };
  };

  C.weaponUpDistribution = function (state, countA) {
    if (countA <= 0) return makeDistribution(new Float64Array([1.0]));
    var weights = C.weaponTargetWeights(countA, state.epitomizedPoints, state.prevStandard);
    var maxGold = weights.length - 1;
    while (maxGold > 0 && weights[maxGold] === 0) maxGold--;

    var pdfs = C.gold.getGoldPdfs('weapon', maxGold);
    var pGold = pdfs[1];
    var firstGold = S.shiftedFirstGold(pGold, state.pity);

    /* 权重计的是总金数；首金的抽数已由 firstGold 给出，故只卷积其余 maxGold-1 金 */
    var result = new Float64Array(firstGold.length + pdfs[maxGold - 1].length - 1);
    for (var g = 1; g <= maxGold; g++) {
      if (weights[g] !== 0) S.convolveInto(result, firstGold, pdfs[g - 1], weights[g]);
    }
    var d = makeDistribution(result);
    d.goldWeights = weights;
    return d;
  };

  /* --- 武器池：给定抽数下（目标数, 歪出五星数）的联合分布 ---
   * 与角色池同理：出金时刻由 pity 过程决定，与「每金是目标 / 另一把限定 / 常驻」独立。
   * 对应 weapon.py 的 weapon_pulls_joint_distribution。 */

  /* D[g][u] = P(前 g 个金中恰有 u 个是定轨目标)。
     状态 = (命定值, 上一金为常驻)：命定值满则必为目标；常驻保底生效时池中只有两把限定
     （各半）；否则 37.5% 目标 / 37.5% 另一把限定 / 25% 常驻。得到目标后状态归零，
     得到另一把限定 → 命定值 +1，得到常驻 → 命定值 +1 且常驻保底生效。 */
  C.weaponLabelChain = function (gMax, ep, prevStd) {
    var P_A = 0, P_B = 1, P_S = 2;
    var label = [
      [[0.375, 0.375, 0.25], [0.5, 0.5, 0.0]],   /* 命定值 0：[上金为限定, 上金为常驻] */
      [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]         /* 命定值 1：无论上金为何，下一金必为目标 */
    ];
    /* 状态编号 = ep * 2 + prevStd；后继：目标 → 0，另一把限定 → 2，常驻 → 3 */
    var next = [0, -1, 2, 3];
    var A = [];
    for (var st = 0; st < 4; st++) A.push(new Float64Array(gMax + 1));
    A[ep * 2 + (prevStd ? 1 : 0)][0] = 1.0;

    var D = [];
    for (var g0 = 0; g0 <= gMax; g0++) D.push(new Float64Array(gMax + 1));
    D[0][0] = 1.0;
    for (var g = 1; g <= gMax; g++) {
      var B = [];
      for (var s1 = 0; s1 < 4; s1++) B.push(new Float64Array(gMax + 1));
      for (var s2 = 0; s2 < 4; s2++) {
        var src = A[s2];
        var probs = label[s2 < 2 ? 0 : 1][s2 % 2];
        if (probs[P_A]) {
          var dstA = B[next[0]];
          for (var u1 = 0; u1 < gMax; u1++) dstA[u1 + 1] += src[u1] * probs[P_A];
        }
        if (probs[P_B]) {
          var dstB = B[next[2]];
          for (var u2 = 0; u2 <= gMax; u2++) dstB[u2] += src[u2] * probs[P_B];
        }
        if (probs[P_S]) {
          var dstS = B[next[3]];
          for (var u3 = 0; u3 <= gMax; u3++) dstS[u3] += src[u3] * probs[P_S];
        }
      }
      A = B;
      for (var s3 = 0; s3 < 4; s3++) {
        var row = A[s3], dst = D[g];
        for (var u4 = 0; u4 <= g; u4++) dst[u4] += row[u4];
      }
    }
    return D;
  };

  C.weaponPullsJointDistribution = function (state, pulls) {
    if (pulls < 0) throw new RangeError('pulls 不能为负');
    var pmf = C.gold.goldCountPmf('weapon', state.pity || 0, pulls);
    var chain = C.weaponLabelChain(pmf.length - 1, state.epitomizedPoints, state.prevStandard);
    return C.jointFromLabels(pmf, chain);
  };

  /* --- 常驻池：纯出金分布 --- */
  C.standardDistribution = function (pity, nGold) {
    if (nGold <= 0) return makeDistribution(new Float64Array([1.0]));
    var pdfs = C.gold.getGoldPdfs('character', nGold);
    var pGold = pdfs[1];
    var result = S.shiftedFirstGold(pGold, pity);
    for (var i = 1; i < nGold; i++) result = S.convolve(result, pGold);
    return makeDistribution(result);
  };

  /* --- 联合：角色池 + 武器池相互独立，总抽数 = 两者卷积 --- */
  C.jointDistribution = function (charState, charNUp, weaponState, weaponCount) {
    var char = C.upDistribution(charState, charNUp);
    var weapon = C.weaponUpDistribution(weaponState, weaponCount);
    var d = makeDistribution(S.convolve(char.pdf, weapon.pdf));
    d.char = char;
    d.weapon = weapon;
    return d;
  };

  /* --- 十连多金：稳态下一次十连出 ≥ gold 个金的概率 --- */
  C.tenPullMultiGold = function (poolKey, gold) {
    var pdf1 = C.gold.getGoldPdfs(poolKey, 1)[1];
    var hard = pdf1.length - 1;

    /* 首金的 pity 按稳态分布取值（生存概率归一） */
    var survival = new Float64Array(hard);
    var acc = 0, total = 0;
    for (var d = 0; d < hard; d++) {
      acc += pdf1[d];
      survival[d] = 1 - acc;
      total += survival[d];
    }

    var sum = 0;
    for (var d2 = 0; d2 < hard; d2++) {
      var w = survival[d2] / total;
      if (w === 0) continue;
      var tail = pdf1.subarray(d2 + 1);
      var tailSum = S.sum(tail);

      /* 首金落在 10 抽内的分布（超出窗口的抽数直接截断） */
      var cur = new Float64Array(11);
      for (var k = 1; k <= 10 && k - 1 < tail.length; k++) cur[k] = tail[k - 1] / tailSum;

      for (var gi = 1; gi < gold; gi++) {
        var conv = S.convolve(cur, pdf1);
        var cut = new Float64Array(11);
        for (var m = 0; m <= 10; m++) cut[m] = conv[m];
        cur = cut;
      }
      sum += S.sum(cur) * w;
    }
    return sum;
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
