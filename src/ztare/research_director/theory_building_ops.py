"""GP-216 Theory-Building Operations vocabulary v3 — descriptive registry.

Twelve operations in four tiers, derived from cold-LLM mining of 8 famous
theory-building arcs (Wiles FLT, Grothendieck schemes, Lurie HTT, Scholze
perfectoid, Riemann surfaces, Newton calculus, Einstein GR, Polya/Hadamard
meta-reflections), validated through:

  - Pass 1: 161 moves enumerated independently by Sonnet 4.6 + Gemini 2.5 Pro
  - Pass 2: 9 clusters with ≥3-arc cross-spread + 41 outliers (Gemini 2.5 Pro)
  - Pass 3: held-out OOD test on Galois/Gödel/Turing/Russell-ZF/Cohen/
    Mandelbrot/Connes — 58% mean h+m coverage; FAILED pre-registered 70%
    bar; vocabulary is DESCRIPTIVE not GENERATIVE
  - Pass 4: cross-LLM stability (Sonnet+Gemini+GPT-5.5) → 78% ≥2/3 majority
    agreement; 2 ops killed (tb_07 Scaffolding, tb_10 Self-Referential
    Encoding monolithic) for failing to win majority on any move
  - Pass 5: literature audit — no 7+/12 collision; 3-4 ops overlap
    Lakatos/metamath; framing as consolidation of Gowers's "theory-building"
    (Two Cultures of Mathematics, 2000)
  - Pass 6: synthetic expert panel (Gowers/Polya/Lakatos/Gigerenzer/Hofstadter/
    WorkingMath) → 6/6 REVISE; 0 RETRACT, 0 SUPPORT; specific revisions
    applied to produce v3
  - Pass 7: active killing — 2 ops fully collapse to Lakatos (tb_LAK1, tb_LAK2;
    attribution required); 11 ops survive with documented novel residue
    (Sonnet PARTIAL_OVERLAP); GPT-5.5 was more aggressive (FULL_COLLAPSE)
    but its reductions miss Sonnet's intensional/extensional, ontological/
    parameter-level distinctions
  - Pass 8: mined 40 prior ZTARE cycles (NS+AQUAL+Neural) → 7 (18%)
    qualify as theory-building moves, clustered on tb_06 (4) and tb_04 (2)
    + tb_NEW_POLYA (1)

Honest scope limit:

  - DESCRIPTIVE not GENERATIVE: ~58% h+m coverage on held-out arcs; ~40%
    of theory-building moves do NOT fit any op in this vocabulary
  - Coverage residue includes: gap recognition / problem entry; post-theory
    application to new domains; exemplar construction; sub-monograph
    "Tuesday-night" moves (hand-compute examples, dualize, localize,
    obstruction class); irreducibly social/historical moves
  - The vocabulary RECOGNIZES recurring structural moves; it does not
    GENERATE next moves for a stuck researcher
  - 2 ops (tb_LAK1, tb_LAK2) are direct rediscoveries of Lakatos's
    monster-barring/exception-barring/lemma-incorporation; cite Lakatos
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class TheoryBuildingOp:
    """A single theory-building operation."""

    op_id: str
    name: str
    tier: str  # "core" | "secondary" | "reflexive_limitative" | "lakatos_attributed"
    structural_mechanism: str
    arc_examples: tuple[str, ...]
    novel_residue: str  # what this op names that existing primitives don't
    overlaps_with: tuple[str, ...]  # named existing primitives this overlaps
    deployable: bool  # can a stuck researcher deploy this, or only recognize it post-hoc


VOCABULARY_V3: Dict[str, TheoryBuildingOp] = {
    # ─── Core (4) — survived Gowers/Polya/Gigerenzer panel; deployable ───
    "tb_01": TheoryBuildingOp(
        op_id="tb_01",
        name="Foundational Object Redefinition",
        tier="core",
        structural_mechanism=(
            "Replace the object class the theory studies with a different class that exposes "
            "structure invisible in the original (variety→scheme; multivalued function→Riemann "
            "surface; commutative C*-algebra→noncommutative C*-algebra; set→type)."
        ),
        arc_examples=("grothendieck_schemes", "riemann_surfaces", "connes_ncg", "russell_zf"),
        novel_residue=(
            "Ontological base replacement — the theory's subject matter is redefined; not a "
            "parameter-level reframe (ZTARE category_switch)."
        ),
        overlaps_with=("ZTARE pivot.category_switch", "ZTARE pivot.dimensional_shift", "Polya generalize"),
        deployable=False,  # WorkingMath: recognize-only
    ),
    "tb_02": TheoryBuildingOp(
        op_id="tb_02",
        name="Cross-Domain Unification",
        tier="core",
        structural_mechanism=(
            "Establish a non-trivial functorial correspondence between two previously-separate "
            "domains and use it to transport theorems across the bridge (Taniyama-Shimura; "
            "Galois groups ↔ field extensions; Gelfand-Naimark)."
        ),
        arc_examples=("wiles_flt", "galois_theory", "connes_ncg"),
        novel_residue=(
            "Rigorous functorial correspondence enabling theorem transport — distinct from "
            "mere analogy (Polya) or category switch (parameter-level)."
        ),
        overlaps_with=("Polya analogous_problem", "ZTARE pivot.category_switch"),
        deployable=False,
    ),
    "tb_08": TheoryBuildingOp(
        op_id="tb_08",
        name="Parameter Space Internalization",
        tier="core",
        structural_mechanism=(
            "Reify a parametric family of objects (one per parameter value) as a single first-class "
            "object of the theory; generic-property and variation questions become internal "
            "(moduli spaces; Mazur deformation rings; Higgs bundles)."
        ),
        arc_examples=("wiles_flt", "grothendieck_schemes", "scholze_perfectoid"),
        novel_residue=(
            "Reification of parametric family as single object — distinct from mere generalization "
            "or dimensional shift (which add a dimension without internalizing the family-as-object)."
        ),
        overlaps_with=("ZTARE pivot.dimensional_shift", "Polya generalize"),
        deployable=True,
    ),
    "tb_09": TheoryBuildingOp(
        op_id="tb_09",
        name="Systematic Vocabulary Lifting",
        tier="core",
        structural_mechanism=(
            "Re-do an entire existing theory move-by-move inside a new framework, preserving "
            "each step's structural role (Lurie ∞-categorifying ordinary category theory; "
            "Connes redoing Riemannian geometry over noncommutative algebras)."
        ),
        arc_examples=("lurie_htt", "connes_ncg", "scholze_perfectoid"),
        novel_residue=(
            "Move-by-move preservation constraint — every proof step in the original must be "
            "faithfully re-enacted in the new framework. Distinct from category_switch "
            "(parameter-level) or generalize (heuristic)."
        ),
        overlaps_with=("ZTARE pivot.category_switch", "Polya generalize"),
        deployable=True,
    ),

    # ─── Strong secondary (4) — novel residue confirmed; varied deployability ───
    "tb_03": TheoryBuildingOp(
        op_id="tb_03",
        name="Surrogate Problem Substitution",
        tier="secondary",
        structural_mechanism=(
            "Replace the original target with a sufficient-condition target whose proof formally "
            "entails the original (FLT via modularity of semistable elliptic curves; CH "
            "independence via forcing; halting via diagonal in universal machine)."
        ),
        arc_examples=("wiles_flt", "cohen_forcing", "turing_universal_machine"),
        novel_residue=(
            "Logical-entailment substitution — the surrogate's proof formally implies the original. "
            "Distinct from analogy (which only suggests) or work-backward (which retraces steps)."
        ),
        overlaps_with=("Polya analogous_problem", "Polya work_backward", "Polya vary_problem"),
        deployable=True,  # WorkingMath: deploy
    ),
    "tb_04": TheoryBuildingOp(
        op_id="tb_04",
        name="Constraint-Driven Solution Forcing",
        tier="secondary",
        structural_mechanism=(
            "Demand that the answer satisfy a list of structural constraints (covariance, "
            "conservation, consistency, symmetry); their simultaneous satisfaction progressively "
            "narrows the form to a unique solution (Einstein 1915 field equations; ZF axiomatization)."
        ),
        arc_examples=("einstein_gr", "russell_zf", "ns_track_b_ztare"),
        novel_residue=(
            "Constraint-intersection narrowing to unique solution — distinct from work-backward "
            "(reverse-engineering from goal) or fixed_point_scan (canonical-value search). "
            "Empirically present in 2/40 ZTARE cycles (Pass 8)."
        ),
        overlaps_with=("Polya work_backward", "ZTARE pivot.fixed_point_scan", "Tao negative_results"),
        deployable=False,  # recognize-only
    ),
    "tb_06": TheoryBuildingOp(
        op_id="tb_06",
        name="Tacit Pattern Formalization",
        tier="secondary",
        structural_mechanism=(
            "Take an already-functioning implicit working pattern and construct a formal apparatus "
            "(notation, axioms, definitions, gate) that makes the pattern's logic explicit, "
            "inspectable, and transferable (fluxion→derivative; intuitive symmetry→tensor "
            "calculus; descriptive scaling→fractal dimension; tacit verification trick→ZTARE gate)."
        ),
        arc_examples=("newton_calculus", "einstein_gr", "mandelbrot_fractals", "ns_track_b_ztare"),
        novel_residue=(
            "Implicit-to-formal direction — taking tacit working practice UP into formal "
            "apparatus. Distinct from entropy_stripping (which moves abstract DOWN to "
            "observables) or anchor_proxy (binds abstract to readable observable). "
            "Empirically present in 4/40 ZTARE cycles (Pass 8) — the most-instantiated "
            "theory-building op in ZTARE day-to-day work."
        ),
        overlaps_with=("ZTARE pivot.entropy_stripping", "Paper5 op5 anchor_proxy", "Tao smell"),
        deployable=True,  # WorkingMath: deploy
    ),
    "tb_NEW_POLYA": TheoryBuildingOp(
        op_id="tb_NEW_POLYA",
        name="Strategic Specialization",
        tier="secondary",
        structural_mechanism=(
            "Solve a deliberately-chosen special case whose solution actively breaks a structural "
            "barrier in the general problem; the special case is the decisive engine, not a stepping "
            "stone (Wiles's semistable elliptic curves; Newton's specific curves)."
        ),
        arc_examples=("wiles_flt", "newton_calculus", "ns_track_b_ztare"),
        novel_residue=(
            "Load-bearing special case that breaks a structural barrier — distinct from generic "
            "Polya specialize (try a special case to gain insight). The special case in this op "
            "is selected because it carries the proof-engine for the general result."
        ),
        overlaps_with=("Polya specialize", "Polya generalize", "Lakatos lemma_incorporation"),
        deployable=True,
    ),

    # ─── Reflexive-limitative (2) — Hofstadter-corrected ───
    "tb_NEW_HOF": TheoryBuildingOp(
        op_id="tb_NEW_HOF",
        name="Diagonal Self-Application",
        tier="reflexive_limitative",
        structural_mechanism=(
            "Apply a predicate defined over codes of statements to its own code; the predicate's "
            "domain (codes) and the predicate itself (a statement, hence codeable) collapse, "
            "producing a fixed point where syntax and semantics tangle (Gödel diagonal lemma; "
            "Cantor's diagonal; Kleene fixed-point; Quine quotation)."
        ),
        arc_examples=("godel_incompleteness", "turing_universal_machine", "cohen_forcing"),
        novel_residue=(
            "Level-collapse via predicate-applied-to-own-code — intensional, not extensional. "
            "Distinct from fixed_point_scan (which finds extensional fixed points f(x)=x without "
            "the syntactic-semantic tangle) and collision_exploit (output coincidence)."
        ),
        overlaps_with=("ZTARE pivot.fixed_point_scan", "ZTARE pivot.collision_exploit"),
        deployable=False,  # technique requires deep formal-systems craft
    ),
    "tb_11": TheoryBuildingOp(
        op_id="tb_11",
        name="Limitative Theorem Construction",
        tier="reflexive_limitative",
        structural_mechanism=(
            "Use the diagonal self-application of tb_NEW_HOF to derive a structural impossibility "
            "(incompleteness, undecidability, independence). Hofstadter's panel correction: "
            "tb_11 is the OUTCOME; tb_NEW_HOF is the move that produces it."
        ),
        arc_examples=("godel_incompleteness", "turing_universal_machine", "cohen_forcing"),
        novel_residue=(
            "Diagonal as generative move for limitative result — distinct from negative_results "
            "(elimination of options) or inversion (what would destroy the hypothesis). The "
            "limitative theorem is consequent of the diagonal, not co-equal."
        ),
        overlaps_with=("Tao negative_results", "ZTARE pivot.inversion", "ZTARE pivot.fixed_point_scan"),
        deployable=False,
    ),

    # ─── Lakatos-attributed (2) — direct rediscovery; cite Lakatos ───
    "tb_LAK1": TheoryBuildingOp(
        op_id="tb_LAK1",
        name="Refutation-Driven Concept Revision",
        tier="lakatos_attributed",
        structural_mechanism=(
            "A concrete counter-example forces revision of the meaning of a core term in the "
            "theory; the concept stretches or restricts in response (Lakatos 1976: monster-"
            "barring, exception-barring; Russell's paradox forcing ZF separation axiom)."
        ),
        arc_examples=("russell_zf",),
        novel_residue=(
            "EMPTY — this op is a direct rediscovery of Lakatos's monster-barring + "
            "exception-barring. Cite Lakatos *Proofs and Refutations* (1976)."
        ),
        overlaps_with=("Lakatos monster_barring", "Lakatos exception_barring"),
        deployable=True,
    ),
    "tb_LAK2": TheoryBuildingOp(
        op_id="tb_LAK2",
        name="Proof-Analysis Under Counter-Example",
        tier="lakatos_attributed",
        structural_mechanism=(
            "When a proof fails on a counter-example, localize which sub-step failed and absorb "
            "the missing condition as an explicit lemma; the proof and the conditions co-evolve "
            "(Lakatos 1976: lemma-incorporation, the preferred dialectical operation)."
        ),
        arc_examples=("wiles_flt",),  # Euler-system gap → Iwasawa-theory replacement
        novel_residue=(
            "EMPTY — direct rediscovery of Lakatos's lemma-incorporation. Cite Lakatos "
            "*Proofs and Refutations* (1976)."
        ),
        overlaps_with=("Lakatos lemma_incorporation", "Paper5 op2 controlling_claim_isolation"),
        deployable=True,
    ),
}


# Tier-based access
def by_tier(tier: str) -> List[TheoryBuildingOp]:
    """Return all ops in a given tier."""
    return [op for op in VOCABULARY_V3.values() if op.tier == tier]


def deployable() -> List[TheoryBuildingOp]:
    """Return ops a stuck researcher can deploy (vs only recognize post-hoc)."""
    return [op for op in VOCABULARY_V3.values() if op.deployable]


def get(op_id: str) -> Optional[TheoryBuildingOp]:
    """Look up an op by id."""
    return VOCABULARY_V3.get(op_id)


# ─── Cross-scale mapping (the user's "fractal" intuition, documented honestly) ───

# At the WORKING-RESEARCH-AT-MONOGRAPH SCALE, the vocabulary v3 lists 12 ops.
# At smaller scales, ZTARE already encodes some of these moves under different
# names. The fractal claim is empirically PARTIAL: 7 of 40 ZTARE cycles (18%)
# instantiate theory-building ops (Pass 8), clustered on tb_06 (4 cycles) and
# tb_04 (2 cycles) and tb_NEW_POLYA (1 cycle). Other ops have no observed
# ZTARE instances in the GP-215 catalog.
#
# The cross-scale correspondences below are CLAIMS OF STRUCTURAL ANALOGY, not
# proofs of equivalence. Each claim names which ZTARE primitive (or paper 5
# op) shares structural mechanism with which theory-building op. The
# correspondences are tested by Sonnet's PARTIAL_OVERLAP verdict in Pass 7
# (active killing): each ZTARE primitive named here was confirmed to overlap
# the theory-building op without fully collapsing it.
CROSS_SCALE_MAPPING: Dict[str, Dict[str, str]] = {
    "tb_01": {
        "ztare_iteration_scale": "pivot.category_switch (mathematical-category change)",
        "ztare_coordinate_scale": "framer.SIGMA primitive selection (signed_log, asinh, etc.)",
        "ztare_physics_scale": "invariant_search rubric_mode (Lagrangian primitive)",
        "novel_residue_at_macro_scale": (
            "Ontological base replacement (variety→scheme) is categorically larger than "
            "any of these ZTARE-scale instances; the scale-up is genuine."
        ),
    },
    "tb_02": {
        "ztare_iteration_scale": "pivot.coordinate_compression (change coordinate system)",
        "ztare_physics_scale": "invariant_search Buckingham π (dimensional unification)",
        "novel_residue_at_macro_scale": (
            "Functorial theorem-transport (Taniyama-Shimura) is categorically larger; "
            "ZTARE-scale instances unify within one substrate, not across domains."
        ),
    },
    "tb_04": {
        "ztare_iteration_scale": "pivot.fixed_point_scan + pivot.collision_exploit (constraint accumulation)",
        "ztare_meta_scale": "Lean obligation gates that must be simultaneously satisfied",
        "empirical_instance_in_corpus": "C20, C39 (NS Track B) — gates as constraint-narrowing",
    },
    "tb_06": {
        "ztare_iteration_scale": "pivot.entropy_stripping (restate in observable transfers)",
        "ztare_meta_scale": "ZTARE gate construction (Pass 8: most-instantiated tb op in ZTARE)",
        "empirical_instances_in_corpus": "C11, C22, C23, C40 — formalizing tacit verification patterns",
    },
    "tb_08": {
        "ztare_iteration_scale": "pivot.dimensional_shift",
        "ztare_physics_scale": "invariant_search Noether variance (parameter-family symmetry)",
    },
    "tb_NEW_HOF": {
        "ztare_iteration_scale": "pivot.fixed_point_scan + pivot.collision_exploit",
        "novel_residue_at_macro_scale": (
            "Intensional level-collapse (predicate-on-own-code) is categorically distinct "
            "from extensional fixed-point search; not present at iteration scale."
        ),
    },
    "tb_11": {
        "ztare_iteration_scale": "pivot.inversion (what observation would destroy hypothesis)",
        "novel_residue_at_macro_scale": (
            "Limitative theorem is global structural impossibility; iteration-scale inversion "
            "asks what would destroy a single thesis."
        ),
    },
}


def render_vocabulary_summary() -> str:
    """Render a human-readable summary of vocabulary v3 with empirical notes."""
    lines = ["# GP-216 Theory-Building Operations Vocabulary v3", ""]
    lines.append("**Status:** descriptive (not generative); ~58% h+m coverage on held-out arcs")
    lines.append("**Source:** Gowers's *Two Cultures of Mathematics* category, operationalized")
    lines.append("**Anti-claim:** this is NOT a meta-solver; ~40% of theory-building moves do not fit any op here")
    lines.append("")
    for tier_name, tier_label in (
        ("core", "Core (4)"),
        ("secondary", "Strong secondary (4)"),
        ("reflexive_limitative", "Reflexive-limitative (2)"),
        ("lakatos_attributed", "Lakatos-attributed (2 — direct rediscovery; cite Lakatos)"),
    ):
        lines.append(f"## {tier_label}")
        for op in by_tier(tier_name):
            deploy = "DEPLOYABLE" if op.deployable else "recognize-only"
            lines.append(f"- **{op.op_id}** {op.name} [{deploy}]")
            lines.append(f"  - Mechanism: {op.structural_mechanism}")
            lines.append(f"  - Arc examples: {', '.join(op.arc_examples)}")
            if op.novel_residue and op.novel_residue != "EMPTY — direct rediscovery; see overlaps":
                lines.append(f"  - Novel residue: {op.novel_residue}")
            lines.append(f"  - Overlaps: {', '.join(op.overlaps_with)}")
        lines.append("")
    return "\n".join(lines)


__all__ = [
    "VOCABULARY_V3",
    "TheoryBuildingOp",
    "CROSS_SCALE_MAPPING",
    "by_tier",
    "deployable",
    "get",
    "render_vocabulary_summary",
]


if __name__ == "__main__":
    print(render_vocabulary_summary())
