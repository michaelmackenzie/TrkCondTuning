"""
Offline reconstruction metrics from the EventNtuples (nts.root, `offline` jobs).

Track per event (the 'CE track'): the highest-nactive fit with trk.pdg == sample.pdg, p_z > 0 at
TT_Front, whose main MC particle is the primary (trkmcsim[0].prirel same). Levels:
  found    such a track exists
  reco     found, p(TT_Front) > sample.pmin and nactive >= sel.nactive_trig
  loose    found, p > sample.pmin and nactive >= sel.nactive_loose
  quality  reco and the TrkQual-input box cuts of the OfflineSelection
Trigger bits are the trig_<path> branches of the ntuple (written from the Redigitize trigger
process of the same events). Implemented with uproot/awkward on the EventNtuple branches
(vectorized; pyevtana's object loop gives the same selection, ~10x slower for this purpose).
"""
from __future__ import annotations

import math
import os
from typing import Dict, List, Sequence, Tuple

import numpy as np

from . import artlog
from .trigger import all_paths, split_expr

SAME = 0       # MCRelationship::same
TT_FRONT = 0   # SurfaceIdDetail::TT_Front
LEVELS = ("found", "reco", "loose", "quality")
BRANCHES = ["trk.pdg", "trk.nhits", "trk.nactive",
            "trk.fitcon", "trksegs", "trksegpars_lh", "trkmcsim", "trksegsmc"]
_cache: Dict[tuple, dict] = {}


def _mag(v):
    c = v.fCoordinates
    return np.sqrt(c.fX ** 2 + c.fY ** 2 + c.fZ ** 2)


def load_file(path: str, pdg: int) -> dict:
    """One entry per ntuple event: arrays run, subrun, event, has (CE track found), p, dp (NaN
    without an MC crossing), nactive, nhits, fitcon, t0err, momerr, and trig (dict path -> bool
    array of the trig_<path> branches)."""
    import awkward as ak
    import uproot
    key = (path, pdg, os.path.getmtime(path))
    if key in _cache:
        return _cache[key]
    with uproot.open(path) as f:
        t = f["EventNtuple/ntuple"]
        trigs = [k for k in t.keys() if k.startswith("trig_") and "/" not in k]
        ids = [k for k in ("evtinfo/run", "evtinfo/subrun", "evtinfo/event") if k in t.keys()]
        if len(ids) != 3:
            ids = ["evtinfo.run", "evtinfo.subrun", "evtinfo.event"]
        a = t.arrays(ids + BRANCHES + trigs, library="ak")
    segs, mc = a["trksegs"], a["trksegsmc"]
    front = (segs.sid == TT_FRONT) & (segs.mom.fCoordinates.fZ > 0)
    has_front = ak.any(front, axis=-1)
    ifront = ak.argmax(ak.values_astype(front, np.int8), axis=-1, keepdims=True)
    seg = ak.firsts(segs[ifront], axis=-1)
    par = ak.firsts(a["trksegpars_lh"][ifront], axis=-1)
    sim0 = ak.firsts(a["trkmcsim"], axis=-1)
    primary = ak.fill_none(sim0.prirel["_rel"] == SAME, False)
    good = (a["trk.pdg"] == pdg) & has_front & primary
    mcf = mc[(mc.sid == TT_FRONT) & (mc.mom.fCoordinates.fZ > 0)]
    imc = ak.argmin(abs(mcf.time - seg.time), axis=-1, keepdims=True)
    pmc = ak.firsts(_mag(mcf[imc].mom), axis=-1)
    nact = ak.where(good, a["trk.nactive"], -1)
    ibest = ak.argmax(nact, axis=-1, keepdims=True)
    has = ak.fill_none(ak.firsts(good[ibest], axis=-1), False)
    has_np = ak.to_numpy(has).astype(bool)

    def best(x, fill=np.nan):
        v = ak.fill_none(ak.firsts(x[ibest], axis=-1), fill)
        return np.where(has_np, ak.to_numpy(v).astype(float), fill)

    p = _mag(seg.mom)
    nactive = best(a["trk.nactive"], 0.)
    out = {
        "run": ak.to_numpy(a[ids[0]]).astype(np.int64),
        "subrun": ak.to_numpy(a[ids[1]]).astype(np.int64),
        "event": ak.to_numpy(a[ids[2]]).astype(np.int64),
        "has": has_np,
        "p": best(p),
        "dp": np.where(has_np, best(p) - best(ak.fill_none(pmc, np.nan)), np.nan),
        "nactive": nactive,
        "nhits": best(a["trk.nhits"], 0.),
        "fitcon": best(a["trk.fitcon"]),
        "t0err": best(par.t0err),
        "momerr": best(seg.momerr),
        "trig": {k[5:]: ak.to_numpy(a[k]).astype(bool) for k in trigs},
    }
    _cache[key] = out
    return out


def levels(d: dict, sample, sel) -> Dict[str, np.ndarray]:
    """Boolean arrays of the Offline levels for loaded events d."""
    found = d["has"]
    with np.errstate(invalid="ignore"):
        ptrk = found & (d["p"] > sample.pmin)
        reco = ptrk & (d["nactive"] >= sel.nactive_trig)
        loose = ptrk & (d["nactive"] >= sel.nactive_loose)
        factive = d["nactive"] / np.maximum(d["nhits"], 1)
        box = ((factive > sel.min_active_frac) & (d["fitcon"] > sel.min_fitcon)
               & (d["t0err"] < sel.max_t0err) & (d["momerr"] < sel.max_momerr))
    return {"found": found, "reco": reco, "loose": loose, "quality": reco & box, "box": found & box}


def _load(wd, config, sample):
    dirs, nfail = artlog.ok_jobs(wd, "offline", config, sample, need="nts.root")
    parts = [load_file(os.path.join(d, "nts.root"), sample.pdg) for d in dirs]
    if not parts:
        return None, 0, nfail

    def cat(k):
        return np.concatenate([p[k] for p in parts])
    d = {k: cat(k) for k in ("run", "subrun", "event", "has", "p", "dp", "nactive", "nhits", "fitcon", "t0err", "momerr")}
    paths = set.intersection(*[set(p["trig"]) for p in parts])
    d["trig"] = {k: np.concatenate([p["trig"][k] for p in parts]) for k in paths}
    d["trig_all_paths"] = sorted(set.union(*[set(p["trig"]) for p in parts]))
    return d, len(dirs), nfail


def _eval(d, expr):
    m = None
    for p in split_expr(expr):
        b = d["trig"][p]
        m = b if m is None else (m | b)
    return m


def _binom(k, n):
    if n <= 0:
        return float("nan")
    e = k / n
    return math.sqrt(max(e * (1 - e), 1. / n) / n)


def efficiency(wd: str, config, sample, sel, paths: Sequence[str]) -> dict:
    """-> {"events", "found", "reco", "loose", "quality", "trig_all": {expr: n},
           "joint": {level: {expr: n}} (Offline level AND trigger), "trig_given_reco": = joint["reco"],
           "n_jobs", "n_failed", "missing_paths"}; empty dict-with-note if there are no ntuples.
    The trigger efficiency given a level is joint[level][expr] / res[level]."""
    d, nj, nfail = _load(wd, config, sample)
    if d is None:
        return {"events": 0, "n_jobs": 0, "n_failed": nfail, "note": "no ok offline jobs"}
    lv = levels(d, sample, sel)
    res = {"events": int(len(d["run"])), "n_jobs": nj, "n_failed": nfail,
           "pmin": sample.pmin, "nactive_trig": sel.nactive_trig, "nactive_loose": sel.nactive_loose}
    for k in LEVELS:
        res[k] = int(lv[k].sum())
    missing = [p for p in all_paths(paths) if p not in d["trig"]]
    res["missing_paths"] = missing
    res["trig_all"], res["joint"] = {}, {k: {} for k in LEVELS}
    for e in paths:
        if any(p in missing for p in split_expr(e)):
            continue
        m = _eval(d, e)
        res["trig_all"][e] = int(m.sum())
        for k in LEVELS:
            res["joint"][k][e] = int((m & lv[k]).sum())
    res["trig_given_reco"] = res["joint"]["reco"]
    return res


def per_event(wd: str, config, sample, sel) -> Dict[Tuple[int, int, int], dict]:
    """{(run, subrun, event): {"found", "reco", "loose", "quality": bool, "dp": float|None,
    "nactive": int, "p": float|None}} over the ok offline jobs."""
    d, _, _ = _load(wd, config, sample)
    out: Dict[Tuple[int, int, int], dict] = {}
    if d is None:
        return out
    lv = levels(d, sample, sel)
    for i in range(len(d["run"])):
        dp = d["dp"][i]
        p = d["p"][i]
        out[(int(d["run"][i]), int(d["subrun"][i]), int(d["event"][i]))] = {
            "found": bool(lv["found"][i]), "reco": bool(lv["reco"][i]), "loose": bool(lv["loose"][i]),
            "quality": bool(lv["quality"][i]),
            "dp": None if math.isnan(dp) else float(dp), "p": None if math.isnan(p) else float(p),
            "nactive": int(d["nactive"][i])}
    return out
