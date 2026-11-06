"""
Reduced-tracker study of 2026-10 (the study this package generalizes), redone with the
exploration. Original work, numbers and logs: main/trigger/reduced_tracker/notes.org
(summary at the top; scans in the 2026-10 log). Condition: 31% dead straws, lower gas gain,
higher noise (conditions/reduced_tracker_2026/README.md).

KNOWN ANSWERS of the original (hand-driven) study, to compare a re-run with
(CeM nominal / reduced default / re-tuned; trigger of Offline-reconstructable events):
  - recommendation 2026-10-14 = "reduced_recommended" below: full tuning + calib + cprchi2 +
    new APR finder (cand3a20 + alias100 + phiz2 + tgtrep100), hit ratio 0.4 (the nominal
    value: nothing to change); Offline = offline_helix_loose + calib.
  - zero-cost alternative = "reduced_safe": safe tuning + tdres20 + cprchi2
    (OR of cpr_75m70p and apr_75m70p_D0200 ~90% of Offline-reconstructable CE).
  - Offline CE found: nominal 90.5%, reduced 63.3%, + loose reco 69.0%, + calib 71.5%.
  - CPR eff relative to nominal ~78%, APR_D0200 ~64% (CeM) with the recommendation.
  - Background (nominal 15 / 34 / 24 Hz for cpr / apr / apr_D0200 at 200k microbunches): the
    recommendation is at or below nominal for cpr and apr_D0200; the non-D0200 apr paths are
    ~3-6x nominal; safe tuning is below nominal everywhere.
  - ks8 (APR KalSeed minNStrawHits 8) costs ~3x APR background for +1-3% signal: it must be
    REJECTED by the rate constraint (a test of the exploration).
  - tdres20 and calib are exclusive: calib replaces tdres20 (group 'straw_response').
  - nSH 15 -> 10 on the 8 TrkDe paths and cprchi2 are free (no background cost).
  - The greedy selection builds the APR finder steps one by one: tgtrep100 requires
    cand3a20, so it is only considered after cand3a20 has been accepted.

The MDC2025au mixes were made with Sim_best v1_3; the reduced condition uses Sim_best v1_5
plus the commissioning text table, and only lowers the hit efficiency, so re-digitizing from the
kept StrawGasSteps is valid (redigi_ok).
"""
from __future__ import annotations

from trkcondtuning.knobs import filter_cut, filter_cuts, combine
from trkcondtuning.study import (Condition, Config, ExploreSettings, OfflineSelection, Sample,
                                 Setting, Study)

# ----------------------------------------------------------------- paths
CPR_PATHS = [f"cpr_TrkDe_{v}" for v in ("75m70p", "75m70p_D0200", "80m70p", "80m70p_D0200")]
APR_PATHS = [f"apr_TrkDe_{v}" for v in ("75m70p", "75m70p_D0200", "80m70p", "80m70p_D0200")]
TRKDE_PATHS = CPR_PATHS + APR_PATHS
# apr_TrkUe_80m70p only enters for the cosmic report (user request); never tpr_ / mpr_ paths
TRIGGER_PATHS = TRKDE_PATHS + ["apr_TrkUe_80m70p"]
OBJECTIVE = ["cpr_TrkDe_75m70p|apr_TrkDe_75m70p_D0200"]
REPORT = ["cpr_TrkDe_75m70p", "apr_TrkDe_75m70p", "apr_TrkDe_75m70p_D0200",
          "cpr_TrkDe_75m70p|apr_TrkDe_75m70p", "cpr_TrkDe_75m70p|apr_TrkDe_75m70p_D0200"]
COSMIC = ["cpr_TrkDe_75m70p", "apr_TrkDe_75m70p", "apr_TrkDe_75m70p_D0200", "apr_TrkUe_80m70p"]
# Rate-constrained paths: the paths that would be used. As in the original recommendation, the
# non-D0200 APR TrkDe paths share the APR producers and are allowed to rise (they would not be
# used with the re-tuned APR finder); their rates are still reported.
RATE = CPR_PATHS + ["apr_TrkDe_75m70p_D0200", "apr_TrkDe_80m70p_D0200"]

# ----------------------------------------------------------------- conditions
nominal = Config("nominal", Condition("nominal", "Sim_best", "v1_3",
                                      description="conditions of the MDC2025au mixes"))
reduced_condition = Condition(
    "reduced_tracker_2026", "Sim_best", "v1_5",
    text_tables=("conditions/reduced_tracker_2026/Sim_commissioning.txt",),
    fcl="conditions/reduced_tracker_2026/conditions.fcl",
    description="31% dead straws, gas gain 5.53e4, threshold noise 3.5")
baseline = Config("reduced", reduced_condition)

# ----------------------------------------------------------------- settings
# knobs (path filter cuts)
nsh10_cpr = filter_cuts("nsh10_cpr", CPR_PATHS,
                        [("TC", "minNStrawHits", 10), ("HS", "minNStrawHits", 10),
                         ("KS", "minNStrawHits", 10)],
                        description="min straw hits 15 -> 10 (TC, HS, KS) on the 4 cpr TrkDe paths")
nsh10_apr = filter_cuts("nsh10_apr", APR_PATHS,
                        [("TC", "minNStrawHits", 10), ("HS", "minNStrawHits", 10),
                         ("KS", "minNStrawHits", 10)],
                        description="min straw hits 15 -> 10 (TC, HS, KS) on the 4 apr TrkDe paths")
cprchi2 = filter_cuts("cprchi2", CPR_PATHS,
                      [("HS", "maxChi2XY", 8), ("HS", "maxChi2PhiZ", 8)],
                      description="CPR helix chi2 cuts 5 -> 8 (as APR); free (no background cost)")
apr_ks8 = filter_cut("apr_ks8", APR_PATHS, "KS", "minNStrawHits", 8,
                     description="APR KalSeed min hits 10 -> 8: KNOWN BAD (3x APR background)")

# fragments
S = {n: Setting(n, fcl=f"fragments/trigger/{n}.fcl", scope="trigger") for n in
     ("cpr_finder_minhits7", "apr_finder_minima", "apr_cand3a20", "apr_alias100", "apr_phiz2")}
S["apr_tgtrep100"] = Setting("apr_tgtrep100", fcl="fragments/trigger/apr_tgtrep100.fcl",
                             scope="trigger", requires=("apr_cand3a20",))
offline_helix_loose = Setting("offline_helix_loose", fcl="fragments/reco/offline_helix_loose.fcl",
                              scope="reco")
tdres20 = Setting("tdres20", fcl="fragments/response/tdres20.fcl", scope="both",
                  group="straw_response")
calib = Setting("calib", fcl="fragments/response/calib_reduced_tracker_2026.fcl", scope="both",
                group="straw_response")

# ----------------------------------------------------------------- references
safe = combine("safe", S["cpr_finder_minhits7"], nsh10_cpr, nsh10_apr)
reduced_safe = baseline.with_settings(safe, tdres20, cprchi2, name="reduced_safe")
reduced_recommended = baseline.with_settings(
    S["cpr_finder_minhits7"], nsh10_cpr, nsh10_apr, S["apr_finder_minima"], cprchi2,
    S["apr_cand3a20"], S["apr_alias100"], S["apr_phiz2"], S["apr_tgtrep100"],
    offline_helix_loose, calib, name="reduced_recommended")

# ----------------------------------------------------------------- samples
SAMPLES = [
    Sample("CeM", "samples/CeM_MDC2025au_1BB.txt", role="signal", nfiles=2, nevents=2000,
           pdg=11, pmin=75., description="CeMLeadingLogMix1BB MDC2025au_best_v1_3 (11 files listed; "
           "the 11-file resolution study used all)"),
    Sample("CeP", "samples/CeP_MDC2025au_1BB.txt", role="signal", nfiles=2, nevents=2000,
           pdg=-11, pmin=70., description="CePLeadingLogMix1BB MDC2025au_best_v1_3"),
    Sample("NoPrimary", "samples/NoPrimary_MDC2025au_1BB.txt", role="background", nfiles=100,
           ngroups=10, duty_factor=0.323, description="NoPrimaryMix1BB; the first 100 files "
           "(original: 200k microbunches)"),
    Sample("Cosmic", "samples/Cosmic_MDC2025au_1BB.txt", role="cosmic", nfiles=2, pmin=75.,
           description="CosmicSignalMix1BB files 673, 9134 (16774 MC-triggerable events)"),
]

STUDY = Study(
    name="reduced_tracker_2026_10",
    description="reduced-tracker study of 2026-10 (the study this package generalizes), redone with the exploration",
    nominal=nominal,
    baseline=baseline,
    references=[reduced_safe, reduced_recommended],
    samples=SAMPLES,
    trigger_paths=TRIGGER_PATHS,
    objective_paths=OBJECTIVE,
    rate_paths=RATE,
    report_paths=REPORT,
    cosmic_paths=COSMIC,
    trigger_candidates=[
        nsh10_cpr, nsh10_apr, S["cpr_finder_minhits7"], cprchi2,
        S["apr_finder_minima"], S["apr_cand3a20"], S["apr_alias100"], S["apr_phiz2"],
        S["apr_tgtrep100"], apr_ks8,
    ],
    reco_candidates=[offline_helix_loose, tdres20, calib],
    offline=OfflineSelection(),
    explore=ExploreSettings(rate_mode="tradeoff", rate_cost_hz=2000.),   # +100 Hz is worth +5% signal
    timing_events=16000,
)
