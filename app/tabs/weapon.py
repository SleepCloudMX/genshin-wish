"""武器池 Tab — CDF / PDF / 分位点表 / 双向查询."""

from __future__ import annotations

import gradio as gr

from app import plot_utils
from genshin_wish.weapon import WeaponState, WeaponTarget, weapon_up_distribution


def _callback(count_a, ep, pity, prev_std, pulls_raw, q):
    state = WeaponState(pity=int(pity), epitomized_points=int(ep),
                        prev_standard=bool(prev_std))
    target = WeaponTarget(count_a=int(count_a))
    dist = weapon_up_distribution(state, target)
    exp_val = dist.expected

    prob = dist.probability(int(pulls_raw)) if pulls_raw is not None and pulls_raw > 0 else None
    q_pulls = dist.quantile(float(q)) if q is not None else None

    tag = f"count={int(count_a)}, ep={int(ep)}"
    cdf_title = f"武器池 CDF ({tag})"
    pdf_title = f"武器池 PDF ({tag})"

    pulls_txt = (
        f"所需抽数：**{q_pulls} 抽**  \n期望抽数：**{exp_val:.1f} 抽**"
        if q_pulls is not None
        else f"期望抽数：**{exp_val:.1f} 抽**"
    )

    return (
        f"达成概率：**{prob:.2%}**" if prob is not None else "",
        pulls_txt,
        plot_utils.plot_cdf(dist.cdf, cdf_title),
        plot_utils.plot_pdf(dist.pdf, pdf_title),
        plot_utils.make_pct_table(dist.cdf),
    )


def build_tab():
    with gr.Tab("武器池"):
        gr.Markdown(
            "查询定轨武器所需的抽数分布。定轨过程中不取消定轨。"
            "支持双向查询：输入抽数查概率，或输入分位点查所需抽数。"
        )

        with gr.Row():
            with gr.Column(scale=1):
                count_a = gr.Slider(1, 5, 1, step=1, label="目标武器数")
                ep = gr.Slider(0, 2, 0, step=1, label="命定值")
            with gr.Column(scale=1):
                with gr.Accordion("高级设置", open=False):
                    pity = gr.Slider(0, 79, 0, step=1, label="已垫抽数")
                    prev_std = gr.Checkbox(False, label="上一金为常驻")

        with gr.Row():
            with gr.Column(scale=1):
                pulls_in = gr.Number(None, label="输入抽数 → 查达成概率", precision=0, minimum=0)
                prob_md = gr.Markdown("")
            with gr.Column(scale=1):
                q_slider = gr.Slider(0, 1, 0.5, label="输入分位点 → 查所需抽数")
                pulls_md = gr.Markdown("")

        btn = gr.Button("计算", variant="primary")

        with gr.Row():
            cdf_img = gr.Image(label="CDF 累积分布", type="filepath")
            pdf_img = gr.Image(label="PDF 概率密度", type="filepath")
        pct_table = gr.Markdown("")

        btn.click(
            fn=_callback,
            inputs=[count_a, ep, pity, prev_std, pulls_in, q_slider],
            outputs=[prob_md, pulls_md, cdf_img, pdf_img, pct_table],
        )
