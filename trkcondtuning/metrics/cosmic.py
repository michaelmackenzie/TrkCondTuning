"""
Cosmic-signal trigger efficiency by particle type and direction (port of scripts/cosmic_eff.py)
from the ana.root trees of the cosmic trigger jobs. The signal particle is the analyzer's: the
highest-momentum e+- / mu+- with >= 5 straw hits, its momentum at its earliest straw gas step.
Categories: electron / muon (|pdg| 11 / 13) x down (p_z > 0) / up (p_z < 0), and 'all'; only
signal particles with p > pmin are counted.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

from . import trigger


def efficiency(wd: str, config, sample, paths: Sequence[str], pmin: float = 75., min_nsh: int = 0) -> dict:
    """-> {"events": n (MC-triggerable), "n_other": events without an e/mu signal particle,
    "categories": {category: {"events": n, "pass": {expr: n}}}, "n_jobs", "n_failed",
    "missing_paths"}"""
    a, info = trigger.read_tree(wd, "trig", config, sample, paths, extra=("pdg", "pz", "p", "nsh"))
    n = len(a["run"])
    res = {"events": n, "n_jobs": info["n_jobs"], "n_failed": info["n_failed"],
           "missing_paths": list(info["missing_paths"]), "pmin": pmin, "categories": {},
           "n_other": int(np.sum(a["pdg"] == 0)) if n else 0, "warnings": list(info["warnings"])}
    if n == 0:
        return res
    pdg, pz = a["pdg"], a["pz"]
    sel = (a["nsh"] >= min_nsh) & (a["p"] > pmin)
    cats = {}
    for name, pdgs in (("electron", [11, -11]), ("muon", [13, -13])):
        for d, dsel in (("down", pz > 0), ("up", pz < 0)):
            cats[f"{name} {d}"] = sel & np.isin(pdg, pdgs) & dsel
    cats["all"] = sel & (pdg != 0)
    for cat, m in cats.items():
        r = {"events": int(m.sum()), "pass": {}}
        for e in paths:
            if any(p in info["missing_paths"] for p in trigger.split_expr(e)):
                continue
            r["pass"][e] = int((trigger.eval_expr(a, e) & m).sum())
        res["categories"][cat] = r
    return res
