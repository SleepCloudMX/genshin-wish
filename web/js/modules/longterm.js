/* 长期欧非 —— 连续抽多个 UP 时平均成本随数量的演变 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core;
  var M = W.modules = W.modules || {};
  var UI = W.ui;
  var P = UI.panels;

  var BANDS = [0.4, 0.3, 0.2, 0.1, 0.01];

  function buildSolver(p) {
    var N = p.N;
    var nPre = Math.min(p.nPre, N);
    return {
      N: N,
      nPre: nPre,
      nPost: N - nPre,
      solver: C.makeLongSolver({ nPre50: nPre, nPost50: N - nPre }, 'exact')
    };
  }

  M.longterm = {
    id: 'longterm',
    title: '长期欧非',
    group: '计算器',
    intro: '连续抽多个 UP 时，总抽数除以 UP 数的平均值随数量收敛：单个 UP 的运气会被平均掉，' +
           '最终贴近每 UP 的理论期望。5.0 版本前后机制不同——5.0 前是纯 50/50 加大保底，' +
           '5.0 后加入捕获明光，因此本页可分别指定两段的 UP 数量。' +
           '参数取自社区总结的模型，结果仅供参考。',
    defaults: { N: 20, nPre: 0 },

    controls: function () {
      return [
        {
          type: 'range', key: 'N', label: 'UP 总数', min: 5, max: 100, step: 5,
          unit: ' 个', help: '横轴的范围'
        },
        {
          type: 'range', key: 'nPre', label: '5.0 前的 UP 数', min: 0, max: 100,
          step: 5, unit: ' 个', help: '按纯 50/50 加大保底计算'
        }
      ];
    },

    views: {
      fan: {
        label: '长期演变',
        render: function (host, ctx) {
          var b = buildSolver(ctx.state);
          var N = b.N, nPre = b.nPre, solver = b.solver;
          var xs = [], perUp = {};
          BANDS.forEach(function (a) { perUp[a] = []; perUp[1 - a] = []; });

          for (var n = 1; n <= N; n++) {
            xs.push(n);
            BANDS.forEach(function (a) {
              /* bounds(n, a) 一次给出 [q_a, q_{1-a}] 两端 */
              var bb = solver.bounds(n, a);
              perUp[a].push(bb[0] / n);
              perUp[1 - a].push(bb[1] / n);
            });
          }

          var regions = BANDS.slice().reverse().map(function (a, k) {
            var idx = BANDS.length - 1 - k;
            return {
              name: Math.round(a * 100) + '%–' + Math.round((1 - a) * 100) + '%',
              lo: perUp[a],
              hi: perUp[1 - a],
              color: C.COLORS.interval5[idx],
              opacity: idx === 0 ? 0.4 : 0.25
            };
          });

          var lo = Infinity, hi = 0;
          BANDS.forEach(function (a) {
            perUp[a].forEach(function (v) { if (v < lo) lo = v; });
            perUp[1 - a].forEach(function (v) { if (v > hi) hi = v; });
          });

          var labelEvery = Math.max(1, Math.ceil(N / 12));
          var labels = [];
          for (var k = 0; k < N; k++) {
            if (k % labelEvery && k !== N - 1) continue;
            labels.push({ i: k, y: perUp[0.1][k], text: perUp[0.1][k].toFixed(1),
                          color: C.COLORS.interval5[3], pos: 'bottom' });
          }

          var chart = P.chart(host);
          var vLines = [];
          if (nPre > 0 && nPre < N) {
            vLines.push({ i: nPre, y0: 0, y1: hi, color: '#e74c3c', text: '5.0 分界' });
          }

          ctx.charts.regions(chart, {
            x: xs,
            xLabel: '获取 UP 角色总数',
            yLabel: '平均每个 UP 消耗抽数',
            yMin: Math.max(0, Math.floor(lo - 5)),
            yMax: Math.ceil(hi + 5),
            regions: regions,
            labels: labels,
            hLines: [{
              y: solver.muSingle, color: 'var(--text)',
              text: '理论均值 ' + solver.muSingle.toFixed(2), pos: 'insideStartTop'
            }],
            vLines: vLines,
            yTickFormatter: function (v) { return v.toFixed(0); },
            tooltipFormatter: function (v) { return v.toFixed(1); },
            tooltipHtml: function (i) {
              var n = xs[i];
              var bb = solver.bounds(n, 0.5);
              var median = (bb[0] + bb[1]) / 2 / n;
              var rows = [
                ['理论均值', solver.muSingle.toFixed(2)],
                ['中位数', median.toFixed(1)],
                ['合计（中位）', Math.round(median * n) + '抽']
              ];
              BANDS.forEach(function (a) {
                rows.push([Math.round(a * 100) + '%–' + Math.round((1 - a) * 100) + '%',
                           perUp[a][i].toFixed(1) + ' – ' + perUp[1 - a][i].toFixed(1)]);
              });
              return P.tip('前 ' + n + ' 个 UP · 抽/UP', rows);
            }
          });
          host.appendChild(P.note('纵轴为前 n 个 UP 的总抽数除以 n。区间自内向外为 ' +
            '40%–60%、30%–70%、20%–80%、10%–90%、1%–99%；标注为 90% 分位。' +
            'UP 数越大，个体差异被平均得越彻底，区间收窄至理论均值附近。'));
          ctx.setStatus('精确卷积 · ' + N + ' 个 UP（其中 5.0 前 ' + nPre +
            ' 个）· 理论均值 ' + solver.muSingle.toFixed(2) + ' 抽/UP');
        }
      },

      table: {
        label: '分位点表',
        render: function (host, ctx) {
          var b = buildSolver(ctx.state);
          var N = b.N, solver = b.solver;
          var step = Math.max(1, Math.round(N / 10));
          var rows = [], labels = [];

          function rowFor(n) {
            return [0.1, 0.3, 0.5].map(function (a) {
              var bb = solver.bounds(n, a);
              return (bb[0] + bb[1]) / 2 / n;
            }).concat([solver.muSingle]);
          }

          for (var n = step; n <= N; n += step) {
            rows.push(rowFor(n));
            labels.push('前 ' + n + ' 个');
          }
          if (labels[labels.length - 1] !== '前 ' + N + ' 个') {
            rows.push(rowFor(N));
            labels.push('前 ' + N + ' 个');
          }

          ctx.charts.table(host, {
            rowHeader: 'UP 数',
            rowLabels: labels,
            colLabels: ['10%–90%', '30%–70%', '中位数', '理论均值'],
            values: rows,
            format: function (v) { return v.toFixed(2); },
            note: '单元格是各对称分位区间中点处的平均每 UP 抽数：10%–90% 列为 ' +
                  '\\([q_{10\\%}, q_{90\\%}]\\) 的中点，30%–70% 列同理，中位数列为 50% 分位。' +
                  '所在行越靠下，个体差异被平均得越彻底，各列一起收敛到理论均值。' +
                  (b.nPost > 0 ? '本组合的理论均值为 ' + solver.muSingle.toFixed(2) +
                                 ' 抽（5.0 前为 93.75 抽）。' : '')
          });
          UI.math.typeset(host);
          ctx.setStatus('精确卷积 · 共 ' + labels.length + ' 行 · 理论均值 ' +
            solver.muSingle.toFixed(2) + ' 抽/UP');
        }
      }
    }
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
