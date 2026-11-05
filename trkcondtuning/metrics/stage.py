"""
Where does the trigger lose CE events that Offline reconstructs? (port of scripts/stage_eff.py)

The `stage` jobs are trigger jobs with the TC / HS / KS filters of the objective paths in debug
mode (the art 'Begin processing' record lines give the event ids). For every event the Offline
reconstructs ('reco' level of offline.per_event of the same configuration) each path is
classified:
  pass      path accepted the event
  TC        time-cluster filter failed
  no helix  time cluster ok, no helix in the merged helix collection
  HS cuts   helices, but none passed the helix filter (the cuts failed by the helix that fails
            the fewest cuts are listed in 'details')
  no fit    helix filter passed, but the trigger KalSeed fit produced no track
  KS cuts   KalSeeds, none accepted (the cuts failed by the best seed are listed)
  other     passes all listed cuts but was rejected (helicity, calo-cluster requirement, ...)
Cut values are read from the resolved configuration of the job (job.dump.fcl).
"""
from __future__ import annotations

import collections
import os
import re
import statistics
from typing import Dict, List, Optional, Sequence, Tuple

from . import artlog
from .trigger import split_expr

CATEGORIES = ["pass", "TC", "no helix", "HS cuts", "no fit", "KS cuts", "other"]


def label(path: str) -> str:
    """cpr_TrkDe_75m70p_D0200 -> CprTrkDe75m70pD0200"""
    return path[0].upper() + path[1:].replace("_", "")


# ---------------------------------------------------------------- configuration (fhicl-dump)
def block(text: str, name: str) -> Optional[str]:
    """Body of the first 'name: {' (or 'name: [') block of a fhicl-dump, at any indentation."""
    m = re.search(r"^([ \t]*)" + re.escape(name) + r": ([{\[])[ \t]*$", text, re.M)
    if not m:
        return None
    close = "}" if m.group(2) == "{" else "]"
    mend = re.compile(r"^" + m.group(1) + re.escape(close) + r",?[ \t]*$", re.M).search(text, m.end())
    return text[m.end():mend.start() if mend else len(text)]


def values(body: str) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for k, v in re.findall(r"^\s*(\w+): ([^{\[\n]+)$", body, re.M):
        v = v.strip().strip('"')
        try:
            out[k] = float(v)
        except ValueError:
            out[k] = {"true": True, "false": False}.get(v, v)
    return out


def path_cuts(dump: str, path: str, pdg: int = 11):
    """(helix cuts, KalSeed cuts) of a path for the signal particle pdg: the positive-helicity
    selection and the fitparticle == pdg KalSeedCuts entry for pdg > 0 (conversion e-), the
    negative-helicity selection for pdg < 0 (conversion e+)."""
    L = label(path)
    hs = block(dump, L + "HSFilter")
    ks = block(dump, L + "KSFilter")
    hb = block(hs, "posHelicitySelection" if pdg > 0 else "negHelicitySelection") if hs else None
    kb = block(ks, "KalSeedCuts") if ks else None
    hcuts = values(hb) if hb else {}
    kcuts = {}
    for entry in (kb.split("},") if kb else []):
        v = values(entry)
        if v.get("fitparticle") == float(pdg):
            kcuts = v
            break
    return hcuts, kcuts


def helix_fails(h, c):
    tests = [("nSH", h["nhits"] >= c.get("minNStrawHits", -1e9)),
             ("pT", h["pT"] >= c.get("minPt", -1e9)),
             ("chi2XY", h["chi2XY"] <= c.get("maxChi2XY", 1e9)),
             ("chi2ZPhi", h["chi2ZPHI"] <= c.get("maxChi2PhiZ", 1e9)),
             ("d0", c.get("minD0", -1e9) <= h["d0"] <= c.get("maxD0", 1e9)),
             ("lambda", c.get("minAbsLambda", -1e9) <= h["lambda"] <= c.get("maxAbsLambda", 1e9)),
             ("nLoops", c.get("minNLoops", -1e9) <= h["nLoops"] <= c.get("maxNLoops", 1e9)),
             ("p", c.get("minMomentum", -1e9) <= h["p"] <= c.get("maxMomentum", 1e9)),
             ("hitRatio", h["hRatio"] >= c.get("minHitRatio", -1e9)),
             ("status", "HelixOK" in h["status"])]
    if "slopeSigMin" in c:
        tests.append(("slopeSig", h["slopeSignedSig"] > c["slopeSigMin"]))
    if "slopeSigMax" in c:
        tests.append(("slopeSig", h["slopeSignedSig"] < c["slopeSigMax"]))
    return [n for n, ok in tests if not ok]


def seed_fails(s, c):
    tests = [("nactive", s["nactive"] >= c.get("minNStrawHits", -1e9)),
             ("nstereo", s["nst"] >= c.get("minNStereo", 0)),
             ("nplanes", s["npl"] >= c.get("minNPlanes", 0)),
             ("p", c.get("minMomentum", -1e9) < s["mom"] < c.get("maxMomentum", 1e9)),
             ("momErr", s["momerr"] < c.get("maxMomErr", 1e9)),
             ("chi2dof", s["chi2dof"] < c.get("maxChi2DOF", 1e9)),
             ("fitcon", s["fitcon"] > c.get("minFitCons", -1e9)),
             ("tanDip", c.get("minTanDip", -1e9) < s["tandip"] < c.get("maxTanDip", 1e9)),
             ("d0", c.get("minD0", -1e9) < s["d0"] < c.get("maxD0", 1e9))]
    return [n for n, ok in tests if not ok]


# ---------------------------------------------------------------- log parsing
RE_EVT = re.compile(r"Begin processing the \S+ record\. run: (\d+) subRun: (\d+) event: (\d+)")
RE_KV = re.compile(r"(\w+) = (\( [^)]*\)|-?[\d.]+(?:e[+-]?\d+)?|\S+)")


def parse_log(log: str, paths: Sequence[str]) -> Dict[tuple, dict]:
    """{(run, subrun, event): {path: record}} from the debug output of the path filters."""
    labels = {label(p): p for p in paths}
    events: Dict[tuple, dict] = {}
    cur, hs_owner, ks_owner, helix = None, None, None, None
    with open(log, errors="replace") as fh:
        for line in fh:
            m = RE_EVT.search(line)
            if m:
                cur = {p: {"tc": False, "helices": [], "hs": False, "nks": None, "seeds": [],
                           "basicfail": 0, "ks": False} for p in paths}
                events[tuple(int(x) for x in m.groups())] = cur
                hs_owner = ks_owner = helix = None
                continue
            if cur is None:
                continue
            head = line.split(" ", 1)[0]
            for L, p in labels.items():
                if head == L + "TCFilter" and "passed event" in line:
                    cur[p]["tc"] = True
                elif head == L + "HSFilter":
                    if "Input from" in line:
                        hs_owner = p
                    elif "passed event" in line:
                        cur[p]["hs"] = True
                elif head == L + "KSFilter":
                    if " input " in line:
                        ks_owner = p
                        mm = re.search(r"has (\d+) tracks", line)
                        cur[p]["nks"] = int(mm.group(1)) if mm else None
                    elif "accepted a track" in line:
                        cur[p]["ks"] = True
            if line.startswith("[HelixFilter] : status") and hs_owner:
                helix = {"status": line.split("status = ")[1].split(")")[0]}
                helix.update({k: float(v) for k, v in RE_KV.findall(line.split(")", 1)[1])})
            elif line.startswith("[HelixFilter] : chi2XY") and helix is not None:
                helix.update({k: float(v) for k, v in RE_KV.findall(line)})
                cur[hs_owner]["helices"].append(helix)
                helix = None
            elif line.startswith("[KalSeedFilter::filter]") and ks_owner:
                f = line.split()[1:]
                if f and f[0].isdigit():
                    keys = ["nactive", "nst", "npl", "mom", "momerr", "chi2dof", "fitcon", "tandip", "d0"]
                    cur[ks_owner]["seeds"].append(dict(zip(keys, map(float, f))))
            elif line.startswith("KalSeedFilter: basic cuts failed") and ks_owner:
                cur[ks_owner]["basicfail"] += 1
    return events


def classify(r, hcuts, kcuts) -> Tuple[str, str]:
    """(category, detail) for one path in one event."""
    if r["ks"]:
        return "pass", ""
    if not r["tc"]:
        return "TC", ""
    if r["nks"] is None:   # KalSeed filter not reached: the helix stage failed
        if not r["helices"]:
            return "no helix", ""
        best = min((helix_fails(h, hcuts) for h in r["helices"]), key=len)
        return ("HS cuts", "+".join(best)) if best else ("other", "helix passes listed cuts")
    if r["nks"] == 0:
        return "no fit", ""
    if not r["seeds"]:
        return "KS cuts", "status/particle/direction"
    best = min((seed_fails(s, kcuts) for s in r["seeds"]), key=len)
    return ("KS cuts", "+".join(best)) if best else ("other", "seed passes listed cuts")


# ---------------------------------------------------------------- driver
def losses(wd: str, config, sample, paths: Sequence[str], offline_events, level: str = "reco",
           max_details: int = 6) -> dict:
    """-> {"n": events with an Offline track (of those in the stage log), "n_missing": Offline
    events not in the stage log, "n_jobs", "n_failed", "paths": {path: {category: n, "details":
    {category: {reason: n}}, "median_nactive": {category: x}}}, "ors": {expr: {"pass", "lost",
    "stages": {"catA/catB": n}}}, "warnings"}.
    offline_events: offline.per_event(...) dict (events with ev[level] true are used) or a set / list
    of event ids. `paths` may contain 'a|b' expressions: those are reported under "ors"."""
    dirs, nfail = artlog.ok_jobs(wd, "stage", config, sample, need="job.log")
    singles: List[str] = []
    for e in paths:
        for p in split_expr(e):
            if p not in singles:
                singles.append(p)
    ors = [e for e in paths if "|" in e]
    if isinstance(offline_events, dict):
        good = {k: v.get("nactive") for k, v in offline_events.items()
                if (v.get(level) if isinstance(v, dict) else v)}
    else:
        good = {k: None for k in offline_events}
    res = {"n_jobs": len(dirs), "n_failed": nfail, "paths": {}, "ors": {}, "warnings": []}
    events: Dict[tuple, dict] = {}
    cuts: Dict[str, tuple] = {}
    for d in dirs:
        events.update(parse_log(os.path.join(d, "job.log"), singles))
        dumpf = os.path.join(d, "job.dump.fcl")
        if os.path.exists(dumpf) and not cuts:
            dump = open(dumpf).read()
            for p in singles:
                cuts[p] = path_cuts(dump, p, getattr(sample, "pdg", 11))
                if not cuts[p][0] or not cuts[p][1]:
                    res["warnings"].append(f"{p}: filter cuts not found in job.dump.fcl; 'other' may be inflated")
    if not dirs:
        res["note"] = "no ok stage jobs"
        res["n"] = 0
        return res
    common = [k for k in good if k in events]
    res["n"], res["n_missing"] = len(common), len(good) - len(common)
    result: Dict[Tuple[str, tuple], str] = {}
    for p in singles:
        cats, details, nact = collections.Counter(), collections.defaultdict(collections.Counter), \
            collections.defaultdict(list)
        for k in common:
            c, dd = classify(events[k][p], *cuts.get(p, ({}, {})))
            result[(p, k)] = c
            cats[c] += 1
            details[c][dd] += 1
            if good[k] is not None:
                nact[c].append(good[k])
        out = {c: cats[c] for c in CATEGORIES}
        out["details"] = {c: dict(details[c].most_common(max_details)) for c in ("HS cuts", "KS cuts", "other") if details[c]}
        out["median_nactive"] = {c: statistics.median(nact[c]) for c in CATEGORIES if nact[c]}
        res["paths"][p] = out
    for e in ors:
        ps = split_expr(e)
        npass = 0
        stages = collections.Counter()
        for k in common:
            cs = [result[(p, k)] for p in ps]
            if "pass" in cs:
                npass += 1
            else:
                stages["/".join(cs)] += 1
        res["ors"][e] = {"pass": npass, "lost": len(common) - npass, "stages": dict(stages.most_common(max_details))}
    return res
