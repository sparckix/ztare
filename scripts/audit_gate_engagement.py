#!/usr/bin/env python3
"""GP-157 — Gate engagement audit (`make gates` backend).

Surfaces the apparatus's hidden-state problem: which gates in
`src/ztare/gates/` are LIVE (wired into autoresearch_loop.py / called
in production) vs DORMANT (shipped code that nothing invokes)?

Output table format:
    name                          state        substrate_class       wire_in
    -----------------------------------------------------------------------
    circularity_gate              LIVE         all                   line 3437 (sbe='gate'/'both')
    wasserstein_persistence_gate  DORMANT      time_series_chaotic   <not called>
    ...

Usage:
    python scripts/audit_gate_engagement.py
    python scripts/audit_gate_engagement.py --json    # machine-readable
    python scripts/audit_gate_engagement.py --strict  # exit 1 if any DORMANT

This is a temporary tool — the long-term fix is the Cage Orchestrator
(GP-157), which makes dormancy structurally impossible by replacing
hardcoded if-block wiring with substrate-class predicate dispatch.
Until v5.0 ships, run `make gates` to surface apparatus debt.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GATES_DIR = REPO_ROOT / "src" / "ztare" / "gates"
LOOP_PATH = REPO_ROOT / "src" / "ztare" / "validator" / "autoresearch_loop.py"


# Hand-curated substrate-class targeting for each gate. Source: spec docs +
# GP-148 mining + 2026-04-25 audit. When a new gate ships, add its row here
# until the Cage Orchestrator's can_handle predicate replaces this map.
GATE_SUBSTRATE_CLASS: dict[str, tuple[str, ...]] = {
    "circularity_gate":              ("all",),
    "falsifiability_gate":           ("all",),
    "global_gates":                  ("all",),     # aggregator; runs always
    "structural_constraint_extractor": ("all",),
    "negative_space_extractor":      ("all",),
    "derived_constraints":           ("all",),
    "corrector_library":             ("all",),
    "deterministic_charter_gates":   ("1d_curve", "feature_dict"),
    "wasserstein_persistence_gate":  ("time_series_chaotic",),
    "ansatz_survivor_gate":          ("proof_target",),       # GP-144 G3
    "proof_surveyability_gate":      ("proof_target",),       # GP-144 G4
    "translation_diff_gate":         ("proof_target",),       # GP-144 G5
    "continuum_limit_gate":          ("time_series_chaotic", "1d_curve"),
    "coordinate_invariance_gate":    ("1d_curve",),
    "ensemble_ambiguity_gate":       ("feature_dict",),
    "prompt_leak_audit":             ("meta_audit",),
    "pslq_falsity_audit_gate":       ("closed_form_constant",),
    "semantic_gate_stabilization":   ("all",),
    "asymptotic_claim_discipline":   ("1d_curve", "feature_dict"),
    "bridge_scope_contract":         ("all",),
    "domain_match_gate":             ("feature_dict",),
    "residual_norm":                 ("1d_curve",),
}


# Substrate classes recognised today. New classes added here must be
# documented in research_areas/private/seams/GP-157_*.md taxonomy.
KNOWN_SUBSTRATE_CLASSES = (
    "1d_curve",
    "feature_dict",
    "feature_dict_categorical",
    "closed_form_constant",
    "time_series_chaotic",
    "proof_target",
    "meta_audit",
    "all",
)


@dataclass
class GateRecord:
    name: str
    file: str
    file_size_bytes: int
    state: str  # "LIVE" | "DORMANT" | "AGGREGATOR"
    substrate_class: tuple[str, ...]
    wire_in: str   # description of where it's called from autoresearch_loop
    has_smoke_test: bool
    has_fixture: bool


def _list_gate_modules() -> list[Path]:
    """Return every gate module in gates/ that is NOT a smoke test or fixture."""
    if not GATES_DIR.is_dir():
        return []
    out = []
    for p in sorted(GATES_DIR.iterdir()):
        if p.suffix != ".py":
            continue
        if p.name in ("__init__.py",):
            continue
        if p.name.endswith("_smoke.py"):
            continue
        if p.name.endswith("_fixture_regression.py"):
            continue
        out.append(p)
    return out


def _has_companion(gate_path: Path, suffix: str) -> bool:
    return (gate_path.parent / f"{gate_path.stem}{suffix}.py").is_file()


def _scan_cage_routed_registrations() -> dict[str, str]:
    """Task #153: Cage-routed gates register via register_*_gates(instance)
    calls in src/ztare/orchestrator/state.py::build_cage_runtime, NOT via
    direct autoresearch_loop imports. Without this scanner, the audit
    reports them as DORMANT despite being properly wired.

    Returns {gate_module_name: wire_in_description} for every gate file
    that exports a register_*_gate(s) function called from state.py.
    """
    state_path = REPO_ROOT / "src" / "ztare" / "orchestrator" / "state.py"
    if not state_path.is_file():
        return {}
    state_text = state_path.read_text(errors="ignore")
    out: dict[str, str] = {}
    # Match: from src.ztare.gates.<module> import register_*
    for m in re.finditer(
        r"from\s+src\.ztare\.gates\.(\w+)\s+import\s+\(?\s*(register_\w+)",
        state_text,
    ):
        mod = m.group(1)
        fn = m.group(2)
        out[mod] = f"Cage-routed registration: state.py calls {fn}() in build_cage_runtime"
    # Some gates self-register from src/ztare/diagnostics or src/ztare/fit
    # (per task #151 backport); those land in state.py too.
    for m in re.finditer(
        r"from\s+src\.ztare\.(?:diagnostics|fit|framer)\.(\w+)\s+import\s+\(?\s*(register_\w+)",
        state_text,
    ):
        mod = m.group(1)
        fn = m.group(2)
        out[mod] = f"Cage-routed (cross-package): state.py calls {fn}() in build_cage_runtime"
    return out


def _scan_loop_imports() -> dict[str, str]:
    """Return {gate_module_name: wire_in_description} for every gate that
    autoresearch_loop.py imports OR calls explicitly OR is registered via
    Cage in state.py (task #153 — Cage-routed gates were previously
    invisible to this auditor)."""
    wired: dict[str, str] = dict(_scan_cage_routed_registrations())
    if not LOOP_PATH.is_file():
        return wired
    text = LOOP_PATH.read_text(errors="ignore")
    # Pattern A: top-level imports (single-line OR multi-line with parens)
    # Single-line: from src.ztare.gates.X import a, b, c
    # Multi-line:  from src.ztare.gates.X import (\n    a,\n    b,\n)
    for m in re.finditer(
        r"^from\s+src\.ztare\.gates\.(\w+)\s+import\s+(\([^)]*\)|[\w, ]+)",
        text, re.MULTILINE,
    ):
        mod = m.group(1)
        symbols = re.sub(r"[\s()]+", " ", m.group(2)).strip()
        wired[mod] = f"top-level import: {symbols[:80]}"
    # Pattern B: in-block / indented imports
    for m in re.finditer(
        r"^\s+from\s+src\.ztare\.gates\.(\w+)\s+import\s+(\([^)]*\)|[\w, ]+)",
        text,
        re.MULTILINE,
    ):
        mod = m.group(1)
        if mod in wired:
            continue
        # Find the if-block context for this import
        line_no = text[: m.start()].count("\n") + 1
        # Look backward for an `if` line within ~20 lines
        before = text[max(0, m.start() - 1500):m.start()].split("\n")
        ctx = ""
        for ln in reversed(before):
            ln_stripped = ln.strip()
            if ln_stripped.startswith("if ") and ":" in ln_stripped:
                ctx = ln_stripped[:120]
                break
        wired[mod] = f"conditional import (line ~{line_no}, context: {ctx or '?'})"
    return wired


def _audit() -> list[GateRecord]:
    wired = _scan_loop_imports()
    records: list[GateRecord] = []
    for gate_path in _list_gate_modules():
        name = gate_path.stem
        substrate = GATE_SUBSTRATE_CLASS.get(name, ("UNKNOWN",))
        if name in wired:
            wire_desc = wired[name]
            # Task #153: distinguish Cage-routed LIVE from direct-wire LIVE.
            # Cage-routed gates self-register via state.py and dispatch
            # through can_handle predicates — that's the right architecture.
            if "Cage-routed" in wire_desc:
                state = "CAGE_ROUTED"
            else:
                state = "LIVE"
        else:
            # Check if the gate module is called via an aggregator
            # (e.g., listed inside global_gates.py). Aggregator membership
            # = LIVE-via-aggregator. Today only global_gates aggregates.
            if name in ("global_gates",):
                state = "AGGREGATOR"
                wire_desc = "aggregator entry point"
            else:
                # Special case: gate is referenced by another gate file
                # (rare; today only used by deterministic_charter_gates)
                state = "DORMANT"
                wire_desc = "<not called by autoresearch_loop or registered via Cage>"
        records.append(GateRecord(
            name=name,
            file=str(gate_path.relative_to(REPO_ROOT)),
            file_size_bytes=gate_path.stat().st_size,
            state=state,
            substrate_class=substrate,
            wire_in=wire_desc,
            has_smoke_test=_has_companion(gate_path, "_smoke"),
            has_fixture=_has_companion(gate_path, "_fixture_regression"),
        ))
    return records


def _format_table(records: list[GateRecord]) -> str:
    lines = []
    name_w = max((len(r.name) for r in records), default=20)
    cls_w = max((len(", ".join(r.substrate_class)) for r in records), default=15)
    header = f"{'GATE':<{name_w}}  {'STATE':<10}  {'SUBSTRATE':<{cls_w}}  TESTS  WIRE-IN"
    sep = "-" * (name_w + 12 + cls_w + 8 + 30)
    lines.append(header)
    lines.append(sep)
    # sort: DORMANT first (most urgent), then by name
    sort_key = {"DORMANT": 0, "LIVE": 1, "AGGREGATOR": 2}
    for r in sorted(records, key=lambda x: (sort_key.get(x.state, 99), x.name)):
        tests = []
        if r.has_smoke_test: tests.append("S")
        if r.has_fixture: tests.append("F")
        tests_str = "".join(tests).ljust(5) if tests else "  -  "
        cls = ", ".join(r.substrate_class)
        wire = r.wire_in[:60] + ("…" if len(r.wire_in) > 60 else "")
        marker = "❌" if r.state == "DORMANT" else ("✅" if r.state == "LIVE" else "🔧")
        lines.append(
            f"{marker} {r.name:<{name_w-2}}  {r.state:<10}  {cls:<{cls_w}}  {tests_str}  {wire}"
        )
    lines.append(sep)
    n_live = sum(1 for r in records if r.state == "LIVE")
    n_dormant = sum(1 for r in records if r.state == "DORMANT")
    n_aggr = sum(1 for r in records if r.state == "AGGREGATOR")
    lines.append(
        f"SUMMARY: {n_live} LIVE, {n_dormant} DORMANT, {n_aggr} AGGREGATOR "
        f"(total {len(records)})"
    )
    if n_dormant > 0:
        lines.append("")
        lines.append(
            f"⚠️  {n_dormant} gates are SHIPPED but NOT WIRED into autoresearch_loop.py."
        )
        lines.append(
            "   Each was built for a substrate class we haven't run live recently."
        )
        lines.append(
            "   Long-term fix: GP-157 Cage Orchestrator (substrate-agnostic dispatch)."
        )
        lines.append(
            "   Short-term: review each dormant gate; either wire it or formally retire."
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="Audit gate engagement (GP-157).")
    p.add_argument("--json", action="store_true",
                   help="Emit JSON instead of human-readable table.")
    p.add_argument("--strict", action="store_true",
                   help="Exit 1 if any DORMANT gate (use in CI).")
    args = p.parse_args()

    records = _audit()
    if args.json:
        print(json.dumps([asdict(r) for r in records], indent=2))
    else:
        print(_format_table(records))

    if args.strict and any(r.state == "DORMANT" for r in records):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
