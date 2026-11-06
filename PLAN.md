# TrkCondTuning: design and status

Generalizes the reduced-tracker study of 2026-10 (main/trigger/reduced_tracker, notes.org there)
so that the re-tuning of the Offline reconstruction and the trigger can be repeated for any new
detector condition (e.g. an official realistic-conditions setup) with repeatable results.

## Status (last update 2026-11-06, rate trade-off)
- v1 complete and run end to end on the 2026-10 reduced-tracker condition
  (`studies/reduced_tracker_2026_10.py`): 4 configurations evaluated, exploration, proposal
  evaluated; reference results in `results/reduced_tracker_2026_10/` (report.md, explore.md,
  explore.json, summary.json for `tct check`). Full chain ~4 h on 18 cores of mu2esrv01.
- Closure with the original study (notes.org): CeM nominal found 90.8% (90.5), CPR 72.8% (72.6),
  reduced CPR 37.8% (37.4), recommended OR 71.5% (73.1), CeP recommended OR 50.8% (50.8); the
  re-digitized trigger counts of the nominal CeM jobs are identical to the old redigi log.
- Proposal (greedy; background as a trade-off, rate_cost_hz 2000 Hz per unit efficiency, i.e.
  +100 Hz is worth +5% signal): reco `calib` + `offline_helix_loose`; trigger `nsh10_cpr`,
  `cpr_finder_minhits7`, `nsh10_apr`, `apr_phiz2`, `apr_finder_minima`, `apr_cand3a20`,
  `apr_tgtrep100` = the hand-tuned recommendation without `apr_alias100` and `cprchi2` (each
  < 0.5% gain). CeM objective OR 71.2% (recommended 71.5, reduced 45.8, nominal 85.9), CeP 50.1%
  (50.8); background OR 35.3 Hz (x1.03 of nominal, same as recommended); trigger CPU x1.16 of
  nominal. `apr_cand3a20` gains +1.1% only after `apr_finder_minima` (+0.2% before), so greedy
  reached the prerequisite chain without a hand-made bundle. `apr_ks8` (known bad) is rejected:
  +50 Hz for +0.75%. apr_TrkDe_80m70p_D0200 alone is x4.6 nominal (22 Hz; the open issue of the
  original study), accepted because the total rate is what is constrained.
- First run with the per-path veto (superseded): proposal stopped after `nsh10_apr` at CeM OR 65.6%,
  background x0.28, because apr_TrkDe_80m70p_D0200 (5 nominal events) vetoed the APR settings.

## Known gaps (next steps)
1. **(addressed 2026-11-06: rate_mode "tradeoff", default)** **Rate constraint was per path with few events.** Each rate path must stay below
   max(nominal, current) + 1 sigma; with 0-36 passing events in 200k NoPrimary microbunches a
   path with 5 nominal events vetoes candidates while the total rate is at 28% of nominal. Options:
   a total-rate budget (OR of the rate paths) as the main constraint, per-path checks only as
   warnings, and more NoPrimary statistics (more groups) before trusting rate decisions.
2. **Greedy selection can miss combinations** (here it did not: apr_cand3a20 became worthwhile after
   apr_finder_minima): a setting whose prerequisite gains nothing on its own is never tried (`apr_tgtrep100` needs `apr_cand3a20`, +0.2%). Bundles must be added by hand
   (`knobs.combine`); no pairwise or backward-elimination pass.
3. **Candidates are discrete, hand-written fragments.** `knobs.py` can generate cut variations
   but there is no scan driver over a cut value; the menu of candidates decides what can be found.
4. **No Offline background constraint** in the reco phase (fake tracks / momentum tails on
   background); only signal efficiency and resolution.
5. **Statistics**: 4000 CeM / 4000 CeP triggerable events (±0.8%), min_gain 0.5% is close to the
   error; paired McNemar z protects the gain sign but not the size. 2 cosmic files.
6. **Redigi validity**: only conditions that lower the hit efficiency (Condition.redigi_ok).
7. **Local runner only** (<= 20 cores on the interactive node); no batch (MC-1 / grid) backend.
8. **Timing** is one 16k-event job per configuration on a shared node: noise between runs is
   not measured; treat differences below ~10% as noise.
9. Stage diagnostics cover the objective paths only; calo paths are not in the study.

## What a study does
1. Evaluate every metric for the nominal configuration (conditions the inputs were made
   with), the condition under study with default settings (baseline), and any reference
   configurations.
2. Explore candidate settings: reco phase (Offline), then trigger phase, greedy forward
   selection with paired significance, a signal vs background-rate trade-off and a resolution constraint.
3. Evaluate every metric for the proposed configuration, and write a report
   (nominal / baseline / references / proposed).

Metrics (each per configuration):
- trigger efficiency per path and path OR, of MC-triggerable signal events (CeM, CeP, ...),
  and relative to nominal
- background trigger rate per path (NoPrimary; pass fraction x 1/microbunch x duty factor,
  0 events -> < 3 events at 95% CL)
- Offline: found efficiency (MC-matched CE track), reconstructable (>= nactive_trig active
  hits, p > pmin), quality (TrkQual-input box cuts); trigger efficiency of Offline
  reconstructable events; Offline AND triggered
- where the trigger loses Offline-reconstructable events (stage diagnostics: TC / no helix /
  HS cuts / no fit / KS cuts)
- Offline momentum resolution at TT_Front: sigma68 and tail fraction, all / quality, and by
  N(active) region
- cosmic signal efficiency by e/mu x up/downstream (p > 75 MeV/c)
- trigger CPU time (studied trigger paths only, data read excluded)

## Layout
```
setup.sh                    environment: muse setup of a work area + PYTHONPATH, PATH
bin/tct                     CLI (python3 -m trkcondtuning.cli)
trkcondtuning/
  study.py                  Study / Condition / Setting / Config / Sample (the API; written first)
  env.py                    muse environment capture, provenance (git hashes, build)
  inputs.py                 sample file lists -> paths (mdh), fixed grouping
  fclgen.py                 job fcl generation (self-contained: templates + fragments inlined)
  templates/*.fcl           redigi_core, reco_core (+ mctags), ntuple, stage/timing snippets
  runner.py                 local job queue, core cap (<= 20), caching by fcl hash
  jobs.py                   job specs per kind (trig, offline, stage, timing) + run helpers
  metrics/artlog.py         TrigReport parsing, art status
  metrics/trigger.py        signal efficiency (per-event bits from the AprHelixTruthAna tree),
                            background rates
  metrics/offline.py        Offline efficiencies, trigger-given-Offline (EventNtuple via pyevtana)
  metrics/stage.py          stage-of-loss classification
  metrics/resolution.py     momentum resolution
  metrics/cosmic.py         cosmic efficiency by category
  metrics/timing.py         TimeTracker sqlite parsing
  explore.py                greedy reco + trigger exploration -> proposal
  knobs.py                  generated settings (e.g. a filter cut on a list of paths)
  report.py                 report.md + summary.json
  cli.py
conditions/<name>/          condition tables and fcl fragments
fragments/{trigger,reco,response}/*.fcl   reusable settings
studies/<name>.py           study definitions (STUDY = Study(...))
samples/*.txt               input file-name lists (fixed order)
results/<study>/            committed reference results (summary.json, report.md, explore.json)
tests/                      unit tests of parsing / metrics on small fixtures
```

## Work directory (outside the repo; default $TCT_WORKDIR/<study> or
## /exp/mu2e/data/users/$USER/tct/<study>)
```
<wd>/study.json                          resolved study, rewritten on each command
<wd>/provenance/<UTC timestamp>.json     env + git hashes + muse build per command
<wd>/conditions/<condition>/<table>      copies of the text tables (on MU2E_SEARCH_PATH)
<wd>/jobs/<kind>/<config>/<sample>/<job>/
      job.fcl         self-contained (only #includes of Offline/Production/mu2e-trig-config/EventNtuple)
      job.dump.fcl    fhicl-dump of job.fcl
      inputs.txt      input file paths
      cmd.sh          exact command (re-runnable by hand)
      job.log         mu2e stdout+stderr
      status.json     {"exit": int, "ok": bool, "start": ..., "end": ..., "host": ..., "key": <hash>}
      ana.root / nts.root / timing.db / ...   outputs
<wd>/results/                            metric JSONs per config, explore.json, summary.json, report.md
```
`<job>` is `f<NNN>` (one input file; signal / cosmic) or `g<NN>` (background group). A job is
re-used when status.ok and its key (hash of job.fcl + inputs.txt + command) is unchanged.

### Job kinds
- `trig` (signal, background, cosmic): re-digitize the tracker (makeSD from compressDigiMCs
  StrawGasSteps, UseStatus per condition) with the condition, run only the study's trigger
  paths (`physics.trigger_paths : [ TriggerablePath, <trigger_paths> ]`), no art output; an
  end-path `AprHelixTruthAna` (module label `aprAna`, TFileService `ana.root`, tree
  `aprAna/helices`, branches run/subrun/event/pdg/p/pz/nsh/trig_<path>) gives per-event trigger
  bits and truth. Signal / cosmic keep MC-triggerable events
  (TriggerableLHPath/TwoTrackPath/CaloPath of the Digitize process); background keeps all
  (DigitizePath). Trigger-scope settings only.
- `offline` (signal): redigi (trigger-scope settings; writes dig.art, triggerable events) ->
  Offline reco (Production recoMC OnSpill + StrawDigiMC tags -> makeSD, reco-scope settings;
  mcs.art) -> EventNtuple (from_mcs-mixed, TriggerProcessName Redigitize; nts.root). One job
  directory, three steps (cmd.sh runs them in sequence); art files deleted after success
  unless --keep-art.
- `stage` (signal): trigger job with the TC/HS/KS filters of the objective paths in debug mode
  and per-event ArtReport markers; log parsed by metrics/stage.py against the `offline`
  ntuples of the same config.
- `timing` (background, first timing_events events): trigger job with TimeTracker
  (sqlite timing.db) and the PrefetchDAQData module after makeSD.

Every mu2e command: `mu2e --nthreads 1 --nschedules 1`, env OMP/OPENBLAS/MKL_NUM_THREADS=1.

## Key interfaces (other modules rely on these)
```python
# env.py
def mu2e_env(musework: str | None = None) -> dict          # captured env (cached per process)
def provenance(env: dict) -> dict                          # git hashes / branches / dirty of musework repos, muse build, host, user, repo hash

# runner.py
@dataclass class Job: kind, config, sample, name, dir, cmd: list[str] (or script), inputs, key
class Runner(max_cores=16): submit(jobs) -> runs all not-cached jobs, at most max_cores at once; returns list[JobResult(ok, dir, cached)]
# hard cap: max_cores <= 20 (refuse more)

# jobs.py
def trig_jobs(study, config, sample, wd) -> list[Job]
def offline_jobs(study, config, sample, wd, keep_art=False) -> list[Job]
def stage_jobs(study, config, sample, wd) -> list[Job]
def timing_jobs(study, config, sample, wd) -> list[Job]
def run(study, configs, kinds, wd, runner, samples=None) -> None   # builds + runs, raises on failures
def job_dirs(wd, kind, config_name, sample_name) -> list[str]       # existing job dirs, sorted

# metrics (all return plain dicts, JSON-serializable; per config)
trigger.signal(wd, config, sample, paths) -> {"events": n, "pass": {expr: n}, "events_ids": ...}
trigger.signal_bits(wd, config, sample, paths) -> {(run,subrun,event): {path: bool}}
trigger.background(wd, config, sample, paths) -> {"events": n, "pass": {path: n}, "rate_hz": {...}, "rate_ul": {...}}
trigger.background_bits(...) -> per-event bits (paired comparisons)
offline.efficiency(wd, config, sample, study.offline, paths) -> {"events", "found", "reco", "quality", "trig_all": {expr: n}, "trig_given_reco": {...}, "joint": {...}}
offline.per_event(wd, config, sample, sel) -> {(run,subrun,event): {"found":bool,"reco":bool,"quality":bool,"dp":float|None,"nactive":int}}
stage.losses(wd, config, sample, paths, offline_events) -> {path: {category: n, "details": {...}}}
resolution.summary(wd, config, sample, sel) -> {"all": {"sigma68":..,"tail":..,"n":..}, "quality": {...}, "by_nactive": {...}}
cosmic.efficiency(wd, config, sample, paths, pmin=75) -> {category: {"events": n, "pass": {path: n}}}
timing.summary(wd, config, sample, study) -> {"events": n, "mean_ms":..., "median_ms":..., "p90":..., "p99":..., "modules": {label: ms}}
paired(a_bits, b_bits) -> {"n": n, "gain": g, "loss": l, "z": (g-l)/sqrt(g+l)}   # McNemar

# explore.py
def explore(study, wd, runner, phases=("reco", "trigger")) -> dict   # writes results/explore.json; returns {"proposed": Config-json, "rounds": [...]}
def proposed_config(study, wd) -> Config                              # from results/explore.json

# report.py
def evaluate(study, wd, configs) -> dict   # all metrics for configs -> results/<config>.json
def report(study, wd, configs) -> str      # results/report.md + summary.json
```

## Repeatability
- Inputs: fixed, ordered file-name lists in samples/, fixed events per file and grouping.
- Seeds: SeedService baseSeed from Production (fixed); the same job (same inputs and
  grouping) gives identical results with the same build. Compare configurations only within
  one grouping (paired).
- Provenance: every command records git hashes and dirty state of the musework repos and
  this repo; the report shows them. `tct check` compares a work directory's summary with a
  committed results/<study>/summary.json.
- The shared work area can change mid-run: pin the build (record and verify the Offline hash
  before each stage; refuse to mix results from different builds unless --allow-mixed).

## Limitations carried over
- Re-digitization from the kept StrawGasSteps is only valid when the condition lowers the
  straw hit efficiency (dead channels, lower gain/HV, higher thresholds). A condition that
  raises it needs new digi samples (Condition.redigi_ok = False -> refuse).
- Background is NoPrimary microbunch triggers only (no Offline fake-track rate for the reco
  phase).
- Paired significance for efficiency gains uses per-event bits (McNemar).

## Work log
- 2026-11-06 (evening): second study `studies/reduced_tracker_2026_v02.py` (Sim_best v2_0 + gain/noise,
  v02 straw-response calibration `calib_v02`; reference `reduced_v02_prev` = the v01 proposal with
  the v02 calibration). New `tct conditions` (trkcondtuning/conditions.py): tracker DB tables per
  config for the sample run (dbTool, cached by CID), text-table overrides, ProditionsService values
  (fhicl-get), dead straws by TrackerStatus noSignal logic, thresholds, alignment, response, and
  re-digitization checks vs nominal (lower thresholds -> 'needs a closure test'; straws dead in
  nominal are fine since production digitization ignores status). v2_0 thresholds are an
  independent draw with the nominal mean: closure test (main/trigger/reduced_tracker_v02/notes.org)
  gives redigi/direct ~0.955 for v02 and ~0.962 for v01 (same within errors; nominal 0.996).
  Fix: load_study ignored a study name when a directory of that name existed in the cwd.
  Runner is node-aware: a job starts only while the user's other mu2e processes (other sessions)
  + this runner's running jobs < max_cores, re-checked every 30 s (other sessions started 16-job
  batches next to an 18-core run twice). Use --cores 20: job batches are multiples of 10
  (20 / 30 / 40), so 18 cores needed an extra wave for 20- and 40-job batches.
- 2026-11-06 (later): background as a trade-off, not a per-path veto (user: ~100 Hz is acceptable
  for +5% signal): ExploreSettings.rate_mode "tradeoff" with rate_cost_hz = 2000 Hz per unit
  efficiency, paired total-rate change with 1 sigma allowance, optional rate_max_hz; ranking by
  utility gain - dR / rate_cost_hz. Old behaviour as rate_mode "per_path". Exploration re-run (~2.3 h):
  proposal = hand-tuned recommendation minus apr_alias100 / cprchi2, CeM OR 71.2%, rate x1.03.
  Runner note: batches of 20 jobs on 18 cores leave 2 jobs for a second wave (~+12 min per batch).
- 2026-11-06: full chain finished (run -> explore -> run proposed -> report). Report fixes:
  cached metric JSONs were reused although the jobs of a configuration had changed (a partial
  report during the run left the references without Offline/timing results); now re-evaluated
  when the configuration's job-status fingerprint changes. Cosmic e/mu x up/down categories now
  for the objective expression; timing modules from TimeModule.Path when no fhicl-dump exists;
  release backing chain in the provenance section. Reference results committed.
- 2026-11-05 (later): integration. Pinned release work area (AnalysisMDC2025 v02_03_01 ->
  Offline v13_43_00): the shared main area's mu2e-trig-config had uncommitted edits breaking
  redigi. Fixes: muse env captured from a clean environment (the rootana driver env made mu2e
  segfault), aprAna SelectEvents TriggerablePath (cosmic files contain non-triggerable events),
  'proposed' config in the CLI, rate_paths = cpr + apr D0200 paths. First full run died when
  /exp/mu2e/data quota filled (Offline art files): work dir moved to /scratch/mu2e/users/$USER/tct,
  chain started as a systemd user unit.
- 2026-11-05: design; study.py API written. Implementation split: infrastructure (env,
  inputs, fclgen, runner, jobs, cli), metrics + report, exploration + study content.
