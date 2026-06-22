#!/usr/bin/env python
"""Generate README.md for each task's output/analysis/task*/ directory."""

import json
import sys
from pathlib import Path

OUTPUT = Path("output/analysis")


def _load(task_dir: str) -> dict:
    p = OUTPUT / task_dir / "data.json"
    if not p.exists():
        raise FileNotFoundError(f"{p} not found — run the benchmark first")
    return json.loads(p.read_text(encoding="utf-8"))


def _sn(f, v, default="—") -> str:
    """Format a value that might be None."""
    if v is None:
        return default
    return f"{v:{f}}"


def _row(label: str, *cells: str) -> str:
    return "| " + label + " | " + " | ".join(str(c) for c in cells) + " |"


# ---------------------------------------------------------------------------
# Task 1
# ---------------------------------------------------------------------------


def _task1() -> None:
    d = _load("task1-n_up-to-pulls")
    lines: list[str] = []
    a = lines.append

    a("# Task 1: n_up-to-pulls")
    a("")
    a("方法：`dp-pulls` (方案1) / `dp-path` (方案2) / `dp-state` (方案3) "
      "/ `dp-golds` (方案4) / `CLT`。")
    a(f"去尾比例：20%。误差带：min-max（trimmed）。")
    a("")

    # --- Expected pulls table ---
    n_keys = [1, 5, 10, 20, 50, 100, 200, 500]
    a("## 期望抽数")
    a("")
    a("| $n_\\text{up}$ | " + " | ".join(str(n) for n in n_keys) + " |")
    a("|------|" + "|".join("------" for _ in n_keys) + "|")
    for m in ["dp-pulls", "dp-path", "dp-state", "dp-golds"]:
        vals = []
        for n in n_keys:
            e = d[m].get(str(n), {}).get("expected")
            vals.append(_sn(".0f", e))
        a(_row(m, *vals))
    a("")

    # CLT error summary
    a("## CLT 近似误差")
    a("")
    a("混合矩 CLT：首 UP 用初始 k_miss 矩，剩余用稳态矩。"
      "误差为 $|\\text{exact} - \\text{clt}|$（总抽数）。")
    a("")
    q_keys = [0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99]
    for n_label in [50, 100, 500]:
        sn = str(n_label)
        a(f"### $n = {n_label}$")
        a("")
        a("| 分位点 | exact | CLT | 误差 (pulls) | 相对误差 |")
        a("|--------|-------|-----|-------------|---------|")
        for q in q_keys:
            qe = d["dp-state"][sn]["quantiles"].get(str(q), d["dp-state"][sn]["quantiles"].get(q, 0))
            qc = d["CLT"][sn]["quantiles"].get(str(q), d["CLT"][sn]["quantiles"].get(q, 0))
            err = abs(qe - qc)
            rel = err / qe * 100 if qe > 0 else 0
            a(f"| {int(q*100)}% | {qe} | {qc} | {err} | {rel:.3f}% |")
        a("")
    a("")

    # Speed summary
    a("## 速度 (n=500)")
    a("")
    a("| 方法 | trimmed mean |")
    a("|------|-------------|")
    for m in ["dp-pulls", "dp-path", "dp-state", "dp-golds", "CLT"]:
        t = d[m].get("500", {}).get("time_ms")
        if t is not None:
            a(f"| {m} | {t:.0f} ms |")
        else:
            # find max n for this method
            ns = sorted([int(k) for k in d[m] if d[m][k].get("time_ms") is not None])
            if ns:
                t_n = d[m][str(ns[-1])]["time_ms"]
                a(f"| {m} | {t_n:.0f} ms (n={ns[-1]}) |")
    a("")

    (OUTPUT / "task1-n_up-to-pulls" / "README.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Task 2
# ---------------------------------------------------------------------------


def _task2() -> None:
    d = _load("task2-n_up-n_std-to-pulls")
    lines: list[str] = []
    a = lines.append

    a("# Task 2: n_up-n_std-to-pulls")
    a("")
    a("方法：`dp-path` (方案2) / `dp-golds` (方案4)。"
      "验证方案4在条件常驻数分布上的正确性。")
    a("")

    # Expected comparison at selected n_up, n_std
    a("## 期望值一致性")
    a("")
    keys = sorted([int(k) for k in d["dp-path"]], key=int)
    # Pick a few key n_up values where dp-path data exists
    sample_ns = [k for k in [10, 15, 20] if k in keys]
    a("| $n_\\text{up}$ | $n_\\text{std}$ | dp-path | dp-golds |")
    a("|------|------|------|------|")
    for n in sample_ns:
        sn = str(n)
        pv = d["dp-path"][sn]["n_std_values"]
        gv = d["dp-golds"][sn]["n_std_values"]
        if pv is None or gv is None:
            continue
        # pick 3 representative n_std values
        std_keys = sorted([int(k) for k in pv], key=int)
        for ns in std_keys[:3]:
            pe = pv[str(ns)]["expected"]
            ge = gv[str(ns)]["expected"]
            a(f"| {n} | {ns} | {pe:.1f} | {ge:.1f} |")
    a("")

    # Speed
    a("## 速度")
    a("")
    a("| 方法 | $n=10$ | $n=20$ | $n=30$ |")
    a("|------|--------|--------|--------|")
    for m in ["dp-path", "dp-golds"]:
        ts = []
        for n in [10, 20]:
            t = d[m].get(str(n), {}).get("time_ms")
            ts.append(_sn(".2f", t, "—"))
        t30 = d[m].get("30", {}).get("time_ms")
        ts.append(_sn(".2f", t30, "—"))
        a(_row(m, *ts))
    a("")
    a(f"dp-path 上限：n=20（$2^{{20}} \\approx 10^6$ 条序列），"
      f"n=20 耗时 {d['dp-path']['20']['time_ms']:.0f} ms。"
      f"dp-golds 在 n=30 耗时 {d['dp-golds']['30']['time_ms']:.0f} ms。")
    a("")

    (OUTPUT / "task2-n_up-n_std-to-pulls" / "README.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Task 3
# ---------------------------------------------------------------------------


def _task3() -> None:
    d = _load("task3-n_up-to-n_std")
    lines: list[str] = []
    a = lines.append

    a("# Task 3: n_up-to-n_std")
    a("")
    a("方法：`dp-path` (方案2) / `dp-golds` (方案4)。"
      "验证方案4在常驻数边际分布 $P(n_\\text{std})$ 上的正确性。")
    a("")

    # Max difference for key n_up
    a("## 正确性验证")
    a("")
    keys = sorted([int(k) for k in d["dp-path"] if d["dp-path"][str(k)]["n_std_dist"] is not None])
    a("| $n_\\text{up}$ | $\\max\\|\\Delta P\\|$ | $E[n_\\text{std}]$ (dp-golds) |")
    a("|------|------|------|")
    for n in [5, 10, 20] if 20 in keys else keys:
        sn = str(n)
        if sn not in d["dp-path"] or d["dp-path"][sn]["n_std_dist"] is None:
            continue
        p_dist = d["dp-path"][sn]["n_std_dist"]
        g_dist = d["dp-golds"][sn]["n_std_dist"]
        max_diff = max(
            abs(p_dist.get(k, 0) - g_dist.get(k, 0))
            for k in set(p_dist) | set(g_dist)
        )
        exp_nstd = d["dp-golds"][sn]["expected_n_std"]
        a(f"| {n} | {max_diff:.2e} | {exp_nstd:.4f} |")
    a("")

    # Speed
    a("## 速度")
    a("")
    a("| 方法 | $n=10$ | $n=50$ | $n=100$ |")
    a("|------|--------|--------|--------|")
    for m in ["dp-path", "dp-golds"]:
        ts = []
        for n in [10, 50]:
            t = d[m].get(str(n), {}).get("time_ms")
            ts.append(_sn(".2f", t, "—"))
        t100 = d[m].get("100", {}).get("time_ms")
        ts.append(_sn(".2f", t100, "—"))
        a(_row(m, *ts))
    a("")

    a(f"dp-path 上限 n=20（$2^{{20}}$ 条序列），"
      f"耗时 {d['dp-path']['20']['time_ms']:.0f} ms。"
      f"dp-golds 在 n=100 耗时 {d['dp-golds']['100']['time_ms']:.0f} ms。"
      f"任务3是三个任务中最轻量的——仅整数计数，无PDF卷积。")
    a("")

    (OUTPUT / "task3-n_up-to-n_std" / "README.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("1", "2", "3"):
        print("Usage: python write_readme.py {1|2|3}")
        sys.exit(1)
    {"1": _task1, "2": _task2, "3": _task3}[sys.argv[1]]()
    print(f"Done — {OUTPUT}/task{sys.argv[1]}-*/README.md")
