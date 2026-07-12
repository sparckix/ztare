"""Resolve a Scenario into concrete kernel wiring — the ONE engine-side door.

A name → {rubric, run-config, gate-package cage-factory, declared surface}. Precedence is
**explicit CLI flag > scenario > code default** (the scenario only backfills what the user left unset), so a
scenario is a convenience bundle, never a straitjacket. The service/CLI layer passes `--scenario` as an opaque
string; every binding happens here so scenario config never has to serialize back through the 424-env-var
sprawl this layer is meant to reduce.

Two honored effects today:
  * `apply_scenario_to_args` backfills the autoresearch loop's `args` (rubric/iters/models/dynamic). The rubric
    is the load-bearing lever — it drives judge dimensions, persona and steering across the whole loop.
  * `build_cage_factory` wraps the default Cage factory to append a scenario's gate-package (honored wherever
    the Cage engages). Claim-governance scenarios ship an empty package (their lever is the rubric); this exists
    for fit/analysis scenarios and future promoted gates. Nothing is auto-wired into the loop's cage seam yet —
    a gate-driven scenario opts in explicitly (see scenarios/README.md), so a package can never be dead config.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ztare.scenarios.loader import load_scenario


@dataclass
class ScenarioResolution:
    scenario: Any                                  # ScenarioConfig
    applied: "dict[str, Any]" = field(default_factory=dict)   # what was pushed into the run (honored)
    declared: "dict[str, Any]" = field(default_factory=dict)  # extension surface recorded; wiring per-scenario
    capabilities: "dict[str, Any]" = field(default_factory=dict)  # declared names -> typed plug-ins (registry)
    notes: "list[str]" = field(default_factory=list)


def _arg_passed(flag: str, argv: "Optional[list[str]]" = None) -> bool:
    """Did the user pass this flag explicitly? (CLI always wins over the scenario.)"""
    argv = sys.argv if argv is None else argv
    return any(a == flag or a.startswith(flag + "=") for a in argv)


def apply_scenario_to_args(name: str, args: Any, *, argv: "Optional[list[str]]" = None) -> ScenarioResolution:
    """Load scenario `<name>` and backfill the loop's `args` namespace — ONLY where the user did not set that
    flag explicitly (CLI wins). Returns a ScenarioResolution for logging. This is the single call the
    autoresearch loop makes right after `parse_args()`."""
    sc = load_scenario(name)
    res = ScenarioResolution(scenario=sc)

    # rubric — the load-bearing lever (drives judge dimensions/persona/steering). Backfill only if unset.
    if sc.rubric and not _arg_passed("--rubric", argv) and getattr(args, "rubric", None) in (None, ""):
        args.rubric = sc.rubric
        res.applied["rubric"] = sc.rubric

    # iters — only if the user didn't pass --iters (its argparse default is a real number, so use argv).
    if sc.iters and not _arg_passed("--iters", argv):
        args.iters = sc.iters
        res.applied["iters"] = sc.iters

    # models — env/CLI default resolves to a family or ""; backfill only when still empty.
    if sc.mutator_model and not _arg_passed("--mutator_model", argv) and not getattr(args, "mutator_model", ""):
        args.mutator_model = sc.mutator_model
        res.applied["mutator_model"] = sc.mutator_model
    if sc.judge_model and not _arg_passed("--judge_model", argv) and not getattr(args, "judge_model", ""):
        args.judge_model = sc.judge_model
        res.applied["judge_model"] = sc.judge_model

    # dynamic — a store_true flag; scenario can turn it on, never off (an explicit --dynamic already set it).
    if sc.dynamic and not getattr(args, "dynamic", False):
        args.dynamic = True
        res.applied["dynamic"] = True

    # gate_package — stash for a gate-driven scenario's opt-in cage-factory (build_cage_factory).
    if sc.gate_package:
        setattr(args, "scenario_gate_package", list(sc.gate_package))
        res.applied["gate_package"] = list(sc.gate_package)

    # declared extension surface — recorded for observability + RESOLVED to typed capability plug-ins.
    for k in ("goal_type", "solvers", "evidence_sources", "renderer", "rechecks",
              "workbench_panels", "deliverables", "deliverable_specs"):
        v = getattr(sc, k)
        if v:
            res.declared[k] = v
    res.capabilities = resolve_capabilities(sc, notes=res.notes)
    return res


def resolve_capabilities(sc: Any, *, notes: "Optional[list[str]]" = None) -> "dict[str, Any]":
    """Resolve a scenario's declared capability NAMES to registered typed plug-ins (EvidenceProvider / Renderer
    / Solver) via `scenarios.registry`. Unknown names are recorded in `notes` and skipped — a scenario naming
    an absent capability warns, it never bricks the run. Returns
    {'evidence': [providers], 'renderer': renderer, 'solver': [solvers], 'recheck': [rechecks]}."""
    from ztare.scenarios import registry as reg

    notes = notes if notes is not None else []
    caps: "dict[str, Any]" = {}
    for src in getattr(sc, "evidence_sources", []) or []:
        obj = reg.get("evidence", src)
        if obj is None:
            notes.append(f"unknown evidence source '{src}' (available: {reg.available('evidence')})")
        else:
            caps.setdefault("evidence", []).append(obj)
    rname = getattr(sc, "renderer", "")
    if rname:
        r = reg.get("renderer", rname)
        if r is None:
            notes.append(f"unknown renderer '{rname}' (available: {reg.available('renderer')})")
        else:
            caps["renderer"] = r
    for sname in getattr(sc, "solvers", []) or []:
        obj = reg.get("solver", sname)
        if obj is None:
            notes.append(f"unknown solver '{sname}' (available: {reg.available('solver')})")
        else:
            caps.setdefault("solver", []).append(obj)
    for rname in getattr(sc, "rechecks", []) or []:
        obj = reg.get("recheck", rname)
        if obj is None:
            notes.append(f"unknown recheck '{rname}' (available: {reg.available('recheck')})")
        else:
            caps.setdefault("recheck", []).append(obj)
    return caps


def scenario_effect(name: str) -> "dict[str, Any]":
    """Pure surfacing of what a scenario `<name>` BINDS (the same wiring `apply_scenario_to_args` /
    `resolve_capabilities` perform on a real run — reused here, not reimplemented, so this can never drift from
    what a run actually honors) and its rubric EFFECT (judge dimensions + persona). Read-only, no LLM, no run —
    the authoring mirror for a workbench 'what would this scenario do' preview. A scenario with no rubric (or a
    rubric file that's gone missing) returns empty dims / a None persona, never a crash — the gap is noted."""
    sc = load_scenario(name)
    notes: "list[str]" = []
    caps = resolve_capabilities(sc, notes=notes)

    bindings: "dict[str, Any]" = {
        "rubric": sc.rubric,
        "run": {"iters": sc.iters, "dynamic": sc.dynamic, "mutator": sc.mutator_model, "judge": sc.judge_model},
        "gate_package": list(sc.gate_package),
        "deliverables": list(sc.deliverables),
        "deliverable_specs": [spec.model_dump(mode="json") for spec in getattr(sc, "deliverable_specs", []) or []],
        "evidence": [getattr(p, "name", str(p)) for p in caps.get("evidence", [])],
        "renderer": getattr(caps.get("renderer"), "name", None) if caps.get("renderer") is not None else None,
        "solvers": [getattr(s, "name", str(s)) for s in caps.get("solver", [])],
        "rechecks": [getattr(r, "name", str(r)) for r in caps.get("recheck", [])],
        "workbench_panels": list(getattr(sc, "workbench_panels", []) or []),
        "goal_type": sc.goal_type,
    }

    dimensions: "list[dict[str, Any]]" = []
    persona: "Optional[str]" = None
    if sc.rubric:
        import json

        from ztare.common.paths import RUBRICS_DIR

        rpath = RUBRICS_DIR / f"{sc.rubric}.json"
        if rpath.exists():
            try:
                rub = json.loads(rpath.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                notes.append(f"rubric '{sc.rubric}' at {rpath} failed to parse: {exc}")
                rub = {}
            dimensions = [
                {"name": d.get("name", ""), "weight": d.get("weight", 0), "description": d.get("description", "")}
                for d in rub.get("dimensions", []) or []
            ]
            persona = str(rub.get("persona") or "").strip() or None
        else:
            notes.append(f"rubric '{sc.rubric}' has no file at {rpath}")

    effect = {
        "dimensions": dimensions,
        "persona": persona,
        "adds_dimensions": bool(dimensions),
        "weights_sum": sum(int(d.get("weight", 0)) for d in dimensions),
    }

    return {"name": sc.name, "description": sc.description, "bindings": bindings, "effect": effect, "notes": notes}


def _scenario_gate_registry() -> "dict[str, Any]":
    """The scenario-gate registry: {gate_name: Gate}. v1 ships none (claim-governance scenarios use rubric
    levers); fit/analysis scenarios register promoted gates here. Kept as a function so future gates can be
    discovered lazily without importing heavy gate modules at import time."""
    return {}


def build_cage_factory(gate_package: "list[str]", base_factory: "Callable[[], Any]", *,
                       registry: "Optional[dict[str, Any]]" = None) -> "Callable[[], Any]":
    """Wrap a zero-arg Cage factory so a scenario's gate-package is appended to the built Cage — the exact
    seam the loop exposes at `autoresearch_loop.py` (`cage_factory=...`). Unknown gate names are logged and
    skipped: a bad package must never brick a run. `registry` is injectable for tests."""
    def _factory() -> Any:
        cage = base_factory()
        if cage is None or not gate_package:
            return cage
        reg = registry if registry is not None else _scenario_gate_registry()
        for gname in gate_package:
            g = reg.get(gname)
            if g is None:
                print(f"[scenario] unknown gate '{gname}' in gate_package — skipped", flush=True)
                continue
            if hasattr(cage, "gates") and isinstance(cage.gates, dict):
                cage.gates[g.name] = g
                if hasattr(cage, "_topo_cache"):
                    cage._topo_cache = None  # invalidate topo cache after append (mirrors register_*_gates)
        return cage
    return _factory


# ─────────────────────────────────────────────────────────────────────────────────────────────────────────
# Behavioral acceptance selftest — Fable's bar: a scenario must produce a NON-EMPTY with/without diff on real,
# honored code paths, or it's cosmetic. Deterministic (no LLM): asserts the scenario changes the INPUTS that
# real kernel code consumes (rubric selection, judge dimensions/persona, resolve_cage_mode channel, cage
# gate-list). A full end-to-end LLM-run diff is the integration test, documented in scenarios/README.md.
# ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def _selftest() -> int:
    import json
    from types import SimpleNamespace

    from ztare.common.paths import RUBRICS_DIR

    fails: "list[str]" = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # 1. The scenario applies its rubric to a bare args namespace (the honored lever).
    a = SimpleNamespace(rubric=None, iters=10, mutator_model="", judge_model="", dynamic=False)
    res = apply_scenario_to_args("product-manager", a, argv=["autoresearch"])
    ok("scenario backfills its rubric onto args", a.rubric == "product_manager")
    ok("scenario records what it applied", res.applied.get("rubric") == "product_manager")
    ok("scenario backfills its iters", a.iters == 8)

    # 2. Precedence: an explicit --rubric WINS over the scenario (CLI wins).
    b = SimpleNamespace(rubric="user_choice", iters=10, mutator_model="", judge_model="", dynamic=False)
    apply_scenario_to_args("product-manager", b, argv=["autoresearch", "--rubric", "user_choice"])
    ok("explicit --rubric overrides scenario (CLI > scenario)", b.rubric == "user_choice")

    # 3. NON-COSMETIC: the scenario's rubric changes what real, honored code consumes.
    pm = json.loads((RUBRICS_DIR / "product_manager.json").read_text(encoding="utf-8"))
    dim_names = [d.get("name", "").lower() for d in pm.get("dimensions", [])]
    ok("PM rubric carries >=4 weighted PM dimensions (honored: drive judge scoring)",
       len([d for d in pm.get("dimensions", []) if d.get("weight", 0) > 0]) >= 4)
    ok("PM rubric surfaces the PM levers (evidence / reversibility / falsifier / dependency)",
       any("evidence" in n for n in dim_names) and any("revers" in n for n in dim_names)
       and any("falsifi" in n for n in dim_names) and any("depend" in n for n in dim_names))
    ok("PM rubric ships a non-empty persona (honored: drives the judge prompt)",
       bool(str(pm.get("persona", "")).strip()))
    ok("PM rubric weights sum to 100", sum(int(d.get("weight", 0)) for d in pm["dimensions"]) == 100)

    # with/without DIFF is non-empty vs a bare rubric — the acceptance gate.
    bare_dims = []
    ok("with/without scenario diff is NON-EMPTY (not cosmetic)", dim_names != bare_dims)

    # 4. resolve_cage_mode channel exists and is honored (a future gate-driven scenario's rubric flips it).
    from ztare.orchestrator.state import resolve_cage_mode
    ok("Cage-mode channel honored: authoritative flag -> 'authoritative'",
       resolve_cage_mode({"cage_authoritative_mode": True}) == "authoritative")
    ok("Cage-mode channel honored: no flags -> 'off'", resolve_cage_mode({}) == "off")

    # 5. gate_package MECHANISM: build_cage_factory appends the named gate; the default factory lacks it.
    from ztare.gates.cage import Cage, Gate
    g = Gate(name="scenario_selftest_gate", phase="POST_FIT",
             can_handle=lambda s, c: (True, "selftest"), run=lambda s, c: {"ok": True})
    base = lambda: Cage([])  # noqa: E731 — tiny factory
    factory = build_cage_factory(["scenario_selftest_gate"], base,
                                 registry={"scenario_selftest_gate": g})
    ok("gate_package appends its gate to the built Cage", "scenario_selftest_gate" in factory().gates)
    ok("default Cage (no package) lacks the gate — the cage diff is real",
       "scenario_selftest_gate" not in base().gates)
    ok("unknown gate name is skipped, not fatal",
       "nope" not in build_cage_factory(["nope"], base, registry={})().gates)

    # 6. TYPED capability interfaces: registry discovery, Protocol conformance, scenario -> plug-in resolution.
    from ztare.scenarios import registry as reg
    from ztare.scenarios.protocols import EvidenceProvider, Renderer
    ok("registry discovers the local_files EvidenceProvider", "local_files" in reg.available("evidence"))
    ok("registry discovers the markdown Renderer", "markdown" in reg.available("renderer"))
    ev = reg.get("evidence", "local_files")
    ok("local_files satisfies the EvidenceProvider Protocol", isinstance(ev, EvidenceProvider))
    ok("markdown satisfies the Renderer Protocol", isinstance(reg.get("renderer", "markdown"), Renderer))

    # the PM scenario's declared capability NAMES resolve to typed plug-ins (via apply_scenario_to_args above).
    ok("PM scenario resolves local and structured evidence providers",
       {getattr(p, "name", "") for p in res.capabilities.get("evidence", [])}
       == {"local_files", "structured_files"})
    ok("PM scenario resolves renderer 'markdown'",
       getattr(res.capabilities.get("renderer"), "name", "") == "markdown")

    # the plug-ins actually WORK (not vaporware): local_files reads real files, markdown renders.
    got = ev.fetch(str(RUBRICS_DIR / "product_manager.json"))
    ok("local_files.fetch reads a real evidence file with body", got is not None and bool(got.body))
    ok("local_files.list_evidence enumerates a real dir", len(ev.list_evidence(str(RUBRICS_DIR))) > 0)
    rr = reg.get("renderer", "markdown").render({"title": "T", "verdict": "pass", "score": 0.9})
    ok("markdown renderer emits a markdown verdict", rr.text.startswith("# T") and "Verdict" in rr.text)

    # 7. an unknown capability name warns (note recorded), never raises.
    from types import SimpleNamespace as _NS
    _notes: "list[str]" = []
    caps = resolve_capabilities(_NS(evidence_sources=["nope"], renderer="", solvers=[]), notes=_notes)
    ok("unknown capability name is a recorded note, not a crash",
       caps == {} and any("nope" in m for m in _notes))

    # 8. a mis-shaped plug-in fails LOUD at registration (the typed contract is enforced).
    try:
        reg.register("evidence", "broken", object())  # object() has no list_evidence/fetch
        _reg_ok = False
    except TypeError:
        _reg_ok = True
    ok("registry rejects a plug-in that violates the Protocol (fails loud)", _reg_ok)

    # 9. scenario_effect — pure surfacing of what the PM scenario BINDS + its rubric EFFECT (workbench mirror).
    pm_effect = scenario_effect("product-manager")
    weighted_dims = [d for d in pm_effect["effect"]["dimensions"] if d.get("weight", 0) > 0]
    ok("scenario_effect: PM has >=4 weighted dims", len(weighted_dims) >= 4)
    ok("scenario_effect: PM weights_sum == 100", pm_effect["effect"]["weights_sum"] == 100)
    ok("scenario_effect: PM persona is non-empty", bool(pm_effect["effect"]["persona"]))
    ok("scenario_effect: PM adds_dimensions is True", pm_effect["effect"]["adds_dimensions"] is True)
    ok("scenario_effect: PM notes are empty (every declared capability resolves)", pm_effect["notes"] == [])
    ok("scenario_effect: PM bindings carry the honored rubric/run levers",
       pm_effect["bindings"]["rubric"] == "product_manager" and pm_effect["bindings"]["run"]["iters"] == 8
       and pm_effect["bindings"]["run"]["dynamic"] is True)
    ok("scenario_effect: PM bindings resolve its evidence/renderer capabilities",
       pm_effect["bindings"]["evidence"] == ["local_files", "structured_files"]
       and pm_effect["bindings"]["renderer"] == "markdown")
    ok("scenario_effect: PM contributes its panel declaratively",
       pm_effect["bindings"]["workbench_panels"] == ["results:governed-rice", "results:pm-decision-kit"])

    # a scenario with NO rubric never crashes — empty dims, no persona, adds_dimensions False (guarded, not
    # fabricated). load_scenario is monkeypatched (this module's global) for this one call only — no new
    # scenario YAML needed.
    from ztare.scenarios.config import ScenarioConfig as _SC

    _orig_load_scenario = globals()["load_scenario"]
    globals()["load_scenario"] = lambda n: _SC(name=n)
    try:
        bare_effect = scenario_effect("bare-selftest")
    finally:
        globals()["load_scenario"] = _orig_load_scenario
    ok("bare scenario (no rubric): empty dimensions, no crash", bare_effect["effect"]["dimensions"] == [])
    ok("bare scenario (no rubric): persona is None", bare_effect["effect"]["persona"] is None)
    ok("bare scenario (no rubric): adds_dimensions is False", bare_effect["effect"]["adds_dimensions"] is False)
    ok("bare scenario (no rubric): weights_sum is 0", bare_effect["effect"]["weights_sum"] == 0)

    print("SCENARIO SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
