"""捕获明光 Tab — 次数分布柱状图 / k_miss 热力图."""

from __future__ import annotations

import gradio as gr

from app import plot_utils
from genshin_wish import CharacterState
from genshin_wish.character import radiance_distribution


def _callback(n_up, loss, guaranteed):
    n_up = int(n_up)
    loss = int(loss)
    state = CharacterState(guaranteed=bool(guaranteed), consecutive_loss=loss)
    dist = radiance_distribution(state, n_up)

    radiance_by_k = {}
    for k in range(4):
        s = CharacterState(consecutive_loss=k)
        radiance_by_k[k] = radiance_distribution(s, n_up)

    return (
        plot_utils.plot_radiance(dist, n_up, loss),
        plot_utils.plot_nstd_hm(
            radiance_by_k, n_up,
            xlabel="捕获明光次数",
            ylabel="k_miss",
            fmt=".2%",
            title=f"捕获明光次数分布 (n_up={n_up})",
        ),
    )


def build_tab():
    with gr.Tab("捕获明光"):
        gr.Markdown(
            "获得 n_up 个 UP 角色过程中触发捕获明光的次数分布。"
            "热力图展示全部 k_miss 状态。"
        )

        with gr.Row():
            with gr.Column(scale=1):
                n_up = gr.Slider(1, 200, 7, step=1, label="目标 UP 数")
                loss = gr.Slider(0, 3, 0, step=1, label="连歪次数")
            with gr.Column(scale=1):
                with gr.Accordion("高级设置", open=False):
                    guaranteed = gr.Checkbox(False, label="大保底")

        btn = gr.Button("计算", variant="primary")

        with gr.Row():
            bar_img = gr.Image(label="捕获明光次数分布", type="filepath")
            hm_img = gr.Image(label="热力图 (k_miss × 明光次数)", type="filepath")

        btn.click(
            fn=_callback,
            inputs=[n_up, loss, guaranteed],
            outputs=[bar_img, hm_img],
        )
