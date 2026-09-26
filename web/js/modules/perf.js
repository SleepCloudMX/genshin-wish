/* 性能与验证 —— 复刻 output/analysis 里的实验图（数据由 scripts/build_web_data.py 导出） */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var M = W.modules = W.modules || {};
  var doc = global.document;

  /* 分位点配色与线型：与实验脚本一致（内→外对称） */
  var Q_COLORS = ['#d62728', '#ff7f0e', '#2ca02c', '#1f77b4', '#2ca02c', '#ff7f0e', '#d62728'];
  var Q_DASH = [true, true, false, false, false, true, true];
  var METHOD_ORDER = ['dp-pulls', 'dp-path', 'dp-state', 'dp-golds', 'CLT'];

  function pct(q) { return Math.round(q * 100) + '%'; }

  function para(host, html, cls) {
    var p = doc.createElement('p');
    p.className = cls || 'chartnote';
    p.innerHTML = html;
    host.appendChild(p);
    return p;
  }

  function heading(host, text) {
    var h = doc.createElement('h2');
    h.className = 'perf__h';
    h.textContent = text;
    host.appendChild(h);
  }

  function chartBox(host, caption, cls) {
    var chart = doc.createElement('div');
    chart.className = 'chart ' + (cls || 'chart--perf');
    host.appendChild(chart);
    if (caption) para(host, caption);
    return chart;
  }

  function fitPoints(fit, xMax) {
    var pts = [];
    if (!fit) return pts;
    var steps = 48;
    for (var i = 0; i <= steps; i++) {
      var x = fit.from * Math.pow(xMax / fit.from, i / steps);
      var y = fit.kind === 'power'
        ? Math.exp(fit.b + fit.k * Math.log(x))
        : Math.exp(fit.a * x + fit.b) + fit.c;
      pts.push([x, y]);
    }
    return pts;
  }

  /* 把 {n, series} 转成 curve 图型要的系列数组 */
  function toSeries(bundle, methods, opts, colors) {
    var xMax = Math.max.apply(null, bundle.n);
    var out = methods.map(function (name) {
      var s = bundle.series[name];
      if (!s) return null;
      var pts = [], band = [];
      for (var i = 0; i < bundle.n.length; i++) {
        if (s.time[i] === null || s.time[i] === undefined) continue;
        pts.push([bundle.n[i], s.time[i]]);
        band.push([bundle.n[i], s.lo[i], s.hi[i]]);
      }
      /* 拟合线只画到该方法自己测到的最大 n，外推会失真（指数拟合尤其明显） */
      var fitMax = pts.length ? pts[pts.length - 1][0] : xMax;
      return {
        name: name,
        color: colors[name],
        points: pts,
        band: opts.band ? band : null,
        fit: (opts.fit && s.fit) ? fitPoints(s.fit, fitMax) : null,
        label: opts.fit ? fitLabel(s.fit, pts) : null
      };
    }).filter(function (s) { return s && s.points.length; });
    return out;
  }

  /* 拟合曲线的斜率标注：贴在拟合线末端 */
  function fitLabel(fit, pts) {
    if (!fit) return null;
    var last = pts[pts.length - 1];
    return {
      x: last[0], y: last[1],
      text: fit.kind === 'power' ? 'k≈' + fit.k.toFixed(2) : 'O(2ⁿ)',
      pos: 'top'
    };
  }

  function slice(bundle, keepIndex) {
    var idx = [];
    bundle.n.forEach(function (n, i) { if (keepIndex(n)) idx.push(i); });
    var out = { n: idx.map(function (i) { return bundle.n[i]; }), series: {} };
    Object.keys(bundle.series).forEach(function (m) {
      var s = bundle.series[m];
      out.series[m] = {
        time: idx.map(function (i) { return s.time[i]; }),
        lo: idx.map(function (i) { return s.lo[i]; }),
        hi: idx.map(function (i) { return s.hi[i]; }),
        fit: null
      };
    });
    return out;
  }

  M.perf = {
    id: 'perf',
    title: '性能与验证',
    group: '关于',
    math: true,
    intro: '五种精确算法与 CLT 近似的实测耗时与近似误差，以及两种独立算法的交叉验证结果。',
    defaultView: 'doc',
    defaults: {},
    controls: function () { return []; },
    views: {
      doc: {
        label: '实验',
        render: function (host, ctx) {
          var A = global.__WISH_ANALYSIS__;
          var box = doc.createElement('div');
          box.className = 'perf';
          host.appendChild(box);

          if (!A) {
            para(box, '实验数据未加载（缺少 web/data/analysis.js）。');
            return;
          }

          para(box, '<b>实验设置</b>：各方法在同一台机器上重复计时，去除两端各 20% 的样本后取均值，' +
            '阴影为剩余样本的最小值与最大值区间。dp-pulls 仅计时至 n ≤ 7，dp-path 仅至 n ≤ 20，' +
            '其余方法覆盖 n = 1–500。虚线为按数据拟合的复杂度曲线：dp-path 采用指数拟合，' +
            '其余采用幂律拟合，标注的 k 为拟合指数。数据由 Python 实现实测，生成于 ' +
            A.meta.generated + '。');

          var pending = [];

          /* --- 任务 1 速度 --- */
          heading(box, '速度对比（任务 1：n 个 UP 所需抽数）');
          var full = chartBox(box, '以 n = 500 为例，dp-golds 耗时 ' +
            pickTime(A, 'dp-golds') + '，dp-state 耗时 ' + pickTime(A, 'dp-state') +
            '，CLT 可忽略。dp-golds 的拟合指数接近 2，与 \\(O(n^2)\\) 相符；' +
            'dp-path 的指数底数接近 2，与 \\(O(2^n)\\) 相符。', 'chart--tall');
          pending.push([full, {
            xType: 'log', yType: 'log',
            xLabel: 'UP 数 n', yLabel: '耗时 (ms)',
            xMin: 1, xMax: Math.max.apply(null, A.n),
            series: toSeries(A.task1, METHOD_ORDER, { fit: true, band: true }, A.colors)
          }]);

          /* --- 小 n 细节 --- */
          heading(box, '小规模区间（n ≤ 20）');
          var detail = chartBox(box, 'n ≤ 7 时最慢的 dp-pulls 亦仅需数毫秒，但其增长率最高；' +
            'n 超过 20 后仅 dp-state、dp-golds 与 CLT 可用。');
          pending.push([detail, {
            xType: 'value', yType: 'log',
            xLabel: 'UP 数 n', yLabel: '耗时 (ms)',
            xMin: 1, xMax: 20,
            series: toSeries(slice(A.task1, function (n) { return n <= 20; }), METHOD_ORDER,
                             { fit: false, band: true }, A.colors)
          }]);

          /* --- CLT 精度 --- */
          heading(box, 'CLT 近似的精度');
          para(box, '以 dp-state 的精确解为基准，比较 CLT 混合矩近似在各分位点的偏差。' +
            '误差随 n 增大迅速收敛，n = 500 时 50% 分位约为 0.007%。');
          pending.push([chartBox(box, null), cltOption(A, 'abs', '绝对误差（按分位点）', '误差（抽）', 1)]);
          pending.push([chartBox(box, null), cltOption(A, 'rel', '相对误差（按分位点）', '相对误差 (%)', 1)]);
          pending.push([chartBox(box, null), cltOption(A, 'perUp', '摊到每个 UP 的误差', '误差（抽/UP）', 1)]);

          /* --- 任务 2 / 3 --- */
          heading(box, '任务 2：条件抽数分布的计算耗时');
          var t2 = chartBox(box, '任务 2 输出「给定常驻数量时的抽数分布」。dp-path 在小 n 时最快' +
            '（无需建表），n ≥ 6 后由 dp-golds 反超。');
          pending.push([t2, {
            xType: 'log', yType: 'log',
            xLabel: 'UP 数 n', yLabel: '耗时 (ms)',
            xMin: 1, xMax: Math.max.apply(null, A.task2.n),
            series: toSeries(A.task2, ['dp-path', 'dp-golds'], { fit: false, band: true }, A.colors)
          }]);

          heading(box, '任务 3：常驻角色数分布的计算耗时');
          var t3 = chartBox(box, '任务 3 输出「歪出多少个常驻」的分布，仅需整数 DP，' +
            '不涉及抽数卷积，两种方法均较快；n ≥ 7 后 dp-golds 领先。');
          pending.push([t3, {
            xType: 'log', yType: 'log',
            xLabel: 'UP 数 n', yLabel: '耗时 (ms)',
            xMin: 1, xMax: Math.max.apply(null, A.task3.n),
            series: toSeries(A.task3, ['dp-path', 'dp-golds'], { fit: false, band: true }, A.colors)
          }]);

          /* --- n=20 分布（两种方法互相印证） --- */
          heading(box, '两种方法的互相印证');
          var dist = chartBox(box, 'n = 20 时歪出常驻角色数量的分布。两种方法的柱高完全一致：' +
            'dp-path 枚举全部 \\(2^{20}\\) 条序列，dp-golds 仅统计金数，二者路径不同而结果相同。');
          var d = A.task3.nstd20;
          pending.push([dist, {
            bars: true,
            title: '任务 3：n = 20 时的常驻角色数分布',
            categories: d.nstd.map(String),
            xLabel: '常驻角色数 n_std', yLabel: '概率',
            yTickFormatter: function (v) { return (v * 100).toFixed(0) + '%'; },
            tooltipFormatter: function (v) { return (v * 100).toFixed(2) + '%'; },
            series: [
              { name: 'dp-path', values: d['dp-path'], color: '#1f77b4' },
              { name: 'dp-golds', values: d['dp-golds'], color: '#ff7f0e' }
            ]
          }]);

          /* 容器已在文档中，可以初始化 */
          pending.forEach(function (item) {
            var el = item[0], opt = item[1];
            if (opt.bars) ctx.charts.bars(el, opt);
            else ctx.charts.curve(el, opt);
          });
        }
      }
    }
  };

  function pickTime(A, method) {
    var s = A.task1.series[method];
    var i = A.task1.n.indexOf(500);
    var v = i >= 0 ? s.time[i] : null;
    return v === null || v === undefined ? '—' : v.toFixed(0) + ' ms';
  }

  function cltOption(A, field, title, yLabel) {
    var clt = A.task1.clt;
    var keys = Object.keys(clt.abs);
    var series = [];
    keys.forEach(function (key, i) {
      var pts = [];
      for (var j = 0; j < clt.n.length; j++) {
        var v = clt[field][key][j];
        if (v === null || v === undefined) continue;
        if (clt.n[j] < 10) continue;          /* 与实验图的 late 区间一致 */
        pts.push([clt.n[j], v]);
      }
      if (!pts.length) return;
      series.push({
        name: pct(Number(key)), color: Q_COLORS[i], points: pts,
        dash: Q_DASH[i], width: 1.8, symbol: false
      });
    });
    return {
      title: title, xType: 'value', yType: 'value',
      xLabel: 'UP 数 n', yLabel: yLabel,
      xMin: 10, xMax: 500, series: series
    };
  }
})(typeof globalThis !== 'undefined' ? globalThis : this);
