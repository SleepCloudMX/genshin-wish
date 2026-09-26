/* 常驻角色数 —— 抽 UP 的过程中歪出的常驻五星数量 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core;
  var S = C.stats;
  var M = W.modules = W.modules || {};
  var UI = W.ui;
  var P = UI.panels;

  var MISS = C.MISS_LABELS;

  function stateOf(p) {
    return C.makeCharacterState({ pity: 0, consecutiveLoss: p.loss, guaranteed: false });
  }

  function mapToArrays(map) {
    var maxK = 0;
    Object.keys(map).forEach(function (k) { if (Number(k) > maxK) maxK = Number(k); });
    var vals = [], labels = [];
    for (var k = 0; k <= maxK; k++) {
      labels.push(String(k));
      vals.push(map[k] || 0);
    }
    return { labels: labels, values: vals, maxK: maxK };
  }

  M.nstd = {
    id: 'nstd',
    title: '常驻角色数',
    group: '计算器',
    intro: '抽到 n 个限定角色的过程中，歪 50/50 会带来常驻五星。本页给出常驻五星数量的分布，' +
           '以及「已知歪出 m 个常驻」时抽数的条件分布。参数取自社区总结的模型，结果仅供参考。',
    defaults: { nUp: 7, loss: 0, nStd: 2 },

    controls: function () {
      return [
        {
          type: 'range', key: 'nUp', label: '目标 UP 数', min: 1,
          max: C.LIMITS.charExactNUp, step: 1, unit: ' 个', help: '含角色本体'
        },
        {
          type: 'segmented', key: 'loss', label: '已连歪次数',
          options: [{ value: 0, label: '0' }, { value: 1, label: '1' },
                    { value: 2, label: '2' }, { value: 3, label: '3' }]
        },
        {
          type: 'range', key: 'nStd', label: '常驻数（条件视图）', min: 0, max: 15,
          step: 1, unit: ' 个', help: '仅影响「条件抽数」视图'
        }
      ];
    },

    views: {
      bar: {
        label: '常驻数分布',
        render: function (host, ctx) {
          var p = ctx.state;
          var dist = C.nStdDistribution(stateOf(p), p.nUp);
          var arr = mapToArrays(dist);
          var expected = 0;
          arr.values.forEach(function (v, k) { expected += k * v; });

          var chart = P.chart(host);
          host.appendChild(P.statRow([
            ['期望常驻数', P.num(expected, 2)],
            ['一个都没歪', P.pct(dist[0] || 0)],
            ['至少歪 1 个', P.pct(1 - (dist[0] || 0))],
            ['至少歪 2 个', P.pct(1 - (dist[0] || 0) - (dist[1] || 0))]
          ]));

          ctx.charts.bars(chart, {
            categories: arr.labels,
            xLabel: '常驻五星数量',
            yLabel: '概率',
            series: [{ name: '恰好歪出 m 个常驻', values: arr.values,
                       color: C.COLORS.primary, maxWidth: 36 }],
            valueLabels: { show: arr.maxK <= 14,
                           formatter: function (pr) { return (pr.value * 100).toFixed(1) + '%'; } },
            yTickFormatter: function (v) { return (v * 100).toFixed(0) + '%'; },
            tooltipFormatter: function (v) { return (v * 100).toFixed(2) + '%'; }
          });
          host.appendChild(P.note('每次歪都会带来一个常驻五星，因此常驻数与「歪的次数」同分布；' +
            '捕获明光生效时该次不再计入歪。'));
          ctx.setStatus(p.nUp + ' 个 UP 中共 ' + arr.maxK + ' 种常驻数量');
        }
      },

      cond: {
        label: '条件抽数',
        render: function (host, ctx) {
          var p = ctx.state;
          var dists = C.nStdConditionalPulls(stateOf(p), p.nUp);
          var marginal = C.nStdDistribution(stateOf(p), p.nUp);
          var keys = Object.keys(dists).map(Number).sort(function (a, b) { return a - b; });

          var shown = keys.filter(function (k) { return (marginal[k] || 0) >= 0.01; });
          if (shown.length > 8) shown = shown.slice(0, 8);
          if (shown.length === 0) shown = keys.slice(0, 1);

          /* 每条曲线在自己的 99.99% 分位处截断，超出部分留空 */
          var hiMax = 0;
          shown.forEach(function (k) {
            var d = dists[k];
            hiMax = Math.max(hiMax, Math.min(S.supportEnd(d.cdf, 1e-4) + 5, d.pdf.length - 1));
          });
          var stride = Math.max(1, Math.round(hiMax / 600));
          var xs = [];
          for (var i = 0; i <= hiMax; i += stride) xs.push(i);

          var lines = shown.map(function (k, idx) {
            var d = dists[k];
            var hi = Math.min(S.supportEnd(d.cdf, 1e-4) + 5, d.pdf.length - 1);
            return {
              name: '歪 ' + k + ' 个（' + P.pct(marginal[k] || 0) + '）',
              y: xs.map(function (t) { return t <= hi ? d.pdf[t] : null; }),
              color: S.ramp(C.COLORS.coolwarm, shown.length > 1 ? idx / (shown.length - 1) : 0.5),
              width: 1.8
            };
          });

          var chart = P.chart(host);
          ctx.charts.regions(chart, {
            x: xs,
            xLabel: '抽数',
            yLabel: '概率密度',
            legend: true,
            lines: lines,
            yTickFormatter: function (v) { return (v * 100).toFixed(1) + '%'; },
            tooltipFormatter: function (v) {
              return v === null || v === undefined ? '—' : (v * 100).toFixed(3) + '%';
            }
          });

          var sel = dists[p.nStd];
          if (sel) {
            host.appendChild(P.statRow([
              ['歪 ' + p.nStd + ' 个的期望', P.num(sel.expected, 1) + ' 抽'],
              ['50% 分位', sel.quantile(0.5) + ' 抽'],
              ['90% 分位', sel.quantile(0.9) + ' 抽'],
              ['该情形占比', P.pct(marginal[p.nStd] || 0)]
            ]));
          }
          host.appendChild(P.note('曲线为 P(抽数 | 常驻数量)，即已经知道歪出 m 个常驻时的抽数分布；' +
            '括号内为该情形的边际概率。仅显示占比 ≥ 1% 的情形。'));
          ctx.setStatus('已列出 ' + shown.length + ' 条条件分布 · 条件视图参数 n_std = ' + p.nStd);
        }
      },

      table: {
        label: '分布表',
        render: function (host, ctx) {
          var p = ctx.state;
          var maps = [], maxK = 0, k, m;
          for (k = 0; k < 4; k++) {
            maps.push(C.nStdDistribution(
              C.makeCharacterState({ pity: 0, consecutiveLoss: k }), p.nUp));
          }
          maps.forEach(function (map) {
            Object.keys(map).forEach(function (kk) { if (Number(kk) > maxK) maxK = Number(kk); });
          });

          var cols = [];
          for (m = 0; m <= maxK; m++) cols.push(String(m));
          var values = maps.map(function (map) {
            var line = [];
            for (m = 0; m <= maxK; m++) line.push(map[m] || 0);
            return line;
          });

          ctx.charts.table(host, {
            rowHeader: '已连歪次数',
            rowLabels: [MISS[0][0], MISS[1][0], MISS[2][0], MISS[3][0]],
            colLabels: cols,
            values: values,
            format: function (v) { return (v * 100).toFixed(1) + '%'; },
            note: '行是抽卡开始时的连歪次数，列是最终歪出的常驻五星数量，单元格为概率。' +
                  '连歪次数越高，捕获明光生效越早，常驻数量整体左移。'
          });
          ctx.setStatus(p.nUp + ' 个 UP · 常驻数 0–' + maxK);
        }
      }
    }
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
