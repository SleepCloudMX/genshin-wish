/* 站点内核的性能基准：给定抽数 → （目标数, 歪出数）联合分布的耗时。
 * 由 scripts/analysis/task4_pulls_to_joint.py 调用，结果写进 data.json 供「算法性能」页。
 * 用法: node web/dev/bench-pulls-joint.js [--runs=3] [--pulls=100,1000,10000]  → stdout 输出 JSON
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..', '..');
const CORE = ['constants.js', 'stats.js', 'gold.js', 'character.js', 'banners.js', 'longterm.js'];

const ctx = { console: console, Math: Math, Float64Array: Float64Array };
vm.createContext(ctx);
for (const f of CORE) {
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web', 'js', 'core', f), 'utf8'),
                  ctx, { filename: f });
}
const C = ctx.Wish.core;

function argOf(name, dflt) {
  const hit = process.argv.slice(2).find((a) => a.indexOf('--' + name + '=') === 0);
  return hit ? hit.slice(name.length + 3) : dflt;
}

const RUNS = Number(argOf('runs', '3'));
const PULLS = String(argOf('pulls', '100,200,300,500,700,1000,1500,2000,3000,5000,7000,10000,20000'))
  .split(',').map(Number);

function ms(fn) {
  const t0 = process.hrtime.bigint();
  fn();
  return Number(process.hrtime.bigint() - t0) / 1e6;
}

/* 预热：首次调用要建金 PDF 表，不计入 */
ms(() => C.pullsJointDistribution(C.makeCharacterState({}), PULLS[0]));
ms(() => C.weaponPullsJointDistribution(C.makeWeaponState({}), PULLS[0]));

const out = { character: {}, weapon: {} };
for (const P of PULLS) {
  const ch = [];
  for (let r = 0; r < RUNS; r++) {
    ch.push(ms(() => C.pullsJointDistribution(C.makeCharacterState({}), P)));
  }
  out.character[P] = ch;

  const wp = [];
  for (let r = 0; r < RUNS; r++) {
    wp.push(ms(() => C.weaponPullsJointDistribution(C.makeWeaponState({}), P)));
  }
  out.weapon[P] = wp;
}
process.stdout.write(JSON.stringify(out));
