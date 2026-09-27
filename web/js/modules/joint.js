/* 角色 + 武器联合 —— 两者独立，总抽数为两条分布之和 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core;
  var S = C.stats;
  var M = W.modules = W.modules || {};
  var UI = W.ui;
  var P = UI.panels;

  var ALPHAS = C.CDF_ALPHAS;

  function isStable(p) { return p.charLoss === C.STABLE_LOSS; }

  function charStateOf(p) {
    return C.makeCharacterState({
      guaranteed: p.charGuaranteed, pity: p.charPity,
      consecutiveLoss: isStable(p) ? 0 : p.charLoss, stable: isStable(p)
    });
  }

  function weaponStateOf(p) {
    return C.makeWeaponState({ epitomizedPoints: p.weaponEp, pity: p.weaponPity });
  }

  function distOf(p) {
    return C.jointDistribution(charStateOf(p), p.charUp, weaponStateOf(p), p.weaponCount);
  }

  /* 双池分布：两池独立，给定各自的抽数预算后，(角色 UP 数, 武器把数) 的联合概率
     就是两条边际之积——柱高为角色 UP 数的边际，柱内按武器把数分色 */
  function budgetJoint(p) {
    var charPulls = Math.round(p.pulls * p.charShare / 100);
    var weaponPulls = p.pulls - charPulls;
    var a = C.pullsJointDistribution(charStateOf(p), charPulls).upMarginal;
    var b = C.weaponPullsJointDistribution(weaponStateOf(p), weaponPulls).upMarginal;
    var matrix = [];
    for (var i = 0; i < a.length; i++) {
      var row = new Float64Array(b.length);
      for (var j = 0; j < b.length; j++) row[j] = a[i] * b[j];
      matrix.push(row);
    }
    return {
      matrix: matrix, upMarginal: Float64Array.from(a),
      charPulls: charPulls, weaponPulls: weaponPulls, weapon: b
    };
  }

  /* 稳态时在状态条标注，免得只有控件上的选中态提示 */
  function setStatus(ctx, p, text) {
    ctx.setStatus(isStable(p) ? text + ' · 角色连歪次数取稳态' : text);
  }

  M.joint = {
    id: 'joint',
    title: '角色 + 武器',
    group: '计算器',
    intro: '角色池与武器池相互独立，两者都抽到目标所需的总抽数为两条分布之和（卷积）。' +
           '本页给出总抽数的分布与分位点，以及角色、武器各自的边际分布，' +
           '用于规划「角色 + 专武」的总预算。参数取自社区总结的模型，结果仅供参考。',
    defaults: {
      charUp: 2, charGuaranteed: false, charPity: 0, charLoss: 0,
      weaponCount: 1, weaponEp: 0, weaponPity: 0, pulls: 1000, charShare: 50
    },

    controls: function () {
      return [
        {
          type: 'range', key: 'charUp', label: '角色 UP 数', min: 1,
          max: C.LIMITS.charExactNUp, step: 1, unit: ' 个',
          views: ['cdf', 'table'], help: '含角色本体'
        },
        {
          type: 'number', key: 'pulls', label: '总抽数', min: 1,
          max: C.LIMITS.pullsMax, step: 1, views: ['spread'],
          help: '「双池分布」视图的抽数预算'
        },
        {
          type: 'range', key: 'charShare', label: '角色池占比', min: 0, max: 100,
          step: 5, unit: ' %', views: ['spread'],
          help: '其余抽数给武器池'
        },
        {
          type: 'segmented', key: 'charLoss', label: '已连歪次数',
          options: [{ value: 0, label: '0' }, { value: 1, label: '1' },
                    { value: 2, label: '2' }, { value: 3, label: '3' },
                    { value: C.STABLE_LOSS, label: '稳态' }],
          help: '「稳态」按连歪次数的长期分布加权'
        },
        {
          type: 'range', key: 'charPity', label: '角色池已垫', min: 0, max: 89,
          step: 1, unit: ' 抽'
        },
        {
          type: 'switch', key: 'charGuaranteed', label: '角色池大保底',
          help: '下一个金必定为限定角色'
        },
        {
          type: 'range', key: 'weaponCount', label: '目标武器数量', min: 1, max: 5,
          step: 1, unit: ' 把', views: ['cdf', 'table'], help: '定轨不取消'
        },
        {
          type: 'segmented', key: 'weaponEp', label: '武器池命定值',
          options: [{ value: 0, label: '0' }, { value: 1, label: '1' }]
        },
        {
          type: 'range', key: 'weaponPity', label: '武器池已垫', min: 0,
          max: C.LIMITS.maxPity.weapon, step: 1, unit: ' 抽'
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
            xLabel: '角色池与武器池合计抽数',
            yLabel: '概率',
            yTickFormatter: function (v) { return v > 1.001 ? '' : (v * 100).toFixed(0) + '%'; },
            tooltipFormatter: function (params) {
              var i = params[0].dataIndex;
              return '合计 ≤ <b>' + params[0].axisValue + '</b> 抽全部达成：<b>' +
                     P.pctAdaptive(y[i]) + '</b>';
            }
          });
          setStatus(ctx, p, '最坏情况 ' + (dist.cdf.length - 1) + '抽');
        }
      },

      spread: {
        label: '双池分布',
        render: function (host, ctx) {
          var p = ctx.state;
          var t0 = performance.now();
          var joint = budgetJoint(p);
          var spec = P.barSpec(joint);
          var rules = P.BAR_RULES;

          var eUp = 0, eW = 0;
          for (var u = 0; u < joint.upMarginal.length; u++) eUp += u * joint.upMarginal[u];
          for (var w = 0; w < joint.weapon.length; w++) eW += w * joint.weapon[w];

          var chart = P.chart(host);
          host.appendChild(P.statRow([
            ['角色池抽数', joint.charPulls + '抽'],
            ['武器池抽数', joint.weaponPulls + '抽'],
            ['期望角色 UP 数', P.num(eUp, 2)],
            ['期望武器把数', P.num(eW, 2)]
          ]));
          P.stackBars(ctx, chart, spec.bars, {
            xLabel: '抽到的限定角色数',
            agg: function (b) { return '限定 ' + b.label + ' 个（不细分武器数）'; },
            total: function (b) { return '恰好 ' + b.label + ' 个限定'; },
            seg: function (sg) { return '武器 ' + sg.s + ' 把'; }
          });
          host.appendChild(P.note('把总抽数按「角色池占比」分给两池后，横轴为抽到的限定角色数，' +
            '柱内按抽到的定轨目标武器数分色；两池相互独立，故联合概率等于两条边际之积。' +
            '概率不足 0.01% 的角色数不单独画柱，' +
            (spec.merged ? '超过 ' + rules.maxBars + ' 根时只留概率之和最大的连续 ' +
                           (rules.maxBars - 2) + ' 项，' : '') +
            '两端分别并入「< n」「> m」两根（不细分武器数）。' +
            '换一种问法——「抽到角色就转抽武器」——属于策略问题，不在这张图的口径内。'));
          ctx.setStatus(p.pulls + ' 抽 · 角色 ' + joint.charPulls + ' / 武器 ' +
                        joint.weaponPulls + ' · ' + spec.bars.length + ' 根柱子 · 用时 ' +
                        (performance.now() - t0).toFixed(0) + 'ms');
        }
      },

      table: {
        label: '分位点对照',
        render: function (host, ctx) {
          var p = ctx.state;
          var joint = distOf(p);
          var parts = [
            ['角色 ' + p.charUp + ' 个 UP', joint.char],
            ['武器 ' + p.weaponCount + ' 把', joint.weapon],
            ['两者合计', joint]
          ];
          var values = parts.map(function (it) {
            var line = ALPHAS.map(function (a) { return it[1].quantile(a); });
            line.push(it[1].expected);
            return line;
          });
          var share = (joint.char.expected / joint.expected * 100).toFixed(0);

          ctx.charts.table(host, {
            rowHeader: '目标',
            rowLabels: parts.map(function (it) { return it[0]; }),
            colLabels: ALPHAS.map(function (a) { return (a * 100) + '%'; }).concat(['期望']),
            values: values,
            meanColumn: true,
            note: '单元格为达到该概率所需的抽数（期望列单位为抽）。合计行的期望等于两行之和；' +
                  '分位点因两者独立而不可直接相加。本组合中角色占期望的 ' + share + '%。'
          });
          setStatus(ctx, p, '角色期望 ' + joint.char.expected.toFixed(0) + '抽 · 武器期望 ' +
                            joint.weapon.expected.toFixed(0) + '抽');
        }
      }
    }
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
