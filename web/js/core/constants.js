/* 池参数与概率常量 —— 对应 src/genshin_wish/_constants.py */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core = W.core || {};

  C.POOLS = {
    character: {
      key: 'character',
      label: '角色池',
      baseRate: 0.006,
      softPityStart: 74,
      hardPity: 90,
      softPityStep: 0.06,
      softPityStart2: null,
      softPityStep2: null
    },
    weapon: {
      key: 'weapon',
      label: '武器池',
      baseRate: 0.007,
      softPityStart: 63,
      hardPity: 80,
      softPityStep: 0.07,
      softPityStart2: 74,
      softPityStep2: 0.035
    }
  };

  /* 连续歪次数 k_miss 的稳态分布，和 ≈ 1.0000004，与 Python 一致不做归一 */
  C.STABLE_P = [0.550404, 0.274707, 0.124167, 0.0507224];

  /* 界面上「已连歪次数」取值 4 表示稳态（次数未知，按 STABLE_P 加权），与 MISS_LABELS 的索引一致 */
  C.STABLE_LOSS = 4;

  /* 各 k_miss 下的等效 UP 率：0.5 + 0.5 * 捕获明光概率 */
  C.CAPTURE_RADIANCE_WIN_RATE = [0.50009, 0.54800, 0.59150, 1.0];

  C.LIMITS = {
    goldTableMax: 64,
    charExactNUp: 30,
    pullsMax: 10000,
    maxPity: { character: 89, weapon: 79 }
  };

  C.MISS_LABELS = [
    ['已连歪 0 次', 'miss=0'],
    ['已连歪 1 次', 'miss=1'],
    ['已连歪 2 次', 'miss=2'],
    ['已连歪 3 次', 'miss=3'],
    ['稳态', 'stable']
  ];

  C.DEFAULT_ALPHAS = [0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99];
  C.CDF_ALPHAS = [0.1, 0.3, 0.5, 0.7, 0.9, 0.99];

  /* 色板沿用 Python 侧 viz/_base.py，保证新图与旧 PNG 观感一致 */
  C.COLORS = {
    alpha6: ['#2ca02c', '#1f77b4', '#ff7f0e', '#9467bd', '#d62728', '#4b0082'],
    interval3: ['#1f77b4', '#ff7f0e', '#d62728'],
    interval5: ['#084594', '#2171b5', '#4292c6', '#f16913', '#cb181d'],
    gold: '#d3a054',
    player: '#27ae60',
    cdfLine: '#333333',
    blues: ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6',
            '#4292c6', '#2171b5', '#08519c', '#08306b'],
    spectral: ['#5e4fa2', '#3288bd', '#66c2a5', '#abdda4', '#e6f598', '#ffffbf',
               '#fee08b', '#fdae61', '#f46d43', '#d53e4f', '#9e0142'],
    /* 堆叠柱专用：恒亮彩虹（同明度、只翻色相；HSL 278°→-20°，S .55 L .62）。
       spectral 的中段近白，层数多时相邻档糊成一片，故另备一条没有亮档的色带 */
    stack: ['#ac69d3', '#8469d3', '#6977d3', '#699fd3', '#69c8d3', '#69d3b6', '#69d38d',
            '#6dd369', '#96d369', '#bfd369', '#d3bf69', '#d39769', '#d36e69', '#d3698c'],
    coolwarm: ['#3b4cc0', '#6788ee', '#9abbff', '#c9d7f0', '#edd1c2', '#f7a889',
               '#e26952', '#b40426'],
    primary: '#2171b5'
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
