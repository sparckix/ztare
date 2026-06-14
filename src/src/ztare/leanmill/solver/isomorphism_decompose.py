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
    ("spectral gap / eigenvalue separation",
     "bound a combinatorial or dynamical quantity by the second eigenvalue (expander mixing, Cheeger)"),
    ("duality certificate (LP/SDP)",
     "prove an extremal bound by exhibiting the DUAL feasible certificate (LP/SDP duality, the dual witness)"),
    ("compactness ⇒ uniformity",
     "upgrade a pointwise/local bound to a uniform/global one via a compactness or limiting argument"),
    ("probabilistic existence",
     "prove existence via a positive-probability / first-moment / Lovász-local-lemma argument"),
)


def _render_techniques(k: int = 4) -> str:
    """Render the top transportable-attack techniques as a domain-general prior for the deanchor prompt."""
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

from ztare.leanmill.solver.prompts import DEANCHOR_PROMPT as _DEANCHOR_PROMPT  # canonical prompts home (#49; moved verbatim)


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


def _agent_plan_on() -> bool:
    # DEFAULT-ON (operator 2026-06-10): the agent ORCHESTRATES the structural action (decompose / specialize /
    # generalize / abduce / TRANSPORT) — declares PLAN: <ACTION> and produces the action-appropriate, kernel-
    # audited DAG — rather than the planner hardcoding decompose. =0 opts out (the byte-parity decompose-only arm
    # for A/B). Pairs with ZTARE_LEANMILL_AGENT_TOOLS (also default-on) so TRANSPORT can reach the exogenous tools.
    return os.environ.get("ZTARE_LEANMILL_AGENT_PLAN", "1") != "0"


def _plan_choice_prefix() -> str:
    opts = "\n".join(f"  {a}: {d}" for a, d in _PLAN_ACTIONS.items())
    return ("FIRST, choose the single best STRUCTURAL ACTION for this goal and state it on ONE line as "
            "`PLAN: <ACTION> — <one-line reason>`, where <ACTION> is EXACTLY one of:\n" + opts +
            "\nThen PRODUCE THE ARTIFACT FOR YOUR CHOSEN ACTION in the DECOMP format below — a sub-lemma DAG "
            "whose sorry-free chain proves the goal G. The SAME kernel audit (sorry-free + non-circular + "
            "every-lemma-load-bearing + proves-G) gates every action, so your CHOICE drives WHICH artifact you "
            "build (this IS the dispatch — it is no longer recorded-and-ignored):\n"
            "  • DECOMPOSE   → the intermediate sub-lemmas L₁…Lₙ, chain proves G from them.\n"
            "  • SPECIALIZE  → FIRST lemma = the STRONGER statement B; chain proves G from B.\n"
            "  • GENERALIZE  → FIRST lemma = the MORE GENERAL H; chain instantiates G from H.\n"
            "  • ABDUCE      → FIRST lemma = the missing PREMISE A; chain proves G from A + the goal's context.\n"
            "  • TRANSPORT   → FIRST lemma = the exogenous-compute fact (a witness / hammered premise); chain closes G with it.\n"
            "(FALSIFY and SOLVE_DIRECT do NOT fit a proves-G DAG — FALSIFY routes to the falsify move, "
            "SOLVE_DIRECT means the goal needs no decomposition; declare either only if it genuinely applies, "
            "else pick a DAG action above.)\n\n")


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
    nocomment = re.sub(r"/-.*?-/", " ", re.sub(r"(?m)--[^\n]*", "", source), flags=re.S)
    blocks = dict(_decl_blocks(nocomment))
    goal_decl = next((blocks[n] for n in blocks if n == target_name or n.endswith("." + target_name)), "")
    preamble = re.split(r"(?m)^(?:theorem|lemma)\s+" + re.escape(target_name) + r"\b", nocomment, maxsplit=1)[0].rstrip()
    sig = _signature(goal_decl)
    j = sig.find(":") if ":" not in (target_name) else -1
    goal_concl = _lemma_conclusion(goal_decl)
    ban = ""
    if banned_terms:
        ban = " Do NOT mention or cite any of: " + ", ".join(t for t in banned_terms if t) + "."
    return preamble, goal_decl, goal_concl, ban


def _parse_dag(raw: str, prefix: str) -> "tuple[list[str], str, list[str]]":
    """Parse DECOMP: fenced block → (sorried lemma blocks, chain block, lemma names). The chain is the
    block whose body is NOT `:= by sorry` (it proves the goal); the rest are the sorried lemmas."""
    m = re.search(r"DECOMP:\s*```(?:lean)?\s*\n(.*?)```", raw, re.DOTALL)
    body = m.group(1) if m else raw
    thms = re.findall(r"(?s)((?:theorem|lemma)\s+(\S+).*?:=\s*by\b.*?)(?=\n(?:theorem|lemma)\s|\Z)", body)
    lemmas, names, chain = [], [], ""
    for block, name in thms:
        b = block.strip()
        if re.search(r":=\s*by\s+sorry\s*$", b) or (":= by sorry" in b and "sorry" in b.split(":=")[-1] and "\n" not in b.split(":= by")[-1].strip()):
            lemmas.append(b); names.append(name)
        elif "sorry" not in b.split(":=", 1)[-1]:
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
    Sequential dispatch (best-of-k is about SELECTION, not timing; concurrent dispatch is a later optimization
    bounded by subscription rate limits)."""
    audited, attempts = [], []
    for i in range(max(1, int(k))):
        ctx = dict(base_ctx or {})
        ctx["feedback"] = (base_ctx or {}).get("feedback", "") + _diversity_seed(i)
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
        from ztare.formal.lean_check_server import ensure_server as _ensure, default_socket_path as _dsock
        _repo = Path(__file__).resolve().parents[4]
        _sock = _ensure(str(lean_root)) or _dsock(str(lean_root))
        _probe = _probe_dir(lean_root) / "IsoDagProbe.lean"
        _leancheck = (f"PYTHONPATH={_repo}/src {_sys.executable} -m ztare.formal.lean_check_server "
                      f"--check {_sock} {_probe}")
        _warmcheck_block = (
            "FAST VERIFICATION — use the WARM checker, do NOT cold-compile: to typecheck your decomposition, "
            f"write the full DAG (sorried lemmas + the sorry-free chain, with `import Mathlib` first) to:\n  {_probe}\n"
            "then check it WARM (~0.1s; prints the EXACT Lean errors or 'OK'):\n  "
            f"{_leancheck}\n"
            "Do NOT run `lake env lean` — a cold Mathlib reload takes ~90s and will exhaust your time budget "
            "before you answer. Iterate write→warm-check→fix until the DAG typechecks (the intermediate lemmas "
            "stay `:= by sorry`; the CHAIN must be sorry-free), THEN emit the DECOMP block. The kernel re-audits "
            "your DAG downstream — this warm check just lets you CONVERGE fast within budget.\n\n")
    except Exception:  # noqa: BLE001 — never let warm-check setup break planning
        _warmcheck_block = ""

    def _generate(ctx):
        fb = (ctx or {}).get("feedback", "")
        prompt = _DEANCHOR_PROMPT.format(p="iso", binders=(binders + " " if binders else ""),
                                         iso_step=_iso_step,
                                         goal_concl=goal_concl, ban=ban + fb, preamble=preamble, goal=goal_decl)
        if _agent_plan_on():                     # #74 step 1: surface the structural-action choice (default-off = parity)
            prompt = _plan_choice_prefix() + prompt
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
        _plan_budget = _clamp("planner", timeout_s)
        print(f"[iso] planner dispatch (budget {_plan_budget}s) for: {goal_concl[:70]}", flush=True)
        try:
            raw = dispatch_fn(prompt, repo=lean_root, timeout=_plan_budget) or ""
        except Exception as e:  # noqa: BLE001
            return {"lemmas": [], "chain": "", "lnames": [], "raw": f"dispatch error: {e!r}"}
        lemmas, chain, lnames = _parse_dag(raw, "iso")
        out = {"lemmas": lemmas, "chain": chain, "lnames": lnames, "raw": raw}
        if _agent_plan_on():                     # #74 step 2: the chosen action DROVE the artifact (the prefix asked for the action-appropriate proves-G DAG); record it for the lift telemetry
            out["plan_action"], out["plan_reason"] = parse_plan_action(raw)
            _record_plan_choice(out["plan_action"], out["plan_reason"], goal_concl)
        return out

    def _verify(art):
        if not art.get("lemmas") or not art.get("chain"):
            return _DagVerdict(False, "no parseable lemma DAG", {})
        passed, v = decomposition_dag_audit(art["lemmas"], art["chain"], art["lnames"], lean_root,
                                            max(120, timeout_s), preamble=preamble, goal_conclusion=goal_concl)
        return _DagVerdict(passed, (v.get("passed") if passed else v.get("killed")) or "", v)

    def _refine_ctx(art, v, ctx):
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

    # PARALLEL DIVERSE SAMPLING (ZTARE_ISO_SAMPLES>1; default 1 = byte-identical single-shot below): a breadth
    # leg over K technique-diverse decompositions, audited, survivors pursued; composes with refine on a miss.
    n_samples = int(os.environ.get("ZTARE_ISO_SAMPLES", "1"))
    if n_samples > 1:
        audited, attempts = _sample_diverse(n_samples, _generate, _verify, {})
        if audited:  # best-of-K: the richest SOUND blueprint
            art, v = _richest(audited)
            return {"audited": True, "lemmas": art.get("lemmas"), "chain": art.get("chain"),
                    "lnames": art.get("lnames"), "verdict": v.detail, "rounds": len(attempts),
                    "n_samples": n_samples, "n_audited": len(audited), "iso_source": _iso_source,
                    "raw_tail": (art.get("raw") or "")[-200:], "notes_used": bool(_notes_block)}
        # none of the K audited → seed the refine loop with the BEST near-miss's targeted feedback (compose:
        # explore K structures, then fix the most-sound one) instead of regenerating blind.
        seed_ctx = _refine_ctx(*_richest(attempts), {}) if attempts else {}
        art, verdict, trace = loop.run(seed_ctx)
        return {"audited": verdict.accepted, "lemmas": art.get("lemmas"), "chain": art.get("chain"),
                "lnames": art.get("lnames"), "verdict": verdict.detail, "rounds": len(attempts) + len(trace),
                "n_samples": n_samples, "n_audited": 0, "iso_source": _iso_source,
                "raw_tail": (art.get("raw") or "")[-200:], "notes_used": bool(_notes_block),
                **({} if verdict.accepted else {"killed": verdict.reason})}

    art, verdict, trace = loop.run({})
    return {"audited": verdict.accepted, "lemmas": art.get("lemmas"), "chain": art.get("chain"),
            "lnames": art.get("lnames"), "verdict": verdict.detail, "rounds": len(trace),
            "iso_source": _iso_source, "raw_tail": (art.get("raw") or "")[-200:], "notes_used": bool(_notes_block),
            **({} if verdict.accepted else {"killed": verdict.reason})}


def solve_decomposition(result: dict, source: str, target_name: str, *, lean_root: Path,
                        timeout_s: int = 400, substrate=None, notes: "str | None" = None) -> dict:
    """CONSISTENCY: route an AUDITED decomposition's lemmas through the ONE governed solver entry
    (`solve_adhoc`) — the SAME interface ad-hoc / autoformalize / residual-C / proof_repair use. No
    parallel solve, no parallel governance: each lemma Lᵢ is a target `preamble + Lᵢ` solved + ratified
    by the ONE kernel. Returns {solved, n_closed, lemmas:[{name, outcome}]}. This makes iso-decompose a
    target-PRODUCER feeding the canonical kernel, not a separate lane. (The loop never closes the goal G
    itself — G closes only if its sub-lemmas close and the chain is then discharged through the kernel.)"""
    if not result.get("audited"):
        return {"solved": False, "reason": "decomposition not audited — nothing to solve"}
    from ztare.leanmill.solver.solver_core import solve_adhoc  # lazy: avoid import cycle
    preamble, _gd, _gc, _ban = deanchor(source, target_name)
    out: list = []
    proofs: dict = {}   # lname → ratified proof body (captured DIRECTLY from each solve result)
    for lemma, lname in zip(result.get("lemmas") or [], result.get("lnames") or []):
        src = preamble.rstrip() + "\n\n" + lemma.strip() + "\n"
        try:
            r = solve_adhoc(lname, src, "", substrate=substrate, mode="dag_search", timeout_s=timeout_s,
                            notes=notes)
            r0 = (r.get("results") or [{}])[0]
            outcome = r0.get("outcome")
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
    return res


def _splice_proof(lemma: str, proof: str) -> str:
    """Replace a sorried lemma's body with its ratified proof (split on the FIRST top-level `:=`)."""
    head = lemma.split(":=", 1)[0].rstrip()
    return f"{head} := {proof.strip()}"


def assemble_composite_proof(preamble: str, lemmas, lnames, lemma_proofs: dict, chain: str) -> str:
    """PURE (no Lean): splice each lemma's ratified proof in place of its sorry, then append the CHAIN (which
    proves G using the lemma names) — a single sorry-free Lean source proving G. '' if any lemma's proof is
    missing / itself contains sorry, or the chain is empty (⇒ cannot assemble; parent stays open). The kernel
    ratifies the result downstream — this only BUILDS the candidate."""
    parts = [preamble.rstrip()] if (preamble or "").strip() else []
    for lemma, lname in zip(lemmas or [], lnames or []):
        proof = (lemma_proofs or {}).get(lname)
        if not proof or "sorry" in proof or "admit" in proof:
            return ""
        parts.append(_splice_proof(lemma, proof))
    if not (chain or "").strip() or not parts:
        return ""
    parts.append(chain.strip())
    return "\n\n".join(parts) + "\n"


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


def route_and_solve(source: str, target_name: str, goal: str, *, lean_root: Path,
                    timeout_s: int = 400, substrate=None, notes: "str | None" = None) -> dict:
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
    depth = int(os.environ.get("ZTARE_ISO_DEPTH", "0"))
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
    res = attack(source, target_name, lean_root=lean_root, timeout_s=timeout_s, notes=notes)
    if not res.get("audited"):
        return {"routed": True, "audited": False, "killed": res.get("killed"),
                "decomposition": res, "depth": depth}
    _prev = os.environ.get("ZTARE_ISO_DEPTH")
    os.environ["ZTARE_ISO_DEPTH"] = str(depth + 1)   # children recurse at depth+1, bounded by the cap
    try:
        sol = solve_decomposition(res, source, target_name, lean_root=lean_root,
                                  timeout_s=timeout_s, substrate=substrate, notes=notes)
    finally:
        if _prev is None:
            os.environ.pop("ZTARE_ISO_DEPTH", None)
        else:
            os.environ["ZTARE_ISO_DEPTH"] = _prev
    return {"routed": True, "audited": True, "decomposition": res, "solution": sol, "depth": depth,
            "rungs_closed": sol.get("n_closed", 0), "rungs_total": sol.get("n_lemmas", 0)}


def _selftest() -> int:
    """Deterministic parse + deanchor checks (no dispatch)."""
    fails = []

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

    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
