"""Tests for standard banner probability."""
import numpy as np
from genshin_wish.standard import StandardState, standard_distribution


def test_n0():
    d = standard_distribution(StandardState(), 0)
    assert len(d.pdf) == 1
    assert d.pdf[0] == 1.0
    assert d.expected == 0.0


def test_n1():
    d = standard_distribution(StandardState(), 1)
    assert abs(d.pdf.sum() - 1.0) < 1e-8
    assert 60 < d.expected < 65


def test_n1_with_pity():
    d0 = standard_distribution(StandardState(pity=0), 1)
    dp = standard_distribution(StandardState(pity=70), 1)
    assert dp.expected < d0.expected


def test_n7():
    d = standard_distribution(StandardState(), 7)
    assert abs(d.pdf.sum() - 1.0) < 1e-6
    # 7 golds ~ 7 * 62.3 = 436
    assert 400 < d.expected < 470


def test_n5_exact():
    """n_gold=5 <= CLT_THRESHOLD uses exact method."""
    d = standard_distribution(StandardState(), 5)
    assert abs(d.pdf.sum() - 1.0) < 1e-6
    assert d.method == "exact"


def test_n30_clt():
    d = standard_distribution(StandardState(), 30)
    assert abs(d.pdf.sum() - 1.0) < 1e-3
    assert d.method == "clt"


def test_clt_self_consistent():
    """CLT result is self-consistent (quantiles monotonic, PDF ≈ 1)."""
    d = standard_distribution(StandardState(), 30)
    assert d.method == "clt"
    assert abs(d.pdf.sum() - 1.0) < 0.02  # discretization error
    assert d.quantile(0.1) < d.quantile(0.5) < d.quantile(0.9)
    # Expect ~30 * 62.3 = 1869 pulls
    assert 1800 < d.expected < 1950


def test_n_gold_negative_raises():
    try:
        standard_distribution(StandardState(), -1)
        assert False
    except ValueError:
        pass
