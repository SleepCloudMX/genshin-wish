"""CLI for genshin-wish: query gacha probabilities from the command line."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import click
import numpy as np

from genshin_wish.character import (
    CharacterState,
    UpDistribution,
    n_std_conditional_pulls,
    n_std_distribution,
    stable_up_distribution,
    up_distribution,
)
from genshin_wish.standard import StandardState, standard_distribution
from genshin_wish.weapon import (
    WeaponState,
    WeaponTarget,
    WeaponUpDistribution,
    weapon_up_distribution,
)
from genshin_wish.joint import joint_distribution

CLI_OUTPUT = Path("output/cli")


def _plot_setup() -> None:
    from genshin_wish.viz._base import setup_style
    setup_style()


def _format_dist(name: str, dist: UpDistribution | WeaponUpDistribution, pulls: int | None) -> str:
    """Format a distribution result as text."""
    lines = [f"{name}:"]
    lines.append(f"  期望抽数: {dist.expected:.1f}")
    if pulls is not None and pulls >= 0:
        lines.append(f"  {pulls} 抽内达成概率: {dist.probability(pulls) * 100:.2f}%")
    return "\n".join(lines)


def _format_quantiles(dist: UpDistribution | WeaponUpDistribution, quantiles: list[float]) -> str:
    """Format quantile results."""
    parts = []
    for q in quantiles:
        parts.append(f"  {int(q * 100)}%: {dist.quantile(q)} 抽")
    return "\n".join(parts)


def _output(result: dict, fmt: str) -> None:
    if fmt == "json":
        click.echo(json.dumps(result, ensure_ascii=False, default=str))
    else:
        click.echo(result["text"])


@click.group()
def main() -> None:
    """genshin-wish — 原神抽卡概率计算器"""


@main.command()
@click.option("--n-up", type=int, required=True, help="目标 UP 数 (含本体)")
@click.option("--pulls", type=int, default=None, help="抽数 (查询概率)")
@click.option("--quantile", type=float, default=None, help="分位点 0~1 (查询所需抽数)")
@click.option("--quantiles", type=str, default=None, help="多个分位点，逗号分隔")
@click.option("--guaranteed/--no-guaranteed", default=False, help="下一个金是否大保底")
@click.option("--pity", type=int, default=0, help="已垫抽数")
@click.option("--loss", type=int, default=0, help="连续歪次数 0~3")
@click.option("--stable/--no-stable", default=False, help="使用稳态分布")
@click.option("--method", type=click.Choice(["auto", "dp-golds", "dp-path", "dp-state", "clt"]),
              default="auto", help="计算方法 (默认 auto)")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def char(
    n_up: int,
    pulls: int | None,
    quantile: float | None,
    quantiles: str | None,
    guaranteed: bool,
    pity: int,
    loss: int,
    stable: bool,
    method: str,
    fmt: str,
) -> None:
    """角色池概率查询"""
    if stable:
        dist = stable_up_distribution(n_up, method=method)
    else:
        state = CharacterState(guaranteed=guaranteed, pity=pity, consecutive_loss=loss)
        dist = up_distribution(state, n_up, method=method)

    text_parts = [_format_dist("角色池", dist, pulls)]

    if quantile is not None:
        text_parts.append(f"  分位点 {quantile}: {dist.quantile(quantile)} 抽")

    if quantiles is not None:
        qs = [float(q.strip()) for q in quantiles.split(",")]
        text_parts.append("  分位点:")
        text_parts.append(_format_quantiles(dist, qs))

    result = {
        "text": "\n".join(text_parts),
        "expected": dist.expected,
        "probability": dist.probability(pulls) if pulls is not None else None,
    }
    if quantile is not None:
        result["quantile"] = {quantile: dist.quantile(quantile)}
    if quantiles is not None:
        qs = [float(q.strip()) for q in quantiles.split(",")]
        result["quantiles"] = {q: dist.quantile(q) for q in qs}

    _output(result, fmt)


@main.command()
@click.option("--count-a", type=int, default=1, help="目标武器 A 的数量")
@click.option("--pulls", type=int, default=None, help="抽数 (查询概率)")
@click.option("--quantile", type=float, default=None, help="分位点")
@click.option("--ep", type=int, default=0, help="命定值 0~2")
@click.option("--pity", type=int, default=0, help="已垫抽数")
@click.option("--prev-std/--no-prev-std", default=False, help="上一金是否为常驻")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def weapon(
    count_a: int,
    pulls: int | None,
    quantile: float | None,
    ep: int,
    pity: int,
    prev_std: bool,
    fmt: str,
) -> None:
    """武器池概率查询 (定轨不取消)"""
    state = WeaponState(pity=pity, epitomized_points=ep, prev_standard=prev_std)
    target = WeaponTarget(count_a=count_a, count_b=0)
    dist = weapon_up_distribution(state, target)

    text_parts = [_format_dist("武器池", dist, pulls)]

    if quantile is not None:
        text_parts.append(f"  分位点 {quantile}: {dist.quantile(quantile)} 抽")

    result = {
        "text": "\n".join(text_parts),
        "expected": dist.expected,
        "probability": dist.probability(pulls) if pulls is not None else None,
        "gold_weights": dist.gold_weights,
    }
    _output(result, fmt)


@main.command()
@click.option("--n-gold", type=int, required=True, help="目标五星数")
@click.option("--pity", type=int, default=0, help="已垫抽数 (0~89)")
@click.option("--pulls", type=int, default=None, help="抽数 (查询概率)")
@click.option("--quantile", type=float, default=None, help="分位点")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def std(
    n_gold: int,
    pity: int,
    pulls: int | None,
    quantile: float | None,
    fmt: str,
) -> None:
    """常驻池概率查询 (纯出金，无 UP 机制)"""
    state = StandardState(pity=pity)
    dist = standard_distribution(state, n_gold)

    text_parts = [_format_dist("常驻池", dist, pulls)]
    if quantile is not None:
        text_parts.append(f"  分位点 {quantile}: {dist.quantile(quantile)} 抽")

    result: dict = {
        "text": "\n".join(text_parts),
        "expected": dist.expected,
        "probability": dist.probability(pulls) if pulls is not None else None,
        "method": dist.method,
    }
    if quantile is not None:
        result["quantile"] = {quantile: dist.quantile(quantile)}

    _output(result, fmt)


@main.command()
@click.option("--char-up", type=int, required=True, help="角色目标 UP 数")
@click.option("--weapon-count", type=int, default=1, help="武器目标数量")
@click.option("--pulls", type=int, default=None, help="抽数 (查询概率)")
@click.option("--char-guaranteed/--no-char-guaranteed", default=False)
@click.option("--char-pity", type=int, default=0)
@click.option("--char-loss", type=int, default=0)
@click.option("--weapon-pity", type=int, default=0)
@click.option("--weapon-ep", type=int, default=0)
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def joint(
    char_up: int,
    weapon_count: int,
    pulls: int | None,
    char_guaranteed: bool,
    char_pity: int,
    char_loss: int,
    weapon_pity: int,
    weapon_ep: int,
    fmt: str,
) -> None:
    """联合计算 (角色 + 武器)"""
    char_state = CharacterState(guaranteed=char_guaranteed, pity=char_pity, consecutive_loss=char_loss)
    weapon_state = WeaponState(pity=weapon_pity, epitomized_points=weapon_ep)
    weapon_target = WeaponTarget(count_a=weapon_count, count_b=0)

    dist = joint_distribution(char_state, char_up, weapon_state, weapon_target)

    text = _format_dist("联合 (角色 + 武器)", dist, pulls)
    if dist.char is not None and dist.weapon is not None:
        text += f"\n  角色单独: {dist.char.expected:.1f} 抽"
        text += f"\n  武器单独: {dist.weapon.expected:.1f} 抽"

    result = {
        "text": text,
        "expected": dist.expected,
        "probability": dist.probability(pulls) if pulls is not None else None,
        "char_expected": dist.char.expected if dist.char else None,
        "weapon_expected": dist.weapon.expected if dist.weapon else None,
    }
    _output(result, fmt)


# ---------------------------------------------------------------------------
# plot command group
# ---------------------------------------------------------------------------


@main.group()
def plot() -> None:
    """单图绘制，灵活参数 — 输出到 output/cli/"""
    _plot_setup()


def _state(guaranteed: bool, pity: int, loss: int) -> CharacterState:
    return CharacterState(guaranteed=guaranteed, pity=pity, consecutive_loss=loss)


@plot.command()
@click.option("--n-up", type=int, required=True, help="目标 UP 数")
@click.option("--guaranteed/--no-guaranteed", default=False)
@click.option("--pity", type=int, default=0, help="已垫抽数")
@click.option("--loss", type=int, default=0, help="连续歪次数 0~3")
def char_cdf(n_up: int, guaranteed: bool, pity: int, loss: int) -> None:
    """角色池标注 CDF"""
    from genshin_wish.viz.cdf import plot_annotated_cdf

    state = _state(guaranteed, pity, loss)
    dist = up_distribution(state, n_up)
    suffix = f"-guaranteed" if guaranteed else ""
    path = CLI_OUTPUT / f"cdf-n{n_up}-loss{loss}-pity{pity}{suffix}.png"
    plot_annotated_cdf(
        dist.cdf,
        f"CDF (n_up={n_up}, loss={loss}, pity={pity}"
        f"{', guaranteed' if guaranteed else ''})",
        path,
    )
    click.echo(f"Saved: {path}")


@plot.command()
@click.option("--n-up", type=int, required=True, help="目标 UP 数")
@click.option("--guaranteed/--no-guaranteed", default=False)
@click.option("--pity", type=int, default=0, help="已垫抽数")
@click.option("--loss", type=int, default=0, help="连续歪次数 0~3")
def char_pdf(n_up: int, guaranteed: bool, pity: int, loss: int) -> None:
    """角色池 PDF"""
    from genshin_wish.viz.pdf import plot_simple_pdf

    state = _state(guaranteed, pity, loss)
    dist = up_distribution(state, n_up)
    suffix = f"-guaranteed" if guaranteed else ""
    path = CLI_OUTPUT / f"pdf-n{n_up}-loss{loss}-pity{pity}{suffix}.png"
    plot_simple_pdf(
        dist.pdf,
        f"PDF (n_up={n_up}, loss={loss}, pity={pity}"
        f"{', guaranteed' if guaranteed else ''})",
        path,
    )
    click.echo(f"Saved: {path}")


@plot.command()
@click.option("--n-up", type=int, default=7, help="最大 UP 数 (默认 7)")
@click.option("--guaranteed/--no-guaranteed", default=False)
@click.option("--pity", type=int, default=0, help="已垫抽数")
@click.option("--loss", type=int, default=0, help="连续歪次数 0~3")
@click.option("--interval", type=click.Choice(["3", "5"]), default="3",
              help="区间层数 (默认 3)")
def char_fan(n_up: int, guaranteed: bool, pity: int, loss: int, interval: str) -> None:
    """角色池幸运扇形图"""
    from genshin_wish.viz.fan import plot_luck_fan

    state = _state(guaranteed, pity, loss)

    def pdf_func(n: int) -> np.ndarray:
        return up_distribution(state, n).pdf

    suffix = f"-guaranteed" if guaranteed else ""
    path = CLI_OUTPUT / f"fan-n{n_up}-loss{loss}-pity{pity}-i{interval}{suffix}.png"
    plot_luck_fan(
        pdf_func, max_n_up=n_up, save_path=path,
        interval_set=int(interval),
        title=f"幸运扇形图 (max_n_up={n_up}, loss={loss}, pity={pity})",
    )
    click.echo(f"Saved: {path}")


@plot.command()
@click.option("--n-up", type=int, required=True, help="目标 UP 数")
@click.option("--guaranteed/--no-guaranteed", default=False)
@click.option("--loss", type=int, default=0, help="连续歪次数 0~3")
def nstd_bar(n_up: int, guaranteed: bool, loss: int) -> None:
    """n_std 分布柱状图 (仅支持 pity=0)"""
    from genshin_wish.viz.nstd import plot_nstd_bar

    state = CharacterState(guaranteed=guaranteed, pity=0, consecutive_loss=loss)
    dist = n_std_distribution(state, n_up)
    suffix = f"-guaranteed" if guaranteed else ""
    path = CLI_OUTPUT / f"nstd-bar-n{n_up}-loss{loss}{suffix}.png"
    plot_nstd_bar(dist, n_up, loss, path)
    click.echo(f"Saved: {path}")


@plot.command()
@click.option("--n-up", type=int, required=True, help="目标 UP 数")
@click.option("--n-std", type=int, required=True, help="常驻数量")
@click.option("--guaranteed/--no-guaranteed", default=False)
@click.option("--loss", type=int, default=0, help="连续歪次数 0~3")
def nstd_pdf(n_up: int, n_std: int, guaranteed: bool, loss: int) -> None:
    """条件抽数分布 PDF (仅支持 pity=0)"""
    from genshin_wish.viz.nstd import plot_nstd_cdf

    state = CharacterState(guaranteed=guaranteed, pity=0, consecutive_loss=loss)
    dists = n_std_conditional_pulls(state, n_up, n_std=n_std)
    if n_std not in dists:
        click.echo(f"n_std={n_std} 不可达 (n_up={n_up}, loss={loss})", err=True)
        sys.exit(1)
    suffix = f"-guaranteed" if guaranteed else ""
    path = CLI_OUTPUT / f"nstd-pdf-n{n_up}-s{n_std}-loss{loss}{suffix}.png"
    plot_nstd_cdf(dists[n_std], n_up, n_std, loss, path)
    click.echo(f"Saved: {path}")


@plot.command()
@click.option("--count-a", type=int, default=1, help="目标武器 A 的数量")
@click.option("--ep", type=int, default=0, help="命定值 0~2")
@click.option("--pity", type=int, default=0, help="已垫抽数")
@click.option("--prev-std/--no-prev-std", default=False, help="上一金是否为常驻")
def weapon_cdf(count_a: int, ep: int, pity: int, prev_std: bool) -> None:
    """武器池标注 CDF (定轨不取消)"""
    from genshin_wish.viz.cdf import plot_annotated_cdf

    state = WeaponState(pity=pity, epitomized_points=ep, prev_standard=prev_std)
    target = WeaponTarget(count_a=count_a, count_b=0)
    dist = weapon_up_distribution(state, target)
    path = CLI_OUTPUT / f"weapon-cdf-a{count_a}-pity{pity}-ep{ep}"
    if prev_std:
        path = Path(str(path) + "-prevstd")
    path = path.with_suffix(".png")
    plot_annotated_cdf(
        dist.cdf,
        f"武器池 CDF (count_a={count_a}, pity={pity}, ep={ep}"
        f"{', prev_std' if prev_std else ''})",
        path,
    )
    click.echo(f"Saved: {path}")


if __name__ == "__main__":
    main()
