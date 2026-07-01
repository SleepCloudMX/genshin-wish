"""Parse player pull sequences for comparison against theoretical distributions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PlayerPulls:
    per_up: list[int]   # pulls for each UP (68, 90, 157, ...)
    cumulative: list[int]  # cumulative total after each UP (68, 158, 315, ...)


def parse_pulls_seq(text: str) -> PlayerPulls:
    """Parse ``"68,79+11,77+80,..."`` → per-UP and cumulative totals."""
    raw = [s.strip() for s in text.split(",") if s.strip()]
    per_up: list[int] = []
    for item in raw:
        if "+" in item:
            a, b = item.split("+", 1)
            per_up.append(int(a) + int(b))
        else:
            per_up.append(int(item))

    cumulative: list[int] = []
    total = 0
    for p in per_up:
        total += p
        cumulative.append(total)
    return PlayerPulls(per_up=per_up, cumulative=cumulative)
