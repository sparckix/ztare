"""Autonomous deanchor → isomorphism → transport → AUDIT decomposition loop (the operator's 4-step
design, 2026-06-05). The solver attacks a HARD target by structurally analogizing to a field where the
pattern is solved, emitting an intermediate lemma DAG of TYPED `sorry` signatures, and — crucially —
governance AUDITS the DAG (compiles + chains to the goal + non-circular + load-bearing) BEFORE the leaf
spends any effort. Composition of EXISTING primitives (no frankenstein):
  Step 1 deanchor/abstract  — strip comments + recognizable names + a banned-terms gate (the
                              is_contaminated concept) so the leaf retrieves STRUCTURE, not a memorized
                              named result. (Heavier ConstraintFingerprint is the RD's research-seam
                              tool; this is the lighter solver-target deanchor.)
  Step 2 isomorphism search — folded into the deanchored decompose prompt (the leaf reasons to the
                              solved-neighbor field). [v2: wire IsomorphismLoop explicitly.]
  Step 3 transport→DAG      — one leaf dispatch → typed Lean `sorry` lemma signatures + a chain-proof.
  Step 4 Meta-Darwin AUDIT  — `conjecture.decomposition_dag_audit` (kill ill-typed/circular/vacuous).
Output: an AUDITED decomposition (sound, non-circular, load-bearing) whose lemmas the EXISTING solver
(`solve_adhoc`) then proves — OR a `killed` verdict (the decomposition is rejected, no leaf spent).

NON-IATROGENIC by construction: the audit (Step 4, calibrated 6/6) rejects the laundered/circular/
vacuous decompositions that would otherwise manufacture fake lift; the lemmas are proved by the
unchanged kernel-gated solver. The loop never closes the goal — it produces a sound sub-goal DAG."""
from __future__ import annotations
import json
import re
from pathlib import Path

import os
from dataclasses import dataclass

from ztare.leanmill.solver.statement_integrity import decl_blocks as _decl_blocks, _signature
from ztare.leanmill.solver.conjecture import decomposition_dag_audit, _lemma_conclusion, _norm_ws
from ztare.common.refine_handover import RefineHandover
# v2 (2026-06-06): wire Step 2 (isomorphism search) to the CANONICAL engine instead of folding it into
# the prompt. `ztare.common.constraint_isomorphism` is the ONE isomorphism engine (the RD's
# research_isomorphism plugs the same engine via a different domain) — reusing it here de-frankensteins
# the parallel "reason about which field" prompt that previously never touched the engine.
from ztare.common.constraint_isomorphism import (
    ConstraintFingerprint, IsomorphismLoop, SurfacedIsomorphism, default_llm_query)


@dataclass
class _DagVerdict:
    accepted: bool
    reason: str
    detail: dict


class _DecomposeDomain:
    """Minimal `StrangeLoopDomain` plug so Step 2 runs through the canonical `IsomorphismLoop` (NOT a
    parallel). Step 1 = fingerprint the deanchored goal (home field forbidden → DEANCHOR direction);
    verification is the downstream `decomposition_dag_audit` (kernel), NOT a holdout oracle, so the
    oracle is advisory (mirrors research_isomorphism's honest 'a transport is verified by an experiment,
    not a cheap score')."""

    def __init__(self, banned: "list[str] | None" = None, home_field: "str | None" = None):
        self._banned = [t for t in (banned or []) if t]
        self._home = home_field

    def abstract_failure(self, fs: dict) -> ConstraintFingerprint:
        return ConstraintFingerprint(
            constraint_class=fs.get("constraint_class", "an open Lean proof obligation"),
            abstract_form=fs.get("abstract_form", ""),
            invariants={}, forbidden_domain=fs.get("home_field", self._home))

    def compile_to_test(self, iso: SurfacedIsomorphism, context: object) -> SurfacedIsomorphism:
        return iso  # the DAG audit is the real test; surfacing only

    def oracle(self, gate, holdout) -> float:
        return 0.0  # advisory: a transported decomposition is verified by the kernel audit, not a score

    def banned_terms(self) -> "list[str]":
        return self._banned


def surface_field_analogies(goal_concl: str, goal_decl: str, *, banned_terms=None, n: int = 3,
                            query=None) -> "list[SurfacedIsomorphism]":
    """Step 2 via the CANONICAL engine: fingerprint the (deanchored) goal and surface up to `n`
    cross-field structural matches with `IsomorphismLoop`. Returns [] gracefully on any error / no key
    (the caller then falls back to the leaf reasoning about the field itself). `query` defaults to the
    shared `default_llm_query` (gemini); inject a mock in tests."""
    try:
        dom = _DecomposeDomain(banned_terms)
        fp = dom.abstract_failure({"constraint_class": goal_concl or "an open Lean proof obligation",
                                   "abstract_form": goal_decl or goal_concl})
        return IsomorphismLoop(dom, query=query or default_llm_query).query(fp, n) or []
    except Exception:  # noqa: BLE001 — surfacing is best-effort; absence ⇒ fall back, never break attack
        return []


def _render_iso_hints(isos: "list[SurfacedIsomorphism]") -> str:
    if not isos:
        return ""
    lines = "; ".join(f"{i.field}: {i.mechanism}" + (f" (maps via {i.mapping_hint})" if i.mapping_hint else "")
                      for i in isos[:4] if getattr(i, "field", None))
    return lines


# ── Transportable-attack catalog — the "exogenous-technique library" (the gap the GPT-5.5 unit-distance / sum–product
# results exposed: those proofs TRANSPORT a powerful technique from a field where the structure is solved —
# orthogonality / the polynomial method). The cross-field LLM query (`surface_field_analogies`) returned
# EMPTY on P1, so the engine surfaced no attack vector and the leaf flailed/gamed the rung. This catalog is
# a curated PRIOR of high-leverage, MECHANISM-named, DOMAIN-GENERAL transportable proof techniques injected
# into the deanchor query so the leaf TRANSPORTS a named attack instead of guessing. Domain-general (no
# Lean / target vocabulary) ⇒ does not violate the deanchor no-leak rule; the audit + kernel still gate
# soundness, so a transported-but-wrong attack fails HONESTLY (never launders). `ZTARE_ISO_TECHNIQUES=0`
# disables. Substrate-agnostic content ⇒ a candidate to promote into `common/constraint_isomorphism`. ──
TRANSPORTABLE_TECHNIQUES = (
    ("orthogonality / polynomial method",
     "bound or rule out a configuration by exhibiting its objects as (near-)orthogonal vectors or a "
     "low-rank tensor decomposition — slice rank / Croot–Lev–Pach / the polynomial method "
     "(cap-set, sum–product, unit-distance, Kakeya)"),
    ("globally-bounded ODE solution ⇒ algebraic",
     "a power series satisfying an algebraic/linear ODE whose coefficients are arithmetically bounded "
     "(globally bounded) is ALGEBRAIC (the G-function circle, André–Chudnovsky–Katz); the engine is p-adic "
     "differential equations + the Frobenius structure across primes — an orthogonality argument over ℚ_p"),
    ("automaticity / diagonal ⇒ algebraic",
     "a generating function with p-automatic coefficients, or a diagonal of a rational function, is "
     "algebraic over 𝔽_p(t) (Christol's theorem / the transfer-matrix method); a finite Myhill–Nerode "
     "prefix-equivalence (finite state) is the rigidity that forces the algebraic relation"),
    ("finite Hankel rank ⇒ rational (Kronecker)",
     "a power series / sequence has a RATIONAL generating function IFF its Hankel matrix has FINITE RANK "
     "(Kronecker's theorem; equivalently a finite linear recurrence / a finite-dimensional LTI state "
     "realization) — bounded local data forces a finite-dimensional realization; the constructive criterion "
     "for the RATIONAL sub-case of algebraicity (a clean SPECIALIZE rung when full algebraicity is out of reach)"),
    ("obstruction-descent (boundedness kills the obstruction class)",
     "compute the LOCAL OBSTRUCTION CLASS to the desired descent (a residue, a log/monodromy term, a Chern/"
     "winding number, a stretch factor), show the GLOBAL boundedness/integrality hypothesis forces it to "
     "VANISH, then DESCEND to the rigid object (rational/algebraic/trivializable). One meta-move across "
     "fields: vanishing residues ⇒ rational antiderivative; Dirac quantization; BIBO stability (no poles on "
     "the boundary — a residue there generates secular/log growth); Wannier localization ⇒ trivial Chern "
     "class. Surfaced by deanchored isomorphism search 2026-06-12 — five independent fields, one argument"),
    ("transport of structure across an isomorphism (prove-once-get-iso-free)",
     "when the goal is an instance of a fact already true for an ISOMORPHIC structure, TRANSPORT it instead of "
     "re-proving: exhibit the iso (a Mathlib `Equiv` / `MulEquiv` / `RingEquiv` / `OrderIso`, or the additive↔"
     "multiplicative `to_additive` duality) and push the known statement across it (`Equiv.forall_congr`, "
     "`MulEquiv.map_*`, congruence / `simp only [e.map_…]`, or cite the `to_additive`-generated sibling lemma). "
     "Lean-INTERNAL transport — no exogenous compute; the kernel re-checks the transported term, so a wrong "
     "iso just fails to compile. The cleanest SPECIALIZE/GENERALIZE rung when a sibling structure already has "
     "the lemma (Pontryagin/Fourier duality, op-ring / `mul_opposite`, completion, quotient-vs-section)"),
    ("spectral gap / eigenvalue separation",
     "bound a combinatorial or dynamical quantity by the second eigenvalue (expander mixing, Cheeger)"),
    ("duality certificate (LP/SDP)",
     "prove an extremal bound by exhibiting the DUAL feasible certificate (LP/SDP duality, the dual witness)"),
    ("compactness ⇒ uniformity",
     "upgrade a pointwise/local bound to a uniform/global one via a compactness or limiting argument"),
    ("probabilistic existence",
     "prove existence via a positive-probability / first-moment / Lovász-local-lemma argument"),
)


def _render_techniques(k: int = 6) -> str:
    """Render the top transportable-attack techniques as a domain-general prior for the deanchor prompt.
    k=6 (2026-06-13): admits TRANSPORT-OF-STRUCTURE (edge #4 — the Lean-internal Equiv/to_additive
    prove-once-get-iso-free move) alongside OBSTRUCTION-DESCENT (2026-06-12), without demoting the four
    P1-relevant domain priors above them."""
    if os.environ.get("ZTARE_ISO_TECHNIQUES") == "0":
        return ""
    return " || ".join(f"[{name}] {how}" for name, how in TRANSPORTABLE_TECHNIQUES[:k])


def _resolve_iso_catalog(have_dynamic: bool, dynamic_primary: bool, has_techniques: bool) -> "tuple[bool, str]":
    """Decide whether to inject the STATIC transportable-attack catalog, and the iso_source telemetry tag.
    Returns (inject_static, source ∈ {dynamic, static, both, none}). The DEFAULT (dynamic_primary=False) ALWAYS
    injects the static prior when available — byte-identical parity with the pre-feature behaviour. Under
    dynamic_primary the static prior is SHRUNK to a fallback: suppressed once the per-target live engine has
    surfaced hints (redundant), kept only when dynamic is empty. Pure (no env / IO) so it is unit-testable."""
    if dynamic_primary and have_dynamic:
        return False, "dynamic"
    if not has_techniques:
        return False, ("dynamic" if have_dynamic else "none")
    return True, ("both" if have_dynamic else "static")

from ztare.leanmill.solver.prompts import (DEANCHOR_PROMPT as _DEANCHOR_PROMPT,  # canonical prompts home (#49; moved verbatim)
                                           ISO_PLANNER_WARMCHECK_BLOCK as _WARMCHECK_TEMPLATE)


# AGENT-ORCHESTRATED PLANNING (#74, `ZTARE_LEANMILL_AGENT_PLAN`, default-off = byte-parity). The planner today
# HARDCODES decompose (this prompt forces a DECOMP DAG). The agent's real planning catalogue is richer — the
# structural moves {decompose, specialize, generalize, falsify, abduce, transport} + solve-direct, each with an
# EXISTING executor (conjecture/specialize/falsify/generalize_generate, abduce_seed). STEP 1 surfaced the CHOICE
# to the agent + recorded it (telemetry). STEP 2 (#74 finish): the agent's chosen action now DRIVES the artifact
# it produces — the plan prefix asks for the action-appropriate proves-G DAG (SPECIALIZE→stronger B, GENERALIZE→
# general H, ABDUCE→premise A, TRANSPORT→exogenous fact, DECOMPOSE→sub-lemmas), ALL gated by the SAME kernel
# decomposition audit (sorry-free + non-circular + load-bearing + proves-G). The agent IS the planner — ONE
# unified DAG producer, action-parameterized (NOT a forked executor path). Default-OFF (ZTARE_LEANMILL_AGENT_PLAN)
# = byte-parity decompose-only until the live lift test promotes it.
_PLAN_ACTIONS = {
    "DECOMPOSE": "break G into sub-lemmas L₁…Lₙ whose conjunction implies G (the current path)",
    "SOLVE_DIRECT": "G is within reach — prove it directly, no decomposition",
    "SPECIALIZE": "prove a STRONGER explicit statement B that implies G",
    "GENERALIZE": "prove a MORE GENERAL lemma H of which G is an instance",
    "FALSIFY": "G looks FALSE — pursue a kernel-checked proof of ¬G instead",
    "ABDUCE": "G needs a missing PREMISE A (A ∧ context ⇒ G) — supply it",
    "TRANSPORT": "bring exogenous compute (a witness / hammer / cross-substrate) to G",
}
# The DAG-artifact format each PROVES-G action injects (data, not hard-coded prose — so surfacing a SUBSET
# also trims the format guidance). FALSIFY / SOLVE_DIRECT carry no proves-G DAG ⇒ absent here by design.
_PLAN_DAG_FORMAT = {
    "DECOMPOSE": "the intermediate sub-lemmas L₁…Lₙ, chain proves G from them.",
    "SPECIALIZE": "FIRST lemma = the STRONGER statement B; chain proves G from B.",
    "GENERALIZE": "FIRST lemma = the MORE GENERAL H; chain instantiates G from H.",
    "ABDUCE": "FIRST lemma = the missing PREMISE A; chain proves G from A + the goal's context.",
    "TRANSPORT": "FIRST lemma = the exogenous-compute fact (a witness / hammered premise); chain closes G with it.",
}
# SITUATION → applicable move SUBSET (the epistemic-generation "mechanization-placement" discipline: route the
# moves that EARN their place for THIS situation, do NOT dump the whole catalogue as prompt ballast). Tunable:
# a caller may pass `enable`/`disable` to `_plan_choice_prefix`. `proof_stuck` (default) = the full menu
# (byte-parity with the prior always-dump). New situations surface a disciplined subset.
_SITUATION_ACTIONS = {
    "proof_stuck": list(_PLAN_ACTIONS.keys()),               # admitted goal, choose how to prove it (default)
    "target_weakened": ["ABDUCE", "DECOMPOSE", "SPECIALIZE"],  # firewall rejected: agent assumed a hypothesis
}


def _agent_plan_on() -> bool:
    # DEFAULT-ON (operator 2026-06-10): the agent ORCHESTRATES the structural action (decompose / specialize /
    # generalize / abduce / TRANSPORT) — declares PLAN: <ACTION> and produces the action-appropriate, kernel-
    # audited DAG — rather than the planner hardcoding decompose. =0 opts out (the byte-parity decompose-only arm
    # for A/B). Pairs with ZTARE_LEANMILL_AGENT_TOOLS (also default-on) so TRANSPORT can reach the exogenous tools.
    return os.environ.get("ZTARE_LEANMILL_AGENT_PLAN", "1") != "0"


def _plan_research_moves(goal: str = "") -> str:
    """The 'lever deeper' (operator 2026-06-20): surface the goal-ranked RESEARCH moves (named mathematician
    moves + transport attacks + structural moves) from the UNIFIED `move_corpus`, via the semantic `move_atlas`,
    so the planner's structural-action choice is informed by the math catalogue — NOT a parallel surface, the
    SAME corpus the leaf sees. Graceful: any failure / empty ⇒ '' (the planner keeps the static technique prior
    below). Domain-general content ⇒ respects the deanchor no-leak discipline."""
    if not (goal or "").strip():
        return ""   # goal-CONDITIONED: no goal ⇒ no ranking ⇒ no ballast (keeps the situation-subset clean)
    try:
        from ztare.leanmill.solver import move_atlas as _ma
        return _ma.render_research_moves_for_goal(goal, k=8)
    except Exception:  # noqa: BLE001 — additive; never break planning
        return ""


def _plan_choice_prefix(situation: str = "proof_stuck", *, enable=None, disable=None, goal: str = "") -> str:
    """Render the PLAN-choice prompt with the move SUBSET applicable to `situation` — the epistemic-generation
    'mechanization-placement' discipline (route the moves that earn their place for THIS situation, do NOT dump
    the whole catalogue as prompt ballast). `proof_stuck` (default) = the full menu (byte-parity with the prior
    always-dump). `enable`/`disable` tune the subset per call (configurable). Data-driven from `_PLAN_ACTIONS`
    + `_PLAN_DAG_FORMAT` + `_SITUATION_ACTIONS` — surfacing a subset trims BOTH the option list and the format
    guidance, automatically."""
    names = list(_SITUATION_ACTIONS.get(situation, list(_PLAN_ACTIONS.keys())))
    for n in (enable or []):
        if n in _PLAN_ACTIONS and n not in names:
            names.append(n)
    _dis = set(disable or [])
    names = [n for n in names if n in _PLAN_ACTIONS and n not in _dis]
    opts = "\n".join(f"  {a}: {_PLAN_ACTIONS[a]}" for a in names)
    dag_bullets = "".join(f"  • {a:<11} → {_PLAN_DAG_FORMAT[a]}\n" for a in names if a in _PLAN_DAG_FORMAT)
    nodag = [a for a in ("SOLVE_DIRECT", "FALSIFY") if a in names]
    tail = ""
    if nodag:
        tail = (f"({' and '.join(nodag)} do NOT fit a proves-G DAG. If genuinely your best move, "
                "declare it on the PLAN line and STOP — produce NO DAG; do NOT fabricate sub-lemmas to satisfy "
                "the format. The harness then routes the goal to the cascade, which carries BOTH a direct-proof "
                "path (SOLVE_DIRECT) and a refutation/¬G move (FALSIFY). Only pick a DAG action above when a "
                "genuine reduction exists. The format serves the proof — never the reverse.)\n")
    research = _plan_research_moves(goal)   # the math catalogue + transport attacks, goal-ranked (lever deeper)
    # WHY_NOT_DIRECT discipline (2026-07-05 CLOB "decompose-forever, 0 closes" RCA): the agent reflexively splits
    # because a sound reduction is easy to find at every level — so it never GRINDS a reachable leaf. Force it to
    # default to SOLVE_DIRECT and justify any decompose. Only surfaced when SOLVE_DIRECT is actually offered (the
    # full `proof_stuck` menu); on the `target_weakened` recourse subset decomposition IS the point, so it stays off
    # (also keeps the subset ballast-free — the selftest asserts no out-of-subset action names leak into the prompt).
    direct_discipline = ""
    if "SOLVE_DIRECT" in names:
        direct_discipline = (
            "\n\nYOU ARE A FRONTIER PROVER — DEFAULT TO SOLVE_DIRECT. Attempt the full proof yourself; splitting is "
            "a LAST RESORT. A sound reduction is easy to find at every level — that is the trap: decomposing forever "
            "closes nothing. If you choose any decomposing action you MUST append to the PLAN line `; WHY_NOT_DIRECT: "
            "<the ONE concrete obstruction that makes proving G directly infeasible RIGHT NOW — a specific missing "
            "lemma, a genuinely hard induction, an unavailable Mathlib result>`. If you cannot name a concrete "
            "obstruction — a membership/subset/monotonicity/`filter` fact, a one-branch case split, anything a "
            "careful proof would just DO — the leaf is within reach: choose SOLVE_DIRECT and PROVE IT.\n")
    return ("FIRST, choose the single best STRUCTURAL ACTION for this goal and state it on ONE line as "
            "`PLAN: <ACTION> — <one-line reason>`, where <ACTION> is EXACTLY one of:\n" + opts + direct_discipline +
            "\nThen PRODUCE THE ARTIFACT FOR YOUR CHOSEN ACTION in the DECOMP format below — a sub-lemma DAG "
            "whose sorry-free chain proves the goal G. The SAME kernel audit (sorry-free + non-circular + "
            "every-lemma-load-bearing + proves-G) gates every action, so your CHOICE drives WHICH artifact you "
            "build (this IS the dispatch — it is no longer recorded-and-ignored):\n" + dag_bullets + tail +
            (research + "\n" if research.strip() else "") +
            "Optionally also declare `BUDGET: <seconds>` — the wallclock you want for your NEXT refinement "
            "round (granted up to a hard cap; omit to keep the default).\n\n")


def parse_plan_action(raw: str) -> "tuple[str, str]":
    """The agent's declared structural action (default DECOMPOSE if absent/unrecognized). Uses the SHARED
    `leanmill.solver.agent_output.labeled_value` — not a per-caller regex (the consolidation of the ad-hoc parsers)."""
    from ztare.leanmill.solver.agent_output import labeled_value
    return labeled_value(raw, "PLAN", allowed=tuple(_PLAN_ACTIONS), default="DECOMPOSE")


def _record_plan_choice(action: str, reason: str, target: str = "") -> None:
    """Best-effort telemetry (#74 step 1): persist the agent's declared PLAN action so we can MEASURE — across
    runs — whether the agent actually wants moves beyond DECOMPOSE. That data gates building the heterogeneous
    step-2 dispatch (don't wire executors the agent never elects). Append-only JSONL, never fails the solve."""
    try:
        import json
        from pathlib import Path
        p = Path(__file__).resolve().parents[4] / "analytics" / "public" / "queries" / "solver_lane_plan_choices.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"action": action, "reason": (reason or "")[:200],
                                "target": (target or "")[:120]}, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 — telemetry is best-effort; never break the solve
        pass


def deanchor(source: str, target_name: str, banned_terms: "list[str] | None" = None) -> "tuple[str, str, str, str]":
    """Step 1: (preamble, goal_decl, goal_conclusion, ban_clause). Strips comments (the framing anchor)
    and builds a banned-terms clause so the leaf can't cite a memorized named result. Local decl names
    are left intact (renaming them reversibly is a v2 refinement); comment-strip + name-ban + the
    'treat as abstract' instruction carry the deanchor for v1."""
    from ztare.leanmill.lean_source import (blank_comments as _bc, preamble_before_target as _preamble)
    nocomment = _bc(source)   # offset/newline-preserving so `^theorem` anchor + decl spans stay valid
    blocks = dict(_decl_blocks(nocomment))
    goal_decl = next((blocks[n] for n in blocks if n == target_name or n.endswith("." + target_name)), "")
    preamble = _preamble(nocomment, target_name)
    sig = _signature(goal_decl)
    j = sig.find(":") if ":" not in (target_name) else -1
    goal_concl = _lemma_conclusion(goal_decl)
    ban = ""
    if banned_terms:
        ban = " Do NOT mention or cite any of: " + ", ".join(t for t in banned_terms if t) + "."
    return preamble, goal_decl, goal_concl, ban


def _parse_dag(raw: str, prefix: str) -> "tuple[list[str], str, list[str]]":
    """Parse DECOMP: fenced block → (sorried lemma blocks, chain block, lemma names). The chain is the
    block whose body is NOT `:= by sorry` (it proves the goal); the rest are the sorried lemmas.

    Block extraction = the CANONICAL `statement_integrity.decl_blocks` (#49 — "no module may regex Lean
    structure on its own"). This is a behaviour-FIX over the prior ad-hoc theorem-regex, whose differential
    (2026-06-12) exposed two latent COMPLETENESS bugs: (1) a helper `def` between sorried lemmas was absorbed
    into the prior theorem's block, breaking the sorry-check → the lemma was SILENTLY DROPPED; (2) comments
    were not blanked, so `-- theorem fake : … := by sorry` became a PHANTOM lemma. decl_blocks fixes both
    (comment-blanked decl detection, per-decl boundaries). Non-theorem decls (def/abbrev/…) are scaffold —
    kept OUT of the lemma/chain classification, exactly as intended."""
    from ztare.leanmill.solver.agent_output import fenced_block  # canonical fence extractor (#80/#49); was a local _fenced-pattern regex
    from ztare.leanmill.solver.statement_integrity import _DECL_START  # the ONE decl-start pattern (no re-rolled regex)
    body = fenced_block(raw, "DECOMP:", lang="lean") or raw   # the DECOMP fence; fall back to scanning the whole output if absent
    def _is_thm(blk: str) -> bool:
        m = _DECL_START.match(blk)
        return bool(m and m.group(1) in ("theorem", "lemma"))
    from ztare.leanmill.solver.statement_integrity import _strip_comments as _sc_dag  # 2026-06-13 audit
    thms = [(blk, nm) for nm, blk in _decl_blocks(body) if _is_thm(blk)]
    lemmas, names, chain = [], [], ""
    for block, name in thms:
        b = block.strip()
        # CLASSIFY on a COMMENT-STRIPPED copy (a `sorry` in a trailing comment that `decl_blocks` glued onto
        # this block must NOT misclassify a sorry-free chain as a sorried lemma — the autoformalize_notes bug
        # class). The RAW `b` is kept for downstream use (lemmas/chain text); only the test reads the stripped.
        bnc = _sc_dag(b)
        if re.search(r":=\s*by\s+sorry\s*$", bnc.strip()) or (":= by sorry" in bnc and "sorry" in bnc.split(":=")[-1] and "\n" not in bnc.split(":= by")[-1].strip()):
            lemmas.append(b); names.append(name)
        elif "sorry" not in bnc.split(":=", 1)[-1]:
            chain = b           # the sorry-free chain proof
    # fallback: the last block is the chain if none classified
    if not chain and thms:
        chain = thms[-1][0].strip()
        if chain in lemmas:
            i = lemmas.index(chain); lemmas.pop(i); names.pop(i)
    # GUARD: reject a verbatim TEMPLATE ECHO — the agent returned the prompt scaffold instead of real Lean
    # (P1 RUNG-A 2026-06-11: it echoed `<statement>` / `<tactics …; NO sorry>`, and the literal "NO sorry" then
    # tripped the audit's sorry check → a MISLEADING "chain not sorry-free" kill that MASKED the real failure
    # "the agent didn't decompose"). A `<word>` placeholder in any block ⇒ NOT a decomposition; return empty so
    # the route reports it honestly (empty decomposition) rather than a confusing sorry kill.
    if re.search(r"<\s*(?:statement|tactics|term|proof|expr|goal|hypoth|lemma|fill|your|the)\b",
                 "\n".join(lemmas) + "\n" + chain, re.I):
        return [], "", []
    return lemmas, chain, names


# ── Parallel diverse decomposition sampling (2026-06-07) ──────────────────────────────────────────
# The `attack` loop is SEQUENTIAL: generate one decomposition → audit → (targeted-)refine on a kill. That is
# a depth search on ONE attack structure. Sampling adds a BREADTH leg: generate K decompositions priming K
# DISTINCT transportable techniques, AUDIT all, pursue the survivors. FORMAL DOMINANCE: the audit
# (`decomposition_dag_audit`) is a SOUND filter — an accepted DAG is genuinely sorry-free / non-circular /
# load-bearing, never laundered — so best-of-K weakly dominates best-of-1 on P(≥1 sound): K independent
# samples can only RAISE the chance one passes, at K× the generate cost. Diversity (distinct primed
# structures, not K stochastic redraws of the same prompt) is what makes the K attacks genuinely independent,
# so the dominance is non-trivial. The two legs COMPOSE: if no sample audits, the best near-miss seeds the
# refine loop (explore K structures, then fix the most-sound one). Default ZTARE_ISO_SAMPLES=1 ⇒ the sampling
# branch is skipped entirely (byte-identical single-shot). K is the A/B knob (cost-normalized lift vs K=1).

def _diversity_seed(i: int) -> str:
    """Per-sample priming for diverse sampling: rotate the EMPHASIZED transportable technique so the K samples
    explore DISTINCT attack structures. Sample 0 is UN-primed (the base prompt's natural best-fit) ⇒ K=1 is
    byte-identical to the single-shot; i≥1 rotates over TRANSPORTABLE_TECHNIQUES. Domain-general (no target
    vocabulary) ⇒ no deanchor leak; the audit still gates soundness, so a forced/ill-fitting prime fails
    honestly rather than laundering."""
    if i <= 0 or not TRANSPORTABLE_TECHNIQUES:
        return ""
    name, how = TRANSPORTABLE_TECHNIQUES[(i - 1) % len(TRANSPORTABLE_TECHNIQUES)]
    return (f" For THIS attempt SPECIFICALLY, lead with the [{name}] attack structure ({how}) IF it can be "
            "made to fit — do NOT force it; a genuine reduction via another route still beats a forced fit.")


def _sample_diverse(k: int, generate, verify, base_ctx: dict):
    """Generate `k` technique-diverse decompositions, AUDIT each, return (audited, attempts):
    audited = [(art, verdict)] that PASSED the sound audit; attempts = all (art, verdict) in order. `generate`
    and `verify` are injected (the attack closures) so this is unit-testable with fakes — no dispatch/Lean.

    PARALLEL GENERATION (#117; ZTARE_ISO_SAMPLES_PARALLEL default-on, =0 reverts to sequential): the K
    planner dispatches are independent LLM calls, so generation wall ≈ 1× planner budget instead of K×.
    Two designed properties: (a) CONCURRENCY-SAFETY — samples i≥1 carry `agent_tag="iso_s<i>"`, keying
    their OWN durable sessions (no collision on the one repo-scoped session resume; sample 0 keeps the
    warm campaign session = single-shot parity; tagged slots stay warm across rounds). (b) INDEPENDENCE —
    sequentially, every sample RESUMED the shared session, so later samples saw earlier samples' context:
    correlated draws, quietly weakening the best-of-K dominance argument. Per-sample sessions make the K
    draws genuinely independent. VERIFY (the audit — Lean compiles) stays SERIAL in sample order: the
    no-parallel-Lean rule + deterministic selection. K=1 (default) never enters the parallel branch."""
    k = max(1, int(k))
    ctxs = []
    for i in range(k):
        ctx = dict(base_ctx or {})
        ctx["feedback"] = (base_ctx or {}).get("feedback", "") + _diversity_seed(i)
        if i:
            ctx["agent_tag"] = f"iso_s{i}"
        ctxs.append(ctx)
    audited, attempts = [], []
    if k > 1 and os.environ.get("ZTARE_ISO_SAMPLES_PARALLEL", "1") != "0":
        from contextvars import copy_context
        from ztare.common.work_plan import fanout, run as wp_run

        def _gen_safe(lane_idx: int):
            ctx = ctxs[lane_idx]
            try:
                return copy_context().run(generate, ctx)
            except Exception as e:  # noqa: BLE001 — one failed sample must not sink the round
                return {"lemmas": [], "chain": "", "lnames": [], "raw": f"sample dispatch error: {e!r}"}

        # ponytail: fanout/collect — generate is pure fan-out (K independent LLM calls);
        # collect returns all in lane-index order (= ctxs order). VERIFY stays serial.
        workers = max(1, min(k, int(os.environ.get("ZTARE_ISO_SAMPLES_WORKERS", "3") or 3)))
        plan = fanout(
            _gen_safe,
            K=k,
            diversify=lambda i: i,
            merge={"kind": "collect"},
        )
        arts = wp_run(plan, max_workers=workers)
        for art in arts:                              # SERIAL audit in sample order
            v = verify(art)
            attempts.append((art, v))
            if getattr(v, "accepted", False):
                audited.append((art, v))
        return audited, attempts
    for ctx in ctxs:                                  # sequential: original interleaved order preserved
        art = generate(ctx)
        v = verify(art)
        attempts.append((art, v))
        if getattr(v, "accepted", False):
            audited.append((art, v))
    return audited, attempts


def _richest(pairs):
    """The (art, verdict) whose decomposition has the MOST lemmas — the richest blueprint among survivors (or
    the best near-miss among attempts). Ties resolve to the first (stable)."""
    return max(pairs, key=lambda av: len(av[0].get("lemmas") or []))


def _planner_semantic_shelf_on() -> bool:
    # DEFAULT-ON A/B knob (the embedding-premise-steering twin of ZTARE_LEANMILL_RUNG_ADJACENCY): =0 ⇒
    # byte-parity (the block is empty, the planner sees only the LEXICAL rung_adjacency advisory it saw
    # before). Mirrors `rung_adjacency.enabled()`.
    return os.environ.get("ZTARE_LEANMILL_PLANNER_SEMANTIC_SHELF", "1") != "0"


def _render_semantic_shelf_block(goal: str, *, top_k: int = 4) -> str:
    """EMBEDDING-based premise steering for the PLANNER (#semantic-shelf): surface the OWN-LEDGER banked
    lemmas most COSINE-SIMILAR to the goal — the semantic complement to the LEXICAL `rung_adjacency`
    advisory (identifier-overlap). A lemma can be the right attachment site yet share NO surface tokens
    with the goal; embedding retrieval names it where token-overlap is blind.

    REUSES `semantic_premise_shelf.own_ledger_hits` + `_cached_embedder` (the SAME retrieval the LEAF
    already gets) — no re-rolled retrieval, no re-rolled embedding. ADVISORY only: the kernel audits every
    cited/decomposed lemma, so this can never launder; it does NOT force or pin any lemma. Default-on with
    `ZTARE_LEANMILL_PLANNER_SEMANTIC_SHELF` (=0 ⇒ '' = byte-parity). Graceful-degrade to '' on ANY
    embedder/import failure (no GOOGLE_API_KEY, offline, empty ledger) — never breaks prompt assembly."""
    if not _planner_semantic_shelf_on() or not (goal or "").strip():
        return ""
    try:
        from ztare.leanmill import semantic_premise_shelf as _sps
        hits, _size, _skip = _sps.own_ledger_hits(
            goal, embedder=_sps._cached_embedder(), top_k=top_k)
        # PROVEN rungs only — the steer is "decompose/cite TOWARD these kernel-closed lemmas". (The shelf
        # also returns open-gap diagnoses; those are a leaf concern, not a planner attachment site.)
        lines = [f"  • {h.get('name') or '?'} : {' '.join(str(h.get('preview') or '').split())[:160]}"
                 for h in hits if isinstance(h, dict) and h.get("kind") == "proven_rung"]
        if not lines:
            return ""
        return ("SEMANTICALLY-RELATED PROVEN LEMMAS (kernel-closed; consider citing/decomposing toward "
                "these — embedding-retrieved, so relevant even with NO shared surface tokens):\n"
                + "\n".join(lines) + "\n\n")
    except Exception:  # noqa: BLE001 — advisory; never break planner-prompt assembly
        return ""


class DecompositionCache:
    """`proof_cache` for DECOMPOSITIONS. Caches the agent's AUDITED DAG (lemmas + chain) per TARGET, keyed by the
    α/∀-invariant statement-hash the proof_cache/checkpoint use. WHY (the RBAC 'no reuse after hours' RCA,
    2026-07-05): the planner re-decomposes a STABLE target into DIFFERENTLY-named/stated sub-lemmas every run, so
    the rungs banked in run N are ORPHANED in run N+1 (a different split cites nothing banked) → each run
    re-formalizes + re-solves from scratch and the library never compounds. Reusing the FIRST audited DAG makes the
    decomposition CONVERGE, so its rungs (banked once) are cited on every later run — expert iteration needs STABLE
    sub-goals. NON-IATROGENIC (this is NOT the 'pin use-lemma-X-here' brittle determinism the arch doc warns
    against): it AMORTIZES the agent's decision (decided once, reused) EXACTLY as proof_cache amortizes a proof; it
    reuses a KERNEL-AUDITED artifact, not a mid-reasoning hint; the caller RE-AUDITS the cached DAG before use (a
    substrate change ⇒ the reused DAG simply fails the audit ⇒ falls through to a fresh plan); and the kernel
    ratifies every closure regardless. `ZTARE_LEANMILL_DECOMP_CACHE=0` reverts to per-run re-planning."""

    def __init__(self, path):
        self.path = Path(path)
        self._mem: dict = {}
        if self.path.exists():
            try:
                for line in self.path.read_text(encoding="utf-8").splitlines():
                    try:
                        r = json.loads(line)
                    except Exception:  # noqa: BLE001 — skip a garbled row, never fail the read
                        continue
                    if isinstance(r, dict) and r.get("key"):
                        self._mem[r["key"]] = r
            except Exception:  # noqa: BLE001
                pass

    def get(self, key: str) -> "dict | None":
        r = self._mem.get(key)
        if not r or not r.get("lemmas") or not (r.get("chain") or "").strip():
            return None
        return {"lemmas": r["lemmas"], "chain": r["chain"], "lnames": r.get("lnames") or []}

    def put(self, key: str, lemmas: list, chain: str, lnames: list) -> None:
        if not key or key in self._mem or not lemmas or not (chain or "").strip():
            return
        rec = {"key": key, "lemmas": lemmas, "chain": chain, "lnames": lnames}
        self._mem[key] = rec
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
        except Exception:  # noqa: BLE001 — cache persistence must never break the solve
            pass


def attack(source: str, target_name: str, *, lean_root: Path, timeout_s: int = 180,
           banned_terms: "list[str] | None" = None, dispatch_fn=None, max_refines: "int | None" = None,
           notes: "str | None" = None) -> dict:
    """Run the full loop on a hard target, with a BOUNDED refine cycle (reuses the canonical
    `RefineHandover` — no new loop machinery): on an audit-KILL, the kill reason is fed back and the
    leaf re-decomposes, until an audited DAG passes or `max_refines` (ZTARE_ISO_REFINES, default 2) is
    hit. Returns {audited, killed?, lemmas, chain, lnames, verdict, rounds, raw_tail, notes_used}.
    `audited=True` ⇒ a SOUND, non-circular, hypothesis-necessary decomposition the solver should now prove.
    `notes` (optional) = a human / research-director BLUEPRINT for this target, injected into the planner
    prompt as guidance (#81 uplevel); the kernel audit still gates soundness, so notes are advisory."""
    preamble, goal_decl, goal_concl, ban = deanchor(source, target_name, banned_terms)
    if not goal_decl or not goal_concl:
        return {"audited": False, "killed": f"could not locate target `{target_name}` in source"}
    sig = _signature(goal_decl)
    jc = sig.find(":")
    binders = sig[sig.find(target_name) + len(target_name):jc].strip() if jc > 0 else ""
    if dispatch_fn is None:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch as dispatch_fn
    if max_refines is None:
        max_refines = int(os.environ.get("ZTARE_ISO_REFINES", "2"))

    # Step 2 via the CANONICAL IsomorphismLoop (the v2 de-frankenstein): surface cross-field structural
    # matches ONCE (the goal's home field is forbidden → deanchor direction), and inject them so the leaf
    # TRANSPORTS a surfaced structure rather than guessing the field from scratch. Default-ON but graceful:
    # if the engine returns nothing (no key / off / error), `iso_step` falls back to the prior instruction,
    # so behaviour degrades to the folded-prompt version — never breaks. ZTARE_ISO_EXPLICIT_LOOP=0 disables.
    _iso_step = "Reason FIRST about which mathematical FIELD already solves this structural pattern, "
    _have_dynamic = False                       # did the per-target gemini engine surface real hints?
    if os.environ.get("ZTARE_ISO_EXPLICIT_LOOP", "1") != "0":
        _isos = surface_field_analogies(goal_concl, goal_decl, banned_terms=banned_terms, n=3)
        _hints = _render_iso_hints(_isos)
        if _hints:
            _iso_step = ("These STRUCTURES from other fields already solve this abstract pattern (surfaced "
                         f"by the cross-field isomorphism engine) — pick the best-fitting one and TRANSPORT it: {_hints}. ")
            _have_dynamic = True
    # STATIC CATALOG = a curated FALLBACK prior. Default (parity): ALWAYS injected — so even when the cross-
    # field engine surfaces nothing (no key / no match — the empty-on-P1 case), the leaf still has a NAMED
    # high-leverage attack to transport. Under ZTARE_LEANMILL_ISO_DYNAMIC_PRIMARY=1 the static list is SHRUNK
    # to a true fallback: skipped when the per-target dynamic engine already surfaced hints (the operator's
    # "why a static catalogue?" smell — the hand-curated prior is REDUNDANT once the live engine fires), kept
    # only as the fallback when dynamic is empty. The audit/kernel gate soundness either way.
    _dynamic_primary = os.environ.get("ZTARE_LEANMILL_ISO_DYNAMIC_PRIMARY") == "1"
    _techniques = _render_techniques()
    _inject_static, _iso_source = _resolve_iso_catalog(_have_dynamic, _dynamic_primary, bool(_techniques))
    if _inject_static:
        _iso_step += (" Among POWERFUL transportable techniques that crack structurally-similar problems, "
                      f"check whether ONE fits and transport it (do not force a fit): {_techniques}. ")

    # NOTES / BLUEPRINT CONTEXT (#81 uplevel): a target may arrive with a human / research-director blueprint
    # — notes that sketch the decomposition. Inject them into the planner prompt as GUIDANCE so the warm leaf
    # decomposes ALONG the blueprint rather than re-inventing it. Parity when `notes` is empty (no block →
    # byte-identical prompt). ADVISORY only: the KERNEL audit still gates every lemma, so a misleading note
    # cannot launder a closure — a wrong decomposition is killed exactly as a guessed one is.
    _notes_block = ""
    if notes and notes.strip():
        _notes_block = ("BLUEPRINT NOTES for this target (a human / research-director sketch of the "
                        "decomposition — use as GUIDANCE, do NOT restate the goal; the kernel still audits "
                        f"every lemma):\n{notes.strip()}\n\n")
    # RUNG-ADJACENCY ADVISORY (#121): name the kernel-closed attachment sites so the planner can decompose
    # TOWARD proven infrastructure (it still decides). Empty when nothing is proven (byte-parity); advisory
    # only — the kernel audit gates every lemma regardless. ZTARE_LEANMILL_RUNG_ADJACENCY=0 disables.
    try:
        from ztare.leanmill.solver import rung_adjacency as _radj_mod
        if _radj_mod.enabled():
            # pass the GOAL so the advisory names the proven rungs most RELEVANT to it (identifier-overlap), not
            # merely the most recent — the decomposition-steering that makes the planner attach to banked atoms.
            _notes_block = _radj_mod.render_adjacency_block(
                _radj_mod.proven_statements(), goal=(goal_concl or goal_decl or "")) + _notes_block
    except Exception:  # noqa: BLE001 — advisory; never break planner-prompt assembly
        pass

    # SEMANTIC-SHELF ADVISORY (embedding-based premise steering): COMPLEMENT the LEXICAL rung_adjacency
    # above with the OWN-LEDGER banked lemmas most COSINE-SIMILAR to the goal — so the planner can attach
    # to proven infrastructure that is semantically relevant even when it shares NO surface tokens (the gap
    # identifier-overlap is blind to). Same ONE injection point + same advisory contract as rung_adjacency;
    # reuses the LEAF's own retrieval (own_ledger_hits) — not a new surface. Empty when off / no API key /
    # nothing similar (byte-parity); the kernel audit gates every lemma regardless.
    try:
        _notes_block = _render_semantic_shelf_block(goal_concl or goal_decl or "") + _notes_block
    except Exception:  # noqa: BLE001 — advisory; never break planner-prompt assembly
        pass

    # WARM LEAN CHECK for the planner (2026-06-11 foot-gun fix): codex's verify instinct is GOOD — it caught a
    # real universe-inference bug while building the DAG — but it reached for COLD `lake env lean` (~90s Mathlib
    # reload), which BLEW the dispatch budget before it could emit. (Recovered from the rollout: codex had an
    # audit-PASSING Hermite split READY and lost it waiting on its own cold compile.) Surface the SAME warm checker
    # the formalizer uses (`lean_check_server --check`, ~0.1s warm) + tell it NOT to cold-compile. This is REUSE of
    # the formalize_interactive pattern, not a fork. Graceful: any setup failure → empty block → prior behaviour
    # (no regression). The hang-protection is now this warm path (no cold-compile stall), not a tiny hard wall.
    _warmcheck_block = ""
    try:
        import sys as _sys
        from ztare.leanmill.solver.agentic_leaf import probe_dir as _probe_dir
        from ztare.formal.lean_check_server import ensure_server_advertised as _ensure_adv
        _repo = Path(__file__).resolve().parents[4]
        # SINGLE DOOR (2026-07-03): advertise-or-loud. Only inject the warm-check block when the socket is LIVE —
        # the prior `or default_socket_path` injected a hint pointing at a possibly-DEAD socket, so codex saw
        # 'unreachable' and cold-compiled anyway. A live socket ⇒ real ~0.1s checks; None ⇒ no block (loud already).
        _sock = _ensure_adv(str(lean_root), context=f"planner {target_name}")
        if not _sock:
            raise RuntimeError("warm server down — no warm-check block (loud warning already logged)")
        # per-target probe name (2026-06-13 audit B3): a FIXED `IsoDagProbe.lean` collides across
        # concurrent shards on the same lean_root — one shard's warm-check reads another's probe. Key it
        # to the target (sound either way — the kernel re-verifies every closure — but a collision wastes
        # the warm-check steer). Sanitize the name to a safe filename fragment.
        _safe_tn = re.sub(r"[^A-Za-z0-9_]", "_", str(target_name or "tgt"))[:60]
        _probe = _probe_dir(lean_root) / f"IsoDagProbe_{_safe_tn}.lean"
        _leancheck = (f"PYTHONPATH={_repo}/src {_sys.executable} -m ztare.formal.lean_check_server "
                      f"--check {_sock} {_probe}")
        _warmcheck_block = _WARMCHECK_TEMPLATE.format(probe=_probe, leancheck=_leancheck)
    except Exception:  # noqa: BLE001 — never let warm-check setup break planning
        _warmcheck_block = ""
    _budget_req: "list[int | None]" = [None]   # #103(1): the agent's BUDGET: declaration, carried across refine rounds

    def _generate(ctx):
        fb = (ctx or {}).get("feedback", "")
        prompt = _DEANCHOR_PROMPT.format(p="iso", binders=(binders + " " if binders else ""),
                                         iso_step=_iso_step,
                                         goal_concl=goal_concl, ban=ban + fb, preamble=preamble, goal=goal_decl)
        if _agent_plan_on():                     # #74 step 1: surface the structural-action choice (default-off = parity)
            prompt = _plan_choice_prefix(goal=(goal_concl or goal_decl or "")) + prompt
        if _notes_block:                          # #81: prepend the blueprint notes as planner context (parity if none)
            prompt = _notes_block + prompt
        if _warmcheck_block:                      # surface the WARM lean-check at the TOP (most salient steer)
            prompt = _warmcheck_block + prompt
        # BOUND the PLANNER dispatch — GENEROUS now (the `planner` factory budget, default 360s, NOT the 180s
        # `propose` clamp that GUILLOTINED a codex run with an audit-PASSING DAG ready, 2026-06-11). A frontier
        # decomposition is real research, not a quick generate. The hang-protection that the old tight clamp gave
        # (a wedged CLI eating the wallclock) is now the WARM check above (codex no longer stalls ~90s on a cold
        # `lake env lean`) + the flushed HEARTBEAT (a frozen log still pinpoints a true wedge here). Still clamped
        # to `timeout_s` remaining so a genuine hang can't exceed the lemma/target wallclock.
        from ztare.common.timeouts import clamp_to_remaining as _clamp
        _cap = _clamp("planner", timeout_s)
        # #103(1) AGENT-CHOSEN TIME (bounded free will): the agent's PRIOR round may have declared
        # `BUDGET: <seconds>` (parsed below, already clamped to [60, cap-at-parse]); grant min(request, cap-now)
        # — re-clamped because the remaining wallclock SHRINKS between rounds. No declaration ⇒ the factory cap.
        _plan_budget = _cap if _budget_req[0] is None else max(60, min(_budget_req[0], _cap))
        _src = "agent-declared" if _budget_req[0] is not None else "factory"
        print(f"[iso] planner dispatch (budget {_plan_budget}s, {_src}) for: {goal_concl[:70]}", flush=True)
        try:
            _kw = {"repo": lean_root, "timeout": _plan_budget}
            # agent_tag: parallel-sample session key if present, else `{target}__planner` so the CoT trace carries
            # the CLEAN target (cot_traces splits on `__`) instead of an empty label (2026-07-03 fix). #117 sampling.
            _kw["agent_tag"] = ((ctx or {}).get("agent_tag")
                                or f"{re.sub(r'[^A-Za-z0-9_.]+', '_', str(target_name or 'tgt'))[:50]}__planner")
            raw = dispatch_fn(prompt, **_kw) or ""
        except TypeError:
            # an injected dispatch (test fake / older signature) without `agent_tag` — retry untagged:
            # SEQUENTIAL-equivalent behavior, never a crash
            raw = dispatch_fn(prompt, repo=lean_root, timeout=_plan_budget) or ""
        except Exception as e:  # noqa: BLE001
            return {"lemmas": [], "chain": "", "lnames": [], "raw": f"dispatch error: {e!r}"}
        lemmas, chain, lnames = _parse_dag(raw, "iso")
        out = {"lemmas": lemmas, "chain": chain, "lnames": lnames, "raw": raw}
        if _agent_plan_on():                     # #74 step 2: the chosen action DROVE the artifact (the prefix asked for the action-appropriate proves-G DAG); record it for the lift telemetry
            out["plan_action"], out["plan_reason"] = parse_plan_action(raw)
            _record_plan_choice(out["plan_action"], out["plan_reason"], goal_concl)
            # ENGAGEMENT JOIN (gap #1): tie the agent's A-PRIORI PLAN action (the "plan-before-work helps the
            # agent think" signal — reusing the existing PLAN: declaration, NOT a new one) to the atlas rank it
            # held in the research-move menu the planner surfaced. Best-effort telemetry.
            try:
                from ztare.leanmill.solver import move_atlas as _ma
                _pm = {"DECOMPOSE": "conjecture_lemma", "SPECIALIZE": "specialize", "GENERALIZE": "generalize",
                       "FALSIFY": "falsify", "ABDUCE": "abduce", "TRANSPORT": "transport"}.get(out["plan_action"], out["plan_action"])
                _ma.log_engagement(goal_concl or "", _pm, outcome="planned", via="plan",
                                   k=8, kinds={"structural", "technique", "research_op"})
            except Exception:  # noqa: BLE001
                pass
            from ztare.leanmill.solver.agent_output import budget_request as _breq   # #103(1): part of the PLAN contract
            _budget_req[0] = _breq(raw, floor=60, cap=_cap)
        return out

    def _verify(art):
        if not art.get("lemmas") or not art.get("chain"):
            # #133 (agency unlock): the agent may DELIBERATELY decline a DAG by electing SOLVE_DIRECT /
            # FALSIFY (the prompt now lets it). That is an honest non-decomposition, NOT a parse failure —
            # label it so, and `_refine_ctx` stops the loop (no re-coercion). The cascade carries both the
            # direct-proof and the ¬G/falsify moves (with their outcome plumbing), so the election routes
            # there; route_and_solve never duplicates that executor.
            _elected = art.get("plan_action")
            if _elected in ("FALSIFY", "SOLVE_DIRECT"):
                return _DagVerdict(False, f"agent elected {_elected} — no decomposition (cascade handles it)",
                                   {"elected": _elected})
            return _DagVerdict(False, "no parseable lemma DAG", {})
        passed, v = decomposition_dag_audit(art["lemmas"], art["chain"], art["lnames"], lean_root,
                                            max(120, timeout_s), preamble=preamble, goal_conclusion=goal_concl,
                                            goal_source=goal_decl, goal_name=target_name)  # kernel α/defeq circularity
        return _DagVerdict(passed, (v.get("passed") if passed else v.get("killed")) or "", v)

    def _refine_ctx(art, v, ctx):
        # #133 (agency): the agent elected SOLVE_DIRECT/FALSIFY and produced no DAG ON PURPOSE — refining
        # would re-coerce a DAG it deliberately declined (the old waste). Return None ⇒ RefineHandover stops
        # the loop immediately; the cascade routes the election to the direct/¬G move.
        if art.get("plan_action") in ("FALSIFY", "SOLVE_DIRECT") and not art.get("lemmas"):
            return None
        # TARGETED refine (2026-06-07): the GENERIC "redo it" demonstrably LOOPS on a circular-kill — the
        # leaf re-introduces a defective lemma each round (P1 iso_lemma1: 3 rounds, still circular, a 4/5-
        # sound DAG discarded). Instead, name the SOUND lemmas to KEEP and the single defective one to
        # replace — the decomposition-level analog of AND-OR DAG node re-expansion (keep the proven subtree,
        # re-attack only the failed node). Reuses the RefineHandover loop; only the feedback is smarter.
        reason = v.reason or ""
        lnames = art.get("lnames") or []
        lemmas = art.get("lemmas") or []
        bad = {n for n in lnames if n and n in reason}          # lemma(s) the audit named as defective
        sound = [l for l, n in zip(lemmas, lnames) if n not in bad]
        if sound and bad:
            fb = (" Your decomposition was SOUND EXCEPT for " + ", ".join(sorted(bad)) + " (kernel audit: "
                  + reason + "). KEEP these sound intermediate lemmas VERBATIM and reuse them in the chain:\n"
                  + "\n\n".join(sound) + "\n\nReplace ONLY the defective lemma(s) with a GENUINE reduction "
                  "(or DROP them if the chain no longer needs them); keep the chain sorry-free, typechecking, "
                  "and load-bearing. Do NOT restate the goal.")
        else:
            fb = (" Your PREVIOUS decomposition was REJECTED by the kernel audit: " + reason
                  + ". Produce a GENUINE reduction — NO lemma may restate the goal, and the chain "
                  "must typecheck and ACTUALLY USE each lemma's content (load-bearing).")
        return {"feedback": fb}

    loop = RefineHandover(generate=_generate, verify=_verify, accept_when=lambda v: v.accepted,
                          build_refine_context=_refine_ctx,
                          better=lambda a, va, b, vb: (b, vb) if vb.accepted else (a, va),
                          max_refines=max_refines)

    # DECOMPOSITION CACHE (2026-07-05, RBAC no-reuse RCA): reuse the FIRST audited DAG for THIS target so the
    # decomposition CONVERGES across runs (else the planner re-splits differently every run → banked rungs orphaned
    # → no compounding). The cached DAG is RE-AUDITED before use (fail-safe); the agent's decision is amortized like
    # a cached proof; the kernel ratifies every closure. Checked BEFORE planning; stored on any audited DAG below.
    _dcache = None
    _dkey = None
    if os.environ.get("ZTARE_LEANMILL_DECOMP_CACHE", "1") != "0":
        try:
            from ztare.formal.repl_compile import canonical_type_hash_via_repl as _cth
            _h = _cth(source, target_name, lean_root, env=None)
            if _h:
                _dkey = "d" + str(_h)
                from ztare.leanmill.solver.solver_core import OUT_DIR as _OUT
                _dcache = DecompositionCache(_OUT / "decomposition_cache.jsonl")
                _hit = _dcache.get(_dkey)
                if _hit:
                    _dv = _verify(_hit)
                    if _dv.accepted:
                        print(f"[iso] REUSED cached decomposition ({len(_hit.get('lnames') or [])} rungs) for "
                              f"'{target_name}' — CONVERGED, not re-planning (banked rungs stay citable)", flush=True)
                        return {"audited": True, "lemmas": _hit["lemmas"], "chain": _hit["chain"],
                                "lnames": _hit.get("lnames") or [], "verdict": _dv.detail, "rounds": 0,
                                "iso_source": "decomp_cache", "raw_tail": "", "notes_used": bool(_notes_block)}
                    print(f"[iso] cached decomposition for '{target_name}' no longer audits "
                          f"({str(_dv.reason)[:70]}) — re-planning", flush=True)
        except Exception:  # noqa: BLE001 — cache is best-effort; fall through to planning
            _dcache = None

    def _store_decomp(_lemmas, _chain, _lnames, _audited) -> None:
        if _audited and _dcache is not None and _dkey and _lemmas and (_chain or "").strip():
            _dcache.put(_dkey, _lemmas, _chain, _lnames or [])

    # DETERMINISTIC CONJUNCTIVE DECOMPOSITION (2026-06-25): when the target is a top-level conjunction, its
    # work-items ARE the conjuncts — derive them MECHANICALLY (no LLM consolidation lottery) and AUDIT through
    # the SAME `decomposition_dag_audit` kernel gate the agentic planner uses. On a pass we skip the agent
    # entirely; the conjuncts then prove (kernel) and `composite_ratify` assembles the And-intro composite —
    # ZERO new soundness surface (the kernel still ratifies G). Default-ON (sound: the audit + composite_ratify
    # gate every closure); ZTARE_LEANMILL_DETERMINISTIC_CONJ_DAG=0 reverts to agent-only. N/A (not a top-level
    # conjunction) or audit-miss ⇒ fall through to the agentic planner below — never a regression.
    if os.environ.get("ZTARE_LEANMILL_DETERMINISTIC_CONJ_DAG", "1") != "0":
        _det = derive_conjunctive_dag(goal_decl, target_name)
        if _det:
            _dv = _verify(_det)
            if _dv.accepted:
                print(f"[iso] DETERMINISTIC conjunctive decomposition: {len(_det['lnames'])} conjunct "
                      f"work-items audited (no LLM split) for: {goal_concl[:60]}", flush=True)
                _store_decomp(_det["lemmas"], _det["chain"], _det["lnames"], True)
                return {"audited": True, "lemmas": _det["lemmas"], "chain": _det["chain"],
                        "lnames": _det["lnames"], "verdict": _dv.detail, "rounds": 0,
                        "iso_source": "deterministic_conjunctive", "raw_tail": "",
                        "notes_used": bool(_notes_block), "deterministic_conjunctive": True}
            print(f"[iso] deterministic conjunctive split did not audit "
                  f"({str(_dv.reason)[:90]}) — falling through to the agentic planner", flush=True)

    # PARALLEL DIVERSE SAMPLING (ZTARE_ISO_SAMPLES>1; default 1 = byte-identical single-shot below): a breadth
    # leg over K technique-diverse decompositions, audited, survivors pursued; composes with refine on a miss.
    n_samples = int(os.environ.get("ZTARE_ISO_SAMPLES", "1"))
    if n_samples > 1:
        audited, attempts = _sample_diverse(n_samples, _generate, _verify, {})
        if audited:  # best-of-K: the richest SOUND blueprint
            art, v = _richest(audited)
            _store_decomp(art.get("lemmas"), art.get("chain"), art.get("lnames"), True)
            return {"audited": True, "lemmas": art.get("lemmas"), "chain": art.get("chain"),
                    "lnames": art.get("lnames"), "verdict": v.detail, "rounds": len(attempts),
                    "n_samples": n_samples, "n_audited": len(audited), "iso_source": _iso_source,
                    "raw_tail": (art.get("raw") or "")[-200:], "notes_used": bool(_notes_block)}
        # none of the K audited → seed the refine loop with the BEST near-miss's targeted feedback (compose:
        # explore K structures, then fix the most-sound one) instead of regenerating blind.
        seed_ctx = _refine_ctx(*_richest(attempts), {}) if attempts else {}
        art, verdict, trace = loop.run(seed_ctx)
        _store_decomp(art.get("lemmas"), art.get("chain"), art.get("lnames"), verdict.accepted)
        return {"audited": verdict.accepted, "lemmas": art.get("lemmas"), "chain": art.get("chain"),
                "lnames": art.get("lnames"), "verdict": verdict.detail, "rounds": len(attempts) + len(trace),
                "n_samples": n_samples, "n_audited": 0, "iso_source": _iso_source,
                "raw_tail": (art.get("raw") or "")[-200:], "notes_used": bool(_notes_block),
                **({} if verdict.accepted else {"killed": verdict.reason})}

    art, verdict, trace = loop.run({})
    _store_decomp(art.get("lemmas"), art.get("chain"), art.get("lnames"), verdict.accepted)
    return {"audited": verdict.accepted, "lemmas": art.get("lemmas"), "chain": art.get("chain"),
            "lnames": art.get("lnames"), "verdict": verdict.detail, "rounds": len(trace),
            "iso_source": _iso_source, "raw_tail": (art.get("raw") or "")[-200:], "notes_used": bool(_notes_block),
            **({} if verdict.accepted else {"killed": verdict.reason})}


def solve_decomposition(result: dict, source: str, target_name: str, *, lean_root: Path,
                        timeout_s: int = 400, substrate=None, notes: "str | None" = None,
                        _depth: int = 0) -> dict:
    """CONSISTENCY: route an AUDITED decomposition's lemmas through the ONE governed solver entry
    (`solve_adhoc`) — the SAME interface ad-hoc / autoformalize / residual-C / proof_repair use. No
    parallel solve, no parallel governance: each lemma Lᵢ is a target `preamble + Lᵢ` solved + ratified
    by the ONE kernel. Returns {solved, n_closed, lemmas:[{name, outcome}]}. This makes iso-decompose a
    target-PRODUCER feeding the canonical kernel, not a separate lane. (The loop never closes the goal G
    itself — G closes only if its sub-lemmas close and the chain is then discharged through the kernel.)"""
    if not result.get("audited"):
        return {"solved": False, "reason": "decomposition not audited — nothing to solve"}
    from ztare.leanmill.solver.solver_core import solve_adhoc  # lazy: avoid import cycle
    import time as _time
    preamble, _gd, _gc, _ban = deanchor(source, target_name)
    out: list = []
    proofs: dict = {}   # lname → ratified proof body (captured DIRECTLY from each solve result)
    # BUDGET-LEAK FIX (RCA 2026-06-12, the v3 2h-elongation): each sub-lemma previously got the FULL
    # `timeout_s` — K sub-lemmas ⇒ K× the phase budget, and each sub-solve recurses with ITS full budget ⇒
    # multiplicative wallclock. DEADLINE-THREAD instead: the WHOLE decomposition shares `timeout_s`; each
    # sub-lemma gets the REMAINING wallclock (≥60s floor). When the budget is spent, the rest are marked
    # `budget_exhausted` HONESTLY (the parent stays open — never a silent skip, never a fake negative).
    _deadline = _time.monotonic() + max(60, int(timeout_s))
    _pairs = list(zip(result.get("lemmas") or [], result.get("lnames") or []))
    # RUNG-ADJACENCY ATTACK ORDER (#121, Kossel–Stranski transport): attack max-coordination-with-proven-
    # rungs FIRST — sub-lemmas are solved INDEPENDENTLY against the preamble (dependencies matter only at
    # composite time), so the reorder is sound; under the SHARED deadline it spends the budget where the
    # proven infrastructure gives the leaf the most purchase, and the isolated deep crux goes last (v3
    # burned 91 min attacking that shape first). Telemetry records the order for the A/B falsifier.
    # ZTARE_LEANMILL_RUNG_ADJACENCY=0 reverts to planner (foundational-first) order.
    try:
        from ztare.leanmill.solver import rung_adjacency as _radj
        if _radj.enabled() and len(_pairs) > 1:
            _pv = _radj.proven_statements()
            if _pv:
                _ord = _radj.attack_order([l for l, _ in _pairs], _pv)
                if _ord != list(range(len(_pairs))):
                    _pairs = [_pairs[i] for i in _ord]
                _radj_telemetry = {"order": _ord,
                                   "scores": _radj.adjacency_scores([l for l, _ in _pairs], _pv)}
            else:
                _radj_telemetry = {"order": None, "note": "no proven rungs — planner order"}
        else:
            _radj_telemetry = None
    except Exception as _e:  # noqa: BLE001 — advisory ordering must never break the solve
        _radj_telemetry = {"error": repr(_e)[:80]}
    false_rungs: list = []   # planner sub-lemmas KERNEL-CONFIRMED false (#143/Layer-B): the decomposition is
    #                          defective (a true parent cannot have a false rung discharge its chain) → re-plan.
    for lemma, lname in _pairs:
        _rem = int(_deadline - _time.monotonic())
        if _rem < 60:
            out.append({"name": lname, "outcome": "budget_exhausted"})
            continue
        src = preamble.rstrip() + "\n\n" + lemma.strip() + "\n"
        try:
            r = solve_adhoc(lname, src, "", substrate=substrate, mode="dag_search", timeout_s=_rem,
                            notes=notes, _iso_depth=_depth)
            r0 = (r.get("results") or [{}])[0]
            outcome = r0.get("outcome")
            # A rung the leaf flagged STATEMENT-FALSE *and* solve_adhoc KERNEL-CONFIRMED (¬rung compiles): the
            # PLANNER produced a false sub-lemma — typically by dropping a hypothesis the parent guarantees
            # (the v7 iso_lemma1 case: a bare ∀ that omitted the denominator-unit hypothesis). Record it so
            # route_and_solve can RE-PLAN with the agent's correction (it never closes, so the chain can't
            # ratify — re-decomposition is the only sound way to progress). Distinct from an honest open rung.
            if r.get("statement_false_verified") and r.get("statement_false"):
                out.append({"name": lname, "outcome": "statement_false_confirmed"})
                false_rungs.append({"name": lname, "lemma": lemma.strip()[:600],
                                    "claim": str(r.get("statement_false") or "")[:400],
                                    "feedback": str(r.get("statement_false_feedback") or "")[:600]})
                continue
            out.append({"name": lname, "outcome": outcome})
            if outcome == "closed":
                # capture the proof DIRECTLY from the result's top-level `proof_text` (which IS the DAG's
                # root_proof_text — reliable), NOT a cache lookup whose key (the ENRICHED goal the DAG banks
                # under) would not match the bare lemma string. (The nested `dag_search` dict carries NO
                # `root_proof_text` key — that prior lookup was dead code; `proof_text` is the populated field.)
                _p = r0.get("proof_text") or ""
                if _p.strip():
                    proofs[lname] = _p
        except Exception as e:  # noqa: BLE001
            out.append({"name": lname, "outcome": f"exc: {repr(e)[:80]}"})
    n_closed = sum(1 for x in out if x["outcome"] == "closed")
    res = {"solved": n_closed == len(out) and bool(out), "n_closed": n_closed,
           "n_lemmas": len(out), "lemmas": out}
    if false_rungs:
        res["false_rungs"] = false_rungs   # planner produced provably-false sub-lemma(s) → route_and_solve re-plans
    # STALL HARVEST (2026-07-03, DeepSeek-Prover-V2 / POETRY / Hilbert recursive decomposition): a rung that is TRUE
    # but the leaf could NOT close in one shot (an honest exact_gap/open/failed — NOT budget_exhausted, NOT false) is
    # the signal to DECOMPOSE IT FURTHER, not to keep one-shotting it. Every prior re-plan trigger fired ONLY on a
    # kernel-FALSE rung, so a hard-but-true stalling rung (EF1 iso_lemma1's cycle-position argument) was left to
    # grind whole-goal. Surface these `open_rungs` so `route_and_solve` re-plans with a "split each stalled rung into
    # strictly smaller steps" cue. SOUND: the finer split re-enters the SAME kernel audit + composite_ratify — a
    # re-plan can never launder. Excludes budget_exhausted (no headroom ⇒ re-planning cannot help).
    _lemma_by_name = {ln: lm for lm, ln in _pairs}
    _STALL_SKIP = ("closed", "statement_false_confirmed", "budget_exhausted")
    open_rungs = [{"name": x["name"], "outcome": str(x["outcome"]),
                   "lemma": (_lemma_by_name.get(x["name"], "") or "").strip()[:600]}
                  for x in out if x["outcome"] not in _STALL_SKIP]
    if open_rungs:
        res["open_rungs"] = open_rungs     # TRUE-but-stalled sub-lemma(s) → route_and_solve re-decomposes them finer
    if _radj_telemetry is not None:
        res["rung_adjacency"] = _radj_telemetry   # the #121 A/B evidence trail (order + scores per run)
    # COMPOSITE RATIFICATION (2026-06-07): when EVERY sub-lemma closed, assemble {proven lemmas} + {chain}
    # → one sorry-free proof of G → ratify the PARENT through the ONE kernel. This is the decomposition→
    # closure step the DAG fail-safe withheld (a child proving a distinct lemma never closes G by itself).
    # Default-ON but kernel-gated (never a false closure); ZTARE_LEANMILL_COMPOSITE_RATIFY=0 reverts to the
    # rung-only behaviour (sub-lemmas verified, parent left open).
    if res["solved"] and os.environ.get("ZTARE_LEANMILL_COMPOSITE_RATIFY", "1") != "0":
        # USE the proofs collected DIRECTLY from each solve result in the loop above (reliable — vs a cache
        # lookup whose key, the ENRICHED goal the DAG banks under, would not match the bare lemma string).
        # Fall back to the proof cache ONLY for any lemma whose result did not expose a proof.
        _missing = [(lemma, lname)
                    for lemma, lname in zip(result.get("lemmas") or [], result.get("lnames") or [])
                    if lname not in proofs]
        if _missing:
            try:
                from ztare.leanmill.solver.solver_core import OUT_DIR as _OUT
                from ztare.leanmill.solver.proof_cache import ProofCache
                _pc = ProofCache(_OUT / "solver_lane_proof_cache.jsonl")
                for lemma, lname in _missing:
                    p = _pc.get(lemma) or _pc.get(preamble.rstrip() + "\n\n" + lemma.strip())
                    if p:
                        proofs[lname] = p
            except Exception:  # noqa: BLE001
                pass
        res["composite"] = composite_ratify(result, source, target_name, proofs,
                                             lean_root=lean_root, timeout_s=min(180, timeout_s),
                                             original_source=source)
        res["parent_closed"] = bool(res["composite"].get("parent_closed"))
        # ASSEMBLY-REPAIR (#160): the sub-rungs all proved but the up-front chain did not assemble the parent —
        # give the agent ONE shot to rewrite the chain with the proven lemmas now citable, re-ratified by the
        # SAME composite_ratify gate (ZERO new soundness surface — the kernel re-verifies the assembled proof).
        # DEFAULT-ON (2026-06-22, anti-sibling / sound-knob-default-on): this was left default-OFF "pending a P1
        # lift measurement", which is exactly the recurring under-use failure mode — a SOUND capability gated
        # off so it never fires. The consciousness stochastic-factorization rung RCA: `comap_measurable` (fwd)
        # + Doob–Dynkin (bwd) BOTH ratified, but the parent (`iff ∧ corollary`) never assembled because the
        # up-front chain abstracted `comap_measurable` as its own rung (not the fwd leg) and the repair shot was
        # OFF → honest-looking `exact_gap` on a fully-proven decomposition. `flag_audit` surfaced this gate. The
        # lift is now measurable via the A/B baseline (`=0` reverts); soundness is unchanged (composite_ratify
        # is the only admit path).
        if not res["parent_closed"] and os.environ.get("ZTARE_LEANMILL_ASSEMBLY_REPAIR", "1") != "0":
            _rep = _assembly_repair(result, source, target_name, proofs, lean_root=lean_root,
                                    timeout_s=min(180, timeout_s), original_source=source)
            if _rep.get("parent_closed"):
                res["composite"] = _rep
                res["parent_closed"] = True
                res["assembly_repaired"] = True
    return res


def _splice_proof(lemma: str, proof: str) -> str:
    """Replace a sorried lemma's body with its ratified proof (split on the FIRST top-level `:=`)."""
    from ztare.leanmill.lean_source import signature_before_proof   # canonical binder-safe head extractor
    head = signature_before_proof(lemma).rstrip()
    return f"{head} := {proof.strip()}"


def _strip_trailing_diagnostics(proof: str) -> str:
    """Drop trailing `#print` / `#check` / `#eval` COMMAND(s) a leaf appended after its proof term. In its OWN
    probe those reference the leaf's own decl name and verify fine, but spliced under the composite's decl name
    they become `unknown constant <leaf-name>` and break the assembly (2026-07-03 — the DeFi conjunct proofs each
    carried a trailing `#print axioms reachable_state_solvency_guarded_actions_conjᵢ`). A `#`-command is only ever a
    top-level diagnostic here (never inside a tactic block), so cutting at the first one is safe + comment-agnostic
    enough for the assembler (the kernel re-ratifies the spliced result regardless)."""
    import re as _re
    return _re.split(r"\n\s*#(?:print|check|eval)\b", proof or "")[0].rstrip()


def assemble_composite_proof(preamble: str, lemmas, lnames, lemma_proofs: dict, chain: str) -> str:
    """PURE (no Lean): splice each lemma's ratified proof in place of its sorry, then append the CHAIN (which
    proves G using the lemma names) — a single sorry-free Lean source proving G. '' if any lemma's proof is
    missing / itself contains sorry, or the chain is empty (⇒ cannot assemble; parent stays open). The kernel
    ratifies the result downstream — this only BUILDS the candidate."""
    parts = [preamble.rstrip()] if (preamble or "").strip() else []
    from ztare.leanmill.lean_source import has_sorry as _hs_assemble   # comment-robust, not substring
    for lemma, lname in zip(lemmas or [], lnames or []):
        proof = (lemma_proofs or {}).get(lname)
        if not proof or _hs_assemble(proof):
            return ""
        proof = _strip_trailing_diagnostics(proof)   # a leaf's trailing `#print axioms <own-name>` becomes an
                                                      # `unknown constant` under the composite's decl (2026-07-03)
        parts.append(_splice_proof(lemma, proof))
    if not (chain or "").strip() or not parts:
        return ""
    parts.append(chain.strip())
    return "\n\n".join(parts) + "\n"


def kernel_conjunction_split(binders: str, concl: str) -> "list[str] | None":
    """REPL-AUTHORITATIVE conjunction split (2026-07-03 — the GENERAL-PURPOSE fix for the recurring regex
    `safe_conjunction_split` bug class). Instead of regex-parsing `C₁ ∧ … ∧ Cₙ` (which can't know `∃`/`∀`/`Σ` binds
    loosest, so it split a binder's OWN body and orphaned the witness — the DeFi false-gap), ASK LEAN: elaborate
    `example <binders> : <concl> := by (repeat' apply And.intro) <;> sorry` in the campaign env and read the LEAF-goal
    sorries — those ARE the conjuncts, from Lean's real parser+elaborator (every binder/precedence/macro/unicode).
    `And.intro` only splits `∧`, never a binder's body, so a ∃/∀ conjunct comes back WHOLE. SYMMETRIC with the
    composite (which already does `repeat' apply And.intro`). Returns [C₁…Cₙ] (n≥2) or None (no campaign env / no REPL
    / not a conjunction / ANY elaboration issue) — the caller falls back to the regex splitter, and the decomposition
    AUDIT (`decomposition_dag_audit`, kernel) gates whichever conjuncts result, so this can never regress or unsound."""
    try:
        from pathlib import Path as _P
        from ztare.formal.repl_compile import (get_campaign_substrate, campaign_file_env, campaign_variables,
                                                campaign_namespaces, _get_repl, _strip_prelude_for_repl)
        sub = get_campaign_substrate()
        if not sub:
            return None
        project = str(_P(sub).parent)
        env = campaign_file_env(str(_P(sub).resolve()), project)   # the defs the target's conjuncts reference
        pl = _get_repl(project)
        if env is None or pl is None:
            return None
        _ns = campaign_namespaces()
        _vb = "".join(v + "\n" for v in campaign_variables())       # section-variable/instance context (K, [Field K]…)
        _open = "".join(f"namespace {n}\n" for n in _ns) if len(_ns) == 1 else ""
        _end = "".join(f"end {n}\n" for n in _ns) if len(_ns) == 1 else ""
        _b = (" " + binders.strip()) if binders.strip() else ""
        ex = f"import Mathlib\n{_open}{_vb}example{_b} : {concl} := by (repeat' apply And.intro) <;> sorry\n{_end}"
        r = pl.check(_strip_prelude_for_repl(ex), timeout=90, env=env)
        if not isinstance(r, dict) or r.get("errors"):             # a real elaboration error ⇒ not a valid split
            return None
        conj = [(s.get("goal", "") if isinstance(s, dict) else "").rsplit("⊢", 1)[-1].strip()
                for s in (r.get("sorries") or [])]
        conj = [c for c in conj if c]
        return conj if len(conj) >= 2 else None
    except Exception:  # noqa: BLE001 — best-effort; ANY failure ⇒ the regex fallback in the caller (never blocks)
        return None


def derive_conjunctive_dag(goal_decl: str, target_name: str) -> "dict | None":
    """DETERMINISTIC decomposition of a top-level CONJUNCTIVE target `C₁ ∧ … ∧ Cₙ` into the SAME
    `{lemmas, lnames, chain}` shape the agentic planner produces — so the conjuncts ARE the work-items
    *by construction* (no LLM consolidation lottery), then the EXISTING pipeline takes over unchanged:
    `decomposition_dag_audit` (kernel) gates it and `composite_ratify` assembles the And-intro composite.
    ZERO new soundness surface — this only proposes WHICH lemmas to prove; the kernel still ratifies G.

    Each conjunct becomes `theorem <target_name>_conjᵢ <binders> : Cᵢ := by sorry` (the FULL binder telescope,
    so the decl is always well-typed). The chain re-states G and discharges it by splitting the conjunction and
    citing the conjunct lemmas — `solve_by_elim [<names>]` names every lemma (the audit's cite-check) and closes
    each leaf by unification (binder-robust). Reuses ONLY canonical parsers (`lean_source` + the one top-level
    splitter); NO brittle decl regex. Returns None when the target is NOT a top-level conjunction (e.g. atomic,
    or a top-level `↔` — left to the planner) or the signature can't be split — caller then dispatches the agent.
    """
    if not goal_decl or not target_name:
        return None
    from ztare.leanmill.lean_source import extract_signature, top_level_colon, safe_conjunction_split
    sig = (extract_signature(goal_decl, target_name) or "").strip()   # `<binders> : <conclusion>`
    if not sig:
        return None
    ci = top_level_colon(sig)
    if ci < 0:
        return None
    binders = sig[:ci].strip()
    concl = sig[ci + 1:].strip()
    if not concl:
        return None
    # ∀-fronting strip + ∃-defer + ↔-guard + `∧`-split all live behind ONE door (lean_source.safe_conjunction_split),
    # shared with governed_dag_search.derive_structural_decomposition so a quantifier guard can never drift into a
    # sibling (2026-07-01 NS-hunt RCA: `∃ w, A∧B` was split as a plain conjunction in the un-guarded twin, orphaning
    # the shared witness `w` as a free variable). `∀` distributes → the prefix is re-prepended to each conjunct.
    # REPL-AUTHORITATIVE split FIRST (2026-07-03 general fix): ask Lean for the conjuncts — respects every binder a
    # regex can't (the DeFi `∃`-conjunct false-gap). The binders are applied in the elaborated `example`, so the
    # conjuncts carry no ∀-prefix (qprefix=""). Fall back to the regex `safe_conjunction_split` (now binder-scoping-
    # fixed) when the REPL split is unavailable; `decomposition_dag_audit` gates whichever conjuncts result, so this
    # can never regress or unsound. Symmetric with the composite, which already uses `repeat' apply And.intro`.
    _kconj = kernel_conjunction_split(binders, concl)
    if _kconj:
        qprefix, conjuncts = "", _kconj
    else:
        _split = safe_conjunction_split(concl)
        if not _split:
            return None   # ∃-led (shared witness), top-level ↔, or atomic — the guarded door decides
        qprefix, conjuncts = _split
    _bind = (" " + binders) if binders else ""
    _q = (qprefix + " ") if qprefix else ""
    lemmas, lnames = [], []
    for i, c in enumerate(conjuncts, start=1):
        lname = f"{target_name}_conj{i}"
        lnames.append(lname)
        # ∀-FRONT the binder telescope (2026-07-03 general fix — the DeFi 3-conjunct composite never compiled).
        # The leaf solver ∀-fronts the goal (`pi_normalized_signature`), so a ratified conjunct proof BEGINS
        # `intro <binders>`. A param-BOUND conjunct theorem (`theorem <name> <binders> : Cᵢ`) then makes that intro
        # fail (`introN failed`: no binders in the goal) the instant the proof is spliced back → the composite stays
        # open even though every conjunct is proven. Emit the conjunct ∀-fronted so the leaf proof splices as-is;
        # `solve_by_elim [<names>]` in the chain applies the ∀-fronted lemma under unification (validated compile,
        # axiom-clean). Empty telescope ⇒ no ∀ (would be `∀ ,`).
        if binders.strip():
            lemmas.append(f"theorem {lname} : ∀{_bind}, {_q}{c} := by sorry")
        else:
            lemmas.append(f"theorem {lname} : {_q}{c} := by sorry")
    cites = ", ".join(lnames)
    # N-agnostic + associativity-robust: `intro` the fronted quantifier (no-op when there is none), peel every
    # top-level `∧`, then close each leaf citing the conjunct lemmas (`solve_by_elim` applies them under unification).
    _intro_line = "  intros\n" if qprefix else ""
    chain = (f"theorem {target_name} {sig} := by\n"
             f"{_intro_line}"
             f"  repeat' apply And.intro\n"
             f"  all_goals solve_by_elim [{cites}]")
    return {"lemmas": lemmas, "lnames": lnames, "chain": chain, "deterministic_conjunctive": True}


def _top_level_comma(s: str) -> int:
    """Index of the FIRST `,` at bracket-depth 0 (binder commas inside (…)/[…]/{…}/⟨…⟩ are nested → ignored);
    used to find where a leading `∀ <binders>,` quantifier prefix ends. -1 if none."""
    depth = 0
    for i, c in enumerate(s):
        if c in "([{⟨⦃":
            depth += 1
        elif c in ")]}⟩⦄":
            depth = max(0, depth - 1)
        elif depth == 0 and c == ",":
            return i
    return -1


def composite_ratify(result: dict, source: str, target_name: str, lemma_proofs: dict, *,
                     lean_root: Path, timeout_s: int = 180, original_source: "str | None" = None) -> dict:
    """COMPOSITE RATIFICATION — the decomposition→closure assembler. Assemble {proven sub-lemmas} + {chain}
    → compile sorry-free (`_compile_probe`) → run the ONE anti-laundering kernel on G (axioms / vacuity /
    statement-integrity vs the original) → a RATIFIED PARENT closure. SAME gate the falsify path uses (zero
    new soundness surface): a mis-assembled composite either fails to compile or trips an organ → parent
    stays open, never a false closure. Returns {parent_closed, composite_source?, target?, reason}."""
    preamble, _gd, _gc, _ban = deanchor(source, target_name)
    composite = assemble_composite_proof(preamble, result.get("lemmas"), result.get("lnames"),
                                         lemma_proofs, result.get("chain") or "")
    if not composite:
        return {"parent_closed": False, "reason": "could not assemble (missing/invalid lemma proof or chain)"}
    chain = result.get("chain") or ""
    from ztare.leanmill import lean_source as _ls   # canonical Lean parsing
    gname = _ls.first_theorem_name(chain) or None
    if not gname:
        return {"parent_closed": False, "reason": "could not locate the chain's goal theorem name"}
    # DEFENSE-IN-DEPTH (do NOT trust the upstream audit for a default-ON parent-closure path): re-check that
    # the chain actually proves the ORIGINAL goal's conclusion — a chain that silently proves a WEAKER G must
    # never ratify the parent, even if it compiles. (statement_integrity in the kernel keys on the original
    # NAME, which the chain renames, so this conclusion-match is the load-bearing statement check here.)
    _chain_concl = _norm_ws(_lemma_conclusion(chain))
    _goal_concl = _norm_ws(_gc or "")
    if _goal_concl and _chain_concl and _chain_concl != _goal_concl:
        return {"parent_closed": False, "composite_source": composite, "target": gname,
                "reason": f"chain proves a DIFFERENT statement than G (got {_chain_concl[:60]!r} vs "
                          f"goal {_goal_concl[:60]!r}) — refusing the parent closure"}
    src = composite if composite.lstrip().startswith("import") else ("import Mathlib\n\n" + composite)
    try:
        from ztare.gates.v33_preflight_risk_detector import _compile_probe
        if _compile_probe(src, lean_root, "Composite", max(120, timeout_s)) is not True:
            return {"parent_closed": False, "composite_source": composite, "target": gname,
                    "reason": "composite does NOT compile sorry-free (a sub-proof did not port into the chain)"}
        from ztare.gates.lean_proof_gate import run_anti_laundering_kernel
        k = run_anti_laundering_kernel(src, Path(lean_root) / "_composite_kernel.lean", Path(lean_root),
                                       original_source=original_source, target_name=gname)
        passed = bool(k.get("passed"))
        _axs: "list[str]" = []
        if passed:
            # AXIOM AUDIT (soundness #84 F2): the parent / open-problem closure must be axiom-CLEAN too — a
            # `native_decide` (Lean.ofReduceBool) in the chain or a spliced sub-lemma proof would otherwise
            # ratify the parent (the anti-laundering kernel does not run `#print axioms`). Fail-CLOSED only on a
            # CONFIRMED banned axiom. Runs once, only on a kernel-passed candidate (no wasted compile).
            from ztare.gates.lean_compile_primitives import audit_axioms_subset as _aax
            _ax_clean, _ax_bad, _axs = _aax(src, gname, Path(lean_root) / "_composite_axiom_audit.lean",
                                            Path(lean_root), timeout_s=max(120, timeout_s))
            if _ax_bad:
                return {"parent_closed": False, "composite_source": composite, "target": gname,
                        "reason": f"BAD_AXIOMS in composite: {_axs} (native_decide?) — refusing parent closure"}
        return {"parent_closed": passed, "composite_source": composite, "target": gname,
                "reason": f"compile_ok + kernel passed={passed} confirmed={k.get('confirmed')} axioms={_axs}"}
    except Exception as e:  # noqa: BLE001
        return {"parent_closed": False, "composite_source": composite, "target": gname,
                "reason": f"kernel error: {repr(e)[:120]}"}


def _assembly_repair(result: dict, source: str, target_name: str, proofs: dict, *,
                     lean_root: Path, timeout_s: int = 180, original_source: "str | None" = None,
                     dispatch_fn=None, ratify_fn=None) -> dict:
    """ASSEMBLY-REPAIR (#160 — the 2026-06-18 P1 meta lever). The sub-lemmas all PROVED but the chain the agent
    committed UP FRONT (before any Lᵢ was proven) did not assemble the parent — `composite_ratify` returned
    parent_closed=False — so closable rungs sit banked with the parent open (P1 lemmas 2–4). Dispatch the agent
    ONCE to REWRITE the chain proving G with the now-PROVEN lemmas citable, then re-ratify through the SAME
    `composite_ratify` gate: ZERO new soundness surface — a bad repair just fails to close (the conclusion-match
    + anti-laundering kernel + axiom audit still gate G). Reuses the canonical `_parse_dag` extractor + the
    `signature_before_proof` head + `composite_ratify`; no re-rolled Lean parsing. `dispatch_fn`/`ratify_fn`
    injectable ⇒ hermetic selftest (no live agent, no Lean)."""
    lemmas = result.get("lemmas") or []
    lnames = result.get("lnames") or []
    chain0 = result.get("chain") or ""
    if not chain0 or not lnames:
        return {"parent_closed": False, "reason": "assembly-repair: no original chain / lemma names"}
    from ztare.leanmill.lean_source import signature_before_proof as _sig
    goal_sig = _sig(chain0).rstrip()
    proven = "\n".join(f"  • `{nm}` : {_sig(l)}" for l, nm in zip(lemmas, lnames) if nm)
    prompt = (
        "ASSEMBLY. These lemmas are ALREADY PROVEN and in scope — cite each by its NAME as an established fact "
        "(do NOT re-prove them):\n" + proven + "\n\n"
        "Write a COMPLETE, sorry-free Lean proof of THIS goal, citing the proven lemmas above by name:\n"
        + goal_sig + "\n\nReturn ONE fenced block exactly like:\n```lean\nDECOMP:\n" + goal_sig
        + " := by\n  <tactics that cite the lemmas by name; NO sorry>\n```\n")
    if dispatch_fn is None:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch as dispatch_fn
    try:
        raw = dispatch_fn(prompt, repo=lean_root, timeout=timeout_s) or ""
    except Exception as e:  # noqa: BLE001 — a failed repair leaves the parent open, never crashes the run
        return {"parent_closed": False, "reason": f"assembly-repair dispatch error: {repr(e)[:100]}"}
    _, new_chain, _ = _parse_dag(raw, "DECOMP:")
    if not new_chain or "sorry" in new_chain.split(":=", 1)[-1] or new_chain.strip() == chain0.strip():
        return {"parent_closed": False, "reason": "assembly-repair: agent produced no NEW sorry-free chain"}
    if ratify_fn is None:
        ratify_fn = composite_ratify
    out = ratify_fn(dict(result, chain=new_chain), source, target_name, proofs,
                    lean_root=lean_root, timeout_s=timeout_s, original_source=original_source) or {}
    out["assembly_repaired"] = bool(out.get("parent_closed"))
    return out


def iso_should_recurse(depth: int, *, soft_bound: int, hard_cap: int,
                       agent_vote: "bool | None" = None) -> "tuple[bool, str]":
    """Decide whether the recursive planner should DECOMPOSE AGAIN at this depth — separating the two concerns
    the old `depth >= ZTARE_ISO_MAX_DEPTH` magic number conflated (operator: "depth<2 is arbitrary; the agent
    should choose WHEN to stop, against a system-defined MAX hard cap, not a strawmanned lower bound"):
      • HARD CAP (`hard_cap`, ZTARE_ISO_DEPTH_HARD_CAP) — the SYSTEM safety ceiling. Recursion NEVER exceeds it,
        whatever the policy or the agent says (the cost + non-termination backstop). Checked FIRST, always wins.
      • STOP POLICY within the cap — TUNABLE, not a hardcoded low bound:
          – default (parity): the legacy soft bound `depth < soft_bound` (ZTARE_ISO_MAX_DEPTH, default 2).
          – adaptive (ZTARE_ISO_ADAPTIVE_DEPTH=1): the AGENT owns the stop — an explicit `agent_vote` (False =
            "solve HERE, do not decompose further") up to the hard cap. The agentic half of the goldilocks split
            (agent chooses the stop; THIS deterministic guard enforces the ceiling). `agent_vote=None` ⇒ recurse
            to the hard cap (the agent has not voted; the cap is then the only bound).
    Returns (should_recurse, reason). The HARD CAP is enforced regardless of mode."""
    if depth >= hard_cap:
        return (False, f"hard depth cap reached ({depth} >= {hard_cap}) — system safety ceiling")
    if os.environ.get("ZTARE_ISO_ADAPTIVE_DEPTH") == "1":
        if agent_vote is False:
            return (False, f"agent elected to solve at depth {depth} rather than decompose further")
        return (True, f"adaptive: decompose at depth {depth} (within hard cap {hard_cap})")
    if depth >= soft_bound:                          # default / parity policy: the legacy soft bound
        return (False, f"iso-route depth cap reached ({depth} >= {soft_bound})")
    return (True, f"within soft bound (depth {depth} < {soft_bound})")


def _render_false_rung_feedback(false_rungs: list) -> str:
    """Planner-prompt correction (#143/Layer-B): tell the re-decomposing leaf which sub-lemma(s) it produced
    were KERNEL-CONFIRMED false and why, so it re-decomposes with the MISSING hypothesis restored — instead of
    silently re-emitting the same defective rung. Advisory (the kernel audit still gates every new lemma);
    cannot launder — it only steers the planner toward a SOUND decomposition the parent actually implies."""
    lines = ["\n\nPRIOR-DECOMPOSITION DEFECT — these sub-lemmas were proven FALSE as stated (a kernel-checked "
             "counterexample compiled), so they CANNOT discharge the parent and the whole decomposition is "
             "invalid. They are almost always a DROPPED HYPOTHESIS the parent guarantees (a non-vanishing "
             "denominator, a unit/regularity condition, a domain restriction). Re-decompose so every sub-lemma "
             "is TRUE: restore the missing hypothesis; do NOT reproduce the refuted statement."]
    for fr in false_rungs:
        lines.append(f"  • `{fr.get('name')}` is FALSE — counterexample/reason: {(fr.get('claim') or '').strip()[:300]}")
    return "\n".join(lines) + "\n"


def _render_open_rung_feedback(open_rungs: list) -> str:
    """Planner-prompt cue for the STALL→DEEPER-DECOMPOSE escalation (2026-07-03; the recursive-decomposition
    mechanism of DeepSeek-Prover-V2 / POETRY / Hilbert). These sub-lemmas are TRUE but the leaf could not close
    them in ONE shot — the fix is not to retry the same whole-goal proof, but to break EACH into strictly smaller
    intermediate steps and hand those back as their OWN sub-lemmas (the prover's `have hStep : … := by …` steps
    become sibling rungs). Advisory: the kernel audit + composite_ratify still gate every new lemma, so this can
    only STEER toward a finer sound decomposition — it can never launder."""
    lines = ["\n\nPRIOR-DECOMPOSITION STALL — these sub-lemmas are TRUE but could NOT be proved in a single pass "
             "(an honest gap, not a false statement). Do NOT re-emit them unchanged. DECOMPOSE EACH ONE FURTHER: "
             "write the proof as a chain of strictly simpler intermediate `have` steps and PROMOTE EACH such step "
             "to its own named sub-lemma, so every new rung is materially smaller than the one that stalled. If you "
             "produced a partial proof with `sorry` placeholders, turn each remaining `sorry` subgoal into a rung."]
    for orr in open_rungs:
        lines.append(f"  • `{orr.get('name')}` stalled ({orr.get('outcome')}) — split it into smaller steps. "
                     f"Statement: {(orr.get('lemma') or '').strip()[:240]}")
    return "\n".join(lines) + "\n"


def route_and_solve(source: str, target_name: str, goal: str, *, lean_root: Path,
                    timeout_s: int = 400, substrate=None, notes: "str | None" = None,
                    _depth: "int | None" = None) -> dict:
    """AUTONOMOUS RECURSION — the wiring that makes leanmill recursively self-solve (the gap: this
    producer was invoked only by an experiment runner, so a `strong_missing` rung that came back
    `exact_gap` was never re-decomposed). `frontier_triage` routes: ONLY a `strong_missing` target
    (full closure needs machinery INVENTED — P1 and its rungs) is sent to the blueprint producer
    `attack` (deanchor→transport→audited DAG), whose sub-lemmas solve through the ONE kernel via
    `solve_decomposition`. Because `solve_decomposition` calls `solve_adhoc`, which re-enters this route
    on an `exact_gap` sub-rung, the decomposition RECURSES until the leaves are citable — bounded by the
    DEPTH GUARD (`ZTARE_ISO_DEPTH`/`ZTARE_ISO_MAX_DEPTH`, default 2). The lemmas that close are verified
    RUNGS; G never closes here unless its sub-lemmas + chain discharge through the kernel. DEFAULT-ON at the
    call site (`ZTARE_LEANMILL_ISO_ROUTE`, 2026-06-09; =0 reverts to parity) — sound by construction (parent
    closes only via composite_ratify's anti-laundering kernel; caught cheats excluded). Fires on the HONEST
    non-closure the caller gates (exact_gap/open/failed) — NOT gated behind triage `strong_missing`, which keys
    on English markers absent from formalized goals (`ZTARE_LEANMILL_ISO_STRONG_ONLY=1` restores the narrow gate).
    Returns {routed, audited?, killed?, decomposition?, solution?, depth}."""
    from ztare.leanmill.solver.frontier_triage import triage
    # RECURSION DEPTH is an explicit PARAMETER threaded through the recursion (#127, 2026-06-13): the prior
    # `os.environ["ZTARE_ISO_DEPTH"]` bump/restore was process-global mutable recursion state — concurrent
    # route_and_solve calls would race and corrupt the depth bound. The env var stays a READ-ONLY top-level
    # override (experiment runner / selftest); the recursion never mutates it.
    depth = _depth if _depth is not None else int(os.environ.get("ZTARE_ISO_DEPTH", "0"))
    soft_bound = int(os.environ.get("ZTARE_ISO_MAX_DEPTH", "2"))
    # HARD CAP (system safety ceiling) DECOUPLED from the stop policy (operator's "depth<2 is arbitrary"): the
    # cap is system-defined + non-negotiable; WHEN to stop within it is a tunable policy / the agent's call.
    # Default (no ZTARE_ISO_ADAPTIVE_DEPTH) = the legacy soft bound ⇒ byte-parity (soft_bound=2 stops before
    # hard_cap=4 is ever reached). `iso_should_recurse` is the named seam where the agent's vote will plug in.
    hard_cap = max(soft_bound, int(os.environ.get("ZTARE_ISO_DEPTH_HARD_CAP", "4")))
    _recurse, _stop = iso_should_recurse(depth, soft_bound=soft_bound, hard_cap=hard_cap)
    if not _recurse:
        return {"routed": False, "reason": _stop, "stop_reason": _stop, "depth": depth, "hard_cap": hard_cap}
    tv = triage(goal or "", source_hint=target_name)
    # REACHABILITY FIX (2026-06-09): fire on the HONEST NON-CLOSURE the caller already gated (exact_gap/open/
    # failed) — direct-failure IS the decompose signal (DeepSeek-Prover-V2 / BFS-Prover-V2 / LEAP all decompose
    # on direct-failure, not on a hardness classifier). The prior `strong_missing`-only gate keyed on ENGLISH
    # discovery-markers ("conjecture" / "open problem" / "sharp constant" …) that are ABSENT from a FORMALIZED
    # Lean signature, so `triage` tagged BOTH the P1 autonomous-n1 target AND the full denef conjecture
    # "elementary" — the planner NEVER fired on exactly the open targets it exists for (verified 2026-06-09).
    # `target_strength` is kept only as an ADVISORY telemetry tag. ZTARE_LEANMILL_ISO_STRONG_ONLY=1 restores
    # the old narrow gate (e.g. for a cost-bounded batch where decomposing every miss is too expensive).
    if os.environ.get("ZTARE_LEANMILL_ISO_STRONG_ONLY") == "1" and tv.target_strength != "strong_missing":
        return {"routed": False, "depth": depth, "target_strength": tv.target_strength,
                "reason": f"target_strength={tv.target_strength!r} (ISO_STRONG_ONLY narrow gate)"}
    # RE-PLAN ON A CONFIRMED-FALSE RUNG (#143/Layer-B, default-on; =0 reverts to single-shot). The agentic-first
    # decomposition can hand back a sub-lemma that is provably FALSE — almost always a hypothesis the parent
    # guarantees but the planner dropped (v7 iso_lemma1: the bare ∀ that omitted the denominator-unit condition,
    # which the leaf CORRECTLY refuted with a compiling ¬G). A true parent cannot be discharged by a false rung,
    # so the run would otherwise STALL with the agent's correct correction thrown away. Feed that correction back
    # to the planner (advisory notes; the kernel audit + composite_ratify still gate soundness — a re-plan can
    # NEVER launder) and re-decompose, bounded by ZTARE_LEANMILL_REPLAN_FALSE_RUNG rounds (default 1).
    _replan_false_budget = (int(os.environ.get("ZTARE_LEANMILL_REPLAN_FALSE_RUNG", "1") or "1")
                            if os.environ.get("ZTARE_LEANMILL_REPLAN_FALSE_RUNG", "1") != "0" else 0)
    # STALL-DRIVEN re-plan (2026-07-03): a TRUE-but-stalled rung triggers ONE finer re-decomposition. OPT-IN
    # (default OFF, =1 enables) — unlike the false-rung re-plan (kernel-fact trigger), "stall" is a heuristic
    # trigger, so a DEFAULT-ON harness-forced re-decompose is goldilocks determinism-creep (the arch invariant:
    # decompose-vs-direct is the AGENT's call; a `falsify-on-stall` was reverted for exactly this). Kept available
    # for A/B / explicit runs; the agent electing DECOMPOSE at re-entry is the invariant-clean path.
    _replan_stalled_budget = (int(os.environ.get("ZTARE_LEANMILL_REPLAN_STALLED_RUNG", "0") or "0")
                              if os.environ.get("ZTARE_LEANMILL_REPLAN_STALLED_RUNG", "0") != "0" else 0)
    _replan_budget = max(_replan_false_budget, _replan_stalled_budget)
    import time as _time
    from ztare.common.timeouts import timeout_s as _budget   # the ONE timeout home (no inline magic numbers)
    # BUDGET CONTRACT (the v3 budget-leak lesson + byte-parity): ROUND 0 is the original single-shot — attack
    # and solve_decomposition each get the caller's `timeout_s`, exactly as before #143 (so the dominant
    # no-false-rung path is unchanged). The EXTRA re-plan rounds collectively share ONE `notes_lemma` budget
    # (`_replan_deadline`), so re-plan can never MULTIPLY the target budget by the round count; a round is only
    # started if at least `replan_floor` wall remains (a planner dispatch + a minimal solve), else we stop
    # HONESTLY (parent left open). Both values resolve through the central factory — no inline constants.
    _replan_floor = _budget("replan_floor")
    _replan_deadline = _time.monotonic() + _budget("notes_lemma")
    _notes = notes
    _replan_trace: list = []
    res = None
    sol = None
    for _round in range(_replan_budget + 1):
        if _round == 0:
            _round_t = int(timeout_s)                       # byte-parity with the pre-#143 single shot
        else:
            _rem = max(0, int(_replan_deadline - _time.monotonic()))
            if _rem < _replan_floor:                        # not enough wall for another round → stop honestly
                _replan_trace.append({"round": _round, "stopped": "replan_budget_exhausted"})
                break
            _round_t = _rem
        res = attack(source, target_name, lean_root=lean_root, timeout_s=_round_t, notes=_notes)
        if not res.get("audited"):
            return {"routed": True, "audited": False, "killed": res.get("killed"),
                    "decomposition": res, "depth": depth,
                    "replan_trace": _replan_trace or None}
        # children recurse at depth+1 — threaded as a PARAMETER (no env mutation, concurrency-safe). Round 0 gets
        # the caller's `timeout_s` (parity); a re-plan round gets what remains of the shared `notes_lemma` extra.
        _sol_t = int(timeout_s) if _round == 0 else max(_replan_floor, int(_replan_deadline - _time.monotonic()))
        sol = solve_decomposition(res, source, target_name, lean_root=lean_root,
                                  timeout_s=_sol_t, substrate=substrate, notes=_notes, _depth=depth + 1)
        _false = sol.get("false_rungs") or []
        # STALL-DRIVEN rungs re-plan too (2026-07-03): a TRUE-but-stalled rung is re-decomposed FINER.
        _open = (sol.get("open_rungs") or []) if _replan_stalled_budget else []
        # Each path re-plans ONLY within ITS OWN budget, so `REPLAN_FALSE_RUNG=0` or `REPLAN_STALLED_RUNG=0`
        # independently restores that path's single-shot A/B baseline (no cross-contamination via the shared loop).
        _do_false = bool(_false) and _round < _replan_false_budget
        _do_open = bool(_open) and _round < _replan_stalled_budget
        # stop: parent already ratified, OR neither path has an actionable rung within its remaining budget.
        if sol.get("parent_closed") or not (_do_false or _do_open):
            break
        _replan_trace.append({"round": _round,
                              "false_rungs": [f["name"] for f in _false] if _do_false else [],
                              "open_rungs": [o["name"] for o in _open] if _do_open else []})
        # correction (false) + decompose-further cue (stalled) → next planner round. Both steer the SAME
        # kernel-audited re-plan; a stalled rung asks for a strictly finer split of that rung.
        _notes = ((notes or "")
                  + (_render_false_rung_feedback(_false) if _do_false else "")
                  + (_render_open_rung_feedback(_open) if _do_open else ""))
    return {"routed": True, "audited": True, "decomposition": res, "solution": sol, "depth": depth,
            "rungs_closed": sol.get("n_closed", 0), "rungs_total": sol.get("n_lemmas", 0),
            "replan_trace": _replan_trace or None}


def _selftest() -> int:
    """Deterministic parse + deanchor checks (no dispatch)."""
    fails = []
    # HERMETIC: rung-adjacency reads the LIVE local cert ledger (box-dependent) — force planner order in
    # the suite (the sledgehammer-live lesson: a default-on signal gating on local state makes tests
    # pass/fail by BOX, not code). Restored on exit.
    _radj_prev = os.environ.get("ZTARE_LEANMILL_RUNG_ADJACENCY")
    os.environ["ZTARE_LEANMILL_RUNG_ADJACENCY"] = "0"

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"); fails.append(name) if not cond else None

    src = ("import Mathlib\n-- a famous comment\ndef Good (n : ℕ) : Prop := n = n\n\n"
           "theorem famous_thm (n : ℕ) : Good n := by sorry\n")
    pre, gd, gc, ban = deanchor(src, "famous_thm", banned_terms=["famous"])
    ok("deanchor strips comments", "famous comment" not in pre)
    ok("deanchor keeps preamble def", "def Good" in pre)
    ok("deanchor extracts goal conclusion", gc == "Good n")
    ok("deanchor ban clause", "famous" in ban)
    raw = ("DECOMP:\n```lean\n"
           "theorem iso_lemma1 : (1:ℕ) = 1 := by sorry\n"
           "theorem iso_chain (n : ℕ) : Good n := by exact iso_lemma1 ▸ rfl\n```\n")
    lemmas, chain, names = _parse_dag(raw, "iso")
    ok("parse: one sorried lemma", len(lemmas) == 1 and names == ["iso_lemma1"])
    ok("parse: chain is sorry-free body", "iso_chain" in chain and "sorry" not in chain.split(":=",1)[-1])
    # _parse_dag behaviour-equivalence NET (#49): locks the parse contract BEFORE the line-249 theorem-regex →
    # decl_blocks migration (which is NOT byte-equivalent, so it needs this net). Also guards the fenced_block (#80)
    # swap of the DECOMP-fence extractor. Cover: multi-lemma, no-fence fallback, echo-guard, empty, fenced-no-thm.
    _raw_multi = ("DECOMP:\n```lean\ntheorem l1 : (1:ℕ)=1 := by sorry\n"
                  "theorem l2 : (2:ℕ)=2 := by sorry\ntheorem chn (n:ℕ) : Good n := by exact l1 ▸ rfl\n```\n")
    _lm, _cm, _nm = _parse_dag(_raw_multi, "iso")
    ok("parse: two sorried lemmas + sorry-free chain", _nm == ["l1", "l2"] and len(_lm) == 2 and "chn" in _cm)
    _ln, _cn, _nn = _parse_dag("theorem l1 : (1:ℕ)=1 := by sorry\ntheorem chn : True := by trivial\n", "iso")
    ok("parse: no DECOMP fence ⇒ scan whole output (legacy fallback preserved)", _nn == ["l1"] and "chn" in _cn)
    ok("parse: echo `<placeholder>` ⇒ empty (the RUNG-A echo-guard)",
       _parse_dag("DECOMP:\n```lean\ntheorem l1 : <statement> := by sorry\n```\n", "iso") == ([], "", []))
    ok("parse: empty input ⇒ empty", _parse_dag("", "iso") == ([], "", []))
    ok("parse: fenced but no theorem ⇒ empty", _parse_dag("DECOMP:\n```lean\njust prose\n```\n", "iso") == ([], "", []))

    # --- STALL→DECOMPOSE-FURTHER re-plan (2026-07-03): the open-rung classifier + the decompose-further cue ---
    _stall_skip = ("closed", "statement_false_confirmed", "budget_exhausted")
    _demo = [{"name": "a", "outcome": "closed"}, {"name": "b", "outcome": "exact_gap"},
             {"name": "c", "outcome": "budget_exhausted"}, {"name": "d", "outcome": "statement_false_confirmed"},
             {"name": "e", "outcome": "open"}]
    ok("stall-harvest: ONLY true-stalled rungs (exact_gap/open) become open_rungs — not closed/false/budget",
       [x["name"] for x in _demo if x["outcome"] not in _stall_skip] == ["b", "e"])
    _ofb = _render_open_rung_feedback([{"name": "b", "outcome": "exact_gap", "lemma": "theorem b : P := by sorry"}])
    ok("stall-harvest: cue tells the planner to DECOMPOSE the stalled rung FURTHER (not retry whole-goal)",
       "DECOMPOSE EACH ONE FURTHER" in _ofb and "`b`" in _ofb and "sorry" in _ofb)
    ok("stall-harvest: false-rung + stall cues are independent (false path byte-unchanged)",
       "FALSE" in _render_false_rung_feedback([{"name": "z", "claim": "cx"}]) and "STALL" in _ofb)

    # --- DETERMINISTIC CONJUNCTIVE DECOMPOSITION (2026-06-25): conjuncts ARE the work-items, no LLM split ---
    _cg = ("theorem amm_cpmm (x y k : Real) (hx : 0 < x) : "
           "x * y = k ∧ 0 < x * y ∧ y = k / x := by sorry")
    _cd2 = derive_conjunctive_dag(_cg, "amm_cpmm")
    ok("det-conj: 3-conjunct target splits into 3 named work-items",
       bool(_cd2) and _cd2["lnames"] == ["amm_cpmm_conj1", "amm_cpmm_conj2", "amm_cpmm_conj3"])
    ok("det-conj: each lemma is a sorried decl carrying the FULL binder telescope",
       bool(_cd2) and all("(x y k : Real) (hx : 0 < x)" in L and L.rstrip().endswith(":= by sorry")
                          for L in _cd2["lemmas"]))
    ok("det-conj: every lemma name is CITED in the chain (passes the audit cite-check)",
       bool(_cd2) and all(ln in _cd2["chain"] for ln in _cd2["lnames"]))
    ok("det-conj: chain concludes the goal G verbatim (passes the conclusion-match)",
       bool(_cd2) and _norm_ws(_lemma_conclusion(_cd2["chain"]))
       == _norm_ws("x * y = k ∧ 0 < x * y ∧ y = k / x"))
    ok("det-conj: no conjunct RESTATES G (non-circular by construction)",
       bool(_cd2) and all(_norm_ws(_lemma_conclusion(L))
                          != _norm_ws("x * y = k ∧ 0 < x * y ∧ y = k / x") for L in _cd2["lemmas"]))
    ok("det-conj: atomic target ⇒ None (no split, agent handles)",
       derive_conjunctive_dag("theorem t (x : Real) : x <= x := by sorry", "t") is None)
    ok("det-conj: top-level ↔ ⇒ None (Iff composite left to the planner)",
       derive_conjunctive_dag("theorem t : A ↔ B := by sorry", "t") is None)
    ok("det-conj: nested ∧ under → ⇒ None (no TOP-level conjunction)",
       derive_conjunctive_dag("theorem t : (A ∧ B) → C := by sorry", "t") is None)
    ok("det-conj: existential witness-sharing conjunction ⇒ None (agent handles)",
       derive_conjunctive_dag("theorem t : ∃ x : Nat, x = x ∧ x = 0 := by sorry", "t") is None)
    _cd3 = derive_conjunctive_dag("theorem t : P ∧ Q := by sorry", "t")
    ok("det-conj: no-binder conjunction builds clean decls",
       bool(_cd3) and _cd3["lemmas"][0] == "theorem t_conj1 : P := by sorry")
    # CORRECTED behaviour (the decl_blocks swap, #49 2026-06-12) — the two latent bugs the differential exposed:
    _ld, _cd, _nd = _parse_dag("DECOMP:\n```lean\ntheorem l1 : (1:ℕ)=1 := by sorry\n"
                               "def helper (n:ℕ) : ℕ := n + 1\ntheorem chn : True := by trivial\n```\n", "iso")
    ok("parse FIX: a helper def between lemmas no longer swallows the sorried lemma",
       _nd == ["l1"] and len(_ld) == 1 and "chn" in _cd)
    _lc, _cc, _nc = _parse_dag("DECOMP:\n```lean\n-- theorem fake_in_comment : False := by sorry\n"
                               "theorem l1 : (1:ℕ)=1 := by sorry\ntheorem chn : True := by trivial\n```\n", "iso")
    ok("parse FIX: a commented-out theorem is no longer a phantom lemma",
       _nc == ["l1"] and "fake_in_comment" not in _nc)

    # v2: Step 2 wired to the CANONICAL IsomorphismLoop (mock query — no live LLM/key in the test).
    _mock = [SurfacedIsomorphism("heat-kernel off-diagonal bound", "spectral geometry",
                                 "Gaussian off-diagonal decay", "maps to the kernel"),
             SurfacedIsomorphism("Noether", "physics", "symmetry→conserved quantity", "")]
    isos = surface_field_analogies("Good n", "theorem t (n:ℕ): Good n", n=2, query=lambda fp, n: _mock)
    ok("surface routes through IsomorphismLoop (canonical engine, not a parallel)",
       len(isos) == 2 and isos[0].field == "spectral geometry")
    hints = _render_iso_hints(isos)
    ok("render hints names the fields", "spectral geometry" in hints and "physics" in hints)
    ok("surface graceful on query error → [] (falls back, never breaks attack)",
       surface_field_analogies("g", "t", query=lambda fp, n: (_ for _ in ()).throw(RuntimeError("x"))) == [])
    # the deanchor prompt still formats with the new {iso_step} slot (no KeyError)
    _p = _DEANCHOR_PROMPT.format(p="iso", binders="", iso_step="X ", goal_concl="Good n",
                                 ban="", preamble="import Mathlib", goal="theorem t : Good n := by sorry")
    ok("deanchor prompt formats with iso_step slot", "DECOMP:" in _p and "X " in _p)

    # GAP 2: transportable-attack catalog renders a domain-general prior (G-function + orthogonality).
    _tech = _render_techniques()
    ok("technique catalog renders G-function + orthogonality attacks",
       "globally-bounded" in _tech and "polynomial method" in _tech)
    ok("technique catalog renders OBSTRUCTION-DESCENT (deanchored-iso meta-move, 2026-06-12)",
       "obstruction-descent" in _tech and "OBSTRUCTION CLASS" in _tech)
    # GAP 1: autonomous-recursion route GATES before any leaf call — depth cap + strong_missing only.
    os.environ["ZTARE_ISO_DEPTH"] = "2"; os.environ["ZTARE_ISO_MAX_DEPTH"] = "2"
    _rc = route_and_solve("s", "t", "theorem t : True := by sorry", lean_root=Path("/tmp"))
    os.environ.pop("ZTARE_ISO_DEPTH", None)
    ok("route depth-cap gates before any leaf call", _rc.get("routed") is False and "depth cap" in _rc.get("reason", ""))
    # DEPTH POLICY decoupling (#82): hard cap (system ceiling) vs soft bound (default/parity) vs adaptive (agent).
    ok("depth policy: default parity = legacy soft bound (recurse below it, stop AT it)",
       iso_should_recurse(1, soft_bound=2, hard_cap=4)[0] is True
       and iso_should_recurse(2, soft_bound=2, hard_cap=4)[0] is False)
    os.environ["ZTARE_ISO_ADAPTIVE_DEPTH"] = "1"
    ok("depth policy: adaptive recurses PAST the soft bound (agent owns the stop, not a fixed 2)",
       iso_should_recurse(2, soft_bound=2, hard_cap=4)[0] is True)
    ok("depth policy: HARD CAP inviolable even in adaptive mode",
       iso_should_recurse(4, soft_bound=2, hard_cap=4)[0] is False
       and "ceiling" in iso_should_recurse(4, soft_bound=2, hard_cap=4)[1])
    ok("depth policy: agent_vote=False stops within the cap (the agentic stop slot)",
       iso_should_recurse(1, soft_bound=2, hard_cap=4, agent_vote=False)[0] is False)
    os.environ.pop("ZTARE_ISO_ADAPTIVE_DEPTH", None)
    _rs = route_and_solve("s", "t", "theorem t : True := by sorry", lean_root=Path("/tmp"))
    ok("route fires on the honest non-closure (no strong_missing pre-gate); attack bails on unlocatable target",
       _rs.get("routed") is True and _rs.get("audited") is False)
    os.environ["ZTARE_LEANMILL_ISO_STRONG_ONLY"] = "1"
    _rg = route_and_solve("s", "t", "theorem t : True := by sorry", lean_root=Path("/tmp"))
    os.environ.pop("ZTARE_LEANMILL_ISO_STRONG_ONLY", None)
    ok("ISO_STRONG_ONLY restores the narrow strong_missing gate",
       _rg.get("routed") is False and "ISO_STRONG_ONLY" in _rg.get("reason", ""))

    # ── Parallel diverse decomposition sampling (best-of-K under a SOUND audit filter) ────────────
    ok("diversity seed 0 is un-primed (K=1 parity)", _diversity_seed(0) == "")
    ok("diversity seed 1 primes a named technique", TRANSPORTABLE_TECHNIQUES[0][0] in _diversity_seed(1))
    ok("diversity seed rotates modulo the catalog",
       _diversity_seed(len(TRANSPORTABLE_TECHNIQUES) + 1) == _diversity_seed(1))
    # CATALOG-SHRINK routing (feature 3): default (dynamic_primary=False) ALWAYS injects the static prior
    # (parity); dynamic-primary SHRINKS it to a fallback (suppressed once the live engine fired).
    ok("iso_catalog parity: static always injected when not dynamic-primary",
       _resolve_iso_catalog(have_dynamic=True, dynamic_primary=False, has_techniques=True) == (True, "both"))
    ok("iso_catalog parity: static-only when no dynamic",
       _resolve_iso_catalog(False, False, True) == (True, "static"))
    ok("iso_catalog shrink: dynamic-primary + dynamic present ⇒ static SUPPRESSED",
       _resolve_iso_catalog(True, True, True) == (False, "dynamic"))
    ok("iso_catalog shrink: dynamic-primary but dynamic EMPTY ⇒ static fallback kept",
       _resolve_iso_catalog(False, True, True) == (True, "static"))
    ok("iso_catalog: techniques disabled + no dynamic ⇒ none",
       _resolve_iso_catalog(False, False, False) == (False, "none"))
    # Fakes (no dispatch / no Lean): the leaf is SOUND only when primed with the first technique (sample i=1),
    # and single-shot (sample 0, un-primed) MISSES it — so best-of-K is what surfaces the sound blueprint.
    _ttech = TRANSPORTABLE_TECHNIQUES[0][0]
    def _fake_gen(ctx):
        fb = ctx.get("feedback", "")
        n = 2 if _ttech in fb else 1   # the primed-sound sample yields a richer (2-lemma) blueprint
        return {"lemmas": [f"L{j}" for j in range(n)], "chain": "c",
                "lnames": [f"L{j}" for j in range(n)], "raw": "", "_fb": fb}
    def _fake_ver(art):
        return _DagVerdict(_ttech in art.get("_fb", ""), "primed-unsound", {"d": 1})
    _aud, _att = _sample_diverse(3, _fake_gen, _fake_ver, {})
    ok("sampling audits the diverse-primed survivor single-shot would miss", len(_aud) == 1)
    ok("sampling tried K distinct seeds", len({a["_fb"] for a, _ in _att}) == 3)
    ok("best-of-K picks the richest sound survivor", len(_richest(_aud)[0]["lemmas"]) == 2)
    ok("richest near-miss selects the most-lemma attempt (refine seed)", len(_richest(_att)[0]["lemmas"]) == 2)
    # K=1 ⇒ a single un-primed sample (byte-identical single-shot input)
    _aud1, _att1 = _sample_diverse(1, _fake_gen, _fake_ver, {})
    ok("K=1 is one un-primed sample (parity)", len(_att1) == 1 and _att1[0][0]["_fb"] == "")
    # ── PARALLEL generation (#117): concurrency + per-sample sessions + order-stable audit ──────
    import time as _tm
    _tags: "list" = []
    def _slow_gen(ctx):
        _tags.append(ctx.get("agent_tag", ""))
        _tm.sleep(0.25)
        return {"lemmas": ["L"], "chain": "c", "lnames": ["L"], "raw": "", "_fb": ctx.get("feedback", "")}
    _t0 = _tm.time()
    _audP, _attP = _sample_diverse(3, _slow_gen, _fake_ver, {})
    _wallP = _tm.time() - _t0
    ok("parallel: 3×0.25s samples overlap (wall < 0.6s)", _wallP < 0.6 and len(_attP) == 3)
    ok("parallel: sample 0 untagged (warm campaign session), 1..K own sessions",
       sorted(_tags) == ["", "iso_s1", "iso_s2"] and "" in _tags)
    ok("parallel: attempts stay in SAMPLE order (deterministic selection)",
       [a["_fb"] for a, _ in _attP] == ["", _diversity_seed(1), _diversity_seed(2)])
    _sv = os.environ.get("ZTARE_ISO_SAMPLES_PARALLEL")
    try:
        os.environ["ZTARE_ISO_SAMPLES_PARALLEL"] = "0"
        _tags.clear()
        _t0 = _tm.time()
        _audS, _attS = _sample_diverse(3, _slow_gen, _fake_ver, {})
        ok("parallel: =0 reverts to sequential (wall ≥ 0.7s, same results shape)",
           (_tm.time() - _t0) >= 0.7 and len(_attS) == 3
           and [a["_fb"] for a, _ in _attS] == [a["_fb"] for a, _ in _attP])
    finally:
        os.environ.pop("ZTARE_ISO_SAMPLES_PARALLEL", None) if _sv is None else os.environ.__setitem__("ZTARE_ISO_SAMPLES_PARALLEL", _sv)
    def _raising_gen(ctx):
        if ctx.get("agent_tag") == "iso_s1":
            raise RuntimeError("boom")
        return {"lemmas": ["L"], "chain": "c", "lnames": ["L"], "raw": "", "_fb": ctx.get("feedback", "")}
    _audE, _attE = _sample_diverse(2, _raising_gen, _fake_ver, {})
    ok("parallel: one raising sample degrades to an empty art, never sinks the round",
       len(_attE) == 2 and "sample dispatch error" in _attE[1][0]["raw"])

    # ── Composite ratification (decomposition→closure assembler) — the PURE assembly ─────────────
    ok("splice: replaces the sorried body with the ratified proof",
       _splice_proof("theorem L1 (n : ℕ) : P n := by sorry", "by exact hp n")
       == "theorem L1 (n : ℕ) : P n := by exact hp n")
    _comp = assemble_composite_proof(
        "import Mathlib\n\ndef P : ℕ → Prop := fun _ => True",
        ["theorem L1 : P 0 := by sorry", "theorem L2 : P 1 := by sorry"],
        ["L1", "L2"],
        {"L1": "by trivial", "L2": "by trivial"},
        "theorem goalG : P 0 ∧ P 1 := ⟨L1, L2⟩")
    ok("assemble: proven lemmas spliced + chain appended, sorry-free",
       "theorem L1 : P 0 := by trivial" in _comp and "theorem L2 : P 1 := by trivial" in _comp
       and "theorem goalG : P 0 ∧ P 1 := ⟨L1, L2⟩" in _comp and "sorry" not in _comp
       and _comp.index("L1 : P 0") < _comp.index("goalG"))   # lemmas BEFORE the chain
    ok("assemble: missing a lemma proof → '' (cannot close the parent)",
       assemble_composite_proof("", ["theorem L1 : P := by sorry"], ["L1"], {}, "theorem g : P := L1") == "")
    ok("assemble: a proof still carrying sorry → '' (never an unsound composite)",
       assemble_composite_proof("", ["theorem L1 : P := by sorry"], ["L1"], {"L1": "by sorry"},
                                "theorem g : P := L1") == "")
    # DEFENSE-IN-DEPTH: composite_ratify re-checks the chain proves the ORIGINAL goal's conclusion; a chain
    # proving a DIFFERENT statement is refused BEFORE the kernel (the conclusion check precedes the compile,
    # so this is offline-testable — no Lean).
    _src_cr = ("import Mathlib\n\ndef P : ℕ → Prop := fun _ => True\ndef Q : ℕ → Prop := fun _ => True\n\n"
               "theorem tgt (n : ℕ) : P n := by sorry")
    _bad = composite_ratify(
        {"lemmas": ["theorem L1 : P 0 := by sorry"], "lnames": ["L1"],
         "chain": "theorem ch (n : ℕ) : Q n := trivial", "audited": True},
        _src_cr, "tgt", {"L1": "by trivial"}, lean_root=Path("/tmp"))
    ok("composite_ratify refuses a chain proving a DIFFERENT statement (pre-kernel)",
       _bad.get("parent_closed") is False and "DIFFERENT statement" in _bad.get("reason", ""))

    # ── ASSEMBLY-REPAIR (#160): sub-rungs proved but the UP-FRONT chain didn't assemble → re-chain with the
    #    proven lemmas citable, re-ratified by the SAME gate. Hermetic: mock dispatch + mock ratify (no Lean). ──
    _rep_result = {"lemmas": ["theorem L1 : P 0 := by sorry", "theorem L2 : P 1 := by sorry"],
                   "lnames": ["L1", "L2"], "chain": "theorem goalG : P 0 ∧ P 1 := by sorry"}  # FAILED chain
    _seen: dict = {}
    def _good_dispatch(prompt, *, repo=None, timeout=None):  # noqa: E306 — agent returns a NEW sorry-free chain
        _seen["prompt"] = prompt
        return "theorem goalG : P 0 ∧ P 1 := ⟨L1, L2⟩\n"
    def _ratify_ok(result, src, tgt, proofs, *, lean_root, timeout_s, original_source=None):  # noqa: E306
        _seen["chain"] = result.get("chain")
        return {"parent_closed": "⟨L1, L2⟩" in (result.get("chain") or ""), "target": "goalG"}
    _r = _assembly_repair(_rep_result, "src", "goalG", {"L1": "by trivial", "L2": "by trivial"},
                          lean_root=Path("/tmp"), dispatch_fn=_good_dispatch, ratify_fn=_ratify_ok)
    ok("assembly-repair: a NEW sorry-free chain re-ratifies ⇒ parent CLOSES (banked rungs assembled)",
       _r.get("parent_closed") is True and _r.get("assembly_repaired") is True
       and "⟨L1, L2⟩" in _seen.get("chain", ""))
    ok("assembly-repair: prompt offers the proven lemmas BY NAME (citable, not re-proven)",
       "ALREADY PROVEN" in _seen.get("prompt", "") and "`L1`" in _seen["prompt"] and "`L2`" in _seen["prompt"])
    _seen2: dict = {}
    def _bad_dispatch(prompt, *, repo=None, timeout=None):  # noqa: E306 — agent yields no usable chain
        return "no fenced block, just prose"
    def _ratify_spy(result, src, tgt, proofs, **kw):  # noqa: E306
        _seen2["called"] = True; return {"parent_closed": True}
    _rb = _assembly_repair(_rep_result, "src", "goalG", {"L1": "by trivial"},
                           lean_root=Path("/tmp"), dispatch_fn=_bad_dispatch, ratify_fn=_ratify_spy)
    ok("assembly-repair: no NEW chain ⇒ parent stays open, gate never consulted (no false close)",
       _rb.get("parent_closed") is False and not _seen2.get("called"))

    # ── SITUATION-ROUTED move surfacing (mechanization-placement, not prompt ballast): the plan prompt
    #    surfaces the move SUBSET applicable to the situation; data-driven from _PLAN_ACTIONS/_PLAN_DAG_FORMAT. ──
    _full = _plan_choice_prefix("proof_stuck")
    ok("plan: proof_stuck surfaces the FULL menu (byte-parity)",
       all(a in _full for a in _PLAN_ACTIONS) and "TRANSPORT   →" in _full and "ABDUCE" in _full)
    _weak = _plan_choice_prefix("target_weakened")
    ok("plan: target_weakened surfaces only the recourse SUBSET (no ballast)",
       all(a in _weak for a in ("ABDUCE", "DECOMPOSE", "SPECIALIZE"))
       and "TRANSPORT" not in _weak and "GENERALIZE" not in _weak and "FALSIFY" not in _weak)
    ok("plan: subset trims the DAG-format guidance too (config is data-driven)",
       "TRANSPORT   →" not in _weak and "ABDUCE      →" in _weak)
    ok("plan: enable/disable tune the subset per call",
       "ABDUCE" not in _plan_choice_prefix("proof_stuck", disable=["ABDUCE"])
       and "TRANSPORT" in _plan_choice_prefix("target_weakened", enable=["TRANSPORT"]))

    # #143/Layer-B — RE-PLAN ON A CONFIRMED-FALSE RUNG. A planner sub-lemma proven FALSE (a dropped hypothesis)
    # must feed the agent's correction back to a bounded re-decomposition, not stall. Inject attack/solve/triage
    # so the loop is exercised with NO LLM/Lean; save+restore the patched globals (hermetic).
    # PATCH `globals()` DIRECTLY, not an `import … as _self` copy: under `python -m` this module runs as
    # `__main__`, so `route_and_solve` resolves `attack`/`solve_decomposition`/`triage` from THIS namespace —
    # patching a re-imported copy would miss it and dispatch the REAL planner (codex) for 180s. (Learned the
    # hard way.) Save+restore here; the finally below restores from `_g` (same globals()).
    _g = {k: globals().get(k) for k in ("attack", "solve_decomposition", "triage")}
    _envk = ("ZTARE_LEANMILL_ISO_ROUTE", "ZTARE_LEANMILL_REPLAN_FALSE_RUNG", "ZTARE_LEANMILL_ISO_STRONG_ONLY")
    _envp = {k: os.environ.get(k) for k in _envk}
    try:
        os.environ["ZTARE_LEANMILL_ISO_ROUTE"] = "1"
        os.environ["ZTARE_LEANMILL_REPLAN_FALSE_RUNG"] = "1"
        os.environ["ZTARE_LEANMILL_ISO_STRONG_ONLY"] = "0"
        _seen = {"notes": [], "solves": 0}

        def _fake_attack(source, target_name, *, lean_root, timeout_s=180, notes=None, **kw):
            _seen["notes"].append(notes or "")
            return {"audited": True, "lemmas": ["theorem iso_lemma1 : P := by sorry"],
                    "lnames": ["iso_lemma1"], "chain": "..."}

        def _fake_solve(result, source, target_name, *, lean_root, timeout_s=400, substrate=None,
                        notes=None, _depth=0):
            _seen["solves"] += 1
            if _seen["solves"] == 1:
                return {"solved": False, "n_closed": 0, "n_lemmas": 1,
                        "lemmas": [{"name": "iso_lemma1", "outcome": "statement_false_confirmed"}],
                        "false_rungs": [{"name": "iso_lemma1", "claim": "needs constantCoeff(q f) ≠ 0"}]}
            return {"solved": True, "n_closed": 1, "n_lemmas": 1, "parent_closed": True,
                    "lemmas": [{"name": "iso_lemma1", "outcome": "closed"}]}
        globals()["triage"] = lambda goal, source_hint=None: type("T", (), {"target_strength": "strong_missing"})()
        globals()["attack"], globals()["solve_decomposition"] = _fake_attack, _fake_solve
        _ro = route_and_solve("import Mathlib\ntheorem t : P := by sorry", "t", "P",
                              lean_root=Path("/tmp"), timeout_s=600)
        ok("replan: re-decomposes once on a confirmed-false rung (2 attacks, 2 solves)",
           len(_seen["notes"]) == 2 and _seen["solves"] == 2)
        ok("replan: round-1 planner gets the false-rung correction; round-0 is clean",
           "PRIOR-DECOMPOSITION DEFECT" in _seen["notes"][1] and "PRIOR-DECOMPOSITION DEFECT" not in _seen["notes"][0])
        ok("replan: parent closes after the corrected decomposition",
           bool((_ro.get("solution") or {}).get("parent_closed")) and bool(_ro.get("replan_trace")))
        os.environ["ZTARE_LEANMILL_REPLAN_FALSE_RUNG"] = "0"
        _seen["notes"].clear(); _seen["solves"] = 0
        route_and_solve("import Mathlib\ntheorem t : P := by sorry", "t", "P", lean_root=Path("/tmp"), timeout_s=120)
        ok("replan: =0 ⇒ single-shot, no re-plan (A/B baseline)", len(_seen["notes"]) == 1 and _seen["solves"] == 1)
    finally:
        for k, v in _g.items():
            if v is not None:
                globals()[k] = v
        for k in _envk:
            if _envp[k] is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = _envp[k]

    # ── EMBEDDING-based premise steering for the PLANNER (semantic shelf) — hermetic: patch the shelf's
    #    own_ledger_hits + _cached_embedder so NO network/API key/ledger is touched. The block must (a) name
    #    PROVEN rungs as the advisory, (b) be byte-parity '' under the =0 A/B knob, (c) graceful-degrade to ''
    #    on any retrieval failure, (d) emit nothing when no proven hit / empty goal. ──
    import ztare.leanmill.semantic_premise_shelf as _sps_mod
    _sps_saved = (_sps_mod.own_ledger_hits, _sps_mod._cached_embedder)
    _shelf_prev = os.environ.get("ZTARE_LEANMILL_PLANNER_SEMANTIC_SHELF")
    try:
        _sps_mod._cached_embedder = lambda: (lambda q: [1.0, 0.0])   # no real embedder
        _sps_mod.own_ledger_hits = lambda query, **kw: (
            [{"source": "own_ledger", "name": "banked_residue_lemma", "kind": "proven_rung",
              "score": 0.91, "preview": "theorem banked_residue_lemma : residue p = 0"},
             {"source": "own_ledger", "name": "some_gap", "kind": "open_gap",
              "score": 0.88, "preview": "missing partial-fraction API"}], 2, None)
        os.environ.pop("ZTARE_LEANMILL_PLANNER_SEMANTIC_SHELF", None)   # default-on
        _blk = _render_semantic_shelf_block("residue vanishing at a simple root")
        ok("semantic shelf: default-on renders the PROVEN-LEMMA advisory, names the banked rung",
           "SEMANTICALLY-RELATED PROVEN LEMMAS" in _blk and "banked_residue_lemma" in _blk)
        ok("semantic shelf: open-gap hits are NOT surfaced as planner attachment sites (proven only)",
           "some_gap" not in _blk and "partial-fraction" not in _blk)
        os.environ["ZTARE_LEANMILL_PLANNER_SEMANTIC_SHELF"] = "0"
        ok("semantic shelf: =0 is byte-parity (empty block, A/B off)",
           _render_semantic_shelf_block("residue vanishing at a simple root") == "")
        os.environ.pop("ZTARE_LEANMILL_PLANNER_SEMANTIC_SHELF", None)
        ok("semantic shelf: empty goal ⇒ empty block (no ballast)",
           _render_semantic_shelf_block("") == "" and _render_semantic_shelf_block("   ") == "")
        _sps_mod.own_ledger_hits = lambda query, **kw: (_ for _ in ()).throw(RuntimeError("embedder dead"))
        ok("semantic shelf: graceful-degrade to '' on any retrieval failure (never breaks assembly)",
           _render_semantic_shelf_block("residue") == "")
        _sps_mod.own_ledger_hits = lambda query, **kw: ([], 0, "no GOOGLE_API_KEY")
        ok("semantic shelf: no proven hits ⇒ empty block (parity)",
           _render_semantic_shelf_block("residue") == "")
    finally:
        _sps_mod.own_ledger_hits, _sps_mod._cached_embedder = _sps_saved
        if _shelf_prev is None:
            os.environ.pop("ZTARE_LEANMILL_PLANNER_SEMANTIC_SHELF", None)
        else:
            os.environ["ZTARE_LEANMILL_PLANNER_SEMANTIC_SHELF"] = _shelf_prev

    if _radj_prev is None:
        os.environ["ZTARE_LEANMILL_RUNG_ADJACENCY"] = "0"   # keep hermetic until process exit (suite-local)
    else:
        os.environ["ZTARE_LEANMILL_RUNG_ADJACENCY"] = _radj_prev
    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
