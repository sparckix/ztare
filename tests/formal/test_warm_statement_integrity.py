"""Regression guard for the SOLVE-TIME statement-integrity gate in the warm/agentic-leaf path
(found 2026-06-06 by the strategist-lift false control).

The warm agent edits a WHOLE probe file, so it can keep the theorem NAME but ALTER the statement
(e.g. prove `¬ ∀ n, P n` of a false `∀ n, P n` goal). `_agentic_leaf_warm_solve` must run
`statement_integrity.check` on the produced probe and return NOT-closed on any alteration — while
still accepting a genuine proof (incl. added helper decls). Mocks `solve_robust` + writes the probe;
no box/agents needed. Self-contained: `python3 tests/formal/test_warm_statement_integrity.py`.
"""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import ztare.leanmill.solver.agentic_leaf as al  # noqa: E402
import ztare.leanmill.solver.solver_core as sc  # noqa: E402

ORIGINAL = (
    "import Mathlib\n\n"
    "theorem tgt (n : ℕ) : (Finset.range n).sum (fun i => i) = n ^ 2 := by\n  sorry\n"
)
ALTERED_PROBE = (  # the laundering: same NAME, flipped statement
    "import Mathlib\n\n"
    "theorem tgt : ¬ ∀ n : ℕ, (Finset.range n).sum (fun i => i) = n ^ 2 := by\n"
    "  intro h; have h2 := h 2; norm_num at h2\n"
)
GENUINE_PROBE = (  # honest: same statement, real proof + an ADDED helper (must be allowed)
    "import Mathlib\n\n"
    "theorem tgt_helper : True := trivial\n\n"
    "theorem tgt (n : ℕ) : (Finset.range n).sum (fun i => i) = n ^ 2 := by\n  exact some_real_proof\n"
)


def _run_with_probe(probe_text: str):
    """Drive _agentic_leaf_warm_solve with solve_robust mocked to 'closed' + a written probe."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        src = root / "src.lean"
        src.write_text(ORIGINAL, encoding="utf-8")
        al.probe_dir(root).joinpath("RobustProbe_codex_0.lean").write_text(
            probe_text,
            encoding="utf-8",
        )
        al.solve_robust = lambda *a, **k: SimpleNamespace(
            inadmissible=False, closed=True, reason="ok", rounds=1, decomposed=False,
            calibration={"best_of": {"winner": "codex"}})
        row = {"row_id": "t", "target_theorem_name": "tgt", "goal": ORIGINAL, "source_file": str(src)}
        return sc._agentic_leaf_warm_solve(row, root, 30)


def test_altered_statement_is_blocked():
    ok, proof, tail = _run_with_probe(ALTERED_PROBE)
    assert ok is False, f"laundered (statement-flipped) probe must NOT be a closure; got ok={ok}"
    assert "statement_integrity" in tail.lower(), tail


def test_genuine_proof_with_helper_passes():
    ok, proof, tail = _run_with_probe(GENUINE_PROBE)
    assert ok is True, f"genuine proof (unaltered statement + added helper) must pass; tail={tail}"


def _main():
    fails = []
    for fn in (test_altered_statement_is_blocked, test_genuine_proof_with_helper_passes):
        try:
            fn(); print(f"  [PASS] {fn.__name__}")
        except AssertionError as e:
            print(f"  [FAIL] {fn.__name__}: {e}"); fails.append(fn.__name__)
    print("WARM-STATEMENT-INTEGRITY", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(_main())
