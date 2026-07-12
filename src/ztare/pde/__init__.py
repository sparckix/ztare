"""Public PDE-engine facade.

The implementation still reuses existing research-director modules, but callers
should prefer this package for engine-level composition.
"""

from ztare.pde.engine import (
    PDEApplicabilityCardOptions,
    PDEEstimateSkeletonOptions,
    PDEEngineContextRequest,
    PDEFormalFeedbackOptions,
    PDEFormalSurfaceMapOptions,
    PDEKnowledgeServiceOptions,
    PDELeafWorkOrderOptions,
    build_pde_engine_context,
)
from ztare.pde.gate_runner import (
    PDEGateRunResult,
    run_pde_gate,
    run_pde_leaf_work_order_gates,
)
from ztare.pde.registry import (
    DEFAULT_PDE_GATE_REGISTRY,
    PDEGateRegistryEntry,
    all_pde_gate_entries,
    entries_for_op,
    entry_by_gate_id,
)
from ztare.pde.work_order import (
    PDELeafWorkOrder,
    build_pde_leaf_work_order,
    render_pde_leaf_work_order,
)
from ztare.pde.applicability_cards import (
    PDEApplicabilityCard,
    applicability_card_retrieval,
    render_applicability_cards,
)
from ztare.pde.formal_surface_status import (
    PDEFormalSurfaceRecord,
    build_pde_formal_surface_map,
    normalize_pde_formal_surface_record,
    render_pde_formal_surface_map,
)
from ztare.pde.formal_feedback import (
    PDEFormalFeedbackCard,
    build_pde_formal_feedback_card,
    render_pde_formal_feedback_card,
)
from ztare.pde.subkernel import (
    PDESubkernelStatus,
    build_pde_subkernel_status,
)
from ztare.pde.architecture_requirements import (
    PDEKernelRequirement,
    pde_kernel_architecture_requirements,
    pde_kernel_requirement_status_counts,
)
from ztare.pde.knowledge_service import (
    PDEKnowledgeContext,
    PDELeanMillMemorySummary,
    build_leanmill_memory_summary,
    build_pde_knowledge_context,
)
from ztare.pde.ops import (
    all_pde_ops,
    deployable_pde_ops,
    pde_execution_template_for_ops,
    pde_op_by_id,
    portable_receipt_pde_ops,
    render_pde_ops_summary,
)
from ztare.pde.currency import (
    missing_pde_exchange_obligations,
    pde_currency_ledger_template,
    pde_exchange_rate_obligations,
)
from ztare.pde.estimates import generate_pde_estimate_skeletons
from ztare.pde.receipts import (
    PDEReceiptRegistryEntry,
    all_pde_receipt_entries,
    pde_gate_receipt_entries,
    pde_work_unit_receipt_entries,
)
from ztare.pde.readiness import (
    build_pde_kernel_readiness_receipt,
)
from ztare.pde.canary import (
    TICK669_PHYSICAL_CANARY_TARGETS,
    build_pde_canary_reingestion_receipt,
    build_pde_failure_memory_rows,
    write_pde_failure_memory_jsonl,
)
from ztare.pde.completion_audit import (
    PDECompletionAuditCheck,
    build_pde_kernel_completion_audit,
)

__all__ = [
    "PDEEngineContextRequest",
    "PDEGateRegistryEntry",
    "PDEFormalFeedbackOptions",
    "PDEFormalFeedbackCard",
    "PDEEstimateSkeletonOptions",
    "PDEKnowledgeServiceOptions",
    "PDEKnowledgeContext",
    "PDELeanMillMemorySummary",
    "PDEReceiptRegistryEntry",
    "PDESubkernelStatus",
    "PDEFormalSurfaceMapOptions",
    "PDEFormalSurfaceRecord",
    "PDELeafWorkOrderOptions",
    "PDELeafWorkOrder",
    "PDEGateRunResult",
    "PDEKernelRequirement",
    "PDECompletionAuditCheck",
    "PDEApplicabilityCard",
    "PDEApplicabilityCardOptions",
    "DEFAULT_PDE_GATE_REGISTRY",
    "applicability_card_retrieval",
    "all_pde_gate_entries",
    "all_pde_ops",
    "all_pde_receipt_entries",
    "build_pde_engine_context",
    "build_pde_formal_feedback_card",
    "build_pde_formal_surface_map",
    "build_pde_knowledge_context",
    "build_pde_leaf_work_order",
    "build_pde_kernel_readiness_receipt",
    "build_pde_kernel_completion_audit",
    "build_pde_canary_reingestion_receipt",
    "build_pde_failure_memory_rows",
    "build_leanmill_memory_summary",
    "build_pde_subkernel_status",
    "deployable_pde_ops",
    "entries_for_op",
    "entry_by_gate_id",
    "generate_pde_estimate_skeletons",
    "missing_pde_exchange_obligations",
    "normalize_pde_formal_surface_record",
    "pde_currency_ledger_template",
    "pde_kernel_architecture_requirements",
    "pde_kernel_requirement_status_counts",
    "pde_exchange_rate_obligations",
    "pde_execution_template_for_ops",
    "pde_gate_receipt_entries",
    "pde_op_by_id",
    "pde_work_unit_receipt_entries",
    "portable_receipt_pde_ops",
    "render_applicability_cards",
    "render_pde_ops_summary",
    "render_pde_formal_surface_map",
    "render_pde_formal_feedback_card",
    "render_pde_leaf_work_order",
    "run_pde_gate",
    "run_pde_leaf_work_order_gates",
    "TICK669_PHYSICAL_CANARY_TARGETS",
    "write_pde_failure_memory_jsonl",
]
