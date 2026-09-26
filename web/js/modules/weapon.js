/* 武器池 —— 定轨机制下的抽数分布 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core;
  var S = C.stats;
  var M = W.modules = W.modules || {};
  var UI = W.ui;
  var P = UI.panels;

  var ALPHAS = C.CDF_ALPHAS;
  var STATE_ROWS = [
    { ep: 0, prevStd: false, label: '命定值 0 · 上金为限定' },
    { ep: 0, prevStd: true, label: '命定值 0 · 上金为常驻' },
    { ep: 1, prevStd: false, label: '命定值 1 · 下一金必中' }
  ];

  function stateOf(p) {
    return C.makeWeaponState({
      epitomizedPoints: p.ep,
      pity: p.pity,
      prevStandard: p.prevStd
    });
  }

  function distOf(p) {
    return C.weaponUpDistribution(stateOf(p), p.countA);
  }

  M.weapon = {
    id: 'weapon',
    title: '武器池',
    group: '计算器',
    intro: '武器池的抽数分布：抽到指定数量的定轨武器所需的抽数。模型依据：前 62 抽出金概率 0.7%，' +
           '第 63–73 抽每抽递增 7 个百分点，第 74–79 抽每抽递增 3.5 个百分点，第 80 抽必出金；' +
           '出金时 37.5% 为定轨目标、37.5% 为另一把限定、25% 为常驻，未中目标时命定值 +1，' +
           '命定值满则下一金必为目标。参数取自社区总结的模型，结果仅供参考。',
    defaults: { countA: 1, ep: 0, pity: 0, prevStd: false },

    controls: function () {
      return [
        {
          type: 'range', key: 'countA', label: '目标武器数量', min: 1, max: 5, step: 1,
          unit: ' 把', help: '定轨不取消，抽到为止'
        },
        {
          type: 'segmented', key: 'ep', label: '命定值',
          options: [{ value: 0, label: '0' }, { value: 1, label: '1' }],
          help: '上一金未中定轨目标则为 1'
        },
        {
          type: 'range', key: 'pity', label: '已垫抽数', min: 0,
          max: C.LIMITS.maxPity.weapon, step: 1, unit: ' 抽',
          help: '距上一个金的抽数'
        },
        {
          type: 'switch', key: 'prevStd', label: '上一金为常驻',
          help: '下一金必为限定武器'
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
              text: 'α=' + a + '\n' + q + '抽', pos: 'insideEndTop'
            };
          });

          var chart = P.chart(host);
          host.appendChild(P.statRow([
            ['期望抽数', P.num(dist.expected, 1)],
            ['50% 分位', dist.quantile(0.5) + '抽'],
            ['90% 分位', dist.quantile(0.9) + '抽'],
            ['99% 分位', dist.quantile(0.99) + '抽']
          ]));

          ctx.charts.line(chart, {
            x: x,
            series: [{ name: '累积概率', y: y, color: 'var(--text)', width: 2.2 }],
            marks: marks,
            xLabel: '抽数',
            yLabel: '概率',
            yTickFormatter: function (v) {
              return v > 1.001 ? '' : (v * 100).toFixed(0) + '%';
            },
            tooltipFormatter: function (params) {
              var i = params[0].dataIndex;
              return '≤ <b>' + params[0].axisValue + '</b> 抽拿到目标：<b>' +
                     P.pctAdaptive(y[i]) + '</b>';
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
            ['最可能抽数', mode + '抽'],
            ['≤期望的概率', P.pctAdaptive(dist.probability(eIdx))]
          ]));

          ctx.charts.line(chart, {
            x: x,
            series: [{ name: '概率密度', y: y, color: C.COLORS.primary, fill: true, width: 1.8 }],
            marks: [{
              x: String(Math.min(eIdx, xMax)),
              y: Math.min(eIdx < dist.pdf.length ? dist.pdf[eIdx] : 0, dist.pdf[mode]) * 1.02,
              color: '#ff7f0e',
              text: '期望 ' + P.num(dist.expected, 1) + '抽',
              pos: 'insideEndTop'
            }],
            xLabel: '抽数',
            yLabel: '概率',
            yMax: dist.pdf[mode] * 1.2,
            yTickFormatter: function (v) { return (v * 100).toFixed(1) + '%'; },
            tooltipFormatter: function (params) {
              var i = params[0].dataIndex;
              return '恰好 <b>' + params[0].axisValue + '</b> 抽达成：<b>' +
                     P.pctAdaptive(y[i]) + '</b>';
            }
          });
          ctx.setStatus('双段软保底（63 抽起 +7%、74 抽起 +3.5%）使分布比角色池更陡');
        }
      },

      weights: {
        label: '金数分布',
        render: function (host, ctx) {
          var p = ctx.state;
          var weights = C.weaponTargetWeights(p.countA, p.ep, p.prevStd);
          var maxGold = weights.length - 1;
          var cats = [], vals = [];
          var expected = 0, total = 0;
          for (var g = 1; g <= maxGold; g++) {
            cats.push(g + ' 金');
            vals.push(weights[g]);
            expected += g * weights[g];
            total += weights[g];
          }

          var chart = P.chart(host);
          ctx.charts.bars(chart, {
            categories: cats,
            xLabel: '消耗金数',
            yLabel: '概率',
            series: [{ name: '达到目标所需金数', values: vals, color: C.COLORS.primary, maxWidth: 40 }],
            valueLabels: { show: true, formatter: function (pr) { return (pr.value * 100).toFixed(1) + '%'; } },
            yTickFormatter: function (v) { return (v * 100).toFixed(0) + '%'; },
            tooltipFormatter: function (v) { return (v * 100).toFixed(2) + '%'; }
          });
          host.appendChild(P.note('达到目标所需的抽数取决于消耗的金数：先按此分布定金数，' +
            '再按每金的抽数分布合成，即 CDF 视图的曲线。'));
          ctx.setStatus('平均消耗 ' + expected.toFixed(2) + ' 金／目标 · 概率和 ' + total.toFixed(3));
        }
      },

      table: {
        label: '分位点表',
        render: function (host, ctx) {
          var p = ctx.state;
          var rows = [], labels = [];
          for (var i = 0; i < STATE_ROWS.length; i++) {
            var row = STATE_ROWS[i];
            rows.push(C.weaponUpDistribution(
              C.makeWeaponState({ epitomizedPoints: row.ep, prevStandard: row.prevStd }),
              p.countA));
            labels.push(row.label);
          }

          var values = rows.map(function (d) {
            var line = ALPHAS.map(function (a) { return d.quantile(a); });
            line.push(d.expected);
            return line;
          });

          ctx.charts.table(host, {
            rowHeader: '定轨状态',
            rowLabels: labels,
            colLabels: ALPHAS.map(function (a) { return (a * 100) + '%'; }).concat(['期望']),
            values: values,
            meanColumn: true,
            note: '单元格为达到该概率所需的抽数（期望列单位为抽）。三行分别对应：未中目标且上金为限定、' +
                  '未中目标且上金为常驻（大保底）、命定值已满（下一金必中）。'
          });
          ctx.setStatus('目标 ' + p.countA + ' 把，已垫 ' + p.pity + ' 抽');
        }
      }
    }
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
