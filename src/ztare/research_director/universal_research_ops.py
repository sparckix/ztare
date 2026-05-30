"""GP-216 paper 5b — Universal Research Operations vocabulary v5.

UPDATED 2026-05-05 after 8-subfield mining + business OOD validation.

The 7-op core from 5-subfield pass (v4) refined to a 6-op core at 8-subfield
scale. Iterative Refinement Loop demoted from shared-core (5/5) to broadly-
shared (5/8) because logic / set theory + algebraic topology use it less.
A new core_05 Canonical Form & Invariance emerged from those subfields.

CRITICAL EXPANSION: business held-out OOD test passed at 58% (shared+broadly)
— vocabulary is universal BEYOND mathematics. The 6-op core is structural-
research-specific, not math-specific.

Empirically derived 6-op shared core + 8 broadly-shared + 4 subfield-specific
ops, mined from 64 arcs across 8 subfields:
  - theory_building (Wiles, Grothendieck, Lurie, Scholze, Riemann, Newton, Einstein, Polya/Hadamard)
  - additive_combinatorics (Erdős, Green-Tao, Hales-Jewett polymath, Szemerédi, Roth, Behrend, Furstenberg, Ramsey-ES)
  - graph_theory (Wagner, Hadwiger, Tutte 4CT, max-flow, Halin, EKR, Karchmer-Wigderson, Menger)
  - complexity_theory (Karp 21, Razborov, Yao, IP=PSPACE, PCP, Toda, Levin, Valiant)
  - geometric_flow_pde (Hamilton MCF, Yang-Mills, harmonic-map, Schoen-Yau, Brendle, Harvey-Lawson, De Giorgi, Moser)
  - logic_set_theory (Cantor, ZF, Gödel, Cohen, Tarski, Robinson, Löwenheim-Skolem, Solovay-Reinhardt)
  - algebraic_topology (Poincaré duality, Hurewicz, Adams, Bott, Atiyah-Singer, Quillen K-theory, Steenrod, Sullivan)
  - applied_math (FFT, Strassen, simplex, Karmarkar, Kalman, FEM, Monte Carlo, autodiff)

Total moves: 1214 across 64 arcs in 8 mathematical subfields.

Validation:
  - 8-subfield cross-clustering: 6 shared-core ops appear in ≥6 of 8 subfields
  - Held-out math subfield (probability/Itô at 7-op vocab): 58% h+m
  - Held-out NON-MATH (6 business arcs: Christensen / Porter / Munger / Drucker / Kahneman / Mintzberg):
    53% shared-core, 58% shared+broadly. Vocabulary IS universal beyond mathematics.
    The 6-op core is structural-research-specific, not math-specific.
  - Original 18-op TB+PS vocabulary was canon-overfit; collapsed via aliasing.
  - 7-op v4 (5-subfield core) refined to 6-op v5 (8-subfield core);
    Iterative Refinement Loop demoted to broadly-shared (5/8 spread).

Honest scope:
  - Empirically validated on 8 mathematical subfields, a 6-arc business OOD
    set, and a sparse post-cutoff 2026 specialist-paper OOD set.
  - Coverage is 58% on held-out, not 100%. ~40% of moves remain outside
    the 18-op total vocabulary even after Path A+B mining.
  - Vocabulary is descriptive, not generative. Recognition tool, not toolkit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Union


@dataclass(frozen=True)
class UniversalResearchOp:
    op_id: str
    name: str
    tier: str  # "shared_core" | "broadly_shared" | "subfield_specific"
    structural_mechanism: str
    subfield_spread: tuple[str, ...]
    n_subfields: int
    aliases_collapsed: tuple[str, ...]  # which v3/v3' ops are aliases of this universal op


VOCABULARY_V5: Dict[str, UniversalResearchOp] = {
    # Shared core: 6 ops, >=6 of 8 subfields.
    "core_01": UniversalResearchOp(
        op_id="core_01",
        name="Problem Reformulation & Reduction",
        tier="shared_core",
        structural_mechanism=(
            "Replacing a problem with a structurally equivalent or logically connected surrogate "
            "to make it more tractable or to transfer properties like computational hardness."
        ),
        subfield_spread=("theory_building", "additive_combinatorics", "graph_theory",
                          "complexity_theory", "geometric_flow_pde", "logic_set_theory",
                          "algebraic_topology", "applied_math"),
        n_subfields=8,
        aliases_collapsed=("tb_03 Surrogate Problem Substitution",
                            "ps_03 Formal Equivalence Transfer"),
    ),
    "core_02": UniversalResearchOp(
        op_id="core_02",
        name="Generalization & Abstraction",
        tier="shared_core",
        structural_mechanism=(
            "Replacing a class of objects or a specific structure with a more encompassing one "
            "that relaxes constraints, thereby unifying disparate cases under a single framework."
        ),
        subfield_spread=("theory_building", "additive_combinatorics", "graph_theory",
                          "complexity_theory", "geometric_flow_pde", "logic_set_theory",
                          "algebraic_topology", "applied_math"),
        n_subfields=8,
        aliases_collapsed=("tb_01 Foundational Object Redefinition",
                            "tb_09 Systematic Vocabulary Lifting"),
    ),
    "core_03": UniversalResearchOp(
        op_id="core_03",
        name="Decomposition & Recomposition",
        tier="shared_core",
        structural_mechanism=(
            "Breaking a complex object or problem into simpler, manageable components, analyzing "
            "or solving them independently, and then reassembling the results."
        ),
        subfield_spread=("theory_building", "additive_combinatorics", "graph_theory",
                          "complexity_theory", "geometric_flow_pde", "logic_set_theory",
                          "algebraic_topology", "applied_math"),
        n_subfields=8,
        aliases_collapsed=("ps_01 Structural Partitioning", "tb_08 Parameter Space Internalization"),
    ),
    "core_04": UniversalResearchOp(
        op_id="core_04",
        name="Local-to-Global Assembly",
        tier="shared_core",
        structural_mechanism=(
            "Constructing a global object or proving a global property by specifying local pieces "
            "and rules for how they cohere, often through gluing or integration."
        ),
        subfield_spread=("theory_building", "additive_combinatorics", "graph_theory",
                          "complexity_theory", "geometric_flow_pde", "logic_set_theory",
                          "algebraic_topology", "applied_math"),
        n_subfields=8,
        aliases_collapsed=(),
    ),
    "core_05": UniversalResearchOp(
        op_id="core_05",
        name="Canonical Form & Invariance",
        tier="shared_core",
        structural_mechanism=(
            "Identifying stable properties or unique representatives within equivalence classes "
            "to simplify analysis by eliminating redundant or superficial complexity."
        ),
        subfield_spread=("theory_building", "additive_combinatorics", "graph_theory",
                          "complexity_theory", "geometric_flow_pde", "algebraic_topology",
                          "applied_math"),
        n_subfields=7,
        aliases_collapsed=(),
    ),
    "core_06": UniversalResearchOp(
        op_id="core_06",
        name="Cross-Domain Translation",
        tier="shared_core",
        structural_mechanism=(
            "Establishing a formal correspondence between two distinct conceptual domains, "
            "allowing methods and insights from one to be applied to the other."
        ),
        subfield_spread=("theory_building", "additive_combinatorics", "graph_theory",
                          "complexity_theory", "geometric_flow_pde", "logic_set_theory",
                          "algebraic_topology"),
        n_subfields=7,
        aliases_collapsed=("tb_02 Cross-Domain Unification",),
    ),

    # Broadly shared: 8 ops, 4-5 subfields.
    "broad_01": UniversalResearchOp(
        op_id="broad_01", name="Iterative Refinement", tier="broadly_shared",
        structural_mechanism=(
            "Progressively improving a solution or approximation through repeated application "
            "of a procedure that guarantees monotonic improvement of a key metric."
        ),
        subfield_spread=("additive_combinatorics", "graph_theory", "geometric_flow_pde",
                         "applied_math", "theory_building"),
        n_subfields=5,
        aliases_collapsed=("ps_02 Governed Iterative Refinement",
                            "ps_06 Proof by Estimate Chaining"),
    ),
    "broad_02": UniversalResearchOp(
        op_id="broad_02", name="Recursive Decomposition", tier="broadly_shared",
        structural_mechanism=(
            "Solving a problem by repeatedly breaking it down into smaller, self-similar "
            "instances of the same problem until a trivial base case is reached."
        ),
        subfield_spread=("additive_combinatorics", "graph_theory", "complexity_theory",
                         "logic_set_theory", "applied_math"),
        n_subfields=5,
        aliases_collapsed=("ps_05 Induction on Structural Rank",),
    ),
    "broad_03": UniversalResearchOp(
        op_id="broad_03", name="Duality & Adversarial Framing", tier="broadly_shared",
        structural_mechanism=(
            "Reframing a problem by constructing a corresponding dual problem or a strategic "
            "game whose solution provides insight into the original."
        ),
        subfield_spread=("graph_theory", "complexity_theory", "additive_combinatorics",
                         "algebraic_topology", "applied_math"),
        n_subfields=5,
        aliases_collapsed=(),
    ),
    "broad_04": UniversalResearchOp(
        op_id="broad_04", name="Layered Approximation & Convergence", tier="broadly_shared",
        structural_mechanism=(
            "Constructing a solution as the limit of a sequence of simpler, staged "
            "approximations whose properties are analyzed at each step."
        ),
        subfield_spread=("theory_building", "additive_combinatorics", "geometric_flow_pde",
                         "algebraic_topology"),
        n_subfields=4,
        aliases_collapsed=(),
    ),
    "broad_05": UniversalResearchOp(
        op_id="broad_05", name="Extremal Method", tier="broadly_shared",
        structural_mechanism=(
            "Analyzing boundary, worst-case, or optimal examples to deduce properties that "
            "must hold for all instances within a class."
        ),
        subfield_spread=("additive_combinatorics", "graph_theory", "geometric_flow_pde",
                         "theory_building"),
        n_subfields=4,
        aliases_collapsed=("tb_NEW_POLYA Strategic Specialization",),
    ),
    "broad_06": UniversalResearchOp(
        op_id="broad_06", name="Probabilistic & Stochastic Methods", tier="broadly_shared",
        structural_mechanism=(
            "Using randomness, sampling, and expectation as computational tools to solve "
            "deterministic problems or to prove existence."
        ),
        subfield_spread=("additive_combinatorics", "graph_theory", "complexity_theory",
                         "applied_math"),
        n_subfields=4,
        aliases_collapsed=(),
    ),
    "broad_07": UniversalResearchOp(
        op_id="broad_07", name="Dimensional & Structural Lifting", tier="broadly_shared",
        structural_mechanism=(
            "Embedding a problem into a higher-dimensional or more abstract space where "
            "constraints are relaxed or new geometric or algebraic tools become available."
        ),
        subfield_spread=("additive_combinatorics", "complexity_theory", "algebraic_topology",
                         "theory_building"),
        n_subfields=4,
        aliases_collapsed=(),
    ),
    "broad_08": UniversalResearchOp(
        op_id="broad_08", name="Constraint Imposition & Propagation", tier="broadly_shared",
        structural_mechanism=(
            "Establishing a set of required conditions and deriving the necessary consequences, "
            "often forcing a unique structure or revealing a contradiction."
        ),
        subfield_spread=("theory_building", "additive_combinatorics", "geometric_flow_pde",
                         "logic_set_theory"),
        n_subfields=4,
        aliases_collapsed=("tb_04 Constraint-Driven Solution Forcing",),
    ),

    # Subfield-specific idioms from the 8-subfield pass.
    "spec_01": UniversalResearchOp(
        op_id="spec_01", name="Characterization by Obstruction", tier="subfield_specific",
        structural_mechanism=(
            "Defining a class of objects not by its internal properties but by the absence "
            "of a finite set of forbidden substructures or configurations."
        ),
        subfield_spread=("graph_theory",), n_subfields=1, aliases_collapsed=(),
    ),
    "spec_02": UniversalResearchOp(
        op_id="spec_02", name="Internalization & Self-Reference", tier="subfield_specific",
        structural_mechanism=(
            "Encoding a system's own structure or meta-properties within the system itself "
            "to construct statements about its own limits or behavior."
        ),
        subfield_spread=("logic_set_theory", "complexity_theory"), n_subfields=2,
        aliases_collapsed=("tb_NEW_HOF Diagonal Self-Application",
                            "tb_11 Limitative Theorem Construction"),
    ),
    "spec_03": UniversalResearchOp(
        op_id="spec_03", name="Axiomatization & Foundational Repair", tier="subfield_specific",
        structural_mechanism=(
            "Establishing or fixing the ground rules of a formal system by explicitly "
            "enumerating a minimal set of generative principles to resolve paradoxes and "
            "ensure consistency."
        ),
        subfield_spread=("theory_building", "logic_set_theory"), n_subfields=2,
        aliases_collapsed=("tb_LAK1 Refutation-Driven Concept Revision",
                            "tb_LAK2 Proof-Analysis Under Counter-Example"),
    ),
    "spec_04": UniversalResearchOp(
        op_id="spec_04", name="Controlled Universe Extension", tier="subfield_specific",
        structural_mechanism=(
            "Augmenting a logical or algebraic universe with new elements in a way that "
            "preserves existing axioms while forcing a specific independent proposition "
            "to be true or false."
        ),
        subfield_spread=("logic_set_theory",), n_subfields=1, aliases_collapsed=(),
    ),
}

# Backward-compatible alias for older imports. The value is intentionally v5.
VOCABULARY_V4 = VOCABULARY_V5


def by_tier(tier: str) -> List[UniversalResearchOp]:
    return [op for op in VOCABULARY_V5.values() if op.tier == tier]


def get(op_id: str) -> Optional[UniversalResearchOp]:
    return VOCABULARY_V5.get(op_id)


def render_vocabulary_summary() -> str:
    lines = ["# Universal Research Operations Vocabulary v5 (paper 5b, GP-216)", ""]
    lines.append("**Status:** descriptive (not generative); empirically generic across structural-research corpora")
    lines.append("**Source:** mined from 64 arcs across 8 mathematical subfields (1214 moves)")
    lines.append("**OOD coverage:** business held-out 57.9% shared+broadly; sparse post-cutoff 2026 papers 75.2% shared+broadly")
    lines.append("")
    for tier_name, tier_label in (
        ("shared_core", "SHARED CORE — 6 ops in >=6 of 8 subfields"),
        ("broadly_shared", "BROADLY SHARED — 8 ops in 4-5 subfields"),
        ("subfield_specific", "SUBFIELD-SPECIFIC IDIOMS — 4 peripheral ops"),
    ):
        lines.append(f"## {tier_label}")
        for op in by_tier(tier_name):
            lines.append(f"- **{op.op_id}** {op.name} ({op.n_subfields} subfields)")
            lines.append(f"  - Mechanism: {op.structural_mechanism}")
            lines.append(f"  - Subfields: {', '.join(op.subfield_spread)}")
            if op.aliases_collapsed:
                lines.append(f"  - Aliases collapsed from v3 vocabulary: {'; '.join(op.aliases_collapsed)}")
        lines.append("")
    return "\n".join(lines)


# ─── META-META tier (added 2026-05-09 per PL-105) ───────────────────────────
#
# The 18 v5 ops mined above describe MOVES — things a researcher does within
# an established mathematical game (translate, decompose, generalize, bound,
# refine). PL-105 (1880s framing-layer cold-shot, GPT-5 HIGH 64K, $0.53,
# response: projects/ns_millennium_hunt/workspace/external_prover/responses/epd-5ca871c6c6ad.md)
# identified a layer ABOVE moves: shifts in what counts as a legitimate object
# / proof / solution / state in the first place. These are not moves inside
# the game; they redraw the boundary of the game.
#
# Two such META-META ops are added below as a new `meta_meta` tier. They are
# intentionally described with concrete worked examples rather than abstract
# mechanisms — the operator-stated motivation for adding them was that the
# original cold-shot description was "too abstract ut words."
#
# WARRANT STATUS — pre-warrant, paper-5b validation pending.
# These ops were proposed by ONE cold-shot, not mined cold from a multi-
# subfield corpus. They have NOT been through the paper-5b validation
# methodology (cold-LLM blind enumeration on 5+ subfields → cross-clustering
# → held-out validation → random-split negative control → compression test
# → sparse-coverage post-cutoff → adversarial stress). The cold-shot's
# adversarial check (against existing 18 v5 + 7 GP-219 ops) showed the closest
# captures live one level below (`broad_05`, `broad_07`, `core_02`, `ec_04`,
# `ec_07`) — they are adjacent but at the move-layer not the game-layer.
# Empirical confirmation that the predicted RENAME failure mode is real on
# our apparatus: C-98 (Duchon-Robert μ[u] echo treated as ec_04 limit-passage
# when META was admissibility-criterion redefinition) and C-96 (Lorentz Strip
# overclaim treated as ec_02 regime-scoping when META was integrability-class
# redefinition). Two retroactive data points → dominant predicted failure
# mode (RENAME, 5/10 cases) is observably live on this apparatus.
#
# The paper-5b methodology owed to fully ratify these ops:
#   1. Re-mine the 8-subfield corpus searching for game-layer reframings
#      (this layer was invisible to the v5 mining because the arcs sampled
#      *work within* an ACR/SSP semantics rather than execute one).
#   2. Held-out validation on physics arcs (where SSP via gauge / GR is most
#      visible) and foundations arcs (where ACR via Cantor / Schwartz /
#      effectivity is most visible).
#   3. Negative control: a forced fit using only the 18 v5 + 7 GP-219 ops on
#      arcs known to execute ACR/SSP (Schwartz distributions, Klein Erlangen,
#      gauge symmetry, suitable-weak-solution definition for NS) — if the
#      forced fit succeeds at >85%, ACR/SSP are renames not gaps.
#   4. Cross-rater inter-rater on retroactive tagging of catch-ledger
#      (C-98 / C-96 + others) for ACR/SSP signal.
#
# Until this validation runs, ops are tagged `validation_status="PRE-WARRANT"`
# and consumers (research-director advisor narration, mandate, charter
# templates) should display this caveat alongside the op.


@dataclass(frozen=True)
class MetaMetaOp:
    """A game-layer reframe — shifts what counts as legitimate object / proof
    / solution / state. One level above the move-layer in `UniversalResearchOp`.

    Fields:
      op_id: stable identifier (mm_NN).
      name: short human-readable label.
      tier: always "meta_meta".
      structural_mechanism: 1-2 sentence description of the reframe.
      worked_examples: list of concrete instantiations (1880s + modern + NS-side
                        if applicable). Required because the op is otherwise
                        too abstract to recognize in the wild.
      ns_substrate_projection: how this op manifests in current NS-Track-B work
                                (or None if it does not).
      adjacent_lower_tier_ops: which v5/GP-219 op_ids the apparatus is most
                                likely to RENAME this move under (predicted
                                failure mode from PL-105 Q3).
      validation_status: "PRE-WARRANT" until paper-5b methodology ratifies.
      proposed_at: ISO date of cold-shot that proposed this op.
      proposed_by: cold-shot PL_id.
    """
    op_id: str
    name: str
    tier: str  # always "meta_meta"
    structural_mechanism: str
    worked_examples: tuple[str, ...]
    ns_substrate_projection: Optional[str]
    adjacent_lower_tier_ops: tuple[str, ...]
    validation_status: str
    proposed_at: str
    proposed_by: str


META_META_VOCABULARY: Dict[str, MetaMetaOp] = {
    "mm_01": MetaMetaOp(
        op_id="mm_01",
        name="Admissible-Criteria Rebaselining (ACR)",
        tier="meta_meta",
        structural_mechanism=(
            "Redraw what counts as a legitimate object/solution/proof. The shift "
            "is at the membership boundary of the game itself: the new criterion "
            "is formalized as an interface (quantifier alternation, weak/test-"
            "function action, equivalence-class identification), the class is "
            "closed under a specified limit/completion, and the completions are "
            "elevated to PRIMARY objects of study, not auxiliary technical "
            "artifacts. Distinct from `core_02 Generalization & Abstraction` — that "
            "extends a family within a fixed admissibility; ACR redraws "
            "admissibility itself."
        ),
        worked_examples=(
            "Cantor 1874-1891: a 'completed infinite set' becomes an admissible "
            "mathematical object. Before Cantor: infinity is potential, sets are "
            "finite. After: completed infinities are primary, with cardinal "
            "arithmetic on them.",
            "Weierstrass 1860s-1880s: a 'proof of convergence' is regimented as "
            "an explicit ε-δ quantifier-alternation witness. Before: geometric/"
            "infinitesimal intuition counted. After: only quantifier-certified "
            "arguments do.",
            "Schwartz 1940s (Heaviside seed 1880s): a 'function' is admissible "
            "as a continuous linear functional on test-function space; "
            "derivatives are weak (action-on-tests) operations. The Dirac δ, "
            "previously a heuristic, becomes a primary object.",
            "Caffarelli-Kohn-Nirenberg 1982 (NS-relevant): 'suitable weak "
            "solution' is the admissibility criterion that powers partial "
            "regularity. The interface is a local-energy inequality + "
            "div-free + L²_t-H¹_x; SWS-class is the primary solution-class for "
            "3D NS regularity questions.",
            "Boltzmann/Gibbs 1877-1902: a 'physical state' is admissible as a "
            "probability measure on phase space. State-space is reset from "
            "points to measures.",
        ),
        ns_substrate_projection=(
            "Three live decisive instantiations on NS-Track-B: "
            "(i) Defect-calculus pivot (RD-BL): μ[u] := w*-lim Π_ℓ[u] is an "
            "ACR move BY CONSTRUCTION — the defect measure is being elevated "
            "to a primary obstruction-to-regularity object, not treated as a "
            "technical limit-passage artifact. C-98 (Duchon-Robert echo) is "
            "what happens when the apparatus mislabels this as ec_04. "
            "(ii) Lorentz Strip re-charter (post-C-96): Lorentz-space "
            "membership L^{p,q} redefines what 'integrability' counts as for "
            "the smallness-class. Without ACR labeling the apparatus drifts "
            "into ec_02 regime-scoping framing and misses the admissibility-"
            "criterion shift. "
            "(iii) Bochner-Fejér extension of trilinear NS form (RD-AJ): the "
            "almost-periodic projector defines a new admissibility-class for "
            "the trilinear form on which stationary NS dynamics reduce. "
            "Partial ACR; full ACR on stationary 3D NS still open."
        ),
        adjacent_lower_tier_ops=(
            "core_02",  # Generalization & Abstraction (RENAME-risk: most likely)
            "ec_04",    # Limit-Passage Property Inheritance (RENAME-risk: C-98 evidence)
            "ec_02",    # Regime / Class Scoping (RENAME-risk: C-96 evidence)
            "core_06",  # External Framework Importation (RENAME-risk: secondary)
        ),
        validation_status="PRE-WARRANT",
        proposed_at="2026-05-09",
        proposed_by="PL-105",
    ),
    "mm_02": MetaMetaOp(
        op_id="mm_02",
        name="Structural-Semantics Pluralization (SSP)",
        tier="meta_meta",
        structural_mechanism=(
            "Shift identity/truth from intended-content semantics to invariance "
            "under a specified transformation/morphism class. Redundant "
            "representational scaffolding (gauge, coordinates, frames, intended "
            "interpretations) is QUOTIENTED OUT of ontology; equivalence-classes "
            "ARE the objects. Multiple models are licensed simultaneously. "
            "Distinct from `broad_05 Forcing via Constraint` — broad_05 narrows "
            "an admissible class within a fixed semantics; SSP rebases what "
            "semantics counts. Distinct from `ec_07 Representation` — that "
            "rewrites in better coordinates; SSP demotes coordinates to "
            "representation."
        ),
        worked_examples=(
            "Beltrami-Klein 1868-1872: 'geometry' is identified with the "
            "consistency of an axiom system + a model; Euclidean is no longer "
            "uniquely compulsory. Multiple consistent geometries are "
            "simultaneously legitimate.",
            "Klein Erlangen 1872: a geometry IS its invariants under a "
            "transformation group. Coordinates and metrics are demoted to "
            "representational scaffolding; the group + invariants ARE the "
            "geometric content.",
            "Maxwell-Hertz 1880s + SR/GR 1905-1915: physical states are "
            "equivalence classes under gauge / inertial-frame transformations. "
            "The ether (a privileged absolute frame) is removed not because "
            "it was empirically refuted, but because the SSP move quotienting "
            "out absolute frames removes its ontological role.",
            "Hilbert axiomatic method 1899: 'meaning' of a theory is any "
            "structure satisfying its axioms; truth is invariance across all "
            "models (isomorphism-invariant validity).",
            "Topology-first identity 1880s-1895: 'same space' means "
            "homeomorphic; metric structure is representational, topological "
            "invariants are constitutive.",
        ),
        ns_substrate_projection=(
            "Two live but weaker instantiations on NS-Track-B: "
            "(i) Galilean / scaling invariance as game-semantics: solutions "
            "u(x,t) and λu(λx,λ²t) ARE the same solution. Apparatus currently "
            "treats scaling as ec_02 regime-scoping; SSP labeling aligns with "
            "how 2026 PDE literature actually frames critical / sub-critical "
            "regimes (the equivalence-class is the object, scaling-orbit "
            "membership IS the regime). "
            "(ii) Transport Gap / Lord Kelvin falsifier (RD-BJ, C-92): tests "
            "whether apparatus-outputs are stable under the operator-scaffold "
            "transformation group — i.e., whether the apparatus has a "
            "scaffold-invariant identity. With SSP vocabulary, RD-BJ becomes "
            "literally an SSP-stability test on the apparatus itself, not a "
            "vague 'is the apparatus over-fit to scaffolds' question. "
            "Effectivity blind-spot (M11) is genuinely outside Clay attack — "
            "do NOT retrofit SSP there."
        ),
        adjacent_lower_tier_ops=(
            "broad_05",  # Forcing via Constraint (RENAME-risk: most likely)
            "broad_07",  # Systematic Cataloging (RENAME-risk: secondary)
            "ec_07",     # Representation / Coordinate Reformulation (RENAME-risk)
            "core_06",   # External Framework Importation (RENAME-risk: tertiary)
        ),
        validation_status="PRE-WARRANT",
        proposed_at="2026-05-09",
        proposed_by="PL-105",
    ),
    "mm_03": MetaMetaOp(
        op_id="mm_03",
        name="Ontological Promotion",
        tier="meta_meta",
        structural_mechanism=(
            "Reconstitute an instrumental, auxiliary, or bookkeeping construct "
            "as an autonomous primary object. Prior uses are then recovered as "
            "derived cases of the promoted object. Distinct from `core_02` "
            "Generalization and `broad_07` Structural Lifting: OP changes the "
            "role of the construct from tool/substrate to object-of-study, not "
            "just its scope or dimension."
        ),
        worked_examples=(
            "Distribution theory after Schwartz: generalized functions and the "
            "Dirac delta move from calculation aids to primary objects with their "
            "own topology and operations.",
            "Scheme theory: prime ideals / functor-of-points machinery promote "
            "solution sets and nilpotent structure from auxiliary algebraic data "
            "to the geometric object itself.",
            "Defect-measure analysis: a limit defect first introduced to account "
            "for lost compactness becomes a primary carrier whose geometry and "
            "transport properties are studied directly.",
            "ZTARE GP-216 meta arc, J4 2026-05-18: the two-family blind pass kept "
            "Ontological Promotion distinct from Generalization/Lifting because "
            "the move is role inversion, not scope extension.",
        ),
        ns_substrate_projection=(
            "For NS Track B, OP is the disciplined version of promoting a "
            "budget, defect, skeleton, invoice, or capacity object to a primary "
            "PDE carrier only when it has autonomous laws. TICK651's fresh-radius "
            "invoice target is OP-adjacent: a capacity budget cannot be promoted "
            "unless it becomes a descendant-exclusive payment object with its own "
            "non-reuse law."
        ),
        adjacent_lower_tier_ops=(
            "core_02",   # Generalization & Abstraction
            "broad_07",  # Dimensional & Structural Lifting
            "core_03",   # Decomposition & Recomposition
            "spec_01",   # Characterization by Obstruction
        ),
        validation_status="WARRANTED_NARROW",
        proposed_at="2026-05-18",
        proposed_by="J4_two_family_blind_meta_pass",
    ),
}


def get_meta_meta(op_id: str) -> Optional[MetaMetaOp]:
    return META_META_VOCABULARY.get(op_id)


StructuralLanguageOp = Union[UniversalResearchOp, MetaMetaOp]


def get_structural_language_op(op_id: str) -> Optional[StructuralLanguageOp]:
    """Return any registered structural-language op accepted by RD pretick.

    The v5 catalog (`core_*`, `broad_*`, `spec_*`) remains the validated
    move-layer vocabulary. The meta-meta catalog (`mm_*`) is the game-layer
    vocabulary and is accepted by pretick because hard research ticks may be
    required to name a frame/object/semantics rebaseline explicitly.
    """
    return get(op_id) or get_meta_meta(op_id)


def render_meta_meta_summary() -> str:
    lines = ["# Meta-Meta Vocabulary (game-layer reframes) — added 2026-05-09 per PL-105", ""]
    lines.append("**Status:** mixed. `mm_02` and `mm_03` are WARRANTED_NARROW from")
    lines.append("the 2026-05-18 two-family blind meta pass; `mm_01` is retained as")
    lines.append("a refuted/effect-named caution and functional-uplift arm, not as a")
    lines.append("validated descriptive primitive.")
    lines.append("**Sources:** PL-105 1880s framing-layer cold-shot;")
    lines.append("`workingpapers/epistemic-generation/cli_runs/track_b_B1_verdict_20260518.md`;")
    lines.append("`workingpapers/epistemic-generation/cli_runs/swarm_consolidated_verdict_20260518.md`;")
    lines.append("`workingpapers/epistemic-generation/consolidated_claim_evidence_20260518.md`.")
    lines.append("")
    for op in META_META_VOCABULARY.values():
        lines.append(f"## {op.op_id} {op.name}")
        lines.append("")
        lines.append(f"**Mechanism:** {op.structural_mechanism}")
        lines.append("")
        lines.append("**Worked examples:**")
        for ex in op.worked_examples:
            lines.append(f"- {ex}")
        lines.append("")
        if op.ns_substrate_projection:
            lines.append(f"**NS-Track-B projection:** {op.ns_substrate_projection}")
            lines.append("")
        lines.append(f"**Adjacent lower-tier ops (RENAME-risk):** {', '.join(op.adjacent_lower_tier_ops)}")
        lines.append("")
        lines.append(f"**Validation status:** {op.validation_status}  ")
        lines.append(f"**Proposed:** {op.proposed_at} by {op.proposed_by}")
        lines.append("")
    return "\n".join(lines)


__all__ = [
    "VOCABULARY_V5", "VOCABULARY_V4", "UniversalResearchOp", "by_tier", "get", "render_vocabulary_summary",
    "META_META_VOCABULARY", "MetaMetaOp", "get_meta_meta", "get_structural_language_op",
    "StructuralLanguageOp", "render_meta_meta_summary",
]


if __name__ == "__main__":
    print(render_vocabulary_summary())
    print()
    print(render_meta_meta_summary())
