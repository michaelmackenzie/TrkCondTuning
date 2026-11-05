"""
Study definition: the detector condition under study, the nominal reference, the samples, the
trigger paths and metrics, and the candidate reco / trigger settings to explore.

A study is a Python file (studies/<name>.py) that defines a module-level ``STUDY`` (a Study).
Everything a job needs is derived from it, so a study file plus a software build fully
determines the results.

Paths in a study (fcl fragments, condition tables, sample lists) are relative to the repository
root unless absolute.
"""
from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCOPES = ("trigger", "reco", "both")
ROLES = ("signal", "background", "cosmic")


def repo_path(p: str) -> str:
    """Absolute path of a repository-relative path (absolute paths are returned as they are)."""
    return p if os.path.isabs(p) else os.path.join(REPO, p)


# --------------------------------------------------------------------------- conditions
@dataclass(frozen=True)
class Condition:
    """
    Detector / calibration conditions, applied to the re-digitization AND the reconstruction
    (trigger and Offline).

    db_purpose, db_version : DbService purpose / version (e.g. "Sim_best", "v1_3")
    text_tables : DbService text tables overriding the database (repo-relative or absolute);
                  copied into the work directory and found through MU2E_SEARCH_PATH
    fcl         : fcl fragment with any other overrides (ProditionsService gain, noise, straw
                  response, ...). It must NOT set services.DbService.textFile (use text_tables).
    use_status  : re-digitize with makeSD.UseStatus true (no digis on straws without signal)
    redigi_ok   : the condition only LOWERS the straw hit efficiency w.r.t. the input sample's
                  conditions, so re-digitizing from the kept StrawGasSteps is valid (see README)
    """
    name: str
    db_purpose: str
    db_version: str
    text_tables: Tuple[str, ...] = ()
    fcl: Optional[str] = None
    use_status: bool = True
    redigi_ok: bool = True
    description: str = ""


# --------------------------------------------------------------------------- settings
@dataclass(frozen=True)
class Setting:
    """
    One named reco / trigger configuration change: an fcl fragment (file or inline text).

    scope    : "trigger" (trigger jobs only), "reco" (Offline reco only) or "both" (e.g. a
               straw-response calibration used by trigger and Offline)
    requires : names of settings that must be applied too (exploration adds this one only
               after them)
    group    : mutually exclusive group (at most one setting of a group in a configuration)
    order    : include order among the settings of a configuration (low first); later
               fragments override earlier ones
    """
    name: str
    fcl: Optional[str] = None
    text: Optional[str] = None
    scope: str = "trigger"
    requires: Tuple[str, ...] = ()
    group: Optional[str] = None
    order: int = 0
    description: str = ""

    def __post_init__(self):
        if (self.fcl is None) == (self.text is None):
            raise ValueError(f"setting {self.name}: give exactly one of fcl / text")
        if self.scope not in SCOPES:
            raise ValueError(f"setting {self.name}: scope must be one of {SCOPES}")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", self.name):
            raise ValueError(f"setting {self.name}: name must be [A-Za-z0-9_.-]")

    def render(self) -> str:
        """The fcl text of this setting, with a header comment."""
        body = self.text if self.text is not None else open(repo_path(self.fcl)).read()
        src = self.fcl if self.fcl else "inline"
        return f"# ---- setting {self.name} ({self.scope}; {src})\n{body.rstrip()}\n"

    def applies_to(self, kind: str) -> bool:
        """kind: 'trigger' or 'reco'."""
        return self.scope in (kind, "both")


# --------------------------------------------------------------------------- configurations
@dataclass(frozen=True)
class Config:
    """A condition plus an ordered set of settings. Its name is the work-directory key."""
    name: str
    condition: Condition
    settings: Tuple[Setting, ...] = ()

    def __post_init__(self):
        if not re.fullmatch(r"[A-Za-z0-9_.+-]+", self.name):
            raise ValueError(f"config {self.name}: name must be [A-Za-z0-9_.+-]")
        names = [s.name for s in self.settings]
        if len(set(names)) != len(names):
            raise ValueError(f"config {self.name}: duplicate settings {names}")
        groups = [s.group for s in self.settings if s.group]
        if len(set(groups)) != len(groups):
            raise ValueError(f"config {self.name}: two settings of one exclusive group {groups}")
        for s in self.settings:
            missing = [r for r in s.requires if r not in names]
            if missing:
                raise ValueError(f"config {self.name}: {s.name} requires {missing}")

    def ordered(self, kind: str) -> List[Setting]:
        """Settings applying to kind ('trigger' / 'reco'), in include order (stable)."""
        return sorted((s for s in self.settings if s.applies_to(kind)), key=lambda s: s.order)

    def with_settings(self, *extra: Setting, name: Optional[str] = None) -> "Config":
        sets = self.settings + tuple(extra)
        return Config(name or config_name(self.condition.name, sets), self.condition, sets)

    def key(self, kind: str) -> str:
        """Hash of what a job of this kind depends on (condition + applicable settings)."""
        payload = json.dumps({"condition": dataclasses.asdict(self.condition),
                              "settings": [s.render() for s in self.ordered(kind)]}, sort_keys=True)
        return hashlib.sha1(payload.encode()).hexdigest()[:12]


def config_name(condition: str, settings: Sequence[Setting]) -> str:
    """Readable config name: <condition>+<s1>+<s2>...; hashed if it gets too long."""
    name = "+".join([condition] + [s.name for s in settings])
    if len(name) > 120:
        h = hashlib.sha1(name.encode()).hexdigest()[:10]
        name = f"{condition}+{len(settings)}settings-{h}"
    return name


# --------------------------------------------------------------------------- samples
@dataclass(frozen=True)
class Sample:
    """
    An input digi dataset (art files with compressDigiMCs StrawGasSteps, e.g. MDC mixed digis).

    files      : text file (repo-relative) listing file names (resolved with mdh) or absolute
                 paths, one per line ('#' comments). The order is the job order: keep it fixed.
    role       : "signal" (efficiency; Offline reco; per-event MC truth), "background"
                 (trigger rates) or "cosmic" (efficiency by particle and direction)
    nfiles     : use the first nfiles of the list (None: all)
    nevents    : events read per file (signal / cosmic: one job per file; None: all)
    ngroups    : background only: the files are split into this many jobs, in list order
                 (keep it fixed: the re-digitization random numbers depend on the grouping)
    pdg        : signal particle / Offline fit hypothesis (11 CeM, -11 CeP)
    pmin       : Offline momentum threshold for 'reconstructable' [MeV/c]
    duty_factor: background: spill duty factor for rates (1BB 0.323, 2BB 0.246)
    microbunch_ns : background: microbunch period [ns] (1695)
    """
    name: str
    files: str
    role: str = "signal"
    nfiles: Optional[int] = None
    nevents: Optional[int] = None
    ngroups: int = 1
    pdg: int = 11
    pmin: float = 75.
    duty_factor: float = 0.323
    microbunch_ns: float = 1695.
    description: str = ""

    def __post_init__(self):
        if self.role not in ROLES:
            raise ValueError(f"sample {self.name}: role must be one of {ROLES}")


# --------------------------------------------------------------------------- selections
@dataclass(frozen=True)
class OfflineSelection:
    """Offline CE track selection (EventNtuple). The track per event is the highest-nactive
    fit of the sample's pdg, downstream at TT_Front, whose main MC particle is the primary."""
    nactive_trig: int = 15        # 'reconstructable' level used for trigger-given-Offline
    nactive_loose: int = 10
    # TrkQual-input box cuts ('quality'; scripts/resolution.py of the original study)
    min_active_frac: float = 0.8
    min_fitcon: float = 1e-3
    max_t0err: float = 0.9
    max_momerr: float = 0.5
    resolution_tail: float = 1.0  # |dp| > this [MeV/c] counts as tail


@dataclass(frozen=True)
class ExploreSettings:
    """
    Greedy forward selection (explore.py).

    Reco phase: from the baseline, add the reco/both-scope candidate that most increases the
    Offline objective (reconstructable efficiency, nactive >= nactive_trig, averaged over the
    signal samples) by >= min_gain (absolute) with paired significance >= min_z, while the
    quality-level sigma68 resolution worsens by <= max_res_worsening (relative).
    Trigger phase: from the reco-phase result, add the trigger-scope candidate that most
    increases the trigger objective (objective_paths efficiency of MC-triggerable events,
    averaged over the signal samples) by >= min_gain with z >= min_z, screening up to
    shortlist candidates on background; a candidate passes when, for every rate path,
    N_bkg(candidate) <= max(N_bkg(nominal), N_bkg(current)) * rate_factor + rate_slack_sigma *
    sqrt(N_bkg(nominal)) (paired, same background events).
    CPU: the proposal's trigger time must be <= cpu_factor x nominal (checked at the end;
    reported, the proposal is flagged if it fails).
    """
    min_gain: float = 0.005
    min_z: float = 2.0
    max_res_worsening: float = 0.10
    rate_factor: float = 1.0
    rate_slack_sigma: float = 1.0
    cpu_factor: float = 1.2
    shortlist: int = 3
    max_rounds: int = 8


# --------------------------------------------------------------------------- study
@dataclass
class Study:
    """
    name          : work-directory and results key
    nominal       : the nominal reference (the conditions the input samples were made with)
    baseline      : the condition under study with default reco / trigger settings
    references    : further configurations always evaluated (e.g. an earlier recommendation)
    samples       : input samples (see Sample)
    trigger_paths : trigger paths run in every trigger job (never the whole menu)
    objective_paths : paths (or 'a|b' ORs) whose efficiency the trigger exploration maximizes
    rate_paths    : paths whose background rate is constrained (default: trigger_paths)
    report_paths  : paths / ORs shown in the report (default: trigger_paths + objective_paths)
    cosmic_paths  : paths reported for cosmic samples (default: report_paths)
    trigger_candidates, reco_candidates : Settings explored (reco_candidates may be scope 'both')
    timing_events : background events for the CPU timing job
    """
    name: str
    nominal: Config
    baseline: Config
    samples: List[Sample]
    trigger_paths: List[str]
    objective_paths: List[str]
    references: List[Config] = field(default_factory=list)
    rate_paths: Optional[List[str]] = None
    report_paths: Optional[List[str]] = None
    cosmic_paths: Optional[List[str]] = None
    trigger_candidates: List[Setting] = field(default_factory=list)
    reco_candidates: List[Setting] = field(default_factory=list)
    offline: OfflineSelection = field(default_factory=OfflineSelection)
    explore: ExploreSettings = field(default_factory=ExploreSettings)
    timing_events: int = 16000
    description: str = ""

    def __post_init__(self):
        bad = [p for p in self.trigger_paths if p.startswith(("tpr_", "mpr_"))]
        if bad:
            print(f"WARNING: tpr_/mpr_ paths are not part of the real trigger: {bad}")
        for p in self.all_paths(self.objective_paths + (self.rate_paths or [])):
            if p not in self.trigger_paths:
                raise ValueError(f"path {p} is not in trigger_paths")
        names = [c.name for c in self.configs()]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate configuration names {names}")

    @staticmethod
    def all_paths(exprs: Sequence[str]) -> List[str]:
        """Individual paths of path expressions ('a|b' = OR)."""
        out = []
        for e in exprs:
            for p in e.split("|"):
                if p not in out:
                    out.append(p)
        return out

    def get_rate_paths(self) -> List[str]:
        return self.rate_paths or list(self.trigger_paths)

    def get_report_paths(self) -> List[str]:
        if self.report_paths:
            return self.report_paths
        return list(self.trigger_paths) + [p for p in self.objective_paths if p not in self.trigger_paths]

    def get_cosmic_paths(self) -> List[str]:
        return self.cosmic_paths or self.get_report_paths()

    def configs(self) -> List[Config]:
        return [self.nominal, self.baseline] + list(self.references)

    def samples_by_role(self, role: str) -> List[Sample]:
        return [s for s in self.samples if s.role == role]

    def sample(self, name: str) -> Sample:
        for s in self.samples:
            if s.name == name:
                return s
        raise KeyError(name)

    def candidate(self, name: str) -> Setting:
        for s in self.trigger_candidates + self.reco_candidates:
            if s.name == name:
                return s
        raise KeyError(name)

    def to_json(self) -> Dict:
        """Resolved study (fcl fragments rendered), for the work-directory record."""
        def cfg(c: Config):
            return {"name": c.name, "condition": dataclasses.asdict(c.condition),
                    "settings": [dataclasses.asdict(s) | {"rendered": s.render()} for s in c.settings]}
        return {"name": self.name, "description": self.description,
                "configs": [cfg(c) for c in self.configs()],
                "samples": [dataclasses.asdict(s) for s in self.samples],
                "trigger_paths": self.trigger_paths, "objective_paths": self.objective_paths,
                "rate_paths": self.get_rate_paths(), "report_paths": self.get_report_paths(),
                "cosmic_paths": self.get_cosmic_paths(),
                "trigger_candidates": [dataclasses.asdict(s) | {"rendered": s.render()} for s in self.trigger_candidates],
                "reco_candidates": [dataclasses.asdict(s) | {"rendered": s.render()} for s in self.reco_candidates],
                "offline": dataclasses.asdict(self.offline), "explore": dataclasses.asdict(self.explore),
                "timing_events": self.timing_events}


def load_study(path: str) -> Study:
    """Load STUDY from a study file (a path, or a name under studies/)."""
    if not os.path.exists(path):
        cand = os.path.join(REPO, "studies", path if path.endswith(".py") else path + ".py")
        if os.path.exists(cand):
            path = cand
    spec = importlib.util.spec_from_file_location(f"tct_study_{os.path.basename(path)[:-3]}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not isinstance(getattr(mod, "STUDY", None), Study):
        raise ValueError(f"{path} does not define STUDY = Study(...)")
    return mod.STUDY
