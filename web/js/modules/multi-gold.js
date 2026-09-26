/* 十连多金 —— 一次十连出多个金的概率与累计曲线 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core;
  var M = W.modules = W.modules || {};
  var UI = W.ui;
  var P = UI.panels;

  var POOLS = [
    { value: 'character', label: '角色池' },
    { value: 'weapon', label: '武器池' }
  ];

  function poolLabel(key) {
    return key === 'weapon' ? '武器池' : '角色池';
  }

  /* 概率跨数量级：大值用百分比，小值转指数记法 */
  function fmtPctLog(v) {
    var p = v * 100;
    if (p >= 0.1) return (p >= 1 ? p.toFixed(0) : p.toFixed(1)) + '%';
    return p.toExponential(0) + '%';
  }

  M['multi-gold'] = {
    id: 'multi-gold',
    title: '十连多金',
    group: '计算器',
    intro: '一次十连中出现多个五星的概率。出金概率随垫抽数增长，因此多金几乎只可能发生在十连的后段：' +
           '首个金的垫抽状态按长期稳态分布取值，其余金按完整出金分布卷积，' +
           '十连窗口外的部分不计入。参数取自社区总结的模型，结果仅供参考。',
    defaults: { pool: 'character', gold: 2 },

    controls: function () {
      return [
        {
          type: 'segmented', key: 'pool', label: '卡池', options: POOLS,
          help: '两池的出金曲线不同'
        },
        {
          type: 'segmented', key: 'gold', label: '金数',
          options: [{ value: 2, label: '2 金' }, { value: 3, label: '3 金' },
                    { value: 4, label: '4 金' }, { value: 5, label: '5 金' },
                    { value: 6, label: '6 金' }],
          help: '一次十连中出现的五星数量'
        }
      ];
    },

    views: {
      prob: {
        label: '单次概率',
        render: function (host, ctx) {
          var golds = [2, 3, 4, 5, 6];
          var series = POOLS.map(function (pl, i) {
            return {
              name: pl.label,
              values: golds.map(function (g) { return C.tenPullMultiGold(pl.value, g); }),
              color: i === 0 ? C.COLORS.primary : C.COLORS.gold
            };
          });

          var chart = P.chart(host);
          var mine = C.tenPullMultiGold(ctx.state.pool, ctx.state.gold);
          var all = series.reduce(function (acc, s) { return acc.concat(s.values); }, []);
          host.appendChild(P.statRow([
            [ctx.state.gold + ' 金的单次概率', P.pct(mine, 3)],
            ['平均需要十连', P.num(1 / mine, 1) + ' 次'],
            ['分布依据', '长期稳态'],
            ['十连上限', '10 抽窗口']
          ]));

          /* 概率跨数个数量级：取对数纵轴的点线，柱状在对数轴上没有零点可依 */
          ctx.charts.curve(chart, {
            xType: 'value',
            yType: 'log',
            xLabel: '一次十连的金数',
            yLabel: '概率',
            xMin: 1.5,
            xMax: 6.5,
            yMin: Math.min.apply(null, all) * 0.4,
            yMax: Math.max.apply(null, all) * 3,
            xTickFormatter: function (v) { return Number.isInteger(v) ? String(v) : ''; },
            yTickFormatter: fmtPctLog,
            series: series.map(function (s) {
              return {
                name: s.name,
                color: s.color,
                points: golds.map(function (g, k) { return [g, s.values[k]]; }),
                symbolSize: 8
              };
            }),
            legend: true
          });
          host.appendChild(P.note('数值为「一次十连中出现至少 k 个五星」的概率，纵轴取对数。' +
            '每多一个金，概率约下降两个数量级，因此 4 金以上极为罕见。'));
          ctx.setStatus('角色池 2 金 ' + P.pct(C.tenPullMultiGold('character', 2), 3) +
                        ' · 武器池 2 金 ' + P.pct(C.tenPullMultiGold('weapon', 2), 3));
        }
      },

      curve: {
        label: '累计概率',
        render: function (host, ctx) {
          var p = ctx.state;
          var prob = C.tenPullMultiGold(p.pool, p.gold);
          var nMax = Math.max(10, Math.ceil(2 / prob));
          var stride = Math.max(1, Math.floor(nMax / 600));
          var xs = [], ys = [];
          for (var x = 1; x <= nMax; x += stride) {
            xs.push(x);
            ys.push(1 - Math.pow(1 - prob, x));
          }
          if (xs[xs.length - 1] !== nMax) {
            xs.push(nMax);
            ys.push(1 - Math.pow(1 - prob, nMax));
          }

          function times(target) { return Math.log(1 - target) / Math.log(1 - prob); }
          function indexOf(v) {
            var best = 0;
            for (var i = 1; i < xs.length; i++) {
              if (Math.abs(xs[i] - v) < Math.abs(xs[best] - v)) best = i;
            }
            return best;
          }
          var avg = 1 / prob;
          /* 只画落在横轴范围内的参考线，超出部分由下方数据条给出 */
          var vLines = [
            { i: indexOf(avg), y1: ys[indexOf(avg)], color: '#2c3e50',
              text: '期望 ' + P.num(avg, 1) + ' 次' }
          ];
          [[0.5, '#2ca02c'], [0.9, '#9467bd'], [0.99, '#4b0082']].forEach(function (it) {
            var t = times(it[0]);
            if (t > nMax) return;
            vLines.push({
              i: indexOf(t), y1: it[0], color: it[1],
              text: Math.round(it[0] * 100) + '% ' + P.num(Math.ceil(t), 0)
            });
          });

          var chart = P.chart(host);
          host.appendChild(P.statRow([
            ['单次概率', P.pct(prob, 4)],
            ['期望十连', P.num(avg, 1) + ' 次'],
            ['50% 把握', P.num(Math.ceil(times(0.5)), 0) + ' 次'],
            ['99% 把握', P.num(Math.ceil(times(0.99)), 0) + ' 次']
          ]));

          ctx.charts.regions(chart, {
            x: xs,
            xLabel: '十连次数',
            yLabel: '至少出现一次的概率',
            yMin: 0,
            yMax: 1.05,
            legend: false,
            lines: [{
              name: p.gold + ' 金（' + poolLabel(p.pool) + '）', y: ys,
              color: C.COLORS.gold, width: 2.4, symbol: false
            }],
            vLines: vLines,
            yTickFormatter: function (v) { return (v * 100).toFixed(0) + '%'; },
            tooltipFormatter: function (v) { return (v * 100).toFixed(2) + '%'; }
          });
          host.appendChild(P.note('每次十连相互独立，累计概率为 \\(1-(1-p)^x\\)，' +
            '在期望次数处只到 ' + P.pct(1 - Math.pow(1 - prob, avg)) + '。'));
          UI.math.typeset(host);
          ctx.setStatus(poolLabel(p.pool) + ' ' + p.gold + ' 金 · 横轴至 ' + nMax + ' 次十连');
        }
      },

      table: {
        label: '概率总表',
        render: function (host, ctx) {
          var golds = [2, 3, 4, 5, 6];
          var rows = [], labels = [];
          POOLS.forEach(function (pl) {
            labels.push(pl.label);
            var probs = golds.map(function (g) { return C.tenPullMultiGold(pl.value, g); });
            rows.push(probs);
          });

          ctx.charts.table(host, {
            shade: false,
            rowHeader: '卡池',
            rowLabels: labels,
            colLabels: golds.map(function (g) { return g + ' 金'; }),
            values: rows,
            format: function (v) {
              if (v <= 0) return '—';
              return P.pct(v, v >= 0.01 ? 2 : 4) + '<span class="is-note"> / ' +
                     P.num(1 / v, 0) + ' 次</span>';
            },
            note: '单元格为单次十连的概率，斜杠后为该情形平均所需的十连次数（1/p）。' +
                  '低于 10⁻⁷ 的情形不予列出。'
          });
          ctx.setStatus('两张卡池、金数 2–6 的单次十连概率');
        }
      }
    }
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
