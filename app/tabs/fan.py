"""幸运扇形图 Tab — 每 UP 消耗的欧非区间."""

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


def _callback(max_n_up, interval_set, loss, guaranteed, stable):
    max_n_up = int(max_n_up)
    loss = int(loss)
    interval_set = int(interval_set)

    if stable:
        pdf_func = _stable_pdf
        tag = f"max_n_up={max_n_up}, 稳态"
    else:
        state = CharacterState(guaranteed=bool(guaranteed), consecutive_loss=loss)
        pdf_func = lambda n: up_distribution(state, n).pdf
        tag = f"max_n_up={max_n_up}, loss={loss}"

    title = f"幸运扇形图 ({tag})"
    return (plot_utils.plot_fan(pdf_func, max_n_up,
                                interval_set=interval_set, title=title),)


def build_tab():
    with gr.Tab("幸运扇形图"):
        gr.Markdown(
            "每获得一个 UP（含本体）平均消耗的抽数分布。"
            "区间越宽越欧/非，用于评估单角色抽取的运气波动。"
        )

        with gr.Row():
            with gr.Column(scale=1):
                max_n_up = gr.Slider(1, 7, 7, step=1, label="目标命座数 (1-6命)")
                loss = gr.Slider(0, 3, 0, step=1, label="连歪次数")
            with gr.Column(scale=1):
                interval_set = gr.Radio([3, 5], value=5, label="区间档数")
                with gr.Accordion("高级设置", open=False):
                    guaranteed = gr.Checkbox(False, label="大保底")
                    stable = gr.Checkbox(False, label="稳态分布")

        btn = gr.Button("计算", variant="primary")

        img = gr.Image(label="幸运扇形图", type="filepath")

        btn.click(
            fn=_callback,
            inputs=[max_n_up, interval_set, loss, guaranteed, stable],
            outputs=[img],
        )
