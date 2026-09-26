/* 站点外壳：hash 路由、侧栏、参数面板、主题、状态条 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var doc = global.document;

  /* --- 内联 SVG 图标（不用 emoji 作图标） --- */
  var ICONS = {
    menu: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    sun: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/></svg>',
    moon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/></svg>',
    link: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1"/><path d="M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1"/></svg>',
    chart: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 19V5"/><path d="M4 19h16"/><path d="M7 15l4-5 3 3 5-7"/></svg>',
    info: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></svg>',
    home: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 11l8-7 8 7"/><path d="M6 10v9h12v-9"/></svg>'
  };

  /* --- 导航结构：可视化 / 说明 --- */
  var NAV = [
    { group: '可视化', items: [
      { id: 'char', icon: 'chart', label: '角色池', ready: true },
      { id: 'weapon', icon: 'chart', label: '武器池', ready: true },
      { id: 'joint', icon: 'chart', label: '角色+武器', ready: true },
      { id: 'std', icon: 'chart', label: '常驻池', ready: true },
      { id: 'nstd', icon: 'chart', label: '常驻角色数', ready: true },
      { id: 'radiance', icon: 'chart', label: '捕获明光', ready: true },
      { id: 'multi-gold', icon: 'chart', label: '十连多金', ready: true },
      { id: 'longterm', icon: 'chart', label: '长期欧非', ready: true },
      { id: 'player', icon: 'chart', label: '个人记录', ready: true }
    ] },
    { group: '说明', items: [
      { id: 'about', icon: 'info', label: '模型与误差', ready: true },
      { id: 'algo', icon: 'info', label: '算法', ready: true },
      { id: 'perf', icon: 'info', label: '性能', ready: true }
    ] }
  ];

  var store = {
    get: function (k) {
      try { return global.localStorage.getItem(k); } catch (e) { return null; }
    },
    set: function (k, v) {
      try { global.localStorage.setItem(k, v); } catch (e) { /* file:// 下可能不可用 */ }
    }
  };

  var app = {
    moduleId: null,
    viewId: null,
    params: {},
    pending: null,
    showAdvanced: false
  };
  W.app = app;

  /* --- 路由 --- */
  function parseHash() {
    var raw = global.location.hash.replace(/^#\/?/, '');
    var qi = raw.indexOf('?');
    var path = qi >= 0 ? raw.slice(0, qi) : raw;
    var query = {};
    if (qi >= 0) {
      raw.slice(qi + 1).split('&').forEach(function (kv) {
        if (!kv) return;
        var i = kv.indexOf('=');
        var k = decodeURIComponent(i < 0 ? kv : kv.slice(0, i));
        var v = i < 0 ? '' : decodeURIComponent(kv.slice(i + 1));
        query[k] = v;
      });
    }
    return { segs: path.split('/').filter(Boolean), query: query };
  }

  function buildHash(moduleId, viewId, params) {
    var qs = Object.keys(params).filter(function (k) {
      return params[k] !== undefined && params[k] !== null && params[k] !== '';
    }).map(function (k) {
      var v = typeof params[k] === 'boolean' ? (params[k] ? '1' : '0') : params[k];
      return encodeURIComponent(k) + '=' + encodeURIComponent(v);
    }).join('&');
    var path = moduleId ? moduleId + (viewId ? '/' + viewId : '') : '';
    return '#/' + path + (qs ? '?' + qs : '');
  }

  var suppressHash = false;

  function writeHash(moduleId, viewId, params, replace) {
    var hash = buildHash(moduleId, viewId, params);
    if (global.location.hash === hash) return;
    if (replace) {
      try {
        global.history.replaceState(null, '', hash);
        return;
      } catch (e) { /* file:// 下部分浏览器拒绝 replaceState */ }
      suppressHash = true;
    }
    global.location.hash = hash;
  }

  function coerce(defaults, query) {
    var out = {};
    Object.keys(defaults).forEach(function (k) {
      var d = defaults[k];
      if (!(k in query)) { out[k] = d; return; }
      if (typeof d === 'boolean') out[k] = query[k] === '1' || query[k] === 'true';
      else if (typeof d === 'number') {
        var n = Number(query[k]);
        out[k] = isNaN(n) ? d : n;
      } else out[k] = query[k];
    });
    return out;
  }

  /* --- 渲染 --- */
  function el(tag, cls, html) {
    var node = doc.createElement(tag);
    if (cls) node.className = cls;
    if (html !== undefined) node.innerHTML = html;
    return node;
  }

  function renderNav(activeId) {
    var host = doc.getElementById('navList');
    host.textContent = '';
    NAV.forEach(function (group) {
      host.appendChild(el('p', 'nav__group', group.group));
      group.items.forEach(function (item) {
        var a = el('a', 'nav__item' + (item.id === activeId ? ' is-active' : '') +
                   (item.ready ? '' : ' is-disabled'));
        a.href = '#/' + item.id;
        a.innerHTML = ICONS[item.icon] + '<span>' + item.label + '</span>';
        if (!item.ready) {
          a.setAttribute('aria-disabled', 'true');
          a.onclick = function (e) { e.preventDefault(); showToast('本页尚未实现'); };
        }
        if (item.id === activeId) a.setAttribute('aria-current', 'page');
        host.appendChild(a);
      });
    });
  }

  /* 首页按信息类型分区：小标题 + 该区的框（读数用卡片，入口用平铺块） */
  function homeSection(title, body, plain) {
    var sec = el('section', 'home__sec' + (plain ? ' home__sec--plain' : ''));
    sec.appendChild(el('h2', 'home__h', title));
    sec.appendChild(body);
    return sec;
  }

  function renderHome(stage) {
    renderNav('');
    var page = el('div', 'page');
    page.appendChild(el('header', 'page__head',
      '<h1>原神抽卡概率</h1>' +
      '<p class="page__intro">本工具给出角色池与武器池的抽数分布，' +
      '用于估算抽到目标数量所需的抽数区间，含捕获明光与武器定轨机制。</p>'));

    var stats = el('div', 'cardgrid');
    var C = W.core;

    /* 官方公布的综合概率：角色池出金 1.600%、综合不歪率 55.000%、武器池出金 1.850%。
       1.600% → 62.5 抽/金；不歪率 55.000% → 每 UP 需要 1/(2-0.55) = 1.45 个金。
       无捕获明光时不歪率为 50% → 每 UP 1.5 个金。 */
    var OFFICIAL_PER_GOLD = 1 / 0.016;              /* 62.5 抽 */
    var OFFICIAL_PER_UP = OFFICIAL_PER_GOLD * 1.45; /* 90.625 抽 */
    var OFFICIAL_PER_UP_NO_RAD = OFFICIAL_PER_GOLD * 1.5; /* 93.75 抽 */

    var one = C.stableUpDistribution(1);
    var seven = C.stableUpDistribution(7);
    var modelPerGold = C.stats.expected(C.gold.getGoldPdfs('character', 1)[1]);

    var card1 = el('div', 'stat-card');
    card1.innerHTML =
      '<p class="stat-card__k">抽到 1 个限定</p>' +
      cmpRow(OFFICIAL_PER_UP.toFixed(3), '按官方综合概率', null) +
      cmpRow(one.expected.toFixed(2), '按玩家总结的概率机制', '#/about') +
      '<p class="stat-card__h">不考虑捕获明光时：' +
      OFFICIAL_PER_UP_NO_RAD.toFixed(2) + ' 抽（官方公式）／ ' +
      (modelPerGold * 1.5).toFixed(2) + ' 抽（玩家总结）</p>';
    stats.appendChild(card1);

    [
      ['抽到 7 个限定（满命）', seven.expected.toFixed(1),
       '中位数 ' + seven.quantile(0.5) + ' 抽'],
      ['90% 的玩家满命需要', String(seven.quantile(0.9)),
       '99% 分位 ' + seven.quantile(0.99) + ' 抽']
    ].forEach(function (row) {
      var card = el('div', 'stat-card');
      card.innerHTML = '<p class="stat-card__k">' + row[0] + '</p>' +
        cmpRow(row[1], '按玩家总结的概率机制', '#/about') +
        '<p class="stat-card__h">' + row[2] + '</p>' +
        '<p class="stat-card__note">官方未公示具体概率，无法计算</p>';
      stats.appendChild(card);
    });
    page.appendChild(homeSection('期望抽数', stats));

    var acc = el('section', 'accuracy');
    acc.innerHTML =
      '<p>官方仅公布三项综合概率：角色池出金 1.600%、武器池出金 1.850%、' +
      '角色池综合不歪率 55.000%；逐抽概率未公布。本站的逐抽参数取自社区总结的模型，' +
      '与官方实现存在少量差异（武器池较角色池更明显），结果仅供参考。' +
      '<a class="accuracy__more" href="#/about">误差来源与适用范围 →</a></p>';
    page.appendChild(homeSection('数据准确度', acc, true));

    var entries = el('div', 'cardgrid');
    [
      ['角色池', 'char', '按目标命座、已垫抽数与连歪次数，查看累积概率、幸运扇形与分位点。'],
      ['武器池', 'weapon', '定轨机制下的抽数分布：命定值、大保底与金数分布。'],
      ['角色 + 武器', 'joint', '角色与武器同时规划，给出总抽数的分布与两边的期望占比。'],
      ['常驻池', 'std', '没有 UP 机制，纯出金的抽数分布。'],
      ['常驻角色数', 'nstd', '抽 UP 的过程中会歪出多少常驻五星及其条件抽数分布。'],
      ['捕获明光', 'radiance', '明光触发次数的分布，也可按自己的中／歪序列计算。'],
      ['十连多金', 'multi-gold', '一次十连出现 2–6 个五星的概率与所需十连次数。'],
      ['长期欧非', 'longterm', 'UP 数量增加时平均成本的收敛，含 5.0 前后的机制差异。'],
      ['个人记录', 'player', '把抽卡记录换算成百分位，逐次对照理论分布。']
    ].forEach(function (it) {
      var entry = el('a', 'entry');
      entry.href = '#/' + it[1];
      entry.innerHTML = '<h3>' + it[0] + '</h3><p>' + it[2] + '</p>' +
                        '<span class="entry__go">进入 →</span>';
      entries.appendChild(entry);
    });
    page.appendChild(homeSection('可视化', entries));

    stage.appendChild(page);
  }

  /* 首页对比行：数值在左，口径说明在右下角 */
  function cmpRow(value, tag, href) {
    var tagHtml = href
      ? '<a class="statcmp__tag" href="' + href + '">' + tag + '</a>'
      : '<span class="statcmp__tag">' + tag + '</span>';
    return '<div class="statcmp"><span class="statcmp__v">' + value +
           '<span class="statcmp__u">抽</span></span>' + tagHtml + '</div>';
  }

  function renderPlaceholder(stage, id) {
    renderNav(id);
    var meta = null;
    NAV.forEach(function (g) {
      g.items.forEach(function (it) { if (it.id === id) meta = it; });
    });
    var page = el('div', 'page');
    page.appendChild(el('header', 'page__head',
      '<h1>' + (meta ? meta.label : '页面') + '</h1>' +
      '<p class="page__intro">本页尚未实现。</p>'));
    var card = el('div', 'card empty');
    card.innerHTML = '<p>没有这个页面。<a href="#/">回到首页</a></p>';
    page.appendChild(card);
    stage.appendChild(page);
  }

  /* 默认视图：模块可显式声明 defaultView，未声明时取 views 的第一项
     （导航链接指向 #/<模块>，没有视图段，必须能落回一个确定的视图） */
  function defaultViewOf(mod) {
    return mod.defaultView || Object.keys(mod.views)[0];
  }

  function renderModule(stage, mod, viewId, params) {
    /* 重置、切视图都会重新进这里，必须先清空，否则页面会一层层叠加 */
    W.ui.charts.disposeAll();
    stage.textContent = '';
    renderNav(mod.id);
    var fallback = defaultViewOf(mod);
    var view = mod.views[viewId] || mod.views[fallback];
    app.viewId = view === mod.views[viewId] ? viewId : fallback;

    /* layout: 'doc' 的模块（纯文档）收窄容器，避免全宽卡片里只有左侧半行文字 */
    var page = el('div', 'page' + (mod.layout === 'doc' ? ' page--doc' : ''));
    page.appendChild(el('header', 'page__head',
      '<h1>' + mod.title + '</h1><p class="page__intro">' + mod.intro + '</p>'));

    /* 控件可声明 views：只对列出的视图有意义（如明光的序列输入对次数分布无用） */
    var controls = (mod.controls ? mod.controls(params) : []).filter(function (c) {
      return !c.views || c.views.indexOf(app.viewId) >= 0;
    });
    var hasControls = controls.length > 0;
    var grid = el('div', 'stage-grid' + (hasControls ? '' : ' stage-grid--wide'));
    var colMain = el('div', 'col-main');

    var tabs = el('div', 'viewtabs');
    tabs.setAttribute('role', 'tablist');
    function addTab(vid) {
      var b = el('button', 'viewtabs__item' + (vid === app.viewId ? ' is-on' : ''),
                 mod.views[vid].label);
      b.type = 'button';
      b.setAttribute('role', 'tab');
      b.setAttribute('aria-selected', vid === app.viewId);
      b.onclick = function () {
        if (vid === app.viewId) return;
        app.viewId = vid;
        writeHash(mod.id, vid, app.params, false);
        renderModule(stage, mod, vid, app.params);
        doc.getElementById('stage').focus();
      };
      tabs.appendChild(b);
    }

    /* 低频视图收进「其他」：主标签保持一行，想深挖的再展开 */
    var allViews = Object.keys(mod.views);
    var advanced = allViews.filter(function (v) { return mod.views[v].advanced; });
    var expanded = app.showAdvanced || advanced.indexOf(app.viewId) >= 0;
    allViews.filter(function (v) { return !mod.views[v].advanced; }).forEach(addTab);
    if (advanced.length) {
      if (expanded) {
        advanced.forEach(addTab);
        var less = el('button', 'viewtabs__more', '收起');
        less.type = 'button';
        less.onclick = function () { app.showAdvanced = false; renderModule(stage, mod, app.viewId, app.params); };
        tabs.appendChild(less);
      } else {
        var more = el('button', 'viewtabs__more', '其他 ▾');
        more.type = 'button';
        more.onclick = function () { app.showAdvanced = true; renderModule(stage, mod, app.viewId, app.params); };
        tabs.appendChild(more);
      }
    }
    if (allViews.length > 1) colMain.appendChild(tabs);
    colMain.appendChild(el('div', 'sr-only', mod.title + ' ' + view.label));

    var viewHost = el('section', 'card viewhost');
    var status = el('div', 'statusbar');
    colMain.appendChild(viewHost);
    if (hasControls) colMain.appendChild(status);
    colMain.appendChild(el('p', 'disclaimer',
      '机制参数取自社区总结的模型，结果仅供参考 · <a href="#/about">误差说明</a>'));
    grid.appendChild(colMain);

    if (!hasControls) {
      page.appendChild(grid);
      stage.appendChild(page);
      redraw(mod, viewHost, status);
      return;
    }

    var colParams = el('aside', 'col-params');
    var inspector = el('div', 'card inspector');
    var head = el('div', 'inspector__head');
    head.innerHTML = '<h2>参数</h2>';
    var reset = el('button', 'btn btn--ghost', '重置');
    reset.type = 'button';
    reset.onclick = function () {
      app.params = Object.assign({}, mod.defaults);
      writeHash(mod.id, app.viewId, app.params, true);
      renderModule(stage, mod, app.viewId, app.params);
    };
    head.appendChild(reset);
    inspector.appendChild(head);

    var controlHost = el('div', 'inspector__body');
    app.controlHost = controlHost;
    inspector.appendChild(controlHost);
    var copy = el('button', 'btn btn--block', ICONS.link + '<span>复制当前链接</span>');
    copy.type = 'button';
    copy.onclick = function () { copyLink(copy); };
    inspector.appendChild(copy);
    colParams.appendChild(inspector);
    grid.appendChild(colParams);
    page.appendChild(grid);
    stage.appendChild(page);

    W.ui.controls.build(controlHost, controls, app.params,
      function (key, value, live) {
        app.params[key] = value;
        writeHash(mod.id, app.viewId, app.params, true);
        if (live) { scheduleRedraw(); } else { redraw(mod, viewHost, status); }
      });

    redraw(mod, viewHost, status);
  }

  var redrawTimer = null;
  function scheduleRedraw() {
    global.clearTimeout(redrawTimer);
    redrawTimer = global.setTimeout(function () {
      var mod = W.modules[app.moduleId];
      var host = doc.querySelector('.viewhost');
      var status = doc.querySelector('.statusbar');
      if (mod && host) redraw(mod, host, status);
    }, 60);
  }

  function redraw(mod, viewHost, status) {
    W.ui.charts.disposeDetached();
    viewHost.textContent = '';
    var view = mod.views[app.viewId] || mod.views[defaultViewOf(mod)];
    var t0 = performance.now();
    var ms = function () { return (performance.now() - t0).toFixed(1); };
    try {
      view.render(viewHost, {
        state: app.params,
        charts: W.ui.charts,
        setStatus: function (text, kind) {
          status.textContent = text;
          status.className = 'statusbar' + (kind ? ' statusbar--' + kind : '');
        }
      });
    } catch (e) {
      W.ui.panels.error(viewHost, '本视图无法渲染：' + (e.message || e));
      status.textContent = '参数超出该视图的处理范围';
      status.className = 'statusbar statusbar--warn';
    }
    if (mod.math) W.ui.math.typeset(viewHost);
    W.ui.controls.refresh(app.controlHost, app.params);
    status.setAttribute('data-ms', ms());
  }

  function copyLink(btn) {
    var url = global.location.href;
    var done = function (ok) {
      var old = btn.querySelector('span').textContent;
      btn.querySelector('span').textContent = ok ? '已复制' : '复制失败，请手动复制地址栏';
      global.setTimeout(function () { btn.querySelector('span').textContent = old; }, 1600);
    };
    if (global.navigator.clipboard) {
      global.navigator.clipboard.writeText(url).then(function () { done(true); },
        function () { done(fallbackCopy(url)); });
    } else {
      done(fallbackCopy(url));
    }
  }

  function fallbackCopy(text) {
    var ta = doc.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    doc.body.appendChild(ta);
    ta.select();
    var ok = false;
    try { ok = doc.execCommand('copy'); } catch (e) { ok = false; }
    doc.body.removeChild(ta);
    return ok;
  }

  var toastTimer = null;
  function showToast(msg) {
    var t = doc.getElementById('toast');
    t.textContent = msg;
    t.classList.add('is-on');
    global.clearTimeout(toastTimer);
    toastTimer = global.setTimeout(function () { t.classList.remove('is-on'); }, 1800);
  }

  function route() {
    var r = parseHash();
    var stage = doc.getElementById('stage');
    W.ui.charts.disposeAll();
    stage.textContent = '';

    if (r.segs.length === 0) {
      app.moduleId = null;
      renderHome(stage);
      return;
    }
    var id = r.segs[0];
    var mod = W.modules[id];
    if (!mod) { app.moduleId = null; renderPlaceholder(stage, id); return; }

    app.moduleId = id;
    app.params = coerce(mod.defaults, r.query);
    var viewId = r.segs[1] && mod.views[r.segs[1]] ? r.segs[1] : defaultViewOf(mod);
    app.viewId = viewId;
    renderModule(stage, mod, viewId, app.params);
  }

  /* --- 主题 --- */
  function currentTheme() {
    return doc.documentElement.getAttribute('data-theme') || 'light';
  }

  /* persist 只在用户手动切换时为 true：跟随系统得到的主题不写回，
     否则系统改回亮色后站点会一直停在暗色 */
  function setTheme(mode, persist) {
    doc.documentElement.setAttribute('data-theme', mode);
    if (persist) store.set('wish.theme', mode);
    var btn = doc.getElementById('themeToggle');
    if (btn) {
      btn.innerHTML = mode === 'dark' ? ICONS.sun : ICONS.moon;
      btn.setAttribute('aria-label', mode === 'dark' ? '切换到亮色主题' : '切换到暗色主题');
    }
    W.ui.charts.redrawAll();
  }

  function systemTheme() {
    var prefersDark = global.matchMedia &&
      global.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'dark' : 'light';
  }

  function initTheme() {
    setTheme(store.get('wish.theme') || systemTheme(), false);
    if (global.matchMedia) {
      var mq = global.matchMedia('(prefers-color-scheme: dark)');
      var onChange = function () {
        if (!store.get('wish.theme')) setTheme(systemTheme(), false);
      };
      if (mq.addEventListener) mq.addEventListener('change', onChange);
      else if (mq.addListener) mq.addListener(onChange);
    }
  }

  function initShell() {
    doc.getElementById('themeToggle').innerHTML = ICONS.moon;
    doc.getElementById('themeToggle').onclick = function () {
      setTheme(currentTheme() === 'dark' ? 'light' : 'dark', true);
    };
    var navBtn = doc.getElementById('navToggle');
    var sidenav = doc.getElementById('sidenav');
    var scrim = doc.getElementById('scrim');
    function closeNav() {
      doc.body.classList.remove('nav-open');
      navBtn.setAttribute('aria-expanded', 'false');
    }
    navBtn.innerHTML = ICONS.menu;
    navBtn.onclick = function () {
      var open = doc.body.classList.toggle('nav-open');
      navBtn.setAttribute('aria-expanded', String(open));
    };
    scrim.onclick = closeNav;
    doc.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeNav();
      if (e.key === 't' || e.key === 'T') {
        if (doc.activeElement && /INPUT|TEXTAREA/.test(doc.activeElement.tagName)) return;
        setTheme(currentTheme() === 'dark' ? 'light' : 'dark', true);
      }
    });
  }

  function boot() {
    initTheme();
    initShell();
    route();
    global.addEventListener('hashchange', function () {
      if (suppressHash) { suppressHash = false; return; }
      route();
      doc.getElementById('stage').focus();
    });
  }

  if (doc.readyState === 'loading') {
    doc.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})(typeof globalThis !== 'undefined' ? globalThis : this);
