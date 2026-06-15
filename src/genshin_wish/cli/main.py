"""CLI for genshin-wish: query gacha probabilities from the command line."""

from __future__ import annotations

import json
import sys

import click

from genshin_wish.character import (
    CharacterState,
    UpDistribution,
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
    fmt: str,
) -> None:
    """角色池概率查询"""
    if stable:
        dist = stable_up_distribution(n_up)
    else:
        state = CharacterState(guaranteed=guaranteed, pity=pity, consecutive_loss=loss)
        dist = up_distribution(state, n_up)

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


if __name__ == "__main__":
    main()
