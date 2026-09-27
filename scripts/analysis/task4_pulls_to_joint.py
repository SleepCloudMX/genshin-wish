#!/usr/bin/env python
"""D组: 任务4 (pulls-to-joint) — 金数分解的耗时随抽数的关系.

站点「金数分布」视图（角色池与武器池）用的算法：给定抽数 P，求（目标数, 歪出数）的联合分布。
金数分解把它拆成「P(恰好 g 金 | P 抽)」与「50/50 标记链」两部分，避免逐抽 DP；本脚本测两者的
耗时，并调用 Node 测站点内核（JavaScript 实现）的同一算法。

输出 speed.png 与 data.json 到 output/analysis/task4-pulls-to-joint/。
逐抽 DP 只测到 P = 500（更慢），站点内核的耗时由 web/dev/bench-pulls-joint.js 给出；
本机没有 Node 时该项留空，不影响其余结果。

使用示例::

    python scripts/analysis/task4_pulls_to_joint.py
    python scripts/analysis/task4_pulls_to_joint.py --runs 5
    python scripts/analysis/task4_pulls_to_joint.py --plot-only
"""

from __future__ import annotations

import argparse
import json as _json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import trim_mean

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from genshin_wish._constants import CHARACTER_POOL, CAPTURE_RADIANCE_WIN_RATE  # noqa: E402
from genshin_wish._gold import build_gold_pdf  # noqa: E402
from genshin_wish.character import CharacterState, pulls_joint_distribution  # noqa: E402

OUTPUT = ROOT / "output" / "analysis" / "task4-pulls-to-joint"
BENCH_JS = ROOT / "web" / "dev" / "bench-pulls-joint.js"
HARD_PITY = CHARACTER_POOL.hard_pity

PULLS = [100, 200, 300, 500, 700, 1000, 1500, 2000, 3000, 5000, 7000, 10000, 20000]
NAIVE_MAX = 500          # 逐抽 DP 只测到这里
RUNS = 3                 # 每个点重复次数
TRIM_FRAC = 0.2
ERROR_BAR = "minmax"

METHOD_COLORS = {
    "split": "#2ca02c",       # 金数分解（Python）
    "split_js": "#1f77b4",    # 金数分解（站点内核，JavaScript）
    "naive": "#d62728",       # 逐抽 DP（Python）
}

METHOD_LABELS = {
    "split": "金数分解（Python）",
    "split_js": "金数分解（JS）",
    "naive": "逐抽 DP（Python）",
}


# ---------------------------------------------------------------------------
# 朴素对照：逐抽正向 DP，状态 (pity, k_miss, 保底) × 计数 (n_up, n_std)
# ---------------------------------------------------------------------------

def naive_pulls_joint(P: int) -> np.ndarray:
    """返回 (n_up, n_std) 的联合概率矩阵；仅供性能对照，规模稍大就跑不动。"""
    p_single = build_gold_pdf(CHARACTER_POOL)
    p_up = CAPTURE_RADIANCE_WIN_RATE
    mu = P / 62.3
    g_cap = int(mu + 6 * math.sqrt(mu)) + 4
    U, S = g_cap + 1, g_cap + 2

    A = np.zeros((HARD_PITY, 4, 2, U, S))            # [pity, k_miss, 保底, n_up, n_std]
    A[0, 0, 0, 0, 0] = 1.0
    qs = p_single[1:].reshape(HARD_PITY, 1, 1, 1, 1)

    for _ in range(P):
        nxt = np.zeros_like(A)
        nxt[1:] += A[:-1] * (1.0 - qs[:-1])          # 未出金：pity + 1
        hit = (A * qs).sum(axis=0)                   # 出金：pity 归零
        for k in range(4):
            nxt[0, k, 0, 1:, :] += hit[k, 1, :-1, :]                  # 保底金必为 UP
            nxt[0, 0, 0, 1:, :] += hit[k, 0, :-1, :] * p_up[k]        # 中
            if k < 3:
                nxt[0, k + 1, 1, :, 1:] += hit[k, 0, :, :-1] * (1.0 - p_up[k])
        A = nxt
    return A.sum(axis=(0, 1, 2))


# ---------------------------------------------------------------------------
# 计时
# ---------------------------------------------------------------------------

def _timed(fn, runs: int) -> list[float]:
    out = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t0) * 1000.0)
    return out


def bench_split(P: int, runs: int) -> list[float]:
    state = CharacterState(guaranteed=False, pity=0, consecutive_loss=0)
    pulls_joint_distribution(state, min(P, 1))       # 预热：建金 PDF 表
    return _timed(lambda: pulls_joint_distribution(state, P), runs)


def bench_naive(P: int, runs: int) -> list[float]:
    return _timed(lambda: naive_pulls_joint(P), runs)


def bench_js(pulls: list[int], runs: int) -> dict | None:
    """调用 Node 测站点内核；没有 Node 或脚本失败时返回 None。"""
    try:
        proc = subprocess.run(
            ["node", str(BENCH_JS), f"--runs={runs}", "--pulls=" + ",".join(str(p) for p in pulls)],
            capture_output=True, text=True, encoding="utf-8", timeout=600,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f"  跳过 JS 基准：{exc}")
        return None
    if proc.returncode != 0:
        print("  跳过 JS 基准：node 退出码 " + str(proc.returncode))
        print("  " + (proc.stderr or "").strip()[:300])
        return None
    return _json.loads(proc.stdout)


def _stats(raw: list[float]) -> dict:
    arr = np.sort(np.array(raw))
    n = len(arr)
    cut = int(n * TRIM_FRAC)
    if cut * 2 >= n:
        cut = (n - 1) // 2
    trimmed = arr[cut: n - cut] if n - cut > cut else arr
    return {
        "time_ms": float(trim_mean(arr, TRIM_FRAC)) if n >= 5 else float(np.mean(arr)),
        "time_min": float(np.min(trimmed)),
        "time_max": float(np.max(trimmed)),
        "time_all": [float(v) for v in raw],
    }


def collect(runs: int, pulls: list[int], naive_max: int) -> dict:
    data: dict = {
        "meta": {"runs": runs, "trim": TRIM_FRAC, "error_bar": ERROR_BAR,
                 "platform": sys.platform},
        "pulls": pulls,
        "split": {},
        "naive": {},
    }

    print("金数分解（Python）…", flush=True)
    for P in pulls:
        data["split"][str(P)] = _stats(bench_split(P, runs))
        print(f"  P={P:>6}  {data['split'][str(P)]['time_ms']:8.3f} ms", flush=True)

    print(f"逐抽 DP（Python，P ≤ {naive_max}）…", flush=True)
    for P in [p for p in pulls if p <= naive_max]:
        data["naive"][str(P)] = _stats(bench_naive(P, max(1, runs - 1)))
        print(f"  P={P:>6}  {data['naive'][str(P)]['time_ms']:8.3f} ms", flush=True)

    print("金数分解（JS，站点内核）…", flush=True)
    js = bench_js(pulls, runs)
    if js:
        data["split_js"] = {str(P): _stats(js["character"][str(P)]) for P in pulls}
        data["weapon_js"] = {str(P): _stats(js["weapon"][str(P)]) for P in pulls}
        for P in pulls:
            print(f"  P={P:>6}  角色池 {data['split_js'][str(P)]['time_ms']:8.3f} ms"
                  f"  武器池 {data['weapon_js'][str(P)]['time_ms']:8.3f} ms", flush=True)
    else:
        data["split_js"] = {}
        data["weapon_js"] = {}
    return data


# ---------------------------------------------------------------------------
# 绘图
# ---------------------------------------------------------------------------

def plot_speed(data: dict) -> None:
    from matplotlib import pyplot as plt
    from genshin_wish.viz._base import setup_style
    setup_style()
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(10, 6))
    for name in ["split", "split_js", "naive"]:
        series = data.get(name) or {}
        xs, ys, los, his = [], [], [], []
        for P in data["pulls"]:
            entry = series.get(str(P))
            if not entry:
                continue
            xs.append(P)
            ys.append(entry["time_ms"])
            los.append(entry["time_min"])
            his.append(entry["time_max"])
        if not xs:
            continue
        line = ax.plot(xs, ys, "o-", markersize=4, label=METHOD_LABELS[name],
                       color=METHOD_COLORS[name])[0]
        ax.fill_between(xs, los, his, alpha=0.15, color=line.get_color())

    ax.set_xlabel("抽数 $P$")
    ax.set_ylabel("time (ms)")
    ax.set_title("Task 4: pulls → (targets, off-target) joint distribution")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "speed.png", dpi=200)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plot-only", action="store_true",
                    help="Skip computation, regenerate plots from data.json")
    ap.add_argument("--runs", type=int, default=RUNS)
    ap.add_argument("--pulls", default="",
                    help="Comma-separated pull counts (default: 100…20000)")
    ap.add_argument("--naive-max", type=int, default=NAIVE_MAX)
    args = ap.parse_args()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    data_path = OUTPUT / "data.json"

    if args.plot_only:
        print(f"Plot-only mode — loading {data_path} ...", flush=True)
        data = _json.loads(data_path.read_text(encoding="utf-8"))
    else:
        pulls = [int(p) for p in args.pulls.split(",")] if args.pulls else PULLS
        data = collect(args.runs, pulls, args.naive_max)

    data_path.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    plot_speed(data)
    print(f"Done — {OUTPUT}")


if __name__ == "__main__":
    main()
