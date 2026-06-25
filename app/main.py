"""genshin-wish Gradio UI — entry point.

Run::

    python app/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from project root without editable install
_sys_path_root = str(Path(__file__).resolve().parent.parent)
if _sys_path_root not in sys.path:
    sys.path.insert(0, _sys_path_root)

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
