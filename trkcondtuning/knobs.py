"""
Generated settings ("knobs"): study.Setting objects with inline fcl, built for whatever trigger
paths / modules a study uses, so that a cut like "15 -> 10 straw hits" is one line in a study.

Trigger filter label convention (mu2e-trig-config core/filters): the path
``cpr_TrkDe_75m70p_D0200`` has the filters ``CprTrkDe75m70pD0200TCFilter`` (time cluster),
``...HSFilter`` (helix selection, cuts under ``posHelicitySelection`` and
``negHelicitySelection``) and ``...KSFilter`` (KalSeed filter, cuts in ``KalSeedCuts[i]``; every
cpr_/apr_ TrkDe/TrkUe filter has two entries: e-minus and e-plus).
"""
from __future__ import annotations

from typing import Any, Iterable, List, Optional, Sequence, Tuple

from .study import Setting

STAGES = ("TC", "HS", "KS")
KS_ENTRIES = 2  # KalSeedCuts entries of the cpr_ / apr_ filters (checked in mu2e-trig-config)


def filter_label(path: str) -> str:
    """Filter-name stem of a trigger path: cpr_TrkDe_75m70p_D0200 -> CprTrkDe75m70pD0200."""
    parts = path.split("_")
    if len(parts) < 2 or not parts[0]:
        raise ValueError(f"unexpected trigger path name {path!r}")
    return parts[0].capitalize() + "".join(parts[1:])


def fcl_value(v: Any) -> str:
    """Format a python value as an fcl value."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return v if (v.startswith('"') or v.startswith("[")) else f'"{v}"'
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(fcl_value(x) for x in v) + "]"
    return repr(v)


def filter_cut_lines(paths: Sequence[str], stage: str, param: str, value: Any,
                     n_ks: int = KS_ENTRIES) -> List[str]:
    """fcl assignment lines setting `param` of the TC / HS / KS filter of each path."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}, got {stage!r}")
    v = fcl_value(value)
    lines = []
    for p in paths:
        base = f"physics.filters.{filter_label(p)}{stage}Filter"
        if stage == "TC":
            lines.append(f"{base}.{param} : {v}")
        elif stage == "HS":
            for h in ("posHelicitySelection", "negHelicitySelection"):
                lines.append(f"{base}.{h}.{param} : {v}")
        else:
            for i in range(n_ks):
                lines.append(f"{base}.KalSeedCuts[{i}].{param} : {v}")
    return lines


def filter_cuts(name: str, paths: Sequence[str], cuts: Iterable[Tuple[str, str, Any]],
                scope: str = "trigger", n_ks: int = KS_ENTRIES, **kw) -> Setting:
    """Several (stage, param, value) cuts on the same paths as one setting.
    kw: Setting fields (requires, group, order, description)."""
    lines: List[str] = []
    desc = []
    for stage, param, value in cuts:
        lines += filter_cut_lines(paths, stage, param, value, n_ks)
        desc.append(f"{stage}.{param}={value}")
    kw.setdefault("description", f"{', '.join(desc)} on {len(paths)} paths")
    return Setting(name=name, text="\n".join(lines) + "\n", scope=scope, **kw)


def filter_cut(name: str, paths: Sequence[str], stage: str, param: str, value: Any,
               scope: str = "trigger", n_ks: int = KS_ENTRIES, **kw) -> Setting:
    """One filter cut on a list of paths: stage 'TC' | 'HS' | 'KS'. HS cuts go to both helicity
    selections, KS cuts to every KalSeedCuts entry."""
    return filter_cuts(name, paths, [(stage, param, value)], scope=scope, n_ks=n_ks, **kw)


def module_param(name: str, module: str, param: str, value: Any, section: str = "producers",
                 scope: str = "trigger", **kw) -> Setting:
    """physics.<section>.<module>.<param> : value ('producers' or 'filters')."""
    if section not in ("producers", "filters", "analyzers"):
        raise ValueError(f"section must be producers / filters / analyzers, got {section!r}")
    kw.setdefault("description", f"{module}.{param} = {value}")
    return Setting(name=name, text=f"physics.{section}.{module}.{param} : {fcl_value(value)}\n",
                   scope=scope, **kw)


def combine(name: str, *settings: Setting, **kw) -> Setting:
    """One setting made of several (inline text of each, in order). They must share the scope
    (give scope= explicitly to override) and the exclusive group; requires are merged."""
    if not settings:
        raise ValueError("combine needs at least one setting")
    scopes = {s.scope for s in settings}
    scope = kw.pop("scope", None)
    if scope is None:
        if len(scopes) > 1:
            raise ValueError(f"combine {name}: mixed scopes {sorted(scopes)}; pass scope=")
        scope = scopes.pop()
    groups = {s.group for s in settings if s.group}
    group: Optional[str] = kw.pop("group", None)
    if group is None and groups:
        if len(groups) > 1:
            raise ValueError(f"combine {name}: mixed groups {sorted(groups)}")
        group = groups.pop()
    inner = {s.name for s in settings}
    requires = list(kw.pop("requires", ()))
    for s in settings:
        for r in s.requires:
            if r not in inner and r not in requires:
                requires.append(r)
    text = "\n".join(s.render().rstrip() for s in settings) + "\n"
    kw.setdefault("description", "combination of " + ", ".join(s.name for s in settings))
    return Setting(name=name, text=text, scope=scope, requires=tuple(requires), group=group, **kw)
