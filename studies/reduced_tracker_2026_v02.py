"""
Reduced-tracker v02 (2026-11): the official reduced-tracker DB version Sim_best v2_0 ("tracker
conditions based on expectations from KPP", R. Bonventre 2026-11-06) with the commissioning gas
gain / threshold noise, plus a straw-response calibration made for it (from Richie,
conditions/reduced_tracker_2026_v02/source_settings_2026-11-06.fcl).

Compared with the first reduced-tracker study (studies/reduced_tracker_2026_10.py, condition
reduced_tracker_2026 = Sim_best v1_5 + Sim_commissioning.txt): same gain / noise / HV, a
different set of dead straws, thresholds and delays, and a new reco straw alignment (see
`tct conditions reduced_tracker_2026_v02 --add reduced_tracker_2026_10`).

Configurations
  - nominal: Sim_best v1_3 (the MDC2025au mixes);
  - reduced_v02 (baseline): v2_0 + gain/noise, default reco and trigger (nominal straw response);
  - reduced_v02_prev: the proposal of reduced_tracker_2026_10 applied unchanged, with the v02
    calibration in place of the v01 one: does the earlier re-tuning carry over?
Candidates: those of reduced_tracker_2026_10 (calibration = the v02 one; the v01 calibration and
tdres20 are not valid here and are left out).

Re-digitization of the MDC2025au mixes (Sim_best v1_3) is valid if v2_0 only lowers the straw
hit efficiency: checked by `tct conditions` (thresholds >= v1_3 on every live straw end, gain /
noise as before; straws dead in v1_3 but live in v2_0 are fine since production digitization
does not use the straw status).
"""
from __future__ import annotations

from trkcondtuning.knobs import filter_cut, filter_cuts
from trkcondtuning.study import (Condition, Config, ExploreSettings, OfflineSelection, Sample,
                                 Setting, Study)

# ----------------------------------------------------------------- paths (as reduced_tracker_2026_10)
CPR_PATHS = [f"cpr_TrkDe_{v}" for v in ("75m70p", "75m70p_D0200", "80m70p", "80m70p_D0200")]
APR_PATHS = [f"apr_TrkDe_{v}" for v in ("75m70p", "75m70p_D0200", "80m70p", "80m70p_D0200")]
TRKDE_PATHS = CPR_PATHS + APR_PATHS
TRIGGER_PATHS = TRKDE_PATHS + ["apr_TrkUe_80m70p"]   # TrkUe for the cosmic report only
OBJECTIVE = ["cpr_TrkDe_75m70p|apr_TrkDe_75m70p_D0200"]
REPORT = ["cpr_TrkDe_75m70p", "apr_TrkDe_75m70p", "apr_TrkDe_75m70p_D0200",
          "cpr_TrkDe_75m70p|apr_TrkDe_75m70p", "cpr_TrkDe_75m70p|apr_TrkDe_75m70p_D0200"]
COSMIC = ["cpr_TrkDe_75m70p", "apr_TrkDe_75m70p", "apr_TrkDe_75m70p_D0200", "apr_TrkUe_80m70p"]
RATE = CPR_PATHS + ["apr_TrkDe_75m70p_D0200", "apr_TrkDe_80m70p_D0200"]

# ----------------------------------------------------------------- conditions
nominal = Config("nominal", Condition("nominal", "Sim_best", "v1_3",
                                      description="conditions of the MDC2025au mixes"))
v02_condition = Condition(
    "reduced_tracker_2026_v02", "Sim_best", "v2_0",
    fcl="conditions/reduced_tracker_2026_v02/conditions.fcl",
    description="Sim_best v2_0 tracker tables (KPP expectations), gas gain 5.53e4, threshold noise 3.5")
baseline = Config("reduced_v02", v02_condition)

# ----------------------------------------------------------------- settings
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
                      description="CPR helix chi2 cuts 5 -> 8 (as APR)")
apr_ks8 = filter_cut("apr_ks8", APR_PATHS, "KS", "minNStrawHits", 8,
                     description="APR KalSeed min hits 10 -> 8 (3x APR background in v01)")

S = {n: Setting(n, fcl=f"fragments/trigger/{n}.fcl", scope="trigger") for n in
     ("cpr_finder_minhits7", "apr_finder_minima", "apr_cand3a20", "apr_alias100", "apr_phiz2")}
S["apr_tgtrep100"] = Setting("apr_tgtrep100", fcl="fragments/trigger/apr_tgtrep100.fcl",
                             scope="trigger", requires=("apr_cand3a20",))
offline_helix_loose = Setting("offline_helix_loose", fcl="fragments/reco/offline_helix_loose.fcl",
                              scope="reco")
calib_v02 = Setting("calib_v02", fcl="fragments/response/calib_reduced_tracker_2026_v02.fcl",
                    scope="both", group="straw_response",
                    description="straw-response calibration for this condition (Richie, 2026-11-06)")

# ----------------------------------------------------------------- references
# the proposal of reduced_tracker_2026_10 (results/reduced_tracker_2026_10/explore.json), v02 calibration
reduced_v02_prev = baseline.with_settings(
    calib_v02, offline_helix_loose, nsh10_cpr, S["cpr_finder_minhits7"], nsh10_apr, S["apr_phiz2"],
    S["apr_finder_minima"], S["apr_cand3a20"], S["apr_tgtrep100"], name="reduced_v02_prev")

# ----------------------------------------------------------------- samples (as reduced_tracker_2026_10)
SAMPLES = [
    Sample("CeM", "samples/CeM_MDC2025au_1BB.txt", role="signal", nfiles=2, nevents=2000,
           pdg=11, pmin=75., description="CeMLeadingLogMix1BB MDC2025au_best_v1_3"),
    Sample("CeP", "samples/CeP_MDC2025au_1BB.txt", role="signal", nfiles=2, nevents=2000,
           pdg=-11, pmin=70., description="CePLeadingLogMix1BB MDC2025au_best_v1_3"),
    Sample("NoPrimary", "samples/NoPrimary_MDC2025au_1BB.txt", role="background", nfiles=100,
           ngroups=10, duty_factor=0.323, description="NoPrimaryMix1BB; the first 100 files"),
    Sample("Cosmic", "samples/Cosmic_MDC2025au_1BB.txt", role="cosmic", nfiles=2, pmin=75.,
           description="CosmicSignalMix1BB files 673, 9134"),
]

STUDY = Study(
    name="reduced_tracker_2026_v02",
    description="reduced tracker v02: Sim_best v2_0 + commissioning gain/noise + v02 straw-response calibration",
    nominal=nominal,
    baseline=baseline,
    references=[reduced_v02_prev],
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
    reco_candidates=[offline_helix_loose, calib_v02],
    offline=OfflineSelection(),
    explore=ExploreSettings(rate_mode="tradeoff", rate_cost_hz=2000.),   # +100 Hz is worth +5% signal
    timing_events=16000,
)
