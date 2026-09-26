/* 个人记录 —— 把自己的抽卡记录换算成百分位 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core;
  var S = C.stats;
  var M = W.modules = W.modules || {};
  var UI = W.ui;
  var P = UI.panels;

  var SAMPLE = '68,79+11,77+80,62,71+9';
  var REF_LINES = [
    { a: 0.01, color: '#cb181d' }, { a: 0.1, color: '#f16913' },
    { a: 0.2, color: '#4292c6' }, { a: 0.3, color: '#2171b5' },
    { a: 0.4, color: '#084594' }
  ];

  function stateOf(p) {
    return C.makeCharacterState({
      guaranteed: p.guaranteed, pity: p.pity, consecutiveLoss: p.loss
    });
  }

  /* 序列 → 累计百分位、逐次分位、状态轨迹 */
  function analyse(p) {
    var parsed = C.parsePullsSeq(p.seq);
    var n = parsed.perUp.length;
    if (n === 0) throw new RangeError('序列为空');
    var nPre = Math.min(Math.max(0, p.nPre), n);
    var state = stateOf(p);

    /* n 个 UP 的抽数分布：5.0 前一段 + 捕获明光一段 */
    function distFor(m) {
      if (nPre === 0) return C.upDistribution(state, m);
      if (m <= nPre) return C.upDistributionPre50(state, m);
      var pre = C.upDistributionPre50(state, nPre);
      var post = C.upDistribution(C.makeCharacterState({}), m - nPre);
      return C.makeDistribution(S.convolve(pre.pdf, post.pdf));
    }

    var cumulativePct = [], refMedians = [];
    for (var i = 0; i < n; i++) {
      var d = distFor(i + 1);
      cumulativePct.push(d.probability(parsed.cumulative[i]) * 100);
      refMedians.push(d.quantile(0.5));
    }

    /* 逐次分位：按记录倒推每抽之前的状态 */
    var gtd = !!p.guaranteed, km = p.loss;
    var marginalPct = [];
    for (var j = 0; j < n; j++) {
      var useKm = km;
      if (nPre > 0 && j === nPre) { km = 0; useKm = 0; }
      var st = C.makeCharacterState({ guaranteed: gtd, pity: 0, consecutiveLoss: useKm });
      var single = (nPre > 0 && j < nPre) ? C.upDistributionPre50(st, 1)
                                          : C.upDistribution(st, 1);
      var idx = Math.min(parsed.perUp[j], single.cdf.length - 1);
      marginalPct.push(single.cdf[idx] * 100);

      if (parsed.isDirectWin[j]) {
        km = 0;
        gtd = false;
      } else {
        km = (nPre > 0 && j < nPre) ? 0 : Math.min(km + 1, 3);
        gtd = false;
      }
    }

    return {
      parsed: parsed, n: n, nPre: nPre, nPost: n - nPre,
      cumulativePct: cumulativePct, marginalPct: marginalPct,
      refMedians: refMedians, distFor: distFor
    };
  }

  function guard(host, ctx) {
    try {
      return analyse(ctx.state);
    } catch (e) {
      P.error(host, e instanceof RangeError
        ? '序列无法解析：' + e.message + '（示例：' + SAMPLE + '）'
        : String(e.message || e));
      return null;
    }
  }

  M.player = {
    id: 'player',
    title: '个人记录',
    group: '计算器',
    intro: '把自己的抽卡记录换算成百分位：逐个 UP 的累计抽数对应多少玩家比不过你。' +
           '序列中每次 UP 写抽数，歪后用「a+b」记录（a 为歪的金、b 为随后的保底金）。' +
           '结果对照的是本项目的社区模型，仅供参考。',
    defaults: { seq: SAMPLE, nPre: 0, loss: 0, guaranteed: false, pity: 0 },

    controls: function () {
      return [
        {
          type: 'text', key: 'seq', label: '抽卡序列', mono: true,
          placeholder: SAMPLE,
          help: '逗号分隔；直接中的写「68」，歪的写「79+11」'
        },
        {
          type: 'range', key: 'nPre', label: '5.0 前的 UP 数', min: 0, max: 50,
          step: 1, unit: ' 个', help: '按纯 50/50 加大保底解读'
        },
        {
          type: 'segmented', key: 'loss', label: '记录开始时的连歪次数',
          options: [{ value: 0, label: '0' }, { value: 1, label: '1' },
                    { value: 2, label: '2' }, { value: 3, label: '3' }]
        },
        {
          type: 'range', key: 'pity', label: '记录开始时的垫抽', min: 0, max: 89,
          step: 1, unit: ' 抽'
        },
        {
          type: 'switch', key: 'guaranteed', label: '记录开始时为大保底',
          help: '第一个金必为限定'
        }
      ];
    },

    views: {
      luck: {
        label: '整体欧非趋势',
        render: function (host, ctx) {
          var a = guard(host, ctx);
          if (!a) return;
          var parsed = a.parsed;

          var xs = [], labels = [];
          for (var i = 0; i < a.n; i++) {
            xs.push(i + 1);
            if (a.n <= 20 || i === 0 || i === a.n - 1) {
              labels.push({ i: i, y: a.cumulativePct[i],
                            text: a.cumulativePct[i].toFixed(1) + '%',
                            color: '#27ae60', pos: 'bottom' });
            }
          }

          var hLines = REF_LINES.map(function (r) {
            return { y: r.a * 100, color: r.color, text: Math.round(r.a * 100) + '%' };
          }).concat(REF_LINES.map(function (r) {
            return { y: 100 - r.a * 100, color: r.color };
          })).concat([{ y: 50, color: '#555555', text: '50%', pos: 'insideStartTop' }]);

          var chart = P.chart(host);
          var total = parsed.cumulative[parsed.cumulative.length - 1];
          var wins = parsed.isDirectWin.filter(Boolean).length;
          host.appendChild(P.statRow([
            ['记录 UP 数', a.n + ' 个'],
            ['平均每 UP', P.num(total / a.n, 1) + '抽'],
            ['不歪率', P.pct(wins / a.n)],
            ['当前百分位', P.pct(a.cumulativePct[a.n - 1] / 100)]
          ]));

          ctx.charts.regions(chart, {
            x: xs,
            xLabel: '第几个 UP',
            yLabel: '比多少玩家非',
            yMin: 0,
            yMax: 102,
            legend: false,
            lines: [{
              name: '玩家记录', y: a.cumulativePct, color: '#27ae60', width: 2.4,
              symbolSize: 7
            }],
            labels: labels,
            hLines: hLines,
            yTickFormatter: function (v) { return v.toFixed(0) + '%'; },
            tooltipFormatter: function (v) { return v.toFixed(1) + '%'; }
          });
          host.appendChild(P.note('曲线为该 UP 数量下的累计百分位：纵值 70% 表示同期有 70% 的玩家' +
            '所需抽数比你少。横线为对称分位参考（1/99、10/90、20/80、30/70、40/60）与中位数。' +
            '悬停可查看同期中位数所需抽数。'));
          ctx.setStatus('合计 ' + total + ' 抽 · 未歪 ' + wins + ' 次 / 共 ' + a.n + ' 个 UP' +
                        (a.nPre > 0 ? ' · 前 ' + a.nPre + ' 个按 5.0 前机制' : ''));
        }
      },

      table: {
        label: '逐次对照',
        render: function (host, ctx) {
          var a = guard(host, ctx);
          if (!a) return;
          var parsed = a.parsed;
          var rows = [], labels = [];
          for (var i = 0; i < a.n; i++) {
            rows.push([
              parsed.perUp[i], parsed.isDirectWin[i] ? 1 : 0,
              a.marginalPct[i], parsed.cumulative[i], a.cumulativePct[i]
            ]);
            labels.push('第 ' + (i + 1) + ' 个');
          }

          ctx.charts.table(host, {
            shade: false,
            rowHeader: 'UP',
            rowLabels: labels,
            colLabels: ['本次抽数', '直接中', '本次分位', '累计抽数', '累计分位'],
            values: rows,
            format: function (v, j) {
              if (j === 1) return v ? '是' : '歪';
              if (j === 2 || j === 4) return v.toFixed(1) + '%';
              return String(v) + (j === 0 ? '抽' : '');
            },
            note: '「本次分位」以记录倒推出的当时状态（是否大保底、连歪几次）为基准，' +
                  '表示这一次出金的运气；「累计分位」不依赖状态，表示到此为止的总运气。'
          });
          ctx.setStatus('共 ' + a.n + ' 次出金记录');
        }
      }
    }
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
