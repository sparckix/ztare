"""G-FALSIFY — deterministic unfalsifiability detector.

A thesis is unfalsifiable when no operational test exists that could
distinguish it from rival explanations. Per the ZTARE anti-pattern
catalog (Part 1 SB-3), this is a structural blocker: without a concrete
observable whose value would falsify the claim, the thesis has no
epistemic content.

This gate replaces the LLM-taxonomy-based `unfalsifiable_claim` injection
from `inject_antipattern_catalog: "hardkill"` with a deterministic
check across three channels:

  1. test_model.py — must contain ≥ 1 numeric-threshold assertion
     (e.g., `assert max_err < 1e-6` or `assert x != 0`).
  2. probability_dag.json — must have ≥ 1 node with a non-empty
     watch_signal string (the DAG-level discriminator).
  3. thesis.md (optional) — must contain a named rival hypothesis
     section OR explicit discriminator declaration.

Channel 1 is MANDATORY (hard fail if zero). Channels 2 and 3 are
ADVISORY: if ≥ 1 is present alongside (1), gate passes; if only (1)
is present, gate passes with a "weak_falsifier" note. If (1) fails,
gate fails.

Scope
-----
- Catches: theses without numeric-threshold tests (placeholder stubs,
  pure hand-wave prose, empty assertions).
- Does NOT catch: a thesis that has well-formatted assertions but
  whose assertions are tautological (`assert 1 == 1`). That requires
  a semantic pass (still out of scope for a deterministic gate; the
  judge catches it).

Usage
-----
  from src.ztare.gates.falsifiability_gate import run_falsifiability_gate
  result = run_falsifiability_gate(
      test_model_path=Path("projects/foo/test_model.py"),
      probability_dag_path=Path("projects/foo/champion_probability_dag.json"),
      thesis_md_path=Path("projects/foo/thesis.md"),
  )
  if not result["passed"]:
      # Dispatch as structural blocker; score → 0
      ...
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any


GATE_ID = "G-FALSIFY"
GATE_NAME = "falsifiability_gate"

# Minimum number of numeric-threshold assertions required in test_model.py.
# One is sufficient: the discriminator question is "does ANY observable
# threshold exist?" not "how many?".
MIN_NUMERIC_ASSERTIONS = 1

# Regex patterns for thesis.md advisory checks
_RIVAL_PATTERNS = [
    r"rival\s+hypothes",
    r"alternative\s+(?:explanation|hypothes)",
    r"counter\s*factual",
    r"null\s+hypothes",
    r"competing\s+(?:theory|explanation)",
]
_DISCRIMINATOR_PATTERNS = [
    r"named\s+discriminator",
    r"discriminator\s*[:=]",
    r"observable\s*[:=]",
    r"forward\s+observable",
    r"falsifier\s*[:=]",
    r"fail.*?(?:threshold|if)",
]


def _count_numeric_assertions(src: str) -> int:
    """Count `assert` statements whose test is a Compare with at least
    one numeric literal comparator. Conservative: excludes `assert x`
    (bare identifier, no threshold) and `assert f(y)` (function call
    without comparison).
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return 0
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        test = node.test
        if isinstance(test, ast.Compare):
            # Numeric threshold check: any comparator is a numeric constant
            for c in test.comparators:
                if isinstance(c, ast.Constant) and isinstance(c.value, (int, float)):
                    count += 1
                    break
                # Allow math.inf / math.nan / similar module attributes
                if isinstance(c, ast.Attribute) and isinstance(c.value, ast.Name):
                    if c.value.id in ("math", "np", "numpy"):
                        count += 1
                        break
                # Also allow numeric arithmetic like `1e-6` as BinOp
                if isinstance(c, ast.BinOp):
                    count += 1
                    break
            continue
        # Also count explicit assertions like `assert abs(x) < tol` where the
        # outer form is Compare — handled above. Conservative: don't count
        # `assert isinstance(x, T)` or `assert hasattr(...)`.
    return count


def _has_any_pattern(text: str, patterns: list[str]) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(re.search(p, lowered) for p in patterns)


def _dag_has_watch_signal(probability_dag_path: Path) -> tuple[bool, int]:
    """(has_any_watch_signal, num_nodes_with_watch). Silent degradation."""
    if not probability_dag_path.is_file():
        return (False, 0)
    try:
        dag = json.loads(probability_dag_path.read_text())
    except json.JSONDecodeError:
        return (False, 0)
    nodes = dag.get("nodes", []) or []
    watched = [n for n in nodes if str(n.get("watch_signal") or "").strip()]
    return (len(watched) > 0, len(watched))


def run_falsifiability_gate(
    test_model_path: Path | str,
    probability_dag_path: Path | str | None = None,
    thesis_md_path: Path | str | None = None,
) -> dict[str, Any]:
    """Run the falsifiability gate.

    Channel 1 (mandatory): test_model.py numeric-threshold assertion count.
    Channel 2 (advisory):  probability_dag.json watch_signal presence.
    Channel 3 (advisory):  thesis.md rival / discriminator section.

    Returns dict with: gate_id, passed, n_numeric_assertions,
    dag_has_watch_signal, n_watch_signals, thesis_has_rival,
    thesis_has_discriminator, rationale, strength.

    strength ∈ {"strong", "weak", "none"}:
      strong — channel 1 ≥ MIN AND at least one of channels 2/3.
      weak   — channel 1 ≥ MIN, but both channels 2 and 3 are absent.
      none   — channel 1 fails; gate fails.
    """
    t_path = Path(test_model_path)
    result: dict[str, Any] = {
        "gate_id": GATE_ID,
        "passed": False,
        "n_numeric_assertions": 0,
        "dag_has_watch_signal": False,
        "n_watch_signals": 0,
        "thesis_has_rival": False,
        "thesis_has_discriminator": False,
        "rationale": "",
        "strength": "none",
    }

    # Channel 1: test_model.py numeric assertions
    if not t_path.is_file():
        result["rationale"] = f"test_model.py not found: {t_path}"
        result["error"] = "FileNotFoundError"
        return result
    try:
        src = t_path.read_text()
    except Exception as exc:
        result["rationale"] = f"test_model.py unreadable: {exc}"
        result["error"] = type(exc).__name__
        return result
    n_asserts = _count_numeric_assertions(src)
    result["n_numeric_assertions"] = n_asserts

    # Channel 2: DAG watch_signal
    if probability_dag_path is not None:
        has_ws, n_ws = _dag_has_watch_signal(Path(probability_dag_path))
        result["dag_has_watch_signal"] = has_ws
        result["n_watch_signals"] = n_ws

    # Channel 3: thesis.md rival/discriminator
    if thesis_md_path is not None:
        t_md = Path(thesis_md_path)
        thesis_text = t_md.read_text() if t_md.is_file() else ""
        result["thesis_has_rival"] = _has_any_pattern(thesis_text, _RIVAL_PATTERNS)
        result["thesis_has_discriminator"] = _has_any_pattern(thesis_text, _DISCRIMINATOR_PATTERNS)

    # Verdict
    channel_1_ok = n_asserts >= MIN_NUMERIC_ASSERTIONS
    channel_2_ok = result["dag_has_watch_signal"]
    channel_3_ok = result["thesis_has_rival"] or result["thesis_has_discriminator"]

    if not channel_1_ok:
        result["passed"] = False
        result["strength"] = "none"
        result["rationale"] = (
            f"test_model.py has 0 numeric-threshold assertions "
            f"(required ≥ {MIN_NUMERIC_ASSERTIONS}). Thesis has no "
            "operational falsifier (SB-3 unfalsifiable_claim)."
        )
        return result

    result["passed"] = True
    if channel_2_ok or channel_3_ok:
        result["strength"] = "strong"
        advisory = []
        if channel_2_ok:
            advisory.append(f"DAG has {result['n_watch_signals']} watch_signals")
        if result["thesis_has_rival"]:
            advisory.append("thesis names rival")
        if result["thesis_has_discriminator"]:
            advisory.append("thesis declares discriminator")
        result["rationale"] = (
            f"{n_asserts} numeric-threshold assertion(s); " + "; ".join(advisory) + "."
        )
    else:
        result["strength"] = "weak"
        result["rationale"] = (
            f"{n_asserts} numeric-threshold assertion(s) present but no "
            "DAG watch_signal and no rival/discriminator section in thesis. "
            "Weakly falsifiable — passes gate but flag for review."
        )
    return result


def _self_test() -> int:
    """Unit tests on in-memory fixtures.

    Runs as __main__; returns 0 on pass, 1 on fail.
    """
    import tempfile

    def _write(content: str, suffix: str) -> Path:
        fh = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
        fh.write(content)
        fh.close()
        return Path(fh.name)

    # Case 1: valid thesis with 2 numeric asserts + watch_signal + rival
    tm = _write(
        "import math\n"
        "x = 3.14\n"
        "assert x < 4.0, 'pi is less than 4'\n"
        "y = compute()\n"
        "assert abs(y - 1.0) < 1e-6\n",
        ".py",
    )
    dag = _write(json.dumps({
        "outcome": {"label": "T"},
        "nodes": [{"id": "A", "watch_signal": "inspect log"}],
        "edges": [],
    }), ".json")
    thesis = _write("# Thesis\n\n## RIVAL HYPOTHESIS\nSomething else.\n", ".md")
    r = run_falsifiability_gate(tm, dag, thesis)
    assert r["passed"], f"valid case failed: {r}"
    assert r["strength"] == "strong"
    assert r["n_numeric_assertions"] == 2
    print(f"  valid thesis: PASS strong ({r['n_numeric_assertions']} asserts)")

    # Case 2: zero numeric asserts → gate fails
    tm = _write("x = 1\ny = 2\nassert isinstance(x, int)\n", ".py")
    r = run_falsifiability_gate(tm)
    assert not r["passed"], "zero-asserts case should fail"
    assert r["strength"] == "none"
    print(f"  no asserts: FAIL-as-expected ({r['n_numeric_assertions']} asserts)")

    # Case 3: bare `assert x` (no threshold) is not counted
    tm = _write("x = True\nassert x\nassert not None\n", ".py")
    r = run_falsifiability_gate(tm)
    assert not r["passed"], "bare-assert case should fail"
    print(f"  bare assertions: FAIL-as-expected")

    # Case 4: one numeric assert, no DAG, no thesis → passes weak
    tm = _write("x = 2\nassert x > 0\n", ".py")
    r = run_falsifiability_gate(tm)
    assert r["passed"], f"weak case should pass gate: {r}"
    assert r["strength"] == "weak"
    print(f"  weak falsifier: PASS weak")

    # Case 5: syntax-error test_model.py → 0 counted → fail
    tm = _write("def x(:\n  pass\n", ".py")
    r = run_falsifiability_gate(tm)
    assert not r["passed"]
    print(f"  syntax-error test_model: FAIL-safe")

    # Case 6: missing file
    r = run_falsifiability_gate(Path("/nonexistent/test_model.py"))
    assert not r["passed"]
    assert r.get("error") == "FileNotFoundError"
    print(f"  missing file: FAIL-safe")

    # Case 7: math.inf as threshold is counted
    tm = _write("import math\nx = float('inf')\nassert x == math.inf\n", ".py")
    r = run_falsifiability_gate(tm)
    assert r["passed"], f"math.inf case: {r}"
    print(f"  math.inf threshold: PASS")

    # Case 8: arithmetic BinOp threshold (e.g. 2**-10) is counted
    tm = _write("x = 0.001\nassert x < 2**-10\n", ".py")
    r = run_falsifiability_gate(tm)
    assert r["passed"], f"BinOp threshold: {r}"
    print(f"  BinOp threshold: PASS")

    print("\n8/8 falsifiability_gate self-tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_self_test())
