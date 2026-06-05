"""Obligation-typed move router — vocabulary-driven, substrate-neutral move selection.

The leanmill solver's native moves are EXECUTION CHANNELS (which prover to call). They do
not consult the repo's mined research-operations vocabulary, so the in-loop solver sprays a
fixed tactic battery instead of selecting a research OPERATION. This module closes that gap
(and the §6n in-loop⇔out-of-loop parity gap): it TYPES each open goal into the universal
obligation class, picks the research op, and maps that to an ORDERED set of Lean tactic
schemas — then, when the standard frame stalls, escalates to the MM meta-meta reframes.

Three reused registries (no reinvention — this is the wiring, not a new vocabulary):
  - universal obligation classes (Construct / Transfer / Bound / Decompose) + v5 ops
    (`research_director.universal_research_ops`).
  - PDE estimate-craft ops pec_a..pec_l (`research_director.pde_estimate_craft_ops`).
  - MM meta-meta ops mm_01 ACR / mm_02 SSP / mm_03 Ontological Promotion
    (`research_director.universal_research_ops.META_META_VOCABULARY`).
  - gap_typing.heuristic_gap_type for PDE-lexical premise-rank enrichment.

Substrate-neutral: classification is driven by Lean GOAL SHAPE (the connective structure),
not by any corpus's vocabulary. The result is explainable in vocabulary terms (every emitted
candidate carries its obligation + op_id), which is exactly the `structural_language_fingerprint`
the catalog asks closure artifacts to record.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

OBLIGATION_CLASSES = ("Construct", "Transfer", "Bound", "Decompose")

# bracket-balanced scan helpers (Lean goals use (), [], {}, ⟨⟩)
_OPEN = {"(": ")", "[": "]", "{": "}", "⟨": "⟩"}
_CLOSE = set(_OPEN.values())


def _strip_turnstile(goal: str) -> str:
    g = goal
    if "⊢" in g:
        g = g.split("⊢")[-1]
    return g.strip()


def _top_level_find(s: str, tokens: tuple[str, ...]) -> Optional[str]:
    """Return the first of `tokens` that occurs at bracket-depth 0, else None."""
    depth = 0
    i = 0
    while i < len(s):
        c = s[i]
        if c in _OPEN:
            depth += 1
        elif c in _CLOSE:
            depth = max(0, depth - 1)
        elif depth == 0:
            for t in tokens:
                if s.startswith(t, i):
                    return t
        i += 1
    return None


@dataclass
class Obligation:
    obligation: str          # one of OBLIGATION_CLASSES
    op_id: str               # canonical op id (core_*/broad_*/pec_*)
    op_name: str
    gap_type: str            # gap_typing PDE-lexical label (or UNKNOWN)
    rationale: str
    head: str = ""           # the detected head connective


def _op_name(op_id: str) -> str:
    """Resolve a canonical op name from the registries; fall back to a literal."""
    try:
        from ztare.research_director import universal_research_ops as uro
        op = uro.get(op_id) or uro.get_meta_meta(op_id)
        if op is not None:
            return op.name
    except Exception:
        pass
    try:
        from ztare.research_director.pde_estimate_craft_ops import PDE_ESTIMATE_CRAFT_OPS
        if op_id in PDE_ESTIMATE_CRAFT_OPS:
            return PDE_ESTIMATE_CRAFT_OPS[op_id].get("name", op_id)
    except Exception:
        pass
    return op_id


def classify(goal_text: str) -> Obligation:
    """Type an open Lean goal into its universal obligation class by SHAPE.

    The obligation is read off the head connective of the goal (after the turnstile):
      ∃ / ∃!         → Construct  (build a witness; pec_e Sharpness/Failure-Witness)
      ∧              → Decompose  (core_03 Decomposition & Recomposition)
      ↔              → Decompose  (two implications) — Transfer-flavored
      ≤ < ≥ > ∣      → Bound      (pec_c Quantitative Threshold Dichotomy)
      ∀ / →          → the goal owes an intro then the consequent's obligation
      = with a count/numeral side → Construct (exhibit/compute the value)
      = otherwise / ∈ / lemma-shaped → Transfer (apply/rewrite a known result; pec_a)
    """
    g = _strip_turnstile(goal_text)
    gap = "UNKNOWN"
    try:
        from ztare.research_director.gap_typing import heuristic_gap_type
        gap = heuristic_gap_type("", g, g).get("gap_type", "UNKNOWN")
    except Exception:
        pass

    def mk(ob, op_id, head, why):
        return Obligation(ob, op_id, _op_name(op_id), gap, why, head)

    if g.startswith("∃"):
        return mk("Construct", "pec_e", "∃",
                  "existential head — owes a witness construction")
    if g.startswith("∀") or _top_level_find(g, ("→",)) == "→":
        return mk("Decompose", "core_03", "∀/→",
                  "universally-quantified / implication head — intro the binders, "
                  "then the consequent's obligation governs")
    if _top_level_find(g, ("↔",)) == "↔":
        return mk("Decompose", "core_03", "↔",
                  "iff — split into two implications")
    if _top_level_find(g, ("∧",)) == "∧":
        return mk("Decompose", "core_03", "∧",
                  "conjunction — split into independently-owned parts")
    rel = _top_level_find(g, ("≤", "<", "≥", ">", "∣"))
    if rel:
        return mk("Bound", "pec_c", rel,
                  "relational/inequality head — owes a quantitative bound")
    if _top_level_find(g, ("=",)) == "=":
        if re.search(r"\.card\b|Finset|numeral|[0-9]\s*$", g) or re.search(r"=\s*[0-9]+\s*$", g):
            return mk("Construct", "core_04", "=count",
                      "equality of a cardinality/computed value — exhibit/compute it "
                      "(local-to-global assembly of the counted set)")
        return mk("Transfer", "pec_a", "=",
                  "equality head — rewrite/transfer via a known identity or comparison object")
    if _top_level_find(g, ("∈",)):
        return mk("Transfer", "pec_a", "∈",
                  "membership — apply a characterization lemma")
    return mk("Transfer", "pec_a", "?",
              "no decisive head connective — try library transfer / search")


# ---- move templates: obligation/op → ordered Lean tactic schemas -------------
def _hint_list(hints):
    return "[" + ", ".join(sorted(hints)[:10]) + "]" if hints else ""


# GENERIC closers — IDENTICAL to the plain decomposition battery. Including these in EVERY
# router plan guarantees router ⊇ battery, so the A/B can never make the router LOSE for a
# move the battery had; any ROUTER-ONLY closure is then purely the obligation/reframe lift.
def _generic_closers(hints) -> list[str]:
    H = _hint_list(hints)
    base = ["decide", "native_decide", "rfl", "trivial", "omega", "norm_num",
            "positivity", "simp_all", "aesop", "tauto"]
    base += [f"intros; {c}" for c in
             ["decide", "norm_num", "omega", "simp_all", "aesop", "positivity", "tauto"]]
    if H:
        unf = " ".join(sorted(hints)[:10])
        base += [f"intros; simp_all {H}", f"simp_all {H}",
                 f"intros; aesop (add simp {H})", f"intros; norm_num {H}",
                 f"unfold {unf}; intros; simp_all", f"intros; simp only {H} <;> norm_num",
                 f"intros; simp_all {H} <;> omega", f"intros; simp_all {H} <;> nlinarith"]
    return base


def move_templates(ob: Obligation, hints: Optional[set] = None) -> list[str]:
    """Obligation-specific moves LAYERED ON TOP of the generic closers (superset design).
    The ordering encodes the obligation (Decompose splits first, Construct offers witnesses,
    Bound leads with inequality tactics), but the full closer pool is always present."""
    hints = hints or set()
    H = _hint_list(hints)
    extra: list[str] = []
    if ob.obligation == "Decompose":
        extra = ["refine ⟨?_, ?_⟩ <;> simp_all" + (f" {H}" if H else ""),
                 "constructor <;> simp_all" + (f" {H}" if H else ""),
                 "refine ⟨?_, ?_, ?_⟩ <;> simp_all" + (f" {H}" if H else ""),
                 "constructor <;> aesop", "rintro ⟨_, _⟩ <;> simp_all" + (f" {H}" if H else "")]
    elif ob.obligation == "Construct":
        extra = ["exact ⟨0, by simp⟩", "refine ⟨0, ?_⟩ <;> simp_all" + (f" {H}" if H else ""),
                 "refine ⟨0, ?_, ?_⟩ <;> simp_all" + (f" {H}" if H else "")]
        extra += [f"exact {h}" for h in sorted(hints)[:4]]   # witness from retrieval (pec_e)
    elif ob.obligation == "Bound":
        extra = ["gcongr", "nlinarith", "linarith", "apply le_trans"]
        if H:
            extra += [f"nlinarith {H}", f"simp_all {H} <;> nlinarith", f"gcongr <;> simp_all {H}"]
    else:  # Transfer
        extra = ["exact?", "apply?"]
        extra += [f"exact {h}" for h in sorted(hints)[:4]]
        extra += [f"apply {h}" for h in sorted(hints)[:4]]
        if H:
            extra += [f"simp only {H} <;> aesop", f"rw [{', '.join(sorted(hints)[:3])}] <;> simp_all {H}"]
    # generic closers ALWAYS included → router ⊇ battery
    return extra + _generic_closers(hints)


# ---- MM meta-meta reframes: the escape tier when the frame stalls ------------
def meta_reframe(ob: Obligation, hints: Optional[set] = None) -> list[tuple[str, str]]:
    """The game-layer reframes (mm_01 ACR / mm_02 SSP / mm_03 Ontological Promotion) as
    COMPLETE whole-proof bodies (reframe AND discharge — a bare reframe that leaves the
    goal open is not a candidate). These CHANGE what counts as the object/criterion: the
    native-agentic 'reframe the problem' move a fixed battery cannot make.

    Caveat the A/B must record: a one-shot whole-proof body cannot express the genuinely
    INTERACTIVE multi-step reframe (reframe, inspect the new goal, then discharge). These
    are the best one-shot approximations; a true strange-loop reframe needs a stateful or
    LLM multi-step solver. So a null result here under-tests the reframe hypothesis."""
    hints = hints or set()
    H = _hint_list(hints)
    unf = " ".join(sorted(hints)[:10]) if hints else ""
    out: list[tuple[str, str]] = []
    if unf:
        # mm_01 ACR — rebaseline to the definitional content, then discharge
        out += [("mm_01", f"unfold {unf}; decide"),
                ("mm_01", f"unfold {unf}; rfl"),
                ("mm_01", f"unfold {unf}; norm_num {H}"),
                ("mm_01", f"unfold {unf}; simp_all {H}"),
                ("mm_01", f"unfold {unf}; intros; simp_all {H} <;> decide")]
        # mm_02 SSP — quotient out representation: membership-extensionality / card-bijection
        out += [("mm_02", f"unfold {unf}; rw [Finset.card_eq_one]; refine ⟨?_, ?_⟩ <;> (ext m; simp_all {H})"),
                ("mm_02", f"unfold {unf}; ext m; simp_all {H}"),
                ("mm_02", f"classical; unfold {unf}; simp_all {H} <;> decide"),
                ("mm_02", f"unfold {unf}; apply Finset.card_eq_one.mpr; refine ⟨?_, ?_⟩ <;> (ext m; simp_all {H})")]
        # mm_03 Ontological Promotion — promote the underlying set to a first-class object
        out += [("mm_03", f"unfold {unf}; ext m; constructor <;> intro h <;> simp_all {H}"),
                ("mm_03", f"unfold {unf}; congr 1; ext m; simp_all {H}")]
    else:
        out += [("mm_02", "ext m <;> simp_all"), ("mm_01", "classical; decide")]
    return out


def candidate_plan(goal_text: str, hints: Optional[set] = None,
                   include_reframe: bool = True) -> tuple[Obligation, list[str]]:
    """Full ordered candidate plan: obligation-typed moves (superset of the battery) then
    the MM-3 reframe tier (complete bodies). Returns (Obligation, ordered tactic strings);
    the caller wraps each as `:= by <body>` and kernel-gates. The plan is a SUPERSET of the
    plain battery, so any router-only closure isolates the obligation/reframe contribution."""
    ob = classify(goal_text)
    plan = list(move_templates(ob, hints))
    if include_reframe:
        plan += [t for _, t in meta_reframe(ob, hints)]
    seen, out = set(), []
    for t in plan:
        if t and t not in seen and "sorry" not in t:   # never search a body that can't close
            seen.add(t); out.append(t)
    return ob, out


__all__ = ["Obligation", "OBLIGATION_CLASSES", "classify", "move_templates",
           "meta_reframe", "candidate_plan"]
