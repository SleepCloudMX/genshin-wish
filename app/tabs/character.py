"""角色池 Tab — CDF / PDF / 分位点表 / 双向查询."""

from __future__ import annotations

import gradio as gr

from app import plot_utils
from genshin_wish import CharacterState, stable_up_distribution, up_distribution


def _callback(n_up, guaranteed, pity, loss, stable, pulls_raw, q):
    n_up = int(n_up)
    loss = int(loss)
    state = CharacterState(guaranteed=bool(guaranteed), pity=int(pity),
                           consecutive_loss=loss)
    dist = stable_up_distribution(n_up) if stable else up_distribution(state, n_up)

    prob = dist.probability(int(pulls_raw)) if pulls_raw is not None and pulls_raw > 0 else None
    q_pulls = dist.quantile(float(q)) if q is not None else None

    tag = f"n_up={n_up}, loss={loss}, pity={int(pity)}"
    tag += ", 稳态" if stable else ""
    cdf_title = f"角色池 CDF ({tag})"
    pdf_title = f"角色池 PDF ({tag})"

    return (
        f"达成概率：**{prob:.2%}**" if prob is not None else "",
        f"所需抽数：**{q_pulls} 抽**" if q_pulls is not None else "",
        plot_utils.plot_cdf(dist.cdf, cdf_title),
        plot_utils.plot_pdf(dist.pdf, pdf_title),
        plot_utils.make_pct_table(dist.cdf),
    )


def build_tab():
    with gr.Tab("角色池"):
        with gr.Row():
            with gr.Column(scale=1):
                n_up = gr.Slider(1, 180, 7, step=1, label="目标 UP 数（含本体）")
                pity = gr.Slider(0, 89, 0, step=1, label="已垫抽数")
            with gr.Column(scale=1):
                loss = gr.Slider(0, 3, 0, step=1, label="连歪次数")
                guaranteed = gr.Checkbox(False, label="大保底")
        stable = gr.Checkbox(False, label="稳态分布")

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
            inputs=[n_up, guaranteed, pity, loss, stable, pulls_in, q_slider],
            outputs=[prob_md, pulls_md, cdf_img, pdf_img, pct_table],
        )
