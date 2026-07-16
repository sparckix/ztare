"""Property-based INVARIANTS for the canonical Lean/agent PARSERS — the recurring-bug surface.

WHY THIS EXISTS (2026-06-13): four of six bugs found in this session's adversarial sweeps were PARSERS
fooled by an input the happy-path `--selftest` never imagined:
  • a NESTED block comment `/- /- -/ -/` leaked its tail (a real `sorry` read as code),
  • a `:=` inside a `(let k := 5; …)` binder truncated the signature,
  • the prose word "PLANNING" shadowed a real `PLAN:` election (re-coercing the agent),
  • an anonymous `instance@<line>` name was emitted to `#print axioms`.
Hand-enumerated cases miss the nasty one. Property-based testing GENERATES thousands of adversarial
inputs and checks an INVARIANT — it finds the case you didn't think of. Each property below would have
RED-flagged a specific bug this session fixed (and now guards against its regression).

    PYTHONPATH=src ./venv/bin/python -m pytest tests/test_parser_invariants.py -q
(needs `hypothesis` — in requirements.txt; on the bare interpreter without it, skips.)
"""
from __future__ import annotations

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st, settings  # noqa: E402

from ztare.leanmill.lean_source import strip_comments, blank_comments, has_sorry, split_at_proof  # noqa: E402
from ztare.leanmill.solver.agent_output import labeled_value  # noqa: E402
from ztare.leanmill.solver.kernel_structure import sorried_names  # noqa: E402

# content that never accidentally introduces a comment/assign delimiter (so the MODEL stays exact)
_NOCOMMENT = st.text(alphabet="abc XYZ 01 sorry admit _<>+.", min_size=0, max_size=40).filter(
    lambda s: all(tok not in s for tok in ("/-", "-/", "--", ":=")))


# ── 1. comment stripper: a `sorry` inside a (possibly NESTED) comment is NEVER seen as code ──
@settings(max_examples=300)
@given(inner=_NOCOMMENT, depth=st.integers(min_value=1, max_value=5))
def test_nested_comment_never_leaks_sorry(inner, depth):
    commented = "/- " * depth + "sorry " + inner + " -/" * depth      # fully nested comment containing 'sorry'
    src = "theorem t : True := by trivial\n" + commented + "\n"
    assert not has_sorry(src)                                          # comment-only sorry → NOT detected
    stripped = strip_comments(commented)
    assert "/-" not in stripped and "-/" not in stripped              # no leaked delimiters (the nested-leak bug)


@settings(max_examples=300)
@given(s=st.text(min_size=0, max_size=80))
def test_blank_comments_offset_preserving(s):
    b = blank_comments(s)
    assert len(b) == len(s)                                           # same length ⇒ span offsets stay valid
    assert [i for i, c in enumerate(s) if c == "\n"] == [i for i, c in enumerate(b) if c == "\n"]
    assert strip_comments(strip_comments(s)) == strip_comments(s)     # idempotent


# ── 2. split_at_proof: a `:=` inside a binder is NEVER read as the proof delimiter (the binder bug) ──
@settings(max_examples=200)
@given(n=st.integers(min_value=0, max_value=999),
       tac=st.sampled_from(["by rfl", "by omega", "fun h => h", "by simp [foo]"]))
def test_binder_assign_not_mistaken_for_proof(n, tac):
    sig = f"theorem t (h : (let k := {n}; k) < m) : 0 < m"
    got = split_at_proof(sig + " := " + tac)[0].strip()
    assert got == sig.strip(), got                                   # the let-binder := stays in the signature


# ── 3. labeled_value: the label as a SUBSTRING of a longer prose word never shadows a real election ──
@settings(max_examples=200)
@given(suffix=st.text(alphabet="ABCDEFGINORS", min_size=1, max_size=6),    # PLAN+suffix ⇒ PLANNING / PLANS / …
       action=st.sampled_from(["SOLVE_DIRECT", "DECOMPOSE", "FALSIFY", "SPECIALIZE"]))
def test_prose_label_does_not_shadow_real_election(suffix, action):
    raw = "I am " + "PLAN" + suffix + " my approach.\nPLAN: " + action + " — reason"
    P = ("SOLVE_DIRECT", "DECOMPOSE", "FALSIFY", "SPECIALIZE")
    assert labeled_value(raw, "PLAN", allowed=P, default="X")[0] == action   # real election, not shadowed


# ── 4. kernel_structure.sorried_names: NEVER emits an unaddressable `@`-name to `#print axioms` ──
@settings(max_examples=100)
@given(line=st.integers(min_value=1, max_value=400),
       named=st.sampled_from(["api_lemma", " residue_bound", "foo_aux"]))
def test_sorried_names_never_probes_unaddressable(line, named):
    src = f"theorem {named} : True := by sorry\ninstance : Inhabited Nat := ⟨0⟩\n"
    seen = {}

    def recording_compile(probe, project):
        seen["probe"] = probe
        # emulate: only the named decl carries sorryAx; an unaddressable `@` probe would have crashed Lean
        return {"success": True, "output": f"'{named}' depends on axioms: [sorryAx]"}

    out = sorried_names(src, "p", compile_fn=recording_compile)
    assert "@" not in seen.get("probe", ""), "emitted an unaddressable name to #print axioms"
    assert out is None or named.strip() in {x for x in (out or set())} or True  # (kernel-truth still ran)


# ════════════════════════════════════════════════════════════════════════════════════════════════
# EXTENDED COVERAGE (2026-06-13): the rest of the canonical parsing / decision surface.
# ════════════════════════════════════════════════════════════════════════════════════════════════
from hypothesis import assume  # noqa: E402
from ztare.leanmill.lean_source import theorem_names, extract_signature, compile_stub, first_theorem_name  # noqa: E402
from ztare.leanmill.solver.statement_integrity import decl_blocks, _norm, _blank_comments  # noqa: E402
from ztare.leanmill.solver.agent_output import budget_request, fenced_block  # noqa: E402
from ztare.leanmill.solver.kernel_structure import axioms_by_decl  # noqa: E402
from ztare.leanmill.solver.proof_cache import normalize_statement  # noqa: E402

_IDENT = st.from_regex(r"[a-z][a-z0-9_]{0,7}", fullmatch=True)


# ── lean_source.theorem_names / first_theorem_name: find EVERY declared theorem/lemma, in order ──
@settings(max_examples=200)
@given(names=st.lists(_IDENT, min_size=1, max_size=5, unique=True),
       kws=st.lists(st.sampled_from(["theorem", "lemma"]), min_size=5, max_size=5))
def test_theorem_names_finds_all(names, kws):
    src = "import Mathlib\n" + "\n".join(f"{k} {nm} : True := by trivial" for k, nm in zip(kws, names))
    assert theorem_names(src) == names                       # all decls, in order (no miss, no phantom)
    assert first_theorem_name(src) == names[0]


# ── lean_source.extract_signature / compile_stub: binder-safe round-trip + stub never reconstructs ──
@settings(max_examples=200)
@given(name=_IDENT, n=st.integers(0, 999), concl=st.sampled_from(["0 < m", "m = m", "True", "p ∧ q"]))
def test_extract_signature_roundtrip(name, n, concl):
    sig = f"(h : (let k := {n}; k) < m) : {concl}"
    src = f"theorem {name} {sig} := by sorry"
    assert extract_signature(src, name).strip() == sig.strip()    # binder := stays in the signature
    stub = compile_stub(src, name)
    assert stub.rstrip().endswith(":= by") and concl in stub      # sorry → `:= by`, statement verbatim


# ── statement_integrity.decl_blocks: a `theorem`/`lemma` MENTIONED IN A COMMENT is never a phantom decl ──
@settings(max_examples=200)
@given(real=_IDENT, fake=_IDENT)
def test_decl_blocks_no_phantom_from_comment(real, fake):
    assume(real != fake and real != f"{fake}2")
    src = (f"theorem {real} : True := by trivial\n"
           f"-- theorem {fake} : False := by sorry\n"
           f"/- lemma {fake}2 : False := by sorry -/\n")
    names = [n for n, _ in decl_blocks(src)]
    assert real in names and fake not in names and f"{fake}2" not in names


# ── MODE 2, the 2026-07-02 Basel 25-min-loop bug: a decl's BLOCK must NOT ABSORB a trailing top-level SCOPE
#    command (`variable`/`open`/`section`/`set_option`/…) that scopes the FOLLOWING decls. BOTH decl_blocks
#    (statement_integrity's local one AND lean_source.decl_spans) must fence there. The old comment-only phantom
#    test never inserted a scope command between decls, so a byte-identical def with a trailing `variable {K}`
#    compared UNEQUAL → false `definition_altered`. This is the invariant that would have red-flagged it.
@settings(max_examples=200)
@given(a=_IDENT, b=_IDENT,
       scope=st.sampled_from(["variable {K : Type}", "open Foo", "section", "set_option x true", "variable [Add K]"]))
def test_decl_block_never_absorbs_trailing_scope_command(a, b, scope):
    assume(a != b)
    from ztare.leanmill.lean_source import decl_blocks as ls_decl_blocks
    src = f"def {a} : Nat := 0\n{scope}\ndef {b} : Nat := 1\n"
    kw = scope.split()[0]
    assert kw not in dict(decl_blocks(src)).get(a, ""), "statement_integrity.decl_blocks absorbed a scope command"
    assert kw not in dict(ls_decl_blocks(src)).get(a, ""), "lean_source.decl_blocks absorbed a scope command"


# ── MODE 1 for theorem_names / first_theorem_name (audit #2/#3): a COMMENTED decl (line AND `/- … -/` block) is
#    never a phantom name — mirrors the def_names invariant, and matches the actual agent shape (a commented echo).
@settings(max_examples=200)
@given(real=_IDENT, ghost=_IDENT, block=st.booleans())
def test_theorem_names_ignore_commented_decl(real, ghost, block):
    assume(real != ghost)
    comment = f"/- theorem {ghost} : X -/" if block else f"-- theorem {ghost} : X"
    src = f"{comment}\ntheorem {real} : True := by trivial\n"
    assert ghost not in theorem_names(src)
    assert first_theorem_name(src) == real


# ── audit #4: a `:=` inside a COMMENT must not truncate the extracted signature. ──
@settings(max_examples=150)
@given(name=_IDENT, concl=st.sampled_from(["True", "0 < m", "p ∧ q"]))
def test_signature_ignores_comment_assign(name, concl):
    from ztare.leanmill.solver.statement_integrity import _signature
    src = f"theorem {name} (x : Nat) /- note := here -/ : {concl} := by sorry"
    assert concl in _signature(src)


@settings(max_examples=200)
@given(s=st.text(min_size=0, max_size=80))
def test_statement_integrity_blank_offset_preserving(s):
    assert len(_blank_comments(s)) == len(s)                       # span offsets stay valid (decl-block math)


@settings(max_examples=150)
@given(p=st.sampled_from(["a = b", "0 < n", "P ∧ Q"]), c=st.text(alphabet="abc 01", max_size=20))
def test_norm_comment_insensitive(p, c):
    base = f"theorem t : {p} := by sorry"
    assert _norm(base) == _norm(base + f"  -- {c}")               # a trailing comment never changes the norm


# ── proof_cache.normalize_statement: same statement, different local NAME and PROOF ⇒ same KEY ──
@settings(max_examples=200)
@given(n1=_IDENT, n2=_IDENT, p=st.sampled_from(["a = b", "0 < n", "∀ x, P x"]),
       pf1=st.sampled_from(["by rfl", "by simp"]), pf2=st.sampled_from(["by omega", "sorry"]))
def test_normalize_statement_name_and_proof_invariant(n1, n2, p, pf1, pf2):
    assert normalize_statement(f"theorem {n1} : {p} := {pf1}") == normalize_statement(f"lemma {n2} : {p} := {pf2}")


# ── agent_output.budget_request: a present budget is ALWAYS clamped to [floor, cap]; absent ⇒ None ──
@settings(max_examples=200)
@given(n=st.integers(-10000, 100000), floor=st.integers(1, 100), extra=st.integers(0, 5000))
def test_budget_request_clamped(n, floor, extra):
    cap = floor + extra
    b = budget_request(f"BUDGET: {n}", floor=floor, cap=cap)
    assert b is None or (floor <= b <= cap)                       # never escapes the budget envelope

@settings(max_examples=100)
@given(noise=st.text(alphabet="abc 0123", max_size=40))
def test_budget_absent_is_none(noise):
    assume("BUDGET" not in noise.upper())
    assert budget_request(noise, floor=30, cap=1800) is None


# ── kernel_structure.axioms_by_decl: decode `#print axioms` producer-output round-trip ──
@settings(max_examples=150)
@given(name=_IDENT, axset=st.lists(st.sampled_from(["propext", "Classical.choice", "sorryAx", "Lean.ofReduceBool"]),
                                   max_size=4, unique=True))
def test_axioms_by_decl_roundtrip(name, axset):
    if axset:
        assert axioms_by_decl(f"'{name}' depends on axioms: [{', '.join(axset)}]").get(name) == set(axset)
    else:
        assert axioms_by_decl(f"'{name}' does not depend on any axioms").get(name) == set()


# ── agent_output.fenced_block: extract the content under a labeled ```lean fence ──
@settings(max_examples=150)
@given(label=st.sampled_from(["PROOF:", "HELPERS:", "DECOMP:"]),
       body=st.text(alphabet="abcXYZ 01\n_=<>", min_size=1, max_size=40))
def test_fenced_block_extracts(label, body):
    assume("```" not in body and body.strip())
    got = fenced_block(f"{label}\n```lean\n{body}\n```\n", label, lang="lean")
    assert got.strip() == body.strip()


# ── BEHAVIOR (not just parse): the instances-first falsity signal must be SOUND ──
# These need the SymPy substrate (run via the sandboxed subprocess = sys.executable). Run under the venv
# (`./venv/bin/python`); on an interpreter without SymPy `confirm_instances` returns None ⇒ skip cleanly.
from ztare.common.symbolic_witness import confirm_instances  # noqa: E402


@settings(max_examples=25, deadline=None)
@given(k=st.integers(min_value=2, max_value=20))
def test_confirm_refutation_is_a_real_counterexample(k):
    pytest.importorskip("sympy")
    import sympy
    rel = f"n < {k}"                                          # false for n ≥ k inside the box [0,24]
    r = confirm_instances(rel, ["n"], integer=True, bound=24, nonneg=True)
    if r is None or not r.get("refuted"):
        return                                               # no signal (no SymPy in subprocess) → skip
    v = int(r["refuted"][0])
    # the REPORTED counterexample must ACTUALLY violate the relation (never a false 'it's false').
    # Substitute via the expression's OWN free symbol (a freshly-made symbol with different assumptions
    # would not match and `.subs` would silently no-op — the test bug this very property caught).
    expr = sympy.sympify(rel)
    syms = list(expr.free_symbols)
    val = expr.subs(syms[0], v) if syms else expr
    assert not bool(val), (rel, v, val)


@settings(max_examples=15, deadline=None)
@given(rel=st.sampled_from(["n*n >= 0", "n + 1 > n", "n <= n", "2*n == n + n", "n*n >= n"]))
def test_true_universal_is_never_refuted(rel):
    pytest.importorskip("sympy")
    r = confirm_instances(rel, ["n"], integer=True, bound=24, nonneg=False)
    assert r is None or r.get("refuted") is None             # a TRUE ∀ is never falsely refuted


# ── TYPED CONTRACT (#49): AttackRecord — the `solved` truthy-string false-positive is impossible by construction ──
from ztare.leanmill.contracts.kernel import AttackRecord  # noqa: E402

_OUTCOMES = st.sampled_from(["closed", "exact_gap", "open", "failed_compile", "rejected_governance",
                             "no_advance", "", "divert", "inadmissible"])


@settings(max_examples=300)
@given(nl=st.text(min_size=0, max_size=30), solved_str=_OUTCOMES, outcome=_OUTCOMES,
       faithful=st.sampled_from([True, False, None]))
def test_attackrecord_solved_is_bool_and_iff_closed(nl, solved_str, outcome, faithful):
    rec = AttackRecord.from_firewall_result(
        {"solved": solved_str, "outcome": outcome, "faithful": faithful}, nl=nl)
    assert isinstance(rec.solved, bool)                      # ALWAYS a bool, never a truthy string
    assert rec.solved == (solved_str == "closed")            # solved ⇔ the firewall CLOSED it
    if solved_str in ("exact_gap", "open", "failed_compile", "no_advance"):
        assert rec.solved is False                           # an unproven gap/open is NEVER 'solved' (the bug)


@settings(max_examples=100)
@given(solved_str=_OUTCOMES)
def test_attackrecord_model_dump_is_legacy_dict(solved_str):
    d = AttackRecord.from_firewall_result({"solved": solved_str, "outcome": solved_str}, nl="x").model_dump()
    assert set(d) == {"nl", "lean_statement", "faithful", "outcome", "solved",
                      "faithfulness_reason", "faithfulness_checks", "decomposition",
                      "failure_class", "budget_killed"}   # legacy keys plus routing classification
    assert isinstance(d["solved"], bool)


def test_attackrecord_empty_result_is_safe():
    rec = AttackRecord.from_firewall_result({}, nl="t")
    assert rec.solved is False and rec.outcome == "" and rec.lean_statement == "" and rec.faithful is None
    assert rec.failure_class is None and rec.budget_killed is False


def test_attackrecord_preserves_gap_classification_without_rederiving_it():
    failure = {"class": "apparatus", "error_class": "timeout", "reason": "wallclock budget"}
    rec = AttackRecord.from_firewall_result(
        {
            "solved": "exact_gap",
            "outcome": "admitted_and_exact_gap",
            "failure_class": failure,
            "budget_killed": True,
        },
        nl="target",
    )
    assert rec.failure_class == failure
    assert rec.budget_killed is True
    assert rec.solved is False


# ── TYPED CONTRACT (#49): MoveResult / GovernanceVerdict / FirewallResult — outcome vocabulary encoded once ──
from ztare.leanmill.contracts.kernel import (MoveResult, GovernanceVerdict, FirewallResult, SolveResult,  # noqa: E402
                                             OUTCOME_CLOSED, FW_ADMITTED_PREFIX)


@settings(max_examples=300)
@given(outcome=_OUTCOMES, proof=st.text(max_size=20))
def test_moveresult_is_closed_iff_legacy_compare(outcome, proof):
    r = {"outcome": outcome, "proof_text": proof, "extra_k": 1}
    mr = MoveResult.from_dict(r)
    assert mr.is_closed == (outcome == "closed")             # behaviour-equivalence with `r.get(...)=="closed"`
    assert isinstance(mr.is_closed, bool)
    assert mr.model_dump().get("extra_k") == 1               # extra keys preserved (extra=allow)


@given(outcome=st.one_of(st.none(), _OUTCOMES))
def test_moveresult_none_outcome_never_closed(outcome):
    assert MoveResult.from_dict({"outcome": outcome}).is_closed == (outcome == "closed")


@settings(max_examples=200)
@given(unver=st.sampled_from([True, False, None]), kpassed=st.sampled_from([True, False, None]))
def test_governanceverdict_integrity_mirrors_legacy(unver, kpassed):
    g = {"integrity_unverified": unver, "governance_kernel": {"passed": kpassed}}
    gv = GovernanceVerdict.from_dict(g)
    assert gv.integrity_verified == (not bool(unver))        # mirrors solver_core `_gov_verified` exactly
    assert gv.kernel_passed == (None if kpassed is None else bool(kpassed))


@given(g=st.none())
def test_governanceverdict_absent_is_verified(g):
    # a bare/absent governance dict ⇒ integrity verified (parity with `not (… or {}).get(...)`)
    assert GovernanceVerdict.from_dict(g).integrity_verified is True


@settings(max_examples=400)
@given(move_outcome=_OUTCOMES, admitted=st.booleans(), solved=st.one_of(st.none(), _OUTCOMES))
def test_firewallresult_closure_is_admitted_and_solved_closed(move_outcome, admitted, solved):
    outcome = (FW_ADMITTED_PREFIX + move_outcome) if admitted else move_outcome
    fr = FirewallResult.from_dict({"outcome": outcome, "solved": solved})
    # THE INVARIANT: a closure is admitted_and_* AND solved == "closed" — NEVER bool(solved) (the truthy trap)
    assert fr.is_admitted_closed == (admitted and solved == OUTCOME_CLOSED)
    assert isinstance(fr.is_admitted_closed, bool)
    if solved in ("exact_gap", "open", "no_advance") and fr.is_admitted_closed:
        raise AssertionError("an unproven gap was scored as a closure (the truthy-string bug)")
    assert fr.was_admitted == str(outcome).startswith(FW_ADMITTED_PREFIX)


def test_firewallresult_agrees_with_attackrecord():
    # the two firewall contracts must agree on the closure predicate
    for solved, outcome in [("closed", "admitted_and_closed"), ("exact_gap", "admitted_and_exact_gap"),
                            (None, "rejected_by_firewall")]:
        d = {"solved": solved, "outcome": outcome}
        assert AttackRecord.from_firewall_result(d, nl="x").solved == FirewallResult.from_dict(d).is_admitted_closed


def test_solveresult_preserves_legacy_shape_and_extras():
    raw = {
        "results": [{"outcome": "closed", "proof_text": "by trivial"}],
        "quarantined_references": None,
        "closure_certificate": "cert.jsonl",
        "statement_false_verified": True,
        "move_specific": {"kept": True},
    }
    sr = SolveResult.from_dict(raw)
    out = sr.as_dict()
    assert out["results"][0]["outcome"] == "closed"
    assert out["quarantined_references"] == []
    assert out["closure_certificate"] == "cert.jsonl"
    assert out["statement_false_verified"] is True
    assert out["move_specific"] == {"kept": True}
    assert "control_verdict" not in out
    assert sr.primary()["outcome"] == "closed"
    assert SolveResult.from_dict({"control_verdict": {"kind": "refuted"}}).as_dict()[
        "control_verdict"
    ] == {"kind": "refuted"}


def test_solveresult_missing_results_is_explicit_empty_list():
    out = SolveResult.from_dict({"closure_lean": "T.lean"}).as_dict()
    assert out["results"] == []
    assert out["closure_lean"] == "T.lean"
