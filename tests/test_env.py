"""provenance comparison tests (no mu2e environment needed)."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from trkcondtuning import env


def rec(build="b1", off="aaa", trig="ccc", diff=None):
    o = {"hash": off, "branch": "x", "dirty": diff is not None}
    if diff:
        o["diff"] = diff
    return {"build": build, "repos": {"Offline": o, "mu2e-trig-config": {"hash": trig, "branch": "x", "dirty": False}}}


def test_compare():
    assert env.compare(rec(), rec()) == []
    assert any("build" in d for d in env.compare(rec(), rec(build="b2")))
    assert any("Offline HEAD" in d for d in env.compare(rec(), rec(off="bbb")))
    assert any("mu2e-trig-config HEAD" in d for d in env.compare(rec(), rec(trig="ddd")))
    assert any("uncommitted" in d for d in env.compare(rec(diff="1"), rec(diff="2")))


def test_check_provenance_modes():
    wd = tempfile.mkdtemp(prefix="tct_test_")
    old = dict(rec(), host="h", user="u", time_utc="2026-01-01T00:00:00Z", tct={})
    env.write_provenance(wd, old, "first")
    new = dict(rec(off="bbb"), host="h", user="u", time_utc="2026-01-02T00:00:00Z", tct={})
    orig = env.provenance
    env.provenance = lambda e: new
    try:
        try:
            env.check_provenance(wd, {}, allow_mixed=False)
        except env.ProvenanceError:
            pass
        else:
            raise AssertionError("changed Offline must be refused")
        assert len(os.listdir(os.path.join(wd, "provenance"))) == 1   # nothing recorded
        _, diffs = env.check_provenance(wd, {}, allow_mixed=True)
        assert diffs and len(os.listdir(os.path.join(wd, "provenance"))) == 2
        _, diffs = env.check_provenance(wd, {}, allow_mixed=False)     # now same as last record
        assert diffs == []
    finally:
        env.provenance = orig


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
            print("ok", k)
