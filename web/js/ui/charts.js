/* ECharts 封装 —— 图表只需传数据，配色/主题/标注排版在内部统一处理
 * line  ：类目横轴（抽数、UP 数）的折线
 * curve ：数值/对数横轴的折线，支持误差带与文字标注（性能实验图）
 * bars  ：柱状图
 * table ：数值表（带底纹）
 */
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
      axis: rawToken('--border', '#e6dfd2'),
      surface: rawToken('--surface', '#ffffff'),
      isDark: global.document.documentElement.getAttribute('data-theme') === 'dark'
    };
  }

  /* 颜色可以是 CSS 变量（'var(--text)'）；暗色下把固定 hex 提亮以保证对比度 */
  function resolveColor(c, t, amount) {
    if (!c) return c;
    if (c.indexOf('var(') === 0) return rawToken(c.slice(4, c.length - 1).trim(), t.text);
    if (t.isDark) return C.stats.mixHex(c, '#ffffff', amount === undefined ? 0.3 : amount);
    return c;
  }

  function baseText(t) {
    return { fontFamily: FONT, color: t.text, fontSize: 13 };
  }

  function axisCommon(t, opt, which) {
    var isLog = (which === 'x' ? opt.xType : opt.yType) === 'log';
    return {
      type: isLog ? 'log' : (which === 'x' && opt.categories ? 'category' : 'value'),
      name: which === 'x' ? opt.xLabel : opt.yLabel,
      nameLocation: 'middle',
      nameGap: which === 'x' ? 30 : 44,
      nameTextStyle: { color: t.dim, fontSize: 12 },
      axisLine: { lineStyle: { color: t.axis } },
      axisTick: { show: false },
      axisLabel: {
        color: t.dim, fontSize: 11, fontFamily: MONO, hideOverlap: true,
        formatter: which === 'x' ? opt.xTickFormatter : opt.yTickFormatter
      },
      splitLine: which === 'y'
        ? { lineStyle: { color: t.grid } }
        : { show: false },
      min: which === 'x' ? opt.xMin : opt.yMin,
      max: which === 'x' ? opt.xMax : opt.yMax,
      logBase: 10
    };
  }

  function acquire(host, kind) {
    for (var i = 0; i < instances.length; i++) {
      var it = instances[i];
      if (it.host === host && !it.inst.isDisposed()) { it.kind = kind; return it; }
    }
    var created = { host: host, kind: kind, inst: global.echarts.init(host, null, { renderer: 'canvas' }) };
    instances.push(created);
    return created;
  }

  /* --- 类目横轴折线（角色池 CDF 等） --- */
  function lineOption(opt, t) {
    var base = {
      animationDuration: 260,
      animationEasing: 'cubicOut',
      textStyle: baseText(t),
      grid: {
        left: 56, right: 28,
        top: opt.title ? 54 : ((opt.marks && opt.marks.length) ? 44 : 24),
        bottom: 44
      },
      title: opt.title ? {
        text: opt.title, subtext: opt.subtitle || '', left: 0,
        textStyle: { fontSize: 15, fontWeight: 600, color: t.text },
        subtextStyle: { fontSize: 12, color: t.dim }
      } : undefined,
      tooltip: {
        trigger: 'axis', confine: true, backgroundColor: t.surface,
        borderColor: t.axis, textStyle: { color: t.text, fontSize: 12, fontFamily: MONO },
        axisPointer: { type: 'line', lineStyle: { color: t.dim, type: 'dashed' } },
        formatter: opt.tooltipFormatter
      },
      xAxis: axisCommon(t, opt, 'x'),
      yAxis: axisCommon(t, opt, 'y')
    };
    base.yAxis.max = opt.yMax === undefined ? 1.05 : opt.yMax;
    base.xAxis.data = opt.x;
    var n = (opt.x || []).length;
    base.xAxis.axisLabel.interval = n > 12 ? Math.ceil(n / 12) - 1 : 0;

    base.series = (opt.series || []).map(function (s) {
      var color = resolveColor(s.color, t);
      return {
        name: s.name, type: 'line', showSymbol: false, symbol: 'circle', symbolSize: 6,
        step: s.step || false, data: s.y,
        lineStyle: { width: s.width === undefined ? 2.2 : s.width, color: color, type: s.dash ? 'dashed' : 'solid' },
        itemStyle: { color: color },
        areaStyle: s.fill ? { color: color, opacity: 0.1 } : undefined,
        markLine: buildMarkLines(s, opt, t),
        z: s.z === undefined ? 3 : s.z
      };
    });
    if (opt.legend !== false && base.series.length > 1) {
      base.legend = {
        top: 0, right: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10,
        textStyle: { color: t.dim, fontSize: 12 }
      };
    }
    return base;
  }

  function buildMarkLines(s, opt, t) {
    var data = [];
    (s.marks || opt.marks || []).forEach(function (m) {
      var color = resolveColor(m.color, t, 0.18);
      data.push([
        { coord: [m.x, m.y0 === undefined ? 0 : m.y0] },
        {
          coord: [m.x, m.y],
          lineStyle: { color: color, type: 'dashed', width: 1.2, opacity: 0.9 },
          label: {
            show: !!m.text, formatter: m.text || '', position: m.pos || 'insideEndTop',
            rotate: 0, color: color, fontSize: 11, fontFamily: MONO, fontWeight: 600,
            padding: [3, 5], borderRadius: 4,
            backgroundColor: t.surface, borderColor: color, borderWidth: 1
          }
        }
      ]);
    });
    (opt.hLines || []).forEach(function (h) {
      data.push({
        yAxis: h.y,
        lineStyle: { color: resolveColor(h.color, t, 0.18), type: 'dotted', width: 1, opacity: 0.5 },
        label: {
          show: !!h.text, formatter: h.text || '', position: 'insideStartTop',
          color: resolveColor(h.color, t, 0.18), fontSize: 11, rotate: 0
        }
      });
    });
    return { silent: true, symbol: 'none', data: data, animation: false };
  }

  /* --- 数值/对数横轴折线（性能实验图） --- */
  function curveOption(opt, t) {
    var series = [];
    (opt.series || []).forEach(function (s) {
      var color = resolveColor(s.color, t, 0.25);
      var logY = opt.yType === 'log';
      if (s.band) {
        if (logY) {
          /* 对数轴上堆叠面积不可靠，改用上下两条细虚线表示波动范围 */
          series.push({
            name: s.name + '_hi', type: 'line', silent: true, z: 1, symbol: 'none',
            data: s.band.map(function (d) { return [d[0], d[2]]; }),
            lineStyle: { color: color, width: 1, opacity: 0.3, type: 'dotted' }
          });
          series.push({
            name: s.name + '_lo', type: 'line', silent: true, z: 1, symbol: 'none',
            data: s.band.map(function (d) { return [d[0], Math.max(d[1], 1e-4)]; }),
            lineStyle: { color: color, width: 1, opacity: 0.3, type: 'dotted' }
          });
        } else {
          var key = 'band_' + s.name;
          series.push({
            name: key + '_lo', type: 'line', stack: key, silent: true, z: 1,
            symbol: 'none', lineStyle: { opacity: 0 },
            data: s.band.map(function (d) { return [d[0], Math.max(d[1], 0)]; })
          });
          series.push({
            name: key, type: 'line', stack: key, silent: true, z: 1,
            symbol: 'none', lineStyle: { opacity: 0 },
            areaStyle: { color: color, opacity: 0.15 },
            data: s.band.map(function (d) { return [d[0], Math.max(d[2] - d[1], 0)]; })
          });
        }
      }
      if (s.fit && s.fit.length) {
        series.push({
          name: s.name + '_fit', type: 'line', symbol: 'none', silent: true, z: 2,
          data: s.fit,
          lineStyle: { color: color, width: 1, type: 'dashed', opacity: 0.5 }
        });
      }
      series.push({
        name: s.name, type: 'line', z: 3,
        symbol: s.symbol === false ? 'none' : 'circle',
        symbolSize: 5,
        data: s.points,
        lineStyle: { color: color, width: s.width || 2 },
        itemStyle: { color: color }
      });
    });
    var labels = (opt.labels || []).concat(
      (opt.series || []).map(function (s) { return s.label; }).filter(Boolean));
    if (labels.length) {
      series.push({
        type: 'scatter', silent: true, z: 5, symbolSize: 1,
        itemStyle: { opacity: 0 },
        data: labels.map(function (l) {
          return {
            value: [l.x, l.y],
            label: {
              show: true, formatter: l.text, position: l.pos || 'top',
              color: resolveColor(l.color, t, 0.25), fontSize: 11, fontFamily: MONO,
              backgroundColor: t.surface, padding: [2, 4], borderRadius: 3
            }
          };
        })
      });
    }

    var hasLegend = !(opt.legend === false || !opt.series || opt.series.length < 2);
    return {
      animationDuration: 260,
      textStyle: baseText(t),
      grid: { left: 64, right: 28, top: opt.title ? 54 : (hasLegend ? 42 : 28), bottom: 46 },
      title: opt.title ? {
        text: opt.title, left: 0,
        textStyle: { fontSize: 15, fontWeight: 600, color: t.text }
      } : undefined,
      tooltip: {
        trigger: 'axis', confine: true, backgroundColor: t.surface,
        borderColor: t.axis, textStyle: { color: t.text, fontSize: 12, fontFamily: MONO },
        valueFormatter: opt.tooltipFormatter
      },
      legend: (opt.legend === false || !opt.series || opt.series.length < 2) ? undefined : {
        top: 0, right: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10,
        textStyle: { color: t.dim, fontSize: 12 },
        data: (opt.series || []).map(function (s) { return s.name; })
      },
      xAxis: axisCommon(t, opt, 'x'),
      yAxis: axisCommon(t, opt, 'y'),
      series: series
    };
  }

  /* --- 柱状 --- */
  function barOption(opt, t) {
    return {
      animationDuration: 260,
      textStyle: baseText(t),
      grid: { left: 60, right: 28, top: opt.title ? 54 : 28, bottom: 46 },
      title: opt.title ? {
        text: opt.title, left: 0,
        textStyle: { fontSize: 15, fontWeight: 600, color: t.text }
      } : undefined,
      tooltip: {
        trigger: 'axis', confine: true, backgroundColor: t.surface,
        borderColor: t.axis, textStyle: { color: t.text, fontSize: 12, fontFamily: MONO },
        valueFormatter: opt.tooltipFormatter
      },
      legend: opt.series.length > 1 ? {
        top: 0, right: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10,
        textStyle: { color: t.dim, fontSize: 12 }
      } : undefined,
      xAxis: {
        type: 'category', data: opt.categories,
        name: opt.xLabel, nameLocation: 'middle', nameGap: 30,
        nameTextStyle: { color: t.dim, fontSize: 12 },
        axisLine: { lineStyle: { color: t.axis } },
        axisTick: { show: false },
        axisLabel: { color: t.dim, fontSize: 11, fontFamily: MONO }
      },
      yAxis: {
        type: 'value', name: opt.yLabel,
        nameTextStyle: { color: t.dim, fontSize: 12, align: 'right' },
        min: 0, max: opt.yMax,
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: t.dim, fontSize: 11, fontFamily: MONO, formatter: opt.yTickFormatter },
        splitLine: { lineStyle: { color: t.grid } }
      },
      series: opt.series.map(function (s) {
        var color = resolveColor(s.color, t);
        return {
          name: s.name, type: 'bar', barMaxWidth: 20,
          data: s.values,
          itemStyle: { color: color, borderRadius: [3, 3, 0, 0] },
          label: (opt.valueLabels && opt.valueLabels.show) ? {
            show: true, position: 'top', fontSize: 10, color: t.dim, fontFamily: MONO,
            formatter: opt.valueLabels.formatter
          } : undefined
        };
      })
    };
  }

  UI.charts = {
    line: function (host, opt) {
      var it = acquire(host, 'line');
      it.opt = opt;
      it.inst.setOption(lineOption(opt, themeTokens()), true);
      return it.inst;
    },

    curve: function (host, opt) {
      var it = acquire(host, 'curve');
      it.opt = opt;
      it.inst.setOption(curveOption(opt, themeTokens()), true);
      return it.inst;
    },

    bars: function (host, opt) {
      var it = acquire(host, 'bars');
      it.opt = opt;
      it.inst.setOption(barOption(opt, themeTokens()), true);
      return it.inst;
    },

    table: function (host, opt) {
      var rows = opt.rowLabels, cols = opt.colLabels, values = opt.values;
      var flat = [];
      values.forEach(function (r) { r.forEach(function (v) { flat.push(v); }); });
      var lo = Math.min.apply(null, flat), hi = Math.max.apply(null, flat);
      var blues = C.COLORS.blues;

      var html = '<div class="tablewrap"><table class="dtable">';
      html += '<thead><tr><th class="dtable__corner">' + (opt.rowHeader || '') + '</th>';
      cols.forEach(function (c) { html += '<th>' + c + '</th>'; });
      html += '</tr></thead><tbody>';
      rows.forEach(function (r, i) {
        html += '<tr><th class="dtable__row">' + r + '</th>';
        values[i].forEach(function (v, j) {
          var norm = hi > lo ? (v - lo) / (hi - lo) : 0;
          var bg = C.stats.ramp(blues, norm);
          var fg = norm > 0.6 ? '#ffffff' : '#2b2b2b';
          var isMean = j === cols.length - 1 && opt.meanColumn !== false;
          html += '<td style="background:' + bg + ';color:' + fg + '">' +
                  (isMean ? v.toFixed(1) : String(v)) + '</td>';
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

    disposeDetached: function () {
      instances = instances.filter(function (it) {
        if (it.host && it.host.isConnected) return true;
        if (it.inst) { try { it.inst.dispose(); } catch (e) { /* noop */ } }
        return false;
      });
    },

    redrawAll: function () {
      var t = themeTokens();
      instances.forEach(function (it) {
        if (it.inst.isDisposed() || !it.opt) return;
        if (it.kind === 'line') it.inst.setOption(lineOption(it.opt, t), true);
        else if (it.kind === 'curve') it.inst.setOption(curveOption(it.opt, t), true);
        else if (it.kind === 'bars') it.inst.setOption(barOption(it.opt, t), true);
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
