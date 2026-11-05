"""
Greedy forward selection of reco and trigger settings (see study.ExploreSettings, PLAN.md).

explore(study, wd, runner, phases=("reco", "trigger")) -> dict, writes <wd>/results/explore.json
and explore.md; proposed_config(study, wd) rebuilds the proposed Config from explore.json.

Reco phase: from the baseline, each round runs the Offline chain ('offline' jobs) of
baseline+candidate for every eligible reco/both-scope candidate on the signal samples. Objective:
fraction of events at the 'reco' level (mean over the signal samples); paired McNemar z (gains
and losses summed over samples); constraint: quality-level sigma68 not worse than the current
configuration's by more than max_res_worsening (relative) in any sample.

Trigger phase: from the reco-phase result, each round runs 'trig' jobs on the signal samples for
all eligible trigger/both-scope candidates at once (one runner submission). Objective: mean over
signal samples and objective_paths expressions of the efficiency. Candidates with gain >= min_gain
and z >= min_z are screened on the background samples, in order of decreasing gain, `shortlist`
at a time (more batches only if the whole batch fails); the best passing candidate is accepted.
Rate constraint, per rate path: N(cand) <= max(N(nominal), N(current)) * rate_factor +
rate_slack_sigma * sqrt(N(nominal)), N summed over the background samples.

Finally the CPU time of nominal and the proposal ('timing' jobs) is compared (cpu_factor).

Everything is recomputed from the (cached) jobs of the runner, so a re-run is cheap and resumes.
The jobs / metrics modules are imported lazily; the thin wrappers below are the points tests
replace.
"""
from __future__ import annotations

import json
import math
import os
from typing import Dict, List, Optional, Sequence, Tuple

from .study import Config, Setting, Study, config_name


# ============================================================ lazy interfaces (mockable)
def run_jobs(study, configs, kinds, wd, runner, samples):
    """jobs.run(study, configs, kinds, wd, runner, samples=Sample list)."""
    from . import jobs
    return jobs.run(study, configs, kinds, wd, runner, samples=samples)


def offline_per_event(wd, config, sample, sel):
    from .metrics import offline
    return offline.per_event(wd, config, sample, sel)


def resolution_summary(wd, config, sample, sel):
    from .metrics import resolution
    return resolution.summary(wd, config, sample, sel)


def trigger_bits(wd, config, sample, paths):
    """{(run, subrun, event): {path: bool}} (signal and background samples)."""
    from .metrics import trigger
    return trigger.signal_bits(wd, config, sample, paths)


def timing_summary(wd, config, sample, study):
    from .metrics import timing
    return timing.summary(wd, config, sample, study)


# ============================================================ helpers
def paired_counts(a: Dict, b: Dict) -> Tuple[int, int, int]:
    """McNemar on common events of {event: bool}: (n, gain = b only, loss = a only)."""
    gain = loss = n = 0
    for k, va in a.items():
        if k not in b:
            continue
        n += 1
        vb = b[k]
        gain += bool(vb) and not va
        loss += bool(va) and not vb
    return n, int(gain), int(loss)


def z_value(gain: int, loss: int) -> float:
    return (gain - loss) / math.sqrt(gain + loss) if gain + loss else 0.0


def eval_expr(ev_bits: Dict, expr: str) -> bool:
    return any(ev_bits[p.strip()] for p in expr.split("|"))


def frac(d: Dict) -> float:
    return sum(1 for v in d.values() if v) / len(d) if d else 0.0


def eligible(current: Config, cand: Setting, scopes: Sequence[str]) -> Tuple[bool, str]:
    """Is the candidate addable to the configuration (scope, not present, requires, group)?"""
    names = {s.name for s in current.settings}
    if cand.scope not in scopes:
        return False, f"scope {cand.scope}"
    if cand.name in names:
        return False, "already applied"
    miss = [r for r in cand.requires if r not in names]
    if miss:
        return False, f"requires {miss}"
    if cand.group and any(s.group == cand.group for s in current.settings):
        return False, f"group {cand.group} occupied"
    return True, ""


def _candidates(study: Study, kind: str, current: Config) -> List[Setting]:
    pool = study.reco_candidates if kind == "reco" else study.trigger_candidates
    scopes = ("reco", "both") if kind == "reco" else ("trigger", "both")
    out = []
    for c in pool:
        if eligible(current, c, scopes)[0] and c.name not in [o.name for o in out]:
            out.append(c)
    return out


def _skipped(study: Study, kind: str, current: Config) -> List[Dict]:
    pool = study.reco_candidates if kind == "reco" else study.trigger_candidates
    scopes = ("reco", "both") if kind == "reco" else ("trigger", "both")
    out = []
    for c in pool:
        ok, why = eligible(current, c, scopes)
        if not ok and why != "already applied":
            out.append({"name": c.name, "status": "ineligible", "reason": why})
    return out


def _signal(study):
    return study.samples_by_role("signal")


def _background(study):
    return study.samples_by_role("background")


# ============================================================ reco phase
def _reco_round(study, wd, runner, current, cands, rnd):
    ex = study.explore
    sel = study.offline
    sigs = _signal(study)
    cfgs = {c.name: current.with_settings(c) for c in cands}
    run_jobs(study, [current] + list(cfgs.values()), ["offline"], wd, runner, sigs)
    cur_pe = {s.name: offline_per_event(wd, current, s, sel) for s in sigs}
    cur_res = {s.name: _sigma68(resolution_summary(wd, current, s, sel)) for s in sigs}
    cur_obj = _mean([frac({k: v["reco"] for k, v in cur_pe[s.name].items()}) for s in sigs])
    records = []
    for c in cands:
        cfg = cfgs[c.name]
        gains = losses = 0
        objs = []
        res_ok, res = True, {}
        for s in sigs:
            pe = offline_per_event(wd, cfg, s, sel)
            a = {k: v["reco"] for k, v in cur_pe[s.name].items()}
            b = {k: v["reco"] for k, v in pe.items()}
            _, g, l = paired_counts(a, b)
            gains += g
            losses += l
            objs.append(frac(b))
            r_new = _sigma68(resolution_summary(wd, cfg, s, sel))
            r_old = cur_res[s.name]
            res[s.name] = {"current": r_old, "candidate": r_new}
            if r_new is not None and r_old is not None and r_new > r_old * (1 + ex.max_res_worsening):
                res_ok = False
        obj = _mean(objs)
        rec = {"name": c.name, "config": cfg.name, "scope": c.scope, "objective": obj,
               "gain": obj - cur_obj, "z": z_value(gains, losses), "n_gain": gains,
               "n_loss": losses, "sigma68_quality": res}
        rec["status"], rec["reason"] = _judge(rec, ex, extra_fail=None if res_ok else
                                              f"quality sigma68 worsens by > {ex.max_res_worsening:.0%}")
        records.append(rec)
    return cur_obj, records


def _sigma68(summary) -> Optional[float]:
    try:
        v = summary["quality"]["sigma68"]
        return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)
    except (KeyError, TypeError):
        return None


def _mean(x: Sequence[float]) -> float:
    return sum(x) / len(x) if x else 0.0


def _judge(rec, ex, extra_fail: Optional[str]) -> Tuple[str, str]:
    if rec["gain"] < ex.min_gain:
        return "fail", f"gain {rec['gain']:+.4f} < min_gain {ex.min_gain}"
    if rec["z"] < ex.min_z:
        return "fail", f"z {rec['z']:.2f} < min_z {ex.min_z}"
    if extra_fail:
        return "fail", extra_fail
    return "pass", ""


# ============================================================ trigger phase
class _BkgCache:
    """Background pass counts (per path, summed over background samples), memoized."""
    def __init__(self, study, wd):
        self.study, self.wd, self.memo = study, wd, {}

    def counts(self, cfg: Config) -> Dict:
        if cfg.name not in self.memo:
            paths = self.study.get_rate_paths()
            plist = Study.all_paths(paths)
            n = {p: 0 for p in plist}
            rate = {p: 0.0 for p in plist}
            events = 0
            for s in _background(self.study):
                bits = trigger_bits(self.wd, cfg, s, plist)
                events += len(bits)
                for p in plist:
                    k = sum(1 for v in bits.values() if v[p])
                    n[p] += k
                    if bits:
                        rate[p] += k / len(bits) * (1e9 / s.microbunch_ns) * s.duty_factor
            self.memo[cfg.name] = {"events": events, "n": n, "rate_hz": rate}
        return self.memo[cfg.name]


def rate_check(ex, n_cand: Dict, n_cur: Dict, n_nom: Dict) -> Tuple[bool, Dict, List[str]]:
    """Per path allowed = max(nom, cur) * rate_factor + slack * sqrt(nom)."""
    allowed, bad = {}, []
    for p, nc in n_cand.items():
        a = max(n_nom.get(p, 0), n_cur.get(p, 0)) * ex.rate_factor + \
            ex.rate_slack_sigma * math.sqrt(n_nom.get(p, 0))
        allowed[p] = a
        if nc > a:
            bad.append(f"{p}: {nc} > {a:.1f} (nom {n_nom.get(p, 0)}, cur {n_cur.get(p, 0)})")
    return not bad, allowed, bad


def _trig_round(study, wd, runner, current, cands, rnd, bkg: _BkgCache, nominal: Config):
    ex = study.explore
    sigs = _signal(study)
    exprs = list(study.objective_paths)
    cfgs = {c.name: current.with_settings(c) for c in cands}
    run_jobs(study, [current] + list(cfgs.values()), ["trig"], wd, runner, sigs)
    cur_bits = {s.name: trigger_bits(wd, current, s, exprs) for s in sigs}

    def pass_dict(bits, e):
        return {k: eval_expr(v, e) for k, v in bits.items()}

    cur_obj = _mean([frac(pass_dict(cur_bits[s.name], e)) for s in sigs for e in exprs])
    records = []
    for c in cands:
        cfg = cfgs[c.name]
        gains = losses = 0
        objs = []
        for s in sigs:
            b = trigger_bits(wd, cfg, s, exprs)
            for e in exprs:
                a_d, b_d = pass_dict(cur_bits[s.name], e), pass_dict(b, e)
                _, g, l = paired_counts(a_d, b_d)
                gains += g
                losses += l
                objs.append(frac(b_d))
        obj = _mean(objs)
        rec = {"name": c.name, "config": cfg.name, "scope": c.scope, "objective": obj,
               "gain": obj - cur_obj, "z": z_value(gains, losses), "n_gain": gains, "n_loss": losses}
        rec["status"], rec["reason"] = _judge(rec, ex, None)
        records.append(rec)

    # background screening of the candidates passing the signal gates, best first
    passing = sorted([r for r in records if r["status"] == "pass"], key=lambda r: -r["gain"])
    accepted = None
    for i in range(0, len(passing), max(1, ex.shortlist)):
        batch = passing[i:i + max(1, ex.shortlist)]
        bcfgs = [cfgs[r["name"]] for r in batch]
        run_jobs(study, [nominal, current] + bcfgs, ["trig"], wd, runner, _background(study))
        n_nom, n_cur = bkg.counts(nominal)["n"], bkg.counts(current)["n"]
        for r in batch:
            bc = bkg.counts(cfgs[r["name"]])
            ok, allowed, bad = rate_check(ex, bc["n"], n_cur, n_nom)
            r["background"] = {"n": bc["n"], "rate_hz": bc["rate_hz"], "n_current": n_cur,
                               "n_nominal": n_nom, "allowed": allowed, "events": bc["events"]}
            if not ok:
                r["status"], r["reason"] = "fail", "rate: " + "; ".join(bad)
        ok_batch = [r for r in batch if r["status"] == "pass"]
        if ok_batch:
            accepted = max(ok_batch, key=lambda r: r["gain"])
            break
    return cur_obj, records, accepted


# ============================================================ driver
def _prior_added(wd: str, study: Study, phase: str) -> List[str]:
    p = os.path.join(wd, "results", "explore.json")
    if not os.path.exists(p):
        return []
    d = json.load(open(p))
    return [r["accepted"] for r in d.get("rounds", []) if r.get("phase") == phase and r.get("accepted")]


def explore(study: Study, wd: str, runner, phases: Sequence[str] = ("reco", "trigger")) -> Dict:
    ex = study.explore
    for ph in phases:
        if ph not in ("reco", "trigger"):
            raise ValueError(f"unknown phase {ph!r}")
    current = study.baseline
    rounds: List[Dict] = []
    flags: List[str] = []

    # phases skipped now keep the settings accepted by an earlier run
    if "reco" not in phases:
        prior = _prior_added(wd, study, "reco")
        if prior:
            current = current.with_settings(*[study.candidate(n) for n in prior])

    for phase in ("reco", "trigger"):
        if phase not in phases:
            continue
        bkg = _BkgCache(study, wd)
        for rnd in range(1, ex.max_rounds + 1):
            cands = _candidates(study, phase, current)
            info = {"phase": phase, "round": rnd, "current": current.name,
                    "settings": [s.name for s in current.settings], "candidates": [],
                    "accepted": None, "stop_reason": None}
            if not cands:
                info["stop_reason"] = "no eligible candidates"
                info["candidates"] = _skipped(study, phase, current)
                rounds.append(info)
                break
            if phase == "reco":
                obj, recs = _reco_round(study, wd, runner, current, cands, rnd)
                acc = max([r for r in recs if r["status"] == "pass"], key=lambda r: r["gain"], default=None)
            else:
                obj, recs, acc = _trig_round(study, wd, runner, current, cands, rnd, bkg, study.nominal)
            info["current_objective"] = obj
            info["candidates"] = recs + _skipped(study, phase, current)
            if acc is None:
                info["stop_reason"] = "no candidate passes"
                rounds.append(info)
                break
            acc["status"] = "accepted"
            for r in recs:
                if r["status"] == "pass":
                    r["reason"] = "passes the gates, not the best / not screened"
            info["accepted"] = acc["name"]
            rounds.append(info)
            current = current.with_settings(study.candidate(acc["name"]))
        else:
            rounds[-1]["stop_reason"] = rounds[-1]["stop_reason"] or "max_rounds"

    added = [s.name for s in current.settings[len(study.baseline.settings):]]
    cpu = _cpu(study, wd, runner, current, flags) if "trigger" in phases or "reco" in phases else {}
    result = {"study": study.name, "phases": list(phases), "rounds": rounds,
              "proposed": {"name": current.name, "settings": [s.name for s in current.settings],
                           "added": added, "condition": current.condition.name},
              "cpu": cpu, "flags": flags}
    _write(wd, result)
    return result


def _cpu(study, wd, runner, proposal: Config, flags: List[str]) -> Dict:
    ex = study.explore
    bk = _background(study)
    if not bk:
        flags.append("no background sample: CPU time not checked")
        return {}
    s = bk[0]
    run_jobs(study, [study.nominal, proposal], ["timing"], wd, runner, [s])
    nom = timing_summary(wd, study.nominal, s, study)
    prop = timing_summary(wd, proposal, s, study)
    ratio = prop["mean_ms"] / nom["mean_ms"] if nom.get("mean_ms") else float("nan")
    cpu = {"sample": s.name, "nominal_mean_ms": nom.get("mean_ms"), "proposal_mean_ms": prop.get("mean_ms"),
           "ratio": ratio, "limit": ex.cpu_factor}
    if not ratio <= ex.cpu_factor:
        flags.append(f"CPU time {ratio:.2f}x nominal exceeds cpu_factor {ex.cpu_factor}")
    return cpu


def proposed_config(study: Study, wd: str) -> Config:
    """The Config proposed by the last explore() (baseline + accepted settings, in order)."""
    d = json.load(open(os.path.join(wd, "results", "explore.json")))
    added = d["proposed"].get("added", [])
    if not added:
        return study.baseline
    return study.baseline.with_settings(*[study.candidate(n) for n in added])


# ============================================================ output
def _write(wd: str, result: Dict) -> None:
    rd = os.path.join(wd, "results")
    os.makedirs(rd, exist_ok=True)
    with open(os.path.join(rd, "explore.json"), "w") as f:
        json.dump(result, f, indent=1, default=str)
    with open(os.path.join(rd, "explore.md"), "w") as f:
        f.write(to_markdown(result))


def to_markdown(r: Dict) -> str:
    L = [f"# Exploration: {r['study']}", "", f"Phases: {', '.join(r['phases'])}.",
         f"Proposed: `{r['proposed']['name']}` (added: {', '.join(r['proposed']['added']) or 'none'})", ""]
    for rd in r["rounds"]:
        L += [f"## {rd['phase']} round {rd['round']} (current `{rd['current']}`"
              + (f", objective {rd['current_objective']:.4f}" if "current_objective" in rd else "") + ")", ""]
        for c in rd["candidates"]:
            if c["status"] == "ineligible":
                L.append(f"- {c['name']}: skipped ({c['reason']})")
                continue
            line = f"- {c['name']}: gain {c['gain']:+.4f}, z {c['z']:.1f} [{c['n_gain']}/{c['n_loss']}] -> {c['status']}"
            if c.get("reason"):
                line += f" ({c['reason']})"
            L.append(line)
        L.append(f"- accepted: {rd['accepted']}" if rd["accepted"] else f"- stop: {rd['stop_reason']}")
        L.append("")
    if r["cpu"]:
        c = r["cpu"]
        L.append(f"CPU: proposal {c['proposal_mean_ms']} ms vs nominal {c['nominal_mean_ms']} ms "
                 f"(x{c['ratio']:.2f}, limit x{c['limit']})")
    for f in r["flags"]:
        L.append(f"FLAG: {f}")
    return "\n".join(L) + "\n"
