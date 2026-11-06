"""
Trigger CPU time per event from the art TimeTracker sqlite database (timing.db of the `timing`
jobs).

TimeTracker schema (art): TimeEvent(Run, SubRun, Event, Time) total per event; TimeModule(Run,
SubRun, Event, Path, ModuleLabel, ModuleType, Time) per module and event (Time in seconds; a
module shared by several paths is recorded once per event, under the path that ran it first);
TimeSource(Run, SubRun, Event, Source, Time) input reading.

Per-event time = the sum over the modules of the studied trigger paths (the module sequences
physics.<path> of job.dump.fcl if present, else the
TimeModule.Path column), without the data read (Prefetch), the re-digitization emulation
(makeSD, TriggerableTrigger), art's own modules (TriggerResults, path/end-path bookkeeping), outputs
and the analyzer. The first event of each job (initialization, conditions) is skipped.
"""
from __future__ import annotations

import os
import re
import sqlite3
from typing import Dict, Iterable, List, Optional, Sequence, Set

import numpy as np

from . import artlog
from .stage import block

EXCLUDE = {"makeSD", "Prefetch", "TriggerableTrigger", "TriggerResults", "aprAna", "Output",
           "LoopHelixOutput"}


def path_modules(dump: str, paths: Sequence[str]) -> Set[str]:
    """Module labels of the sequences physics.<path> in a fhicl-dump (all paths given)."""
    mods: Set[str] = set()
    for p in paths:
        b = block(dump, p)
        if b is None:
            continue
        mods.update(re.findall(r'"([^"]+)"', b))
    return mods


def db_path_modules(db: str, paths: Sequence[str]) -> Set[str]:
    """Module labels the TimeTracker recorded under the given paths (TimeModule.Path). A module
    shared with another path counts under the path that ran it first."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        q = "SELECT DISTINCT ModuleLabel FROM TimeModule WHERE Path IN (%s)" % ",".join("?" * len(paths))
        return {r[0] for r in con.execute(q, list(paths))}
    finally:
        con.close()


def event_times(db: str, modules: Optional[Iterable[str]], exclude: Iterable[str] = EXCLUDE,
                skip_first: int = 1):
    """(per-event times [s] (array), {module: summed time [s]}, n events) of one timing.db.
    modules=None: every module except the excluded ones and the '[art]' pseudo-path."""
    ex = set(exclude)
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        events = [tuple(r) for r in con.execute("SELECT Run, SubRun, Event FROM TimeEvent ORDER BY rowid")]
        tot: Dict[tuple, float] = {e: 0.0 for e in events}
        mod: Dict[str, float] = {}
        keep = set(events[skip_first:])
        for run, sub, evt, path, label, t in con.execute(
                "SELECT Run, SubRun, Event, Path, ModuleLabel, Time FROM TimeModule"):
            if label in ex or path == "[art]" or (modules is not None and label not in modules):
                continue
            key = (run, sub, evt)
            if key not in keep:
                continue
            tot[key] += t
            mod[label] = mod.get(label, 0.0) + t
    finally:
        con.close()
    times = np.array([tot[e] for e in events[skip_first:]])
    return times, mod, len(times)


def summary(wd: str, config, sample, study, skip_first: int = 1) -> dict:
    """-> {"events", "mean_ms", "median_ms", "p90_ms", "p99_ms", "max_ms", "modules": {label: mean
    ms per event} (descending), "n_jobs", "n_failed", "n_modules"}"""
    dirs, nfail = artlog.ok_jobs(wd, "timing", config, sample, need="timing.db")
    res = {"n_jobs": len(dirs), "n_failed": nfail, "events": 0}
    if not dirs:
        res["note"] = "no ok timing jobs"
        return res
    allt: List[np.ndarray] = []
    mods: Dict[str, float] = {}
    mlist: Set[str] = set()
    for d in dirs:
        dumpf = os.path.join(d, "job.dump.fcl")
        modules = None
        if os.path.exists(dumpf):
            modules = path_modules(open(dumpf).read(), study.trigger_paths) - EXCLUDE
        if not modules:   # no fhicl-dump: the paths recorded by the TimeTracker
            modules = db_path_modules(os.path.join(d, "timing.db"), study.trigger_paths) - EXCLUDE
        if not modules:
            res.setdefault("warnings", []).append(f"{d}: no modules of the trigger paths found; all modules summed")
            modules = None
        t, m, n = event_times(os.path.join(d, "timing.db"), modules, skip_first=skip_first)
        allt.append(t)
        for k, v in m.items():
            mods[k] = mods.get(k, 0.0) + v
        mlist |= set(modules or m)
    t = np.concatenate(allt) * 1e3
    if len(t) == 0:
        res["note"] = "no events in timing.db"
        return res
    res.update({"events": int(len(t)), "mean_ms": float(t.mean()), "median_ms": float(np.median(t)),
                "p90_ms": float(np.percentile(t, 90)), "p99_ms": float(np.percentile(t, 99)),
                "max_ms": float(t.max()), "n_modules": len(mlist),
                "modules": {k: v * 1e3 / len(t) for k, v in sorted(mods.items(), key=lambda kv: -kv[1])},
                "skip_first": skip_first})
    return res
