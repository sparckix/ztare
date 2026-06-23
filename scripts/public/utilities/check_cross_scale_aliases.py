#!/usr/bin/env python3
"""GP-216f Item 4 — auto-cross-reference linter.

Checks that documented cross-scale aliases (e.g., `coordinate_compression`
at iteration scale ↔ `core_01 Problem Reformulation` at research scale)
still resolve to existing artifacts. Prevents silent drift across the 7
ZTARE scales when one apparatus is renamed/refactored without updating
the others.

Source of truth: GP-216f's "Rosetta Stone" alias table (this script
encodes a subset of that table; expand as more aliases are documented).

Exit codes:
    0 — all aliases resolve
    1 — drift detected (missing apparatus on one side)
    2 — script error

Same exit-code semantics as validate_autoresearch_arch_map.py (GP-101)
and validate_knowledge_graph.py (GP-216d).
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PIVOT_HEURISTICS = REPO / "src" / "ztare" / "validator" / "utilities" / "pivot_heuristics.py"
FRAMER_PRIMITIVES = REPO / "src" / "ztare" / "framer" / "primitives.py"
UNIVERSAL_OPS = REPO / "src" / "ztare" / "research_director" / "universal_research_ops.py"
REFLEXIVE_DOC = REPO / "docs" / "concepts" / "reflexive_engineering.md"
PATTERNS_DOC = REPO / "docs" / "concepts" / "agentic_engineering_patterns.md"
GATES_DIR = REPO / "src" / "ztare" / "gates"


@dataclass
class Alias:
    """A documented cross-scale alias between artifacts."""
    description: str
    artifacts: list[tuple[str, str]]  # [(scale, identifier), ...]


# Subset of GP-216f's Rosetta Stone alias table. Each Alias documents
# one underlying structural-move and lists the apparatus that enforces
# it across multiple scales.
DOCUMENTED_ALIASES: list[Alias] = [
    Alias(
        description="Translate problem to other domain (core_01 Problem Reformulation)",
        artifacts=[
            ("framer_sigma", "log"),
            ("framer_sigma", "signed_log"),
            ("pivot_module", "coordinate_compression"),
            ("v5_op", "core_01"),
        ],
    ),
    Alias(
        description="Iterate with monotone potential (broad_01 Iterative Refinement)",
        artifacts=[
            ("pivot_module", "failure_topology"),
            ("v5_op", "broad_01"),
            ("gate_class", "PotentialFunctionMonotonicityGate"),
            ("reflexive_primitive", "Reflexive Orchestration"),
        ],
    ),
    Alias(
        description="Decompose into canonical pieces (core_03 Decomposition & Recomposition)",
        artifacts=[
            ("framer_sigma", "power_2"),
            ("pivot_module", "entropy_stripping"),
            ("v5_op", "core_03"),
            ("reflexive_primitive", "Hybrid Persona Router"),
        ],
    ),
    Alias(
        description="Reduce to extremal case (broad_05 Extremal Method)",
        artifacts=[
            ("framer_sigma", "reciprocal"),
            ("pivot_module", "fixed_point_scan"),
            ("pivot_module", "inversion"),
            ("v5_op", "broad_05"),
            ("gate_class", "StagnationSpecialCaseHintGate"),
            ("reflexive_primitive", "Inception"),
        ],
    ),
    Alias(
        description="Import external framework (core_06 Cross-Domain Translation)",
        artifacts=[
            ("framer_sigma", "arctan"),
            ("pivot_module", "interface_discipline"),
            ("v5_op", "core_06"),
            ("gate_class", "BoundChainConsistencyGate"),
            ("reflexive_primitive", "Operator-Replay Mechanization"),
        ],
    ),
    Alias(
        description="Generalize / abstract (core_02 Generalization & Abstraction)",
        artifacts=[
            ("framer_sigma", "signed_log"),
            ("framer_sigma", "softplus"),
            ("pivot_module", "dimensional_shift"),
            ("pivot_module", "category_switch"),
            ("v5_op", "core_02"),
            ("reflexive_primitive", "Token-Optimized Self-Modeling"),
            ("reflexive_primitive", "Research Taste Router"),
        ],
    ),
]


def _read(path: Path) -> str:
    if not path.exists():
        print(f"ERROR: missing source: {path}", file=sys.stderr)
        sys.exit(2)
    return path.read_text()


def check_artifact(scale: str, identifier: str) -> bool:
    """Return True if the artifact identifier exists in the relevant source."""
    if scale == "framer_sigma":
        text = _read(FRAMER_PRIMITIVES)
        # Search for `"identifier":` as dict key in SIGMA registry
        return bool(re.search(rf'\"{re.escape(identifier)}\"\s*:', text))

    if scale == "pivot_module":
        text = _read(PIVOT_HEURISTICS)
        # Search for `"identifier":` as dict key in MODULE_TEXT
        return bool(re.search(rf'\"{re.escape(identifier)}\"\s*:', text))

    if scale == "v5_op":
        text = _read(UNIVERSAL_OPS)
        # Search for `"identifier":` as VOCABULARY_V4 key
        return bool(re.search(rf'\"{re.escape(identifier)}\"\s*:', text))

    if scale == "gate_class":
        if not GATES_DIR.exists():
            return False
        # Gates may be classes OR modules (filename -> PascalCase class name).
        # Map identifier (PascalCase) to expected file name (snake_case).
        snake = re.sub(r'(?<!^)(?=[A-Z])', '_', identifier).lower()
        expected_path = GATES_DIR / f"{snake}.py"
        if expected_path.exists():
            return True
        # Fallback: search all gate files for the class name OR the function name
        for path in GATES_DIR.glob("*.py"):
            text = path.read_text()
            if re.search(rf'\bclass\s+{re.escape(identifier)}\b', text):
                return True
            if re.search(rf'\bdef\s+{re.escape(identifier)}\b', text):
                return True
        return False

    if scale == "reflexive_primitive":
        text = _read(REFLEXIVE_DOC)
        # Heading format: "## Primitive N: Identifier (...)" — match prefix substring
        # Identifier may have a parenthetical, so match identifier as substring of heading line
        for m in re.finditer(r'## Primitive \d+:\s*(.+?)$', text, re.MULTILINE):
            heading_body = m.group(1).strip()
            if heading_body.startswith(identifier):
                return True
        return False

    if scale == "agentic_pattern":
        text = _read(PATTERNS_DOC)
        # Look for `### Pattern N — Identifier`
        return bool(re.search(rf'### Pattern \d+\s*[—\-]\s*{re.escape(identifier)}', text))

    return False


def main() -> int:
    print("=== Cross-scale alias linter ===\n")
    total_artifacts = 0
    missing: list[tuple[str, str, str]] = []  # (alias_desc, scale, identifier)

    for alias in DOCUMENTED_ALIASES:
        print(f"Checking alias: {alias.description}")
        for scale, ident in alias.artifacts:
            total_artifacts += 1
            ok = check_artifact(scale, ident)
            mark = "✓" if ok else "✗"
            print(f"  {mark} {scale}={ident}")
            if not ok:
                missing.append((alias.description, scale, ident))
        print()

    print("=" * 60)
    print(f"Total artifacts checked: {total_artifacts}")
    print(f"Missing artifacts: {len(missing)}")

    if missing:
        print("\nDRIFT DETECTED:")
        for desc, scale, ident in missing:
            print(f"  - alias '{desc[:50]}': {scale}={ident} not found")
        print("\nFix: either restore the missing apparatus, or update DOCUMENTED_ALIASES")
        print("in this script + GP-216f's Rosetta Stone table to reflect the rename.")
        return 1

    print("\nAll documented cross-scale aliases resolve. No drift.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
