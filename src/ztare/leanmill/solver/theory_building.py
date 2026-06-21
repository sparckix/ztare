"""The GENERATIVE theory-building leg (2026-06-20).

The research apparatus already MINED a theory-building / problem-solving move catalogue (the Universal
Research Operations v5 + PDE estimate-craft ops + the two-cultures classifier) — but per its own header it
was wired DESCRIPTIVELY (fingerprint/route/label a closed arc), not GENERATIVELY. So when a Lean rung can't
close because it needs a PREREQUISITE LEMMA that doesn't exist yet (e.g. `derivative_local_simple_residue_…`
needs "the residue of a rational derivative vanishes" + "the principal part is unique" — neither in Mathlib),
the solver could NAME the gap (theory-building culture, owes a Decomposition, gap=missing-lemma) but had no
loop that turned that classification into a banked prerequisite. The conjecture prompt was also blind: "invent
ONE intermediate lemma, self-contained against import Mathlib" — a tactical decomposition, not theory-building.

This module closes the descriptive→generative loop by REUSE (no new move, no new catalogue):
  • `classify_gap` — runs the EXISTING `obligation_router.classify` + `two_cultures.classify_arc` and pulls
    the matching op's `structural_mechanism` + example from the EXISTING op registries.
  • `build_prompt` — turns that classification into a CATALOGUE-GUIDED theory-building prompt (the fix for
    the "stupid" generic conjecture prompt): frame as theory-building, embed the op mechanism, ask for the
    most GENERAL reusable prerequisite a mathematician would name+bank, and expose the campaign theory's own
    definitions. It keeps the `LEMMA:/PROOF:` fenced contract so the SAME `conjecture_advances` kernel gate +
    child-spawn + `family_lemma_library.bank` + `RefineHandover` retry path apply UNCHANGED (soundness intact).
  • `obligation_hint` — a per-GOAL catalogue read (the obligation the goal owes + canonical op + culture),
    surfaced to the agentic leaf THROUGH `move_cards.render_tool_block(goal=…)` (the single menu seam).

The agent-facing STRATEGY card ("build_prerequisite") that advertises this loop lives in `move_cards`
(`_STRATEGY_SPECS` / `build_strategy_cards`), built through the `contracts/action_card.py` pattern-action
contract and rendered in the SAME menu the agent chooses from — NOT a separate free-text blurb (the
2026-06-20 de-frankenstein). This module no longer defines its own `leaf_card`.

Soundness: zero new closure surface. The generated lemma is `sorry`-stubbed; it only becomes a child node if
`conjecture_advances` (kernel-checked, load-bearing, non-circular) passes, and it only closes via the same
kernel+MNC gates as any rung. A bad prerequisite is a wasted dispatch, never a false closure.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class TheoryGap:
    obligation: str = ""        # Construct / Transfer / Bound / Decompose
    op_id: str = ""             # core_03 / pec_a / …
    op_name: str = ""
    mechanism: str = ""         # the op's structural_mechanism — the GENERATIVE template content
    example: str = ""           # one instantiation example
    culture: str = ""           # theory_building / problem_solving / mixed
    head: str = ""              # the goal's head connective
    is_theory_building: bool = False


def _op_mechanism(op_id: str) -> "tuple[str, str]":
    """(mechanism, example) for an op_id from the EXISTING registries (universal v5 first, then PDE craft).
    Fail-soft to ('','') — the prompt degrades to obligation-only guidance, never crashes the move."""
    try:
        from ztare.research_director import universal_research_ops as _uro
        op = _uro.get(op_id) if hasattr(_uro, "get") else None
        if op is None:
            voc = getattr(_uro, "VOCABULARY_V5", {}) or {}
            op = voc.get(op_id)
        if op is not None:
            mech = getattr(op, "structural_mechanism", "") or ""
            ex = ""
            exs = getattr(op, "instantiation_examples", ()) or ()
            if exs:
                ex = exs[0]
            if mech:
                return mech, ex
    except Exception:  # noqa: BLE001
        pass
    try:
        from ztare.research_director.pde_estimate_craft_ops import get as _pde_get
        op = _pde_get(op_id)
        if op is not None:
            mech = getattr(op, "structural_mechanism", "") or ""
            exs = getattr(op, "instantiation_examples", ()) or ()
            return mech, (exs[0] if exs else "")
    except Exception:  # noqa: BLE001
        pass
    return "", ""


def classify_gap(goal_text: str) -> TheoryGap:
    """Classify a stuck goal via the EXISTING catalogue: obligation (shape) + culture (vocabulary) + the
    matching op's structural mechanism. `is_theory_building` is the gate the move uses to decide whether to
    use the theory-building prompt (true when the vocabulary leans theory-building, or the goal owes a
    Decompose/Transfer — the obligations that a missing prerequisite-lemma satisfies)."""
    g = goal_text or ""
    obligation = op_id = op_name = head = culture = ""
    try:
        from ztare.leanmill.solver.obligation_router import classify as _classify
        ob = _classify(g)
        obligation, op_id, op_name, head = ob.obligation, ob.op_id, ob.op_name, ob.head
    except Exception:  # noqa: BLE001
        pass
    try:
        from ztare.research_director.two_cultures import classify_arc as _arc
        culture = (_arc(g).dominant if g.strip() else "") or ""
    except Exception:  # noqa: BLE001
        pass
    mech, ex = _op_mechanism(op_id) if op_id else ("", "")
    # A missing-prerequisite-lemma is the natural remedy for Transfer (apply a not-yet-existing result) and
    # Decompose (split off a reusable lemma); culture=theory_building reinforces it. Construct/Bound owe a
    # witness/threshold, not (usually) a new lemma — so they don't trigger the theory-building prompt by shape
    # alone, only when the vocabulary says theory-building.
    is_tb = (culture == "theory_building") or (obligation in ("Transfer", "Decompose"))
    return TheoryGap(obligation=obligation, op_id=op_id, op_name=op_name, mechanism=mech,
                     example=ex, culture=culture, head=head, is_theory_building=bool(is_tb))


_DEFS_CACHE: "dict" = {}


def campaign_theory_defs(max_chars: int = 2500) -> str:
    """The DEFINITION signatures (def/abbrev names + their types, via canonical `lean_source`) of the ACTIVE
    campaign theory — so the theory-building prompt states prerequisites in the substrate's OWN vocabulary
    (`HasRatDeriv`, `simpleResidueCoeff`, …) instead of re-deriving from `import Mathlib`. '' when no campaign
    substrate. Cached by (path, mtime). NO regex on decls — reuses `lean_source.def_names`/`extract_signature`."""
    try:
        from pathlib import Path as _P
        from ztare.formal.repl_compile import get_campaign_substrate
        from ztare.leanmill import lean_source as _ls
        cs = get_campaign_substrate()
        if not cs:
            return ""
        p = _P(cs)
        mt = p.stat().st_mtime
        hit = _DEFS_CACHE.get(cs)
        if hit and hit[0] == mt:
            return hit[1]
        src = p.read_text(encoding="utf-8", errors="replace")
        lines = []
        for n in _ls.def_names(src):
            sig = _ls.extract_signature(src, n)
            if sig.strip():
                lines.append(f"def {n.split('.')[-1]} {sig.strip()}")
        out = "\n".join(lines)[:max_chars]
        _DEFS_CACHE[cs] = (mt, out)
        return out
    except Exception:  # noqa: BLE001
        return ""


def is_enabled() -> bool:
    """Default-ON (sound knob ⇒ default-on; the conjecture_advances kernel gate still guards every closure).
    `ZTARE_LEANMILL_THEORY_BUILDING=0` reverts to the blind generic conjecture prompt (the A/B baseline)."""
    return os.environ.get("ZTARE_LEANMILL_THEORY_BUILDING", "1") != "0"


def build_prompt(goal_text: str, gap: "TheoryGap | None" = None, theory_defs: str = "") -> str:
    """The CATALOGUE-GUIDED theory-building prompt (the prompt_override for `conjecture_generate`). Frames the
    task as theory-building, embeds the matched op's mechanism + example, asks for the MOST GENERAL reusable
    prerequisite (the lemma a mathematician would name + add to the theory + reuse), and exposes the campaign
    theory's own definitions so the lemma is stated in the substrate's vocabulary — not re-derived from
    `import Mathlib` alone. Keeps the `LEMMA:/PROOF:` fenced contract verbatim (parsed + gated identically)."""
    gap = gap or classify_gap(goal_text)
    op_line = ""
    if gap.op_name or gap.mechanism:
        op_line = (f"This goal's shape owes a **{gap.obligation or 'Decompose'}**"
                   + (f" — the canonical research move is *{gap.op_name}*" if gap.op_name else "")
                   + (f": {gap.mechanism.strip()}" if gap.mechanism else "") + "\n")
        if gap.example:
            op_line += f"Example of this move: {gap.example.strip()}\n"
    if gap.culture:
        op_line += f"Mathematical culture of this gap: {gap.culture.replace('_', '-')}.\n"
    defs_block = ""
    if (theory_defs or "").strip():
        defs_block = ("AVAILABLE THEORY OBJECTS — state your lemma in terms of THESE (already defined; do NOT "
                      "redefine them):\n" + theory_defs.strip()[:2500] + "\n\n")
    return (
        "You are a Lean 4 mathematician doing THEORY-BUILDING, not tactic search. This goal is hard because "
        "its proof needs a piece of THEORY that may not yet exist in the library — a GENERAL prerequisite "
        "lemma about the objects involved (the kind a mathematician would name, prove once, and reuse).\n\n"
        + op_line + "\n" + defs_block +
        "Your task: identify the MISSING PREREQUISITE — the most general, reusable lemma that, once "
        "established, makes this goal a SHORT consequence. It will be PROVEN and BANKED into the theory, then "
        "cited by this goal and its siblings. State it GENERALLY (quantify over the relevant objects); do NOT "
        "restate the goal, do NOT make it trivially true, do NOT bake in the goal's specific hypotheses as "
        "the lemma's conclusion. Think: 'what theorem is the library missing here?' (e.g. 'the residue of a "
        "rational derivative vanishes', 'the local principal part is unique').\n\n"
        "Output EXACTLY:\n"
        "LEMMA:\n```lean\ntheorem {lname} : <the general prerequisite, in the objects' own vocabulary> := by sorry\n```\n"
        "PROOF:\n```lean\n{goal_head} := by\n  <short tactics that REFERENCE {lname} to close the ORIGINAL goal>\n```\n"
        "Rules: the lemma must be GENERAL and load-bearing (the proof genuinely needs it); the PROOF must cite "
        "`{lname}` and contain NO `sorry`.\n"
        "GOAL:\n{goal}\n"
    )


def obligation_hint(goal_text: str) -> str:
    """A per-GOAL catalogue analysis surfaced to the leaf — reconciles the (formerly blind) leaf prompt with
    the research-move catalogue for BOTH cultures: it names the obligation the goal's shape owes, the canonical
    op + its mechanism, and the culture, so the agent picks the catalogue-recommended move (a Construct owes a
    witness, a Transfer owes finding/building the result, a Decompose owes splitting off a reusable lemma).
    '' when nothing classifies (byte-parity). Additive — never overrides the agent's judgment, only informs."""
    g = (goal_text or "").strip()
    if not g:
        return ""
    gap = classify_gap(g)
    if not gap.obligation:
        return ""
    line = f"\n### Obligation analysis (catalogue)\nThis goal's shape owes a **{gap.obligation}**"
    if gap.op_name:
        line += f" — canonical move *{gap.op_name}*"
    if gap.mechanism:
        line += f": {gap.mechanism.strip()[:300]}"
    if gap.culture and gap.culture not in ("unclassified", ""):
        line += f"\nCulture: {gap.culture.replace('_', '-')}."
    if gap.is_theory_building:
        line += ("\nThis is theory-building-flavored: if no existing result applies, NAME the missing general "
                 "prerequisite lemma (it will be proven + banked + cited).")
    return line + "\n"


def _selftest() -> int:
    fails = []
    # classify a clearly theory-building, lemma-shaped goal
    g = "theorem t (f : RatFunc K) (h : HasRatDeriv F f) : simpleResidueCoeff c = 0 := by sorry"
    gap = classify_gap(g)
    if not isinstance(gap, TheoryGap):
        fails.append("classify_gap return type")
    p = build_prompt(g, gap, theory_defs="def simpleResidueCoeff (c) := c 1")
    for tok in ("{lname}", "{goal_head}", "{goal}", "THEORY-BUILDING", "MISSING PREREQUISITE"):
        if tok not in p:
            fails.append(f"prompt missing {tok!r}")
    hint = obligation_hint(g)
    if hint and "Obligation" not in hint:
        fails.append("obligation_hint missing catalogue framing")
    if not isinstance(is_enabled(), bool):
        fails.append("is_enabled not bool")
    # default-on
    os.environ.pop("ZTARE_LEANMILL_THEORY_BUILDING", None)
    if not is_enabled():
        fails.append("should default-on")
    os.environ["ZTARE_LEANMILL_THEORY_BUILDING"] = "0"
    if is_enabled():
        fails.append("=0 should disable")
    os.environ.pop("ZTARE_LEANMILL_THEORY_BUILDING", None)
    print("THEORY_BUILDING SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
