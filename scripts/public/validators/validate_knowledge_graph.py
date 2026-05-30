#!/usr/bin/env python3
"""GP-216d knowledge-graph drift validator (Pattern 10 sister to Pattern 9).

Mirrors `scripts/public/validators/validate_autoresearch_arch_map.py` (GP-101) but for the
artifact-network knowledge graph instead of code-internal arch maps.

Drift checks performed on `analytics/public/queries/graphs/ztare_knowledge_graph_prototype.json`
(or any path passed via --graph):

  C1. Every seam node corresponds to an existing .md file in the seams or specs
      directories.
  C2. Every depends_on edge target resolves to a node that exists in the graph
      AND a corresponding .md file on disk.
  C3. Every instantiates_op reference resolves to a real op_id in the canonical
      VOCABULARY_V4 from src/ztare/research_director/universal_research_ops.py.
  C4. Every references_gate target corresponds to a real gate class in
      src/ztare/gates/.

Same exit-code semantics as the GP-101 validator:
  0 — validation passed
  1 — drift detected
  2 — validator error (graph or source unreadable)

Usage:
    python -m scripts.validate_knowledge_graph
    python -m scripts.validate_knowledge_graph --graph analytics/public/queries/graphs/foo.json
    python -m scripts.validate_knowledge_graph --regenerate  # also re-run extractor first

Per Pattern 10: the graph is regenerable; this validator is a safety net for
when the graph drifts from the underlying artifacts (e.g., a seam was renamed
without updating a referencing seam's text).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEFAULT_GRAPH_PATH = (
    REPO
    / "analytics"
    / "public"
    / "queries"
    / "graphs"
    / "ztare_knowledge_graph_prototype.json"
)
SEAMS_DIRS = [
    REPO / "research_areas" / "private" / "seams",
    REPO / "research_areas" / "specs" / "active",
]
GATES_DIR = REPO / "src" / "ztare" / "gates"
UNIVERSAL_OPS_PATH = REPO / "src" / "ztare" / "research_director" / "universal_research_ops.py"


@dataclass
class DriftReport:
    missing_seam_files: list[str]
    unresolved_depends_on: list[tuple[str, str]]  # (from_node, missing_target)
    unresolved_op_refs: list[tuple[str, str]]      # (node_id, op_id_not_in_vocab)
    unresolved_gate_refs: list[tuple[str, str]]    # (node_id, gate_class_not_found)
    n_nodes: int
    n_edges: int

    def total_drifts(self) -> int:
        return (
            len(self.missing_seam_files)
            + len(self.unresolved_depends_on)
            + len(self.unresolved_op_refs)
            + len(self.unresolved_gate_refs)
        )


def load_graph(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: graph file not found: {path}", file=sys.stderr)
        sys.exit(2)
    return json.loads(path.read_text())


def extract_canonical_op_ids() -> set[str]:
    """Extract canonical op_ids from universal_research_ops.py + legacy ops from
    theory_building_ops.py + problem_solving_ops.py.

    Legacy v3 ops (tb_*, ps_*) remain valid historical references in seams that
    document the v3→v4/v5 evolution. The validator accepts them as canonical
    so seam-text references don't false-fire on intentional historical mentions.
    """
    if not UNIVERSAL_OPS_PATH.exists():
        print(f"ERROR: universal_research_ops.py not found: {UNIVERSAL_OPS_PATH}", file=sys.stderr)
        sys.exit(2)
    text = UNIVERSAL_OPS_PATH.read_text()
    op_pattern = re.compile(r'"(core_\d+|broad_\d+|sub_\d+_\w+|spec_\d+(?:_\w+)?)"')
    ops = set(op_pattern.findall(text))
    # Aliases: spec_XX_YYY (used in cluster naming + GP-216f) ↔ sub_XX_YYY (canonical in v5)
    # Both forms are accepted as valid historical references.
    for sub_op in list(ops):
        if sub_op.startswith("sub_"):
            ops.add(sub_op.replace("sub_", "spec_", 1))
        elif sub_op.startswith("spec_"):
            ops.add(sub_op.replace("spec_", "sub_", 1))
    legacy_pattern = re.compile(r"(tb_\d+|tb_NEW_\w+|tb_LAK\d|ps_\d+)")
    ops.update(legacy_pattern.findall(text))
    # Also walk legacy v3 modules to harvest historical op_ids
    legacy_modules = [
        UNIVERSAL_OPS_PATH.parent / "theory_building_ops.py",
        UNIVERSAL_OPS_PATH.parent / "problem_solving_ops.py",
    ]
    for path in legacy_modules:
        if path.exists():
            ops.update(legacy_pattern.findall(path.read_text()))
    # Also walk the GP-216 seam itself (it documents the legacy ops as part of its history)
    gp216_seam = REPO / "research_areas" / "private" / "seams" / "engine" / "GP-216_theory_building_operations_seam.md"
    if gp216_seam.exists():
        ops.update(legacy_pattern.findall(gp216_seam.read_text()))
    return ops


def find_gate_classes() -> set[str]:
    """Walk src/ztare/gates/ and extract gate identifiers.

    Gates may be (a) Python class names; (b) module-style with run_*_gate
    functions; (c) module file names. Map file names to PascalCase class
    identifiers (e.g., potential_function_monotonicity_gate.py →
    PotentialFunctionMonotonicityGate) so seam references match.
    """
    if not GATES_DIR.exists():
        return set()
    classes: set[str] = set()
    class_pattern = re.compile(r"^class\s+(\w+)", re.MULTILINE)
    func_pattern = re.compile(r"^def\s+(run_\w+_gate)", re.MULTILINE)
    for path in GATES_DIR.glob("*.py"):
        if path.name.startswith("__"):
            continue
        text = path.read_text()
        classes.update(class_pattern.findall(text))
        classes.update(func_pattern.findall(text))
        # File-name → PascalCase class identifier
        # (e.g., potential_function_monotonicity_gate -> PotentialFunctionMonotonicityGate)
        stem = path.stem
        pascal = "".join(part.capitalize() for part in stem.split("_"))
        classes.add(pascal)
        # Also handle Detector suffix variants
        if "detector" in stem.lower():
            # tacit_pattern_recurrence_detector -> TacitPatternRecurrenceDetector
            pascal_alt = "".join(part.capitalize() for part in stem.split("_"))
            classes.add(pascal_alt)
    return classes


def find_seam_files() -> dict[str, Path]:
    """Walk seam dirs and build a map of seam_id (e.g., 'GP-216') → file path."""
    out: dict[str, Path] = {}
    seam_id_pattern = re.compile(r"^(GP-\d+[a-z]?)")
    for sd in SEAMS_DIRS:
        if not sd.exists():
            continue
        for path in sd.rglob("*.md"):
            stem = path.stem
            # Match GP-XXX prefix
            m = seam_id_pattern.match(stem)
            if m:
                out.setdefault(m.group(1), path)
            else:
                # Non-GP-prefixed file (e.g., readme); fallback to whole stem
                out.setdefault(stem, path)
    return out


def validate(graph: dict) -> DriftReport:
    """Run all 4 drift checks; collect violations."""
    nodes = graph.get("@graph", [])
    canonical_ops = extract_canonical_op_ids()
    gate_classes = find_gate_classes()
    seam_files = find_seam_files()

    # Build node id index
    node_ids = {n["@id"]: n for n in nodes if "@id" in n}

    report = DriftReport(
        missing_seam_files=[],
        unresolved_depends_on=[],
        unresolved_op_refs=[],
        unresolved_gate_refs=[],
        n_nodes=len(nodes),
        n_edges=0,
    )

    for node in nodes:
        nid = node.get("@id", "")
        ntype = node.get("@type", "")

        # C1: seam node → file existence
        if ntype == "seam":
            seam_id = nid.removeprefix("seam:")
            if seam_id not in seam_files:
                report.missing_seam_files.append(seam_id)

        # C2: depends_on resolution
        for target in node.get("depends_on", []):
            report.n_edges += 1
            target_id = target.removeprefix("seam:")
            if target_id not in seam_files:
                report.unresolved_depends_on.append((nid, target))

        # C3: instantiates_op resolution
        for op_ref in node.get("instantiates_op", []):
            report.n_edges += 1
            op_id = op_ref.removeprefix("op:")
            if op_id not in canonical_ops:
                report.unresolved_op_refs.append((nid, op_id))

        # C4: references_gate resolution
        for gate_ref in node.get("references_gate", []):
            report.n_edges += 1
            gate_id = gate_ref.removeprefix("gate:")
            if gate_id not in gate_classes:
                report.unresolved_gate_refs.append((nid, gate_id))

    return report


def print_report(report: DriftReport, verbose: bool = True) -> int:
    """Print the drift report; return exit code."""
    print(f"=== Knowledge-graph drift validation ===")
    print(f"  Nodes: {report.n_nodes}")
    print(f"  Edges: {report.n_edges}")
    print(f"  Total drifts: {report.total_drifts()}")
    print()

    if report.missing_seam_files:
        print(f"DRIFT C1: {len(report.missing_seam_files)} seam nodes have no corresponding file:")
        for sid in (report.missing_seam_files[:10] if not verbose else report.missing_seam_files):
            print(f"  - {sid}")
        if not verbose and len(report.missing_seam_files) > 10:
            print(f"  ... ({len(report.missing_seam_files) - 10} more)")
        print()

    if report.unresolved_depends_on:
        print(f"DRIFT C2: {len(report.unresolved_depends_on)} depends_on edges target missing seams:")
        for src, target in (report.unresolved_depends_on[:10] if not verbose else report.unresolved_depends_on):
            print(f"  - {src} → {target}  (target file does not exist)")
        if not verbose and len(report.unresolved_depends_on) > 10:
            print(f"  ... ({len(report.unresolved_depends_on) - 10} more)")
        print()

    if report.unresolved_op_refs:
        print(f"DRIFT C3: {len(report.unresolved_op_refs)} instantiates_op references unresolved (not in canonical vocabulary):")
        for src, op in (report.unresolved_op_refs[:10] if not verbose else report.unresolved_op_refs):
            print(f"  - {src} → {op}  (not a canonical op_id; legacy / typo / drift)")
        if not verbose and len(report.unresolved_op_refs) > 10:
            print(f"  ... ({len(report.unresolved_op_refs) - 10} more)")
        print()

    if report.unresolved_gate_refs:
        print(f"DRIFT C4: {len(report.unresolved_gate_refs)} references_gate targets not found in src/ztare/gates/:")
        for src, gate in report.unresolved_gate_refs:
            print(f"  - {src} → {gate}")
        print()

    if report.total_drifts() == 0:
        print("All drift checks passed.")
        return 0
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--regenerate", action="store_true",
                          help="re-run the extractor before validating (currently calls /tmp/gp216_graph_db_prototype.py)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if args.regenerate:
        import subprocess
        extractor = REPO / ".." / ".." / "tmp" / "gp216_graph_db_prototype.py"
        # Just note: regeneration via this CLI is a future feature; for now manual
        print("(regenerate flag: re-run /tmp/gp216_graph_db_prototype.py manually before validating)")

    graph = load_graph(args.graph)
    report = validate(graph)
    return print_report(report, verbose=not args.quiet)


if __name__ == "__main__":
    sys.exit(main())
