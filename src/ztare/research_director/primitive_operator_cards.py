"""Experimental operator cards for primitive-facing RD tests.

The universal research-op catalog is descriptive. This module exposes a smaller
execution surface for experiments: route a context to one compact operator card
with concrete output obligations.

This module is surfaced by ``rd_tick_brief.py`` as an experimental router.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Iterable

from ztare.common.kernel_action_schema import KernelActionSchema


REPO = Path(__file__).resolve().parents[3]
OUT_PATH = REPO / "analytics" / "public" / "queries" / "rd_operator_cards_experimental.json"
OPERATOR_CARD_ATLAS_PATH = REPO / "analytics" / "public" / "index" / "operator_card_atlas_embeddings.json"
OPERATOR_CARD_ATLAS_MANIFEST_PATH = REPO / "analytics" / "public" / "index" / "operator_card_atlas_manifest.json"


@dataclass(frozen=True)
class ObligationClass:
    class_id: str
    name: str
    trigger_terms: tuple[str, ...]
    owes: tuple[str, ...]
    falsifier: str
    evidence_basis: str
    score: float = 0.0
    matched_terms: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class OperatorCard:
    card_id: str
    name: str
    source_ops: tuple[str, ...]
    trigger_terms: tuple[str, ...]
    obligation_classes: tuple[str, ...]
    problem_classes: tuple[str, ...]
    entry_conditions: tuple[str, ...]
    steps: tuple[str, ...]
    required_output: tuple[str, ...]
    breaker: str
    stop_update_rule: str
    boundary: str
    disambiguators: tuple[str, ...] = field(default_factory=tuple)
    fine_handles: tuple[str, ...] = field(default_factory=tuple)
    required_schema_fields: tuple[str, ...] = field(default_factory=tuple)
    route_required_match_groups: tuple[tuple[str, ...], ...] = field(default_factory=tuple)
    score: float = 0.0
    matched_terms: tuple[str, ...] = field(default_factory=tuple)


OBLIGATION_CLASSES: tuple[ObligationClass, ...] = (
    ObligationClass(
        class_id="construct",
        name="Construct / Witness",
        trigger_terms=(
            "construct",
            "construction",
            "example",
            "witness",
            "candidate",
            "auxiliary object",
            "engineered object",
            "object",
            "build",
            "artifact",
            "counterexample",
            "define",
            "defined",
            "explicit",
            "algorithm",
            "procedure",
            "diagram",
            "diagrams",
            "family",
            "families",
            "seed",
            "exhibit",
            "certificate",
        ),
        owes=(
            "a concrete object or artifact",
            "the property it is meant to witness",
            "the check that would falsify the witness",
        ),
        falsifier="the object exists only as prose, or the claimed property is not checked on the object",
        evidence_basis="v128d: construct is one of the four higher-reliability obligation classes.",
    ),
    ObligationClass(
        class_id="transfer",
        name="Transfer / Representation",
        trigger_terms=(
            "transfer",
            "translation",
            "analogy",
            "isomorphism",
            "source",
            "target",
            "map",
            "mapping",
            "representation",
            "invariant",
            "projection",
            "lift",
            "bridge",
            "carry",
            "encode",
            "encodes",
            "encoding",
            "reformulate",
            "reformulates",
            "replace",
            "replacing",
            "convert",
            "converting",
            "interpretation",
            "reinterpret",
            "import",
            "imports",
            "redeploy",
            "reuse",
            "re-use",
            "template",
            "generalize",
            "generalized",
            "extend",
            "extends",
            "invariance",
            "equivalence",
            "preserve",
            "preserves",
            "substitution",
            "corollary",
            "package",
            "packages",
        ),
        owes=(
            "source object and target object",
            "the relation or invariant claimed to survive",
            "the target-side receipt or failure point",
        ),
        falsifier="the source-side move does not preserve the target-side invariant or lacks a target-side receipt",
        evidence_basis="v128d: transfer is reliable enough as a routing spine; fine labels remain retrieval handles.",
    ),
    ObligationClass(
        class_id="bound",
        name="Bound / Boundary",
        trigger_terms=(
            "bound",
            "estimate",
            "threshold",
            "criterion",
            "falsifier",
            "receipt",
            "claim",
            "overclaim",
            "boundary",
            "scope",
            "update",
            "evidence",
            "validation",
            "failure",
            "range",
            "lower bound",
            "upper bound",
            "control",
            "constraint",
            "constrain",
            "count",
            "counts",
            "asymptotic",
            "minimal",
            "separation",
            "distinguish",
            "distinguishes",
            "diagnostic",
            "metric",
            "metrics",
            "freshness",
            "sample",
            "sample-scoped",
            "yield",
            "portfolio",
            "roi",
            "share",
            "attention",
            "roadmap",
        ),
        owes=(
            "the claimed bound, boundary, or update",
            "the evidence that licenses it",
            "the pass/fail condition that blocks overclaim",
        ),
        falsifier="the boundary is asserted without a checkable pass/fail condition",
        evidence_basis="v128b/v128d: binary covered-vs-none and coarse obligations are more reliable than full/partial labels.",
    ),
    ObligationClass(
        class_id="decompose",
        name="Decompose / Cover Cases",
        trigger_terms=(
            "branch",
            "case",
            "split",
            "regime",
            "dichotomy",
            "coverage",
            "local",
            "global",
            "interface",
            "piece",
            "pieces",
            "strata",
            "layer",
            "aggregation",
            "restrict",
            "restricts",
            "isolate",
            "isolating",
            "sub-structure",
            "substructure",
            "canonical",
            "normal form",
            "reduce",
            "reduces",
            "reduction",
            "deleting",
            "induction",
            "survive",
            "survives",
            "parity",
            "corner case",
        ),
        owes=(
            "the component cases or local pieces",
            "the receipt owed by each component",
            "the aggregation rule and one unpaid-component breaker",
        ),
        falsifier="one branch, piece, or interface lacks a receipt but the aggregate claim proceeds",
        evidence_basis="v128d: decompose is a stable coarse obligation; branch/interface fine labels are nearest-confuser checks.",
    ),
)

GP219_PROMOTION_POLICY: dict[str, str] = {
    "pec_a": "freeze_as_portable_receipt_schema",
    "pec_b": "freeze_as_portable_receipt_schema",
    "pec_e": "freeze_as_portable_receipt_schema",
    "cand_g": "decline_core_promotion_merge_pressure_with_core_01",
}


CARDS: tuple[OperatorCard, ...] = (
    OperatorCard(
        card_id="OP-ECR-01",
        name="Evidence-Carrier Routing",
        source_ops=("core_01", "core_05", "core_07"),
        trigger_terms=(
            "proxy",
            "evidence carrier",
            "measurement",
            "readout",
            "claim update",
            "indirect evidence",
            "observable",
            "assay",
            "biopsy",
            "reproducibility",
            "endpoint",
            "receipt",
            "validation",
        ),
        obligation_classes=("bound",),
        problem_classes=("proxy_evidence", "measurement_validity", "claim_update"),
        entry_conditions=(
            "A claim depends on an indirect signal, proxy, benchmark, theorem import, or measurement.",
            "The next update is unsafe unless the evidence carrier is named and tested.",
        ),
        steps=(
            "Name the exact claim update.",
            "Name the evidence carrier that would license that update.",
            "State the receipt that makes the carrier admissible.",
            "State what observation invalidates the carrier.",
        ),
        required_output=(
            "4-row table: claim, carrier, receipt needed, failure condition.",
            "One falsifier sentence.",
            "One stop/update rule.",
            "One boundary sentence saying what cannot yet be claimed.",
        ),
        breaker="Find a case where the carrier is true but the claim update is false, or where the carrier is confounded.",
        stop_update_rule="Do not update the claim until the carrier receipt is present and the breaker has been checked.",
        boundary="This supports only the named claim update, not the broader thesis.",
    ),
    OperatorCard(
        card_id="OP-HRD-01",
        name="Hard Residual Research Contract",
        source_ops=("PATTERN-011", "PATTERN-025", "PATTERN-028"),
        trigger_terms=(
            "hard mathematical residual",
            "hard research residual",
            "hard residual",
            "proof frontier",
            "formal frontier",
            "research depth required",
            "recursive research required",
            "millennium problem",
            "millennium",
        ),
        obligation_classes=("decompose", "construct", "bound"),
        problem_classes=(
            "hard_mathematical_residual",
            "hard_research_residual",
            "proof_frontier",
            "formal_frontier",
            "research_depth_required",
            "recursive_research_required",
        ),
        entry_conditions=(
            "The task declares a hard residual, proof frontier, or recursive-depth requirement.",
            "A close would be unsafe without orientation, independent attack lanes, and a tool or primitive pass.",
        ),
        steps=(
            "Name the residual and the exact claim boundary.",
            "Produce a pencil/orientation artifact before formal or code edits.",
            "Select independent attack lanes and their kill conditions.",
            "Run the class-matched tool, primitive, graph, or workbench surface.",
            "Record the post-edit stress pass and remaining live vectors.",
        ),
        required_output=(
            "orientation artifact with eigenquestion, candidate theorem or obstruction, and kill condition.",
            "tool-or-primitive pass receipt or why_not for every class-matched tool skipped.",
            "artifact edit plus verification receipt.",
            "stop/update rule for recurrence, terminal negative, or next attack lane.",
        ),
        breaker="A prior manifest, graph basin, primitive, or amnesia surface shows this is only a renamed known gap.",
        stop_update_rule=(
            "Do not close or widen the claim until orientation, tool pass, artifact edit, "
            "and post-edit stress receipt are present."
        ),
        boundary="This routes hard research execution; it does not certify the mathematical or scientific claim.",
        disambiguators=(
            "Prefer this card when the task declares a hard residual or recursive-depth requirement.",
            "Prefer evidence-carrier routing for ordinary claim updates that only need a receipt.",
            "Prefer graph diagnostics when the immediate action is selecting or validating a graph carrier.",
        ),
        fine_handles=(
            "hard_residual_antipattern_guard: prior overlap, object identity, clean-proceed condition.",
            "orientation_artifact: eigenquestion, candidate theorem or obstruction, kill condition.",
            "stress_test_artifact: class-matched tool, primitive, graph, or workbench result.",
            "verification_artifact: compile/check/tool pass after artifact edit.",
        ),
        required_schema_fields=(
            "eigenquestion",
            "candidate_theorem_or_obstruction",
            "kill_condition",
            "tool_or_primitive",
            "residual_delta",
            "verification_command_or_gate",
            "remaining_failure_mode",
        ),
    ),
    OperatorCard(
        card_id="OP-PDE-01",
        name="PDE Estimate or Carrier Contract",
        source_ops=("GP-219", "PATTERN-028"),
        trigger_terms=(
            "area ns",
            "pde",
            "pde estimate",
            "pde workbench",
            "navier",
            "stokes",
            "navier stokes",
            "vorticity",
            "duhamel",
            "de giorgi",
            "carleson",
            "bkm",
            "prodi",
            "serrin",
            "conditional source law",
            "source law",
            "bounded carrier",
            "selectable carrier",
            "dimensional endpoint",
        ),
        obligation_classes=("bound", "construct", "decompose"),
        problem_classes=(
            "pde_estimate_or_carrier_residual",
            "pde_estimate",
            "pde_carrier_residual",
            "navier_stokes",
            "pde_workbench",
        ),
        entry_conditions=(
            "The task touches a PDE estimate, Navier-Stokes surface, or PDE carrier/source law.",
            "A claim update depends on a PDE workbench, dimensional check, endpoint check, or constructor attempt.",
        ),
        steps=(
            "Name the PDE estimate target and carrier.",
            "Run the relevant workbench, dimensional, endpoint, single-spend, or pi/Buckingham check.",
            "Attempt the estimate route or produce a sharp hostile witness.",
            "If a bounded/selectable carrier is visible, record the positive constructor attempt or the tested blocker.",
        ),
        required_output=(
            "PDE tool/gate receipt with estimate target and pass/fail result.",
            "theorem-or-counterexample attempt with proof layers and kill condition.",
            "constructor attempt receipt when source law and bounded/selectable carrier are visible.",
        ),
        breaker="The visible surface is not a PDE inequality/carrier problem, or the carrier is not selectable in the claimed regime.",
        stop_update_rule=(
            "Do not proceed on obstruction-only prose when a conditional source law and bounded/selectable "
            "carrier require a constructor attempt."
        ),
        boundary="This routes PDE estimate and carrier work; it does not replace the domain workbench or proof checker.",
        disambiguators=(
            "Prefer this card when the task area explicitly says ns or the goal names a PDE object.",
            "Reject this card for generic pressure, endpoint, or source words without a PDE context.",
            "Prefer portable estimate receipts when the receipt schema is reused outside PDE.",
        ),
        fine_handles=(
            "pde_tool_or_gate: workbench, dimensional, endpoint, single-spend, pi/Buckingham, or why_not.",
            "estimate_target: the exact inequality, carrier, or source law under test.",
            "constructor_map_or_why_not: positive turn when a bounded/selectable carrier is visible.",
        ),
        required_schema_fields=(
            "pde_tool_or_gate",
            "estimate_target",
            "passed_or_failed",
            "theorem_or_counterexample",
            "proof_layers",
            "conditional_source_law",
            "target_carrier",
            "constructor_map_or_why_not",
        ),
    ),
    OperatorCard(
        card_id="OP-BCG-01",
        name="Branch-Coverage Gate",
        source_ops=("core_03", "broad_08"),
        trigger_terms=(
            "case split",
            "branch",
            "coverage",
            "criterion",
            "threshold",
            "dichotomy",
            "regime",
            "parity",
            "scope",
            "criteria",
            "required",
            "readiness",
            "pathway",
            "manufacturing",
            "institutional",
            "strata",
            "layers",
            "competing bounds",
            "exception",
            "vertices",
            "vertex",
            "different limit problems",
            "coefficient vanishes",
            "separately",
            "non-self crossings",
            "non self crossings",
            "restricts",
        ),
        obligation_classes=("decompose", "bound"),
        problem_classes=("case_coverage", "threshold_dichotomy", "incomplete_branch"),
        entry_conditions=(
            "The conclusion depends on several cases, regimes, criteria, or branches.",
            "One unpaid branch would invalidate the aggregate conclusion.",
        ),
        steps=(
            "List every branch or criterion.",
            "Attach one receipt required for each branch.",
            "Mark the blocker that prevents aggregation.",
            "State the aggregation rule only after all branches are paid.",
        ),
        required_output=(
            "4-row branch table: branch, receipt, failure condition, aggregation status.",
            "One blocker rule.",
            "One unresolved-branch sentence.",
            "One global-claim boundary.",
        ),
        breaker="Exhibit one branch that lacks a receipt or violates the aggregation rule.",
        stop_update_rule="No aggregate claim until every branch has a receipt or is explicitly excluded.",
        boundary="The result is branch-conditioned unless the branch table is complete.",
        disambiguators=(
            "Prefer branch over interface when named cases, criteria, regimes, or excluded branches must be covered before aggregation.",
            "Prefer interface over branch when the visible risk is valid local pieces failing at a handoff.",
            "Prefer claim-boundary over branch when the broad claim may fail but a narrower survivor remains and no explicit branch checklist is named.",
        ),
    ),
    OperatorCard(
        card_id="OP-XFT-01",
        name="Analogy-to-Receipt Transfer Audit",
        source_ops=("core_06", "core_05"),
        trigger_terms=(
            "analogy",
            "isomorphism",
            "isomorphic",
            "translation",
            "transfer",
            "cross-domain",
            "de-anchor",
            "state pricing",
            "state price",
            "superhedging",
            "max-flow",
            "min-cut",
            "hall",
            "representation",
            "mapping",
            "invariant",
            "bridge",
            "source",
            "target",
            "preservation",
            "preserved",
            "transport",
            "reduction",
            "definition",
            "encoding",
            "encodings",
            "representative",
            "representatives",
            "obligations preserved",
            "transfer map",
            "failure breakpoints",
            "analogous",
            "reused",
            "toric",
            "lattice",
            "metalanguage",
            "primitive",
        ),
        obligation_classes=("transfer",),
        problem_classes=(
            "analogy_transfer",
            "domain_translation",
            "invariant_preservation",
            "receipt_forced_transfer",
        ),
        entry_conditions=(
            "A move is imported from another field, representation, or formal frame.",
            "The imported move must change the target-side evidence path, not just rename the residual.",
        ),
        steps=(
            "Name the source frame and target frame.",
            "Map source objects to target objects.",
            "List invariants that must survive transfer.",
            "Compile the analogy into a target-side receipt: theorem, gate, workbench check, formal field, or falsifier.",
            "Name the decision consequence: proceed, kill as recurrence, or narrow to a missing primitive.",
        ),
        required_output=(
            "4-row source-target mapping table.",
            "Invariant checklist.",
            "One target-side receipt or explicit missing-receipt slot.",
            "One transfer falsifier tied to the target domain.",
            "One decision rule saying what changes if the receipt passes or fails.",
            "One boundary sentence forbidding source-domain authority as evidence.",
            "For structural-semantics quotient rows, include equivalence-class id, accepted representation, invariant content, representation-local support, and disagreement witness fields.",
        ),
        breaker=(
            "Find an invariant that holds in the source frame but fails in the target frame, "
            "or show the mapped object lacks a target-side receipt."
        ),
        stop_update_rule=(
            "Do not spend another analogy step unless it produced a target-side receipt, "
            "a falsifier, or a narrowed missing primitive."
        ),
        boundary=(
            "The analogy is only a generator of target-side receipt obligations; "
            "it is never evidence for the imported claim by itself."
        ),
        disambiguators=(
            "Prefer source-target over branch when the bottleneck is invariant preservation across a map.",
            "Prefer branch over source-target when the visible restriction mainly excludes regimes or cases.",
            "Prefer interface over source-target when the source and target are local pieces whose compatibility, not invariant transport, is unpaid.",
        ),
        fine_handles=(
            "source_target_transfer: source object/claim, target counterpart, carried relation, preservation receipt, missing or risk-enlarging rows.",
            "structural_semantics_quotient: equivalence-class object, accepted representations, invariant content, per-representation support, disagreement witnesses, no privileged surface form.",
        ),
        required_schema_fields=(
            "source_frame",
            "target_frame",
            "object_mapping",
            "preservation_receipt",
            "target_domain_falsifier",
            "decision_consequence",
        ),
        route_required_match_groups=(
            (
                "analogy",
                "isomorphism",
                "isomorphic",
                "translation",
                "transfer",
                "cross-domain",
                "state pricing",
                "state price",
                "superhedging",
                "max-flow",
                "min-cut",
                "hall",
                "representation",
                "mapping",
                "invariant",
                "bridge",
                "transport",
                "reduction",
                "encoding",
            ),
        ),
    ),
    OperatorCard(
        card_id="OP-SLP-01",
        name="Surplus-Loss Projection Certificate",
        source_ops=("core_06", "broad_07", "core_05"),
        trigger_terms=(
            "ambient",
            "bounded multiplicity",
            "chebotarev",
            "class number",
            "class group",
            "constants before limit",
            "denominator",
            "entropy",
            "fiber",
            "frattini",
            "frobenius",
            "golod",
            "high-dimensional",
            "injective",
            "lattice",
            "lift",
            "loss budget",
            "loss",
            "minkowski",
            "multiplicity",
            "norm-one",
            "pigeonhole",
            "packing",
            "project",
            "projection",
            "quotient",
            "root discriminant",
            "shafarevich",
            "splitting",
            "surplus",
            "tower",
            "unit distance",
            "window",
        ),
        obligation_classes=("transfer", "bound"),
        problem_classes=(
            "surplus_loss",
            "dimensional_lift",
            "projection_certificate",
            "ambient_certificate",
        ),
        entry_conditions=(
            "A hard target may be easier after lifting to an auxiliary ambient representation.",
            "The lifted proof must show surplus choices beat all loss/quotient costs before projecting back.",
            "The target claim depends on preserving a concrete target-side invariant under projection, not on ambient abundance alone.",
        ),
        steps=(
            "Name the target object and the ambient lifted object.",
            "State the surplus lower bound in the ambient representation.",
            "State every loss, quotient, denominator, or bad-class budget.",
            "State the projection back to the target and its injectivity or finite-multiplicity receipt.",
            "Fix constants and selection rules before the limiting process.",
            "State the target-size upper bound or packing bound used to convert ambient surplus into target exponent/decision gain.",
            "Name a target-domain packet that would break the certificate.",
        ),
        required_output=(
            "7-row certificate table: target, lift, surplus, loss budget, projection, target-size bound, breaker.",
            "One inequality showing surplus beats all losses after constants are fixed, or one missing-surplus slot.",
            "One projection/injectivity or finite-multiplicity receipt.",
            "One target-size/denominator/packing receipt.",
            "One target-domain falsifier packet.",
            "One boundary sentence forbidding ambient authority as target proof.",
        ),
        breaker=(
            "Show the target projection has unbounded multiplicity, the loss grows like the surplus, "
            "the constants are chosen after the limit, or the target packet has no ambient surplus fiber."
        ),
        stop_update_rule=(
            "Do not claim target progress from a lift until surplus, loss, and projection receipts "
            "are all present with constants fixed before the limit and a target-size bound paid."
        ),
        boundary=(
            "The ambient construction is only a proof engine after projection and multiplicity are paid."
        ),
        required_schema_fields=(
            "target_object",
            "ambient_lift",
            "surplus_lower_bound",
            "loss_or_quotient_budget",
            "projection_map",
            "multiplicity_or_injectivity_receipt",
            "target_size_or_packing_bound",
            "constants_before_limit_rule",
            "target_domain_falsifier",
        ),
        route_required_match_groups=(
            (
                "surplus",
                "entropy",
                "fiber",
                "class number",
                "class group",
                "chebotarev",
                "frobenius",
                "golod",
                "pigeonhole",
                "packing",
                "unit distance",
            ),
            (
                "ambient",
                "high-dimensional",
                "lift",
                "project",
                "projection",
                "quotient",
                "injective",
                "multiplicity",
                "bounded multiplicity",
                "lattice",
                "tower",
            ),
        ),
    ),
    OperatorCard(
        card_id="OP-PER-01",
        name="Portable Estimate Receipt Schema",
        source_ops=("GP-219", "core_03", "core_05"),
        trigger_terms=(
            "portable receipt",
            "portable estimate",
            "estimate receipt",
            "auxiliary object",
            "comparison object",
            "engineered object",
            "scope contract",
            "regime contract",
            "class scoping",
            "sharpness witness",
            "failure witness",
            "hostile witness",
            "counterexample",
            "representation reformulation",
            "coordinate reformulation",
            "same formal system",
            "pec_a",
            "pec_b",
            "pec_e",
            "cand_g",
        ),
        obligation_classes=("bound", "decompose", "transfer"),
        problem_classes=(
            "portable_estimate_receipt",
            "typed_receipt_schema",
            "estimate_craft_receipt",
        ),
        entry_conditions=(
            "A PDE or non-PDE estimate move is being reused as a portable receipt.",
            "The move is unsafe unless it names the receipt family and the fields that separate it from its nearest confuser.",
        ),
        steps=(
            "Select the receipt family: pec_a, pec_b, pec_e, cand_g, or another explicitly named portable receipt.",
            "Name the substrate or domain where the receipt is being used.",
            "Fill the receipt's action-constraint fields with checkable content.",
            "Name the nearest pec/cand confuser and the field that rejects it.",
            "State the artifact change and the decision consequence.",
        ),
        required_output=(
            "Portable receipt row: selected_receipt_family, substrate_or_domain, action_constraint_fields.",
            "Typed-field completion row: typed_fields_filled, nearest_confuser, confuser_rejection_reason.",
            "Artifact and decision row: artifact_change, decision_consequence.",
            "One boundary sentence forbidding pec/cand labels as payment without field content.",
        ),
        breaker=(
            "Show that the artifact only names pec_a/pec_b/pec_e/cand_g or a witness label, "
            "without the fields that distinguish that receipt from its nearest confuser."
        ),
        stop_update_rule=(
            "Do not accept a portable estimate move until selected family, typed fields, "
            "nearest-confuser rejection, artifact change, and decision consequence are present."
        ),
        boundary=(
            "Portable receipt names are routing handles. They become evidence only through "
            "filled action-constraint fields and a downstream artifact or decision change."
        ),
        disambiguators=(
            "Prefer portable-estimate receipt over evidence-carrier routing when pec/cand families or estimate-craft receipt names are visible.",
            "Prefer source-target transfer when the live issue is preserving an invariant across representations rather than filling a known portable receipt family.",
            "Prefer branch coverage when the work is paying every regime before aggregation, not selecting a receipt schema.",
        ),
        fine_handles=(
            "pec_a: auxiliary comparison object with comparison_map and target_quantity fields.",
            "pec_b: regime/class scoping with scope_breaker and boundary condition fields.",
            "pec_e: sharpness or failure witness with claim_boundary_update fields.",
            "cand_g: same-formal-system representation reformulation with translation_rule fields.",
        ),
        required_schema_fields=(
            "selected_receipt_family",
            "substrate_or_domain",
            "action_constraint_fields",
            "typed_fields_filled",
            "nearest_confuser",
            "confuser_rejection_reason",
            "artifact_change",
            "decision_consequence",
        ),
    ),
    OperatorCard(
        card_id="OP-LGA-01",
        name="Local-to-Global Assembly Check",
        source_ops=("core_04", "core_03"),
        trigger_terms=(
            "local",
            "global",
            "assembly",
            "gluing",
            "compatibility",
            "interface",
            "patch",
            "piece",
            "pieces",
            "handoff",
            "module",
            "modular",
            "compose",
            "composition",
            "graft",
            "partition",
            "function validation",
            "barrier",
            "factorization",
        ),
        obligation_classes=("decompose", "transfer"),
        problem_classes=("local_global", "interface_compatibility", "assembly_failure"),
        entry_conditions=(
            "Valid local pieces exist.",
            "The global conclusion depends on interfaces between those pieces.",
        ),
        steps=(
            "List local pieces.",
            "Name every interface condition.",
            "Attach a receipt for each compatibility condition.",
            "Block the global claim if one interface is unpaid.",
        ),
        required_output=(
            "4-row local-piece/interface table.",
            "One compatibility falsifier.",
            "One global stop/update rule.",
            "One boundary sentence.",
        ),
        breaker="Find one local piece that is valid alone but fails at an interface.",
        stop_update_rule="No global update until every interface has a receipt.",
        boundary="Local validity is not global validity until compatibility is checked.",
        disambiguators=(
            "Prefer interface over branch when the facts already supply local pieces and the live question is whether they compose.",
            "Prefer branch over interface when the live work is enumerating regimes or criteria before any handoff can be tested.",
            "Prefer source-target over interface when the bottleneck is preserving an invariant across a representation map, not compatibility among pieces.",
        ),
    ),
    OperatorCard(
        card_id="OP-CBM-01",
        name="Claim Boundary Mutation",
        source_ops=("core_01", "broad_05"),
        trigger_terms=(
            "overclaim",
            "boundary",
            "scope",
            "narrow",
            "mutation",
            "conjecture",
            "negative",
            "null",
            "limitation",
            "weaker claim",
            "selective",
            "narrower",
            "broader",
            "ordinary",
            "restricted",
            "variant",
            "some directions",
            "directions of inequality",
            "can fail",
            "may fail",
            "localized nonlinearities",
            "half-line",
            "half line",
            "question",
            "old question",
            "new question",
            "question being asked",
            "usable answer object",
            "answer object",
            "dominance certificate",
            "dominance certificates",
            "impossibility witness",
            "impossibility witnesses",
        ),
        obligation_classes=("bound",),
        problem_classes=("claim_scope", "negative_result", "overclaim_guard"),
        entry_conditions=(
            "The broad claim may be false, ambiguous, or unsupported.",
            "A narrower claim may still be useful and testable.",
        ),
        steps=(
            "State the broad claim.",
            "State the narrower claim that survives the evidence.",
            "Name the discriminator between broad and narrow.",
            "State what result would force another mutation.",
        ),
        required_output=(
            "4-row claim-boundary table.",
            "Typed broad/narrow claim rows with claim_kind, claim_text, answer_object, success_criterion, evidence_available, missing_evidence_or_blocker, and permitted_status.",
            "One discriminator.",
            "One stop/update rule.",
            "One sentence forbidding the broad claim.",
            "For claim-boundary rows, include explicit answer_object and success_criterion fields for both broad and narrow claims.",
        ),
        breaker="Show that the narrower claim fails for the same reason as the broad claim.",
        stop_update_rule="Keep the broad claim closed until the discriminator separates it from the narrower claim.",
        boundary="The narrowed claim is the current object; the broad claim is not reopened by wording.",
        disambiguators=(
            "Prefer claim-boundary over branch when the broad claim is being narrowed rather than exhaustively split.",
            "Prefer branch over claim-boundary when every branch must be paid for one aggregate conclusion.",
        ),
        fine_handles=(
            "claim_boundary_split: route to typed broad/narrow claim rows; broad row BLOCKED, narrow row PERMITTED, with answer_object, success_criterion, evidence_available, and missing_evidence_or_blocker fields.",
            "question_game_reframing: old question, candidate new question, old/new answer object, new success criterion, bridge back to original stakes.",
        ),
        required_schema_fields=(
            "claim_kind",
            "claim_text",
            "answer_object",
            "success_criterion",
            "evidence_available",
            "missing_evidence_or_blocker",
            "permitted_status",
            "pass_fail_boundary",
        ),
    ),
    OperatorCard(
        card_id="OP-RMI-01",
        name="Reflexive Mining Instrument Check",
        source_ops=("core_01", "core_03", "broad_08"),
        trigger_terms=(
            "reflexive mining",
            "reflexive mine",
            "primitive roi",
            "capability roi",
            "recursive gain",
            "bifurcation",
            "in loop share",
            "in-loop share",
            "out of loop share",
            "out-of-loop share",
            "agent work share",
            "abandoned project",
            "abandoned projects",
            "project portfolio",
            "operations intelligence",
            "route row",
            "route rows",
            "missing route row",
            "missing route rows",
            "backfill route row",
            "backfill route rows",
            "p0 metrics",
            "dashboard",
            "taste rating",
            "contextualized rater",
            "artifact index",
        ),
        obligation_classes=("bound", "decompose"),
        problem_classes=(
            "reflexive_mining",
            "primitive_roi_audit",
            "portfolio_attention",
            "in_loop_out_of_loop_measurement",
        ),
        entry_conditions=(
            "The decision depends on whether the apparatus is spending effort in the right place.",
            "The project or primitive portfolio may be stale, underused, duplicated, or overcounted.",
        ),
        steps=(
            "Name the portfolio question: primitive reuse, project focus, in-loop/out-of-loop split, or dashboard trust.",
            "Run or inspect the canonical reflexive sources instead of relying on memory.",
            "Separate activity volume from measured yield before recommending work.",
            "Name the next action and the measurement that would falsify it.",
        ),
        required_output=(
            "Reflexive instrument row: question, source inspected, metric, current value, decision consequence.",
            "Pointers to the relevant source files: bifurcation report, P0 metrics, recursive-gain candidates, primitive ROI, operations-intelligence payload, or dashboard bundle.",
            "One stale-source or missing-source note if a source is absent, old, or sample-scoped.",
            "One action rule: continue kernel work, revive a project, retire/deprioritize a project, backfill route rows, or repair an emitter.",
        ),
        breaker=(
            "Show that the recommendation follows from artifact volume alone, or from a stale/sample-scoped source "
            "that does not measure the claimed portfolio property."
        ),
        stop_update_rule=(
            "Do not convert reflexive mining into roadmap claims until the source, metric, and decision consequence are named."
        ),
        boundary=(
            "Reflexive mining is measurement and triage. It can prioritize kernel or project work, but it is not "
            "evidence that a primitive improves research output without a downstream outcome trace."
        ),
        disambiguators=(
            "Prefer this card over autoresearch workbench routing when the live question is portfolio measurement rather than whether to invoke the loop for a bounded task.",
            "Prefer autoresearch workbench routing when the task has a bounded claim/evaluator/rubric/artifact surface and the decision is in-loop versus out-of-loop execution.",
            "Prefer branch coverage when all sources are current and the only missing object is a branch table.",
        ),
        fine_handles=(
            "bifurcation_measure: iter_loop_artifacts, agent_work_artifacts, agent_work_share.",
            "primitive_roi_measure: capability id, action count, downstream outcome trace, verdict band.",
            "operations_intelligence_attention: attention kind, severity, source refs, learning candidate.",
            "contextualized_taste_measure: rater id, sample scope, freshness, canonical-series caveat.",
        ),
        required_schema_fields=(
            "portfolio_question",
            "source_refs",
            "metric_name",
            "metric_value",
            "freshness_or_scope_note",
            "decision_consequence",
            "falsifier",
            "next_action",
        ),
    ),
    OperatorCard(
        card_id="OP-GDC-01",
        name="Graph Diagnostic Carrier",
        source_ops=("core_01", "core_03", "core_05"),
        trigger_terms=(
            "graph",
            "context graph",
            "graph carrier",
            "graph diagnostic",
            "probability dag",
            "constraint basin",
            "constraint-basin",
            "source claim graph",
            "code dependency graph",
            "primitive capability graph",
            "dag steering",
            "min cut",
            "min-cut",
            "dominators",
            "pagerank",
            "hits",
            "k core",
            "k-core",
            "louvain",
            "edge betweenness",
            "counterfactual edge",
            "graph perturbation",
            "graph disagreement",
            "graph receipt",
        ),
        obligation_classes=("bound", "decompose", "transfer"),
        problem_classes=(
            "graph_diagnostic_carrier",
            "graph_receipt",
            "context_graph_routing",
            "research_state_graph",
        ),
        entry_conditions=(
            "A graph-shaped artifact is being used to orient research, select a route, or demote a route.",
            "The metric is unsafe unless it names its producer, baseline, noise filter, and downstream decision effect.",
        ),
        steps=(
            "Name the graph kind, producer, source artifacts, and consumer.",
            "Name the standard library or method family behind each diagnostic.",
            "State the substrate-specific extraction or filtering layer.",
            "Record whether the graph changed a route, selected a check, was ignored, or was misleading.",
            "Compile the selected graph result into a gate, pattern-action carrier, or explicit non-use receipt.",
        ),
        required_output=(
            "Graph carrier row: graph_id, graph_kind, producer, source_artifacts, consumer, freshness_rule.",
            "Diagnostic rows with method, baseline, result summary, and library or literature anchor.",
            "Noise-filter row naming plumbing, aliases, generated binders, or low-signal edges removed.",
            "Decision receipt: strategy_change, no_strategy_change, or misleading_or_noise.",
            "Selected action card, gate, or next artifact slot, or a non-use reason.",
        ),
        breaker=(
            "Show that the graph metric is a standard algorithm reported without provenance, "
            "without a baseline/noise filter, or without changing any downstream check."
        ),
        stop_update_rule=(
            "Do not treat a graph metric as evidence until it validates as a graph carrier "
            "and either selects a next check/artifact or records a no-use/misleading receipt."
        ),
        boundary=(
            "The graph layer supplies orientation and route accounting. It does not replace the "
            "domain gate, proof check, source audit, or evaluator."
        ),
        disambiguators=(
            "Prefer this card over evidence-carrier routing when the carrier is explicitly graph-shaped.",
            "Prefer source-target transfer when the live risk is invariant preservation across a map rather than graph metric interpretation.",
            "Prefer reflexive mining when the live question is portfolio measurement and the graph is only one inspected source.",
        ),
        fine_handles=(
            "graph_carrier_schema: graph_id, graph_kind, producer, source_artifacts, consumer, freshness_rule, vocabularies, diagnostics, noise_filter, decision_receipt.",
            "algorithm_boundary: standard framework method versus ZTARE extraction, conditioning, disagreement, perturbation, and receipt layer.",
            "action_card_lowering: selected graph finding compiles to a pattern-action carrier, gate, next artifact slot, or explicit non-use.",
        ),
        required_schema_fields=(
            "graph_id",
            "graph_kind",
            "producer",
            "source_artifacts",
            "consumer",
            "freshness_rule",
            "diagnostics",
            "noise_filter",
            "decision_receipt",
            "selected_action_card_or_gate",
            "non_use_or_retraction",
        ),
    ),
    OperatorCard(
        card_id="OP-MME-01",
        name="Meta-Language Edge Carrier",
        source_ops=("mm_02", "mm_03", "core_01"),
        trigger_terms=(
            "mm_01",
            "mm_02",
            "mm_03",
            "meta-language",
            "meta language",
            "evidence-path graph",
            "evidence path graph",
            "causal edge",
            "residual-to-check",
            "residual to check",
            "surface quotient",
            "quotient surface",
            "live residual",
            "recurring residual",
        ),
        obligation_classes=("bound", "transfer"),
        problem_classes=(
            "meta_language_edge_carrier",
            "residual_to_check_edge",
            "surface_quotient_edge",
        ),
        entry_conditions=(
            "A meta-language or mm surface is being used to select the next check.",
            "The route is unsafe unless the surface is lowered into a causal edge from observed state to required artifact.",
        ),
        steps=(
            "State the observed state.",
            "Name the quotient-hidden surface wording.",
            "Name the evidence-path graph or residual edge.",
            "State the candidate edge and required check.",
            "Name the forbidden sibling and the stop rule.",
        ),
        required_output=(
            "Meta-language edge row: observed_state, quotient_hidden_surface, evidence_path_graph.",
            "Residual edge row: live_residual_or_blocker, candidate_edge, required_check.",
            "Boundary row: forbidden_sibling, permitted_update_if_paid, stop_rule.",
            "One sentence forbidding mm labels as payment without edge content.",
        ),
        breaker=(
            "Show that the artifact only names an mm label, graph family, or residual family "
            "without the observed-state-to-required-check edge."
        ),
        stop_update_rule=(
            "Do not accept a meta-language move until the causal edge and required check are explicit."
        ),
        boundary=(
            "The mm surface is a compiler handle. The accepted artifact is the edge from observed state "
            "to required check, not the label."
        ),
        disambiguators=(
            "Prefer meta-language edge over graph diagnostic when mm labels, quotient surfaces, or residual-to-check wording select the next artifact.",
            "Prefer graph diagnostic when the live issue is algorithm provenance, graph producer, diagnostics, or non-use receipt.",
            "Prefer portable receipt when the visible obligation is pec/cand typed fields rather than a residual-to-check edge.",
        ),
        fine_handles=(
            "mm_02: surface quotient to evidence-path graph.",
            "mm_03: promote live residual or blocker into the required-check edge.",
        ),
        required_schema_fields=(
            "observed_state",
            "quotient_hidden_surface",
            "evidence_path_graph",
            "live_residual_or_blocker",
            "candidate_edge",
            "required_check",
            "forbidden_sibling",
            "permitted_update_if_paid",
            "stop_rule",
        ),
    ),
    OperatorCard(
        card_id="OP-AWR-01",
        name="Autoresearch Workbench Routing",
        source_ops=("core_01", "core_05", "broad_08"),
        trigger_terms=(
            "autoresearch",
            "auto research",
            "workbench",
            "in loop",
            "in-loop",
            "out of loop",
            "out-of-loop",
            "research director",
            "subscription agent",
            "agentic workbench",
            "bounded claim",
            "stable evaluator",
            "rubric surface",
            "artifact surface",
            "hypothesis projection",
            "manual agent",
        ),
        obligation_classes=("bound", "transfer"),
        problem_classes=(
            "autoresearch_workbench_routing",
            "agentic_workbench_boundary",
            "in_loop_out_of_loop_decision",
        ),
        entry_conditions=(
            "An RD or out-of-loop agent may do work that could be run through autoresearch.",
            "The task may have a bounded claim, evaluator, rubric, and artifact surface.",
        ),
        steps=(
            "Score the four workbench prerequisites: bounded claim, stable evaluator, rubric surface, artifact surface.",
            "Choose invoke_autoresearch, prepare_autoresearch_surface, or stay_out_of_loop.",
            "If invoking autoresearch, run the workbench and inspect the projection before treating the result as evidence.",
            "If staying out of loop, record the missing surface or cost reason in action intelligence.",
            "Feed failed branches back as reusable negative constraints rather than private session memory.",
        ),
        required_output=(
            "Workbench routing row: task, project family, four prerequisite booleans, router decision, missing surfaces.",
            "Saved route JSON and action-intelligence row from `ztare autoresearch route --record-decision-id`, or an equivalent pre-saved route JSON recorded through `record-agentic-route`.",
            "Command or artifact pointer for the autoresearch run/projection, or a reason it was not run.",
            "One negative-constraint summary for any failed branch worth reusing.",
        ),
        breaker=(
            "Show that an out-of-loop agent produced primary evidence while all four workbench "
            "prerequisites were present and no bypass reason/action-impact row was recorded."
        ),
        stop_update_rule=(
            "Do not promote manual RD/out-of-loop work as primary workbench evidence until the "
            "router decision is recorded and any ready autoresearch surface was either used or "
            "explicitly bypassed."
        ),
        boundary=(
            "This card governs the transport/state/identity boundary; it does not claim the "
            "autoresearch result is true without normal gates and held-out/admission evidence."
        ),
        disambiguators=(
            "Prefer this card over generic evidence-carrier routing when the decision is whether the RD should use autoresearch.",
            "Prefer evidence-carrier routing when the workbench path is already chosen and the live issue is a claim/evidence receipt.",
            "Prefer claim-boundary mutation when the task itself is too broad and no bounded workbench claim exists yet.",
        ),
        fine_handles=(
            "workbench_router_decision: invoke_autoresearch, prepare_autoresearch_surface, stay_out_of_loop.",
            "worker_metadata: worker_archetype, worker_capability, worker_state, worker_identity, transport.",
            "route_receipt: route_json_ref plus action_impact_ref; default producer is `ztare autoresearch route --record-decision-id`.",
            "negative_constraint_summary: tried branch, failure receipt, reusable constraint, next excluded region.",
        ),
        required_schema_fields=(
            "task",
            "project_family",
            "bounded_claim",
            "stable_evaluator",
            "rubric_ready",
            "artifact_surface",
            "workbench_router_decision",
            "why_not_autoresearch",
            "worker_metadata",
            "route_json_ref",
            "action_impact_ref",
            "workbench_evidence_ref",
        ),
    ),
)

ROUTER_BOILERPLATE_PHRASES: tuple[str, ...] = (
    "produce the single next audit artifact and falsifier",
    "produce the next audit artifact and falsifier",
    "before a larger claim update",
    "before any claim update",
    "do not output family names, taxonomy labels, protocol names, or op ids",
)


def _normalize_context(context: str | Iterable[str] | None) -> list[str]:
    def clean(item: object) -> str:
        text = str(item).replace("_", " ").replace("-", " ").lower()
        for phrase in ROUTER_BOILERPLATE_PHRASES:
            text = text.replace(phrase, " ")
        return " ".join(text.split())

    if context is None:
        return []
    if isinstance(context, str):
        return [clean(context)]
    return [clean(item) for item in context]


def route_operator_cards(
    *,
    context: str | Iterable[str] | None = None,
    top_n: int = 2,
) -> list[OperatorCard]:
    """Route visible context to compact operator cards."""
    haystacks = _normalize_context(context)
    routed: list[OperatorCard] = []

    def matches(term: str) -> bool:
        needle = term.replace("_", " ").replace("-", " ").lower()
        return any(needle in hay for hay in haystacks)

    for card in CARDS:
        matched: list[str] = []
        score = 0.0
        for term in card.trigger_terms:
            if matches(term):
                matched.append(term)
                score += 2.0
        for problem_class in card.problem_classes:
            if matches(problem_class):
                matched.append(problem_class)
                score += 3.0
        if score > 0:
            if card.route_required_match_groups and not all(
                any(matches(term) for term in group)
                for group in card.route_required_match_groups
            ):
                continue
            routed.append(
                replace(
                    card,
                    score=score,
                    matched_terms=tuple(dict.fromkeys(matched)),
                )
            )
    routed.sort(key=lambda card: (-card.score, card.card_id))
    return routed[:top_n]


def operator_card_catalog_entries() -> list[dict]:
    """Return atlas-ready rows for individual operator-card selection."""

    try:
        from ztare.common.embeddings import content_id
    except Exception:  # noqa: BLE001
        content_id = None

    rows: list[dict] = []
    for card in CARDS:
        parts = [
            card.card_id,
            card.name,
            "problem classes: " + ", ".join(card.problem_classes),
            "entry: " + " ".join(card.entry_conditions),
            "steps: " + " ".join(card.steps),
            "outputs: " + " ".join(card.required_output),
            "breaker: " + card.breaker,
            "boundary: " + card.boundary,
            "fields: " + ", ".join(card.required_schema_fields),
            "handles: " + " ".join(card.fine_handles),
            "disambiguators: " + " ".join(card.disambiguators),
        ]
        text = "\n".join(part for part in parts if part.strip())
        row_id = (
            f"operator_card:{card.card_id}:{content_id(card.card_id, text)}"
            if content_id
            else f"operator_card:{card.card_id}"
        )
        rows.append(
            {
                "id": row_id,
                "text": text,
                "card_id": card.card_id,
                "name": card.name,
                "source_ops": list(card.source_ops),
                "problem_classes": list(card.problem_classes),
                "obligation_classes": list(card.obligation_classes),
                "required_schema_fields": list(card.required_schema_fields),
            }
        )
    return rows


def _card_id_from_atlas_row(row_id: str, row: object) -> str:
    if isinstance(row, dict) and isinstance(row.get("card_id"), str):
        return str(row["card_id"])
    parts = str(row_id).split(":")
    return parts[1] if len(parts) >= 2 and parts[0] == "operator_card" else str(row_id)


def _card_ids_for_atlas_rows(row_ids: set[str], meta: dict[str, object], current_by_id: dict[str, str]) -> list[str]:
    card_ids: set[str] = set()
    for row_id in row_ids:
        card_ids.add(current_by_id.get(row_id) or _card_id_from_atlas_row(row_id, meta.get(row_id)))
    return sorted(card_ids)


def operator_card_atlas_freshness(
    *,
    atlas_path: Path = OPERATOR_CARD_ATLAS_PATH,
    manifest_path: Path = OPERATOR_CARD_ATLAS_MANIFEST_PATH,
) -> dict:
    """Return an offline contract check between the card catalog and atlas rows.

    The semantic route is only trustworthy when the embedded row ids match the
    current catalog rows. This check deliberately avoids provider calls.
    """

    expected_rows = operator_card_catalog_entries()
    expected_ids = {str(row["id"]) for row in expected_rows}
    current_by_id = {str(row["id"]): str(row["card_id"]) for row in expected_rows}
    base = {
        "atlas_path": str(atlas_path),
        "manifest_path": str(manifest_path),
        "atlas_exists": Path(atlas_path).exists(),
        "manifest_exists": Path(manifest_path).exists(),
        "expected_count": len(expected_rows),
        "expected_card_ids": sorted({str(row["card_id"]) for row in expected_rows}),
        "next_command": "make move-card-atlas-build",
    }
    if not Path(atlas_path).exists():
        return {
            **base,
            "status": "absent",
            "fresh": False,
            "routing_mode": "lexical_fallback",
            "semantic_deployed": False,
            "reason": "move-card semantic atlas file is absent",
        }
    try:
        atlas = json.loads(Path(atlas_path).read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            **base,
            "status": "invalid",
            "fresh": False,
            "routing_mode": "lexical_fallback",
            "semantic_deployed": False,
            "reason": f"move-card atlas is unreadable: {type(exc).__name__}",
        }
    embeddings = atlas.get("embeddings")
    meta = atlas.get("meta")
    if not isinstance(embeddings, list) or not embeddings:
        return {
            **base,
            "status": "empty",
            "fresh": False,
            "routing_mode": "lexical_fallback",
            "semantic_deployed": False,
            "model": atlas.get("model"),
            "dimensions": atlas.get("dimensions"),
            "declared_size": atlas.get("size"),
            "embedding_count": len(embeddings) if isinstance(embeddings, list) else 0,
            "meta_count": len(meta) if isinstance(meta, dict) else 0,
            "reason": "move-card atlas has no embeddings",
        }
    if not isinstance(meta, dict) or not meta:
        return {
            **base,
            "status": "invalid",
            "fresh": False,
            "routing_mode": "lexical_fallback",
            "semantic_deployed": False,
            "model": atlas.get("model"),
            "dimensions": atlas.get("dimensions"),
            "declared_size": atlas.get("size"),
            "embedding_count": len(embeddings),
            "meta_count": len(meta) if isinstance(meta, dict) else 0,
            "reason": "move-card atlas is missing metadata rows",
        }
    embedding_ids = {
        str(row.get("id"))
        for row in embeddings
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    meta_ids = {str(row_id) for row_id in meta.keys()}
    missing_ids = expected_ids - meta_ids
    extra_ids = meta_ids - expected_ids
    missing_embedding_ids = expected_ids - embedding_ids
    extra_embedding_ids = embedding_ids - expected_ids
    declared_size = atlas.get("size")
    size_matches = isinstance(declared_size, int) and declared_size == len(expected_ids)

    manifest: dict = {}
    manifest_size_matches = False
    manifest_source_matches = False
    if Path(manifest_path).exists():
        try:
            loaded = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
            manifest = loaded if isinstance(loaded, dict) else {}
        except Exception:
            manifest = {}
    manifest_size_matches = manifest.get("size") == len(expected_ids)
    manifest_source_matches = manifest.get("source") == __name__

    fresh = (
        not missing_ids
        and not extra_ids
        and not missing_embedding_ids
        and not extra_embedding_ids
        and size_matches
        and Path(manifest_path).exists()
        and manifest_size_matches
        and manifest_source_matches
    )
    status = "fresh" if fresh else "stale"
    reason = (
        "move-card semantic atlas matches the current card catalog"
        if fresh
        else "rebuild move-card atlas; embedded row ids or manifest metadata do not match the current catalog"
    )
    return {
        **base,
        "status": status,
        "fresh": fresh,
        "routing_mode": "semantic_atlas" if fresh else "lexical_fallback",
        "semantic_deployed": fresh,
        "model": atlas.get("model"),
        "dimensions": atlas.get("dimensions"),
        "declared_size": declared_size,
        "embedding_count": len(embedding_ids),
        "meta_count": len(meta_ids),
        "manifest_size": manifest.get("size") if isinstance(manifest, dict) else None,
        "size_matches_expected": size_matches,
        "manifest_size_matches_expected": manifest_size_matches,
        "manifest_source_matches": manifest_source_matches,
        "missing_card_ids": _card_ids_for_atlas_rows(missing_ids, meta, current_by_id),
        "extra_card_ids": _card_ids_for_atlas_rows(extra_ids, meta, current_by_id),
        "missing_embedding_card_ids": _card_ids_for_atlas_rows(missing_embedding_ids, meta, current_by_id),
        "extra_embedding_card_ids": _card_ids_for_atlas_rows(extra_embedding_ids, meta, current_by_id),
        "next_command": None if fresh else "make move-card-atlas-build",
        "reason": reason,
    }


def build_operator_card_atlas(
    *,
    out_emb: Path = OPERATOR_CARD_ATLAS_PATH,
    out_manifest: Path = OPERATOR_CARD_ATLAS_MANIFEST_PATH,
) -> dict:
    """Build the optional semantic atlas for operator-card selection."""

    from ztare.common.embeddings import build_atlas

    return build_atlas(
        operator_card_catalog_entries(),
        out_emb,
        out_manifest,
        extra_manifest={"corpus": "operator_cards", "source": __name__},
    )


def route_operator_cards_semantic(
    *,
    context: str | Iterable[str] | None = None,
    top_n: int = 2,
    atlas_path: Path = OPERATOR_CARD_ATLAS_PATH,
    raise_on_semantic_error: bool = False,
) -> list[OperatorCard]:
    """Route operator cards through the optional card atlas, with lexical backfill."""

    haystacks = _normalize_context(context)
    lexical_cards = route_operator_cards(context=context, top_n=len(CARDS))
    if not haystacks or not Path(atlas_path).exists():
        return lexical_cards

    try:
        from ztare.common.embeddings import query_atlas

        hits = query_atlas(Path(atlas_path), " ".join(haystacks), k=max(top_n * 3, top_n))
    except (Exception, SystemExit):
        if raise_on_semantic_error:
            raise
        return lexical_cards

    by_id = {card.card_id: card for card in CARDS}
    routed: list[OperatorCard] = []
    seen: set[str] = set()
    for hit in hits:
        card_id = str(hit.get("card_id") or "")
        if not card_id or card_id in seen or card_id not in by_id:
            continue
        seen.add(card_id)
        score = float(hit.get("score") or 0.0)
        routed.append(
            replace(
                by_id[card_id],
                score=round(score * 100, 4),
                matched_terms=(f"semantic:{score:.4f}",),
            )
        )
        if len(routed) >= top_n:
            break

    for card in lexical_cards:
        if card.card_id in seen:
            continue
        routed.append(card)
        seen.add(card.card_id)

    return routed or lexical_cards


def operator_card_route_receipts(routed_operator_cards: Iterable[object]) -> list[dict]:
    """Return compact, serializable provenance for routed operator cards."""
    receipts: list[dict] = []
    for card in routed_operator_cards:
        matched_terms = [str(term) for term in getattr(card, "matched_terms", ())]
        receipts.append(
            {
                "card_id": str(getattr(card, "card_id", "")),
                "name": str(getattr(card, "name", "")),
                "score": float(getattr(card, "score", 0.0) or 0.0),
                "matched_terms": matched_terms,
                "route_mode": (
                    "semantic_atlas"
                    if any(term.startswith("semantic:") for term in matched_terms)
                    else "lexical_fallback"
                ),
            }
        )
    return receipts


def render_operator_card_route_summary(
    routes: list[dict],
    *,
    limit: int = 5,
) -> str:
    """Render compact route provenance for CLI and RD receipts."""
    if not routes:
        return "none"
    chunks: list[str] = []
    for route in routes[:limit]:
        card_id = str(route.get("card_id") or "unknown")
        route_mode = str(route.get("route_mode") or "unknown")
        matched_terms = [
            str(term)
            for term in route.get("matched_terms", [])
            if str(term).strip()
        ][:3]
        term_suffix = f"[{','.join(matched_terms)}]" if matched_terms else ""
        chunks.append(f"{card_id}:{route_mode}{term_suffix}")
    if len(routes) > limit:
        chunks.append(f"+{len(routes) - limit} more")
    return ";".join(chunks)


def route_obligation_classes(
    *,
    context: str | Iterable[str] | None = None,
    top_n: int = 2,
) -> list[ObligationClass]:
    """Route visible context to the coarse obligation spine from v128d."""
    haystacks = _normalize_context(context)
    routed: list[ObligationClass] = []
    for obligation in OBLIGATION_CLASSES:
        matched: list[str] = []
        score = 0.0
        for term in obligation.trigger_terms:
            needle = term.replace("_", " ").replace("-", " ").lower()
            if any(needle in hay for hay in haystacks):
                matched.append(term)
                score += 2.0
        if score > 0:
            routed.append(
                replace(
                    obligation,
                    score=score,
                    matched_terms=tuple(dict.fromkeys(matched)),
                )
            )
    routed.sort(key=lambda item: (-item.score, item.class_id))
    return routed[:top_n]


def render_obligation_classes(obligations: list[ObligationClass]) -> str:
    if not obligations:
        return "obligation_spine_ok = False\nno coarse obligation matched this context"
    lines = [
        "obligation_spine_ok = True",
        "coarse obligation routing (v128d spine; fine cards are secondary):",
    ]
    for obligation in obligations:
        lines.append(f"  {obligation.class_id}: {obligation.name} score={obligation.score:g}")
        if obligation.matched_terms:
            lines.append(f"    matched: {', '.join(obligation.matched_terms[:8])}")
        lines.append("    owes:")
        for item in obligation.owes:
            lines.append(f"      - {item}")
        lines.append(f"    falsifier: {obligation.falsifier}")
    lines.append(
        "  policy: route machinery on coarse obligations; use fine op/card labels as retrieval/checklist handles, not promotion evidence."
    )
    return "\n".join(lines)


def render_operator_cards(cards: list[OperatorCard]) -> str:
    if not cards:
        return "operator_card_surface_ok = False\nno operator card matched this context"

    primary = cards[0]
    lines = [
        "operator_card_surface_ok = True",
        "primary operator:",
        f"  {primary.card_id}: {primary.name} score={primary.score:g}",
    ]
    if primary.matched_terms:
        lines.append(f"  matched: {', '.join(primary.matched_terms[:8])}")
    if primary.obligation_classes:
        lines.append(f"  coarse obligations: {', '.join(primary.obligation_classes)}")
    lines.append("  entry:")
    for item in primary.entry_conditions:
        lines.append(f"    - {item}")
    lines.append("  do:")
    for step in primary.steps:
        lines.append(f"    - {step}")
    lines.append("  required output:")
    for item in primary.required_output:
        lines.append(f"    - {item}")
    if primary.disambiguators:
        lines.append("  nearest-confuser disambiguators:")
        for item in primary.disambiguators:
            lines.append(f"    - {item}")
    if primary.fine_handles:
        lines.append("  fine receipt handles:")
        for item in primary.fine_handles:
            lines.append(f"    - {item}")
    if primary.required_schema_fields:
        lines.append("  action-constraint fields:")
        lines.append(f"    - {', '.join(primary.required_schema_fields)}")
    lines.append("  action-target guard: infer the action target from source facts; do not let task wording or a check menu supply the route.")
    lines.append(f"  breaker: {primary.breaker}")
    lines.append(f"  stop/update: {primary.stop_update_rule}")
    lines.append(f"  boundary: {primary.boundary}")

    if len(cards) > 1:
        secondary = cards[1]
        lines.append(f"secondary breaker candidate: {secondary.card_id}: {secondary.name}")
    return "\n".join(lines)


def operator_card_to_kernel_action_schema(card: OperatorCard) -> dict:
    """View an operator card through the common kernel action ABI."""

    return KernelActionSchema(
        source_kind="primitive_operator_card",
        action_family="operator_card",
        action_name=card.card_id,
        source_summary=f"{card.name}: {'; '.join(card.entry_conditions)}",
        target_mapping=(
            " -> ".join(card.steps[:3])
            if card.steps
            else "apply selected operator card to the current research context"
        ),
        nearest_confuser=(
            card.disambiguators[0]
            if card.disambiguators
            else "nearby operator card selected by vocabulary overlap rather than owed artifact"
        ),
        falsifier=card.breaker,
        verification_artifact=card.required_output[0] if card.required_output else "operator-card artifact",
        action_constraints=[
            *card.required_schema_fields,
            card.stop_update_rule,
            card.boundary,
        ],
        evidence_basis="epistemic-generation: coarse obligation plus checked action fields",
        payload={
            "card_id": card.card_id,
            "name": card.name,
            "source_ops": list(card.source_ops),
            "obligation_classes": list(card.obligation_classes),
            "problem_classes": list(card.problem_classes),
            "matched_terms": list(card.matched_terms),
            "required_output": list(card.required_output),
            "fine_handles": list(card.fine_handles),
        },
    ).to_dict()


def operator_cards_to_kernel_action_schemas(cards: list[OperatorCard]) -> list[dict]:
    return [operator_card_to_kernel_action_schema(card) for card in cards]


def write_operator_cards(
    path: Path = OUT_PATH,
    *,
    context: str | Iterable[str] | None = None,
    top_n: int = 2,
) -> list[OperatorCard]:
    cards = route_operator_cards(context=context, top_n=top_n)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": bool(cards),
        "obligation_route": [asdict(item) for item in route_obligation_classes(context=context, top_n=top_n)],
        "top_cards": [asdict(card) for card in cards],
        "kernel_action_schemas": operator_cards_to_kernel_action_schemas(cards),
        "promotion_policy": GP219_PROMOTION_POLICY,
        "note": (
            "Experimental operator-card surface. V128 policy: coarse obligation "
            "classes route machinery; fine cards and GP-219 handles are recall, "
            "receipt, and nearest-confuser surfaces. V177R narrows the active "
            "carrier to action-constraint content; field names are routing support. "
            "The 2026-05-23 HES ceiling adds a surface "
            "guard: action targets must be inferred from source facts, not "
            "spoon-fed by proposed-update/check-menu wording."
        ),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return cards
