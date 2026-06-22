"""Tests for character banner probability."""
import numpy as np
from genshin_wish.character import (
    CharacterState,
    UpDistribution,
    up_distribution,
    stable_up_distribution,
)
from genshin_wish._capture_radiance import guarantee_seq
from genshin_wish._constants import STABLE_P


def test_guarantee_seq_sum_to_one():
    """All sequence probabilities sum to 1."""
    for k_miss in range(4):
        for n_up in range(1, 8):
            seq = guarantee_seq(k_miss, n_up)
            total = sum(p for _, (_, p) in seq.items())
            assert abs(total - 1.0) < 1e-12, f"k_miss={k_miss}, n_up={n_up}: sum={total}"


def test_guarantee_seq_k_miss_3_always_win():
    """At k_miss=3, capture radiance guarantees the first UP is a win."""
    for n_up in range(1, 6):
        seq = guarantee_seq(3, n_up)
        for s, (final_k, _) in seq.items():
            # First element is always a win (p_up[3]=1.0)
            assert s[0] == 1, f"First element should be win: {s}"


def test_up_distribution_n0():
    """n_up=0 returns [1.0]."""
    state = CharacterState()
    d = up_distribution(state, 0)
    assert len(d.pdf) == 1
    assert d.pdf[0] == 1.0
    assert d.expected == 0.0


def test_up_distribution_guaranteed_n1():
    """Bug fix: guaranteed=True, n_up=1 should not crash or return wrong result."""
    state = CharacterState(guaranteed=True, pity=0, consecutive_loss=0)
    d = up_distribution(state, 1)
    assert abs(d.pdf.sum() - 1.0) < 1e-8
    assert d.expected > 0
    # Should equal single-gold expected (no uncertain UPs)
    assert 60 < d.expected < 65, f"Expected ~62.3, got {d.expected:.1f}"


def test_up_distribution_pdf_sums_to_one():
    """PDF normalizes to 1."""
    for n_up in [1, 3, 7]:
        state = CharacterState()
        d = up_distribution(state, n_up)
        assert abs(d.pdf.sum() - 1.0) < 1e-6, f"n_up={n_up}: pdf sum={d.pdf.sum()}"


def test_up_distribution_expected_increases():
    """Expected pulls increases with n_up."""
    state = CharacterState()
    prev = 0
    for n_up in [1, 2, 3, 5, 7]:
        d = up_distribution(state, n_up)
        assert d.expected > prev
        prev = d.expected


def test_stable_pdf_sums_to_one():
    """Stable PDF normalizes."""
    for n_up in [1, 3, 7]:
        d = stable_up_distribution(n_up)
        assert abs(d.pdf.sum() - 1.0) < 1e-6


def test_stable_expected_close_to_weighted():
    """Stable expected ≈ weighted sum of per-k_miss expectations."""
    for n_up in [1, 3, 7]:
        weighted_sum = 0.0
        for k_miss, w in enumerate(STABLE_P):
            s = CharacterState(consecutive_loss=k_miss)
            weighted_sum += up_distribution(s, n_up).expected * w
        d = stable_up_distribution(n_up)
        assert abs(d.expected - weighted_sum) / weighted_sum < 0.01


def test_clt_close_to_exact():
    """CLT approximation close to exact for medium n_up at common quantiles."""
    d_exact = stable_up_distribution(100)
    d_clt = stable_up_distribution(100, method="clt")

    for q in [0.1, 0.3, 0.5, 0.7, 0.9]:
        exact_val = d_exact.quantile(q)
        clt_val = d_clt.quantile(q)
        err = abs(exact_val - clt_val) / exact_val
        assert err < 0.05, f"q={q}: exact={exact_val}, clt={clt_val}, err={err:.3%}"


def test_luck_monotonic():
    """luck() increases with pulls."""
    d = up_distribution(CharacterState(), 7)
    prev = 0.0
    for pulls in range(0, 1600, 100):
        l = d.luck(pulls)
        assert l >= prev, f"pulls={pulls}: luck decreased"
        prev = l


def test_quantile_monotonic():
    """quantile() increases with q."""
    d = up_distribution(CharacterState(), 7)
    prev = 0
    for q in [0.1, 0.3, 0.5, 0.7, 0.9, 0.99]:
        val = d.quantile(q)
        assert val >= prev, f"q={q}: quantile decreased"
        prev = val
