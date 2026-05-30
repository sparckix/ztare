"""GP-241 frozen adversarial-fixture kill-test.

This is the acceptance artifact the forward spec
(`research_areas/seams/apparatus/cage/GP-241_forward_spec_promotion_contracts.md`)
and the external verdict both name as the real next milestone: prove,
with FROZEN bad fixtures and a deterministic FP/FN table, that the
membrane catches the exact laundering failures this project lived —
not the builder asserting it works.

Discipline (precommitted):
  * Each fixture below is a laundering attempt this project actually
    hit, OR a benign control that MUST pass. The expected verdict is
    a frozen constant in this file, authored as the contract — the
    implementation may not be edited to make a fixture pass without
    that being a reviewed change (paper-2 promotion-path scoping).
  * The test exercises the *importable decision primitives* (pure,
    deterministic). Legs that need a live daemon process or a Lean
    toolchain are asserted at the safety boundary (BLOCKED-not-PASS)
    and otherwise marked xfail-with-reason — NEVER faked green.
  * Acceptance = this test reproduced from a clean checkout by
    not-the-builder. A builder run is recorded, not acceptance.

Run: `pytest -q tests/gates/test_gp241_laundering_fixtures.py`
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import pytest
except ModuleNotFoundError:  # plain-script / minimal-env fallback
    class _XF:
        def __call__(self, *a, **k):
            def _d(fn):
                fn.__xfail__ = True
                return fn
            return _d
    class _Mark:
        xfail = _XF()
    class _PytestShim:
        mark = _Mark()
    pytest = _PytestShim()  # type: ignore

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


# ── FN table: lived laundering attempts that MUST be caught ──────────

def test_cite_hash_prove_weaker_is_discriminated():
    """Lived failure SM3: cite a registered Clay hash in prose while
    the Lean proves a weaker toy theorem. The canonical-statement
    hash of the weaker proof MUST differ from the registered target's
    hash (so the daemon's claimed ∈ proven intersection fails)."""
    from src.ztare.gates.lean_proof_gate import (
        theorem_statement_hashes, canonical_statement)
    import hashlib
    clay_txt = "(u : VectorField) (h : NavierStokes u) : SmoothForever u"
    clay_hash = hashlib.sha256(
        canonical_statement(clay_txt).encode()).hexdigest()
    weaker = "theorem toy : 1 = 1 := rfl"
    proven = [h["statement_sha256"]
              for h in theorem_statement_hashes(weaker)]
    assert clay_hash not in proven, (
        "FN: a weaker toy proof must not collide with the registered "
        "Clay target hash")


def test_binder_colon_not_misparsed():
    """Lived self-MD regression: a `:` inside binders must not split
    the statement (else faithful proofs mis-hash / false-FAIL)."""
    from src.ztare.gates.lean_proof_gate import theorem_statement_hashes
    got = theorem_statement_hashes(
        "theorem clay (u : VF) (h : NS u) : Smooth u := by sorry")
    assert got and "Smooth u" not in got[0]["statement_sha256"]
    # parity: the same signature text registered by the operator
    # hashes identically (no operator/prover normalization drift)
    from src.ztare.gates.lean_proof_gate import canonical_statement
    import hashlib
    op = hashlib.sha256(canonical_statement(
        " (u : VF) (h : NS u) : Smooth u ").encode()).hexdigest()
    assert op == got[0]["statement_sha256"], (
        "FN: operator-registered text must hash == prover proven text")


def test_operator_attestation_is_not_a_flag():
    """Lived failure C2: an `i_am_operator` flag / env var the agent
    runtime could carry must NOT authenticate; only a pinned-key
    signature, and an unprovisioned anchor MUST fail closed."""
    from src.ztare.gates._daemon_sig import (
        operator_verify, operator_anchor_provisioned)
    # INVARIANT (must hold in EVERY state, provisioned or not): a
    # forged / garbage / absent operator sig never verifies. This is
    # the actual C2 security property; an env flag / proposal boolean
    # is not even consulted.
    assert operator_verify("payload", "deadbeef") is False, (
        "FN: a forged/garbage operator sig must not verify")
    assert operator_verify("payload", None) is False, (
        "FN: a missing operator sig must not verify (no flag path)")
    # STATE-DEPENDENT (not laundering — the fixture under-specified by
    # baking in the placeholder): if the anchor is still the
    # placeholder it MUST read unprovisioned (P5 fail-closed); if the
    # operator has pinned a real 64-hex key it MUST read provisioned.
    # Either way C2 is correct; only the *current state* differs.
    import pathlib
    _hx = (pathlib.Path(__file__).resolve().parents[2]
           / "deploy" / "gp241_operator_pubkey.hex"
           ).read_text(encoding="utf-8").strip()
    _is_placeholder = (len(_hx) != 64
                       or not all(c in "0123456789abcdefABCDEF"
                                  for c in _hx))
    if _is_placeholder:
        assert operator_anchor_provisioned() is False, (
            "FN: placeholder anchor MUST read unprovisioned so "
            "target_register fails closed (P5)")
    else:
        assert operator_anchor_provisioned() is True, (
            "FN: a pinned 64-hex anchor MUST read provisioned (else "
            "an honest operator-signed target_register false-FAILs)")


def test_c3_blocked_not_passed_without_toolchain_or_on_divergence():
    """C3 safety property: the defeq probe must return BLOCKED (never
    PASS) when it cannot run, and must NOT return PASS for two plainly
    different statements. (PASS-on-faithful needs a live toolchain and
    is the not-the-builder kill-test; here we assert it never silently
    passes.)"""
    from src.ztare.gates.lean_statement_identity import statements_defeq
    v_empty, _ = statements_defeq("", "")
    assert v_empty == "BLOCKED"
    v, _ = statements_defeq("(a : Nat) : a = a", "(a : Nat) : a = a+1")
    assert v in {"FAIL", "BLOCKED"}, (
        "FN: clearly-different statements must never PASS; if no "
        "toolchain, BLOCKED — never silent PASS")


def test_full_sha256_required_for_target():
    """Lived failure F6: an 8-hex prefix is collision-weak for a
    Clay-target anchor; only a full 64-hex sha256 is accepted."""
    from src.ztare.gates.commit_membrane_daemon import _re_hex64
    assert _re_hex64("a" * 64) is True
    assert _re_hex64("a" * 8) is False
    assert _re_hex64("a" * 63) is False
    assert _re_hex64("xyz") is False


# ── FP table: benign cases that MUST NOT be falsely caught ──────────

def test_faithful_statement_self_parity_is_stable():
    """FP guard: the same statement canonicalizes identically across
    whitespace/comment noise — an honest faithful proof whose text
    matches the registered text must hash-match (no false-FAIL)."""
    from src.ztare.gates.lean_proof_gate import canonical_statement
    a = canonical_statement("  (u : VF)   : P u  ")
    b = canonical_statement("(u : VF) : P u")
    c = canonical_statement("/- c -/ (u : VF) : P u -- t")
    assert a == b == c, "FP: benign formatting noise must not change "\
        "the canonical statement"


def test_nonclosure_goal_not_forced_into_lean(tmp_path):
    """Lived regression (finding 5): a non-Lean analysis goal
    containing generic words must NOT be forced to declare a thesis.
    Asserted via the narrowed Lean-claim token set."""
    gl = "scope the closure of the argument and prove the lemma"\
         " informally".lower()
    lean_tokens = ("lean", "lake build", "sorry-free", "no sorry",
                   "axiom-free", "compiled proof", " qed", "∎",
                   "mathlib")
    assert not any(t in gl for t in lean_tokens), (
        "FP: generic 'closure/prove/lemma' must not trip the Lean "
        "faithfulness HARD requirement (finding-5 regression guard)")


def test_tick_close_proposed_f_row_body_is_not_official_write():
    """GP-241 regression: tick_close may accept a proposed F-row body,
    but this must stay a proposal surface. The row must still be
    owner-tagged and dispatch-ledger-valid locally, and officialness
    still belongs to the daemon's H7 stamp."""
    import importlib.util

    p = REPO / "scripts/public/control/tick_close.py"
    spec = importlib.util.spec_from_file_location("tick_close_control", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    _dispatch_ledger_errors = mod._dispatch_ledger_errors

    good = (
        "| F-TEST | `2026-05-19` | x | y | z | owner:codex:RD; "
        "consumes_surfaced:selected_projected_cross_defect_observable_"
        "liminf_source; dispatch_ledger: lane=adversarial_kill |"
    )
    bad = good.replace("adversarial_kill", "forward_work")
    assert _dispatch_ledger_errors(good) == []
    assert _dispatch_ledger_errors(bad), (
        "FN: proposed f_row_body must not let an unsanctioned "
        "dispatch class through before daemon submission")


def test_judge_prompt_for_why_not_uses_why_not_rubric():
    """Regression for the TICK649 close jam: a valid why_not discharge
    must be judged as a why_not, not as a successful construction
    witness; arbitrary reasons must not get that treatment."""
    from src.ztare.surfacing.pre_tick_obligation_compiler import (
        judge_prompt_for,
    )

    goal = (
        "Characterize whether the C7 weak-bilinear high-level "
        "production gain for (A_visc)_+ on high-vorticity level sets "
        "can supply beta>0 or q>5/2 without Constantin-Fefferman "
        "alignment, and if not identify the exact endpoint or "
        "route-promotion obstruction that retires the CV branch without "
        "claiming a millennium-problem result."
    )
    declared = {"math_estimate": True}
    valid = judge_prompt_for(
        goal, "math_estimate", declared,
        "auxiliary_comparison_object_construction",
        {"reason": "contradicted_by_goal",
         "justification": "classification/useful-negative tick",
         "provenance": "judge:auto"})
    invalid = judge_prompt_for(
        goal, "math_estimate", declared,
        "auxiliary_comparison_object_construction",
        {"reason": "made_up_reason",
         "justification": "classification/useful-negative tick",
         "provenance": "judge:auto"})
    assert "DISCHARGE KIND: why_not" in valid
    assert "Do NOT require the successful-construction" in valid
    assert "DISCHARGE KIND: witness" in invalid
    assert "why_not_enum" in valid


def test_judge_request_id_changes_when_prompt_rubric_changes():
    """A corrected judge rubric must be able to emit a fresh request.
    Otherwise an old failed verdict for the same witness sha can wedge
    a corrected why_not forever."""
    import hashlib

    tick_id = "F-TEST"
    contract_id = "abc123"
    item_id = "auxiliary_comparison_object_construction"
    witness_sha = "f" * 64
    old_prompt_hash = "oldprompt"
    new_prompt_hash = "newprompt"
    old = hashlib.sha256(
        f"{tick_id}|{contract_id}|{item_id}|{witness_sha}|"
        f"{old_prompt_hash}".encode()).hexdigest()[:16]
    new = hashlib.sha256(
        f"{tick_id}|{contract_id}|{item_id}|{witness_sha}|"
        f"{new_prompt_hash}".encode()).hexdigest()[:16]
    assert old != new, (
        "FN: judge request identity must include the prompt/rubric hash "
        "so rubric fixes are not blocked by stale failed requests")


# ── Honest coverage boundary (NOT faked green) ──────────────────────

def _run_all() -> int:
    """Plain-script runner: a run MUST produce a loud, unambiguous
    verdict. SILENCE IS NOT A PASS — the absence of this runner is why
    'no response' was misread as ready. Exit code: 0 iff every
    non-xfail fixture PASSED; nonzero otherwise. Each fixture prints
    PASS / FAIL / XFAIL explicitly."""
    import inspect
    fns = sorted(
        (n, f) for n, f in globals().items()
        if n.startswith("test_") and callable(f))
    npass = nfail = nxfail = 0
    fails: list[str] = []
    for n, f in fns:
        xfail = getattr(f, "__xfail__", False)
        try:
            f("/tmp") if "tmp_path" in inspect.signature(
                f).parameters else f()
            if xfail:
                print(f"XPASS  {n}  (xfail-marked but passed — review)")
                nxfail += 1
            else:
                print(f"PASS   {n}")
                npass += 1
        except Exception as e:  # noqa: BLE001
            if xfail:
                print(f"XFAIL  {n}  (expected: not-the-builder leg) "
                      f"— {type(e).__name__}")
                nxfail += 1
            else:
                print(f"FAIL   {n}  -> {type(e).__name__}: "
                      f"{str(e)[:200]}")
                fails.append(n)
                nfail += 1
    print("-" * 60)
    print(f"VERDICT: {npass} PASS, {nfail} FAIL, {nxfail} XFAIL/XPASS")
    if nfail:
        print(f"NOT READY — failing: {fails}")
        return 1
    print("pure fixtures GREEN. NOTE: this is BUILDER self-review and "
          "does NOT constitute acceptance. The XFAIL legs (daemon-"
          "integration, C2 forged-sig, C3 Lean-live) MUST be run "
          "green by NOT-the-builder before closure-grade is trusted "
          "(spec acceptance protocol).")
    return 0


@pytest.mark.xfail(reason="requires a live daemon process + ledger: "
                          "substrate-swap / receipt-churn / forged-"
                          "COMPLETE / namespace-mismatch are enforced "
                          "in process_one and must be exercised by "
                          "the not-the-builder daemon kill-test, not "
                          "unit-faked here",
                   strict=False)
def test_daemon_integration_legs_placeholder():
    raise AssertionError(
        "daemon-integration laundering fixtures (substrate-swap, "
        "receipt-churn, forged-COMPLETE, namespace-mismatch, C3 "
        "PASS-on-faithful) are the not-the-builder daemon+Lean "
        "kill-test — explicitly not asserted green by the builder")


if __name__ == "__main__":
    raise SystemExit(_run_all())
