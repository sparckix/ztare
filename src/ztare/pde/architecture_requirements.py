"""Machine-readable PDE kernel architecture requirement matrix."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PDEKernelRequirement:
    requirement_id: str
    title: str
    status: str
    evidence: tuple[str, ...]
    boundary_owner: str
    notes: str = ""


_REQUIREMENTS: tuple[PDEKernelRequirement, ...] = (
    PDEKernelRequirement(
        requirement_id="pde.registry.gates",
        title="registry-backed PDE gates",
        status="implemented",
        evidence=(
            "ztare.pde.registry.DEFAULT_PDE_GATE_REGISTRY",
            "ztare.pde.gate_runner.run_pde_gate",
            "ztare pde gates",
            "ztare pde run-gate",
        ),
        boundary_owner="pde_kernel",
    ),
    PDEKernelRequirement(
        requirement_id="pde.leaf.work_order",
        title="atomic PDE leaf work orders with hard-PDE process carriers",
        status="implemented",
        evidence=(
            "ztare.pde.work_order.build_pde_leaf_work_order",
            "ztare.pde.gate_runner.run_pde_leaf_work_order_gates",
            "ztare pde work-order",
            "ztare pde run-work-order",
            "--require-process-contract",
        ),
        boundary_owner="pde_kernel",
        notes=(
            "Hard PDE leaves can require brief-derived pattern-action, "
            "orchestration, and Gowers-first pencil artifact references before "
            "gate payloads count as complete."
        ),
    ),
    PDEKernelRequirement(
        requirement_id="pde.ops.currency.estimates",
        title="operation, currency, and estimate facades",
        status="implemented",
        evidence=(
            "ztare.pde.ops",
            "ztare.pde.currency",
            "ztare.pde.estimates",
            "ztare pde ops",
            "ztare pde currency",
            "ztare pde estimates",
        ),
        boundary_owner="pde_kernel",
        notes="Facades preserve existing RD primitives while moving caller imports to ztare.pde.",
    ),
    PDEKernelRequirement(
        requirement_id="pde.receipts",
        title="receipt registry",
        status="implemented",
        evidence=(
            "ztare.pde.receipts.all_pde_receipt_entries",
            "ztare pde receipts",
        ),
        boundary_owner="pde_kernel",
    ),
    PDEKernelRequirement(
        requirement_id="pde.operator.numerics.plugins",
        title="operator-admissibility and rigorous-numerics plugin gates",
        status="implemented",
        evidence=(
            "G-PDE-OPERATOR-ADMISSIBILITY",
            "G-PDE-RIGOROUS-NUMERICS",
            "ztare.gates.pde_operator_admissibility_gate",
            "ztare.gates.pde_rigorous_numerics_certificate_gate",
        ),
        boundary_owner="pde_kernel",
    ),
    PDEKernelRequirement(
        requirement_id="pde.physics.equality.plugins",
        title="physical-accounting and equality-provenance anti-laundering gates",
        status="implemented",
        evidence=(
            "G-PDE-PHYSICAL-ACCOUNTING",
            "G-PDE-EQUALITY-PROVENANCE",
            "ztare.gates.pde_physical_accounting_gate",
            "ztare.gates.pde_equality_provenance_gate",
            "ztare.pde.canary.build_pde_canary_reingestion_receipt",
        ),
        boundary_owner="pde_kernel",
        notes=(
            "Forces dimensional/balance-law invoices and blocks record-field "
            "projection of unpaid equality between physical streams."
        ),
    ),
    PDEKernelRequirement(
        requirement_id="pde.theorem.profile.cards",
        title="field-level theorem applicability cards",
        status="implemented",
        evidence=(
            "ztare.pde.applicability_cards.applicability_card_retrieval",
            "ztare.pde.knowledge_service.build_pde_knowledge_context",
        ),
        boundary_owner="pde_kernel",
        notes="These are PDE profile cards, not Lean theorem-bank entries.",
    ),
    PDEKernelRequirement(
        requirement_id="leanmill.formal.feedback.adapter",
        title="LeanMill formal feedback adapter",
        status="implemented",
        evidence=(
            "ztare.pde.formal_feedback.build_pde_formal_feedback_card",
            "ztare.leanmill.semantic_premise_shelf",
        ),
        boundary_owner="leanmill_service",
        notes="PDE consumes LeanMill retrieval/compiler context read-only.",
    ),
    PDEKernelRequirement(
        requirement_id="leanmill.failure.memory.adapter",
        title="LeanMill proof-cache and no-good memory adapter",
        status="implemented",
        evidence=(
            "ztare.pde.knowledge_service.build_leanmill_memory_summary",
            "ztare.leanmill.solver.proof_cache.ProofCache",
            "ztare.leanmill.solver.no_good_store.NoGoodStore",
        ),
        boundary_owner="leanmill_service",
    ),
    PDEKernelRequirement(
        requirement_id="pde.formal.surface.map",
        title="PDE formal-surface inventory",
        status="implemented",
        evidence=(
            "ztare.pde.formal_surface_status.build_pde_formal_surface_map",
            "ztare.pde.engine.PDEFormalSurfaceMapOptions",
        ),
        boundary_owner="pde_kernel",
    ),
    PDEKernelRequirement(
        requirement_id="pde.engine.context",
        title="composable PDE engine context",
        status="implemented",
        evidence=(
            "ztare.pde.engine.build_pde_engine_context",
            "ztare pde context",
        ),
        boundary_owner="pde_kernel",
    ),
    PDEKernelRequirement(
        requirement_id="rd.workbench.consumer",
        title="RD workbench consumes PDE kernel surfaces",
        status="implemented",
        evidence=(
            "ztare.research_director.pde_estimate_workbench",
            "pde_engine_context",
            "pde_gate_registry",
            "pde_receipt_registry",
        ),
        boundary_owner="rd_workbench",
    ),
    PDEKernelRequirement(
        requirement_id="project.app.boundary",
        title="project app owns substrate theorem profiles and receipts",
        status="implemented",
        evidence=(
            "ztare.pde.engine.service_boundaries.project_app",
            "ztare.pde.knowledge_service.service_boundaries.project_app",
        ),
        boundary_owner="project_app",
        notes="NS/TICK profiles remain caller data, not PDE kernel constants.",
    ),
)


def pde_kernel_architecture_requirements() -> list[dict[str, Any]]:
    """Return the PDE kernel architecture requirement matrix."""
    return [asdict(item) for item in _REQUIREMENTS]


def pde_kernel_requirement_status_counts() -> dict[str, int]:
    """Return counts by requirement status."""
    counts: dict[str, int] = {}
    for item in _REQUIREMENTS:
        counts[item.status] = counts.get(item.status, 0) + 1
    return dict(sorted(counts.items()))
