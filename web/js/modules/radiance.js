/* 捕获明光 —— 抽 UP 过程中明光触发次数的分布 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core;
  var M = W.modules = W.modules || {};
  var UI = W.ui;
  var P = UI.panels;

  var MISS = C.MISS_LABELS;
  var SAMPLE = '1,2,2,1,2,1,2,2,1,1';

  function stateOf(p) {
    return C.makeCharacterState({ pity: 0, consecutiveLoss: p.loss, guaranteed: false });
  }

  /* 序列里的项数即要抽的 UP 数（空项不算） */
  function seqCount(raw) {
    return String(raw === undefined || raw === null ? '' : raw).split(',')
      .map(function (s) { return s.trim(); })
      .filter(function (s) { return s.length > 0; }).length;
  }

  /* 分布 → 柱状图数据。
   * 概率不足 0.01% 的尾部不单独画柱：横轴止于最后一个达标的分支，
   * 其余合并成一根「> n」柱，高度为超出部分的总概率（分布本身照常返回全部概率）。 */
  function barData(dist) {
    var maxR = 0, expected = 0;
    Object.keys(dist).forEach(function (k) {
      if (Number(k) > maxR) maxR = Number(k);
      expected += Number(k) * dist[k];
    });

    var last = -1, r;
    for (r = 0; r <= maxR; r++) {
      if ((dist[r] || 0) >= 0.0001) last = r;
    }
    if (last < 0) last = maxR;                 /* 全部低于阈值时不合并 */

    var labels = [], values = [];
    for (r = 0; r <= Math.min(last, maxR); r++) {
      labels.push(String(r));
      values.push(dist[r] || 0);
    }
    var merged = last < maxR;
    if (merged) {
      var tail = 0;
      for (r = last + 1; r <= maxR; r++) tail += dist[r] || 0;
      labels.push('>' + last);
      values.push(tail);
    }
    return { labels: labels, values: values, maxR: maxR, merged: merged,
             expected: expected };
  }

  function drawBars(chart, ctx, data) {
    ctx.charts.bars(chart, {
      categories: data.labels,
      xLabel: '捕获明光触发次数',
      yLabel: '概率',
      series: [{ name: '恰好触发 r 次', values: data.values, color: '#deebf7',
                 borderColor: '#4292c6', borderWidth: 0.5, maxWidth: 34 }],
      valueLabels: { show: data.labels.length <= 12,
                     formatter: function (pr) { return P.pctAdaptive(pr.value); } },
      yTickFormatter: function (v) { return (v * 100).toFixed(0) + '%'; },
      tooltipFormatter: function (v) { return P.pctAdaptive(v); }
    });
  }

  /* 尾部合并时的说明，未合并则为空 */
  function tailNote(data) {
    return data.merged
      ? '最后一柱为「' + data.labels[data.labels.length - 1].replace('>', '超过 ') +
        ' 次」的总概率，不足 0.01% 的分支不再单独画柱。'
      : '';
  }

  M.radiance = {
    id: 'radiance',
    title: '捕获明光',
    group: '计算器',
    intro: '捕获明光的触发次数分布：在连续歪 0/1/2/3 次时，出金的中奖率分别为 ' +
           '50.0%/54.8%/59.2%/100%，其中高出 50% 的部分即明光的作用。' +
           '本页给出抽 UP 过程中明光触发次数的分布，也可按给定的中／歪序列计算。' +
           '参数取自社区总结的模型，结果仅供参考。',
    defaults: { nUp: 7, loss: 0, seq: SAMPLE },

    controls: function () {
      return [
        {
          type: 'range', key: 'nUp', label: '目标 UP 数', min: 1, max: 100, step: 1,
          unit: ' 个', help: '含角色本体', views: ['bar', 'table']
        },
        {
          type: 'segmented', key: 'loss', label: '已连歪次数',
          options: [{ value: 0, label: '0' }, { value: 1, label: '1' },
                    { value: 2, label: '2' }, { value: 3, label: '3' }],
          views: ['bar', 'table']
        },
        {
          type: 'static', key: 'nUp', label: '目标 UP 数', views: ['seq'],
          value: function (state) {
            var n = seqCount(state.seq);
            return n ? n + ' 个' : '—';
          },
          help: '由序列长度决定，不可修改'
        },
        {
          type: 'text', key: 'seq', label: '中／歪序列', views: ['seq'],
          help: '1 表示中、2 表示歪，逗号分隔', placeholder: SAMPLE
        }
      ];
    },

    views: {
      bar: {
        label: '次数分布',
        render: function (host, ctx) {
          var p = ctx.state;
          var dist = C.radianceDistribution(stateOf(p), p.nUp);
          var data = barData(dist);

          host.appendChild(P.statRow([
            ['期望触发次数', P.num(data.expected, 2)],
            ['一次都不触发', P.pct(dist[0] || 0)],
            ['每个 UP 平均', P.num(data.expected / p.nUp, 3) + ' 次'],
            ['最多触发', data.maxR + ' 次']
          ]));
          drawBars(P.chart(host), ctx, data);
          host.appendChild(P.note('明光只在 50/50 未中时补足概率，因此触发次数不超过歪的次数；' +
            '已连歪 ' + p.loss + ' 次起步时初始中奖率即为 ' +
            (C.CAPTURE_RADIANCE_WIN_RATE[p.loss] * 100).toFixed(1) + '%。' + tailNote(data)));
          ctx.setStatus(p.nUp + ' 个 UP · 每次出金依次更新连歪状态');
        }
      },

      seq: {
        label: '按序列',
        render: function (host, ctx) {
          var raw = String(ctx.state.seq || '').trim();
          var parts = raw.split(',').map(function (s) { return s.trim(); })
            .filter(function (s) { return s.length > 0; });
          var seq = [];
          for (var i = 0; i < parts.length; i++) {
            var v = Number(parts[i]);
            if (v !== 1 && v !== 2) {
              P.error(host, '序列只能包含 1（中）与 2（歪），以逗号分隔。当前输入：' + raw);
              return;
            }
            seq.push(v);
          }
          if (!seq.length) {
            P.error(host, '请填写中／歪序列，例如 ' + SAMPLE);
            return;
          }

          var dist = C.radianceDistFromSeq(seq);
          var wins = seq.filter(function (v) { return v === 1; }).length;
          var data = barData(dist);
          host.appendChild(P.statRow([
            ['中／歪', wins + ' / ' + (seq.length - wins)],
            ['不歪率', P.pct(wins / seq.length)],
            ['期望触发次数', P.num(data.expected, 3)],
            ['最多触发', data.maxR + ' 次']
          ]));
          drawBars(P.chart(host), ctx, data);
          host.appendChild(P.note('序列 ' + seq.join(',') + '：对每次「中」按当前连歪状态折算明光概率' +
            '（50% 之外的部分），再按泊松二项分布累加。' + tailNote(data)));
          ctx.setStatus('按 ' + seq.length + ' 次出金记录计算');
        }
      },

      table: {
        label: '分布表',
        render: function (host, ctx) {
          var p = ctx.state;
          var maps = [], maxR = 0, k, r;
          for (k = 0; k < 4; k++) {
            maps.push(C.radianceDistribution(
              C.makeCharacterState({ pity: 0, consecutiveLoss: k }), p.nUp));
          }
          maps.forEach(function (map) {
            Object.keys(map).forEach(function (kk) { if (Number(kk) > maxR) maxR = Number(kk); });
          });

          var cols = [];
          for (r = 0; r <= maxR; r++) cols.push(String(r));
          var values = maps.map(function (map) {
            var line = [];
            for (r = 0; r <= maxR; r++) line.push(map[r] || 0);
            return line;
          });

          ctx.charts.table(host, {
            rowHeader: '已连歪次数',
            rowLabels: [MISS[0][0], MISS[1][0], MISS[2][0], MISS[3][0]],
            colLabels: cols,
            values: values,
            format: function (v) { return (v * 100).toFixed(1) + '%'; },
            note: '行为开始抽卡时的连歪次数，列为明光触发次数，单元格为概率。' +
                  '连歪 3 次后中奖率为 100%，明光不再额外补偿，分布右上角随即收窄。'
          });
          ctx.setStatus(p.nUp + ' 个 UP · 明光次数 0–' + maxR);
        }
      }
    }
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
