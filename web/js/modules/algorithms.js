/* 算法 —— 复杂度的逐步降低：朴素解 → 序列枚举 → 状态聚合 → 金数 DP → 正态近似 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var M = W.modules = W.modules || {};

  function row(cells) {
    return '<tr>' + cells.map(function (c, i) {
      return i === 0 ? '<th scope="row">' + c + '</th>' : '<td>' + c + '</td>';
    }).join('') + '</tr>';
  }

  /* n = 500 的实测数字取自实验数据，避免正文与图表脱节 */
  function benchLine() {
    var A = global.__WISH_ANALYSIS__;
    var fallback = '实测耗时见 <a href="#/perf">性能与验证</a>。';
    if (!A) return fallback;
    var i = A.task1.n.indexOf(500);
    if (i < 0) return fallback;
    var g = A.task1.series['dp-golds'].time[i];
    var s = A.task1.series['dp-state'].time[i];
    if (g === null || s === null) return fallback;
    return '实测：n = 500 时 dp-state 耗时 ' + s.toFixed(0) + ' ms，dp-golds 耗时 ' +
      g.toFixed(0) + ' ms，约为前者的 1/' + (s / g).toFixed(0) + '。';
  }

  var DOC_HEAD = '' +
    '<p>精确求解 n 个 UP 的抽数分布，朴素的逐抽算法在 n 稍大时即不可行。' +
    '以下记录复杂度的逐步降低过程：每一步消除哪个维度、代价如何转移。' +
    '各步的实测耗时见 <a href="#/perf">性能与验证</a>。</p>' +

    '<h2>问题定义</h2>' +
    '<p>同一模型需要回答三类问题：</p>' +
    '<div class="tablewrap"><table class="dtable dtable--plain">' +
    '<thead><tr><th>任务</th><th>输入</th><th>输出</th></tr></thead><tbody>' +
    row(['任务 1', '目标 UP 数 n、初始状态', '抽到 n 个限定所需抽数的分布 P(抽数)']) +
    row(['任务 2', '任务 1 的输入 + 常驻数量', '每个常驻数量下的条件分布 P(抽数 | 常驻数)']) +
    row(['任务 3', '任务 1 的输入', '歪出多少个常驻的分布 P(常驻数)']) +
    '</tbody></table></div>' +
    '<p>三者相互关联：任务 1 = 任务 3 加权任务 2，即 P(抽数) = Σ P(常驻数) · P(抽数 | 常驻数)。' +
    '以下以任务 1 为主线；任务 2 与任务 3 仅需在状态中增加一个维度。</p>' +

    '<h2>朴素解法：逐抽递推</h2>' +
    '<p>最直接的实现按抽推进，状态为（抽数 i，已获得 UP 数 j，已连歪次数 s）。' +
    '每一抽转移到下一抽，出金时按 p_up[s] 分裂为「中」与「歪」两条支路。</p>' +
    '<p>该实现的代价不可接受。抽数轴长度为 180n（每个 UP 至多消耗 2 个金，每金至多 90 抽），' +
    'n = 500 时达 9 万；状态数为 4 × n × 180n 量级；且每一状态均需与长度为 91 的金分布做卷积，' +
    '总复杂度 O(n²·m²)。实测 n = 7 耗时 24.8 ms、n = 10 耗时 56.7 ms，之后迅速失去可用性。' +
    '该实现对第二目标的扩展性同样不足：若同时统计歪出的常驻数量，状态空间须再增加一维，' +
    '代价乘以 n。</p>' +
    '<p>根本原因在于抽数维度被过早引入。抽数仅在最终结果中需要，' +
    '中间过程所需计算的是「需要多少个金」以及「这些金对应多少抽」。</p>' +

    '<h2>第一步：枚举中／歪序列，抽数后置（dp-path）</h2>' +
    '<p>n 次 UP 的中／歪组合共 2ⁿ 条序列。每条序列只记录两个量：消耗的金数（中记 1、歪记 2）' +
    '与歪的次数（即歪出的常驻数量）。将金数相同的序列概率求和，得到「需要 g 个金」的分布；' +
    '再与预先计算的「g 个金所需抽数」加权合成抽数分布。</p>' +
    '<p>该实现每步均为标量运算，n ≤ 10 时耗时约 0.5 ms，较逐抽递推快两个数量级。' +
    '其代价随序列数指数增长：n = 20 为一百万条（约 0.6 s），n = 30 达十亿条，不再可行。</p>' +

    '<h2>第二步：按状态聚合，取消序列枚举（dp-state）</h2>' +
    '<p>状态转移只依赖当前的连歪次数，与到达该状态的路径无关。因此到达同一状态的序列可以合并：' +
    '只需保留「到达状态 s 的抽数分布」，每步对四个状态各做一次卷积，将概率质量推进一轮。</p>' +
    '<p>序列维度由此消除，代价是抽数维度重新出现：每步需卷积长度为 O(k·m) 的数组，' +
    '复杂度 O(n²·m·log(n·m))。n = 500 由不可行变为数秒量级。</p>' +

    '<h2>第三步：DP 只统计金数，抽数一次性卷积（dp-golds，当前默认）</h2>' +
    '<p>进一步观察：代价只取决于共获得多少个金。因此 DP 无需携带抽数，' +
    '状态缩减为（连歪次数，金数）两维，全部为整数运算，复杂度 O(n²)，与单金抽数上限 m 无关。</p>' +
    '<p>抽数在最后一步引入：将「需要 g 个金」的概率与缓存的多金分布「g 个金所需抽数」加权求和。' +
    '多金分布只与池参数有关，与垫抽、大保底等初始状态无关，可一次计算反复使用。' +
    '初始状态仅在最后一步卷积中体现：已垫 p 抽等价于将首金分布右移并截断；' +
    '大保底等价于额外获得一个金，在末尾再卷积一次普通出金分布。</p>' +
    '<p>%BENCH%</p>' +
    '<p>三类任务可一并求解：状态中增加「歪出的常驻数」后仍为整数 DP，' +
    '任务 2 与任务 3 无需另行处理。</p>' +

    '<h2>更大规模：正态近似（CLT，n &gt; 500）</h2>' +
    '<p>n 较大时，总抽数可用正态分布近似。需注意各次 UP 的连歪状态并不固定，' +
    '会由初始值迁移至稳态分布，因此第一个 UP 使用初始状态的精确矩、其余 n−1 个使用稳态矩，' +
    '二者相加后取正态，再以 ±0.5 的连续性修正映射到整数抽数。复杂度 O(1)；' +
    'n = 500 时相对误差已降至 0.001% 量级，收敛曲线见 <a href="#/perf">性能与验证</a>。' +
    '网页界面当前将目标 UP 数限制在 30 以内，均属精确解范围。</p>' +

    '<h2>方案对照</h2>' +
    '<div class="tablewrap"><table class="dtable dtable--plain">' +
    '<thead><tr><th>方案</th><th>复杂度</th><th>现状</th></tr></thead><tbody>' +
    row(['dp-pulls', 'O(n²·m²)', '仅作基准，已不用于计算']) +
    row(['dp-path', 'O(2ⁿ)', '小 n 最快；n ≤ 20 可用于交叉校验']) +
    row(['dp-state', 'O(n²·m·log(n·m))', '可显式调用；曾被采用，现由 dp-golds 取代']) +
    row(['dp-golds', 'O(n²) + 一次加权卷积', '当前默认，三类任务通用']) +
    row(['dp-state-golds', 'O(n³·m·log(n·m))', '理论可行，常数远大于 dp-golds，未实现']) +
    row(['CLT', 'O(1)', 'n &gt; 500 的近似方案']) +
    '</tbody></table></div>' +

    '<h2>未采用 FFT 的原因</h2>' +
    '<p>卷积表面上是性能瓶颈，实测并非如此：在 100–90000 的长度范围内，' +
    'numpy 的卷积快于 FFT 实现；而 FFT 幂次法（对分布做 k 次自卷积）在 k = 101 时误差已达 2.0，' +
    '数值上不可用。更有效的做法是避免卷积本身——即 dp-golds：' +
    '先以整数 DP 消除序列维度，最后只做一次卷积。</p>' +

    '<h2>数值精度</h2>' +
    '<p>全部计算采用双精度浮点，除 CLT 分支外不作近似与截断。舍入误差量级如下：</p>' +
    '<div class="tablewrap"><table class="dtable dtable--plain">' +
    '<thead><tr><th>环节</th><th>相对误差量级</th></tr></thead><tbody>' +
    row(['单金分布构造', '~4×10⁻¹⁴']) +
    row(['多金分布卷积（k 次）', '~k × 2×10⁻¹⁴']) +
    row(['dp-golds（n = 500，约 1000 次卷积）', '~2×10⁻¹¹']) +
    row(['稳态权重的归一化偏差', '~4×10⁻⁷（系统性，已计入模型）']) +
    '</tbody></table></div>' +
    '<p>卷积的相对误差与数值大小成正比：尾部 10⁻⁵⁰ 量级的概率与主体 0.1 量级的概率' +
    '具有相同的相对精度，不会因极端幸运的尾部而失真。上述量级均远小于模型本身的偏差，' +
    '详见 <a href="#/about">模型与误差</a>。</p>';

  M.algo = {
    id: 'algo',
    title: '算法',
    group: '关于',
    layout: 'doc',
    intro: '朴素解在 n 增大后不可行。本文记录每一步优化消除的维度，以及代价的转移。',
    defaultView: 'doc',
    defaults: {},
    controls: function () { return []; },
    views: {
      doc: {
        label: '说明',
        render: function (host) {
          var box = global.document.createElement('div');
          box.className = 'prose';
          box.innerHTML = DOC_HEAD.replace('%BENCH%', benchLine());
          host.appendChild(box);
        }
      }
    }
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
