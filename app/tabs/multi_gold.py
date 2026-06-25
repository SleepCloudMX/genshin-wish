"""多金概率 Tab — 十连多金累积概率."""

from __future__ import annotations

import gradio as gr
import numpy as np

from app import plot_utils
from genshin_wish._constants import CHARACTER_POOL, WEAPON_POOL
from genshin_wish._gold import get_gold_pdfs


def _pull10_prob(pdf1: np.ndarray, gold: int) -> float:
    """Estimate steady-state 10-pull probability of >= *gold* golds."""
    cdfs = [np.cumsum(p) for p in [np.array([1.0]), pdf1]]
    survival = 1.0 - cdfs[1][:-1]
    weights = survival / survival.sum()

    total = 0.0
    for d, w in enumerate(weights):
        shifted = np.insert(pdf1[d + 1:] / pdf1[d + 1:].sum(), 0, 0)[:11]
        result = shifted.copy()
        for _ in range(gold - 1):
            result = np.convolve(result, pdf1)[:11]
        total += result.sum() * w
    return float(total)


def _callback(pool, gold):
    gold = int(gold)
    pool_config = CHARACTER_POOL if pool == "角色池" else WEAPON_POOL
    pool_label = "角色" if pool == "角色池" else "武器"

    pdfs = get_gold_pdfs(pool_config)
    p = _pull10_prob(pdfs[1], gold)
    title = f"稳态下{pool_label}池十连 {gold} 金"

    return (plot_utils.plot_multi(p, title),)


def build_tab():
    with gr.Tab("多金概率"):
        gr.Markdown(
            "一次十连中出现多金的累积概率曲线。横轴 = 十连次数，纵轴 = 至少出现一次多金的概率。"
        )

        with gr.Row():
            with gr.Column(scale=1):
                pool = gr.Radio(["角色池", "武器池"], value="角色池", label="池子")
            with gr.Column(scale=1):
                gold = gr.Slider(2, 6, 2, step=1, label="目标金数")

        btn = gr.Button("计算", variant="primary")

        img = gr.Image(label="多金概率", type="filepath")

        btn.click(fn=_callback, inputs=[pool, gold], outputs=[img])
