/* 模块共用的展示片段：数据条、图表容器、说明行 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var UI = W.ui = W.ui || {};
  var doc = global.document;

  var ICON_IMAGE = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" ' +
    'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" ' +
    'stroke-linejoin="round">' +
    '<rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/>' +
    '<path d="m21 15-3.6-3.6a2 2 0 0 0-2.8 0L5 21"/></svg>';
  var ICON_DOWN = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" ' +
    'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" ' +
    'stroke-linejoin="round">' +
    '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M4 21h16"/></svg>';

  /* 底色取当前主题的 --surface：canvas 本身透明，暗色下导出的图也该是深底 */
  function chartPng(inst) {
    var surface = global.getComputedStyle(doc.documentElement)
      .getPropertyValue('--surface').trim() || '#ffffff';
    return inst.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: surface });
  }

  function downloadChartPng(url) {
    var path = String(global.location.hash || '').replace(/^#\/?/, '').split('?')[0]
      .replace(/\//g, '-');
    var a = doc.createElement('a');
    a.href = url;
    a.download = 'genshin-wish' + (path ? '-' + path : '') + '.png';
    doc.body.appendChild(a);
    a.click();
    doc.body.removeChild(a);
  }

  /* data URL → Blob：剪贴板只收 Blob；用 atob 而不是 fetch，file:// 下同样可用 */
  function dataUrlToBlob(url) {
    var bin = global.atob(url.split(',')[1]);
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new global.Blob([bytes], { type: 'image/png' });
  }

  function instanceOf(chartEl) {
    var echarts = global.echarts;
    return chartEl && echarts ? echarts.getInstanceByDom(chartEl) : null;
  }

  var toastTimer = null;

  var P = UI.panels = {
    /* items: [[指标, 数值], ...]，数值列自动等宽对齐 */
    statRow: function (items) {
      var wrap = doc.createElement('div');
      wrap.className = 'statrow';
      items.forEach(function (it) {
        var cell = doc.createElement('div');
        cell.className = 'stat';
        var k = doc.createElement('span');
        k.className = 'stat__k';
        k.textContent = it[0];
        var v = doc.createElement('span');
        v.className = 'stat__v';
        v.innerHTML = it[1];
        cell.appendChild(k);
        cell.appendChild(v);
        wrap.appendChild(cell);
      });
      return wrap;
    },

    /* 图表容器。导出按钮不放在图上（会压住数据标注），由外壳的参数面板统一提供 */
    chart: function (host, modifier) {
      var node = doc.createElement('div');
      node.className = 'chart' + (modifier ? ' chart--' + modifier : '');
      host.appendChild(node);
      return node;
    },

    /* 返回说明节点，由调用方决定插入位置 */
    note: function (text) {
      var node = doc.createElement('p');
      node.className = 'chartnote';
      node.innerHTML = text;
      return node;
    },

    error: function (host, msg) {
      host.innerHTML = '<p class="viewerror">' + msg + '</p>';
    },

    /* 悬浮框内容：标题 + 两列读数 */
    tip: function (title, rows) {
      var html = '<p class="tip__t">' + title + '</p><table class="tip__table">';
      rows.forEach(function (r) {
        html += '<tr><th>' + r[0] + '</th><td>' + r[1] + '</td></tr>';
      });
      return html + '</table>';
    },

    /* 悬浮框：读数行 + 分位区间行。
     * 上下界各占一列（右对齐、等宽数字），比「85.3 – 93.3」整串文本对得齐；
     * 色块取自图中对应的区间颜色。bands: [{label, color, lo, hi}] */
    tipBands: function (title, rows, bands) {
      var html = '<p class="tip__t">' + title + '</p>';
      if (rows.length) {
        html += '<table class="tip__table">';
        rows.forEach(function (r) {
          html += '<tr><th>' + r[0] + '</th><td>' + r[1] + '</td></tr>';
        });
        html += '</table>';
      }
      html += '<div class="tip__bands">';
      bands.forEach(function (b) {
        html += '<span class="tip__sw" style="background:' + b.color + '"></span>' +
                '<span class="tip__band-k">' + b.label + '</span>' +
                '<span class="tip__num">' + b.lo + '</span>' +
                '<span class="tip__dash">–</span>' +
                '<span class="tip__num">' + b.hi + '</span>';
      });
      return html + '</div>';
    },

    /* --- 「给定抽数」类联合分布视图（角色池 / 武器池的「金数分布」）的共用片段 ---
     * joint = core 的 pullsJointDistribution / weaponPullsJointDistribution：
     *   matrix[u][s]（u = 目标数，s = 歪出数）、upMarginal[u]
     */

    BAR_RULES: { minP: 1e-4, maxBars: 20, top: 10, segMinP: 1e-6 },

    /* 取柱规则：概率 > 0.01% 的目标数单独成柱；超过 maxBars 根时只留概率之和最大的连续
       maxBars−2 项。两端各并成一根「< n」「> m」（不细分，把区间外的全部质量——含不足
       0.01% 的部分——计入，故柱子之和恒为 100%）；n = 0 或上方无正概率时省去。 */
    barSpec: function (joint, minP, maxBars) {
      minP = minP || P.BAR_RULES.minP;
      maxBars = maxBars || P.BAR_RULES.maxBars;
      var marg = joint.upMarginal, M = joint.matrix, u, i, j;
      var qual = [];
      for (u = 0; u < marg.length; u++) if (marg[u] > minP) qual.push(u);

      var merged = qual.length > maxBars;
      var lo = 0, hi = qual.length - 1;
      if (merged) {
        var width = maxBars - 2, bestSum = -1;
        for (i = 0; i + width <= qual.length; i++) {
          var sum = 0;
          for (j = i; j < i + width; j++) sum += marg[qual[j]];
          if (sum > bestSum) { bestSum = sum; lo = i; hi = i + width - 1; }
        }
      }

      var bars = [];
      if (qual[lo] > 0) {
        var below = 0;
        for (u = 0; u < qual[lo]; u++) below += marg[u];
        bars.push({ label: '<' + qual[lo], total: below, segs: null });
      }
      for (i = lo; i <= hi; i++) {
        u = qual[i];
        var segs = [];
        for (var s = 0; s < M[u].length; s++) {
          if (M[u][s] > 0) segs.push({ s: s, p: M[u][s] });
        }
        bars.push({ label: String(u), total: marg[u], segs: segs });
      }
      if (qual[hi] < marg.length - 1) {
        var above = 0;
        for (u = qual[hi] + 1; u < marg.length; u++) above += marg[u];
        bars.push({ label: '>' + qual[hi], total: above, segs: null });
      }
      return { bars: bars, merged: merged };
    },

    /* 堆叠柱状图：柱内按分段值分色（同一值在各柱同色，色带按该值在图中的出现区间拉伸，
       而不是按柱内排名；只为概率 ≥ 0.0001% 的分段建系列，更小的分段画出来也只是细边），
       柱顶标注该柱总概率，悬浮框由 segTip 拼装。
       opts = { xLabel, agg(bar), total(bar), seg(segment), palette, maxWidth } */
    stackBars: function (ctx, chart, bars, opts) {
      var palette = opts.palette || W.core.COLORS.stack;
      var seen = {};
      bars.forEach(function (b) {
        if (!b.segs) return;
        b.segs.forEach(function (sg) { if (sg.p >= P.BAR_RULES.segMinP) seen[sg.s] = true; });
      });
      var sList = Object.keys(seen).map(Number).sort(function (a, b) { return a - b; });
      var minS = sList.length ? sList[0] : 0;
      var maxS = sList.length ? sList[sList.length - 1] : 0;
      var width = opts.maxWidth || 34;
      var series = sList.map(function (s) {
        return {
          name: '', stack: 'up', maxWidth: width,
          color: W.core.stats.ramp(palette, maxS > minS ? (s - minS) / (maxS - minS) : 0),
          values: bars.map(function (b) {
            if (!b.segs) return null;
            for (var k = 0; k < b.segs.length; k++) {
              if (b.segs[k].s === s) return b.segs[k].p;
            }
            return null;
          })
        };
      });
      if (bars.some(function (b) { return !b.segs; })) {
        series.push({
          name: '', stack: 'up', maxWidth: width, color: 'var(--text-dim)',
          values: bars.map(function (b) { return b.segs ? null : b.total; })
        });
      }

      var top = 0;
      bars.forEach(function (b) { if (b.total > top) top = b.total; });
      ctx.charts.bars(chart, {
        categories: bars.map(function (b) { return b.label; }),
        xLabel: opts.xLabel,
        yLabel: '概率',
        yMax: Math.max(top * 1.16, 0.02),
        legend: false,
        series: series,
        /* 柱顶标注柱子的总概率：只要标注，不要折线与符号 */
        overlays: [{
          name: '', type: 'line', line: false, color: 'transparent', symbolSize: 1,
          data: bars.map(function (b, i) { return [i, b.total]; }),
          label: {
            pos: 'top', color: 'var(--text)',
            formatter: function (pr) { return P.pctAdaptive(pr.value[1]); }
          }
        }],
        yTickFormatter: function (v) { return (v * 100).toFixed(0) + '%'; },
        tooltipHtml: function (i) {
          return P.segTip(bars[i], { agg: opts.agg, total: opts.total, seg: opts.seg });
        }
      });
    },

    /* 悬浮框：柱内各分段按概率降序、最多 top 项，其余（含不足 0.0001% 的）合并一行。
       opts = { total(bar) → 标题, agg(bar) → 合并柱标题, seg(segment) → 行名, top } */
    segTip: function (bar, opts) {
      var top = opts.top || P.BAR_RULES.top;
      if (!bar.segs) {
        return P.tip(opts.agg(bar), [['合计', P.pctAdaptive(bar.total)]]);
      }
      var segs = bar.segs.slice().sort(function (a, b) { return b.p - a.p; });
      var rows = [], rest = 0, shown = 0;
      segs.forEach(function (sg, i) {
        if (i < top && sg.p >= P.BAR_RULES.segMinP) {
          rows.push([opts.seg(sg), P.pctAdaptive(sg.p)]);
          shown++;
        } else {
          rest += sg.p;
        }
      });
      if (shown < segs.length) {
        rows.push(['其余 ' + (segs.length - shown) + ' 项', P.pctAdaptive(rest)]);
      }
      return P.tip(opts.total(bar) + ' · ' + P.pctAdaptive(bar.total), rows);
    },

    /* 轻提示：状态类反馈统一走这里（app.js 的外壳也用） */
    toast: function (msg) {
      var t = doc.getElementById('toast');
      if (!t) return;
      t.textContent = msg;
      t.classList.add('is-on');
      global.clearTimeout(toastTimer);
      toastTimer = global.setTimeout(function () { t.classList.remove('is-on'); }, 1800);
    },

    /* --- 图像导出：图是 canvas，读者既选不中也复制不了 --- */

    copyChartImage: function (chartEl) {
      var inst = instanceOf(chartEl);
      if (!inst) { P.toast('当前视图没有图表'); return; }
      var url = chartPng(inst);
      var clip = global.navigator.clipboard;
      if (!global.ClipboardItem || !clip || !clip.write) {
        downloadChartPng(url);
        P.toast('浏览器不支持复制图像，已改为下载');
        return;
      }
      clip.write([new global.ClipboardItem({ 'image/png': dataUrlToBlob(url) })])
        .then(function () { P.toast('已复制图像'); },
              function () { downloadChartPng(url); P.toast('复制失败，已改为下载'); });
    },

    saveChartImage: function (chartEl) {
      var inst = instanceOf(chartEl);
      if (!inst) { P.toast('当前视图没有图表'); return; }
      downloadChartPng(chartPng(inst));
      P.toast('已开始下载');
    },

    /* 「复制图像 / 下载图像」两个按钮。target 可以是图表节点或返回节点的函数
       （参数面板在图表创建前就建好了，只能惰性取）；样式与摆放由调用方决定。 */
    chartActionButtons: function (target, btnClass) {
      var get = typeof target === 'function' ? target : function () { return target; };
      var cls = btnClass || 'btn btn--ghost';
      var copy = doc.createElement('button');
      copy.type = 'button';
      copy.className = cls;
      copy.innerHTML = ICON_IMAGE + '<span>复制图像</span>';
      copy.onclick = function () { P.copyChartImage(get()); };
      var save = doc.createElement('button');
      save.type = 'button';
      save.className = cls;
      save.innerHTML = ICON_DOWN + '<span>下载图像</span>';
      save.onclick = function () { P.saveChartImage(get()); };
      return [copy, save];
    },

    pct: function (v, d) { return (v * 100).toFixed(d === undefined ? 1 : d) + '%'; },

    /* 概率百分数：越靠近 0 或 100 越需要有效位数——
     * 0.2% 与 99.8% 之外各加一位小数，0.02% / 99.98% 再加一位，最多 4 位 */
    pctAdaptive: function (v, maxDigits) {
      var p = v * 100;
      if (p === 0 || p === 100) return p.toFixed(0) + '%';   /* 端点不必补小数位 */
      var d = 1, lim = 0.2;
      var max = maxDigits === undefined ? 4 : maxDigits;
      while (d < max && (p < lim || p > 100 - lim)) { d++; lim /= 10; }
      return p.toFixed(d) + '%';
    },

    /* 数值 → 保留 d 位、带千分位 */
    num: function (v, d) {
      return Number(v).toFixed(d === undefined ? 1 : d).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
