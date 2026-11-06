"""
tct: command-line interface.

  tct run STUDY [--configs C ...] [--kinds trig offline stage timing] [--samples S ...]
                [--cores N] [--workdir WD] [--keep-art] [--dry-run] [--allow-mixed]
  tct status STUDY [--workdir WD]
  tct fcl STUDY --config C --kind K --sample S [--workdir WD]
  tct explore STUDY [--phases reco trigger]      (trkcondtuning.explore)
  tct evaluate STUDY [--configs ...]             (trkcondtuning.report)
  tct report STUDY [--configs ...]               (trkcondtuning.report)
  tct check STUDY --reference summary.json       (trkcondtuning.report)
  tct conditions STUDY [--configs ...] [--add OTHER_STUDY:CONFIG ...] [--run N]
                                                 (trkcondtuning.conditions: tracker tables, gain,
                                                 response; re-digitization validity vs nominal)
STUDY: a study file or a name under studies/.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from typing import List, Optional

from . import env as envmod
from . import fclgen, jobs
from .runner import Runner, read_status
from .study import Config, Study, load_study

ALL_KINDS = list(jobs.KINDS)


def default_workdir(study: Study) -> str:
    base = os.environ.get("TCT_WORKDIR")
    if base:
        return os.path.join(base, study.name)
    user = os.environ.get("USER") or getpass.getuser()
    return f"/exp/mu2e/data/users/{user}/tct/{study.name}"


def _configs(study: Study, names: Optional[List[str]], wd: Optional[str] = None) -> List[Config]:
    """Configurations by name; 'proposed' = the proposal of `tct explore` (results/explore.json)."""
    if not names:
        return study.configs()
    allc = {c.name: c for c in study.configs()}
    out = []
    for n in names:
        if n == "proposed":
            from . import explore
            out.append(explore.proposed_config(study, wd or os.path.abspath(default_workdir(study))))
            continue
        if n not in allc:
            sys.exit(f"unknown config {n}; known: {', '.join(allc)}")
        out.append(allc[n])
    return out


def _prepare(args, study: Study, record: bool = True):
    """Work directory, environment, study.json and a provenance record."""
    wd = os.path.abspath(args.workdir or default_workdir(study))
    os.makedirs(wd, exist_ok=True)
    env = envmod.mu2e_env(workdir=wd)
    try:
        prov, _ = envmod.check_provenance(wd, env, allow_mixed=getattr(args, "allow_mixed", False),
                                          command=" ".join(sys.argv[1:]), record=record)
    except envmod.ProvenanceError as e:
        sys.exit(str(e))
    if record:
        with open(os.path.join(wd, "study.json"), "w") as f:
            json.dump(study.to_json(), f, indent=1)
    print(envmod.format_provenance(prov), flush=True)
    return wd, env


def cmd_run(args) -> None:
    study = load_study(args.study)
    wd, env = _prepare(args, study)
    configs = _configs(study, args.configs, wd)
    kinds = args.kinds or ALL_KINDS
    try:
        runner = Runner(max_cores=args.cores, env=env, dry_run=args.dry_run)
    except ValueError as e:
        sys.exit(f"ERROR: {e}")
    print(f"work directory {wd}", flush=True)
    try:
        jobs.run(study, configs, kinds, wd, runner, samples=args.samples, keep_art=args.keep_art,
                 allow_mixed=args.allow_mixed)
    except (RuntimeError, ValueError, FileNotFoundError) as e:
        sys.exit(f"ERROR: {e}")


def cmd_status(args) -> None:
    study = load_study(args.study)
    wd = os.path.abspath(args.workdir or default_workdir(study))
    print(f"work directory {wd}")
    print(f"{'kind':8s} {'config':44s} {'sample':16s} {'ok':>4s} {'failed':>7s} {'missing':>8s}")
    for kind in ALL_KINDS:
        for c in study.configs():
            for s in study.samples:
                if kind not in jobs.applicable_kinds(s):
                    continue
                try:
                    expected = jobs.build_jobs(study, [c], [kind], wd, [s.name])
                except Exception as e:   # input list not resolvable etc.
                    print(f"{kind:8s} {c.name:44s} {s.name:16s}  cannot build jobs: {e}")
                    continue
                ok = failed = missing = 0
                for j in expected:
                    st = read_status(j.dir)
                    if st is None:
                        missing += 1
                    elif st.get("ok") and st.get("key") == j.key:
                        ok += 1
                    elif st.get("ok"):
                        missing += 1      # stale: key changed
                    else:
                        failed += 1
                print(f"{kind:8s} {c.name:44s} {s.name:16s} {ok:4d} {failed:7d} {missing:8d}")


def cmd_fcl(args) -> None:
    study = load_study(args.study)
    wd = os.path.abspath(args.workdir or default_workdir(study))
    config = _configs(study, [args.config], wd)[0]
    sample = study.sample(args.sample)
    k = args.kind
    if k in ("trig", "stage", "timing"):
        text = fclgen.trig_fcl(study, config, sample, wd, k)
    elif k == "redigi":
        text = fclgen.redigi_fcl(study, config, sample, wd)
    elif k == "reco":
        text = fclgen.reco_fcl(study, config, wd)
    elif k == "ntuple":
        text = fclgen.ntuple_fcl(study, config, wd)
    elif k == "offline":
        text = "\n".join(f"# ######## {n}\n" + t for n, t in
                         (("redigi.fcl", fclgen.redigi_fcl(study, config, sample, wd)),
                          ("reco.fcl", fclgen.reco_fcl(study, config, wd)),
                          ("ntuple.fcl", fclgen.ntuple_fcl(study, config, wd))))
    else:
        sys.exit("kind must be one of trig, stage, timing, offline, redigi, reco, ntuple")
    sys.stdout.write(text)


def _lazy(modname: str):
    import importlib
    try:
        return importlib.import_module(f"trkcondtuning.{modname}")
    except ImportError as e:
        sys.exit(f"trkcondtuning.{modname} is not available: {e}")


def cmd_explore(args) -> None:
    study = load_study(args.study)
    wd, env = _prepare(args, study)
    explore = _lazy("explore")
    runner = Runner(max_cores=args.cores, env=env)
    explore.explore(study, wd, runner, tuple(args.phases))


def cmd_evaluate(args) -> None:
    study = load_study(args.study)
    wd, env = _prepare(args, study)
    report = _lazy("report")
    report.evaluate(study, wd, _configs(study, args.configs, wd))


def cmd_report(args) -> None:
    study = load_study(args.study)
    wd, env = _prepare(args, study)
    report = _lazy("report")
    print(report.report(study, wd, _configs(study, args.configs, wd)))


def cmd_check(args) -> None:
    study = load_study(args.study)
    wd, env = _prepare(args, study, record=False)
    report = _lazy("report")
    res = report.check(study, wd, args.reference)
    print(res)


def cmd_conditions(args) -> None:
    from . import conditions
    study = load_study(args.study)
    wd = os.path.abspath(args.workdir or default_workdir(study))
    os.makedirs(wd, exist_ok=True)
    env = envmod.mu2e_env(workdir=wd)
    cfgs = [(c.name, c) for c in _configs(study, args.configs, wd)]
    if cfgs[0][1] is not study.nominal:
        cfgs.insert(0, (study.nominal.name, study.nominal))   # reference for the redigi checks
    for spec in args.add or []:
        other, _, name = spec.partition(":")
        ostudy = load_study(other)
        c = {x.name: x for x in ostudy.configs()}.get(name or ostudy.baseline.name)
        if c is None:
            sys.exit(f"unknown config {name} in {other}")
        cfgs.append((f"{ostudy.name}:{c.name}", c))
    run = args.run or conditions.sample_run(study)
    res = conditions.compare(cfgs, run, env, wd, input_use_status=args.input_use_status)
    j, m = conditions.write(res, wd)
    print(open(m).read())
    print(f"written: {j}\n         {m}")


def main(argv: Optional[List[str]] = None) -> None:
    ap = argparse.ArgumentParser(prog="tct", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, configs=False):
        p.add_argument("study")
        p.add_argument("--workdir", help="work directory (default $TCT_WORKDIR/<study> or /exp/mu2e/data/users/$USER/tct/<study>)")
        p.add_argument("--allow-mixed", action="store_true",
                       help="continue although Offline / mu2e-trig-config / the build changed since the last command")
        if configs:
            p.add_argument("--configs", nargs="+", help="configuration names (default: study.configs())")

    p = sub.add_parser("run", help="build and run jobs")
    common(p, True)
    p.add_argument("--kinds", nargs="+", choices=ALL_KINDS, help="job kinds (default: all applicable)")
    p.add_argument("--samples", nargs="+")
    p.add_argument("--cores", type=int, default=16, help="max cores at once (default 16; hard limit 20)")
    p.add_argument("--keep-art", action="store_true", help="keep dig.art / mcs.art of offline jobs")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("status", help="job counts per kind / config / sample")
    common(p)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("fcl", help="print a generated fcl")
    common(p)
    p.add_argument("--config", required=True)
    p.add_argument("--kind", required=True, help="trig, stage, timing, offline (all three steps), redigi, reco, ntuple")
    p.add_argument("--sample", required=True)
    p.set_defaults(func=cmd_fcl)

    p = sub.add_parser("explore", help="greedy reco + trigger exploration (explore.py)")
    common(p)
    p.add_argument("--phases", nargs="+", default=["reco", "trigger"], choices=["reco", "trigger"])
    p.add_argument("--cores", type=int, default=16)
    p.set_defaults(func=cmd_explore)

    p = sub.add_parser("evaluate", help="compute all metrics (report.evaluate)")
    common(p, True)
    p.set_defaults(func=cmd_evaluate)

    p = sub.add_parser("report", help="write report.md + summary.json (report.report)")
    common(p, True)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("check", help="compare the work directory's summary with a reference summary.json")
    common(p)
    p.add_argument("--reference", required=True)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("conditions", help="compare the tracker conditions of the configurations "
                       "(DB tables, gain/noise, straw response) and check re-digitization validity")
    common(p, True)
    p.add_argument("--add", nargs="+", metavar="STUDY:CONFIG",
                   help="configurations of other studies to compare with (CONFIG default: baseline)")
    p.add_argument("--run", type=int, help="run for the DB IOVs (default: from the sample file names)")
    p.add_argument("--input-use-status", action="store_true",
                   help="the inputs were digitized with UseStatus (production: no)")
    p.set_defaults(func=cmd_conditions)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
