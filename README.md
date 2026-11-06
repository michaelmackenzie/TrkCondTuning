# TrkCondTuning

Re-tune the Mu2e Offline reconstruction and trigger for a new detector condition (dead
channels, gas gain, thresholds, a new straw-response calibration, ...), with repeatable
results:

1. evaluate every metric for the **nominal** configuration (the conditions the input samples
   were made with), the new condition with default settings (**baseline**) and any
   **reference** configurations;
2. **explore** candidate reco and trigger settings (greedy forward selection: paired per-event
   gains, background-rate and resolution constraints) and **propose** a configuration;
3. evaluate the proposal and write a **report** (markdown + JSON) comparing all of them.

It generalizes the 2026-10 reduced-tracker study (`main/trigger/reduced_tracker`, notes.org);
`studies/reduced_tracker_2026_10.py` reproduces it; its reference results are in
[results/reduced_tracker_2026_10/](results/reduced_tracker_2026_10/report.md). Design, status and
known gaps: [PLAN.md](PLAN.md).

## Setup

TrkCondTuning needs a muse work area for the mu2e jobs. Pin it to a release (recommended:
a shared development area can change under a run of several hours, and the provenance check
then stops the run):

```bash
mkdir -p <somewhere>/tct_musework && cd <somewhere>/tct_musework
source /cvmfs/mu2e.opensciencegrid.org/setupmu2e-art.sh
muse backing AnalysisMDC2025 v02_03_01     # Offline + Production + mu2e-trig-config + EventNtuple
export TCT_MUSEWORK=$PWD
source /path/to/TrkCondTuning/setup.sh      # python analysis env (pyenv rootana) + tct on PATH
```

A local work area with your own Offline / mu2e-trig-config branches works too (clone this
repository into it, or point `TCT_MUSEWORK` at it). The jobs get the muse environment of
`$TCT_MUSEWORK`, captured in a subshell. The driver itself runs in the `pyenv rootana`
python environment (uproot, awkward, matplotlib), which conflicts with `muse setup`, so don't
set up muse in the same shell.

Required code: Offline with the status-aware HelixTool hit ratio, the AgnosticHelixFinder
candidate options and `Analyses/AprHelixTruthAna` (Offline v13_43_00 or later).

## Usage

```bash
tct run      reduced_tracker_2026_10 --cores 18     # nominal, baseline, references: all job kinds
tct explore  reduced_tracker_2026_10 --cores 18     # reco then trigger exploration -> proposal
tct run      reduced_tracker_2026_10 --configs proposed --cores 18
tct report   reduced_tracker_2026_10                # results/report.md, summary.json
tct status   reduced_tracker_2026_10
tct fcl      reduced_tracker_2026_10 --config reduced --kind trig --sample CeM   # inspect a job fcl
tct check    reduced_tracker_2026_10 --reference results/reduced_tracker_2026_10/summary.json
```

The work directory (default `$TCT_WORKDIR/<study>`, else `/exp/mu2e/data/users/$USER/tct/<study>`)
holds one directory per job with a self-contained `job.fcl`, `cmd.sh` (re-runnable by
hand), the log and the outputs. Jobs are cached by the hash of their fcl, inputs and command,
so re-running a command only runs what changed. `--cores` is capped at 20 (shared node);
every mu2e process is single-threaded.

**Long runs:** a full study takes hours. Start it outside your login/IDE session, which can
be torn down with every process in it, e.g. as a systemd user unit:
`systemd-run --user --collect --unit=tct bash -c "source .../setup.sh; tct run ... > log 2>&1"`.
Put the work directory on a disk with room (`export TCT_WORKDIR=...`): each Offline job writes
~2 GB of temporary art files (deleted after the ntuple), so with 16-18 parallel jobs it needs
~40 GB. On mu2esrv01, the local `/scratch/mu2e/users/$USER` is a good choice; a full
`/exp/mu2e/data` quota makes every job fail at once.

Commit the final `results/report.md`, `summary.json` and `explore.json` of a study to
`results/<study>/` as the reference for later re-runs (`tct check`).

## A new condition

Copy `studies/TEMPLATE_new_condition.py` and change:
- the `Condition`: DB purpose/version, text tables (copied into `conditions/<name>/`) and an
  fcl fragment with any ProditionsService overrides;
- the nominal `Condition`: the DB version the input samples were made with;
- the samples (file-name lists in `samples/`, fixed order), trigger paths, objective / rate /
  report paths;
- the candidate settings: fcl fragments in `fragments/` or generated knobs
  (`trkcondtuning/knobs.py`: e.g. a filter cut on a list of paths). A straw-response
  calibration made for the condition should be a `scope="both"` candidate (trigger and
  Offline).

**Validity of the re-digitization:** the tracker digis are remade from the StrawGasSteps that
`compressDigiMCs` kept, i.e. only the steps that made a digi in the original production. This
is valid when the new condition only *lowers* the straw hit efficiency (dead channels, lower
gain or HV, higher thresholds) with respect to the input's conditions. A condition that raises
it needs new digi samples: set `Condition(redigi_ok=False)` and `tct` refuses.

## Metrics

Per configuration and sample: trigger efficiency per path / OR of MC-triggerable signal
events; background rates (NoPrimary pass fraction x 1/microbunch x duty factor); Offline found /
reconstructable / quality efficiency and trigger efficiency of Offline-reconstructable events;
where the trigger loses them (time cluster, helix, fit, cuts); Offline momentum resolution
(sigma68, tails, by N(active)); cosmic efficiency by e/mu and direction; trigger CPU time of the
studied paths. See PLAN.md for the definitions.

## Exploration

Greedy forward selection (`trkcondtuning/explore.py`, parameters in `ExploreSettings`):
- **reco phase**: add the reco (or reco+trigger) candidate that most increases the Offline
  reconstructable efficiency, with a paired (McNemar, same events) significance cut and a
  resolution constraint;
- **trigger phase**: add the trigger candidate that most increases the objective-path
  efficiency, trading signal against background: the total background rate (OR of the rate
  paths, same microbunches) may rise by up to `gain x rate_cost_hz` (default 2000 Hz: +100 Hz
  is worth +5% signal; +1 sigma allowance), optionally capped at `rate_max_hz`; the passing
  candidate with the largest `gain - dRate / rate_cost_hz` is accepted. Per-path rates are
  reported. `rate_mode="per_path"` restores the strict check (every rate path at or below
  max(nominal, current) plus 1 sigma);
- the proposal's trigger CPU time is compared with nominal.

Limitations: a candidate whose prerequisite shows no gain on its own is never tried (bundle
them with `knobs.combine`); the reco phase has no background (fake-track) constraint;
efficiencies of samples with few events have large errors, so check `min_gain` / `min_z`.
