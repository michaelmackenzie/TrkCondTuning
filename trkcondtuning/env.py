"""
Mu2e environment capture and provenance.

mu2e_env()    : environment after setupmu2e-art + muse setup of the work area (cached)
provenance()  : host / user / time / muse build / git state of every repo of the work area
check_provenance() : compare with the last record of a work directory (shared work areas change
                under long runs) and record the current one
"""
from __future__ import annotations

import datetime
import getpass
import glob
import hashlib
import json
import os
import shutil
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

from .study import REPO

SETUP_SCRIPT = "/cvmfs/mu2e.opensciencegrid.org/setupmu2e-art.sh"
KEY_REPOS = ("Offline", "Production", "mu2e-trig-config", "EventNtuple")
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")

_cache: Dict[str, Dict[str, str]] = {}


class ProvenanceError(RuntimeError):
    pass


def find_musework(musework: Optional[str] = None) -> str:
    """The muse work area: argument, $TCT_MUSEWORK, else the parent directory of the repo if it
    is a muse work area (has build/ or .muse)."""
    w = musework or os.environ.get("TCT_MUSEWORK")
    if not w:
        parent = os.path.dirname(REPO)
        if os.path.isdir(os.path.join(parent, "build")) or os.path.exists(os.path.join(parent, ".muse")):
            w = parent
    if not w or not os.path.isdir(w):
        raise RuntimeError("no muse work area: set TCT_MUSEWORK to a muse work area (a directory "
                           "with a build/ directory) or clone TrkCondTuning into one")
    return os.path.realpath(w)


def _capture(work: str) -> Dict[str, str]:
    cmd = (f"source {SETUP_SCRIPT} > /dev/null 2>&1; cd '{work}' || exit 1; "
           "muse setup > /dev/null 2>&1; env -0")
    # start from a clean environment: the driver runs in the python analysis env (pyenv
    # rootana, conda), whose PATH / LD_LIBRARY_PATH / ROOT and compiler variables break mu2e
    # (cling picks up the conda headers and art segfaults)
    keep = ("HOME", "USER", "LOGNAME", "HOSTNAME", "TERM", "LANG", "TZ", "KRB5CCNAME",
            "X509_USER_PROXY", "X509_CERT_DIR", "BEARER_TOKEN_FILE", "BEARER_TOKEN", "TMPDIR")
    clean = {k: os.environ[k] for k in keep if k in os.environ}
    clean["PATH"] = "/usr/local/bin:/usr/bin:/bin"
    r = subprocess.run(["bash", "--noprofile", "--norc", "-c", cmd], capture_output=True, check=True,
                       env=clean)
    env = {}
    for item in r.stdout.split(b"\0"):
        if not item:
            continue
        k, _, v = item.decode(errors="replace").partition("=")
        if k.startswith("BASH_FUNC_") or not k.isidentifier():
            continue
        env[k] = v
    if "MUSE_BUILD_BASE" not in env:
        raise RuntimeError(f"muse setup failed in {work} (MUSE_BUILD_BASE not set)")
    return env


def mu2e_env(musework: Optional[str] = None, workdir: Optional[str] = None) -> Dict[str, str]:
    """
    Environment after setupmu2e-art + muse setup of the work area, with single-threaded BLAS
    and, if workdir is given, the work directory first on MU2E_SEARCH_PATH (condition text
    tables are found there). The captured base environment is cached per work area; a shell
    that already has this work area set up (setup.sh) is used as it is.
    """
    work = find_musework(musework)
    if work not in _cache:
        cur = os.environ
        if (os.path.realpath(cur.get("MUSE_WORK_DIR", "")) == work and cur.get("MUSE_BUILD_BASE")
                and shutil.which("mu2e", path=cur.get("PATH", ""))):
            _cache[work] = dict(cur)
        else:
            _cache[work] = _capture(work)
    env = dict(_cache[work])
    for v in THREAD_VARS:
        env[v] = "1"
    if workdir:
        sp = env.get("MU2E_SEARCH_PATH", "")
        env["MU2E_SEARCH_PATH"] = os.path.abspath(workdir) + (":" + sp if sp else "")
    return env


# --------------------------------------------------------------------------- provenance
def _git(path: str, *args: str, timeout: int = 120) -> str:
    r = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip() if r.returncode == 0 else ""


def repo_state(path: str, diff_hash: bool = False) -> Dict:
    st = {"hash": _git(path, "rev-parse", "HEAD"),
          "branch": _git(path, "rev-parse", "--abbrev-ref", "HEAD"),
          "dirty": bool(_git(path, "status", "--porcelain", "--untracked-files=no"))}
    if diff_hash and st["dirty"]:
        st["diff"] = hashlib.sha1(_git(path, "diff", "HEAD").encode()).hexdigest()[:12]
    return st


def work_repos(work: str) -> List[str]:
    names = []
    for d in sorted(os.listdir(work)):
        p = os.path.join(work, d)
        if d != "build" and os.path.realpath(p) != os.path.realpath(REPO) and os.path.isdir(p) and os.path.exists(os.path.join(p, ".git")):
            names.append(d)
    return names


def provenance(env: Dict[str, str]) -> Dict:
    """Provenance record: host, user, UTC time, muse build, git state of the work-area repos and
    of this repository."""
    work = os.path.realpath(env["MUSE_WORK_DIR"])
    names = work_repos(work)
    with ThreadPoolExecutor(8) as ex:
        states = list(ex.map(lambda n: repo_state(os.path.join(work, n), diff_hash=n in KEY_REPOS), names))
    return {"host": socket.gethostname(),
            "user": os.environ.get("USER") or getpass.getuser(),
            "time_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "musework": work,
            "build": os.path.basename(env.get("MUSE_BUILD_DIR", "").rstrip("/") or env["MUSE_BUILD_BASE"].rstrip("/")),
            "repos": dict(zip(names, states)),
            "backing": backing_chain(work),
            "tct": repo_state(REPO)}


def backing_chain(work: str) -> List[str]:
    """Release (Musing) backing chain of a work area: the resolved 'backing' links."""
    out, d = [], work
    for _ in range(5):
        link = os.path.join(d, "backing")
        if not os.path.islink(link) and not os.path.isdir(link):
            break
        d = os.path.realpath(link)
        out.append(d)
    return out


def last_record(wd: str) -> Optional[Dict]:
    files = sorted(glob.glob(os.path.join(wd, "provenance", "*.json")))
    if not files:
        return None
    with open(files[-1]) as f:
        return json.load(f)


def compare(old: Dict, new: Dict) -> List[str]:
    """Differences in what determines results: build and the Offline / Production /
    mu2e-trig-config / EventNtuple state."""
    diffs = []
    if old.get("build") != new.get("build"):
        diffs.append(f"muse build {old.get('build')} -> {new.get('build')}")
    if old.get("backing", []) != new.get("backing", []):
        diffs.append(f"backing release {old.get('backing')} -> {new.get('backing')}")
    for r in KEY_REPOS:
        a, b = old.get("repos", {}).get(r), new.get("repos", {}).get(r)
        if a is None and b is None:
            continue
        if (a or {}).get("hash") != (b or {}).get("hash"):
            diffs.append(f"{r} HEAD {(a or {}).get('hash', '-')[:9]} -> {(b or {}).get('hash', '-')[:9]}")
        elif (a or {}).get("diff") != (b or {}).get("diff"):
            diffs.append(f"{r} uncommitted changes differ ({(a or {}).get('diff')} -> {(b or {}).get('diff')})")
    return diffs


def write_provenance(wd: str, prov: Dict, command: str = "") -> str:
    d = os.path.join(wd, "provenance")
    os.makedirs(d, exist_ok=True)
    rec = dict(prov, command=command)
    base = prov["time_utc"].replace(":", "")
    path = os.path.join(d, base + ".json")
    n = 1
    while os.path.exists(path):
        path = os.path.join(d, f"{base}_{n}.json")
        n += 1
    with open(path, "w") as f:
        json.dump(rec, f, indent=1)
    return path


def check_provenance(wd: str, env: Dict[str, str], allow_mixed: bool = False,
                     command: str = "", record: bool = True) -> Tuple[Dict, List[str]]:
    """
    Provenance of the current command, compared with the last record in <wd>/provenance/.
    If Offline / mu2e-trig-config / ... or the build changed since: a loud warning and, unless
    allow_mixed, ProvenanceError (nothing recorded). Otherwise the record is written.
    Returns (provenance, differences).
    """
    prov = provenance(env)
    old = last_record(wd)
    diffs = compare(old, prov) if old else []
    if diffs:
        bar = "!" * 78
        msg = (f"{bar}\nWARNING: the software changed since the last command in this work directory:\n  "
               + "\n  ".join(diffs) +
               "\nResults from before and after are NOT comparable (not repeatable). Re-run the affected jobs\n"
               f"or use a work area that is not changing.\n{bar}")
        if not allow_mixed:
            raise ProvenanceError(msg + "\nRefusing to continue (pass --allow-mixed to override).")
        print(msg, flush=True)
    if record:
        write_provenance(wd, prov, command)
    return prov, diffs


def format_provenance(prov: Dict) -> str:
    lines = [f"host {prov['host']}  user {prov['user']}  {prov['time_utc']}  build {prov['build']}"]
    for r, s in prov["repos"].items():
        lines.append(f"  {r:20s} {s['hash'][:9]} {s['branch']}{' (dirty)' if s['dirty'] else ''}")
    t = prov["tct"]
    lines.append(f"  {'TrkCondTuning':20s} {t['hash'][:9] or '(no commit)'} {t['branch']}{' (dirty)' if t['dirty'] else ''}")
    return "\n".join(lines)
