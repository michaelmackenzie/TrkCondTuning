"""
Job fcl generation. Generated fcls are SELF-CONTAINED: the repository templates, the condition
fragment and the setting fragments are inlined as text, so the only #includes left are of
Offline / Production / mu2e-trig-config / EventNtuple files (found through the muse work area).

Order in a job fcl:
    core template -> condition -> settings (Config.ordered(kind) order) -> job overrides
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
from typing import Dict, List, Optional

from .study import Condition, Config, Sample, Study, repo_path, REPO

TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

# AprHelixTruthAna inputs: the APR merged helices and the finder's input combo hits (labels
# checked with fhicl-dump of a generated job; see tests/test_fclgen.py)
APR_HELIX_TAG = "TrigAprHelixMerger"
APR_COMBOHIT_TAG = "TrigFlagPH"
STRAWDIGIMC_TAG = "makeSD"


def template(name: str) -> str:
    with open(os.path.join(TEMPLATES, name)) as f:
        return f.read()


def section(title: str) -> str:
    return f"\n# ================ {title}\n"


# --------------------------------------------------------------------------- conditions
def condition_dir(wd: str, cond: Condition) -> str:
    return os.path.join(wd, "conditions", cond.name)


def install_condition_tables(wd: str, cond: Condition) -> List[str]:
    """Copy the condition's text tables to <wd>/conditions/<name>/; returns the relative paths
    ("conditions/<name>/<file>") DbService finds through MU2E_SEARCH_PATH (which contains wd).
    Copying is skipped when the destination is identical."""
    out = []
    d = condition_dir(wd, cond)
    for t in cond.text_tables:
        src = repo_path(t)
        if not os.path.exists(src):
            raise FileNotFoundError(f"condition {cond.name}: text table {src} not found")
        os.makedirs(d, exist_ok=True)
        dst = os.path.join(d, os.path.basename(src))
        if not (os.path.exists(dst) and _same(src, dst)):
            shutil.copyfile(src, dst)
        out.append(f"conditions/{cond.name}/{os.path.basename(src)}")
    return out


def _same(a: str, b: str) -> bool:
    with open(a, "rb") as fa, open(b, "rb") as fb:
        return fa.read() == fb.read()


def condition_fcl(cond: Condition, wd: str, redigi: bool) -> str:
    """The condition as fcl text. redigi: also set makeSD.UseStatus (the re-digitization step)."""
    if cond.fcl and re.search(r"DbService\.textFile", open(repo_path(cond.fcl)).read()):
        raise ValueError(f"condition {cond.name}: its fcl must not set DbService.textFile (use text_tables)")
    tables = install_condition_tables(wd, cond)
    lines = [section(f"condition {cond.name}")]
    lines.append(f'services.DbService.purpose : "{cond.db_purpose}"')
    lines.append(f'services.DbService.version : "{cond.db_version}"')
    if tables:
        lines.append("services.DbService.textFile : [ " + ", ".join(f'"{t}"' for t in tables) + " ]")
    if cond.fcl:
        lines.append(f"# ---- condition fragment ({cond.fcl})")
        lines.append(open(repo_path(cond.fcl)).read().rstrip())
    if redigi:
        lines.append(f"physics.producers.makeSD.UseStatus : {'true' if cond.use_status else 'false'}")
    return "\n".join(lines) + "\n"


def settings_fcl(config: Config, kind: str) -> str:
    """The applicable settings (kind: 'trigger' or 'reco') in include order."""
    s = config.ordered(kind)
    if not s:
        return ""
    return section(f"settings ({kind}) of {config.name}") + "\n".join(x.render() for x in s)


# --------------------------------------------------------------------------- helpers
def filter_label(path: str) -> str:
    """cpr_TrkDe_75m70p_D0200 -> CprTrkDe75m70pD0200"""
    p = path.replace("_", "")
    return p[:1].upper() + p[1:]


def _trigger_paths_line(paths: List[str]) -> str:
    return "physics.trigger_paths : [ TriggerablePath, " + ", ".join(paths) + " ]"


def _quote_list(items: List[str]) -> str:
    return "[ " + ", ".join(f'"{i}"' for i in items) + " ]"


def _no_art_output() -> str:
    return ("outputs : {}\n"
            "physics.OutputPath : []\n"
            "end_paths : []\n"
            "physics.end_paths : []")


def _only_ana_end_path() -> str:
    return "outputs : {}\nphysics.OutputPath : []"


def _ana_block(study: Study) -> str:
    return f"""
# end-path analyzer: per-event trigger bits (trig_<path>) and signal-particle truth
physics.analyzers.aprAna : {{
  module_type    : AprHelixTruthAna
  helixSeedTag   : "{APR_HELIX_TAG}"
  comboHitTag    : "{APR_COMBOHIT_TAG}"
  strawDigiMCTag : "{STRAWDIGIMC_TAG}"
  triggerPaths   : {_quote_list(study.trigger_paths)}
  # only MC-triggerable events (makeSD doesn't run on the others): the tree entries are the
  # efficiency denominator
  SelectEvents   : [ TriggerablePath ]
}}
physics.AnaPath : [ aprAna ]
physics.end_paths : [ AnaPath ]
end_paths : [ AnaPath ]
services.TFileService : {{ fileName : "ana.root" }}
"""


def _selection(sample: Sample) -> str:
    """Signal / cosmic keep the MC-triggerable events; background keeps all (DigitizePath)."""
    if sample.role == "background":
        return 'physics.filters.TriggerableTrigger.TriggerNames : [ "DigitizePath" ]\n'
    return ""


# --------------------------------------------------------------------------- generators
def trig_fcl(study: Study, config: Config, sample: Sample, wd: str, mode: str = "trig") -> str:
    """
    mode "trig"   : trigger-only job, no art output, end-path AprHelixTruthAna -> ana.root
          "stage" : as trig without the analyzer; TC/HS/KS filters of the objective paths in
                    debug mode and an ArtReport line per event
          "timing": as trig without the analyzer; TimeTracker sqlite timing.db
    """
    if mode not in ("trig", "stage", "timing"):
        raise ValueError(mode)
    t = [f"# TrkCondTuning job: {mode}  study={study.name}  config={config.name}  sample={sample.name}\n"
         "# generated; do not edit (see trkcondtuning/fclgen.py)\n",
         section("template redigi_core.fcl"), template("redigi_core.fcl"),
         condition_fcl(config.condition, wd, redigi=True),
         settings_fcl(config, "trigger"),
         section("job overrides"),
         _trigger_paths_line(study.trigger_paths),
         _selection(sample)]
    if mode == "trig":
        t.append(_only_ana_end_path())
        t.append(_ana_block(study))
    else:
        t.append(_no_art_output())
    if mode == "stage":
        t.append("services.message.destinations.log.categories.ArtReport.reportEvery : 1\n"
                 "services.message.destinations.log.categories.ArtReport.limit : -1")
        for p in Study.all_paths(study.objective_paths):
            L = filter_label(p)
            t.append(f"physics.filters.{L}TCFilter.debugLevel : 2\n"
                     f"physics.filters.{L}HSFilter.debugLevel : 3\n"
                     f"physics.filters.{L}KSFilter.debugLevel : 3")
    if mode == "timing":
        t.append("services.TimeTracker : { dbOutput : { filename : \"timing.db\" overwrite : true } }\n"
                 "services.scheduler.wantSummary : true")
    return "\n".join(x for x in t if x) + "\n"


def redigi_fcl(study: Study, config: Config, sample: Sample, wd: str, out: str = "dig.art") -> str:
    """Re-digitization step of an offline job: trigger-scope settings, keeps the triggerable events."""
    t = [f"# TrkCondTuning job: offline/redigi  study={study.name}  config={config.name}  sample={sample.name}\n",
         section("template redigi_core.fcl"), template("redigi_core.fcl"),
         condition_fcl(config.condition, wd, redigi=True),
         settings_fcl(config, "trigger"),
         section("job overrides"),
         _trigger_paths_line(study.trigger_paths),
         _selection(sample),
         f'outputs.Output.fileName : "{out}"']
    return "\n".join(x for x in t if x) + "\n"


def reco_fcl(study: Study, config: Config, wd: str, out: str = "mcs.art") -> str:
    """Offline reconstruction step (reco-scope settings)."""
    t = [f"# TrkCondTuning job: offline/reco  study={study.name}  config={config.name}\n",
         section("template reco_core.fcl"), template("reco_core.fcl"),
         condition_fcl(config.condition, wd, redigi=False),
         settings_fcl(config, "reco"),
         section("job overrides"),
         f'outputs.LoopHelixOutput.fileName : "{out}"']
    return "\n".join(x for x in t if x) + "\n"


def ntuple_fcl(study: Study, config: Config, wd: str) -> str:
    """EventNtuple step (condition applies: ntuple reads the geometry / conditions too)."""
    t = [f"# TrkCondTuning job: offline/ntuple  study={study.name}  config={config.name}\n",
         section("template ntuple.fcl"), template("ntuple.fcl"),
         condition_fcl(config.condition, wd, redigi=False)]
    return "\n".join(t) + "\n"


def includes(fcl_text: str) -> List[str]:
    """The #include targets of a fcl text."""
    return re.findall(r'^\s*#include\s+"([^"]+)"', fcl_text, flags=re.M)


def check_self_contained(fcl_text: str) -> List[str]:
    """Includes that are not Offline / Production / mu2e-trig-config / EventNtuple files."""
    ok = ("Offline/", "Production/", "mu2e-trig-config/", "EventNtuple/")
    return [i for i in includes(fcl_text) if not i.startswith(ok)]
