"""Autoformalization with a FAITHFULNESS FIREWALL — the leanmill-distinctive component.

Frontier models can turn a natural-language math problem into *a* Lean statement. The HARD part —
the part everyone punts and the reason leanmill is uniquely the place to build this — is
FAITHFULNESS: is the formal statement a true rendering of the NL problem, or is it subtly
VACUOUS / TRIVIALLY-TRUE / WEAKER-than-intended / WRONG? A mis-formalization that then gets "closed"
is the WORST outcome: it looks like solving a hard problem and isn't. Faithfulness IS anti-laundering
— the governance competency. So the value here is not the NL→Lean step (any leaf does that); it is
the GATE that refuses to admit an unfaithful formalization as a target.

PIPELINE (each step a pluggable fn so it reuses the real apparatus and is unit-testable with mocks):
  1. formalize(nl)            → candidate Lean statement (`… := by sorry`)   [leaf/LLM]
  2. FAITHFULNESS GATE (the firewall) — admit the target ONLY if ALL hold:
       a. compiles            — typechecks with `sorry` (a malformed statement is not a target) [kernel]
       b. non-trivial         — cheap tactics (`simp`/`decide`/`trivial`/`omega`/`tauto`) do NOT close
                                it (a trivially-closed formalization is degenerate / not the problem) [kernel]
       c. round-trip faithful — back-translate the Lean statement to NL and have an INDEPENDENT (cold,
                                cross-family) judge rule it the SAME problem: not weakened, not vacuous,
                                not changed. [back-translate LLM + cold judge — never self-blessed]
  3. only an admitted (faithful) statement becomes a target for the existing solver.

STATUS: apparatus, OPT-IN (not wired into any live loop). The gate's REJECT behavior is the point and
is what the self-test (and the adversarial review) must verify — it must reject vacuous / trivial /
non-compiling / round-trip-mismatched formalizations, not just accept faithful ones. A faithfulness
gate that never says no is a false-success generator.

KERNEL REUSE — NO STANDALONE GOVERNANCE FRANKENSTEIN. This module is deliberately a thin orchestrator
of INJECTED fns; it embeds NO kernel/governance logic. Faithfulness IS anti-laundering, so the gate is
an EXTENSION of the ONE governance kernel applied to a new artifact (statements, not proofs) — not a
parallel governance. The PRODUCTION fns MUST inject the existing apparatus, never reimplement it:
  * compile_fn     → the kernel verify (`gates/lean_proof_gate` / the worker's `_verify_compile` /
                     `agentic_leaf.verify_lean_proof`), i.e. `lake env lean` + the v33 stack.
  * triviality_fn  → the SAME kernel verify, re-running the statement under cheap tactics.
  * (vacuity)      → the existing v33 / `governance_organs` vacuity check — do NOT add a new one.
  * judge_fn       → the existing COLD cross-family judge dispatch (`dispatch_external_prover` /
                     `judge_out_of_loop` / the cli-agent protocol), NOT a fresh LLM-judge.
The ONLY genuinely new piece is the NL↔Lean round-trip itself (statement faithfulness is a new domain
the proof-laundering organs don't cover); even that reuses the LLM runtime + cold-judge infra.
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from ztare.leanmill.exploration_budget import BudgetExceeded
from ztare.leanmill.solver import prompts          # canonical prompt home (#49): backtranslate / judge / def-judge templates

# Phase-timing seam (shared common.telemetry, read by factory_intelligence): time the FORMALIZE phase so
# "time to insight" can be decomposed (formalize vs solve vs govern). Defensive — telemetry never breaks the gate.
try:
    from ztare.leanmill.phase_timing import phase_timer as _phase_timer
except Exception:  # noqa: BLE001
    import contextlib as _ctxlib_pt

    def _phase_timer(*_a, **_k):  # type: ignore
        return _ctxlib_pt.nullcontext()


def _is_true(v) -> bool:
    """STRICT: only canonical `True` counts. Any other value (a verdict string like 'NO', a non-zero
    returncode, None, an error message — all of which a real kernel/LLM wrapper can return and which
    `bool(...)` would coerce to True) is treated as inconclusive ⇒ NOT a pass. Adversarial-review fix:
    here a false ACCEPT is a fabricated success, so the gate must never coerce."""
    return v is True


def _visible(s: str) -> str:
    """Strip format / zero-width / control / separator chars (U+200B, U+2060, NBSP, …) before the
    non-empty check — `str.strip()` alone lets a zero-width back-translation slip through."""
    return "".join(c for c in (s or "") if unicodedata.category(c) not in ("Cf", "Zs", "Cc", "Zl", "Zp")).strip()


def _reference_gate_inputs(reference: object) -> tuple[object | None, str]:
    """Return hard-gate inputs only for an exact NL↔statement match.

    A semantic neighbour is a useful generation hint, but it is not the
    identity of this claim.  Letting its fingerprint or statement enter the
    structural/defeq gates turns similarity into a false theorem constraint.
    """
    if not isinstance(reference, dict) or reference.get("exact") is not True:
        return None, ""
    return reference.get("fingerprint"), str(reference.get("statement") or "")


@dataclass(frozen=True)
class AutoformalizeSolveConfig:
    """Entry config for `autoformalize_and_solve`.

    Adapter over the existing keyword surface. Callers stay unchanged; the
    function normalizes its scalar knobs once at entry.
    """
    timeout_s: int = 600
    max_refines: int = 2
    def_faithfulness: bool = False
    reformulate_budget: Optional[int] = None
    literal_first_done: bool = False
    strengthening_mode: bool = False

    @classmethod
    def from_boundary(
        cls,
        *,
        timeout_s: int = 600,
        max_refines: int = 2,
        def_faithfulness: bool = False,
        reformulate_budget: Optional[int] = None,
        literal_first_done: bool = False,
        strengthening_mode: bool = False,
    ) -> "AutoformalizeSolveConfig":
        def _int_at_least(value, default: int, floor: int) -> int:
            try:
                return max(floor, int(value))
            except (TypeError, ValueError):
                return default

        rb = None
        if reformulate_budget is not None:
            rb = _int_at_least(reformulate_budget, 0, 0)
        return cls(
            timeout_s=_int_at_least(timeout_s, 600, 1),
            max_refines=_int_at_least(max_refines, 2, 0),
            def_faithfulness=bool(def_faithfulness),
            reformulate_budget=rb,
            literal_first_done=bool(literal_first_done),
            strengthening_mode=bool(strengthening_mode),
        )


_OPENERS = {"(": ")", "{": "}", "[": "]", "⦃": "⦄"}
_CONC_OPS = ["↔", "≤", "≥", "<", ">", "=", "∣"]  # checked longest-first; '=' last so '≤' isn't split


_PROP_MARKERS = re.compile(r"[≤<≥>=∈∣↔→∧∨¬≠]|\bPrime\b|\.Prime\b|IsHermitian|PosSemidef|"
                           r"\bOdd\b|\bEven\b|Nonneg|Dvd|\bTrue\b|\bFalse\b")


def _consume_binders(s: str) -> "tuple[list, str]":
    """From `theorem name <binders> : <conclusion> := …` consume the LEADING balanced binder groups.
    Returns (groups, remainder_at_conclusion_colon) where each group is (kind_char, inner_text).
    Purely lexical, depth-tracked, bounded — no Lean parse."""
    import re as _re  # local: module `re` imported at top
    groups: list = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c in _OPENERS:
            depth = 0
            j = i
            while j < n:
                cj = s[j]
                if cj in _OPENERS:
                    depth += 1
                elif cj in (")", "}", "]", "⦄"):
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            groups.append((c, s[i + 1:j]))
            i = j + 1
            continue
        break
    return groups, s[i:]


def _split_binder(inner: str) -> "tuple[list, str]":
    """`hA : A.IsHermitian` → (['hA'], 'A.IsHermitian'); `{A B : Matrix n n ℝ}` → (['A','B'], 'Matrix…');
    `(i)` → (['i'], ''); `[DecidableEq n]` → ([], 'DecidableEq n'). Split on the FIRST top-level ':'."""
    depth = 0
    for k, ch in enumerate(inner):
        if ch in "([{⦃":
            depth += 1
        elif ch in ")]}⦄":
            depth -= 1
        elif ch == ":" and depth == 0:
            return inner[:k].split(), inner[k + 1:].strip()
    return inner.split(), ""


def _quantifier_sequence(conclusion: str) -> list:
    """The order of ∀/∃ at paren-depth 0 in the conclusion, e.g. `∀ t, ∃ C, P` → ['∀','∃']. A REORDER
    (∀∃ vs ∃∀) is a real weakening that leaves the ∀/∃ PRESENCE booleans unchanged."""
    depth = 0
    seq = []
    for ch in conclusion:
        if ch in "([{⦃":
            depth += 1
        elif ch in ")]}⦄":
            depth -= 1
        elif depth == 0 and ch in ("∀", "∃"):
            seq.append(ch)
    return seq


def _top_level_conclusion_op(conclusion: str) -> "str | None":
    """The dominant comparator of the conclusion at PAREN-depth 0 (so `(a < b) → c`'s top op is the
    arrow, not `<`). Returns one of _CONC_OPS, or '→'/'∧'/'∨' for connective conclusions, else None."""
    depth = 0
    found = None
    for ch in conclusion:
        if ch in "([{⦃":
            depth += 1
        elif ch in ")]}⦄":
            depth -= 1
        elif depth == 0:
            if ch in ("→", "∧", "∨", "↔"):
                return ch  # a connective conclusion dominates a buried comparator
            if found is None and ch in _CONC_OPS:
                found = ch
    return found


def _parse_lean_statement(stmt: str) -> dict:
    """Lexical structural fingerprint of a Lean theorem/lemma statement (no kernel). Extracts the
    binder counts, the conclusion text + its top-level comparator/connective, and whether ∀/∃ appear.
    Used by `structural_faithfulness` to detect silent weakening (dropped hypothesis / relaxed
    conclusion / quantifier swap) INDEPENDENT of the charitable round-trip judge."""
    import re
    s = (stmt or "").strip()
    m = re.match(r"\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+|noncomputable\s+)*"
                 r"(?:theorem|lemma|example|def)\s+([A-Za-z_][\w'.]*)?", s)
    body = s[m.end():] if m else s
    groups, rest = _consume_binders(body)
    n_groups = len(groups)
    n_explicit = sum(1 for k, _ in groups if k == "(")
    binder_names: list = []
    data_binder_names: list = []   # data/variable binders (NOT prop hypotheses) — candidates for "decorative"
    hyp_prop_texts: list = []      # the Prop-typed binder types
    binder_types: list = []        # ALL non-empty binder types — for circular / degeneracy detection
    for kind, inner in groups:
        names, typ = _split_binder(inner)
        binder_names.extend(names)
        if typ:
            binder_types.append(typ.strip())
        is_prop = bool(_PROP_MARKERS.search(typ)) if typ else False
        if is_prop:
            hyp_prop_texts.append(typ.strip())
        else:
            data_binder_names.extend(names)
    rest = rest.lstrip()
    conclusion = ""
    if rest.startswith(":"):
        rest = rest[1:]
        # conclusion runs up to the top-level ':=' (proof) — track depth so ':=' inside a term is safe
        depth = 0
        end = len(rest)
        k = 0
        while k < len(rest) - 1:
            ch = rest[k]
            if ch in "([{⦃":
                depth += 1
            elif ch in ")]}⦄":
                depth -= 1
            elif depth == 0 and ch == ":" and rest[k + 1] == "=":
                end = k
                break
            k += 1
        conclusion = rest[:end].strip()
    return {
        "n_binder_groups": n_groups,
        "n_explicit_binders": n_explicit,
        "conclusion": conclusion,
        "conclusion_op": _top_level_conclusion_op(conclusion),
        "has_forall": ("∀" in s) or bool(re.search(r"\bforall\b", s)),
        "has_exists": ("∃" in s) or bool(re.search(r"\bexists\b", s)),
        "binder_names": binder_names,
        "data_binder_names": data_binder_names,
        "hyp_prop_texts": hyp_prop_texts,
        "binder_types": binder_types,
        "quantifier_sequence": _quantifier_sequence(conclusion),
    }


def structural_faithfulness(nl: str, lean_statement: str, *, expected: "Optional[dict]" = None) -> bool:
    """Deterministic structural carrier (the HIGH-4 organ): True iff the Lean statement preserves the
    NL's structure — no silently DROPPED/ADDED hypothesis, no RELAXED conclusion comparator, no
    quantifier SWAP. When `expected` is supplied (the faithful reference fingerprint: any of
    n_binder_groups / n_explicit_binders / conclusion_op / has_forall / has_exists), the candidate is
    compared key-by-key and ANY deviation ⇒ False (strict, fail-closed — a false ACCEPT here is a
    fabricated target). With no `expected`, this is ADVISORY-True (the round-trip judge is then the only
    weakening defense) — production wiring SHOULD pass the reference fingerprint derived from a trusted
    formalization or the NL spec. Reuses no kernel; it is the genuinely-new NL↔Lean structure diff."""
    fp = statement_fingerprint(lean_statement)   # SINGLE DOOR — targets the theorem, not a multi-decl blob's leading def
    if not expected:
        return True
    for key, want in expected.items():
        if key not in fp:
            continue
        if fp[key] != want:
            return False
    return True


def _kernel_defeq_to_reference(candidate_stmt: str, reference_stmt: str, lean_root) -> bool:
    """KERNEL accept-override for the cross-run FaithfulnessStore (2026-07-02 general-purpose fix). The store's
    SYNTACTIC fingerprint false-rejects a faithful RESTYLE of a stored confirmed-faithful reference — ∀-fronted
    vs binders-after-colon, implicit `{x}` vs explicit `(x)`, binder ORDER, an inferable instance — because those
    change the fingerprint but NOT the Prop. So a different model (or the same model on a rerun) formalizing the
    SAME target in a different style recurs as a false-reject (the median-voter incident). When the fingerprint
    mismatches, ask the kernel whether the candidate's type is DEFINITIONALLY EQUAL to the stored reference: defeq
    is invariant to every faithful restyle, while a real weakening (dropped/added hypothesis, relaxed conclusion)
    is a TYPE mismatch ⇒ NOT defeq ⇒ still rejected. Reuses the ONE oracle `kernel_type_equiv_fn` (now section-
    variable-aware). FAIL-CLOSED: any infra failure ⇒ False (the syntactic verdict stands; never a laundering hole)."""
    if not (candidate_stmt or "").strip() or not (reference_stmt or "").strip() or lean_root is None:
        return False
    try:
        from ztare.leanmill.solver.statement_integrity import kernel_type_equiv_fn
        from ztare.leanmill.lean_source import extract_signature, theorem_names
        cn = (theorem_names(candidate_stmt) or [""])[-1]
        rn = (theorem_names(reference_stmt) or [""])[-1]
        if not cn or not rn:
            return False
        csig, rsig = extract_signature(candidate_stmt, cn), extract_signature(reference_stmt, rn)
        if not csig.strip() or not rsig.strip():
            return False
        nm = "_faithref_eq_probe"
        eq = kernel_type_equiv_fn(nm, lean_root)
        if eq is None:
            return False
        return bool(eq(f"theorem {nm} {rsig} := by sorry", f"theorem {nm} {csig} := by sorry"))
    except Exception:  # noqa: BLE001 — fail-CLOSED: the syntactic reject stands, never a false accept
        return False


def semantic_instance_battery(formalization: str, predicate: str, cases: "list[tuple[str, bool]]",
                              *, compile_probe: "Callable[[str], bool]") -> bool:
    """GROUND-TRUTH-BINDING faithfulness leg (KERNEL-grade — the non-math-enabling carrier). The
    formalization's `predicate`, applied to concrete human-LABELLED instances, must DECIDE to the labelled
    truth: for each `(instance, expected)` the probe `example : (¬)?(predicate instance) := by decide`
    must compile. A formalization silently WEAKENED / BROADENED (∧→∨, dropped clause, flipped comparator,
    swapped role) misclassifies ≥1 labelled instance ⇒ its probe fails to compile ⇒ this leg returns
    False. This is the carrier the round-trip judge (consensus-grade) and the structural diff (syntactic)
    cannot supply — the difference between 'two models agree it's the same problem' and 'the predicate
    returns the human-labelled answer on concrete cases'. It is also the only leg that binds the formal
    statement to GROUND TRUTH (the firewall's documented faithfulness ceiling).

    Requires a DECIDABLE predicate (access policies / arithmetic thresholds / boolean compliance rules —
    the non-math sweet spot). For an undecidable / universally-quantified math claim pass `cases=[]` and
    the leg is skipped (returns True; the consensus/structural legs remain the defense). FAIL-CLOSED: one
    wrong OR unverifiable decision ⇒ False (a probe that won't `decide` is not a positive ground-truth
    signal, so it must not admit)."""
    if not cases:
        return True
    # AXIOM-CLEAN by default (2026-06-09): `decide | norm_num | simp_all` keep the ground-truth certificate
    # inside the kernel allowlist {propext, Classical.choice, Quot.sound}. `norm_num` (not bare `decide`)
    # is what handles `Nat.Prime`/large-arithmetic instances — bare `decide` builds an inefficient proof
    # term and chokes (the "decide is shit" failure). `native_decide` is OPT-IN ONLY
    # (`ZTARE_LEANMILL_BATTERY_NATIVE_DECIDE=1`): it adds `Lean.ofReduceBool` (compiler-trust, OUTSIDE the
    # allowlist), so a battery cert that relied on it is NOT kernel-clean — which would undercut the
    # firewall's whole "verifiable kernel certificate" value. Off by default ⇒ the cert is auditable.
    _nd = " | native_decide" if os.environ.get("ZTARE_LEANMILL_BATTERY_NATIVE_DECIDE") == "1" else ""
    for instance, expected in cases:
        guard = "" if expected else "¬ "
        probe = (f"{formalization.rstrip()}\n\n"
                 f"example : {guard}({predicate} {instance}) := by\n"
                 f"  first | decide | norm_num | simp_all{_nd}\n")
        if compile_probe(probe) is not True:
            return False
    return True


def provable_equivalence(prelude: str, predicate: str, binder: str, domain_type: str,
                         body_ref: str, body_cand: str, *, compile_probe: "Callable[[str], bool]") -> bool:
    """KERNEL-grade EXHAUSTIVE faithfulness for a FINITE decidable domain — the '100%' leg. Are two
    formalizations of `predicate` (Lean bodies `body_ref` = a TRUSTED reference, `body_cand` = the
    candidate; both over `(binder : domain_type)`) PROVABLY EQUIVALENT on EVERY element? Compiles
    `example : ∀ <binder> : <domain_type>, ref <binder> ↔ cand <binder> := by decide`. When `domain_type`
    is a `Fintype` with `DecidableEq`, this `decide` ENUMERATES the whole domain — every input checked —
    so a True verdict is a genuine 100%-faithfulness certificate ON THAT FINITE DOMAIN (strictly stronger
    than a finite labelled battery, which only samples). Two faithful renderings are equivalent (compiles);
    a silently weakened/broadened one is NOT (a disagreeing element makes the ∀-iff false ⇒ no compile).
    The reference can be a human-checked formalization OR the majority of N independent samples (consensus
    promoted to a kernel-checked equivalence — the upgrade from 'judges agree' to 'provably the same')."""
    # `abbrev` (reducible), NOT `def` (semireducible): `decide` must unfold the predicate to synthesize its
    # `Decidable` instance — a `def` blocks instance synthesis and the ∀-iff silently fails to compile for
    # EVERY candidate (a false-negative that makes even a genuinely-equivalent body look non-equivalent).
    probe = (f"{prelude.rstrip()}\n\n"
             f"abbrev {predicate}_ref ({binder} : {domain_type}) : Prop := {body_ref}\n"
             f"abbrev {predicate}_cand ({binder} : {domain_type}) : Prop := {body_cand}\n\n"
             f"example : ∀ {binder} : {domain_type}, "
             f"{predicate}_ref {binder} ↔ {predicate}_cand {binder} := by decide\n")
    return compile_probe(probe) is True


@dataclass
class FaithfulnessVerdict:
    accepted: bool
    reason: str
    checks: dict = field(default_factory=dict)   # compiles / non_trivial / round_trip_faithful


@dataclass
class AutoformalizeResult:
    nl: str
    lean_statement: str
    verdict: FaithfulnessVerdict

    @property
    def is_target(self) -> bool:
        return self.verdict.accepted and bool(self.lean_statement.strip())


def _target_signature(stmt: str) -> str:
    """The TARGET theorem's signature (binders + conclusion, NO `:=` body) of a possibly-MULTI-DECL
    `define_then_state` statement — the LAST theorem/lemma, mirroring the solver's canonical `theorem_names[-1]`
    target selection. Fingerprinting the WHOLE blob (the raw-statement parser) parses the FIRST decl — a
    leading `def` — which masks the theorem's real binder count + conclusion (the 2026-06-23 GATE3 bug: a
    def + theorem blob fingerprinted 1-vs-1 binders instead of the theorem's 2-vs-4). THE single chokepoint for
    statement-level fingerprinting in the gate logic — route every fingerprint through here, never the raw blob.
    Falls back to the whole statement when there is no theorem/lemma (a bare single statement)."""
    try:
        from ztare.leanmill.lean_source import theorem_names, extract_signature
        names = theorem_names(stmt or "")
        if names:
            sig = extract_signature(stmt, names[-1])
            if (sig or "").strip():
                return sig
    except Exception:  # noqa: BLE001 — canonical parser unavailable ⇒ fall back to the whole statement
        pass
    return stmt or ""


def _hypotheses_of(sig: str) -> str:
    """The binder/hypothesis portion of a signature (everything BEFORE the top-level type `:`), whitespace-
    normalized. "" if unparseable. Used to detect whether a reformulation actually CHANGED the hypotheses (a
    correction) vs merely re-stated / unfolded the conclusion with the SAME — still-refuted — hypotheses."""
    try:
        from ztare.leanmill.lean_source import top_level_colon
        i = top_level_colon(sig or "")
        return " ".join((sig[:i] if i >= 0 else sig).split())
    except Exception:  # noqa: BLE001
        return ""


def statement_fingerprint(stmt: str) -> dict:
    """THE SINGLE ENTRY DOOR for fingerprinting a (possibly MULTI-DECL `define_then_state`) statement — the
    anti-sibling chokepoint (2026-06-23). EVERY gate / decision / reference that needs a statement's structural
    fingerprint MUST call THIS, never `_parse_lean_statement` on the raw blob: the raw-blob parser reads the FIRST
    decl (a leading `def`), masking the TARGET theorem's binders + conclusion. The recurring bug (GATE2/GATE3 +
    the structural-faithfulness + reference-fingerprint siblings) was exactly the same line — `_parse_lean_statement
    (whole_statement)` — copied to five sites; this collapses them to one door so a new caller cannot forget to
    target. `_parse_lean_statement` stays the low-level SIGNATURE parser (called here on the already-extracted
    `_target_signature`, and on bare sigs in tests) — it is NOT a statement fingerprinter. Guarded in CI
    (`test_firewall_gates_validated_on_production_shape_not_toys`)."""
    return _parse_lean_statement(_target_signature(stmt))


def _licensed_strengthening_admit(nl: str, stmt: str, checks: dict) -> "str | None":
    """DISCLOSED-STRENGTHENING (refute-and-correct, 2026-06-23) — the ONLY path that admits a formalization the
    round-trip judge rejects as 'weakened vs the literal NL'. It is the SIBLING of the `prior_confirmed`
    round-trip bypass (a narrow, fail-CLOSED conditional, NOT a parallel admit surface), and it reuses existing
    signals only — the one refutation ledger, the firewall's own `non_vacuous`/`non_trivial` legs, the existing
    fingerprint parser. Rationale: when the NL's LITERAL claim is kernel-FALSE, the true theorem MUST add a
    hypothesis; that is a faithful CORRECTION, not laundering. Returns a DISCLOSURE string (the delta) to ADMIT,
    or None to keep the rejection (the default). Every gate is non-fakeable; ANY uncertainty ⇒ None.
    ZTARE_LEANMILL_DISCLOSED_STRENGTHENING=0 reverts to never-override (byte-parity)."""
    if os.environ.get("ZTARE_LEANMILL_DISCLOSED_STRENGTHENING", "1") == "0":
        return None
    # GATE 1 — the ¬G LICENSE + comparand: the literal NL's formalization is KERNEL-PROVED FALSE (recorded
    # `statement_false` in the ONE refutation ledger; surfaced via the faithfulness store's `refuted_literal`).
    # Non-fakeable — the record exists only because a kernel ¬G was confirmed at the single chokepoint. No
    # license ⇒ no override (the firewall stays strict). `refuted` is also the comparand for the strengthening.
    refuted = ""
    try:
        from ztare.leanmill.solver.faithfulness_store import FaithfulnessStore
        from ztare.leanmill.solver.solver_core import OUT_DIR as _OUT
        refuted = FaithfulnessStore(_OUT / "solver_lane_faithfulness_store.jsonl").refuted_literal(nl)
    except Exception:  # noqa: BLE001 — no store ⇒ no license ⇒ no override (safe / byte-parity)
        return None
    if not (refuted or "").strip():
        return None
    # GATE 2 — NON-TRIVIAL (+ NON-VACUOUS when supplied): reject a vacuous or cheap-tactic (goal-as-hypothesis)
    # "strengthening". `non_trivial` is the LOAD-BEARING leg here because it ALWAYS runs in production AND already
    # subsumes the vacuity check: `default_triviality` is True (⇒ non_trivial False) when cheap tactics close it
    # (a contradictory added hypothesis ⇒ `simp_all`/`omega` derives False), OR `nondegenerate_instance_probe`
    # confirms NO satisfying instance exists (hidden vacuity = contradictory hypotheses). So `non_trivial is True`
    # already clears the same vacuity bar every admitted formalization clears. The dedicated `non_vacuous`
    # (consistency) leg is OPTIONAL (the production `autoformalize_and_solve` path supplies no `consistency_fn`, so
    # the key is ABSENT there) — require non_trivial, and additionally reject only if a SUPPLIED consistency leg
    # explicitly found a contradiction (`non_vacuous is False`). Fail-closed: an absent non_vacuous relies on the
    # always-run non_trivial; it never weakens the bar. [2026-06-23: was `non_vacuous is not True`, which could
    # never pass in production — the key was never populated — so the override was DEAD end-to-end. Unit test
    # injected the key directly and missed the integration gap.]
    if checks.get("non_trivial") is not True or checks.get("non_vacuous") is False:
        return None
    # GATE 3 — a faithful CORRECTION of the refuted claim, fingerprinted on the TARGET THEOREM (via
    # `_target_signature`, the canonical LAST theorem/lemma), NEVER `_parse_lean_statement` on the whole multi-decl
    # `define_then_state` blob (which parses the leading `def`: the 2026-06-23 GATE3 bug, 1-vs-1 binders instead of
    # 2-vs-4). GOLDILOCKS, not brittle determinism: the override is PERMISSIVE on PURPOSE — its only job is to let
    # the agent's correction PROCEED past the literal-faithfulness round-trip VETO once the literal is kernel-FALSE;
    # the DOWNSTREAM KERNEL PROOF + the DISCLOSURE are the real soundness boundary, not a syntactic strengthening
    # oracle. So the checks are COARSE + ROBUST (tolerate unfolding / reordering / def-swaps; NO regex, NO text-
    # identity match — only canonical `lean_source` binder/colon primitives), failing CLOSED only on the
    # unambiguous NON-corrections:
    #   (a) the HYPOTHESES actually CHANGED — a candidate that re-states / unfolds the conclusion with the SAME
    #       (still-refuted) hypotheses is NOT a correction; admitting it would only burn a solve on the known-false
    #       claim (this is what rejected the prior run's "unfolded, not strengthened" reformulation);
    #   (b) it does NOT DROP hypotheses (target binders ≥ the refuted's) — a pure weakening is rejected;
    #   (c) the conclusion connective is not PLAINLY weakened (a clear ∧→∨-class change) when BOTH are parseable.
    hyp_s, hyp_r = _hypotheses_of(_target_signature(stmt)), _hypotheses_of(_target_signature(refuted))
    if not hyp_s or hyp_s == hyp_r:                       # hypotheses unchanged ⇒ a re-statement, not a correction
        return None
    fp_s, fp_r = statement_fingerprint(stmt), statement_fingerprint(refuted)   # SINGLE DOOR (targets the theorem)
    n_s, n_r = (fp_s.get("n_explicit_binders") or 0), (fp_r.get("n_explicit_binders") or 0)
    if n_s < n_r:                                         # dropped hypotheses ⇒ a weakening, reject
        return None
    _op_s, _op_r = fp_s.get("conclusion_op"), fp_r.get("conclusion_op")
    if _op_s is not None and _op_r is not None and _op_s != _op_r:   # a clear conclusion-connective change ⇒ reject
        return None
    _delta = f"binders {n_r}→{n_s}" if n_s != n_r else "hypothesis strengthened in place (def-swap, same arity)"
    return (f"disclosed correction of a kernel-refuted literal ({_delta}; conclusion connective preserved) — "
            "the downstream kernel proof is the arbiter")


def faithfulness_gate(nl: str, lean_statement: str, *,
                      compile_fn: "Callable[[str], bool]",
                      triviality_fn: "Callable[[str], bool]",
                      backtranslate_fn: "Callable[[str], str]",
                      judge_fn: "Callable[[str, str], bool]",
                      consistency_fn: "Optional[Callable[[str], bool]]" = None,
                      structural_fn: "Optional[Callable[[str, str], bool]]" = None,
                      battery_fn: "Optional[Callable[[str], bool]]" = None,
                      crossvote_fn: "Optional[Callable[[str, str], bool]]" = None,
                      prior_confirmed_fn: "Optional[Callable[[str, str], bool]]" = None) -> FaithfulnessVerdict:
    """The firewall. ALL injected fns MUST return strict `bool`. compile_fn(stmt)->typechecks-with-
    sorry; triviality_fn(stmt)->closeable-by-cheap-tactics(goal AND context, e.g. simp_all/omega);
    consistency_fn(stmt)->hypotheses-mutually-CONSISTENT (False ⇒ vacuous; reuse
    `governance_organs.randomized_differential_probe` / a derive-False probe); backtranslate_fn(stmt)
    ->NL; judge_fn(orig_nl, back_nl)->does-proving-the-candidate-ESTABLISH-the-original (DIRECTIONAL-for-
    proving — see contract below).

    FAIL-CLOSED on EVERY leg: a formalization is admitted only on a POSITIVE signal; ANY inconclusive,
    errored, or non-canonical-True result ⇒ NOT admitted. Opposite of the prover gates, because here a
    false ACCEPT is a fabricated success.

    judge_fn CONTRACT (HIGH-4/MEDIUM-3, enforce in the PRODUCTION wiring, not here): the judge is
    DIRECTIONAL-FOR-PROVING — "would PROVING the candidate ESTABLISH the original's claim?" — accept a
    STRONGER-or-equal CONCLUSION (incl. a CONSTRUCTIVE witness for an ∃-goal — proving a specific F for
    `∃F,F'=f` is faithful, NEVER a launder: proving more is harder, not easier) on the SAME-or-weaker
    HYPOTHESES; REJECT a WEAKER/changed conclusion (≤→<, =→≤, ∀→∃) or a DROPPED/ADDED/RESTRICTED hypothesis
    (narrowed domain, assumed splitting). [2026-06-11: was strict EQUIVALENCE, which wrongly REJECTED a
    faithful constructive formalization — equivalence is over-strict on the ADMIT side for a PROVING firewall.]
    It must be a COLD cross-family judge (family ≠ the formalizer's), ideally ≥2 unanimous; and the
    deterministic structural diff (`statement_integrity`) on the hypothesis set / conclusion shape OVERRIDES a
    charitable judge (it still rejects a hypothesis change). The NL-vs-NL paraphrase judge alone is NOT
    sufficient for hard targets."""
    checks: dict = {}
    stmt = (lean_statement or "").strip()
    if not stmt:
        return FaithfulnessVerdict(False, "empty formalization", checks)

    try:
        checks["compiles"] = _is_true(compile_fn(stmt))
    except Exception as e:
        return FaithfulnessVerdict(False, f"compile check errored ⇒ not admitted (fail-closed): {repr(e)[:80]}", checks)
    if not checks["compiles"]:
        return FaithfulnessVerdict(False, "does not typecheck (or compile inconclusive) — malformed formalization", checks)

    # SUBSTRATE-FIDELITY — an ENTRY gate (2026-07-05, operator "make sure no gaming enters the store" / "single
    # point"). When a campaign substrate is registered, a SELF-CONTAINED re-formalization that DRIFTS from it — a
    # WEAKER carrier order ([LinearOrder K] → bare [LT K][LE K], the CLOB carrier-ghost) OR a divergent def body — is
    # a DIFFERENT theorem, UNFAITHFUL to the theory it claims to extend and a laundering vector INTO the store that
    # downstream semantic reuse would then TRUST. Reject it here, at entry, through the ONE `substrate_infidelities`
    # door the falsify gate and the reuse-store retrieval also use (one drift definition, three enforcement sites —
    # never again a per-site subset). Deterministic (no LLM). No-op off-campaign / when the probe CITES the substrate
    # instead of re-declaring it. ADDITIVE + fail-OPEN on a read/parse error (never breaks the firewall on tooling).
    try:
        from ztare.formal.repl_compile import get_campaign_substrate as _gcs_fw
        _cs_fw = _gcs_fw()
        if _cs_fw:
            from pathlib import Path as _P_fw
            from ztare.leanmill.lean_source import substrate_infidelities as _sinf_fw
            _drift_fw = _sinf_fw(stmt, _P_fw(_cs_fw).read_text(encoding="utf-8", errors="replace"))
            if _drift_fw:
                checks["substrate_infidelities"] = _drift_fw
                return FaithfulnessVerdict(
                    False, f"UNFAITHFUL to the registered substrate ({_drift_fw[:2]}) — a self-contained re-"
                    "declaration that weakens the carrier or diverges a def body is a DIFFERENT theorem (the ghost "
                    "laundering vector); rejected at entry so no drifted statement is ever banked + then trusted by "
                    "reuse", checks)
    except Exception:  # noqa: BLE001 — additive entry gate; a tooling failure must NOT break the firewall
        pass

    # FAIL-CLOSED on the triviality leg too (was the lone fail-open path — review HIGH-2).
    try:
        trivial = _is_true(triviality_fn(stmt))
    except Exception as e:
        return FaithfulnessVerdict(False, f"triviality probe errored ⇒ not admitted (fail-closed): {repr(e)[:80]}", checks)
    checks["non_trivial"] = not trivial
    if trivial:
        # SAFE handling of the cold-agent "compliance is mathematically trivial" point (2026-06-09): real
        # policy/IAM/legal rules ARE simple (threshold inequalities), so theorem-triviality mis-fires. But
        # do NOT disable the check (that admits `permit := True` always-allow — a vacuity laundering hole).
        # Instead, when a GROUND-TRUTH BATTERY is supplied, DEFER to it: a battery that decides the labelled
        # allow/deny instances correctly already rules out vacuity (an always-true predicate misclassifies the
        # deny cases ⇒ battery FAILS later). With no battery (the math regime) triviality stays FATAL.
        if battery_fn is not None:
            checks["non_trivial_deferred_to_battery"] = True
        else:
            return FaithfulnessVerdict(False, "closed by a cheap tactic — degenerate / not the hard problem", checks)

    # Vacuity: contradictory hypotheses ⇒ vacuously true (ex falso). Optional probe (reuse the SZ /
    # derive-False organ); if not supplied the round-trip is the only vacuity defense (weaker).
    if consistency_fn is not None:
        try:
            consistent = _is_true(consistency_fn(stmt))
        except Exception as e:
            return FaithfulnessVerdict(False, f"consistency probe errored ⇒ not admitted (fail-closed): {repr(e)[:80]}", checks)
        checks["non_vacuous"] = consistent
        if not consistent:
            return FaithfulnessVerdict(False, "hypotheses mutually contradictory — vacuously true (ex falso)", checks)

    # STRUCTURAL carrier (iso + lossless round-trip, surfaced by the isomorphism engine on the
    # faithfulness ceiling): a deterministic-ish check INDEPENDENT of the charitable round-trip judge —
    # the formalization must preserve the NL's hypothesis set + conclusion (no silently DROPPED or ADDED
    # hypothesis, no WEAKENED conclusion ≤→< / =→≤ / ∀→∃). This is the HIGH-4 fix: it can OVERRIDE a
    # judge that smooths over weakening. Reuses `statement_integrity` (Lean-side structure) in production.
    if structural_fn is not None:
        try:
            preserved = _is_true(structural_fn(nl, stmt))
        except Exception as e:
            return FaithfulnessVerdict(False, f"structural check errored ⇒ not admitted (fail-closed): {repr(e)[:80]}", checks)
        checks["structure_preserved"] = preserved
        if not preserved:
            return FaithfulnessVerdict(False, "structure NOT preserved — dropped/added hypothesis or weakened conclusion (silent weakening)", checks)

    # GROUND-TRUTH carrier (KERNEL-grade, non-math-enabling): the predicate, applied to human-labelled
    # concrete instances, must DECIDE to the labelled truth. Binds the formal statement to reality the
    # consensus round-trip and the syntactic structural diff cannot. Strongest single faithfulness leg
    # where the domain is decidable; skipped (no-op True) when no cases are supplied. Fail-closed.
    if battery_fn is not None:
        try:
            battery_ok = _is_true(battery_fn(stmt))
        except Exception as e:
            return FaithfulnessVerdict(False, f"instance battery errored ⇒ not admitted (fail-closed): {repr(e)[:80]}", checks)
        checks["instance_battery"] = battery_ok
        if not battery_ok:
            return FaithfulnessVerdict(False, "instance battery FAILED — predicate misclassifies a labelled instance (ground-truth-bound weakening/broadening)", checks)

    # PRIOR-CONFIRMED short-circuit (#105): an EXACT statement already CONFIRMED faithful for this NL need not
    # be re-litigated by the variance-prone round-trip JUDGE (the 2026-06-11 flaky judge false-rejected a
    # statement that had PASSED the prior run). SOUND: the deterministic legs above (compile / triviality /
    # consistency / structural / battery) ALREADY ran on THIS statement; this skips ONLY the LLM round-trip,
    # and only on an EXACT prior confirmation (prior_confirmed_fn returns True solely for the stored statement).
    _prior = False
    if prior_confirmed_fn is not None:
        try:
            _prior = _is_true(prior_confirmed_fn(nl, stmt))
        except Exception:  # noqa: BLE001 — a broken store never blocks the gate; fall through to the judge
            _prior = False
    if _prior:
        checks["round_trip_faithful"] = True
        checks["prior_confirmed"] = True
    else:
        try:
            back_nl = backtranslate_fn(stmt) or ""
            checks["round_trip_faithful"] = bool(_visible(back_nl)) and _is_true(judge_fn(nl, back_nl))
        except Exception as e:
            if isinstance(e, BudgetExceeded):
                checks["budget_exhausted"] = True
                return FaithfulnessVerdict(False, "BUDGET_EXHAUSTED", checks)
            return FaithfulnessVerdict(False, f"round-trip errored ⇒ NOT admitted (fail-closed): {repr(e)[:80]}", checks)
    if not checks["round_trip_faithful"]:
        # DISCLOSED-STRENGTHENING OVERRIDE (refute-and-correct, 2026-06-23) — a SIBLING of the `prior_confirmed`
        # round-trip bypass above, not a parallel admit surface. The round-trip CORRECTLY rejects a strengthening
        # as "weakened vs the literal NL" — but when the literal NL claim is kernel-FALSE, the true theorem MUST
        # add a hypothesis, and that is a faithful CORRECTION, not laundering. Admit ONLY under non-fakeable
        # gates (all in `_licensed_strengthening_admit`, fail-CLOSED): ¬G license + conclusion preserved + strictly
        # MORE hypotheses + non-vacuous + non-trivial; the correction is DISCLOSED in the verdict.
        _disc = _licensed_strengthening_admit(nl, stmt, checks)
        if _disc:
            checks["licensed_strengthening"] = _disc
            return FaithfulnessVerdict(True, f"licensed disclosed-strengthening of a kernel-refuted literal claim — {_disc}", checks)
        return FaithfulnessVerdict(False, "round-trip does NOT match the NL (or empty/degenerate) — unfaithful / weakened / vacuous", checks)

    # CROSS-VOTE carrier (kernel-grade CONSENSUS, optional — heaviest leg, so LAST): dispatch N DIVERSE
    # formalizers on the SAME NL and require the independent consensus to be kernel-equivalent to `stmt`.
    # Catches a single-formalizer systematic mistranslation the one-shot round-trip judge would bless
    # (the judge sees ONE back-translation; cross-vote sees N independent FORWARD formalizations and the
    # kernel adjudicates their agreement). FAIL-CLOSED like every other leg; flag-gated at the call site
    # (`crossvote_enabled()` decides whether crossvote_fn is supplied — default None ⇒ skipped, byte parity).
    if crossvote_fn is not None:
        try:
            agree = _is_true(crossvote_fn(nl, stmt))
        except Exception as e:
            return FaithfulnessVerdict(False, f"cross-vote errored ⇒ not admitted (fail-closed): {repr(e)[:80]}", checks)
        checks["cross_vote_consensus"] = agree
        if not agree:
            return FaithfulnessVerdict(False, "cross-vote DISAGREES — independent formalizers do not kernel-agree with this statement (systematic mistranslation)", checks)

    return FaithfulnessVerdict(True, "faithful: typechecks, non-trivial, (consistent,) round-trip matches the NL intent", checks)


def autoformalize(nl: str, *, formalize_fn: "Callable[[str], str]",
                  compile_fn: "Callable[[str], bool]",
                  triviality_fn: "Callable[[str], bool]",
                  backtranslate_fn: "Callable[[str], str]",
                  judge_fn: "Callable[[str, str], bool]",
                  consistency_fn: "Optional[Callable[[str], bool]]" = None,
                  structural_fn: "Optional[Callable[[str, str], bool]]" = None,
                  battery_fn: "Optional[Callable[[str], bool]]" = None,
                  crossvote_fn: "Optional[Callable[[str, str], bool]]" = None) -> AutoformalizeResult:
    """NL → candidate Lean statement → faithfulness gate. Returns the result; `.is_target` is True
    only for an ADMITTED faithful formalization. All steps injected (real apparatus in production,
    mocks in tests). The formalizer and the judge SHOULD be different model families (the judge is a
    cold cross-family check, never the formalizer blessing its own output)."""
    try:
        with _phase_timer("formalize"):
            lean_statement = (formalize_fn(nl) or "").strip()
    except Exception as e:
        return AutoformalizeResult(nl, "", FaithfulnessVerdict(False, f"formalizer errored: {repr(e)[:80]}"))
    from ztare.leanmill.solver.agentic_leaf import (
        BUDGET_EXHAUSTED_DISPATCH,
        INADMISSIBLE_DISPATCH,
    )
    if lean_statement == INADMISSIBLE_DISPATCH:                # #89: every provider dead ⇒ a DEAD INSTRUMENT,
        return AutoformalizeResult(nl, "",                    # not an unfaithful formalization. Skip the gate;
                                   FaithfulnessVerdict(False, "INADMISSIBLE_PROVIDER_DEAD"))  # caller marks inadmissible.
    if lean_statement == BUDGET_EXHAUSTED_DISPATCH:
        return AutoformalizeResult(nl, "", FaithfulnessVerdict(False, "BUDGET_EXHAUSTED"))
    verdict = faithfulness_gate(nl, lean_statement, compile_fn=compile_fn, triviality_fn=triviality_fn,
                                backtranslate_fn=backtranslate_fn, judge_fn=judge_fn,
                                consistency_fn=consistency_fn, structural_fn=structural_fn,
                                battery_fn=battery_fn, crossvote_fn=crossvote_fn)
    return AutoformalizeResult(nl, lean_statement, verdict)


def _formalize_feedback_hint(verdict: "FaithfulnessVerdict", prior_stmt: str, compile_error: str = "",
                             reference_statement: str = "", strengthening_mode: bool = False) -> str:
    """Turn the firewall's REJECTION into targeted NL guidance the formalizer can act on — the
    per-leg feedback that makes the refine loop close compile/faithfulness gaps instead of re-rolling.
    `compile_error` (optional, from `default_compile_diagnose`) is the ACTUAL Lean error so a compile-fail
    refine is GUIDED (fix THIS error) not blind (re-guess) — the convergence + burn fix. `strengthening_mode`
    (set during a REFORMULATION re-entry, where the literal was kernel-REFUTED) FLIPS the round-trip guidance:
    a round-trip mismatch is EXPECTED for a true correction (it is stronger than the literal), so the hint must
    NOT push "neither weaker nor stronger" (which fought the strengthening and made the agent re-emit the refuted
    reading — the 2026-06-23 refine↔reformulate conflict); it tells the agent to keep the stronger, true hypotheses."""
    checks = getattr(verdict, "checks", {}) or {}
    reason = getattr(verdict, "reason", "") or ""
    if checks.get("compiles") is False or "typecheck" in reason:
        guide = ("It did NOT typecheck. Fix the Lean 4 syntax / Mathlib API errors so `lake env lean` "
                 "reports zero `error:` lines (the `sorry` is fine). Keep the definitions; correct only what fails.")
        if (compile_error or "").strip():
            guide += ("\n\nThe Lean compiler reported (fix EXACTLY these, do not re-guess the whole statement):\n"
                      + compile_error.strip()[:600])
    elif checks.get("non_trivial") is False or "cheap tactic" in reason or "degenerate" in reason:
        guide = ("It was closed by a CHEAP tactic (degenerate / not the real problem). State the GENUINE "
                 "claim — non-vacuous, non-trivially-true.")
    elif checks.get("structure_preserved") is False or "weaken" in reason or "hypothesis" in reason:
        guide = ("It DROPPED/ADDED a hypothesis or WEAKENED the conclusion. Preserve EVERY hypothesis and "
                 "the EXACT conclusion; keep quantifier order.")
        # GUIDED weakening repair (2026-06-20): a weakening compiles fine, so there is no Lean error to feed
        # back — the generic guide above let the formalizer re-weaken (the lemma-2 partial-fraction case: it
        # dropped the `den/num = P + r/num` conjunct 5×). When a CONFIRMED-FAITHFUL rendering exists (the
        # faithfulness-store reference the structural check just rejected against), SHOW it so the agent
        # restores the exact dropped content. Sound: the firewall still re-gates every leg, so copying the
        # confirmed-faithful STATEMENT (not a proof) can only produce a faithful target, never launder.
        if (reference_statement or "").strip():
            guide += ("\n\nA CONFIRMED-FAITHFUL rendering of THIS lemma already exists — match its logical content "
                      "EXACTLY (every hypothesis AND every conjunct of the conclusion). You dropped/relaxed part of "
                      "it; restore that part:\n" + reference_statement.strip()[:800])
    elif checks.get("round_trip_faithful") is False or "round-trip" in reason:
        if strengthening_mode:
            guide = ("Its back-translation did not match the LITERAL problem — which is EXPECTED here: the literal "
                     "claim was KERNEL-REFUTED (false), so the TRUE theorem needs a STRONGER hypothesis. Do NOT weaken "
                     "back to the refuted literal reading; keep (or further strengthen) the corrected hypotheses and "
                     "keep the SAME conclusion. The engine admits a DISCLOSED strengthening of a refuted literal.")
        else:
            guide = ("Its back-translation did not match the problem. Re-formalize faithfully to the ORIGINAL "
                     "statement — neither weaker nor stronger.")
    else:
        guide = f"It was rejected: {reason}"
    return (f"\n\n[REFINE] Your previous formalization was REJECTED by the faithfulness firewall. {guide}\n"
            f"Your previous attempt (REPAIR it; reuse what is right, fix only the fault — do not restart):\n"
            f"{prior_stmt}\n")


def autoformalize_refine(nl: str, *, formalize_fn: "Callable[[str], str]",
                         compile_fn: "Callable[[str], bool]", triviality_fn: "Callable[[str], bool]",
                         backtranslate_fn: "Callable[[str], str]", judge_fn: "Callable[[str, str], bool]",
                         consistency_fn: "Optional[Callable[[str], bool]]" = None,
                         structural_fn: "Optional[Callable[[str, str], bool]]" = None,
                         compile_diagnose_fn: "Optional[Callable[[str], str]]" = None,
                         prior_confirmed_fn: "Optional[Callable[[str, str], bool]]" = None,
                         reference_statement: str = "",
                         max_refines: int = 2, strengthening_mode: bool = False) -> "tuple[AutoformalizeResult, list]":
    """Autoformalize through the shared RefineHandover loop — the compile-fix the one-shot `autoformalize`
    lacks (a real open-problem target produced a faithful-STRUCTURED but uncompiling formalization that the
    one-shot gate just rejected). On a firewall rejection, hand the formalizer back the verdict's failing leg + its prior
    attempt and re-formalize, bounded. SAME produce→feedback→refine shape as the solver's gap-refine, via
    the SAME driver. The faithfulness gate stays FAIL-CLOSED on every leg (the driver never accepts on a
    rejection). Returns (AutoformalizeResult, trace)."""
    from ztare.common.refine_handover import RefineHandover

    def _execution_stop_verdict(stmt: str):
        try:
            from ztare.leanmill.solver.agentic_leaf import (
                BUDGET_EXHAUSTED_DISPATCH,
                INADMISSIBLE_DISPATCH,
            )
            if stmt.strip() == BUDGET_EXHAUSTED_DISPATCH:
                return FaithfulnessVerdict(False, "BUDGET_EXHAUSTED")
            if stmt.strip() == INADMISSIBLE_DISPATCH:
                return FaithfulnessVerdict(False, "INADMISSIBLE_PROVIDER_DEAD")
        except Exception:  # noqa: BLE001
            pass
        return None

    def _gen(ctx):
        try:
            with _phase_timer("formalize"):   # cycle/lead-time telemetry: the NL→Lean dispatch (the dominant cost)
                return (formalize_fn((ctx.get("nl") or "") + (ctx.get("hint") or "")) or "").strip()
        except Exception as e:  # noqa: BLE001
            if isinstance(e, BudgetExceeded):
                from ztare.leanmill.solver.agentic_leaf import BUDGET_EXHAUSTED_DISPATCH
                return BUDGET_EXHAUSTED_DISPATCH
            return ""

    def _verify(stmt):
        stopped = _execution_stop_verdict(stmt)
        if stopped is not None:
            return stopped
        return faithfulness_gate(nl, stmt, compile_fn=compile_fn, triviality_fn=triviality_fn,
                                 backtranslate_fn=backtranslate_fn, judge_fn=judge_fn,
                                 consistency_fn=consistency_fn, structural_fn=structural_fn,
                                 prior_confirmed_fn=prior_confirmed_fn)

    def _refine_ctx(stmt, verdict, ctx):
        if (
            not (stmt or "").strip()
            or _execution_stop_verdict(stmt) is not None
            or str(getattr(verdict, "reason", "")) == "BUDGET_EXHAUSTED"
        ):
            return None                      # empty generation ⇒ nothing to repair from ⇒ stop
        cerr = ""
        if compile_diagnose_fn is not None and (getattr(verdict, "checks", {}) or {}).get("compiles") is False:
            try:
                cerr = compile_diagnose_fn(stmt) or ""    # the ACTUAL Lean error ⇒ guided (not blind) repair
            except Exception:  # noqa: BLE001 — advisory; never break the refine on a diagnose failure
                cerr = ""
        return {"nl": nl, "hint": _formalize_feedback_hint(verdict, stmt, cerr,
                                                            reference_statement=reference_statement,
                                                            strengthening_mode=strengthening_mode)}

    rh = RefineHandover(generate=_gen, verify=_verify, accept_when=lambda v: bool(v.accepted),
                        build_refine_context=_refine_ctx, max_refines=max_refines)
    stmt, verdict, trace = rh.run({"nl": nl, "hint": ""})
    return AutoformalizeResult(nl, stmt, verdict), trace


def reference_fingerprint(lean_statement: str) -> dict:
    """The structural fingerprint to pass as `expected=` — derive it from a TRUSTED formalization (a
    human-checked reference, or the cross-family-agreed candidate). Then `structural_faithfulness`
    flags any later candidate that deviates (dropped hyp / relaxed conclusion / quantifier swap)."""
    return statement_fingerprint(lean_statement)   # SINGLE DOOR (anti-sibling) — targets the theorem


def _cli_text(
    prompt: str,
    *,
    runtime: str,
    timeout_s: int,
    agent_tag: str = "faithfulness",
) -> str:
    """One round-trip completion via the SUBSCRIPTION CLI (codex/claude) — the SAME dispatch the solver uses
    (`agentic_leaf.default_dispatch`), NOT the metered API. Strips the CLI banner/transcript noise to the answer
    text. Returns '' on any failure ⇒ the caller falls back to the API (never a dead-instrument hard fail)."""
    try:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch
        import os as _os
        _repo = _os.environ.get("ZTARE_LEANMILL_LEAN_ROOT") or _os.getcwd()
        raw = default_dispatch(
            prompt,
            runtime=runtime,
            repo=_repo,
            timeout=int(timeout_s),
            agent_tag=agent_tag,
        ) or ""
        # the CLI echoes the PROMPT + prints the answer (often twice) + a token count. Strip the banner
        # (_CLI_NOISE), the prompt echo (lines that appear verbatim in `prompt`), pure-number/token-count lines,
        # then de-dup consecutive repeats — leaving the actual answer (a one-sentence back-translation or a judge
        # verdict). Robust to the CLI's transcript shape; empty ⇒ caller's API fallback fires.
        _pl = {l.strip() for l in prompt.splitlines() if l.strip()}
        out: "list[str]" = []
        for ln in raw.splitlines():
            s = ln.strip()
            if not s or _CLI_NOISE.match(s) or s in _pl:
                continue
            if re.fullmatch(r"[\d,\.]+", s):          # token-count / stray-number noise (e.g. "30,977")
                continue
            if out and out[-1] == s:                  # collapse the doubled-answer echo
                continue
            out.append(s)
        return "\n".join(out).strip()
    except Exception as exc:  # noqa: BLE001 — CLI unavailable ⇒ '' ⇒ API fallback
        if isinstance(exc, BudgetExceeded):
            raise
        return ""


def _roundtrip_cli_text(
    prompt: str,
    *,
    runtime: str,
    timeout_s: int,
    label: str,
) -> str:
    """Dispatch a reviewer CLI under its own frozen model/effort settings."""

    from contextlib import contextmanager

    @contextmanager
    def reviewer_config():
        model = os.environ.get("ZTARE_LEANMILL_ROUNDTRIP_AGENT_MODEL", "").strip()
        effort = os.environ.get(
            "ZTARE_LEANMILL_ROUNDTRIP_AGENT_REASONING_EFFORT", ""
        ).strip()
        bindings: dict[str, str] = {}
        if runtime == "codex":
            if model:
                bindings["ZTARE_CODEX_AGENT_MODEL"] = model
            if effort:
                bindings["ZTARE_CODEX_AGENT_REASONING_EFFORT"] = effort
        elif runtime == "claude":
            if model:
                bindings["ZTARE_CLAUDE_AGENT_MODEL"] = model
            if effort:
                bindings["ZTARE_CLAUDE_EFFORT"] = effort
        prior = {key: os.environ.get(key) for key in bindings}
        os.environ.update(bindings)
        try:
            yield
        finally:
            for key, value in prior.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                        os.environ[key] = value

    @contextmanager
    def reviewer_dispatch_identity():
        from ztare.common.subscription_agent_runtime import (
            subscription_dispatch_provenance_active,
            subscription_dispatch_role_scope,
        )

        if not subscription_dispatch_provenance_active():
            yield
            return
        agent_id = os.environ.get(
            "ZTARE_LEANMILL_ROUNDTRIP_AGENT_ID", ""
        ).strip()
        model = os.environ.get(
            "ZTARE_LEANMILL_ROUNDTRIP_AGENT_MODEL", ""
        ).strip()
        effort = os.environ.get(
            "ZTARE_LEANMILL_ROUNDTRIP_AGENT_REASONING_EFFORT", ""
        ).strip()
        config_sha256 = os.environ.get(
            "ZTARE_LEANMILL_ROUNDTRIP_CONFIG_SHA256", ""
        ).strip()
        run_tag = os.environ.get(
            "ZTARE_LEANMILL_ROUNDTRIP_RUN_TAG", ""
        ).strip()
        with subscription_dispatch_role_scope(
            role="faithfulness_reviewer",
            agent_id=agent_id,
            run_tag=run_tag,
            runtime=runtime,
            model=model,
            reasoning_effort=effort,
            config_sha256=config_sha256,
            record_empty_attempt=True,
        ):
            yield

    effective_timeout_s = int(timeout_s)
    reviewer_timeout = os.environ.get(
        "ZTARE_LEANMILL_ROUNDTRIP_TIMEOUT_S", ""
    ).strip()
    if reviewer_timeout:
        effective_timeout_s = min(effective_timeout_s, int(reviewer_timeout))
    if effective_timeout_s < 1:
        raise ValueError("round-trip reviewer timeout must be positive")

    with reviewer_config(), reviewer_dispatch_identity():
        return _cli_text(
            prompt,
            runtime=runtime,
            timeout_s=effective_timeout_s,
            agent_tag=label,
        )


def _api_text(prompt: str, *, model: "Optional[str]" = None, label: str, timeout_s: int = 120) -> str:
    """One round-trip completion, provider-routed by MODEL ID (general, 2026-07-05 — operator "codex via CLI not
    API, and general across families"): a SUBSCRIPTION id (`codex`/`claude`) dispatches via the SAME CLI the
    solver uses; any other id (`gemini-…`/`deepseek-…`) via the metered `LLMRuntime` API. So
    `ZTARE_LEANMILL_ROUNDTRIP_MODEL=codex` ⇒ CLI-codex (no metered spend), `=deepseek-chat` ⇒ API — one selector,
    every family. Falls back API-on-empty-CLI (resilience). For the mechanical legs (back-translate, judge) — NOT
    formalize. `model=None` ⇒ the configured round-trip model."""
    model = model or _roundtrip_model()
    if (model or "").startswith(("codex", "claude")):        # subscription CLI family ⇒ the solver's dispatch
        _t = _roundtrip_cli_text(
            prompt,
            runtime=model,
            timeout_s=timeout_s,
            label=label,
        )
        if _t.strip():
            return _t
        if os.environ.get("ZTARE_LEANMILL_ROUNDTRIP_API_FALLBACK", "1") == "0":
            return ""
        _fb = _roundtrip_fallback()                          # empty CLI ⇒ API fallback (never a dead instrument)
        model = _fb[0] if _fb else "deepseek-chat"
    try:
        from ztare.common.llm_runtime import LLMRuntime
    except Exception:
        try:
            from ztare.common.llm_runtime import LLMRuntime  # type: ignore
        except Exception:
            return ""
    try:
        resp = LLMRuntime().call_text(prompt, model_id=model, fallback_model_ids=_roundtrip_fallback(),
                                      max_tokens=2000, request_label=label, timeout_seconds=timeout_s)
        return getattr(resp, "text", "") or ""
    except Exception as exc:
        if isinstance(exc, BudgetExceeded):
            raise
        return ""


_FORMALIZE_PROMPTS = {
    # one-shot: just the theorem statement (objects assumed to be in Mathlib).
    "oneshot": ("Formalize this natural-language math problem as a SINGLE Lean 4 theorem statement ending "
                "in ` := by sorry`. Preserve every hypothesis and the exact conclusion — do not strengthen, "
                "weaken, drop, or add anything; keep quantifier order. Output ONLY the `theorem … := by "
                "sorry` line.\n\nPROBLEM: "),
    # define-then-state: a self-contained file that DEFINES Mathlib-absent objects, then states the theorem.
    # This is the SAME artifact shape the solver already consumes (most closures are non-Mathlib self-defined),
    # so the autoformalize→solve link needs NO new solver code.
    "define_then_state": ("Formalize this natural-language math problem as a SELF-CONTAINED Lean 4 file. If an "
                "object it refers to is NOT already in Mathlib, DEFINE it faithfully with `def`/`structure`/"
                "`abbrev` (never leave it as an undefined/opaque parameter, and never define it as a trivial "
                "constant or `True`). Then state the theorem about those objects, ending in ` := by sorry`. "
                "Preserve every hypothesis and the exact conclusion; keep quantifier order. Output ONLY the "
                "Lean file (`import Mathlib`, the definitions, the theorem).\n\nPROBLEM: "),
}


_CLI_NOISE = re.compile(
    r"^(Reading additional input|OpenAI Codex|Anthropic|Claude Code|workdir:|model:|provider:|"
    r"approval:|sandbox:|reasoning effort|reasoning summaries|session id|tokens used|-{3,}|"
    r"user|codex|assistant|system|\d{4}-\d\d-\d\dT[\d:.]+Z|.*ERROR rmcp|.*Transport channel|"
    r".*AuthRequired|.*www_authenticate).*$",
    re.IGNORECASE)


def _extract_lean_from_dispatch(blob: str, mode: str) -> str:
    """`default_dispatch` returns the RAW codex/claude CLI stdout+stderr — banner + prompt echo +
    transcript + the answer (often printed twice). It is NOT a clean Lean statement; compiling it
    raw chokes on the banner (this is WHY the autoformalizer one-shot e2e failed pre-2026-06-05).
    Extract the Lean artifact: for `oneshot` the LAST `theorem|lemma … := (by) sorry` statement
    (single- or multi-line); for `define_then_state` the `import…theorem` block. The oneshot path
    keys on the theorem REGEX (not 'everything left'), so residual banner lines are harmless."""
    if not blob:
        return ""
    text = blob.replace("\r", "")
    # PREFER the LEAN-TAGGED fence (the model's deliberate Lean answer), take the LAST one (final
    # answer); only fall back to the longest UNtagged fence if there is no ```lean block. (Adversarial-
    # review fix 2026-06-05: "longest fence wins" mis-picked a prose fence / echoed example.)
    tagged = re.findall(r"```lean\s*\n(.*?)```", text, re.DOTALL)
    if tagged:
        text = tagged[-1]
    else:
        untagged = re.findall(r"```\s*\n(.*?)```", text, re.DOTALL)
        if untagged:
            text = max(untagged, key=len)
    lines = [ln for ln in text.split("\n")
             if not _CLI_NOISE.match(ln.strip())
             and not ln.strip().startswith(("Formalize this", "PROBLEM:", "Output ONLY", "Translate this"))]
    clean = "\n".join(lines)
    if mode == "define_then_state":
        m = re.search(r"(?m)^\s*(import|open|set_option|variable|namespace|def|structure|abbrev|"
                      r"inductive|class|instance|theorem|lemma)\b", clean)
        return (clean[m.start():].strip() if m else "")    # "" (not prose) on no-match ⇒ gate fast-rejects
    # STRIP COMMENTS before extracting the formalized statement (2026-06-13 audit): a commented
    # `-- theorem ex : … := by sorry` in the model's answer must not be picked as THE formalization.
    # Canonical NESTED-aware stripper (handles `/- /- -/ -/`).
    from ztare.leanmill.lean_source import strip_comments as _sc_af, has_sorry as _has_sorry_af
    clean_nc = _sc_af(clean)
    # TEMPERED bound (2026-07-01 audit): the body `.*?` must NOT cross a `theorem`/`lemma` keyword, else a
    # `theorem helper … := by <proof>` FOLLOWED by `theorem target … := sorry` matched as ONE blob (helper's
    # name + target's sorry) → a mangled two-theorem extraction → compile failure (fail-safe, but a wasted
    # formalize round). `(?:(?!\btheorem\b|\blemma\b).)*?` keeps each match to a SINGLE decl. NOT switched to
    # `decl_blocks` here on purpose: that parser is column-0-only and model output can be indented (regression);
    # the `\b`-anchored regex stays lenient. Still takes the LAST sorried statement (the posed target).
    stmts = re.findall(r"(?s)\b((?:theorem|lemma)\s+\S+(?:(?!\btheorem\b|\blemma\b).)*?:=\s*(?:by\s+)?sorry)",
                       clean_nc)
    if stmts:
        return stmts[-1].strip()
    for ln in reversed(clean_nc.split("\n")):                           # fallback: last theorem-ish line
        if ("theorem" in ln or "lemma" in ln) and _has_sorry_af(ln):
            return ln.strip()
    return ""   # no theorem/import block found ⇒ "" so the firewall's empty-formalization fast-reject fires


def _observe_formalize(nl: str, mode: str, raw: str, extracted: str, provider: str = "subscription") -> None:
    """OBSERVABILITY (the recurring 'why did formalize produce empty' gap — diagnose from the LOG, not a re-run):
    append the RAW dispatch output + the extracted statement to OUT_DIR/formalize_observations.jsonl. So an empty
    formalization is attributable: raw_len≈0 ⇒ claude returned nothing (dispatch timeout/fail); raw_len>0 ∧
    extracted_empty ⇒ the extraction regex MISSED claude's answer. `provider` attributes which lane produced it
    (`subscription` = codex/claude CLI; `deepseek` = the API fallback) so a run's provider mix is legible.
    Best-effort, never breaks formalize; default-on (cheap append), ZTARE_LEANMILL_FORMALIZE_OBS=0 disables."""
    import os as _os
    if _os.environ.get("ZTARE_LEANMILL_FORMALIZE_OBS", "1") == "0":
        return
    try:
        import json                          # LOCAL import — module has no top-level `json`; its absence made
        from datetime import datetime, timezone   # this whole writer throw on json.dumps and the bare except
        from ztare.leanmill.solver.solver_core import OUT_DIR as _OUT   # swallow it ⇒ a created-but-EMPTY obs file
        rec = {"ts": datetime.now(timezone.utc).isoformat(), "mode": mode, "provider": provider,
               "run_tag": _os.environ.get("ZTARE_SOLVER_RUN_TAG", ""),
               "nl": (nl or "")[:200],
               "raw_len": len(raw or ""), "extracted_empty": not (extracted or "").strip(),
               "raw_tail": (raw or "")[-1500:], "extracted": (extracted or "")[:400]}
        p = _OUT / "formalize_observations.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass


def _observe_roundtrip(kind: str, **fields) -> None:
    """OBSERVABILITY for the FAITHFULNESS round-trip (the 'WHY did the judge reject a CORRECT statement' gap,
    2026-06-11 — a correct RatFunc-antiderivative formalization that PASSED one run was false-rejected the
    next with only an opaque `round-trip does NOT match the NL`). Append the back-translation + the judge's
    RAW verdict text to OUT_DIR/faithfulness_roundtrip_observations.jsonl, so a rejection is ATTRIBUTABLE:
    a back-translation that DROPPED a hypothesis (back-translator bug) vs. a JUDGE false-negative on a
    precise-but-informal mismatch (the formal `hres` quantifies residues over ALL field extensions L; the
    one-sentence NL is looser). Best-effort, never breaks the gate; ZTARE_LEANMILL_FORMALIZE_OBS=0 disables."""
    import os as _os
    if _os.environ.get("ZTARE_LEANMILL_FORMALIZE_OBS", "1") == "0":
        return
    try:
        import json                                   # LOCAL imports (module has no top-level json/datetime) —
        from datetime import datetime, timezone       # else this best-effort writer NameErrors + silently no-ops
        from ztare.leanmill.solver.solver_core import OUT_DIR as _OUT
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "run_tag": _os.environ.get("ZTARE_SOLVER_RUN_TAG", ""),
        }
        for k, v in fields.items():
            rec[k] = (v[:1500] if isinstance(v, str) else v)
        p = _OUT / "faithfulness_roundtrip_observations.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass


# The subscription CLI runtimes (agentic, repo-aware) — anything else passed as `runtime` is treated as an
# llm_runtime API MODEL ID, routed provider-agnostically. "" = the configured default subscription runtime.
_SUBSCRIPTION_RUNTIMES = {"", "claude", "codex"}


def _api_formalize_fallback_enabled() -> bool:
    """The API-activated formalize fallback is DEFAULT-ON: the subscription CLI (codex/claude) is a single
    contended/quota-limited lane, and the P1-RUNG-A close died because every formalize TIMED OUT on sole-claude
    contention. The fallback provider is API-metered (NOT subscription), so it neither competes with the CLI nor
    hits the codex usage wall. Set ZTARE_LEANMILL_FORMALIZE_API_FALLBACK=0 to force subscription-only."""
    import os as _os
    return _os.environ.get("ZTARE_LEANMILL_FORMALIZE_API_FALLBACK", "1") != "0"


def _api_fallback_model() -> str:
    """The API formalize provider model — PROVIDER-AGNOSTIC, chosen via env. The kernel's `llm_runtime` routes
    ANY of gemini / deepseek / openai by model id, so switching providers is a config change, NOT a code change:
        ZTARE_LEANMILL_FORMALIZE_API_MODEL=gemini-3.1-pro-preview   # or gpt-5.5, o3, deepseek-reasoner, …
    Default 'deepseek-chat' (fast V3 chat, cheap, cross-family from the codex/claude subscription lane)."""
    import os as _os
    from ztare.common.llm_runtime import MODEL_MAP
    raw = (_os.environ.get("ZTARE_LEANMILL_FORMALIZE_API_MODEL") or "deepseek-chat").strip()
    return MODEL_MAP.get(raw, raw)          # resolve a friendly alias ("deepseek"→"deepseek-chat") if given


def _formalize_via_api(prompt: str, *, model: str = "", timeout_s: int = 120) -> str:
    """RAW single-shot formalization via the API-activated provider — PROVIDER-AGNOSTIC: the model is resolved
    from env (`_api_fallback_model`) or the explicit `model` arg, then routed by `llm_runtime` to whichever of
    gemini/deepseek/openai owns it. Availability is checked with the util's own `model_is_configured` (NO
    hardcoded *_API_KEY). Used (a) as the FALLBACK when the subscription dispatch is dead/empty and (b) directly
    for an API `runtime`. Returns '' if the chosen model is unconfigured or the call fails ⇒ the caller
    propagates INADMISSIBLE/empty. NOT a faithfulness shortcut: the firewall (compile + round-trip + structural
    + battery) stays the SOLE admit arbiter, so a weaker API formalizer can only ever FAIL CLOSED."""
    try:
        from ztare.common.llm_runtime import LLMRuntime, MODEL_MAP
    except Exception:
        try:
            from ztare.common.llm_runtime import LLMRuntime, MODEL_MAP  # type: ignore
        except Exception:
            return ""
    model = MODEL_MAP.get((model or "").strip(), (model or "").strip()) or _api_fallback_model()
    try:
        rt = LLMRuntime()
        if not rt.model_is_configured(model):
            return ""                       # provider-agnostic availability (no hardcoded key name)
        resp = rt.call_text(prompt, model_id=model, fallback_model_ids=(),
                            max_tokens=2000, request_label="autoformalize_api_provider",
                            timeout_seconds=timeout_s)
        return getattr(resp, "text", "") or ""
    except Exception:  # noqa: BLE001
        return ""


def _formalize_interactive_on() -> bool:
    """The INTERACTIVE formalizer (the agent ITERATES write→warm-check→search→fix to a TYPECHECKING statement)
    is DEFAULT-ON 2026-06-10 — single-shot formalize was the P1 bottleneck (the agent invents Mathlib names →
    does not typecheck → firewall rejects → solve never reached). =0 reverts to single-shot (the A/B baseline)."""
    import os as _os
    return _os.environ.get("ZTARE_LEANMILL_FORMALIZE_INTERACTIVE", "1") != "0"


_FORMALIZE_INTERACTIVE_PROMPT = (
    "You are FORMALIZING a natural-language math statement into a Lean 4 theorem. You STATE it, you do NOT prove "
    "it — end the theorem in ` := by sorry`. Produce a SINGLE theorem that TYPECHECKS against Mathlib.\n\n"
    "WORKFLOW — write the file, then ITERATE against the warm kernel until it typechecks (do NOT stop at the "
    "first draft):\n"
    "  1. Write your candidate (with `import Mathlib` on the first line) to this file:\n       {probe_ref}\n"
    "  2. Check it — warm, ~0.1s, prints the EXACT Lean errors or 'OK':\n       {leancheck_cmd}\n"
    "  3. On an 'unknown identifier' / 'unknown constant' / wrong-API error, find the REAL Mathlib name — do NOT "
    "invent one:\n       {search_cmd}\n"
    "  4. Fix the file and re-check. Repeat until ZERO errors (the `sorry` is fine — you are only stating it).\n\n"
    "MANDATORY — do NOT skip the checker: you MUST run the check command in step 2 and SEE it print 'OK' before "
    "you output anything. A statement you have not verified with the checker WILL be rejected. Common errors the "
    "checker catches that you must fix: `∑`/`∏` with no Finset domain (use `∑ x ∈ s, …` or `Finset.sum`), a "
    "wrong/invented lemma or definition name (use the search tool — do NOT guess), a missing instance argument, a "
    "type mismatch. Iterate; do not hand back a first draft.\n\n"
    "FAITHFULNESS — typechecking is NECESSARY but NOT SUFFICIENT (a downstream firewall back-translates your "
    "statement and rejects it unless it is LOGICALLY EQUIVALENT to the NL AND non-degenerate): preserve EVERY "
    "hypothesis and the EXACT conclusion below; do NOT strengthen, weaken, drop, add, or reorder quantifiers. "
    "Do NOT take the easy way out — a statement that typechecks because you WEAKENED it (dropped a hypothesis, "
    "added a vacuous/decorative binder, relaxed `=`→`≤` or `∀`→`∃`, or made it trivially true) is REJECTED as "
    "degenerate. Encode the FULL claim even when that is harder to state in Lean.\n\nONLY after the checker prints "
    "'OK', leave the final theorem in the file AND print it between "
    "===LEAN-BEGIN=== and ===LEAN-END===.\n\nThe statement to formalize:\n")


def formalize_interactive(nl: str, *, lean_root, timeout_s: int = 360, context: str = "", runtime: str = "") -> str:
    """INTERACTIVE formalize: the CLI agent ITERATES (write probe → warm `lean-check` → `search` Loogle for the
    REAL Mathlib name → fix) until the statement TYPECHECKS — instead of a blind single-shot that invents names.
    REUSES the primitives (the agentic `default_dispatch`, the warm `lean_check_server`, `agent_tools search`,
    the tool block) — NOT a fork. The agent fixes the COMPILE leg (the P1 bottleneck); the firewall still governs
    FAITHFULNESS downstream. Returns the typechecking statement, or '' to let the caller fall back to single-shot."""
    import re
    import sys as _sys
    from pathlib import Path
    try:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch, probe_dir
        from ztare.formal.lean_check_server import ensure_server_advertised, default_socket_path
    except Exception:  # noqa: BLE001
        return ""
    lean_root = Path(lean_root)
    repo = Path(__file__).resolve().parents[4]
    # SINGLE DOOR (2026-07-03): advertise-or-loud. Fall back to the path for the command string only if down.
    sock = ensure_server_advertised(str(lean_root), context="formalize") or default_socket_path(str(lean_root))
    probe = probe_dir(lean_root) / "FormalizeProbe.lean"
    try:
        probe.write_text("import Mathlib\n\n-- replace with the theorem statement, ending in := by sorry\n", encoding="utf-8")
    except Exception:  # noqa: BLE001
        return ""
    leancheck = f"PYTHONPATH={repo}/src {_sys.executable} -m ztare.formal.lean_check_server --check {sock} {probe}"
    search = f"PYTHONPATH={repo}/src {_sys.executable} -m ztare.leanmill.agent_tools search '<Mathlib name or type pattern>'"
    # CONTEXT framing (2026-06-21): the load-bearing fix is that this context now reaches formalize DEFAULT-ON
    # (the notes-blind formalizer over-modeled an abstract target onto heavy Mathlib machinery because it never
    # saw the operator's intended model). The only change here is to UN-GAG: the old "use ONLY to render
    # faithfully; do NOT formalize the context" implicitly discouraged honoring the blueprint's intended MODEL.
    # Now the context may steer WHICH model/nucleus to formalize — the operator's lane — while the surrounding
    # prose is still not itself formalized. NO encoding lecture / no concrete types (that would be us coaching
    # the formalizer with this example's answer); the firewall is the sole faithfulness arbiter, so honoring the
    # blueprint's model can never specialise a genuinely-general claim or launder a weakening past the gate.
    ctx_block = (f"\n\nSURROUNDING CONTEXT — use it to render the INTENDED statement faithfully: its notation, the "
                 f"intended objects, and (when the blueprint says so) WHICH concrete model / nucleus to formalize. "
                 f"Do NOT formalize the surrounding prose itself.\n{context.strip()[:8000]}\n"
                 if (context or "").strip() else "")
    # NOTE: do NOT append render_tool_block here — that surfaces the PROVING tools (witness/abduct/hammer), which
    # are useless for STATING a theorem and would duplicate the inline `search` command. Formalize needs only
    # lean-check + search, both specified in the prompt above.
    prompt = (_FORMALIZE_INTERACTIVE_PROMPT.format(probe_ref=str(probe), leancheck_cmd=leancheck, search_cmd=search)
              + ctx_block + (nl or ""))
    try:
        raw = default_dispatch(
            prompt,
            runtime=runtime,
            repo=repo,
            timeout=timeout_s,
            agent_tag="autoformalize_statement",
        ) or ""
    except Exception:  # noqa: BLE001
        raw = ""
    # EXTRACT the statement via the CANONICAL parsers (#49 / #80), NOT ad-hoc regex. Order by RELIABILITY:
    #   1) the lean-checked PROBE FILE — the artifact the agent ITERATED to TYPECHECK; it is real Lean (ground
    #      truth), with no ```fence to mis-strip. THIS is why the 2026-06-11 "```lean glue ⇒ does not typecheck"
    #      P1 blocker existed: the text-marker path ran FIRST and left the fence; preferring the probe avoids it.
    #   2) the agent's TEXT answer — the ```lean fence ANCHORED to the ===LEAN-BEGIN=== label via the canonical
    #      `agent_output.fenced_block` (label-anchored so a prompt-echo example fence can't win), else the bare
    #      marker body.
    #   3) the shared oneshot theorem extractor.
    # Validity is judged by `lean_source.theorem_names` (the one canonical Lean parser), not a `"theorem" in s`
    # substring. The only regexes left are at the true LLM-output boundary (the markers + the import prefix).
    from ztare.leanmill import lean_source as _ls
    from ztare.leanmill.solver.agent_output import fenced_block as _fb
    stmt = ""
    try:                                                   # 1) lean-checked probe file (ground truth, no fence)
        _body = probe.read_text(encoding="utf-8")
        if _ls.theorem_names(_body):
            stmt = _body
    except Exception:  # noqa: BLE001
        pass
    if not stmt.strip():                                   # 2) the agent text answer (canonical, label-anchored fence)
        stmt = _fb(raw, "===LEAN-BEGIN===", lang="lean")
        if not stmt:                                       #    no ```lean fence ⇒ the bare ===LEAN-BEGIN/END=== body
            _m = re.search(r"===LEAN-BEGIN===(.*?)===LEAN-END===", raw, re.DOTALL)
            stmt = (_m.group(1).strip() if _m else "")
    if not stmt.strip():                                   # 3) last resort: the shared oneshot theorem extractor
        stmt = _extract_lean_from_dispatch(raw, "oneshot")
    stmt = re.sub(r"^\s*import\s+Mathlib\s*\n+", "", stmt or "").strip()   # minimal boundary strip (the preamble)
    if stmt and not _ls.theorem_names(stmt):               # a non-theorem fragment (e.g. a stray 'and') is NOT a stmt
        stmt = ""
    _observe_formalize(nl, "interactive", raw, stmt, provider="interactive")
    return stmt


def default_formalize(nl: str, *, mode: str = "oneshot", runtime: str = "", timeout_s: "int | None" = None,
                      context: str = "", lean_root=None) -> str:
    """NL → candidate Lean (`… := by sorry`) via the leanmill WARM-AGENT ARCHITECTURE
    (`agentic_leaf.default_dispatch` on subscription, codex/claude) — the SAME dispatch the SOLVER uses,
    NOT a parallel one and NOT the isomorphism loop (which deanchors for analogical jumps).

    PROVIDER RESILIENCE (formalize is SINGLE-SHOT, so it can use a non-agentic API model — unlike the solver
    leaf which is agentic/repo-aware): pass `runtime='deepseek-chat'` (or any llm_runtime model id) to formalize
    purely via the API provider, OR rely on the DEFAULT-ON fallback — if the subscription lane returns DEAD/EMPTY
    (the sole-claude-contention timeouts that zeroed P1-RUNG-A), it recovers via the env-selected API provider
    (`_api_fallback_model`, provider-agnostic). `mode`
    selects the prompt: 'oneshot' (single theorem, objects in Mathlib) or 'define_then_state' (a
    self-contained file that DEFINES Mathlib-absent objects then states the theorem — the same file shape
    the solver already proves, so the link reuses `solve_adhoc` unchanged). The judge must be a DIFFERENT
    family (cold cross-family), never self-blessing.

    define_then_state CAVEAT: faithfulness shifts onto the DEFINITIONS (a `def Genus := 0` shell makes a
    vacuous theorem typecheck — the opaque-shell problem one level down, harder with no reference). Gate
    the defs (back-translate + cold-judge + #24 non-vacuity per def) BEFORE routing multistep output to
    the solver, or a def-shell launders through. That def-faithfulness gate is the remaining work."""
    # FORMALIZE/SOLVE RUNTIME DECOUPLING (2026-06-21 RCA): formalize routes through the SAME leaf dispatch as
    # the solver, so a global `ZTARE_LEANMILL_LEAF_RUNTIME=kimi` (cheap SOLVER leaf) SILENTLY also routed
    # FORMALIZE to kimi — a weak/slow formalizer that stalled the consciousness campaign ~17min on a single
    # lemma (codex did the same render in ~30s). This knob lets the operator keep formalize on the proven
    # codex/claude while the solver leaf is the cheap kimi/deepseek. Unset ⇒ "" ⇒ leaf runtime (byte-parity).
    import os as _os_fr
    runtime = runtime or _os_fr.environ.get("ZTARE_LEANMILL_FORMALIZE_RUNTIME", "")
    from pathlib import Path
    if mode not in _FORMALIZE_PROMPTS:
        mode = "oneshot"
    if timeout_s is None:                    # NOT a hardcoded 240 — the calibrated, env-tunable factory budget
        from ztare.common.timeouts import timeout_s as _budget
        timeout_s = _budget("formalize_oneshot")
    # INTERACTIVE (agentic) formalize — the agent ITERATES write→warm-check→search→fix to a TYPECHECKING
    # statement, fixing the single-shot "invented name → does not typecheck" P1 bottleneck. Default-on; the
    # firewall still governs faithfulness. Only on the agentic path (a lean_root + subscription runtime);
    # falls through to single-shot if it returns empty.
    if (mode == "oneshot" and lean_root is not None and (runtime or "") in _SUBSCRIPTION_RUNTIMES
            and _formalize_interactive_on()):
        _iv = formalize_interactive(nl, lean_root=lean_root, timeout_s=max(int(timeout_s), 360),
                                    context=context, runtime=runtime)
        if (_iv or "").strip():
            return _iv
    try:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch
    except Exception:
        try:
            from ztare.leanmill.solver.agentic_leaf import default_dispatch  # type: ignore
        except Exception:
            return ""
    repo = Path(__file__).resolve().parents[4]
    # #88: optional BLUEPRINT CONTEXT so the formalizer can faithfully render a hard research-level lemma it
    # cannot pin down from the prose alone (the P1-RUNG-A run rejected every lemma faithful=False because the
    # formalizer was blind to the surrounding notation/objects). The context INFORMS rendering only — the
    # firewall (round-trip + cross-vote + structural + def-faithfulness) is still the SOLE admit arbiter, so an
    # over-helpful context can never launder an unfaithful statement through.
    # CONTEXT framing — mirror of formalize_interactive: UN-GAG only (let the blueprint steer WHICH model/nucleus
    # to formalize, the operator's lane), no encoding lecture / no concrete types. Firewall remains the sole
    # faithfulness arbiter, so honoring the model can never launder a weakening past the boundary.
    ctx_block = ("\n\nSURROUNDING BLUEPRINT CONTEXT — use it to render the INTENDED statement faithfully: its "
                 "notation, the intended objects, how this piece fits, and (when the blueprint says so) WHICH "
                 "concrete model / nucleus to formalize. Do NOT formalize the surrounding prose itself:\n"
                 + context.strip()[:8000] + "\n\n") if (context or "").strip() else ""
    prompt = _FORMALIZE_PROMPTS[mode] + ctx_block + (nl or "")
    # PROVIDER A — caller named an API model (runtime is not a subscription CLI runtime — e.g. 'deepseek-chat',
    # 'gemini-3.1-pro-preview', 'gpt-5.5'): formalize single-shot via llm_runtime, no subscription quota / no CLI
    # contention. Provider-agnostic; the firewall still arbitrates faithfulness downstream.
    if (runtime or "") not in _SUBSCRIPTION_RUNTIMES:
        api_raw = _formalize_via_api(prompt, model=runtime, timeout_s=min(timeout_s, 120))
        extracted = _extract_lean_from_dispatch(api_raw, mode)
        _observe_formalize(nl, mode, api_raw, extracted, provider=(runtime or "api"))
        return extracted
    try:
        raw = default_dispatch(
            prompt,
            runtime=runtime,
            repo=repo,
            timeout=timeout_s,
            agent_tag="autoformalize_statement",
        ) or ""
        from ztare.leanmill.solver.agentic_leaf import INADMISSIBLE_DISPATCH
        # PROVIDER B (fallback) — the subscription lane came back DEAD (all providers down ⇒ INADMISSIBLE) or
        # EMPTY (the close's 240s timeouts returned ''). Recover via the API-activated provider (env-selected,
        # provider-agnostic) so a contended/exhausted subscription no longer ZEROES the run (the whole reason
        # RUNG-A produced 0 closures).
        sub_dead = (raw.strip() == INADMISSIBLE_DISPATCH) or (not raw.strip())
        if sub_dead and _api_formalize_fallback_enabled():
            api_raw = _formalize_via_api(prompt, timeout_s=min(timeout_s, 120))
            api_extracted = _extract_lean_from_dispatch(api_raw, mode)
            _observe_formalize(nl, mode, api_raw, api_extracted, provider=_api_fallback_model())
            if api_extracted.strip():
                return api_extracted            # the API provider recovered a statement the subscription couldn't
        if raw.strip() == INADMISSIBLE_DISPATCH:
            _observe_formalize(nl, mode, raw, INADMISSIBLE_DISPATCH)
            return INADMISSIBLE_DISPATCH       # #89: propagate the dead-instrument signal (every provider dead)
        extracted = _extract_lean_from_dispatch(raw, mode)
        _observe_formalize(nl, mode, raw, extracted)   # OBSERVABILITY: raw output + extraction logged (no re-run)
        return extracted
    except Exception as _e:  # noqa: BLE001
        try:
            from ztare.leanmill.exploration_budget import BudgetExceeded as _BudgetExceeded
            from ztare.leanmill.solver.agentic_leaf import BUDGET_EXHAUSTED_DISPATCH
            if isinstance(_e, _BudgetExceeded):
                _observe_formalize(nl, mode, "", f"BUDGET_EXHAUSTED: {_e}")
                return BUDGET_EXHAUSTED_DISPATCH
        except Exception:  # noqa: BLE001 — preserve the existing fail-closed empty result
            pass
        _observe_formalize(nl, mode, "", f"EXCEPTION: {_e!r}")
        return ""


def default_formalize_multistep(nl: str, *, runtime: str = "", timeout_s: "int | None" = None,
                                context: str = "", lean_root=None) -> str:
    """Thin alias — define-then-state is now a MODE of `default_formalize` (merged to kill the duplicate
    dispatch boilerplate). See the def-faithfulness CAVEAT in `default_formalize`. The per-dispatch budget is
    the CALIBRATED `formalize_multistep` factory budget (measured ~243s peak + headroom, not guessed) unless
    the caller overrides — so it lives in `common/timeouts`, the one home, env-tunable per node. `context` threads
    the SAME formalizer context (blueprint + established vocabulary) the oneshot path gets — the escalation must
    not be context-blind (it would re-author the canonical defs and re-orphan the shelf, the very drift we fix)."""
    if timeout_s is None:
        from ztare.common.timeouts import timeout_s as _budget
        timeout_s = _budget("formalize_multistep")
    return default_formalize(nl, mode="define_then_state", runtime=runtime, timeout_s=timeout_s,
                             context=context, lean_root=lean_root)


_ROUNDTRIP_MODEL_DEFAULT = "gemini-3.1-pro-preview"   # a DIFFERENT family from the codex/claude formalizer
# CROSS-FAMILY chain (2026-07-01 RCA): cheap same-family retry FIRST (a flaky primary), THEN a DIFFERENT family so
# a gemini-WIDE outage (quota/rate-limit) can't empty the back-translation and FALSE-REJECT a faithful target — the
# BFT campaign's run-1 firewall reject. A same-family-only fallback is not resilience; it dies with the primary.
_ROUNDTRIP_FALLBACK_DEFAULT = "gemini-2.5-flash,deepseek-chat"


def _roundtrip_fallback() -> "tuple[str, ...]":
    """The round-trip dispatch fallback model(s). Precedence: ENV `ZTARE_LEANMILL_ROUNDTRIP_FALLBACK`
    (comma-separated) > POLICY (`SolverConfig.roundtrip_fallback_model`) > code default. Env-first so the
    fallback can be a DIFFERENT family from the primary (e.g. primary=deepseek, fallback=kimi) — cross-family
    resilience so one dead provider can't manufacture an empty-backtranslation false-reject."""
    import os as _os
    env = (_os.environ.get("ZTARE_LEANMILL_ROUNDTRIP_FALLBACK") or "").strip()
    if env:
        return tuple(x.strip() for x in env.split(",") if x.strip())
    try:
        from ztare.leanmill.solver.config import SolverConfig
        m = (SolverConfig.load_default().roundtrip_fallback_model or "").strip()
        if m:
            return tuple(x.strip() for x in m.split(",") if x.strip())
    except Exception:  # noqa: BLE001
        pass
    # split the (comma-separated) default too — it is a cross-family CHAIN, not a single model id
    return tuple(x.strip() for x in _ROUNDTRIP_FALLBACK_DEFAULT.split(",") if x.strip())


def _roundtrip_model() -> str:
    """The round-trip back-translate/judge model. Precedence: ENV `ZTARE_LEANMILL_ROUNDTRIP_MODEL` > solver
    POLICY config (`SolverConfig.roundtrip_model` in solver.yaml) > code default. Env-first so the judge family
    can be swapped per-run without a config/code change (e.g. away from a flaky gemini to deepseek/kimi).
    Cross-family independence FROM the formalizer (codex/claude) is the soundness-relevant property; the specific
    id is operator policy."""
    import os as _os
    env = (_os.environ.get("ZTARE_LEANMILL_ROUNDTRIP_MODEL") or "").strip()
    if env:
        return env
    try:
        from ztare.leanmill.solver.config import SolverConfig
        m = (SolverConfig.load_default().roundtrip_model or "").strip()
        if m:
            return m
    except Exception:  # noqa: BLE001 — a config error never breaks the firewall; fall back to the code default
        pass
    return _ROUNDTRIP_MODEL_DEFAULT


def _claim_signature(lean_statement: str) -> str:
    """The FINAL theorem/lemma SIGNATURE (binders + conclusion, proof stripped) from a possibly self-contained
    probe — the CLAIM the back-translator should render. RCA 2026-07-05 (CLOB `rejected_by_firewall` on proven
    axiom-clean lemmas): the faithfulness `stmt` is frequently the WHOLE probe (every substrate def — `inductive
    Side`, `structure Order`/`Book`, `def betterPrice`, … — plus the one theorem, ~1k lines), so a one-sentence
    back-translator describes the def/instance SETUP ("for any types K,T with a zero, a linear order …") or
    returns EMPTY on the oversized input, and the round-trip judge then false-rejects a faithful statement. The
    target is the LAST named decl (assemblers append it last — see solve_adhoc `dedup_decl_keep_last`). '' if
    unparseable ⇒ caller falls back to the whole text (byte-parity for a bare signature that has no preamble)."""
    try:
        from ztare.leanmill.lean_source import decl_blocks, signature_before_proof
        named = [(n, b) for n, b in decl_blocks(lean_statement or "") if n]
        if len(named) <= 1:                       # already a bare statement (or nothing) ⇒ leave it to the caller
            return ""
        return (signature_before_proof(named[-1][1]) or "").strip()
    except Exception:  # noqa: BLE001 — extraction is best-effort; the whole text is the sound fallback
        return ""


def default_backtranslate(lean_statement: str, *, model: "Optional[str]" = None) -> str:
    """Lean → NL back-translation — a mechanical rendering (one completion), so it uses `LLMRuntime`
    (a DIFFERENT family from a codex formalizer; model is env-overridable via `_roundtrip_model`). Returns ''
    on any failure ⇒ the gate's non-empty guard fails-closed (no admission on a dead back-translator)."""
    primary = model or _roundtrip_model()
    # Render only the CLAIM (final theorem signature), never the whole def-preamble probe (the CLOB oversized-
    # input false-reject, 2026-07-05). Falls back to the full text when it is already a bare statement.
    _claim = _claim_signature(lean_statement)
    prompt = prompts.BACKTRANSLATE_PROMPT.format(lean_statement=(_claim or lean_statement or ""))
    back = (_api_text(prompt, model=primary, label="autoformalize_backtranslate") or "").strip()
    used = primary
    # LIVENESS RESILIENCE (RCA 2026-06-25): an EMPTY back-translation means the judge MODEL is dead/flaky
    # (quota, rate-limit) — NOT that the statement is unfaithful — yet the gate's non-empty guard then
    # FALSE-REJECTS a faithful target ("round-trip … or empty/degenerate"). That manufactured the v4 vs v4b
    # NON-DETERMINISM: the identical target was admitted one run, rejected the next. Retry the fallback model(s)
    # before yielding empty, so a transiently-flaky primary can't fabricate an unfaithful verdict. (Soundness
    # unchanged: a recovered back-translation is still JUDGED; only a genuinely dead translator yields empty.)
    if not back and model is None:
        for fb in _roundtrip_fallback():
            if not fb or fb == primary:
                continue
            back = (_api_text(prompt, model=fb, label="autoformalize_backtranslate_fallback") or "").strip()
            if back:
                used = fb
                break
    _observe_roundtrip("backtranslate", lean_statement=(lean_statement or ""), back_nl=back, model=used)
    return back


def default_directional_judge(orig_nl: str, back_nl: str, *, model: "Optional[str]" = None) -> bool:
    """DIRECTIONAL-for-proving faithfulness judge: True iff PROVING the back-translation would ESTABLISH the
    original's claim — a stronger-or-equal CONCLUSION (incl. a CONSTRUCTIVE witness for an ∃-goal: exhibiting a
    specific F for "∃F, F'=f" is faithful, never a launder — proving more is harder, not easier) on the
    same-or-weaker HYPOTHESES. False on a WEAKER/changed conclusion (=→≤, ∀→∃) or a DROPPED/ADDED/RESTRICTED
    hypothesis (narrowed domain, assumed splitting, extra side condition). FAILS-CLOSED on ambiguity/failure.
    The deterministic `statement_integrity` carrier OVERRIDES a charitable verdict here. (2026-06-11: was strict
    EQUIVALENCE, which wrongly rejected a faithful CONSTRUCTIVE formalization — equivalence is over-strict on
    the ADMIT side for a proving firewall; directional implication is the correct model.)

    MAJORITY-OF-N (2026-06-11 flaky-judge fix): a SINGLE gemini completion is a near-coin-flip on a HARD
    equivalence (an INFORMAL NL vs. a deliberately MORE-PRECISE formalization — e.g. `hres` quantifying the
    residue over every field extension L). MEASURED: the identical (nl, back_nl) returned True/True/False on
    the EXACT RatFunc-antiderivative statement, so the production single-sample false-rejected a CORRECT
    formalization and dead-ended the run. We now take a STRICT MAJORITY of N independent votes
    (ZTARE_LEANMILL_JUDGE_SAMPLES, default 3) — sound variance reduction (an UNFAITHFUL statement still loses
    the vote) — and the prompt explicitly tells the judge that MORE PRECISION is NOT strengthening. Every
    vote + the raw verdicts are logged via `_observe_roundtrip` so a rejection is never opaque again."""
    import os as _os
    model = model or _roundtrip_model()   # env-overridable single-model judge id (the panel below ignores it)
    # JUDGE-DIVERSITY PANEL (#116 follow-up, `ZTARE_LEANMILL_JUDGE_PANEL`, default-off = byte-parity): poll K
    # DIFFERENT model families + Dawid–Skene reliability weighting instead of N samples of ONE model — the
    # measured single-judge 5/6-FALSE-REJECT fix (samples of one model share its systematic over-strictness;
    # diverse families decorrelate). SOUNDNESS: the deterministic statement_integrity carrier still OVERRIDES
    # downstream, so the panel only moves the faithful-admit / false-reject margin, never the no-false-admit
    # floor. Any panel failure falls back to the single-model judge below (never crashes the gate).
    if _os.environ.get("ZTARE_LEANMILL_JUDGE_PANEL", "0") == "1":
        try:
            from ztare.leanmill.solver.judge_panel import panel_judge
            faithful, tel = panel_judge(
                orig_nl, back_nl, prompt_template=prompts.DIRECTIONAL_JUDGE_PROMPT,
                dispatch=lambda p, m: _api_text(p, model=m, label="autoformalize_judge_panel"))
            if tel["n_live"] > 0:                          # ≥1 live judge ⇒ trust the panel; all-dead ⇒ fall through
                _observe_roundtrip("judge_panel", orig_nl=orig_nl, back_nl=back_nl, n=tel["n_live"],
                                   votes=list(tel["live_votes"].values()), raw_verdicts=tel["raw"],
                                   faithful=faithful, model=f"panel:{tel['method']}")
                return faithful
        except Exception as exc:  # noqa: BLE001 — panel error ⇒ fall back to the single-model judge
            if isinstance(exc, BudgetExceeded):
                raise
            pass
    prompt = prompts.DIRECTIONAL_JUDGE_PROMPT.format(orig_nl=orig_nl, back_nl=back_nl)
    n = 3
    try:
        n = max(1, int(_os.environ.get("ZTARE_LEANMILL_JUDGE_SAMPLES", "3") or "3"))
    except (TypeError, ValueError):
        n = 3
    raws: "list[str]" = []
    votes: "list[bool]" = []
    for sample in range(n):
        raw = (
            _api_text(
                prompt,
                model=model,
                label=f"autoformalize_judge_{sample}",
            )
            or ""
        ).strip()
        raws.append(raw)
        # AUDIT #1 verdict-collapse fix (2026-07-05): count ONLY a LIVE (non-empty) sample. An empty raw means the
        # judge dispatch was UNAVAILABLE (quota/outage) — that is NOT a 'not-equivalent' NO vote, and counting it
        # as one is how a momentarily-dead judge false-rejects a FAITHFUL formalization (the recurring dead-judge
        # class). `_api_text` already falls CLI→API internally, so an empty raw is a genuine outage.
        if raw:
            votes.append(raw.upper().splitlines()[0].strip().startswith("EQUIVALENT"))
    if not votes:
        # FULL judge outage ⇒ a DEAD instrument, not a verdict. Fail-CLOSED (never ADMIT on a dead judge — no
        # laundering) but LOUD, so a dead judge is a VISIBLE dead instrument, not a silent unfaithful-reject.
        print("⚠️  [firewall] round-trip judge DEAD — all N samples empty (dispatch outage), round-trip "
              "UNVERIFIABLE; failing closed (no admission on a dead judge). Check ZTARE_LEANMILL_ROUNDTRIP_MODEL.",
              flush=True)
        faithful = False
    else:
        faithful = (sum(1 for v in votes if v) * 2 > len(votes))   # STRICT majority of the LIVE votes only
    _observe_roundtrip("judge", orig_nl=orig_nl, back_nl=back_nl, n=n, votes=votes,
                       raw_verdicts=[r[:200] for r in raws], faithful=faithful, model=model)
    return faithful


# ── PRODUCTION wiring of the firewall to the ONE kernel + the #24 probe, and the SOLVER LINK ────────
# These reuse the existing apparatus (gates/v33_preflight_risk_detector + the worker's solve_adhoc) —
# NO standalone governance. They are what turns the OPT-IN apparatus into the live end-to-end loop:
#   NL → autoformalize → faithfulness firewall (governance on the STATEMENT) → solve_adhoc (solver +
#   governance on the PROOF).

def _extract_signature(statement: str) -> str:
    """`theorem T (a:ℝ) : a = a := by sorry` → `theorem T (a:ℝ) : a = a` (drop the proof tail).
    The detector helpers (`_conclusion`/`_hyp_types`) tolerate the `theorem T` prefix. Binder-safe:
    a `let k := 5` inside a hypothesis must NOT be read as the proof `:=` (canonical splitter)."""
    from ztare.leanmill.lean_source import signature_before_proof
    return signature_before_proof(statement).strip()


def default_compile(statement: str, sandbox) -> bool:
    """compile_fn: does the statement TYPECHECK (with `sorry`)? Reuses the kernel compile path
    (`_compile_probe` = `lake env lean`, error≠warning so `sorry` is fine). True iff no Lean error."""
    from ztare.gates.v33_preflight_risk_detector import _compile_probe
    body = statement if statement.lstrip().startswith("import") else f"import Mathlib\n\n{statement}"
    return _compile_probe(body, sandbox, "AutoformCompile", 150) is True


def default_compile_diagnose(statement: str, sandbox) -> str:
    """The compile ERROR TEXT for a failing statement — the targeted feedback the refine loop needs so the
    formalizer FIXES the specific Lean error instead of re-guessing blind. The firewall's `compile_fn` returns
    only a bool (discarding WHY it failed), which made the compile-fix refine loop non-convergent (the root
    cause of the P1-RUNG-A formalize-reject + the retry token-burn: claude was told 'it did not typecheck' with
    no error to act on). Best-effort, ADVISORY (never a gate — it does not affect admission, only the hint):
    reuses the warm REPL (which already returns the actual `error:` lines, just discarded by `default_compile`).
    Returns '' when it compiles, or when the REPL is unavailable here (graceful — the hint stays generic, no
    worse than before). `reject_sorry=False` matches `default_compile`'s policy (a `sorry` is fine)."""
    body = statement if statement.lstrip().startswith("import") else f"import Mathlib\n\n{statement}"
    try:
        from ztare.formal.repl_compile import compile_probe_via_repl
        r = compile_probe_via_repl(body, sandbox, reject_sorry=False)
        if r is None:
            return ""                         # REPL off / toolchain mismatch / dead ⇒ no diagnostics available
        ok, diag = r
        return "" if ok else (diag or "")
    except Exception:  # noqa: BLE001
        return ""


def default_instance_battery(formalization: str, predicate: str, cases, *, sandbox) -> bool:
    """battery_fn production wiring: run `semantic_instance_battery` through the kernel compile probe
    (`_compile_probe` = `lake env lean`). `import Mathlib` is prepended when absent. `cases` is the
    human-labelled `[(instance_lean_term, expected_truth)]` for the decidable predicate `predicate`."""
    from ztare.gates.v33_preflight_risk_detector import _compile_probe

    def _probe(body: str) -> bool:
        full = body if body.lstrip().startswith("import") else f"import Mathlib\n\n{body}"
        return _compile_probe(full, sandbox, "AutoformBattery", 150) is True

    return semantic_instance_battery(formalization, predicate, cases, compile_probe=_probe)


def _smt_assignment_to_lean(assignment: "dict", field_order: "list[str]",
                            value_map: "Optional[dict]" = None) -> str:
    """Render an SMT model assignment `{attr: value}` as a Lean anonymous-constructor instance term
    `⟨v0, v1, …⟩` in `field_order`. bool→`true`/`false`, int→decimal; a `value_map[attr][value]` override
    renders enum/string attributes to their Lean constructor. The structure's field order MUST match."""
    value_map = value_map or {}
    parts = []
    for f in field_order:
        v = assignment.get(f)
        if value_map.get(f) and v in value_map[f]:
            parts.append(str(value_map[f][v]))
        elif isinstance(v, bool):
            parts.append("true" if v else "false")
        else:
            parts.append(str(v))
    return "⟨" + ", ".join(parts) + "⟩"


def default_smt_boundary_battery(formalization: str, predicate: str, *, sandbox,
                                 smt_rule: str, numeric_attr: str, smt_domain: "dict",
                                 field_order: "list[str]", value_map: "Optional[dict]" = None,
                                 candidate_smt: "Optional[str]" = None, auto_candidates: bool = True) -> bool:
    """CROSS-SUBSTRATE battery_fn: instead of HUMAN-labelled instances, the SMT side (z3) PROPOSES the
    adversarial cases over the INFINITE numeric range and the Lean KERNEL RATIFIES them. The "SMT proposes,
    Lean ratifies" leapfrog as a production firewall leg — a drop-in `battery_fn` (same `(stmt)->bool`
    contract), so it composes with the existing gate. Reuses the ONE battery kernel (`default_instance_
    battery` = `semantic_instance_battery` over `_compile_probe`); NO parallel governance.

    Cases come from `SmtPolicyChecker`:
      • `threshold_cases(smt_rule, numeric_attr)` — the decision-FLIP boundary over all ℤ (the $10,000 edge
        a human battery misses), labelled by the rule's own z3 decision;
      • if `candidate_smt` is given, ALSO `distinguishing_requests(smt_rule, candidate_smt)` — concrete
        requests where the trusted rule and the candidate DISAGREE (each labelled by the trusted rule).
    The Lean `predicate` must DECIDE to those labels; a laundered formalization (e.g. `>=` weakened to `>`)
    misclassifies the SMT-found boundary and FAILS. FAIL-CLOSED: no z3 / no cases ⇒ False (no silent admit;
    a firewall leg that can't produce its adversarial cases must not wave the formalization through)."""
    try:
        from ztare.common.smt_checker import SmtPolicyChecker
    except Exception:  # noqa: BLE001
        return False
    try:
        chk = SmtPolicyChecker(smt_domain)
    except Exception:  # noqa: BLE001 — z3 absent ⇒ fail-closed
        return False
    cases_smt = list(chk.threshold_cases(smt_rule, numeric_attr) or [])
    if candidate_smt:
        cases_smt += list(chk.distinguishing_requests(smt_rule, candidate_smt) or [])
    if auto_candidates:   # AUTO-derive the laundering surface (off-by-one + operator weakenings) — no human
        cases_smt += list(chk.auto_distinguishing_battery(smt_rule) or [])   # candidate needed; the kernel ratifies each
    # dedup by request (threshold / distinguishing / auto may land on the same boundary point)
    _seen: set = set()
    _dedup: "list[tuple[dict, bool]]" = []
    for req, dec in cases_smt:
        k = tuple(sorted(req.items()))
        if k not in _seen:
            _seen.add(k)
            _dedup.append((req, dec))
    cases_smt = _dedup
    if not cases_smt:
        return False   # FAIL-CLOSED: the SMT side proposed no adversarial case (cannot certify emptily)
    lean_cases = [(_smt_assignment_to_lean(req, field_order, value_map), bool(dec)) for req, dec in cases_smt]
    return default_instance_battery(formalization, predicate, lean_cases, sandbox=sandbox)


def default_crossvote(nl: str, statement: str, *, sandbox, mode: str = "oneshot",
                      timeout_s: int = 240, equiv_timeout_s: "Optional[int]" = None) -> bool:
    """crossvote_fn production wiring (flag-gated by `crossvote_enabled()` at the call site): dispatch the
    DIVERSE formalizer panel on `nl`, require they form a CROSS-FAMILY kernel-equivalence clique, AND require
    the candidate `statement` to be kernel-equivalent to that consensus. Two clean checks, both via the ONE
    kernel (`kernel_equivalent` = a `lake env lean` ↔-bridge compile):
      (1) `cross_vote_faithfulness` — ≥2 independent formalizations agree (across ≥2 families); and
      (2) `kernel_equivalent(statement, consensus)` — THIS statement is the same problem as the consensus.
    FAIL-CLOSED on every leg (kernel_equivalent / cross_vote_faithfulness both return False / non-faithful on
    any infra failure, <2 votes, or disagreement). NEVER admits on a missing signal.

    `equiv_timeout_s` (the per-pair `↔` compile budget) defaults to `ZTARE_LEANMILL_EQUIV_TIMEOUT_S` (else
    300s) — NOT hardcoded tight: each pair pays a cold Mathlib reload, so a small value times out → None →
    fail-closed false-negative."""
    from ztare.leanmill.solver.cross_voting import (cross_vote_faithfulness, kernel_equivalent,
                                                    _equiv_timeout_default)
    if equiv_timeout_s is None:
        equiv_timeout_s = _equiv_timeout_default()
    verdict, _votes = cross_vote_faithfulness(nl, lean_root=Path(sandbox), mode=mode,
                                              timeout_s=timeout_s, equiv_timeout_s=equiv_timeout_s)
    if not verdict.faithful or not (verdict.agreed_statement or "").strip():
        return False   # the independent panel did not reach a cross-family kernel consensus
    agree, _why = kernel_equivalent(statement, verdict.agreed_statement, Path(sandbox), equiv_timeout_s)
    return bool(agree)


def default_triviality(statement: str, sandbox) -> bool:
    """triviality_fn: True ⇒ the statement is DEGENERATE (reject). Combines all three vacuity carriers,
    reusing the #24 apparatus (NO new governance): (a) lexical `detect_risks` vacuity_suspected;
    (b) the cheap-tactic cascade actually CLOSES it (genuinely trivial); (c) the exogenous
    non-degenerate-instance probe REFUTES instance-existence (hidden vacuity). Raises on infra failure
    so the gate fails-CLOSED (a probe we can't run must not silently admit)."""
    from ztare.gates.v33_preflight_risk_detector import (
        detect_risks, _compile_probe, nondegenerate_instance_probe)
    # Risk detection is a statement-level gate: for define-then-state blobs, inspect
    # the target theorem signature, not the leading definition/abbrev.
    sig = _extract_signature(_target_signature(statement))
    if detect_risks(sig).get("vacuity_suspected") is True:
        return True
    if _define_then_state_blob(statement):
        # A define-then-state candidate has already typechecked as a full blob in
        # the compile leg. Running a cold proof-search replacement over the whole
        # definition prelude is both high-cost and the wrong granularity for
        # vacuity; the lexical risk check above already inspected the target
        # theorem signature. Single-theorem statements still take the proof probe.
        return False
    # CANONICAL sorry→tactic splice (binder/by-token aware) instead of a `:=…sorry` regex.
    from ztare.leanmill.lean_source import swap_sorry as _swap_sorry
    triv = _swap_sorry(statement, "by first | trivial | rfl | simp_all | omega | decide | tauto | norm_num") or statement
    body = triv if triv.lstrip().startswith("import") else f"import Mathlib\n\n{triv}"
    cheap = _compile_probe(body, sandbox, "AutoformTriv", 150)
    if cheap is None:
        # FAIL-CLOSED (matches the docstring): a cheap-tactic probe we COULDN'T RUN (timeout / infra
        # failure) must NOT silently admit. Raising routes through faithfulness_gate's fail-closed
        # exception path. (Adversarial-review fix 2026-06-05: the old `is True` coerced None→False =
        # "non-trivial PASS" = a documented fail-closed guarantee that was FALSE in code.)
        raise RuntimeError("AutoformTriv cheap-tactic probe inconclusive (infra) — fail-closed, no silent admit")
    if cheap is True:
        return True                                          # closed by cheap tactics → degenerate
    from ztare.common.timeouts import timeout_s   # central budget factory (byte-parity: vacuity_probe defaults to the prior 150)
    return nondegenerate_instance_probe(sig, sandbox, timeout=timeout_s("vacuity_probe")).get("vacuity_confirmed") is True


_DEF_KINDS = {"def", "structure", "inductive", "abbrev", "class", "instance",
              "notation", "opaque", "axiom", "variable", "open"}
_DECL_MODIFIERS = ("noncomputable", "private", "protected", "scoped", "local", "unsafe", "partial")


def _decl_kw(block: str) -> str:
    """The decl's KEYWORD (`def`/`abbrev`/`structure`/`theorem`/…), with leading attributes (`@[…]`) and modifiers
    (`noncomputable`/`private`/…) stripped first. The ONE keyword reader — `_decl_is_definition` and the def-shell
    degeneracy check both derive from it (no two places re-strip modifiers and risk drift)."""
    head = (block or "").lstrip()
    changed = True
    while changed:
        changed = False
        if head.startswith("@["):
            i = head.find("]")
            if i != -1:
                head = head[i + 1:].lstrip()
                changed = True
        for mod in _DECL_MODIFIERS:
            if head.startswith(mod + " ") or head.startswith(mod + "\n"):
                head = head[len(mod):].lstrip()
                changed = True
    return head.split(None, 1)[0] if head.split() else ""


def _decl_is_definition(block: str) -> bool:
    """True if a decl block introduces a NAMED OBJECT (def/structure/instance/…) rather than a PROOF
    (theorem/lemma/example). Definitions must appear ONCE and BEFORE the theorems that cite them; proofs follow."""
    return _decl_kw(block) in _DEF_KINDS


def _define_then_state_blob(statement: str) -> bool:
    """True for formalizer blobs that introduce definitions and end in a theorem/lemma target."""
    try:
        from ztare.leanmill.solver.statement_integrity import decl_blocks
        blocks = [(name, block) for name, block in decl_blocks(statement or "") if (block or "").strip()]
    except Exception:  # noqa: BLE001
        return False
    if len(blocks) < 2:
        return False
    if _decl_kw(blocks[-1][1]) not in {"theorem", "lemma"}:
        return False
    return any(_decl_is_definition(block) for _name, block in blocks[:-1])


def _norm_block(block: str) -> str:
    """Whitespace- AND comment-insensitive normal form for the compose conflict-check. Comments have ZERO kernel
    meaning, so two definitions identical up to a doc-/line-comment are the SAME def — stripping comments before
    comparison can never mask a real semantic difference, only eliminate a FALSE conflict. (2026-06-24: with the
    established-vocabulary cure the target copies the canonical def VERBATIM incl. the theory file's trailing
    `/-- Anchor: … -/` doc-comment, while the banked lemma probes carry the comment-free body — semantically
    identical, so they MUST compose; the old whitespace-only norm false-conflicted on the doc-comment alone.)
    Canonical nested-aware `lean_source.strip_comments` — never a bare `re.sub(r'/-.*?-/')`."""
    try:
        from ztare.leanmill.lean_source import strip_comments
        return " ".join(strip_comments(block or "").split())
    except Exception:  # noqa: BLE001 — never block composition on the parser import; fall back to whitespace-only
        return " ".join((block or "").split())


def assemble_campaign_probe(target_statement: str, shelf_probes: "list[str]",
                            *, header: str = "import Mathlib") -> "tuple[str, dict]":
    """THE campaign probe assembler — the SINGLE source of truth for a target's COMPILE SCOPE.

    Builds one well-formed Lean file: a single import header, every bespoke DEFINITION exactly once (deduped by
    name, definitions first), the proven SHELF theorems, then the TARGET theorem last. This gives the target the
    shelf IN SCOPE so it can CITE the lemmas (a real dependency graph) AND prevents the duplicate-declare clash on
    theory-building targets that inline the same `def`/`structure` in every self-contained probe. The notes carry
    intent (advisory); THIS function is what actually determines scope (authoritative) — so the two can't drift,
    which is the root cause of the notes-path bug class (text-context ≠ compile-scope). Canonical decl parser
    (`statement_integrity.decl_blocks`) — never a re-rolled regex.

    Fall-back-safe: on an UNRESOLVABLE conflict (same decl name, DIFFERENT body across sources — composing would
    silently pick one meaning) it returns the BARE target and `info['composed']=False`, never a wrong merge.
    Empty `shelf_probes` ⇒ byte-equivalent bare target. Returns (probe_text, info={composed, defs,
    shelf_theorems, reason})."""
    from ztare.leanmill.solver.statement_integrity import decl_blocks

    def _strip_import(s: str) -> str:
        return "\n".join(l for l in (s or "").splitlines() if not l.lstrip().startswith("import"))

    defs: "dict[str, str]" = {}
    def_order: "list[str]" = []
    shelf_thms: "list[str]" = []
    seen_thm: set = set()
    conflicts: "list[dict]" = []   # OBSERVABILITY: record WHICH decl drifted + the two divergent bodies, not a bare bool

    def _ingest_defs_and(name_block, *, collect_thms: "list[str] | None"):
        name, block = name_block
        b = (block or "").strip()
        if not b:
            return
        if _decl_is_definition(b):
            if name in defs:
                if _norm_block(defs[name]) != _norm_block(b):
                    conflicts.append({"name": name, "kept": _norm_block(defs[name])[:240],
                                      "rejected": _norm_block(b)[:240]})
            else:
                defs[name] = b
                def_order.append(name)
        elif collect_thms is not None and name not in seen_thm:
            seen_thm.add(name)
            collect_thms.append(b)

    # THE TARGET OWNS ITS NAME (2026-07-02 RCA — the Basel `iso_lemma1` IN-FILE collision that blocked kernel
    # RATIFICATION). The planner reuses a GENERIC decomposition name (`iso_lemmaN`) for BOTH a proven shelf rung
    # AND the target, so BOTH were emitted as `theorem iso_lemma1` → TWO same-named theorems in one probe. The
    # target THEOREM is appended un-deduped (below), so a shelf theorem of the SAME name co-exists — and every
    # name-based extractor (statement_integrity's original-vs-probe diff, the closing-probe readback, `_decl_body`
    # find-first vs `decl_blocks` last-wins) then resolves a DIFFERENT `iso_lemma1` ⇒ false `target_signature_altered`
    # ⇒ the kernel-proven target can never ratify. A shelf theorem sharing the target's name is redundant (same
    # statement — the target IS it) or a collision (different statement — cannot co-exist under one name in Lean);
    # in BOTH cases EXCLUDE it so each theorem name appears exactly once (defs are already deduped by name above).
    _target_thm_names = {n for (n, b) in decl_blocks(_strip_import(target_statement))
                         if (b or "").strip() and not _decl_is_definition((b or "").strip())}
    for probe in (shelf_probes or []):
        for nb in decl_blocks(_strip_import(probe)):
            if nb[0] in _target_thm_names and not _decl_is_definition((nb[1] or "").strip()):
                continue   # shelf theorem colliding with the TARGET's name — drop (would break every name-based tool)
            _ingest_defs_and(nb, collect_thms=shelf_thms)

    target_thms: "list[str]" = []
    for nb in decl_blocks(_strip_import(target_statement)):
        # target defs merge into the shared def set; the target THEOREM is appended last (not deduped vs shelf)
        nm, blk = nb
        if _decl_is_definition((blk or "").strip()):
            _ingest_defs_and(nb, collect_thms=None)
        elif (blk or "").strip():
            target_thms.append((blk or "").strip())

    if not shelf_probes or conflicts or not target_thms:
        bare = (header + "\n\n" + _strip_import(target_statement).strip()).strip() + "\n"
        return bare, {"composed": False, "defs": 0, "shelf_theorems": 0,
                      "reason": "conflict" if conflicts else ("no_shelf" if not shelf_probes else "no_target_theorem"),
                      "conflicts": conflicts}

    parts = [header, ""]
    for n in def_order:
        parts += [defs[n], ""]
    for b in shelf_thms:
        parts += [b, ""]
    parts.append("\n\n".join(target_thms))
    return "\n".join(parts).rstrip() + "\n", {"composed": True, "defs": len(def_order),
                                              "shelf_theorems": len(shelf_thms), "reason": "composed",
                                              "conflicts": []}


def default_solve(target_name: str, statement: str, *, substrate, timeout_s: int = 600,
                  notes: "str | None" = None, shelf_prelude: str = "") -> dict:
    """solve_fn: route an ADMITTED faithful statement into the existing solver+governance (solve_adhoc).
    `notes` (optional, #81) carries a blueprint into the recursive planner (advisory; kernel-gated).

    `shelf_prelude` (2026-06-23, the composition fix): proven sibling lemmas (full `theorem … := <proof>`) to
    place IN COMPILE SCOPE via `assemble_campaign_probe`, so the agent can CITE them instead of re-deriving them
    inline (the dead-code gap Gemini flagged on FTAP). The assembler dedups shared definitions (theory-building
    targets inline the same `def`/`structure`) and falls back to the bare target on an unresolvable conflict.
    The kernel re-verifies the whole composite; the axiom audit still gates (the shelf is ratified/axiom-clean);
    the MNC still strips the prelude (a proof that needs the shelf reads as 'needs the prelude' = PASS, not
    leakage). Empty ⇒ byte-equivalent to the prior single-statement body."""
    from ztare.leanmill.solver.solver_core import solve_adhoc  # #42: import from src, not the script
    body, _info = assemble_campaign_probe(statement, [shelf_prelude] if (shelf_prelude or "").strip() else [])
    if shelf_prelude and shelf_prelude.strip() and not _info.get("composed"):
        _cf = _info.get("conflicts") or []
        _detail = ""
        if _cf:
            # NAME the drifted def(s) so the orphaned-shelf cause is readable in the log, not hand-diffed later.
            _detail = " — DRIFTED def(s): " + "; ".join(
                f"`{c['name']}` (shelf≠target: {c['kept'][:80]!r} vs {c['rejected'][:80]!r})" for c in _cf[:3])
            if len(_cf) > 3:
                _detail += f" (+{len(_cf) - 3} more)"
        print(f"[compose] shelf NOT put in scope for {target_name} (reason={_info.get('reason')}) — solving bare; "
              f"the 'citable' shelf could not be composed safely{_detail}", flush=True)
    elif _info.get("composed"):
        print(f"[compose] {target_name}: {_info.get('shelf_theorems')} shelf lemma(s) + {_info.get('defs')} def(s) "
              f"IN SCOPE (citable, not re-derived)", flush=True)
    return solve_adhoc(target_name, body, "", substrate=str(substrate), mode="dag_search",
                       timeout_s=timeout_s, notes=notes)


_SHELL_CONST = {"0", "1", "True", "False", "∅", "()", "Unit", "PUnit", "default", "arbitrary",
                "sorry", "trivial", "{}", "[]"}


def _degenerate_def_body(block: str) -> "str | None":
    """THE single degeneracy core (2026-06-24, tasteful consolidation): given ONE def/abbrev decl block, return its
    body text iff that body is a DEGENERATE CONSTANT (bare literal / True/False / ∅ / sorry / `fun _ => <const>`) —
    the def-shell laundering shape — else None. PARSING is 100% canonical `lean_source` (`split_at_proof` = binder-
    safe `:=`, `strip_comments`); NO regex parses the decl (the old `detect_def_shells` hand-rolled a multiline regex
    that returned BARE names while `decl_blocks` qualifies with the namespace — that mismatch forced a `.split('.')`
    band-aid at the vocab call site). Both consumers — the firewall's def-shell GATE and `_substrate_established_defs`'
    vocabulary EXCLUSION — call THIS on the SAME block, so they can never disagree and neither matches on names."""
    if _decl_kw(block) not in {"def", "abbrev"}:     # constant-shell laundering surface is def/abbrev (the #23 case);
        return None                                  # a structure/inductive/instance/axiom/notation is not a "shell"
    from ztare.leanmill.lean_source import split_at_proof, strip_comments
    _sig, proof = split_at_proof(block or "")        # proof = ":= <body>" (depth-0 `:=`, binder-safe), "" if none
    raw = strip_comments(proof[2:] if proof.startswith(":=") else proof).strip()
    if not raw:
        return None                                  # no `:=` body (e.g. a `structure … where`) ⇒ never a constant shell
    body = raw
    if body.startswith(("fun ", "fun\t", "λ")) and "=>" in body:   # strip a leading λ head: `fun _ => 0` ⇒ `0`
        body = body.split("=>", 1)[1].strip()
    # DEGENERATE = the WHOLE body is a single bare constant (after the λ-head strip): `:= 0` / `:= True` /
    # `fun _ => ∅` / `:= 5` / `:= sorry`. CONSERVATIVE BY CONTRACT — only an UNAMBIGUOUS bare constant flags, so a
    # real predicate/expression is NEVER false-rejected. RCA 2026-06-24: a first-TOKEN match (`tok in _SHELL_CONST`)
    # flagged any body STARTING with a constant — `0 < x ∧ 0 < y`, `1 + n`, `True ∧ p` — as a "shell", silently
    # rejecting every lemma over a simple well-formedness predicate (the AMM `PoolWellFormed` stall). The semantic
    # decoy notion is "the body ignores the def's inputs"; this cheap pre-gate stays strictly whole-body to honor
    # its own conservatism, and the LLM denotation/anchor layer (def_denotation) catches the non-obvious decoys.
    is_const = (body in _SHELL_CONST
                or re.fullmatch(r"-?\d+(\.\d+)?", body) is not None   # numeric LITERAL value-check, not decl parsing
                or body.startswith("sorry"))
    return raw if is_const else None


def detect_def_shells(formalization: str) -> "list[tuple[str, str]]":
    """Deterministic def-faithfulness PRE-gate for `define_then_state` output (#23). A `def Genus := 0`
    / `abbrev X := True` shell makes the theorem typecheck VACUOUSLY while the statement-level round-trip
    (which back-translates the THEOREM text, not the def BODY) passes — so a def-shell launders through
    the firewall. Flags def/abbrev/… declarations whose body is a DEGENERATE CONSTANT. CONSERVATIVE — only
    UNAMBIGUOUS constant shells, so it never false-rejects a real def. Returns [(name, reason)]; empty = no
    obvious shell. Canonical parse via `decl_blocks` + `_decl_is_definition` + `_degenerate_def_body` (one shared
    core with the vocabulary exclusion) — NO hand-rolled decl regex. (The full gate also back-translates each def +
    cold-judges it vs the NL — the LLM layer; this is the cheap core.)"""
    from ztare.leanmill.solver.statement_integrity import decl_blocks
    shells: "list[tuple[str, str]]" = []
    for name, block in decl_blocks(formalization or ""):
        b = (block or "").strip()
        if not name or not _decl_is_definition(b):
            continue
        raw = _degenerate_def_body(b)
        if raw is not None:
            shells.append((name, f"`{name}` body is a degenerate constant: {raw[:50]!r}"))
    return shells


# ── TYPECLASS-GENERALITY faithfulness leg (the sibling of detect_def_shells; inline here, NOT a separate module).
# Flags a formalization that assumes a STRONGER instance class than the informal statement's stated generality —
# the silent narrowing the round-trip glosses (`[LinearOrder]` where the NL said "partial order / pari-passu";
# `[Field]` where "ring"; an unimplied `[DecidableEq]`/`[Fintype]`/`[Nonempty]`). Caught on the APR corporate-
# waterfall close (2026-06-24): the blueprint asked for a PARTIAL priority order (incomparable / pari-passu
# tranches); the proof shipped `[LinearOrder]`.
#   WHY the structural firewall misses it: the instance hierarchy is a strength PARTIAL ORDER
#   (LinearOrder ⊃ PartialOrder ⊃ Preorder; Field ⊃ DivisionRing ⊃ CommRing ⊃ Ring) — a STRONGER instance is a
#   STRONGER hypothesis ⇒ a NARROWER theorem — but `[LinearOrder]` and `[Preorder]` give the SAME binder-count +
#   conclusion fingerprint, and the round-trip back-translates the (identical) CONCLUSION, so the reduction hidden
#   in an instance binder passes NL↔Lean faithfulness.
#   NEUROSYMBOLIC (operator: "no brittle determinism — handle it via the LLM judge, neurosymbolically"). The first
#   cut hardcoded a `_GENERALITY_DOMAINS` registry + keyword cues ("partial"/"linear"/"chain") — overfit + brittle,
#   un-coverable (Group/Monoid, Module, Metric, finite-dimensional, …). REPLACED with: (SYMBOLIC) `_instance_classes`
#   extracts the actual instance binders — a structural fact the model can't hallucinate away + a cheap gate (no
#   binders ⇒ no judge call); (NEURAL) a cross-family majority-of-N LLM judge compares those assumed structures
#   against the NL's stated generality (the model knows the Lean instance hierarchy + math generality — no registry).
#   Same judge infra as `_default_def_judge`/`default_directional_judge` (`_api_text`, `ZTARE_LEANMILL_JUDGE_SAMPLES`,
#   `_observe_roundtrip`); prompt in `prompts.GENERALITY_JUDGE_PROMPT`. Graceful-degrade to EMPTY when the judge is
#   dead (no keyword fallback — brittleness is the disease, not the cure).
#   RESEARCH: autoformalization faithfulness = capturing the source "at full strength, without ... hiding content in
#   TYPECLASS FIELDS"; "typeclass generality" is a named formal-quality dimension — Reliable Evaluation/Benchmarks
#   for Statement Autoformalization (arXiv:2406.07222), CriticLean (arXiv:2507.06181, critic-guided RL for exactly
#   this judgment), Autoformalize by Symbolic Equivalence & Semantic Consistency (arXiv:2410.20936 — the same
#   neurosymbolic split: symbolic checks + LLM semantic-consistency judge).
#   GOLDILOCKS: ADVISORY, never a hard gate (a narrower theorem is still TRUE — the kernel rightly closes it; a
#   deliberate specialization is legitimate). REPORTS a suspected narrowing for a scope-fidelity cross-check /
#   operator. Run against the BROADEST available intent — the blueprint/notes when present, else the per-rung NL.
#   `ZTARE_LEANMILL_GENERALITY_AUDIT=0` reverts.
def _instance_classes(statement: str) -> "list[str]":
    """Instance-binder classes `[C …]` / `[inst : C …]` in a statement's signature (leading class identifier).
    Bracket-MATCHED scan over the canonical signature (comments stripped, proof dropped) — not a brittle decl regex.
    This is the SYMBOLIC half: the assumed structures are a structural fact that grounds the neural judge (and a
    cheap gate — no instance binders ⇒ nothing can be over-assumed ⇒ skip the LLM call)."""
    try:
        from ztare.leanmill.lean_source import strip_comments, signature_before_proof, theorem_names, extract_signature
        s = strip_comments(statement or "")
        names = theorem_names(s)
        sig = (extract_signature(s, names[-1]) if names else "") or signature_before_proof(s)
    except Exception:  # noqa: BLE001 — never break on a parser hiccup
        sig = statement or ""
    classes: "list[str]" = []
    i, n = 0, len(sig)
    while i < n:
        if sig[i] == "[":
            depth, j = 1, i + 1
            while j < n and depth:
                depth += (sig[j] == "[") - (sig[j] == "]")
                j += 1
            inner = re.sub(r"^[A-Za-z_][\w']*\s*:\s*", "", sig[i + 1:j - 1].strip())   # drop a `name :`
            m = re.match(r"([A-Za-z_][\w'.]*)", inner)
            if m and m.group(1).split(".")[-1] not in classes:
                classes.append(m.group(1).split(".")[-1])
            i = j
        else:
            i += 1
    return classes


def typeclass_generality_audit(nl: str, lean_statement: str, *, judge_fn=None, model: "Optional[str]" = None) -> dict:
    """ADVISORY, NEUROSYMBOLIC generality-fidelity check. SYMBOLIC: extract the assumed instance binders. NEURAL: a
    cross-family majority-of-N LLM judge decides whether those structures are STRONGER (less general) than `nl`'s
    stated generality. Returns {"flags": [...], "advisory": True}; empty ⇒ no suspected narrowing (or no instance
    binders / judge unavailable). `nl` = the BROADEST intent (blueprint/notes when present). NEVER gates."""
    if os.environ.get("ZTARE_LEANMILL_GENERALITY_AUDIT", "1") == "0":
        return {"flags": [], "advisory": True, "disabled": True}
    classes = _instance_classes(lean_statement)          # SYMBOLIC gate + grounding
    if not classes:
        return {"flags": [], "advisory": True}           # no assumed instances ⇒ nothing to over-assume; no LLM call
    import os as _os
    _judge = judge_fn or (lambda _p: (_api_text(_p, model=model, label="autoformalize_generality_judge") or "").strip())
    prompt = prompts.GENERALITY_JUDGE_PROMPT.format(
        classes=", ".join(f"[{c}]" for c in classes), nl=(nl or "")[:2000],
        stmt=" ".join((lean_statement or "").split())[:600])
    try:
        n = max(1, int(_os.environ.get("ZTARE_LEANMILL_JUDGE_SAMPLES", "3") or "3"))
    except (TypeError, ValueError):
        n = 3
    raws: "list[str]" = []
    narrower, detail = 0, ""
    for _ in range(n):
        raw = (_judge(prompt) or "").strip()
        raws.append(raw)
        first = raw.splitlines()[0].strip() if raw else ""
        if first.upper().startswith("NARROWER"):
            narrower += 1
            detail = detail or first
    flagged = (narrower * 2 > n)                          # STRICT majority NARROWER (flaky-single-sample-safe)
    _observe_roundtrip("generality_judge", nl=(nl or "")[:400], classes=classes, n=n, narrower_votes=narrower,
                       raw_verdicts=[r[:160] for r in raws], flagged=flagged, model=model)
    flags = ([{"kind": "stronger_instance_than_nl", "classes": classes,
               "note": (detail or "judge: NARROWER — formalization assumes a stronger structure than the intent's "
                        "stated generality")}] if flagged else [])
    return {"flags": flags, "advisory": True}


# ADDED-HYPOTHESIS ambition audit (advisory, 2026-07-02): the EXPLICIT-binder face of the same ambition gap the
# typeclass audit covers for instances (§4.2a: nothing formal checks statement ⊨ NL ambition; the round-trip judge's
# documented weak leg is *added-hypothesis* weakenings, whose conclusion back-translates identically). Canonical
# instance: Topkis' "the unique maximizer" — a uniqueness HYPOTHESIS yields a true-but-WEAK theorem the whole
# firewall admits. Same neurosymbolic split, same discipline: (SYMBOLIC) extract the explicit propositional binders
# — a structural fact + a cheap gate (none ⇒ no LLM call); (NEURAL) a majority-of-N cross-family judge rules
# ADDED-vs-LICENSED against the broadest intent. GOLDILOCKS: ADVISORY, never gates (an over-hypothesized theorem is
# still TRUE; a deliberate restriction is legitimate). `ZTARE_LEANMILL_AMBITION_AUDIT=0` reverts.
# NOTE: named _HYP_PROP_MARKERS, not _PROP_MARKERS — the module already has a compiled-regex `_PROP_MARKERS`
# (line ~80, used via `.search` in the structural leg); a same-named tuple here SHADOWED it and crashed the
# firewall's structural check fail-closed (AttributeError '.search' on tuple — live on the fable ftap run,
# 2026-07-02). Module-level names must not collide across distant sections of a 2700-line file.
_HYP_PROP_MARKERS = ("=", "≤", "<", "≥", ">", "≠", "∈", "∉", "∧", "∨", "↔", "¬", "∀", "∃", "→",
                     "Nonempty", "Unique", "Injective", "Surjective", "Bijective", "Monotone", "StrictMono")


def _explicit_hypotheses(statement: str) -> "list[str]":
    """Explicit parenthesized binders `(h : P)` in the signature whose TYPE reads propositional (contains a
    relational/logical marker) — the symbolic grounding for the added-hypothesis judge. Bracket-MATCHED scan over
    the canonical signature (same discipline as `_instance_classes`); pure data binders (`(f : X → T → ℝ)` with no
    relational content beyond the arrow) are noise for THIS audit, so the arrow alone does not qualify — a missed
    hypothesis is only a lost advisory flag, never a lost soundness check."""
    try:
        from ztare.leanmill.lean_source import strip_comments, signature_before_proof, theorem_names, extract_signature
        s = strip_comments(statement or "")
        names = theorem_names(s)
        sig = (extract_signature(s, names[-1]) if names else "") or signature_before_proof(s)
    except Exception:  # noqa: BLE001 — never break on a parser hiccup
        sig = statement or ""
    hyps: "list[str]" = []
    i, n = 0, len(sig)
    while i < n:
        if sig[i] == "(":
            depth, j = 1, i + 1
            while j < n and depth:
                depth += (sig[j] == "(") - (sig[j] == ")")
                j += 1
            inner = sig[i + 1:j - 1].strip()
            if ":" in inner:
                typ = inner.split(":", 1)[1].strip()
                markers = [m for m in _HYP_PROP_MARKERS if m in typ]
                if markers and markers != ["→"]:          # arrow-only = a plain function type, not a Prop
                    h = " ".join(inner.split())[:160]
                    if h not in hyps:
                        hyps.append(h)
            i = j
        else:
            i += 1
    return hyps


def added_hypothesis_audit(nl: str, lean_statement: str, *, judge_fn=None, model: "Optional[str]" = None) -> dict:
    """ADVISORY, NEUROSYMBOLIC ambition-fidelity check (the added-hypothesis sibling of
    `typeclass_generality_audit`). SYMBOLIC: extract the explicit propositional hypothesis binders. NEURAL: a
    cross-family majority-of-N LLM judge decides whether any is ADDED — assumed though the intent never granted it
    (uniqueness, extra positivity, comparability, assuming-the-conclusion). Returns {"flags": [...], "advisory":
    True}; empty ⇒ nothing suspected (or no propositional binders / judge unavailable). NEVER gates."""
    if os.environ.get("ZTARE_LEANMILL_AMBITION_AUDIT", "1") == "0":
        return {"flags": [], "advisory": True, "disabled": True}
    hyps = _explicit_hypotheses(lean_statement)          # SYMBOLIC gate + grounding
    if not hyps:
        return {"flags": [], "advisory": True}           # nothing explicitly assumed ⇒ nothing added; no LLM call
    import os as _os
    _judge = judge_fn or (lambda _p: (_api_text(_p, model=model, label="autoformalize_ambition_judge") or "").strip())
    prompt = prompts.ADDED_HYPOTHESIS_JUDGE_PROMPT.format(
        hyps="\n".join(f"  ({h})" for h in hyps), nl=(nl or "")[:2000],
        stmt=" ".join((lean_statement or "").split())[:600])
    try:
        n = max(1, int(_os.environ.get("ZTARE_LEANMILL_JUDGE_SAMPLES", "3") or "3"))
    except (TypeError, ValueError):
        n = 3
    raws: "list[str]" = []
    added, detail = 0, ""
    for _ in range(n):
        raw = (_judge(prompt) or "").strip()
        raws.append(raw)
        first = raw.splitlines()[0].strip() if raw else ""
        if first.upper().startswith("ADDED"):
            added += 1
            detail = detail or first
    flagged = (added * 2 > n)                             # STRICT majority ADDED (flaky-single-sample-safe)
    _observe_roundtrip("added_hypothesis_judge", nl=(nl or "")[:400], hypotheses=hyps, n=n, added_votes=added,
                       raw_verdicts=[r[:160] for r in raws], flagged=flagged, model=model)
    flags = ([{"kind": "added_hypothesis_not_in_nl", "hypotheses": hyps,
               "note": (detail or "judge: ADDED — formalization assumes an explicit hypothesis the intent "
                        "never granted")}] if flagged else [])
    return {"flags": flags, "advisory": True}


def _default_def_judge(nl: str, decl: str, *, model: "Optional[str]" = None) -> bool:   # model=None ⇒ config round-trip model
    """Cold cross-family (gemini) judge for ONE Lean definition vs the NL intent. Returns True (faithful)
    unless a STRICT MAJORITY of N votes give a CLEAR `UNFAITHFUL` verdict — FAITHFUL / ambiguous / empty /
    error all → True (admit), so the layer does NOT over-reject faithful defs (detect_def_shells + the
    statement-level firewall are the fail-closed layers; this catches the clear NON-constant wrong-object /
    placeholder). MAJORITY-OF-N (2026-06-11, same flaky-single-sample class as `default_directional_judge`):
    a lone spurious `UNFAITHFUL` used to reject a correct def; now reject only on a strict majority. Votes +
    raw verdicts logged via `_observe_roundtrip`."""
    import os as _os
    prompt = prompts.DEF_JUDGE_PROMPT.format(nl=(nl or "")[:1200], decl=(decl or "")[:800])
    try:
        n = max(1, int(_os.environ.get("ZTARE_LEANMILL_JUDGE_SAMPLES", "3") or "3"))
    except (TypeError, ValueError):
        n = 3
    raws: "list[str]" = []
    unfaithful = 0
    for _ in range(n):
        raw = (_api_text(prompt, model=model, label="autoformalize_def_judge") or "").strip()
        raws.append(raw)
        first = raw.upper().splitlines()[0] if raw else ""
        if first.startswith("UNFAITHFUL"):
            unfaithful += 1
    faithful = not (unfaithful * 2 > n)                  # reject ONLY on a strict majority of UNFAITHFUL (admit-biased)
    _observe_roundtrip("def_judge", nl=(nl or "")[:400], decl=(decl or "")[:400], n=n,
                       unfaithful_votes=unfaithful, raw_verdicts=[r[:120] for r in raws], faithful=faithful, model=model)
    return faithful


def default_def_faithfulness(nl: str, formalization: str, *, judge_fn=None) -> dict:
    """LLM-per-def layer of the def-faithfulness gate (#23): cold-judge each def/abbrev/structure against
    the NL intent. Complements `detect_def_shells` (constant shells) by catching a NON-constant UNFAITHFUL
    def (right shape, wrong object). Rejects ONLY on a clear UNFAITHFUL verdict (biased to admit — see
    `_default_def_judge`). Returns {checked, unfaithful:[{name, decl}]}; `judge_fn(nl, decl)->bool` injectable."""
    decls = re.findall(
        r"(?ms)^\s*(?:noncomputable\s+|private\s+|scoped\s+)*(?:def|abbrev|structure)\s+[A-Za-z_][\w'.]*"
        r".*?(?=\n\s*(?:noncomputable\s+|private\s+|scoped\s+)*"
        r"(?:def|abbrev|structure|inductive|theorem|lemma|instance|class|namespace|end|open|variable|#)\b|\Z)",
        formalization)
    if not decls:
        return {"checked": 0, "unfaithful": []}
    judge_fn = judge_fn or _default_def_judge
    unfaithful = []
    for decl in decls:
        nm = re.search(r"(?:def|abbrev|structure)\s+([A-Za-z_][\w'.]*)", decl)
        name = nm.group(1) if nm else "?"
        try:
            faithful = judge_fn(nl, decl.strip())
        except Exception:  # noqa: BLE001
            faithful = True   # judge error → admit (do not over-reject on a tooling failure)
        if faithful is False:
            unfaithful.append({"name": name, "decl": decl.strip()[:120]})
    return {"checked": len(decls), "unfaithful": unfaithful}


def _solve_refutation(sv) -> str:
    """The solver's signal that the FORMAL target itself is false / mis-stated — the trigger for a governed
    reformulation re-entry. Both strengths are now KERNEL-GATED before reaching here (so acting on them is
    sound, and a reformulation additionally re-passes the firewall so it cannot launder): (a) HARD — the
    falsify move kernel-proved ¬G (`outcome="falsified"`); (b) SOFT — the leaf flagged the statement mis-stated
    (`-- STATEMENT-FALSE:`) AND `solve_adhoc` independently CONFIRMED it via a kernel ¬G attempt (#143; only
    then is `statement_false` set — an UNVERIFIED claim lands in `statement_false_unverified` and is NOT a
    refutation, which is what stops the v7 deadlock on a true-but-hard lemma the leaf wrongly flagged). The
    `statement_false_verified` flag is the defense-in-depth guard: the SOFT path counts only when the verify
    gate confirmed it, OR when that gate was explicitly disabled (=0 opt-out, legacy A/B baseline). Returns
    the refutation text (witness/counterexample/reason), or "" if not refuted."""
    if not isinstance(sv, dict):
        return ""
    control_verdict = sv.get("control_verdict")
    if isinstance(control_verdict, dict):
        try:
            from ztare.leanmill.control_plane import Verdict, VerdictKind

            typed = Verdict.from_json(control_verdict)
            if typed.kind is VerdictKind.REFUTED:
                source = typed.kernel_refutation_source()
                return (typed.detail or source)[:600] if source else ""
        except (TypeError, ValueError):
            return ""
    r0 = (sv.get("results") or [{}])[0] if (sv.get("results")) else {}
    if (r0.get("outcome") or "") == "falsified":
        return (r0.get("falsifier") or r0.get("notes") or "kernel-checked ¬G (falsify move)")[:600]
    sf = r0.get("statement_false") or sv.get("statement_false")
    if not sf:
        return ""
    # SOFT path: only a kernel-CONFIRMED claim refutes. Accept when solve_adhoc verified it, or when the
    # verify gate was explicitly turned off (the legacy/A-B baseline). A bare claim with the gate ON but no
    # confirmation is NOT trusted here (belt-and-suspenders behind solve_adhoc's single capture point).
    _verified = bool(sv.get("statement_false_verified") or r0.get("statement_false_verified"))
    _gate_off = os.environ.get("ZTARE_LEANMILL_VERIFY_STATEMENT_FALSE", "1") == "0"
    if not (_verified or _gate_off):
        return ""
    return str(sf)[:600]


def _record_statement_false_no_good(statement: str, refutation: str, *, confirmed: bool,
                                    source: str = "reformulation_refutation") -> bool:
    """Persist a statement-false no-good only after the kernel-confirmed path.

    A soft leaf refutation may be useful as reformulation feedback, but it is
    not cross-run governance memory. This helper is the narrow ledger membrane:
    only a confirmed refutation can enter `NoGoodStore` as `statement_false`.
    """
    if not confirmed or not (statement or "").strip() or not (refutation or "").strip():
        return False
    try:
        from ztare.leanmill.solver.no_good_store import NoGoodStore as _NGS
        from ztare.leanmill.solver.solver_core import OUT_DIR as _OUTD
        return bool(_NGS(_OUTD / "solver_lane_no_good_store.jsonl").record(
            statement, "statement_false", (refutation or "kernel ¬G (statement false)")[:300],
            confirmed=True, source=source))
    except Exception:  # noqa: BLE001 — ledger coordination is advisory; never break the reformulation
        return False


def _substrate_proven_shelf(substrate_src: str) -> str:
    """The substrate's already-PROVEN (sorry-free, kernel-checked) THEOREM signatures, rendered for the
    reformulation feedback so a refuted target can ADOPT + CITE the agent's OWN proven strengthened result
    instead of re-deriving a weak one from the prose — the routing the binding needs (the consolidation pass
    often proves the corrected/strong theorem, but the fresh re-formalizer reads the literal NL and never
    realizes it). `substrate_src` is the REGISTERED substrate `.lean` file's CONTENT — the authoritative source:
    the notes only NAME the theory file, while consolidation BANKS the proven corrected theory INTO that file, so
    a notes-only read returned EMPTY once consolidation had moved the proofs to the file (the 2026-06-23
    convergence gap: the reformulation had no proven-strong to cite, so it re-derived the weak version and
    unfolded the conclusion). Parsing is 100% canonical `lean_source`/`statement_integrity` — NO regex: `decl_blocks`
    + `_decl_is_definition` (kind) + `extract_signature`. Domain-agnostic: theorems/lemmas only, sorry-free; skips
    the engine's OWN scaffolding (`anchor_`/`witness_`) so real RESULTS surface first. Not laundering — it surfaces
    the agent's own proven work; the agent still states + cites + the kernel re-verifies. "" when nothing proven."""
    if not (substrate_src or "").strip():
        return ""
    try:
        from ztare.leanmill.solver.statement_integrity import decl_blocks
        from ztare.leanmill.lean_source import extract_signature
    except Exception:  # noqa: BLE001 — never block the reformulation on a parser import
        return ""
    from ztare.leanmill.lean_source import signature_before_proof as _sig_of_block, first_theorem_name, has_sorry
    out: "list[str]" = []
    seen: "set[str]" = set()
    for name, block in decl_blocks(substrate_src):
        # canonical decl-KIND classification (NO regex): `_decl_is_definition` strips attrs/modifiers and reads the
        # keyword against `_DEF_KINDS`; a NON-definition WITH a name is a theorem/lemma RESULT (an `example` is
        # anonymous ⇒ excluded by the name check). PROVEN only (skip sorried/admitted); skip the engine's own
        # non-result scaffolding (`anchor_`/`witness_`).
        if not name or _decl_is_definition(block):
            continue
        if has_sorry(block):   # comment-ROBUST (RCA 2026-06-25: `"sorry" in block` is a SUBSTRING that dropped
            continue           # proven theorems whose COMMENT mentioned sorry; the kernel re-verifies any cite)
        # NAMESPACE-QUALIFIED-NAME BUG (RCA 2026-06-25, the AMM re-proof): `decl_blocks` returns the FQ name
        # (`AMMConstantProduct.roundTripXReturn_le_input`) for a theory wrapped in `namespace …`, but the decl is
        # WRITTEN short (`theorem roundTripXReturn_le_input`) — so `extract_signature(src, fq_name)` searched for
        # `theorem AMMConstantProduct.…` (a string that does not exist) → empty sig → EVERY namespaced theorem was
        # silently dropped → the shelf was EMPTY → the planner re-proved already-banked lemmas. Cure: take the
        # signature from the BLOCK we already hold (canonical `signature_before_proof`, robust to qualification),
        # exactly as the working `_substrate_established_defs` sibling renders its blocks verbatim — no re-search.
        short = first_theorem_name(block) or str(name).split(".")[-1]
        if not short or short in seen or short.startswith(("anchor_", "witness_")):
            continue
        sig = " ".join((_sig_of_block(block) or "").split())[:240]   # `theorem <short> <binders> : <concl>`
        if sig:
            out.append(f"  • {sig}")
            seen.add(short)
        if len(out) >= 40:
            break
    return "\n".join(out)


def _substrate_established_defs(substrate_src: str, *, max_chars: int = 4000) -> str:
    """The substrate's already-ESTABLISHED definitions, rendered VERBATIM (full `def`/`abbrev`/`structure`/
    `inductive`/`class` block) so a fresh formalizer can COPY the canonical vocabulary instead of re-deriving it
    from the prose. This is the DEFINITION-level companion to `_substrate_proven_shelf` (which surfaces proven
    THEOREM signatures and DELIBERATELY drops defs): the orphaned-shelf root cause (2026-06-24, APR `AbsolutePriority`
    drift) was that EVERY formalization-context path showed def NAMES (via lemma signatures) but never the canonical
    def BODIES — so each self-contained probe re-authored the shared vocabulary, and the lemmas (proven against the
    canonical body) silently failed to compose into a target that minted a divergent body of the same name. Surfacing
    the bodies lets the agent reuse them by reference; if it needs a stronger notion it introduces a NEW name + bridge
    (the firewall + the compose conflict-check stay the deterministic boundary — this only supplies the vocabulary,
    it does not pin or coerce). Canonical parser (`decl_blocks` + `_decl_is_definition`) — NO regex; verbatim blocks
    (copy-pasteable Lean), deduped by name, length-capped. "" when the substrate has no definitions (⇒ no-op parity).

    EXCLUDES degenerate-constant defs (witness/example scaffolding like `ZeroPayment := fun _ => 0`,
    `boolTwoTrancheClaims := fun _ => 1`) via `_degenerate_def_body` — the SAME core the firewall's def-shell GATE
    uses, applied to the SAME decl block (no name-matching, so the two can never disagree) — so by construction the
    vocabulary can never carry a def the gate would then REJECT as a shell (the 2026-06-24 interaction bug: copying
    the theory's legitimate constant-bodied witness defs verbatim tripped the gate → false-rejected the whole
    formalization). Those defs are concrete WITNESSES, not the shared CONCEPT vocabulary a fresh probe needs to
    reuse, so dropping them is correct on both counts."""
    if not (substrate_src or "").strip():
        return ""
    try:
        from ztare.leanmill.solver.statement_integrity import decl_blocks
    except Exception:  # noqa: BLE001 — never block formalization on a parser import
        return ""
    blocks: "list[str]" = []
    seen: "set[str]" = set()
    total = 0
    for name, block in decl_blocks(substrate_src):
        b = (block or "").strip()
        if not name or name in seen or not _decl_is_definition(b):
            continue
        if _degenerate_def_body(b) is not None:   # SAME core the def-shell gate uses, on the SAME block — no name-match
            continue   # degenerate-constant witness/example def — not shared vocabulary; would trip the def-shell gate
        seen.add(name)
        if total + len(b) > max_chars and blocks:   # keep at least one; otherwise stop before bloating the prompt
            break
        blocks.append(b)
        total += len(b)
    return "\n\n".join(blocks)


def _read_substrate_src(notes: "str | None", sandbox) -> str:
    """The registered campaign theory `.lean` file's CONTENT (the authoritative def + proven-result source), or "".
    The notes only NAME the theory file (`## Theory file`); consolidation BANKS the proven corrected theory INTO it.
    ONE reader so the formalize-context vocabulary injection and the reformulation `_substrate_proven_shelf` feedback
    read the SAME source the SAME way (no sibling re-reads). Canonical `parse_theory_file` for the name; `sandbox`
    is the lean_root. Best-effort; "" on any miss (⇒ the callers degrade to no-substrate, never break)."""
    try:
        from ztare.leanmill.solver.autoformalize_notes import parse_theory_file as _ptf
        from pathlib import Path as _P
        _trel = _ptf(notes or "")
        if _trel and sandbox is not None:
            _tp = (_P(sandbox) / _trel) if not _P(_trel).is_absolute() else _P(_trel)
            if _tp.exists():
                return _tp.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 — substrate read is best-effort; callers handle ""
        return ""
    return ""


def _reformulate_feedback(prior_stmt: str, refutation: str, proven_shelf: str = "") -> str:
    """General-purpose formalizer context for the reformulation re-entry, used whenever a formalization is
    KERNEL-REFUTED (¬G proven) during proving. The agent already holds the substrate + the refutation in context,
    so this ORIENTS rather than informs-or-dictates: a refuted statement is FALSE because a HYPOTHESIS is too
    WEAK, so the intended true theorem needs a STRONGER hypothesis than the most literal reading of the prose. The
    text only points the agent to STRENGTHEN and shows it the refuting case; it names NO specific definition — the
    agent must still find, state, and prove the strengthening, and the faithfulness firewall + statement_integrity
    re-gate every reformulation (a different or weaker theorem is rejected). Non-laundering and domain-agnostic by
    construction. `proven_shelf` (when supplied) lets the agent ADOPT + CITE its OWN already-proven substrate
    theorem rather than re-derive — the routing the binding needs (the fresh re-formalizer otherwise never
    realizes the consolidation already proved the corrected theorem). The prompt TEXT lives in `prompts.py`
    (`REFORMULATE_FEEDBACK` / `REFORMULATE_SHELF_BLOCK`) — this only assembles it; the block is ADVISORY (the
    agent judges relevance, the kernel re-verifies any cite), not coercive."""
    from ztare.leanmill.solver import prompts as _p
    _shelf_block = _p.REFORMULATE_SHELF_BLOCK.format(shelf=proven_shelf) if (proven_shelf or "").strip() else ""
    return _p.REFORMULATE_FEEDBACK.format(
        prior_stmt=(prior_stmt or "").strip()[:500],
        refutation=(refutation or "").strip()[:600],
        shelf_block=_shelf_block)


def _planner_subdag(sv) -> "Optional[dict]":
    """The planner's sub-DAG `{lemmas, chain, lnames}` for the notes write-back / compound. `route_and_solve`
    returns `{routed, decomposition: {lemmas, chain, lnames}, solution}` — the lemmas live UNDER `decomposition`.
    Surface THAT, not the whole `iso_route` wrapper: the prior code set `out["decomposition"] = sv["iso_route"]`,
    so compound/refined-notes looked for `["lemmas"]` one level too high, found None, and the self-evolving loop
    PERSISTED NOTHING (the agent's mid-proof decomposition was dropped between runs — the amnesia bug)."""
    if not isinstance(sv, dict):
        return None
    return (sv.get("iso_route") or {}).get("decomposition") or None


def _needs_literal_first_recovery(nl: str, af: "AutoformalizeResult") -> bool:
    """LITERAL-FIRST RECOVERY trigger (2026-06-23). True iff the firewall REJECTED this FIRST formalization as a
    silent STRENGTHENING of the literal claim whose falsity we have NOT yet established — the one case where the
    honest fix is to re-enter literal-first (establish the literal's truth-status, then strengthen via the override)
    rather than dead-end. Gated tight + fail-CLOSED (a False here only ever KEEPS the rejection; it can admit
    nothing — the re-entry it authorises re-passes the SAME firewall + kernel):
      • round-trip rejection — the weakened-vs-literal signal — NOT a malformed/vacuous/def-shell reject (those are
        not "the agent strengthened too early", and re-entering would not help);
      • the candidate FINGERPRINTS as a real statement WITH hypotheses (a conclusion connective + ≥1 explicit
        binder), so there is a literal to weaken back to (a degenerate/garbage reject is skipped);
      • NO ¬G license exists yet for this NL (`refuted_literal`==""): if one did, the override would already have
        governed this statement (admit on a valid strengthening, or reject on shape) — recovery cannot add anything.
    Reuses the firewall's own verdict, the canonical fingerprint parser, and the ONE refutation ledger surfaced via
    `refuted_literal` — no parallel surface, no domain specifics."""
    if af.verdict.accepted:
        return False
    if "round-trip" not in (af.verdict.reason or "") and af.verdict.checks.get("round_trip_faithful") is not False:
        return False
    # Fingerprint the TARGET theorem (not the multi-decl blob — same canonical-target rule as GATE3): a real
    # statement with hypotheses to weaken back to. (`conclusion_op` is intentionally NOT required — a predicate-
    # application conclusion parses to None, and the recovery is a bounded backstop, so over-skipping there would
    # silently disable it on exactly the structured targets it is for.)
    if (statement_fingerprint(af.lean_statement or "").get("n_explicit_binders") or 0) < 1:
        return False
    try:
        from ztare.leanmill.solver.faithfulness_store import FaithfulnessStore
        from ztare.leanmill.solver.solver_core import OUT_DIR as _OUT
        if (FaithfulnessStore(_OUT / "solver_lane_faithfulness_store.jsonl").refuted_literal(nl) or "").strip():
            return False   # a ¬G license already exists ⇒ the override path governs this, not a recovery
    except Exception:  # noqa: BLE001 — no store ⇒ no license ⇒ recovery remains safe to attempt
        pass
    return True


def autoformalize_and_solve(nl: str, *, sandbox, substrate=None,
                            formalize_fn=None, compile_fn=None, triviality_fn=None,
                            backtranslate_fn=None, judge_fn=None, structural_fn=None,
                            solve_fn=None, timeout_s: int = 600, max_refines: int = 2,
                            def_faithfulness: bool = False, notes: "str | None" = None,
                            extra_context: str = "", reformulate_budget: "int | None" = None,
                            shelf_prelude: str = "", _literal_first_done: bool = False,
                            _strengthening_mode: bool = False) -> dict:
    """THE END-TO-END LINK: NL → autoformalize (faithfulness firewall) → if admitted, solve_adhoc
    (solver + governance kernel). The firewall GATES the solver — an unfaithful / vacuous / trivial
    statement is rejected BEFORE any solve, which is what prevents the worst laundering (an opaque or
    weakened statement that then gets "closed"). Every leg is injectable (mocks in tests); the defaults
    wire the real apparatus. Returns the formalization, the faithfulness verdict, and the closure.

    REFORMULATION RE-ENTRY (ZTARE_LEANMILL_REFORMULATE=1, default-off; rounds = ZTARE_LEANMILL_REFORMULATE_ROUNDS
    or 1): when the solver REFUTES the formal target (kernel ¬G, or a leaf `statement_false` flag — the
    iso_lemma1 case, only discoverable by attempting the proof), re-open the SAME firewall on the SAME nl with
    the refutation as formalizer context (a warm RESUME → the agent continues, not a cold re-call), bounded.
    Architecture: the AGENT owns formalize↔prove↔reformulate; the HARNESS owns only the independent faithfulness
    gate + kernel audit (the agent can't be its own faithfulness judge). SOUND: each reformulation re-passes the
    firewall against the original nl; the refuted formalization is reported, NEVER credited as a closure."""
    cfg = AutoformalizeSolveConfig.from_boundary(
        timeout_s=timeout_s,
        max_refines=max_refines,
        def_faithfulness=def_faithfulness,
        reformulate_budget=reformulate_budget,
        literal_first_done=_literal_first_done,
        strengthening_mode=_strengthening_mode,
    )
    timeout_s = cfg.timeout_s
    max_refines = cfg.max_refines
    def_faithfulness = cfg.def_faithfulness
    reformulate_budget = cfg.reformulate_budget
    _literal_first_done = cfg.literal_first_done
    _strengthening_mode = cfg.strengthening_mode
    substrate = substrate or sandbox
    _caller_formalize_fn = formalize_fn   # PRESERVE the caller's value (None in prod) for the reformulate recursion,
    #                                       so the re-entry rebuilds formalize_fn with the NEW refutation context.
    _caller_structural_fn = structural_fn  # PRESERVE the caller's structural_fn (None in prod) so a RE-ENTRY rebuilds
    #   it fresh against the CURRENT store reference — `reference(nl)` drops a rendering once it is recorded kernel-
    #   FALSE, so a literal-first re-entry that deposits then refutes the literal correctly re-fetches expected=None
    #   and the structural silent-weakening leg does NOT block the strengthened reformalization (it would, with a
    #   stale literal fingerprint baked into the parent's rebuilt closure).
    formalize_fn = formalize_fn or default_formalize
    _fctx = ""   # the assembled formalizer context (vocabulary + blueprint + reentry cue); also fed to multistep escalation
    if formalize_fn is default_formalize:
        # Thread the LEAN ROOT so the INTERACTIVE formalizer (default-on) can start the warm REPL + the agent can
        # `lean-check`/`search` to a TYPECHECKING statement. Plus the blueprint NOTES as render context (#88; it
        # was notes-blind). DEFAULT-ON (anti-sibling cure 2026-06-21): the notes-blind formalizer over-modeled an
        # abstract Čech target onto Mathlib's full Grothendieck-site stack (`PresheafOfGroups.OneCocycle`/`H1`)
        # because it never saw the blueprint's own "render over the minimal concrete model" encoding guidance —
        # the ONE instruction that steers it to a tractable encoding was withheld by a default-OFF flag. The
        # firewall still gates faithfulness, so the notes can NEVER launder an unfaithful statement — they only
        # RAISE the faithful-AND-tractable render rate. So this is default-on; set ZTARE_LEANMILL_FORMALIZE_NOTES=0
        # for the notes-blind A/B baseline. `extra_context` carries the reformulate refutation feedback
        # (warm-resumed agent's continuation cue) on a re-entry.
        _notes_ctx = notes if (os.environ.get("ZTARE_LEANMILL_FORMALIZE_NOTES", "1") != "0" and (notes or "").strip()) else ""
        # ESTABLISHED-VOCABULARY (2026-06-24 — the orphaned-shelf / def-drift cure). THE single door: every
        # formalization (first pass, reformulation re-entry, literal-first recovery) builds its formalizer context
        # HERE. The campaign's proven lemmas are checked against the canonical def BODIES in the substrate theory
        # file, but every context path only ever surfaced def NAMES (via lemma signatures) — so each self-contained
        # probe re-authored the shared vocabulary from the prose, and a target that minted a divergent same-named def
        # (APR `AbsolutePriority`: 2-clause vs the proven 1-clause) silently ORPHANED its own shelf at compose time
        # → solved bare → exact_gap. Surfacing the canonical BODIES with the reuse-verbatim norm lets the formalizer
        # reuse them by reference (agency preserved: it still chooses reuse vs extend-under-a-new-name; the firewall +
        # compose conflict-check stay the only deterministic boundary). "" ⇒ byte-identical to before.
        _vocab = ""
        if os.environ.get("ZTARE_LEANMILL_ESTABLISHED_VOCAB", "1") != "0":
            _substrate_src0 = _read_substrate_src(notes, sandbox)
            _defs0 = _substrate_established_defs(_substrate_src0)
            if _defs0.strip():
                from ztare.leanmill.solver import prompts as _pv
                _vocab = _pv.ESTABLISHED_DEFS_NOTE.format(defs=_defs0)
                print(f"[formalize] established-vocabulary surfaced: {_defs0.count(chr(10) + chr(10)) + 1} canonical "
                      f"def(s) given to the formalizer (reuse-verbatim — prevents the orphaned-shelf drift)", flush=True)
            # PROVEN-SHELF AT FORMALIZE (2026-06-25, the AMM `reachable_pool_wellFormed` gap RCA): the def-body
            # companion above was wired here, but the proven-LEMMA shelf (each banked rung's EXACT conclusion) was
            # surfaced ONLY in reformulation feedback — so a compounding target was formalized BLIND to what its
            # named banked rung actually CONCLUDES (the bank proved the trajectory predicate `TradesKeepWellFormed`,
            # not the endpoint `PoolWellFormed (executeTrades …)` the prose asked to "cite"). The formalizer then
            # wrote an endpoint statement matching no banked conclusion → no cite → single-trade decomposition → gap.
            # Surface the actual signatures here (the SAME chokepoint, the SAME single reader) so the formalizer can
            # MATCH a rung or state a DISCLOSED corollary that cites it. Embedder-INDEPENDENT (lexical), so it holds
            # even when the semantic shelf is dead. Advisory; the firewall still gates faithfulness. =0 reverts.
            if os.environ.get("ZTARE_LEANMILL_PROVEN_SHELF_AT_FORMALIZE", "1") != "0":
                _shelf0 = _substrate_proven_shelf(_substrate_src0)
                if _shelf0.strip():
                    from ztare.leanmill.solver import prompts as _pv
                    _vocab = _vocab + _pv.PROVEN_SHELF_NOTE.format(shelf=_shelf0)
                    print(f"[formalize] proven-shelf surfaced: {_shelf0.count(chr(10)) + 1} banked kernel-checked "
                          f"lemma signature(s) given to the formalizer (cite/bridge — prevents re-deriving a banked "
                          f"rung under a conclusion it does not have)", flush=True)
        # CARRIER-PRESERVATION (2026-07-05, THE CLOB carrier-ghost that blocked autonomous closure): the def
        # bodies above carry the substrate's EXACT typeclass instances (e.g. `[LinearOrder K]`), but a self-
        # contained re-declaration lets the LLM substitute a WEAKER order ([LT K]/[LE K]) — a partial-order version
        # that is a DIFFERENT, FALSE theorem. The carrier gate then correctly REJECTS it → reject loop → never
        # closes. Surface the substrate's `variable` context VERBATIM + a hard directive to preserve the exact
        # instances, so the formalizer stops weakening at the SOURCE (vs the gate catching it downstream forever).
        # Monotone (only the substrate's own consistent carrier — the single-door `campaign_variables`); ADVISORY
        # (the firewall + carrier gate stay the deterministic boundary). No substrate ⇒ "" ⇒ byte-parity.
        try:
            from ztare.formal.repl_compile import campaign_variables as _cvars_fw
            _cv_fw = [v for v in (_cvars_fw() or []) if v.strip()]
            if _cv_fw:
                from ztare.leanmill.solver import prompts as _pcarr
                _vocab = _vocab + _pcarr.CARRIER_CONTEXT_NOTE.format(carrier="\n".join(_cv_fw))
        except Exception:  # noqa: BLE001 — carrier context is additive; a failure keeps the prior vocab
            pass
        _fctx = (_vocab + _notes_ctx + extra_context).strip()
        formalize_fn = lambda _nl: default_formalize(_nl, lean_root=sandbox, context=_fctx)  # noqa: E731
    compile_fn = compile_fn or (lambda s: default_compile(s, sandbox))
    compile_diagnose_fn = lambda s: default_compile_diagnose(s, sandbox)  # noqa: E731 — advisory Lean-error text for the refine hint (not a gate)
    triviality_fn = triviality_fn or (lambda s: default_triviality(s, sandbox))
    backtranslate_fn = backtranslate_fn or default_backtranslate
    judge_fn = judge_fn or default_directional_judge
    solve_fn = solve_fn or (lambda n, s: default_solve(n, s, substrate=substrate, timeout_s=timeout_s,
                                                        notes=notes, shelf_prelude=shelf_prelude))

    # FAITHFULNESS STORE (#86, ZTARE_LEANMILL_FAITHFULNESS_STORE=1; default-off = byte-parity). The
    # autoformalize axis was the ONLY one that learned nothing — every faithfulness verdict recomputed cold,
    # and `structural_faithfulness` ran advisory-NO-OP because production never fed it a reference. When ON +
    # no caller-supplied structural_fn: recall a prior CONFIRMED faithful rendering of THIS NL and feed its
    # fingerprint as the `expected` reference so the silent-weakening guard runs LOAD-BEARING for an exact
    # NL identity; semantic retrieval is generation-only; deposit on a
    # fresh admit. Parity-safe: a first-seen NL has no reference ⇒ `structural_faithfulness(expected=None)` =
    # True (admit, as today); only a RE-seen NL whose new rendering is WEAKER than the stored faithful one is
    # newly caught (a sound tightening). The firewall's kernel legs remain the sole faithfulness arbiter.
    _fstore = None
    _prior_confirmed_fn = None
    _ref_stmt = ""   # the CONFIRMED-FAITHFUL reference statement (if any) — fed into the weakening-refine feedback
    if structural_fn is None and os.environ.get("ZTARE_LEANMILL_FAITHFULNESS_STORE", "1") != "0":   # DEFAULT-ON 2026-06-12 (deposit only on CONFIRMED admits; recall only STRENGTHENS the guard; =0 reverts)
        try:
            from ztare.leanmill.solver.faithfulness_store import FaithfulnessStore
            from ztare.leanmill.solver.solver_core import OUT_DIR as _OUT
            _fstore = FaithfulnessStore(_OUT / "solver_lane_faithfulness_store.jsonl")
            _ref0 = _fstore.reference(nl) or {}
            _ref_exact = bool(_ref0.get("exact"))
            # Semantic retrieval is generation-side evidence only.  It must
            # never provide a fingerprint or statement to a hard identity
            # gate; only an exact NL key is allowed to do that.
            _exp, _ref_stmt = _reference_gate_inputs(_ref0)
            # KERNEL accept-override (2026-07-02): the syntactic fingerprint alone false-rejects a faithful RESTYLE
            # of the stored reference (∀-fronting / implicit-explicit / binder-order / inferable instance) — a
            # cross-run/cross-model recurrence. When it mismatches, defer to kernel DEFEQ vs the stored reference
            # statement (same Prop ⇒ accept; a real weakening is a type mismatch ⇒ reject stands). Upgrade-only +
            # fail-closed; ZTARE_LEANMILL_FAITHFULNESS_KERNEL_OVERRIDE=0 reverts to the pure-syntactic check.
            _kov = os.environ.get("ZTARE_LEANMILL_FAITHFULNESS_KERNEL_OVERRIDE", "1") != "0"
            # confirms() FIRST (2026-07-03): a statement that name-agnostically matches a CONFIRMED-faithful
            # rendering for this NL is the same Prop as one already admitted — skip the variance-prone structural
            # reference-comparison too (not just the round-trip judge below). Without this, the load-bearing
            # structural leg re-litigates a re-confirmed statement against a NON-DETERMINISTIC prior formalization
            # (the reference is the LATEST confirmed rendering, which differs run-to-run) and false-rejects a
            # faithful restyle as `structure NOT preserved` — the DeFi lemmas regressed exactly this way once
            # earlier runs had recorded their own confirmations. SOUND: same argument as the round-trip short-
            # circuit — the deterministic legs (compile / triviality) still run; confirms() only skips the
            # reference-comparison for a Prop ALREADY confirmed faithful, so it can never admit a weaker one.
            structural_fn = (lambda _nl, _s: _fstore.confirms(_nl, _s)  # noqa: E731
                             or structural_faithfulness(_nl, _s, expected=_exp)
                             or (_kov and _kernel_defeq_to_reference(_s, _ref_stmt, sandbox)))
            # #105: a re-seen statement that matches a stored CONFIRMED rendering skips the flaky round-trip JUDGE
            # (the deterministic legs — incl. the structural reference above — still run, so this can only skip the
            # variance-prone LLM, never admit a different/weaker statement). NAME-AGNOSTIC via the store's single
            # `confirms()` door (2026-07-03 RCA): the old inline EXACT-string compare INCLUDED the theorem name, so
            # the formalizer's run-to-run name non-determinism defeated the short-circuit and the flaky judge
            # false-rejected a re-confirmed target (the DeFi liquidation target — closed run N, round-trip-rejected
            # run N+1 on the identical Prop under a new name). `confirms()` keys on the proof_cache normalizer.
            def _prior_confirmed_fn(_nl, _s, _ref=_ref_stmt):  # noqa: E306
                # confirms() store OR the reference-reused CONFIRMED statement. RCA 2026-07-05 (CLOB thrash):
                # a re-seen NL's rung is reused VERBATIM from `reference()` — the kernel-confirmed, non-refuted,
                # firewall-ACCEPTED rendering — yet confirms() missed it (its faithfulness row was keyed to an
                # EARLIER run's NL phrasing), so every reused iso_lemmaN got re-thrown to the NON-DETERMINISTIC
                # back-translate judge and flaky-rejected (rejected_by_firewall on an axiom-clean proven lemma).
                # A statement name-agnostically EQUAL to the reference IS that already-admitted Prop, so skip the
                # flaky JUDGE (the deterministic legs — compile / triviality / structural — still run below, so
                # this can never admit a weaker/different statement; same soundness argument as confirms()).
                if _fstore.confirms(_nl, _s):
                    return True
                _r = (_ref or "").strip()
                if _r:
                    try:
                        from ztare.leanmill.solver.proof_cache import normalize_statement as _nst
                        return _nst(_s) == _nst(_r)
                    except Exception:  # noqa: BLE001 — normalizer optional; fall back to a strict compare
                        return _s.strip() == _r
                return False
        except Exception:  # noqa: BLE001 — the store is advisory; never break the firewall
            _fstore = None
            _prior_confirmed_fn = None

    # SUFFICIENT-STATISTIC REUSE (2026-07-04, the cache-churn once-and-for-all — Neyman-Fisher transport surfaced by
    # research_isomorphism + the operator "the caches never hit because the formalizer re-samples the statement").
    # Every reuse cache (proof_cache, decomposition_cache, rung_adjacency, staged) keys on the canonical hash of the
    # formal OUTPUT, but the formalizer is STOCHASTIC — it renders the same fixed NL into a structurally-variant
    # statement each run, so the key churns and every content-cache misses; stacking more output-keyed caches
    # compounds NOTHING because they all inherit the one churning key (why reuse stays flat as caches are added). The
    # store already holds the KERNEL-CONFIRMED agreed statement for a re-seen NL (`reference()`), but production used
    # only its coarse FINGERPRINT (to accept a restyle) and RE-SAMPLED the statement anyway — so the churned rendering
    # is what got banked/cached. Cure = the sufficient statistic: pin on the stable INTENT (NL→its confirmed
    # statement), not the noisy sample. When a confirmed non-refuted reference exists, REUSE ITS STATEMENT VERBATIM as
    # the first rendering → byte-identical across runs → canonical hash stable → decomp-cache hits → proof-cache hits
    # (one domino, all caches cascade). SOUND, not laundering: the full firewall (compile / round-trip / structural /
    # triviality) still re-gates the reused statement below, and `reference()` already EXCLUDES any rendering the
    # no-good ledger marked kernel-FALSE (a strengthened reformalization is never blocked). If the reused statement
    # now FAILS the firewall (substrate/env drift), the refine loop falls back to the real formalizer (stateful: first
    # call reuses, later calls re-sample) — never a reuse-loop. Frugal: skips the formalizer LLM dispatch on the
    # re-seen NL. ZTARE_LEANMILL_REFERENCE_REUSE_STATEMENT=0 reverts to always-re-sample (A/B).
    # REUSE-VERBATIM only on an EXACT NL match (2026-07-06, gale capstone — operator "we implemented cache
    # invalidation already, why is it not working?"). A SEMANTIC reference (`reference()` fell back to the embedding
    # when the exact key MISSED) means the NL was EDITED — adding a hypothesis (list-completeness) reads as a ~90%
    # rephrase, so reusing its OLD statement verbatim SKIPS the very re-formalization the edit intended → the edit is
    # silently ignored (4 NL fixes did nothing). Exact-only reuse ⇒ a changed NL always re-formalizes; the semantic
    # match still feeds the weakening-guard above. `_ref_exact` is NameError-safe (only set when the store ran).
    _reuse_stmt = (_ref_stmt or "").strip() if locals().get("_ref_exact") else ""
    if _reuse_stmt and os.environ.get("ZTARE_LEANMILL_REFERENCE_REUSE_STATEMENT", "1") != "0":
        _orig_ff = formalize_fn
        _reuse_state = {"used": False}
        def formalize_fn(_nl, _stmt=_reuse_stmt, _orig=_orig_ff, _st=_reuse_state):  # noqa: E306
            if not _st["used"]:
                _st["used"] = True
                return _stmt           # FIRST: the kernel-confirmed rendering (byte-stable ⇒ downstream caches hit)
            return _orig(_nl)          # REFINE: reused one failed the firewall (env drift) ⇒ re-sample, no loop
        print("[reference-reuse] NL re-seen → reusing the kernel-CONFIRMED statement verbatim "
              "(skip re-formalize; stable hash ⇒ caches hit; firewall still re-gates)", flush=True)

    af, refine_trace = autoformalize_refine(
        nl, formalize_fn=formalize_fn, compile_fn=compile_fn, triviality_fn=triviality_fn,
        backtranslate_fn=backtranslate_fn, judge_fn=judge_fn, structural_fn=structural_fn,
        compile_diagnose_fn=compile_diagnose_fn,   # feed the ACTUAL Lean error into the compile-fix refine (not blind)
        prior_confirmed_fn=_prior_confirmed_fn,
        reference_statement=_ref_stmt,   # GUIDED weakening-repair: show the confirmed-faithful rendering to restore
        max_refines=max_refines,
        strengthening_mode=_strengthening_mode)   # reformulation re-entry ⇒ a round-trip mismatch is EXPECTED (don't fight the strengthening)
    # #88 MULTISTEP ESCALATION: a oneshot formalization the firewall REJECTS may still be faithfully
    # formalizable with more deliberation — MEASURED 2026-06-10: the hard partial-fraction-existence lemma went
    # rejected(oneshot) → admitted+faithful(multistep, real Mathlib `RatFunc` objects, no def-shell). Retry the
    # REJECTED case ONCE with `default_formalize_multistep` (define_then_state). The escalated statement flows
    # through the SAME downstream gates (def-shell + def-faithfulness below), so it cannot launder. DEFAULT-ON
    # (2026-06-20, operator: it's the MEASURED recovery for exactly the partial-fraction lemma class that the
    # p1 campaign dead-ended on; it only fires on a REJECTED oneshot, so the ~7-dispatch cost is bounded to the
    # hard lemmas, not every lemma — sound: re-passes the SAME firewall, never launders). `=0` reverts (A/B).
    from ztare.leanmill.solver.agentic_leaf import (
        BUDGET_EXHAUSTED_DISPATCH as _BUDGET_STOP,
        INADMISSIBLE_DISPATCH as _INADM,
    )
    if (not af.is_target and af.verdict.reason not in {"INADMISSIBLE_PROVIDER_DEAD", "BUDGET_EXHAUSTED"}
            and af.lean_statement not in {_INADM, _BUDGET_STOP}
            and os.environ.get("ZTARE_LEANMILL_MULTISTEP_ESCALATE", "1") != "0"):
        try:
            _af2, _tr2 = autoformalize_refine(
                nl, formalize_fn=lambda _nl: default_formalize_multistep(_nl, context=_fctx, lean_root=sandbox),
                compile_fn=compile_fn, triviality_fn=triviality_fn, backtranslate_fn=backtranslate_fn,
                judge_fn=judge_fn, structural_fn=structural_fn, max_refines=0)
            if _af2.is_target:
                af, refine_trace = _af2, (refine_trace or []) + ["multistep_escalation"] + (_tr2 or [])
        except Exception:  # noqa: BLE001 — escalation is best-effort; the oneshot rejection stands on failure
            pass
    # `faithful` reports `is_target` (= accepted AND a non-empty statement), NOT raw `verdict.accepted`: a flaky/empty
    # extraction (or a dead dispatch) can leave accepted=True with an EMPTY statement — an empty Lean file compiles and
    # has no false theorem to back-translate — which then read as `faithful=True outcome=rejected_by_firewall`, an
    # inconsistent record that hid the reason (the lemma log only prints `reason=` when faithful is not True) and
    # polluted the faithful-rate. is_target is the honest "was an admitted faithful TARGET produced" signal. (2026-06-24)
    out = {"nl": nl, "lean_statement": af.lean_statement, "faithful": af.is_target,
           "faithfulness_reason": af.verdict.reason, "faithfulness_checks": af.verdict.checks,
           "refine_trace": refine_trace, "refine_rounds": max(0, len(refine_trace) - 1), "solved": None}
    from ztare.leanmill.solver.agentic_leaf import (
        BUDGET_EXHAUSTED_DISPATCH as _BUDGET_STOP,
        INADMISSIBLE_DISPATCH as _INADM,
    )
    if af.lean_statement == _INADM or af.verdict.reason == "INADMISSIBLE_PROVIDER_DEAD":  # every provider dead ⇒
        out["outcome"] = "inadmissible_provider_dead"      # NOT a faithful=False negative. Deposit nothing,
        out["faithful"] = None; out["lean_statement"] = ""  # exclude from the faithful-rate denominator.
        return out
    if af.lean_statement == _BUDGET_STOP or af.verdict.reason == "BUDGET_EXHAUSTED":
        out["outcome"] = "budget_exhausted"
        out["faithful"] = None; out["lean_statement"] = ""
        return out
    # Resolve the re-entry budget ONCE here (was resolved only at the post-solve reformulation site below) so the
    # firewall-REJECT recovery path shares it. A re-entry both literal-first-recovers a strengthened reject AND
    # carries the post-solve reformulation; both must see the same bound.
    if reformulate_budget is None:
        reformulate_budget = (int(os.environ.get("ZTARE_LEANMILL_REFORMULATE_ROUNDS", "1") or "1")
                              if os.environ.get("ZTARE_LEANMILL_REFORMULATE", "1") != "0" else 0)
    if not af.is_target:
        out["outcome"] = "rejected_by_firewall"          # the firewall did its job — no unsound solve
        # #85: a CROSS-VOTE disagreement is a cross-substrate MISTRANSLATION — record it as a faithfulness
        # CONFLICT memo so the formalizer recalls the trap on a re-seen NL (prompt_block). This is what makes
        # the cross-substrate "alien" consensus LOAD-BEARING (it compounds into learned memos) instead of pure
        # advisory telemetry. Best-effort + gated by the store (default-off) ⇒ parity; can never admit anything.
        if _fstore is not None and af.verdict.checks.get("cross_vote_consensus") is False:
            try:
                _fstore.record_conflict(nl, ["lean", "cross_vote"], af.verdict.reason, source="firewall_crossvote")
            except Exception:  # noqa: BLE001
                pass
        # LITERAL-FIRST RECOVERY (2026-06-23) — the integration wire that turns this DEAD-END reject into the honest
        # truth-first loop. ROOT CAUSE (not iatrogenic harness; a sequencing gap): the agent — primed by a substrate
        # that already holds the corrected theorem — formalized the STRENGTHENED claim directly, so the firewall
        # rejected it as round-trip-weakened and, with NO ¬G license minted, the disclosed-strengthening override had
        # nothing to act on; the reject returned BEFORE the reformulation re-entry below could ever run. Fix: re-enter
        # THIS SAME function ONCE, literal-first — render the LITERAL claim (the firewall ADMITS it iff it matches the
        # NL), solve it (the agent elects FALSIFY ⇒ kernel ¬G ⇒ `statement_false` recorded + literal deposited), and
        # the EXISTING reformulation re-entry then re-strengthens through the override. NOT a new surface: it reuses
        # this function, the firewall, the kernel falsifier, the ONE ledger, and the override. NON-GAMABLE: the license
        # is kernel-EARNED — a "literal" rendering that is itself a strengthening just fails the firewall again ⇒ no
        # license ⇒ the original reject stands. STRICTLY ADDITIVE: only a recovered FAITHFUL CLOSURE is returned, else
        # the original rejection is kept. Bounded to ONE attempt (`_literal_first_done`);
        # ZTARE_LEANMILL_LITERAL_FIRST_RECOVERY=0 reverts to the dead-end (byte-parity).
        if (not _literal_first_done and reformulate_budget > 0
                and os.environ.get("ZTARE_LEANMILL_LITERAL_FIRST_RECOVERY", "1") != "0"
                and _needs_literal_first_recovery(nl, af)):
            try:
                from ztare.leanmill.solver import prompts as _lp
                _lf = autoformalize_and_solve(
                    nl, sandbox=sandbox, substrate=substrate, formalize_fn=_caller_formalize_fn,
                    compile_fn=compile_fn, triviality_fn=triviality_fn, backtranslate_fn=backtranslate_fn,
                    judge_fn=judge_fn, structural_fn=_caller_structural_fn, solve_fn=solve_fn, timeout_s=timeout_s,
                    max_refines=max_refines, def_faithfulness=def_faithfulness, notes=notes,
                    extra_context=extra_context + _lp.LITERAL_FIRST_CUE,
                    reformulate_budget=reformulate_budget, _literal_first_done=True)
            except Exception:  # noqa: BLE001 — recovery is best-effort; the original rejection stands on failure
                _lf = None
            if isinstance(_lf, dict) and _lf.get("faithful") and _lf.get("solved") == "closed":
                _lf["literal_first_recovery_from"] = af.lean_statement
                return _lf
        return out
    # DEF-FAITHFULNESS GATE (#23): for define_then_state output, a degenerate-constant def-shell
    # (`def Genus := 0`) makes the theorem typecheck vacuously while the statement round-trip passes
    # (it back-translates the THEOREM, not the def body). If the formalization DEFINES objects and any
    # is an unambiguous shell, REJECT before solving — no auto-solve of a def-shell. (Deterministic
    # layer; the cold-judge-per-def is the remaining LLM layer.)
    _shells = detect_def_shells(af.lean_statement)
    if _shells:
        out["def_shells"] = _shells
        out["faithfulness_reason"] = f"def-shell(s) detected — unfaithful definition(s): {_shells}"
        out["outcome"] = "rejected_by_firewall"
        return out
    # LLM-per-def layer (opt-in #23, def_faithfulness=True): catches a NON-constant UNFAITHFUL def (right
    # shape, wrong object) that the deterministic detect_def_shells misses. Opt-in (per-def LLM cost +
    # biased-to-admit so it never over-rejects a faithful def — rejects only on a clear UNFAITHFUL verdict).
    # confirms() short-circuit (2026-07-03 sweep): if this exact Prop (name-agnostic) was already CONFIRMED
    # faithful for this NL, its defs were part of that confirmation — don't re-litigate them with the
    # non-deterministic per-def LLM judge (the def-level sibling of the round-trip/structural flaky-judge class).
    if def_faithfulness and not (_fstore is not None and _fstore.confirms(nl, af.lean_statement)):
        _dff = default_def_faithfulness(nl, af.lean_statement)
        if _dff["unfaithful"]:
            out["def_unfaithful"] = _dff["unfaithful"]
            out["faithfulness_reason"] = f"unfaithful def(s) (cold per-def judge): {_dff['unfaithful']}"
            out["outcome"] = "rejected_by_firewall"
            return out
    # FAITHFULNESS STORE deposit (#86): the statement passed EVERY firewall leg (round-trip + structural +
    # def-shell + def-faithfulness) ⇒ a CONFIRMED faithful NL→Lean correspondence. Record it (the compounding
    # win the inventory found missing) so a re-seen NL recalls it + the silent-weakening guard gets a reference.
    if _fstore is not None:
        try:
            _fstore.record(nl, af.lean_statement, confirmed=True,
                           fingerprint=statement_fingerprint(af.lean_statement), source="firewall_admit")
        except Exception:  # noqa: BLE001
            pass
    # TYPECLASS-GENERALITY audit (advisory, 2026-06-24): the statement passed NL↔Lean faithfulness, but that is
    # BLIND to instance-class generality (a stronger instance ⇒ a narrower theorem; identical fingerprint). Surface
    # a suspected silent narrowing against the BROADEST available intent — the blueprint/`notes` if present, else
    # the NL — for a scope-fidelity cross-check. NEVER gates (a narrower theorem is still true; the kernel governs).
    try:
        _gen = typeclass_generality_audit((notes or "").strip() or nl, af.lean_statement)
        if _gen.get("flags"):
            out["generality_audit"] = _gen
            for _gf in _gen["flags"]:
                print(f"[firewall] ⚠ generality: {_gf['note']}", flush=True)
    except Exception:  # noqa: BLE001 — advisory; never break the admit
        pass
    # ADDED-HYPOTHESIS ambition audit (advisory, 2026-07-02): the explicit-binder face of the same gap — an added
    # hypothesis (uniqueness, extra positivity, comparability) narrows the claim while the conclusion round-trips
    # identically. Same broadest-intent input, same never-gates discipline.
    try:
        _amb = added_hypothesis_audit((notes or "").strip() or nl, af.lean_statement)
        if _amb.get("flags"):
            out["ambition_audit"] = _amb
            for _af_ in _amb["flags"]:
                print(f"[firewall] ⚠ ambition: {_af_['note']}", flush=True)
    except Exception:  # noqa: BLE001 — advisory; never break the admit
        pass
    # Target the LAST theorem|lemma (the stated target — in define_then_state the main claim follows
    # the helper defs/lemmas; the old FIRST-`theorem`-only regex mis-pointed the solver at a helper and
    # missed `lemma`-only bodies → misreported `admitted_and_closed` on a trivial helper). Review fix 2026-06-05.
    from ztare.leanmill.lean_source import theorem_names as _thm_names   # canonical, line-anchored
    _names = _thm_names(af.lean_statement)
    name = _names[-1] if _names else "autoform_target"
    sv = solve_fn(name, af.lean_statement)
    r0 = (sv.get("results") or [{}])[0] if isinstance(sv, dict) else {}
    out["solved"] = r0.get("outcome")
    # Preserve the solver's apparatus-vs-math classification at the firewall boundary.  Without these fields,
    # downstream notes/Workbench records cannot distinguish a mathematical exact gap from a timeout or budget cut.
    out["failure_class"] = r0.get("failure_class")
    out["budget_killed"] = r0.get("budget_killed", False)
    out["governance"] = sv.get("governance") if isinstance(sv, dict) else None
    out["closure_certificate"] = sv.get("closure_certificate") if isinstance(sv, dict) else None
    # #81: surface the PLANNER's actual decomposition (route_and_solve's {lemmas, chain, lnames}) so the notes
    # write-back persists the SAME agent's mid-proof sub-DAG, not a fresh post-hoc re-proposal.
    out["decomposition"] = _planner_subdag(sv)   # the nested {lemmas,chain,lnames}, NOT the iso_route wrapper
    out["outcome"] = f"admitted_and_{r0.get('outcome')}"

    # REFORMULATION RE-ENTRY (the agent owns formalize↔prove↔reformulate; the harness re-opens the independent
    # faithfulness gate). The solver REFUTED this formalization (kernel ¬G or a leaf statement_false flag) — a
    # falsity the STATIC firewall could not see (a false statement compiles + looks faithful; only PROVING reveals
    # it). Re-open the SAME firewall on the SAME nl with the refutation as formalizer context (warm RESUME → the
    # agent continues), bounded. SOUND: the reformulation re-passes the firewall vs the original nl; the refuted
    # original is surfaced (`refutation`/`reformulated_from`), never credited as a closure.
    if reformulate_budget is None:
        reformulate_budget = (int(os.environ.get("ZTARE_LEANMILL_REFORMULATE_ROUNDS", "1") or "1")
                              if os.environ.get("ZTARE_LEANMILL_REFORMULATE", "1") != "0" else 0)   # DEFAULT-ON 2026-06-12 (sound: re-entry re-passes the SAME firewall; =0 reverts)
    _refutation = _solve_refutation(sv)
    _refutation_confirmed_for_memory = bool(_refutation)
    if not _refutation and reformulate_budget and reformulate_budget > 0 and r0.get("outcome") != "closed" \
            and os.environ.get("ZTARE_LEANMILL_SOFT_REFUTATION_REFORMULATE", "1") != "0":
        # SOFT-REFUTATION reformulation (2026-07-06, gale capstone — operator "make the fix GENERAL for other cases /
        # if you see it why can't leanmill"). THE general false-as-stated recovery. The leaf REFUTED the statement
        # (a `-- STATEMENT-FALSE:` marker or a proven `_counterexample`/`_statement_false` decl) but the KERNEL ¬G
        # confirmation FAILED — because the leaf's counterexample uses a DIVERGENT carrier (a `PUnit` / redefined-
        # `proposalStep` GHOST the divergence guard correctly rejects) even though the STATEMENT is genuinely false
        # (a faithful counterexample exists). Requiring a kernel-confirmed ¬G (the v7 anti-bogus gate) then blocks the
        # reformulation FOREVER and the campaign GRINDS a false statement (the gale capstone: 5 runs). Firing on the
        # SOFT signal is SOUND: the re-entry STRENGTHENS the statement and the FIREWALL RE-GATES it vs the ORIGINAL nl
        # — a bogus refutation of a TRUE lemma yields an over-strong statement the faithfulness gate REJECTS (falls
        # back to the original, nothing closed), a genuine false-as-stated yields the corrected FAITHFUL theorem. The
        # KERNEL stays the boundary (it re-proves the strengthened statement); the soft signal only lets the recovery
        # REACH the reformulation, it never closes anything. This is the channel from "leanmill SEES it's false"
        # (falsify/refute) to "so ADD the hypothesis that rules the counterexample out" (strengthening re-formalize).
        try:
            from ztare.leanmill.solver.agentic_leaf import scan_probes_for_statement_false as _scan_sf, probe_dir as _pd_sf
            _soft = _scan_sf(_pd_sf(sandbox))
            if _soft:
                print(f"[reformulate] SOFT refutation (leaf refuted; kernel ¬G NOT confirmed — divergent-carrier "
                      f"ghost) → STRENGTHENING re-entry, firewall re-gates vs original NL: {str(_soft)[:110]}", flush=True)
                _refutation = _soft
                _refutation_confirmed_for_memory = False
        except Exception:  # noqa: BLE001 — best-effort; no soft signal ⇒ no reformulation (prior behaviour, byte-parity)
            pass
    if _refutation:
        # SINGLE COORDINATION POINT (2026-06-23, operator: "a single entry point for false-statement
        # reformalization so everyone is up to date" + "no parallel surfaces"). `_refutation` has two authority
        # levels: kernel-confirmed (from `_solve_refutation`) or soft reformulation feedback (from a leaf marker
        # whose ¬G did not pass the gate). Both may guide a governed re-entry that re-passes the firewall; only the
        # kernel-confirmed path may enter cross-run `NoGoodStore` memory as `statement_false`. That keeps the
        # faithfulness `reference()` filter tied to confirmed refutations, not useful-but-unverified hints.
        _record_statement_false_no_good(
            af.lean_statement, _refutation,
            confirmed=_refutation_confirmed_for_memory,
            source="reformulation_refutation")
    if _refutation and reformulate_budget > 0 and r0.get("outcome") != "closed":
        # ROUTE THE AGENT'S OWN CORRECTION: the consolidation pass often already PROVED the corrected (strong)
        # theorem; surface those proven substrate results so the fresh re-formalizer ADOPTS + CITES one instead of
        # re-deriving a weak version from the prose (the binding gap — operator: "the agent proposed a
        # reformulation, why isn't that the path?"). The proofs live in the registered substrate `.lean` FILE (the
        # notes only NAME it); `_read_substrate_src` is the ONE reader the formalize-context vocabulary injection also
        # uses, so the shelf is non-empty even when consolidation already moved the proofs there (the 2026-06-23
        # convergence gap). Domain-agnostic; the kernel re-verifies every citation.
        _proven_shelf = _substrate_proven_shelf(_read_substrate_src(notes, sandbox))
        re_out = autoformalize_and_solve(
            nl, sandbox=sandbox, substrate=substrate, formalize_fn=_caller_formalize_fn,
            compile_fn=compile_fn, triviality_fn=triviality_fn, backtranslate_fn=backtranslate_fn,
            judge_fn=judge_fn, structural_fn=structural_fn, solve_fn=solve_fn, timeout_s=timeout_s,
            max_refines=max_refines, def_faithfulness=def_faithfulness, notes=notes,
            extra_context=extra_context + _reformulate_feedback(af.lean_statement, _refutation, _proven_shelf),
            reformulate_budget=reformulate_budget - 1,
            _strengthening_mode=True)   # the literal was kernel-refuted ⇒ a round-trip mismatch on the correction is EXPECTED
        re_out["reformulated_from"] = af.lean_statement
        re_out["prior_refutation"] = _refutation
        re_out["reformulate_trace"] = (out.get("reformulate_trace") or []) + [
            {"refuted_statement": af.lean_statement, "refutation": _refutation, "refuted_outcome": r0.get("outcome")}]
        return re_out
    if _refutation:
        out["refutation"] = _refutation   # terminal honest non-closure (no budget left / could not reformulate)
    return out


def _self_test() -> int:
    fails = []
    # HERMETIC: multistep escalation (now DEFAULT-ON, 2026-06-20) dispatches the REAL `default_formalize_multistep`
    # agent on a firewall reject — a live, non-hermetic path. The mock-injected suite below uses permissive
    # compile/triviality/structural fns, so the escalation would admit a mock and flip the reject-path tests.
    # Force it OFF for the suite (the canonical "default-on live capability must be off in a hermetic test"
    # fix — see the sledgehammer-live lesson). The escalation's own behaviour is validated live, not here.
    os.environ["ZTARE_LEANMILL_MULTISTEP_ESCALATE"] = "0"

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # the planner sub-DAG capture seam (the self-evolving-loop amnesia bug): surface iso_route['decomposition']
    # ({lemmas,chain,lnames}), NOT the iso_route wrapper, so compound/refined-notes find the lemmas.
    _iso = {"iso_route": {"routed": True, "decomposition": {"lemmas": ["theorem L1 : P := by sorry"],
            "chain": "c", "lnames": ["L1"]}, "solution": {"parent_closed": True}}}
    ok("planner_subdag: extracts NESTED decomposition lemmas (not the iso_route wrapper)",
       (_planner_subdag(_iso) or {}).get("lemmas") == ["theorem L1 : P := by sorry"])
    ok("planner_subdag: no iso_route ⇒ None (fail-safe, compound no-ops)", _planner_subdag({"outcome": "x"}) is None)
    ok("planner_subdag: non-dict ⇒ None", _planner_subdag(None) is None)

    # DEF-SHELL gate (anti-decoy) — must FLAG bare-constant shells AND must NOT flag real predicates/expressions.
    # RCA 2026-06-24 (the AMM stall): a first-token match flagged `0 < x ∧ 0 < y` as a "shell", silently rejecting
    # every lemma over a simple well-formedness predicate. A reject-gate MUST be tested on the GOOD inputs it has to
    # PASS, not only the bad ones it catches — this dual corpus is that anti-regression battery.
    _shell = lambda d: bool(detect_def_shells(d))
    ok("def-shell: `:= 0` flagged", _shell("def Genus := 0"))
    ok("def-shell: `:= True` flagged", _shell("abbrev X := True"))
    ok("def-shell: `fun _ => 0` flagged", _shell("def f (n : Nat) := fun _ => 0"))
    ok("def-shell: `:= sorry` flagged", _shell("def g := sorry"))
    ok("def-shell: predicate `0 < a ∧ 0 < b` NOT flagged (the AMM PoolWellFormed false-reject)",
       not _shell("def PoolWellFormed (p : Pool) : Prop := 0 < p.reserveX ∧ 0 < p.reserveY"))
    ok("def-shell: predicate `0 ≤ x` NOT flagged", not _shell("def NonNeg (x : NNReal) : Prop := 0 ≤ x"))
    ok("def-shell: expression `1 + n` NOT flagged", not _shell("def succ (n : Nat) := 1 + n"))
    ok("def-shell: predicate `True ∧ p` NOT flagged", not _shell("def P (p : Prop) : Prop := True ∧ p"))

    NL = "For Hermitian matrices A, B, if B - A is positive semidefinite then each sorted eigenvalue of A is ≤ that of B."
    GOOD = "theorem t {A B : Matrix n n ℝ} (hA : A.IsHermitian) (hB : B.IsHermitian) (h : (B-A).PosSemidef) (i) : hA.ev i ≤ hB.ev i := by sorry"

    # default-ish mock apparatus: GOOD compiles, is non-trivial, round-trips faithfully.
    compiles = lambda s: "PosSemidef" in s or "ev i" in s          # GOOD typechecks; junk doesn't
    not_trivial = lambda s: "True" in s or "0 = 0" in s             # trivial iff it's a tautology
    backtr = lambda s: NL if ("PosSemidef" in s and "ev i" in s) else "some unrelated statement about primes"
    judge = lambda orig, back: back == NL                          # faithful iff back-translation == NL

    # ACCEPT the faithful one
    v = faithfulness_gate(NL, GOOD, compile_fn=compiles, triviality_fn=not_trivial,
                          backtranslate_fn=backtr, judge_fn=judge)
    ok("accepts_faithful", v.accepted and all(v.checks.values()))

    # REJECT: does not compile (malformed)
    v_bad = faithfulness_gate(NL, "theorem t : @@junk := by sorry", compile_fn=compiles,
                              triviality_fn=not_trivial, backtranslate_fn=backtr, judge_fn=judge)
    ok("rejects_non_compiling", not v_bad.accepted and v_bad.checks.get("compiles") is False)

    # REJECT: trivially true (`theorem t : True`)
    v_triv = faithfulness_gate(NL, "theorem t : True := by sorry",
                               compile_fn=lambda s: True, triviality_fn=lambda s: "True" in s,
                               backtranslate_fn=backtr, judge_fn=judge)
    ok("rejects_trivial", not v_triv.accepted and v_triv.checks.get("non_trivial") is False)

    # REJECT: unfaithful — compiles + non-trivial but the round-trip says it's a DIFFERENT problem
    UNFAITHFUL = "theorem t (p : ℕ) (hp : p.Prime) : p ≥ 2 := by sorry"
    v_unf = faithfulness_gate(NL, UNFAITHFUL, compile_fn=lambda s: True, triviality_fn=lambda s: False,
                              backtranslate_fn=lambda s: "a statement about primes being ≥ 2", judge_fn=judge)
    ok("rejects_unfaithful_round_trip",
       not v_unf.accepted and v_unf.checks.get("round_trip_faithful") is False)

    # FAIL-CLOSED: judge errors ⇒ NOT admitted (cost of false-accept is a fabricated success)
    def judge_raises(o, b):
        raise RuntimeError("judge unavailable")
    v_err = faithfulness_gate(NL, GOOD, compile_fn=lambda s: True, triviality_fn=lambda s: False,
                              backtranslate_fn=backtr, judge_fn=judge_raises)
    ok("fail_closed_on_judge_error", not v_err.accepted)

    # --- ADVERSARIAL regressions (adversarial review 2026-06-04): these FAILED before the fixes ---
    base = dict(compile_fn=lambda s: True, triviality_fn=lambda s: False, backtranslate_fn=backtr)
    # HIGH-1: a judge returning a REJECTION STRING / nonzero int must NOT coerce to accept
    ok("rejects_judge_string_verdict",
       not faithfulness_gate(NL, GOOD, judge_fn=lambda o, b: "NO these differ", **base).accepted)
    ok("rejects_judge_nonzero_int",
       not faithfulness_gate(NL, GOOD, judge_fn=lambda o, b: 2, **base).accepted)
    # HIGH-1: a compile_fn returning an error STRING must NOT read as 'typechecks'
    ok("rejects_compile_error_string",
       not faithfulness_gate(NL, GOOD, compile_fn=lambda s: "error: 1 goal", triviality_fn=lambda s: False,
                             backtranslate_fn=backtr, judge_fn=judge).accepted)
    # HIGH-2: triviality_fn RAISING must FAIL-CLOSED (was the lone fail-open leg)
    def triv_raises(s):
        raise RuntimeError("lean repl crashed")
    ok("fail_closed_on_triviality_error",
       not faithfulness_gate(NL, "theorem t : True := by sorry", compile_fn=lambda s: True,
                             triviality_fn=triv_raises, backtranslate_fn=backtr, judge_fn=judge).accepted)
    # MEDIUM-1: a zero-width-only back-translation must NOT pass the non-empty guard
    ok("rejects_zero_width_backtranslation",
       not faithfulness_gate(NL, GOOD, compile_fn=lambda s: True, triviality_fn=lambda s: False,
                             backtranslate_fn=lambda s: "​⁠", judge_fn=lambda o, b: True).accepted)
    # HIGH-3: contradictory-hypothesis VACUITY ⇒ rejected when a consistency_fn is supplied
    ok("rejects_vacuous_contradictory_hyps",
       not faithfulness_gate(NL, GOOD, judge_fn=judge, consistency_fn=lambda s: False, **base).accepted)
    ok("accepts_when_consistency_passes",
       faithfulness_gate(NL, GOOD, judge_fn=judge, consistency_fn=lambda s: True, **base).accepted)
    # HIGH-4: the STRUCTURAL carrier (iso+lossless) OVERRIDES a charitable judge — a weakened/dropped-
    # hypothesis formalization is rejected even when the round-trip judge would wave it through.
    ok("structural_carrier_rejects_weakening",
       not faithfulness_gate(NL, GOOD, judge_fn=lambda o, b: True, structural_fn=lambda nl, s: False, **base).accepted)
    ok("structural_carrier_fail_closed_on_error",
       not faithfulness_gate(NL, GOOD, judge_fn=judge, structural_fn=lambda nl, s: (_ for _ in ()).throw(RuntimeError("x")), **base).accepted)
    ok("structural_carrier_pass_then_judge",
       faithfulness_gate(NL, GOOD, judge_fn=judge, structural_fn=lambda nl, s: True, **base).accepted)

    # end-to-end: a formalizer that emits the faithful statement → is_target; one that emits junk → not
    r_good = autoformalize(NL, formalize_fn=lambda nl: GOOD, compile_fn=compiles, triviality_fn=not_trivial,
                           backtranslate_fn=backtr, judge_fn=judge)
    ok("e2e_faithful_is_target", r_good.is_target)
    r_junk = autoformalize(NL, formalize_fn=lambda nl: "theorem t : True := by sorry",
                           compile_fn=lambda s: True, triviality_fn=lambda s: "True" in s,
                           backtranslate_fn=backtr, judge_fn=judge)
    ok("e2e_trivial_not_target", not r_junk.is_target)

    # --- typeclass-GENERALITY audit (neurosymbolic: symbolic binder extraction + injected LLM judge; hermetic) ---
    _LIN = "theorem t {ι : Type*} [Fintype ι] [LinearOrder ι] (c : ι → Nat) : True := by trivial"
    ok("generality: symbolic instance extraction", _instance_classes(_LIN) == ["Fintype", "LinearOrder"])
    ok("generality: judge NARROWER ⇒ advisory flag (no registry/keywords)",
       bool(typeclass_generality_audit("a partial order; pari-passu allowed", _LIN,
                                        judge_fn=lambda _p: "NARROWER: [LinearOrder] too strong")["flags"]))
    ok("generality: judge FAITHFUL ⇒ no flag",
       not typeclass_generality_audit("a linear order", _LIN, judge_fn=lambda _p: "FAITHFUL")["flags"])
    _calls = []
    ok("generality: NO instance binders ⇒ symbolic gate skips the LLM (no call)",
       not typeclass_generality_audit("any naturals", "theorem t (n:Nat): n=n := rfl",
                                       judge_fn=lambda _p: _calls.append(1) or "NARROWER")["flags"] and not _calls)
    ok("generality: dead judge ⇒ graceful-degrade empty (no keyword fallback)",
       not typeclass_generality_audit("a partial order", _LIN, judge_fn=lambda _p: "")["flags"])

    # --- ADDED-HYPOTHESIS ambition audit (the explicit-binder sibling; same hermetic discipline) ---
    _UNIQ = ("theorem t {X : Type*} [Preorder X] (g : X → ℝ) (x : X) "
             "(huniq : ∀ y : X, IsGreatest (Set.range g) (g y) → y = x) : True := by trivial")
    ok("ambition: symbolic hypothesis extraction (Prop binder in, data binder out)",
       any("huniq" in h for h in _explicit_hypotheses(_UNIQ)) and
       not any(h.startswith("g :") for h in _explicit_hypotheses(_UNIQ)))
    ok("ambition: judge ADDED ⇒ advisory flag",
       bool(added_hypothesis_audit("the set of maximizers rises with the parameter (optima not assumed unique)",
                                   _UNIQ, judge_fn=lambda _p: "ADDED: uniqueness of the maximizer")["flags"]))
    ok("ambition: judge LICENSED ⇒ no flag",
       not added_hypothesis_audit("assuming the maximizer is unique", _UNIQ,
                                  judge_fn=lambda _p: "LICENSED")["flags"])
    _acalls = []
    ok("ambition: NO propositional binders ⇒ symbolic gate skips the LLM (no call)",
       not added_hypothesis_audit("any function", "theorem t {X : Type*} (f : X → ℝ) : True := by trivial",
                                  judge_fn=lambda _p: _acalls.append(1) or "ADDED")["flags"] and not _acalls)
    ok("ambition: dead judge ⇒ graceful-degrade empty",
       not added_hypothesis_audit("anything", _UNIQ, judge_fn=lambda _p: "")["flags"])

    # --- REAL structural carrier (the new deterministic NL↔Lean diff) — calibration, not just mocks ---
    GOODFP = reference_fingerprint(GOOD)
    ok("structural_parses_two_hyps", _parse_lean_statement(GOOD)["n_explicit_binders"] >= 1)
    ok("structural_conclusion_op_le", _parse_lean_statement(GOOD)["conclusion_op"] == "≤")
    # faithful candidate matches its own reference fingerprint
    ok("structural_accepts_reference", structural_faithfulness(NL, GOOD, expected=GOODFP))
    # DROPPED hypothesis: same conclusion, one fewer hypothesis binder ⇒ structure NOT preserved
    DROPPED = "theorem t {A B : Matrix n n ℝ} (hA : A.IsHermitian) (h : (B-A).PosSemidef) (i) : hA.ev i ≤ hB.ev i := by sorry"
    ok("structural_rejects_dropped_hyp",
       not structural_faithfulness(NL, DROPPED, expected={"n_explicit_binders": GOODFP["n_explicit_binders"]}))
    # RELAXED conclusion: ≤ silently weakened to < (over/under-claim) ⇒ NOT preserved
    RELAXED = GOOD.replace("≤", "<")
    ok("structural_rejects_relaxed_conclusion",
       not structural_faithfulness(NL, RELAXED, expected={"conclusion_op": "≤"}))
    # QUANTIFIER swap: a ∀ intent rendered with ∃ ⇒ NOT preserved
    ok("structural_rejects_quantifier_swap",
       not structural_faithfulness(NL, "theorem t : ∃ i, P i := by sorry",
                                   expected={"has_forall": False, "has_exists": False}))
    # top-level connective dominates a buried comparator (no false op match)
    ok("structural_top_level_arrow",
       _parse_lean_statement("theorem t (n:ℕ) : (a < b) → c = d := by sorry")["conclusion_op"] == "→")
    # absent reference ⇒ advisory-True (round-trip judge is then the defense), never a false reject
    ok("structural_advisory_when_no_reference", structural_faithfulness(NL, GOOD, expected=None))

    # --- INSTANCE BATTERY leg (ground-truth binding) — mock the kernel decide-probe with a python oracle.
    # NL policy: "permit iff role=admin AND resource=secret." Labelled battery + a BROADENED (∧→∨) launder.
    FAITHFUL_DEC = {"admin_secret": True, "user_secret": False, "admin_public": False}
    LAUNDERED_OR = {"admin_secret": True, "user_secret": True, "admin_public": True}  # AND→OR broadening
    BATTERY = [("admin_secret", True), ("user_secret", False), ("admin_public", False)]

    def _mk_probe(decision):  # mock: probe `example : (¬)?(permit <inst>) := by …` compiles iff polarity matches
        def probe(body):
            m = re.search(r"example : (¬ )?\(permit (\w+)\)", body)
            if not m:
                return False
            asserted = not bool(m.group(1))
            return decision.get(m.group(2), False) == asserted
        return probe

    ok("battery_admits_faithful",
       semantic_instance_battery("def permit …", "permit", BATTERY, compile_probe=_mk_probe(FAITHFUL_DEC)))
    ok("battery_rejects_broadening_launder",
       not semantic_instance_battery("def permit …", "permit", BATTERY, compile_probe=_mk_probe(LAUNDERED_OR)))
    ok("battery_skipped_when_no_cases",
       semantic_instance_battery("def permit …", "permit", [], compile_probe=_mk_probe(LAUNDERED_OR)))
    # gate integration: a faithful-everything-else formalization is REJECTED when the battery fails, and
    # ADMITTED when it passes — the new leg gates independently of the consensus round-trip.
    ok("gate_rejects_on_battery_fail",
       not faithfulness_gate(NL, GOOD, judge_fn=lambda o, b: True, battery_fn=lambda s: False, **base).accepted)
    ok("gate_admits_on_battery_pass",
       faithfulness_gate(NL, GOOD, judge_fn=judge, battery_fn=lambda s: True, **base).accepted)
    ok("gate_battery_fail_closed_on_error",
       not faithfulness_gate(NL, GOOD, judge_fn=judge,
                             battery_fn=lambda s: (_ for _ in ()).throw(RuntimeError("repl down")), **base).accepted)

    # --- CROSS-VOTE leg (kernel-grade consensus) — mock crossvote_fn (the live N-formalizer + kernel
    # equivalence is exercised in cross_voting._selftest). The gate must: ADMIT on consensus, REJECT on
    # disagreement, and FAIL-CLOSED on a probe error. Gates independently of every other leg.
    ok("gate_admits_on_crossvote_agree",
       faithfulness_gate(NL, GOOD, judge_fn=judge, crossvote_fn=lambda nl, s: True, **base).accepted)
    ok("gate_rejects_on_crossvote_disagree",
       not faithfulness_gate(NL, GOOD, judge_fn=lambda o, b: True, crossvote_fn=lambda nl, s: False, **base).accepted)
    ok("gate_crossvote_fail_closed_on_error",
       not faithfulness_gate(NL, GOOD, judge_fn=judge,
                             crossvote_fn=lambda nl, s: (_ for _ in ()).throw(RuntimeError("panel down")), **base).accepted)
    ok("gate_crossvote_skipped_when_none",
       faithfulness_gate(NL, GOOD, judge_fn=judge, crossvote_fn=None, **base).accepted)

    # --- REFORMULATION RE-ENTRY (the governed formal↔NL oscillation) — mock the whole pipeline ---
    # The agent's "this formalization is FALSE (found while proving) — here is the corrected one" must:
    # re-open the firewall on the refutation, re-solve the corrected statement, NEVER credit the refuted one,
    # stay firewall-gated (an unfaithful reformulation is REJECTED not closed), and honor the budget. The live
    # agent loop runs on the VPS; here we pin the MECHANICS + the soundness boundary. max_refines=0 ⇒ exactly
    # one formalize call per pass, so the stateful mock (FALSE first, TRUE on re-entry) is deterministic.
    RF_NL = "the intended true statement about X"
    FALSE_STMT, TRUE_STMT = "theorem t : FalseRender := by sorry", "theorem t : TrueRender := by sorry"

    def _mk_formalize():            # FALSE first (refuted during proving), TRUE on the reformulate re-entry
        st = {"n": 0}
        def f(_s):
            st["n"] += 1
            return TRUE_STMT if st["n"] >= 2 else FALSE_STMT
        return f
    _rf_solve = lambda name, stmt: {"results": [{"outcome": "closed" if "TrueRender" in stmt else "falsified",
                                                 "falsifier": "counterexample at x=0"}]}
    _rf_base = dict(sandbox=".", compile_fn=lambda s: True, triviality_fn=lambda s: False,
                    judge_fn=lambda o, b: True, structural_fn=lambda o, s: True, solve_fn=_rf_solve, max_refines=0)
    r_ref = autoformalize_and_solve(RF_NL, formalize_fn=_mk_formalize(), backtranslate_fn=lambda s: RF_NL,
                                    reformulate_budget=1, **_rf_base)
    ok("reformulate_reenters_and_closes",
       r_ref.get("outcome") == "admitted_and_closed" and r_ref.get("reformulated_from") == FALSE_STMT
       and "counterexample" in (r_ref.get("prior_refutation") or ""))
    r_nb = autoformalize_and_solve(RF_NL, formalize_fn=lambda _s: FALSE_STMT, backtranslate_fn=lambda s: RF_NL,
                                   reformulate_budget=0, **_rf_base)
    ok("reformulate_budget0_terminal_noclose",
       r_nb.get("outcome") == "admitted_and_falsified" and bool(r_nb.get("refutation"))
       and not r_nb.get("reformulated_from"))
    # the reformulation is itself UNFAITHFUL (round-trips to a DIFFERENT problem) ⇒ the firewall REJECTS it —
    # the refuted original is NOT laundered into a close (the load-bearing soundness property).
    r_unf = autoformalize_and_solve(RF_NL, formalize_fn=_mk_formalize(), reformulate_budget=1,
                                    backtranslate_fn=lambda s: ("a different problem" if "TrueRender" in s else RF_NL),
                                    judge_fn=lambda o, b: b == RF_NL, sandbox=".", compile_fn=lambda s: True,
                                    triviality_fn=lambda s: False, structural_fn=lambda o, s: True,
                                    solve_fn=_rf_solve, max_refines=0)
    ok("reformulate_unfaithful_rejected_not_closed",
       r_unf.get("outcome") == "rejected_by_firewall" and r_unf.get("solved") != "closed")
    r_clean = autoformalize_and_solve(RF_NL, formalize_fn=lambda _s: TRUE_STMT, backtranslate_fn=lambda s: RF_NL,
                                      reformulate_budget=1, **_rf_base)
    ok("reformulate_noop_on_clean_close",
       r_clean.get("outcome") == "admitted_and_closed" and not r_clean.get("reformulated_from"))

    # #143 — the STATEMENT-FALSE kernel-gate invariant in _solve_refutation: a HARD kernel ¬G refutes; a SOFT
    # `statement_false` claim refutes ONLY when solve_adhoc CONFIRMED it (statement_false_verified) — an
    # unverified claim with the gate ON is NOT a refutation (the v7 deadlock fix). The =0 opt-out restores the
    # legacy bare-claim behaviour for the A/B baseline. (Pure-function cases; no Lean needed.)
    _gate_prev = os.environ.get("ZTARE_LEANMILL_VERIFY_STATEMENT_FALSE")
    os.environ["ZTARE_LEANMILL_VERIFY_STATEMENT_FALSE"] = "1"
    ok("refutation_hard_falsified", _solve_refutation({"results": [{"outcome": "falsified", "falsifier": "n=2"}]}) == "n=2")
    ok("refutation_soft_unverified_is_NOT_refutation",
       _solve_refutation({"results": [{"outcome": "open"}], "statement_false": "cex p=1"}) == "")
    ok("refutation_soft_verified_is_refutation",
       _solve_refutation({"results": [{"outcome": "open"}], "statement_false": "cex z",
                          "statement_false_verified": True}) == "cex z")
    os.environ["ZTARE_LEANMILL_VERIFY_STATEMENT_FALSE"] = "0"
    ok("refutation_soft_bare_refutes_when_gate_OFF",
       _solve_refutation({"results": [{"outcome": "open"}], "statement_false": "cex"}) == "cex")
    if _gate_prev is None:
        os.environ.pop("ZTARE_LEANMILL_VERIFY_STATEMENT_FALSE", None)
    else:
        os.environ["ZTARE_LEANMILL_VERIFY_STATEMENT_FALSE"] = _gate_prev

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
