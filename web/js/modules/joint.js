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

  function charStateOf(p) {
    return C.makeCharacterState({
      guaranteed: p.charGuaranteed, pity: p.charPity, consecutiveLoss: p.charLoss
    });
  }

  function weaponStateOf(p) {
    return C.makeWeaponState({ epitomizedPoints: p.weaponEp, pity: p.weaponPity });
  }

  function distOf(p) {
    return C.jointDistribution(charStateOf(p), p.charUp, weaponStateOf(p), p.weaponCount);
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
      weaponCount: 1, weaponEp: 0, weaponPity: 0
    },

    controls: function () {
      return [
        {
          type: 'range', key: 'charUp', label: '角色 UP 数', min: 1,
          max: C.LIMITS.charExactNUp, step: 1, unit: ' 个', help: '含角色本体'
        },
        {
          type: 'segmented', key: 'charLoss', label: '已连歪次数',
          options: [{ value: 0, label: '0' }, { value: 1, label: '1' },
                    { value: 2, label: '2' }, { value: 3, label: '3' }],
          help: '连歪会提升捕获明光概率'
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
          step: 1, unit: ' 把', help: '定轨不取消'
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
            xLabel: '角色池与武器池合计抽数',
            yLabel: '概率',
            yTickFormatter: function (v) { return v > 1.001 ? '' : (v * 100).toFixed(0) + '%'; },
            tooltipFormatter: function (params) {
              var i = params[0].dataIndex;
              return '合计 ≤ <b>' + params[0].axisValue + '</b> 抽全部达成：<b>' +
                     P.pctAdaptive(y[i]) + '</b>';
            }
          });
          ctx.setStatus('最坏情况 ' + (dist.cdf.length - 1) + '抽');
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
          ctx.setStatus('角色期望 ' + joint.char.expected.toFixed(0) + '抽 · 武器期望 ' +
                        joint.weapon.expected.toFixed(0) + '抽');
        }
      }
    }
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
