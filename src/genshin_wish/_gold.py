"""Gold (5-star) probability: single-pull PDF and multi-gold PDF/CDF cached to disk."""

import pickle
from pathlib import Path
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
    """Return multi-gold PDFs, at least up to *min_gold* levels.

    Base level (``pool.max_gold_cache``) is persisted to disk (~60 KB).
    Extensions beyond that are cached in memory only, not persisted.
    """
    path = _cache_path(pool, "pdfs")
    key = path.name

    # In-memory hit
    cached = _mem_cache.get(key)
    if cached is not None and len(cached) > max(pool.max_gold_cache, min_gold):
        return cached

    pdfs: list[np.ndarray] | None = None
    if path.is_file():
        with open(path, "rb") as f:
            pdfs = pickle.load(f)
        _mem_cache[key] = pdfs

    need = max(pool.max_gold_cache, min_gold)
    if pdfs is not None and len(pdfs) > need:
        return pdfs

    # Compute full range (only save base to disk)
    pdfs, cdfs = _compute_pdf_cdf(pool, min_gold)
    _mem_cache[key] = pdfs
    _mem_cache[_cache_path(pool, "cdfs").name] = cdfs
    path.parent.mkdir(parents=True, exist_ok=True)
    base = pdfs[: pool.max_gold_cache + 1]
    with open(path, "wb") as f:
        pickle.dump(base, f)
    cdf_path = _cache_path(pool, "cdfs")
    base_cdfs = cdfs[: pool.max_gold_cache + 1]
    with open(cdf_path, "wb") as f:
        pickle.dump(base_cdfs, f)
    return pdfs


def gold_count_pmf(pool: PoolConfig, pity: int, n_pulls: int,
                   eps: float = 1e-15) -> np.ndarray:
    """P(exactly *g* 5-stars within *n_pulls* pulls), g = 0..g_max.

    ``P(g) = P(T_g ≤ n_pulls) − P(T_{g+1} ≤ n_pulls)``，``T_g`` 由单金 PDF 逐次卷积得到
    （首金按当前 pity 平移）。只对 t ≤ n_pulls 求和，卷积可截断到 n_pulls+1 项；
    当 ``P(T_{g+1} ≤ n_pulls) < eps`` 时截断（尾部再往上可忽略）。
    """
    p_first = get_gold_pdfs(pool)[1]
    if pity == 0:
        dist = p_first.copy()
    else:
        tail = p_first[pity + 1:]
        dist = np.insert(tail / tail.sum(), 0, 0)

    out: list[float] = []
    prev = 1.0
    for _ in range(n_pulls + 2):
        cur = float(dist[: n_pulls + 1].sum())
        out.append(max(prev - cur, 0.0))
        if cur < eps:
            break
        dist = np.convolve(dist[: n_pulls + 1], p_first)
        prev = cur
    return np.array(out, dtype=np.float64)


def joint_from_labels(pmf: np.ndarray, chain: np.ndarray) -> dict[int, dict[int, float]]:
    """金数分布 ⊗ 标记链 → ``{目标数: {歪出数: 概率}}``。

    ``chain[g][u]`` 为「前 g 个金中恰有 u 个目标」的概率，且 ``g = u + 歪出数``。
    """
    acc: dict[int, dict[int, float]] = {}
    for g, p in enumerate(pmf):
        if p == 0.0:
            continue
        for u in range(g + 1):
            w = chain[g][u]
            if w == 0.0:
                continue
            row = acc.setdefault(u, {})
            row[g - u] = row.get(g - u, 0.0) + p * w
    return acc


def get_gold_cdfs(pool: PoolConfig, min_gold: int = 0) -> list[np.ndarray]:
    """Return multi-gold CDFs.  Mirrors ``get_gold_pdfs`` caching strategy."""
    path = _cache_path(pool, "cdfs")
    key = path.name

    cached = _mem_cache.get(key)
    if cached is not None and len(cached) > max(pool.max_gold_cache, min_gold):
        return cached

    cdfs: list[np.ndarray] | None = None
    if path.is_file():
        with open(path, "rb") as f:
            cdfs = pickle.load(f)
        _mem_cache[key] = cdfs

    need = max(pool.max_gold_cache, min_gold)
    if cdfs is not None and len(cdfs) > need:
        return cdfs

    pdfs, cdfs = _compute_pdf_cdf(pool, min_gold)
    _mem_cache[key] = cdfs
    _mem_cache[_cache_path(pool, "pdfs").name] = pdfs
    path.parent.mkdir(parents=True, exist_ok=True)
    base_cdfs = cdfs[: pool.max_gold_cache + 1]
    with open(path, "wb") as f:
        pickle.dump(base_cdfs, f)
    pdf_path = _cache_path(pool, "pdfs")
    base = pdfs[: pool.max_gold_cache + 1]
    with open(pdf_path, "wb") as f:
        pickle.dump(base, f)
    return cdfs
