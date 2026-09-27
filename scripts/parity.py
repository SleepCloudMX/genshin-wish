#!/usr/bin/env python
"""JS ↔ Python 一致性校验。

Python 侧生成基准（各分布的期望、分位点、CDF 采样）→ Node 加载 `web/js/core/*`
重算同一批用例 → 逐项比对 → 打印分组表并以退出码给出结论。

    python scripts/parity.py

容差：概率 5e-13；分位点要求完全一致；长期分布的分位点允许 1 抽（CLT 通道 3 抽）。
基准文件写到 `temp/parity-ref.json`（已 gitignore），重算结果不落盘。
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from genshin_wish._capture_radiance import radiance_dist_from_seq  # noqa: E402
from genshin_wish._constants import CHARACTER_POOL, STABLE_P, WEAPON_POOL  # noqa: E402
from genshin_wish._gold import get_gold_pdfs  # noqa: E402
from genshin_wish.character import (  # noqa: E402
    CharacterState,
    UpDistribution,
    n_std_conditional_pulls,
    n_std_distribution,
    radiance_distribution,
    stable_up_distribution,
    stable_up_distribution_pre50,
    up_distribution,
    up_distribution_pre50,
)
from genshin_wish.joint import joint_distribution  # noqa: E402
from genshin_wish.long_term import LongTermState, make_long_solver  # noqa: E402
from genshin_wish.standard import StandardState, standard_distribution  # noqa: E402
from genshin_wish.weapon import WeaponState, WeaponTarget, weapon_up_distribution  # noqa: E402

ALPHAS = [0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99]
NODE_RUNNER = ROOT / "web" / "dev" / "parity-node.js"

# 每组统计：比对项、最大概率偏差、最大抽数偏差、失败项
GROUPS: dict[str, dict] = {}


def record(name: str, items: int = 0, prob: float = 0.0, pull: float = 0.0,
           failed: int = 0) -> None:
    g = GROUPS.setdefault(name, {"items": 0, "prob": 0.0, "pull": 0.0, "failed": 0})
    g["items"] += items
    g["prob"] = max(g["prob"], prob)
    g["pull"] = max(g["pull"], pull)
    g["failed"] += failed


def cdf_indices(cdf, k=6):
    return [int(i) for i in np.linspace(0, len(cdf) - 1, k)]


def dist_ref(kind, case, dist, alphas=ALPHAS) -> dict:
    cdf = np.asarray(dist.cdf, dtype=float)
    pdf = np.asarray(dist.pdf, dtype=float)
    idx = cdf_indices(cdf)
    return {
        "kind": kind, "case": case, "len": int(len(cdf)),
        "sum": float(pdf.sum()), "expected": float(dist.expected),
        "cdf_idx": idx, "cdf": [float(cdf[i]) for i in idx],
        "quant": [int(dist.quantile(a)) for a in alphas],
    }


def stable_state_dist(n_up: int, pity: int, guaranteed: bool) -> UpDistribution:
    """对照 JS 的 ``stableUpDistribution(n_up, {pity, guaranteed})``：
    STABLE_P 加权 k_miss = 0..3，已知的 pity / guaranteed 照常施加。"""
    dists = [up_distribution(
        CharacterState(guaranteed=guaranteed, pity=pity, consecutive_loss=k), n_up)
        for k in range(4)]
    pdf = np.zeros(max(len(d.pdf) for d in dists), dtype=np.float64)
    for d, weight in zip(dists, STABLE_P):
        pdf[: len(d.pdf)] += d.pdf * weight
    return UpDistribution(pdf=pdf, cdf=np.cumsum(pdf), method=dists[0].method)


def stable_n_std_distribution(n_up: int) -> dict[int, float]:
    """对照 JS 的稳态 n_std 分布：STABLE_P 加权 k_miss = 0..3。"""
    out: dict[int, float] = {}
    for k, weight in enumerate(STABLE_P):
        state = CharacterState(pity=0, consecutive_loss=k)
        for ns, p in n_std_distribution(state, n_up).items():
            out[ns] = out.get(ns, 0.0) + weight * p
    return out


def stable_n_std_conditional(n_up: int) -> dict[int, UpDistribution]:
    """对照 JS 的稳态条件抽数分布：各状态按 STABLE_P × P(n_std | 该状态) 加权，再归一。"""
    acc: dict[int, np.ndarray] = {}
    for k, weight in enumerate(STABLE_P):
        state = CharacterState(pity=0, consecutive_loss=k)
        marg = n_std_distribution(state, n_up)
        for ns, d in n_std_conditional_pulls(state, n_up).items():
            w = weight * marg.get(ns, 0.0)
            if w == 0.0:
                continue
            pdf = np.asarray(d.pdf, dtype=float) * w
            cur = acc.get(ns)
            if cur is None:
                acc[ns] = pdf
            else:
                buf = np.zeros(max(len(cur), len(pdf)), dtype=np.float64)
                buf[: len(cur)] += cur
                buf[: len(pdf)] += pdf
                acc[ns] = buf
    out: dict[int, UpDistribution] = {}
    for ns, pdf in acc.items():
        total = pdf.sum()
        if total <= 0:
            continue
        norm = pdf / total
        out[ns] = UpDistribution(pdf=norm, cdf=np.cumsum(norm))
    return out


def map_ref(kind, case, mapping) -> dict:
    return {"kind": kind, "case": case,
            "map": {str(k): float(v) for k, v in sorted(mapping.items())}}


def build_references() -> list[dict]:
    refs: list[dict] = []

    # --- 正态分布（CLT 通道的基础） ---
    from scipy.stats import norm as _norm

    zs = [-6, -3, -2.3263, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2, 2.3263, 3, 5]
    ps = [0.005, 0.01, 0.1, 0.3, 0.5, 0.7, 0.99, 0.999]
    refs.append({"kind": "norm", "case": {},
                 "z": zs, "cdf": [float(_norm.cdf(z)) for z in zs],
                 "p": ps, "ppf": [float(_norm.ppf(p)) for p in ps]})

    # --- 角色池 ---
    for n in [1, 2, 3, 7, 20]:
        for pity in [0, 1, 34, 89]:
            for loss in range(4):
                for g in [False, True]:
                    # Python 的 pity>0 分支是指数枚举，n 大了会爆；JS 侧另有等价改写
                    if pity > 0 and n > 12:
                        continue
                    state = CharacterState(guaranteed=g, pity=pity, consecutive_loss=loss)
                    refs.append(dist_ref("char", {"n": n, "pity": pity, "loss": loss, "g": g},
                                         up_distribution(state, n)))
    for n in [1, 2, 7, 20]:
        refs.append(dist_ref("char", {"n": n, "stable": True}, stable_up_distribution(n)))
    # 稳态 + 已知状态（已垫抽数 / 大保底）：JS 侧由 upDistribution 分流到 stableUpDistribution
    for n in [1, 2, 3, 7]:
        for pity in [0, 34]:
            for g in [False, True]:
                case = {"n": n, "pity": pity, "stable": True, "g": g}
                refs.append(dist_ref("char", case, stable_state_dist(n, pity, g)))

    # --- 武器池 ---
    for count_a in [1, 2, 3]:
        for ep in [0, 1]:
            for prev_std in [False, True]:
                for pity in [0, 45, 79]:
                    case = {"countA": count_a, "ep": ep, "prevStd": prev_std, "pity": pity}
                    state = WeaponState(pity=pity, epitomized_points=ep,
                                        prev_standard=prev_std)
                    refs.append(dist_ref("weapon", case, weapon_up_distribution(
                        state, WeaponTarget(count_a=count_a))))

    # --- 常驻池 ---
    for pity in [0, 45, 89]:
        for n_gold in [1, 3, 10]:
            refs.append(dist_ref("std", {"pity": pity, "nGold": n_gold},
                                 standard_distribution(StandardState(pity=pity), n_gold)))

    # --- 联合 ---
    for char_up, wcount, cpity, wpity, ep in [(2, 1, 0, 0, 0), (7, 1, 34, 45, 1),
                                              (1, 2, 0, 0, 0)]:
        case = {"charUp": char_up, "weaponCount": wcount, "charPity": cpity,
                "weaponPity": wpity, "weaponEp": ep}
        refs.append(dist_ref("joint", case, joint_distribution(
            CharacterState(guaranteed=False, pity=cpity, consecutive_loss=0), char_up,
            WeaponState(pity=wpity, epitomized_points=ep, prev_standard=False),
            WeaponTarget(count_a=wcount))))

    # --- 常驻五星数 ---
    for n_up in [1, 7, 20, 30]:
        for loss in range(4):
            state = CharacterState(pity=0, consecutive_loss=loss)
            refs.append(map_ref("nstd", {"nUp": n_up, "loss": loss},
                                n_std_distribution(state, n_up)))
    for n_up, loss in [(7, 0), (7, 2), (20, 3)]:
        state = CharacterState(pity=0, consecutive_loss=loss)
        cond = n_std_conditional_pulls(state, n_up)
        refs.append(map_ref("nstd_cond", {"nUp": n_up, "loss": loss},
                            {ns: d.expected for ns, d in cond.items()}))
    for n_up in [1, 7, 20, 30]:
        refs.append(map_ref("nstd", {"nUp": n_up, "stable": True},
                            stable_n_std_distribution(n_up)))
    for n_up in [7, 20]:
        refs.append(map_ref("nstd_cond", {"nUp": n_up, "stable": True},
                            {ns: d.expected for ns, d in stable_n_std_conditional(n_up).items()}))

    # --- 捕获明光 ---
    for n_up in [1, 7, 20, 50]:
        for loss in range(4):
            state = CharacterState(pity=0, consecutive_loss=loss)
            refs.append(map_ref("radiance", {"nUp": n_up, "loss": loss},
                                radiance_distribution(state, n_up)))
    seq = [1, 2, 2, 1, 2, 2, 1, 1, 1, 2]
    refs.append(map_ref("radiance_seq", {"seq": seq}, radiance_dist_from_seq(seq)))

    # --- 5.0 前机制 ---
    for n_up in [1, 3, 7]:
        for pity in [0, 34]:
            for loss in range(4):
                for g in [False, True]:
                    case = {"nUp": n_up, "pity": pity, "loss": loss, "g": g}
                    refs.append(dist_ref("pre50", case, up_distribution_pre50(
                        CharacterState(guaranteed=g, pity=pity, consecutive_loss=loss), n_up)))
    for n_up in [1, 7]:
        refs.append(dist_ref("pre50", {"nUp": n_up, "stable": True},
                             stable_up_distribution_pre50(n_up)))

    # --- 十连多金 ---
    for name, pool in [("character", CHARACTER_POOL), ("weapon", WEAPON_POOL)]:
        p_gold = get_gold_pdfs(pool)[1]
        refs.append(map_ref("tenpull", {"pool": name},
                            {g: _pull10_prob(p_gold, g) for g in range(2, 7)}))

    # --- 长期分布 ---
    long_cases = [
        ({"N": 20, "nPre": 0}, "exact"),
        ({"N": 20, "nPre": 5}, "exact"),
        ({"N": 20, "nPre": 20}, "exact"),
        ({"N": 60, "nPre": 0}, "exact"),
        ({"N": 100, "nPre": 0}, "clt"),
    ]
    for case, method in long_cases:
        state = LongTermState(n_pre_50=case["nPre"], n_post_50=case["N"] - case["nPre"])
        solver = make_long_solver(state, method=method)
        ns = sorted({n for n in (1, 5, 10, case["N"]) if 1 <= n <= case["N"]})
        refs.append({
            "kind": "longterm", "case": dict(case, method=method),
            "mu": float(solver.mu_single), "alphas": [0.01, 0.1, 0.3, 0.5],
            "rows": [{"n": n} for n in ns],
            "bounds": {str(n): {str(a): [int(solver(n, [a])[a][n - 1][0]),
                                         int(solver(n, [a])[a][n - 1][1])]
                                for a in [0.01, 0.1, 0.3, 0.5]} for n in ns},
        })
    return refs


def _pull10_prob(pdf1, gold: int) -> float:
    """稳态下一次十连出 ≥ gold 个金的概率（与 scripts/plots/multi_gold.py 同式）。"""
    cdfs = [np.cumsum(p) for p in [np.array([1.0]), pdf1]]
    survival = 1.0 - cdfs[1][:-1]
    weights = survival / survival.sum()
    total = 0.0
    for d, w in enumerate(weights):
        shifted = np.insert(pdf1[d + 1:] / pdf1[d + 1:].sum(), 0, 0)[:11]
        result = shifted.copy()
        for _ in range(gold - 1):
            result = np.convolve(result, pdf1)[:11]
        total += result.sum() * w
    return float(total)


def near(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def compare(refs: list[dict], got: list[dict]) -> int:
    """逐项比对，返回失败项数。"""
    failed_all = 0

    def check(name, what, a, b, delta_tol, exact=False):
        nonlocal failed_all
        if exact:
            ok, delta = a == b, (0.0 if a == b else float("inf"))
            scale = "pull"
        else:
            ok = near(a, b, delta_tol)
            delta = abs(a - b)
            scale = "pull" if delta_tol >= 1.0 else "prob"
        record(name, items=1,
               prob=delta if scale == "prob" else 0.0,
               pull=delta if scale == "pull" else 0.0,
               failed=0 if ok else 1)
        if not ok:
            failed_all += 1
            if failed_all <= 25:
                print(f"  x [{name}] {what}: python={a!r} js={b!r}")

    for ref, res in zip(refs, got):
        name, case = ref["kind"], ref["case"]
        if name == "norm":
            for z, v in zip(ref["z"], ref["cdf"]):
                check(name, f"normCdf({z})", v, res["cdf"][ref["z"].index(z)], 5e-12)
            for p, v in zip(ref["p"], ref["ppf"]):
                check(name, f"normPpf({p})", v, res["ppf"][ref["p"].index(p)], 5e-12)
        elif "map" in ref:
            for k in sorted(set(ref["map"]) | set(res["map"]),
                            key=lambda s: int(s) if s.lstrip("-").isdigit() else 0):
                check(name, f"{case} p({k})", ref["map"].get(k, 0.0),
                      res["map"].get(k, 0.0), 5e-13)
        elif name == "longterm":
            check(name, f"{case} mu", ref["mu"], res["mu"], 1e-9)
            pull_tol = 3.0 if case["method"] == "clt" else 1.0
            for i, row in enumerate(ref["rows"]):
                n = row["n"]
                for a, pair in ref["bounds"][str(n)].items():
                    js_pair = res["rows"][i]["bounds"][a]
                    check(name, f"{case} n={n} a={a} lo", pair[0], js_pair[0], pull_tol)
                    check(name, f"{case} n={n} a={a} hi", pair[1], js_pair[1], pull_tol)
        else:
            check(name, f"{case} len", ref["len"], res["len"], 0, exact=True)
            check(name, f"{case} sum", ref["sum"], res["sum"], 1e-9)
            check(name, f"{case} expected", ref["expected"], res["expected"], 1e-9)
            for i, v in zip(ref["cdf_idx"], ref["cdf"]):
                check(name, f"{case} cdf[{i}]", v, res["cdf"][ref["cdf_idx"].index(i)], 5e-13)
            for a, q in zip(ALPHAS, ref["quant"]):
                check(name, f"{case} q({a})", q, res["quant"][ALPHAS.index(a)], 0, exact=True)
    return failed_all


ORDER = ["norm", "char", "weapon", "std", "joint", "nstd", "nstd_cond", "radiance",
         "radiance_seq", "pre50", "tenpull", "longterm"]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # Windows 控制台默认 GBK 会乱码
    refs = build_references()
    tmp = Path(tempfile.gettempdir()) / "parity-ref.json"
    tmp.write_text(json.dumps(refs), encoding="utf-8")

    runner = ["node", str(NODE_RUNNER), str(tmp)]
    proc = subprocess.run(runner, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        print("Node 端失败：")
        print(proc.stderr[-2000:])
        return 2

    failed = compare(refs, json.loads(proc.stdout))

    cases: dict[str, int] = {}
    for ref in refs:
        cases[ref["kind"]] = cases.get(ref["kind"], 0) + 1

    print(f"{'组别':<14}{'用例':>6}{'比对项':>8}{'最大偏差':>16}  结论")
    for name in ORDER:
        g = GROUPS.get(name)
        if not g:
            continue
        parts = []
        if g["prob"]:
            parts.append(f"{g['prob']:.3g}")
        if g["pull"]:
            parts.append(f"{g['pull']:.0f} 抽")
        shown = " + ".join(parts) if parts else "0"
        print(f"{name:<14}{cases.get(name, 0):>6}{g['items']:>8}{shown:>16}  "
              f"{'PASS' if g['failed'] == 0 else 'FAIL'}")
    total_items = sum(g["items"] for g in GROUPS.values())
    print(f"\n{len(refs)} 组用例，{total_items} 项比对，失败 {failed} 项")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
