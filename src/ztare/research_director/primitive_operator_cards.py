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


REPO = Path(__file__).resolve().parents[3]
OUT_PATH = REPO / "analytics" / "public" / "queries" / "rd_operator_cards_experimental.json"


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
            "scaffold",
            "scaffolds",
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
    for card in CARDS:
        matched: list[str] = []
        score = 0.0
        for term in card.trigger_terms:
            needle = term.replace("_", " ").replace("-", " ").lower()
            if any(needle in hay for hay in haystacks):
                matched.append(term)
                score += 2.0
        for problem_class in card.problem_classes:
            needle = problem_class.replace("_", " ").replace("-", " ").lower()
            if any(needle in hay for hay in haystacks):
                matched.append(problem_class)
                score += 3.0
        if score > 0:
            routed.append(
                replace(
                    card,
                    score=score,
                    matched_terms=tuple(dict.fromkeys(matched)),
                )
            )
    routed.sort(key=lambda card: (-card.score, card.card_id))
    return routed[:top_n]


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
        "promotion_policy": GP219_PROMOTION_POLICY,
        "note": (
            "Experimental operator-card surface. V128 policy: coarse obligation "
            "classes route machinery; fine cards and GP-219 handles are recall, "
            "receipt, and nearest-confuser surfaces. V177R narrows the active "
            "carrier to action-constraint content; field names are scaffold "
            "and routing support. The 2026-05-23 HES ceiling adds a surface "
            "guard: action targets must be inferred from source facts, not "
            "spoon-fed by proposed-update/check-menu wording."
        ),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return cards
