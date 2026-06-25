"""genshin-wish Gradio UI"""

from __future__ import annotations

import gradio as gr
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from genshin_wish import CharacterState, up_distribution, stable_up_distribution
from genshin_wish.character import (
    n_std_conditional_pulls,
    n_std_distribution,
    radiance_distribution,
)
from genshin_wish.joint import joint_distribution
from genshin_wish.standard import StandardState, standard_distribution
from genshin_wish.viz._base import setup_style
from genshin_wish.weapon import WeaponState, WeaponTarget, weapon_up_distribution

setup_style()

# ═══════════════════════════════════════════════════════════
# helpers
# ═══════════════════════════════════════════════════════════

FIG_SIZE = (7, 4.5)
LINE_COLOR = "#4C72B0"


def _cdf_fig(cdf: np.ndarray, title: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(np.arange(len(cdf)), cdf, linewidth=1.5, color=LINE_COLOR)
    ax.set_title(title)
    ax.set_xlabel("抽数")
    ax.set_ylabel("达成概率")
    ax.set_ylim(0, 1.02)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.grid(True, alpha=0.25, linestyle="--")
    fig.tight_layout()
    return fig


def _pdf_fig(pdf: np.ndarray, title: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(np.arange(len(pdf)), pdf, linewidth=1.5, color="#55A868")
    ax.set_title(title)
    ax.set_xlabel("抽数")
    ax.set_ylabel("概率密度")
    ax.grid(True, alpha=0.25, linestyle="--")
    fig.tight_layout()
    return fig


# ═══════════════════════════════════════════════════════════
# callbacks
# ═══════════════════════════════════════════════════════════

def _char_callback(n_up, guaranteed, pity, loss, stable, pulls_raw, q):
    state = CharacterState(guaranteed=bool(guaranteed), pity=int(pity), consecutive_loss=int(loss))
    dist = stable_up_distribution(int(n_up)) if stable else up_distribution(state, int(n_up))

    prob = dist.probability(int(pulls_raw)) if pulls_raw is not None and pulls_raw > 0 else None
    q_pulls = dist.quantile(float(q)) if q is not None else None

    tag = f"n_up={int(n_up)}, loss={int(loss)}, pity={int(pity)}"
    tag += ", 稳态" if stable else ""
    return (
        f"达成概率：**{prob:.2%}**" if prob is not None else "",
        f"所需抽数：**{q_pulls} 抽**" if q_pulls is not None else "",
        _cdf_fig(dist.cdf, f"角色池 CDF ({tag})"),
        _pdf_fig(dist.pdf, f"角色池 PDF ({tag})"),
    )


def _weapon_callback(count_a, ep, pity, prev_std, pulls_raw, q):
    state = WeaponState(pity=int(pity), epitomized_points=int(ep), prev_standard=bool(prev_std))
    target = WeaponTarget(count_a=int(count_a))
    dist = weapon_up_distribution(state, target)

    prob = dist.probability(int(pulls_raw)) if pulls_raw is not None and pulls_raw > 0 else None
    q_pulls = dist.quantile(float(q)) if q is not None else None

    tag = f"count={int(count_a)}, ep={int(ep)}, pity={int(pity)}"
    return (
        f"达成概率：**{prob:.2%}**" if prob is not None else "",
        f"所需抽数：**{q_pulls} 抽**" if q_pulls is not None else "",
        _cdf_fig(dist.cdf, f"武器池 CDF ({tag})"),
        _pdf_fig(dist.pdf, f"武器池 PDF ({tag})"),
    )


def _joint_callback(char_up, weapon_count, char_loss, char_guaranteed, char_pity,
                    weapon_pity, weapon_ep, pulls_raw, q):
    cs = CharacterState(guaranteed=bool(char_guaranteed), pity=int(char_pity),
                        consecutive_loss=int(char_loss))
    ws = WeaponState(pity=int(weapon_pity), epitomized_points=int(weapon_ep))
    wt = WeaponTarget(count_a=int(weapon_count))
    dist = joint_distribution(cs, int(char_up), ws, wt)

    prob = dist.probability(int(pulls_raw)) if pulls_raw is not None and pulls_raw > 0 else None
    q_pulls = dist.quantile(float(q)) if q is not None else None

    tag = f"C{int(char_up)}+W{int(weapon_count)}, loss={int(char_loss)}"
    return (
        f"达成概率：**{prob:.2%}**" if prob is not None else "",
        f"所需抽数：**{q_pulls} 抽**" if q_pulls is not None else "",
        _cdf_fig(dist.cdf, f"联合 CDF ({tag})"),
        _pdf_fig(dist.pdf, f"联合 PDF ({tag})"),
    )


def _standard_callback(n_gold, pity, pulls_raw, q):
    state = StandardState(pity=int(pity))
    dist = standard_distribution(state, int(n_gold))

    prob = dist.probability(int(pulls_raw)) if pulls_raw is not None and pulls_raw > 0 else None
    q_pulls = dist.quantile(float(q)) if q is not None else None

    tag = f"n_gold={int(n_gold)}, pity={int(pity)}"
    return (
        f"达成概率：**{prob:.2%}**" if prob is not None else "",
        f"所需抽数：**{q_pulls} 抽**" if q_pulls is not None else "",
        _cdf_fig(dist.cdf, f"常驻池 CDF ({tag})"),
        _pdf_fig(dist.pdf, f"常驻池 PDF ({tag})"),
    )


def _nstd_callback(n_up, loss, guaranteed):
    state = CharacterState(guaranteed=bool(guaranteed), consecutive_loss=int(loss))
    n_up = int(n_up)
    nstd_dist = n_std_distribution(state, n_up)
    cond_dists = n_std_conditional_pulls(state, n_up)

    # bar chart
    fig_bar, ax = plt.subplots(figsize=FIG_SIZE)
    keys = sorted(nstd_dist.keys())
    probs = [nstd_dist[k] for k in keys]
    ax.bar(keys, probs, color="#4C72B0", edgecolor="white", width=0.8)
    for k, p in zip(keys, probs):
        if p > 0:
            ax.text(k, p + max(probs) * 0.015, f"{p:.1%}",
                    ha="center", va="bottom", fontsize=8)
    ax.set_xlabel("$n_\\mathrm{std}$")
    ax.set_ylabel("概率")
    ax.set_title(f"常驻角色数量分布 (n_up={n_up}, loss={int(loss)})")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    fig_bar.tight_layout()

    # overlaid conditional PDF
    fig_pdf, ax_pdf = plt.subplots(figsize=FIG_SIZE)
    top_items = sorted(nstd_dist.items(), key=lambda kv: -kv[1])[:10]
    for n_std, _ in sorted(top_items):
        if n_std in cond_dists:
            ax_pdf.plot(cond_dists[n_std].pdf, linewidth=1.0, alpha=0.75,
                        label=f"n_std={n_std}")
    ax_pdf.set_xlabel("抽数")
    ax_pdf.set_ylabel("概率密度")
    ax_pdf.set_title(f"条件抽数分布 (n_up={n_up}, loss={int(loss)})")
    ax_pdf.legend(fontsize=7, ncol=2)
    ax_pdf.grid(True, alpha=0.25, linestyle="--")
    fig_pdf.tight_layout()

    return fig_bar, fig_pdf


def _radiance_callback(n_up, loss, guaranteed):
    state = CharacterState(guaranteed=bool(guaranteed), consecutive_loss=int(loss))
    n_up = int(n_up)
    dist = radiance_distribution(state, n_up)

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    keys = sorted(dist.keys())
    probs = [dist[k] for k in keys]
    ax.bar(keys, probs, color="#DD8452", edgecolor="white", width=0.8)
    for k, p in zip(keys, probs):
        if p > 0.001:
            ax.text(k, p + max(probs) * 0.015, f"{p:.1%}",
                    ha="center", va="bottom", fontsize=9)
    ax.set_xlabel("捕获明光次数")
    ax.set_ylabel("概率")
    ax.set_title(f"捕获明光次数分布 (n_up={n_up}, loss={int(loss)})")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    fig.tight_layout()

    return fig


# ═══════════════════════════════════════════════════════════
# param builders
# ═══════════════════════════════════════════════════════════

def _build_char_params():
    n_up = gr.Slider(1, 180, 7, step=1, label="目标 UP 数（含本体）")
    pity = gr.Slider(0, 89, 0, step=1, label="已垫抽数")
    loss = gr.Slider(0, 3, 0, step=1, label="连歪次数")
    guaranteed = gr.Checkbox(False, label="大保底")
    stable = gr.Checkbox(False, label="稳态分布")
    return n_up, pity, loss, guaranteed, stable


def _build_weapon_params():
    count_a = gr.Slider(1, 5, 1, step=1, label="目标武器数")
    ep = gr.Slider(0, 2, 0, step=1, label="命定值")
    pity = gr.Slider(0, 79, 0, step=1, label="已垫抽数")
    prev_std = gr.Checkbox(False, label="上一金为常驻")
    return count_a, ep, pity, prev_std


def _build_joint_params():
    char_up = gr.Slider(1, 180, 7, step=1, label="角色目标 UP 数")
    weapon_count = gr.Slider(1, 5, 1, step=1, label="武器目标数")
    char_loss = gr.Slider(0, 3, 0, step=1, label="角色连歪次数")
    char_guaranteed = gr.Checkbox(False, label="角色大保底")
    char_pity = gr.Slider(0, 89, 0, step=1, label="角色已垫抽数")
    weapon_pity = gr.Slider(0, 79, 0, step=1, label="武器已垫抽数")
    weapon_ep = gr.Slider(0, 2, 0, step=1, label="武器命定值")
    return char_up, weapon_count, char_loss, char_guaranteed, char_pity, weapon_pity, weapon_ep


def _build_query_row():
    """Return (pulls_input, q_slider, prob_md, pulls_md)."""
    with gr.Column(scale=1):
        pulls_input = gr.Number(None, label="输入抽数 → 查达成概率", precision=0, minimum=0)
        prob_md = gr.Markdown("")
    with gr.Column(scale=1):
        q_slider = gr.Slider(0, 1, 0.5, label="输入分位点 → 查所需抽数")
        pulls_md = gr.Markdown("")
    return pulls_input, q_slider, prob_md, pulls_md


def _build_result_plots():
    """Return (cdf_plot, pdf_plot)."""
    with gr.Column(scale=1):
        cdf_plot = gr.Plot(label="CDF")
    with gr.Column(scale=1):
        pdf_plot = gr.Plot(label="PDF")
    return cdf_plot, pdf_plot


# ═══════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════

def main():
    with gr.Blocks(title="genshin-wish") as demo:
        gr.Markdown("# genshin-wish 概率查询")

        # ── Tab 1: 角色池 ──────────────────────────────
        with gr.Tab("角色池"):
            with gr.Row(equal_height=False):
                with gr.Column(scale=1):
                    n_up, pity, loss, guaranteed, stable = _build_char_params()
                with gr.Column(scale=2):
                    pulls_in_1, q_slider_1, prob_md_1, pulls_md_1 = _build_query_row()
                    btn1 = gr.Button("计算", variant="primary")
            cdf_1, pdf_1 = _build_result_plots()
            btn1.click(
                fn=_char_callback,
                inputs=[n_up, guaranteed, pity, loss, stable, pulls_in_1, q_slider_1],
                outputs=[prob_md_1, pulls_md_1, cdf_1, pdf_1],
            )

        # ── Tab 2: 武器池 ──────────────────────────────
        with gr.Tab("武器池"):
            with gr.Row(equal_height=False):
                with gr.Column(scale=1):
                    count_a, ep, w_pity, prev_std = _build_weapon_params()
                with gr.Column(scale=2):
                    pulls_in_2, q_slider_2, prob_md_2, pulls_md_2 = _build_query_row()
                    btn2 = gr.Button("计算", variant="primary")
            cdf_2, pdf_2 = _build_result_plots()
            btn2.click(
                fn=_weapon_callback,
                inputs=[count_a, ep, w_pity, prev_std, pulls_in_2, q_slider_2],
                outputs=[prob_md_2, pulls_md_2, cdf_2, pdf_2],
            )

        # ── Tab 3: 联合计算 ────────────────────────────
        with gr.Tab("联合计算"):
            with gr.Row(equal_height=False):
                with gr.Column(scale=1):
                    gr.Markdown("### 角色池")
                    char_up, weapon_count, char_loss, char_guaranteed, \
                        char_pity, weapon_pity, weapon_ep = _build_joint_params()
                with gr.Column(scale=1):
                    gr.Markdown("### 武器池")
                    # weapon params already captured via weapon_pity, weapon_ep
                    gr.Markdown("")  # spacer
                with gr.Column(scale=2):
                    pulls_in_3, q_slider_3, prob_md_3, pulls_md_3 = _build_query_row()
                    btn3 = gr.Button("计算", variant="primary")
            cdf_3, pdf_3 = _build_result_plots()
            btn3.click(
                fn=_joint_callback,
                inputs=[char_up, weapon_count, char_loss, char_guaranteed, char_pity,
                        weapon_pity, weapon_ep, pulls_in_3, q_slider_3],
                outputs=[prob_md_3, pulls_md_3, cdf_3, pdf_3],
            )

        # ── Tab 4: 常驻池 ──────────────────────────────
        with gr.Tab("常驻池"):
            with gr.Row(equal_height=False):
                with gr.Column(scale=1):
                    n_gold = gr.Slider(1, 50, 5, step=1, label="目标五星数")
                    std_pity = gr.Slider(0, 89, 0, step=1, label="已垫抽数")
                with gr.Column(scale=2):
                    pulls_in_4, q_slider_4, prob_md_4, pulls_md_4 = _build_query_row()
                    btn4 = gr.Button("计算", variant="primary")
            cdf_4, pdf_4 = _build_result_plots()
            btn4.click(
                fn=_standard_callback,
                inputs=[n_gold, std_pity, pulls_in_4, q_slider_4],
                outputs=[prob_md_4, pulls_md_4, cdf_4, pdf_4],
            )

        # ── Tab 5: 常驻分布 ────────────────────────────
        with gr.Tab("常驻分布"):
            with gr.Row():
                with gr.Column(scale=1):
                    ns_n_up = gr.Slider(1, 30, 7, step=1, label="目标 UP 数")
                    ns_loss = gr.Slider(0, 3, 0, step=1, label="连歪次数")
                    ns_guaranteed = gr.Checkbox(False, label="大保底")
                with gr.Column(scale=2):
                    btn5 = gr.Button("计算", variant="primary")
            with gr.Row():
                ns_bar = gr.Plot(label="常驻数量分布")
                ns_pdf = gr.Plot(label="条件抽数 PDF")
            btn5.click(
                fn=_nstd_callback,
                inputs=[ns_n_up, ns_loss, ns_guaranteed],
                outputs=[ns_bar, ns_pdf],
            )

        # ── Tab 6: 捕获明光 ────────────────────────────
        with gr.Tab("捕获明光"):
            with gr.Row():
                with gr.Column(scale=1):
                    rd_n_up = gr.Slider(1, 200, 7, step=1, label="目标 UP 数")
                    rd_loss = gr.Slider(0, 3, 0, step=1, label="连歪次数")
                    rd_guaranteed = gr.Checkbox(False, label="大保底")
                with gr.Column(scale=2):
                    btn6 = gr.Button("计算", variant="primary")
            rd_plot = gr.Plot(label="捕获明光次数分布")
            btn6.click(
                fn=_radiance_callback,
                inputs=[rd_n_up, rd_loss, rd_guaranteed],
                outputs=[rd_plot],
            )

    demo.launch()


if __name__ == "__main__":
    main()
