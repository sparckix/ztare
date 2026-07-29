"""GP-246 — Governed DAG proof-search over a proof-obligation DAG.

This is the v2 EVOLUTION of the fixed Layer-2→5 cascade in the solver lane
(`scripts/public/control/leanmill/solver_lane_worker.py`). The cascade stays as
the measured BASELINE; this module is the optimization OVER it and earns
adoption only by closing ≥ the cascade's closures on the SAME rows (see the
GP-246 seam). It is NOT a smarter prover — the LLM/hammer/frontier prover stays
a subordinate move-generator and the defensible value is the mechanization-placement
governance: ex-ante typed contract → typed moves → kernel-ratified credit →
matched-negative-control → residual→lever → no-false-closure.

KEY ARCHITECTURE — the search PROPOSES, governance RATIFIES.
  * The search NEVER decides a closure itself. It runs a typed MOVE via an
    injected `move_runner` callable and inspects the `MoveResult` the runner
    returns. The runner is responsible for kernel-verify + matched-negative-
    control (it reuses the worker's `_verify_compile` / `_validate_against_contract`
    / `_is_compile_ok` — this module reimplements NONE of that). A node is set
    `closed` ONLY when the MoveResult carries `kernel_clean=True AND mnc_passed
    =True` (the no-false-closure invariant; a `sorry` proof has kernel_clean
    False so it can never close).
  * In production the worker binds `move_runner` to its real move generators.
    In tests a MOCK runner returns scripted results, so the search itself is
    unit-testable with zero Lean/LLM.

SUBSTRATE-AGNOSTIC: this module carries NO NS / Clay / PDE logic. Any substrate
specifics enter only through the contract (`build_solver_action_contract`) and
the provider registry — never here.

Offline self-test:  python -m ztare.leanmill.solver.governed_dag_search --selftest
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Obligation DAG
# ─────────────────────────────────────────────────────────────────────────────

# Node kinds and statuses are the GP-246 typed vocabulary. Any new value here is
# a schema change → update the seam (per its `update_post`).
NODE_KINDS = ("root_goal", "sub_goal", "helper_lemma", "gap", "falsifier")
# "rung" (2026-06-05): a SPECIALIZE move produced a kernel-verified WEAKER special case G' (G⇒G'). This
# is honest partial progress on a hard/open goal — NOT a closure (G stays open as the documented residual)
# and NOT a gap (real verified progress was made). A distinct typed terminal so it can't be confused with
# either; resolved by `residual_to_lever`.
NODE_STATUSES = ("open", "closed", "exact_gap", "falsifier", "rung", "retired", "deferred")

# Ordered move menu (cheap → expensive). The policy walks this order.
MOVE_NATIVE_HAMMER = "native_hammer"        # FREE, deterministic tactic cascade
MOVE_CLAUDE_WARM = "claude_warm"            # iterative warm agent
MOVE_CLAUDE_WARM_REFINE = "claude_warm_refine"  # gap-refine retry of a warm near-miss (TRACKED-only,
#   NOT in MOVE_ORDER ⇒ not policy-selectable). It exists so the gap-refine outcomes the worker records
#   under provider `claude_opus_warm_refine` ENTER calibration as their own arm instead of being dropped
#   (the loss = warm's near-miss-then-refined rows vanishing). Its posterior = P(close | near-miss + the
#   2nd refine budget unit ran) — the signal for whether gap-refine earns its budget (#4 / task #30).
MOVE_COLD_SHOT = "cold_shot_fanout"        # one-shot multi-provider fan-out
MOVE_FRONTIER = "external_frontier_prover"  # provider-agnostic frontier slot
# INVERT leg — goal-directed lemma conjecturing: instead of forward-proving the whole
# goal, propose the intermediate lemma that would discharge it and recurse. GENERAL
# (any goal shape via `have`/`suffices`), unlike the ∧-only structural split. The
# runner returns the conjectured statement in `new_sub_goal_text`; the search spawns it.
#
# The conjecture is NOT limited to decomposing the given statement. The runner may
# INVENT new mathematical machinery to make solving tractable — a stronger
# generalization that's easier to prove (the "generalization is easier" phenomenon), a
# fresh auxiliary construction/witness, a reformulation, a new invariant. The engine is
# deliberately INDIFFERENT to whether the conjectured math is conventional or unusual:
# the kernel + matched-negative-control are the sole arbiters (a conjecture earns its
# place by being VERIFIED and advancing the goal, not by looking familiar). Verified
# inventions are banked in the proof cache and compound — a growing library of
# solving-useful lemmas, conventional or not.
MOVE_CONJECTURE = "conjecture_lemma"
# ── Strategist moves (wm3zp587b synthesis, 2026-06-05) — the rest of Pólya's playbook ─────────────────
# The base menu above is a COMPILER (attack G as-stated). These two are STRATEGIST moves that change the
# battlefield, sharing ONE kernel-decidable soundness contract with the rest of the menu:
#   SPECIALIZE — down ↓: prove a WEAKER provable special case G' + the `G ⇒ G'` witness. Verified RUNG
#                (honest partial progress on a hard/open goal); NEVER closes G (no false-closure surface).
#   GENERALIZE — up ↑: close G via an internal induction-strengthening (`have` a STRONGER fact, then
#                instantiate). It IS a closure of G, so it routes through the SAME governance as a direct
#                move (kernel + MNC + statement_integrity) — the strengthening lives in a `have`, the
#                ratified theorem is G unaltered. The one move that CLOSES G when it fires.
# Both are NON_COMMUTATIVE (structure-changing) and ship DEFAULT-OFF: they are NOT in the default
# MOVE_ORDER walk; `move_policy` offers them only when their env flag is set AND the node is STUCK
# (cheap+direct moves exhausted), so default behaviour is byte-identical (no Barrington blanket-reorder).
MOVE_SPECIALIZE = "specialize"
MOVE_GENERALIZE = "generalize"
MOVE_FALSIFY = "falsify"                     # the Invert leg: pursue a kernel-checked proof of ¬G (feeds
#   the existing-but-unfed falsifier sink). A falsified target is a first-class outcome on the OPEN regime.
MOVE_TACTIC_STEP = "tactic_step"             # M3 v2: per-step agentic search — the leaf emits ONE tactic at
#   a time vs a PERSISTENT proofState built from OUR decl (no file edit; the leaf reacts to each live goal).
#   REPL-closed is re-verified through the SAME governance. WIRED: conjecture.tactic_step_solve + runner.
MOVE_CORROBORATE = "corroborate"             # Popper DUAL of falsify: refute a CONSEQUENCE K of G
#   (prove G→K ∧ ¬K ⟹ ¬G by modus tollens — often easier than direct ¬G). Feeds the SAME falsifier sink via
#   conjecture.LeanConsequenceCorroborator (identical gate to MOVE_FALSIFY; never closes G).
MOVE_WITNESS_TRANSPORT = "witness_transport"  # CLOSURE move, gate-triggered: for a non-linear existential the
#   native cascade can't close, SymPy FINDS the witness → inject `refine ⟨w,?_⟩ <;> norm_num` → the kernel
#   PROVES it (witness-transport.solve_witness). Same _verify_compile+_govern closure gate as warm/generalize.
MOVE_SLEDGEHAMMER = "sledgehammer"           # PREMISE-RETRIEVAL closure move: translate G to Isabelle/HOL, run
#   `sledgehammer` (EXTERNAL server) → its dependency trace → map Isabelle fact names to Mathlib (HALLUCINATES)
#   → kernel `#check`-validate each (drop hallucinations) → inject the survivors as exact?/aesop premises. Same
#   _verify_compile+_govern closure gate as warm/generalize. FAIL-CLOSED (no-op) when no Isabelle server is set.
MOVE_REFLECTION = "reflection"               # COMPUTATIONAL closure move: the leaf writes a decidable
#   `def check` + `theorem check_sound : check args = true → G` + a closing body; the helper decls prepend
#   to the goal stub (added decls statement_integrity allows) and the kernel PROVES G via `by decide` —
#   same _verify_compile+_govern closure gate as generalize. native_decide is fail-closed (axiom). Finite/
#   decidable goals only. WIRED: reflection.reflection_solve + runner.
MOVE_ABDUCE = "abduce"                        # SMT-GROUNDED conjecture: for a decidable-arithmetic goal,
#   cvc5 `(get-abduct)` derives the minimal missing premise A; abduce_seed wraps it as a targeted prompt
#   override for conjecture_generate (replaces weak free-generation with a grounded one). Same advance/spawn
#   gate as MOVE_CONJECTURE; inert (fail-closed) without cvc5. WIRED: abduction.abduce_seed + runner.
MOVE_FUNCTOR_LIFT = "functor_lift"            # SPECTRAL/domain lift: a stuck DISCRETE goal is lifted to the
#   continuous domain (graph→adjacency matrix), NumPy computes the spectral bound, the continuous bound
#   bounds the discrete property — GATED on the Mathlib bridge lemma EXISTING (abort if absent; don't prove
#   it from scratch). NumPy fail-closed. Narrow/domain-specific. WIRED: spectral_lift + runner.
MOVE_DEFER = "defer"                         # explicit stop → exact_gap
MOVE_CACHE_REUSE = "cache_reuse"             # TELEMETRY-only label for a CLOSED-FROM-CACHE reuse (COMPRESS+
#   SCALE leg). Not a selectable move — emitted by the cache-hit branch so a reuse is a first-class attributed
#   row (move_yield_report / per-arm lift), closing audit gap #3 (reuse was invisible to the attempts DB).

# Conjecture is tried AFTER the cheap direct moves (try to close directly first; if
# stuck, invert and decompose). The strategist moves (specialize/generalize) are NOT in this default
# walk — they are stuck-gated + env-flagged in `move_policy` (parity-safe), see STRATEGIST_MOVES.
MOVE_ORDER = (MOVE_NATIVE_HAMMER, MOVE_CLAUDE_WARM, MOVE_COLD_SHOT, MOVE_FRONTIER, MOVE_CONJECTURE)  # the FULL ladder (the non-agent fallback)
STRATEGIST_MOVES = (MOVE_SPECIALIZE, MOVE_GENERALIZE, MOVE_FALSIFY, MOVE_TACTIC_STEP, MOVE_CORROBORATE, MOVE_SLEDGEHAMMER, MOVE_REFLECTION, MOVE_ABDUCE, MOVE_FUNCTOR_LIFT)  # default-OFF; offered by move_policy on a stuck signal

# AGENTIC-FIRST move ladder (the architecture, not a filter): when the agent path is LIVE — `claude_warm` runs the
# agentic leaf with AGENT_TOOLS{witness/abduct/hammer/search} + AGENT_PLAN{decompose} — the agent REACHES those
# capabilities itself, so cold_shot + frontier are the REDUNDANT cold one-shots (arch §685: "the agent now reaches
# the same moves… the redundant cascade"; a warm, iterating, tool-equipped agent that already tried can't be beaten
# by a cold one-shot). So they DEMOTE to the non-agent fallback: the live ladder is native_hammer (free cheap-first
# filter) → claude_warm (THE agent) → conjecture (decompose). The deterministic cascade is what runs WITHOUT an agent.
_AGENT_FIRST_ORDER = (MOVE_NATIVE_HAMMER, MOVE_CLAUDE_WARM, MOVE_CONJECTURE)


def _active_move_order() -> "tuple[str, ...]":
    """The per-node move ladder. AGENT-FIRST by default (native filter → agent → decompose); the cold one-shots
    (cold_shot/frontier) are the NON-AGENT FALLBACK, included only when there is no agent. `ZTARE_LEANMILL_FULL_CASCADE=1`
    restores the legacy 5-move cascade (the A/B baseline); `ZTARE_LEANMILL_AGENT_TOOLS=0` (no agent) also keeps the
    full ladder so a non-agent run still has its fallbacks. SOUND: removing direct-proof moves only shrinks attack
    surface — the kernel re-verifies every closure — so this can never false-close, only save the doomed grind."""
    if (os.environ.get("ZTARE_LEANMILL_FULL_CASCADE") == "1"
            or os.environ.get("ZTARE_LEANMILL_AGENT_TOOLS", "1") == "0"):
        return MOVE_ORDER
    return _AGENT_FIRST_ORDER

# Heuristic cost model (v1, STUB — see honest-notes in the seam/report). Units
# are abstract "budget units" (cold wall-clock seconds / fan-out width proxy),
# NOT calibrated. native_hammer is free; the rest escalate.
MOVE_COST: dict[str, float] = {
    MOVE_NATIVE_HAMMER: 0.0,
    MOVE_CLAUDE_WARM: 3.0,
    MOVE_CLAUDE_WARM_REFINE: 3.0,   # a 2nd warm call; costly ⇒ NOT free-floored (data can down-weight it)
    MOVE_COLD_SHOT: 4.0,
    MOVE_FRONTIER: 6.0,
    MOVE_CONJECTURE: 2.0,   # cheap proposal; the cost is in proving the spawned child
    MOVE_SPECIALIZE: 2.0,   # one leaf call: generate G' + the G⇒G' witness, kernel-gated to a rung
    MOVE_GENERALIZE: 4.0,   # one leaf call proving G via an internal strengthening; ~a strong direct attempt
    MOVE_FALSIFY: 4.0,      # one leaf call proving ¬G + kernel gate; ~a strong direct attempt at the negation
    MOVE_TACTIC_STEP: 5.0,  # multi-step per-tactic leaf loop (several leaf calls) + REPL; costliest leaf move
    MOVE_CORROBORATE: 4.0,  # one leaf call: a consequence K + G→K + ¬K proofs, kernel-gated like falsify
    MOVE_WITNESS_TRANSPORT: 1.0,  # a BOUNDED SymPy subprocess (direct path; no LLM) + one kernel compile — cheap
    MOVE_SLEDGEHAMMER: 4.0,  # one external Isabelle sledgehammer call + per-premise #check probes + one closing compile
    MOVE_REFLECTION: 4.0,    # one leaf call (check/sound/close) + a pre-filter compile + the closure compile ≈ generalize
    MOVE_ABDUCE: 2.0,        # a bounded cvc5 abduct + ONE seeded leaf call; the proving cost is in the spawned child ≈ conjecture
    MOVE_FUNCTOR_LIFT: 4.0,  # one leaf call (define the lift) + a NumPy spectral compute + a bridge-lemma #check + closing compile
}

# Heuristic prior P(this move closes THIS node), independent of node features. These are the
# Beta-prior MEANS for Arc-H calibration; `solver/move_calibration.py` shifts them toward the
# measured per-move closure rate from `solver_lane_attempts.db` (small samples stay near these).
MOVE_PRIOR_P_CLOSE: dict[str, float] = {
    MOVE_NATIVE_HAMMER: 0.25,
    MOVE_CLAUDE_WARM: 0.35,
    MOVE_CLAUDE_WARM_REFINE: 0.35,  # stub = warm's (a refined warm retry); shifts to the measured rate
    MOVE_COLD_SHOT: 0.30,
    MOVE_FRONTIER: 0.40,
    MOVE_CONJECTURE: 0.50,  # decomposition advances even when direct proof fails
    MOVE_SPECIALIZE: 0.45,  # P(genuine rung) — verified special case; honest progress, not closure
    MOVE_GENERALIZE: 0.35,  # P(close G via a stronger IH) — stub = warm's; shifts to the measured rate
    MOVE_FALSIFY: 0.20,     # P(the target is actually false AND we can prove ¬G) — rarely the right move
    MOVE_TACTIC_STEP: 0.35, # P(close via per-step stepping) — stub = warm's; shifts to the measured rate
    MOVE_CORROBORATE: 0.22, # P(G false AND a CONSEQUENCE is refutable) — ≥ falsify (a consequence can be far
    #   easier to refute than G directly), but still rare (most targets are true). Non-closure (emits a falsifier).
    MOVE_WITNESS_TRANSPORT: 0.45,  # P(close) CONDITIONAL on the gate (a computable non-linear ∃) — SymPy is
    #   complete on its fragment, so when eligible the close rate is high; the gate makes it rarely eligible.
    MOVE_SLEDGEHAMMER: 0.30,  # P(close) CONDITIONAL on a configured Isabelle server — sledgehammer is a strong
    #   premise selector, but the Isabelle→Mathlib name map + translation are lossy; shifts to the measured rate.
    MOVE_REFLECTION: 0.35,   # P(close a finite/decidable goal via a reflection procedure) — stub = generalize's
    MOVE_ABDUCE: 0.45,       # P(ADVANCE) given a decidable-arithmetic goal + a non-trivial cvc5 abduct (ORDERING only; never P(close G))
    MOVE_FUNCTOR_LIFT: 0.25,  # P(close) CONDITIONAL on a discrete goal WITH the Mathlib bridge lemma present — narrow gate
}

# Arc-H calibration override (GP-246): a caller (the worker) may install measured priors via
# `set_move_priors(...)`; until then `_move_prior` falls back to the stub above. Default None ⇒
# behaviour is byte-identical to the stub policy (reversible, no surprise in-loop swap).
_CALIBRATED_PRIORS: Optional[dict] = None


def set_move_priors(priors: Optional[dict]) -> None:
    """Install calibrated est_p_close priors (or None to revert to the stubs)."""
    global _CALIBRATED_PRIORS
    _CALIBRATED_PRIORS = dict(priors) if priors else None


def _move_prior(move: str) -> float:
    src = _CALIBRATED_PRIORS if _CALIBRATED_PRIORS is not None else MOVE_PRIOR_P_CLOSE
    return src.get(move, 0.0)


# GP-248 context-aware move prior (the one learned/neural addition that fits the topology): a provider
# (error_class -> {move: est_p}) that conditions move SELECTION on the node's failure context, e.g.
# move_calibration.calibrated_priors_for_class (BIC-selected per-(move,error_class) Beta posterior). It
# only changes ORDERING — the kernel still RATIFIES — so a bad prior wastes budget but can NEVER launder a
# closure (NOT a learned gate; see GP-248_neurosymbolic_boundary_seam). Default None ⇒ flat prior (parity).
_CONTEXT_PRIOR_FN: "Optional[Callable[[str], dict]]" = None


def set_context_prior_fn(fn) -> None:
    """Install (or clear with None) the context-aware move-prior provider. The worker installs it ONLY
    under ZTARE_LEANMILL_CONTEXT_PRIOR=1; unset ⇒ None ⇒ byte-identical flat-prior behaviour."""
    global _CONTEXT_PRIOR_FN
    _CONTEXT_PRIOR_FN = fn


# UCB-over-moves visit snapshot (the exploration denominator): {move: attempt_count}, installed once per
# solve by the worker under ZTARE_LEANMILL_UCB_MOVES=1 (from move_calibration.move_visit_counts). None ⇒
# UCB disabled (byte-identical fixed-order policy). A per-solve snapshot is fine — counts are ~static within
# one target's search; the cross-target accumulation (what makes a dormant move's bonus decay) is in the DB.
_MOVE_VISITS: "Optional[dict]" = None


def set_move_visits(counts: "Optional[dict]") -> None:
    """Install (or clear with None) the per-move attempt-count snapshot UCB uses as its exploration
    denominator. None ⇒ UCB selection is off (fixed-order parity)."""
    global _MOVE_VISITS
    _MOVE_VISITS = dict(counts) if counts is not None else None

# ── Move-algebra structure (Barrington isomorphism, 2026-06-02) ───────────────
# Barrington: at BOUNDED resource (constant width), expressive power comes from the
# NON-COMMUTATIVITY of the composition, not from the width. A solvable/abelian
# move-set collapses; a non-solvable one (rich commutator structure) stays expressive.
# Transported to proof search:
#   COMMUTATIVE  — moves that attack the goal AS-STATED with more/wider resource and
#                  preserve the obligation structure (order-insensitive spraying). They
#                  collapse: stacking more of them does not add depth.
#   NON_COMMUTATIVE — moves that CHANGE the obligation structure (invent a lemma /
#                  generalize / reframe / decompose), spawning a new typed sub-target.
#                  These are the "commutators" — depth is built by composing them.
# This is not a passive label: it REORDERS the policy (escalate composition, not
# resource, once spraying has failed) and TYPES the residual→lever. Grounded in this
# session's kernel-arbitrated P1 ablation — commutative spraying 0/4 vs invention 4/4
# at comparable budget. Falsifier: if closure rate tracks budget/width as much as the
# non-commutative reorder, the isomorphism is poetry (see the GP-246 seam).
MOVE_CLASS: dict[str, str] = {
    MOVE_NATIVE_HAMMER: "commutative",
    MOVE_CLAUDE_WARM: "commutative",
    MOVE_CLAUDE_WARM_REFINE: "commutative",  # re-attacks the same goal with feedback (structure-preserving)
    MOVE_COLD_SHOT: "commutative",
    MOVE_FRONTIER: "commutative",
    MOVE_CONJECTURE: "non_commutative",
    MOVE_SPECIALIZE: "non_commutative",   # changes the obligation (weaker target G') — a commutator
    MOVE_GENERALIZE: "non_commutative",   # changes the obligation (stronger IH inside the proof)
    MOVE_FALSIFY: "non_commutative",      # changes the obligation entirely (prove ¬G) — the Invert leg
    MOVE_TACTIC_STEP: "commutative",       # attacks G AS-STATED via stepping (structure-preserving)
    MOVE_CORROBORATE: "non_commutative",  # changes the obligation (refute a CONSEQUENCE of G) — Invert-dual
    MOVE_WITNESS_TRANSPORT: "commutative",  # attacks G AS-STATED with a computed witness (structure-preserving)
    MOVE_SLEDGEHAMMER: "commutative",       # attacks G AS-STATED with retrieved premises (structure-preserving)
    MOVE_REFLECTION: "commutative",         # attacks G AS-STATED with a decision procedure (structure-preserving)
    MOVE_ABDUCE: "non_commutative",         # changes the obligation (spawns a missing-premise sub-target) — Invert/decompose
    MOVE_FUNCTOR_LIFT: "commutative",       # attacks G AS-STATED via a spectral bound (structure-preserving)
    MOVE_DEFER: "terminal",
}


def move_class(move: str) -> str:
    """Commutative (resource/spraying, structure-preserving) vs non_commutative
    (structure-changing invention/decompose/reframe) — the Barrington axis."""
    return MOVE_CLASS.get(move, "commutative")


# Below this marginal est_p_close the policy chooses DEFER (emit exact_gap)
# rather than spend more budget on a node.
DEFAULT_DEFER_THRESHOLD = 0.12

# How strongly observed partial progress (GP-187 gradient) boosts the best-first
# frontier score. A node at progress 0.5 (one goal left) outranks a fresh sibling
# of equal value; this is what lets the DAG climb the gradient instead of treating
# every non-closure as identical (the measured DAG≈cascade failure mode).
PROGRESS_WEIGHT = 1.0

# VALUE-BACKUP tunables (MCTS arm; used only when ZTARE_LEANMILL_VALUE_BACKUP=1, default OFF = byte-parity).
# A move's realized reward is backed UP to its ancestors' `subtree_value`; an OPEN node's frontier score then
# gains `WEIGHT × (ancestor-chain subtree_value)` so productive branches are expanded first and doomed ones
# drained last. Env-overridable (no magic literals). FAIL_PENALTY is the small negative reward of a move that
# made no progress (so a branch of repeated failures self-deprioritises).
DEFAULT_VALUE_BACKUP_WEIGHT = 0.5     # ZTARE_LEANMILL_VALUE_BACKUP_WEIGHT
DEFAULT_VALUE_BACKUP_FAIL_PENALTY = 0.1   # ZTARE_LEANMILL_VALUE_BACKUP_FAIL_PENALTY

# UCB-over-moves tunables (used only when ZTARE_LEANMILL_UCB_MOVES=1). Named constants — NOT magic literals
# — so the default is a single, documented, discoverable source of truth (the convention of the tunables
# above); each is also OVERRIDABLE per-run via its env var so the A/B can sweep it / an operator can set it.
#   DEFAULT_UCB_C (env ZTARE_LEANMILL_UCB_C): exploration weight as a DIMENSIONLESS fraction of the Q-spread
#     (the bonus is scaled by (Qmax−Qmin) in ucb_move_scores, so `c` means the same thing regardless of N).
#     Set to 0.15 by a FRESH-EYES measurement (2026-06-07) on BOTH the live DB skew and a matured-DB sim:
#     the regression onset (a dormant move overtaking the proven warm) is at c≈0.25 on the matured skew, so
#     0.15 is a safe no-regression default. NOT a final value — the instrumented A/B sweeps it; auto-tuning
#     it (cf. autotune_strength for prior k) is the end-state.
#   DEFAULT_UCB_EXPLORE_COST_LAMBDA (env ZTARE_LEANMILL_UCB_LAMBDA): discounts a move's exploration bonus by
#     its MOVE_COST, so an expensive closer (frontier) is not over-explored per unit budget.
DEFAULT_UCB_C = 0.15
DEFAULT_UCB_EXPLORE_COST_LAMBDA = 0.15

# UCB over the FRONTIER (NODE selection — "which open DAG node to expand"; ZTARE_LEANMILL_UCB_FRONTIER=1,
# default OFF = greedy argmax parity). Distinct from UCB-over-MOVES (which move within a node): this is the
# MCTS-style frontier selection — boost an UNDER-EXPANDED open node so the search EXPLORES diverse
# decomposition branches instead of tunneling greedily on the single best-scoring node. The payoff is in the
# DEEP-decomposition regime (a large theorem's conjecture-DAG with many open sub-goals — the P1 regime); on a
# shallow single-node DAG it is a no-op. `c` is a dimensionless fraction of the frontier-score SPREAD.
DEFAULT_UCB_FRONTIER_C = 0.5
# default floor for the frontier score-spread scale (frontier scores are O(1) value−cost units);
# env-overridable ZTARE_LEANMILL_UCB_FRONTIER_MIN_SPAN.
DEFAULT_UCB_FRONTIER_MIN_SPAN = 0.5

# BOOSTING (AdaBoost analog; ZTARE_LEANMILL_BOOST=1, default OFF = parity). A bottleneck rung — an open node
# the frontier keeps re-selecting after _BOOST_AFTER failed moves — gets a per-move budget cap MULTIPLIER
# (_BOOST_MULT), concentrating DEPTH on the load-bearing sub-goal instead of spreading budget thin across
# already-tried nodes. Distinct from UCB-over-frontier (which NODE) and UCB-over-moves (which MOVE): boosting
# is about HOW MUCH budget the chosen move gets. Read at search time → DagNode.boost_factor → solver_core _cap.
DEFAULT_BOOST_AFTER = 3        # failed moves on a node before it counts as a bottleneck worth concentrating on
DEFAULT_BOOST_MULT = 2.0       # per-move cap multiplier for a bottleneck node (capped downstream by wallclock)
# NB: env is read at CALL time (in the search loop), not module-import time — so the in-process self-test and
# any env toggle take effect without a re-import, matching the UCB-frontier flag pattern.


@dataclass
class DagNode:
    """One typed proof-obligation in the ex-ante DAG."""
    node_id: str
    kind: str                       # ∈ NODE_KINDS
    goal_text: str
    parent_id: Optional[str] = None
    status: str = "open"            # ∈ NODE_STATUSES
    residual: Optional[str] = None  # residual class when not closed
    proof_text: str = ""            # ratified proof body when closed
    # Bookkeeping for the policy: which moves have already been spent here.
    moves_tried: list[str] = field(default_factory=list)
    next_lever: str = ""            # residual_to_lever output
    est_p_seed: Optional[float] = None  # exogenous est_p_close prior (e.g. retrieval
                                        # score) for premise-anchored nodes; overrides
                                        # the heuristic move prior in the policy.
    premise: Optional[str] = None       # retrieved premise name this helper closes via
    composition_required: bool = False  # SINGLE-DOOR INVARIANT (2026-06-25): True ⇒ this child is part of a
    #   GENUINE decomposition (a top-level ∧/↔ conjunct, or a contract-declared sub_goal/helper) that does NOT
    #   re-prove the parent — so closing it can NEVER status-flip the parent closed; the parent must close
    #   through the kernel (a direct proof or `composite_ratify`'s And-intro composite). False (default) ⇒ this
    #   child RE-PROVES the parent goal (a premise-anchored restatement), so its proof IS a parent proof and may
    #   propagate. This is the property the `_propagate_closure` soundness actually depends on — keyed on the
    #   PROPERTY, not on the `ZTARE_CONJECTURE_DECOMPOSE` flag (the flag-keyed guard silently went false-clean on
    #   conjunct children in the default config; arch §"governed obligation-DAG search" documents the invariant).
    # Best partial progress observed on this node across NON-closing moves (the
    # GP-187 gradient). Raised from MoveResult.progress; used to (a) boost the
    # best-first frontier score so a near-closing node is expanded first, and
    # (b) keep a genuinely-advancing node from deferring prematurely.
    best_progress: float = 0.0
    min_goals_remaining: Optional[int] = None
    last_error_class: str = ""      # last MoveResult.error_class (out-of-span signal for invent-criterion)
    target_strength: str = ""       # M4: frontier_triage target_strength tag (strong_missing|elementary|''),
    #   advisory steering signal for the SPECIALIZE preference; default '' = no steer (parity)
    boost_factor: float = 1.0       # BOOSTING (AdaBoost analog): a per-node budget MULTIPLIER the move runner
    #   applies to this node's per-move cap. 1.0 = no boost (parity); >1 = concentrate budget DEPTH on a
    #   bottleneck rung. Set by the search loop under ZTARE_LEANMILL_BOOST=1; read by solver_core's _cap.
    subtree_value: float = 0.0      # MCTS value-BACKUP signal: realized reward (close/rung/progress − fail) of
    #   this node's DESCENDANTS, backed UP via `_backup_value`. Biases frontier selection toward branches whose
    #   subtree is productive and away from doomed ones (the MCTS arm boosting/UCB-frontier don't cover). Only
    #   read under ZTARE_LEANMILL_VALUE_BACKUP=1 (default off ⇒ stays 0.0 ⇒ byte-parity). No soundness surface.

    def is_finished(self) -> bool:
        return self.status in ("closed", "exact_gap", "falsifier", "rung", "retired")


@dataclass
class MoveResult:
    """Typed result a `move_runner` returns for one (node, move) execution.

    The runner has ALREADY run governance (kernel verify + MNC). This module
    only READS these fields; it never re-decides them. That is the
    proposes/ratifies boundary: the runner ratifies, the search records.
    """
    move: str
    kernel_clean: bool = False      # kernel-clean per _is_compile_ok (no sorry/admit/error, allowlisted axioms)
    mnc_passed: bool = False        # matched-negative-control passed (NOT leakage)
    # Full governance in addition to compile and MNC; omission fails closed.
    governance_ready: bool = False
    proof_text: str = ""
    residual: Optional[str] = None  # diagnostic / remaining obligation; never an executable theorem by itself
    new_sub_goal_text: Optional[str] = None  # text for the new sub_goal node, if any
    falsifier: bool = False         # the move found a falsifying candidate
    rung: bool = False              # SPECIALIZE produced a kernel-verified WEAKER special case (honest
                                    # partial progress; NEVER a closure — kernel_clean stays False)
    tail: str = ""                  # transcript tail (for audit)
    wallclock_s: float = 0.0
    # Partial-progress gradient (GP-187 middle layer, from proof_state.py). The
    # runner fills these from `proof_state_signal(rc, compile_tail)` on a
    # NON-closing move so the search can tell a near-closing node (1 goal left)
    # from a dead direction (unknown_identifier). Defaults make this fully
    # backward-compatible: a runner that ignores them yields the old behavior.
    goals_remaining: Optional[int] = None
    progress: float = 0.0           # 0..1; closed≈1, 1-goal-left≈0.5, broken-name≈0.05
    error_class: str = ""           # clean|unsolved_goals|tactic_failed|unknown_identifier|...
    # Disposable carrier control.  Set only for an isolated calibration node;
    # it cannot satisfy theorem-governance axes or earn move attribution.
    calibration_available: Optional[bool] = None

    @property
    def ratified_close(self) -> bool:
        """A close needs compile, MNC, and the complete governance contract."""
        return bool(
            self.kernel_clean and self.mnc_passed and self.governance_ready
        )


# The move_runner the search calls. Signature: (node, move, budget_remaining) ->
# MoveResult. Injected so the search is mockable in tests and wired to the real
# worker moves in production.
MoveRunner = Callable[[DagNode, str, float], MoveResult]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Ex-ante DAG build
# ─────────────────────────────────────────────────────────────────────────────

def build_obligation_dag(
    contract: dict,
    goal_text: str,
    premise_shelf: Optional[list] = None,
    target_strength: str = "",
) -> dict[str, DagNode]:
    """Build the EX-ANTE proof-obligation DAG BEFORE any move runs.

    Always emits a `root_goal`. Children come from, in priority order:
      1. a contract-declared decomposition (`decomposition` / `sub_goals` /
         `helper_lemmas`) — human/pre-registered, highest trust; else
      2. governed STRUCTURAL decomposition of the goal's top-level ∧/↔
         (deterministic, auditable connective splitting; NOT model-improvised).
    The root stays directly attackable regardless, so any imperfect split only
    costs a little search budget — it can never block the direct proof, and the
    kernel+MNC check gates every close so it can never mint a false closure.
    The premise_shelf is accepted for forward-compat (a richer decomposer may
    consult it). Substrate-agnostic: no NS/Clay logic; specifics enter only via
    the contract.

    Returns an ordered dict {node_id: DagNode}.
    """
    nodes: dict[str, DagNode] = {}
    root = DagNode(node_id="n0_root", kind="root_goal", goal_text=goal_text, parent_id=None)
    nodes[root.node_id] = root

    # `composition_required` is set by the SOURCE, not guessed per-child: a contract/structural decomposition
    # is a GENUINE split (children do NOT re-prove the parent → the parent needs a kernel composite, never a
    # status-flip); premise-anchored helpers each RE-PROVE the parent goal (their proof IS a parent proof →
    # may propagate). Keying on the producer is the property `_propagate_closure` soundness depends on.
    decomposition = _contract_decomposition(contract)
    _composition_required = True
    if not decomposition:
        decomposition = derive_structural_decomposition(goal_text)
    if not decomposition and premise_shelf:
        # atomic goal + retrieval available → premise-anchored candidate closing moves (re-prove the parent).
        decomposition = derive_premise_helpers(goal_text, premise_shelf)
        _composition_required = False
    for i, child in enumerate(decomposition, start=1):
        kind = child.get("kind", "sub_goal")
        if kind not in NODE_KINDS:
            kind = "sub_goal"
        nid = f"n{i}_{kind}"
        nodes[nid] = DagNode(
            node_id=nid,
            kind=kind,
            goal_text=child.get("goal_text", ""),
            parent_id=root.node_id,
            est_p_seed=child.get("est_p_seed"),
            premise=child.get("premise"),
            composition_required=_composition_required,
        )
    if target_strength:  # M4: stamp the advisory strength tag onto every node (default '' = no steer)
        for _n in nodes.values():
            _n.target_strength = target_strength
    return nodes


def _contract_decomposition(contract: dict) -> list[dict]:
    """Extract a contract-declared decomposition, if any. Tolerant of several
    shapes so the contract author isn't locked to one key."""
    if not isinstance(contract, dict):
        return []
    decomp = contract.get("decomposition")
    if isinstance(decomp, list) and decomp:
        return [d for d in decomp if isinstance(d, dict)]
    out: list[dict] = []
    for sg in (contract.get("sub_goals") or []):
        if isinstance(sg, dict):
            out.append({"kind": "sub_goal", "goal_text": sg.get("goal_text", "")})
        elif isinstance(sg, str):
            out.append({"kind": "sub_goal", "goal_text": sg})
    for hl in (contract.get("helper_lemmas") or []):
        if isinstance(hl, dict):
            out.append({"kind": "helper_lemma", "goal_text": hl.get("goal_text", "")})
        elif isinstance(hl, str):
            out.append({"kind": "helper_lemma", "goal_text": hl})
    return out


# ── Governed structural decomposition (deterministic, auditable; NOT model-improvised) ──
# Splits a goal's TOP-LEVEL conjunction/iff into independent sub-goals. The KERNEL
# discharges the composition (⟨_, _⟩ / constructor), and the root_goal stays directly
# attackable, so a wrong split can neither block the direct proof nor mint a false
# closure (the existing kernel+MNC check gates every close). Conservative: returns []
# on any parse uncertainty or an atomic goal (e.g. a bare inequality → single root).
_OPENERS = set("([{⟨")
_CLOSERS = set(")]}⟩")


def _split_top_level(s: str, sep_chars: set[str]) -> list[str]:
    """Split s on single-char separators occurring at bracket-depth 0 (Unicode-safe)."""
    parts, buf, depth = [], [], 0
    for c in s:
        if c in _OPENERS:
            depth += 1; buf.append(c)
        elif c in _CLOSERS:
            depth = max(0, depth - 1); buf.append(c)
        elif depth == 0 and c in sep_chars:
            parts.append("".join(buf)); buf = []
        else:
            buf.append(c)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def _goal_prefix_and_type(goal_text: str):
    """(prefix_ending_in_the_goal_colon, goal_type) or (None, None) if uncertain.
    Strips the proof; the goal type is whatever follows the declaration's top-level ':'."""
    from ztare.leanmill.lean_source import signature_before_proof, top_level_colon
    s = (goal_text or "").strip()
    sig = signature_before_proof(s)
    ci = top_level_colon(sig)
    if ci < 0:
        return None, None
    head = s[:s.find(sig)] if sig and sig in s else ""
    prefix, gtype = head + sig[:ci + 1], sig[ci + 1:].strip()
    return (prefix, gtype) if gtype else (None, None)


def derive_structural_decomposition(goal_text: str) -> list[dict]:
    """Top-level ∧/↔ → independent sub-goals, preserving the binder context. Pure
    connective splitting (auditable), no model improvisation. [] when atomic/uncertain."""
    if not goal_text or not isinstance(goal_text, str):
        return []
    prefix, gtype = _goal_prefix_and_type(goal_text)
    if not gtype:
        return []
    # BOTH connective splits route through the ONE guarded door in lean_source (∀-fronting distributes and is
    # re-prepended; a leading ∃ shares a witness and is DEFERRED), shared with isomorphism_decompose so no
    # hand-copied quantifier guard can drift into a sibling. Fixes the ↔-under-∃/∀ permutations here too.
    from ztare.leanmill.lean_source import safe_conjunction_split, safe_iff_split
    _iff = safe_iff_split(gtype)
    if _iff:
        qprefix, (a, b) = _iff
        _q = (qprefix + " ") if qprefix else ""
        return [
            {"kind": "sub_goal", "goal_text": f"{prefix} {_q}({a}) → ({b})"},
            {"kind": "sub_goal", "goal_text": f"{prefix} {_q}({b}) → ({a})"},
        ]
    _and = safe_conjunction_split(gtype)
    if not _and:
        return []
    qprefix, conj = _and
    _q = (qprefix + " ") if qprefix else ""
    return [{"kind": "sub_goal", "goal_text": f"{prefix} {_q}{c}"} for c in conj]


# Top-k retrieved premises to fan out as candidate closing-moves for an atomic goal.
PREMISE_HELPER_K = 4


def derive_premise_helpers(goal_text: str, premise_shelf, k: int = PREMISE_HELPER_K) -> list[dict]:
    """For an ATOMIC goal (no structural split), turn the top-k EXOGENOUS retrieved
    premises into candidate closing-move helper nodes ("close via premise P"), each
    carrying the retrieval SCORE as its est_p_close prior — an exogenous signal, not a
    heuristic stub. Best-first then tries the highest-scored premise first, with deferral.
    Gated/auditable: premises come from RETRIEVAL (not model-invented), the root stays
    directly attackable, and the kernel+MNC check gates every close. [] if no shelf."""
    if not premise_shelf:
        return []
    out: list[dict] = []
    for p in list(premise_shelf)[:max(0, k)]:
        if isinstance(p, dict):
            name = p.get("name") or p.get("premise") or p.get("lemma")
            score = p.get("score", p.get("similarity"))
        elif isinstance(p, str):
            name, score = p, None
        else:
            continue
        if not name:
            continue
        try:
            score = float(score) if score is not None else None
        except (TypeError, ValueError):
            score = None
        out.append({
            "kind": "helper_lemma",
            "goal_text": f"{goal_text}   -- via premise `{name}`",
            "premise": name,
            "est_p_seed": score,
        })
    return out


def _children(nodes: dict[str, DagNode], parent_id: str) -> list[DagNode]:
    return [n for n in nodes.values() if n.parent_id == parent_id]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Move policy (EV/cost ordered, with explicit DEFER)
# ─────────────────────────────────────────────────────────────────────────────

def _node_value(node: DagNode) -> float:
    """Value of closing this node. Root is worth most; helpers/sub-goals less
    (they only matter insofar as they discharge a parent). Heuristic v1."""
    return {
        "root_goal": 1.0,
        "sub_goal": 0.6,
        "helper_lemma": 0.5,
        "gap": 0.3,
        "falsifier": 0.4,
    }.get(node.kind, 0.5)


def _effective_est_p(node: DagNode, move: str) -> float:
    """The close-probability VALUE the search acts on for (node, move) — the single source of
    truth shared by the policy AND the best-first frontier. An EXOGENOUS prior on the node
    (`est_p_seed`, e.g. a retrieval score) overrides the per-move stub/calibrated prior; with no
    seed it is the move prior (calibrated via `set_move_priors`, else the heuristic stub).

    Progress is NOT folded in here — it floors the policy's decision and rides the frontier as an
    additive bonus, exactly as before; this helper only fixes that the frontier previously ignored
    `est_p_seed` entirely (so a retrieval-score-0.9 premise node was ranked at the generic 0.25
    native prior). Now the frontier expands high-value premise-anchored nodes first.

    GP-248: when a context-prior provider is installed (worker, ZTARE_LEANMILL_CONTEXT_PRIOR=1) AND the
    node has a failure context, the per-move prior is CONDITIONED on `node.last_error_class` (the learned
    per-(move,error_class) posterior) instead of the flat move prior. Ordering-only; the kernel ratifies."""
    if node.est_p_seed is not None:
        return node.est_p_seed
    if _CONTEXT_PRIOR_FN is not None and node.last_error_class:
        try:
            return _CONTEXT_PRIOR_FN(node.last_error_class).get(move, _move_prior(move))
        except Exception:  # noqa: BLE001 — a context-prior error must never break selection
            return _move_prior(move)
    return _move_prior(move)


def _ucb_eligible_moves(node: DagNode, budget_remaining: float,
                        menu_allowed: "Optional[tuple]") -> list[str]:
    """The untried, affordable, menu-allowed moves UCB ranks over: the STANDARD CLOSURE MENU (MOVE_ORDER)
    ONLY. The strategist tail (specialize/falsify/generalize/tactic_step) is DELIBERATELY EXCLUDED — those are
    last-resort, stuck-gated, NON-closure moves whose stub Q is not a closure rate (specialize 0.45 = P(rung),
    falsify 0.20 = P(¬G)). Letting blind UCB rank them by that incomparable Q + an n=0 exploration bonus
    OVER-PROMOTES them — verified 2026-06-07: on a production-skewed snapshot `specialize` WINS the fresh node
    ahead of every closer, i.e. the search would settle for a weaker rung before even ATTEMPTING closure. So
    UCB only value-orders + explores the CLOSURE menu; the tail keeps its existing context-gated path
    (`_strategist_move`), exactly as the fixed-order policy, and its reachability is the context-prior's job
    (calibrated_priors_for_class on the error signal), not blind exploration."""
    out: list[str] = []
    for m in _active_move_order():
        if m in node.moves_tried:
            continue
        if menu_allowed is not None and m not in menu_allowed:
            continue
        if MOVE_COST.get(m, 1.0) > budget_remaining:
            continue
        out.append(m)
    return out


def _ucb_move_policy(node: DagNode, budget_remaining: float, defer_threshold: float,
                     menu_allowed: "Optional[tuple]") -> str:
    """UCB-over-moves selection (ZTARE_LEANMILL_UCB_MOVES=1). Replaces the FIXED priority order of the
    standard closure menu (native→warm→cold→frontier→conjecture) with argmax over `Q(node,move) + a
    SCALE-INVARIANT exploration bonus` — so the calibrated closure value drives order (native's measured
    0/29 is de-prioritized, frontier/cold are value-ranked) and an under-used closer earns exploration. Q =
    the (progress-floored) effective est_p the rest of the search already acts on; the bonus comes from
    `move_calibration.ucb_move_scores` over the installed visit snapshot. The strategist tail is NOT in the
    pool (see _ucb_eligible_moves) — after the closure menu, control falls through to `_strategist_move`
    EXACTLY as the fixed-order path, so the tail's stuck-gate is byte-identical. The kernel still ratifies ⇒
    a mis-ranked closer only wastes budget, never launders. If no closer clears threshold → the strategist
    gate → DEFER (same terminal structure as fixed-order)."""
    eligible = _ucb_eligible_moves(node, budget_remaining, menu_allowed)
    if os.environ.get("ZTARE_LEANMILL_NO_CONJECTURE") == "1":
        eligible = [m for m in eligible if m != MOVE_CONJECTURE]   # #53 apparatus_no_conjecture control arm (UCB path)
    if eligible:
        c = float(os.environ.get("ZTARE_LEANMILL_UCB_C", DEFAULT_UCB_C))
        lam = float(os.environ.get("ZTARE_LEANMILL_UCB_LAMBDA", DEFAULT_UCB_EXPLORE_COST_LAMBDA))
        # Q per eligible move = the SAME progress-floored effective est_p the fixed-order walk gates on, so UCB
        # at c=0 reduces exactly to value-ordered selection over the closure menu.
        q = {m: max(_effective_est_p(node, m), node.best_progress) for m in eligible}
        from ztare.leanmill.solver import move_calibration as _mc  # lazy: avoids the calibration→gds cycle
        scores = _mc.ucb_move_scores(q, _MOVE_VISITS or {}, MOVE_COST, c=c, lam=lam)
        best = max(eligible, key=lambda m: scores[m])
        if scores[best] >= defer_threshold:
            return best
    # No closer eligible / none clears threshold → the SAME strategist-gate + DEFER terminal the fixed-order
    # path uses (UCB never touches the tail). _menu_allowed restricts to native+warm ⇒ no strategist tail.
    if menu_allowed is not None:
        return MOVE_DEFER
    strat = _strategist_move(node, budget_remaining)
    return strat if strat is not None else MOVE_DEFER


def move_policy(node: DagNode, budget_remaining: float,
                defer_threshold: float = DEFAULT_DEFER_THRESHOLD) -> str:
    """Choose ONE typed move for `node`, by EV/cost, over the ordered menu, with
    an explicit DEFER. Deterministic (v1): walk the menu in cost order, skip
    moves already tried on this node, skip moves whose cost exceeds the
    remaining budget, and pick the FIRST whose marginal est_p_close ≥ threshold.
    If none qualifies, DEFER (the node becomes exact_gap — no silent death).

    The est_p_close is the move prior here (v1 STUB). A calibrated per-node model
    is future work; the SHAPE (ordered EV/cost choice + explicit deferral) is the
    GP-246 contribution and is real.

    NON-PROMOTION (2026-06-02): a Barrington-motivated reorder that PROMOTED the
    non-commutative `conjecture` (invent/decompose) move ahead of the resource-scaling moves
    was tested — exogenous v26 Mathlib rows + the APN invention-bound frontier, every closure
    kernel-arbitrated, apparatus-certified with an adequacy gate — and REFUTED: the invent
    move NEVER beat a strong direct agentic attempt (signal=0 across all admissible targets;
    on P1 invent uniquely lost; elsewhere a tie or both-failed). A capable direct prover
    already invents inline (`have`-steps) as needed, so a separate forced invent mode is
    redundant. The menu therefore keeps its PLAIN order — free probe → strong direct →
    resource → invent (last) — and we do NOT promote invention. The move_class taxonomy +
    the typed `escalate_noncommutative` lever stay as neutral DIAGNOSTICS only. See GP-246.

    REACHABILITY INVENT-CRITERION (default OFF; ZTARE_LEANMILL_REACH_INVENT=1): the isomorphism
    engine, on the fixed-primitive reach-cap ceiling, surfaced Kronecker field-extension / Kalman
    controllability: a target OUTSIDE the span of the current primitive vocabulary is unreachable by
    more search within it — you must ADJOIN a primitive. This is NOT the reverted blanket promotion:
    it fires invent EARLY only on an OUT-OF-SPAN signal — a direct (commutative) move returned
    `unknown_identifier` (a missing primitive) — so the doomed resource escalation (cold_shot/frontier,
    more of the same in-span search) is skipped. A near-miss, a noisy failure (`other_error`:
    syntax/import/elaboration), or a no-telemetry move does NOT trigger it (only the missing-primitive
    signal does; zero-progress alone was removed — it conflated genuine-stuck with noise). Default-off ⇒ plain
    order, byte-identical to the non-promotion behavior. Lift-test: does criterion-gated invent close
    more out-of-span targets / save budget vs the plain menu (the revert only refuted BLANKET promotion).
    """
    # A/B MENU RESTRICTION (ZTARE_LEANMILL_MENU, default "full" = parity): "native_warm" restricts the
    # menu to native_hammer + claude_warm (no cold/frontier/conjecture/strategist tail), so the equal-total-
    # budget A/B compares {native+warm only} vs {full menu} at the SAME per-move caps + wallclock — the ONLY
    # difference being tail availability (unconfounded). Default ⇒ no filter (byte-identical to v1).
    _menu_allowed = ((MOVE_NATIVE_HAMMER, MOVE_CLAUDE_WARM)
                     if os.environ.get("ZTARE_LEANMILL_MENU", "full") == "native_warm" else None)
    # #53 apparatus_no_conjecture CONTROL ARM (ZTARE_LEANMILL_NO_CONJECTURE=1, default-OFF = byte-identical): excludes
    # MOVE_CONJECTURE from EVERY selection path (router/REACH_INVENT/fixed-order; UCB filters in _ucb_move_policy) so the
    # obstruction/decomposition-lift ablation has a clean control — it was hardwired in MOVE_ORDER with no off-flag.
    _no_conjecture = os.environ.get("ZTARE_LEANMILL_NO_CONJECTURE") == "1"
    # TARGET-CONDITIONED MOVE ROUTER (ZTARE_LEANMILL_MOVE_ROUTER=1, default-OFF): the reachability fix —
    # after the FREE native probe, PROMOTE the move whose precondition matches THIS target (generalizes the
    # witness gate to all moves). Fires only once native_hammer is tried (native keeps first crack), so it
    # composes with both the UCB and fixed-order paths; caller-verified enabled/affordable/untried. This is
    # what makes the strategist/exogenous tail REACHABLE (the apparatus-lift run showed it never fires otherwise).
    if (_menu_allowed is None and os.environ.get("ZTARE_LEANMILL_MOVE_ROUTER", "1") != "0"   # DEFAULT-ON 2026-06-12 (selection-only; kernel ratifies; =0 reverts)
            and MOVE_NATIVE_HAMMER in node.moves_tried):
        _routed = move_router(node)
        if (_routed and _routed not in node.moves_tried and MOVE_COST.get(_routed, 1.0) <= budget_remaining
                and not (_no_conjecture and _routed == MOVE_CONJECTURE)):
            return _routed
    # WITNESS TRANSPORT (ZTARE_LEANMILL_WITNESS_TRANSPORT=1, default-OFF): a gate-triggered COMPUTATIONAL
    # closure move. Offered AFTER native_hammer (the free native bridges — omega/polyrith/decide — get first
    # crack) but BEFORE the LLM moves, and ONLY when the goal is a computable non-linear existential (the
    # SymPy niche). The kernel ratifies the injected witness (no false-closure surface). Composes with both
    # the UCB and fixed-order paths because it fires only once native is already tried.
    if (_menu_allowed is None
            and os.environ.get("ZTARE_LEANMILL_WITNESS_TRANSPORT", "1") != "0"   # DEFAULT-ON 2026-06-12
            and MOVE_WITNESS_TRANSPORT not in node.moves_tried
            and MOVE_NATIVE_HAMMER in node.moves_tried
            and MOVE_COST.get(MOVE_WITNESS_TRANSPORT, 1.0) <= budget_remaining
            and _witness_transport_eligible(node)):
        return MOVE_WITNESS_TRANSPORT
    # UCB-OVER-MOVES (ZTARE_LEANMILL_UCB_MOVES=1, default OFF = byte-identical fixed-order policy): replace
    # the fixed-priority walk + last-place strategist tail with a calibrated bandit that makes every enabled
    # move reachable (the move-starvation fix). Short-circuits the fixed-order body below; respects the same
    # _menu_allowed A/B restriction. The REACH_INVENT criterion is a SEPARATE default-off experiment on the
    # fixed-order path, so the two never compose.
    if os.environ.get("ZTARE_LEANMILL_UCB_MOVES") == "1":
        return _ucb_move_policy(node, budget_remaining, defer_threshold, _menu_allowed)
    if (_menu_allowed is None
            and not _no_conjecture
            and os.environ.get("ZTARE_LEANMILL_REACH_INVENT") == "1"
            and MOVE_CONJECTURE not in node.moves_tried
            and MOVE_COST.get(MOVE_CONJECTURE, 1.0) <= budget_remaining
            and any(move_class(m) == "commutative" for m in node.moves_tried)
            and node.last_error_class == "unknown_identifier"):
        # out-of-span signal = a direct move hit a MISSING PRIMITIVE (unknown_identifier) → adjoin
        # (invent). Adversarial review (2026-06-04) removed the `best_progress <= 0.0` disjunct: it
        # also fired on `other_error` (syntax/import/elaboration noise) and on the no-telemetry default
        # (best_progress=0.0 unset), spuriously pre-empting the strong-direct move. unknown_identifier
        # is the only clean out-of-span signal; a noisy failure is NOT one.
        if max(_effective_est_p(node, MOVE_CONJECTURE), node.best_progress) >= defer_threshold:
            return MOVE_CONJECTURE
    for move in _active_move_order():
        if move in node.moves_tried:
            continue
        if _no_conjecture and move == MOVE_CONJECTURE:
            continue   # #53 apparatus_no_conjecture control arm: drop conjecture, fall through to strategist/DEFER
        if _menu_allowed is not None and move not in _menu_allowed:
            continue   # A/B restricted menu: skip the tail moves entirely
        cost = MOVE_COST.get(move, 1.0)
        if cost > budget_remaining:
            continue
        # Effective value = exogenous est_p_seed (retrieval) override, else the (calibrated)
        # move prior. Observed partial progress floors it: a node already at 1 goal remaining
        # (progress≈0.5) is genuinely close, so it keeps earning moves rather than deferring.
        est_p = max(_effective_est_p(node, move), node.best_progress)
        if est_p >= defer_threshold:
            return move
    # STRATEGIST MOVES (wm3zp587b, default-OFF): the standard menu is now exhausted on this node — the
    # STUCK precondition. Offer a strategist move ONLY if its env flag is set (so default = byte-identical
    # straight-to-DEFER; no Barrington blanket-reorder). The leaf chooses the move; the kernel decides if
    # it counts — adding these gives a LEGAL honest move when direct proof is infeasible (the cheat was a
    # missing-move artifact, not too-much-freedom).
    if _menu_allowed is not None:
        return MOVE_DEFER   # A/B restricted menu: no strategist tail (native+warm only)
    strat = _strategist_move(node, budget_remaining)
    if strat is not None:
        return strat
    return MOVE_DEFER


_ROUTER_UNSET = object()   # sentinel for the per-node memoized counterexample result in move_router


def move_router(node: DagNode) -> "Optional[str]":
    """TARGET-CONDITIONED MOVE ROUTER (the reachability fix) — examine the goal's STRUCTURE + the failure
    SIGNAL and return the matched high-value move, selected on a PRECONDITION MATCH rather than its menu
    position. So the right move FIRES instead of starving at the tail (the fixed-priority menu is the wrong
    abstraction: a move's queue position has nothing to do with whether it fits THIS target). Returns a move
    (caller verifies enabled/affordable/untried) or None (→ default menu). The kernel still ratifies — this
    only reorders SELECTION, never a closure decision. Each signal is gated by its move's enable flag so the
    A/B menu control still governs availability. Ordered by signal STRENGTH (cleanest/cheapest first)."""
    goal = node.goal_text or ""
    tried = node.moves_tried
    ec = node.last_error_class

    def _on(flag: str) -> bool:
        return os.environ.get(flag, "1") != "0"   # DEFAULT-ON 2026-06-12 (router legs; each move still kernel-ratified)

    # ── Signals that fire after the FREE native probe (the caller already gated on native tried) ──────
    # (A) COMPUTABLE ARITHMETIC ∃ → WITNESS-TRANSPORT before warm: SymPy is COMPLETE on its fragment, so it
    #     beats the warm LLM for an arithmetic witness — no reason to spend a warm call first.
    if _on("ZTARE_LEANMILL_WITNESS_TRANSPORT") and MOVE_WITNESS_TRANSPORT not in tried:
        try:
            from ztare.leanmill.solver.witness_transport import is_computable_existential
            if is_computable_existential(goal) is not None:
                return MOVE_WITNESS_TRANSPORT
        except Exception:  # noqa: BLE001
            pass
    # (B) MISSING PRIMITIVE (`unknown_identifier`) → INVENT (conjecture): warm can't conjure a missing
    #     primitive either, so invent early.
    if MOVE_CONJECTURE not in tried and ec == "unknown_identifier":
        return MOVE_CONJECTURE

    # ── Signals that COMPETE with the strong warm leaf — only AFTER warm has also failed (don't pre-empt a
    #    target warm would close directly; the apparatus-lift run showed warm closes the generalize tier). ──
    if MOVE_CLAUDE_WARM not in tried:
        return None
    # (C) COUNTEREXAMPLE EXISTS — the goal is computably FALSE (bounded SymPy grid search) → FALSIFY /
    #     CORROBORATE. Checked BEFORE the induction heuristic: a CONFIRMED counterexample is a stronger signal
    #     than "∀ stalled" (a false ∀ that stalls must go to falsify, NOT generalize).
    _fal = _on("ZTARE_LEANMILL_FALSIFY") and MOVE_FALSIFY not in tried
    _cor = _on("ZTARE_LEANMILL_CORROBORATE") and MOVE_CORROBORATE not in tried
    if _fal or _cor:
        # MEMOIZE the bounded counterexample subprocess on the node — the router is consulted once per move,
        # so without this a true ∀ goal would re-run the (fruitless) ~8s grid search every call.
        lf = getattr(node, "_router_false", _ROUTER_UNSET)
        if lf is _ROUTER_UNSET:
            try:
                from ztare.leanmill.solver.witness_transport import looks_false
                lf = looks_false(goal)
            except Exception:  # noqa: BLE001
                lf = None
            try:
                node._router_false = lf
            except Exception:  # noqa: BLE001 — dataclass may forbid the attr; correctness still holds
                pass
        if lf is not None:
            return MOVE_FALSIFY if _fal else MOVE_CORROBORATE
    # (D) INDUCTION STALL — a TRUE ∀-goal (no counterexample) whose attempt hit `unsolved_goals`/
    #     `tactic_failed` → GENERALIZE (a stronger internal IH).
    if (_on("ZTARE_LEANMILL_GENERALIZE") and MOVE_GENERALIZE not in tried
            and ec in ("unsolved_goals", "tactic_failed") and "∀" in goal):
        return MOVE_GENERALIZE
    return None


def _witness_transport_eligible(node: DagNode) -> bool:
    """True iff the node's goal is a computable existential (the SymPy witness-transport niche). Lazy import
    (avoids a hard dep + an import cycle); a cheap regex on the goal text. Any error ⇒ not eligible (safe)."""
    try:
        from ztare.leanmill.solver.witness_transport import is_computable_existential
        return is_computable_existential(node.goal_text or "") is not None
    except Exception:  # noqa: BLE001
        return False


def _strategist_move(node: DagNode, budget_remaining: float) -> Optional[str]:
    """Stuck-gated, env-flagged offer of a strategist move. Returns the move or None. Reached ONLY after
    the standard MOVE_ORDER walk is exhausted (cheap + direct + conjecture all tried/unaffordable) — so
    direct-first is preserved. Default-OFF: with no flag set this returns None and the policy DEFERs
    exactly as before (parity).

    TWO arms, sharing the SAME enabled/affordable/untried strategist set (the byte-identical gate):
      * SIGNAL arm (default when a flag is set): map the diagnostic → the right move. GENERALIZE on an
        INDUCTION-STALL signal (`unsolved_goals`/`tactic_failed`, the regime the literature says
        generalization rescues); SPECIALIZE as the last-resort honest rung. NOT blanket (the 2026-06-02
        blanket promotion was refuted).
      * RANDOM arm (`ZTARE_LEANMILL_STRATEGIST_RANDOM=1`): the CONTROL for the A=B master-discriminator —
        pick UNIFORMLY at random from the eligible set, IGNORING the signal mapping. The move-language is
        real iff `closed_or_rung@budget(SIGNAL) > closed_or_rung@budget(RANDOM)`; if they tie, SELECTION
        carries no information and the claim is dropped. Seeded per (run, node, history) for reproducibility.
    """
    gen_on = os.environ.get("ZTARE_LEANMILL_GENERALIZE", "1") != "0"      # DEFAULT-ON 2026-06-12 (stuck-gated + kernel-ratified; =0 reverts)
    spec_on = os.environ.get("ZTARE_LEANMILL_SPECIALIZE", "1") != "0"
    fal_on = os.environ.get("ZTARE_LEANMILL_FALSIFY", "1") != "0"
    step_on = os.environ.get("ZTARE_LEANMILL_TACTIC_STEP", "1") != "0"
    corr_on = os.environ.get("ZTARE_LEANMILL_CORROBORATE", "1") != "0"
    from ztare.leanmill.solver.sledgehammer import isabelle_hammer_live as _hammer_live
    sledge_on = _hammer_live()   # DEFAULT-ON when the Isabelle server is live (was opt-in `==1`); =0 force-off
    reflect_on = os.environ.get("ZTARE_LEANMILL_REFLECT", "1") != "0"
    abduce_on = os.environ.get("ZTARE_LEANMILL_ABDUCE", "1") != "0"
    lift_on = os.environ.get("ZTARE_LEANMILL_FUNCTORLIFT", "1") != "0"
    eligible: list[str] = []
    if (step_on and MOVE_TACTIC_STEP not in node.moves_tried
            and MOVE_COST.get(MOVE_TACTIC_STEP, 1.0) <= budget_remaining):
        eligible.append(MOVE_TACTIC_STEP)
    if (sledge_on and MOVE_SLEDGEHAMMER not in node.moves_tried
            and MOVE_COST.get(MOVE_SLEDGEHAMMER, 1.0) <= budget_remaining):
        eligible.append(MOVE_SLEDGEHAMMER)
    if (reflect_on and MOVE_REFLECTION not in node.moves_tried
            and MOVE_COST.get(MOVE_REFLECTION, 1.0) <= budget_remaining):
        eligible.append(MOVE_REFLECTION)
    if (abduce_on and MOVE_ABDUCE not in node.moves_tried
            and MOVE_COST.get(MOVE_ABDUCE, 1.0) <= budget_remaining):
        eligible.append(MOVE_ABDUCE)
    if (lift_on and MOVE_FUNCTOR_LIFT not in node.moves_tried
            and MOVE_COST.get(MOVE_FUNCTOR_LIFT, 1.0) <= budget_remaining):
        eligible.append(MOVE_FUNCTOR_LIFT)
    if (gen_on and MOVE_GENERALIZE not in node.moves_tried
            and MOVE_COST.get(MOVE_GENERALIZE, 1.0) <= budget_remaining):
        eligible.append(MOVE_GENERALIZE)
    if (spec_on and MOVE_SPECIALIZE not in node.moves_tried
            and MOVE_COST.get(MOVE_SPECIALIZE, 1.0) <= budget_remaining):
        eligible.append(MOVE_SPECIALIZE)
    if (fal_on and MOVE_FALSIFY not in node.moves_tried
            and MOVE_COST.get(MOVE_FALSIFY, 1.0) <= budget_remaining):
        eligible.append(MOVE_FALSIFY)
    if (corr_on and MOVE_CORROBORATE not in node.moves_tried
            and MOVE_COST.get(MOVE_CORROBORATE, 1.0) <= budget_remaining):
        eligible.append(MOVE_CORROBORATE)
    if not eligible:
        return None
    if os.environ.get("ZTARE_LEANMILL_STRATEGIST_RANDOM") == "1":
        import random as _random
        seed = os.environ.get("ZTARE_LEANMILL_STRATEGIST_SEED", "")
        rng = _random.Random(f"{seed}:{node.node_id}:{tuple(node.moves_tried)}")
        return rng.choice(sorted(eligible))   # uniform over the SAME set (exogenous carrier for A=B)
    # M4 TARGET-STRENGTH preference (ZTARE_LEANMILL_TARGET_STRENGTH=1, default-OFF): when frontier_triage
    # tagged the FULL target as likely-out-of-reach (strong_missing — needs machinery absent from the
    # library), prefer the honest SPECIALIZE rung over burning more closure-seeking budget. NON-IATROGENIC:
    # only reached when ALREADY stuck (menu exhausted), so it can never pre-empt a direct attempt; and only
    # on the conjunctive strong_missing tag. Default-OFF ⇒ this branch is skipped (parity).
    if (os.environ.get("ZTARE_LEANMILL_TARGET_STRENGTH") == "1"
            and node.target_strength == "strong_missing" and MOVE_SPECIALIZE in eligible):
        return MOVE_SPECIALIZE
    # SIGNAL arm: GENERALIZE first (closure move, strictly more valuable when it fires) on an induction stall.
    if MOVE_GENERALIZE in eligible and node.last_error_class in ("unsolved_goals", "tactic_failed"):
        return MOVE_GENERALIZE
    # SLEDGEHAMMER — a CLOSURE attempt via RETRIEVED premises (the missing-premise regime: the leaf knows the
    # tactics but not WHICH Mathlib lemmas unlock the goal). Offered before the finer tactic-stepping / rung /
    # falsify moves; it still tries to close G as-stated (kernel-validated premises → exact?/aesop). FAIL-CLOSED
    # to a no-op when no Isabelle server is configured (the runner records 'no_server'), so it never starves the
    # later moves on a box without the external infra.
    if MOVE_SLEDGEHAMMER in eligible:
        return MOVE_SLEDGEHAMMER
    # REFLECTION — a CLOSURE attempt via a decision procedure on a finite/decidable goal (kernel-ratified
    # like generalize; native_decide axiom-banned). FUNCTOR_LIFT — a CLOSURE via a spectral bound on a
    # discrete goal (gated on the Mathlib bridge lemma existing). Both attack G AS-STATED, closure tier.
    if MOVE_REFLECTION in eligible:
        return MOVE_REFLECTION
    if MOVE_FUNCTOR_LIFT in eligible:
        return MOVE_FUNCTOR_LIFT
    # ABDUCE — a GROUNDED conjecture: cvc5 derives the missing premise on an arithmetic stall (replaces weak
    # free-generation). It SPAWNS a sub-target (never closes G), so it sits in the advance tier before SPECIALIZE.
    if MOVE_ABDUCE in eligible:
        return MOVE_ABDUCE
    # TACTIC_STEP — a CLOSURE attempt at finer (per-tactic) granularity when the whole-proof moves stalled;
    # offered before the rung/falsify moves (it still tries to close G as-stated).
    if MOVE_TACTIC_STEP in eligible:
        return MOVE_TACTIC_STEP
    # SPECIALIZE — honest rung (a rung NEVER closes G ⇒ verified progress, never a false win).
    if MOVE_SPECIALIZE in eligible:
        return MOVE_SPECIALIZE
    # CORROBORATE — the skeptic's CONSEQUENCE route, offered BEFORE direct falsify: a consequence K of G is
    # often FAR easier to refute (a decidable instance) than G itself, so when the goal looks false this is
    # the cheaper disproof. Same sink/gate as falsify; never closes G.
    if MOVE_CORROBORATE in eligible:
        return MOVE_CORROBORATE
    # FALSIFY — the skeptic's LAST resort (after closure-seeking moves AND the consequence route): when direct
    # proof keeps failing, the target may be FALSE. A kernel-checked ¬G is a first-class outcome, but it's
    # offered last because most targets are true; it never closes G (the kernel decides ¬G on the verbatim Prop).
    if MOVE_FALSIFY in eligible:
        return MOVE_FALSIFY
    return None


def _frontier_score(node: DagNode, budget_remaining: float) -> float:
    """Best-first key for an OPEN node: (est_p_close × value) − cost of the move
    the policy would pick. Higher = expand first. A node with no affordable move
    (policy returns DEFER) scores very low so it's drained last."""
    move = move_policy(node, budget_remaining)
    if move == MOVE_DEFER:
        return -1e9
    # Value-guided: rank by the SAME effective close-probability the policy acts on — so an
    # exogenous retrieval score (est_p_seed) drives expansion order, not the generic move prior.
    est_p = _effective_est_p(node, move)
    cost = MOVE_COST.get(move, 1.0)
    # Progress bonus (GP-187 gradient): a node that has shown partial progress is
    # expanded before an untouched sibling of equal static value.
    return (est_p * _node_value(node)) - cost + PROGRESS_WEIGHT * node.best_progress


def _backup_value(nodes: "dict[str, DagNode]", node: "DagNode", delta: float) -> None:
    """MCTS value-BACKUP: add `delta` (the realized reward of the move just applied at `node`) to EVERY
    ancestor's `subtree_value`, so a branch's track record informs future frontier selection. Walks up
    `parent_id` (the same chain `_propagate_closure` uses). Pure selection bookkeeping — NEVER touches closure
    soundness (the kernel still ratifies every close); the worst case is a sub-optimal expansion ORDER."""
    pid, hops = node.parent_id, 0
    while pid is not None and hops < 256:        # hop cap = cycle/loop backstop
        p = nodes.get(pid)
        if p is None:
            break
        p.subtree_value += delta
        pid, hops = p.parent_id, hops + 1


def _branch_value(nodes: "dict[str, DagNode]", node: "DagNode") -> float:
    """The backed-up reward accumulated along `node`'s ANCESTOR chain — how productive this branch has been."""
    s, pid, hops = 0.0, node.parent_id, 0
    while pid is not None and hops < 256:
        p = nodes.get(pid)
        if p is None:
            break
        s += p.subtree_value
        pid, hops = p.parent_id, hops + 1
    return s


def _frontier_select(open_nodes: list, budget_units: float, total_expansions: int,
                     nodes: "Optional[dict]" = None):
    """Choose ONE open node to expand. DEFAULT = greedy argmax of `_frontier_score` (byte-identical to the
    prior `sorted(...)[0]`). Under ZTARE_LEANMILL_UCB_FRONTIER=1 = UCB over the FRONTIER: add an exploration
    bonus that boosts an UNDER-EXPANDED node (node "visits" = len(moves_tried)) so the search explores diverse
    decomposition branches instead of tunneling on the single best-scoring node. The bonus is scaled by the
    frontier-score SPREAD (dimensionless `c`); DEFER-scored nodes (-1e9, no affordable move) are excluded from
    the UCB pool but remain the greedy fallback. At c=0 (or ≤1 live node) this reduces to greedy.

    VALUE-BACKUP (ZTARE_LEANMILL_VALUE_BACKUP=1, default off; needs `nodes` to walk ancestors): add
    `WEIGHT × _branch_value` so an open node in a PRODUCTIVE branch (closing/progressing descendants) outranks
    one in a doomed branch — the MCTS arm boosting (concentrate on a stuck node) and UCB-frontier (explore the
    under-expanded) do NOT cover. DEFER-scored nodes keep their -1e9 (never resurrected by a branch bonus)."""
    base = [(n, _frontier_score(n, budget_units)) for n in open_nodes]
    if (nodes is not None and os.environ.get("ZTARE_LEANMILL_VALUE_BACKUP") == "1"):
        _w = float(os.environ.get("ZTARE_LEANMILL_VALUE_BACKUP_WEIGHT", DEFAULT_VALUE_BACKUP_WEIGHT))
        base = [(n, sc + (_w * _branch_value(nodes, n) if sc > -1e8 else 0.0)) for n, sc in base]
    if os.environ.get("ZTARE_LEANMILL_UCB_FRONTIER") != "1":
        return max(base, key=lambda nb: nb[1])[0]
    live = [(n, s) for n, s in base if s > -1e8]   # exclude DEFER-scored nodes (no affordable move)
    if len(live) <= 1:
        return max(base, key=lambda nb: nb[1])[0]
    c = float(os.environ.get("ZTARE_LEANMILL_UCB_FRONTIER_C", DEFAULT_UCB_FRONTIER_C))
    ss = [s for _, s in live]
    span = max(max(ss) - min(ss),
               float(os.environ.get("ZTARE_LEANMILL_UCB_FRONTIER_MIN_SPAN", DEFAULT_UCB_FRONTIER_MIN_SPAN)))
    lnT = math.log(max(0, int(total_expansions)) + 1.0)
    return max(live, key=lambda nb: nb[1]
               + c * span * math.sqrt(lnT / (len(nb[0].moves_tried) + 1.0)))[0]


def _boost_factor(node: "DagNode") -> float:
    """BOOSTING (AdaBoost analog; ZTARE_LEANMILL_BOOST=1, default OFF = 1.0 parity). A node the frontier keeps
    re-selecting after ZTARE_LEANMILL_BOOST_AFTER (default DEFAULT_BOOST_AFTER) failed moves is a load-bearing
    BOTTLENECK rung → return ZTARE_LEANMILL_BOOST_MULT (default DEFAULT_BOOST_MULT) as a per-move budget cap
    MULTIPLIER, concentrating DEPTH on it. Pure + env-read-at-CALL so the in-process self-test (and any toggle)
    takes effect without a re-import. The downstream wallclock cap (solver_core _cap) bounds the boosted cap so
    one node can't exceed the whole budget."""
    if os.environ.get("ZTARE_LEANMILL_BOOST") != "1":
        return 1.0
    after = int(os.environ.get("ZTARE_LEANMILL_BOOST_AFTER", DEFAULT_BOOST_AFTER))
    mult = float(os.environ.get("ZTARE_LEANMILL_BOOST_MULT", DEFAULT_BOOST_MULT))
    return mult if len(node.moves_tried) >= after else 1.0


# ── LUBY RESTARTS (#116; ZTARE_LEANMILL_LUBY_RESTARTS=1, default OFF = byte-parity) ───────────────────
# Move-search runtimes are HEAVY-TAILED (the same observation that motivated the dispatch-layer Luby in
# `common/timeouts.luby`): a search can tunnel into one doomed frontier branch and grind down its
# move-budget-units without closing, when a FRESH exploration budget on the (re-scored) frontier would have
# found the close. The Luby–Sinclair–Zuckerman sequence (1,1,2,1,1,2,4,…) is the provably near-optimal
# restart schedule when the runtime distribution is unknown — NOT one long shot. Transposed to this search:
# a "restart" REFILLS the abstract move-budget-units to a fresh Luby-scaled window when the search has burned
# a window's worth of moves WITHOUT audited progress (the same stall signal the adaptive-termination block
# already computes). Restarts NEVER touch closure soundness — the kernel still ratifies every close; a restart
# only buys the search another exploration window on the SAME DAG (closed/rung nodes persist), so the worst
# case is "spends the wallclock backstop trying" — never a false closure. The wallclock + max_moves stay the
# hard outer bound (a restart cannot resurrect an exhausted wallclock). Reuses `timeouts.luby` (one home for
# the sequence). Default OFF ⇒ the budget-units monotonically deplete exactly as before (byte-identical).
DEFAULT_LUBY_RESTART_PATIENCE = 4   # consecutive no-progress moves that trigger a restart (≤ stall_patience)
DEFAULT_LUBY_MAX_RESTARTS = 6       # cap restarts so a pathological run can't loop forever inside the wallclock


def _luby_restart_unit(base_units: float, restart_n: int) -> float:
    """The refilled move-budget window for the `restart_n`-th restart (1-indexed): `luby(restart_n) * base`
    units, where `base` is the ORIGINAL move_budget_units the run started with. Pure; reuses the canonical
    Luby sequence in `common/timeouts`. Degenerate inputs clamp safely (never a starving 0)."""
    from ztare.common.timeouts import luby
    return max(1.0, float(base_units)) * luby(max(1, int(restart_n)))


# ── INTERNAL-STANDARD SPIKING (#116; ZTARE_LEANMILL_SPIKE=1, default OFF = byte-parity) ───────────────
# Borrowed from analytical chemistry: you cannot tell a TRULY-zero reading from a DEAD instrument unless you
# periodically inject a KNOWN quantity (the "internal standard") and confirm the apparatus registers it. The
# dead-instrument class here is the recurring one (memory: probes that never parse/run record a silent 0/N that
# masquerades as "this move can't close anything"). The PREFLIGHT carriers (preflight_carriers.run_preflight +
# solver_core.preflight_moves_alive) are the ONE-SHOT positive control at run START; SPIKING is the in-stream
# COMPLEMENT — periodically inject a trivially-closeable target INTO the live move stream and assert the move
# actually closed it. A spike that FAILS to close means the apparatus has gone dead MID-RUN (the move runner
# stopped parsing/compiling), so every subsequent 0/N is INADMISSIBLE — surfaced LOUD (same contract as
# solver_core._preflight_dead_loud_record), never a silent pass. Pure calibration: a spike result NEVER closes
# a real node, spawns no sub-goal, and is excluded from move_attribution credit — it only proves the apparatus
# is live. Default OFF ⇒ no spike target is ever injected (byte-identical move stream).
DEFAULT_SPIKE_EVERY = 8   # inject a spike once per this many real moves (calibration cadence; ≥1)

# The known-answer standard has an isolated target identity and a single
# deterministic closer.  It is posed with ``sorry`` because the production
# probe replaces that proof with the selected ``rfl`` tactic.
SPIKE_GOAL_TEXT = (
    "theorem _spike_internal_standard (n : Nat) : n + 0 = n := by sorry"
)


def spike_probe() -> DagNode:
    """A KNOWN-closeable calibration target (the analytical-chemistry internal standard): a fresh disposable
    DagNode carrying an isolated natural-number reflexivity target. It is outside the campaign DAG; the search
    runs one native-hammer move on it solely to confirm carrier availability, then discards it. Returns a new
    node each call (no shared mutable state across spikes)."""
    return DagNode(
        node_id="_spike",
        kind="calibration_control",
        goal_text=SPIKE_GOAL_TEXT,
    )


def spike_closed(result: "MoveResult") -> bool:
    """Read only the disposable carrier-control field.

    Calibration never passes through theorem governance and therefore cannot
    mint a ratified close for either the control or the campaign target.
    """
    return bool(
        result is not None and result.calibration_available is True
    )


def _spike_dead_loud(restart_detail: str) -> None:
    """Fail-LOUD when a spike does not close — a dead apparatus mid-run can never be a silent 0/N. Mirrors
    solver_core._preflight_dead_loud_record's banner contract; kept dependency-light (a print) so this module
    stays import-cycle-free. The caller also stamps a `spike` event into the trace for the structured record."""
    bar = "=" * 70
    print(f"\n{bar}\n⚠ DEAD APPARATUS (spike) — the internal-standard probe '{SPIKE_GOAL_TEXT}' did NOT close.\n"
          f"  {restart_detail}\n  Every subsequent move 0/N is INADMISSIBLE until the move runner is fixed "
          f"(probe assembly / carrier).\n{bar}\n", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4. residual_to_lever — no silent deaths
# ─────────────────────────────────────────────────────────────────────────────

def _stayed_in_commutative_subgroup(node: DagNode) -> bool:
    """The node spent ≥1 commutative (spraying) move and NEVER reached the
    non-commutative core (conjecture/decompose/reframe). Barrington: this is the
    'solvable subgroup' regime — it collapses, so the lever is to add a
    non-commutative move, NOT more budget/width."""
    cls = {move_class(m) for m in node.moves_tried}
    return "commutative" in cls and "non_commutative" not in cls


def residual_to_lever(node: DagNode) -> str:
    """Resolve a FINISHED node to exactly one of {closure | exact_gap |
    falsifier | retired_impossible | new_sub_target} and set node.next_lever.
    Every finished node MUST resolve; this is what guarantees no attempt dies
    silently. Returns the resolution token.

    For a non-closing node the lever is annotated by the move-class history as a NEUTRAL
    DIAGNOSTIC: a node that died still spraying (commutative/direct-only, never reached the
    invent move) is flagged `escalate_noncommutative` — i.e. "the structure-changing move
    was not tried." This is informational, NOT a prescription: testing (v26 + APN frontier,
    kernel-arbitrated) showed the invent move did not beat a strong direct attempt, so this
    flags the failure mode without claiming invention will close it. The returned TOKEN stays
    in the stable enum (the annotation rides in next_lever) so consumers are unaffected."""
    if node.status == "closed":
        node.next_lever = (
            f"closure: node {node.node_id} ({node.kind}) ratified; "
            "propagate to parent / hand typed-exit to governance"
        )
        return "closure"
    if node.status == "falsifier":
        node.next_lever = (
            f"falsifier: node {node.node_id} exposed a falsifying candidate; "
            "route to falsification review (the target as stated may be false)"
        )
        return "falsifier"
    if node.status == "rung":
        node.next_lever = (
            f"rung: node {node.node_id} produced a kernel-verified WEAKER special case "
            f"({node.residual or 'special case'}); the full goal remains OPEN — next lever: "
            "GENERALIZE the rung toward the full statement, or escalate to a stronger prover / human"
        )
        return "rung"
    if node.status == "retired":
        if _stayed_in_commutative_subgroup(node):
            node.next_lever = (
                f"escalate_noncommutative(diagnostic): node {node.node_id} retired having tried "
                f"ONLY commutative/direct moves {node.moves_tried} — the invent/decompose move "
                "was not reached. (Diagnostic only: tested invent ≯ strong-direct, so this flags "
                "the failure mode, not a guaranteed lever; escalate to a stronger prover/human.)"
            )
        else:
            node.next_lever = (
                f"retired_impossible: node {node.node_id} retired "
                f"({node.residual or 'no affordable move / out of budget'}) after the "
                "non-commutative core was also spent — genuine wall (new math / stronger prover)"
            )
        return "retired_impossible"
    if node.status == "exact_gap":
        if _stayed_in_commutative_subgroup(node):
            node.next_lever = (
                f"escalate_noncommutative(diagnostic): node {node.node_id} deferred having tried "
                f"ONLY commutative/direct moves {node.moves_tried} — invent/decompose not reached. "
                "(Diagnostic only: tested invent ≯ strong-direct; flags the failure mode, not a "
                "guaranteed lever — escalate to a stronger prover/human.)"
            )
        else:
            node.next_lever = (
                f"exact_gap: node {node.node_id} deferred at marginal P(close) below "
                "threshold after the non-commutative core was tried; emit as the exact "
                "remaining obligation for a future lever (stronger prover slot / human)"
            )
        return "exact_gap"
    # An open node can carry a diagnostic residual, but it is not a theorem
    # until a producer supplies `new_sub_goal_text`.
    node.next_lever = (
        f"exact_gap: node {node.node_id} retains diagnostic residual "
        f"'{node.residual or 'unspecified'}'; require a typed proposed theorem before spawning work"
    )
    return "exact_gap"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Governed best-first search
# ─────────────────────────────────────────────────────────────────────────────

def _propagate_closure(nodes: dict[str, DagNode], node: DagNode,
                       trace: list[dict]) -> None:
    """When `node` closes, a parent whose children ALL close → closes too.
    Walk up the chain. Substrate-agnostic structural propagation."""
    pid = node.parent_id
    while pid is not None:
        parent = nodes.get(pid)
        if parent is None or parent.status == "closed":
            break
        kids = _children(nodes, pid)
        if kids and all(k.status == "closed" for k in kids):
            # SINGLE-DOOR SOUNDNESS (2026-06-25 RCA): a parent closes by PROPAGATION only when its children
            # RE-PROVE the parent goal (premise-anchored restatements) — then a closed child's proof_text IS a
            # proof of the parent, so the parent is genuinely kernel-proven and we carry that proof up. When ANY
            # child is a GENUINE decomposition (`composition_required` — a top-level ∧/↔ conjunct or a contract
            # sub_goal that proves a DISTINCT lemma), closing the children does NOT kernel-prove the parent: that
            # needs the And-intro composite (`composite_ratify`) or the parent's own direct proof. WITHHOLD the
            # status-flip — never a false closure of G via uncomposed lemmas. This is the documented invariant
            # (arch "governed obligation-DAG search"); it now keys on the PROPERTY, not the
            # `ZTARE_CONJECTURE_DECOMPOSE` flag (the old flag-keyed guard silently false-cleaned conjunct
            # children in the default config — a conjunctive root flipped to "closed" with an EMPTY proof).
            if any(k.composition_required for k in kids):
                trace.append({"event": "parent_close_withheld_pending_composite_ratification",
                              "node_id": parent.node_id, "via_children": [k.node_id for k in kids],
                              "reason": "genuine decomposition — parent needs a kernel And-intro composite, "
                                        "not a status-flip"})
                break
            # children re-prove the parent → propagate WITH a real proof_text (no proof ⇒ withhold, never a
            # status-only close: the single-door invariant `closed ⟺ kernel-verified proof_text`).
            _proof = parent.proof_text or next((k.proof_text for k in kids if (k.proof_text or "").strip()), "")
            if not _proof.strip():
                trace.append({"event": "parent_close_withheld_no_proof_text",
                              "node_id": parent.node_id, "via_children": [k.node_id for k in kids]})
                break
            parent.status = "closed"
            parent.proof_text = _proof
            parent.next_lever = ""  # set below by residual_to_lever
            residual_to_lever(parent)
            trace.append({
                "event": "parent_closed_by_children",
                "node_id": parent.node_id,
                "via_children": [k.node_id for k in kids],
            })
            pid = parent.parent_id
        else:
            break


def run_governed_dag_search(
    contract: dict,
    goal_text: str,
    move_runner: MoveRunner,
    *,
    premise_shelf: Optional[list] = None,
    max_moves: int = 12,
    wallclock_budget_s: float = 600.0,
    move_budget_units: float = 20.0,
    defer_threshold: float = DEFAULT_DEFER_THRESHOLD,
    cache=None,   # optional ProofCache (COMPRESS+SCALE): reuse + bank verified lemmas
    cache_verify=None,  # optional (goal_text, cached_proof)->bool: RE-VERIFY a cache hit in THIS
                        # context before closing (no-false-closure on reuse). None ⇒ trust (mock).
    cache_get=None,  # optional (DagNode)->proof|None: context-bound lookup supplied by the solver.
    cache_verify_node=None,  # optional (DagNode, proof)->bool: context-bound reverify supplied by the solver.
    cache_put=None,  # optional (DagNode, proof)->None: context-bound deposit supplied by the solver.
    on_cache_reuse=None,  # optional (node_id, goal_text, reverified: bool, wallclock_s: float)->None:
                          # TELEMETRY hook for a CLOSED-FROM-CACHE reuse. The cache hit closes + `continue`s
                          # BEFORE move_runner, so without this the reuse writes NO attempts-DB row and is
                          # invisible to move_yield_report / exogenous_move_telemetry (audit 2026-06-07 gap #3).
                          # solver_core injects a thin _record_attempt(move="cache_reuse"); None ⇒ no-op (tests).
    target_strength: str = "",  # M4: frontier_triage strength tag stamped onto nodes (advisory steer)
) -> dict:
    """Governed best-first search over the ex-ante obligation DAG.

    The search PROPOSES candidate moves; the injected `move_runner` RATIFIES
    each result through the existing governance (kernel + MNC). A node closes
    ONLY on a ratified close (MoveResult.ratified_close). Budget-bounded by
    max_moves AND wallclock AND abstract move-budget-units.

    Returns a structured result: the final DAG (as node dicts), the move trace,
    the root verdict, per-node levers, and per-move attribution.
    """
    nodes = build_obligation_dag(contract, goal_text, premise_shelf, target_strength=target_strength)
    root_id = "n0_root"
    trace: list[dict] = []
    move_attribution: list[dict] = []
    start = time.time()
    budget_units = float(move_budget_units)
    moves_made = 0
    # ADAPTIVE termination — track AUDITED progress so the budget follows PROGRESS, not an arbitrary clock.
    _best_sig = None   # (closed+rung count, best partial-progress); strictly increasing while productive
    _stall = 0
    # LUBY RESTARTS (#116; ZTARE_LEANMILL_LUBY_RESTARTS=1, default OFF = byte-parity). When ON: a search that
    # burns `LUBY_RESTART_PATIENCE` consecutive no-AUDITED-progress moves with budget still left has tunnelled
    # into a doomed branch — REFILL the move-budget-units to a fresh Luby-scaled window (luby(n) × the original
    # base) and reset the stall counter, so the re-scored frontier gets a clean exploration budget instead of
    # grinding the remaining units into one branch. Soundness untouched: the kernel still ratifies every close;
    # a restart only buys another window on the SAME DAG (closed/rung nodes persist). The wallclock + max_moves
    # stay the hard outer bound. OFF ⇒ these stay inert and budget_units deplete byte-identically.
    _luby_on = os.environ.get("ZTARE_LEANMILL_LUBY_RESTARTS") == "1"
    _luby_base_units = float(move_budget_units)   # the ORIGINAL window the run started with (restart unit base)
    _luby_restart_patience = int(os.environ.get("ZTARE_LEANMILL_LUBY_RESTART_PATIENCE",
                                                str(DEFAULT_LUBY_RESTART_PATIENCE)))
    _luby_max_restarts = int(os.environ.get("ZTARE_LEANMILL_LUBY_MAX_RESTARTS", str(DEFAULT_LUBY_MAX_RESTARTS)))
    _luby_restarts = 0          # restarts done so far (1-indexes the Luby sequence)
    _luby_stall = 0             # consecutive no-progress moves toward the NEXT restart (separate from _stall)
    # INTERNAL-STANDARD SPIKING (#116; ZTARE_LEANMILL_SPIKE=1, default OFF = byte-parity). When ON: every
    # `_spike_every` real moves, inject the known-answer standard (spike_probe) into the move stream and assert
    # the runner CLOSED it (spike_closed). A failed spike ⇒ the apparatus went dead mid-run ⇒ LOUD telemetry +
    # a `spike` trace event so the subsequent 0/N can never be a silent null. Spikes are pure calibration: they
    # do NOT spend budget_units, do NOT count as real moves, and are excluded from move_attribution credit.
    # OFF ⇒ no spike is ever injected (byte-identical move stream).
    _spike_on = os.environ.get("ZTARE_LEANMILL_SPIKE") == "1"
    _spike_every = max(1, int(os.environ.get("ZTARE_LEANMILL_SPIKE_EVERY", str(DEFAULT_SPIKE_EVERY))))
    _spikes_done = _spikes_live = _spikes_dead = 0

    while moves_made < max_moves:
        if (time.time() - start) >= wallclock_budget_s:
            trace.append({"event": "stop", "reason": "wallclock_budget_exhausted"})
            break
        if budget_units <= 0:
            trace.append({"event": "stop", "reason": "move_budget_units_exhausted"})
            break
        # Root closed → done (its children all closed, or it closed directly).
        if nodes[root_id].status == "closed":
            trace.append({"event": "stop", "reason": "root_closed"})
            break

        # Shared AUDITED-progress signal (more closed/rung nodes, or higher partial-progress) used by BOTH the
        # adaptive-termination stall and the Luby restart below. Computed once per loop (parity: identical to
        # the prior inline `_sig`).
        _open_now = [n for n in nodes.values() if n.status == "open"]
        _sig = (sum(1 for n in nodes.values() if n.status in ("closed", "rung")),
                round(max((getattr(n, "best_progress", 0.0) or 0.0 for n in _open_now), default=0.0), 3))
        _progressed = _best_sig is None or _sig > _best_sig

        # LUBY RESTART (default OFF). Checked BEFORE the adaptive-termination stall-break so that, when ON, a
        # stalled branch RESTARTS with a fresh Luby-scaled exploration window instead of terminating — until
        # the restart cap is hit, after which the adaptive break (or budget/wallclock backstop) ends the run.
        # OFF ⇒ this whole block is skipped and behaviour is byte-identical.
        if _luby_on and moves_made > 0:
            if _progressed:
                _luby_stall = 0
            else:
                _luby_stall += 1
                if _luby_stall >= _luby_restart_patience and _luby_restarts < _luby_max_restarts:
                    _luby_restarts += 1
                    budget_units = _luby_restart_unit(_luby_base_units, _luby_restarts)
                    _luby_stall = 0
                    _stall = 0   # a fresh window is genuine progress room — don't let the adaptive break fire
                    trace.append({"event": "luby_restart", "restart_n": _luby_restarts,
                                  "refilled_budget_units": round(budget_units, 3),
                                  "moves_made": moves_made})

        # ADAPTIVE termination: stop when the search STALLS — no AUDITED progress (more closed/rung nodes,
        # or higher partial-progress) in `stall_patience` consecutive moves. This makes the budget track
        # PROGRESS rather than a hardcoded clock; max_moves/wallclock are generous BACKSTOPS, not the bound,
        # so an open problem can run as long as it keeps climbing and stops the moment it's genuinely stuck.
        # Stopping early on a real stall only saves wasted budget — a node about to close shows RISING
        # best_progress (goal-count dropping), so it isn't a plateau. `ZTARE_DAG_STALL_PATIENCE=0` disables.
        _patience = int(os.environ.get("ZTARE_DAG_STALL_PATIENCE", "6"))
        if _patience > 0 and moves_made > 0:
            if _progressed:
                _best_sig, _stall = _sig, 0
            else:
                _stall += 1
                if _stall >= _patience:
                    trace.append({"event": "stop", "reason": "stalled_no_progress",
                                  "moves_without_progress": _stall, "moves_made": moves_made})
                    break
        elif _progressed:
            _best_sig = _sig   # keep _best_sig current even when the adaptive stall-break is disabled

        # Frontier = open nodes; pick the best by (est_p×value − cost) — greedy by default, or UCB over the
        # frontier (explore under-expanded branches) under ZTARE_LEANMILL_UCB_FRONTIER=1 (default-off parity).
        open_nodes = [n for n in nodes.values() if n.status == "open"]
        if not open_nodes:
            trace.append({"event": "stop", "reason": "no_open_nodes"})
            break
        node = _frontier_select(open_nodes, budget_units, moves_made, nodes)

        # BOOSTING (AdaBoost analog), default-off (ZTARE_LEANMILL_BOOST=1): a node that the frontier keeps
        # re-selecting after _BOOST_AFTER failed moves is a load-bearing BOTTLENECK rung — concentrate budget
        # DEPTH on it (give its next move a per-move cap MULTIPLIER) instead of spreading thin. The factor is
        # read by solver_core's move_runner→_cap; capped so one node can't eat the whole wallclock. Parity when
        # off: boost_factor stays 1.0 and _cap multiplies by 1.0 (byte-identical caps).
        node.boost_factor = _boost_factor(node)
        if node.boost_factor > 1.0:
            trace.append({"event": "boost", "node_id": node.node_id,
                          "moves_tried": len(node.moves_tried), "factor": node.boost_factor})

        # COMPRESS+SCALE: if this exact lemma is already in the global cache, reuse it.
        # NON-IATROGENIC GUARD (no-false-closure): a cached proof was verified in ANOTHER
        # context; it may not port (different imports/defs). If `cache_verify` is supplied,
        # RE-COMPILE the cached proof in THIS context and only close on a clean re-verify —
        # a cheap compile vs an expensive LLM move, so the reuse lift survives. A failed
        # re-verify is treated as a cache MISS (fall through to the normal moves), never a
        # closure. (cache_verify=None keeps the trust-the-cache path for the offline mock test.)
        cached = cache_get(node) if cache_get is not None else (
            cache.get(node.goal_text) if cache is not None and node.goal_text and cache.has(node.goal_text) else None
        )
        if cached:
            if cache_verify_node is not None:
                reuse_ok = bool(cache_verify_node(node, cached))
            elif cache_verify is not None:
                reuse_ok = bool(cache_verify(node.goal_text, cached))
            elif os.environ.get("ZTARE_LEANMILL_EQUIV_CACHE", "1") != "0":   # default-on 2026-06-19
                # MUST-FIX (adversarial review 2026-06-04): the equiv key is α-COLLAPSED and the
                # normalizer is scope-blind, so a hit can be a FALSE cross-theorem collapse. Without
                # an in-context re-verify there is no safety net → it would mint a WRONG closure. So an
                # equiv-cache hit with no cache_verify is treated as a MISS (fall through to moves),
                # NOT trusted. Exact-keying keeps the trust-on-None path (a clean string match is sound).
                reuse_ok = False
                trace.append({"event": "equiv_cache_hit_needs_reverify", "node_id": node.node_id})
            else:
                reuse_ok = True   # exact-key + no verify → trust (sound: identical normalized statement)
            if reuse_ok:
                node.status = "closed"
                node.proof_text = cached
                residual_to_lever(node)
                trace.append({"event": "closed_from_cache", "node_id": node.node_id,
                              "reverified": cache_verify_node is not None or cache_verify is not None})
                # TELEMETRY (audit gap #3): record the reuse as a first-class move so cache lift is sliceable
                # in move_yield_report / per-arm. Both an in-loop attribution row AND the injected DB hook —
                # the cache-hit `continue` below skips the normal move_attribution.append + move_runner record.
                move_attribution.append({
                    "node_id": node.node_id, "node_kind": node.kind, "move": MOVE_CACHE_REUSE,
                    "kernel_clean": True, "mnc_passed": True, "governance_ready": True,
                    "ratified_close": True,
                    "falsifier": None, "rung": None, "residual": None, "progress": 1.0,
                    "goals_remaining": 0, "error_class": "", "wallclock_s": time.time() - start,
                    "reverified": cache_verify_node is not None or cache_verify is not None,
                })
                if on_cache_reuse is not None:
                    try:
                        on_cache_reuse(node.node_id, node.goal_text,
                                       cache_verify_node is not None or cache_verify is not None, time.time() - start)
                    except Exception:  # telemetry must NEVER block a real reuse-closure
                        pass
                _propagate_closure(nodes, node, trace)
                continue
            trace.append({"event": "cache_reverify_failed", "node_id": node.node_id})

        move = move_policy(node, budget_units, defer_threshold)
        if move == MOVE_DEFER:
            # Explicit deferral → exact_gap (the no-silent-death path for a node
            # with no affordable / high-enough-EV move left).
            node.status = "exact_gap"
            node.residual = node.residual or "deferred_marginal_p_close_below_threshold"
            residual_to_lever(node)
            trace.append({"event": "defer", "node_id": node.node_id,
                          "lever": node.next_lever})
            continue

        # Run the move via the injected runner (it owns kernel-verify + MNC).
        node.moves_tried.append(move)
        result = move_runner(node, move, budget_units)
        moves_made += 1
        budget_units -= MOVE_COST.get(move, 1.0)

        # INTERNAL-STANDARD SPIKE (default OFF). Once per `_spike_every` real moves, inject the known-answer
        # standard and confirm the live apparatus CLOSES it. A failed spike ⇒ the move runner went dead
        # mid-run (probe assembly broke) ⇒ LOUD + a `spike` trace event, so the subsequent 0/N are flagged
        # INADMISSIBLE rather than silently believed. Pure calibration: the spike does NOT spend budget_units,
        # does NOT count toward moves_made, and is excluded from move_attribution credit. OFF ⇒ never runs.
        if _spike_on and moves_made % _spike_every == 0:
            _spike_node = spike_probe()
            try:
                _spike_res = move_runner(_spike_node, MOVE_NATIVE_HAMMER, budget_units)
                _live = spike_closed(_spike_res)
            except Exception as _se:  # a runner that THROWS on the standard is itself a dead-apparatus signal
                _live, _spike_res = False, None
                _spike_detail = f"move_runner raised on the spike: {type(_se).__name__}: {_se}"
            else:
                _spike_detail = ("apparatus live (standard closed)" if _live
                                 else "move ran but did not close the isolated rfl control")
            _spikes_done += 1
            if _live:
                _spikes_live += 1
            else:
                _spikes_dead += 1
                _spike_dead_loud(_spike_detail)
            trace.append({"event": "spike", "after_moves": moves_made, "live": _live,
                          "detail": _spike_detail})

        move_attribution.append({
            "node_id": node.node_id,
            "node_kind": node.kind,
            "move": move,
            "kernel_clean": result.kernel_clean,
            "mnc_passed": result.mnc_passed,
            "governance_ready": result.governance_ready,
            "ratified_close": result.ratified_close,
            "falsifier": result.falsifier,
            "rung": result.rung,
            "residual": result.residual,
            "progress": result.progress,
            "goals_remaining": result.goals_remaining,
            "error_class": result.error_class,
            "tail": (result.tail or "")[-300:],
            "wallclock_s": result.wallclock_s,
        })
        # Record the partial-progress gradient (GP-187) so the frontier/policy can
        # climb it on subsequent loops. Always safe: a ratified close ends the node
        # anyway; a non-close updates how promising the node looks.
        if result.progress and result.progress > node.best_progress:
            node.best_progress = result.progress
        if result.goals_remaining is not None:
            node.min_goals_remaining = (
                result.goals_remaining if node.min_goals_remaining is None
                else min(node.min_goals_remaining, result.goals_remaining))
        if result.error_class:
            node.last_error_class = result.error_class   # out-of-span signal for the invent-criterion

        # MCTS VALUE-BACKUP (ZTARE_LEANMILL_VALUE_BACKUP=1, default off ⇒ no-op): credit/debit this move's
        # realized reward to the ancestor chain so the frontier prefers productive branches. close=+1, rung=
        # partial-credit, otherwise the progress gained minus a small fail-penalty (so a branch of repeated
        # no-progress moves self-deprioritises). Pure selection bookkeeping; the kernel still ratifies closes.
        if os.environ.get("ZTARE_LEANMILL_VALUE_BACKUP") == "1":
            _fp = float(os.environ.get("ZTARE_LEANMILL_VALUE_BACKUP_FAIL_PENALTY", DEFAULT_VALUE_BACKUP_FAIL_PENALTY))
            _delta = (1.0 if result.ratified_close
                      else 0.5 if result.rung
                      else float(result.progress or 0.0) - _fp)
            _backup_value(nodes, node, _delta)

        if result.falsifier:
            node.status = "falsifier"
            node.residual = result.residual or "falsifying_candidate_found"
            residual_to_lever(node)
            trace.append({"event": "falsifier", "node_id": node.node_id,
                          "move": move, "lever": node.next_lever})
            # A falsifier on the root is terminal.
            if node.node_id == root_id:
                trace.append({"event": "stop", "reason": "root_falsified"})
                break
            continue

        if result.rung:
            # SPECIALIZE produced a kernel-verified WEAKER special case (G⇒G'). Honest partial progress,
            # NOT a closure: G stays documented-open. A rung NEVER propagates closure (G' is weaker, so
            # proving it cannot close G) and CANNOT mint a false win (kernel_clean stayed False). Record
            # the verified special case and resolve the node to the typed `rung` lever.
            node.status = "rung"
            node.proof_text = result.proof_text   # the verified special-case G' (for audit/reporting)
            node.residual = result.residual or "verified_special_case_rung"
            residual_to_lever(node)
            trace.append({"event": "rung", "node_id": node.node_id, "move": move,
                          "lever": node.next_lever})
            continue

        if result.ratified_close:
            # no-false-closure already enforced by ratified_close (kernel+MNC).
            node.status = "closed"
            node.proof_text = result.proof_text
            # COMPRESS+SCALE: bank the verified lemma so it's free everywhere else.
            if cache_put is not None and node.proof_text:
                cache_put(node, node.proof_text)
            elif cache is not None and node.proof_text:
                cache.put(node.goal_text, node.proof_text, source=f"dag:{node.node_id}")
            residual_to_lever(node)
            trace.append({"event": "closed", "node_id": node.node_id, "move": move,
                          "lever": node.next_lever})
            _propagate_closure(nodes, node, trace)
            continue

        # A proposal and a residual are different kinds of information. Only a
        # typed proposed theorem may become executable child work. A residual is
        # evidence about the current node; treating strings such as
        # `abduce_no_seed` or a compiler diagnosis as Lean source creates bogus
        # children and destroys source/target identity downstream.
        if result.new_sub_goal_text:
            new_idx = sum(1 for n in nodes.values() if n.kind == "sub_goal") + 1
            new_id = f"n{len(nodes)}_sub_goal_{new_idx}"
            nodes[new_id] = DagNode(
                node_id=new_id,
                kind="sub_goal",
                goal_text=result.new_sub_goal_text,
                parent_id=node.node_id,
                # A conjectured theorem cannot stand in for its parent proof.
                composition_required=True,
            )
            # Record that this open node spawned a sub-target (lever), without
            # finishing it — it still has remaining moves.
            node.residual = result.residual
            spawned = result.new_sub_goal_text
            trace.append({
                "event": "conjectured_sub_lemma" if move == MOVE_CONJECTURE else "new_sub_target",
                "node_id": node.node_id,
                "move": move,
                "new_node_id": new_id,
                "lever": (f"conjecture: proposed sub-lemma → {new_id}" if move == MOVE_CONJECTURE
                          else f"new_sub_target: residual '{result.residual}' → {new_id}"),
                "sub_goal_preview": (spawned or "")[:80],
            })
            # A sorry/non-clean attempt that yields a residual MUST NOT close the
            # node; it stays open and is later resolved (closure or exact_gap).
            continue

        if result.residual:
            node.residual = result.residual
            trace.append({"event": "residual", "node_id": node.node_id, "move": move,
                          "residual": result.residual[:160]})
            continue

        # Move failed, no residual, no falsifier: just a failed attempt. The node
        # stays open; the policy will pick the next move (or DEFER) next loop.
        trace.append({"event": "move_failed", "node_id": node.node_id, "move": move})

    # Drain: every open node still unfinished after the budget is resolved by
    # the policy's DEFER path → exact_gap (no silent deaths). Finished nodes that
    # never got a lever (e.g. spawned-sub-target parents still open) get one.
    for n in nodes.values():
        if n.status == "open":
            n.status = "exact_gap"
            n.residual = n.residual or "unfinished_at_budget_exhaustion"
            residual_to_lever(n)
        elif not n.next_lever:
            residual_to_lever(n)

    root = nodes[root_id]
    # SINGLE-DOOR INVARIANT ENFORCEMENT (the no-false-clean floor): `status == "closed"` MUST carry a
    # kernel-verified proof_text. Any closed node without one is a bookkeeping bug (a status-flip that bypassed
    # the kernel door) — DOWNGRADE it to an honest exact_gap, LOUDLY, rather than emit a closure with no proof.
    # This is the chokepoint that makes "closed" inseparable from "has a proof" so the propagate-close class
    # (and any future sibling that sets status without a proof) can never leak past here.
    for _n in nodes.values():
        if _n.status == "closed" and not (_n.proof_text or "").strip():
            _n.status = "exact_gap"
            _n.residual = _n.residual or "closed_without_proof_text_invariant_violation"
            residual_to_lever(_n)
            trace.append({"event": "closed_without_proof_DOWNGRADED_to_gap", "node_id": _n.node_id,
                          "note": "single-door invariant: closed ⟺ kernel-verified proof_text"})
    root_resolution = residual_to_lever(root)
    terminal_row = next(
        (row for row in reversed(move_attribution)
         if row.get("error_class") or row.get("tail") or row.get("move")),
        {},
    )
    terminal_signal = {
        "node_id": str(terminal_row.get("node_id") or root_id),
        "move": str(terminal_row.get("move") or ""),
        "error_class": str(terminal_row.get("error_class") or root.last_error_class or ""),
        "tail": str(terminal_row.get("tail") or "")[-300:],
        "stop_reason": next((str(row.get("reason") or "") for row in reversed(trace)
                             if row.get("event") == "stop"), ""),
    }

    return {
        "schema": "leanmill-governed-dag-search-v1",
        "root_status": root.status,
        "root_resolution": root_resolution,        # closure|exact_gap|falsifier|rung|retired_impossible|new_sub_target
        "root_proof_text": root.proof_text,
        "closed_or_exact_gap": root.status in ("closed", "exact_gap"),
        "moves_made": moves_made,
        "wallclock_s": round(time.time() - start, 3),
        "budget_units_remaining": round(budget_units, 3),
        "luby_restarts": _luby_restarts,   # 0 when the flag is off (byte-parity) or no restart was needed
        "spikes": {"done": _spikes_done, "live": _spikes_live, "dead": _spikes_dead},  # all 0 when SPIKE off
        "apparatus_live": _spikes_dead == 0,  # True unless a spike caught a dead apparatus mid-run

        "nodes": {nid: asdict(n) for nid, n in nodes.items()},
        "levers": {nid: n.next_lever for nid, n in nodes.items()},
        "terminal_signal": terminal_signal,
        "trace": trace,
        "move_attribution": move_attribution,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Offline self-test (MOCK move_runner; no Lean, no LLM)
# ─────────────────────────────────────────────────────────────────────────────

def _selftest() -> int:
    failures: list[str] = []
    # HERMETICITY: these tests assert the STRATEGIST tail is default-off (stuck ⇒ DEFER). But sledgehammer is now
    # DEFAULT-ON when the Isabelle server is LIVE (`sledge_on = isabelle_hammer_live()`, 2026-06-11), so on a box WITH
    # Isabelle (the VPS) a stuck node falls through to sledgehammer instead of DEFER and ~14 asserts flip. Force it OFF
    # for the suite so it is deterministic regardless of whether Isabelle is live on THIS box (surfaced by a VPS sync).
    import os as _os_h
    _sledge_save = _os_h.environ.get("ZTARE_LEANMILL_SLEDGEHAMMER")
    _os_h.environ["ZTARE_LEANMILL_SLEDGEHAMMER"] = "0"
    # HERMETICITY: most tests below assert the FULL 5-move cascade (cold_shot/frontier present); the agent-first
    # ladder (default) demotes those — force the full cascade so they're deterministic. A dedicated block (tagged
    # 'agentic_ladder') tests the agent-first collapse with it ON.
    _cascade_save = _os_h.environ.get("ZTARE_LEANMILL_FULL_CASCADE")
    _os_h.environ["ZTARE_LEANMILL_FULL_CASCADE"] = "1"
    # HERMETICITY (executors DEFAULT-ON 2026-06-12): the strategist/exogenous moves are now default-on; the
    # parity tests below assert flags-OFF behaviour, so force the whole set to "0" — each block that TESTS a
    # move sets its flag explicitly (same pattern as sledge/FULL_CASCADE above; restored at the end).
    _EXEC_FLAGS = ("ZTARE_LEANMILL_WITNESS_TRANSPORT", "ZTARE_LEANMILL_KRONECKER", "ZTARE_LEANMILL_FALSIFY",
                   "ZTARE_LEANMILL_CORROBORATE", "ZTARE_LEANMILL_REFLECT", "ZTARE_LEANMILL_ABDUCE",
                   "ZTARE_LEANMILL_FUNCTORLIFT", "ZTARE_LEANMILL_SPECIALIZE", "ZTARE_LEANMILL_GENERALIZE",
                   "ZTARE_LEANMILL_TACTIC_STEP")
    _exec_save = {k: _os_h.environ.get(k) for k in _EXEC_FLAGS}
    for _k in _EXEC_FLAGS:
        _os_h.environ[_k] = "0"

    def ok(name: str, cond: bool) -> None:
        status = "PASS" if cond else "FAIL"
        print(f"  [{status}] {name}")
        if not cond:
            failures.append(name)

    # --- Test 1: DAG build (root only, no decomposition) ---
    nodes = build_obligation_dag({}, "theorem T : True := by")
    ok("dag_build_root_only", len(nodes) == 1 and "n0_root" in nodes
       and nodes["n0_root"].kind == "root_goal")

    # --- Test 2: DAG build with contract decomposition ---
    contract_decomp = {"decomposition": [
        {"kind": "sub_goal", "goal_text": "sub A"},
        {"kind": "helper_lemma", "goal_text": "helper B"},
    ]}
    nodes2 = build_obligation_dag(contract_decomp, "root goal")
    children = _children(nodes2, "n0_root")
    ok("dag_build_decomposition", len(nodes2) == 3 and len(children) == 2
       and {c.kind for c in children} == {"sub_goal", "helper_lemma"})

    # --- Test 2b: governed STRUCTURAL decomposition (top-level ∧/↔) ---
    conj = derive_structural_decomposition("theorem t (h : H) : P x ∧ Q y := by")
    ok("decomp_conjunction_splits", len(conj) == 2
       and conj[0]["goal_text"].endswith("P x") and conj[1]["goal_text"].endswith("Q y"))
    ok("decomp_preserves_binders", all("(h : H)" in c["goal_text"] for c in conj))
    iff = derive_structural_decomposition("example : A ↔ B := by")
    ok("decomp_iff_to_implications", len(iff) == 2
       and "→" in iff[0]["goal_text"] and "→" in iff[1]["goal_text"])
    ok("decomp_atomic_no_split",
       derive_structural_decomposition("theorem t (x y : ℝ) : x ≤ y := by") == [])
    # top-level connective is →, the ∧ is nested in parens → must NOT split
    ok("decomp_nested_paren_guard",
       derive_structural_decomposition("example : (A ∧ B) → C := by") == [])
    ok("decomp_existential_shared_witness_guard",
       derive_structural_decomposition("theorem t : ∃ x : Nat, x = x ∧ x = 0 := by sorry") == [])
    # structural decomposition is the FALLBACK when the contract declares none
    nodes_struct = build_obligation_dag({}, "theorem t : P ∧ Q := by")
    ok("dag_struct_fallback", len(_children(nodes_struct, "n0_root")) == 2)
    # contract decomposition still wins over structural
    nodes_pri = build_obligation_dag(contract_decomp, "theorem t : P ∧ Q ∧ R := by")
    ok("dag_contract_priority", len(_children(nodes_pri, "n0_root")) == 2)

    # --- Test 2c: premise-anchored helpers for ATOMIC goals (exogenous score prior) ---
    shelf = [{"name": "le_trans", "score": 0.9}, {"name": "mul_le_mul", "score": 0.7},
             {"name": "abs_nonneg", "score": 0.3}]
    ph = derive_premise_helpers("theorem t (x y : ℝ) : x ≤ y := by", shelf, k=3)
    ok("premise_helpers_from_shelf", len(ph) == 3 and ph[0]["premise"] == "le_trans"
       and ph[0]["est_p_seed"] == 0.9 and all(h["kind"] == "helper_lemma" for h in ph))
    ok("premise_helpers_empty_shelf", derive_premise_helpers("g", []) == [])
    nodes_ph = build_obligation_dag({}, "theorem t (x y : ℝ) : x ≤ y := by", premise_shelf=shelf)
    ph_children = _children(nodes_ph, "n0_root")
    ok("dag_premise_helpers_atomic", len(ph_children) == 3
       and all(c.est_p_seed is not None and c.premise for c in ph_children))
    nodes_struct_shelf = build_obligation_dag({}, "theorem t : P ∧ Q := by", premise_shelf=shelf)
    sc = _children(nodes_struct_shelf, "n0_root")
    ok("structural_beats_premise_when_structured",
       len(sc) == 2 and all(c.premise is None for c in sc))
    # the exogenous retrieval-score prior drives the policy (replaces the heuristic stub)
    ok("est_p_seed_high_picks_move",
       move_policy(DagNode("hi", "helper_lemma", "g", est_p_seed=0.9), 100.0) != MOVE_DEFER)
    ok("est_p_seed_low_defers",
       move_policy(DagNode("lo", "helper_lemma", "g", est_p_seed=0.01), 100.0) == MOVE_DEFER)

    # --- Test 3: best-first ordering picks highest (est_p×value − cost) ---
    # root (value 1.0) vs a helper (value 0.5); both fresh, full budget.
    root = DagNode("r", "root_goal", "g")
    helper = DagNode("h", "helper_lemma", "g")
    ok("best_first_prefers_root",
       _frontier_score(root, 100.0) > _frontier_score(helper, 100.0))

    # --- Test 3b (VALUE-GUIDED): exogenous est_p_seed drives the frontier, not just the policy ---
    # Two premise-anchored helper nodes of EQUAL kind/value; the one with the higher retrieval
    # score must be expanded first. Before the fix both scored at the generic native prior (0.25),
    # so retrieval order was ignored — the bug this wires shut.
    hi = DagNode("hi", "helper_lemma", "g", est_p_seed=0.9)
    lo = DagNode("lo", "helper_lemma", "g", est_p_seed=0.2)
    ok("value_guided_high_retrieval_first",
       _frontier_score(hi, 100.0) > _frontier_score(lo, 100.0))
    # A high-retrieval premise node (0.9) outranks a generic node (move prior 0.25) of EQUAL value.
    gen = DagNode("gen", "helper_lemma", "g")  # no seed → generic move prior
    ok("value_guided_premise_beats_generic",
       _frontier_score(hi, 100.0) > _frontier_score(gen, 100.0))
    # Consistency: the frontier's effective est_p equals the value the policy acts on (no seed).
    nseed = DagNode("ns", "sub_goal", "g")
    ok("effective_est_p_consistent_no_seed",
       _effective_est_p(nseed, MOVE_NATIVE_HAMMER) == _move_prior(MOVE_NATIVE_HAMMER))
    ok("effective_est_p_seed_overrides",
       _effective_est_p(DagNode("s", "helper_lemma", "g", est_p_seed=0.77), MOVE_FRONTIER) == 0.77)

    # --- Test 4: SINGLE-DOOR — a GENUINE decomposition does NOT status-flip the parent closed ---
    # The root has NO direct proof; only its children (a contract sub_goal + helper = a genuine decomposition,
    # composition_required=True) close. Closing distinct sub-lemmas does NOT kernel-prove the parent without an
    # And-intro composite — so the root MUST be WITHHELD (honest exact_gap), never falsely "closed" with an
    # empty proof. This is the no-false-clean invariant (it encoded the OPPOSITE — the bug — before 2026-06-25).
    def runner_children_only(node: DagNode, move: str, budget: float) -> MoveResult:
        if node.kind == "root_goal":
            return MoveResult(move=move, kernel_clean=False, mnc_passed=False)
        return MoveResult(move=move, kernel_clean=True, mnc_passed=True, governance_ready=True,
                          proof_text=f"by exact proof_for_{node.node_id}")
    res4 = run_governed_dag_search(contract_decomp, "root goal", runner_children_only,
                                   max_moves=20)
    ok("decomposition_parent_NOT_falsely_closed", res4["root_status"] != "closed")
    ok("decomposition_parent_no_empty_proof_closure",
       not (res4["root_status"] == "closed" and not (res4["root_proof_text"] or "").strip()))
    res4_children = [n for nid, n in res4["nodes"].items() if nid != "n0_root"]
    ok("decomposition_children_still_closed",
       all(n["status"] == "closed" for n in res4_children))
    ok("decomposition_withhold_trace_emitted",
       any(e.get("event") == "parent_close_withheld_pending_composite_ratification" for e in res4["trace"]))

    # --- Test 4b: a CONJUNCTIVE structural split likewise withholds (the empirically-found false-clean) ---
    def runner_conj_children(node: DagNode, move: str, budget: float) -> MoveResult:
        if node.kind == "root_goal":
            return MoveResult(move=move, kernel_clean=False, mnc_passed=False)
        return MoveResult(move=move, kernel_clean=True, mnc_passed=True, governance_ready=True,
                          proof_text=f"by proof_of_{node.node_id}")
    import os as _os4b   # _selftest binds a function-local `os` (line ~2180 `import tempfile, os`) ⇒ alias
    _prev_decomp = _os4b.environ.pop("ZTARE_CONJECTURE_DECOMPOSE", None)   # exercise the DEFAULT (flag-off) config
    try:
        res4b = run_governed_dag_search({}, "theorem amm (x y : Real) : P x ∧ Q y ∧ R x := by",
                                        runner_conj_children, max_moves=30, move_budget_units=60.0)
    finally:
        if _prev_decomp is not None:
            _os4b.environ["ZTARE_CONJECTURE_DECOMPOSE"] = _prev_decomp
    ok("conjunctive_root_not_false_clean_default_config",
       not (res4b["root_status"] == "closed" and not (res4b["root_proof_text"] or "").strip()))

    # --- Test 4c: LEGITIMATE propagation — children that RE-PROVE the parent close it WITH a real proof ---
    # premise-anchored helpers (composition_required=False) each prove the parent goal; the parent closes and
    # CARRIES a child's proof_text (never a status-only close). Root direct attack fails, so only propagation can.
    shelf4c = [{"name": "le_trans", "score": 0.9}]
    def runner_premise_reproves(node: DagNode, move: str, budget: float) -> MoveResult:
        if node.kind == "root_goal":
            return MoveResult(move=move, kernel_clean=False, mnc_passed=False)
        return MoveResult(move=move, kernel_clean=True, mnc_passed=True,
                          governance_ready=True, proof_text="by exact le_trans h1 h2")
    res4c = run_governed_dag_search({}, "theorem t (x y : Real) : x <= y := by", runner_premise_reproves,
                                    premise_shelf=shelf4c, max_moves=20)
    ok("premise_reprove_propagation_closes_root", res4c["root_status"] == "closed")
    ok("premise_reprove_propagation_carries_proof", bool((res4c["root_proof_text"] or "").strip()))

    # --- Test 5: residual → new sub-goal node ---
    spawned = {"count": 0}

    def runner_residual_then_close(node: DagNode, move: str, budget: float) -> MoveResult:
        # First move on root: fail-with-residual (spawns sub_goal). Then close all.
        if node.kind == "root_goal" and spawned["count"] == 0:
            spawned["count"] += 1
            return MoveResult(move=move, kernel_clean=False, mnc_passed=False,
                              residual="missing_lemma_X",
                              new_sub_goal_text="lemma X : ...")
        return MoveResult(move=move, kernel_clean=True, mnc_passed=True, governance_ready=True,
                          proof_text="by closed")
    res5 = run_governed_dag_search({}, "root goal", runner_residual_then_close,
                                   max_moves=20)
    spawned_nodes = [n for n in res5["nodes"].values()
                     if n["kind"] == "sub_goal" and "missing_lemma_X" in (n["goal_text"] or "")
                     or n["goal_text"] == "lemma X : ..."]
    ok("residual_spawned_new_sub_goal", len(spawned_nodes) >= 1)

    # --- Test 6: DEFER → exact_gap ---
    # A runner that always fails (no residual). With a defer_threshold above every
    # move prior, the policy DEFERs immediately → root exact_gap, never closed.
    def runner_always_fail(node: DagNode, move: str, budget: float) -> MoveResult:
        return MoveResult(move=move, kernel_clean=False, mnc_passed=False)
    res6 = run_governed_dag_search({}, "root goal", runner_always_fail,
                                   max_moves=20, defer_threshold=0.99)
    ok("defer_to_exact_gap", res6["root_status"] == "exact_gap"
       and res6["root_resolution"] == "exact_gap")
    ok("defer_no_move_spent", res6["moves_made"] == 0)

    # --- Test 7 (REGRESSION): no-false-closure — a `sorry` proof must NOT close ---
    # Mock a move that returns a sorry proof: kernel_clean is False (the real
    # _is_compile_ok rejects sorry), so ratified_close is False → node exact_gap,
    # NEVER closed. This is the GP-246 hard invariant.
    def runner_sorry(node: DagNode, move: str, budget: float) -> MoveResult:
        # Simulate the worker's governance verdict on a `by sorry` proof:
        # kernel_clean=False because _is_compile_ok rejects the sorry warning.
        return MoveResult(move=move, kernel_clean=False, mnc_passed=False,
                          proof_text="by sorry",
                          tail="declaration uses `sorry`")
    res7 = run_governed_dag_search({}, "theorem T : P := by", runner_sorry,
                                   max_moves=20)
    ok("no_false_closure_sorry_not_closed", res7["root_status"] != "closed")
    ok("no_false_closure_sorry_is_exact_gap", res7["root_status"] == "exact_gap")
    # And a sorry that ALSO claims mnc_passed but kernel_clean=False must STILL
    # not close (both conditions required).
    def runner_sorry_but_mnc(node: DagNode, move: str, budget: float) -> MoveResult:
        return MoveResult(move=move, kernel_clean=False, mnc_passed=True,
                          proof_text="by sorry")
    res7b = run_governed_dag_search({}, "g", runner_sorry_but_mnc, max_moves=20)
    ok("no_false_closure_requires_kernel_clean", res7b["root_status"] != "closed")
    # A kernel-clean proof that FAILS MNC (leakage) must also NOT close.
    def runner_leakage(node: DagNode, move: str, budget: float) -> MoveResult:
        return MoveResult(move=move, kernel_clean=True, mnc_passed=False,
                          proof_text="by exact SomeMathlibLemma")
    res7c = run_governed_dag_search({}, "g", runner_leakage, max_moves=20)
    ok("no_false_closure_requires_mnc", res7c["root_status"] != "closed")
    # Compile+MNC alone cannot override the complete contract.
    def runner_governance_reject(node: DagNode, move: str, budget: float) -> MoveResult:
        return MoveResult(
            move=move,
            kernel_clean=True,
            mnc_passed=True,
            governance_ready=False,
            proof_text="by exact candidate",
        )
    res7d = run_governed_dag_search({}, "g", runner_governance_reject, max_moves=20)
    ok("no_false_closure_requires_full_governance", res7d["root_status"] != "closed")

    # --- Test 8: residual_to_lever resolves EVERY finished node (no silent death) ---
    res8 = run_governed_dag_search(contract_decomp, "root goal", runner_always_fail,
                                   max_moves=20, defer_threshold=0.99)
    all_levered = all(lever for lever in res8["levers"].values())
    ok("no_silent_deaths_all_nodes_levered", all_levered)

    # --- Test 9: falsifier path ---
    def runner_falsifier(node: DagNode, move: str, budget: float) -> MoveResult:
        return MoveResult(move=move, falsifier=True, residual="counterexample_found")
    res9 = run_governed_dag_search({}, "g", runner_falsifier, max_moves=20)
    ok("falsifier_root_resolution", res9["root_status"] == "falsifier"
       and res9["root_resolution"] == "falsifier")

    # --- Test 10 (GP-187 gradient): partial progress drives the search ---
    # 10a: a node that showed progress outranks a fresh sibling on the frontier.
    prog = DagNode("p", "sub_goal", "g"); prog.best_progress = 0.5
    fresh = DagNode("f", "sub_goal", "g")
    ok("gradient_boosts_frontier", _frontier_score(prog, 100.0) > _frontier_score(fresh, 100.0))
    # 10b: progress rescues a node from deferring when the static prior is below threshold.
    n_prog = DagNode("np", "helper_lemma", "g"); n_prog.best_progress = 0.6
    ok("progress_prevents_premature_defer",
       move_policy(n_prog, 100.0, defer_threshold=0.5) != MOVE_DEFER)
    ok("no_progress_defers_at_high_threshold",
       move_policy(DagNode("nn", "helper_lemma", "g"), 100.0, defer_threshold=0.99) == MOVE_DEFER)
    # #53 apparatus_no_conjecture CONTROL ARM: a node with all 4 closure moves tried selects conjecture by default;
    # ZTARE_LEANMILL_NO_CONJECTURE=1 excludes it → falls through to the (default-off) strategist tail → DEFER.
    import os as _osnc
    _ncn = DagNode("ncj", "sub_goal", "g")
    _ncn.moves_tried = [MOVE_NATIVE_HAMMER, MOVE_CLAUDE_WARM, MOVE_COLD_SHOT, MOVE_FRONTIER]
    _osnc.environ.pop("ZTARE_LEANMILL_NO_CONJECTURE", None)
    ok("no_conjecture OFF: stuck node still selects conjecture (byte-parity)",
       move_policy(_ncn, 100.0, defer_threshold=0.3) == MOVE_CONJECTURE)
    _osnc.environ["ZTARE_LEANMILL_NO_CONJECTURE"] = "1"
    ok("no_conjecture ON: conjecture excluded → DEFER (the apparatus_no_conjecture control)",
       move_policy(_ncn, 100.0, defer_threshold=0.3) == MOVE_DEFER)
    _osnc.environ.pop("ZTARE_LEANMILL_NO_CONJECTURE", None)
    # 10c: backward-compat — a runner that never sets progress leaves best_progress 0.
    n_bp = [n for n in res6["nodes"].values()]  # res6 used runner_always_fail (no progress)
    ok("gradient_backward_compatible", all(n.get("best_progress", 0.0) == 0.0 for n in n_bp))

    # --- Test 10f (UCB over the FRONTIER — node selection): parity + formula + explores under-expanded ---
    import os as _osf
    # nA: more-expanded (3 visits) but the costly moves are the ones already tried, so its next move is the
    # FREE native ⇒ higher base score (greedy winner). nB: unexpanded (0 visits), lower base. So a flip to nB
    # under UCB is unambiguously EXPLORATION, not nB just scoring higher.
    nA = DagNode("fa", "sub_goal", "g"); nA.moves_tried = [MOVE_COLD_SHOT, MOVE_FRONTIER, MOVE_CONJECTURE]; nA.best_progress = 0.7
    nB = DagNode("fb", "sub_goal", "g"); nB.best_progress = 0.2   # unexpanded (0 visits), lower base score
    _bA, _bB = _frontier_score(nA, 100.0), _frontier_score(nB, 100.0)
    ok("frontier_select_greedy_default", _frontier_select([nA, nB], 100.0, 10) is (nA if _bA >= _bB else nB))
    ok("frontier_select_single_node", _frontier_select([nA], 100.0, 10) is nA)
    _saved_f = {k: _osf.environ.get(k) for k in ("ZTARE_LEANMILL_UCB_FRONTIER", "ZTARE_LEANMILL_UCB_FRONTIER_C")}
    try:
        _osf.environ["ZTARE_LEANMILL_UCB_FRONTIER"] = "1"
        _span = max(abs(_bA - _bB), DEFAULT_UCB_FRONTIER_MIN_SPAN); _lnT = math.log(11.0)
        def _u(_n, _b, _c): return _b + _c * _span * math.sqrt(_lnT / (len(_n.moves_tried) + 1.0))
        for _c in ("0.0", "0.5", "5.0"):
            _osf.environ["ZTARE_LEANMILL_UCB_FRONTIER_C"] = _c
            _cc = float(_c)
            _want = nA if _u(nA, _bA, _cc) >= _u(nB, _bB, _cc) else nB
            ok(f"frontier_ucb_matches_formula_c{_c}", _frontier_select([nA, nB], 100.0, 10) is _want)
        # the mechanism BITES: at strong exploration the under-expanded node (0 visits) is chosen over the
        # more-expanded one even though the latter has the higher base (greedy) score.
        _osf.environ["ZTARE_LEANMILL_UCB_FRONTIER_C"] = "5.0"
        ok("frontier_ucb_explores_under_expanded_at_high_c",
           (_bA >= _bB) and _frontier_select([nA, nB], 100.0, 10) is nB)
    finally:
        for k, v in _saved_f.items():
            _osf.environ.pop(k, None) if v is None else _osf.environ.__setitem__(k, v)

    # --- Test 10c (VALUE-BACKUP — MCTS branch credit): the pure propagation + the gated frontier bonus ---
    _vr = DagNode(node_id="vr", kind="root_goal", goal_text="vg")
    _vpg = DagNode(node_id="vpg", kind="sub_goal", goal_text="vgg", parent_id="vr")   # productive branch
    _vpb = DagNode(node_id="vpb", kind="sub_goal", goal_text="vgb", parent_id="vr")   # doomed branch
    _vlg = DagNode(node_id="vlg", kind="sub_goal", goal_text="vlg", parent_id="vpg")  # open leaf (good branch)
    _vlb = DagNode(node_id="vlb", kind="sub_goal", goal_text="vlb", parent_id="vpb")  # open leaf (bad branch)
    _vnodes = {n.node_id: n for n in (_vr, _vpg, _vpb, _vlg, _vlb)}
    _backup_value(_vnodes, _vlg, +5.0)   # a descendant of vpg paid off → credit the chain up to root
    _backup_value(_vnodes, _vlb, -5.0)   # a descendant of vpb failed → debit its chain
    ok("value_backup_credits_ancestors_only",
       _vpg.subtree_value == 5.0 and _vpb.subtree_value == -5.0 and _vr.subtree_value == 0.0
       and _vlg.subtree_value == 0.0)   # the node itself is NOT credited (only ancestors)
    ok("branch_value_sums_ancestor_chain",
       _branch_value(_vnodes, _vlg) == 5.0 and _branch_value(_vnodes, _vlb) == -5.0)
    import os as _osv
    _saved_vb = _osv.environ.get("ZTARE_LEANMILL_VALUE_BACKUP")
    try:
        # the gated frontier bonus tips selection toward the productive branch when base scores tie (both
        # leaves are structurally identical ⇒ equal _frontier_score). OFF ⇒ no branch term (parity).
        _osv.environ["ZTARE_LEANMILL_VALUE_BACKUP"] = "1"
        ok("value_backup_frontier_prefers_productive_branch",
           _frontier_select([_vlb, _vlg], 100.0, 10, _vnodes) is _vlg)
    finally:
        _osv.environ.pop("ZTARE_LEANMILL_VALUE_BACKUP", None) if _saved_vb is None \
            else _osv.environ.__setitem__("ZTARE_LEANMILL_VALUE_BACKUP", _saved_vb)

    # --- Test 10b (BOOSTING — budget-concentration on a bottleneck rung): parity + bite + tunables ---
    import os as _osb
    _bk = ("ZTARE_LEANMILL_BOOST", "ZTARE_LEANMILL_BOOST_AFTER", "ZTARE_LEANMILL_BOOST_MULT")
    _bsave = {k: _osb.environ.get(k) for k in _bk}
    try:
        for k in _bk:
            _osb.environ.pop(k, None)
        # PARITY: flag off ⇒ factor 1.0 regardless of how many moves were tried.
        _nb = DagNode("b0", "sub_goal", "g"); _nb.moves_tried = [MOVE_NATIVE_HAMMER] * 9
        ok("boost_off_is_parity_factor_1", _boost_factor(_nb) == 1.0)
        _osb.environ["ZTARE_LEANMILL_BOOST"] = "1"
        # below the default threshold (DEFAULT_BOOST_AFTER=3) ⇒ still 1.0; at/above ⇒ the multiplier.
        _few = DagNode("b1", "sub_goal", "g"); _few.moves_tried = [MOVE_NATIVE_HAMMER, MOVE_CLAUDE_WARM]
        ok("boost_below_threshold_factor_1", _boost_factor(_few) == 1.0)
        _bn = DagNode("b2", "sub_goal", "g"); _bn.moves_tried = [MOVE_NATIVE_HAMMER] * DEFAULT_BOOST_AFTER
        ok("boost_at_threshold_multiplies", _boost_factor(_bn) == DEFAULT_BOOST_MULT)
        # TUNABLES bite: a higher AFTER de-triggers the same node; a custom MULT is honored.
        _osb.environ["ZTARE_LEANMILL_BOOST_AFTER"] = str(DEFAULT_BOOST_AFTER + 5)
        ok("boost_after_tunable_detriggers", _boost_factor(_bn) == 1.0)
        _osb.environ["ZTARE_LEANMILL_BOOST_AFTER"] = "1"
        _osb.environ["ZTARE_LEANMILL_BOOST_MULT"] = "3.5"
        ok("boost_mult_tunable_honored", _boost_factor(_bn) == 3.5)
        # the cap consumer (solver_core _cap) computes max(base, min(base×f, wallclock)) — wallclock-bounded
        # AND MONOTONE NON-DECREASING vs base. Lock both the normal bound AND the inversion case (base already
        # exceeds wallclock via a move floor) the 2026-06-07 bug exposed, even though _cap lives in solver_core.
        _bc = lambda base, f, wall: max(base, min(int(base * f), int(wall)))
        ok("boost_cap_bounded_by_wallclock", _bc(200, 3.5, 300) == 300)        # capped at wallclock
        ok("boost_cap_increases_when_room", _bc(48, 2.0, 600) == 96)           # boosted up
        ok("boost_cap_never_below_base", _bc(150, 2.0, 120) == 150)            # floor>wallclock ⇒ no reduction
    finally:
        for k, v in _bsave.items():
            _osb.environ.pop(k, None) if v is None else _osb.environ.__setitem__(k, v)

    # --- Test 10r (TARGET-CONDITIONED MOVE ROUTER): the reachability fix ---
    import os as _osr
    _rk = ("ZTARE_LEANMILL_MOVE_ROUTER", "ZTARE_LEANMILL_FALSIFY", "ZTARE_LEANMILL_GENERALIZE",
           "ZTARE_LEANMILL_WITNESS_TRANSPORT", "ZTARE_LEANMILL_CORROBORATE")
    _rsave = {k: _osr.environ.get(k) for k in _rk}
    try:
        for k in _rk:
            _osr.environ.pop(k, None)
        _osr.environ["ZTARE_LEANMILL_MOVE_ROUTER"] = "1"
        _osr.environ["ZTARE_LEANMILL_WITNESS_TRANSPORT"] = "1"
        _osr.environ["ZTARE_LEANMILL_FALSIFY"] = "1"
        _osr.environ["ZTARE_LEANMILL_GENERALIZE"] = "1"
        # (A) computable arithmetic ∃ + native tried → WITNESS-TRANSPORT (before warm; regex-only, no subproc).
        _ce = DagNode("rce", "sub_goal", "theorem t : ∃ x : ℤ, x^2 + x = 42 := by sorry"); _ce.moves_tried = [MOVE_NATIVE_HAMMER]
        ok("router_computable_exists_to_witness", move_router(_ce) == MOVE_WITNESS_TRANSPORT)
        # DON'T pre-empt warm: a ∀-stall with native tried but warm NOT tried → None (warm gets first crack).
        _fp = DagNode("rfp", "sub_goal", "theorem t : ∀ n : ℤ, n + 1 = n := by sorry")
        _fp.moves_tried = [MOVE_NATIVE_HAMMER]; _fp.last_error_class = "unsolved_goals"
        ok("router_does_not_preempt_warm", move_router(_fp) is None)
        # (C, the REORDER fix) a FALSE ∀ that stalled (native+warm tried) → FALSIFY, NOT generalize. The
        # counterexample value is memoized so the test needs no SymPy subprocess.
        _ff = DagNode("rff", "sub_goal", "theorem t : ∀ n : ℤ, n + 1 = n := by sorry")
        _ff.moves_tried = [MOVE_NATIVE_HAMMER, MOVE_CLAUDE_WARM]; _ff.last_error_class = "unsolved_goals"; _ff._router_false = ["0"]
        ok("router_false_forall_to_falsify_not_generalize", move_router(_ff) == MOVE_FALSIFY)
        # (D) a TRUE ∀ stall (no counterexample) → GENERALIZE.
        _tg = DagNode("rtg", "sub_goal", "theorem t : ∀ n : ℕ, P n := by sorry")
        _tg.moves_tried = [MOVE_NATIVE_HAMMER, MOVE_CLAUDE_WARM]; _tg.last_error_class = "unsolved_goals"; _tg._router_false = None
        ok("router_true_forall_stall_to_generalize", move_router(_tg) == MOVE_GENERALIZE)
        # (B) missing primitive (unknown_identifier) + native tried → CONJECTURE (invent early, before warm).
        _ui = DagNode("rui", "sub_goal", "theorem t : Foo n := by sorry")
        _ui.moves_tried = [MOVE_NATIVE_HAMMER]; _ui.last_error_class = "unknown_identifier"
        ok("router_unknown_id_to_conjecture", move_router(_ui) == MOVE_CONJECTURE)
        # WIRING: move_policy promotes the routed move (fresh node → native first; after native → router fires).
        _w = DagNode("rw", "sub_goal", "theorem t : ∃ x : ℤ, x^2 + x = 42 := by sorry")
        ok("router_policy_native_first", move_policy(_w, 100.0) == MOVE_NATIVE_HAMMER)
        _w.moves_tried = [MOVE_NATIVE_HAMMER]
        ok("router_policy_promotes_after_native", move_policy(_w, 100.0) == MOVE_WITNESS_TRANSPORT)
    finally:
        for k, v in _rsave.items():
            _osr.environ.pop(k, None) if v is None else _osr.environ.__setitem__(k, v)

    # --- Test 10u (UCB-over-moves): the move-reachability fix ---
    # PARITY: with the flag OFF, a fresh node picks the fixed-order first move (native_hammer) — unchanged.
    ok("ucb_off_is_fixed_order_native_first",
       move_policy(DagNode("u0", "sub_goal", "g"), 100.0) == MOVE_NATIVE_HAMMER)
    import os as _osu  # _selftest binds a function-local `os` later (line ~1397) ⇒ alias, per _os16/_os17
    _env_keys = ("ZTARE_LEANMILL_UCB_MOVES", "ZTARE_LEANMILL_FALSIFY", "ZTARE_LEANMILL_UCB_C")
    _saved_env = {k: _osu.environ.get(k) for k in _env_keys}
    try:
        _osu.environ["ZTARE_LEANMILL_UCB_MOVES"] = "1"
        _osu.environ.pop("ZTARE_LEANMILL_UCB_C", None)  # default c
        # (a) UCB VALUE-ORDERS the closure menu: frontier is the best-calibrated closer ⇒ UCB picks it on a
        # fresh node where the FIXED order would pick native first (native's measured value de-prioritized).
        set_move_priors({MOVE_NATIVE_HAMMER: 0.05, MOVE_CLAUDE_WARM: 0.20, MOVE_COLD_SHOT: 0.20,
                         MOVE_FRONTIER: 0.55, MOVE_CONJECTURE: 0.20})
        set_move_visits({MOVE_NATIVE_HAMMER: 50, MOVE_CLAUDE_WARM: 50, MOVE_COLD_SHOT: 50,
                         MOVE_FRONTIER: 50, MOVE_CONJECTURE: 50})
        ok("ucb_value_orders_closure_menu_frontier_over_native",
           move_policy(DagNode("u1", "sub_goal", "g"), 100.0) == MOVE_FRONTIER)
        # (b) UCB EXPLORES an under-used closer: equal Q, but frontier dormant (n=0) vs the others saturated;
        # the scale-invariant exploration bonus lifts the dormant closer above the saturated ones.
        set_move_priors({m: 0.20 for m in MOVE_ORDER})
        set_move_visits({MOVE_NATIVE_HAMMER: 500, MOVE_CLAUDE_WARM: 500, MOVE_COLD_SHOT: 500,
                         MOVE_CONJECTURE: 500, MOVE_FRONTIER: 0})
        ok("ucb_explores_under_used_closer_frontier_n0",
           move_policy(DagNode("u2", "sub_goal", "g"), 100.0) == MOVE_FRONTIER)
        # (c) UCB does NOT promote the strategist tail: even with FALSIFY enabled, a FRESH node (closure menu
        # non-empty) picks a CLOSER, never falsify — the tail is excluded from the UCB pool (the 2026-06-07
        # over-promotion fix: blind UCB ranked specialize/falsify ahead of the closers on a skewed snapshot).
        _osu.environ["ZTARE_LEANMILL_FALSIFY"] = "1"
        set_move_priors(None); set_move_visits({MOVE_NATIVE_HAMMER: 50, MOVE_CLAUDE_WARM: 50})
        ok("ucb_does_not_promote_strategist_tail_on_fresh_node",
           move_policy(DagNode("u3", "sub_goal", "g"), 100.0) in MOVE_ORDER)
        # (d) the strategist GATE is preserved: closure menu exhausted (all tried) + FALSIFY on ⇒ UCB falls
        # through to `_strategist_move` exactly as fixed-order (falsify reachable via the gate, not via UCB).
        _stk = DagNode("u4", "sub_goal", "g"); _stk.moves_tried = list(MOVE_ORDER)
        ok("ucb_preserves_strategist_gate_when_menu_exhausted",
           move_policy(_stk, 100.0) == MOVE_FALSIFY)
        # (e) DEFER on a hopeless node (high threshold, strategist off).
        _osu.environ["ZTARE_LEANMILL_FALSIFY"] = "0"   # hermetic: default-ON now
        set_move_visits({})
        ok("ucb_defers_hopeless_node",
           move_policy(DagNode("u5", "sub_goal", "g"), 100.0, defer_threshold=0.99) == MOVE_DEFER)
    finally:
        set_move_visits(None); set_move_priors(None)
        for k, v in _saved_env.items():
            if v is None:
                _osu.environ.pop(k, None)
            else:
                _osu.environ[k] = v
    # 10d: end-to-end — a failed move that reports progress is recorded, the node
    # keeps earning moves (does not defer), and closes on a later move.
    calls = {"n": 0}
    def runner_progress_then_close(node: DagNode, move: str, budget: float) -> MoveResult:
        calls["n"] += 1
        if calls["n"] == 1:
            return MoveResult(move=move, kernel_clean=False, mnc_passed=False,
                              goals_remaining=2, progress=0.33, error_class="unsolved_goals")
        return MoveResult(move=move, kernel_clean=True, mnc_passed=True,
                          governance_ready=True, proof_text="by ok")
    res10 = run_governed_dag_search({}, "theorem T : P := by", runner_progress_then_close,
                                    max_moves=20)
    ok("gradient_recorded_and_closed",
       res10["root_status"] == "closed"
       and any(a.get("progress") == 0.33 for a in res10["move_attribution"])
       and res10["nodes"]["n0_root"]["min_goals_remaining"] == 2)

    # --- Test 11: a conjectured child does not close its parent. ---
    cstate = {"conjectured": False}
    def runner_conjecture(node: DagNode, move: str, budget: float) -> MoveResult:
        if node.kind == "root_goal":
            if move == MOVE_CONJECTURE and not cstate["conjectured"]:
                cstate["conjectured"] = True
                return MoveResult(move=move, new_sub_goal_text="lemma helper_needed : H")
            return MoveResult(move=move, kernel_clean=False, mnc_passed=False)  # direct attempts fail
        # the conjectured helper child closes; root composition is still owed
        return MoveResult(move=move, kernel_clean=True, mnc_passed=True,
                          governance_ready=True, proof_text="by ok")
    res11 = run_governed_dag_search({}, "theorem T : P := by", runner_conjecture,
                                    max_moves=30, defer_threshold=0.0)
    ok("conjecture_spawns_sub_lemma",
       any(e.get("event") == "conjectured_sub_lemma" for e in res11["trace"]))
    ok("conjecture_child_does_not_launder_parent_closure",
       res11["root_status"] != "closed"
       and any(e.get("event") == "parent_close_withheld_pending_composite_ratification"
               for e in res11["trace"]))

    # --- Test 12 (COMPRESS+SCALE): cache reuse closes a node with zero moves; closing banks ---
    import tempfile, os
    from ztare.leanmill.solver.proof_cache import ProofCache
    db = tempfile.mktemp(suffix=".jsonl")
    pc = ProofCache(db)
    pc.put("theorem T : P := by", "by cached_proof", "preloaded")
    def runner_never(node, move, budget):   # would never close on its own
        return MoveResult(move=move, kernel_clean=False, mnc_passed=False)
    _reuse_log = []
    # `cache_verify` is REQUIRED for reuse now that ZTARE_LEANMILL_EQUIV_CACHE is default-ON (2026-06-19): an
    # α-collapsed hit with NO re-verify is a MISS (can't trust a scope-blind normalized key) — exactly the
    # production path (solver_core always passes cache_verify). A True re-verify ⇒ the reuse fires + closes.
    res12 = run_governed_dag_search({}, "theorem T : P := by", runner_never, max_moves=20, cache=pc,
                                    cache_verify=lambda g, p: True,
                                    on_cache_reuse=lambda nid, g, rev, wc: _reuse_log.append((nid, rev)))
    ok("cache_reuse_closes_zero_moves",
       res12["root_status"] == "closed" and res12["moves_made"] == 0
       and any(e.get("event") == "closed_from_cache" for e in res12["trace"]))
    # TELEMETRY (audit gap #3): the reuse is a first-class attributed move AND fires the DB hook (so it is
    # never invisible to move_yield_report / per-arm lift again).
    ok("cache_reuse_emits_attribution_row",
       any(a.get("move") == MOVE_CACHE_REUSE and a.get("ratified_close") for a in res12["move_attribution"]))
    ok("cache_reuse_fires_telemetry_hook", len(_reuse_log) == 1 and _reuse_log[0][0] == "n0_root")
    # closing banks to cache
    db2 = tempfile.mktemp(suffix=".jsonl"); pc2 = ProofCache(db2)
    def runner_close(node, move, budget):
        return MoveResult(move=move, kernel_clean=True, mnc_passed=True,
                          governance_ready=True, proof_text="by banked")
    run_governed_dag_search({}, "theorem U : Q := by", runner_close, max_moves=20, cache=pc2)
    ok("close_banks_to_cache", pc2.get("theorem U : Q := by") == "by banked")
    for f in (db, db2):
        if os.path.exists(f):
            os.remove(f)

    # --- Test 13 (BARRINGTON): non-commutative core promotion + typed lever ---
    # 13a: move_class taxonomy.
    ok("move_class_commutative",
       move_class(MOVE_NATIVE_HAMMER) == "commutative"
       and move_class(MOVE_FRONTIER) == "commutative")
    ok("move_class_noncommutative", move_class(MOVE_CONJECTURE) == "non_commutative")
    # 13b: NON-PROMOTION (REGRESSION) — the Barrington reorder was REFUTED on evidence
    # (invent never beat strong-direct), so the menu keeps its PLAIN order and invention is
    # NOT promoted. free probe → strong direct → resource → invent (last). The key guard:
    # after the free probe, the policy picks the STRONG-DIRECT move, NOT conjecture.
    fresh_n = DagNode("bf", "root_goal", "g")
    ok("plainorder_fresh_picks_free_probe",
       move_policy(fresh_n, 100.0) == MOVE_NATIVE_HAMMER)
    probed = DagNode("bp", "root_goal", "g"); probed.moves_tried = [MOVE_NATIVE_HAMMER]
    ok("plainorder_strong_direct_after_probe",
       move_policy(probed, 100.0) == MOVE_CLAUDE_WARM)
    # 13c: invention is NOT promoted ahead of resource-scaling — after the free probe and
    # strong-direct, the next move is a resource move (cold_shot), with conjecture LAST.
    sprayed = DagNode("bs", "root_goal", "g")
    sprayed.moves_tried = [MOVE_NATIVE_HAMMER, MOVE_CLAUDE_WARM]
    ok("plainorder_invent_not_promoted",
       move_policy(sprayed, 100.0) == MOVE_COLD_SHOT)
    drained = DagNode("bd", "root_goal", "g")
    drained.moves_tried = [MOVE_NATIVE_HAMMER, MOVE_CLAUDE_WARM, MOVE_COLD_SHOT, MOVE_FRONTIER]
    ok("plainorder_invent_is_last_resort",
       move_policy(drained, 100.0) == MOVE_CONJECTURE)
    # 13d: TYPED lever — a node that died still spraying emits escalate_noncommutative;
    # a node that also spent the core does NOT (it points at a genuine wall).
    spray_dead = DagNode("sd", "sub_goal", "g", status="exact_gap")
    spray_dead.moves_tried = [MOVE_NATIVE_HAMMER, MOVE_COLD_SHOT]
    residual_to_lever(spray_dead)
    ok("barrington_lever_escalate_after_spray_only",
       "escalate_noncommutative" in spray_dead.next_lever)
    core_dead = DagNode("cd", "sub_goal", "g", status="exact_gap")
    core_dead.moves_tried = [MOVE_NATIVE_HAMMER, MOVE_CONJECTURE]
    residual_to_lever(core_dead)
    ok("barrington_lever_wall_after_core",
       "escalate_noncommutative" not in core_dead.next_lever
       and "exact_gap" in core_dead.next_lever)
    # 13e: a node that NEVER moved (no spray) does not over-fire the escalation.
    untouched = DagNode("ut", "sub_goal", "g", status="exact_gap")
    residual_to_lever(untouched)
    ok("barrington_lever_no_fire_when_untouched",
       "escalate_noncommutative" not in untouched.next_lever)

    # --- Test 14 (Arc-H calibration override): default = stubs; installed priors change policy ---
    ok("calib_default_is_stub", _move_prior(MOVE_NATIVE_HAMMER) == MOVE_PRIOR_P_CLOSE[MOVE_NATIVE_HAMMER])
    # with the stub (native 0.25 ≥ threshold) a fresh node's first pick is the free native_hammer:
    ok("calib_stub_picks_native",
       move_policy(DagNode("c1", "root_goal", "g"), 100.0) == MOVE_NATIVE_HAMMER)
    # install a full calibrated map that down-weights native_hammer below the defer threshold
    # (mirrors the live attempts DB: native 0/29 ⇒ ~0.05); the policy must skip it for the
    # productive warm move — the data-driven behaviour change.
    set_move_priors({**MOVE_PRIOR_P_CLOSE, MOVE_NATIVE_HAMMER: 0.05})
    ok("calib_override_applies", abs(_move_prior(MOVE_NATIVE_HAMMER) - 0.05) < 1e-9)
    ok("calib_changes_policy_choice",
       move_policy(DagNode("c2", "root_goal", "g"), 100.0) == MOVE_CLAUDE_WARM)
    set_move_priors(None)  # revert — MUST restore stub behaviour exactly
    ok("calib_revert_restores_stub",
       _move_prior(MOVE_NATIVE_HAMMER) == MOVE_PRIOR_P_CLOSE[MOVE_NATIVE_HAMMER]
       and _CALIBRATED_PRIORS is None)

    # --- Test 15 (cache reuse is NON-IATROGENIC): cache_verify guards no-false-closure on reuse ---
    import tempfile as _tf2, os as _os2
    from ztare.leanmill.solver.proof_cache import ProofCache as _PC2
    _db15 = _tf2.mktemp(suffix=".jsonl"); _pc15 = _PC2(_db15)
    _pc15.put("theorem T : P := by", "by cached_but_maybe_unportable", "preloaded")
    def _runner_never15(node, move, budget):
        return MoveResult(move=move, kernel_clean=False, mnc_passed=False)
    # REJECTING re-verify (cached proof doesn't port) ⇒ cache hit must NOT close ⇒ exact_gap.
    r_rej = run_governed_dag_search({}, "theorem T : P := by", _runner_never15, max_moves=5,
                                    cache=_pc15, cache_verify=lambda g, p: False, defer_threshold=0.99)
    ok("cache_reverify_reject_no_false_closure",
       r_rej["root_status"] != "closed"
       and any(e.get("event") == "cache_reverify_failed" for e in r_rej["trace"]))
    # ACCEPTING re-verify ⇒ cache hit closes (reverified), zero moves = the compounding lift.
    r_acc = run_governed_dag_search({}, "theorem T : P := by", _runner_never15, max_moves=5,
                                    cache=_pc15, cache_verify=lambda g, p: True)
    ok("cache_reverify_accept_closes",
       r_acc["root_status"] == "closed" and r_acc["moves_made"] == 0)
    if _os2.path.exists(_db15):
        _os2.remove(_db15)

    # --- Test 15b (MUST-FIX regression, adversarial review): an EQUIV-cache hit with NO cache_verify
    # is treated as a MISS, never a closure (the α-collapse key can false-merge theorems, so it MUST
    # be re-verified in-context; without the verifier we do not trust it). ---
    _db15b = _tf2.mktemp(suffix=".jsonl"); _pc15b = _PC2(_db15b)
    _os2.environ["ZTARE_LEANMILL_EQUIV_CACHE"] = "1"
    try:
        _pc15b.put("theorem T : P := by", "by cached_alpha", "preloaded")
        r_guard = run_governed_dag_search({}, "theorem T : P := by", _runner_never15, max_moves=5,
                                          cache=_pc15b, cache_verify=None, defer_threshold=0.99)
        ok("equiv_cache_no_verify_treated_as_miss",
           r_guard["root_status"] != "closed"
           and any(e.get("event") == "equiv_cache_hit_needs_reverify" for e in r_guard["trace"]))
    finally:
        del _os2.environ["ZTARE_LEANMILL_EQUIV_CACHE"]
    _os2.path.exists(_db15b) and _os2.remove(_db15b)

    # --- Test 16 (REACHABILITY INVENT-CRITERION, default-off lever) ---
    import os as _os16
    # out-of-span node: tried a direct (commutative) move, hit unknown_identifier (missing primitive).
    oos = DagNode("oos", "root_goal", "g"); oos.moves_tried = [MOVE_NATIVE_HAMMER, MOVE_CLAUDE_WARM]
    oos.last_error_class = "unknown_identifier"
    # the ROUTER (default-ON 2026-06-12) promotes conjecture on exactly this signal — assert the new default,
    # then force it OFF to isolate the REACH_INVENT lever this block actually tests (hermetic, like sledge).
    ok("router_default_on_promotes_conjecture_on_missing_primitive",
       move_policy(oos, 100.0) == MOVE_CONJECTURE)
    _os16.environ["ZTARE_LEANMILL_MOVE_ROUTER"] = "0"
    ok("reach_invent_default_off_plain_order",
       move_policy(oos, 100.0) == MOVE_COLD_SHOT)        # router off ⇒ plain order (resource next), parity
    _os16.environ["ZTARE_LEANMILL_REACH_INVENT"] = "1"
    try:
        ok("reach_invent_on_fires_invent_out_of_span",
           move_policy(oos, 100.0) == MOVE_CONJECTURE)    # flag on + out-of-span → adjoin (invent) early
        # near-miss node (progress, no missing-primitive) must NOT early-invent even with the flag
        nm = DagNode("nm", "root_goal", "g"); nm.moves_tried = [MOVE_NATIVE_HAMMER]
        nm.last_error_class = "unsolved_goals"; nm.best_progress = 0.5
        ok("reach_invent_near_miss_no_early_invent", move_policy(nm, 100.0) != MOVE_CONJECTURE)
        # REGRESSION (adversarial review 2026-06-04): a NOISY failure (other_error) or no-telemetry
        # zero-progress must NOT early-invent — only unknown_identifier (a real missing-primitive) does.
        noisy = DagNode("noisy", "root_goal", "g"); noisy.moves_tried = [MOVE_NATIVE_HAMMER]
        noisy.last_error_class = "other_error"; noisy.best_progress = 0.0
        ok("reach_invent_other_error_no_early_invent", move_policy(noisy, 100.0) != MOVE_CONJECTURE)
        notel = DagNode("notel", "root_goal", "g"); notel.moves_tried = [MOVE_NATIVE_HAMMER]
        notel.last_error_class = ""; notel.best_progress = 0.0  # no telemetry observed
        ok("reach_invent_no_telemetry_no_early_invent", move_policy(notel, 100.0) != MOVE_CONJECTURE)
        # a fresh node (no commutative move tried yet) must NOT early-invent (still try the free probe)
        fresh16 = DagNode("f16", "root_goal", "g")
        ok("reach_invent_fresh_node_unaffected", move_policy(fresh16, 100.0) == MOVE_NATIVE_HAMMER)
    finally:
        del _os16.environ["ZTARE_LEANMILL_REACH_INVENT"]
        _os16.environ.pop("ZTARE_LEANMILL_MOVE_ROUTER", None)   # restore the default-ON router for later tests

    # --- Test 17: STRATEGIST MOVES (specialize/generalize) — stuck-gated, env-flagged, parity ---
    import os as _os17
    def _stuck(eclass=""):
        n = DagNode("stk", "root_goal", "g")
        n.moves_tried = list(MOVE_ORDER)   # standard menu exhausted = the STUCK precondition
        n.last_error_class = eclass
        return n
    # (a) PARITY: flags OFF ⇒ a stuck node DEFERs exactly as before (no strategist move offered).
    ok("strategist_default_off_defers",
       move_policy(_stuck("tactic_failed"), 100.0) == MOVE_DEFER)
    # (a2) CORROBORATE (Popper dual): flag on + stuck ⇒ offered; and offered BEFORE direct FALSIFY when both
    # are flagged (a consequence is often easier to refute than G itself). Default-off ⇒ not offered (parity).
    _os17.environ["ZTARE_LEANMILL_CORROBORATE"] = "1"
    try:
        ok("corroborate_on_fires_on_stuck", move_policy(_stuck("tactic_failed"), 100.0) == MOVE_CORROBORATE)
        _os17.environ["ZTARE_LEANMILL_FALSIFY"] = "1"
        try:
            ok("corroborate_offered_before_falsify",
               move_policy(_stuck("tactic_failed"), 100.0) == MOVE_CORROBORATE)
        finally:
            _os17.environ["ZTARE_LEANMILL_FALSIFY"] = "0"   # hermetic: default-ON now
    finally:
        _os17.environ["ZTARE_LEANMILL_CORROBORATE"] = "0"   # hermetic: default-ON now
    ok("corroborate_default_off_not_offered", move_policy(_stuck("tactic_failed"), 100.0) == MOVE_DEFER)
    # (a3) WITNESS TRANSPORT: gate-triggered (computable ∃) + flag-on + native ALREADY tried ⇒ offered before
    # the LLM moves; default-off ⇒ not offered; not eligible (∀ goal) ⇒ not offered even when flagged.
    _wt_node = DagNode("wt", "sub_goal", "theorem t : ∃ x : ℤ, x^2 + x = 42 := by sorry")
    _wt_node.moves_tried = [MOVE_NATIVE_HAMMER]   # native tried (the gate requires it)
    ok("witness_transport_default_off", move_policy(_wt_node, 100.0) != MOVE_WITNESS_TRANSPORT)
    _os17.environ["ZTARE_LEANMILL_WITNESS_TRANSPORT"] = "1"
    try:
        ok("witness_transport_on_fires_on_computable_existential_after_native",
           move_policy(_wt_node, 100.0) == MOVE_WITNESS_TRANSPORT)
        # not yet tried native ⇒ NOT offered (native gets first crack)
        _wt_fresh = DagNode("wtf", "sub_goal", "theorem t : ∃ x : ℤ, x^2 + x = 42 := by sorry")
        ok("witness_transport_not_before_native", move_policy(_wt_fresh, 100.0) != MOVE_WITNESS_TRANSPORT)
        # abstract goal (∀, no arithmetic) ⇒ gate rejects even when flagged
        _ab = DagNode("ab", "sub_goal", "theorem t : ∀ n : ℕ, n = n := by sorry"); _ab.moves_tried = [MOVE_NATIVE_HAMMER]
        ok("witness_transport_gate_rejects_abstract", move_policy(_ab, 100.0) != MOVE_WITNESS_TRANSPORT)
    finally:
        _os17.environ["ZTARE_LEANMILL_WITNESS_TRANSPORT"] = "0"   # hermetic: default-ON now
    # (b) GENERALIZE: flag on + INDUCTION-STALL signal ⇒ offered (only after the menu is exhausted).
    _os17.environ["ZTARE_LEANMILL_GENERALIZE"] = "1"
    try:
        ok("generalize_on_fires_on_stall",
           move_policy(_stuck("unsolved_goals"), 100.0) == MOVE_GENERALIZE)
        # (c) GENERALIZE gated: flag on but NO stall signal ⇒ NOT offered (avoids the Barrington blanket trap).
        ok("generalize_no_stall_no_fire",
           move_policy(_stuck("unknown_identifier"), 100.0) == MOVE_DEFER)
        # (d) GENERALIZE not offered before the menu is exhausted (direct-first preserved).
        _fresh = DagNode("gf", "root_goal", "g"); _fresh.last_error_class = "unsolved_goals"
        ok("generalize_not_before_menu_exhausted",
           move_policy(_fresh, 100.0) == MOVE_NATIVE_HAMMER)
    finally:
        _os17.environ["ZTARE_LEANMILL_GENERALIZE"] = "0"   # hermetic: default-ON now
    # (e) SPECIALIZE: flag on ⇒ offered as the last-resort rung on a stuck node (no signal required).
    _os17.environ["ZTARE_LEANMILL_SPECIALIZE"] = "1"
    try:
        ok("specialize_on_fires_last_resort",
           move_policy(_stuck("other_error"), 100.0) == MOVE_SPECIALIZE)
        # (f) GENERALIZE preferred over SPECIALIZE when both flagged + stall (closure > rung).
        _os17.environ["ZTARE_LEANMILL_GENERALIZE"] = "1"
        try:
            ok("generalize_preferred_over_specialize",
               move_policy(_stuck("unsolved_goals"), 100.0) == MOVE_GENERALIZE)
        finally:
            _os17.environ["ZTARE_LEANMILL_GENERALIZE"] = "0"   # hermetic: default-ON now
        # (g) RUNG PATH: a runner that returns rung=True on SPECIALIZE ⇒ root resolves to the typed `rung`
        # outcome (NOT closed, NOT exact_gap) and NEVER mints a closure.
        def runner_rung(node: DagNode, move: str, budget: float) -> MoveResult:
            if move == MOVE_SPECIALIZE:
                return MoveResult(move=move, kernel_clean=False, mnc_passed=False, rung=True,
                                  proof_text="theorem spec : Weaker := by rfl",
                                  residual="verified_special_case_rung")
            return MoveResult(move=move, kernel_clean=False, mnc_passed=False,
                              error_class="tactic_failed")
        res17 = run_governed_dag_search({}, "theorem t : G := by", runner_rung, max_moves=12,
                                        move_budget_units=100.0)
        ok("rung_root_resolution", res17["root_resolution"] == "rung")
        ok("rung_root_status_not_closed", res17["root_status"] == "rung"
           and res17["root_status"] != "closed")
        ok("rung_not_counted_as_closed_or_gap", res17["closed_or_exact_gap"] is False)
    finally:
        _os17.environ["ZTARE_LEANMILL_SPECIALIZE"] = "0"   # hermetic: default-ON now
    # (h) PARITY (whole-search): with NO flags, the same stuck-runner search DEFERs to exact_gap, byte-for-byte
    # the pre-strategist behaviour (the rung path is unreachable without the flag).
    def runner_rung_off(node: DagNode, move: str, budget: float) -> MoveResult:
        return MoveResult(move=move, kernel_clean=False, mnc_passed=False, error_class="tactic_failed")
    res17b = run_governed_dag_search({}, "theorem t : G := by", runner_rung_off, max_moves=12,
                                     move_budget_units=100.0)
    ok("strategist_off_search_no_rung", res17b["root_status"] != "rung")

    # ── (L) LUBY RESTARTS (#116) — pure sequence + restart wiring + default-off parity ──
    from ztare.common.timeouts import luby as _luby
    ok("luby_canonical_1..15",
       [_luby(i) for i in range(1, 16)] == [1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8])
    # property: luby(2^k - 1) == 2^(k-1) (the powers-of-two peaks), and every value is a power of two
    ok("luby_peak_property", all(_luby((1 << k) - 1) == (1 << (k - 1)) for k in range(1, 8)))
    ok("luby_restart_unit_scales", _luby_restart_unit(10.0, 1) == 10.0
       and _luby_restart_unit(10.0, 7) == 40.0 and _luby_restart_unit(10.0, 0) >= 10.0)

    # A runner that NEVER closes ⇒ the search makes no audited progress ⇒ stalls. With a SMALL move budget and
    # Luby ON, the search must REFILL (luby_restart events appear) and run MORE moves than the OFF baseline,
    # which exhausts the small budget and stops. Both are SOUND: the runner never closes, so neither arm mints
    # a closure (root stays exact_gap) — Luby only buys more exploration windows, never a false win.
    def _runner_stuck(node: DagNode, move: str, budget: float) -> MoveResult:
        return MoveResult(move=move, kernel_clean=False, mnc_passed=False, error_class="tactic_failed")
    # OFF baseline (byte-parity): no restarts, budget depletes once, search stops on stall/exhaustion.
    _os_h.environ.pop("ZTARE_LEANMILL_LUBY_RESTARTS", None)
    _os_h.environ["ZTARE_DAG_STALL_PATIENCE"] = "0"   # disable the adaptive break so the run is budget-bounded
    res_luby_off = run_governed_dag_search({}, "theorem t : G := by", _runner_stuck,
                                           max_moves=200, move_budget_units=4.0)
    ok("luby_off_no_restarts", res_luby_off["luby_restarts"] == 0
       and not any(e.get("event") == "luby_restart" for e in res_luby_off["trace"]))
    ok("luby_off_root_open_no_false_closure", res_luby_off["root_status"] != "closed")
    _moves_off = res_luby_off["moves_made"]
    # ON: same stuck runner + small budget, but restarts refill the window so MORE moves run before the
    # max_moves/restart-cap backstop ends it. The restart cap bounds it (can't loop forever).
    _os_h.environ["ZTARE_LEANMILL_LUBY_RESTARTS"] = "1"
    _os_h.environ["ZTARE_LEANMILL_LUBY_RESTART_PATIENCE"] = "2"
    _os_h.environ["ZTARE_LEANMILL_LUBY_MAX_RESTARTS"] = "3"
    res_luby_on = run_governed_dag_search({}, "theorem t : G := by", _runner_stuck,
                                          max_moves=200, move_budget_units=4.0)
    ok("luby_on_restarts_fire", res_luby_on["luby_restarts"] >= 1
       and any(e.get("event") == "luby_restart" for e in res_luby_on["trace"]))
    ok("luby_on_runs_more_moves_than_off", res_luby_on["moves_made"] > _moves_off)
    ok("luby_on_respects_restart_cap", res_luby_on["luby_restarts"] <= 3)
    ok("luby_on_no_false_closure", res_luby_on["root_status"] != "closed")
    _os_h.environ.pop("ZTARE_LEANMILL_LUBY_RESTARTS", None)
    _os_h.environ.pop("ZTARE_LEANMILL_LUBY_RESTART_PATIENCE", None)
    _os_h.environ.pop("ZTARE_LEANMILL_LUBY_MAX_RESTARTS", None)
    _os_h.environ.pop("ZTARE_DAG_STALL_PATIENCE", None)

    # ── (S) INTERNAL-STANDARD SPIKING (#116) — known-answer probe + dead-apparatus detection + parity ──
    ok("spike_probe_is_known_closeable_target",
       spike_probe().goal_text == SPIKE_GOAL_TEXT and spike_probe().goal_text != "")
    ok("spike_closed_true_on_calibration",
       spike_closed(MoveResult(move="m", calibration_available=True)) is True)
    ok("spike_closed_ignores_theorem_credit",
       spike_closed(MoveResult(move="m", kernel_clean=True, mnc_passed=True,
                               governance_ready=True)) is False)
    ok("spike_closed_false_on_dead",
       spike_closed(MoveResult(move="m", calibration_available=False))
       is False and spike_closed(None) is False)

    # A LIVE apparatus: the runner closes the spike (and any real move). Spikes register LIVE, apparatus_live
    # stays True, and (parity) the spike does NOT spend budget or count toward moves_made.
    def _runner_live(node: DagNode, move: str, budget: float) -> MoveResult:
        if node.kind == "calibration_control":
            return MoveResult(move=move, calibration_available=True)
        return MoveResult(move=move, kernel_clean=True, mnc_passed=True,
                          governance_ready=True, proof_text="by trivial")
    _os_h.environ["ZTARE_LEANMILL_SPIKE"] = "1"
    _os_h.environ["ZTARE_LEANMILL_SPIKE_EVERY"] = "1"
    res_spike_live = run_governed_dag_search(
        {"decomposition": [{"kind": "sub_goal", "goal_text": "a"}, {"kind": "sub_goal", "goal_text": "b"}]},
        "root", _runner_live, max_moves=10, move_budget_units=100.0)
    ok("spike_live_registers", res_spike_live["spikes"]["done"] >= 1
       and res_spike_live["spikes"]["live"] == res_spike_live["spikes"]["done"]
       and res_spike_live["spikes"]["dead"] == 0)
    ok("spike_live_apparatus_live_true", res_spike_live["apparatus_live"] is True)

    # A DEAD apparatus: the runner closes a REAL move BUT fails the known-answer standard (the dead-instrument
    # signature: a probe that no longer parses/compiles). The spike must CATCH it — dead>0, apparatus_live
    # False, and a `spike` event with live=False in the trace. This is the whole point: a silent 0/N becomes a
    # LOUD inadmissibility flag.
    def _runner_dead_on_spike(node: DagNode, move: str, budget: float) -> MoveResult:
        if node.kind == "calibration_control":
            return MoveResult(move=move, calibration_available=False,
                              error_class="parse_error")
        return MoveResult(move=move, kernel_clean=True, mnc_passed=True,
                          governance_ready=True, proof_text="by ok")
    res_spike_dead = run_governed_dag_search(
        {"decomposition": [{"kind": "sub_goal", "goal_text": "a"}, {"kind": "sub_goal", "goal_text": "b"}]},
        "root", _runner_dead_on_spike, max_moves=10, move_budget_units=100.0)
    ok("spike_dead_caught", res_spike_dead["spikes"]["dead"] >= 1
       and res_spike_dead["apparatus_live"] is False)
    ok("spike_dead_trace_event",
       any(e.get("event") == "spike" and e.get("live") is False for e in res_spike_dead["trace"]))
    _os_h.environ.pop("ZTARE_LEANMILL_SPIKE", None)
    _os_h.environ.pop("ZTARE_LEANMILL_SPIKE_EVERY", None)

    # PARITY: with SPIKE off, no spike is injected (done==0) and apparatus_live is vacuously True.
    res_spike_off = run_governed_dag_search({}, "theorem t : G := by", _runner_live,
                                            max_moves=5, move_budget_units=100.0)
    ok("spike_off_no_injection", res_spike_off["spikes"]["done"] == 0
       and not any(e.get("event") == "spike" for e in res_spike_off["trace"]))

    # (i) A=B CONTROL ARM (random over the SAME strategist set): the master-discriminator's Arm B.
    # With both flags + RANDOM mode on, a stuck node returns SOME enabled strategist move regardless of
    # the signal (here NO stall signal, so the SIGNAL arm would DEFER) — i.e. random ignores the mapping.
    _os17.environ["ZTARE_LEANMILL_SPECIALIZE"] = "1"
    _os17.environ["ZTARE_LEANMILL_GENERALIZE"] = "1"
    _os17.environ["ZTARE_LEANMILL_STRATEGIST_RANDOM"] = "1"
    _os17.environ["ZTARE_LEANMILL_STRATEGIST_SEED"] = "abtest"
    try:
        # no stall signal ('other_error') ⇒ SIGNAL arm would pick specialize (last-resort) but NOT
        # generalize; RANDOM arm may pick EITHER from {generalize, specialize}. Assert it returns one of
        # the two (never DEFER while a move is eligible) and is DETERMINISTIC given the seed.
        _r1 = move_policy(_stuck("other_error"), 100.0)
        _r2 = move_policy(_stuck("other_error"), 100.0)
        ok("abtest_random_picks_a_strategist_move", _r1 in (MOVE_SPECIALIZE, MOVE_GENERALIZE))
        ok("abtest_random_is_seed_deterministic", _r1 == _r2)
        # over many distinct node histories the random arm must select BOTH moves at least once (uniform).
        _seen = set()
        for _i in range(40):
            _n = DagNode(f"rb{_i}", "root_goal", "g"); _n.moves_tried = list(MOVE_ORDER); _n.last_error_class = "other_error"
            _seen.add(move_policy(_n, 100.0))
        ok("abtest_random_covers_both_moves", {MOVE_SPECIALIZE, MOVE_GENERALIZE} <= _seen)
    finally:
        # SPECIALIZE/GENERALIZE are default-ON now ⇒ restore the suite's hermetic "0", NOT unset (a pop would
        # fall back to default-on and break the flags-off parity re-confirm below).
        _os17.environ["ZTARE_LEANMILL_SPECIALIZE"] = "0"
        _os17.environ["ZTARE_LEANMILL_GENERALIZE"] = "0"
        for _k in ("ZTARE_LEANMILL_STRATEGIST_RANDOM", "ZTARE_LEANMILL_STRATEGIST_SEED"):
            _os17.environ.pop(_k, None)
    # (j) PARITY re-confirm: after the A=B env is cleared, a stuck node DEFERs again (no leakage).
    ok("strategist_env_cleared_defers_again", move_policy(_stuck("unsolved_goals"), 100.0) == MOVE_DEFER)

    # (k) AGENTIC LADDER (A): agent-first demotes cold_shot/frontier to the non-agent fallback. A node with
    # native+warm tried picks cold_shot under the FULL cascade, but conjecture under the agent-first ladder.
    _al = DagNode("al", "sub_goal", "g"); _al.moves_tried = [MOVE_NATIVE_HAMMER, MOVE_CLAUDE_WARM]
    _os_h.environ["ZTARE_LEANMILL_FULL_CASCADE"] = "1"
    ok("full_cascade: native+warm tried → cold_shot next (legacy ladder)",
       move_policy(_al, 100.0, defer_threshold=0.2) == MOVE_COLD_SHOT)
    _os_h.environ.pop("ZTARE_LEANMILL_FULL_CASCADE", None)   # agent-first (AGENT_TOOLS default-on)
    ok("agentic ladder: cold_shot/frontier demoted → conjecture next (agent-first)",
       move_policy(_al, 100.0, defer_threshold=0.2) == MOVE_CONJECTURE)
    _os_h.environ["ZTARE_LEANMILL_AGENT_TOOLS"] = "0"   # no agent ⇒ the full cascade returns (fallbacks available)
    ok("no-agent: cold_shot fallback returns when AGENT_TOOLS off",
       move_policy(_al, 100.0, defer_threshold=0.2) == MOVE_COLD_SHOT)
    _os_h.environ.pop("ZTARE_LEANMILL_AGENT_TOOLS", None)

    if _sledge_save is None:
        _os_h.environ.pop("ZTARE_LEANMILL_SLEDGEHAMMER", None)
    else:
        _os_h.environ["ZTARE_LEANMILL_SLEDGEHAMMER"] = _sledge_save
    if _cascade_save is None:
        _os_h.environ.pop("ZTARE_LEANMILL_FULL_CASCADE", None)
    else:
        _os_h.environ["ZTARE_LEANMILL_FULL_CASCADE"] = _cascade_save
    for _k, _v in _exec_save.items():
        if _v is None:
            _os_h.environ.pop(_k, None)
        else:
            _os_h.environ[_k] = _v
    print()
    if failures:
        print(f"SELFTEST FAILED: {len(failures)} failing — {failures}")
        return 1
    print("SELFTEST PASSED: all invariant tests green")
    return 0


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="GP-246 governed DAG proof-search")
    ap.add_argument("--selftest", action="store_true",
                    help="run the offline self-test (mock move_runner; no Lean/LLM)")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
