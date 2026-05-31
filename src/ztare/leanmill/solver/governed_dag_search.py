"""GP-246 — Governed DAG proof-search over a proof-obligation DAG.

This is the v2 EVOLUTION of the fixed Layer-2→5 cascade in the solver lane
(`scripts/public/control/leanmill/solver_lane_worker.py`). The cascade stays as
the measured BASELINE; this module is the optimization OVER it and earns
adoption only by closing ≥ the cascade's closures on the SAME rows (see the
GP-246 seam). It is NOT a smarter prover — the LLM/hammer/frontier prover stays
a subordinate move-generator and the moat is the mechanization-placement
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
NODE_STATUSES = ("open", "closed", "exact_gap", "falsifier", "retired", "deferred")

# Ordered move menu (cheap → expensive). The policy walks this order.
MOVE_NATIVE_HAMMER = "native_hammer"        # FREE, deterministic tactic cascade
MOVE_CLAUDE_WARM = "claude_warm"            # iterative warm agent
MOVE_COLD_SHOT = "cold_shot_fanout"        # one-shot multi-provider fan-out
MOVE_FRONTIER = "external_frontier_prover"  # provider-agnostic frontier slot
MOVE_DEFER = "defer"                        # explicit stop → exact_gap

MOVE_ORDER = (MOVE_NATIVE_HAMMER, MOVE_CLAUDE_WARM, MOVE_COLD_SHOT, MOVE_FRONTIER)

# Heuristic cost model (v1, STUB — see honest-notes in the seam/report). Units
# are abstract "budget units" (cold wall-clock seconds / fan-out width proxy),
# NOT calibrated. native_hammer is free; the rest escalate.
MOVE_COST: dict[str, float] = {
    MOVE_NATIVE_HAMMER: 0.0,
    MOVE_CLAUDE_WARM: 3.0,
    MOVE_COLD_SHOT: 4.0,
    MOVE_FRONTIER: 6.0,
}

# Heuristic prior P(this move closes THIS node), independent of node features
# (v1 STUB; a calibrated model is future work — needs the VPS benchmark to fit).
MOVE_PRIOR_P_CLOSE: dict[str, float] = {
    MOVE_NATIVE_HAMMER: 0.25,
    MOVE_CLAUDE_WARM: 0.35,
    MOVE_COLD_SHOT: 0.30,
    MOVE_FRONTIER: 0.40,
}

# Below this marginal est_p_close the policy chooses DEFER (emit exact_gap)
# rather than spend more budget on a node.
DEFAULT_DEFER_THRESHOLD = 0.12


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

    def is_finished(self) -> bool:
        return self.status in ("closed", "exact_gap", "falsifier", "retired")


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
    proof_text: str = ""
    residual: Optional[str] = None  # if the move exposed a NEW sub-obligation
    new_sub_goal_text: Optional[str] = None  # text for the new sub_goal node, if any
    falsifier: bool = False         # the move found a falsifying candidate
    tail: str = ""                  # transcript tail (for audit)
    wallclock_s: float = 0.0

    @property
    def ratified_close(self) -> bool:
        """no-false-closure: a close is ratified ONLY if kernel-clean AND MNC."""
        return bool(self.kernel_clean and self.mnc_passed)


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

    decomposition = _contract_decomposition(contract)
    if not decomposition:
        decomposition = derive_structural_decomposition(goal_text)
    if not decomposition and premise_shelf:
        # atomic goal + retrieval available → premise-anchored candidate closing moves.
        decomposition = derive_premise_helpers(goal_text, premise_shelf)
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
        )
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
    Strips the proof; the goal type is whatever follows the last top-level ':'."""
    s = goal_text
    for marker in (":= by", ":=by", ":="):
        idx = s.find(marker)
        if idx != -1:
            s = s[:idx]; break
    s = s.strip()
    depth, last_colon = 0, -1
    for i, c in enumerate(s):
        if c in _OPENERS:
            depth += 1
        elif c in _CLOSERS:
            depth = max(0, depth - 1)
        elif c == ":" and depth == 0:
            if (i + 1 < len(s) and s[i + 1] == ":") or (i > 0 and s[i - 1] == ":"):
                continue  # skip '::'
            last_colon = i
    if last_colon == -1:
        return None, None
    prefix, gtype = s[:last_colon + 1], s[last_colon + 1:].strip()
    return (prefix, gtype) if gtype else (None, None)


def derive_structural_decomposition(goal_text: str) -> list[dict]:
    """Top-level ∧/↔ → independent sub-goals, preserving the binder context. Pure
    connective splitting (auditable), no model improvisation. [] when atomic/uncertain."""
    if not goal_text or not isinstance(goal_text, str):
        return []
    prefix, gtype = _goal_prefix_and_type(goal_text)
    if not gtype:
        return []
    iff_parts = _split_top_level(gtype, {"↔"})
    if len(iff_parts) == 2:
        a, b = iff_parts
        return [
            {"kind": "sub_goal", "goal_text": f"{prefix} ({a}) → ({b})"},
            {"kind": "sub_goal", "goal_text": f"{prefix} ({b}) → ({a})"},
        ]
    conj = _split_top_level(gtype, {"∧"})
    if len(conj) >= 2:
        return [{"kind": "sub_goal", "goal_text": f"{prefix} {c}"} for c in conj]
    return []


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
    """
    for move in MOVE_ORDER:
        if move in node.moves_tried:
            continue
        cost = MOVE_COST.get(move, 1.0)
        if cost > budget_remaining:
            continue
        # Premise-anchored nodes carry an EXOGENOUS est_p prior (retrieval score);
        # it overrides the heuristic per-move stub. Otherwise use the move prior.
        est_p = node.est_p_seed if node.est_p_seed is not None else MOVE_PRIOR_P_CLOSE.get(move, 0.0)
        if est_p >= defer_threshold:
            return move
    return MOVE_DEFER


def _frontier_score(node: DagNode, budget_remaining: float) -> float:
    """Best-first key for an OPEN node: (est_p_close × value) − cost of the move
    the policy would pick. Higher = expand first. A node with no affordable move
    (policy returns DEFER) scores very low so it's drained last."""
    move = move_policy(node, budget_remaining)
    if move == MOVE_DEFER:
        return -1e9
    est_p = MOVE_PRIOR_P_CLOSE.get(move, 0.0)
    cost = MOVE_COST.get(move, 1.0)
    return (est_p * _node_value(node)) - cost


# ─────────────────────────────────────────────────────────────────────────────
# 4. residual_to_lever — no silent deaths
# ─────────────────────────────────────────────────────────────────────────────

def residual_to_lever(node: DagNode) -> str:
    """Resolve a FINISHED node to exactly one of {closure | exact_gap |
    falsifier | retired_impossible | new_sub_target} and set node.next_lever.
    Every finished node MUST resolve; this is what guarantees no attempt dies
    silently. Returns the resolution token."""
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
    if node.status == "retired":
        node.next_lever = (
            f"retired_impossible: node {node.node_id} retired "
            f"({node.residual or 'no affordable move / out of budget'})"
        )
        return "retired_impossible"
    if node.status == "exact_gap":
        node.next_lever = (
            f"exact_gap: node {node.node_id} deferred at marginal P(close) below "
            "threshold; emit as the exact remaining obligation for a future lever "
            "(stronger prover slot / human / decomposition)"
        )
        return "exact_gap"
    # An open node that produced a residual → a NEW sub-target was the lever.
    node.next_lever = (
        f"new_sub_target: node {node.node_id} exposed residual "
        f"'{node.residual}' → added as a typed sub_goal node"
    )
    return "new_sub_target"


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
            parent.status = "closed"
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
) -> dict:
    """Governed best-first search over the ex-ante obligation DAG.

    The search PROPOSES candidate moves; the injected `move_runner` RATIFIES
    each result through the existing governance (kernel + MNC). A node closes
    ONLY on a ratified close (MoveResult.ratified_close). Budget-bounded by
    max_moves AND wallclock AND abstract move-budget-units.

    Returns a structured result: the final DAG (as node dicts), the move trace,
    the root verdict, per-node levers, and per-move attribution.
    """
    nodes = build_obligation_dag(contract, goal_text, premise_shelf)
    root_id = "n0_root"
    trace: list[dict] = []
    move_attribution: list[dict] = []
    start = time.time()
    budget_units = float(move_budget_units)
    moves_made = 0

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

        # Frontier = open nodes; pick the best by (est_p×value − cost).
        open_nodes = [n for n in nodes.values() if n.status == "open"]
        if not open_nodes:
            trace.append({"event": "stop", "reason": "no_open_nodes"})
            break
        scored = sorted(
            open_nodes,
            key=lambda n: _frontier_score(n, budget_units),
            reverse=True,
        )
        node = scored[0]

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
        move_attribution.append({
            "node_id": node.node_id,
            "node_kind": node.kind,
            "move": move,
            "kernel_clean": result.kernel_clean,
            "mnc_passed": result.mnc_passed,
            "ratified_close": result.ratified_close,
            "falsifier": result.falsifier,
            "residual": result.residual,
            "wallclock_s": result.wallclock_s,
        })

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

        if result.ratified_close:
            # no-false-closure already enforced by ratified_close (kernel+MNC).
            node.status = "closed"
            node.proof_text = result.proof_text
            residual_to_lever(node)
            trace.append({"event": "closed", "node_id": node.node_id, "move": move,
                          "lever": node.next_lever})
            _propagate_closure(nodes, node, trace)
            continue

        # NOT ratified. If the move exposed a residual, turn it into a NEW typed
        # sub_goal node (child of this node) and keep this node open for more
        # moves. This is the "residual → new typed sub_goal" path.
        if result.residual:
            new_idx = sum(1 for n in nodes.values() if n.kind == "sub_goal") + 1
            new_id = f"n{len(nodes)}_sub_goal_{new_idx}"
            nodes[new_id] = DagNode(
                node_id=new_id,
                kind="sub_goal",
                goal_text=result.new_sub_goal_text or result.residual,
                parent_id=node.node_id,
            )
            # Record that this open node spawned a sub-target (lever), without
            # finishing it — it still has remaining moves.
            node.residual = result.residual
            trace.append({
                "event": "new_sub_target",
                "node_id": node.node_id,
                "move": move,
                "new_node_id": new_id,
                "lever": f"new_sub_target: residual '{result.residual}' → {new_id}",
            })
            # A sorry/non-clean attempt that yields a residual MUST NOT close the
            # node; it stays open and is later resolved (closure or exact_gap).
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
    root_resolution = residual_to_lever(root)

    return {
        "schema": "leanmill-governed-dag-search-v1",
        "root_status": root.status,
        "root_resolution": root_resolution,        # closure|exact_gap|falsifier|retired_impossible|new_sub_target
        "root_proof_text": root.proof_text,
        "closed_or_exact_gap": root.status in ("closed", "exact_gap"),
        "moves_made": moves_made,
        "wallclock_s": round(time.time() - start, 3),
        "budget_units_remaining": round(budget_units, 3),
        "nodes": {nid: asdict(n) for nid, n in nodes.items()},
        "levers": {nid: n.next_lever for nid, n in nodes.items()},
        "trace": trace,
        "move_attribution": move_attribution,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Offline self-test (MOCK move_runner; no Lean, no LLM)
# ─────────────────────────────────────────────────────────────────────────────

def _selftest() -> int:
    failures: list[str] = []

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

    # --- Test 4: parent propagation on child closure ---
    # The root has NO direct proof (every direct attempt on it fails); only its
    # children close. The root must close by PROPAGATION once all children close.
    def runner_children_only(node: DagNode, move: str, budget: float) -> MoveResult:
        if node.kind == "root_goal":
            return MoveResult(move=move, kernel_clean=False, mnc_passed=False)
        return MoveResult(move=move, kernel_clean=True, mnc_passed=True,
                          proof_text=f"by exact proof_for_{node.node_id}")
    res4 = run_governed_dag_search(contract_decomp, "root goal", runner_children_only,
                                   max_moves=20)
    ok("parent_propagation_root_closed", res4["root_status"] == "closed")
    res4_children = [n for nid, n in res4["nodes"].items() if nid != "n0_root"]
    ok("parent_propagation_all_children_closed",
       all(n["status"] == "closed" for n in res4_children))

    # --- Test 5: residual → new sub-goal node ---
    spawned = {"count": 0}

    def runner_residual_then_close(node: DagNode, move: str, budget: float) -> MoveResult:
        # First move on root: fail-with-residual (spawns sub_goal). Then close all.
        if node.kind == "root_goal" and spawned["count"] == 0:
            spawned["count"] += 1
            return MoveResult(move=move, kernel_clean=False, mnc_passed=False,
                              residual="missing_lemma_X",
                              new_sub_goal_text="lemma X : ...")
        return MoveResult(move=move, kernel_clean=True, mnc_passed=True,
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
