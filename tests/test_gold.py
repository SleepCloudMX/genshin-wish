"""Tests for gold probability module."""
import numpy as np
import pytest
from genshin_wish._gold import build_gold_pdf, get_gold_pdfs, get_gold_cdfs
from genshin_wish._constants import CHARACTER_POOL, WEAPON_POOL


def test_character_gold_pdf_shape():
    pdf = build_gold_pdf(CHARACTER_POOL)
    assert len(pdf) == 91
    assert pdf[0] == 0.0
    assert pdf[1] == 0.006
    assert pdf[73] == 0.006
    assert pdf[74] == 0.066
    assert pdf[90] == 1.0


def test_weapon_gold_pdf_shape():
    pdf = build_gold_pdf(WEAPON_POOL)
    assert len(pdf) == 81
    assert pdf[0] == 0.0
    assert pdf[1] == 0.007
    assert pdf[62] == 0.007
    assert pdf[63] == pytest.approx(0.077)
    assert pdf[80] == 1.0


def test_character_gold_expected():
    """Single gold expected ~62.3 (comprehensive rate ~1.6%)."""
    pdfs = get_gold_pdfs(CHARACTER_POOL)
    exp = sum(i * p for i, p in enumerate(pdfs[1]))
    assert 60 < exp < 65, f"Expected ~62.3, got {exp:.2f}"


def test_weapon_gold_expected():
    """Single gold expected ~54.1 (comprehensive rate ~1.85%)."""
    pdfs = get_gold_pdfs(WEAPON_POOL)
    exp = sum(i * p for i, p in enumerate(pdfs[1]))
    assert 50 < exp < 58, f"Expected ~54.1, got {exp:.2f}"


def test_pdfs_sum_to_one():
    """Each multi-gold PDF sums to 1."""
    for pool in [CHARACTER_POOL, WEAPON_POOL]:
        pdfs = get_gold_pdfs(pool)
        for k, pdf in enumerate(pdfs):
            assert abs(pdf.sum() - 1.0) < 1e-10, f"Pool={pool}, k={k}: sum={pdf.sum()}"


def test_cdfs_converge_to_one():
    """CDFs converge to 1 at hard pity."""
    for pool in [CHARACTER_POOL, WEAPON_POOL]:
        cdfs = get_gold_cdfs(pool)
        for k, cdf in enumerate(cdfs):
            if k > 0:
                assert abs(cdf[-1] - 1.0) < 1e-10, f"Pool={pool}, k={k}: last CDF={cdf[-1]}"


def test_multi_gold_pdf_length():
    """k-gold PDF has correct length."""
    pdfs = get_gold_pdfs(CHARACTER_POOL)
    L = len(pdfs[1])  # 91
    for k in range(1, len(pdfs)):
        expected_len = k * (L - 1) + 1
        assert len(pdfs[k]) == expected_len, f"k={k}: {len(pdfs[k])} != {expected_len}"
