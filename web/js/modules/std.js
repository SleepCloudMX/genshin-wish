/* 常驻池 —— 纯出金分布 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core;
  var S = C.stats;
  var M = W.modules = W.modules || {};
  var UI = W.ui;
  var P = UI.panels;

  var ALPHAS = C.CDF_ALPHAS;

  function distOf(p) {
    return C.standardDistribution(p.pity, p.nGold);
  }

  M.std = {
    id: 'std',
    title: '常驻池',
    group: '计算器',
    intro: '常驻池的抽数分布：抽到指定数量的五星所需的抽数。常驻池没有 UP 机制，' +
           '任何五星均为常驻五星，出金概率与角色池一致（前 73 抽 0.6%，此后每抽递增 6 个百分点，' +
           '第 90 抽必出金）。参数取自社区总结的模型，结果仅供参考。',
    defaults: { nGold: 5, pity: 0 },

    controls: function () {
      return [
        {
          type: 'range', key: 'nGold', label: '目标五星数', min: 1, max: 30, step: 1,
          unit: ' 个', help: '常驻池所有五星等价'
        },
        {
          type: 'range', key: 'pity', label: '已垫抽数', min: 0, max: 89, step: 1,
          unit: ' 抽', help: '距上一个五星的抽数'
        }
      ];
    },

    views: {
      cdf: {
        label: '累积分布 (CDF)',
        render: function (host, ctx) {
          var dist = distOf(ctx.state);
          var xMax = Math.max(1, Math.ceil(S.supportEnd(dist.cdf) * 1.05));
          var x = [], y = [];
          for (var i = 0; i <= xMax; i++) {
            x.push(String(i));
            y.push(i < dist.cdf.length ? dist.cdf[i] : 1);
          }
          var marks = ALPHAS.map(function (a, k) {
            var q = dist.quantile(a);
            return {
              x: String(Math.min(q, xMax)), y: a, color: C.COLORS.alpha6[k],
              text: 'α=' + a + '\n' + q + ' 抽', pos: 'insideEndTop'
            };
          });

          var chart = P.chart(host);
          host.appendChild(P.statRow([
            ['期望抽数', P.num(dist.expected, 1)],
            ['50% 分位', dist.quantile(0.5) + ' 抽'],
            ['90% 分位', dist.quantile(0.9) + ' 抽'],
            ['99% 分位', dist.quantile(0.99) + ' 抽']
          ]));

          ctx.charts.line(chart, {
            x: x,
            series: [{ name: '累积概率', y: y, color: 'var(--text)', width: 2.2 }],
            marks: marks,
            xLabel: '抽数',
            yLabel: '概率',
            yTickFormatter: function (v) { return v > 1.001 ? '' : (v * 100).toFixed(0) + '%'; },
            tooltipFormatter: function (params) {
              var i = params[0].dataIndex;
              return '≤ <b>' + params[0].axisValue + '</b> 抽拿到 ' + ctx.state.nGold +
                     ' 个五星：<b>' + P.pct(y[i]) + '</b>';
            }
          });
          ctx.setStatus('最坏情况 ' + (dist.cdf.length - 1) + ' 抽');
        }
      },

      pdf: {
        label: '概率密度 (PDF)',
        render: function (host, ctx) {
          var dist = distOf(ctx.state);
          var xMax = Math.max(2, Math.ceil(S.supportEnd(dist.cdf) * 1.02));
          var x = [], y = [];
          for (var i = 0; i <= xMax; i++) {
            x.push(String(i));
            y.push(i < dist.pdf.length ? dist.pdf[i] : 0);
          }
          var eIdx = Math.round(dist.expected);
          var mode = 0;
          for (var j = 0; j < dist.pdf.length; j++) if (dist.pdf[j] > dist.pdf[mode]) mode = j;

          var chart = P.chart(host);
          host.appendChild(P.statRow([
            ['期望抽数', P.num(dist.expected, 1)],
            ['标准差', P.num(Math.sqrt(S.moments(dist.pdf).variance), 1)],
            ['最可能抽数', mode + ' 抽'],
            ['≤期望的概率', P.pct(dist.probability(eIdx))]
          ]));

          ctx.charts.line(chart, {
            x: x,
            series: [{ name: '概率密度', y: y, color: C.COLORS.primary, fill: true, width: 1.8 }],
            marks: [{
              x: String(Math.min(eIdx, xMax)),
              y: Math.min(eIdx < dist.pdf.length ? dist.pdf[eIdx] : 0, dist.pdf[mode]) * 1.02,
              color: '#ff7f0e',
              text: '期望 ' + P.num(dist.expected, 1) + ' 抽',
              pos: 'insideEndTop'
            }],
            xLabel: '抽数',
            yLabel: '概率',
            yMax: dist.pdf[mode] * 1.2,
            yTickFormatter: function (v) { return (v * 100).toFixed(1) + '%'; },
            tooltipFormatter: function (params) {
              var i = params[0].dataIndex;
              return '恰好 <b>' + params[0].axisValue + '</b> 抽达成：<b>' +
                     (y[i] * 100).toFixed(3) + '%</b>';
            }
          });
          ctx.setStatus('多个五星为同一出金过程的高次卷积');
        }
      },

      table: {
        label: '分位点表',
        render: function (host, ctx) {
          var N = ctx.state.nGold;
          var rows = [], labels = [];
          for (var n = 1; n <= N; n++) {
            rows.push(C.standardDistribution(0, n));
            labels.push(n + ' 个五星');
          }

          var values = rows.map(function (d) {
            var line = ALPHAS.map(function (a) { return d.quantile(a); });
            line.push(d.expected);
            return line;
          });

          ctx.charts.table(host, {
            rowHeader: '目标',
            rowLabels: labels,
            colLabels: ALPHAS.map(function (a) { return (a * 100) + '%'; }).concat(['期望']),
            values: values,
            meanColumn: true,
            note: '单元格为达到该概率所需的抽数（期望列单位为抽），均从零垫抽算起。'
          });
          ctx.setStatus('共 ' + N + ' 行，覆盖 1–' + N + ' 个五星');
        }
      }
    }
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
