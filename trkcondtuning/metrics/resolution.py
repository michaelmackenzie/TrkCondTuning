"""
Offline momentum resolution at the tracker entrance, dp = p(TT_Front, fit) - p(TT_Front, MC),
of the CE track (see offline.py). sigma68 = half the 16-84% range [MeV/c]; tail = fraction with
|dp| > sel.resolution_tail. 'quality' = the TrkQual-input box cuts of the OfflineSelection.
"""
from __future__ import annotations

import math
import os
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import offline

# N(active) regions [lo, hi); None = open
REGIONS: List[Tuple[Optional[int], Optional[int]]] = [(None, 15), (15, 20), (20, 25), (25, 30), (30, 40), (40, None)]


def region_name(lo, hi) -> str:
    if lo is None:
        return f"<{hi}"
    return f">={lo}" if hi is None else f"{lo}-{hi - 1}"


def stats(dp: np.ndarray, tail: float = 1.0, bootstrap: int = 0, seed: int = 12345) -> dict:
    n = int(len(dp))
    if n == 0:
        return {"n": 0, "sigma68": None, "median": None, "tail": None, "tail_err": None}
    q16, q50, q84 = np.percentile(dp, [16, 50, 84])
    t = float(np.mean(np.abs(dp) > tail))
    out = {"n": n, "sigma68": float((q84 - q16) / 2), "median": float(q50), "tail": t,
           "tail_err": math.sqrt(max(t * (1 - t), 1. / n) / n)}
    if bootstrap and n > 1:
        rng = np.random.default_rng(seed)
        vals = []
        for _ in range(bootstrap):
            s = dp[rng.integers(0, n, n)]
            a, b = np.percentile(s, [16, 84])
            vals.append((b - a) / 2)
        out["sigma68_err"] = float(np.std(vals))
    return out


def arrays(wd: str, config, sample, sel):
    """(dp, nactive, quality mask) of the events with a CE track and an MC crossing, or None."""
    d, nj, nfail = offline._load(wd, config, sample)
    if d is None:
        return None, nfail
    lv = offline.levels(d, sample, sel)
    m = lv["found"] & np.isfinite(d["dp"])
    return {"dp": d["dp"][m], "nactive": d["nactive"][m], "quality": lv["box"][m],
            "n_events": int(len(d["run"])), "n_jobs": nj}, nfail


def summary(wd: str, config, sample, sel, bootstrap: int = 0) -> dict:
    """-> {"events", "n_jobs", "n_failed", "all": stats, "quality": stats + "kept" (fraction of
    all), "by_nactive": {region: {"all": stats, "quality": stats}}}"""
    a, nfail = arrays(wd, config, sample, sel)
    if a is None:
        return {"events": 0, "n_jobs": 0, "n_failed": nfail, "note": "no ok offline jobs"}
    dp, na, q = a["dp"], a["nactive"], a["quality"]
    t = sel.resolution_tail
    res = {"events": a["n_events"], "n_jobs": a["n_jobs"], "n_failed": nfail, "tail_cut": t,
           "all": stats(dp, t, bootstrap), "quality": stats(dp[q], t, bootstrap), "by_nactive": {}}
    res["quality"]["kept"] = float(q.sum() / len(dp)) if len(dp) else None
    for lo, hi in REGIONS:
        r = (na >= (lo if lo is not None else -1)) & (na < (hi if hi is not None else 1e9))
        s_all = stats(dp[r], t, bootstrap)
        s_q = stats(dp[r & q], t, bootstrap)
        s_q["kept"] = float((r & q).sum() / r.sum()) if r.sum() else None
        res["by_nactive"][region_name(lo, hi)] = {"all": s_all, "quality": s_q}
    return res


def plots(wd: str, configs, sample, sel, outdir: str, labels: Optional[Dict[str, str]] = None) -> List[str]:
    """dp histograms (all / quality) of the configurations overlaid; returns the files written
    (PNG and PDF)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(outdir, exist_ok=True)
    written = []
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for c in configs:
        a, _ = arrays(wd, c, sample, sel)
        if a is None:
            continue
        name = (labels or {}).get(getattr(c, "name", c), getattr(c, "name", c))
        for ax, m, title in ((axes[0], np.ones(len(a["dp"]), bool), "all"), (axes[1], a["quality"], "quality cuts")):
            dp = np.clip(a["dp"][m], -5, 5)
            if len(dp):
                s = stats(a["dp"][m], sel.resolution_tail)
                ax.hist(dp, bins=100, range=(-5, 5), histtype="step", density=True,
                        label=f"{name}: s68 {s['sigma68']:.2f}, tail {100 * s['tail']:.1f}%")
            ax.set_title(f"{sample.name}: {title}")
    for ax in axes:
        ax.set_yscale("log")
        ax.set_xlabel("p_fit - p_MC at tracker entrance [MeV/c]")
        ax.legend(fontsize=7)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        f = os.path.join(outdir, f"resolution_{sample.name}.{ext}")
        fig.savefig(f, dpi=120)
        written.append(f)
    plt.close(fig)
    return written
