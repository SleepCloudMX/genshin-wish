"""genshin-wish Gradio UI — entry point.

Run::

    python app/main.py
"""

from __future__ import annotations

import gradio as gr

from app.tabs import (
    character,
    joint,
    nstd,
    radiance,
    standard,
    weapon,
)


def main():
    with gr.Blocks(title="genshin-wish") as demo:
        gr.Markdown("# genshin-wish 概率查询")

        character.build_tab()
        weapon.build_tab()
        joint.build_tab()
        standard.build_tab()
        nstd.build_tab()
        radiance.build_tab()

    demo.launch()


if __name__ == "__main__":
    main()
