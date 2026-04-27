#!/usr/bin/env python3
"""META-GATE 2A — static scope-narrowing linter for gate / diagnostic /
orchestrator code.

Catches the gp163d-class blind spot at the SOURCE level: a function whose
parameter list mentions a partition pair (visible / withheld, visible /
holdout, visible / farther_tail, etc.) but whose body iterates only one
of them — silently leaving the other partition unscanned.

The motivating bug. R13's `_detect_dimensionality_collapse(summary,
visible_classes, ...)` had a body that walked `for cls in visible_classes`
only. Within-withheld-class collapses were invisible to the apparatus
until the R26 runtime gate caught it. This linter is the STATIC twin of
R26: catch the same shape before it ships.

Heuristic stack:

  HIGH  — function accepts a complete partition PAIR (e.g., visible_X
          AND withheld_X) but the for-loop bodies iterate only one side
          when the partition vocabulary suggests symmetric coverage.
          Same severity also applies to subscript patterns
          `summary[visible_class]` without the matching
          `summary[withheld_class]` access.

  MEDIUM — function accepts a single partition parameter, but the
           docstring mentions multiple partition concepts (suggesting
           the author had broader coverage in mind than the code
           implements).

  LOW   — ambiguous: partition vocabulary appears in args but no
          for-loops iterate any of them (often a passthrough). Surfaced
          for review, not for correction.

Escape hatch: any function with a `# scope-linter: skip` comment in its
body or immediately preceding its def line is excluded from findings.

Test fixture: an embedded synthetic AST mirroring the OLD shape of
`_detect_dimensionality_collapse` (visible-only loop with both
visible_classes and withheld_classes in args) is exercised in
`--self-test` mode to confirm the linter flags the historical bug.

Usage:
    python scripts/audit_gate_coverage.py
    python scripts/audit_gate_coverage.py --strict     # exit 1 on HIGH
    python scripts/audit_gate_coverage.py --json
    python scripts/audit_gate_coverage.py --self-test  # fixture check

Exit codes:
    0 — default (informational), or strict with no HIGH findings
    1 — strict mode and at least one HIGH finding (or self-test failed)
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]

SCAN_DIRS = [
    REPO_ROOT / "src" / "ztare" / "diagnostics",
    REPO_ROOT / "src" / "ztare" / "gates",
    REPO_ROOT / "src" / "ztare" / "orchestrator",
]

# Files to skip even if they live under SCAN_DIRS. __init__, fixtures,
# smoke tests, and any file whose name advertises that it isn't gate logic.
SKIP_FILE_SUFFIXES = (
    "__init__.py",
    "_fixture_regression.py",
    "_smoke.py",
)
SKIP_FILE_NAMES = {
    "tests",
}

# Partition vocabulary — names whose appearance in arg lists or for-loop
# targets the linter treats as "partition reference."
PARTITION_TOKENS = {
    "visible_classes",
    "withheld_classes",
    "holdout_classes",
    "holdout",
    "farther_tail",
    "farther_tail_classes",
    "farther_tail_data",
    "farther_tail_rows",
    "honest_null",
    "honest_null_rows",
    "visible_features",
    "farther_features",
    "withheld_features",
    "holdout_features",
    "visible_rows",
    "withheld_rows",
    "holdout_rows",
    "visible_pairs",
    "withheld_pairs",
    "visible_data",
    "withheld_data",
    "visible_class",
    "withheld_class",
    "visible_keys",
    "withheld_keys",
    "visible_summary",
    "withheld_summary",
}

# Partition pairs — when the linter sees BOTH sides of a pair in the arg
# list, it expects symmetric iteration in the body. The first element is
# the "visible-side" canonical name; the second is its missing twin.
PARTITION_PAIRS = [
    ("visible_classes", "withheld_classes"),
    ("visible_classes", "holdout_classes"),
    ("visible_classes", "farther_tail_classes"),
    ("visible_features", "withheld_features"),
    ("visible_features", "holdout_features"),
    ("visible_features", "farther_features"),
    ("visible_rows", "withheld_rows"),
    ("visible_rows", "holdout_rows"),
    ("visible_data", "withheld_data"),
    ("visible_data", "farther_tail_data"),
    ("visible_pairs", "withheld_pairs"),
    ("visible_class", "withheld_class"),
    ("visible_summary", "withheld_summary"),
]

# Docstring keywords that, in a single-partition function, suggest the
# author intended broader coverage than the code implements.
DOCSTRING_PARTITION_HINTS = (
    "withheld",
    "holdout",
    "farther tail",
    "farther-tail",
    "honest null",
    "honest_null",
    "cross-class",
    "cross class",
    "both classes",
    "both partitions",
)

SKIP_COMMENT = "scope-linter: skip"


# ── data ───────────────────────────────────────────────────────────────


@dataclass
class Finding:
    file: str
    function: str
    line: int
    severity: str  # "HIGH" | "MEDIUM" | "LOW"
    accepts_partitions: list[str] = field(default_factory=list)
    iterates_partitions: list[str] = field(default_factory=list)
    subscripted_partitions: list[str] = field(default_factory=list)
    missing_partitions: list[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ── helpers ────────────────────────────────────────────────────────────


def _should_skip_file(path: Path) -> bool:
    name = path.name
    if any(name.endswith(suf) for suf in SKIP_FILE_SUFFIXES):
        return True
    if name in SKIP_FILE_NAMES:
        return True
    return False


def _iter_source_files() -> Iterable[Path]:
    for root in SCAN_DIRS:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.py")):
            if _should_skip_file(p):
                continue
            # Skip nested tests/ dirs
            if "tests" in p.parts[len(REPO_ROOT.parts):]:
                continue
            yield p


def _arg_names(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    names: list[str] = []
    a = func.args
    for arg in (a.posonlyargs or []) + a.args + (a.kwonlyargs or []):
        names.append(arg.arg)
    if a.vararg:
        names.append(a.vararg.arg)
    if a.kwarg:
        names.append(a.kwarg.arg)
    return names


def _collect_for_loop_iters(
    func_node: ast.AST,
) -> list[str]:
    """Return the rendered iter-expression of every For loop nested in
    func_node, as a string."""
    out: list[str] = []
    for node in ast.walk(func_node):
        if isinstance(node, (ast.For, ast.AsyncFor)):
            try:
                out.append(ast.unparse(node.iter))
            except Exception:
                out.append("<unparse-failed>")
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for gen in node.generators:
                try:
                    out.append(ast.unparse(gen.iter))
                except Exception:
                    out.append("<unparse-failed>")
    return out


def _collect_subscript_keys(func_node: ast.AST) -> list[str]:
    """Collect rendered keys used in subscripts inside the function body —
    e.g., `summary[visible_class]` → "visible_class". Used to detect the
    asymmetric `summary[visible_class]` / no-`summary[withheld_class]`
    pattern even when there is no for-loop iterating partitions.
    """
    keys: list[str] = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.Subscript):
            sl = node.slice
            try:
                rendered = ast.unparse(sl)
                keys.append(rendered)
            except Exception:
                continue
    return keys


def _has_skip_comment(source: str, func_lineno: int) -> bool:
    """Look for # scope-linter: skip on the def line, the line above,
    or any of the first three lines of the function body."""
    lines = source.splitlines()
    # def line + 1 line above + first 3 body lines
    candidates = []
    for offset in (-1, 0, 1, 2, 3, 4):
        idx = func_lineno - 1 + offset
        if 0 <= idx < len(lines):
            candidates.append(lines[idx])
    return any(SKIP_COMMENT in c for c in candidates)


def _docstring_has_partition_hint(func: ast.FunctionDef | ast.AsyncFunctionDef) -> Optional[str]:
    doc = ast.get_docstring(func) or ""
    low = doc.lower()
    for hint in DOCSTRING_PARTITION_HINTS:
        if hint in low:
            return hint
    return None


def _partition_tokens_in(text: str) -> set[str]:
    found: set[str] = set()
    for tok in PARTITION_TOKENS:
        # naive substring sufficient — partition tokens are distinctive
        if tok in text:
            found.add(tok)
    return found


def _partition_subscript_hits(keys: list[str]) -> set[str]:
    """Detect partition tokens used as subscript keys.
    e.g., `cls in visible_classes` rendered as iter "visible_classes" is
    handled in iter analysis; here we look at things like
    `summary[visible_class]` where the key text contains a partition token.
    """
    out: set[str] = set()
    for k in keys:
        for tok in PARTITION_TOKENS:
            if tok in k:
                out.add(tok)
    return out


# ── core analysis ──────────────────────────────────────────────────────


def analyze_function(
    file_path: Path,
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    source: str,
) -> Optional[Finding]:
    if _has_skip_comment(source, func.lineno):
        return None

    args = _arg_names(func)
    arg_partitions = [a for a in args if a in PARTITION_TOKENS]

    iter_exprs = _collect_for_loop_iters(func)
    iterated_tokens: set[str] = set()
    for expr in iter_exprs:
        iterated_tokens |= _partition_tokens_in(expr)

    subscript_keys = _collect_subscript_keys(func)
    subscripted_tokens = _partition_subscript_hits(subscript_keys)

    docstring_hint = _docstring_has_partition_hint(func)

    # If function has no partition signal at all — skip
    if (
        not arg_partitions
        and not iterated_tokens
        and not subscripted_tokens
    ):
        return None

    # ── HIGH severity: complete partition pair accepted but only one side
    # iterated/subscripted ────────────────────────────────────────────
    accepts_set = set(arg_partitions)
    for vis_tok, with_tok in PARTITION_PAIRS:
        if vis_tok in accepts_set and with_tok in accepts_set:
            # Both sides declared. Check coverage in body.
            vis_used = (
                vis_tok in iterated_tokens
                or vis_tok in subscripted_tokens
                or any(
                    vis_tok.replace("_classes", "_class") in k
                    or vis_tok.replace("_features", "_feature") in k
                    or vis_tok.replace("_rows", "_row") in k
                    for k in subscript_keys
                )
            )
            with_used = (
                with_tok in iterated_tokens
                or with_tok in subscripted_tokens
                or any(
                    with_tok.replace("_classes", "_class") in k
                    or with_tok.replace("_features", "_feature") in k
                    or with_tok.replace("_rows", "_row") in k
                    for k in subscript_keys
                )
            )
            if vis_used and not with_used:
                return Finding(
                    file=str(file_path.relative_to(REPO_ROOT)),
                    function=func.name,
                    line=func.lineno,
                    severity="HIGH",
                    accepts_partitions=sorted(arg_partitions),
                    iterates_partitions=sorted(iterated_tokens),
                    subscripted_partitions=sorted(subscripted_tokens),
                    missing_partitions=[with_tok],
                    rationale=(
                        f"function accepts both {vis_tok!r} and "
                        f"{with_tok!r} but body iterates / subscripts "
                        f"only {vis_tok!r}; symmetric coverage is "
                        f"plausible (gp163d pattern)."
                    ),
                )
            if with_used and not vis_used:
                return Finding(
                    file=str(file_path.relative_to(REPO_ROOT)),
                    function=func.name,
                    line=func.lineno,
                    severity="HIGH",
                    accepts_partitions=sorted(arg_partitions),
                    iterates_partitions=sorted(iterated_tokens),
                    subscripted_partitions=sorted(subscripted_tokens),
                    missing_partitions=[vis_tok],
                    rationale=(
                        f"function accepts both {vis_tok!r} and "
                        f"{with_tok!r} but body iterates / subscripts "
                        f"only {with_tok!r}; mirror coverage is "
                        f"plausible (inverse gp163d pattern)."
                    ),
                )

    # ── MEDIUM severity: single-partition function whose docstring hints
    # at broader coverage ──────────────────────────────────────────────
    if docstring_hint and arg_partitions:
        # Only meaningful when args contain only ONE side of any pair
        single_side = True
        for vis_tok, with_tok in PARTITION_PAIRS:
            if vis_tok in accepts_set and with_tok in accepts_set:
                single_side = False
                break
        if single_side:
            # Check if docstring hints at the OTHER side that isn't in args
            mentioned_in_args = {a for a in arg_partitions}
            other_side_hinted = False
            for vis_tok, with_tok in PARTITION_PAIRS:
                if vis_tok in mentioned_in_args and with_tok not in mentioned_in_args:
                    if (
                        with_tok.replace("_", " ") in docstring_hint
                        or any(s in docstring_hint for s in (
                            with_tok.split("_")[0],
                        ))
                    ):
                        other_side_hinted = True
                        break
                if with_tok in mentioned_in_args and vis_tok not in mentioned_in_args:
                    other_side_hinted = True
                    break
            # Even without exact pair match, the generic hint qualifies
            return Finding(
                file=str(file_path.relative_to(REPO_ROOT)),
                function=func.name,
                line=func.lineno,
                severity="MEDIUM",
                accepts_partitions=sorted(arg_partitions),
                iterates_partitions=sorted(iterated_tokens),
                subscripted_partitions=sorted(subscripted_tokens),
                missing_partitions=[],
                rationale=(
                    f"single-partition arg signature but docstring "
                    f"mentions {docstring_hint!r}; review whether the "
                    f"function should accept the other partition too."
                ),
            )

    # ── LOW severity: partition vocabulary appears but no for-loops
    # iterate any of them — could be a pure passthrough or could be a
    # missed scan ─────────────────────────────────────────────────────
    if arg_partitions and not iterated_tokens and not subscripted_tokens:
        return Finding(
            file=str(file_path.relative_to(REPO_ROOT)),
            function=func.name,
            line=func.lineno,
            severity="LOW",
            accepts_partitions=sorted(arg_partitions),
            iterates_partitions=[],
            subscripted_partitions=[],
            missing_partitions=[],
            rationale=(
                "function accepts partition arg(s) but neither iterates "
                "nor subscripts any partition vocabulary; ambiguous — "
                "may be a passthrough or a missed scan."
            ),
        )

    return None


def analyze_file(path: Path) -> list[Finding]:
    try:
        source = path.read_text(encoding="utf-8")
    except Exception:
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            f = analyze_function(path, node, source)
            if f is not None:
                findings.append(f)
    return findings


def run_audit() -> list[Finding]:
    all_findings: list[Finding] = []
    for path in _iter_source_files():
        all_findings.extend(analyze_file(path))
    return all_findings


# ── self-test fixture ─────────────────────────────────────────────────


_FIXTURE_OLD_SHAPE = '''
def _detect_dimensionality_collapse(
    summary,
    visible_classes,
    withheld_classes,
    rel_threshold=0.02,
):
    """Flag features whose within-visible-class relative range is below
    threshold. Withheld classes are accepted for cross-class signaling."""
    collapses = []
    for cls in visible_classes:
        per_feat = summary.get(cls, {})
        for fk, s in per_feat.items():
            if s["max"] - s["min"] < rel_threshold:
                collapses.append({"class": cls, "feature_key": fk})
    return collapses
'''

_FIXTURE_LEGITIMATE_SINGLE_PARTITION = '''
def _fit_visible_only(visible_rows, params):
    """Fit a model to visible_rows. Holdout / withheld is excluded by
    design — the visible-only fit is the apparatus's in-distribution
    estimate; cross-class extrapolation is tested elsewhere via R26.
    # scope-linter: skip
    """
    out = []
    for row in visible_rows:
        out.append(row)
    return out
'''


def run_self_test() -> int:
    """Exercise the linter on two embedded fixtures.

    1. The OLD shape of `_detect_dimensionality_collapse` MUST be flagged HIGH.
    2. The legitimate single-partition fixture (with skip comment) must NOT be flagged.
    """
    print("META-GATE 2A self-test")
    print("=" * 60)
    rc = 0

    # Fixture 1 — historical bug shape, must be flagged HIGH
    tmp1 = REPO_ROOT / "scripts" / "_audit_gate_coverage_fixture_old.py"
    tmp1.write_text(_FIXTURE_OLD_SHAPE, encoding="utf-8")
    try:
        findings = analyze_file(tmp1)
        high = [f for f in findings if f.severity == "HIGH"]
        if high and any(f.function == "_detect_dimensionality_collapse" for f in high):
            print("  [PASS] historical _detect_dimensionality_collapse shape flagged HIGH")
            for f in high:
                print(f"         missing_partitions={f.missing_partitions}")
        else:
            print("  [FAIL] historical _detect_dimensionality_collapse shape NOT flagged HIGH")
            print(f"         findings={[f.to_dict() for f in findings]}")
            rc = 1
    finally:
        try:
            tmp1.unlink()
        except Exception:
            pass

    # Fixture 2 — legitimate visible-only with skip comment, must NOT be flagged
    tmp2 = REPO_ROOT / "scripts" / "_audit_gate_coverage_fixture_legit.py"
    tmp2.write_text(_FIXTURE_LEGITIMATE_SINGLE_PARTITION, encoding="utf-8")
    try:
        findings = analyze_file(tmp2)
        if not findings:
            print("  [PASS] legitimate visible-only with skip comment NOT flagged")
        else:
            print("  [FAIL] legitimate visible-only with skip comment was flagged")
            print(f"         findings={[f.to_dict() for f in findings]}")
            rc = 1
    finally:
        try:
            tmp2.unlink()
        except Exception:
            pass

    return rc


# ── reporting ──────────────────────────────────────────────────────────


def print_human_report(findings: list[Finding]) -> None:
    by_sev = {"HIGH": [], "MEDIUM": [], "LOW": []}
    for f in findings:
        by_sev.setdefault(f.severity, []).append(f)
    print("=" * 78)
    print("META-GATE 2A — Static Scope-Narrowing Linter")
    print("=" * 78)
    print(
        f"Scanned dirs: {[str(d.relative_to(REPO_ROOT)) for d in SCAN_DIRS]}"
    )
    print(
        f"Findings: HIGH={len(by_sev['HIGH'])} "
        f"MEDIUM={len(by_sev['MEDIUM'])} "
        f"LOW={len(by_sev['LOW'])}"
    )
    print()
    for sev in ("HIGH", "MEDIUM", "LOW"):
        items = by_sev.get(sev, [])
        if not items:
            continue
        print(f"── {sev} ({len(items)}) " + "─" * (60 - len(sev)))
        for f in items:
            print(f"  {f.file}:{f.line}  {f.function}")
            print(f"    accepts:    {f.accepts_partitions}")
            print(f"    iterates:   {f.iterates_partitions}")
            if f.subscripted_partitions:
                print(f"    subscripts: {f.subscripted_partitions}")
            if f.missing_partitions:
                print(f"    missing:    {f.missing_partitions}")
            print(f"    rationale:  {f.rationale}")
            print()
    if not findings:
        print("No findings — gate / diagnostic / orchestrator code "
              "appears symmetric on partition coverage.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any HIGH-severity findings")
    ap.add_argument("--json", action="store_true",
                    help="emit findings as JSON to stdout")
    ap.add_argument("--self-test", action="store_true",
                    help="run the embedded fixture self-test and exit")
    args = ap.parse_args()

    if args.self_test:
        return run_self_test()

    findings = run_audit()

    if args.json:
        payload = {
            "schema": "meta-gate-2a-v1",
            "scanned_dirs": [str(d.relative_to(REPO_ROOT)) for d in SCAN_DIRS],
            "n_findings": len(findings),
            "by_severity": {
                "HIGH": sum(1 for f in findings if f.severity == "HIGH"),
                "MEDIUM": sum(1 for f in findings if f.severity == "MEDIUM"),
                "LOW": sum(1 for f in findings if f.severity == "LOW"),
            },
            "findings": [f.to_dict() for f in findings],
        }
        print(json.dumps(payload, indent=2))
    else:
        print_human_report(findings)

    if args.strict and any(f.severity == "HIGH" for f in findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
