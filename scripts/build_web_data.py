#!/usr/bin/env python
"""把实验数据导出给站点：output/analysis/*/data.json → web/data/analysis.js

站点运行时只读生成的 JS 文件，不依赖 Python；重跑实验后执行本脚本即可更新。
截尾均值、误差带与拟合参数直接复用 task1 分析脚本里的实现，保证与实验图口径一致。

用法::

    python scripts/build_web_data.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / "output" / "analysis"
ANALYSIS_SCRIPTS = ROOT / "scripts" / "analysis"
OUT = ROOT / "web" / "data" / "analysis.js"
TRIM = 0.2  # 与分析脚本的 TRIM_FRAC 一致


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


task1 = _load("task1_analysis", ANALYSIS_SCRIPTS / "task1_n_up_to_pulls.py")


def _round(x: float | None, nd: int) -> float | None:
    return None if x is None else round(float(x), nd)


def speed_series(per_n: dict, ns: list[int]) -> dict:
    """每个 n 的截尾均值与误差带（与 _plot_speed 的 _draw_speed 一致）。"""
    time, lo, hi = [], [], []
    for n in ns:
        entry = per_n.get(str(n)) or {}
        raw = entry.get("time_all")
        if not raw:
            time.append(None)
            lo.append(None)
            hi.append(None)
            continue
        st = task1._trimmed_stats(raw, TRIM)
        time.append(_round(st["mean"], 4))
        lo.append(_round(st["min"], 4))
        hi.append(_round(st["max"], 4))
    return {"time": time, "lo": lo, "hi": hi}


def fit_params(name: str, ns: list[int], series: dict) -> dict | None:
    """与 _add_fit_lines 相同的拟合规则：dp-path 指数，其余幂律。"""
    pts = [(n, t) for n, t in zip(ns, series["time"]) if t is not None]
    if len(pts) < 3:
        return None
    xs = np.array([p[0] for p in pts], dtype=float)
    ys = np.array([p[1] for p in pts], dtype=float)

    if name == "dp-path":
        c0 = np.polyfit(xs, np.log(np.maximum(ys, 1e-9)), 1)
        popt, _ = task1.curve_fit(
            task1._exp_offset, xs, ys, p0=[c0[0], c0[1], 0.0],
            bounds=([0, -np.inf, 0], [np.inf, np.inf, ys[0]]),
            method="trf", maxfev=10000,
        )
        a, b, c = (float(v) for v in popt)
        return {"kind": "exp", "a": round(a, 6), "b": round(b, 4),
                "c": round(c, 4), "from": 7}

    if name in ("dp-golds", "dp-state"):
        mask = xs >= task1.FIT_N_MIN
        start = int(xs[mask][0])
    else:
        mask = np.ones(len(xs), dtype=bool)
        start = int(xs[0])
    k, b = np.polyfit(np.log(xs[mask]), np.log(ys[mask]), 1)
    return {"kind": "power", "k": round(float(k), 4), "b": round(float(b), 4),
            "from": start}


def clt_errors(data: dict, ns: list[int]) -> dict:
    """以 dp-state 的分位为基准，计算 CLT 的绝对/相对/每 UP 误差。"""
    quantiles = task1.QUANTILES
    out = {"n": [], "abs": {}, "rel": {}, "perUp": {}}
    for q in quantiles:
        key = str(q)
        out["abs"][key] = []
        out["rel"][key] = []
        out["perUp"][key] = []
    used_n = []
    for n in ns:
        exact = data["dp-state"].get(str(n))
        approx = data["CLT"].get(str(n))
        if not exact or not approx or exact.get("quantiles") is None:
            continue
        used_n.append(n)
        for q in quantiles:
            key = str(q)
            e = task1._q(exact, q)
            c = task1._q(approx, q)
            out["abs"][key].append(_round(abs(e - c), 4))
            out["rel"][key].append(_round(abs(e - c) / max(e, 1.0) * 100, 6))
            out["perUp"][key].append(_round(abs(e / n - c / n), 5))
    out["n"] = used_n
    return out


def main() -> None:
    t1 = json.loads((ANALYSIS / "task1-n_up-to-pulls" / "data.json").read_text(encoding="utf-8"))
    t2 = json.loads((ANALYSIS / "task2-n_up-n_std-to-pulls" / "data.json").read_text(encoding="utf-8"))
    t3 = json.loads((ANALYSIS / "task3-n_up-to-n_std" / "data.json").read_text(encoding="utf-8"))
    t4 = json.loads((ANALYSIS / "task4-pulls-to-joint" / "data.json").read_text(encoding="utf-8"))

    n1 = sorted(int(k) for k in t1["dp-state"])
    methods1 = ["dp-pulls", "dp-path", "dp-state", "dp-golds", "CLT"]
    series1 = {}
    for m in methods1:
        s = speed_series(t1[m], n1)
        s["fit"] = fit_params(m, n1, s)
        series1[m] = s

    n2 = sorted(int(k) for k in t2["dp-golds"])
    series2 = {m: speed_series(t2[m], n2) for m in ["dp-path", "dp-golds"]}

    n3 = sorted(int(k) for k in t3["dp-golds"])
    series3 = {m: speed_series(t3[m], n3) for m in ["dp-path", "dp-golds"]}

    # Task 3 的 n=20 分布：两种方法的分布并列画出，用于互相印证
    dist_path = t3["dp-path"]["20"]["n_std_dist"]
    dist_golds = t3["dp-golds"]["20"]["n_std_dist"]
    keys = sorted(int(k) for k in dist_golds)
    nstd20 = {
        "nstd": keys,
        "dp-path": [_round(dist_path.get(str(k), 0.0), 8) for k in keys],
        "dp-golds": [_round(dist_golds[str(k)], 8) for k in keys],
    }

    # Task 4：给定抽数 → 联合分布，三条线分别对应 Python 实现、站点内核（JS）与朴素逐抽递推
    n4 = t4["pulls"]
    series4 = {}
    for label, key in [("金数分解（Python）", "split"), ("金数分解（浏览器）", "split_js"),
                       ("逐抽递推（Python）", "naive")]:
        s = speed_series(t4.get(key) or {}, n4)
        s["fit"] = fit_params(key, n4, s)
        series4[label] = s

    payload = {
        "meta": {
            "generated": date.today().isoformat(),
            "trim": TRIM,
            "source": ("output/analysis/task1-n_up-to-pulls, task2-n_up-n_std-to-pulls, "
                       "task3-n_up_to-n_std, task4-pulls-to-joint"),
        },
        "quantiles": task1.QUANTILES,
        "colors": task1.METHOD_COLORS,
        "fitNMin": task1.FIT_N_MIN,
        "task1": {"n": n1, "series": series1, "clt": clt_errors(t1, n1)},
        "task2": {"n": n2, "series": series2},
        "task3": {"n": n3, "series": series3, "nstd20": nstd20},
        "task4": {"n": n4, "series": series4, "runs": t4["meta"]["runs"]},
        "colors4": {"金数分解（Python）": "#2ca02c", "金数分解（浏览器）": "#1f77b4",
                    "逐抽递推（Python）": "#d62728"},
    }

    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "/* 由 scripts/build_web_data.py 从 output/analysis/ 的 data.json 生成，请勿手改。\n"
        "   重跑实验后执行 python scripts/build_web_data.py 更新。 */\n"
        "globalThis.__WISH_ANALYSIS__ = " + body + ";\n",
        encoding="utf-8",
    )
    kb = OUT.stat().st_size / 1024
    print(f"已写出 {OUT.relative_to(ROOT)}（{kb:.0f} KB）")


if __name__ == "__main__":
    main()
