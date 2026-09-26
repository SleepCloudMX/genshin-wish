/* ECharts 封装 —— 图表只需传数据，配色/主题/标注排版在内部统一处理 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core;
  var UI = W.ui = W.ui || {};

  var MONO = 'Consolas, "Cascadia Mono", ui-monospace, monospace';
  var FONT = 'system-ui, "Microsoft YaHei", "PingFang SC", sans-serif';

  var instances = [];

  var _tokens = null;

  function rawToken(name, fallback) {
    if (!_tokens) _tokens = global.getComputedStyle(global.document.documentElement);
    var got = _tokens.getPropertyValue(name);
    return (got && got.trim()) || fallback;
  }

  function themeTokens() {
    _tokens = null;
    return {
      text: rawToken('--text', '#221f1a'),
      dim: rawToken('--text-dim', '#6f685c'),
      grid: rawToken('--grid', 'rgba(34,31,26,.10)'),
      axis: rawToken('--border', '#e5ded1'),
      surface: rawToken('--surface', '#ffffff'),
      tooltipBg: rawToken('--surface-2', '#f1ece2'),
      isDark: global.document.documentElement.getAttribute('data-theme') === 'dark'
    };
  }

  /* 颜色可以是 CSS 变量（'var(--text)'），暗色下把固定 hex 提亮以保证对比度 */
  function resolveColor(c, t, amount) {
    if (!c) return c;
    if (c.indexOf('var(') === 0) {
      var name = c.slice(4, c.length - 1).trim();
      return rawToken(name, t.text);
    }
    if (t.isDark) return C.stats.mixHex(c, '#ffffff', amount === undefined ? 0.3 : amount);
    return c;
  }

  function baseOption(t, opt) {
    return {
      animationDuration: 260,
      animationEasing: 'cubicOut',
      textStyle: { fontFamily: FONT, color: t.text, fontSize: 13 },
      grid: {
        left: 56,
        right: 28,
        top: opt.title ? 54 : ((opt.marks && opt.marks.length) ? 44 : 24),
        bottom: 44
      },
      title: opt.title ? {
        text: opt.title,
        subtext: opt.subtitle || '',
        left: 0,
        textStyle: { fontSize: 15, fontWeight: 600, color: t.text },
        subtextStyle: { fontSize: 12, color: t.dim }
      } : undefined,
      tooltip: {
        trigger: 'axis',
        confine: true,
        backgroundColor: t.surface,
        borderColor: t.axis,
        textStyle: { color: t.text, fontSize: 12, fontFamily: MONO },
        axisPointer: { type: 'line', lineStyle: { color: t.dim, type: 'dashed' } },
        formatter: opt.tooltipFormatter
      },
      xAxis: {
        type: 'category',
        name: opt.xLabel,
        nameLocation: 'middle',
        nameGap: 28,
        nameTextStyle: { color: t.dim, fontSize: 12 },
        axisLine: { lineStyle: { color: t.axis } },
        axisTick: { show: false },
        axisLabel: { color: t.dim, fontSize: 11, fontFamily: MONO, hideOverlap: true },
        splitLine: { show: false },
        data: opt.x
      },
      yAxis: {
        type: 'value',
        name: opt.yLabel,
        nameTextStyle: { color: t.dim, fontSize: 12, align: 'right' },
        min: opt.yMin === undefined ? 0 : opt.yMin,
        /* 顶部留 5% 余量：α=0.99 的标注框需要空间 */
        max: opt.yMax === undefined ? 1.05 : opt.yMax,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: t.dim, fontSize: 11, fontFamily: MONO,
          formatter: opt.yTickFormatter
        },
        splitLine: { lineStyle: { color: t.grid } }
      }
    };
  }

  function option(opt) {
    var t = themeTokens();
    var base = baseOption(t, opt);
    /* 类目轴标签密度：最多约 12 个刻度 */
    var n = (opt.x || []).length;
    base.xAxis.axisLabel.interval = n > 12 ? Math.ceil(n / 12) - 1 : 0;
    var series = (opt.series || []).map(function (s) {
      var color = resolveColor(s.color, t);
      return {
        name: s.name,
        type: 'line',
        showSymbol: false,
        symbol: 'circle',
        symbolSize: 6,
        smooth: false,
        step: s.step || false,
        data: s.y,
        lineStyle: {
          width: s.width === undefined ? 2.2 : s.width,
          color: color,
          type: s.dash ? 'dashed' : 'solid'
        },
        itemStyle: { color: color },
        areaStyle: s.fill ? { color: color, opacity: 0.1 } : undefined,
        markLine: buildMarkLines(s, opt, t),
        z: s.z === undefined ? 3 : s.z
      };
    });
    base.series = series;
    if (opt.legend !== false && series.length > 1) {
      base.legend = {
        top: 0, right: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10,
        textStyle: { color: t.dim, fontSize: 12 }
      };
      series.forEach(function (s) { s.markLine.silent = true; });
    }
    return base;
  }

  function buildMarkLines(s, opt, t) {
    var data = [];
    var marks = (s.marks || opt.marks || []);
    marks.forEach(function (m) {
      var color = resolveColor(m.color, t, 0.18);
      var style = { color: color, type: 'dashed', width: 1.2, opacity: 0.9 };
      data.push([
        { coord: [m.x, m.y0 === undefined ? 0 : m.y0] },
        {
          coord: [m.x, m.y],
          lineStyle: style,
          label: {
            show: !!m.text,
            formatter: m.text || '',
            position: m.pos || 'insideEndTop',
            rotate: 0,
            color: color,
            fontSize: 11,
            fontFamily: MONO,
            fontWeight: 600,
            padding: [3, 5],
            borderRadius: 4,
            backgroundColor: t.surface,
            borderColor: m.color,
            borderWidth: 1
          }
        }
      ]);
    });
    (opt.hLines || []).forEach(function (h) {
      data.push({
        yAxis: h.y,
        lineStyle: {
          color: resolveColor(h.color, t, 0.18), type: 'dotted', width: 1, opacity: 0.5
        },
        label: {
          show: !!h.text, formatter: h.text || '', position: 'insideStartTop',
          color: resolveColor(h.color, t, 0.18), fontSize: 11, rotate: 0
        }
      });
    });
    return { silent: true, symbol: 'none', data: data, animation: false };
  }

  UI.charts = {
    /* 折线：x 为字符串/数字数组，series[].y 与 x 等长 */
    line: function (host, opt) {
      var found = null;
      for (var i = 0; i < instances.length; i++) {
        if (instances[i].host === host) { found = instances[i]; break; }
      }
      if (found && found.kind === 'line' && !found.inst.isDisposed()) {
        found.opt = opt;
        found.inst.setOption(option(opt), true);
        return found.inst;
      }
      var inst = global.echarts.init(host, null, { renderer: 'canvas' });
      inst.setOption(option(opt));
      instances.push({ host: host, opt: opt, kind: 'line', inst: inst });
      return inst;
    },

    /* 视图重建后清掉已脱离文档的实例 */
    disposeDetached: function () {
      instances = instances.filter(function (it) {
        if (it.host && it.host.isConnected) return true;
        if (it.inst) { try { it.inst.dispose(); } catch (e) { /* noop */ } }
        return false;
      });
    },

    /* 数值表：行 = 状态，列 = 分位点/期望，带 Blues 底纹 */
    table: function (host, opt) {
      var rows = opt.rowLabels, cols = opt.colLabels, values = opt.values;
      var flat = [];
      values.forEach(function (r) { r.forEach(function (v) { flat.push(v); }); });
      var lo = Math.min.apply(null, flat), hi = Math.max.apply(null, flat);
      var blues = C.COLORS.blues;

      var html = '<div class="tablewrap"><table class="dtable">';
      html += '<thead><tr><th class="dtable__corner">' + (opt.rowHeader || '') +
              '</th>';
      cols.forEach(function (c) { html += '<th>' + c + '</th>'; });
      html += '</tr></thead><tbody>';
      rows.forEach(function (r, i) {
        html += '<tr><th class="dtable__row">' + r + '</th>';
        values[i].forEach(function (v, j) {
          var norm = hi > lo ? (v - lo) / (hi - lo) : 0;
          var bg = C.stats.ramp(blues, norm);
          var fg = norm > 0.6 ? '#ffffff' : '#2b2b2b';
          var isMean = j === cols.length - 1 && opt.meanColumn !== false;
          var text = isMean ? v.toFixed(1) : String(v);
          html += '<td style="background:' + bg + ';color:' + fg + '">' + text + '</td>';
        });
        html += '</tr>';
      });
      html += '</tbody></table></div>';
      if (opt.note) html += '<p class="chartnote">' + opt.note + '</p>';
      host.innerHTML = html;
      return null;
    },

    disposeAll: function () {
      instances.forEach(function (it) {
        if (it.inst) { try { it.inst.dispose(); } catch (e) { /* noop */ } }
      });
      instances = [];
    },

    /* 主题切换后重画（ECharts 不响应 CSS 变量） */
    redrawAll: function () {
      instances.forEach(function (it) {
        if (it.kind === 'line' && !it.inst.isDisposed()) {
          it.inst.setOption(option(it.opt), true);
        }
      });
    },

    resizeAll: function () {
      instances.forEach(function (it) {
        if (it.inst) { try { it.inst.resize(); } catch (e) { /* noop */ } }
      });
    }
  };

  global.addEventListener('resize', function () {
    global.clearTimeout(global.__wishResize);
    global.__wishResize = global.setTimeout(UI.charts.resizeAll, 120);
  });
})(typeof globalThis !== 'undefined' ? globalThis : this);
