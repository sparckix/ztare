"""GP-219 — estimate-craft receipt vocabulary (PDE-origin + portable candidates).

Companion to `universal_research_ops.py` (GP-216 v5). It began as a
PDE-native estimate-craft vocabulary, but the epistemic-generation audit found
some receipt forms outside PDE. Keep the legacy module name for compatibility;
use `portable_receipt_fields` and `portability_status` for general-purpose
routing.

Phase 1 mining: 13 PDE-native moves from analysis_pde paper +
30 NS Track B F-rows. 6 proto-ops (A-F) clustered.
Phase 2 cross-walk: 3 additional papers; Candidate G surfaced
(Representation/Coordinate Reformulation) as likely v5-tier (universal
across PDE+NT+combinatorics) — recommended for paper-5b post-publication
addition as `core_08`.

# Vocabulary

PDE estimate-craft ops + one v5-tier candidate:

  pec_a  Auxiliary Comparison Object Construction
  pec_b  Regime / Class Scoping
  pec_c  Quantitative Threshold Dichotomy
  pec_d  Limit-Passage Property Inheritance
  pec_e  Sharpness / Failure-Witness Construction
  pec_f  Proof-Surface Compression  [provisional — NS-heavy]
  pec_h  Distribution / Tail Upgrade
  pec_i  Nonadaptive Source-Selection Receipt
  pec_j  Same-Carrier Packing / No-Reuse Injection Receipt
  pec_k  Phase-Space Packet Ownership Receipt
  pec_l  Symbol / Cancellation Coercivity Audit
  cand_g Representation / Coordinate Reformulation [v5-tier candidate]

# Honest scope

- Proto-op F (Compression) is provisional — strong on NS, weak on PDE
  paper. May be NS-substrate-specific or research-management rather
  than mathematical. Phase 3 cross-paper test required before promotion.
- Proto-op A vs C boundary fragile (auxiliary object that produces
  dichotomy). Watch for collapse under future cross-walks.
- Proto-op A vs E boundary fragile (sharpness witness IS an auxiliary
  object). Distinguished by whether the construction argues FOR the
  theorem (A) or AGAINST it to scope it (E).
- Candidate G is v5-tier per Phase 2 evidence (14 instances across
  7 papers spanning PDE + NT + combinatorics) — should likely move
  to `universal_research_ops.py` as `core_08` after paper 5b ships.

# Validation references

- Phase 1 source: `projects/ztare_on_ztare/workspace/gp219_pde_estimate_craft/proto_vocabulary_phase1.md`
- Phase 2 cross-walk: `projects/ztare_on_ztare/workspace/gp219_pde_estimate_craft/g_validation/`
- Seam: `research_areas/private/seams/engine/GP-219_pde_estimate_craft_sister_vocabulary.md`
- Joint v5 + GP-219 coverage: ~95% on fresh PDE+NT corpus
- Three deterministic gates already shipped (per RD mandate v1.22+):
    - `src/ztare/gates/auxiliary_object_declaration_gate.py` (mechanizes pec_a)
    - `src/ztare/gates/threshold_dichotomy_branch_coverage_gate.py` (mechanizes pec_c)
    - `src/ztare/gates/limit_passage_inheritance_lemma_gate.py` (mechanizes pec_d)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class PDEEstimateCraftOp:
    op_id: str
    name: str
    tier: str  # "proto" | "v5_candidate"
    structural_mechanism: str
    distinct_from_v5_because: str
    instantiation_examples: tuple[str, ...]
    gate_mechanization: Optional[str]  # path to deterministic gate if shipped
    provisional: bool = False
    boundary_collapse_risk: Optional[str] = None
    portability_status: str = "pde_origin"
    portable_receipt_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class PDEWorkUnitTemplate:
    """Artifact shape required after a GP-219 PDE route is selected.

    These templates do not check mathematical truth. They define the minimum
    inspectable objects an RD agent must produce before ending a PDE turn with
    an open-gap verdict.
    """

    unit_type: str
    required_fields: tuple[str, ...]
    prompt: str


BASE_WORK_UNIT_TEMPLATES: dict[str, PDEWorkUnitTemplate] = {
    "estimate_derivation": PDEWorkUnitTemplate(
        unit_type="estimate_derivation",
        required_fields=(
            "target",
            "normalized_variables",
            "target_inequality",
            "terms",
            "proof_steps",
            "first_failed_line",
            "conclusion",
        ),
        prompt=(
            "Normalize variables, write the target inequality, decompose terms, "
            "run Holder/Sobolev/Bernstein/CZ/local-energy steps as applicable, "
            "and name the first line where the estimate closes or fails."
        ),
    ),
    "falsifier_packet": PDEWorkUnitTemplate(
        unit_type="falsifier_packet",
        required_fields=(
            "name",
            "amplitude",
            "support_volume",
            "frequency",
            "satisfies_hypotheses",
            "violates_conclusion",
            "kills",
            "survives",
        ),
        prompt=(
            "Build a hostile family with amplitude, support, frequency, sign or "
            "orientation, hypotheses satisfied, and conclusion violated."
        ),
    ),
    "literature_match": PDEWorkUnitTemplate(
        unit_type="literature_match",
        required_fields=(
            "theorem",
            "requires",
            "available",
            "verdict",
            "missing_field",
        ),
        prompt=(
            "Match a cited theorem field by field. Verdict must be MATCH, "
            "PARTIAL, or NO_MATCH."
        ),
    ),
    "smaller_theorem": PDEWorkUnitTemplate(
        unit_type="smaller_theorem",
        required_fields=(
            "statement",
            "smaller_than_target",
            "proof_obligation",
            "falsifier_class_excluded",
            "residual_normal_form",
        ),
        prompt=(
            "State the smaller theorem left after failed attempts and prove why "
            "it is smaller: fewer carriers, fewer branches, excluded packet, "
            "or lower-dimensional residual normal form."
        ),
    ),
    "positive_constructor_attempt": PDEWorkUnitTemplate(
        unit_type="positive_constructor_attempt",
        required_fields=(
            "source_law",
            "target_carrier",
            "bounded_or_selectable_variable",
            "constructor_map",
            "nearest_confuser",
            "first_failed_line_or_success",
            "conclusion",
        ),
        prompt=(
            "When a conditional source law plus bounded/selectable carrier is "
            "available, attempt the positive construction before adding another "
            "obstruction layer. State the source law, target carrier, selected "
            "variable, constructor map, nearest confuser, and the first line "
            "where the construction succeeds or fails."
        ),
    ),
}


PDE_EXECUTION_HINTS: dict[str, dict[str, Any]] = {
    "pec_h": {
        "name": "Distribution / Tail Upgrade",
        "required_units": ["estimate_derivation", "falsifier_packet"],
        "fields": [
            "average_quantity",
            "target_tail",
            "normalized_variable",
            "distribution_function",
            "layer_cake_identity",
            "bad_packet_tested",
            "threshold_where_estimate_fails",
        ],
    },
    "pec_j": {
        "name": "Same-Carrier Packing / No-Reuse",
        "required_units": ["estimate_derivation", "falsifier_packet"],
        "fields": [
            "carrier",
            "target_payment",
            "assignment_map",
            "overlap_bound",
            "monotone_reserve",
            "nested_reuse_packet",
        ],
    },
    "pec_l": {
        "name": "Symbol / Cancellation Coercivity Audit",
        "required_units": ["estimate_derivation", "falsifier_packet"],
        "fields": [
            "signed_identity",
            "positive_target",
            "symbol",
            "cancellation_set",
            "dangerous_interaction",
            "high_high_or_core_sheath_interaction",
            "coercive_remainder",
            "counterpacket_if_false",
        ],
    },
    "constructive_turn": {
        "name": "Conditional Source to Positive Constructor",
        "required_units": ["positive_constructor_attempt"],
        "fields": [
            "conditional_source_law",
            "target_carrier",
            "bounded_or_selectable_variable",
            "constructor_map",
            "nearest_confuser",
            "first_failed_line_or_success",
        ],
    },
}


VOCABULARY_GP219: List[PDEEstimateCraftOp] = [
    PDEEstimateCraftOp(
        op_id="pec_a",
        name="Auxiliary Comparison Object Construction",
        tier="proto",
        structural_mechanism=(
            "Build an explicit, hand-tailored auxiliary object (barrier, "
            "intertwiner, certificate, test function, charged observable) "
            "whose role is to be compared against the unknown solution to "
            "extract a specific bound or rule out a specific behavior. The "
            "object is engineered to have known analytic properties (decay "
            "rate, sign, PSD-ness) the original problem lacks, deployed "
            "locally so its properties transfer to the target via comparison."
        ),
        distinct_from_v5_because=(
            "v5 has no op for ad-hoc auxiliary-object construction; "
            "canonical_decomposition decomposes an existing object into "
            "known parts, while this op fabricates a new object from scratch "
            "with engineered properties."
        ),
        instantiation_examples=(
            "analysis_pde Lemma 2.14: cosh-based exponential majorant",
            "NS PHASE5ET: charged pressure-aware matrix intertwiners",
            "NS PHASE5GDGE-STATEPRICE-SOS: explicit SOS/PSD certificate",
        ),
        gate_mechanization="src/ztare/gates/auxiliary_object_declaration_gate.py",
        boundary_collapse_risk="overlap with pec_e (sharpness witness IS an auxiliary object)",
        portability_status="portable_candidate",
        portable_receipt_fields=(
            "target_problem",
            "engineered_auxiliary_object",
            "known_properties",
            "comparison_map",
            "transfer_condition",
            "failure_condition",
        ),
    ),
    PDEEstimateCraftOp(
        op_id="pec_b",
        name="Regime / Class Scoping",
        tier="proto",
        structural_mechanism=(
            "Restrict attention to a parameterized sub-regime of the "
            "original problem (bounded Morse index + λ → ∞, scalar-only "
            "Track B, fixed observable class, fixed topology) and "
            "explicitly declare the questions deferred outside that regime. "
            "Not a simplification by symmetry but a deliberate scope "
            "contract that determines which lemmas apply and which "
            "counterexamples are out of bounds."
        ),
        distinct_from_v5_because=(
            "v5's extremal_case_analysis picks worst/limiting cases inside "
            "a fixed problem; this op modifies the problem itself by "
            "carving out a sub-regime in which the rest of the analysis "
            "is valid."
        ),
        instantiation_examples=(
            "analysis_pde move #1: NLS family scoped to bounded Morse + λ_n→∞",
            "NS PHASE5ET: scoping to scalar-only Track B",
            "NS PHASE5FM-BRANCHGRID: Track B as fixed seven-branch grid",
        ),
        gate_mechanization=None,
        portability_status="portable_candidate",
        portable_receipt_fields=(
            "original_problem",
            "scoped_regime_or_class",
            "included_cases",
            "excluded_or_deferred_cases",
            "lemmas_enabled_by_scope",
            "scope_breaker",
        ),
    ),
    PDEEstimateCraftOp(
        op_id="pec_c",
        name="Quantitative Threshold Dichotomy",
        tier="proto",
        structural_mechanism=(
            "Prove that some local quantity must either exceed a fixed "
            "positive threshold OR force a strong degeneracy on a "
            "structural neighborhood (vanishing on whole edges, collapse "
            "to null route, payoff dilution). Converts a continuous "
            "unknown into a binary alternative driving downstream "
            "blow-up alternatives or no-survivor verdicts."
        ),
        distinct_from_v5_because=(
            "v5's local_to_global_inference pieces local facts into a "
            "global conclusion additively; this op produces a forced "
            "binary at the local level that prunes the search space."
        ),
        instantiation_examples=(
            "analysis_pde Lemma 3.1: local max ≥ height OR vanishing-on-edges",
            "NS PHASE5EYEZ-STATEPRICE: exceed wall OR collapse to null",
            "NS PHASE5GB-LOWHIGH-KINEMATIC: zero-deformation OR priced",
        ),
        gate_mechanization="src/ztare/gates/threshold_dichotomy_branch_coverage_gate.py",
    ),
    PDEEstimateCraftOp(
        op_id="pec_d",
        name="Limit-Passage Property Inheritance",
        tier="proto",
        structural_mechanism=(
            "Take a sequence (of solutions, profiles, finite prefixes, "
            "finite packets) for which uniform bounds and structural "
            "properties have been proven, and transfer those properties "
            "to the limit object via a named lower-semicontinuity / "
            "approximation / inheritance lemma. Makes the gap between "
            "'true on every finite member' and 'true on the infinite "
            "limit' the explicit theorem to be paid."
        ),
        distinct_from_v5_because=(
            "v5's iterative_refinement_loop describes successive "
            "improvement of a candidate; this op specifically transfers "
            "established finite-stage properties across a limit-taking "
            "boundary, with the limit-passage hypothesis named as the "
            "open obligation."
        ),
        instantiation_examples=(
            "analysis_pde Cor 2.10: limit profile inherits frequency bound",
            "NS PHASE5FDFE-LIMITPASS: blocked on profile-limit theorem",
            "NS PHASE5FZ-PROFILE-LIPSCHITZ-CLOSURE: Clay closure via two limit-passage theorems",
        ),
        gate_mechanization="src/ztare/gates/limit_passage_inheritance_lemma_gate.py",
    ),
    PDEEstimateCraftOp(
        op_id="pec_e",
        name="Sharpness / Failure-Witness Construction",
        tier="proto",
        structural_mechanism=(
            "Build a concrete object (counterexample graph, tadpole "
            "construction, candidate adversary, hostile packet class) "
            "whose role is to either witness sharpness of a stated "
            "bound OR demonstrate that a specific class of escapes does "
            "NOT exist after stress-testing. The object is engineered "
            "against the theorem statement; whether it succeeds or fails "
            "sharpens the scope of the claim."
        ),
        distinct_from_v5_because=(
            "v5's probabilistic_existence requires probabilistic / random "
            "construction; this op is deterministic engineering of either "
            "a sharpness-saturating example or a stress-test adversary, "
            "and the theorem-class includes 'no such object exists' as "
            "a valid outcome."
        ),
        instantiation_examples=(
            "analysis_pde move #16: four-star example sharpening",
            "NS PHASE5FJ-PREFIXAUDIT: dyadic finite-prefix profile stacking",
            "NS PHASE5GB-LOWHIGH-KINEMATIC: kinematic falsifier candidate",
        ),
        gate_mechanization=None,
        boundary_collapse_risk="overlap with pec_a (witness IS an auxiliary object; distinction is purpose)",
        portability_status="portable_candidate",
        portable_receipt_fields=(
            "claim_under_stress",
            "hostile_or_sharpness_object",
            "saturating_or_failing_feature",
            "stress_result",
            "claim_boundary_update",
            "next_falsifier",
        ),
    ),
    PDEEstimateCraftOp(
        op_id="pec_f",
        name="Proof-Surface Compression",
        tier="proto_demoted",  # Phase 3 cross-paper test 2026-05-06: 0/3 PDE papers
        structural_mechanism=(
            "After accumulated local results, restate the remaining open "
            "problem as a small fixed list of named analytic obligations. "
            "[DEMOTED 2026-05-06 per GP-219 Phase 3 cross-walk: appears "
            "in 0 of 3 fresh PDE papers (quasilinear elliptic, kinetic "
            "Boltzmann, dispersive Ricci soliton). Confirmed NS-substrate-"
            "specific or research-management move; not generic PDE "
            "estimate-craft. Use pec_b (Regime/Class Scoping) for the "
            "scoping-flavored aspect or treat as substrate-management "
            "metadata rather than mathematical operation.]"
        ),
        distinct_from_v5_because=(
            "[DEMOTED] Original distinction from canonical_decomposition "
            "stands at the NS-substrate level but doesn't generalize "
            "across PDE subfields. Cross-paper test failed."
        ),
        instantiation_examples=(
            "NS PHASE5FQ-PROFILE-SPINE: Track B → single profile-decomposition obligation",
            "NS PHASE5FT-CLAY-CLOSURE / 5FZ / 5GA: successive top-level obligation list compressions",
        ),
        gate_mechanization=None,
        provisional=True,
        boundary_collapse_risk="DEMOTED 2026-05-06 — NS-substrate-specific per Phase 3; treat as substrate-management metadata, not generic PDE op",
    ),
    PDEEstimateCraftOp(
        op_id="pec_h",
        name="Distribution / Tail Upgrade",
        tier="proto",
        structural_mechanism=(
            "Upgrade signed, averaged, integral, or quadratic-energy control "
            "into a local distribution estimate: weak-L^q tail, reverse "
            "Holder gain, level-set decay exponent, or anti-concentration "
            "bound on a specified positive part. Also covers the closely "
            "related upgrade from energy/dissipation currency to a critical "
            "same-carrier nonlinear source-square or source-Carleson budget. "
            "This names the theorem that "
            "prevents concentrated spikes from preserving the weaker average "
            "or moment while destroying the stronger production estimate."
        ),
        distinct_from_v5_because=(
            "v5 has no primitive for the PDE-specific promotion from "
            "mean/integral control to distribution-function control. This is "
            "not just threshold dichotomy (pec_c), because it must quantify "
            "the whole tail/level-set law; not just sharpness witness (pec_e), "
            "because the positive route is a theorem producing weak-L^q or "
            "reverse Holder control."
        ),
        instantiation_examples=(
            "NS TICK664: anti-twist signed-average control would need a local "
            "weak-L^q tail for the unshadowed Duhamel positive part",
            "De Giorgi production coefficient: q > 5/2 reverse Holder gives "
            "beta-positive level-set recursion",
            "CV/SQG-style drift closures: BMO or distribution-function control "
            "rather than scalar energy bookkeeping",
            "NS TICK668: annular Duhamel renewal needs a same-carrier critical "
            "source-square Carleson budget, not only Leray energy dissipation",
        ),
        gate_mechanization=None,
        boundary_collapse_risk=(
            "overlaps with pec_e when the tail upgrade is killed by a spike "
            "witness; keep pec_h for the positive theorem obligation and pec_e "
            "for the hostile witness"
        ),
    ),
    PDEEstimateCraftOp(
        op_id="pec_i",
        name="Nonadaptive Source-Selection Receipt",
        tier="proto",
        structural_mechanism=(
            "Prove that the source objects, event indices, stopping regions, "
            "gauges, windows, or schedules used by an estimate are selected "
            "from data available before the payoff/failure quantity is known. "
            "This is a filtration/stopping-time style receipt: the theorem "
            "must display fixed-before-payoff selection, no post-hoc tuning "
            "from the target sum, and compatibility with the carrier used by "
            "the later inequality."
        ),
        distinct_from_v5_because=(
            "v5 has routing language for anti-leakage and canonical forms, "
            "but no PDE-native primitive for proving that an analytic source "
            "selection is nonanticipative. This differs from pec_b because it "
            "does not merely scope a regime; it proves the selected objects "
            "are admissible before the estimate consumes them. It differs from "
            "pec_d because the issue is selection timing, not limit passage."
        ),
        instantiation_examples=(
            "NS TICK668: C7 route active tail/event schedule must be fixed "
            "before event payoff and not defined from realized radius sums",
            "Calderon-Zygmund pressure windows: gauge/window fixed before "
            "fresh-region pressure visibility is scored",
            "Stopping-time corona estimates: children/fresh regions selected "
            "before local defect or critical-increment accounting",
        ),
        gate_mechanization=None,
        boundary_collapse_risk=(
            "overlaps with pec_b when the selection is described as a regime; "
            "use pec_i only when the theorem must prove nonanticipative source "
            "selection or no post-hoc carrier tuning"
        ),
    ),
    PDEEstimateCraftOp(
        op_id="pec_j",
        name="Same-Carrier Packing / No-Reuse Injection Receipt",
        tier="proto",
        structural_mechanism=(
            "Prove that local lower payments are injected into a fresh carrier "
            "budget on the same analytic object, with disjointness or bounded "
            "overlap strong enough to prevent the same capacity packet from "
            "being billed repeatedly. The receipt must display the source "
            "carrier, target payments, assignment/injection or monotone reserve "
            "map, overlap bound, and finite prefix/global budget."
        ),
        distinct_from_v5_because=(
            "v5 has single-spend and anti-leakage routing language, but not "
            "the PDE-native theorem shape that converts local bad-scale "
            "payments into a fresh same-carrier packing budget. This differs "
            "from pec_i because selection timing can be nonadaptive while the "
            "capacity packet is still reused; pec_j proves the no-reuse "
            "packing/injection itself."
        ),
        instantiation_examples=(
            "NS TICK668: selected C7 bad nodes need fresh annular capacity "
            "assigned on the same residual-fresh carrier, with no descendant "
            "capacity rebilling",
            "Corona decompositions: stopping children must charge disjoint or "
            "bounded-overlap tents rather than one ancestor packet",
            "Carleson packing estimates: local lower payments inject into a "
            "finite measure/budget without reusing the same tile mass",
        ),
        gate_mechanization="src/ztare/gates/same_carrier_packing_gate.py",
        boundary_collapse_risk=(
            "overlaps with the single-spend audit when used as a checklist; "
            "use pec_j only when the theorem must prove the same-carrier "
            "packing/no-reuse injection or monotone reserve drop"
        ),
    ),
    PDEEstimateCraftOp(
        op_id="pec_k",
        name="Phase-Space Packet Ownership Receipt",
        tier="proto",
        structural_mechanism=(
            "Prove that selected events are assigned to concrete phase-space "
            "or material packets by a pre-payoff owner map, and that the owner "
            "preimages have a numerical packing/multiplicity bound strong "
            "enough to turn pointwise event payments into finite prefix "
            "budgets. The receipt must display event-to-packet ownership, "
            "support/band/material compatibility, full output-scale packet "
            "eligibility rather than reusable factor/catalyst ownership, "
            "pointwise payment, bounded global selected-tree preimage or "
            "equivalent prefix inequality, finite atom budget, and "
            "inherited-or-fresh routing for descendants."
        ),
        distinct_from_v5_because=(
            "v5 can route source selection and no-reuse language, but not "
            "the PDE/microlocal theorem shape that an event owns a specific "
            "packet/tile/tube and that owner multiplicity is numerically "
            "controlled. This differs from pec_i because timing can be valid "
            "while the same packet is reused; it differs from pec_j because "
            "same-carrier packing may be true only after a separate "
            "phase-space owner map and preimage bound are proved."
        ),
        instantiation_examples=(
            "NS TICK668: selected residual-fresh C7 events need pre-payoff "
            "annular corona-Duhamel owner atoms with a global selected-tree "
            "multiplicity/prefix receipt",
            "Paraproduct estimates: bad events own Littlewood-Paley/Bony "
            "tiles whose preimages satisfy a Carleson embedding",
            "Lagrangian/material arguments: events own transported tubes "
            "with finite overlap before the downstream energy budget is spent",
        ),
        gate_mechanization="src/ztare/gates/owner_preimage_prefix_gate.py",
        boundary_collapse_risk=(
            "collapses to pec_j if the owner map is already implicit in the "
            "packing theorem; use pec_k when pointwise ownership and finite "
            "atom budget are present but owner-preimage multiplicity or "
            "factor-vs-output-packet eligibility is the actual missing "
            "estimate"
        ),
    ),
    PDEEstimateCraftOp(
        op_id="pec_l",
        name="Symbol / Cancellation Coercivity Audit",
        tier="proto",
        structural_mechanism=(
            "When an argument invokes skew-symmetry, null-form structure, "
            "projection cancellation, commutator cancellation, or oscillatory "
            "sign cancellation, prove that the cancellation survives in the "
            "exact positive/coercive quantity being estimated. The receipt "
            "must display the bilinear/multilinear symbol or tested identity, "
            "the positive target norm or measure, the dangerous interactions "
            "where the symbol must vanish or gain, and the signed-to-positive "
            "exchange theorem if the target is not signed."
        ),
        distinct_from_v5_because=(
            "v5 can route invariance or representation changes, but not the "
            "PDE/harmonic-analysis theorem shape that a signed cancellation "
            "or symbol identity yields coercive control of a positive target. "
            "This differs from pec_h because tail/source upgrades may be "
            "purely measure-theoretic; pec_l is about whether the claimed "
            "symbolic cancellation applies to the target norm after squaring, "
            "projection, localization, or packet selection."
        ),
        instantiation_examples=(
            "NS TICK668: energy skew-symmetry after testing against velocity "
            "does not control the positive source square of P_N div(u_N tensor u_N)",
            "Null-form estimates: high-high interactions must have genuine "
            "symbol vanishing or angular gain before an L2 source estimate is claimed",
            "Commutator methods: a signed commutator identity cannot be used "
            "as a positive Carleson measure without a coercive remainder theorem",
        ),
        gate_mechanization=None,
        boundary_collapse_risk=(
            "overlaps with cand_g when a representation change exposes the "
            "symbol; keep pec_l for the audit that the cancellation actually "
            "pays the positive/coercive target"
        ),
    ),
    PDEEstimateCraftOp(
        op_id="cand_g",
        name="Representation / Coordinate Reformulation",
        tier="v5_candidate",
        structural_mechanism=(
            "Reformulate the same problem in a conjugate / rescaled / "
            "principal-object-swapped frame WITHOUT crossing formal-system "
            "boundary. Includes coordinate change, conjugation by a "
            "well-chosen invertible operator, dimensionalization swap, "
            "or change of unknown."
        ),
        distinct_from_v5_because=(
            "Distinct from core_01 (no domain crossing — same problem "
            "different frame) and from proto-op pec_a (no new object "
            "created — existing problem re-expressed). Likely v5-tier "
            "(universal across PDE + NT + combinatorics per 14 instances "
            "across 7 papers, GP-219 Phase 2 cross-walk 2026-05-05). "
            "Recommended for paper-5b post-publication addition as "
            "`core_08` in universal_research_ops.py."
        ),
        instantiation_examples=(
            "GP-219 Phase 2 g_validation/2605.01646.json (PDE)",
            "GP-219 Phase 2 g_validation/2605.02540.json (NT)",
            "GP-219 Phase 2 g_validation/2605.02612.json (combinatorics)",
        ),
        gate_mechanization=None,
        portability_status="v5_candidate_portable",
        portable_receipt_fields=(
            "original_representation",
            "new_representation",
            "invariant_content",
            "translation_rule",
            "disagreement_witness",
            "decision_consequence",
        ),
    ),
]


# Lookup helpers (same shape as universal_research_ops.py)
by_id: Dict[str, PDEEstimateCraftOp] = {op.op_id: op for op in VOCABULARY_GP219}


def get(op_id: str) -> Optional[PDEEstimateCraftOp]:
    """Look up an op by id (e.g. 'pec_a')."""
    return by_id.get(op_id)


def by_tier(tier: str) -> List[PDEEstimateCraftOp]:
    """List ops by tier ('proto' | 'v5_candidate')."""
    return [op for op in VOCABULARY_GP219 if op.tier == tier]


def deployable_gates() -> List[PDEEstimateCraftOp]:
    """List ops with a shipped deterministic gate."""
    return [op for op in VOCABULARY_GP219 if op.gate_mechanization]


def portable_receipt_candidates() -> List[PDEEstimateCraftOp]:
    """List estimate-craft receipts treated as portable candidates."""
    return [
        op for op in VOCABULARY_GP219
        if op.portability_status in {
            "portable_candidate",
            "v5_candidate_portable",
        }
    ]


def execution_template_for_ops(op_ids: list[str]) -> dict[str, Any]:
    """Return the PDE-work contract selected by routed GP-219 ops."""
    hints = {
        op_id: PDE_EXECUTION_HINTS[op_id]
        for op_id in op_ids
        if op_id in PDE_EXECUTION_HINTS
    }
    return {
        "base_work_unit_templates": {
            key: asdict(value)
            for key, value in BASE_WORK_UNIT_TEMPLATES.items()
        },
        "pde_execution_hints": hints,
        "default_required_terminal_work": {
            "estimate_derivation_min": 2,
            "falsifier_packet_min": 1,
            "requires_one_of": ["smaller_theorem", "literature_match"],
        },
        "terminal_rule": (
            "MISSING_HYPOTHESIS / OPEN / NO_CLOSE is invalid before the "
            "required PDE work units are present."
        ),
    }


PORTABLE_RECEIPT_OVERLAP_MAP = {
    "pec_a": {
        "nearest_universal_ops": ("core_03", "broad_08"),
        "overlap_status": "known_overlap_but_receipt_extra",
        "overlap_summary": (
            "Universal ops can route decomposition or constraints, while the "
            "portable receipt asks for the engineered auxiliary object, its "
            "known properties, comparison map, transfer condition, and failure "
            "condition."
        ),
        "promotion_rule": (
            "Keep as portable receipt schema unless cross-domain evidence shows "
            "that auxiliary-object construction changes generated artifacts "
            "beyond what core_03/broad_08 plus schema fields already cover."
        ),
    },
    "pec_b": {
        "nearest_universal_ops": ("core_05", "broad_05"),
        "overlap_status": "known_overlap_but_receipt_extra",
        "overlap_summary": (
            "Universal ops name invariance or extremal restriction, while the "
            "portable receipt requires an explicit scope contract with included "
            "cases, excluded/deferred cases, enabled lemmas, and scope breaker."
        ),
        "promotion_rule": (
            "Keep as receipt schema unless tests show scope contracts cannot be "
            "recovered from core_05/broad_05 plus claim-boundary fields."
        ),
    },
    "pec_e": {
        "nearest_universal_ops": ("broad_05", "spec_01"),
        "overlap_status": "boundary_ambiguous",
        "overlap_summary": (
            "Extremal/obstruction language overlaps strongly. The receipt adds "
            "a concrete hostile or sharpness object, stress result, and claim "
            "boundary update. Research_log V65 found a real ambiguity with "
            "cand_g when a witness is presented through a representation change."
        ),
        "promotion_rule": (
            "Do not promote from receipt to op without a consequence endpoint "
            "that separates hostile-witness generation from generic extremal "
            "or obstruction routing."
        ),
    },
    "cand_g": {
        "nearest_universal_ops": ("core_01", "core_05", "core_06"),
        "overlap_status": "v5_candidate_portable",
        "overlap_summary": (
            "Problem reformulation and invariance overlap. Candidate G is "
            "narrower: same formal system, representation/coordinate/frame "
            "change, invariant content preserved, and disagreement witness "
            "named."
        ),
        "promotion_rule": (
            "Candidate for universal promotion only after a held-out test shows "
            "same-system representation reformulation is repeatedly missed or "
            "misrouted by core_01/core_05/core_06."
        ),
    },
}


def render_vocabulary_summary() -> str:
    """One-screen narration for advisor turns."""
    lines = ["GP-219 PDE estimate-craft vocabulary:"]
    for op in VOCABULARY_GP219:
        marker = ""
        if op.provisional:
            marker += " [provisional]"
        if op.gate_mechanization:
            marker += " [gate-shipped]"
        lines.append(f"  {op.op_id}  {op.name}{marker}")
    return "\n".join(lines)


# Cross-vocabulary mapping to v5 core ops (for joint coverage analysis)
# Each PDE op's nearest v5 neighbor + boundary note
CROSS_VOCABULARY_MAPPING = {
    "pec_a": {"v5_neighbor": "core_03 Decomposition (negative)",
              "boundary": "v5 has NO ad-hoc auxiliary-object construction op"},
    "pec_b": {"v5_neighbor": "core_05 Canonical Form / Invariance",
              "boundary": "extremal picks worst-case IN problem; pec_b changes problem boundary"},
    "pec_c": {"v5_neighbor": "core_04 Local-to-Global Assembly",
              "boundary": "local-to-global is additive piecing; pec_c is forced local binary"},
    "pec_d": {"v5_neighbor": "core_02 Iterative Refinement Loop",
              "boundary": "iterative refines candidate; pec_d transfers across limit boundary"},
    "pec_e": {"v5_neighbor": "Probabilistic existence (negative)",
              "boundary": "v5 prob-existence requires randomness; pec_e is deterministic engineering"},
    "pec_f": {"v5_neighbor": "core_03 Decomposition (objects vs proofs)",
              "boundary": "decomposition acts on objects; pec_f compresses proof surface"},
    "pec_h": {"v5_neighbor": "broad_02 Quantitative Invariant / Measure",
              "boundary": "v5 names quantitative control but not the PDE-specific upgrade from average/moment control to distribution-tail or reverse-Holder control"},
    "pec_i": {"v5_neighbor": "core_05 Canonical Form / Invariance",
              "boundary": "v5 can route anti-leakage, but pec_i is the PDE theorem that selected analytic sources are fixed before the payoff/failure quantity"},
    "pec_j": {"v5_neighbor": "core_04 Local-to-Global Assembly",
              "boundary": "v5 can route local-to-global budget assembly, but pec_j is the PDE theorem that local payments inject into the same fresh carrier without reuse"},
    "pec_k": {"v5_neighbor": "core_04 Local-to-Global Assembly",
              "boundary": "v5 can route local-to-global packet assembly, but pec_k is the PDE theorem that selected events own concrete phase-space/material packets with numerically bounded owner preimages"},
    "pec_l": {"v5_neighbor": "core_05 Canonical Form / Invariance",
              "boundary": "v5 can notice invariance/cancellation language, but pec_l is the PDE/harmonic-analysis audit that signed symbol cancellation yields the advertised positive coercive estimate"},
    "cand_g": {"v5_neighbor": "core_01 Problem Reformulation",
               "boundary": "core_01 may cross domain; cand_g stays in same formal system"},
}
