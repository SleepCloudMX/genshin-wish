/* 角色池 —— 对应 output/character/ 下的 CDF、扇形、柱状、堆叠、阶梯与分位点表 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core;
  var S = C.stats;
  var M = W.modules = W.modules || {};
  var UI = W.ui;
  var P = UI.panels;
  var doc = global.document;

  var ALPHAS = C.CDF_ALPHAS;
  var FAN_ALPHAS = [0.4, 0.3, 0.2, 0.1, 0.01];
  var FAN_COLORS = C.COLORS.interval5;          /* 内 → 外 */
  var COLUMN_ALPHAS = [
    { a: 0.1, color: '#2ca02c' }, { a: 0.3, color: '#1f77b4' },
    { a: 0.5, color: '#ff7f0e' }, { a: 0.7, color: '#9467bd' },
    { a: 0.9, color: '#d62728' }, { a: 0.99, color: '#4b0082' }
  ];

  function isStable(p) { return p.loss === C.STABLE_LOSS; }

  function stateOf(p) {
    return C.makeCharacterState({
      guaranteed: p.guaranteed,
      pity: p.pity,
      consecutiveLoss: isStable(p) ? 0 : p.loss,
      stable: isStable(p)
    });
  }

  function distOf(p) {
    return C.upDistribution(stateOf(p), p.nUp);
  }

  /* 稳态时在状态条标注，免得只有控件上的选中态提示 */
  function setStatus(ctx, p, text) {
    ctx.setStatus(isStable(p) ? text + ' · 连歪次数取稳态' : text);
  }

  function label(n) { return n === 7 ? '满命' : (n - 1) + ' 命'; }

  /* P(≥ n UP | pulls) 网格：n = 0..upto，长度统一为 maxPulls（尾部补 1） */
  function cdfGrid(p, upto, maxPulls) {
    var out = [];
    var top = new Float64Array(maxPulls);
    top.fill(1);
    out[0] = top;
    for (var n = 1; n <= upto; n++) {
      var d = C.upDistribution(stateOf(p), n);
      var arr = new Float64Array(maxPulls);
      arr.fill(1);
      var len = Math.min(d.cdf.length, maxPulls);
      for (var i = 0; i < len; i++) arr[i] = d.cdf[i];
      out[n] = arr;
    }
    return out;
  }

  M.char = {
    id: 'char',
    title: '角色池',
    group: '计算器',
    intro: '限定角色池的抽数分布：抽到指定数量的限定角色所需的抽数及其分位点。' +
           '模型依据：前 73 抽出金概率 0.6%，此后每抽递增 6 个百分点，第 90 抽必出金；' +
           '出金时 50% 为限定角色，歪后下一金必为限定，连歪触发捕获明光' +
           '（等效 UP 率 50.0%/54.8%/59.2%/100%）。参数取自社区总结的模型，结果仅供参考。',
    defaults: { nUp: 7, loss: 0, pity: 0, guaranteed: false },

    controls: function () {
      return [
        {
          type: 'range', key: 'nUp', label: '目标 UP 数', min: 1,
          max: C.LIMITS.charExactNUp, step: 1, unit: ' 个',
          help: '含角色本体；7 对应满命'
        },
        {
          type: 'segmented', key: 'loss', label: '已连歪次数',
          options: [{ value: 0, label: '0' }, { value: 1, label: '1' },
                    { value: 2, label: '2' }, { value: 3, label: '3' },
                    { value: C.STABLE_LOSS, label: '稳态' }],
          help: '「稳态」按连歪次数的长期分布加权'
        },
        {
          type: 'range', key: 'pity', label: '已垫抽数', min: 0, max: 89, step: 1,
          unit: ' 抽', help: '距上一个金的抽数'
        },
        {
          type: 'switch', key: 'guaranteed', label: '大保底',
          help: '下一个金必定为限定角色'
        }
      ];
    },

    views: {
      cdf: {
        label: '累积分布 (CDF)',
        render: function (host, ctx) {
          var p = ctx.state;
          var dist = distOf(p);
          var xMax = Math.max(1, Math.ceil(S.supportEnd(dist.cdf) * 1.05));
          var x = [], y = [];
          for (var i = 0; i <= xMax; i++) {
            x.push(String(i));
            y.push(i < dist.cdf.length ? dist.cdf[i] : 1);
          }
          var marks = ALPHAS.map(function (a, k) {
            var q = dist.quantile(a);
            return {
              x: String(Math.min(q, xMax)),
              y: a,
              color: C.COLORS.alpha6[k],
              text: 'α=' + a + '\n' + q + '抽',
              pos: 'insideEndTop'
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
              var pulls = Number(params[0].axisValue);
              return '≤ <b>' + pulls + '</b> 抽：<b>' + P.pctAdaptive(y[i]) + '</b>';
            }
          });
          setStatus(ctx, p, '最坏情况 ' + (dist.cdf.length - 1) + ' 抽');
        }
      },

      pdf: {
        label: '概率密度 (PDF)',
        render: function (host, ctx) {
          var p = ctx.state;
          var dist = distOf(p);
          var t0 = performance.now();
          var xMax = Math.max(2, Math.ceil(S.supportEnd(dist.cdf) * 1.02));
          var x = [], y = [];
          for (var i = 0; i <= xMax; i++) {
            x.push(String(i));
            y.push(i < dist.pdf.length ? dist.pdf[i] : 0);
          }
          var eIdx = Math.round(dist.expected);
          var peakIdx = S.maxIndex(dist.pdf);
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
              y: Math.min(eIdx < dist.pdf.length ? dist.pdf[eIdx] : 0, dist.pdf[peakIdx]) * 1.02,
              color: '#ff7f0e',
              text: '期望 ' + P.num(dist.expected, 1) + '抽',
              pos: 'insideEndTop'
            }],
            xLabel: '抽数',
            yLabel: '概率',
            yMax: dist.pdf[peakIdx] * 1.2,
            yTickFormatter: function (v) { return (v * 100).toFixed(1) + '%'; },
            tooltipFormatter: function (params) {
              var i = params[0].dataIndex;
              return '恰好 <b>' + params[0].axisValue + '</b> 抽达成：<b>' +
                     P.pctAdaptive(y[i]) + '</b>';
            }
          });
          setStatus(ctx, p, '单峰分布，峰值在 ' + mode + ' 抽 · 用时 ' +
                            (performance.now() - t0).toFixed(0) + 'ms');
        }
      },

      fan: {
        label: '幸运扇形',
        render: function (host, ctx) {
          var p = ctx.state;
          var maxN = Math.max(2, p.nUp);
          var xs = [], exps = [], bounds = {};
          FAN_ALPHAS.forEach(function (a) { bounds[a] = []; bounds[1 - a] = []; });

          for (var n = 1; n <= maxN; n++) {
            var d = C.upDistribution(stateOf(p), n);
            xs.push(n);
            exps.push(d.expected / n);
            FAN_ALPHAS.forEach(function (a) {
              bounds[a].push(d.quantile(a) / n);
              bounds[1 - a].push(d.quantile(1 - a) / n);
            });
          }

          /* 由外到内压栈：外层先画，内层后盖 */
          var regions = FAN_ALPHAS.slice().reverse().map(function (a, k) {
            var idx = FAN_ALPHAS.length - 1 - k;
            return {
              name: Math.round(a * 100) + '%–' + Math.round((1 - a) * 100) + '%',
              lo: bounds[a],
              hi: bounds[1 - a],
              color: FAN_COLORS[idx],
              opacity: idx === 0 ? 0.4 : 0.25
            };
          });

          var labelEvery = Math.max(1, Math.ceil(maxN / 15));
          var labels = [];
          for (var k = 0; k < maxN; k++) {
            if (k % labelEvery && k !== maxN - 1) continue;
            labels.push({ i: k, y: exps[k], text: exps[k].toFixed(1),
                          color: 'var(--text)', pos: 'top', weight: 'bold' });
          }

          var top = 0;
          FAN_ALPHAS.forEach(function (a) {
            bounds[1 - a].forEach(function (v) { if (v > top) top = v; });
          });

          var chart = P.chart(host);
          ctx.charts.regions(chart, {
            x: xs,
            xLabel: '目标 UP 数',
            yLabel: '平均每 UP 抽数',
            yMin: 0,
            yMax: Math.max(top * 1.08, 170),
            regions: regions,
            lines: [{
              name: '期望', y: exps, color: 'var(--text)', width: 2.2, symbolSize: 6
            }],
            labels: labels,
            hLines: [{
              y: 160, color: '#d62728', text: '极限大保底 160 抽/UP', pos: 'insideStartTop'
            }],
            yTickFormatter: function (v) { return v.toFixed(0); },
            tooltipFormatter: function (v) { return v.toFixed(1); },
            tooltipHtml: function (i) {
              var n = xs[i];
              var bands = FAN_ALPHAS.map(function (a, k) {
                return {
                  label: Math.round(a * 100) + '%–' + Math.round((1 - a) * 100) + '%',
                  color: FAN_COLORS[k],
                  lo: bounds[a][i].toFixed(1),
                  hi: bounds[1 - a][i].toFixed(1)
                };
              });
              return P.tipBands('第 ' + n + ' 个 UP · 抽/UP',
                [['期望', exps[i].toFixed(1)],
                 ['合计抽数', Math.round(exps[i] * n) + '抽']], bands);
            }
          });
          host.appendChild(P.note('纵轴为抽到第 n 个 UP 的总抽数除以 n。' +
            '区间自内向外依次为 40%–60%、30%–70%、20%–80%、10%–90%、1%–99%。'));
          setStatus(ctx, p, '第 ' + maxN + ' 个 UP 的期望成本 ' + exps[maxN - 1].toFixed(1) +
                            ' 抽/UP · 区间为同一 UP 的对称分位点');
        }
      },

      column: {
        advanced: true,
        label: '达成概率柱状',
        render: function (host, ctx) {
          var p = ctx.state;
          var N = p.nUp;
          var cats = [], tops = [], exps = [];
          var qs = COLUMN_ALPHAS.map(function () { return []; });
          var showLabels = N <= 10;

          for (var n = 1; n <= N; n++) {
            var d = C.upDistribution(stateOf(p), n);
            cats.push(String(n));
            tops.push(d.quantile(0.995));
            exps.push(d.expected);
            COLUMN_ALPHAS.forEach(function (c, k) { qs[k].push(d.quantile(c.a)); });
          }

          var chart = P.chart(host);
          var overlays = COLUMN_ALPHAS.map(function (c, k) {
            return {
              name: Math.round(c.a * 100) + '%',
              type: 'scatter', color: c.color,
              data: qs[k].map(function (v, m) { return [m, v]; }),
              symbol: 'rect', symbolSize: [22, 2],
              label: showLabels ? {
                formatter: function (pr) { return Math.round(pr.value[1]); }, pos: 'top'
              } : null
            };
          });
          overlays.push({
            name: '期望', type: 'line', color: 'var(--text)',
            data: exps.map(function (v, m) { return [m, v]; }),
            symbolSize: 5, width: 1.8,
            label: showLabels ? {
              formatter: function (pr) { return pr.value[1].toFixed(1); }, pos: 'bottom'
            } : null
          });

          ctx.charts.bars(chart, {
            categories: cats,
            xLabel: 'UP 数',
            yLabel: '投入总抽数',
            yMax: Math.max.apply(null, tops) * 1.18,
            xTickFormatter: function (v) { return v; },
            series: [{
              name: '99.5% 分位',
              values: tops,
              gradient: ['#deebf7', '#08519c'],
              maxWidth: N > 15 ? 14 : 26
            }],
            overlays: overlays,
            yTickFormatter: function (v) { return String(Math.round(v)); },
            tooltipFormatter: function (v) {
              return typeof v === 'number' ? v.toFixed(1) : v;
            }
          });
          host.appendChild(P.note('柱高为 99.5% 分位（近似上限），柱内颜色由浅至深对应达成概率自 0 到 1 递增；' +
                                  '横线为各分位点，黑线为期望抽数。'));
          setStatus(ctx, p, '每列对应抽到前 n 个 UP 所需的总抽数');
        }
      },

      stack: {
        advanced: true,
        label: '堆叠面积',
        render: function (host, ctx) {
          var p = ctx.state;
          var N = p.nUp;
          var maxNPulls = C.upDistribution(stateOf(p), N).quantile(0.995);
          var maxPulls = Math.min(Math.max(200, Math.ceil(maxNPulls * 1.05)), 6000);
          var stride = Math.max(1, Math.round(maxPulls / 600));
          var layers = Math.min(N, 10);
          var grid = cdfGrid(p, layers, maxPulls);

          var idx = [];
          for (var i = 0; i < maxPulls; i += stride) idx.push(i);
          if (idx[idx.length - 1] !== maxPulls - 1) idx.push(maxPulls - 1);

          var stack = [], n;
          for (n = 0; n < layers; n++) {
            stack.push({
              name: n === 0 ? '未获得 UP' : (n === 1 ? '1 个 UP（本体）' : n + ' 个 UP'),
              color: S.ramp(C.COLORS.spectral, n / layers),
              y: idx.map(function (t) { return Math.max(grid[n][t] - grid[n + 1][t], 0); })
            });
          }
          stack.push({
            name: '≥ ' + layers + ' 个 UP',
            color: S.ramp(C.COLORS.spectral, 1),
            y: idx.map(function (t) { return grid[layers][t]; })
          });

          var chart = P.chart(host);
          ctx.charts.regions(chart, {
            x: idx,
            xLabel: '累计抽数',
            yLabel: '玩家占比',
            yMin: 0,
            yMax: 1.02,
            stack: stack,
            legend: layers > 1,
            yTickFormatter: function (v) { return (v * 100).toFixed(0) + '%'; },
            tooltipFormatter: function (v) { return (v * 100).toFixed(1) + '%'; },
            tooltipHtml: function (i) {
              var t = idx[i];
              var rows = [];
              for (var k = 0; k < layers; k++) {
                rows.push([k === 0 ? '未获得 UP' : (k === 1 ? '1 个' : k + ' 个'),
                           P.pct(Math.max(grid[k][t] - grid[k + 1][t], 0))]);
              }
              rows.push(['≥ ' + layers + ' 个', P.pct(grid[layers][t])]);
              return P.tip('第 ' + t + ' 抽', rows);
            }
          });
          host.appendChild(P.note('各层为「恰好持有 n 个限定角色」的玩家占比，随抽数累积此消彼长；' +
            (N > layers ? '超过 ' + layers + ' 个的部分合并计入最上层。'
                        : '最上层为持有全部 ' + layers + ' 个的占比。')));
          setStatus(ctx, p, '横轴至 ' + maxPulls + ' 抽（' + N + ' 个 UP 的 99.5% 分位）');
        }
      },

      staircase: {
        advanced: true,
        label: '阶梯扇形',
        render: function (host, ctx) {
          var p = ctx.state;
          var N = p.nUp;
          var calcLimit = Math.min(N, 15);
          var maxPulls = Math.min(Math.max(200, Math.ceil(
            C.upDistribution(stateOf(p), N).quantile(0.995) * 1.05)), 6000);
          var stride = Math.max(1, Math.round(maxPulls / 600));
          var grid = cdfGrid(p, calcLimit, maxPulls);

          var alphas = [0.01, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.99];
          var bounds = {}, index = [], expectation = [];
          alphas.forEach(function (a) { bounds[a] = []; });
          for (var i = 0; i < maxPulls; i += stride) index.push(i);
          if (index[index.length - 1] !== maxPulls - 1) index.push(maxPulls - 1);

          index.forEach(function (i) {
            var vals = [];
            for (var n = 0; n <= calcLimit; n++) vals.push(grid[n][i]);
            var exp = 0;
            for (var n2 = 1; n2 <= calcLimit; n2++) exp += vals[n2];
            expectation.push(exp);
            alphas.forEach(function (a) {
              var hit = 0;
              for (var m = calcLimit; m >= 0; m--) {
                if (vals[m] >= 1 - a) { hit = m; break; }
              }
              bounds[a].push(hit);
            });
          });

          var pairs = [0.4, 0.3, 0.2, 0.1, 0.01];
          var blues = C.COLORS.blues;
          var regions = pairs.slice().reverse().map(function (a, k) {
            var idx = pairs.length - 1 - k;
            return {
              name: Math.round(a * 100) + '%–' + Math.round((1 - a) * 100) + '%',
              lo: bounds[a],
              hi: bounds[1 - a],
              color: blues[Math.round((0.8 - idx * 0.12) * 8)],
              opacity: 0.7 - idx * 0.12,
              step: 'end'
            };
          });

          var vLines = [];
          for (var k2 = 1; k2 <= calcLimit; k2++) {
            var idx2 = -1;
            for (var m2 = 0; m2 < expectation.length; m2++) {
              if (expectation[m2] >= k2) { idx2 = m2; break; }
            }
            if (idx2 < 0) continue;
            vLines.push({
              i: idx2, y0: 0, y1: k2, color: '#005f5f', text: index[idx2] + '抽'
            });
          }

          var chart = P.chart(host);
          ctx.charts.regions(chart, {
            x: index,
            xLabel: '累计消耗抽数',
            yLabel: '获得 UP 角色总数',
            yMin: 0,
            yMax: calcLimit + 0.8,
            regions: regions,
            lines: [
              { name: '期望 UP 数', y: expectation, color: 'var(--text)', width: 2.6 },
              { name: '中位数 (50%)', y: bounds[0.5], color: '#555555', width: 1.4,
                dash: true, step: 'end', symbol: false }
            ],
            vLines: vLines,
            yTickFormatter: function (v) { return Number.isInteger(v) ? String(v) : ''; },
            tooltipFormatter: function (v) { return typeof v === 'number' ? v.toFixed(1) : v; },
            tooltipHtml: function (i) {
              var rows = [['期望', expectation[i].toFixed(2) + ' 个'],
                          ['中位数', bounds[0.5][i] + ' 个']];
              [0.3, 0.1, 0.01].forEach(function (a) {
                rows.push([Math.round(a * 100) + '%–' + Math.round((1 - a) * 100) + '%',
                           bounds[a][i] + ' – ' + bounds[1 - a][i] + ' 个']);
              });
              return P.tip('第 ' + index[i] + ' 抽', rows);
            }
          });
          host.appendChild(P.note('期望线为前 ' + calcLimit + ' 个 UP 的达成概率累加：' +
            '\\(E[n]=\\sum_{k=1}^{' + calcLimit + '} P(\\geq k\\ \\text{个 UP})\\)。' +
            '虚线切面标出期望达到各整数个 UP 所需的抽数。'));
          UI.math.typeset(host);
          setStatus(ctx, p, '分位带为 UP 数的对称区间；求和截止到第 ' + calcLimit + ' 个 UP');
        }
      },

      table: {
        label: '分位点表',
        render: function (host, ctx) {
          var rows = [], labels = [];
          for (var k = 0; k < 4; k++) {
            rows.push(C.upDistribution(
              C.makeCharacterState({ consecutiveLoss: k, pity: 0 }), ctx.state.nUp));
            labels.push(C.MISS_LABELS[k][0]);
          }
          rows.push(C.stableUpDistribution(ctx.state.nUp));
          labels.push(C.MISS_LABELS[4][0]);

          var values = rows.map(function (d) {
            var line = ALPHAS.map(function (a) { return d.quantile(a); });
            line.push(d.expected);
            return line;
          });

          ctx.charts.table(host, {
            rowHeader: '状态',
            rowLabels: labels,
            colLabels: ALPHAS.map(function (a) { return (a * 100) + '%'; }).concat(['期望']),
            values: values,
            meanColumn: true,
            note: '单元格为达到该概率所需的抽数（期望列单位为抽）。稳态行按连歪次数的稳态概率 55.0%/27.5%/12.4%/5.1% 加权。'
          });
          ctx.setStatus('含已连歪 0–3 次与长期稳态共 5 种状态');
        }
      }
    }
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
