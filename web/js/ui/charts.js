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

  /* ECharts 的对数刻度从 0 起排（第一个刻度值为 0，落在轴外），
     格式化后会变成「0e+0%」之类压在轴名上，直接丢掉 */
  function logTick(fmt) {
    return function (v) {
      if (!(v > 0)) return '';
      return fmt ? fmt(v) : String(v);
    };
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
        formatter: isLog ? logTick(which === 'x' ? opt.xTickFormatter : opt.yTickFormatter)
                         : (which === 'x' ? opt.xTickFormatter : opt.yTickFormatter)
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
    /* line 一律用类目横轴：抽数是可数的整数，类目轴能保证等距并且标注可落在任意抽数上 */
    base.xAxis.type = 'category';
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

  /* --- 数值/对数横轴折线（性能实验图、扇形、堆叠面积、阶梯） --- */
  function curveOption(opt, t) {
    var series = [];
    var legendNames = [];
    var logY = opt.yType === 'log';

    function pushBand(name, data, color, opacity, z, step, lines, inLegend) {
      var key = 'band_' + name;
      var base = data.map(function (d) { return [d[0], Math.max(d[1], 0)]; });
      var height = data.map(function (d) { return [d[0], Math.max(d[2] - d[1], 0)]; });
      series.push({
        name: key + '_lo', type: 'line', stack: key, silent: true, symbol: 'none',
        step: step || false, z: z === undefined ? 1 : z, tooltip: { show: false },
        lineStyle: { opacity: 0 }, data: base
      });
      series.push({
        name: name, type: 'line', stack: key, silent: true, symbol: 'none',
        step: step || false, z: z === undefined ? 1 : z,
        tooltip: { show: false }, showInLegend: false,
        lineStyle: { opacity: 0 },
        areaStyle: { color: color, opacity: opacity === undefined ? 0.2 : opacity },
        data: height
      });
      if (lines) {
        series.push({
          name: key + '_hi', type: 'line', silent: true, symbol: 'none',
          step: step || false, z: (z === undefined ? 1 : z) + 0.1,
          tooltip: { show: false },
          data: data.map(function (d) { return [d[0], d[2]]; }),
          lineStyle: { color: color, width: 1, opacity: 0.55, type: 'dashed' }
        });
      }
      if (inLegend !== false) legendNames.push(name);
    }

    /* 1. 显式区间带：opt.bands（由外到内依次压栈，内层后画） */
    (opt.bands || []).forEach(function (b, i) {
      pushBand(b.name || ('band' + i), b.data, resolveColor(b.color, t, 0.2),
               b.opacity, b.z, b.step, b.lines, b.legend);
    });

    /* 2. 堆叠面积：opt.stack（自下而上） */
    (opt.stack || []).forEach(function (s) {
      var color = resolveColor(s.color, t, 0.2);
      series.push({
        name: s.name, type: 'line', stack: opt.stackKey || 'total',
        symbol: 'none', z: 1, tooltip: { show: false },
        data: s.points,
        lineStyle: { opacity: 0 },
        areaStyle: { color: color, opacity: s.opacity === undefined ? 0.75 : s.opacity }
      });
      legendNames.push(s.name);
    });

    /* 3. 常规折线 */
    (opt.series || []).forEach(function (s) {
      var color = resolveColor(s.color, t, 0.25);
      if (s.band) {
        if (logY) {
          /* 对数轴上堆叠面积不可靠，改用上下两条细虚线表示波动范围 */
          series.push({
            name: s.name + '_hi', type: 'line', silent: true, z: 1, symbol: 'none',
            tooltip: { show: false },
            data: s.band.map(function (d) { return [d[0], d[2]]; }),
            lineStyle: { color: color, width: 1, opacity: 0.3, type: 'dotted' }
          });
          series.push({
            name: s.name + '_lo', type: 'line', silent: true, z: 1, symbol: 'none',
            tooltip: { show: false },
            data: s.band.map(function (d) { return [d[0], Math.max(d[1], 1e-4)]; }),
            lineStyle: { color: color, width: 1, opacity: 0.3, type: 'dotted' }
          });
        } else {
          pushBand(s.name + '_band', s.band.map(function (d) { return d; }),
                   color, 0.15, 1, false, false, false);
        }
      }
      if (s.fit && s.fit.length) {
        series.push({
          name: s.name + '_fit', type: 'line', symbol: 'none', silent: true, z: 2,
          tooltip: { show: false },
          data: s.fit,
          lineStyle: { color: color, width: 1, type: 'dashed', opacity: 0.5 }
        });
      }
      series.push({
        name: s.name, type: 'line',
        z: s.z === undefined ? 3 : s.z,
        step: s.step || false,
        symbol: s.symbol === false ? 'none' : 'circle',
        symbolSize: s.symbolSize || 5,
        data: s.points,
        lineStyle: { color: color, width: s.width === undefined ? 2 : s.width, type: s.dash ? 'dashed' : 'solid' },
        itemStyle: { color: color }
      });
      legendNames.push(s.name);
    });

    /* 4. 标注与参考线 */
    var labels = (opt.labels || []).concat(
      (opt.series || []).map(function (s) { return s.label; }).filter(Boolean));
    if (labels.length) {
      series.push({
        type: 'scatter', silent: true, z: 5, symbolSize: 1,
        itemStyle: { opacity: 0 },
        tooltip: { show: false },
        data: labels.map(function (l) {
          return {
            value: [l.x, l.y],
            label: {
              show: true, formatter: l.text, position: l.pos || 'top',
              color: resolveColor(l.color, t, 0.25), fontSize: l.size || 11,
              fontFamily: MONO, fontWeight: l.weight || 'normal',
              backgroundColor: t.surface, padding: [2, 4], borderRadius: 3
            }
          };
        })
      });
    }

    var markData = [];
    (opt.vLines || []).forEach(function (v) {
      var color = resolveColor(v.color, t, 0.2);
      markData.push([
        { coord: [v.x, v.y0 === undefined ? 0 : v.y0] },
        { coord: [v.x, v.y1], lineStyle: { color: color, type: 'dotted', width: 1, opacity: 0.55 },
          label: v.text ? {
            show: true, formatter: v.text, position: 'insideEndTop',
            color: color, fontSize: 10, fontFamily: MONO,
            backgroundColor: t.surface, padding: [2, 4], borderRadius: 3
          } : { show: false } }
      ]);
    });
    (opt.hLines || []).forEach(function (h) {
      markData.push({
        yAxis: h.y,
        lineStyle: {
          color: resolveColor(h.color, t, 0.2),
          type: h.dash === false ? 'solid' : 'dashed', width: h.width || 1.2, opacity: 0.7
        },
        label: {
          show: !!h.text, formatter: h.text || '', position: h.pos || 'insideEndTop',
          color: resolveColor(h.color, t, 0.2), fontSize: 11, fontFamily: MONO,
          backgroundColor: t.surface, padding: [2, 4], borderRadius: 3
        }
      });
    });
    if (markData.length) {
      series.push({
        name: '__marks', type: 'line', silent: true, symbol: 'none', data: [],
        tooltip: { show: false }, showInLegend: false,
        markLine: { silent: true, symbol: 'none', animation: false, data: markData }
      });
    }

    var names = legendNames.filter(function (n, i) { return legendNames.indexOf(n) === i; });
    var showLegend = opt.legend !== false && names.length > 1;
    return {
      animationDuration: 260,
      textStyle: baseText(t),
      grid: { left: 64, right: 28, top: opt.title ? 54 : (showLegend ? 42 : 28), bottom: 46 },
      title: opt.title ? {
        text: opt.title, left: 0,
        textStyle: { fontSize: 15, fontWeight: 600, color: t.text }
      } : undefined,
      tooltip: {
        trigger: 'axis', confine: true, backgroundColor: t.surface,
        borderColor: t.axis, textStyle: { color: t.text, fontSize: 12, fontFamily: MONO },
        /* 对数轴的刻度值是浮点，默认表头会印出 13.0000000000；交给模块自己排版 */
        formatter: opt.tooltipHeader ? function (params) {
          var list = params instanceof Array ? params : [params];
          var rows = list.map(function (p) {
            /* 折线数据的 value 是 [x, y]，取末位还原成读数 */
            var raw = p.value instanceof Array ? p.value[p.value.length - 1] : p.value;
            var v = opt.tooltipFormatter ? opt.tooltipFormatter(raw) : raw;
            return '<div style="display:flex;justify-content:space-between;gap:16px">' +
                   '<span>' + p.marker + ' ' + p.seriesName + '</span><b>' + v + '</b></div>';
          }).join('');
          return '<div style="margin-bottom:4px">' +
                 opt.tooltipHeader(list[0].axisValue) + '</div>' + rows;
        } : undefined,
        valueFormatter: opt.tooltipFormatter
      },
      legend: showLegend ? {
        top: 0, right: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10,
        textStyle: { color: t.dim, fontSize: 12 }, data: names
      } : undefined,
      xAxis: axisCommon(t, opt, 'x'),
      yAxis: axisCommon(t, opt, 'y'),
      series: series
    };
  }

  /* --- 类目横轴的区间图：扇形带、堆叠面积、阶梯
   * ECharts 的面积堆叠只在类目轴上生效，因此横轴统一转成类目（标签仍显示原始抽数）。
   * opt = { x, regions:[{name,lo,hi,color,opacity,step}], stack:[{name,y,color,opacity}],
   *         lines:[{name,y,color,width,dash,step,symbol,labels:{...}}], labels, vLines, hLines }
   */
  function regionsOption(opt, t) {
    var x = opt.x || [];
    var cats = x.map(function (v) { return String(v); });
    var series = [], legendNames = [];
    /* 自定义 tooltip 时不给系列屏蔽：轴触发的浮层需要至少一条系列参与，否则整块不显示 */
    function mute() { return opt.tooltipHtml ? {} : { show: false }; }

    (opt.regions || []).forEach(function (rg) {
      var key = 'rg' + series.length;
      var color = resolveColor(rg.color, t, 0.2);
      series.push({
        name: key + '_lo', type: 'line', stack: key, silent: true, symbol: 'none',
        step: rg.step || false, tooltip: mute(),
        lineStyle: { opacity: 0 }, data: rg.lo
      });
      series.push({
        name: rg.name || key, type: 'line', stack: key, silent: true,
        symbol: 'none', step: rg.step || false, tooltip: mute(),
        showInLegend: false,
        lineStyle: { opacity: 0, color: color },
        itemStyle: { color: color },
        areaStyle: { color: color, opacity: rg.opacity === undefined ? 0.25 : rg.opacity },
        data: rg.hi.map(function (v, i) { return Math.max(v - rg.lo[i], 0); })
      });
      if (rg.name) legendNames.push(rg.name);
    });

    (opt.stack || []).forEach(function (st) {
      var color = resolveColor(st.color, t, 0.2);
      series.push({
        name: st.name, type: 'line', stack: 'stackTotal', symbol: 'none',
        tooltip: mute(),
        lineStyle: { opacity: 0, color: color },
        itemStyle: { color: color },
        areaStyle: { color: color, opacity: st.opacity === undefined ? 0.85 : st.opacity },
        data: st.y
      });
      legendNames.push(st.name);
    });

    (opt.lines || []).forEach(function (ln) {
      var color = resolveColor(ln.color, t, 0.25);
      var alpha = ln.opacity === undefined ? 1 : ln.opacity;
      series.push({
        name: ln.name, type: 'line',
        symbol: ln.symbol === false ? 'none' : 'circle',
        symbolSize: ln.symbolSize || 5,
        step: ln.step || false,
        data: ln.y,
        lineStyle: {
          color: color, width: ln.width === undefined ? 2 : ln.width,
          type: ln.dash ? 'dashed' : 'solid', opacity: alpha
        },
        itemStyle: { color: color, opacity: alpha },
        label: ln.labels ? {
          show: true, position: ln.labels.pos || 'top', fontSize: 10,
          fontFamily: MONO, fontWeight: ln.labels.weight || 'normal',
          color: color, formatter: ln.labels.formatter
        } : undefined
      });
      if (ln.name) legendNames.push(ln.name);
    });

    (opt.points || []).forEach(function (pt) {
      var color = resolveColor(pt.color, t, 0.25);
      series.push({
        name: pt.name, type: 'scatter', z: 6, silent: true,
        symbol: pt.symbol || 'rect', symbolSize: pt.symbolSize || [24, 2],
        data: pt.data,
        itemStyle: { color: color },
        label: pt.labels ? {
          show: true, position: pt.labels.pos || 'top', fontSize: 9,
          fontFamily: MONO, color: color, formatter: pt.labels.formatter,
          backgroundColor: t.surface, padding: [1, 3], borderRadius: 3
        } : undefined
      });
      if (pt.name) legendNames.push(pt.name);
    });

    if (opt.labels && opt.labels.length) {
      /* 符号本身用透明色隐藏：itemStyle.opacity 会被标注文字继承，把字也一起抹掉 */
      series.push({
        type: 'scatter', silent: true, z: 7, symbolSize: 1,
        itemStyle: { color: 'transparent', borderWidth: 0 },
        tooltip: { show: false },
        data: opt.labels.map(function (l) {
          /* bg:false 的标注不铺底色（密集的参考读数铺底色会互相盖住） */
          return {
            value: [l.i, l.y],
            label: {
              show: true, formatter: l.text, position: l.pos || 'top',
              color: resolveColor(l.color, t, 0.25), fontSize: l.size || 11,
              fontFamily: MONO, fontWeight: l.weight || 'normal',
              backgroundColor: l.bg === false ? 'transparent' : t.surface,
              padding: l.bg === false ? 0 : [2, 4], borderRadius: 3
            }
          };
        })
      });
    }

    var markData = [];
    (opt.vLines || []).forEach(function (v) {
      var color = resolveColor(v.color, t, 0.2);
      markData.push([
        { coord: [v.i, v.y0 === undefined ? 0 : v.y0] },
        {
          coord: [v.i, v.y1],
          lineStyle: { color: color, type: 'dotted', width: 1, opacity: 0.6 },
          label: v.text ? {
            show: true, formatter: v.text, position: 'insideEndTop', rotate: 0,
            color: color, fontSize: 10, fontFamily: MONO,
            backgroundColor: t.surface, padding: [2, 4], borderRadius: 3
          } : { show: false }
        }
      ]);
    });
    (opt.hLines || []).forEach(function (h) {
      markData.push({
        yAxis: h.y,
        lineStyle: {
          color: resolveColor(h.color, t, 0.2),
          type: h.dash === false ? 'solid' : 'dashed', width: h.width || 1.2, opacity: 0.7
        },
        label: {
          show: !!h.text, formatter: h.text || '', position: h.pos || 'insideEndTop',
          color: resolveColor(h.color, t, 0.2), fontSize: 11, fontFamily: MONO,
          backgroundColor: t.surface, padding: [2, 4], borderRadius: 3
        }
      });
    });
    if (markData.length) {
      series.push({
        name: '__marks', type: 'line', silent: true, symbol: 'none', data: [],
        tooltip: { show: false }, showInLegend: false,
        markLine: { silent: true, symbol: 'none', animation: false, data: markData }
      });
    }

    var names = legendNames.filter(function (n, i) { return legendNames.indexOf(n) === i; });
    var showLegend = opt.legend !== false && names.length > 1;
    var n = cats.length;
    return {
      animationDuration: 260,
      textStyle: baseText(t),
      grid: { left: 64, right: 28, top: opt.title ? 54 : (showLegend ? 42 : 24), bottom: 46 },
      title: opt.title ? {
        text: opt.title, left: 0,
        textStyle: { fontSize: 15, fontWeight: 600, color: t.text }
      } : undefined,
      tooltip: {
        trigger: 'axis', confine: true, backgroundColor: t.surface,
        borderColor: t.axis, textStyle: { color: t.text, fontSize: 12, fontFamily: MONO },
        /* tooltipHtml(dataIndex)：区间图的读数无法由单条系列表达，交给模块拼装 */
        formatter: opt.tooltipHtml
          ? function (params) {
              var list = params instanceof Array ? params : [params];
              return opt.tooltipHtml(list[0].dataIndex);
            }
          : undefined,
        valueFormatter: opt.tooltipFormatter
      },
      legend: showLegend ? {
        top: 0, right: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10,
        textStyle: { color: t.dim, fontSize: 12 }, data: names
      } : undefined,
      xAxis: {
        type: 'category', data: cats, boundaryGap: false,
        name: opt.xLabel, nameLocation: 'middle', nameGap: 30,
        nameTextStyle: { color: t.dim, fontSize: 12 },
        axisLine: { lineStyle: { color: t.axis } },
        axisTick: { show: false },
        axisLabel: {
          color: t.dim, fontSize: 11, fontFamily: MONO, hideOverlap: true,
          interval: n > 14 ? Math.ceil(n / 12) - 1 : 0
        }
      },
      yAxis: {
        type: 'value', name: opt.yLabel,
        nameLocation: 'middle', nameGap: 44,
        nameTextStyle: { color: t.dim, fontSize: 12 },
        min: opt.yMin, max: opt.yMax, interval: opt.yInterval,
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: {
          color: t.dim, fontSize: 11, fontFamily: MONO, formatter: opt.yTickFormatter
        },
        splitLine: { lineStyle: { color: t.grid } }
      },
      series: series
    };
  }

  /* --- 柱状 --- */
  function barOption(opt, t) {
    var hasLegend = !(opt.legend === false ||
                      (opt.series.length + (opt.overlays || []).length) < 2);
    return {
      animationDuration: 260,
      textStyle: baseText(t),
      grid: { left: 60, right: 28, top: opt.title ? 54 : (hasLegend ? 42 : 28), bottom: 46 },
      title: opt.title ? {
        text: opt.title, left: 0,
        textStyle: { fontSize: 15, fontWeight: 600, color: t.text }
      } : undefined,
      tooltip: {
        trigger: 'axis', confine: true, backgroundColor: t.surface,
        borderColor: t.axis, textStyle: { color: t.text, fontSize: 12, fontFamily: MONO },
        /* tooltipHtml(dataIndex)：堆叠柱的读数要跨系列排序、截断，交给模块拼装 */
        formatter: opt.tooltipHtml
          ? function (params) {
              var list = params instanceof Array ? params : [params];
              return opt.tooltipHtml(list[0].dataIndex);
            }
          : undefined,
        valueFormatter: opt.tooltipHtml ? undefined : opt.tooltipFormatter
      },
      legend: hasLegend ? {
        top: 0, right: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10,
        textStyle: { color: t.dim, fontSize: 12 },
        data: opt.series.map(function (s) { return s.name; })
          .concat((opt.overlays || []).filter(function (o) { return o.name; })
            .map(function (o) { return o.name; }))
      } : undefined,
      xAxis: {
        type: 'category', data: opt.categories,
        name: opt.xLabel, nameLocation: 'middle', nameGap: 30,
        nameTextStyle: { color: t.dim, fontSize: 12 },
        axisLine: { lineStyle: { color: t.axis } },
        axisTick: { show: false },
        axisLabel: {
          color: t.dim, fontSize: 11, fontFamily: MONO, hideOverlap: true,
          interval: opt.categoryInterval === undefined ? 'auto' : opt.categoryInterval,
          formatter: opt.xTickFormatter
        }
      },
      yAxis: {
        type: opt.yType === 'log' ? 'log' : 'value', logBase: 10,
        name: opt.yLabel,
        nameTextStyle: { color: t.dim, fontSize: 12, align: 'right' },
        min: opt.yType === 'log' ? opt.yMin : 0, max: opt.yMax,
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: t.dim, fontSize: 11, fontFamily: MONO, formatter: opt.yTickFormatter },
        splitLine: { lineStyle: { color: t.grid } }
      },
      series: opt.series.map(function (s) {
        var color = resolveColor(s.color, t);
        var fill = s.gradient
          ? new global.echarts.graphic.LinearGradient(0, 1, 0, 0, [
              { offset: 0, color: s.gradient[0] }, { offset: 1, color: s.gradient[1] }])
          : color;
        return {
          name: s.name, type: 'bar',
          stack: s.stack,
          barMaxWidth: s.maxWidth || 20,
          barGap: s.gap,
          z: 2,
          data: (s.colors || s.values),
          itemStyle: {
            color: s.colors
              ? function (p) { return s.colors[p.dataIndex]; }
              : fill,
            /* 堆叠柱不加圆角，改用 1px 底色描边把相邻段分开 */
            borderRadius: (s.stack || s.gradient) ? 0 : [3, 3, 0, 0],
            borderColor: s.stack ? (s.borderColor || t.surface) : s.borderColor,
            borderWidth: s.stack ? (s.borderWidth === undefined ? 1 : s.borderWidth)
                                 : s.borderWidth
          },
          label: (opt.valueLabels && opt.valueLabels.show) ? {
            show: true, position: s.labelPos || 'top', fontSize: 10,
            color: t.dim, fontFamily: MONO, formatter: opt.valueLabels.formatter
          } : undefined
        };
      }).concat((opt.overlays || []).map(function (o) {
        var color = resolveColor(o.color, t);
        if (o.type === 'scatter') {
          return {
            name: o.name, type: 'scatter', z: 5, symbol: o.symbol || 'rect',
            symbolSize: o.symbolSize || [26, 2],
            data: o.data,
            itemStyle: { color: color, opacity: o.opacity === undefined ? 1 : o.opacity },
            label: o.label ? {
              show: true, position: o.label.pos || 'top', formatter: o.label.formatter,
              fontSize: 9, fontFamily: MONO, color: color,
              backgroundColor: t.surface, padding: [1, 3], borderRadius: 3
            } : undefined
          };
        }
        return {
          name: o.name, type: 'line', z: 4, symbol: o.symbol === false ? 'none' : 'circle',
          symbolSize: o.symbolSize || 5, smooth: false,
          data: o.data,
          /* line: false —— 只要标注不要折线（符号用透明色隐去，标注文字另给颜色） */
          lineStyle: o.line === false ? { opacity: 0 }
                   : { color: color, width: o.width || 1.6, type: o.dash ? 'dashed' : 'solid' },
          itemStyle: { color: color },
          label: o.label ? {
            show: true, position: o.label.pos || 'top', formatter: o.label.formatter,
            fontSize: 10, fontFamily: MONO,
            color: o.label.color ? resolveColor(o.label.color, t) : color
          } : undefined
        };
      }))
    };
  }

  function optionFor(kind, opt, t) {
    if (kind === 'curve') return curveOption(opt, t);
    if (kind === 'regions') return regionsOption(opt, t);
    if (kind === 'bars') return barOption(opt, t);
    return lineOption(opt, t);
  }

  function draw(host, kind, opt) {
    var it = acquire(host, kind);
    it.opt = opt;
    it.inst.setOption(optionFor(kind, opt, themeTokens()), true);
    return it.inst;
  }

  UI.charts = {
    line: function (host, opt) { return draw(host, 'line', opt); },
    curve: function (host, opt) { return draw(host, 'curve', opt); },
    bars: function (host, opt) { return draw(host, 'bars', opt); },

    regions: function (host, opt) { return draw(host, 'regions', opt); },

    table: function (host, opt) {
      var rows = opt.rowLabels, cols = opt.colLabels, values = opt.values;
      var flat = [];
      values.forEach(function (r) { r.forEach(function (v) { flat.push(v); }); });
      var lo = Math.min.apply(null, flat), hi = Math.max.apply(null, flat);
      var blues = C.COLORS.blues;
      var shade = opt.shade !== false;

      var html = '<div class="tablewrap"><table class="dtable' +
                 (shade ? '' : ' dtable--plain') + '">';
      html += '<thead><tr><th class="dtable__corner">' + (opt.rowHeader || '') + '</th>';
      cols.forEach(function (c) { html += '<th>' + c + '</th>'; });
      html += '</tr></thead><tbody>';
      rows.forEach(function (r, i) {
        html += '<tr><th class="dtable__row">' + r + '</th>';
        values[i].forEach(function (v, j) {
          var norm = hi > lo ? (v - lo) / (hi - lo) : 0;
          var style = '';
          var fg = '';
          if (shade) {
            style = 'background:' + C.stats.ramp(blues, norm) + ';';
            fg = 'color:' + (norm > 0.6 ? '#ffffff' : '#2b2b2b') + ';';
          }
          var isMean = j === cols.length - 1 && opt.meanColumn === true;
          var text = opt.format ? opt.format(v, j, i)
                                : (isMean ? v.toFixed(1) : String(v));
          html += '<td style="' + style + fg + '">' + text + '</td>';
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
        else if (it.kind === 'regions') it.inst.setOption(regionsOption(it.opt, t), true);
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
