"""
Trigger metrics from the per-event bits of the trigger jobs (AprHelixTruthAna tree
aprAna/helices in ana.root: one entry per processed event, branches run/subrun/event and
trig_<path>). A path expression 'a|b' is the OR of the paths a and b.
"""
from __future__ import annotations

import math
import os
from typing import Dict, List, Sequence, Tuple

import numpy as np

from . import artlog

TREE = "aprAna/helices"
UL_EVENTS = 3.0  # 95% CL upper limit on the number of events when none pass


def split_expr(expr: str) -> List[str]:
    return [p.strip() for p in expr.split("|")]


def all_paths(exprs: Sequence[str]) -> List[str]:
    out: List[str] = []
    for e in exprs:
        for p in split_expr(e):
            if p not in out:
                out.append(p)
    return out


def read_tree(wd: str, kind: str, config, sample, paths: Sequence[str], extra: Sequence[str] = ()):
    """Concatenated arrays of the ok jobs' ana.root: dict with run, subrun, event, the extra
    branches and trig_<p> (bool arrays) for each available path; plus info {n_jobs, n_failed,
    missing_paths, dirs, warnings}."""
    import uproot
    dirs, nfail = artlog.ok_jobs(wd, kind, config, sample, need="ana.root")
    info = {"n_jobs": len(dirs), "n_failed": nfail, "missing_paths": [], "dirs": dirs, "warnings": []}
    names = ["run", "subrun", "event"] + list(extra)
    cols: Dict[str, list] = {}
    plist = all_paths(paths)
    avail = set(plist)
    for d in dirs:
        with uproot.open(os.path.join(d, "ana.root")) as f:
            if TREE not in f:
                info["warnings"].append(f"{d}: no tree {TREE}")
                continue
            t = f[TREE]
            keys = set(t.keys())
            have = [p for p in plist if f"trig_{p}" in keys]
            avail &= set(have)
            for p in plist:
                if p not in have and p not in info["missing_paths"]:
                    info["missing_paths"].append(p)
            want = [n for n in names if n in keys] + [f"trig_{p}" for p in have]
            a = t.arrays(want, library="np")
            n = len(a["run"])
            for k in names + [f"trig_{p}" for p in plist]:
                cols.setdefault(k, []).append(a[k] if k in a else np.zeros(n, dtype=float) if k in names else np.zeros(n, bool))
    out = {k: (np.concatenate(v) if v else np.zeros(0)) for k, v in cols.items()}
    for k in names:
        out.setdefault(k, np.zeros(0))
    for p in plist:
        out[f"trig_{p}"] = out.get(f"trig_{p}", np.zeros(len(out["run"]), bool)).astype(bool)
    info["available"] = [p for p in plist if p in avail and p not in info["missing_paths"]]
    return out, info


def eval_expr(arrays: Dict[str, np.ndarray], expr: str) -> np.ndarray:
    m = None
    for p in split_expr(expr):
        b = arrays[f"trig_{p}"]
        m = b if m is None else (m | b)
    return m


def _crosscheck(wd, config, sample, dirs, arrays, paths, n_events, warns, role):
    """Compare tree entries / pass counts with the TrigReport of the same jobs."""
    rep = artlog.sum_path_counts(dirs)
    out = {}
    if not rep:
        warns.append("no TrigReport found in job logs; cross-check skipped")
        return out
    if role != "background" and "TriggerablePath" in rep:
        rn = rep["TriggerablePath"][1]
        out["triggerable_report"] = rn
        if rn != n_events:
            warns.append(f"TriggerablePath count in TrigReport ({rn}) != ana.root entries ({n_events})")
    for p in all_paths(paths):
        if p in rep and f"trig_{p}" in arrays:
            ntree = int(arrays[f"trig_{p}"].sum())
            out.setdefault("path_counts", {})[p] = {"run": rep[p][0], "passed": rep[p][1], "tree": ntree}
            if ntree != rep[p][1]:
                warns.append(f"path {p}: ana.root passes {ntree} != TrigReport {rep[p][1]}")
    return out


def _binom(k: int, n: int) -> float:
    if n <= 0:
        return float("nan")
    e = k / n
    return math.sqrt(max(e * (1 - e), 1. / n) / n)


def signal(wd: str, config, sample, paths: Sequence[str]) -> dict:
    """Trigger efficiency of MC-triggerable events (all entries of the ana.root trees).
    -> {"events", "pass": {expr: n}, "eff": {expr: [e, err]}, "path_counts", "n_jobs", "n_failed",
        "missing_paths", "warnings"}"""
    arrays, info = read_tree(wd, "trig", config, sample, paths)
    n = len(arrays["run"])
    res = {"events": n, "n_jobs": info["n_jobs"], "n_failed": info["n_failed"],
           "missing_paths": [p for p in info["missing_paths"]], "pass": {}, "eff": {}}
    warns = list(info["warnings"])
    for e in paths:
        if any(p in info["missing_paths"] for p in split_expr(e)):
            continue
        k = int(eval_expr(arrays, e).sum())
        res["pass"][e] = k
        res["eff"][e] = [k / n if n else float("nan"), _binom(k, n)]
    res.update(_crosscheck(wd, config, sample, info["dirs"], arrays, paths, n, warns, "signal"))
    res["warnings"] = warns
    return res


def signal_bits(wd: str, config, sample, paths: Sequence[str]) -> Dict[Tuple[int, int, int], Dict[str, bool]]:
    """{(run, subrun, event): {path: bool}} of the individual paths of the expressions."""
    arrays, info = read_tree(wd, "trig", config, sample, paths)
    plist = [p for p in all_paths(paths) if p not in info["missing_paths"]]
    return _bits(arrays, plist)


def _bits(arrays, plist):
    run, sub, evt = (arrays[k].astype(np.int64).tolist() for k in ("run", "subrun", "event"))
    cols = {p: arrays[f"trig_{p}"].tolist() for p in plist}
    return {(r, s, e): {p: cols[p][i] for p in plist} for i, (r, s, e) in enumerate(zip(run, sub, evt))}


def rate_hz(n_pass: int, n_events: int, sample) -> float:
    """pass / events x (1e9 / microbunch_ns) x duty_factor [Hz]; 0 passes -> UL_EVENTS events."""
    if n_events <= 0:
        return float("nan")
    return (n_pass if n_pass else UL_EVENTS) / n_events * (1e9 / sample.microbunch_ns) * sample.duty_factor


def background(wd: str, config, sample, paths: Sequence[str]) -> dict:
    """NoPrimary background: -> {"events", "pass": {expr: n}, "rate_hz": {expr: Hz} (passes > 0),
    "rate_err_hz", "rate_ul": {expr: Hz upper limit at 95% CL (3 events)} (no passes),
    "path_counts", "n_jobs", "n_failed", "missing_paths", "warnings"}"""
    arrays, info = read_tree(wd, "trig", config, sample, paths)
    n = len(arrays["run"])
    res = {"events": n, "n_jobs": info["n_jobs"], "n_failed": info["n_failed"],
           "missing_paths": list(info["missing_paths"]), "pass": {}, "rate_hz": {}, "rate_err_hz": {},
           "rate_ul": {}, "duty_factor": sample.duty_factor, "microbunch_ns": sample.microbunch_ns}
    warns = list(info["warnings"])
    for e in paths:
        if any(p in info["missing_paths"] for p in split_expr(e)):
            continue
        k = int(eval_expr(arrays, e).sum())
        res["pass"][e] = k
        if k:
            res["rate_hz"][e] = rate_hz(k, n, sample)
            res["rate_err_hz"][e] = rate_hz(k, n, sample) / math.sqrt(k)
        else:
            res["rate_ul"][e] = rate_hz(0, n, sample)
    res.update(_crosscheck(wd, config, sample, info["dirs"], arrays, paths, n, warns, "background"))
    res["warnings"] = warns
    return res


def background_bits(wd: str, config, sample, paths: Sequence[str]):
    """Per-event bits of the background sample (same as signal_bits)."""
    return signal_bits(wd, config, sample, paths)


def eval_bits(bits: Dict, expr: str) -> Dict:
    """{event id: bool} of a path expression over a bits dict."""
    ps = split_expr(expr)
    return {k: any(v[p] for p in ps) for k, v in bits.items()}


def paired(bits_a: Dict, bits_b: Dict, expr: str) -> dict:
    """McNemar comparison of two configurations on the common events:
    gain = pass in b only, loss = pass in a only; z = (gain - loss) / sqrt(gain + loss)."""
    ps = split_expr(expr)
    common = [k for k in bits_a if k in bits_b]
    gain = loss = pa = pb = 0
    for k in common:
        a = any(bits_a[k][p] for p in ps)
        b = any(bits_b[k][p] for p in ps)
        pa += a
        pb += b
        gain += (b and not a)
        loss += (a and not b)
    z = (gain - loss) / math.sqrt(gain + loss) if gain + loss else 0.0
    return {"n": len(common), "gain": int(gain), "loss": int(loss), "z": z, "pass_a": int(pa), "pass_b": int(pb)}
