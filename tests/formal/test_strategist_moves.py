"""Regression guard for the strategist moves (SPECIALIZE rung + GENERALIZE closure)
wired into the SHARED move space (governed_dag_search.MOVE_ORDER layer + the
solver_core move-runner). Exercises the REAL runner branches with ONLY the
Lean/LLM-touching calls mocked — positive AND negative controls through the same
code path (a negative is inadmissible without calibration).

Locks, in particular:
  * the `by`-fold: the generalize proof_text must be `by `-prefixed (single `by`),
    never `by\\n...` (which doubles the `by` when folded into the goal's `:= by`);
  * SPECIALIZE produces an honest RUNG that NEVER closes G (no false-closure surface);
  * GENERALIZE closes ONLY through the standard kernel+MNC governance;
  * default-OFF parity is covered by the gds offline selftest (`--selftest`).

Self-contained: `python3 tests/formal/test_strategist_moves.py` (also pytest-collectable).
"""
import os
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
os.environ.pop("ZTARE_CONJECTURE_DECOMPOSE", None)

import ztare.leanmill.solver.agentic_leaf as al
import ztare.gates.v33_preflight_risk_detector as v33
import ztare.leanmill.solver.solver_core as sc
import ztare.leanmill.solver.governed_dag_search as gds

GOAL = "theorem t : G n := by"   # canonical stub shape (ends with ':= by')
ROW = {"row_id": "rt", "target_theorem_name": "t", "goal": GOAL}


class _N:  # minimal DagNode stand-in (the runner only reads kind/goal_text/node_id)
    kind = "root_goal"
    goal_text = GOAL
    node_id = "n0_root"


def _runner(captured=None):
    """Build the REAL move-runner with the Lean/LLM-touching deps mocked."""
    if captured is None:
        captured = {}

    def fake_verify_compile(row_id, goal_text, proof_text, lean_root, timeout_s):
        captured["proof_text"] = proof_text
        captured["goal"] = goal_text
        return True, "compiled clean (mock)"

    def fake_validate(contract, proof_text, enriched_goal, target_name, lean_root,
                      timeout_s, kernel_compile_ok, kernel_compile_tail, goal_type=None,
                      closure_source=None, posed_source=None):
        return {"receipts": {"kernel_compile_receipt": {"passed": True},
                             "matched_negative_control_receipt": {"passed": True}}}

    sc._verify_compile = fake_verify_compile
    sc._validate_against_contract = fake_validate
    sc._record_attempt = lambda *a, **k: None
    pt = []
    runner = sc._build_dag_move_runner(
        r=ROW, contract={}, enriched_goal=GOAL, verify_timeout=30,
        provider="codex", fallbacks=[], invoke_with_routing=lambda *a, **k: None,
        providers_tried=pt, lean_root="/tmp")
    return runner, pt, captured


def test_specialize_positive_is_a_rung_not_a_closure():
    al.default_dispatch = lambda *a, **k: (
        "SPECIAL:\n```lean\ntheorem spec_t : G 0 := by rfl\n```\n"
        "IMPLIES:\n```lean\ntheorem spec_t_imp (h : G n) : G 0 := by exact h0\n```\n")
    v33._compile_probe = lambda *a, **k: True
    runner, pt, _ = _runner()
    res = runner(_N(), gds.MOVE_SPECIALIZE, 100.0)
    assert res.rung is True
    assert res.kernel_clean is False and res.ratified_close is False   # a rung NEVER closes G
    assert "spec_t" in (res.proof_text or "")
    assert pt[-1]["outcome"] == "rung"


def test_specialize_negative_no_false_rung():
    al.default_dispatch = lambda *a, **k: (
        "SPECIAL:\n```lean\ntheorem spec_t : G 0 := by rfl\n```\n"
        "IMPLIES:\n```lean\ntheorem spec_t_imp (h : G n) : G 0 := by exact h0\n```\n")
    v33._compile_probe = lambda *a, **k: False        # the special case does NOT compile sorry-free
    runner, pt, _ = _runner()
    res = runner(_N(), gds.MOVE_SPECIALIZE, 100.0)
    assert res.rung is False
    assert pt[-1]["outcome"] == "no_rung"


def test_generalize_positive_closes_through_governance_and_by_fold_is_single():
    al.default_dispatch = lambda *a, **k: (
        "PROOF:\n```lean\nby\n  have gen : ∀ m, G m := by intro m; induction m <;> simp\n  exact gen n\n```\n")
    runner, pt, cap = _runner()
    res = runner(_N(), gds.MOVE_GENERALIZE, 100.0)
    assert res.ratified_close is True and res.kernel_clean and res.mnc_passed
    ptx = cap["proof_text"]
    # THE by-FOLD GUARD: single `by`, space form — a `by\n...` body would double the `by`.
    assert ptx.startswith("by ")
    assert "by by" not in ptx and not ptx[3:].lstrip().startswith("by")
    assert pt[-1]["outcome"] == "closed"


def test_generalize_negative_sorry_no_closure():
    al.default_dispatch = lambda *a, **k: "PROOF:\n```lean\nby\n  sorry\n```\n"
    runner, pt, _ = _runner()
    res = runner(_N(), gds.MOVE_GENERALIZE, 100.0)
    assert res.ratified_close is False
    assert pt[-1]["outcome"] == "failed_compile"


def test_spawned_goal_materializes_parent_vocabulary(tmp_path, monkeypatch):
    parent = tmp_path / "AdHoc_parent.lean"
    parent.write_text(
        "import Mathlib\n\ndef CampaignDef : Prop := True\n\n"
        "theorem parent : CampaignDef := by sorry\n",
        encoding="utf-8",
    )
    row = {
        "row_id": "spawned",
        "target_theorem_name": "parent",
        "goal": "theorem parent : CampaignDef := by",
        "source_file": str(parent),
        "sorried_file": str(parent),
    }
    seen = {}

    def fake_native(child, *_args):
        seen.update(child)
        return False, "", "expected miss"

    monkeypatch.setenv("ZTARE_CONJECTURE_DECOMPOSE", "1")
    monkeypatch.setattr(sc, "_native_hammer_probe", fake_native)
    monkeypatch.setattr(sc, "_record_attempt", lambda *a, **k: None)
    runner = sc._build_dag_move_runner(
        r=row, contract={}, enriched_goal=row["goal"], verify_timeout=30,
        provider="codex", fallbacks=[], invoke_with_routing=lambda *a, **k: None,
        providers_tried=[], lean_root=tmp_path,
    )
    child = _N()
    child.kind = "sub_goal"
    child.node_id = "n1_sub_goal_1"
    child.goal_text = "theorem child : CampaignDef := by sorry"
    runner(child, gds.MOVE_NATIVE_HAMMER, 30.0)

    materialized = Path(seen["source_file"])
    assert materialized != parent
    assert seen["target_theorem_name"] == "child"
    assert "def CampaignDef" in materialized.read_text(encoding="utf-8")
    assert "theorem child : CampaignDef" in materialized.read_text(encoding="utf-8")


def test_spawned_child_governance_is_invariant_to_root_identity(tmp_path, monkeypatch):
    """A child closure is governed as its own theorem, even when its parent is renamed."""
    parent = tmp_path / "AdHoc_parent.lean"
    parent.write_text(
        "import Mathlib\n\ndef CampaignDef : Prop := True\n\n"
        "theorem renamed_root : CampaignDef := by sorry\n",
        encoding="utf-8",
    )
    row = {
        "row_id": "spawned-governance", "target_theorem_name": "renamed_root",
        "goal": "theorem renamed_root : CampaignDef := by", "source_file": str(parent),
        "sorried_file": str(parent),
    }
    seen = {}

    monkeypatch.setenv("ZTARE_CONJECTURE_DECOMPOSE", "1")
    monkeypatch.setattr(sc, "_native_hammer_probe", lambda *_a, **_k: (True, "trivial", "compiled"))
    monkeypatch.setattr(sc, "_record_attempt", lambda *a, **k: None)

    def governed(**kwargs):
        seen.update(kwargs)
        return {"receipts": {"kernel_compile_receipt": {"passed": True},
                              "matched_negative_control_receipt": {"passed": True}}}

    monkeypatch.setattr(sc, "_validate_against_contract", governed)
    runner = sc._build_dag_move_runner(
        r=row, contract={}, enriched_goal=row["goal"], verify_timeout=30,
        provider="codex", fallbacks=[], invoke_with_routing=lambda *a, **k: None,
        providers_tried=[], lean_root=tmp_path,
    )
    child = _N()
    child.kind, child.node_id = "sub_goal", "n1_sub_goal_1"
    child.goal_text = "theorem child_identity : CampaignDef := by sorry"
    result = runner(child, gds.MOVE_NATIVE_HAMMER, 30.0)

    assert result.ratified_close
    assert seen["target_name"] == "child_identity"
    assert seen["goal_type"].startswith("theorem child_identity")
    assert "theorem child_identity" in seen["posed_source"]
    assert "renamed_root" not in seen["enriched_goal"]


def _main():
    fails = []
    for fn in (test_specialize_positive_is_a_rung_not_a_closure,
               test_specialize_negative_no_false_rung,
               test_generalize_positive_closes_through_governance_and_by_fold_is_single,
               test_generalize_negative_sorry_no_closure):
        try:
            fn()
            print(f"  [PASS] {fn.__name__}")
        except AssertionError as e:  # noqa: PERF203
            print(f"  [FAIL] {fn.__name__}: {e!r}")
            fails.append(fn.__name__)
    print("STRATEGIST-MOVES", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(_main())
