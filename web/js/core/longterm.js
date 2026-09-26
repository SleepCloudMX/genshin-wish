/* 长期分布求解器与玩家序列解析 —— 对应 long_term.py + _player_pulls.py */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core = W.core || {};
  var S = C.stats;

  function padTo(arr, len) {
    if (arr.length >= len) return arr;
    var out = new Float64Array(len);
    out.set(arr);
    return out;
  }

  /* 迭代卷积：pdf_state[s] 表示"已完成 n 个 UP 且停在状态 s"的抽数分布
   * pUp[s] 为状态 s 下中 UP 的概率，最后一个状态必中（pUp 末项为 1）。
   * 返回 [n] = 恰好 n 个 UP 的抽数 PDF（数组下标 0 为占位）。 */
  C.solveExactPdfs = function (maxN, pUp, pGold, pGold2, startState) {
    var nStates = pUp.length;
    var state = [], i;
    for (i = 0; i < nStates; i++) state.push(null);
    state[startState || 0] = new Float64Array([1.0]);

    var out = new Array(maxN + 1);
    out[0] = new Float64Array([1.0]);

    for (var n = 1; n <= maxN; n++) {
      var next = [], s;
      for (s = 0; s < nStates; s++) next.push(null);

      for (s = 0; s < nStates; s++) {
        var ps = state[s];
        if (!ps) continue;

        var wc = S.convolve(ps, pGold);
        next[0] = padTo(next[0] || new Float64Array(0), wc.length);
        for (i = 0; i < wc.length; i++) next[0][i] += wc[i] * pUp[s];

        if (s < nStates - 1) {
          var lc = S.convolve(ps, pGold2);
          next[s + 1] = padTo(next[s + 1] || new Float64Array(0), lc.length);
          for (i = 0; i < lc.length; i++) next[s + 1][i] += lc[i] * (1 - pUp[s]);
        }
      }
      state = next;

      var mlen = 0;
      for (s = 0; s < nStates; s++) {
        if (state[s] && state[s].length > mlen) mlen = state[s].length;
      }
      var total = new Float64Array(mlen);
      for (s = 0; s < nStates; s++) {
        var p = state[s];
        if (!p) continue;
        for (i = 0; i < p.length; i++) total[i] += p[i];
      }
      out[n] = total;
    }
    return out;
  };

  /* 长期求解器：前 n_pre_50 个 UP 走 5.0 前机制，其余走捕获明光
   * method: 'exact' 迭代卷积 / 'clt' 正态近似（仅用于大规模快速预览） */
  C.makeLongSolver = function (state, method) {
    var nPre = state.nPre50 || 0;
    var nPost = state.nPost50 || 0;
    var total = nPre + nPost;
    if (total <= 0) throw new RangeError('至少需要 1 个 UP');
    method = method || 'exact';

    /* 迭代卷积只用单金 PDF，不随 UP 数增长 */
    var pGold = C.gold.getGoldPdfs('character', 1)[1];
    var pGold2 = S.convolve(pGold, pGold);

    var muPre = C.pre50Moments(pGold, pGold2);
    var muPost = C.post50Moments(pGold);
    var muSingle;
    if (nPre > 0 && nPost > 0) muSingle = (nPre * muPre.mean + nPost * muPost.mean) / total;
    else if (nPre > 0) muSingle = muPre.mean;
    else muSingle = muPost.mean;

    if (method === 'clt') {
      var bounds = function (n, alpha) {
        var mu, va;
        if (nPre > 0 && nPre < n) {
          mu = nPre * muPre.mean + (n - nPre) * muPost.mean;
          va = nPre * muPre.variance + (n - nPre) * muPost.variance;
        } else if (n <= nPre) {
          mu = n * muPre.mean;
          va = n * muPre.variance;
        } else {
          mu = n * muPost.mean;
          va = n * muPost.variance;
        }
        var sd = Math.sqrt(Math.max(va, 0));
        return [Math.max(0, mu + sd * S.normPpf(alpha)), mu - sd * S.normPpf(alpha)];
      };
      return { method: 'clt', muSingle: muSingle, total: total, bounds: bounds, cdfAt: null };
    }

    var prePdfs = nPre > 0 ? C.pre50Pdfs(nPre, pGold, pGold2) : null;
    var postPdfs = nPost > 0
      ? C.solveExactPdfs(nPost, C.CAPTURE_RADIANCE_WIN_RATE, pGold, pGold2, 0) : null;

    var cdfs = new Array(total + 1);
    for (var n = 1; n <= total; n++) {
      var pdf;
      if (n <= nPre) pdf = prePdfs[n];
      else if (nPre === 0) pdf = postPdfs[n];
      else pdf = S.convolve(prePdfs[nPre], postPdfs[n - nPre]);
      cdfs[n] = S.cumsum(pdf);
    }

    return {
      method: 'exact',
      muSingle: muSingle,
      total: total,
      bounds: function (n, alpha) {
        var cdf = cdfs[n];
        return [S.searchsortedLeft(cdf, alpha), S.searchsortedLeft(cdf, 1 - alpha)];
      }
    };
  };

  /* "68,79+11,77+80" → 每个 UP 的抽数、累计抽数、是否直接中（未歪） */
  C.parsePullsSeq = function (text) {
    var raw = String(text || '').split(',').map(function (s) { return s.trim(); })
      .filter(function (s) { return s.length > 0; });
    var perUp = [], isDirectWin = [];
    for (var i = 0; i < raw.length; i++) {
      var item = raw[i];
      if (item.indexOf('+') >= 0) {
        var parts = item.split('+');
        perUp.push(Number(parts[0]) + Number(parts[1]));
        isDirectWin.push(false);
      } else {
        perUp.push(Number(item));
        isDirectWin.push(true);
      }
    }
    for (var j = 0; j < perUp.length; j++) {
      if (!isFinite(perUp[j]) || perUp[j] <= 0) throw new RangeError('序列格式应为 数字 或 数字+数字');
    }
    var cumulative = [], sum = 0;
    for (var k = 0; k < perUp.length; k++) { sum += perUp[k]; cumulative.push(sum); }
    return { perUp: perUp, cumulative: cumulative, isDirectWin: isDirectWin };
  };

})(typeof globalThis !== 'undefined' ? globalThis : this);
