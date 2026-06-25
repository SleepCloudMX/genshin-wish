"""联合计算 Tab — 角色 + 武器联合 CDF / PDF."""

from __future__ import annotations

import gradio as gr

from app import plot_utils
from genshin_wish import CharacterState
from genshin_wish.joint import joint_distribution
from genshin_wish.weapon import WeaponState, WeaponTarget


def _callback(char_up, weapon_count, char_loss, char_guaranteed, char_pity,
              weapon_pity, weapon_ep, pulls_raw, q):
    cs = CharacterState(guaranteed=bool(char_guaranteed), pity=int(char_pity),
                        consecutive_loss=int(char_loss))
    ws = WeaponState(pity=int(weapon_pity), epitomized_points=int(weapon_ep))
    wt = WeaponTarget(count_a=int(weapon_count))
    dist = joint_distribution(cs, int(char_up), ws, wt)
    exp_val = dist.expected

    prob = dist.probability(int(pulls_raw)) if pulls_raw is not None and pulls_raw > 0 else None
    q_pulls = dist.quantile(float(q)) if q is not None else None

    tag = f"C{int(char_up)}+W{int(weapon_count)}, loss={int(char_loss)}"
    cdf_title = f"联合 CDF ({tag})"
    pdf_title = f"联合 PDF ({tag})"

    pulls_txt = (
        f"所需抽数：**{q_pulls} 抽**  \n期望抽数：**{exp_val:.1f} 抽**"
        if q_pulls is not None
        else f"期望抽数：**{exp_val:.1f} 抽**"
    )

    return (
        f"达成概率：**{prob:.2%}**" if prob is not None else "",
        pulls_txt,
        plot_utils.plot_cdf(dist.cdf, cdf_title),
        plot_utils.plot_pdf(dist.pdf, pdf_title),
        plot_utils.make_pct_table(dist.cdf),
    )


def build_tab():
    with gr.Tab("联合计算"):
        gr.Markdown(
            "角色池与武器池独立卷积的联合抽数分布。"
            "支持双向查询：输入抽数查概率，或输入分位点查所需抽数。"
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 角色池")
                char_up = gr.Slider(1, 180, 7, step=1, label="目标 UP 数")
                char_loss = gr.Slider(0, 3, 0, step=1, label="连歪次数")
                char_guaranteed = gr.Checkbox(False, label="大保底")
                with gr.Accordion("高级设置", open=False):
                    char_pity = gr.Slider(0, 89, 0, step=1, label="角色已垫抽数")
            with gr.Column(scale=1):
                gr.Markdown("### 武器池")
                weapon_count = gr.Slider(1, 5, 1, step=1, label="目标武器数")
                with gr.Accordion("高级设置", open=False):
                    weapon_pity = gr.Slider(0, 79, 0, step=1, label="武器已垫抽数")
                    weapon_ep = gr.Slider(0, 2, 0, step=1, label="武器命定值")

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
            inputs=[char_up, weapon_count, char_loss, char_guaranteed,
                    char_pity, weapon_pity, weapon_ep, pulls_in, q_slider],
            outputs=[prob_md, pulls_md, cdf_img, pdf_img, pct_table],
        )
