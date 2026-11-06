"""
Compare the detector conditions of several configurations (tracker DB tables + ProditionsService
values), and check the validity of re-digitizing the nominal samples with each condition.

What a configuration's tracker conditions are made of
  - the DbService purpose / version: tables with an IOV covering the run of the input samples
    (dbTool print-run, then print-content per CID; CIDs are immutable and cached on disk);
  - the condition's text tables, which replace the DB table of the same name;
  - the ProditionsService values after the condition fcl and the configuration's settings
    (fhicl-get on Services.Reco + fragments, i.e. defaults from Offline included).

Quantities (per configuration)
  - straws without signal (TrackerStatus::noSignal: plane OR panel OR straw status with Absent,
    NoWire, NoHV, NoLV, NoGas, LowGasGain, NoHVPreamp, NoCalPreamp or Disabled), per station;
    noisy straws (Sparking / Noise / Pickup); NoHV panels
  - preamp thresholds (hv / cal end, mV), ADC gain, total time offsets (panel + preamp delays)
  - reco straw alignment (TrkAlignStraw) vs the alignment used by the simulation
    (TrkAlignStrawSim): wire / straw displacement differences
  - gas gain, wire voltage, threshold noise and the straw-response (reco) parameters

Re-digitization checks against the reference (nominal) configuration, see README "Validity":
straws that have signal in the condition but not in the reference, straw ends with a LOWER
threshold, a higher gas gain or lower threshold noise. Each raises the hit efficiency, which the
kept StrawGasSteps cannot reproduce.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
from typing import Dict, List, Optional, Sequence, Tuple

from .study import Config, Study, repo_path

NPLANES, NPANELS, NSTRAWS = 36, 6, 96
THR_HIST = (6.0, 20.0, 56)   # preamp threshold histogram [mV]: low, high, bins
NUSTRAWS = NPLANES * NPANELS * NSTRAWS

NO_SIGNAL = {"Absent", "NoWire", "NoHV", "NoLV", "NoGas", "LowGasGain", "NoHVPreamp",
             "NoCalPreamp", "Disabled"}
NOISY = {"Sparking", "Noise", "Pickup"}
STATUS_TABLES = ("TrkPlaneStatus", "TrkPanelStatus", "TrkStrawStatusLong", "TrkStrawStatusShort")
TRACKER_TABLES = STATUS_TABLES + ("TrkPreampStraw", "TrkDelayPanel", "TrkDelayRStraw",
                                  "TrkAlignStraw", "TrkAlignStrawSim")
# ProditionsService parameters compared (scalars; strawResponse arrays are summarized)
SCALARS = ("strawPhysics.gasGain", "strawDrift.wireVoltage", "strawElectronics.thresholdAnalogNoise")
RESPONSE = ("strawResponse.eBins", "strawResponse.eBinWidth", "strawResponse.tdCentralRes",
            "strawResponse.tdResSlope", "strawResponse.eHalfPVScale",
            "strawResponse.strawHalfPropVelocity", "strawResponse.totDriftTime",
            "strawResponse.totDriftError")


# --------------------------------------------------------------------------- table I/O
def parse_tables(text: str) -> Dict[str, List[List[str]]]:
    """DbService text format: 'TABLE <name>' then CSV rows; '#' comments."""
    out: Dict[str, List[List[str]]] = {}
    cur = None
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("TABLE"):
            cur = s.split()[1]
            out[cur] = []
            continue
        if cur is not None:
            out[cur].append([c.strip() for c in s.split(",")])
    return out


def _run(cmd: List[str], env: Dict[str, str], cwd: Optional[str] = None) -> str:
    r = subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return r.stdout


def db_cids(purpose: str, version: str, run: int, env: Dict[str, str]) -> Dict[str, Tuple[int, str]]:
    """{table: (cid, iov)} of the calibration set for one run (dbTool print-run)."""
    out = {}
    txt = _run(["dbTool", "print-run", "--purpose", purpose, "--version", version, "--run", str(run)], env)
    for line in txt.splitlines():
        f = line.split()
        if len(f) == 3 and f[1].isdigit():
            out[f[0]] = (int(f[1]), f[2])
    if not out:
        raise RuntimeError(f"no tables for {purpose} {version} run {run}:\n{txt}")
    return out


def db_content(cid: int, env: Dict[str, str], cache: str) -> Dict[str, List[List[str]]]:
    os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, f"cid_{cid}.txt")
    if not os.path.exists(path):
        txt = _run(["dbTool", "print-content", "--cid", str(cid)], env)
        with open(path + ".tmp", "w") as f:
            f.write(txt)
        os.replace(path + ".tmp", path)
    with open(path) as f:
        return parse_tables(f.read())


def tracker_tables(config: Config, run: int, env: Dict[str, str], cache: str) -> Dict[str, Dict]:
    """{table: {"source": "cid N (iov)" | "text: file", "rows": [...]}} for TRACKER_TABLES."""
    cond = config.condition
    cids = db_cids(cond.db_purpose, cond.db_version, run, env)
    out = {}
    for t in TRACKER_TABLES:
        if t in cids:
            cid, iov = cids[t]
            out[t] = {"source": f"cid {cid} ({iov})", "rows": db_content(cid, env, cache).get(t, [])}
        else:
            out[t] = {"source": "none", "rows": []}
    for tt in cond.text_tables:
        with open(repo_path(tt)) as f:
            for t, rows in parse_tables(f.read()).items():
                if t in TRACKER_TABLES:
                    out[t] = {"source": f"text {os.path.basename(tt)}", "rows": rows}
    return out


def proditions(config: Config, env: Dict[str, str], tmpdir: str) -> Dict[str, object]:
    """ProditionsService values seen by the reco (Services.Reco + condition fcl + the
    configuration's settings for the reco). Arrays as lists."""
    os.makedirs(tmpdir, exist_ok=True)
    lines = ['#include "Offline/fcl/standardServices.fcl"', "services : @local::Services.Reco"]
    if config.condition.fcl:
        lines.append(open(repo_path(config.condition.fcl)).read())
    for s in config.ordered("reco"):
        lines.append(s.render())
    path = os.path.join(tmpdir, f"proditions_{config.name}.fcl")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    out: Dict[str, object] = {}
    for k in SCALARS + RESPONSE:
        key = f"services.ProditionsService.{k}"
        try:
            out[k] = float(_run(["fhicl-get", "--atom-as", "double", key, path], env).strip())
        except RuntimeError:
            txt = _run(["fhicl-get", "--sequence-of", "double", key, path], env)
            out[k] = [float(x) for x in txt.split()]
    return out


# --------------------------------------------------------------------------- derived
def _sid(s: str) -> Tuple[int, ...]:
    return tuple(int(x) for x in s.split("_"))


def straw_status(tables: Dict[str, Dict]) -> List[set]:
    """Net status words (set of names) per unique straw, as TrackerStatus aggregates them."""
    st = [set() for _ in range(NUSTRAWS)]
    # the table sets the granularity (TrackerStatusMaker: addStatus(id, table.sidMask(), ...)),
    # e.g. "6_2_0" in TrkPanelStatus is the whole panel 6_2
    level = {"TrkPlaneStatus": 1, "TrkPanelStatus": 2, "TrkStrawStatusLong": 3, "TrkStrawStatusShort": 3}
    for t in STATUS_TABLES:
        for row in tables[t]["rows"]:
            idx, words = _sid(row[0])[:level[t]], set(row[1].split(":"))
            if len(idx) == 1:
                rng = range(idx[0] * NPANELS * NSTRAWS, (idx[0] + 1) * NPANELS * NSTRAWS)
            elif len(idx) == 2:
                b = (idx[0] * NPANELS + idx[1]) * NSTRAWS
                rng = range(b, b + NSTRAWS)
            else:
                b = (idx[0] * NPANELS + idx[1]) * NSTRAWS + idx[2]
                rng = range(b, b + 1)
            for i in rng:
                st[i] |= words
    return st


def _stats(v: Sequence[float]) -> Dict[str, float]:
    if not v:
        return {}
    s = sorted(v)
    return {"n": len(v), "mean": statistics.fmean(v), "rms": statistics.pstdev(v),
            "min": s[0], "median": s[len(s) // 2], "max": s[-1]}


def summarize(tables: Dict[str, Dict], prod: Dict[str, object]) -> Dict:
    st = straw_status(tables)
    dead = [bool(w & NO_SIGNAL) for w in st]
    noisy = [bool(w & NOISY) and not d for w, d in zip(st, dead)]
    per_station = [sum(dead[i] for i in range(s * 2 * NPANELS * NSTRAWS, (s + 1) * 2 * NPANELS * NSTRAWS))
                   for s in range(NPLANES // 2)]
    nohv_panels = sorted(r[0] for r in tables["TrkPanelStatus"]["rows"] if "NoHV" in r[1].split(":"))
    full_panels_dead = sum(all(dead[p * NSTRAWS:(p + 1) * NSTRAWS]) for p in range(NPLANES * NPANELS))
    # why straws are dead (first matching reason, in order of precedence)
    reasons: Dict[str, int] = {}
    for w in st:
        if w & NO_SIGNAL:
            r = ("NoHV (panel)" if "NoHV" in w else "no preamp / wire / absent"
                 if w & {"Absent", "NoWire", "NoHVPreamp", "NoCalPreamp"} else
                 "Disabled" if "Disabled" in w else "other")
            reasons[r] = reasons.get(r, 0) + 1
    pre = tables["TrkPreampStraw"]["rows"]
    thr_hv = [float(r[3]) for r in pre]
    thr_cal = [float(r[4]) for r in pre]
    gain = [float(r[5]) for r in pre]
    alive = [i for i in range(len(pre)) if not dead[i]]
    dpanel = {int(r[0]): float(r[1]) for r in tables["TrkDelayPanel"]["rows"]}
    dstraw = {int(r[0]): (float(r[1]), float(r[2])) for r in tables["TrkDelayRStraw"]["rows"]}
    off_hv = [dpanel.get(i // NSTRAWS, 0.) + dstraw.get(i % NSTRAWS, (0., 0.))[0] + float(pre[i][1])
              for i in range(len(pre))]
    off_cal = [dpanel.get(i // NSTRAWS, 0.) + dstraw.get(i % NSTRAWS, (0., 0.))[1] + float(pre[i][2])
               for i in range(len(pre))]
    # alignment: reco minus sim (wire hv/cal dV dW, straw hv/cal dV dW)
    sim = {r[1]: [float(x) for x in r[2:]] for r in tables["TrkAlignStrawSim"]["rows"]}
    rec = {r[1]: [float(x) for x in r[2:]] for r in tables["TrkAlignStraw"]["rows"]}
    cols = ["wire_cal_dV", "wire_cal_dW", "wire_hv_dV", "wire_hv_dW",
            "straw_cal_dV", "straw_cal_dW", "straw_hv_dV", "straw_hv_dW"]
    align = {}
    common = [k for k in rec if k in sim]
    for j, c in enumerate(cols):
        align[c] = _stats([rec[k][j] - sim[k][j] for k in common])
    resp = {}
    for k in RESPONSE:
        v = prod.get(k)
        resp[k] = _stats(v) if isinstance(v, list) else v
    per_panel = [sum(dead[p * NSTRAWS:(p + 1) * NSTRAWS]) for p in range(NPLANES * NPANELS)]
    lo, hi, nb = THR_HIST
    hist = [0] * nb
    for i in alive:
        for v in (thr_hv[i], thr_cal[i]):
            b = int((v - lo) / (hi - lo) * nb)
            hist[min(max(b, 0), nb - 1)] += 1   # under/overflow into the edge bins
    return {
        "sources": {t: tables[t]["source"] for t in TRACKER_TABLES},
        "dead_straws": sum(dead), "dead_fraction": sum(dead) / NUSTRAWS,
        "dead_by_reason": reasons, "dead_per_station": per_station,
        "dead_per_panel": per_panel,   # index plane * 6 + panel, out of 96 straws
        "threshold_hist": {"range": [lo, hi], "counts": hist},   # both ends of live straws
        "noisy_straws": sum(noisy),
        "nohv_panels": nohv_panels, "panels_fully_dead": full_panels_dead,
        "threshold_hv": _stats([thr_hv[i] for i in alive]),
        "threshold_cal": _stats([thr_cal[i] for i in alive]),
        "adc_gain": _stats([gain[i] for i in alive]),
        "time_offset_hv": _stats([off_hv[i] for i in alive]),
        "time_offset_cal": _stats([off_cal[i] for i in alive]),
        "panel_delay": _stats(list(dpanel.values())),
        "align_reco_minus_sim": align,
        "proditions": {k: prod[k] for k in SCALARS},
        "response": resp,
        "_dead": dead, "_thr": list(zip(thr_hv, thr_cal)), "_off": list(zip(off_hv, off_cal)),
        "_response_raw": {k: prod.get(k) for k in RESPONSE},
    }


def redigi_checks(ref: Dict, cond: Dict, input_use_status: bool = False) -> Dict:
    """Ways the condition RAISES the hit efficiency w.r.t. the reference (re-digitization invalid).
    Straws without signal in the reference but alive in the condition only matter if the input
    samples were digitized with UseStatus (production digitization does not use it: default
    false in StrawDigisFromStrawGasSteps, not set in Production), otherwise their gas steps
    were kept."""
    revived = [i for i in range(NUSTRAWS) if ref["_dead"][i] and not cond["_dead"][i]]
    lower, lower1, worst, ends = 0, 0, 0., 0
    for i, ((rh, rc), (ch, cc)) in enumerate(zip(ref["_thr"], cond["_thr"])):
        if cond["_dead"][i]:
            continue
        ends += 2
        lower1 += (ch - rh < -1.) + (cc - rc < -1.)
        d = min(ch - rh, cc - rc)
        if d < -1e-6:
            lower += 1
            worst = min(worst, d)
    dt = [c[k] - r[k] for r, c, i in zip(ref["_off"], cond["_off"], range(NUSTRAWS))
          if not cond["_dead"][i] for k in (0, 1)]
    rp, cp = ref["proditions"], cond["proditions"]
    issues = []
    if revived and input_use_status:
        issues.append(f"{len(revived)} straws have signal but none in the reference")
    if lower:
        issues.append(f"{lower} live straws with a lower threshold (worst {worst:.2f} mV; "
                      f"{lower1} of {ends} ends lower by > 1 mV): needs a closure test")
    if cp["strawPhysics.gasGain"] > rp["strawPhysics.gasGain"] * (1 + 1e-6):
        issues.append("higher gas gain")
    if cp["strawElectronics.thresholdAnalogNoise"] < rp["strawElectronics.thresholdAnalogNoise"] * (1 - 1e-6):
        issues.append("lower threshold noise")
    return {"revived_straws": len(revived), "lower_threshold_straws": lower,
            "live_ends": ends, "ends_lower_by_1mV": lower1,
            "worst_threshold_change_mV": worst, "time_offset_change": _stats(dt),
            "ok": not issues, "issues": issues}


# --------------------------------------------------------------------------- driver
def sample_run(study: Study) -> int:
    """Run number of the input samples (from the first file name's sequencer, rrrrrr_ssssssss)."""
    for s in study.samples:
        with open(repo_path(s.files)) as f:
            for line in f:
                m = re.search(r"\.(\d{6})_\d{8}\.", line)
                if m and not line.lstrip().startswith("#"):
                    return int(m.group(1))
    raise RuntimeError("cannot find a run number in the sample file lists; pass --run")


def compare(configs: Sequence[Tuple[str, Config]], run: int, env: Dict[str, str], wd: str,
            input_use_status: bool = False) -> Dict:
    """configs: (label, Config); the first is the reference for the re-digitization checks
    (the conditions the input samples were made with)."""
    cache = os.path.join(wd, "conditions_db")
    out = {"run": run, "configs": {}}
    raw = {}
    for label, cfg in configs:
        tabs = tracker_tables(cfg, run, env, cache)
        prod = proditions(cfg, env, cache)
        raw[label] = summarize(tabs, prod)
        c = cfg.condition
        raw[label]["condition"] = {"name": c.name, "db": f"{c.db_purpose} {c.db_version}",
                                   "text_tables": list(c.text_tables), "fcl": c.fcl,
                                   "settings": [s.name for s in cfg.ordered("reco")]}
    ref = configs[0][0]
    for label, _ in configs:
        d = {k: v for k, v in raw[label].items() if not k.startswith("_")}
        if label != ref:
            d["redigi_vs_" + ref] = redigi_checks(raw[ref], raw[label], input_use_status)
        d["response_raw"] = raw[label]["_response_raw"]
        out["configs"][label] = d
    return out


def _f(x, fmt="{:.3g}"):
    return "-" if x is None else fmt.format(x)


def markdown(res: Dict) -> str:
    labels = list(res["configs"])
    C = res["configs"]
    ref = labels[0]
    L = [f"# Tracker conditions (run {res['run']})", "", "| quantity | " + " | ".join(labels) + " |",
         "|---" * (len(labels) + 1) + "|"]

    def row(name, fn):
        L.append(f"| {name} | " + " | ".join(fn(C[l]) for l in labels) + " |")

    row("DB", lambda c: c["condition"]["db"] + (" + " + ", ".join(os.path.basename(t) for t in c["condition"]["text_tables"])
                                                if c["condition"]["text_tables"] else ""))
    row("straws without signal", lambda c: f"{c['dead_straws']} ({100 * c['dead_fraction']:.1f}%)")
    for r in ("NoHV (panel)", "no preamp / wire / absent", "Disabled"):
        row(f"&nbsp;&nbsp;{r}", lambda c, r=r: str(c["dead_by_reason"].get(r, 0)))
    row("NoHV panels", lambda c: str(len(c["nohv_panels"])))
    row("fully dead panels", lambda c: str(c["panels_fully_dead"]))
    row("stations > 50% dead", lambda c: ", ".join(str(i) for i, n in enumerate(c["dead_per_station"])
                                                   if n > 0.5 * 2 * NPANELS * NSTRAWS) or "none")
    row("noisy straws (live)", lambda c: str(c["noisy_straws"]))
    for k in ("threshold_hv", "threshold_cal"):
        row(f"{k} mean / rms [mV]", lambda c, k=k: f"{c[k]['mean']:.2f} / {c[k]['rms']:.2f}")
    row("ADC gain mean", lambda c: f"{c['adc_gain']['mean']:.4g}")
    row("panel delay mean / rms [ns]", lambda c: f"{c['panel_delay']['mean']:.3f} / {c['panel_delay']['rms']:.3f}")
    for k in ("wire_hv_dV", "wire_hv_dW", "straw_hv_dV"):
        row(f"align reco-sim {k} rms [mm]", lambda c, k=k: _f(c["align_reco_minus_sim"][k].get("rms")))
    for k in SCALARS:
        row(k, lambda c, k=k: f"{c['proditions'][k]:.4g}")
    for k in ("strawResponse.tdCentralRes", "strawResponse.totDriftError"):
        row(f"{k} (n, mean)", lambda c, k=k: f"{c['response'][k]['n']}, {c['response'][k]['mean']:.3g}")
    row(f"redigi valid vs {ref}", lambda c: "(reference)" if f"redigi_vs_{ref}" not in c else
        ("yes" if c[f"redigi_vs_{ref}"]["ok"] else "CHECK: " + "; ".join(c[f"redigi_vs_{ref}"]["issues"])))
    L += ["", "Table sources:", ""]
    for l in labels:
        L.append(f"- {l}: " + ", ".join(f"{t} {s}" for t, s in C[l]["sources"].items()))
    return "\n".join(L) + "\n"


def write(res: Dict, wd: str) -> Tuple[str, str]:
    d = os.path.join(wd, "results")
    os.makedirs(d, exist_ok=True)
    j, m = os.path.join(d, "conditions.json"), os.path.join(d, "conditions.md")
    with open(j, "w") as f:
        json.dump(res, f, indent=1)
    with open(m, "w") as f:
        f.write(markdown(res))
    return j, m
