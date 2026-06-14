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

from ztare.leanmill.solver import prompts          # canonical prompt home (#49): backtranslate / judge / def-judge templates


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
    fp = _parse_lean_statement(lean_statement)
    if not expected:
        return True
    for key, want in expected.items():
        if key not in fp:
            continue
        if fp[key] != want:
            return False
    return True


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
            return FaithfulnessVerdict(False, f"round-trip errored ⇒ NOT admitted (fail-closed): {repr(e)[:80]}", checks)
    if not checks["round_trip_faithful"]:
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
        lean_statement = (formalize_fn(nl) or "").strip()
    except Exception as e:
        return AutoformalizeResult(nl, "", FaithfulnessVerdict(False, f"formalizer errored: {repr(e)[:80]}"))
    from ztare.leanmill.solver.agentic_leaf import INADMISSIBLE_DISPATCH
    if lean_statement == INADMISSIBLE_DISPATCH:                # #89: every provider dead ⇒ a DEAD INSTRUMENT,
        return AutoformalizeResult(nl, "",                    # not an unfaithful formalization. Skip the gate;
                                   FaithfulnessVerdict(False, "INADMISSIBLE_PROVIDER_DEAD"))  # caller marks inadmissible.
    verdict = faithfulness_gate(nl, lean_statement, compile_fn=compile_fn, triviality_fn=triviality_fn,
                                backtranslate_fn=backtranslate_fn, judge_fn=judge_fn,
                                consistency_fn=consistency_fn, structural_fn=structural_fn,
                                battery_fn=battery_fn, crossvote_fn=crossvote_fn)
    return AutoformalizeResult(nl, lean_statement, verdict)


def _formalize_feedback_hint(verdict: "FaithfulnessVerdict", prior_stmt: str, compile_error: str = "") -> str:
    """Turn the firewall's REJECTION into targeted NL guidance the formalizer can act on — the
    per-leg feedback that makes the refine loop close compile/faithfulness gaps instead of re-rolling.
    `compile_error` (optional, from `default_compile_diagnose`) is the ACTUAL Lean error so a compile-fail
    refine is GUIDED (fix THIS error) not blind (re-guess) — the convergence + burn fix."""
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
    elif checks.get("round_trip_faithful") is False or "round-trip" in reason:
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
                         max_refines: int = 2) -> "tuple[AutoformalizeResult, list]":
    """Autoformalize through the shared RefineHandover loop — the compile-fix the one-shot `autoformalize`
    lacks (a real open-problem target produced a faithful-STRUCTURED but uncompiling formalization that the
    one-shot gate just rejected). On a firewall rejection, hand the formalizer back the verdict's failing leg + its prior
    attempt and re-formalize, bounded. SAME produce→feedback→refine shape as the solver's gap-refine, via
    the SAME driver. The faithfulness gate stays FAIL-CLOSED on every leg (the driver never accepts on a
    rejection). Returns (AutoformalizeResult, trace)."""
    from ztare.common.refine_handover import RefineHandover

    def _gen(ctx):
        try:
            return (formalize_fn((ctx.get("nl") or "") + (ctx.get("hint") or "")) or "").strip()
        except Exception as e:  # noqa: BLE001
            return ""

    def _verify(stmt):
        return faithfulness_gate(nl, stmt, compile_fn=compile_fn, triviality_fn=triviality_fn,
                                 backtranslate_fn=backtranslate_fn, judge_fn=judge_fn,
                                 consistency_fn=consistency_fn, structural_fn=structural_fn,
                                 prior_confirmed_fn=prior_confirmed_fn)

    def _refine_ctx(stmt, verdict, ctx):
        if not (stmt or "").strip():
            return None                      # empty generation ⇒ nothing to repair from ⇒ stop
        cerr = ""
        if compile_diagnose_fn is not None and (getattr(verdict, "checks", {}) or {}).get("compiles") is False:
            try:
                cerr = compile_diagnose_fn(stmt) or ""    # the ACTUAL Lean error ⇒ guided (not blind) repair
            except Exception:  # noqa: BLE001 — advisory; never break the refine on a diagnose failure
                cerr = ""
        return {"nl": nl, "hint": _formalize_feedback_hint(verdict, stmt, cerr)}

    rh = RefineHandover(generate=_gen, verify=_verify, accept_when=lambda v: bool(v.accepted),
                        build_refine_context=_refine_ctx, max_refines=max_refines)
    stmt, verdict, trace = rh.run({"nl": nl, "hint": ""})
    return AutoformalizeResult(nl, stmt, verdict), trace


def reference_fingerprint(lean_statement: str) -> dict:
    """The structural fingerprint to pass as `expected=` — derive it from a TRUSTED formalization (a
    human-checked reference, or the cross-family-agreed candidate). Then `structural_faithfulness`
    flags any later candidate that deviates (dropped hyp / relaxed conclusion / quantifier swap)."""
    return _parse_lean_statement(lean_statement)


def _api_text(prompt: str, *, model: str = "gemini-3.1-pro-preview", label: str, timeout_s: int = 120) -> str:
    """One API completion via the EXISTING `LLMRuntime` (gemini/deepseek allowed; never a metered
    codex/claude call). For the mechanical legs (back-translate, judge) — NOT for formalize."""
    try:
        from ztare.common.llm_runtime import LLMRuntime
    except Exception:
        try:
            from src.ztare.common.llm_runtime import LLMRuntime  # type: ignore
        except Exception:
            return ""
    try:
        resp = LLMRuntime().call_text(prompt, model_id=model, fallback_model_ids=("gemini-2.5-flash",),
                                      max_tokens=2000, request_label=label, timeout_seconds=timeout_s)
        return getattr(resp, "text", "") or ""
    except Exception:
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
    stmts = re.findall(r"(?s)\b((?:theorem|lemma)\s+\S+.*?:=\s*(?:by\s+)?sorry)", clean_nc)
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
        rec = {"ts": datetime.now(timezone.utc).isoformat(), "kind": kind}
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
            from src.ztare.common.llm_runtime import LLMRuntime, MODEL_MAP  # type: ignore
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
        from ztare.formal.lean_check_server import ensure_server, default_socket_path
    except Exception:  # noqa: BLE001
        return ""
    lean_root = Path(lean_root)
    repo = Path(__file__).resolve().parents[4]
    sock = ensure_server(str(lean_root)) or default_socket_path(str(lean_root))
    probe = probe_dir(lean_root) / "FormalizeProbe.lean"
    try:
        probe.write_text("import Mathlib\n\n-- replace with the theorem statement, ending in := by sorry\n", encoding="utf-8")
    except Exception:  # noqa: BLE001
        return ""
    leancheck = f"PYTHONPATH={repo}/src {_sys.executable} -m ztare.formal.lean_check_server --check {sock} {probe}"
    search = f"PYTHONPATH={repo}/src {_sys.executable} -m ztare.leanmill.agent_tools search '<Mathlib name or type pattern>'"
    ctx_block = (f"\n\nSURROUNDING CONTEXT (use ONLY to render faithfully; do NOT formalize the context):\n"
                 f"{context.strip()[:2000]}\n" if (context or "").strip() else "")
    # NOTE: do NOT append render_tool_block here — that surfaces the PROVING tools (witness/abduct/hammer), which
    # are useless for STATING a theorem and would duplicate the inline `search` command. Formalize needs only
    # lean-check + search, both specified in the prompt above.
    prompt = (_FORMALIZE_INTERACTIVE_PROMPT.format(probe_ref=str(probe), leancheck_cmd=leancheck, search_cmd=search)
              + ctx_block + (nl or ""))
    try:
        raw = default_dispatch(prompt, runtime=runtime, repo=repo, timeout=timeout_s) or ""
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
            from src.ztare.leanmill.solver.agentic_leaf import default_dispatch  # type: ignore
        except Exception:
            return ""
    repo = Path(__file__).resolve().parents[4]
    # #88: optional BLUEPRINT CONTEXT so the formalizer can faithfully render a hard research-level lemma it
    # cannot pin down from the prose alone (the P1-RUNG-A run rejected every lemma faithful=False because the
    # formalizer was blind to the surrounding notation/objects). The context INFORMS rendering only — the
    # firewall (round-trip + cross-vote + structural + def-faithfulness) is still the SOLE admit arbiter, so an
    # over-helpful context can never launder an unfaithful statement through.
    ctx_block = ("\n\nSURROUNDING BLUEPRINT CONTEXT — use ONLY to render the statement below faithfully (its "
                 "notation, the intended objects, how this piece fits); do NOT formalize the context itself:\n"
                 + context.strip()[:2000] + "\n\n") if (context or "").strip() else ""
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
        raw = default_dispatch(prompt, runtime=runtime, repo=repo, timeout=timeout_s) or ""
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
        _observe_formalize(nl, mode, "", f"EXCEPTION: {_e!r}")
        return ""


def default_formalize_multistep(nl: str, *, runtime: str = "", timeout_s: "int | None" = None) -> str:
    """Thin alias — define-then-state is now a MODE of `default_formalize` (merged to kill the duplicate
    dispatch boilerplate). See the def-faithfulness CAVEAT in `default_formalize`. The per-dispatch budget is
    the CALIBRATED `formalize_multistep` factory budget (measured ~243s peak + headroom, not guessed) unless
    the caller overrides — so it lives in `common/timeouts`, the one home, env-tunable per node."""
    if timeout_s is None:
        from ztare.common.timeouts import timeout_s as _budget
        timeout_s = _budget("formalize_multistep")
    return default_formalize(nl, mode="define_then_state", runtime=runtime, timeout_s=timeout_s)


def default_backtranslate(lean_statement: str, *, model: str = "gemini-3.1-pro-preview") -> str:
    """Lean → NL back-translation — a mechanical rendering (one completion), so it uses `LLMRuntime`
    (gemini, a DIFFERENT family from a codex formalizer). Returns '' on any failure ⇒ the gate's
    non-empty guard fails-closed (no admission on a dead back-translator)."""
    prompt = prompts.BACKTRANSLATE_PROMPT.format(lean_statement=(lean_statement or ""))
    back = (_api_text(prompt, model=model, label="autoformalize_backtranslate") or "").strip()
    _observe_roundtrip("backtranslate", lean_statement=(lean_statement or ""), back_nl=back, model=model)
    return back


def default_directional_judge(orig_nl: str, back_nl: str, *, model: str = "gemini-3.1-pro-preview") -> bool:
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
    prompt = prompts.DIRECTIONAL_JUDGE_PROMPT.format(orig_nl=orig_nl, back_nl=back_nl)
    n = 3
    try:
        n = max(1, int(_os.environ.get("ZTARE_LEANMILL_JUDGE_SAMPLES", "3") or "3"))
    except (TypeError, ValueError):
        n = 3
    raws: "list[str]" = []
    votes: "list[bool]" = []
    for _ in range(n):
        raw = (_api_text(prompt, model=model, label="autoformalize_judge") or "").strip()
        raws.append(raw)
        first = raw.upper().splitlines()[0] if raw else ""
        votes.append(first.strip().startswith("EQUIVALENT"))
    faithful = (sum(1 for v in votes if v) * 2 > n)          # STRICT majority (fail-closed on a tie)
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
    sig = _extract_signature(statement)
    if detect_risks(sig).get("vacuity_suspected") is True:
        return True
    triv = re.sub(r":=\s*(?:by\s+)?sorry",
                  ":= by first | trivial | rfl | simp_all | omega | decide | tauto | norm_num | aesop",
                  statement, count=1, flags=re.S)
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


def default_solve(target_name: str, statement: str, *, substrate, timeout_s: int = 600,
                  notes: "str | None" = None) -> dict:
    """solve_fn: route an ADMITTED faithful statement into the existing solver+governance (solve_adhoc).
    `notes` (optional, #81) carries a blueprint into the recursive planner (advisory; kernel-gated)."""
    from ztare.leanmill.solver.solver_core import solve_adhoc  # #42: import from src, not the script
    body = statement if statement.lstrip().startswith("import") else f"import Mathlib\n\n{statement}"
    return solve_adhoc(target_name, body, "", substrate=str(substrate), mode="dag_search",
                       timeout_s=timeout_s, notes=notes)


_SHELL_CONST = {"0", "1", "True", "False", "∅", "()", "Unit", "PUnit", "default", "arbitrary",
                "sorry", "trivial", "{}", "[]"}


def detect_def_shells(formalization: str) -> "list[tuple[str, str]]":
    """Deterministic def-faithfulness PRE-gate for `define_then_state` output (#23). A `def Genus := 0`
    / `abbrev X := True` shell makes the theorem typecheck VACUOUSLY while the statement-level round-trip
    (which back-translates the THEOREM text, not the def BODY) passes — so a def-shell launders through
    the firewall. Flags def/abbrev declarations whose body is a DEGENERATE CONSTANT (bare literal /
    True/False / ∅ / sorry / `fun _ => <const>`). CONSERVATIVE — only UNAMBIGUOUS shells, so it never
    false-rejects a real def. Returns [(name, reason)]; empty = no obvious shell. (The full gate also
    back-translates each def + cold-judges it vs the NL — the LLM layer; this is the cheap core.)"""
    shells: "list[tuple[str, str]]" = []
    for m in re.finditer(
        r"(?ms)^\s*(?:noncomputable\s+|private\s+|scoped\s+)*(def|abbrev)\s+([A-Za-z_][\w'.]*)"
        r".*?:=\s*(.+?)(?=\n\s*(?:noncomputable\s+|private\s+|scoped\s+)*"
        r"(?:def|abbrev|structure|inductive|theorem|lemma|instance|class|namespace|end|open|variable|#)\b|\Z)",
        formalization):
        kind, name, raw = m.group(1), m.group(2), m.group(3).strip()
        body = re.sub(r"^fun\b.*?=>\s*", "", raw, flags=re.DOTALL).strip()   # strip a leading λ
        tok = body.split()[0] if body.split() else body
        if (body in _SHELL_CONST or tok in _SHELL_CONST
                or re.fullmatch(r"-?\d+(\.\d+)?", body) or body.startswith("sorry")):
            shells.append((name, f"{kind} `{name}` body is a degenerate constant: {raw[:50]!r}"))
    return shells


def _default_def_judge(nl: str, decl: str, *, model: str = "gemini-3.1-pro-preview") -> bool:
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


def _reformulate_feedback(prior_stmt: str, refutation: str) -> str:
    """Targeted formalizer context for the reformulation re-entry: tell the (warm-RESUMED) agent its prior
    rendering was REFUTED and why, and that it must produce the INTENDED TRUE statement faithful to the NL —
    NOT a weakening, NOT the refuted rendering. The faithfulness firewall re-gates this against the ORIGINAL nl
    (it cannot launder); statement_integrity keeps it from reproducing the refuted statement."""
    return ("\n\n[REFORMULATE] A prior formalization of this target was REFUTED as FALSE during proving:\n"
            f"  {(prior_stmt or '').strip()[:500]}\n"
            f"Refutation: {refutation.strip()[:400]}\n"
            "That rendering MIS-STATES the intended mathematics. Produce the INTENDED, TRUE statement that "
            "faithfully captures the natural-language target — do NOT weaken it, and do NOT reproduce the "
            "refuted rendering. (The faithfulness firewall re-checks this against the original problem.)")


def _planner_subdag(sv) -> "Optional[dict]":
    """The planner's sub-DAG `{lemmas, chain, lnames}` for the notes write-back / compound. `route_and_solve`
    returns `{routed, decomposition: {lemmas, chain, lnames}, solution}` — the lemmas live UNDER `decomposition`.
    Surface THAT, not the whole `iso_route` wrapper: the prior code set `out["decomposition"] = sv["iso_route"]`,
    so compound/refined-notes looked for `["lemmas"]` one level too high, found None, and the self-evolving loop
    PERSISTED NOTHING (the agent's mid-proof decomposition was dropped between runs — the amnesia bug)."""
    if not isinstance(sv, dict):
        return None
    return (sv.get("iso_route") or {}).get("decomposition") or None


def autoformalize_and_solve(nl: str, *, sandbox, substrate=None,
                            formalize_fn=None, compile_fn=None, triviality_fn=None,
                            backtranslate_fn=None, judge_fn=None, structural_fn=None,
                            solve_fn=None, timeout_s: int = 600, max_refines: int = 2,
                            def_faithfulness: bool = False, notes: "str | None" = None,
                            extra_context: str = "", reformulate_budget: "int | None" = None) -> dict:
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
    substrate = substrate or sandbox
    _caller_formalize_fn = formalize_fn   # PRESERVE the caller's value (None in prod) for the reformulate recursion,
    #                                       so the re-entry rebuilds formalize_fn with the NEW refutation context.
    formalize_fn = formalize_fn or default_formalize
    if formalize_fn is default_formalize:
        # Thread the LEAN ROOT so the INTERACTIVE formalizer (default-on) can start the warm REPL + the agent can
        # `lean-check`/`search` to a TYPECHECKING statement. Plus, when ZTARE_LEANMILL_FORMALIZE_NOTES=1, the
        # blueprint NOTES as render context (#88; it was notes-blind). The firewall still gates faithfulness, so
        # neither can launder — they only RAISE the faithful-render rate. `extra_context` carries the reformulate
        # refutation feedback (warm-resumed agent's continuation cue) on a re-entry.
        _notes_ctx = notes if (os.environ.get("ZTARE_LEANMILL_FORMALIZE_NOTES") == "1" and (notes or "").strip()) else ""
        _fctx = (_notes_ctx + extra_context).strip()
        formalize_fn = lambda _nl: default_formalize(_nl, lean_root=sandbox, context=_fctx)  # noqa: E731
    compile_fn = compile_fn or (lambda s: default_compile(s, sandbox))
    compile_diagnose_fn = lambda s: default_compile_diagnose(s, sandbox)  # noqa: E731 — advisory Lean-error text for the refine hint (not a gate)
    triviality_fn = triviality_fn or (lambda s: default_triviality(s, sandbox))
    backtranslate_fn = backtranslate_fn or default_backtranslate
    judge_fn = judge_fn or default_directional_judge
    solve_fn = solve_fn or (lambda n, s: default_solve(n, s, substrate=substrate, timeout_s=timeout_s, notes=notes))

    # FAITHFULNESS STORE (#86, ZTARE_LEANMILL_FAITHFULNESS_STORE=1; default-off = byte-parity). The
    # autoformalize axis was the ONLY one that learned nothing — every faithfulness verdict recomputed cold,
    # and `structural_faithfulness` ran advisory-NO-OP because production never fed it a reference. When ON +
    # no caller-supplied structural_fn: recall a prior CONFIRMED faithful rendering of THIS NL and feed its
    # fingerprint as the `expected` reference so the silent-weakening guard runs LOAD-BEARING; deposit on a
    # fresh admit. Parity-safe: a first-seen NL has no reference ⇒ `structural_faithfulness(expected=None)` =
    # True (admit, as today); only a RE-seen NL whose new rendering is WEAKER than the stored faithful one is
    # newly caught (a sound tightening). The firewall's kernel legs remain the sole faithfulness arbiter.
    _fstore = None
    _prior_confirmed_fn = None
    if structural_fn is None and os.environ.get("ZTARE_LEANMILL_FAITHFULNESS_STORE", "1") != "0":   # DEFAULT-ON 2026-06-12 (deposit only on CONFIRMED admits; recall only STRENGTHENS the guard; =0 reverts)
        try:
            from ztare.leanmill.solver.faithfulness_store import FaithfulnessStore
            from ztare.leanmill.solver.solver_core import OUT_DIR as _OUT
            _fstore = FaithfulnessStore(_OUT / "solver_lane_faithfulness_store.jsonl")
            _exp = (_fstore.reference(nl) or {}).get("fingerprint")
            structural_fn = lambda _nl, _s: structural_faithfulness(_nl, _s, expected=_exp)  # noqa: E731
            # #105: a re-seen statement that EXACTLY matches the stored CONFIRMED rendering skips the flaky
            # round-trip JUDGE (the deterministic legs — incl. the structural reference above — still run, so
            # this can only skip the variance-prone LLM, never admit a different/weaker statement).
            def _prior_confirmed_fn(_nl, _s):  # noqa: E306
                _ref = _fstore.reference(_nl) or {}
                _ss = " ".join((_ref.get("statement") or "").split())
                return bool(_ss) and _ss == " ".join((_s or "").split())
        except Exception:  # noqa: BLE001 — the store is advisory; never break the firewall
            _fstore = None
            _prior_confirmed_fn = None

    af, refine_trace = autoformalize_refine(
        nl, formalize_fn=formalize_fn, compile_fn=compile_fn, triviality_fn=triviality_fn,
        backtranslate_fn=backtranslate_fn, judge_fn=judge_fn, structural_fn=structural_fn,
        compile_diagnose_fn=compile_diagnose_fn,   # feed the ACTUAL Lean error into the compile-fix refine (not blind)
        prior_confirmed_fn=_prior_confirmed_fn,
        max_refines=max_refines)
    # #88 MULTISTEP ESCALATION: a oneshot formalization the firewall REJECTS may still be faithfully
    # formalizable with more deliberation — MEASURED 2026-06-10: the hard partial-fraction-existence lemma went
    # rejected(oneshot) → admitted+faithful(multistep, real Mathlib `RatFunc` objects, no def-shell). Retry the
    # REJECTED case ONCE with `default_formalize_multistep` (define_then_state). The escalated statement flows
    # through the SAME downstream gates (def-shell + def-faithfulness below), so it cannot launder. Gated
    # default-off (`ZTARE_LEANMILL_MULTISTEP_ESCALATE`) — multistep is EXPENSIVE (~7 dispatches/lemma).
    from ztare.leanmill.solver.agentic_leaf import INADMISSIBLE_DISPATCH as _INADM
    if (not af.is_target and af.verdict.reason != "INADMISSIBLE_PROVIDER_DEAD" and af.lean_statement != _INADM
            and os.environ.get("ZTARE_LEANMILL_MULTISTEP_ESCALATE") == "1"):
        try:
            _af2, _tr2 = autoformalize_refine(
                nl, formalize_fn=lambda _nl: default_formalize_multistep(_nl),
                compile_fn=compile_fn, triviality_fn=triviality_fn, backtranslate_fn=backtranslate_fn,
                judge_fn=judge_fn, structural_fn=structural_fn, max_refines=0)
            if _af2.is_target:
                af, refine_trace = _af2, (refine_trace or []) + ["multistep_escalation"] + (_tr2 or [])
        except Exception:  # noqa: BLE001 — escalation is best-effort; the oneshot rejection stands on failure
            pass
    out = {"nl": nl, "lean_statement": af.lean_statement, "faithful": af.verdict.accepted,
           "faithfulness_reason": af.verdict.reason, "faithfulness_checks": af.verdict.checks,
           "refine_trace": refine_trace, "refine_rounds": max(0, len(refine_trace) - 1), "solved": None}
    from ztare.leanmill.solver.agentic_leaf import INADMISSIBLE_DISPATCH as _INADM  # #89: dead instrument —
    if af.lean_statement == _INADM or af.verdict.reason == "INADMISSIBLE_PROVIDER_DEAD":  # every provider dead ⇒
        out["outcome"] = "inadmissible_provider_dead"      # NOT a faithful=False negative. Deposit nothing,
        out["faithful"] = None; out["lean_statement"] = ""  # exclude from the faithful-rate denominator.
        return out
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
    if def_faithfulness:
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
                           fingerprint=_parse_lean_statement(af.lean_statement), source="firewall_admit")
        except Exception:  # noqa: BLE001
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
    if _refutation and reformulate_budget > 0 and r0.get("outcome") != "closed":
        re_out = autoformalize_and_solve(
            nl, sandbox=sandbox, substrate=substrate, formalize_fn=_caller_formalize_fn,
            compile_fn=compile_fn, triviality_fn=triviality_fn, backtranslate_fn=backtranslate_fn,
            judge_fn=judge_fn, structural_fn=structural_fn, solve_fn=solve_fn, timeout_s=timeout_s,
            max_refines=max_refines, def_faithfulness=def_faithfulness, notes=notes,
            extra_context=extra_context + _reformulate_feedback(af.lean_statement, _refutation),
            reformulate_budget=reformulate_budget - 1)
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
