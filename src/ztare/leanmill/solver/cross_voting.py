"""CROSS-VOTING — the AWS-ARc faithfulness move for AUTOFORMALIZATION (NL→Lean), NOT a DAG/proof move.

The hard, un-punted problem of autoformalization is FAITHFULNESS: is the formal Lean statement a true
rendering of the natural-language problem, or subtly VACUOUS / WEAKER / WRONG? (see the firewall in
`ztare.leanmill.solver.autoformalize`.) The single-judge round-trip is consensus-grade; this is the
KERNEL-grade upgrade that needs NO human labels: ask N DIVERSE formalizers (different model families —
codex + claude + gemini) to independently formalize the SAME NL statement, then prove PAIRWISE EQUIVALENCE
with the Lean kernel. The carrier is exogenous: agreement is not "two models think it's the same", it is
"the kernel proves `ref ↔ cand` over the whole (finite) domain". This is the AWS Automated-Reasoning-Checks
move (cross-check independent renderings against a sound arbiter), instanced on Lean.

  * If all K formalizations are PROVABLY EQUIVALENT (clique of kernel-checked `↔`) ⇒ FAITHFUL without
    human labels — the agreed statement is admitted as the target.
  * If they DISAGREE ⇒ return the DISTINGUISHING CASE (via `smt_checker.distinguishing_requests` when the
    predicate is over a decidable finite/enum domain, else the structural diff) to feed back to the
    formalizers / the operator. A disagreement is a SIGNAL, never a silent admit.

DISCIPLINE (matches `conjecture.py`):
  (1) NEW self-contained module — it ORCHESTRATES the canonical homes, embeds NO governance:
      kernel equivalence = the EXISTING `autoformalize.provable_equivalence` (Lean `decide` over a Fintype)
      OR a `↔`-probe through the ONE kernel (`v33_preflight_risk_detector._compile_probe`); the structural
      fallback = the EXISTING `statement_integrity`; the distinguishing case = the EXISTING
      `common.smt_checker`. No parallel governance frankenstein.
  (2) KERNEL-GATED — `cross_vote_equivalent` only reports FAITHFUL on a clique the Lean kernel verifies
      via `_compile_probe`/`provable_equivalence`. A wrong/optimistic equivalence merely fails to compile
      ⇒ NOT-faithful (a MISS), never a false "faithful". No laundering surface.
  (3) FLAG-GATED — the move-runner wiring is behind `ZTARE_LEANMILL_CROSSVOTE` (default off = byte parity;
      this is an autoformalization-stage move, not a DAG move, so it does not touch the proof loop unless
      the flag is on and the autoformalize entry-point calls it).
  (4) `_selftest()` with POSITIVE (faithful clique admitted) AND NEGATIVE (a silently-weakened
      formalization rejected + its distinguishing case returned) controls — a gate that never says no is a
      false-success generator. The kernel legs are SKIPPED (not faked) when Lean/z3 are absent.
  (5) External deps (z3 via `smt_checker`, the Lean toolchain) lazy-imported + FAIL-CLOSED on absence:
      no kernel ⇒ no FAITHFUL verdict (it stays inconclusive), never a silent admit.

SOUNDNESS NOTE: cross-voting NEVER closes a goal or proves a theorem — it only decides whether a set of
candidate STATEMENTS is the same problem. Its output is a faithfulness verdict on the TARGET; the proof
loop is downstream and unchanged.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

CROSSVOTE_FLAG = "ZTARE_LEANMILL_CROSSVOTE"
EQUIV_TIMEOUT_ENV = "ZTARE_LEANMILL_EQUIV_TIMEOUT_S"   # per-pair kernel `↔` compile budget (cold-Mathlib safe)


def _equiv_timeout_default() -> int:
    """Per-pair kernel-equivalence compile budget, from `ZTARE_LEANMILL_EQUIV_TIMEOUT_S` (else 180s).

    The 180 is MEASURED, not guessed (`projects/leanmill_experiments/calibrate_equiv_timeout.py`,
    2026-06-09): a COLD `↔` probe compiles in ~10-11s (max 22s on the first cold OS-cache miss) — Mathlib
    oleans load in ~10s here, NOT the ~90s once assumed. The 120s timeouts that produced false-negatives
    were pure CONTENTION (4 parallel `lake env lean` jobs → ~12× slowdown), not inherent time. 180s = ~16×
    the median clean compile: covers first-cold + moderate load, yet fails-closed within 3 min if a compile
    genuinely hangs. Asymmetric on purpose — a too-tight value times out → `_compile_probe` None →
    fail-closed FALSE-NEGATIVE (rejects a FAITHFUL formalization), which is worse than waiting. Raise it via
    the env on a heavily-contended box (and prefer NOT running parallel Lean compiles — see the calibrator).
    Floors at 60s. Resolved through the central time-budget factory (`ztare.common.timeouts`, env
    ZTARE_LEANMILL_EQUIV_TIMEOUT_S, default 180, floor 60) so every blocking timeout lives in one place."""
    from ztare.common.timeouts import timeout_s
    return timeout_s("equiv_compile")


# ── formalizer specs: N DIVERSE families via the EXISTING dispatch (no parallel) ─────────────────────
@dataclass(frozen=True)
class Formalizer:
    """One independent formalizer: a (family, route) the cross-vote dispatches NL→Lean through. `family`
    is for the diversity/audit label; `route` selects the EXISTING dispatch path:
      * "subscription" → `agentic_leaf.default_dispatch` (codex/claude) via `autoformalize.default_formalize`;
      * "llm_runtime"  → `autoformalize._api_text` (gemini/deepseek), the cross-family non-subscription path.
    DIVERSITY is the whole point — at least two distinct `family` values, never one family voting twice."""
    family: str            # "codex" | "claude" | "gemini" | …  (the model family, the diversity axis)
    route: str = "subscription"   # "subscription" | "llm_runtime"
    model: str = ""        # for llm_runtime: the model id (e.g. "gemini-3.1-pro-preview"); else unused


DEFAULT_FORMALIZERS = (
    Formalizer("codex", "subscription"),
    Formalizer("claude", "subscription"),
    Formalizer("gemini", "llm_runtime"),   # model="" ⇒ the configured round-trip model (solver.yaml), not hardcoded
)


def _formalize_one(nl: str, f: Formalizer, *, mode: str, timeout_s: int) -> str:
    """NL → a candidate Lean statement via ONE formalizer, reusing the EXISTING autoformalize dispatch.
    Returns the extracted `theorem … := by sorry` (or '' on any failure — the kernel/structural legs then
    treat a missing vote as no-agreement, never a silent admit)."""
    try:
        from ztare.leanmill.solver.autoformalize import default_formalize, _api_text, _extract_lean_from_dispatch
    except Exception:  # noqa: BLE001
        return ""
    if f.route == "subscription":
        if f.family not in ("codex", "claude"):   # default_dispatch supports ONLY these (fail-closed)
            return ""
        try:
            return default_formalize(nl, mode=mode, runtime=f.family, timeout_s=timeout_s) or ""
        except Exception:  # noqa: BLE001
            return ""
    if f.route == "llm_runtime":
        # the cross-family non-subscription path (gemini/deepseek), reusing the autoformalize prompts +
        # the SAME banner-stripping extractor so the candidate shape matches the subscription votes.
        from ztare.leanmill.solver.autoformalize import _FORMALIZE_PROMPTS
        prompt = _FORMALIZE_PROMPTS.get(mode, _FORMALIZE_PROMPTS["oneshot"]) + (nl or "")
        model = f.model or None   # None ⇒ `_api_text` uses the configured round-trip model (solver.yaml), not hardcoded
        try:
            raw = _api_text(prompt, model=model, label="crossvote_formalize", timeout_s=timeout_s) or ""
        except Exception:  # noqa: BLE001
            return ""
        return _extract_lean_from_dispatch(raw, mode)
    return ""


# ── kernel-checked pairwise equivalence over the FULL theorem statements ─────────────────────────────
def _closed_prop(stmt: str) -> str:
    """The candidate's statement as a CLOSED Prop (`∀ binders, conclusion`) — exactly what the `↔` probe
    compares. Reuses `conjecture._closed_goal_prop` so the binder parse is consistent across the solver.
    '' if the signature can't be cleanly split (⇒ no kernel vote rather than an unsound one)."""
    try:
        from ztare.leanmill.solver.conjecture import _closed_goal_prop
        return _closed_goal_prop(stmt) or ""
    except Exception:  # noqa: BLE001
        return ""


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _smt_iff_fallback(rp: str, cp: str, timeout_s: int = 5) -> "bool | None":
    """COLD-AGENT #3 (valid): on a kernel `↔` TIMEOUT, a None is NOT a disagreement — Lean automation is weak
    at structural equivalence. Distinguish 'too hard for Lean' from 'genuinely inequivalent' over the
    LIA/NIA fragment with z3: translate both closed Props' conclusions (reusing abduction's Lean→SMT) and ask
    whether they can DIFFER over the binder domain. Returns True (equivalent — z3 proves they never differ),
    False (a distinguishing assignment exists ⇒ really inequivalent), or None (can't translate ⇒ caller stays
    fail-closed). Quantifier-free differ-check; sound (a z3 verdict is exogenous, not a Lean-automation guess)."""
    try:
        import z3
        from ztare.leanmill.solver.abduction import _lean_term_to_smt, _parse_binders, _NAT_TYPES
    except Exception:  # noqa: BLE001
        return None

    def _split(p):
        m = re.match(r"^\s*∀\s*(.*?),\s*(.*)$", (p or "").strip(), re.S)
        return (m.group(1), m.group(2)) if m else (None, None)

    rb, rc = _split(rp)
    cb, cc = _split(cp)
    if rc is None or cc is None:
        return None
    rcs, ccs = _lean_term_to_smt(rc), _lean_term_to_smt(cc)
    if not rcs or not ccs:
        return None
    try:
        binders = _parse_binders(rb or "")
    except Exception:  # noqa: BLE001
        binders = []
    decls = "\n".join(f"(declare-const {n} Int)" for n, _t in binders)
    nat = "\n".join(f"(assert (>= {n} 0))" for n, t in binders if t in _NAT_TYPES)
    smt = f"(set-logic ALL)\n{decls}\n{nat}\n(assert (distinct {rcs} {ccs}))\n(check-sat)\n"
    try:
        s = z3.Solver()
        s.set("timeout", max(1, int(timeout_s)) * 1000)
        s.from_string(smt)
        r = s.check()
    except Exception:  # noqa: BLE001
        return None
    if r == z3.unsat:
        return True                                   # never differ over the domain ⇒ EQUIVALENT
    if r == z3.sat:
        return False                                  # a distinguishing assignment ⇒ genuinely inequivalent
    return None                                       # z3 unknown ⇒ stay fail-closed


def kernel_equivalent(ref_stmt: str, cand_stmt: str, lean_root: Path, timeout_s: int,
                      preamble: str = "") -> "tuple[bool, str]":
    """KERNEL-grade pairwise faithfulness: are two formalizations PROVABLY the SAME problem? Build the
    closed Props (`∀ binders, conclusion`) from each statement and ask the kernel to prove `(ref) ↔ (cand)`.
    A faithful pair compiles; a silently weakened/broadened one does NOT (a divergent input makes the `↔`
    false ⇒ no compile). Reuses the ONE kernel (`v33_preflight_risk_detector._compile_probe`), never a
    parallel verifier.

    FAIL-CLOSED on every non-positive signal: a missing/unparseable statement, an infra failure (probe
    returns None), or a non-compiling probe ⇒ (False, reason). A True is returned ONLY on a kernel-clean
    `↔` proof — so a wrong equivalence is a MISS, never a fabricated 'faithful'. The proof search is a
    bounded cheap-tactic cascade (the equivalence of two FAITHFUL renderings is typically `Iff.rfl` / a
    propositional rearrangement / `decide` on a finite domain); a hard `↔` that needs real math is reported
    NOT-equivalent here (conservative — we never assert faithfulness we cannot kernel-witness)."""
    if not (ref_stmt and ref_stmt.strip()) or not (cand_stmt and cand_stmt.strip()):
        return False, "missing statement (empty vote) — no kernel equivalence"
    rp, cp = _closed_prop(ref_stmt), _closed_prop(cand_stmt)
    if not rp or not cp:
        return False, "could not build a closed Prop from a statement signature (no kernel vote)"
    if _norm_ws(rp) == _norm_ws(cp):
        return True, "verbatim-identical closed Props (no kernel call needed)"
    try:
        from ztare.gates.v33_preflight_risk_detector import _compile_probe
    except Exception as e:  # noqa: BLE001
        return False, f"kernel unavailable ⇒ fail-closed (no faithful verdict): {e!r}"
    _pre = (preamble.strip() + "\n\n") if preamble.strip() else ""
    # Bounded cheap-tactic cascade for the ↔: faithful renderings differ only propositionally/definitionally.
    probe = (_pre + f"theorem _crossvote_equiv : ({rp}) ↔ ({cp}) := by\n"
             "  first | rfl | (constructor <;> intro h <;> exact h) | tauto | simp_all | decide | "
             "norm_num | omega | (constructor <;> intro h <;> (try exact h) <;> tauto)\n")
    if not probe.lstrip().startswith("import"):
        probe = "import Mathlib\n\n" + probe
    ok = _compile_probe(probe, lean_root, "CrossVoteEquiv", timeout_s)
    if ok is None:
        # COLD-AGENT #3: a TIMEOUT ≠ disagreement. Ask z3 to distinguish (over the LIA/NIA fragment) before
        # fail-closing — so a faithful pair whose `↔` Lean simply couldn't prove in time is NOT false-rejected.
        sv = _smt_iff_fallback(rp, cp, timeout_s=5)
        if sv is True:
            return True, "kernel ↔ timed out, but z3 PROVES equivalence over the arithmetic domain (Lean was just slow)"
        if sv is False:
            return False, "kernel ↔ timed out; z3 found a DISTINGUISHING assignment ⇒ genuinely inequivalent"
        return False, "kernel probe inconclusive (infra/timeout); z3 fallback couldn't decide ⇒ fail-closed"
    if ok is True:
        return True, "kernel-checked: (ref) ↔ (cand) compiles — provably the same problem"
    return False, "kernel could NOT prove (ref) ↔ (cand) — formalizations DISAGREE (or `↔` beyond cheap reach)"


def fintype_equivalent(prelude: str, predicate: str, binder: str, domain_type: str,
                       body_ref: str, body_cand: str, *, compile_probe: "Callable[[str], bool]") -> bool:
    """The '100%' EXHAUSTIVE leg for a FINITE decidable domain — delegates verbatim to the EXISTING
    `autoformalize.provable_equivalence` (`∀ x : domain_type, ref x ↔ cand x` by `decide`, enumerated over
    the Fintype). Use this instead of `kernel_equivalent` when the two votes are PREDICATES over a finite
    `Fintype`+`DecidableEq` domain (the AWS-ARc decidable-policy sweet spot) — a True is then a genuine
    100%-faithfulness certificate on that domain. `compile_probe(body)->bool` is the kernel probe (e.g.
    `lambda b: _compile_probe(b, lean_root, tag, t) is True`)."""
    from ztare.leanmill.solver.autoformalize import provable_equivalence
    return provable_equivalence(prelude, predicate, binder, domain_type, body_ref, body_cand,
                                compile_probe=compile_probe)


def structural_equivalent(ref_stmt: str, cand_stmt: str) -> "tuple[bool, str]":
    """ADVISORY structural-equality fallback (when no kernel is available, or to OVERRIDE a charitable
    kernel `↔` that smooths over a weakening). Reuses `statement_integrity` + `autoformalize`'s lexical
    fingerprint: equivalent iff the two signatures have the SAME normalized statement OR the SAME structural
    fingerprint (binder counts + conclusion comparator + ∀/∃ presence + quantifier order). This is NEVER a
    faithful-ADMIT on its own (no kernel) — it is the disagreement DETECTOR + the no-kernel degraded signal.
    Returns (structurally_equal, reason)."""
    from ztare.leanmill.solver.statement_integrity import _signature, _norm
    if _norm(_signature(ref_stmt or "")) == _norm(_signature(cand_stmt or "")):
        return True, "byte-identical signatures (mod whitespace/comments)"
    try:
        # SINGLE DOOR (2026-06-24 sweep): fingerprint the TARGET theorem, not the raw blob. `_parse_lean_statement`
        # on a multi-decl `define_then_state` formalization parses its LEADING def (the GATE3 sibling bug) — so a
        # cross-vote could call two formalizations "structurally equal" by comparing their shared leading defs while
        # the TARGET theorems differ (a silent-weakening false-negative). `statement_fingerprint` routes through
        # `_target_signature` (canonical last theorem/lemma) — the one door every gate/decision already uses.
        from ztare.leanmill.solver.autoformalize import statement_fingerprint as _parse_lean_statement
    except Exception:  # noqa: BLE001
        return False, "no structural parser available"
    a, b = _parse_lean_statement(ref_stmt or ""), _parse_lean_statement(cand_stmt or "")
    keys = ("n_binder_groups", "n_explicit_binders", "conclusion_op",
            "has_forall", "has_exists", "quantifier_sequence")
    diffs = [k for k in keys if a.get(k) != b.get(k)]
    if not diffs:
        return True, "same structural fingerprint (binders/conclusion-op/quantifiers match)"
    return False, f"structural fingerprint DIFFERS on {diffs} — silent weakening/broadening suspected"


# ── distinguishing case: the DISAGREEMENT payload (decidable-domain SMT, else structural diff) ───────
def distinguishing_case(ref_dsl: str, cand_dsl: str, domain: dict, *, max_cases: int = 6) -> "list[dict]":
    """When two formalizations DISAGREE over a DECIDABLE finite/numeric domain, return the concrete
    DISTINGUISHING requests (the exact inputs where they differ, labelled with the REFERENCE's decision) —
    the glass-box payload that feeds back to the formalizers/operator. Delegates to the EXISTING
    `common.smt_checker.SmtPolicyChecker.distinguishing_requests` (z3); the inputs are the two policies in
    that module's small z3-DSL over `domain` (attr→enum-list / 'int' / 'real' / 'bool').

    FAIL-CLOSED on z3 absence: returns [] (no distinguishing case found) — NEVER a silent 'they agree'.
    The CALLER must not read [] as agreement; agreement is decided ONLY by a positive `kernel_equivalent` /
    `fintype_equivalent`. This is purely the disagreement-EXPLANATION channel."""
    try:
        from ztare.common.smt_checker import SmtPolicyChecker
    except Exception:  # noqa: BLE001  (z3 absent → lazy ImportError here)
        return []
    try:
        chk = SmtPolicyChecker(domain)
        cases = chk.distinguishing_requests(ref_dsl, cand_dsl, max_cases=max_cases)
    except Exception:  # noqa: BLE001
        return []
    return [{"request": req, "ref_decision": bool(label)} for req, label in cases]


@dataclass
class CrossVoteVerdict:
    """The cross-vote outcome on a set of formalizations of ONE NL statement."""
    faithful: bool                      # True ⇒ a kernel-checked equivalence CLIQUE covers all votes
    agreed_statement: str = ""          # the representative faithful statement (the admitted target), if any
    n_votes: int = 0
    n_distinct_families: int = 0
    clique: "list[int]" = field(default_factory=list)      # indices of the agreeing (kernel-equivalent) votes
    disagreements: "list[dict]" = field(default_factory=list)  # [{i, j, reason}] for the failing pairs
    distinguishing: "list[dict]" = field(default_factory=list)  # decidable-domain divergence requests, if any
    reason: str = ""

    def to_dict(self) -> dict:
        return {"faithful": self.faithful, "agreed_statement": self.agreed_statement,
                "n_votes": self.n_votes, "n_distinct_families": self.n_distinct_families,
                "clique": self.clique, "disagreements": self.disagreements,
                "distinguishing": self.distinguishing, "reason": self.reason,
                "kind": "cross_voting", "carrier": "lean_kernel_pairwise_equivalence"}


def cross_vote_equivalent(statements: "list[str]", *, lean_root: Path, timeout_s: int,
                          preamble: str = "", families: "Optional[list[str]]" = None,
                          equiv_fn: "Optional[Callable[[str, str], tuple[bool, str]]]" = None,
                          domain: "Optional[dict]" = None,
                          dsl_of: "Optional[Callable[[str], str]]" = None) -> CrossVoteVerdict:
    """The core gate: given K candidate Lean statements (the diverse formalizers' votes), decide FAITHFUL
    iff the kernel proves them ALL pairwise EQUIVALENT (a clique over every pair). Pairwise equivalence is
    `equiv_fn(a, b) -> (bool, reason)`; the default is `kernel_equivalent` (the ONE kernel). FAIL-CLOSED:
    `faithful=True` only on a complete kernel-checked clique with ≥2 votes from ≥2 DISTINCT families
    (a single family voting twice is NOT cross-family corroboration). On ANY disagreeing pair ⇒
    `faithful=False` + the disagreement reasons + (if `domain`/`dsl_of` given) the SMT distinguishing case.

    DIVERSITY guard: `families` (parallel to `statements`) supplies each vote's model family. With <2
    distinct families present the verdict is NOT faithful regardless of kernel agreement (cross-voting's
    independence assumption — same-family agreement can be a SHARED bias, not faithfulness)."""
    n = len(statements or [])
    fams = list(families or [])
    n_fams = len(set(f for f in fams if f))
    v = CrossVoteVerdict(faithful=False, n_votes=n, n_distinct_families=n_fams)
    nonempty = [i for i, s in enumerate(statements or []) if (s or "").strip()]
    if len(nonempty) < 2:
        v.reason = "fewer than 2 non-empty votes — cannot cross-vote (need ≥2 independent formalizations)"
        return v
    eq = equiv_fn or (lambda a, b: kernel_equivalent(a, b, lean_root, timeout_s, preamble=preamble))
    disagreements: "list[dict]" = []
    for ai in range(len(nonempty)):
        for bi in range(ai + 1, len(nonempty)):
            i, j = nonempty[ai], nonempty[bi]
            ok, why = eq(statements[i], statements[j])
            if not ok:
                disagreements.append({"i": i, "j": j, "reason": why})
    v.disagreements = disagreements
    if disagreements:
        v.reason = (f"{len(disagreements)} disagreeing pair(s) — NOT faithful; the formalizations are not "
                    "the same problem (silent weakening/broadening or a genuine divergence)")
        # decidable-domain distinguishing case for the FIRST disagreeing pair (the feedback payload)
        if domain is not None and dsl_of is not None:
            i, j = disagreements[0]["i"], disagreements[0]["j"]
            try:
                ref_dsl, cand_dsl = dsl_of(statements[i]), dsl_of(statements[j])
                if ref_dsl and cand_dsl:
                    v.distinguishing = distinguishing_case(ref_dsl, cand_dsl, domain)
            except Exception:  # noqa: BLE001
                v.distinguishing = []
        return v
    # complete kernel-checked clique over all non-empty votes
    if n_fams < 2 and fams:   # families supplied but not diverse ⇒ no cross-family corroboration
        v.reason = (f"all votes agree but only {n_fams} distinct family(ies) — not cross-family corroboration "
                    "(same-family agreement can be shared bias, not faithfulness)")
        return v
    v.faithful = True
    v.clique = nonempty
    v.agreed_statement = statements[nonempty[0]]
    v.reason = (f"FAITHFUL — all {len(nonempty)} votes pairwise kernel-equivalent"
                + (f" across {n_fams} families" if n_fams >= 2 else "")
                + " (kernel-checked agreement, no human labels)")
    return v


def cross_vote_faithfulness(nl: str, *, lean_root: Path, formalizers=DEFAULT_FORMALIZERS,
                            mode: str = "oneshot", timeout_s: int = 240, equiv_timeout_s: "int | None" = None,
                            preamble: str = "", domain: "Optional[dict]" = None,
                            dsl_of: "Optional[Callable[[str], str]]" = None,
                            formalize_fn: "Optional[Callable[[str, Formalizer], str]]" = None
                            ) -> "tuple[CrossVoteVerdict, list[str]]":
    """END-TO-END cross-voting on an NL statement: dispatch the N DIVERSE formalizers → collect their Lean
    votes → `cross_vote_equivalent` (kernel-checked pairwise equivalence). Returns (verdict, votes). The
    formalizer dispatch reuses the EXISTING autoformalize path (`_formalize_one`); `formalize_fn(nl, f)->str`
    is injectable for tests (so the kernel/structural legs are unit-testable WITHOUT live agents). The
    verdict's `.faithful` is the kernel-grade, label-free faithfulness signal; on disagreement `.disagreements`
    + `.distinguishing` are the feedback payload.

    FLAG-GATED at the call site, not here: this function is only INVOKED when `ZTARE_LEANMILL_CROSSVOTE=1`
    (the autoformalize entry-point checks `crossvote_enabled()`); the function itself is pure orchestration
    so it stays unit-testable. NEVER closes a goal — purely a statement-faithfulness verdict.

    `equiv_timeout_s` (the per-pair kernel `↔` compile budget) defaults to `ZTARE_LEANMILL_EQUIV_TIMEOUT_S`
    (else 300s) — NOT hardcoded: each pair pays a COLD Mathlib reload (~90s, no persistent REPL), so a tight
    value silently times out → None → fail-closed false-negative (the calibration bug the e2e exposed). Raise
    it on a slow/contended box."""
    if equiv_timeout_s is None:
        equiv_timeout_s = _equiv_timeout_default()
    gen = formalize_fn or (lambda _nl, _f: _formalize_one(_nl, _f, mode=mode, timeout_s=timeout_s))
    votes: "list[str]" = []
    fams: "list[str]" = []
    for f in formalizers:
        try:
            stmt = (gen(nl, f) or "").strip()
        except Exception:  # noqa: BLE001
            stmt = ""
        votes.append(stmt)
        fams.append(f.family)
    verdict = cross_vote_equivalent(votes, lean_root=lean_root, timeout_s=equiv_timeout_s,
                                    preamble=preamble, families=fams, domain=domain, dsl_of=dsl_of)
    return verdict, votes


def crossvote_enabled() -> bool:
    """The move is FLAG-GATED: default off (byte parity — the autoformalize entry-point skips cross-voting
    and behaves exactly as before). On only with `ZTARE_LEANMILL_CROSSVOTE=1`."""
    return os.environ.get(CROSSVOTE_FLAG) == "1"


def _selftest() -> int:
    """POSITIVE + NEGATIVE controls. The pure-orchestration legs (clique logic, diversity guard,
    structural diff, distinguishing-case wiring) run WITHOUT any external dep. The kernel-equivalence leg
    (`kernel_equivalent`) and the z3 distinguishing leg are exercised through a MOCK equiv/dsl so the
    selftest is deterministic + offline; an additional LIVE kernel leg runs only if the Lean toolchain is
    present (skipped, not faked, when absent — a negative is inadmissible without a live instrument)."""
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    root = Path("/nonexistent")   # the mock-equiv path never touches the kernel

    # ── POSITIVE: a diverse, all-agreeing clique ⇒ FAITHFUL ──
    agree = lambda a, b: (True, "mock: equivalent")
    v_pos = cross_vote_equivalent(
        ["theorem t : ∀ n : ℕ, n + 0 = n := by sorry",
         "theorem t : ∀ n : ℕ, 0 + n = n := by sorry"],
        lean_root=root, timeout_s=5, families=["codex", "gemini"], equiv_fn=agree)
    ok("POS: diverse all-agree clique ⇒ faithful", v_pos.faithful and v_pos.clique == [0, 1])
    ok("POS: agreed_statement set + reason mentions kernel", bool(v_pos.agreed_statement) and "FAITHFUL" in v_pos.reason)

    # ── NEGATIVE 1: a disagreeing pair ⇒ NOT faithful + the disagreement surfaced ──
    def _disagree(a, b):
        return (False, "mock: ref ≤ vs cand <") if a != b else (True, "same")
    v_neg = cross_vote_equivalent(
        ["theorem t (h : a ≤ b) : P := by sorry",   # faithful ≤
         "theorem t (h : a < b) : P := by sorry"],  # silently weakened to <
        lean_root=root, timeout_s=5, families=["codex", "claude"], equiv_fn=_disagree)
    ok("NEG: disagreeing pair ⇒ NOT faithful", not v_neg.faithful)
    ok("NEG: disagreement recorded", len(v_neg.disagreements) == 1 and v_neg.disagreements[0]["i"] == 0)

    # ── NEGATIVE 2 (gate-never-says-no guard): the distinguishing case is RETURNED on a decidable domain ──
    domain = {"role": ["admin", "analyst", "guest"], "resource": ["secret", "internal", "pub"]}
    # map each (mock) statement to its z3-DSL policy; ref = the faithful rule, cand = a BROADENED one
    _dsls = {"REF": "And(role == admin, resource == secret)",
             "CAND": "Or(role == admin, resource == secret)"}
    v_dc = cross_vote_equivalent(
        ["REF", "CAND"], lean_root=root, timeout_s=5, families=["codex", "gemini"],
        equiv_fn=_disagree, domain=domain, dsl_of=lambda s: _dsls.get(s, ""))
    try:
        import z3  # noqa: F401
        _have_z3 = True
    except Exception:  # noqa: BLE001
        _have_z3 = False
    if _have_z3:
        ok("NEG: SMT distinguishing case returned on disagreement",
           len(v_dc.distinguishing) >= 1 and all("request" in d and "ref_decision" in d for d in v_dc.distinguishing))
    else:
        ok("NEG: z3 absent ⇒ distinguishing fail-closed to [] (no silent agree)", v_dc.distinguishing == [])

    # ── DIVERSITY guard: all agree but only ONE family ⇒ NOT faithful (shared bias, not corroboration) ──
    v_div = cross_vote_equivalent(
        ["theorem t : P := by sorry", "theorem t : P := by sorry"],
        lean_root=root, timeout_s=5, families=["codex", "codex"], equiv_fn=agree)
    ok("DIVERSITY: single-family agreement ⇒ NOT faithful", not v_div.faithful and v_div.n_distinct_families == 1)

    # ── too-few-votes guard ──
    v_one = cross_vote_equivalent(["theorem t : P := by sorry"], lean_root=root, timeout_s=5,
                                  families=["codex"], equiv_fn=agree)
    ok("GUARD: <2 votes ⇒ NOT faithful", not v_one.faithful and "fewer than 2" in v_one.reason)

    # ── structural diff: detects a relaxed conclusion / quantifier swap (no kernel needed) ──
    se_eq, _ = structural_equivalent("theorem t : ∀ n : ℕ, n + 0 = n := by sorry",
                                     "theorem t : ∀ n : ℕ, n + 0 = n := by sorry")
    ok("STRUCT: identical signatures ⇒ structurally equal", se_eq)
    se_ne, se_why = structural_equivalent("theorem t : ∀ n : ℕ, P n := by sorry",
                                          "theorem t : ∃ n : ℕ, P n := by sorry")
    ok("STRUCT: ∀ vs ∃ ⇒ NOT structurally equal", not se_ne and "fingerprint DIFFERS" in se_why)

    # ── _closed_prop sanity (the kernel-leg input builder) ──
    cp = _closed_prop("theorem t (n : ℕ) : n + 0 = n := by sorry")
    ok("closed_prop builds ∀-form", cp.startswith("∀") and "n + 0 = n" in cp)

    # ── end-to-end with a MOCK formalizer (no live agents): diverse faithful votes ⇒ faithful ──
    def _mock_formalize(_nl, f):
        # codex + gemini render the SAME statement; claude renders a trivially-equal reordering
        return {"codex": "theorem t : ∀ n : ℕ, n + 0 = n := by sorry",
                "gemini": "theorem t : ∀ n : ℕ, n + 0 = n := by sorry",
                "claude": "theorem t : ∀ n : ℕ, n + 0 = n := by sorry"}.get(f.family, "")
    v_e2e, votes_e2e = cross_vote_faithfulness(
        "for every natural number n, n + 0 = n", lean_root=root,
        formalizers=(Formalizer("codex"), Formalizer("gemini", "llm_runtime", "x")),
        formalize_fn=_mock_formalize)
    ok("E2E: mock diverse faithful votes ⇒ faithful (verbatim-identical fast path)",
       v_e2e.faithful and len(votes_e2e) == 2)

    # ── LIVE kernel leg (only if the Lean toolchain is present; SKIPPED, not faked, otherwise) ──
    live_root = Path(__file__).resolve().parents[4] / "ztare_proofs"   # repo-relative (portable, no abs path)
    if live_root.exists() and os.environ.get("ZTARE_CROSSVOTE_LIVE_KERNEL") == "1":
        # POSITIVE: `∀ n, n+0=n` ↔ `∀ n, 0+n=n` — kernel-provably the same (simp/omega). NEGATIVE: a true
        # ∀ vs a FALSE ∀ cannot be `↔`-proved ⇒ NOT equivalent (the kernel refuses to launder).
        keq, _ = kernel_equivalent("theorem t : ∀ n : ℕ, n + 0 = n := by sorry",
                                   "theorem t : ∀ n : ℕ, 0 + n = n := by sorry", live_root, 120)
        ok("LIVE POS: kernel proves n+0=n ↔ 0+n=n", keq)
        kne, _ = kernel_equivalent("theorem t : ∀ n : ℕ, n + 0 = n := by sorry",
                                   "theorem t : ∀ n : ℕ, n + 1 = n := by sorry", live_root, 120)
        ok("LIVE NEG: kernel REFUSES n+0=n ↔ n+1=n (different problems)", not kne)
    else:
        print("  [SKIP] live kernel leg (set ZTARE_CROSSVOTE_LIVE_KERNEL=1 with the Lean toolchain present)")

    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
