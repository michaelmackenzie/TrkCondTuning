"""inputs grouping / list reading / runner tests (no mu2e environment needed)."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from trkcondtuning import inputs, runner

TMP = tempfile.mkdtemp(prefix="tct_test_")


def test_read_list_and_groups():
    p = os.path.join(TMP, "l.txt")
    open(p, "w").write("# c\n\na\nb # x\n  \nc\nd\ne\n")
    assert inputs.read_list(p) == ["a", "b", "c", "d", "e"]
    # run_trigger_study.sh: PER = ceil(NF/NGROUP) contiguous chunks
    assert inputs.groups(list("abcde"), 2) == [list("abc"), list("de")]
    assert inputs.groups(list("abcde"), 4) == [list("ab"), list("cd"), list("e")]
    assert inputs.groups(list("abcd"), 4) == [["a"], ["b"], ["c"], ["d"]]
    assert inputs.groups(list("ab"), 1) == [list("ab")]


def test_resolve_absolute():
    f = os.path.join(TMP, "f.art")
    open(f, "w").write("x")
    assert inputs.resolve([f], TMP) == [f]
    try:
        inputs.resolve([os.path.join(TMP, "nope.art")], TMP)
    except FileNotFoundError:
        return
    raise AssertionError


def mkjob(name, script, nsteps=1):
    return runner.Job("trig", "c", "s", name, os.path.join(TMP, "jobs", name), "#!/bin/bash\n" + script + "\n",
                      {"job.fcl": "x"}, ["in.art"], nsteps)


def test_runner_cache_and_status():
    ok = mkjob("ok", "echo 'Art has completed and will exit with status 0.'")
    bad = mkjob("bad", "echo fail; exit 3")
    noart = mkjob("noart", "echo nothing")
    r = runner.Runner(max_cores=2, env=dict(os.environ), progress=lambda s: None)
    res = r.submit([ok, bad, noart])
    assert [x.ok for x in res] == [True, False, False] and not any(x.cached for x in res)
    st = json.load(open(os.path.join(ok.dir, "status.json")))
    assert st["ok"] and st["exit"] == 0 and st["key"] == ok.key
    res = r.submit([ok, bad])
    assert res[0].cached and not res[1].cached
    changed = mkjob("ok", "echo 'Art has completed and will exit with status 0.'; true")
    assert not runner.is_cached(changed)


def test_core_limit():
    try:
        runner.Runner(max_cores=21)
    except ValueError:
        return
    raise AssertionError("more than 20 cores must be refused")


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
            print("ok", k)
