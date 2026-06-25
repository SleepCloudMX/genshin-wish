"""长期欧非 Tab — 长期 UP 累计抽数分位区间演变."""

from __future__ import annotations

import gradio as gr

from app import plot_utils
from genshin_wish.long_term import LongTermState, make_long_solver


def _callback(N, model):
    N = int(N)

    n_pre = N if model == "5.0 之前 (纯 50/50)" else 0
    n_post = N if model == "5.0 之后 (含捕获明光)" else 0

    state = LongTermState(n_pre_50=n_pre, n_post_50=n_post)
    solver = make_long_solver(state)

    title = f"{model} 长期欧非演变 (N={N})"
    return plot_utils.plot_luck_long(solver, N, interval_set=3, title=title)


def build_tab():
    with gr.Tab("长期欧非"):
        gr.Markdown(
            "长期视角下（多次 UP）平均每 UP 消耗的抽数分位区间。"
            "随 UP 数增加，区间收敛到理论均值。区分 5.0 前后机制。"
        )

        with gr.Row():
            N = gr.Slider(10, 500, 100, step=10, label="UP 总数 (N)")
            model = gr.Radio(
                ["5.0 之后 (含捕获明光)", "5.0 之前 (纯 50/50)"],
                value="5.0 之后 (含捕获明光)",
                label="模型",
            )

        btn = gr.Button("计算", variant="primary")

        img = gr.Image(label="长期欧非演变", type="filepath")

        btn.click(fn=_callback, inputs=[N, model], outputs=[img])
