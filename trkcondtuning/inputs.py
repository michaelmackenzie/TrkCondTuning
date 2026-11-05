"""
Input file lists: samples/*.txt -> file paths (mdh), existence checks, background grouping.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional

from .study import Sample, repo_path
from .env import SETUP_SCRIPT

CACHE_NAME = "inputs_cache.json"
_MDH_ENV = ("source %s > /dev/null 2>&1; muse setup ops > /dev/null 2>&1; " % SETUP_SCRIPT)


def read_list(path: str) -> List[str]:
    """Entries of a list file: one per line, '#' comments and blank lines ignored."""
    out = []
    with open(path) as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if line:
                out.append(line)
    return out


def _mdh(names: List[str], location: str) -> List[str]:
    """mdh print-url for names (one call; mdh lives in the ops environment, separate from muse)."""
    if not names:
        return []
    args = "mdh print-url -s path -l %s %s" % (location, " ".join(names))
    cmd = args if shutil.which("mdh") else _MDH_ENV + args
    r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, cwd=tempfile.gettempdir())  # mdh drops files in its cwd
    lines = [l for l in r.stdout.split("\n") if l.strip()]
    if r.returncode != 0 or len(lines) != len(names):
        raise RuntimeError(f"mdh print-url -l {location} failed for {len(names)} names:\n{r.stderr[-500:]}")
    return lines


def _load_cache(wd: str) -> Dict[str, str]:
    try:
        with open(os.path.join(wd, CACHE_NAME)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def resolve(names: List[str], wd: Optional[str] = None, chunk: int = 50) -> List[str]:
    """
    Paths of the entries: absolute paths pass through (must exist); file names are resolved with
    mdh, disk location first, then tape (tape-backed dCache files are readable), and checked for
    existence. Resolutions are cached in <wd>/inputs_cache.json (re-checked for existence).
    Raises FileNotFoundError listing every file that is nowhere.
    """
    cache = _load_cache(wd) if wd else {}
    out: Dict[str, str] = {}
    todo = []
    for n in names:
        if os.path.isabs(n):
            out[n] = n
        elif n in cache and os.path.exists(cache[n]):
            out[n] = cache[n]
        elif n not in todo:
            todo.append(n)
    for loc in ("disk", "tape"):
        if not todo:
            break
        rest = []
        for i in range(0, len(todo), chunk):
            part = todo[i:i + chunk]
            for n, p in zip(part, _mdh(part, loc)):
                if os.path.exists(p):
                    out[n] = p
                else:
                    rest.append(n)
        todo = rest
    missing = [n for n in names if n not in out or not os.path.exists(out[n])]
    if missing:
        raise FileNotFoundError("input files not found (disk or tape): " + ", ".join(missing[:10])
                                + (" ..." if len(missing) > 10 else ""))
    if wd:
        new = {n: p for n, p in out.items() if not os.path.isabs(n)}
        if new != {k: cache.get(k) for k in new}:
            cache.update(new)
            os.makedirs(wd, exist_ok=True)
            tmp = os.path.join(wd, CACHE_NAME + ".tmp")
            with open(tmp, "w") as f:
                json.dump(cache, f, indent=1, sort_keys=True)
            os.replace(tmp, os.path.join(wd, CACHE_NAME))
    return [out[n] for n in names]


def sample_files(sample: Sample, wd: Optional[str] = None) -> List[str]:
    """Paths of the first sample.nfiles files of the sample's list, in list order."""
    names = read_list(repo_path(sample.files))
    if sample.nfiles is not None:
        names = names[:sample.nfiles]
    if not names:
        raise ValueError(f"sample {sample.name}: empty file list {sample.files}")
    return resolve(names, wd)


def groups(files: List[str], ngroups: int) -> List[List[str]]:
    """Contiguous chunks of PER = ceil(N / ngroups) files (as run_trigger_study.sh); empty chunks
    are dropped."""
    n = len(files)
    per = -(-n // max(1, ngroups))
    return [g for g in (files[i * per:(i + 1) * per] for i in range(ngroups)) if g]
