"""Composable PDE engine context builder.

This is the narrow OS/app boundary for PDE work:

- PDE gate registry and leaf work orders are PDE-kernel concerns.
- Formal retrieval/compiler surfaces are consumed through the LeanMill adapter.
- Project apps such as NS/TICK provide theorem profiles, hostile packets, and
  source-specific receipts outside this module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ztare.pde.formal_feedback import (
    build_pde_formal_feedback_card,
)
from ztare.pde.currency import pde_currency_ledger_template
from ztare.pde.estimates import generate_pde_estimate_skeletons
from ztare.pde.ops import all_pde_ops
from ztare.pde.receipts import all_pde_receipt_entries
from ztare.pde.registry import all_pde_gate_entries
from ztare.pde.work_order import build_pde_leaf_work_order
from ztare.pde.applicability_cards import applicability_card_retrieval
from ztare.pde.formal_surface_status import build_pde_formal_surface_map
from ztare.pde.knowledge_service import build_pde_knowledge_context
from ztare.pde.architecture_requirements import (
    pde_kernel_architecture_requirements,
    pde_kernel_requirement_status_counts,
)


@dataclass(frozen=True)
class PDEFormalFeedbackOptions:
    enabled: bool = False
    statement: str = ""
    context: str = ""
    source: str = ""
    lean_root: str | None = None
    compile_result: dict[str, Any] | None = None
    typed_exit: dict[str, Any] | None = None
    top_k_mathlib: int = 8
    top_k_domain: int = 5
    top_k_own: int = 4
    threshold: float = 0.55


@dataclass(frozen=True)
class PDELeafWorkOrderOptions:
    op_id: str = ""
    goal: str = ""
    given: dict[str, Any] | None = None
    only_gate_ids: tuple[str, ...] = ()
    extra_gate_ids: tuple[str, ...] = ()
    require_process_contract: bool = False
    pattern_action_contract_ref: str = ""
    orchestration_contract_ref: str = ""
    pencil_artifact_ref: str = ""


@dataclass(frozen=True)
class PDEApplicabilityCardOptions:
    enabled: bool = False
    query: str = ""
    available: dict[str, Any] | None = None
    source_profile: str = "unknown"
    top_k: int = 8


@dataclass(frozen=True)
class PDEFormalSurfaceMapOptions:
    records: tuple[dict[str, Any], ...] = ()
    required_primitives: tuple[str, ...] = ()
    source_profile: str = "unknown"


@dataclass(frozen=True)
class PDEKnowledgeServiceOptions:
    enabled: bool = False
    query: str = ""
    available: dict[str, Any] | None = None
    source_profile: str = "unknown"
    statement: str = ""
    context: str = ""
    source: str = ""
    lean_root: str | None = None
    proof_cache_path: str | None = None
    no_good_store_path: str | None = None
    top_k_cards: int = 8
    top_k_mathlib: int = 0
    top_k_domain: int = 0
    top_k_own: int = 0
    threshold: float = 0.55


@dataclass(frozen=True)
class PDEEstimateSkeletonOptions:
    enabled: bool = False
    field: str = ""
    gap_type: str = ""
    context: dict[str, Any] | None = None
    inequalities: tuple[str, ...] = ()


@dataclass(frozen=True)
class PDEEngineContextRequest:
    target: str
    formal_feedback: PDEFormalFeedbackOptions = PDEFormalFeedbackOptions()
    leaf_work_order: PDELeafWorkOrderOptions = PDELeafWorkOrderOptions()
    applicability_cards: PDEApplicabilityCardOptions = PDEApplicabilityCardOptions()
    formal_surface_map: PDEFormalSurfaceMapOptions = PDEFormalSurfaceMapOptions()
    knowledge_service: PDEKnowledgeServiceOptions = PDEKnowledgeServiceOptions()
    estimate_skeletons: PDEEstimateSkeletonOptions = PDEEstimateSkeletonOptions()
    target_currency: str = ""
    theorem_db: dict[str, dict[str, Any]] | None = None


def build_pde_engine_context(request: PDEEngineContextRequest) -> dict[str, Any]:
    """Build reusable PDE-engine context for workbench packs or leaf dispatch."""
    gate_registry = all_pde_gate_entries()
    op_registry = all_pde_ops()
    receipt_registry = all_pde_receipt_entries()
    currency_ledger = pde_currency_ledger_template(
        request.target_currency or request.target or None
    )
    formal_feedback = None
    if request.formal_feedback.enabled:
        ff = request.formal_feedback
        formal_feedback = build_pde_formal_feedback_card(
            target=request.target,
            statement=ff.statement,
            context=ff.context,
            source=ff.source,
            lean_root=ff.lean_root,
            compile_result=ff.compile_result,
            typed_exit=ff.typed_exit,
            top_k_mathlib=ff.top_k_mathlib,
            top_k_domain=ff.top_k_domain,
            top_k_own=ff.top_k_own,
            threshold=ff.threshold,
        )
    leaf_work_order = None
    if request.leaf_work_order.op_id:
        leaf = request.leaf_work_order
        leaf_work_order = build_pde_leaf_work_order(
            target=request.target,
            op_id=leaf.op_id,
            goal=leaf.goal or request.target,
            given=leaf.given or {},
            only_gate_ids=leaf.only_gate_ids,
            extra_gate_ids=leaf.extra_gate_ids,
            formal_feedback_requested=bool(formal_feedback),
            require_process_contract=leaf.require_process_contract,
            pattern_action_contract_ref=leaf.pattern_action_contract_ref,
            orchestration_contract_ref=leaf.orchestration_contract_ref,
            pencil_artifact_ref=leaf.pencil_artifact_ref,
        )
    applicability_cards = []
    if request.applicability_cards.enabled:
        opts = request.applicability_cards
        applicability_cards = applicability_card_retrieval(
            request.theorem_db or {},
            query=opts.query or request.target,
            available=opts.available or {},
            source_profile=opts.source_profile,
            top_k=opts.top_k,
        )
    formal_surface_map = None
    if request.formal_surface_map.records or request.formal_surface_map.required_primitives:
        surface = request.formal_surface_map
        formal_surface_map = build_pde_formal_surface_map(
            list(surface.records),
            target=request.target,
            required_primitives=surface.required_primitives,
            source_profile=surface.source_profile,
        )
    knowledge_context = None
    if request.knowledge_service.enabled:
        opts = request.knowledge_service
        knowledge_context = build_pde_knowledge_context(
            target=request.target,
            query=opts.query,
            theorem_db=request.theorem_db,
            available=opts.available or {},
            source_profile=opts.source_profile,
            statement=opts.statement,
            context=opts.context,
            source=opts.source,
            lean_root=opts.lean_root,
            proof_cache_path=opts.proof_cache_path,
            no_good_store_path=opts.no_good_store_path,
            top_k_cards=opts.top_k_cards,
            top_k_mathlib=opts.top_k_mathlib,
            top_k_domain=opts.top_k_domain,
            top_k_own=opts.top_k_own,
            threshold=opts.threshold,
        )
    estimate_skeletons = []
    if request.estimate_skeletons.enabled:
        opts = request.estimate_skeletons
        estimate_skeletons = generate_pde_estimate_skeletons(
            target=request.target,
            field=opts.field,
            gap_type=opts.gap_type,
            context=opts.context,
            inequalities=opts.inequalities,
        )
    return {
        "schema": "pde-engine-context-v1",
        "target": request.target,
        "service_boundaries": {
            "pde_kernel": [
                "op_registry",
                "currency_ledger",
                "estimate_skeletons",
                "receipt_registry",
                "gate_registry",
                "leaf_work_order",
                "estimate_currency_and_operator_gates",
            ],
            "leanmill_service": [
                "semantic_premise_shelf",
                "compiler_feedback",
                "typed_exit_payloads",
            ],
            "project_app": [
                "theorem_profiles",
                "hostile_packets",
                "source_contracts",
                "formal_surfaces",
            ],
        },
        "request": asdict(request),
        "architecture_requirements": pde_kernel_architecture_requirements(),
        "architecture_requirement_status_counts": pde_kernel_requirement_status_counts(),
        "op_registry": op_registry,
        "currency_ledger": currency_ledger,
        "receipt_registry": receipt_registry,
        "gate_registry": gate_registry,
        "estimate_skeletons": estimate_skeletons,
        "formal_feedback": formal_feedback,
        "leaf_work_order": leaf_work_order,
        "applicability_cards": applicability_cards,
        "formal_surface_map": formal_surface_map,
        "knowledge_context": knowledge_context,
    }
