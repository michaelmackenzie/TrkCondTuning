"""
TEMPLATE: study of a new detector condition (e.g. an upcoming official realistic-conditions
setup). Copy to studies/<name>.py, edit the marked places, check with
``python3 -c "from trkcondtuning.study import load_study; load_study('<name>')"`` and then run the
CLI. See studies/reduced_tracker_2026_10.py for a complete worked example, with the known
answers of that study.

What to change
  1. CONDITION: the DB purpose / version of the new condition. For an official condition that
     is all (no text tables, no fcl). Use text_tables= / fcl= only for unofficial tables or
     ProditionsService overrides (see conditions/reduced_tracker_2026/).
  2. redigi_ok: see the warning below.
  3. NOMINAL: the conditions the input samples were made with.
  4. SAMPLES: keep the fixed file lists in samples/ for comparability with earlier studies, or
     write new name lists (file NAMES, fixed order; header comment with the query used).
  5. PATHS: trigger_paths = only the paths under study (never the whole menu, never tpr_ /
     mpr_ paths); objective_paths = what the trigger exploration maximizes ('a|b' = OR).
  6. CANDIDATES: the settings to try. Filter cuts via knobs for the paths of this study; reuse
     the fragments in fragments/ (an APR finder fragment, response calibration, ...). A
     response calibration is condition-specific: do not reuse
     fragments/response/calib_reduced_tracker_2026.fcl for another condition; replace it with
     the new condition's calibration or leave the straw-response candidates out.

WARNING redigi_ok
  The trigger and Offline are evaluated on RE-DIGITIZED samples (makeSD from the StrawGasSteps
  kept in the input digis). That is valid only if the new condition LOWERS the straw hit
  efficiency with respect to the conditions of the inputs (more dead channels, lower gain/HV,
  higher thresholds, disabled panels). A condition that RAISES it (revived channels, higher
  gain, lower threshold, a better ToT calibration producing more hits) cannot be produced from
  these inputs: set redigi_ok=False (the jobs refuse to run) and make new digi samples.
  The MDC2025au mixes were made with Sim_best v1_3 (use nominal = Sim_best v1_3). If the new
  official condition is a different DB version, make sure it does not recover channels that
  v1_3 had marked dead or noisy, and compare its status tables to v1_3 first.
"""
from __future__ import annotations

from trkcondtuning.knobs import filter_cut, filter_cuts, combine
from trkcondtuning.study import (Condition, Config, ExploreSettings, OfflineSelection, Sample,
                                 Setting, Study)

# 1-2. CONDITION (EDIT: purpose / version of the new official condition)
condition = Condition(
    "new_condition",                 # EDIT: short name (work-directory key)
    db_purpose="Sim_best",           # EDIT
    db_version="v1_X",               # EDIT: official DB version of the new condition
    redigi_ok=True,                  # EDIT: only if the condition lowers hit efficiency (see above)
    description="EDIT",
)
# 3. NOMINAL: conditions the input mixes were made with (MDC2025au_best_v1_3)
nominal = Config("nominal", Condition("nominal", "Sim_best", "v1_3"))
baseline = Config("new_condition", condition)

# 5. PATHS (EDIT: the paths under study)
CPR = [f"cpr_TrkDe_{v}" for v in ("75m70p", "75m70p_D0200")]
APR = [f"apr_TrkDe_{v}" for v in ("75m70p", "75m70p_D0200")]

# 6. CANDIDATES (EDIT): knobs for path cuts, fragments for module settings
nsh10_cpr = filter_cuts("nsh10_cpr", CPR, [("TC", "minNStrawHits", 10),
                                           ("HS", "minNStrawHits", 10),
                                           ("KS", "minNStrawHits", 10)])
nsh10_apr = filter_cuts("nsh10_apr", APR, [("TC", "minNStrawHits", 10),
                                           ("HS", "minNStrawHits", 10),
                                           ("KS", "minNStrawHits", 10)])
cpr_finder = Setting("cpr_finder_minhits7", fcl="fragments/trigger/cpr_finder_minhits7.fcl")
apr_cand3a20 = Setting("apr_cand3a20", fcl="fragments/trigger/apr_cand3a20.fcl")
apr_tgtrep100 = Setting("apr_tgtrep100", fcl="fragments/trigger/apr_tgtrep100.fcl",
                        requires=("apr_cand3a20",))
offline_loose = Setting("offline_helix_loose", fcl="fragments/reco/offline_helix_loose.fcl",
                        scope="reco")

# 4. SAMPLES: the same fixed lists as the reduced-tracker study
SAMPLES = [
    Sample("CeM", "samples/CeM_MDC2025au_1BB.txt", role="signal", nfiles=2, nevents=2000, pdg=11, pmin=75.),
    Sample("CeP", "samples/CeP_MDC2025au_1BB.txt", role="signal", nfiles=2, nevents=2000, pdg=-11, pmin=70.),
    Sample("NoPrimary", "samples/NoPrimary_MDC2025au_1BB.txt", role="background", nfiles=100,
           ngroups=10, duty_factor=0.323),
    Sample("Cosmic", "samples/Cosmic_MDC2025au_1BB.txt", role="cosmic", nfiles=2, pmin=75.),
]

STUDY = Study(
    name="new_condition_study",      # EDIT
    description="EDIT",
    nominal=nominal,
    baseline=baseline,
    references=[],                   # e.g. an earlier recommendation, evaluated for comparison
    samples=SAMPLES,
    trigger_paths=CPR + APR,
    objective_paths=["cpr_TrkDe_75m70p|apr_TrkDe_75m70p_D0200"],
    trigger_candidates=[nsh10_cpr, nsh10_apr, cpr_finder, apr_cand3a20, apr_tgtrep100],
    reco_candidates=[offline_loose],
    offline=OfflineSelection(),
    explore=ExploreSettings(),       # thresholds: min_gain, min_z, rate_factor, cpu_factor, ...
)
