"""fcl generation tests (no mu2e environment needed). Run: python3 tests/test_fclgen.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from trkcondtuning import fclgen
from trkcondtuning.study import Condition, Config, Sample, Setting, Study

TMP = tempfile.mkdtemp(prefix="tct_test_")
table = os.path.join(TMP, "tab.txt")
open(table, "w").write("TABLE TrkStrawStatusLong\n0_0_6, Absent\n")
cfrag = os.path.join(TMP, "cond.fcl")
open(cfrag, "w").write("services.ProditionsService.strawPhysics.gasGain : 5.53e4\n")

nom = Config("nominal", Condition("nominal", "Sim_best", "v1_3"))
red_cond = Condition("red", "Sim_best", "v1_5", text_tables=(table,), fcl=cfrag)
s_late = Setting("late", text="physics.producers.TrigAprHelixFinder.maxSeedLineGap : 600", order=5)
s_early = Setting("early", text="physics.producers.TrigAprHelixFinder.maxSeedLineGap : 300", order=1)
s_reco = Setting("recoonly", text="physics.producers.DeltaFinder.foo : 1", scope="reco")
red = Config("red+late+early", red_cond, (s_late, s_early, s_reco))
paths = ["cpr_TrkDe_75m70p", "apr_TrkDe_75m70p_D0200"]
sig = Sample("cem", "x.txt", "signal", nevents=10)
bkg = Sample("np", "y.txt", "background")
study = Study("t", nom, red, [sig, bkg], paths, ["cpr_TrkDe_75m70p|apr_TrkDe_75m70p_D0200"])


def test_label():
    assert fclgen.filter_label("cpr_TrkDe_75m70p_D0200") == "CprTrkDe75m70pD0200"
    assert fclgen.filter_label("apr_TrkDe_75m70p") == "AprTrkDe75m70p"


def test_self_contained_and_order():
    t = fclgen.trig_fcl(study, red, sig, TMP)
    assert fclgen.check_self_contained(t) == [], fclgen.check_self_contained(t)
    # core -> condition -> settings (order) -> overrides
    i_core = t.index("template redigi_core.fcl")
    i_cond = t.index("condition red")
    i_early = t.index("maxSeedLineGap : 300")
    i_late = t.index("maxSeedLineGap : 600")
    i_over = t.index("job overrides")
    assert i_core < i_cond < i_early < i_late < i_over
    assert "DeltaFinder.foo" not in t          # reco-scope setting not in a trigger job
    assert 'services.DbService.textFile : [ "conditions/red/tab.txt" ]' in t
    assert os.path.exists(os.path.join(TMP, "conditions", "red", "tab.txt"))
    assert "physics.trigger_paths : [ TriggerablePath, cpr_TrkDe_75m70p, apr_TrkDe_75m70p_D0200 ]" in t
    assert "physics.producers.makeSD.UseStatus : true" in t
    assert 'helixSeedTag   : "TrigAprHelixMerger"' in t and 'comboHitTag    : "TrigFlagPH"' in t
    assert "outputs : {}" in t and "AprHelixTruthAna" in t
    assert "DigitizePath" not in t


def test_background_and_modes():
    t = fclgen.trig_fcl(study, nom, bkg, TMP)
    assert 'TriggerNames : [ "DigitizePath" ]' in t
    assert "textFile" not in t
    s = fclgen.trig_fcl(study, nom, sig, TMP, "stage")
    assert "AprHelixTruthAna" not in s
    assert "physics.filters.CprTrkDe75m70pTCFilter.debugLevel : 2" in s
    assert "physics.filters.AprTrkDe75m70pD0200HSFilter.debugLevel : 3" in s
    assert "ArtReport.reportEvery : 1" in s
    m = fclgen.trig_fcl(study, nom, bkg, TMP, "timing")
    assert "timing.db" in m and "TimeTracker" in m


def test_offline_steps():
    r = fclgen.reco_fcl(study, red, TMP)
    assert "DeltaFinder.foo : 1" in r and "maxSeedLineGap" not in r
    assert fclgen.check_self_contained(r) == []
    assert "UseStatus" not in r
    n = fclgen.ntuple_fcl(study, red, TMP)
    assert 'TriggerProcessName : "Redigitize"' in n
    d = fclgen.redigi_fcl(study, red, sig, TMP)
    assert 'outputs.Output.fileName : "dig.art"' in d


def test_condition_textfile_rejected():
    bad = os.path.join(TMP, "bad.fcl")
    open(bad, "w").write('services.DbService.textFile : ["/abs/x.txt"]\n')
    try:
        fclgen.condition_fcl(Condition("b", "Sim_best", "v1", fcl=bad), TMP, True)
    except ValueError:
        return
    raise AssertionError("textFile in a condition fcl must be rejected")


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
            print("ok", k)
