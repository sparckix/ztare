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

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable, Optional


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
                      structural_fn: "Optional[Callable[[str, str], bool]]" = None) -> FaithfulnessVerdict:
    """The firewall. ALL injected fns MUST return strict `bool`. compile_fn(stmt)->typechecks-with-
    sorry; triviality_fn(stmt)->closeable-by-cheap-tactics(goal AND context, e.g. simp_all/omega);
    consistency_fn(stmt)->hypotheses-mutually-CONSISTENT (False ⇒ vacuous; reuse
    `governance_organs.randomized_differential_probe` / a derive-False probe); backtranslate_fn(stmt)
    ->NL; judge_fn(orig_nl, back_nl)->faithful-AND-not-weaker (DIRECTIONAL — see contract below).

    FAIL-CLOSED on EVERY leg: a formalization is admitted only on a POSITIVE signal; ANY inconclusive,
    errored, or non-canonical-True result ⇒ NOT admitted. Opposite of the prover gates, because here a
    false ACCEPT is a fabricated success.

    judge_fn CONTRACT (HIGH-4/MEDIUM-3, enforce in the PRODUCTION wiring, not here): the judge must be
    DIRECTIONAL — "is the formalization EQUIVALENT, or weaker/stronger? does it drop/add a hypothesis or
    relax the conclusion (≤→<, =→≤, ∀→∃)?" — accept only EQUIVALENT; it must be a COLD cross-family
    judge (family ≠ the formalizer's), ideally ≥2 unanimous; and a deterministic structural diff
    (`statement_integrity`) on the hypothesis set / conclusion shape should be able to OVERRIDE a
    charitable judge. The single NL-vs-NL paraphrase judge alone is NOT sufficient for hard targets."""
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

    try:
        back_nl = backtranslate_fn(stmt) or ""
        checks["round_trip_faithful"] = bool(_visible(back_nl)) and _is_true(judge_fn(nl, back_nl))
    except Exception as e:
        return FaithfulnessVerdict(False, f"round-trip errored ⇒ NOT admitted (fail-closed): {repr(e)[:80]}", checks)
    if not checks["round_trip_faithful"]:
        return FaithfulnessVerdict(False, "round-trip does NOT match the NL (or empty/degenerate) — unfaithful / weakened / vacuous", checks)

    return FaithfulnessVerdict(True, "faithful: typechecks, non-trivial, (consistent,) round-trip matches the NL intent", checks)


def autoformalize(nl: str, *, formalize_fn: "Callable[[str], str]",
                  compile_fn: "Callable[[str], bool]",
                  triviality_fn: "Callable[[str], bool]",
                  backtranslate_fn: "Callable[[str], str]",
                  judge_fn: "Callable[[str, str], bool]",
                  consistency_fn: "Optional[Callable[[str], bool]]" = None,
                  structural_fn: "Optional[Callable[[str, str], bool]]" = None) -> AutoformalizeResult:
    """NL → candidate Lean statement → faithfulness gate. Returns the result; `.is_target` is True
    only for an ADMITTED faithful formalization. All steps injected (real apparatus in production,
    mocks in tests). The formalizer and the judge SHOULD be different model families (the judge is a
    cold cross-family check, never the formalizer blessing its own output)."""
    try:
        lean_statement = (formalize_fn(nl) or "").strip()
    except Exception as e:
        return AutoformalizeResult(nl, "", FaithfulnessVerdict(False, f"formalizer errored: {repr(e)[:80]}"))
    verdict = faithfulness_gate(nl, lean_statement, compile_fn=compile_fn, triviality_fn=triviality_fn,
                                backtranslate_fn=backtranslate_fn, judge_fn=judge_fn,
                                consistency_fn=consistency_fn, structural_fn=structural_fn)
    return AutoformalizeResult(nl, lean_statement, verdict)


def _formalize_feedback_hint(verdict: "FaithfulnessVerdict", prior_stmt: str) -> str:
    """Turn the firewall's REJECTION into targeted NL guidance the formalizer can act on — the
    per-leg feedback that makes the refine loop close compile/faithfulness gaps instead of re-rolling."""
    checks = getattr(verdict, "checks", {}) or {}
    reason = getattr(verdict, "reason", "") or ""
    if checks.get("compiles") is False or "typecheck" in reason:
        guide = ("It did NOT typecheck. Fix the Lean 4 syntax / Mathlib API errors so `lake env lean` "
                 "reports zero `error:` lines (the `sorry` is fine). Keep the definitions; correct only what fails.")
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
                         max_refines: int = 2) -> "tuple[AutoformalizeResult, list]":
    """Autoformalize through the shared RefineHandover loop — the compile-fix the one-shot `autoformalize`
    lacks (Litt P1 produced a faithful-STRUCTURED but uncompiling formalization that the one-shot gate just
    rejected). On a firewall rejection, hand the formalizer back the verdict's failing leg + its prior
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
                                 consistency_fn=consistency_fn, structural_fn=structural_fn)

    def _refine_ctx(stmt, verdict, ctx):
        if not (stmt or "").strip():
            return None                      # empty generation ⇒ nothing to repair from ⇒ stop
        return {"nl": nl, "hint": _formalize_feedback_hint(verdict, stmt)}

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
    stmts = re.findall(r"(?s)\b((?:theorem|lemma)\s+\S+.*?:=\s*(?:by\s+)?sorry)", clean)
    if stmts:
        return stmts[-1].strip()
    for ln in reversed(lines):                                          # fallback: last theorem-ish line
        if ("theorem" in ln or "lemma" in ln) and "sorry" in ln:
            return ln.strip()
    return ""   # no theorem/import block found ⇒ "" so the firewall's empty-formalization fast-reject fires


def default_formalize(nl: str, *, mode: str = "oneshot", runtime: str = "codex", timeout_s: int = 240) -> str:
    """NL → candidate Lean (`… := by sorry`) via the leanmill WARM-AGENT ARCHITECTURE
    (`agentic_leaf.default_dispatch` on subscription, codex/claude) — the SAME dispatch the SOLVER uses,
    NOT a parallel one and NOT the isomorphism loop (which deanchors for analogical jumps). `mode`
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
    try:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch
    except Exception:
        try:
            from src.ztare.leanmill.solver.agentic_leaf import default_dispatch  # type: ignore
        except Exception:
            return ""
    repo = Path(__file__).resolve().parents[4]
    prompt = _FORMALIZE_PROMPTS[mode] + (nl or "")
    try:
        raw = default_dispatch(prompt, runtime=runtime, repo=repo, timeout=timeout_s) or ""
        return _extract_lean_from_dispatch(raw, mode)
    except Exception:
        return ""


def default_formalize_multistep(nl: str, *, runtime: str = "codex", timeout_s: int = 360) -> str:
    """Thin alias — define-then-state is now a MODE of `default_formalize` (merged to kill the duplicate
    dispatch boilerplate). See the def-faithfulness CAVEAT in `default_formalize`."""
    return default_formalize(nl, mode="define_then_state", runtime=runtime, timeout_s=timeout_s)


def default_backtranslate(lean_statement: str, *, model: str = "gemini-3.1-pro-preview") -> str:
    """Lean → NL back-translation — a mechanical rendering (one completion), so it uses `LLMRuntime`
    (gemini, a DIFFERENT family from a codex formalizer). Returns '' on any failure ⇒ the gate's
    non-empty guard fails-closed (no admission on a dead back-translator)."""
    prompt = ("Translate this Lean 4 theorem statement into a precise one-sentence natural-language math "
              "statement. Preserve EVERY hypothesis and the exact conclusion (do not strengthen, weaken, "
              "or drop anything). Output ONLY the sentence.\n\n" + (lean_statement or ""))
    return (_api_text(prompt, model=model, label="autoformalize_backtranslate") or "").strip()


def default_directional_judge(orig_nl: str, back_nl: str, *, model: str = "gemini-3.1-pro-preview") -> bool:
    """DIRECTIONAL faithfulness judge: True ONLY if the back-translation is LOGICALLY EQUIVALENT to the
    original — not weaker, not stronger, no dropped/added hypothesis, no relaxed conclusion (≤→<, =→≤,
    ∀→∃). One `LLMRuntime` completion (gemini, cross-family from a codex formalizer); parses a strict
    verdict token and FAILS-CLOSED (returns False) on any ambiguity/failure. The deterministic
    `structural_faithfulness` carrier OVERRIDES a charitable verdict here."""
    prompt = ("You are a strict faithfulness judge. Two natural-language math statements:\n"
              f"ORIGINAL: {orig_nl}\nCANDIDATE (back-translated from a formalization): {back_nl}\n\n"
              "Is the CANDIDATE LOGICALLY EQUIVALENT to the ORIGINAL — same hypotheses, same conclusion, "
              "neither weaker nor stronger (watch for a dropped/added hypothesis or a relaxed conclusion "
              "such as ≤ vs <, = vs ≤, ∀ vs ∃)? Answer with EXACTLY one token on the first line: "
              "EQUIVALENT or NOT_EQUIVALENT.")
    text = (_api_text(prompt, model=model, label="autoformalize_judge") or "").strip().upper()
    first = text.splitlines()[0] if text else ""
    return first.strip().startswith("EQUIVALENT")


# ── PRODUCTION wiring of the firewall to the ONE kernel + the #24 probe, and the SOLVER LINK ────────
# These reuse the existing apparatus (gates/v33_preflight_risk_detector + the worker's solve_adhoc) —
# NO standalone governance. They are what turns the OPT-IN apparatus into the live end-to-end loop:
#   NL → autoformalize → faithfulness firewall (governance on the STATEMENT) → solve_adhoc (solver +
#   governance on the PROOF).

def _extract_signature(statement: str) -> str:
    """`theorem T (a:ℝ) : a = a := by sorry` → `theorem T (a:ℝ) : a = a` (drop the proof tail).
    The detector helpers (`_conclusion`/`_hyp_types`) tolerate the `theorem T` prefix."""
    return re.split(r":=", statement, maxsplit=1)[0].strip()


def default_compile(statement: str, sandbox) -> bool:
    """compile_fn: does the statement TYPECHECK (with `sorry`)? Reuses the kernel compile path
    (`_compile_probe` = `lake env lean`, error≠warning so `sorry` is fine). True iff no Lean error."""
    from ztare.gates.v33_preflight_risk_detector import _compile_probe
    body = statement if statement.lstrip().startswith("import") else f"import Mathlib\n\n{statement}"
    return _compile_probe(body, sandbox, "AutoformCompile", 150) is True


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
    return nondegenerate_instance_probe(sig, sandbox, timeout=150).get("vacuity_confirmed") is True


def default_solve(target_name: str, statement: str, *, substrate, timeout_s: int = 600) -> dict:
    """solve_fn: route an ADMITTED faithful statement into the existing solver+governance (solve_adhoc)."""
    from ztare.leanmill.solver.solver_core import solve_adhoc  # #42: import from src, not the script
    body = statement if statement.lstrip().startswith("import") else f"import Mathlib\n\n{statement}"
    return solve_adhoc(target_name, body, "", substrate=str(substrate), mode="dag_search", timeout_s=timeout_s)


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


_DEF_JUDGE_PROMPT = (
    "A natural-language math problem and a Lean DEFINITION extracted from its formalization:\n"
    "PROBLEM: {nl}\nDEFINITION (Lean): {decl}\n\n"
    "Is this definition a FAITHFUL formalization of an object/notion the problem refers to — or is it a "
    "PLACEHOLDER / SHELL / WRONG object (a constant stand-in, an opaque parameter, or a DIFFERENT notion "
    "than intended)? Answer with EXACTLY one token on the first line: FAITHFUL or UNFAITHFUL, then a "
    "one-line reason."
)


def _default_def_judge(nl: str, decl: str, *, model: str = "gemini-3.1-pro-preview") -> bool:
    """Cold cross-family (gemini) judge for ONE Lean definition vs the NL intent. Returns True (faithful)
    unless a CLEAR `UNFAITHFUL` verdict — FAITHFUL / ambiguous / empty / error all → True (admit), so the
    layer does NOT over-reject faithful defs (detect_def_shells + the statement-level firewall are the
    fail-closed layers; this catches the clear NON-constant wrong-object / placeholder)."""
    text = (_api_text(_DEF_JUDGE_PROMPT.format(nl=(nl or "")[:1200], decl=(decl or "")[:800]),
                      model=model, label="autoformalize_def_judge") or "").strip().upper()
    first = text.splitlines()[0] if text else ""
    return not first.startswith("UNFAITHFUL")


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


def autoformalize_and_solve(nl: str, *, sandbox, substrate=None,
                            formalize_fn=None, compile_fn=None, triviality_fn=None,
                            backtranslate_fn=None, judge_fn=None, structural_fn=None,
                            solve_fn=None, timeout_s: int = 600, max_refines: int = 2,
                            def_faithfulness: bool = False) -> dict:
    """THE END-TO-END LINK: NL → autoformalize (faithfulness firewall) → if admitted, solve_adhoc
    (solver + governance kernel). The firewall GATES the solver — an unfaithful / vacuous / trivial
    statement is rejected BEFORE any solve, which is what prevents the worst laundering (an opaque or
    weakened statement that then gets "closed"). Every leg is injectable (mocks in tests); the defaults
    wire the real apparatus. Returns the formalization, the faithfulness verdict, and the closure."""
    substrate = substrate or sandbox
    formalize_fn = formalize_fn or default_formalize
    compile_fn = compile_fn or (lambda s: default_compile(s, sandbox))
    triviality_fn = triviality_fn or (lambda s: default_triviality(s, sandbox))
    backtranslate_fn = backtranslate_fn or default_backtranslate
    judge_fn = judge_fn or default_directional_judge
    solve_fn = solve_fn or (lambda n, s: default_solve(n, s, substrate=substrate, timeout_s=timeout_s))

    af, refine_trace = autoformalize_refine(
        nl, formalize_fn=formalize_fn, compile_fn=compile_fn, triviality_fn=triviality_fn,
        backtranslate_fn=backtranslate_fn, judge_fn=judge_fn, structural_fn=structural_fn,
        max_refines=max_refines)
    out = {"nl": nl, "lean_statement": af.lean_statement, "faithful": af.verdict.accepted,
           "faithfulness_reason": af.verdict.reason, "faithfulness_checks": af.verdict.checks,
           "refine_trace": refine_trace, "refine_rounds": max(0, len(refine_trace) - 1), "solved": None}
    if not af.is_target:
        out["outcome"] = "rejected_by_firewall"          # the firewall did its job — no unsound solve
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
    # Target the LAST theorem|lemma (the stated target — in define_then_state the main claim follows
    # the helper defs/lemmas; the old FIRST-`theorem`-only regex mis-pointed the solver at a helper and
    # missed `lemma`-only bodies → misreported `admitted_and_closed` on a trivial helper). Review fix 2026-06-05.
    _names = re.findall(r"(?m)\b(?:theorem|lemma)\s+([A-Za-z_][\w'.]*)", af.lean_statement)
    name = _names[-1] if _names else "autoform_target"
    sv = solve_fn(name, af.lean_statement)
    r0 = (sv.get("results") or [{}])[0] if isinstance(sv, dict) else {}
    out["solved"] = r0.get("outcome")
    out["governance"] = sv.get("governance") if isinstance(sv, dict) else None
    out["closure_certificate"] = sv.get("closure_certificate") if isinstance(sv, dict) else None
    out["outcome"] = f"admitted_and_{r0.get('outcome')}"
    return out


def _self_test() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

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

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
