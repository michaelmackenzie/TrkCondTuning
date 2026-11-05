#!/usr/bin/env python3
"""
Tests of the metrics and the report on small fixtures (plain asserts; run: python3 tests/test_metrics.py).

Needs the mu2e python environment (uproot, awkward, numpy; matplotlib for the plot test):
    source <pyevtana>/setup.sh
Committed fixtures (tests/data/metrics): a 100-event CeM trigger job (ana.root + art log), the stage log and
job.dump.fcl of the same events, and a 20-event TimeTracker database. The Offline / resolution tests use
EventNtuples of the original study if they are readable (OLD_NTS; skipped otherwise).
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

# ---- external fixtures (original reduced-tracker study; 2000 CeM events per file, input file 00000003) ----
# optional: directory with the original study's ntuples (tests needing them are skipped if unset)
OLD_NTS = os.environ.get("TCT_TEST_OLD_NTS", "")
OLD_NTS_FILES = {"nominal": "nts.nominal_00000003.root", "reduced": "nts.reduced_tuned_calib_00000003.root"}
# -----------------------------------------------------------------------------------------------------------

DATA = os.path.join(HERE, "data", "metrics")
PATHS = ["cpr_TrkDe_75m70p", "apr_TrkDe_75m70p_D0200", "cpr_TrkDe_75m70p|apr_TrkDe_75m70p_D0200"]


def have_old_nts() -> bool:
    return all(os.access(os.path.join(OLD_NTS, f), os.R_OK) for f in OLD_NTS_FILES.values())


def make_study():
    from trkcondtuning.study import Condition, Config, Sample, Study
    nom = Config("nominal", Condition("nominal", "Sim_best", "v1_3"))
    red = Config("reduced", Condition("reduced", "Sim_best", "v1_5"))
    samples = [Sample("CeM", "x", role="signal", pdg=11, pmin=75.),
               Sample("NoPrimary", "x", role="background", duty_factor=0.323),
               Sample("Cosmic", "x", role="cosmic", pmin=75.)]
    return Study("fixture", nom, red, samples,
                 trigger_paths=["cpr_TrkDe_75m70p", "cpr_TrkDe_75m70p_D0200", "cpr_TrkDe_80m70p", "cpr_TrkDe_80m70p_D0200",
                                "apr_TrkDe_75m70p", "apr_TrkDe_75m70p_D0200", "apr_TrkDe_80m70p", "apr_TrkDe_80m70p_D0200",
                                "apr_TrkUe_80m70p"],
                 objective_paths=["cpr_TrkDe_75m70p|apr_TrkDe_75m70p_D0200"],
                 report_paths=PATHS, cosmic_paths=PATHS, timing_events=20)


def job(wd, kind, config, sample, name="f000", ok=True, files=(), ntuple=None):
    d = os.path.join(wd, "jobs", kind, config, sample, name)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "status.json"), "w") as f:
        json.dump({"exit": 0 if ok else 1, "ok": ok}, f)
    for src, dst in files:
        shutil.copy(os.path.join(DATA, src), os.path.join(d, dst))
    if ntuple:
        os.symlink(ntuple, os.path.join(d, "nts.root"))
    return d


def make_wd(offline=True):
    """A work directory with the fixtures for the nominal and reduced configurations."""
    wd = tempfile.mkdtemp(prefix="tct_test_")
    for cfg in ("nominal", "reduced"):
        for s in ("CeM", "NoPrimary", "Cosmic"):
            job(wd, "trig", cfg, s, files=[("trig/ana.root", "ana.root"), ("trig/job.log", "job.log")])
        job(wd, "trig", cfg, "CeM", "f001", ok=False)   # a failed job must be counted and ignored
        job(wd, "stage", cfg, "CeM", files=[("stage/job.log", "job.log"), ("stage/job.dump.fcl", "job.dump.fcl")])
        job(wd, "timing", cfg, "NoPrimary", "t00", files=[("timing/timing.db", "timing.db"), ("timing/job.dump.fcl", "job.dump.fcl")])
        if offline:
            job(wd, "offline", cfg, "CeM", ntuple=os.path.join(OLD_NTS, OLD_NTS_FILES[cfg]))
    return wd


# ------------------------------------------------------------------------------------------------ tests
def test_artlog():
    from trkcondtuning.metrics import artlog
    c = artlog.path_counts(os.path.join(DATA, "trig", "job.log"))
    assert c["TriggerablePath"] == (100, 100), c["TriggerablePath"]
    assert "cpr_TrkDe_75m70p" in c and c["cpr_TrkDe_75m70p"][0] == 100
    assert artlog.event_summary(os.path.join(DATA, "trig", "job.log")) == (100, 100)
    assert artlog.art_ok(os.path.join(DATA, "trig", "job.log"))


def test_trigger_signal_background():
    from trkcondtuning.metrics import trigger
    from trkcondtuning.study import Sample
    wd = make_wd(offline=False)
    s = Sample("CeM", "x")
    r = trigger.signal(wd, "nominal", s, PATHS)
    assert r["events"] == 100 and r["n_jobs"] == 1 and r["n_failed"] == 1, r
    assert r["pass"]["cpr_TrkDe_75m70p"] == 64 and r["pass"]["apr_TrkDe_75m70p_D0200"] == 76, r["pass"]
    assert r["pass"][PATHS[2]] >= max(r["pass"][PATHS[0]], r["pass"][PATHS[1]])
    assert r["triggerable_report"] == 100 and not r["warnings"], r["warnings"]
    assert r["path_counts"]["cpr_TrkDe_75m70p"]["passed"] == 64      # TrigReport cross-check
    assert r["missing_paths"] == []
    json.dumps(r)
    # background rate: pass / events x 1e9/microbunch_ns x duty factor; 0 passes -> upper limit with 3 events
    b = Sample("NoPrimary", "x", role="background", duty_factor=0.323, microbunch_ns=1695.)
    r = trigger.background(wd, "nominal", b, PATHS + ["apr_TrkUe_80m70p", "no_such_path"])
    k = r["pass"]["cpr_TrkDe_75m70p"]
    assert abs(r["rate_hz"]["cpr_TrkDe_75m70p"] - k / 100 * (1e9 / 1695.) * 0.323) < 1e-9
    assert "no_such_path" in r["missing_paths"] and "no_such_path" not in r["pass"]
    zero = [e for e, n in r["pass"].items() if n == 0]
    for e in zero:
        assert abs(r["rate_ul"][e] - 3. / 100 * (1e9 / 1695.) * 0.323) < 1e-9
    assert trigger.rate_hz(0, 1000, b) == 3. / 1000 * (1e9 / 1695.) * 0.323
    bits = trigger.signal_bits(wd, "nominal", s, PATHS)
    assert len(bits) == 100 and set(next(iter(bits.values()))) == {"cpr_TrkDe_75m70p", "apr_TrkDe_75m70p_D0200"}
    assert sum(v["cpr_TrkDe_75m70p"] for v in bits.values()) == 64
    shutil.rmtree(wd)


def test_paired():
    from trkcondtuning.metrics import paired
    a = {(1, 1, i): {"p": i < 6, "q": False} for i in range(10)}
    b = {(1, 1, i): {"p": 3 <= i < 9, "q": True} for i in range(10)}
    b[(1, 1, 99)] = {"p": True, "q": True}   # not in a: ignored
    r = paired(a, b, "p")
    assert r["n"] == 10 and r["gain"] == 3 and r["loss"] == 3 and r["z"] == 0.0, r
    r = paired(a, b, "p|q")
    assert r["gain"] == 10 - 6 and r["loss"] == 0 and abs(r["z"] - 4 / math.sqrt(4)) < 1e-12, r
    assert paired({}, {}, "p")["z"] == 0.0


def test_cosmic():
    from trkcondtuning.metrics import cosmic
    from trkcondtuning.study import Sample
    wd = make_wd(offline=False)
    r = cosmic.efficiency(wd, "nominal", Sample("Cosmic", "x", role="cosmic"), PATHS, 75.)
    assert r["events"] == 100 and set(r["categories"]) == {"electron down", "electron up", "muon down", "muon up", "all"}
    a = r["categories"]["all"]
    assert a["events"] <= 100 and 0 <= a["pass"][PATHS[0]] <= a["events"]
    # the four categories partition the 'all' events (electrons and muons only)
    assert sum(v["events"] for k, v in r["categories"].items() if k != "all") <= a["events"]
    json.dumps(r)
    shutil.rmtree(wd)


def test_timing():
    from trkcondtuning.metrics import timing
    from trkcondtuning.study import Sample
    wd = make_wd(offline=False)
    study = make_study()
    r = timing.summary(wd, "nominal", Sample("NoPrimary", "x", role="background"), study)
    assert r["events"] == 19 and r["n_jobs"] == 1       # 20 events, the first is skipped
    assert 0 < r["median_ms"] <= r["p90_ms"] <= r["p99_ms"] <= r["max_ms"] and r["mean_ms"] > 0, r
    ex = set(timing.EXCLUDE)
    assert not (ex & set(r["modules"])), "excluded modules in the sum"
    assert abs(sum(r["modules"].values()) - r["mean_ms"]) < 1e-6 * max(1., r["mean_ms"])
    shutil.rmtree(wd)


def test_stage_parse():
    from trkcondtuning.metrics import stage
    dump = open(os.path.join(DATA, "stage", "job.dump.fcl")).read()
    h, k = stage.path_cuts(dump, "cpr_TrkDe_75m70p", 11)
    assert h["minNStrawHits"] == 15 and h["minMomentum"] == 70 and k["minMomentum"] == 75 and k["fitparticle"] == 11
    h, k = stage.path_cuts(dump, "cpr_TrkDe_75m70p", -11)
    assert k["minMomentum"] == 70 and k["fitparticle"] == -11
    ev = stage.parse_log(os.path.join(DATA, "stage", "job.log"), ["cpr_TrkDe_75m70p"])
    assert len(ev) == 100 and (1430, 3, 3) in ev
    assert stage.classify(ev[(1430, 3, 3)]["cpr_TrkDe_75m70p"], h, k)[0] == "pass"
    cats = [stage.classify(r["cpr_TrkDe_75m70p"], h, k)[0] for r in ev.values()]
    assert cats.count("pass") == 64        # = trigger passes of the same events (trig job)
    assert set(cats) <= set(stage.CATEGORIES)


def test_offline_resolution_stage():
    if not have_old_nts():
        print("  (skipped: old EventNtuples not readable)")
        return
    from trkcondtuning.metrics import offline, resolution, stage
    from trkcondtuning.study import OfflineSelection, Sample
    wd = make_wd()
    s = Sample("CeM", "x", pdg=11, pmin=75.)
    sel = OfflineSelection()
    r = offline.efficiency(wd, "nominal", s, sel, PATHS)
    assert r["events"] == 2000
    # original study: CeM file 00000003, Offline found 90.5% nominal / ~73.5% reduced (tuned + calib)
    assert abs(r["found"] / 2000 - 0.905) < 0.001, r["found"]
    assert r["reco"] <= r["found"] and r["quality"] <= r["reco"] and r["loose"] >= r["reco"]
    for k in offline.LEVELS:
        for e in PATHS:
            assert r["joint"][k][e] <= r[k] and r["joint"][k][e] <= r["trig_all"][e]
    assert r["trig_given_reco"] == r["joint"]["reco"]
    json.dumps(r)
    rr = offline.efficiency(wd, "reduced", s, sel, PATHS)
    assert abs(rr["found"] / 2000 - 0.736) < 0.003, rr["found"]
    pe = offline.per_event(wd, "nominal", s, sel)
    assert len(pe) == 2000 and sum(v["reco"] for v in pe.values()) == r["reco"]
    assert all((v["dp"] is None) == (not v["found"]) or v["found"] for v in pe.values())
    # resolution of the one file (the 11-file numbers are in the validation notes of the report)
    res = resolution.summary(wd, "nominal", s, sel)
    assert res["all"]["n"] > 1500 and 0.1 < res["all"]["sigma68"] < 0.5, res["all"]
    assert res["quality"]["sigma68"] < res["all"]["sigma68"] and 0.5 < res["quality"]["kept"] < 0.95
    assert sum(v["all"]["n"] for v in res["by_nactive"].values()) == res["all"]["n"]
    resb = resolution.summary(wd, "nominal", s, sel, bootstrap=20)
    assert resb["all"]["sigma68_err"] > 0 and resb["all"]["sigma68"] == res["all"]["sigma68"]
    # stage losses against the Offline events of the same input file (the stage job reads its first 100 events)
    st = stage.losses(wd, "nominal", s, [PATHS[2]], pe)
    assert st["n"] > 50 and st["n_failed"] == 0 and PATHS[2] in st["ors"]
    p = st["paths"]["cpr_TrkDe_75m70p"]
    assert sum(p[c] for c in stage.CATEGORIES) == st["n"]
    assert st["ors"][PATHS[2]]["pass"] + st["ors"][PATHS[2]]["lost"] == st["n"]
    shutil.rmtree(wd)


def test_plots():
    if not have_old_nts():
        return
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        print("  (skipped: no matplotlib)")
        return
    from trkcondtuning.metrics import resolution
    from trkcondtuning.study import OfflineSelection, Sample
    wd = make_wd()
    out = resolution.plots(wd, ["nominal", "reduced"], Sample("CeM", "x"), OfflineSelection(), os.path.join(wd, "plots"))
    assert out and all(os.path.getsize(f) > 1000 for f in out)
    shutil.rmtree(wd)


def test_report_and_check():
    from trkcondtuning import report
    study = make_study()
    wd = make_wd(offline=have_old_nts())
    m = report.evaluate(study, wd, study.configs()[:2])
    assert set(m) == {"nominal", "reduced"}
    assert os.path.exists(os.path.join(wd, "results", "metrics", "nominal.json"))
    assert m["nominal"]["signal"]["CeM"]["events"] == 100
    assert m["nominal"]["timing"]["NoPrimary"]["events"] == 19
    assert "stage" in m["nominal"]
    md = report.report(study, wd, study.configs()[:2])
    for head in ("## 1.", "## 2.", "## 3.", "## 4.", "## 5.", "## 6.", "## 7."):
        assert head in md, head
    assert "cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200" in md and "64.0 ± " in md
    assert "1 failed / missing signal job(s) not used" in md
    s = json.load(open(os.path.join(wd, "results", "summary.json")))
    assert s["configs"] == ["nominal", "reduced"] and s["counts"]["nominal"]["signal"]["CeM"]["pass"]["cpr_TrkDe_75m70p"] == 64
    ref = os.path.join(wd, "ref.json")
    shutil.copy(os.path.join(wd, "results", "summary.json"), ref)
    assert report.check(study, wd, ref) is True
    s["counts"]["nominal"]["signal"]["CeM"]["pass"]["cpr_TrkDe_75m70p"] = 65
    json.dump(s, open(ref, "w"))
    assert report.check(study, wd, ref) is False
    assert report.check(study, wd, ref, tol=0.02) is True
    # the proposed configuration (explore.json) is appended last
    for s_ in ("CeM", "NoPrimary", "Cosmic"):
        job(wd, "trig", "proposed", s_, files=[("trig/ana.root", "ana.root"), ("trig/job.log", "job.log")])
    json.dump({"proposed": {"name": "proposed", "settings": ["a", "b"]}}, open(os.path.join(wd, "results", "explore.json"), "w"))
    assert report.config_names(study, wd) == ["nominal", "reduced", "proposed"]
    md = report.report(study, wd)
    assert "`proposed`" in md and "a, b" in md
    shutil.rmtree(wd)


def main():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for n, f in tests:
        print(f"{n} ...", flush=True)
        f()
    print(f"all {len(tests)} tests passed")


if __name__ == "__main__":
    main()
