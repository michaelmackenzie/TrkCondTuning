"""
Local job queue: each job is a directory with job.fcl / inputs.txt / cmd.sh; the runner runs
the not-cached jobs in parallel (bash cmd.sh, stdout+stderr -> job.log), writes status.json,
and reports. Shared interactive node: at most 20 cores in total (hard refusal), default 16.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

HARD_MAX_CORES = 20
DONE_MARKER = "Art has completed and will exit with status 0"


@dataclass
class Job:
    """
    kind, config, sample, name : identify the job (dir = <wd>/jobs/<kind>/<config>/<sample>/<name>)
    cmd      : the text of cmd.sh (runs in the job directory; self-contained environment settings)
    files    : extra text files to write into the job directory {filename: text} (job.fcl, ...)
    inputs   : input file paths (written to inputs.txt)
    nsteps   : number of mu2e steps in cmd.sh (each must report a clean art exit)
    """
    kind: str
    config: str
    sample: str
    name: str
    dir: str
    cmd: str
    files: Dict[str, str] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    nsteps: int = 1

    @property
    def key(self) -> str:
        """sha1 of the job's fcl files + inputs.txt + cmd.sh."""
        h = hashlib.sha1()
        for n in sorted(self.files):
            if n.endswith(".fcl") and n != "job.dump.fcl":
                h.update(n.encode()); h.update(self.files[n].encode())
        h.update("\n".join(self.inputs).encode())
        h.update(self.cmd.encode())
        return h.hexdigest()[:16]

    @property
    def label(self) -> str:
        return f"{self.kind}/{self.config}/{self.sample}/{self.name}"

    def write(self) -> None:
        os.makedirs(self.dir, exist_ok=True)
        for n, t in self.files.items():
            with open(os.path.join(self.dir, n), "w") as f:
                f.write(t)
        with open(os.path.join(self.dir, "inputs.txt"), "w") as f:
            f.write("\n".join(self.inputs) + ("\n" if self.inputs else ""))
        p = os.path.join(self.dir, "cmd.sh")
        with open(p, "w") as f:
            f.write(self.cmd)
        os.chmod(p, 0o755)


@dataclass
class JobResult:
    ok: bool
    dir: str
    cached: bool
    job: Optional[Job] = None
    seconds: float = 0.0
    exit: Optional[int] = None


def read_status(jobdir: str) -> Optional[Dict]:
    try:
        with open(os.path.join(jobdir, "status.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def is_cached(job: Job) -> bool:
    st = read_status(job.dir)
    return bool(st and st.get("ok") and st.get("key") == job.key)


def log_ok(logpath: str, nsteps: int) -> bool:
    """Every mu2e step reported a clean exit."""
    try:
        with open(logpath, errors="replace") as f:
            return f.read().count(DONE_MARKER) >= nsteps
    except OSError:
        return False


class Runner:
    def __init__(self, max_cores: int = 16, env: Optional[Dict[str, str]] = None,
                 dry_run: bool = False, progress: Callable[[str], None] = None):
        if max_cores > HARD_MAX_CORES:
            raise ValueError(f"refusing max_cores={max_cores}: never more than {HARD_MAX_CORES} cores "
                             "on the shared mu2e node (count cores, not jobs)")
        if max_cores < 1:
            raise ValueError("max_cores must be >= 1")
        self.max_cores = max_cores
        self.env = env
        self.dry_run = dry_run
        self._print = progress or (lambda s: print(s, flush=True))
        self._lock = threading.Lock()
        self._procs: List[subprocess.Popen] = []

    # ------------------------------------------------------------------ one job
    def _run_one(self, job: Job) -> JobResult:
        job.write()
        stpath = os.path.join(job.dir, "status.json")
        if os.path.exists(stpath):
            os.remove(stpath)
        start = datetime.datetime.now(datetime.timezone.utc)
        t0 = time.time()
        logpath = os.path.join(job.dir, "job.log")
        with open(logpath, "w") as log:
            p = subprocess.Popen(["bash", os.path.join(job.dir, "cmd.sh")], cwd=job.dir, env=self.env,
                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            with self._lock:
                self._procs.append(p)
            code = p.wait()
            with self._lock:
                self._procs.remove(p)
        ok = code == 0 and log_ok(logpath, job.nsteps)
        sec = time.time() - t0
        st = {"exit": code, "ok": ok, "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
              "end": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "seconds": round(sec, 1), "host": socket.gethostname(), "key": job.key}
        tmp = stpath + ".tmp"
        with open(tmp, "w") as f:
            json.dump(st, f)
        os.replace(tmp, stpath)
        return JobResult(ok, job.dir, False, job, sec, code)

    def _kill_all(self):
        with self._lock:
            procs = list(self._procs)
        for p in procs:
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except OSError:
                pass

    # ------------------------------------------------------------------ queue
    def submit(self, jobs: List[Job]) -> List[JobResult]:
        """Run all not-cached jobs, at most max_cores at once (each job is one single-threaded
        process). Returns one JobResult per job, in order."""
        results: Dict[int, JobResult] = {}
        todo = []
        for i, j in enumerate(jobs):
            if is_cached(j):
                results[i] = JobResult(True, j.dir, True, j)
            else:
                todo.append((i, j))
        ncached = len(jobs) - len(todo)
        self._print(f"{len(jobs)} jobs: {ncached} cached, {len(todo)} to run (max {self.max_cores} cores)")
        if self.dry_run:
            for i, j in todo:
                self._print(f"  would run {j.label}")
            return [results.get(i, JobResult(False, j.dir, False, j)) for i, j in enumerate(jobs)]
        done = [0]
        t0 = time.time()

        def work(item):
            i, j = item
            r = self._run_one(j)
            with self._lock:
                done[0] += 1
                n = done[0]
            self._print(f"[{n}/{len(todo)}] {'ok    ' if r.ok else 'FAILED'} {j.label}  {r.seconds:.0f} s"
                        + ("" if r.ok else f"  (exit {r.exit}; see {os.path.join(j.dir, 'job.log')})"))
            return i, r

        if todo:
            ex = ThreadPoolExecutor(self.max_cores)
            try:
                for i, r in ex.map(work, todo):
                    results[i] = r
            except KeyboardInterrupt:
                self._kill_all()
                raise
            finally:
                ex.shutdown(wait=True)
            self._print(f"finished {len(todo)} jobs in {time.time() - t0:.0f} s")
        return [results[i] for i in range(len(jobs))]
