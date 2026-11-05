"""
Evaluation of all metrics per configuration and the study report.

  evaluate(study, wd, configs)  -> <wd>/results/metrics/<config>.json (every metric available)
  report(study, wd, configs)    -> <wd>/results/report.md + summary.json
  check(study, wd, reference_json, tol=0.0) -> compare summary.json counts with a committed reference

Configuration order in the report: nominal, baseline, references, then the proposed configuration
if <wd>/results/explore.json exists ({"proposed": {"name": ..., "settings": [...]}}).
"""
from __future__ import annotations

import glob
import json
import math
import os
import sys
from typing import Dict, List, Optional, Sequence, Tuple

from .metrics import artlog, cosmic, offline, resolution, stage, timing, trigger
from .study import Study

KEY_REPOS = ("Offline", "Production", "mu2e-trig-config", "EventNtuple")


# --------------------------------------------------------------------------- helpers
def _name(c) -> str:
    return c if isinstance(c, str) else c.name


def _clean(x):
    """JSON-safe copy: NaN / inf -> None, tuples -> lists, numpy scalars -> python."""
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if hasattr(x, "item") and not isinstance(x, (str, bytes)):
        return _clean(x.item())
    return x


def _read_json(path: str) -> Optional[dict]:
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def results_dir(wd: str) -> str:
    return os.path.join(wd, "results")


def proposed_entry(wd: str) -> Optional[dict]:
    d = _read_json(os.path.join(results_dir(wd), "explore.json"))
    p = (d or {}).get("proposed")
    return p if isinstance(p, dict) and p.get("name") else None


def config_names(study: Study, wd: str, configs=None) -> List[str]:
    """Configuration names in report order (see the module docstring)."""
    names = [_name(c) for c in (configs if configs is not None else study.configs())]
    p = proposed_entry(wd)
    if p and p["name"] not in names:
        names.append(p["name"])
    return names


def _has_jobs(wd: str, kind: str, config: str, sample: str) -> bool:
    return bool(artlog.job_dirs(wd, kind, config, sample))


def _unique(seq):
    out = []
    for x in seq:
        if x not in out:
            out.append(x)
    return out


# --------------------------------------------------------------------------- evaluate
def evaluate_config(study: Study, wd: str, config) -> dict:
    """All metrics available for one configuration (a dict; see the keys below)."""
    cname = _name(config)
    res: dict = {"config": cname, "study": study.name, "notes": [],
                 "signal": {}, "background": {}, "offline": {}, "resolution": {}, "stage": {},
                 "cosmic": {}, "timing": {}}
    notes = res["notes"]
    rpaths = study.get_report_paths()
    bpaths = _unique(study.get_rate_paths() + list(study.objective_paths))

    def run(section, sample, fn, *a):
        try:
            res[section][sample.name] = fn(*a)
        except Exception as e:  # keep the other metrics; the failure is recorded
            msg = f"{section} {sample.name}: {type(e).__name__}: {e}"
            notes.append(msg)
            print(f"WARNING [{cname}] {msg}", file=sys.stderr)

    for s in study.samples:
        if s.role == "signal":
            if _has_jobs(wd, "trig", cname, s.name):
                run("signal", s, trigger.signal, wd, cname, s, rpaths)
            else:
                notes.append(f"signal {s.name}: no trig jobs")
            if _has_jobs(wd, "offline", cname, s.name):
                run("offline", s, offline.efficiency, wd, cname, s, study.offline, rpaths)
                run("resolution", s, resolution.summary, wd, cname, s, study.offline)
            else:
                notes.append(f"offline/resolution {s.name}: no offline jobs")
            if _has_jobs(wd, "stage", cname, s.name) and _has_jobs(wd, "offline", cname, s.name):
                ev = offline.per_event(wd, cname, s, study.offline)
                run("stage", s, stage.losses, wd, cname, s, study.objective_paths, ev)
            else:
                notes.append(f"stage {s.name}: no stage and/or offline jobs")
        elif s.role == "background":
            if _has_jobs(wd, "trig", cname, s.name):
                run("background", s, trigger.background, wd, cname, s, bpaths)
            else:
                notes.append(f"background {s.name}: no trig jobs")
            if _has_jobs(wd, "timing", cname, s.name):
                run("timing", s, timing.summary, wd, cname, s, study)
            else:
                notes.append(f"timing {s.name}: no timing jobs")
        elif s.role == "cosmic":
            if _has_jobs(wd, "trig", cname, s.name):
                run("cosmic", s, cosmic.efficiency, wd, cname, s, study.get_cosmic_paths(), s.pmin)
            else:
                notes.append(f"cosmic {s.name}: no trig jobs")
    return _clean(res)


def evaluate(study: Study, wd: str, configs=None) -> dict:
    """Evaluate every metric for the configurations and write <wd>/results/metrics/<config>.json.
    Returns {config name: metrics dict}."""
    out = {}
    d = os.path.join(results_dir(wd), "metrics")
    os.makedirs(d, exist_ok=True)
    for name in config_names(study, wd, configs):
        out[name] = evaluate_config(study, wd, name)
        with open(os.path.join(d, name + ".json"), "w") as f:
            json.dump(out[name], f, indent=1, sort_keys=True)
    return out


# --------------------------------------------------------------------------- formatting
def _lab(expr: str) -> str:
    return expr.replace("|", " OR ")


def _eff(k, n) -> Tuple[Optional[float], Optional[float]]:
    if not n:
        return None, None
    e = k / n
    return e, math.sqrt(max(e * (1 - e), 1. / n) / n)


def _pe(k, n, ref=None) -> str:
    """'72.6 +- 0.8' percent, with ' (xx% of nominal)' when ref = (k_nom, n_nom) is given."""
    e, s = _eff(k, n)
    if e is None:
        return "-"
    txt = f"{100 * e:.1f} ± {100 * s:.1f}"
    if ref:
        e0, _ = _eff(*ref)
        if e0:
            txt += f" ({100 * e / e0:.0f}%)"
    return txt


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def _get(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def _warns(metrics: Dict[str, dict], section: str, sample: str) -> List[str]:
    out = []
    for c, m in metrics.items():
        r = _get(m, section, sample, default={}) or {}
        nf = r.get("n_failed", 0)
        if nf:
            out.append(f"{c}: {nf} failed / missing {section} job(s) not used")
        for w in r.get("warnings", []) or []:
            out.append(f"{c}: {w}")
    return out


# --------------------------------------------------------------------------- report sections
def _sec_takeaway(study, metrics, names, nominal):
    out = ["## 1. Takeaway: Offline reconstruction and trigger efficiency\n"]
    rpaths = study.get_report_paths()
    sel = study.offline
    for s in study.samples_by_role("signal"):
        out.append(f"### {s.name}\n")
        out.append(f"Percent of MC-triggerable events ± binomial error; (x%) = fraction of the nominal "
                   f"configuration. Offline: highest-nactive fit of pdg {s.pdg} with p > {s.pmin:g} MeV/c, "
                   f"matched to the primary; reconstructable = >= {sel.nactive_trig} active hits. Trigger rows: "
                   f"each configuration's own re-digitized events (`trig` jobs); 'of those' and 'AND' use the "
                   f"trigger bits of the Offline-job events.\n")

        def sig(c):
            return _get(metrics[c], "signal", s.name, default={}) or {}

        def off(c):
            return _get(metrics[c], "offline", s.name, default={}) or {}

        def cell(c, k, n, refk, refn, rel=True):
            ref = (refk, refn) if (rel and c != nominal and refn) else None
            return _pe(k, n, ref)

        rows = []
        n0o = off(nominal).get("events", 0)
        for label, key in ((f"Offline track found", "found"),
                           (f"Offline reconstructable (>= {sel.nactive_trig} active hits)", "reco"),
                           (f"Offline loose (>= {sel.nactive_loose} active hits)", "loose"),
                           ("Offline quality (TrkQual-input box cuts)", "quality")):
            rows.append([label] + [cell(c, off(c).get(key, 0), off(c).get("events", 0), off(nominal).get(key, 0), n0o)
                                   if off(c).get("events") else "-" for c in names])
        n0 = sig(nominal).get("events", 0)
        for e in rpaths:
            rows.append([f"trigger {_lab(e)}"] + [
                cell(c, sig(c)["pass"][e], sig(c)["events"], _get(sig(nominal), "pass", e, default=0), n0)
                if e in (sig(c).get("pass") or {}) else "-" for c in names])
        for e in rpaths:
            rows.append([f"{_lab(e)}, of Offline reconstructable"] + [
                cell(c, off(c)["joint"]["reco"][e], off(c)["reco"], _get(off(nominal), "joint", "reco", e, default=0),
                     off(nominal).get("reco", 0))
                if e in (_get(off(c), "joint", "reco", default={}) or {}) else "-" for c in names])
        for e in _unique(list(study.objective_paths) + [x for x in rpaths if "|" in x]):
            rows.append([f"**Offline reconstructable AND {_lab(e)}**"] + [
                cell(c, off(c)["joint"]["reco"][e], off(c)["events"], _get(off(nominal), "joint", "reco", e, default=0), n0o)
                if e in (_get(off(c), "joint", "reco", default={}) or {}) else "-" for c in names])
        rows.append(["events (trigger jobs / Offline jobs)"] + [f"{sig(c).get('events', '-')} / {off(c).get('events', '-')}"
                                                                 for c in names])
        out.append(_table(["quantity"] + names, rows))
        for w in _warns(metrics, "signal", s.name) + _warns(metrics, "offline", s.name):
            out.append(f"- WARNING {w}")
        out.append("")
    return "\n".join(out)


def _sec_background(study, metrics, names, nominal):
    out = ["## 2. Background trigger rates\n"]
    exprs = _unique(study.get_rate_paths() + list(study.objective_paths))
    for s in study.samples_by_role("background"):
        out.append(f"### {s.name}\n")
        out.append(f"Rate = passing microbunches / events x {1e9 / s.microbunch_ns / 1e3:.1f} kHz x duty factor "
                   f"{s.duty_factor:g}; no passes -> upper limit with 3 events (95% CL). Cells: rate [Hz] (events "
                   f"passing); x nominal = ratio of passing events.\n")

        def bk(c):
            return _get(metrics[c], "background", s.name, default={}) or {}

        rows = []
        for e in exprs:
            row = [_lab(e)]
            for c in names:
                b = bk(c)
                if e not in (b.get("pass") or {}):
                    row.append("-")
                    continue
                k = b["pass"][e]
                txt = f"{b['rate_hz'][e]:.1f} Hz ({k})" if k else f"< {b['rate_ul'][e]:.1f} Hz (0)"
                k0 = _get(bk(nominal), "pass", e)
                if c != nominal and k0:
                    txt += f" x{k / k0:.2f}"
                row.append(txt)
            rows.append(row)
        rows.append(["microbunches"] + [str(bk(c).get("events", "-")) for c in names])
        out.append(_table(["path"] + names, rows))
        for w in _warns(metrics, "background", s.name):
            out.append(f"- WARNING {w}")
        out.append("")
    return "\n".join(out)


def _sec_stage(study, metrics, names, nominal):
    out = ["## 3. Where the trigger loses Offline-reconstructable events\n"]
    for s in study.samples_by_role("signal"):
        st = {c: _get(metrics[c], "stage", s.name, default={}) or {} for c in names}
        if not any(st[c].get("paths") for c in names):
            out.append(f"### {s.name}\n\nno stage jobs.\n")
            continue
        out.append(f"### {s.name}\n")
        out.append("Events with an Offline track of the same configuration (reconstructable level); each path "
                   "classified by the last stage reached (stage jobs, debug output). Cells: events (percent).\n")
        paths = _unique([p for c in names for p in (st[c].get("paths") or {})])
        rows = []
        for p in paths:
            for cat in stage.CATEGORIES:
                vals = [(st[c].get("paths") or {}).get(p, {}).get(cat) for c in names]
                if cat != "pass" and not any(vals):
                    continue
                rows.append([f"{p}: {cat}"] + [f"{v} ({100 * v / st[c]['n']:.1f}%)" if v is not None and st[c].get("n") else "-"
                                              for c, v in zip(names, vals)])
        for e in _unique([e for c in names for e in (st[c].get("ors") or {})]):
            rows.append([f"**{_lab(e)}: lost**"] + [
                f"{st[c]['ors'][e]['lost']} ({100 * st[c]['ors'][e]['lost'] / st[c]['n']:.1f}%)"
                if e in (st[c].get("ors") or {}) and st[c].get("n") else "-" for c in names])
        rows.append(["Offline events in the stage log"] + [str(st[c].get("n", "-")) for c in names])
        out.append(_table(["path: stage"] + names, rows))
        for c in names:
            for e, v in (st[c].get("ors") or {}).items():
                if v.get("stages"):
                    out.append(f"- {c}, {_lab(e)} lost, stages (path 1/path 2): " +
                               ", ".join(f"{k} {n}" for k, n in v["stages"].items()))
            for p, v in (st[c].get("paths") or {}).items():
                for cat, dd in (v.get("details") or {}).items():
                    out.append(f"- {c}, {p}, {cat}: " + ", ".join(f"{k} {n}" for k, n in dd.items()))
        out.append("")
    return "\n".join(out)


def _sec_resolution(study, metrics, names, nominal):
    out = ["## 4. Offline momentum resolution at the tracker entrance\n"]
    t = study.offline.resolution_tail
    for s in study.samples_by_role("signal"):
        rs = {c: _get(metrics[c], "resolution", s.name, default={}) or {} for c in names}
        if not any(rs[c].get("all") for c in names):
            out.append(f"### {s.name}\n\nno offline jobs.\n")
            continue
        out.append(f"### {s.name}\n")
        out.append(f"dp = p_fit - p_MC at TT_Front of the CE track; sigma68 = half the 16-84% range [MeV/c]; tail = "
                   f"fraction with |dp| > {t:g} MeV/c. Quality = nactive/nhits > {study.offline.min_active_frac:g}, "
                   f"fitcon > {study.offline.min_fitcon:g}, t0err < {study.offline.max_t0err:g} ns, momerr < "
                   f"{study.offline.max_momerr:g} MeV/c. Cells: sigma68 / tail (tracks).\n")

        def f(x):
            if not x or not x.get("n"):
                return "-"
            err = f" ±{x['sigma68_err']:.2f}" if x.get("sigma68_err") is not None else ""
            return f"{x['sigma68']:.2f}{err} / {100 * x['tail']:.1f}% ({x['n']})"

        rows = [["all"] + [f(rs[c].get("all")) for c in names],
                ["quality"] + [f(rs[c].get("quality")) for c in names],
                ["quality: fraction kept"] + [f"{100 * rs[c]['quality']['kept']:.0f}%" if _get(rs[c], "quality", "kept") is not None
                                              else "-" for c in names]]
        out.append(_table(["selection"] + names, rows))
        regions = _unique([r for c in names for r in (rs[c].get("by_nactive") or {})])
        rows = [[f"N(active) {r}"] + [f(_get(rs[c], "by_nactive", r, "all")) for c in names] for r in regions]
        out.append("By N(active) region, all tracks:\n")
        out.append(_table(["region"] + names, rows))
        rows = [[f"N(active) {r}"] + [
            (f(_get(rs[c], "by_nactive", r, "quality")) + (f" [{100 * _get(rs[c], 'by_nactive', r, 'quality', 'kept'):.0f}% kept]"
                                                          if _get(rs[c], "by_nactive", r, "quality", "kept") is not None else ""))
            for c in names] for r in regions]
        out.append("By N(active) region, quality cuts:\n")
        out.append(_table(["region"] + names, rows))
        for w in _warns(metrics, "resolution", s.name):
            out.append(f"- WARNING {w}")
    return "\n".join(out)


def _sec_cosmic(study, metrics, names, nominal):
    out = ["## 5. Cosmic signal efficiency\n"]
    exprs = study.get_cosmic_paths()
    for s in study.samples_by_role("cosmic"):
        cs = {c: _get(metrics[c], "cosmic", s.name, default={}) or {} for c in names}
        if not any(cs[c].get("categories") for c in names):
            out.append(f"### {s.name}\n\nno cosmic jobs.\n")
            continue
        out.append(f"### {s.name}\n")
        out.append(f"Signal particle p > {s.pmin:g} MeV/c; percent of the category's MC-triggerable events ± binomial "
                   f"error, (x%) = fraction of nominal.\n")

        def cell(c, cat, e):
            r = _get(cs[c], "categories", cat, default={}) or {}
            if e not in (r.get("pass") or {}):
                return "-"
            ref = None
            if c != nominal:
                r0 = _get(cs[nominal], "categories", cat, default={}) or {}
                if r0.get("events"):
                    ref = (r0["pass"].get(e, 0), r0["events"])
            return _pe(r["pass"][e], r["events"], ref)

        rows = [[_lab(e), "all"] + [cell(c, "all", e) for c in names] for e in exprs]
        for e in study.objective_paths:
            for cat in ("electron down", "electron up", "muon down", "muon up"):
                rows.append([_lab(e), cat] + [cell(c, cat, e) for c in names])
        rows.append(["events (all / MC-triggerable)", ""] + [f"{_get(cs[c], 'categories', 'all', 'events', default='-')} / "
                                                           f"{cs[c].get('events', '-')}" for c in names])
        out.append(_table(["path", "category"] + names, rows))
        for w in _warns(metrics, "cosmic", s.name):
            out.append(f"- WARNING {w}")
    return "\n".join(out)


def _sec_timing(study, metrics, names, nominal):
    out = ["## 6. Trigger CPU time\n"]
    for s in study.samples_by_role("background"):
        tm = {c: _get(metrics[c], "timing", s.name, default={}) or {} for c in names}
        if not any(tm[c].get("events") for c in names):
            out.append(f"### {s.name}\n\nno timing jobs.\n")
            continue
        out.append(f"### {s.name}\n")
        out.append("Per-event time summed over the modules of the studied trigger paths, without the data read "
                   "(Prefetch), the re-digitization emulation (makeSD, TriggerableTrigger), art's own modules and "
                   "outputs; first event of the job skipped. Single thread.\n")
        m0 = _get(tm[nominal], "mean_ms")
        rows = []
        for key, lab in (("mean_ms", "mean [ms]"), ("median_ms", "median [ms]"), ("p90_ms", "p90 [ms]"),
                         ("p99_ms", "p99 [ms]"), ("max_ms", "max [ms]")):
            row = [lab]
            for c in names:
                v = tm[c].get(key)
                if v is None:
                    row.append("-")
                elif key == "mean_ms" and c != nominal and m0:
                    row.append(f"{v:.3f} (x{v / m0:.2f})")
                else:
                    row.append(f"{v:.3f}")
            rows.append(row)
        rows.append(["events"] + [str(tm[c].get("events", "-")) for c in names])
        out.append(_table(["quantity"] + names, rows))
        mods = sorted({k for c in names for k in (tm[c].get("modules") or {})},
                      key=lambda k: -max((tm[c].get("modules") or {}).get(k, 0) for c in names))[:8]
        rows = [[m] + [f"{(tm[c].get('modules') or {}).get(m, 0):.3f}" if tm[c].get("events") else "-" for c in names]
                for m in mods]
        out.append("Largest modules, mean per event [ms]:\n")
        out.append(_table(["module"] + names, rows))
        for w in _warns(metrics, "timing", s.name):
            out.append(f"- WARNING {w}")
    return "\n".join(out)


def _provenance(wd: str) -> Tuple[List[dict], List[str]]:
    recs = []
    for f in sorted(glob.glob(os.path.join(wd, "provenance", "*.json"))):
        r = _read_json(f)
        if r:
            recs.append(r)
    mixed = []
    if recs:
        for r in KEY_REPOS:
            hashes = {(x.get("repos", {}).get(r) or {}).get("hash") for x in recs}
            if len(hashes) > 1:
                mixed.append(f"{r} HEAD changed during the study ({len(hashes)} different hashes)")
        if len({x.get("build") for x in recs}) > 1:
            mixed.append("the muse build changed during the study")
    return recs, mixed


def _sec_provenance(study, wd, names):
    out = ["## 7. Provenance and configurations\n"]
    recs, mixed = _provenance(wd)
    if not recs:
        out.append("no provenance records in `<wd>/provenance/`.\n")
    else:
        last = recs[-1]
        out.append(f"{len(recs)} provenance record(s); last: {last.get('time_utc', '?')} on {last.get('host', '?')} "
                   f"(user {last.get('user', '?')}), muse build `{last.get('build', '?')}`.\n")
        rows = []
        repos = last.get("repos", {})
        for r in list(KEY_REPOS) + [k for k in repos if k not in KEY_REPOS and repos[k].get("dirty")]:
            if r in repos:
                v = repos[r]
                rows.append([r, (v.get("hash") or "-")[:10], v.get("branch", "-"), "yes" if v.get("dirty") else "no",
                             v.get("diff", "")])
        t = last.get("tct")
        if t:
            rows.append(["TrkCondTuning", (t.get("hash") or "-")[:10], t.get("branch", "-"), "yes" if t.get("dirty") else "no",
                         t.get("diff", "")])
        out.append(_table(["repository", "HEAD", "branch", "dirty", "diff hash"], rows))
        for m in mixed:
            out.append(f"- WARNING {m}")
        if any(v.get("dirty") for k, v in repos.items() if k in KEY_REPOS):
            out.append("- WARNING a key repository has uncommitted changes: results are reproducible only with the "
                       "same working-tree state (see the diff hash).")
        out.append("")
    sj = _read_json(os.path.join(wd, "study.json")) or study.to_json()
    prop = proposed_entry(wd)
    rows = []
    for c in sj.get("configs", []):
        rows.append([c["name"], c["condition"]["name"] + f" ({c['condition']['db_purpose']} {c['condition']['db_version']})",
                     ", ".join(s["name"] for s in c.get("settings", [])) or "-"])
    if prop and prop["name"] not in [r[0] for r in rows]:
        base = sj["configs"][1]["condition"] if len(sj.get("configs", [])) > 1 else {}
        rows.append([prop["name"], (base.get("name", "?") + " (as baseline)") if base else "?",
                     ", ".join(prop.get("settings", [])) or "-"])
    out.append("Configurations:\n")
    out.append(_table(["configuration", "condition", "settings"], rows))
    out.append(f"Study `{study.name}`: trigger paths {', '.join(study.trigger_paths)}; objective "
               f"{', '.join(_lab(p) for p in study.objective_paths)}.\n")
    return "\n".join(out)


# --------------------------------------------------------------------------- report
def _load_metrics(study, wd, names, refresh) -> Dict[str, dict]:
    out = {}
    for n in names:
        p = os.path.join(results_dir(wd), "metrics", n + ".json")
        m = None if refresh else _read_json(p)
        if m is None:
            m = evaluate(study, wd, [n])[n]
        out[n] = m
    return out


def summary_dict(study: Study, metrics: Dict[str, dict]) -> dict:
    """Counts and derived numbers of the metrics (no timing: not deterministic); what `check` compares."""
    counts = {}
    for c, m in metrics.items():
        d = {k: v for k, v in m.items() if k not in ("timing", "notes")}
        counts[c] = _strip(d)
    return {"study": study.name, "configs": list(metrics), "counts": counts,
            "timing_mean_ms": {c: {s: t.get("mean_ms") for s, t in (m.get("timing") or {}).items()}
                               for c, m in metrics.items()}}


def _strip(x):
    """Drop volatile entries (warnings) and directory lists."""
    if isinstance(x, dict):
        return {k: _strip(v) for k, v in x.items() if k not in ("warnings", "dirs")}
    return x


def report(study: Study, wd: str, configs=None, refresh: bool = False) -> str:
    """Write <wd>/results/report.md and summary.json; returns the markdown. Metrics are read from
    <wd>/results/metrics/<config>.json, evaluated if missing (refresh=True: always re-evaluated)."""
    names = config_names(study, wd, configs)
    metrics = _load_metrics(study, wd, names, refresh)
    nominal = _name(study.nominal)
    if nominal not in metrics:
        nominal = names[0]
    parts = [f"# Study {study.name}: {study.description or 'trigger / Offline re-tuning report'}\n",
             f"Configurations: {', '.join(f'`{n}`' for n in names)}"
             f"{' (last: proposed)' if proposed_entry(wd) else ''}. Nominal reference: `{nominal}`.\n"]
    notes = [f"- `{c}`: {n}" for c, m in metrics.items() for n in m.get("notes", [])]
    if notes:
        parts.append("Notes (missing inputs / errors):\n\n" + "\n".join(notes) + "\n")
    for sec in (_sec_takeaway, _sec_background, _sec_stage, _sec_resolution, _sec_cosmic, _sec_timing):
        parts.append(sec(study, metrics, names, nominal))
    parts.append(_sec_provenance(study, wd, names))
    md = "\n".join(parts)
    rd = results_dir(wd)
    os.makedirs(rd, exist_ok=True)
    with open(os.path.join(rd, "report.md"), "w") as f:
        f.write(md)
    with open(os.path.join(rd, "summary.json"), "w") as f:
        json.dump(_clean(summary_dict(study, metrics)), f, indent=1, sort_keys=True)
    return md


# --------------------------------------------------------------------------- check
def _flatten(x, prefix="") -> Dict[str, float]:
    out = {}
    if isinstance(x, dict):
        for k, v in x.items():
            out.update(_flatten(v, f"{prefix}/{k}"))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            out.update(_flatten(v, f"{prefix}[{i}]"))
    elif isinstance(x, bool):
        out[prefix] = int(x)
    elif isinstance(x, (int, float)):
        out[prefix] = x
    elif x is not None:
        out[prefix] = x
    return out


def check(study: Study, wd: str, reference_json: str, tol: float = 0.0) -> bool:
    """Compare <wd>/results/summary.json (counts) with a committed reference summary. Numbers must
    agree exactly (tol = 0) or within a relative tolerance |a - b| <= tol * max(|a|, |b|); timing is not
    compared. Prints the differences; returns True if there are none."""
    new = _read_json(os.path.join(results_dir(wd), "summary.json"))
    ref = _read_json(reference_json)
    if new is None:
        print(f"check: no summary.json in {results_dir(wd)} (run report first)")
        return False
    if ref is None:
        print(f"check: cannot read reference {reference_json}")
        return False
    a, b = _flatten(new.get("counts", {})), _flatten(ref.get("counts", {}))
    diffs = []
    for k in sorted(set(a) | set(b)):
        if k not in a:
            diffs.append(f"missing in result: {k} (reference {b[k]})")
        elif k not in b:
            diffs.append(f"not in reference: {k} = {a[k]}")
        elif a[k] != b[k]:
            both_num = all(isinstance(v, (int, float)) for v in (a[k], b[k]))
            if both_num and tol > 0 and abs(a[k] - b[k]) <= tol * max(abs(a[k]), abs(b[k])):
                continue
            diffs.append(f"{k}: {a[k]} (reference {b[k]})")
    if diffs:
        print(f"check: {len(diffs)} difference(s) vs {reference_json} (tol {tol:g}):")
        for d in diffs[:200]:
            print("  " + d)
        if len(diffs) > 200:
            print(f"  ... {len(diffs) - 200} more")
        return False
    print(f"check: OK ({len(a)} values compared with {reference_json}, tol {tol:g})")
    return True
