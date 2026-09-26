/* LaTeX 公式渲染：按需加载 MathJax（SVG 输出，不依赖字体文件，file:// 下可用）
 * 用法：文档里写 \( 行内公式 \) 或 $$ 行间公式 $$，渲染后调用 W.ui.math.typeset(root)。
 */
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var UI = W.ui = W.ui || {};
  var doc = global.document;

  var SRC = 'web/vendor/mathjax-tex-svg.js';
  var loading = null;

  function ensure() {
    if (global.MathJax && global.MathJax.typesetPromise) return Promise.resolve();
    if (loading) return loading;
    loading = new Promise(function (resolve, reject) {
      var s = doc.createElement('script');
      s.src = SRC;
      s.onload = function () { resolve(); };
      s.onerror = function () { reject(new Error('MathJax 加载失败')); };
      doc.head.appendChild(s);
    });
    return loading;
  }

  UI.math = {
    /* 渲染 root 子树里的公式；加载失败时保留原文（形如 \(O(n^2)\)） */
    typeset: function (root) {
      if (!root) return;
      ensure().then(function () {
        var MJ = global.MathJax;
        if (!MJ) return null;
        /* typesetPromise 要等 startup 完成才存在，直接调用会静默失败 */
        var ready = (MJ.startup && MJ.startup.promise) || Promise.resolve();
        return ready.then(function () {
          if (typeof MJ.typesetPromise === 'function') {
            return MJ.typesetPromise([root]);
          }
          return null;
        });
      }).catch(function () { /* 保留原文 */ });
    }
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
