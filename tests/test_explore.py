"""Tests of the exploration and knob logic with mocked jobs / metrics (no mu2e). Run: python3 tests/test_explore.py"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from trkcondtuning import explore as ex  # noqa: E402
from trkcondtuning import knobs  # noqa: E402
from trkcondtuning.study import (Condition, Config, ExploreSettings, Sample, Setting, Study,  # noqa: E402
                                 load_study)

# ------------------------------------------------------------------ knobs


def assignments(text):
    out = set()
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        m = re.match(r"^(\S+)\s*:\s*(.+)$", line)
        if m:
            out.add((m.group(1), m.group(2).strip()))
    return out


def test_filter_label():
    assert knobs.filter_label("cpr_TrkDe_75m70p_D0200") == "CprTrkDe75m70pD0200"
    assert knobs.filter_label("apr_Hlx_50_Hlx_30") == "AprHlx50Hlx30"


def test_knob_structure():
    s = knobs.filter_cut("k", ["apr_TrkUe_80m70p"], "HS", "maxChi2XY", 8)
    a = assignments(s.text)
    assert a == {("physics.filters.AprTrkUe80m70pHSFilter.posHelicitySelection.maxChi2XY", "8"),
                 ("physics.filters.AprTrkUe80m70pHSFilter.negHelicitySelection.maxChi2XY", "8")}
    ks = assignments(knobs.filter_cut("k", ["cpr_TrkDe_75m70p"], "KS", "minNStrawHits", 10).text)
    assert len(ks) == 2 and all("KalSeedCuts[" in k for k, _ in ks)
    m = knobs.module_param("m", "TrigAprHelixFinder", "minAliasGap", 100)
    assert m.text.strip() == "physics.producers.TrigAprHelixFinder.minAliasGap : 100"
    assert knobs.fcl_value(True) == "true" and knobs.fcl_value([1, "a"]) == '[1, "a"]'


def test_combine():
    a = knobs.module_param("a", "M", "x", 1)
    b = knobs.module_param("b", "M", "y", 2, scope="both")
    try:
        knobs.combine("ab", a, b)
        raise AssertionError("mixed scopes must fail")
    except ValueError:
        pass
    c = knobs.combine("ab", a, knobs.module_param("c", "M", "z", 3))
    assert assignments(c.text) == {("physics.producers.M.x", "1"), ("physics.producers.M.z", "3")}


def test_safe_tuning_reproduced():
    """The knobs reproduce helix_tuning_safe.fcl of the original study (order independent)."""
    orig = assignments(open(os.path.join(REPO, "tests", "data", "helix_tuning_safe.fcl")).read())
    cpr = ["cpr_TrkDe_" + v for v in ("75m70p", "75m70p_D0200", "80m70p", "80m70p_D0200")]
    apr = [p.replace("cpr_", "apr_") for p in cpr]
    parts = [knobs.module_param("a", "TrigCalHelixFinderDe", "HelixFinderAlg.minNHit", 7),
             knobs.module_param("b", "TrigCalHelixFinderDe", "HelixFinderAlg.maxNHitsRatio", 3),
             knobs.module_param("c", "TrigCalHelixFinderDe", "minNHitsTimeCluster", 7),
             knobs.filter_cuts("d", cpr + apr, [("TC", "minNStrawHits", 10), ("HS", "minNStrawHits", 10),
                                               ("KS", "minNStrawHits", 10)])]
    gen = assignments(knobs.combine("safe", *parts).text)
    assert gen == orig, (sorted(gen - orig), sorted(orig - gen))


def test_fragments_and_studies_load():
    s = load_study("reduced_tracker_2026_10")
    for c in s.trigger_candidates + s.reco_candidates + [x for c in s.configs() for x in c.settings]:
        assert "#include" not in c.render(), c.name
    names = {c.name for c in s.configs()}
    assert {"nominal", "reduced", "reduced_safe", "reduced_recommended"} <= names
    assert not any(p.startswith(("tpr_", "mpr_")) for p in s.trigger_paths)
    load_study("TEMPLATE_new_condition")

# ------------------------------------------------------------------ explore with mocks


class FakeEnv:
    """Fake world: efficiency / rates / resolution as functions of the set of settings."""
    def __init__(self):
        self.reco_gain = {}      # setting -> list of event ids gained (reco)
        self.res = {}            # setting -> sigma68 multiplier
        self.trig_gain = {}      # setting -> event ids gained (trigger)
        self.bkg = {}            # setting -> extra background events per path
        self.calls = []
        self.N = 1000
        self.cpu = 1.0


def install(env: FakeEnv):
    def names(cfg):
        return {s.name for s in cfg.settings}

    def run_jobs(study, configs, kinds, wd, runner, samples):
        env.calls.append(([c.name for c in configs], list(kinds), [s.name for s in samples]))

    def per_event(wd, cfg, sample, sel):
        got = set()
        for n in names(cfg):
            got |= set(env.reco_gain.get(n, ()))
        return {(1, 0, i): {"reco": (i < 300) or (i in got)} for i in range(env.N)}

    def res(wd, cfg, sample, sel):
        m = 1.0
        for n in names(cfg):
            m *= env.res.get(n, 1.0)
        return {"quality": {"sigma68": 0.3 * m}}

    def bits(wd, cfg, sample, paths):
        plist = Study.all_paths(paths)
        out = {}
        if sample.role == "background":
            extra = sum(env.bkg.get(n, 0) for n in names(cfg))
            for i in range(env.N):
                out[(1, 0, i)] = {p: (i < 10 or i < 10 + extra) for p in plist}
            return out
        got = set()
        for n in names(cfg):
            got |= set(env.trig_gain.get(n, ()))
        return {(1, 0, i): {p: (i < 300 or i in got) for p in plist} for i in range(env.N)}

    def timing(wd, cfg, sample, study):
        return {"mean_ms": env.cpu if cfg.name != study.nominal.name else 1.0}

    ex.run_jobs, ex.offline_per_event, ex.resolution_summary = run_jobs, per_event, res
    ex.trigger_bits, ex.timing_summary = bits, timing


def make_study(cands_trig, cands_reco, **exkw):
    cond = Condition("c", "Sim_best", "v1")
    nominal = Config("nominal", Condition("nominal", "Sim_best", "v0"))
    samples = [Sample("S", "x.txt", role="signal"), Sample("B", "b.txt", role="background")]
    return Study(name="t", nominal=nominal, baseline=Config("base", cond), samples=samples,
                 trigger_paths=["cpr_TrkDe_75m70p", "apr_TrkDe_75m70p"],
                 objective_paths=["cpr_TrkDe_75m70p|apr_TrkDe_75m70p"],
                 trigger_candidates=cands_trig, reco_candidates=cands_reco,
                 explore=ExploreSettings(**exkw))


def T(name, **kw):
    return Setting(name, text=f"physics.producers.{name}.x : 1\n", **kw)


def trig_rounds(r):
    return [x for x in r["rounds"] if x["phase"] == "trigger"]


def reco_rounds(r):
    return [x for x in r["rounds"] if x["phase"] == "reco"]


def run_explore(study, env):
    install(env)
    wd = tempfile.mkdtemp()
    return wd, ex.explore(study, wd, None)


def test_eligibility():
    cond = Condition("c", "d", "v")
    cur = Config("c", cond, (T("a", group="g"),))
    assert ex.eligible(cur, T("b", group="g"), ("trigger",))[0] is False
    assert "requires" in ex.eligible(cur, T("b", requires=("zz",)), ("trigger",))[1]
    assert ex.eligible(cur, T("b", requires=("a",)), ("trigger",))[0]
    assert ex.eligible(cur, T("b", scope="reco"), ("trigger", "both"))[0] is False
    assert ex.eligible(cur, T("a"), ("trigger",))[0] is False


def test_requires_and_acceptance():
    env = FakeEnv()
    env.trig_gain = {"first": range(300, 360), "second": range(360, 400)}  # +6%, +4%
    study = make_study([T("second", requires=("first",)), T("first")], [])
    wd, r = run_explore(study, env)
    acc = [x["accepted"] for x in r["rounds"] if x["phase"] == "trigger"]
    assert acc[:2] == ["first", "second"], acc
    # 'second' was not evaluated in round 1
    r1 = trig_rounds(r)[0]["candidates"]
    assert [c["status"] for c in r1 if c["name"] == "second"] == ["ineligible"]
    assert r["proposed"]["added"] == ["first", "second"]
    assert ex.proposed_config(study, wd).name == "c+first+second"
    assert r["rounds"][-1]["stop_reason"] == "no eligible candidates"


def test_threshold_and_stop():
    env = FakeEnv()
    env.trig_gain = {"tiny": range(300, 303),            # +0.3% < min_gain
                     "big": range(300, 400)}             # +10%
    study = make_study([T("tiny"), T("big")], [])
    wd, r = run_explore(study, env)
    rd = trig_rounds(r)[0]
    d = {c["name"]: c for c in rd["candidates"]}
    assert d["tiny"]["status"] == "fail" and "min_gain" in d["tiny"]["reason"]
    assert rd["accepted"] == "big"
    assert trig_rounds(r)[1]["stop_reason"] in ("no candidate passes", "no eligible candidates")
    assert r["proposed"]["added"] == ["big"]


def test_low_significance():
    env = FakeEnv()
    # large gain but half lost elsewhere is not possible here; use tiny z threshold check
    env.trig_gain = {"a": range(300, 330)}                # +3%, z = sqrt(30) = 5.5
    study = make_study([T("a")], [], min_z=6.0)
    _, r = run_explore(study, env)
    c = trig_rounds(r)[0]["candidates"][0]
    assert c["status"] == "fail" and "min_z" in c["reason"]
    assert r["proposed"]["added"] == []


def test_rate_constraint_rejects_like_ks8():
    env = FakeEnv()
    env.trig_gain = {"ks8": range(300, 340), "ok": range(300, 330)}  # ks8 gains more
    env.bkg = {"ks8": 20}                                            # but triples the background
    study = make_study([T("ks8"), T("ok")], [])
    _, r = run_explore(study, env)
    rd = trig_rounds(r)[0]
    d = {c["name"]: c for c in rd["candidates"]}
    assert d["ks8"]["status"] == "fail" and d["ks8"]["reason"].startswith("rate")
    assert d["ks8"]["background"]["n"]["cpr_TrkDe_75m70p"] == 30
    assert rd["accepted"] == "ok", rd
    assert r["proposed"]["added"] == ["ok"]


def test_exclusive_group_and_reco_resolution():
    env = FakeEnv()
    env.reco_gain = {"tdres": range(300, 380), "calib": range(300, 400), "loose": range(400, 450)}
    env.res = {"loose": 1.5}                                          # resolution worsens by 50%
    study = make_study([], [T("tdres", scope="both", group="resp"), T("calib", scope="both", group="resp"),
                            T("loose", scope="reco")])
    _, r = run_explore(study, env)
    rd = reco_rounds(r)[0]
    d = {c["name"]: c for c in rd["candidates"]}
    assert rd["accepted"] == "calib"
    assert d["loose"]["status"] == "fail" and "sigma68" in d["loose"]["reason"]
    r2 = reco_rounds(r)[1]
    assert any(c["name"] == "tdres" and c["status"] == "ineligible" for c in r2["candidates"])
    assert r["proposed"]["added"] == ["calib"]


def test_max_rounds_and_batch_continuation():
    env = FakeEnv()
    env.trig_gain = {f"s{i}": range(300, 300 + 20 * (i + 1)) for i in range(3)}
    # the cumulative gain is the union, so later rounds add nothing: stop after round 1 + 1
    study = make_study([T(f"s{i}") for i in range(3)], [], max_rounds=1)
    _, r = run_explore(study, env)
    tr = trig_rounds(r)
    assert len(tr) == 1 and tr[0]["stop_reason"] == "max_rounds"
    assert tr[0]["accepted"] == "s2"


def test_one_submission_per_round_and_cpu_flag():
    env = FakeEnv()
    env.trig_gain = {"a": range(300, 360), "b": range(300, 340)}
    env.cpu = 1.5
    study = make_study([T("a"), T("b")], [])
    _, r = run_explore(study, env)
    trig_sig = [c for c in env.calls if c[1] == ["trig"] and c[2] == ["S"]]
    assert set(trig_sig[0][0]) == {"base", "c+a", "c+b"}          # all candidates in one call
    assert r["cpu"]["ratio"] == 1.5 and r["flags"] and "CPU" in r["flags"][0]


def test_explore_json_schema():
    env = FakeEnv()
    env.reco_gain = {"r": range(300, 400)}
    env.trig_gain = {"a": range(300, 360)}
    study = make_study([T("a")], [T("r", scope="reco")])
    wd, r = run_explore(study, env)
    d = json.load(open(os.path.join(wd, "results", "explore.json")))
    assert os.path.exists(os.path.join(wd, "results", "explore.md"))
    assert set(d) == {"study", "phases", "rounds", "proposed", "cpu", "flags"}
    assert set(d["proposed"]) == {"name", "settings", "added", "condition"}
    assert d["phases"] == ["reco", "trigger"]
    for rd in d["rounds"]:
        assert {"phase", "round", "current", "settings", "candidates", "accepted", "stop_reason"} <= set(rd)
        for c in rd["candidates"]:
            assert "name" in c and "status" in c
            if c["status"] != "ineligible":
                assert {"gain", "z", "n_gain", "n_loss"} <= set(c)
    assert d["proposed"]["added"] == ["r", "a"]
    assert ex.proposed_config(study, wd).name == "c+r+a"
    # trigger phase alone keeps the reco-phase settings of the earlier run
    install(env)
    r2 = ex.explore(study, wd, None, phases=("trigger",))
    assert r2["proposed"]["added"] == ["r", "a"]


def test_rate_tradeoff_accepts_rate_for_signal():
    # B: 1000 microbunches, Hz per event = 1/1695 ns x duty / 1000
    env = FakeEnv()
    env.trig_gain = {"big": range(300, 400), "small": range(400, 460)}   # +10%, +6%
    env.bkg = {"big": 5}                                                 # +5 background events
    hz = 1e9 / Sample("B", "b.txt", role="background").microbunch_ns * \
        Sample("B", "b.txt", role="background").duty_factor / env.N
    cost = 30 * hz / 0.02          # 30 events' worth of rate per 2% efficiency
    study = make_study([T("big"), T("small")], [], rate_cost_hz=cost)
    _, r = run_explore(study, env)
    rd = trig_rounds(r)[0]
    d = {c["name"]: c for c in rd["candidates"]}
    assert abs(d["big"]["background"]["delta_hz"] - 5 * hz) < 1e-6 * hz
    assert d["big"]["utility"] > 0.06                    # 0.10 - 5/1500
    assert rd["accepted"] == "big", rd
    # the per-path mode rejects it (15 > 10 + sqrt(10))
    study = make_study([T("big"), T("small")], [], rate_mode="per_path")
    _, r = run_explore(study, env)
    assert trig_rounds(r)[0]["accepted"] == "small"
    # a total-rate ceiling below the candidate's rate rejects it too
    study = make_study([T("big"), T("small")], [], rate_cost_hz=cost, rate_max_hz=12 * hz)
    _, r = run_explore(study, env)
    assert trig_rounds(r)[0]["accepted"] == "small"


if __name__ == "__main__":
    n = 0
    for k, v in sorted(globals().items()):
        if k.startswith("test_") and callable(v):
            v()
            n += 1
            print("ok", k)
    print(f"{n} tests passed")
