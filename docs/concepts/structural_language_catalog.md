---
description: "The mathematical-content move catalog (PDE craft ops + universal v5 ops + op tiers) the Research Director composes during pre-tick."
---

# Structural language catalog

Generated from Python registries. Do not hand-edit this file. Run `python scripts/public/control/render_structural_language_catalog.py` after changing the registries.

Purpose: a readable public concept surface for the universal research language, the theory-builder/problem-solver split, meta-meta reframes, and [GP-219](../../research_areas/seams/engine/meta/GP-219_pde_estimate_craft_sister_vocabulary.md) PDE estimate-craft language. The `.py` registries remain canonical because tick briefs, gates, and classifiers import them.

## Use rule

Pattern catalog = how to move next. Structural language = what mechanism the move found or repaired. Pretick may require either move-layer v5 ops or game-layer `mm_*` ops when the tick changes what counts as the object, state, or admissible frame. Closure artifacts should include `structural_language_fingerprint` with universal ops, TB/PS culture, PDE ops or `not_applicable`, evidence pointer, and next-move effect.

# Universal Research Operations Vocabulary v5 (paper 5b, [GP-216](../../research_areas/seams/engine/meta/GP-216_theory_building_operations_seam.md))

*Status:* descriptive (not generative), empirically generic across structural-research corpora
*Source:* mined from 64 arcs across 8 mathematical subfields (1214 moves)
*OOD coverage:* business held-out 57.9% shared+broadly; post-cutoff 2026 papers (sparse) 75.2% shared+broadly

## Shared core, 6 ops in >=6 of 8 subfields
- core_01 Problem Reformulation & Reduction (8 subfields)
  - Mechanism: Replacing a problem with a structurally equivalent or logically connected surrogate to make it more tractable or to transfer properties like computational hardness.
  - Subfields: theory_building, additive_combinatorics, graph_theory, complexity_theory, geometric_flow_pde, logic_set_theory, algebraic_topology, applied_math
  - Aliases collapsed from v3 vocabulary: tb_03 Surrogate Problem Substitution, ps_03 Formal Equivalence Transfer
- core_02 Generalization & Abstraction (8 subfields)
  - Mechanism: Replacing a class of objects or a specific structure with a more encompassing one that relaxes constraints, thereby unifying disparate cases under a single framework.
  - Subfields: theory_building, additive_combinatorics, graph_theory, complexity_theory, geometric_flow_pde, logic_set_theory, algebraic_topology, applied_math
  - Aliases collapsed from v3 vocabulary: tb_01 Foundational Object Redefinition, tb_09 Systematic Vocabulary Lifting
- core_03 Decomposition & Recomposition (8 subfields)
  - Mechanism: Breaking a complex object or problem into simpler, manageable components, analyzing or solving them independently, and then reassembling the results.
  - Subfields: theory_building, additive_combinatorics, graph_theory, complexity_theory, geometric_flow_pde, logic_set_theory, algebraic_topology, applied_math
  - Aliases collapsed from v3 vocabulary: ps_01 Structural Partitioning, tb_08 Parameter Space Internalization
- core_04 Local-to-Global Assembly (8 subfields)
  - Mechanism: Constructing a global object or proving a global property by specifying local pieces and rules for how they cohere, often through gluing or integration.
  - Subfields: theory_building, additive_combinatorics, graph_theory, complexity_theory, geometric_flow_pde, logic_set_theory, algebraic_topology, applied_math
- core_05 Canonical Form & Invariance (7 subfields)
  - Mechanism: Identifying stable properties or unique representatives within equivalence classes to simplify analysis by eliminating redundant or superficial complexity.
  - Subfields: theory_building, additive_combinatorics, graph_theory, complexity_theory, geometric_flow_pde, algebraic_topology, applied_math
- core_06 Cross-Domain Translation (7 subfields)
  - Mechanism: Establishing a formal correspondence between two distinct conceptual domains, allowing methods and insights from one to be applied to the other.
  - Subfields: theory_building, additive_combinatorics, graph_theory, complexity_theory, geometric_flow_pde, logic_set_theory, algebraic_topology
  - Aliases collapsed from v3 vocabulary: tb_02 Cross-Domain Unification

## Broadly shared, 8 ops in 4-5 subfields
- broad_01 Iterative Refinement (5 subfields)
  - Mechanism: Progressively improving a solution or approximation through repeated application of a procedure that guarantees monotonic improvement of a key metric.
  - Subfields: additive_combinatorics, graph_theory, geometric_flow_pde, applied_math, theory_building
  - Aliases collapsed from v3 vocabulary: ps_02 Governed Iterative Refinement, ps_06 Proof by Estimate Chaining
- broad_02 Recursive Decomposition (5 subfields)
  - Mechanism: Solving a problem by repeatedly breaking it down into smaller, self-similar instances of the same problem until a trivial base case is reached.
  - Subfields: additive_combinatorics, graph_theory, complexity_theory, logic_set_theory, applied_math
  - Aliases collapsed from v3 vocabulary: ps_05 Induction on Structural Rank
- broad_03 Duality & Adversarial Framing (5 subfields)
  - Mechanism: Reframing a problem by constructing a corresponding dual problem or a strategic game whose solution provides insight into the original.
  - Subfields: graph_theory, complexity_theory, additive_combinatorics, algebraic_topology, applied_math
- broad_04 Layered Approximation & Convergence (4 subfields)
  - Mechanism: Constructing a solution as the limit of a sequence of simpler, staged approximations whose properties are analyzed at each step.
  - Subfields: theory_building, additive_combinatorics, geometric_flow_pde, algebraic_topology
- broad_05 Extremal Method (4 subfields)
  - Mechanism: Analyzing boundary, worst-case, or optimal examples to deduce properties that must hold for all instances within a class.
  - Subfields: additive_combinatorics, graph_theory, geometric_flow_pde, theory_building
  - Aliases collapsed from v3 vocabulary: tb_NEW_POLYA Strategic Specialization
- broad_06 Probabilistic & Stochastic Methods (4 subfields)
  - Mechanism: Using randomness, sampling, and expectation as computational tools to solve deterministic problems or to prove existence.
  - Subfields: additive_combinatorics, graph_theory, complexity_theory, applied_math
- broad_07 Dimensional & Structural Lifting (4 subfields)
  - Mechanism: Embedding a problem into a higher-dimensional or more abstract space where constraints are relaxed or new geometric or algebraic tools become available.
  - Subfields: additive_combinatorics, complexity_theory, algebraic_topology, theory_building
- broad_08 Constraint Imposition & Propagation (4 subfields)
  - Mechanism: Establishing a set of required conditions and deriving the necessary consequences, often forcing a unique structure or revealing a contradiction.
  - Subfields: theory_building, additive_combinatorics, geometric_flow_pde, logic_set_theory
  - Aliases collapsed from v3 vocabulary: tb_04 Constraint-Driven Solution Forcing

## Subfield-specific idioms, 4 peripheral ops
- spec_01 Characterization by Obstruction (1 subfields)
  - Mechanism: Defining a class of objects not by its internal properties but by the absence of a finite set of forbidden substructures or configurations.
  - Subfields: graph_theory
- spec_02 Internalization & Self-Reference (2 subfields)
  - Mechanism: Encoding a system's own structure or meta-properties within the system itself to construct statements about its own limits or behavior.
  - Subfields: logic_set_theory, complexity_theory
  - Aliases collapsed from v3 vocabulary: tb_NEW_HOF Diagonal Self-Application, tb_11 Limitative Theorem Construction
- spec_03 Axiomatization & Foundational Repair (2 subfields)
  - Mechanism: Establishing or fixing the ground rules of a formal system by explicitly enumerating a minimal set of generative principles to resolve paradoxes and ensure consistency.
  - Subfields: theory_building, logic_set_theory
  - Aliases collapsed from v3 vocabulary: tb_LAK1 Refutation-Driven Concept Revision, tb_LAK2 Proof-Analysis Under Counter-Example
- spec_04 Controlled Universe Extension (1 subfields)
  - Mechanism: Augmenting a logical or algebraic universe with new elements in a way that preserves existing axioms while forcing a specific independent proposition to be true or false.
  - Subfields: logic_set_theory


# Meta-Meta Vocabulary (game-layer reframes), added 2026-05-09 per PL-105

*Status:* mixed. `mm_02` and `mm_03` are WARRANTED_NARROW from
the 2026-05-18 two-family blind meta pass. `mm_01` is retained at
caution grade as a refuted/effect-named entry and functional-uplift
arm, below the validated-descriptive-primitive bar the others clear.
*Sources:* PL-105 1880s framing-layer cold-shot;
`workingpapers/epistemic-generation/cli_runs/track_b_B1_verdict_20260518.md`;
`workingpapers/epistemic-generation/cli_runs/swarm_consolidated_verdict_20260518.md`;
`workingpapers/epistemic-generation/consolidated_claim_evidence_20260518.md`.

## mm_01 Admissible-Criteria Rebaselining (ACR)

*Mechanism:* Redraw what counts as a legitimate object/solution/proof. The shift is at the membership boundary of the game itself: the new criterion is formalized as an interface (quantifier alternation, weak/test-function action, equivalence-class identification), the class is closed under a specified limit/completion, and the completions are elevated to PRIMARY objects of study. Distinct from `core_02 Generalization & Abstraction`, which extends a family within a fixed admissibility. ACR redraws admissibility itself.

*Worked examples:*
- Cantor 1874-1891: a 'completed infinite set' becomes an admissible mathematical object. Before Cantor: infinity is potential, sets are finite. After: completed infinities are primary, with cardinal arithmetic on them.
- Weierstrass 1860s-1880s: a 'proof of convergence' is regimented as an explicit ε-δ quantifier-alternation witness. Before: geometric/infinitesimal intuition counted. After: only quantifier-certified arguments do.
- Schwartz 1940s (Heaviside seed 1880s): a 'function' is admissible as a continuous linear functional on test-function space, with derivatives defined as weak (action-on-tests) operations. The Dirac δ, previously a heuristic, becomes a primary object.
- Caffarelli-Kohn-Nirenberg 1982 (NS-relevant): 'suitable weak solution' is the admissibility criterion that powers partial regularity. The interface is a local-energy inequality + div-free + L²_t-H¹_x. SWS-class is the primary solution-class for 3D NS regularity questions.
- Boltzmann/Gibbs 1877-1902: a 'physical state' is admissible as a probability measure on phase space. State-space is reset from points to measures.

*NS-Track-B projection:* Three live decisive instantiations on NS-Track-B: (i) Defect-calculus pivot (RD-BL): μ[u] := w*-lim Π_ℓ[u] is an ACR move BY CONSTRUCTION, the defect measure is elevated to a primary obstruction-to-regularity object with its own status. C-98 (Duchon-Robert echo) is what happens when the apparatus mislabels this as ec_04. (ii) Lorentz Strip re-charter (post-C-96): Lorentz-space membership L^{p,q} redefines what 'integrability' counts as for the smallness-class. Without ACR labeling the apparatus drifts into ec_02 regime-scoping framing and misses the admissibility-criterion shift. (iii) Bochner-Fejér extension of trilinear NS form (RD-AJ): the almost-periodic projector defines a new admissibility-class for the trilinear form on which stationary NS dynamics reduce. Partial ACR. Full ACR on stationary 3D NS still open.

*Adjacent lower-tier ops (RENAME-risk):* core_02, ec_04, ec_02, core_06

*Validation status:* PRE-WARRANT
*Proposed:* 2026-05-09 by PL-105

## mm_02 Structural-Semantics Pluralization (SSP)

*Mechanism:* Shift identity/truth from intended-content semantics to invariance under a specified transformation/morphism class. Redundant representational scaffolding (gauge, coordinates, frames, intended interpretations) is QUOTIENTED OUT of ontology; equivalence-classes ARE the objects. Multiple models are licensed simultaneously. Distinct from `broad_05 Forcing via Constraint`, which narrows an admissible class within a fixed semantics, SSP rebases what semantics counts. Distinct from `ec_07 Representation`, which rewrites in better coordinates, SSP demotes coordinates to representation.

*Worked examples:*
- Beltrami-Klein 1868-1872: 'geometry' is identified with the consistency of an axiom system + a model. Euclidean geometry is no longer uniquely compulsory. Multiple consistent geometries are simultaneously legitimate.
- Klein Erlangen 1872: a geometry IS its invariants under a transformation group. Coordinates and metrics are demoted to representational scaffolding. The group and its invariants ARE the geometric content.
- Maxwell-Hertz 1880s + SR/GR 1905-1915: physical states are equivalence classes under gauge / inertial-frame transformations. The ether (a privileged absolute frame) is removed not because it was empirically refuted, but because the SSP move quotienting out absolute frames removes its ontological role.
- Hilbert axiomatic method 1899: 'meaning' of a theory is any structure satisfying its axioms. Truth is invariance across all models (isomorphism-invariant validity).
- Topology-first identity 1880s-1895: 'same space' means homeomorphic. Metric structure is representational; topological invariants are constitutive.

*NS-Track-B projection:* Two live but weaker instantiations on NS-Track-B: (i) Galilean / scaling invariance as game-semantics: solutions u(x,t) and λu(λx,λ²t) ARE the same solution. Apparatus currently treats scaling as ec_02 regime-scoping. SSP labeling aligns with how 2026 PDE literature frames critical / sub-critical regimes (the equivalence-class is the object, scaling-orbit membership IS the regime). (ii) Transport Gap / Lord Kelvin falsifier (RD-BJ, C-92): tests whether apparatus-outputs are stable under the operator-scaffold transformation group, i.e., whether the apparatus has a scaffold-invariant identity. With SSP vocabulary, RD-BJ becomes literally an SSP-stability test on the apparatus itself, and the question sharpens beyond a vague over-fit concern. Effectivity blind-spot (M11) is genuinely outside Clay attack, do NOT retrofit SSP there.

*Adjacent lower-tier ops (RENAME-risk):* broad_05, broad_07, ec_07, core_06

*Validation status:* PRE-WARRANT
*Proposed:* 2026-05-09 by PL-105

## mm_03 Ontological Promotion

*Mechanism:* Reconstitute an instrumental, auxiliary, or bookkeeping construct as an autonomous primary object. Prior uses are then recovered as derived cases of the promoted object. Distinct from `core_02` Generalization and `broad_07` Structural Lifting: OP changes the role of the construct from tool/substrate to object-of-study, not just its scope or dimension.

*Worked examples:*
- Distribution theory after Schwartz: generalized functions and the Dirac delta move from calculation aids to primary objects with their own topology and operations.
- Scheme theory: prime ideals / functor-of-points machinery promote solution sets and nilpotent structure from auxiliary algebraic data to the geometric object itself.
- Defect-measure analysis: a limit defect first introduced to account for lost compactness becomes a primary carrier whose geometry and transport properties are studied directly.
- ZTARE [GP-216](../../research_areas/seams/engine/meta/GP-216_theory_building_operations_seam.md) meta arc, J4 2026-05-18: the two-family blind pass kept Ontological Promotion distinct from Generalization/Lifting because the move is role inversion, not scope extension.

*NS-Track-B projection:* For NS Track B, OP is the disciplined version of promoting a budget, defect, skeleton, invoice, or capacity object to a primary PDE carrier only when it has autonomous laws. TICK651's fresh-radius invoice target is OP-adjacent: a capacity budget cannot be promoted unless it becomes a descendant-exclusive payment object with its own non-reuse law.

*Adjacent lower-tier ops (RENAME-risk):* core_02, broad_07, core_03, spec_01

*Validation status:* WARRANTED_NARROW
*Proposed:* 2026-05-18 by J4_two_family_blind_meta_pass


# GP-216 Theory-Building Operations Vocabulary v3

*Status:* descriptive (not generative), ~58% h+m coverage on held-out arcs
*Source:* Gowers's *Two Cultures of Mathematics* category, operationalized
*Anti-claim:* this is NOT a meta-solver. ~40% of theory-building moves do not fit any op here.

## Core (4)
- tb_01 Foundational Object Redefinition [recognize-only]
  - Mechanism: Replace the object class the theory studies with a different class that exposes structure invisible in the original (variety→scheme; multivalued function→Riemann surface; commutative C*-algebra→noncommutative C*-algebra; set→type).
  - Arc examples: grothendieck_schemes, riemann_surfaces, connes_ncg, russell_zf
  - Novel residue: Ontological base replacement, the theory's subject matter is redefined (distinct from a parameter-level reframe, ZTARE category_switch).
  - Overlaps: ZTARE pivot.category_switch, ZTARE pivot.dimensional_shift, Polya generalize
- tb_02 Cross-Domain Unification [recognize-only]
  - Mechanism: Establish a non-trivial functorial correspondence between two previously-separate domains and use it to transport theorems across the bridge (Taniyama-Shimura; Galois groups ↔ field extensions; Gelfand-Naimark).
  - Arc examples: wiles_flt, galois_theory, connes_ncg
  - Novel residue: Rigorous functorial correspondence enabling theorem transport, distinct from mere analogy (Polya) or category switch (parameter-level).
  - Overlaps: Polya analogous_problem, ZTARE pivot.category_switch
- tb_08 Parameter Space Internalization [DEPLOYABLE]
  - Mechanism: Reify a parametric family of objects (one per parameter value) as a single first-class object of the theory. Generic-property and variation questions become internal (moduli spaces; Mazur deformation rings; Higgs bundles).
  - Arc examples: wiles_flt, grothendieck_schemes, scholze_perfectoid
  - Novel residue: Reification of parametric family as single object, distinct from mere generalization or dimensional shift (which add a dimension without internalizing the family-as-object).
  - Overlaps: ZTARE pivot.dimensional_shift, Polya generalize
- tb_09 Systematic Vocabulary Lifting [DEPLOYABLE]
  - Mechanism: Re-do an entire existing theory move-by-move inside a new framework, preserving each step's structural role (Lurie ∞-categorifying ordinary category theory; Connes redoing Riemannian geometry over noncommutative algebras).
  - Arc examples: lurie_htt, connes_ncg, scholze_perfectoid
  - Novel residue: Move-by-move preservation constraint, every proof step in the original must be faithfully re-enacted in the new framework. Distinct from category_switch (parameter-level) or generalize (heuristic).
  - Overlaps: ZTARE pivot.category_switch, Polya generalize

## Strong secondary (4)
- tb_03 Surrogate Problem Substitution [DEPLOYABLE]
  - Mechanism: Replace the original target with a sufficient-condition target whose proof formally entails the original (FLT via modularity of semistable elliptic curves; CH independence via forcing; halting via diagonal in universal machine).
  - Arc examples: wiles_flt, cohen_forcing, turing_universal_machine
  - Novel residue: Logical-entailment substitution, the surrogate's proof formally implies the original. Distinct from analogy (which only suggests) or work-backward (which retraces steps).
  - Overlaps: Polya analogous_problem, Polya work_backward, Polya vary_problem
- tb_04 Constraint-Driven Solution Forcing [recognize-only]
  - Mechanism: Demand that the answer satisfy a list of structural constraints (covariance, conservation, consistency, symmetry). Their simultaneous satisfaction progressively narrows the form to a unique solution (Einstein 1915 field equations; ZF axiomatization).
  - Arc examples: einstein_gr, russell_zf, ns_track_b_ztare
  - Novel residue: Constraint-intersection narrowing to unique solution, distinct from work-backward (reverse-engineering from goal) or fixed_point_scan (canonical-value search). Empirically present in 2/40 ZTARE cycles (Pass 8).
  - Overlaps: Polya work_backward, ZTARE pivot.fixed_point_scan, Tao negative_results
- tb_06 Tacit Pattern Formalization [DEPLOYABLE]
  - Mechanism: Take an already-functioning implicit working pattern and construct a formal apparatus (notation, axioms, definitions, gate) that makes the pattern's logic explicit, inspectable, and transferable (fluxion→derivative; intuitive symmetry→tensor calculus; descriptive scaling→fractal dimension; tacit verification trick→ZTARE gate).
  - Arc examples: newton_calculus, einstein_gr, mandelbrot_fractals, ns_track_b_ztare
  - Novel residue: Implicit-to-formal direction, taking tacit working practice UP into formal apparatus. Distinct from entropy_stripping (which moves abstract DOWN to observables) or anchor_proxy (binds abstract to readable observable). Empirically present in 4/40 ZTARE cycles (Pass 8), the most-instantiated theory-building op in ZTARE day-to-day work.
  - Overlaps: ZTARE pivot.entropy_stripping, Paper5 op5 anchor_proxy, Tao smell
- tb_NEW_POLYA Strategic Specialization [DEPLOYABLE]
  - Mechanism: Solve a deliberately-chosen special case whose solution actively breaks a structural barrier in the general problem. The special case is the decisive engine, not a stepping stone (Wiles's semistable elliptic curves; Newton's specific curves).
  - Arc examples: wiles_flt, newton_calculus, ns_track_b_ztare
  - Novel residue: central special case that breaks a structural barrier, distinct from generic Polya specialize (try a special case to gain insight). The special case in this op is selected because it carries the proof-engine for the general result.
  - Overlaps: Polya specialize, Polya generalize, Lakatos lemma_incorporation

## Reflexive-limitative (2)
- tb_NEW_HOF Diagonal Self-Application [recognize-only]
  - Mechanism: Apply a predicate defined over codes of statements to its own code. The predicate's domain (codes) and the predicate itself (a statement, hence codeable) collapse, producing a fixed point where syntax and semantics tangle (Gödel diagonal lemma; Cantor's diagonal; Kleene fixed-point; Quine quotation).
  - Arc examples: godel_incompleteness, turing_universal_machine, cohen_forcing
  - Novel residue: Level-collapse via predicate-applied-to-own-code, intensional, not extensional. Distinct from fixed_point_scan (which finds extensional fixed points f(x)=x without the syntactic-semantic tangle) and collision_exploit (output coincidence).
  - Overlaps: ZTARE pivot.fixed_point_scan, ZTARE pivot.collision_exploit
- tb_11 Limitative Theorem Construction [recognize-only]
  - Mechanism: Use the diagonal self-application of tb_NEW_HOF to derive a structural impossibility (incompleteness, undecidability, independence). Hofstadter's panel correction: tb_11 is the OUTCOME, tb_NEW_HOF is the move that produces it.
  - Arc examples: godel_incompleteness, turing_universal_machine, cohen_forcing
  - Novel residue: Diagonal as generative move for limitative result, distinct from negative_results (elimination of options) or inversion (what would destroy the hypothesis). The limitative theorem is consequent of the diagonal, not co-equal.
  - Overlaps: Tao negative_results, ZTARE pivot.inversion, ZTARE pivot.fixed_point_scan

## Lakatos-attributed (2, direct rediscovery; cite Lakatos)
- tb_LAK1 Refutation-Driven Concept Revision [DEPLOYABLE]
  - Mechanism: A concrete counter-example forces revision of the meaning of a core term in the theory; the concept stretches or restricts in response (Lakatos 1976: monster-barring, exception-barring; Russell's paradox forcing ZF separation axiom).
  - Arc examples: russell_zf
  - Novel residue: EMPTY, this op is a direct rediscovery of Lakatos's monster-barring + exception-barring. Cite Lakatos *Proofs and Refutations* (1976).
  - Overlaps: Lakatos monster_barring, Lakatos exception_barring
- tb_LAK2 Proof-Analysis Under Counter-Example [DEPLOYABLE]
  - Mechanism: When a proof fails on a counter-example, localize which sub-step failed and absorb the missing condition as an explicit lemma; the proof and the conditions co-evolve (Lakatos 1976: lemma-incorporation, the preferred dialectical operation).
  - Arc examples: wiles_flt
  - Novel residue: EMPTY, direct rediscovery of Lakatos's lemma-incorporation. Cite Lakatos *Proofs and Refutations* (1976).
  - Overlaps: Lakatos lemma_incorporation, Paper5 op2 controlling_claim_isolation


# Problem-Solving Sister Vocabulary v1 (paper 5b)

*Status:* descriptive (not generative), ~66% h+m coverage on own (PS) corpus, ~19% on theory-builder corpus
*Source:* mined from 8 Gowers/Tao-tradition problem-solver arcs
*Cross-corpus gap:* −46.8 pp own-corpus advantage (vs theory-builder vocabulary's −37.4 pp)

## Problem-Solver-Specific (3 ops, zero theory-builder instances)
- ps_02 Governed Iterative Refinement
  - Mechanism: An iterative process is proven to terminate by defining a scalar potential function that is guaranteed to improve monotonically at each step and is bounded by a fixed ceiling (Roth's density-increment iteration; Szemerédi's mean-square energy potential; Tao's entropy decrement).
  - Arc examples: roth_3ap, szemeredi_regularity, erdos_discrepancy, hales_jewett_polymath
  - Own corpus instances: 11, opposite corpus: 0
- ps_05 Induction on Structural Rank
  - Mechanism: A proof proceeds by induction or recursion on a complexity measure derived from a structural decomposition of the objects under study (Furstenberg's induction on tower height in the structure theorem; Ramsey induction on color/depth).
  - Arc examples: furstenberg_ergodic_szemeredi, ramsey_erdos_szekeres, hales_jewett_polymath
  - Own corpus instances: 4, opposite corpus: 0
- ps_06 Proof by Estimate Chaining
  - Mechanism: A conclusion is reached not by introducing new conceptual objects, but by establishing a chain of precise quantitative bounds on existing structures (Roth's Fourier-coefficient bounds chained to density-increment; Erdős's probabilistic method; Behrend's geometric counting; Erdős-Szekeres double-counting).
  - Arc examples: roth_3ap, behrend_construction, erdos_discrepancy, ramsey_erdos_szekeres, green_tao
  - Own corpus instances: 9, opposite corpus: 0

## Shared core (3 ops, non-zero in both corpora)
- ps_01 Structural Partitioning
  - Mechanism: An arbitrary object is decomposed into a canonical set of well-behaved (structured) and chaotic (pseudorandom) components to isolate complexity (Szemerédi's regularity partition; Furstenberg structure theorem; Green-Tao decomposition into structured + pseudorandom integers).
  - Arc examples: szemeredi_regularity, furstenberg_ergodic_szemeredi, green_tao, hales_jewett_polymath, erdos_discrepancy
  - Own corpus instances: 7, opposite corpus: 2
  - Overlaps: tb_06 Tacit Pattern Formalization (partial)
- ps_03 Formal Equivalence Transfer
  - Mechanism: A problem is translated into an equivalent form in a different mathematical domain, allowing the application of that domain's native tools and structures (Furstenberg's correspondence translating density-A into multiple-recurrence; Green-Tao transference principle; Behrend's lift to Z^d).
  - Arc examples: furstenberg_ergodic_szemeredi, green_tao, behrend_construction, erdos_discrepancy, hales_jewett_polymath, ramsey_erdos_szekeres
  - Own corpus instances: 16, opposite corpus: 7
  - Overlaps: tb_02 Cross-Domain Unification (strongest cross-cultural overlap)
- ps_04 Black-Box Theorem Application
  - Mechanism: A major theorem is treated as a self-contained module, and the primary work becomes proving that a new problem setting satisfies the theorem's preconditions (Green-Tao using Szemerédi as black-box; polymath1 reducing DHJ to Szemerédi-style increment in IP-rich sets).
  - Arc examples: green_tao, hales_jewett_polymath, erdos_discrepancy
  - Own corpus instances: 5, opposite corpus: 3
  - Overlaps: tb_NEW_POLYA Strategic Specialization, tb_03 Surrogate Problem Substitution


# Two Cultures of Mathematics, Operationalized, empirical summary

## 2×2 corpus-vocabulary cross-coverage

|  | TB corpus | PS corpus |
|---|---|---|
| **TB vocab (12 ops)** | **58.1%** | 20.7% |
| **PS vocab (6 ops)** | 19.1% | **65.9%** |

Average own-corpus advantage: 42.1 percentage points (symmetric in both directions)

## Per-op tier assignment (paper 5b §4.2)

- TB-specific (8): tb_04, tb_08, tb_09, tb_11, tb_LAK1, tb_LAK2, tb_NEW_HOF, tb_NEW_POLYA
- TB-mostly (2): tb_01, tb_02
- shared-core (5): ps_01, ps_03, ps_04, tb_03, tb_06
- PS-specific (3): ps_02, ps_05, ps_06

## Strongest cross-cultural pairs
- tb_02 ↔ ps_03, Cross-Domain Unification ↔ Formal Equivalence Transfer (strongest)
- tb_06 ↔ ps_01, Tacit Pattern Formalization ↔ Structural Partitioning (related)
- tb_03 ↔ ps_04, Surrogate Problem Substitution ↔ Black-Box Theorem Application (leverage moves)
- tb_NEW_POLYA ↔ ps_04, Strategic Specialization ↔ Black-Box Theorem Application (special-case leverage)

[GP-219](../../research_areas/seams/engine/meta/GP-219_pde_estimate_craft_sister_vocabulary.md) PDE estimate-craft vocabulary:
  pec_a  Auxiliary Comparison Object Construction [gate-shipped]
  pec_b  Regime / Class Scoping
  pec_c  Quantitative Threshold Dichotomy [gate-shipped]
  pec_d  Limit-Passage Property Inheritance [gate-shipped]
  pec_e  Sharpness / Failure-Witness Construction
  pec_f  Proof-Surface Compression [provisional]
  pec_h  Distribution / Tail Upgrade
  pec_i  Nonadaptive Source-Selection Receipt
  pec_j  Same-Carrier Packing / No-Reuse Injection Receipt [gate-shipped; upstream metric-covering receipt gate available]
  pec_k  Phase-Space Packet Ownership Receipt [gate-shipped]
  pec_l  Symbol / Cancellation Coercivity Audit
  cand_g  Representation / Coordinate Reformulation
