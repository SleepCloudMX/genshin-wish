"""Gold (5-star) probability: single-pull PDF and multi-gold PDF/CDF cached to disk."""

import pickle
from pathlib import Path
from functools import cache

import numpy as np

from ._constants import PoolConfig

_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".cache"
_CACHE_DIR.mkdir(exist_ok=True)

# In-memory cache to avoid repeated disk loads of large pickle files
_mem_cache: dict[str, list[np.ndarray]] = {}


def _cache_path(pool: PoolConfig, kind: str) -> Path:
    """Build cache filename from pool identity."""
    label = "character" if pool.base_rate == 0.006 else "weapon"
    return _CACHE_DIR / f"{label}-{kind}.pkl"


def build_gold_pdf(pool: PoolConfig) -> np.ndarray:
    """Build single-gold conditional-probability array.

    Returns array of length hard_pity+1 where index i (0..hard_pity) is
    P(get the i-th gold at pull i | no gold before pull i).
    Index 0 is always 0.
    """
    hard = pool.hard_pity
    arr = [0.0]  # index 0

    # Constant probability section: pulls 1 .. soft_pity_start-1
    n_const = pool.soft_pity_start - 1
    arr.extend([pool.base_rate] * n_const)

    if pool.soft_pity_start2 is None:
        # Single soft-pity ramp: soft_pity_start .. hard_pity-1
        n_ramp = hard - pool.soft_pity_start
        start_val = pool.base_rate
        for i in range(1, n_ramp + 1):
            arr.append(start_val + pool.soft_pity_step * i)
    else:
        # Two-stage soft pity (weapon pool)
        # Stage 1: soft_pity_start .. soft_pity_start2-1
        n_ramp1 = pool.soft_pity_start2 - pool.soft_pity_start
        start_val = pool.base_rate
        for i in range(1, n_ramp1 + 1):
            arr.append(start_val + pool.soft_pity_step * i)

        # Stage 2: soft_pity_start2 .. hard_pity-1
        ramp1_end = start_val + pool.soft_pity_step * n_ramp1
        n_ramp2 = hard - pool.soft_pity_start2
        for i in range(1, n_ramp2 + 1):
            arr.append(ramp1_end + pool.soft_pity_step2 * i)

    # Guaranteed at hard_pity
    arr.append(1.0)
    return np.array(arr, dtype=np.float64)


def _compute_pdf_cdf(pool: PoolConfig, min_gold: int = 0) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Compute multi-gold PDFs and CDFs by convolution, at least up to *min_gold*."""
    p_single = build_gold_pdf(pool)
    max_gold = max(pool.max_gold_cache, min_gold)

    pdfs: list[np.ndarray] = [np.array([1.0], dtype=np.float64), np.zeros(len(p_single), dtype=np.float64)]

    # pdfs[1]: probability of first gold at each pull
    temp = 1.0
    for i, p in enumerate(p_single):
        pdfs[1][i] = temp * p
        temp *= 1.0 - p

    # pdfs[k] = pdfs[1] ⊗ pdfs[k-1] for k >= 2
    for _ in range(2, max_gold + 1):
        pdfs.append(np.convolve(pdfs[1], pdfs[-1]))

    cdfs = [np.cumsum(pdf) for pdf in pdfs]
    return pdfs, cdfs


def get_gold_pdfs(pool: PoolConfig, min_gold: int = 0) -> list[np.ndarray]:
    """Load cached multi-gold PDFs, computing and caching on first call.

    If *min_gold* > 0, ensures at least that many gold levels are available,
    recomputing and updating the cache if necessary.
    """
    path = _cache_path(pool, "pdfs")
    key = path.name

    # In-memory hit (common case after first load)
    cached = _mem_cache.get(key)
    need = max(pool.max_gold_cache, min_gold)
    if cached is not None and len(cached) > need:
        return cached

    pdfs: list[np.ndarray] | None = None
    if path.is_file():
        with open(path, "rb") as f:
            pdfs = pickle.load(f)

    need = max(pool.max_gold_cache, min_gold)
    if pdfs is not None and len(pdfs) > need:
        _mem_cache[key] = pdfs
        return pdfs

    # Compute fresh and update cache
    pdfs, cdfs = _compute_pdf_cdf(pool, min_gold)
    _mem_cache[key] = pdfs
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(pdfs, f)
    cdf_path = _cache_path(pool, "cdfs")
    with open(cdf_path, "wb") as f:
        pickle.dump(cdfs, f)
    return pdfs


def get_gold_cdfs(pool: PoolConfig, min_gold: int = 0) -> list[np.ndarray]:
    """Load cached multi-gold CDFs, computing and caching on first call."""
    path = _cache_path(pool, "cdfs")
    key = path.name

    cached = _mem_cache.get(key)
    need = max(pool.max_gold_cache, min_gold)
    if cached is not None and len(cached) > need:
        return cached

    cdfs: list[np.ndarray] | None = None
    if path.is_file():
        with open(path, "rb") as f:
            cdfs = pickle.load(f)

    need = max(pool.max_gold_cache, min_gold)
    if cdfs is not None and len(cdfs) > need:
        _mem_cache[key] = cdfs
        return cdfs

    pdfs, cdfs = _compute_pdf_cdf(pool, min_gold)
    _mem_cache[key] = cdfs
    _mem_cache[_cache_path(pool, "pdfs").name] = pdfs
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(cdfs, f)
    pdf_path = _cache_path(pool, "pdfs")
    with open(pdf_path, "wb") as f:
        pickle.dump(pdfs, f)
    return cdfs
