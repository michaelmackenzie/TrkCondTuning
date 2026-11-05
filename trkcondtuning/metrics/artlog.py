"""
Parsing of art job output (TrigReport in job.log) and work-directory job helpers shared by the
metric modules.
"""
from __future__ import annotations

import glob
import json
import os
import re
from typing import Dict, List, Optional, Sequence, Tuple


def name_of(x) -> str:
    """Name of a Config / Sample object or a plain string."""
    return x if isinstance(x, str) else x.name


# --------------------------------------------------------------------------- job directories
def job_dirs(wd: str, kind: str, config, sample) -> List[str]:
    """Existing job directories <wd>/jobs/<kind>/<config>/<sample>/<job>, sorted.
    Uses jobs.job_dirs when importable, otherwise a plain glob."""
    try:
        from trkcondtuning import jobs  # type: ignore
        return jobs.job_dirs(wd, kind, name_of(config), name_of(sample))
    except Exception:
        pass
    base = os.path.join(wd, "jobs", kind, name_of(config), name_of(sample))
    return sorted(d for d in glob.glob(os.path.join(base, "*")) if os.path.isdir(d))


def read_status(d: str) -> Optional[dict]:
    try:
        with open(os.path.join(d, "status.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def ok_jobs(wd: str, kind: str, config, sample, need: Optional[str] = None) -> Tuple[List[str], int]:
    """(directories of jobs with status.ok true [and the file `need` present], number of
    failed / incomplete jobs). Job directories without a status.json count as failed."""
    good, bad = [], 0
    for d in job_dirs(wd, kind, config, sample):
        st = read_status(d)
        if st and st.get("ok") and (need is None or os.path.exists(os.path.join(d, need))):
            good.append(d)
        else:
            bad += 1
    return good, bad


# --------------------------------------------------------------------------- TrigReport
def path_counts(log: str) -> Dict[str, Tuple[int, int]]:
    """{path: (run, passed)} from the last 'Trigger-path summary' of an art log (as
    scripts/trig_summary.py of the original study)."""
    out: Dict[str, Tuple[int, int]] = {}
    on = False
    try:
        fh = open(log, errors="replace")
    except OSError:
        return out
    with fh:
        for line in fh:
            if "Trigger-path summary" in line:
                on, out = True, {}
            elif "End-path summary" in line or "Modules in path" in line:
                on = False
            elif on:
                f = line.split()
                if len(f) == 7 and f[0] == "TrigReport" and f[1].isdigit():
                    out[f[6]] = (int(f[2]), int(f[3]))
    return out


def event_summary(log: str) -> Optional[Tuple[int, int]]:
    """(total, passed) of the last 'TrigReport Events total = N passed = M' line, or None."""
    res = None
    try:
        fh = open(log, errors="replace")
    except OSError:
        return None
    with fh:
        for line in fh:
            m = re.match(r"TrigReport Events total = (\d+) passed = (\d+)", line)
            if m:
                res = (int(m.group(1)), int(m.group(2)))
    return res


def sum_path_counts(dirs: Sequence[str], logname: str = "job.log") -> Dict[str, Tuple[int, int]]:
    """Path counts summed over the logs of several job directories."""
    tot: Dict[str, Tuple[int, int]] = {}
    for d in dirs:
        for p, (r, n) in path_counts(os.path.join(d, logname)).items():
            r0, n0 = tot.get(p, (0, 0))
            tot[p] = (r0 + r, n0 + n)
    return tot


def art_ok(log: str) -> bool:
    """True if the art log ends with 'Art has completed and will exit with status 0'."""
    try:
        with open(log, errors="replace") as f:
            return "Art has completed and will exit with status 0" in f.read()
    except OSError:
        return False
