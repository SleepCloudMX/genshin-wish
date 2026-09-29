/* 站点外壳：hash 路由、侧栏、参数面板、主题、状态条 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var doc = global.document;

  /* --- 内联 SVG 图标（不用 emoji 作图标） --- */
  function icon(paths, size) {
    return '<svg viewBox="0 0 24 24" width="' + (size || 18) + '" height="' + (size || 18) +
           '" fill="none" stroke="currentColor" stroke-width="1.8" ' +
           'stroke-linecap="round" stroke-linejoin="round">' + paths + '</svg>';
  }

  var ICONS = {
    menu: icon('<path d="M4 7h16M4 12h16M4 17h16"/>'),
    sun: icon('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/>'),
    moon: icon('<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/>'),

    /* 导航图标：一页一个，取该页计算对象的形状——
       人物（角色）／剑（武器）／人物+剑（两者合并）／一颗星（常驻池的"金"）／
       人物+星（常驻五星角色）／闪电（明光触发）／三颗星（一次十连里的多金）／
       趋势线（长期收敛）／时钟（历史记录）；
       说明组：靶心（误差）／芯片（算法）／仪表（性能）
       星用五角轮廓，细碎图案（点阵、圆内星）在 18px 下会糊成一团 */
    user: icon('<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>'),
    sword: icon('<path d="M14.5 17.5 3 6V3h3l11.5 11.5"/><path d="M13 19l6-6"/><path d="M16 16l4 4"/><path d="M19 21l2-2"/>'),
    pair: icon('<circle cx="9" cy="7.5" r="3.2"/><path d="M3.8 19.8a5.2 5.2 0 0 1 10.4 0"/><path d="M20.6 3.6 14.4 9.8"/><path d="m13.1 8.5 2.6 2.6"/>'),
    star: icon('<path d="M12 2.8 14.29 8.84 20.75 9.16 15.71 13.21 17.41 19.44 12 15.9 6.59 19.44 8.29 13.21 3.25 9.16 9.71 8.84Z"/>'),
    userStar: icon('<circle cx="9.4" cy="8.6" r="3.4"/><path d="M3.5 20.4a5.9 5.9 0 0 1 11.8 0"/><path d="M18.4 3.6 19.4 6.22 22.2 6.36 20.02 8.13 20.75 10.84 18.4 9.3 16.05 10.84 16.78 8.13 14.6 6.36 17.4 6.22Z"/>'),
    bolt: icon('<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8Z"/>'),
    /* 三个金（一次十连里的多金） */
    trio: icon('<path d="M4.2 7.8 5.24 10.57 8.19 10.7 5.88 12.55 6.67 15.4 4.2 13.76 1.73 15.4 2.52 12.55 0.21 10.7 3.16 10.57Z"/>' +
               '<path d="M12 7.8 13.04 10.57 15.99 10.7 13.68 12.55 14.47 15.4 12 13.76 9.53 15.4 10.32 12.55 8.01 10.7 10.96 10.57Z"/>' +
               '<path d="M19.8 7.8 20.84 10.57 23.79 10.7 21.48 12.55 22.27 15.4 19.8 13.76 17.33 15.4 18.12 12.55 15.81 10.7 18.76 10.57Z"/>'),
    trend: icon('<path d="M16 17h6v-6"/><path d="m22 17-8.5-8.5-5 5L2 7"/>'),
    history: icon('<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>'),
    target: icon('<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>'),
    cpu: icon('<rect width="16" height="16" x="4" y="4" rx="2"/><rect width="6" height="6" x="9" y="9" rx="1"/><path d="M15 2v2M15 20v2M2 15h2M2 9h2M20 15h2M20 9h2M9 2v2M9 20v2"/>'),
    gauge: icon('<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>'),
    home: icon('<path d="M4 11l8-7 8 7"/><path d="M6 10v9h12v-9"/>')
  };

  /* --- 导航结构：可视化 / 说明 --- */
  var NAV = [
    /* 首页不归组：它是概览与入口，不是某张图，也不属于「说明」 */
    { group: '', items: [
      { id: '', icon: 'home', label: '首页', ready: true }
    ] },
    { group: '可视化', items: [
      { id: 'char', icon: 'user', label: '角色池', ready: true },
      { id: 'weapon', icon: 'sword', label: '武器池', ready: true },
      { id: 'joint', icon: 'pair', label: '角色+武器', ready: true },
      { id: 'std', icon: 'star', label: '常驻池', ready: true },
      { id: 'nstd', icon: 'userStar', label: '常驻角色数', ready: true },
      { id: 'radiance', icon: 'bolt', label: '捕获明光', ready: true },
      { id: 'multi-gold', icon: 'trio', label: '十连多金', ready: true },
      { id: 'longterm', icon: 'trend', label: '长期欧非', ready: true },
      { id: 'player', icon: 'history', label: '个人记录', ready: true }
    ] },
    { group: '说明', items: [
      { id: 'about', icon: 'target', label: '机制误差', ready: true },
      { id: 'algo', icon: 'cpu', label: '算法介绍', ready: true },
      { id: 'perf', icon: 'gauge', label: '算法性能', ready: true }
    ] }
  ];

  /* 页面 id → 该页在导航里的图标（首页入口复用同一套） */
  function navIcon(id) {
    var hit = '';
    NAV.forEach(function (g) {
      g.items.forEach(function (it) { if (it.id === id) hit = it.icon; });
    });
    return ICONS[hit] || '';
  }

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
      if (group.group) host.appendChild(el('p', 'nav__group', group.group));
      group.items.forEach(function (item) {
        var a = el('a', 'nav__item' + (item.id === activeId ? ' is-active' : '') +
                   (item.ready ? '' : ' is-disabled'));
        a.href = '#/' + item.id;
        a.innerHTML = ICONS[item.icon] + '<span>' + item.label + '</span>';
        if (!item.ready) {
          a.setAttribute('aria-disabled', 'true');
          a.onclick = function (e) { e.preventDefault(); W.ui.panels.toast('本页尚未实现'); };
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

    /* 说明紧接导语，与正文同为无框文字；读数与入口再各自成区 */
    var acc = el('section', 'accuracy');
    acc.innerHTML =
      '<p>官方仅公示三项综合概率：角色池出金 1.600%、武器池出金 1.850%、' +
      '角色池不歪 55.000%；逐抽概率和捕获明光具体机制未公布。本站的逐抽参数取自社区总结的模型，' +
      '与官方实现存在少量差异，以官方数据为准，结果仅供参考。除舍入误差（可忽略），' +
      '本站的唯一误差为模型误差，非蒙特卡洛、无方法误差。' +
      '<a class="accuracy__more" href="#/about">误差来源与适用范围 →</a></p>';
    page.appendChild(homeSection('数据准确度', acc, true));

    var stats = el('div', 'cardgrid');
    var C = W.core;

    /* 官方公布的综合概率：角色池出金 1.600%、综合不歪率 55.000%、武器池出金 1.850%。
       1.600% → 62.5 抽/金；不歪率 55.000% → 每 UP 需要 1/(2-0.55) = 1.45 个金。
       武器池每金 37.5% 命中定轨目标，未中则命定值填满、下一金必中 → 每个目标 1.625 个金。 */
    var OFFICIAL_PER_GOLD = 1 / 0.016;              /* 62.5 抽 */
    var OFFICIAL_PER_UP = OFFICIAL_PER_GOLD * 1.45; /* 90.625 抽 */
    var OFFICIAL_PER_UP_NO_RAD = OFFICIAL_PER_GOLD * 1.5; /* 93.75 抽 */
    var OFFICIAL_WEAPON_UP = (1 / 0.0185) * 1.625;  /* 87.838 抽 */

    var one = C.stableUpDistribution(1);
    var seven = C.stableUpDistribution(7);
    var modelPerGold = C.stats.expected(C.gold.getGoldPdfs('character', 1)[1]);
    var weapon1 = C.weaponUpDistribution(C.makeWeaponState({}), 1);
    var weapon5 = C.weaponUpDistribution(C.makeWeaponState({}), 5);

    /* 官方行只有综合概率，给不出分布，故分位数一律「未知」；悬停说明为什么 */
    var NO_MECH = '官方未公示具体概率机制，无法计算。';
    function unknown() {
      return { v: '未知', plain: true, box: { tex: NO_MECH, math: false } };
    }
    var MODEL = '（按<a href="#/about">玩家总结概率机制</a>）';

    /* 分位数（50% / 90% / 99%） */
    function quantiles(d) {
      return [0.5, 0.9, 0.99].map(function (a) {
        return { v: String(d.quantile(a)) };
      });
    }
    /* tex 有值时该格带推导悬浮，没有就是普通读数 */
    function cell(v, tex, code) {
      return tex ? { v: v, box: { tex: tex, code: code } } : { v: v };
    }
    /* 期望一律 5 位有效数字：既保住 90.625 这类精确值，也不再暗示精确到千分之一抽 */
    function sig5(v) { return String(Number(v.toPrecision(5))); }

    /* 「官方公示」两行的推导：都只用官方数据（角色池 1.600% / 55.000%，武器池 1.850% / 37.5% 命中） */
    var OFFICIAL_UP_TEX = '综合不歪率 55.000% 已计入大保底：每个 UP 平均消耗 ' +
      '\\(\\frac{1}{2-55.000\\%}=1.45\\) 个金，单金 ' +
      '\\(\\frac{1}{1.600\\%}=62.5\\) 抽，于是 ' +
      '\\(1.45\\times62.5=90.625\\) 抽。';
    var OFFICIAL_WEAPON_TEX = '综合出金率 1.850% → 单金 \\(\\frac{1}{1.850\\%}=54.054\\) 抽；' +
      '每金命中定轨目标的概率 37.5%，未中使命定值填满、下一金必中，' +
      '故每个目标平均 \\(1+62.5\\%=1.625\\) 个金：' +
      '\\(54.054\\times1.625=87.838\\) 抽。';

    /* 「玩家总结」两行的推导：单金期望按软保底逐抽概率求生存和 */
    var PITY_CHAR = '$$p_i=\\begin{cases}0.6\\%, & i\\le73,\\\\ ' +
      '0.6\\%+6\\%(i-73), & 74\\le i\\le89,\\\\ 100\\%, & i=90.\\end{cases}$$';
    var PITY_WEAPON = '$$p_i=\\begin{cases}0.7\\%, & i\\le62,\\\\ ' +
      '0.7\\%+7\\%(i-62), & 63\\le i\\le73,\\\\ ' +
      '77.7\\%+3.5\\%(i-73), & 74\\le i\\le79,\\\\ 100\\%, & i=80.\\end{cases}$$';
    /* 悬浮里的推导：为什么单金期望是「仍未出金」的连乘求和 */
    var SUM_TEX = '记 \\(T\\) 为出金所需抽数。\\(T=\\sum_{n\\ge0}\\mathbf 1\\{T>n\\}\\)（数一遍 \\(n\\lt T\\) 的个数），' +
      '取期望得 \\(E[T]=\\sum_{n\\ge0}P(T>n)\\)；\\(\\{T>n\\}\\) 就是前 \\(n\\) 抽都没出金：' +
      '$$E=\\sum_{n\\ge0}\\prod_{i\\le n}(1-p_i)=';
    /* 代码只算「单金期望」那一项（与页面上的乘法分开），免得末位对不上 */
    function goldCode(pLine, comment) {
      return [
        pLine, 's, e = 1.0, 0.0', 'for pi in p:',
        '    e += s          # 期望 = Σ P(第 n 抽仍未出金)', '    s *= 1 - pi',
        'print(round(e, 6))  # ' + comment
      ].join('\n');
    }
    var CHAR_GOLD_CODE = goldCode(
      'p = [0.006] * 73 + [0.006 + 0.06*(i - 73) for i in range(74, 90)] + [1.]',
      '62.297332');
    var WEAPON_GOLD_CODE = goldCode(
      'p = ([0.007]*62 + [0.007 + 0.07*(i-62) for i in range(63, 74)]\n' +
      '     + [0.777 + 0.035*(i-73) for i in range(74, 80)] + [1.])',
      '53.250420');

    var card1 = el('div', 'stat-card');
    card1.appendChild(el('p', 'stat-card__k', '角色池'));
    card1.appendChild(statTable([
      {
        label: '1 个限定（按官方公示综合概率）',
        cells: [cell(sig5(OFFICIAL_PER_UP), OFFICIAL_UP_TEX), unknown(), unknown(), unknown()]
      },
      {
        label: '1 个限定' + MODEL,
        cells: [cell(sig5(one.expected),
          '软保底的逐抽出金概率：' + PITY_CHAR + SUM_TEX + '62.297$$' +
          '再乘每个 UP 的 1.45 个金：\\(62.297\\times1.45\\approx90.334\\) 抽。',
          CHAR_GOLD_CODE)].concat(quantiles(one))
      },
      {
        label: '满命' + MODEL,
        cells: [cell(sig5(seven.expected), '\\(90.334\\times7\\approx632.32\\) 抽。')]
          .concat(quantiles(seven))
      }
    ]));
    stats.appendChild(card1);

    var card2 = el('div', 'stat-card');
    card2.appendChild(el('p', 'stat-card__k', '武器池'));
    card2.appendChild(statTable([
      {
        label: '1 把定轨（按官方公示综合概率）',
        cells: [cell(sig5(OFFICIAL_WEAPON_UP), OFFICIAL_WEAPON_TEX),
                unknown(), unknown(), unknown()]
      },
      {
        label: '1 把定轨' + MODEL,
        cells: [cell(sig5(weapon1.expected),
          '软保底的逐抽出金概率（63 抽起 +7%，74 抽起 +3.5%）：' + PITY_WEAPON +
          SUM_TEX + '53.250$$' +
          '再乘每个目标的 1.625 个金：\\(53.250\\times1.625=86.532\\) 抽。',
          WEAPON_GOLD_CODE)].concat(quantiles(weapon1))
      },
      {
        label: '满精' + MODEL,
        cells: [cell(sig5(weapon5.expected), '\\(86.532\\times5=432.66\\) 抽。')]
          .concat(quantiles(weapon5))
      }
    ]));
    stats.appendChild(card2);

    page.appendChild(homeSection('期望与分位', stats));

    /* 星辉兑换：抽卡返还的无主星辉可再换抽数，上面的读数都没计入。
       两池的推荐口径不同——角色池看四星是否满命，武器池与账号状态无关 */
    var glare = el('div', 'home__block');
    glare.appendChild(el('p', 'home__lead',
      '抽卡返还的无主星辉可再兑换为抽数，上表尚未计入。' +
      '每 5 星辉兑换 1 抽且不限量，长期口径下等额预算能抽到的抽数如下。'));
    var glareCards = el('div', 'cardgrid');

    var charCard = el('div', 'stat-card');
    charCard.innerHTML = '<p class="stat-card__k">角色池</p>';
    charCard.appendChild(derivRow('1.0917', '四星角色均未满命', '×',
      '每抽平均返还 \\(13.000\\%\\times\\frac{2}{5}+1.600\\%\\times\\frac{10}{5}=0.084\\) 抽；' +
      '\\(1+0.084+0.084^{2}+\\cdots=\\frac{1}{1-0.084}=1.0917\\)。'));
    charCard.appendChild(derivRow('1.1933', '假设四星均为满命四星角色', '×',
      '每抽平均返还 \\(13.000\\%\\times\\frac{5}{5}+1.600\\%\\times\\frac{10}{5}=0.162\\) 抽；' +
      '\\(1+0.162+0.162^{2}+\\cdots=\\frac{1}{1-0.162}=1.1933\\)。'));
    charCard.appendChild(el('p', 'stat-card__h', '每抽平均返还 0.42 / 0.81 星辉'));
    charCard.appendChild(el('p', 'stat-card__note',
      '四星武器固定 2 星辉；四星中角色与武器的占比随版本变化。'));
    glareCards.appendChild(charCard);

    var weaponCard = el('div', 'stat-card');
    weaponCard.innerHTML = '<p class="stat-card__k">武器池</p>';
    weaponCard.appendChild(derivRow('1.1050', '四星角色均未满命', '×',
      '四星一律 2 星辉（武器不因满精炼增加），每抽平均返还 ' +
      '\\(14.500\\%\\times\\frac{2}{5}+1.850\\%\\times\\frac{10}{5}=0.095\\) 抽；' +
      '\\(1+0.095+0.095^{2}+\\cdots=\\frac{1}{1-0.095}=1.1050\\)。'));
    weaponCard.appendChild(el('p', 'stat-card__h', '每抽平均返还 0.475 星辉'));
    /* 满命档要算「非 UP 四星里角色的占比」，而这随版本变化（角色与武器等概率），故不给 */
    weaponCard.appendChild(el('p', 'stat-card__note',
      '武器池也会出四星角色；非 UP 四星中角色与武器等概率，占比随版本变化，故不列满命档。'));
    glareCards.appendChild(weaponCard);

    glare.appendChild(glareCards);
    glare.appendChild(el('p', 'home__foot',
      '以上倍数均为长期期望，以星辉最终都换回抽数为前提；整抽兑换使实际结果至多少 1 抽。'));
    var glareSec = homeSection('星辉等效抽数', glare);
    glareSec.addEventListener('mouseenter', function () { W.ui.math.preload(); }, { once: true });
    page.appendChild(glareSec);

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
      entry.innerHTML = '<span class="entry__head"><span class="entry__ico">' +
                        navIcon(it[1]) + '</span><h3>' + it[0] + '</h3></span>' +
                        '<p>' + it[2] + '</p>' +
                        '<span class="entry__go">进入 →</span>';
      entries.appendChild(entry);
    });
    page.appendChild(homeSection('可视化', entries));

    stage.appendChild(page);
  }

  /* 靠边就换边：右侧放不下改挂左侧；下方放不下且底边对齐放得下才改成底对齐
     （浮层是 absolute + visibility 隐藏，尺寸量得到，不必先显形） */
  function placePop(box) {
    var pop = box.querySelector('.deriv__pop');
    box.classList.remove('deriv--left', 'deriv--up');
    if (pop.getBoundingClientRect().right > global.innerWidth - 12) {
      box.classList.add('deriv--left');
    }
    var r = pop.getBoundingClientRect();
    if (r.bottom > global.innerHeight - 12 &&
        box.getBoundingClientRect().bottom - r.height >= 12) {
      box.classList.add('deriv--up');
    }
  }

  /* 排版一次即可：MathJax 把 \(…\) 换成 SVG 后，重复调用没有意义 */
  function typesetOnce(box, body) {
    if (box.getAttribute('data-ts')) return;
    box.setAttribute('data-ts', '1');
    W.ui.math.typeset(body).then(function () {
      body.classList.add('is-ready');
      placePop(box);              /* 公式排完宽度会变，重挂一次 */
    });
  }

  /* 复制代码：剪贴板不可用或被拒时，退化为选中代码由读者自行复制 */
  function copyCode(code, node) {
    var fallback = function () {
      var range = doc.createRange();
      range.selectNodeContents(node);
      var sel = global.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      W.ui.panels.toast('复制失败，已选中代码');
    };
    var clip = global.navigator.clipboard;
    if (clip && clip.writeText) {
      clip.writeText(code).then(function () { W.ui.panels.toast('已复制'); }, fallback);
    } else {
      fallback();
    }
  }

  /* 把推导浮层挂到 box 上（box 的内容由调用方放好）：数值虚线下划线，悬停（或键盘聚焦，
     含「复制」按钮）时排版推导。tex 可含 LaTeX，opts.code 追加一段可复制的 python。
     MathJax 是 vendor 里的大文件，进入该区域才预热、真正悬停才排版 */
  function attachPop(box, tex, opts) {
    opts = opts || {};
    box.tabIndex = 0;
    var pop = el('span', 'deriv__pop');
    var body = el('span', 'deriv__body');
    body.appendChild(el('span', 'deriv__tex', tex));
    if (opts.code) {
      var codeBox = el('span', 'deriv__code');
      var code = doc.createElement('code');
      code.textContent = opts.code;
      var btn = doc.createElement('button');
      btn.type = 'button';
      btn.className = 'deriv__copy';
      btn.textContent = '复制';
      btn.onclick = function () { copyCode(opts.code, code); };
      codeBox.appendChild(code);
      codeBox.appendChild(btn);
      body.appendChild(codeBox);
    }
    pop.appendChild(body);
    box.appendChild(pop);
    var show = function () {
      if (opts.math === false) body.classList.add('is-ready');   /* 纯文字，不必拉 MathJax */
      else typesetOnce(box, body);
      placePop(box);
    };
    box.addEventListener('mouseenter', show);
    box.addEventListener('focusin', show);
    return box;
  }

  /* 带推导悬浮的读数行：数值在左，口径说明在右 */
  function derivRow(value, tag, unit, tex, opts) {
    opts = opts || {};
    var row = el('div', 'statcmp');
    var box = el('span', 'deriv');
    var v = el('span', 'statcmp__v', value);
    v.appendChild(el('span', 'statcmp__u', unit));
    box.appendChild(v);
    attachPop(box, tex, opts);
    row.appendChild(box);
    var tagNode = el(opts.href ? 'a' : 'span', 'statcmp__tag');
    if (opts.href) tagNode.href = opts.href;
    tagNode.textContent = tag;
    row.appendChild(tagNode);
    return row;
  }

  /* 首页读数表：行 = 目标，列 = 期望 / 50% / 90% / 99% 分位；
     rows = [{ label, cells: [{ v, box? }] }]，box = { tex, code } 时该格可悬停看推导 */
  function statTable(rows) {
    var table = el('table', 'stattable');
    var head = el('thead');
    var hr = el('tr');
    hr.appendChild(el('th'));
    ['期望', '50% 分位', '90% 分位', '99% 分位'].forEach(function (h, i) {
      hr.appendChild(el('th', i === 0 ? 'stattable__e' : null, h));
    });
    head.appendChild(hr);
    table.appendChild(head);

    var tbody = el('tbody');
    rows.forEach(function (r) {
      var tr = el('tr');
      tr.appendChild(el('th', null, r.label));
      r.cells.forEach(function (c, i) {
        /* plain 的格子（「未知」）不带单位、居中、用正文字体 */
        var td = el('td', i === 0 ? 'stattable__e' : (c.plain ? 'stattable__unknown' : null));
        var holder = el('span', c.box ? 'deriv' : null);
        holder.appendChild(el('span', c.plain ? null : 'stattable__v', c.v));
        if (!c.plain) holder.appendChild(el('span', 'stattable__u', '抽'));
        if (c.box) attachPop(holder, c.box.tex, c.box);
        td.appendChild(holder);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    return table;
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
    /* 页脚的「机制误差」链接在机制误差页自身是自指，隐去 */
    var flink = doc.getElementById('footer-about');
    if (flink) flink.hidden = mod.id === 'about';
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
    if (!mod.noDisclaimer) {
      colMain.appendChild(el('p', 'disclaimer',
        '机制参数取自社区总结的模型，结果仅供参考 · <a href="#/about">机制误差</a>'));
    }
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
    /* 图像导出放在参数面板里：图上的浮动按钮会压住数据标注。
       链接不进面板——地址栏里那份就是（hash 即全部状态）。 */
    var acts = el('div', 'inspector__acts');
    W.ui.panels.chartActionButtons(function () {
      return viewHost ? viewHost.querySelector('.chart') : null;
    }, 'btn').forEach(function (b) { acts.appendChild(b); });
    inspector.appendChild(acts);
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
