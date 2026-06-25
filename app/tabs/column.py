"""限定数分布 Tab — 各命座抽数达成概率柱状图."""

from __future__ import annotations

import gradio as gr
import numpy as np

from app import plot_utils
from genshin_wish import CharacterState, up_distribution
from genshin_wish._constants import STABLE_P


def _stable_pdf(n_up: int) -> np.ndarray:
    res: np.ndarray | None = None
    for m, w in enumerate(STABLE_P):
        pdf = up_distribution(CharacterState(consecutive_loss=m), n_up).pdf
        if res is None:
            res = np.zeros(len(pdf))
        if len(res) < len(pdf):
            new_res = np.zeros(len(pdf))
            new_res[:len(res)] = res
            res = new_res
        res[:len(pdf)] += pdf * w
    return res


def _callback(max_n_up, loss, guaranteed, stable):
    max_n_up = int(max_n_up)
    loss = int(loss)

    if stable:
        pdf_func = _stable_pdf
        label = "稳态"
    else:
        state = CharacterState(guaranteed=bool(guaranteed), consecutive_loss=loss)
        pdf_func = lambda n: up_distribution(state, n).pdf
        label = f"已连歪 {loss} 次"

    title = f"【{label}】各命座抽数分位点分布图"
    return plot_utils.plot_column(pdf_func, max_n_up, title)


def build_tab():
    with gr.Tab("限定数分布"):
        gr.Markdown(
            "给定抽数内各命座达成的概率分布。每列为一个命座，"
            "颜色深浅 = 累积概率，横线标注分位点。"
        )

        with gr.Row():
            with gr.Column(scale=1):
                max_n_up = gr.Slider(1, 7, 7, step=1, label="目标命座数 (1-6命)")
                loss = gr.Slider(0, 3, 0, step=1, label="连歪次数")
            with gr.Column(scale=1):
                with gr.Accordion("高级设置", open=False):
                    guaranteed = gr.Checkbox(False, label="大保底")
                    stable = gr.Checkbox(False, label="稳态分布")

        btn = gr.Button("计算", variant="primary")

        img = gr.Image(label="限定数分布", type="filepath")

        btn.click(
            fn=_callback,
            inputs=[max_n_up, loss, guaranteed, stable],
            outputs=[img],
        )
