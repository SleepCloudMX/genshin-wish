"""Tests for player pulls parsing and percentile computation."""

import numpy as np
import pytest

from genshin_wish._player_pulls import parse_pulls_seq, PlayerPulls
from genshin_wish.character import CharacterState, up_distribution


class TestParsePullsSeq:
    def test_simple_wins(self):
        pp = parse_pulls_seq("68,79,77,74")
        assert pp.per_up == [68, 79, 77, 74]
        assert pp.cumulative == [68, 147, 224, 298]

    def test_mixed_wins_and_losses(self):
        pp = parse_pulls_seq("68,79+11,77+80,77")
        assert pp.per_up == [68, 90, 157, 77]
        assert pp.cumulative == [68, 158, 315, 392]

    def test_spaces(self):
        pp = parse_pulls_seq(" 68 , 79+11 , 77 ")
        assert pp.per_up == [68, 90, 77]

    def test_empty_trailing(self):
        pp = parse_pulls_seq("68,79,")
        assert pp.per_up == [68, 79]

    def test_single(self):
        pp = parse_pulls_seq("68")
        assert pp.per_up == [68]
        assert pp.cumulative == [68]


class TestPlayerPercentile:
    def test_percentile_bounds(self):
        """Player percentile should be in [0, 1] for valid pull counts."""
        pp = parse_pulls_seq("68,79+11,77+80,77")
        state = CharacterState(guaranteed=False, pity=0, consecutive_loss=0)
        for i, total in enumerate(pp.cumulative):
            dist = up_distribution(state, i + 1)
            pct = float(dist.cdf[min(total, len(dist.cdf) - 1)])
            assert 0.0 <= pct <= 1.0, f"Percentile {pct} out of bounds for UP={i+1}"
