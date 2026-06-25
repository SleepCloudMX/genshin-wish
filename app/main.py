"""genshin-wish Gradio UI — entry point.

Run::

    python app/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_sys_path_root = str(Path(__file__).resolve().parent.parent)
if _sys_path_root not in sys.path:
    sys.path.insert(0, _sys_path_root)

import gradio as gr

from app.tabs import (
    character,
    column,
    fan,
    joint,
    long_term,
    multi_gold,
    nstd,
    radiance,
    standard,
    weapon,
)


def main():
    with gr.Blocks(
        title="genshin-wish",
        theme=gr.themes.Soft(primary_hue="blue"),
    ) as demo:
        gr.HTML(
            "<h1>genshin-wish</h1>"
            "<p>原神抽卡概率计算器 — 基于解析计算（非蒙特卡洛），"
            "支持角色池、武器池、常驻池及联合计算。</p>"
        )

        character.build_tab()
        weapon.build_tab()
        joint.build_tab()
        standard.build_tab()
        nstd.build_tab()
        radiance.build_tab()
        fan.build_tab()
        column.build_tab()
        multi_gold.build_tab()
        long_term.build_tab()

    demo.launch()


if __name__ == "__main__":
    main()
