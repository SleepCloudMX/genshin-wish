/* 角色池模块 —— 对应 output/character/ 下的 CDF 曲线与分位点表 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core;
  var M = W.modules = W.modules || {};
  var doc = global.document;

  var ALPHAS = C.CDF_ALPHAS;

  function stateOf(p) {
    return C.makeCharacterState({
      guaranteed: p.guaranteed,
      pity: p.pity,
      consecutiveLoss: p.loss
    });
  }

  function distOf(p) {
    return C.upDistribution(stateOf(p), p.nUp);
  }

  function percent(v) { return (v * 100).toFixed(1) + '%'; }

  /* 注册键必须与路由 id 一致（#/char/...） */
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
          help: '含本体；7 = 满命'
        },
        {
          type: 'segmented', key: 'loss', label: '已连歪次数',
          options: [{ value: 0, label: '0' }, { value: 1, label: '1' },
                    { value: 2, label: '2' }, { value: 3, label: '3' }],
          help: '连歪会提升捕获明光概率'
        },
        {
          type: 'range', key: 'pity', label: '已垫抽数', min: 0, max: 89, step: 1,
          unit: ' 抽', help: '距上一个金的抽数'
        },
        {
          type: 'switch', key: 'guaranteed', label: '大保底',
          help: '下一个金必定是 UP'
        }
      ];
    },

    views: {
      cdf: {
        label: '累积分布 (CDF)',
        render: function (host, ctx) {
          var p = ctx.state;
          var dist = distOf(p);
          var t0 = performance.now();
          var xMax = Math.max(1, Math.ceil(C.stats.supportEnd(dist.cdf) * 1.05));
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
              text: 'α=' + a + '\n' + q + ' 抽',
              pos: 'insideEndTop'
            };
          });
          /* 期望值不画进图里：与 50% 分位几乎重合，改由下方数据条呈现 */


          var chart = doc.createElement('div');
          chart.className = 'chart';
          host.appendChild(chart);
          host.appendChild(statRow(dist));

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
              return '≤ <b>' + pulls + '</b> 抽：<b>' + percent(y[i]) + '</b>';
            }
          });
          ctx.setStatus('最坏情况 ' + (dist.cdf.length - 1) +
                        ' 抽（此后概率恒为 100%）');
        }
      },

      table: {
        label: '分位点表',
        render: function (host, ctx) {
          var t0 = performance.now();
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
            note: '单元格为达到该概率所需的抽数（期望列单位为抽）。稳态 = 连歪次数按稳态概率 55.0%/27.5%/12.4%/5.1% 加权。'
          });
          ctx.setStatus('含已连歪 0–3 次与长期稳态共 5 种状态；' +
                        '表格中的抽数为达到该概率所需抽数');
        }
      }
    }
  };

  function statRow(dist) {
    var wrap = doc.createElement('div');
    wrap.className = 'statrow';
    var items = [
      ['期望抽数', dist.expected.toFixed(1)],
      ['50% 分位', dist.quantile(0.5) + ' 抽'],
      ['90% 分位', dist.quantile(0.9) + ' 抽'],
      ['99% 分位', dist.quantile(0.99) + ' 抽']
    ];
    items.forEach(function (it) {
      var cell = doc.createElement('div');
      cell.className = 'stat';
      cell.innerHTML = '<span class="stat__k">' + it[0] + '</span>' +
                       '<span class="stat__v">' + it[1] + '</span>';
      wrap.appendChild(cell);
    });
    return wrap;
  }
})(typeof globalThis !== 'undefined' ? globalThis : this);
