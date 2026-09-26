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
