"""常驻分布 Tab — n_std 柱状图 / 条件 PDF 迭图 / k_miss 热力图."""

from __future__ import annotations

import gradio as gr

from app import plot_utils
from genshin_wish import CharacterState
from genshin_wish.character import (
    n_std_conditional_pulls,
    n_std_distribution,
)


def _callback(n_up, loss, guaranteed):
    n_up = int(n_up)
    loss = int(loss)
    state = CharacterState(guaranteed=bool(guaranteed), consecutive_loss=loss)

    nstd_dist = n_std_distribution(state, n_up)
    cond_dists = n_std_conditional_pulls(state, n_up)

    # heatmap: compute for all k_miss
    nstd_by_k = {}
    for k in range(4):
        s = CharacterState(consecutive_loss=k)
        nstd_by_k[k] = n_std_distribution(s, n_up)

    return (
        plot_utils.plot_nstd(nstd_dist, n_up, loss),
        plot_utils.plot_nstd_cond(cond_dists, n_up, loss, nstd_probs=nstd_dist),
        plot_utils.plot_nstd_hm(nstd_by_k, n_up),
    )


def build_tab():
    with gr.Tab("常驻分布"):
        with gr.Row():
            with gr.Column(scale=1):
                n_up = gr.Slider(1, 30, 7, step=1, label="目标 UP 数")
                loss = gr.Slider(0, 3, 0, step=1, label="连歪次数")
                guaranteed = gr.Checkbox(False, label="大保底")
            with gr.Column(scale=2):
                pass

        btn = gr.Button("计算", variant="primary")

        with gr.Row():
            bar_img = gr.Image(label="常驻数量分布", type="filepath")
            pdf_img = gr.Image(label="条件抽数 PDF", type="filepath")
        with gr.Row():
            hm_img = gr.Image(label="热力图 (k_miss × n_std)", type="filepath")

        btn.click(
            fn=_callback,
            inputs=[n_up, loss, guaranteed],
            outputs=[bar_img, pdf_img, hm_img],
        )
