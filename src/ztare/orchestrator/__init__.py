"""GP-157 v5.0 Phase 4a: orchestrator package.

Extraction target for the large autoresearch_loop control surface.
Per panel synthesis 2026-04-25, the extraction sequence is:

    Phase 4a:  IterContext dataclass (this commit — additive)
    Phase 3c:  Cage authoritative dispatch (uses IterContext)
    Phase 4b:  orchestrator/telemetry.py (Karpathy "extract primitive")
    Phase 4c:  orchestrator/state.py (state-flow)

Until Phase 4b/4c, this package's job is narrow: provide the typed
IterContext that future extraction targets can rely on.
"""

from src.ztare.orchestrator.contract_adherence import (
    AdherenceReport,
    check_contract_adherence,
    emit_adherence,
    format_adherence_summary,
)
from src.ztare.orchestrator.contract_table import (
    CONTRACT_REGISTRY,
    ContractSpec,
    SubstrateABI,
    get_spec,
    get_spec_by_class,
    list_substrate_classes,
)
from src.ztare.orchestrator.protocols import (
    CONTRACT_ERROR_CODES,
    ContractError,
    FeatureModel,
    ScalarModel,
    adapt,
)
from src.ztare.orchestrator.render_evidence_template import (
    render_active_contract_label,
    render_evidence_set_d,
)
from src.ztare.orchestrator.iter_context import IterContext
from src.ztare.orchestrator.parallel_mutator import (
    DEFAULT_PARALLEL_PERSONAS,
    MutatorResult,
    MutatorTask,
    build_default_tasks,
    pick_best_candidate,
    run_parallel_mutators,
)
from src.ztare.orchestrator.evidence_contract import (
    EVIDENCE_ERROR_CODES,
    EvidenceContractError,
    EvidenceFormat,
    EvidenceSpec,
    get_evidence_spec,
    list_evidence_formats,
)
from src.ztare.orchestrator.fitted_model import FrozenFittedModel
from src.ztare.orchestrator.prompt import (
    active_contract_label,
    needs_override_contract_hint,
    needs_scalar_contract_hint,
    select_substrate_contract_hint,
    verify_class_consistency_with_substrate,
    verify_convention_bridge_in_form,
)
from src.ztare.orchestrator.state import (
    CageRuntime,
    build_cage_runtime,
    cage_init_banner,
    resolve_cage_mode,
)
from src.ztare.orchestrator.telemetry import (
    CageEngagementRecord,
    append_jsonl,
    emit_cage_engagement,
    format_cage_observe_summary,
)

__all__ = [
    "IterContext",
    "CageRuntime",
    "build_cage_runtime",
    "cage_init_banner",
    "resolve_cage_mode",
    "CageEngagementRecord",
    "append_jsonl",
    "emit_cage_engagement",
    "format_cage_observe_summary",
    "needs_override_contract_hint",
    "select_substrate_contract_hint",
    "verify_class_consistency_with_substrate",
    "verify_convention_bridge_in_form",
    "active_contract_label",
    "needs_scalar_contract_hint",
    "FrozenFittedModel",
    "AdherenceReport",
    "check_contract_adherence",
    "emit_adherence",
    "format_adherence_summary",
    "DEFAULT_PARALLEL_PERSONAS",
    "MutatorResult",
    "MutatorTask",
    "build_default_tasks",
    "pick_best_candidate",
    "run_parallel_mutators",
    "EvidenceFormat",
    "EvidenceSpec",
    "EvidenceContractError",
    "EVIDENCE_ERROR_CODES",
    "get_evidence_spec",
    "list_evidence_formats",
]
