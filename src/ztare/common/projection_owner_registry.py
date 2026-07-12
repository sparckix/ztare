from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


VISIBLE_WORKBENCH_SOURCE_REFS: tuple[str, ...] = (
    "src/ztare/__init__.py",
    "src/ztare/common/__init__.py",
    "src/ztare/validator/__init__.py",
    "src/ztare/validator/core/__init__.py",
    "src/ztare/worldmodel/__init__.py",
    "src/ztare/common/activity_meter.py",
    "src/ztare/common/artifact_refs.py",
    "src/ztare/common/candidate_first_policy.py",
    "src/ztare/common/candidate_memory.py",
    "src/ztare/common/cegis_membrane.py",
    "src/ztare/common/control_state_machine.py",
    "src/ztare/common/projection_owner_registry.py",
    "src/ztare/common/science_output_policy.py",
    "src/ztare/common/patch_base_identity.py",
    "src/ztare/common/ask_spec.py",
    "src/ztare/common/leaf_workbench_executor.py",
    "src/ztare/common/leaf_workbench_contract.py",
    "src/ztare/common/sealed_boundary_cegar.py",
    "src/ztare/common/structured_blocks.py",
    "src/ztare/common/leaf_workbench_python.py",
    "src/ztare/common/tool_synthesis_contract.py",
    "src/ztare/common/visible_workbench_actions.py",
    "src/ztare/common/visible_workbench_cli.py",
    "src/ztare/common/worldmodel_carrier_purity.py",
    "src/ztare/orchestrator/retry_contract.py",
    "src/ztare/validator/core/candidate_preflight.py",
    "src/ztare/validator/core/pre_judge_gate.py",
    "src/ztare/validator/core/repair_preflight.py",
    "src/ztare/validator/worldmodel_typed_payload.py",
    "src/ztare/worldmodel/episode_log.py",
    "src/ztare/worldmodel/evidence_probe.py",
    "src/ztare/worldmodel/evidence_quotients.py",
    "src/ztare/worldmodel/grid_dsl.py",
    "src/ztare/worldmodel/goal_abduction.py",
    "src/ztare/worldmodel/leaf_workbench.py",
    "src/ztare/worldmodel/patch_carrier_contract.py",
    "src/ztare/worldmodel/retry_surface.py",
    "src/ztare/worldmodel/spec_abduction.py",
    "src/ztare/worldmodel/spec_catalog.py",
)


@dataclass(frozen=True)
class ProjectionOwner:
    concept_id: str
    owner_module: str
    owner_file: str
    owner_symbols: tuple[str, ...] = ()
    projections: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    doc_refs: tuple[str, ...] = ()
    notes: str = ""

    def all_paths(self) -> tuple[str, ...]:
        return (
            self.owner_file,
            *self.projections,
            *self.tests,
            *self.doc_refs,
        )


PROJECTION_OWNERS: tuple[ProjectionOwner, ...] = (
    ProjectionOwner(
        concept_id="control_work_items",
        owner_module="ztare.common.control_work_items",
        owner_file="src/ztare/common/control_work_items.py",
        owner_symbols=("RunContext", "WorkItemRole", "classify_control_work_item", "should_block"),
        projections=(
            "src/ztare/common/strategy_card_roles.py",
            "src/ztare/orchestrator/briefing_providers/strategy_experiments.py",
            "src/ztare/validator/core/worldmodel_prompt_context.py",
            "src/ztare/worldmodel/retry_surface.py",
            "src/ztare/validator/core/strategy_card_gate.py",
        ),
        tests=(
            "tests/common/test_control_work_items.py",
            "tests/validator/test_strategy_card_gate.py",
        ),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Work-item lane, authority, blocking policy, and run-context blocking.",
    ),
    ProjectionOwner(
        concept_id="ask_spec",
        owner_module="ztare.common.ask_spec",
        owner_file="src/ztare/common/ask_spec.py",
        owner_symbols=("AskSpec", "render_ask_spec_markdown", "worldmodel_candidate_ask_spec"),
        projections=(
            "src/ztare/common/briefing_pack.py",
            "src/ztare/common/dispatch_model.py",
            "src/ztare/worldmodel/retry_surface.py",
        ),
        tests=("tests/test_dispatch_model.py",),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Requested output contract projected into API and agentic surfaces.",
    ),
    ProjectionOwner(
        concept_id="science_output_policy",
        owner_module="ztare.common.science_output_policy",
        owner_file="src/ztare/common/science_output_policy.py",
        owner_symbols=("SCIENCE_OUTPUT_POLICY",),
        projections=(
            "src/ztare/common/ask_spec.py",
            "src/ztare/common/briefing_pack.py",
            "src/ztare/orchestrator/briefing_providers/contract_rules.py",
            "src/ztare/orchestrator/briefing_providers/r1_pattern_warning.py",
            "src/ztare/worldmodel/retry_surface.py",
            "src/ztare/validator/worldmodel_typed_payload.py",
        ),
        tests=(
            "tests/test_dispatch_model.py",
            "tests/orchestrator/test_theorem_packet_prompting.py",
            "tests/validator/test_worldmodel_typed_payload.py",
        ),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Object-level candidate/action/lowerability contract.",
    ),
    ProjectionOwner(
        concept_id="structured_block_parsing",
        owner_module="ztare.common.structured_blocks",
        owner_file="src/ztare/common/structured_blocks.py",
        owner_symbols=("balanced_object_after_marker", "json_object_span"),
        projections=(
            "src/ztare/validator/worldmodel_typed_payload.py",
            "src/ztare/common/leaf_workbench_proposals.py",
            "src/ztare/orchestrator/submission_path_helpers.py",
        ),
        tests=(
            "tests/validator/test_worldmodel_typed_payload.py",
            "tests/test_leaf_workbench_contract.py",
        ),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Balanced extraction of JSON/control blocks from model text; regex fallbacks stay out of policy.",
    ),
    ProjectionOwner(
        concept_id="artifact_ref_membrane",
        owner_module="ztare.common.artifact_refs",
        owner_file="src/ztare/common/artifact_refs.py",
        owner_symbols=(
            "normalize_artifact_ref",
            "resolve_project_artifact_ref",
            "missing_project_artifact_refs",
        ),
        projections=(
            "src/ztare/common/briefing_pack.py",
            "src/ztare/common/dispatch_model.py",
            "src/ztare/common/visible_workbench_cli.py",
            "src/ztare/validator/core/candidate_preflight.py",
        ),
        tests=(
            "tests/common/test_artifact_refs.py",
            "tests/test_dispatch_model.py",
            "tests/validator/test_candidate_preflight.py",
        ),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Project-local artifact refs must resolve in the authority project before they can support receipts.",
    ),
    ProjectionOwner(
        concept_id="retry_contract",
        owner_module="ztare.orchestrator.retry_contract",
        owner_file="src/ztare/orchestrator/retry_contract.py",
        owner_symbols=("RetryContractSurface", "render_retry_contract_surface"),
        projections=(
            "src/ztare/orchestrator/submission_path_helpers.py",
            "src/ztare/worldmodel/retry_surface.py",
        ),
        tests=("tests/orchestrator/test_theorem_packet_prompting.py",),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Shared R1 retry envelope; substrate adapters own carrier details.",
    ),
    ProjectionOwner(
        concept_id="boundary_cegar_automaton",
        owner_module="ztare.common.sealed_boundary_cegar",
        owner_file="src/ztare/common/sealed_boundary_cegar.py",
        owner_symbols=("BOUNDARY_CEGAR_CHART", "LOWERABILITY_BLOCKED_SCHEMA"),
        projections=(
            "src/ztare/common/control_state_machine.py",
            "src/ztare/orchestrator/briefing_providers/leaf_workbench.py",
            "src/ztare/worldmodel/retry_surface.py",
            "src/ztare/common/visible_workbench_cli.py",
            "src/ztare/validator/worldmodel_typed_payload.py",
        ),
        tests=(
            "tests/common/test_control_state_machine.py",
            "tests/common/test_sealed_boundary_cegar.py",
            "tests/common/test_visible_workbench_cli.py",
            "tests/orchestrator/test_theorem_packet_prompting.py",
        ),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Boundary states, lowerability, and tool-gap lifecycle.",
    ),
    ProjectionOwner(
        concept_id="control_receipt_read_model",
        owner_module="ztare.common.control_state_machine",
        owner_file="src/ztare/common/control_state_machine.py",
        owner_symbols=(
            "CONTROL_RECEIPT_MARKERS",
            "control_receipt_rows",
            "control_receipt_payloads",
            "executed_morphism_ids_from_receipts",
        ),
        projections=(
            "src/ztare/validator/worldmodel_typed_payload.py",
            "src/ztare/common/leaf_workbench_executor.py",
            "src/ztare/validator/core/candidate_preflight.py",
            "src/ztare/validator/core/repair_preflight.py",
            "src/ztare/validator/autoresearch_loop.py",
            "src/ztare/worldmodel/retry_surface.py",
        ),
        tests=(
            "tests/common/test_control_state_machine.py",
            "tests/validator/test_candidate_preflight.py",
            "tests/validator/test_worldmodel_typed_payload.py",
        ),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes=(
            "Single read model for raw JSON control_receipts and rendered marker "
            "blocks. Callers may render markers, but policy must consume typed rows."
        ),
    ),
    ProjectionOwner(
        concept_id="strategy_card_decision_membrane",
        owner_module="ztare.research_director.strategy_decision_policy",
        owner_file="src/ztare/research_director/strategy_decision_policy.py",
        owner_symbols=("StrategyCardBatchSubmission", "submit_strategy_card_batch"),
        projections=(
            "src/ztare/research_director/strategy_office.py",
            "src/ztare/common/leaf_workbench_proposals.py",
            "src/ztare/worldmodel/residual_repair.py",
            "src/ztare/worldmodel/level_transfer_repair.py",
            "src/ztare/worldmodel/search_control_repair.py",
        ),
        tests=(
            "tests/test_worldmodel_p0.py",
            "tests/test_leaf_workbench_contract.py",
        ),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Single write membrane for experiment and tool-synthesis cards.",
    ),
    ProjectionOwner(
        concept_id="tool_synthesis_contract",
        owner_module="ztare.common.tool_synthesis_contract",
        owner_file="src/ztare/common/tool_synthesis_contract.py",
        owner_symbols=("classify_tool_target", "tool_synthesis_card", "validate_tool_synthesis_card"),
        projections=(
            "src/ztare/common/leaf_workbench_proposals.py",
            "src/ztare/research_director/strategy_office.py",
        ),
        tests=("tests/test_leaf_workbench_contract.py",),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Mutable-sensor classification and tool-synthesis card shape.",
    ),
    ProjectionOwner(
        concept_id="leaf_workbench_contract",
        owner_module="ztare.common.leaf_workbench_contract",
        owner_file="src/ztare/common/leaf_workbench_contract.py",
        owner_symbols=("DEFAULT_LEAF_WORKBENCH_CONTRACT", "render_leaf_workbench_contract_prompt"),
        projections=(
            "src/ztare/common/leaf_workbench_executor.py",
            "src/ztare/common/visible_workbench_actions.py",
            "src/ztare/common/visible_workbench_cli.py",
            "src/ztare/orchestrator/briefing_providers/leaf_workbench.py",
            "src/ztare/worldmodel/leaf_workbench.py",
        ),
        tests=(
            "tests/test_leaf_workbench_contract.py",
            "tests/common/test_visible_workbench_actions.py",
            "tests/common/test_visible_workbench_cli.py",
        ),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Workbench capability identity, receipts, and proposal shape.",
    ),
    ProjectionOwner(
        concept_id="leaf_workbench_executor",
        owner_module="ztare.common.leaf_workbench_executor",
        owner_file="src/ztare/common/leaf_workbench_executor.py",
        owner_symbols=(
            "execute_unique_boundary_morphism_chain",
            "leaf_workbench_action_request_retry_message",
            "leaf_workbench_receipt_preflight_message",
        ),
        projections=(
            "src/ztare/validator/core/repair_preflight.py",
            "src/ztare/common/visible_workbench_cli.py",
            "src/ztare/worldmodel/retry_surface.py",
        ),
        tests=(
            "tests/validator/test_pre_judge_gate_harness.py",
            "tests/orchestrator/test_theorem_packet_prompting.py",
        ),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Parent-kernel execution of registered workbench action requests.",
    ),
    ProjectionOwner(
        concept_id="subscription_agent_runtime",
        owner_module="ztare.common.subscription_agent_runtime",
        owner_file="src/ztare/common/subscription_agent_runtime.py",
        owner_symbols=(
            "CODEX_SANDBOX_SEALED_COMPLETION",
            "CODEX_SANDBOX_VISIBLE_WORKBENCH",
            "build_subscription_agent_command",
        ),
        projections=("src/ztare/common/dispatch_model.py",),
        tests=("tests/test_dispatch_model.py",),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Subscription CLI profiles and sandbox lowering.",
    ),
    ProjectionOwner(
        concept_id="agentic_briefing_pack",
        owner_module="ztare.common.briefing_pack",
        owner_file="src/ztare/common/briefing_pack.py",
        owner_symbols=("BriefingPackRequest", "build_briefing_pack"),
        projections=(
            "src/ztare/common/dispatch_model.py",
            "src/ztare/common/ask_spec.py",
            "src/ztare/orchestrator/mutator_briefing.py",
            "src/ztare/common/visible_workbench_cli.py",
        ),
        tests=("tests/test_dispatch_model.py",),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Agentic TASK/ATTENTION/RECORDS/TOOLS/MANIFEST renderer.",
    ),
    ProjectionOwner(
        concept_id="visible_workbench_source_membrane",
        owner_module="ztare.common.projection_owner_registry",
        owner_file="src/ztare/common/projection_owner_registry.py",
        owner_symbols=("VISIBLE_WORKBENCH_SOURCE_REFS",),
        projections=(
            "src/ztare/common/dispatch_model.py",
            "src/ztare/common/briefing_pack.py",
        ),
        tests=("tests/common/test_projection_owner_registry.py",),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes=(
            "Curated source files staged into visible workbench. This is a "
            "capability membrane, not a transitive import graph."
        ),
    ),
    ProjectionOwner(
        concept_id="mutator_briefing_core",
        owner_module="ztare.orchestrator.mutator_briefing",
        owner_file="src/ztare/orchestrator/mutator_briefing.py",
        owner_symbols=("BriefingProvider", "render_default_briefing_context"),
        projections=(
            "src/ztare/orchestrator/briefing_projection.py",
            "src/ztare/orchestrator/briefing_attention.py",
            "src/ztare/orchestrator/briefing_providers/contract_rules.py",
            "src/ztare/orchestrator/briefing_providers/r1_pattern_warning.py",
            "src/ztare/orchestrator/briefing_providers/strategy_experiments.py",
            "src/ztare/orchestrator/briefing_providers/leaf_workbench.py",
            "src/ztare/orchestrator/briefing_providers/worldmodel_committee.py",
            "src/ztare/orchestrator/briefing_providers/tried_failed_digest.py",
        ),
        tests=(
            "tests/orchestrator/test_mutator_briefing.py",
            "tests/orchestrator/test_briefing_projection.py",
            "tests/orchestrator/test_briefing_attention.py",
        ),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="API briefing core, provider projection, attention, and projection receipts.",
    ),
    ProjectionOwner(
        concept_id="worldmodel_prompt_surfaces",
        owner_module="ztare.common.projection_owner_registry",
        owner_file="src/ztare/common/projection_owner_registry.py",
        owner_symbols=("PROJECTION_OWNERS",),
        projections=(
            "src/ztare/common/briefing_pack.py",
            "src/ztare/worldmodel/retry_surface.py",
            "src/ztare/worldmodel/leaf_workbench.py",
            "src/ztare/validator/worldmodel_typed_payload.py",
            "src/ztare/validator/core/worldmodel_prompt_context.py",
            "src/ztare/orchestrator/submission_path_helpers.py",
            "src/ztare/orchestrator/briefing_providers/contract_rules.py",
            "src/ztare/orchestrator/briefing_providers/r1_pattern_warning.py",
            "src/ztare/orchestrator/briefing_providers/strategy_experiments.py",
            "src/ztare/orchestrator/briefing_providers/leaf_workbench.py",
            "src/ztare/orchestrator/briefing_providers/worldmodel_committee.py",
            "src/ztare/worldmodel/operator_implement.py",
        ),
        tests=(
            "tests/test_dispatch_model.py",
            "tests/orchestrator/test_theorem_packet_prompting.py",
            "tests/orchestrator/test_mutator_briefing.py",
            "tests/orchestrator/test_briefing_projection.py",
            "tests/orchestrator/test_briefing_attention.py",
            "tests/validator/test_pre_judge_gate_harness.py",
            "tests/validator/test_worldmodel_typed_payload.py",
        ),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Known brittle prompt/projection surfaces for ARC worldmodel runs.",
    ),
    ProjectionOwner(
        concept_id="dispatch_model",
        owner_module="ztare.common.dispatch_model",
        owner_file="src/ztare/common/dispatch_model.py",
        owner_symbols=("dispatch_model", "dispatch_call_text", "resolve_agent_execution_mode"),
        projections=(
            "src/ztare/validator/autoresearch_loop.py",
            "src/ztare/research_director/strategy_office.py",
        ),
        tests=("tests/test_dispatch_model.py",),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Transport selection and pack staging; consumes contracts and runtime profiles.",
    ),
    ProjectionOwner(
        concept_id="visible_workbench_routing",
        owner_module="ztare.common.visible_workbench_actions",
        owner_file="src/ztare/common/visible_workbench_actions.py",
        owner_symbols=("visible_workbench_action_routes", "route_visible_workbench_action_request"),
        projections=(
            "src/ztare/common/visible_workbench_cli.py",
            "src/ztare/common/briefing_pack.py",
            "src/ztare/common/leaf_workbench_python.py",
            "src/ztare/common/worldmodel_carrier_purity.py",
        ),
        tests=(
            "tests/common/test_visible_workbench_actions.py",
            "tests/common/test_visible_workbench_cli.py",
            "tests/test_dispatch_model.py",
        ),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="In-turn visible tool routing and parent-kernel routing.",
    ),
    ProjectionOwner(
        concept_id="patch_base_identity",
        owner_module="ztare.common.patch_base_identity",
        owner_file="src/ztare/common/patch_base_identity.py",
        owner_symbols=("resolve_patch_base_ref", "verify_patch_base_digest"),
        projections=(
            "src/ztare/worldmodel/patch_carrier_contract.py",
            "src/ztare/validator/core/repair_preflight.py",
        ),
        tests=("tests/validator/test_pre_judge_gate_harness.py",),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Project-relative patch-base refs and full-digest identity checks.",
    ),
    ProjectionOwner(
        concept_id="worldmodel_induction_tools",
        owner_module="ztare.worldmodel.spec_abduction",
        owner_file="src/ztare/worldmodel/spec_abduction.py",
        owner_symbols=("AbductionResult", "abduce_spec"),
        projections=(
            "src/ztare/worldmodel/spec_catalog.py",
            "src/ztare/worldmodel/goal_abduction.py",
            "src/ztare/worldmodel/grid_dsl.py",
            "src/ztare/worldmodel/episode_log.py",
            "src/ztare/worldmodel/patch_carrier_contract.py",
            "src/ztare/worldmodel/operator_implement.py",
        ),
        tests=(
            "tests/test_worldmodel_p0.py",
            "tests/test_worldmodel_patch_base_carrier.py",
        ),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="ARC worldmodel law, goal, catalog, and carrier induction surfaces.",
    ),
    ProjectionOwner(
        concept_id="candidate_first_payload_policy",
        owner_module="ztare.common.candidate_first_policy",
        owner_file="src/ztare/common/candidate_first_policy.py",
        owner_symbols=("candidate_first_empty_candidate_decision", "candidate_first_policy_text"),
        projections=("src/ztare/validator/worldmodel_typed_payload.py",),
        tests=("tests/validator/test_worldmodel_typed_payload.py",),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Whether a final worldmodel payload may omit executable code.",
    ),
    ProjectionOwner(
        concept_id="candidate_preflight_registry",
        owner_module="ztare.validator.core.candidate_preflight",
        owner_file="src/ztare/validator/core/candidate_preflight.py",
        owner_symbols=("PreflightRule", "run_candidate_preflights", "run_worldmodel_control_only_preflights"),
        projections=(
            "src/ztare/validator/core/repair_preflight.py",
            "src/ztare/validator/core/pre_judge_gate.py",
        ),
        tests=("tests/validator/test_pre_judge_gate_harness.py",),
        doc_refs=("docs/concepts/arc_agi_3_system.md",),
        notes="Ordered candidate/control compatibility preflights before authority gates.",
    ),
)


def projection_owner(concept_id: str) -> ProjectionOwner | None:
    for owner in PROJECTION_OWNERS:
        if owner.concept_id == concept_id:
            return owner
    return None


def projection_blast_radius(concept_id: str) -> tuple[str, ...]:
    owner = projection_owner(concept_id)
    return owner.all_paths() if owner is not None else ()


def validate_projection_owner_registry(
    *,
    repo_root: str | Path,
    owners: Iterable[ProjectionOwner] = PROJECTION_OWNERS,
) -> list[str]:
    root = Path(repo_root)
    failures: list[str] = []
    seen: set[str] = set()
    visible_seen: set[str] = set()
    for rel in VISIBLE_WORKBENCH_SOURCE_REFS:
        if rel in visible_seen:
            failures.append(f"visible_workbench_source_membrane: duplicate source {rel}")
        visible_seen.add(rel)
        if not (root / rel).is_file():
            failures.append(f"visible_workbench_source_membrane: missing source {rel}")
    for owner in owners:
        if owner.concept_id in seen:
            failures.append(f"duplicate concept_id: {owner.concept_id}")
        seen.add(owner.concept_id)
        for rel in owner.all_paths():
            if not (root / rel).exists():
                failures.append(f"{owner.concept_id}: missing path {rel}")
        try:
            module = __import__(owner.owner_module, fromlist=["*"])
        except Exception as exc:  # noqa: BLE001
            failures.append(
                f"{owner.concept_id}: cannot import {owner.owner_module}: "
                f"{type(exc).__name__}: {exc}"
            )
            continue
        for symbol in owner.owner_symbols:
            if not hasattr(module, symbol):
                failures.append(
                    f"{owner.concept_id}: missing owner symbol "
                    f"{owner.owner_module}.{symbol}"
                )
    return failures
