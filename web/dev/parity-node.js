/* 一致性校验的 Node 端：加载 web/js/core/* 重算基准用例，结果写 stdout。
 * 由 scripts/parity.py 调用：node web/dev/parity-node.js <fixture.json>
 * 只依赖 vm，不依赖浏览器环境——core 层不碰 document/window。
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
  const code = fs.readFileSync(path.join(ROOT, 'web', 'js', 'core', f), 'utf8');
  vm.runInContext(code, ctx, { filename: f });
}

const C = ctx.Wish.core;
const ALPHAS = [0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99];
const refs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));

function distOut(d, cdfIdx) {
  let sum = 0;
  for (let i = 0; i < d.pdf.length; i++) sum += d.pdf[i];
  return {
    len: d.cdf.length,
    sum: sum,
    expected: d.expected,
    cdf: cdfIdx.map((i) => d.cdf[i]),
    quant: ALPHAS.map((a) => d.quantile(a)),
  };
}

function charState(c) {
  return C.makeCharacterState({
    guaranteed: !!c.g, pity: c.pity || 0, consecutiveLoss: c.loss || 0, stable: !!c.stable,
  });
}

function mapOut(map) {
  const o = {};
  Object.keys(map).forEach((k) => { o[k] = map[k]; });
  return o;
}

const out = refs.map((ref) => {
  const c = ref.case;
  switch (ref.kind) {
    case 'norm':
      return {
        cdf: ref.z.map((z) => C.stats.normCdf(z)),
        ppf: ref.p.map((p) => C.stats.normPpf(p)),
      };
    case 'char':
      return distOut(C.upDistribution(charState(c), c.n), ref.cdf_idx);
    case 'weapon':
      return distOut(C.weaponUpDistribution(
        C.makeWeaponState({ pity: c.pity, epitomizedPoints: c.ep, prevStandard: !!c.prevStd }),
        c.countA), ref.cdf_idx);
    case 'std':
      return distOut(C.standardDistribution(c.pity, c.nGold), ref.cdf_idx);
    case 'joint':
      return distOut(C.jointDistribution(
        C.makeCharacterState({ guaranteed: false, pity: c.charPity, consecutiveLoss: 0 }),
        c.charUp,
        C.makeWeaponState({ pity: c.weaponPity, epitomizedPoints: c.weaponEp }),
        c.weaponCount), ref.cdf_idx);
    case 'nstd':
      return { map: mapOut(C.nStdDistribution(
        C.makeCharacterState({ pity: 0, consecutiveLoss: c.loss }), c.nUp)) };
    case 'nstd_cond': {
      const dists = C.nStdConditionalPulls(
        C.makeCharacterState({ pity: 0, consecutiveLoss: c.loss }), c.nUp);
      const o = {};
      Object.keys(dists).forEach((k) => { o[k] = dists[k].expected; });
      return { map: o };
    }
    case 'radiance':
      return { map: mapOut(C.radianceDistribution(
        C.makeCharacterState({ pity: 0, consecutiveLoss: c.loss }), c.nUp)) };
    case 'radiance_seq':
      return { map: mapOut(C.radianceDistFromSeq(c.seq)) };
    case 'pre50':
      return distOut(C.upDistributionPre50(charState(c), c.nUp), ref.cdf_idx);
    case 'pre50_stable':
      return distOut(C.stableUpDistributionPre50(c.nUp), ref.cdf_idx);
    case 'tenpull': {
      const o = {};
      for (let g = 2; g <= 6; g++) o[String(g)] = C.tenPullMultiGold(c.pool, g);
      return { map: o };
    }
    case 'longterm': {
      const solver = C.makeLongSolver({ nPre50: c.nPre, nPost50: c.N - c.nPre }, c.method);
      const rows = ref.rows.map((row) => {
        const bounds = {};
        ref.alphas.forEach((a) => { bounds[String(a)] = solver.bounds(row.n, a); });
        return { n: row.n, bounds: bounds };
      });
      return { mu: solver.muSingle, rows: rows };
    }
    default:
      throw new Error('unknown kind: ' + ref.kind);
  }
});

process.stdout.write(JSON.stringify(out));
