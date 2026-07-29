"""The single public orchestration inlet for frontier AxiomPack campaigns."""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence

from ztare.common.leaf_workbench_environment import resolve_leaf_workbench_environment
from ztare.leanmill.adapter_forge import AdapterGap, AdapterGapRequired
from ztare.leanmill.axiompack_leaf_workbench import AXIOMPACK_LEAF_WORKBENCH_CONTRACT
from ztare.leanmill.authority_slot import read_bounded_json_authority_slot
from ztare.leanmill.common import read_json, write_json_atomic, write_text_atomic
from ztare.leanmill.context_epoch import (
    admit_rebuilt_context_epoch,
    propose_context_epoch,
)
from ztare.leanmill.deterministic_frontier_campaign import run_deterministic_frontier_campaign
from ztare.leanmill.evidence_theory_context import (
    EvidenceTheoryContext,
    load_evidence_theory_context,
    save_evidence_theory_context,
)
from ztare.leanmill.exploration_budget import (
    BudgetPreferenceCompilation,
    BudgetExceeded,
    BudgetStopReceipt,
    ExplorationBudget,
    ExplorationBudgetLedger,
    compile_budget_preference,
    render_budget_yaml,
)
from ztare.leanmill.finite_theory_context import (
    FormalTheoryContext,
    build_formal_theory_context,
    load_formal_theory_context,
    save_formal_theory_context,
)
from ztare.leanmill.frontier_blueprint import (
    FrontierExplorationBrief,
    FrontierTheoryBlueprint,
    cold_navigator_manifest,
    navigator_selection_mode,
    presentation_size_bounds,
    frontier_objective_contract,
)
from ztare.leanmill.frontier_blueprint_compiler import (
    DraftFn,
    ReviewFn,
    compile_frontier_blueprint,
    compile_structure_first_blueprint,
)
from ztare.leanmill.frontier_campaign import (
    FrontierCampaignPacket,
    SignedFrontierCampaign,
    packet_for_context,
    validate_campaign_artifact_binding,
)
from ztare.leanmill.frontier_campaign_definition import FrontierCampaignDefinition
from ztare.leanmill.theory_adapter_registry import resolve_theory_adapter_module
from ztare.leanmill.theory_campaign_journal import (
    TheoryCampaignEvent,
    TheoryCampaignJournal,
)
from ztare.leanmill.theory_conflict_ledger import (
    TheoryConflictLedger,
    open_theory_conflict_ledger,
    zero_residual_conflict_receipt,
)
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    TheorySignature,
    content_hash,
    logical_coordinate_hash,
)
from ztare.leanmill.theory_language import (
    TheoryLanguageExpansionRequest,
    compile_theory_language_expansion,
)
from ztare.leanmill.theory_lineage_synthesis import (
    compose_selected_language_expansion,
    lineage_request_matches_context,
)
from ztare.leanmill.theory_navigator import reject_all_sequence_receipt
from ztare.leanmill.theory_program import TheoryProgram
from ztare.leanmill.typed_axiom_proposal import TypedAxiomProposal


PacketSigner = Callable[[FrontierCampaignPacket], SignedFrontierCampaign]
NavigatorFn = Callable[..., Mapping[str, Any]]
BudgetCompilerFn = Callable[[str], Mapping[str, Any] | str]
NavigationOwnershipFn = Callable[[Path, int, str], Any]
_MAX_CONSTRUCTION_RECOVERY_AUTHORITY_SLOT_BYTES = 64_000_000


def _freeze_theory_conflict_memory(
    context: Any,
    directory: Path,
    *,
    epoch: int,
) -> tuple[TheoryConflictLedger, tuple[Mapping[str, Any], ...]]:
    """Freeze the cross-attempt no-good view before this epoch's first call."""

    ledger = open_theory_conflict_ledger(
        context, directory.parent / "theory_conflicts.jsonl"
    )
    snapshot_path = directory / f"theory_conflict_memory.epoch-{epoch:03d}.json"
    existing = read_json(snapshot_path, None)
    if snapshot_path.exists():
        if not isinstance(existing, Mapping):
            raise ValueError("theory conflict memory snapshot is unreadable")
        core = {
            key: value for key, value in existing.items() if key != "snapshot_sha256"
        }
        if (
            existing.get("schema") != "leanmill.theory_conflict_memory_snapshot.v1"
            or existing.get("context_hash") != context.context_hash
            or existing.get("snapshot_sha256") != content_hash(core)
        ):
            raise ValueError("theory conflict memory snapshot does not replay")
        rows = existing.get("conflicts")
        if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
            raise ValueError("theory conflict memory snapshot has malformed rows")
        return ledger, tuple(dict(row) for row in rows)
    rows = ledger.navigator_rows()
    core = {
        "schema": "leanmill.theory_conflict_memory_snapshot.v1",
        "context_hash": context.context_hash,
        "context_epoch": epoch,
        "conflicts": rows,
        "conflict_count": len(rows),
        "authority": "host_witness_replay",
    }
    write_json_atomic(
        snapshot_path, {**core, "snapshot_sha256": content_hash(core)}
    )
    return ledger, tuple(rows)


def _learn_navigation_conflicts(
    context: Any,
    navigation: Mapping[str, Any],
    ledger: TheoryConflictLedger,
    journal: TheoryCampaignJournal,
    *,
    attempt_id: str,
    campaign_id: str,
    epoch: int,
) -> int:
    """Deposit every presentation whose zero residual replays on the host."""

    existing = {
        (event.subject_ids[0], event.output_refs[0])
        for event in journal.replay()
        if event.event_type == "conflict_learned"
        and event.context_hash == context.context_hash
        and event.subject_ids
        and event.output_refs
    }
    learned = 0
    trace_rows = list(navigation.get("trace") or ())
    for lineage in navigation.get("lineages") or ():
        if isinstance(lineage, Mapping) and isinstance(
            lineage.get("navigation"), Mapping
        ):
            trace_rows.extend(lineage["navigation"].get("trace") or ())
    for trace_row in trace_rows:
        if not isinstance(trace_row, Mapping) or trace_row.get("decision") != "candidate_rejected":
            continue
        rejection = trace_row.get("rejection")
        if not isinstance(rejection, Mapping):
            continue
        try:
            receipt = zero_residual_conflict_receipt(context, rejection)
        except ValueError:
            # A refusal may be agent-owned, but a no-good is host-owned: only
            # exact residual replay can turn it into memory.
            continue
        clause = ledger.learn(receipt)
        witness_ref = str(receipt["witness_ref"])
        if (clause.signature, witness_ref) in existing:
            continue
        journal.append(
            TheoryCampaignEvent(
                attempt_id=attempt_id,
                campaign_id=campaign_id,
                epoch=epoch,
                context_hash=context.context_hash,
                event_type="conflict_learned",
                subject_ids=(clause.signature,),
                input_refs=tuple(
                    sorted(str(row) for row in rejection.get("formula_ids") or ())
                ),
                output_refs=(witness_ref,),
                evidence_status="witnessed",
                authority="deterministic_residual_replay",
            )
        )
        existing.add((clause.signature, witness_ref))
        learned += 1
    return learned


def _refresh_theory_conflict_memory_after_wave(
    context: Any,
    directory: Path,
    ledger: TheoryConflictLedger,
    *,
    epoch: int,
    search_wave: int,
) -> None:
    """Expose completed-wave no-goods without leaking them across siblings."""

    path = directory / f"theory_conflict_memory.epoch-{epoch:03d}.json"
    prior = read_json(path, None)
    rows = ledger.navigator_rows()
    if not isinstance(prior, Mapping) or prior.get("conflicts") == rows:
        return
    parent = str(prior.get("snapshot_sha256") or "")
    archived = directory / (
        f"theory_conflict_memory.epoch-{epoch:03d}."
        f"before-wave-{search_wave + 1:03d}.{parent.split(':')[-1][:16]}.json"
    )
    if not archived.exists():
        path.replace(archived)
    core = {
        "schema": "leanmill.theory_conflict_memory_snapshot.v1",
        "context_hash": context.context_hash,
        "context_epoch": epoch,
        "search_wave": search_wave + 1,
        "parent_snapshot_sha256": parent,
        "conflicts": rows,
        "conflict_count": len(rows),
        "authority": "completed_search_wave_host_replay",
    }
    write_json_atomic(path, {**core, "snapshot_sha256": content_hash(core)})


def compile_campaign_brief(
    definition: FrontierCampaignDefinition,
    *,
    budget: str | Mapping[str, Any] | ExplorationBudget | None = None,
    budget_compiler_fn: BudgetCompilerFn | None = None,
) -> tuple[
    FrontierExplorationBrief,
    ExplorationBudget,
    BudgetPreferenceCompilation,
]:
    """Lower one campaign definition exactly as both preflight and execution do."""

    from ztare.leanmill.exploration_budget import budget_to_user_mapping

    budget_input = budget
    if budget_input is None:
        budget_input = budget_to_user_mapping(
            definition.budget,
            delegated_stop_instruction=definition.delegated_stop_instruction,
        )
    budget_contract, budget_preference = compile_budget_preference(
        budget_input,
        direction_text=definition.direction,
        compiler_fn=budget_compiler_fn,
    )
    brief = definition.to_brief()
    return (
        replace(
            brief,
            resource_envelope={
                **dict(brief.resource_envelope),
                "budget_contract": budget_contract.to_json(),
                "budget_preference_compilation": budget_preference.to_json(),
            },
        ),
        budget_contract,
        budget_preference,
    )


def _campaign_reject_all_sequence(
    directory: Path,
    *,
    campaign_id: str,
    context_hash: str,
    current_navigation: Mapping[str, Any],
) -> dict[str, Any]:
    """Reduce sibling attempt outcomes for one frozen campaign/context."""

    outcomes: list[tuple[str, bool, Mapping[str, Any] | None]] = []
    for sibling in directory.parent.iterdir():
        if not sibling.is_dir():
            continue
        events_path = sibling / "events.jsonl"
        if not events_path.is_file():
            continue
        try:
            events = [
                event
                for event in TheoryCampaignJournal(events_path).replay()
                if event.campaign_id == campaign_id
                and event.context_hash == context_hash
                and event.event_type
                in {
                    "finalist_frozen",
                    "navigator_reject_all",
                    "theory_presentation_rejected",
                }
            ]
        except (OSError, ValueError):
            continue
        if not events:
            continue
        navigation = (
            current_navigation
            if sibling == directory
            else dict(read_json(sibling / "run.json", {}).get("navigation") or {})
        )
        has_finalist = bool(navigation.get("finalists"))
        receipt = navigation.get("reject_all_receipt")
        if not has_finalist and not isinstance(receipt, Mapping):
            continue
        outcomes.append((max(event.created_at for event in events), has_finalist, receipt))
    outcomes.sort(key=lambda row: row[0])
    consecutive: list[Mapping[str, Any]] = []
    for _created_at, has_finalist, receipt in outcomes:
        if has_finalist:
            consecutive.clear()
        elif isinstance(receipt, Mapping):
            consecutive.append(receipt)
    return reject_all_sequence_receipt(consecutive)


def _validate_no_candidate_navigation(
    context: Any, navigation: Mapping[str, Any]
) -> None:
    receipt = navigation.get("reject_all_receipt")
    if not isinstance(receipt, Mapping):
        raise ValueError("frontier no-candidate outcome requires reject-all receipt")
    if (
        receipt.get("schema") not in {
            "leanmill.receipted_reject_all.v1",
            "leanmill.receipted_reject_all.v2",
        }
        or receipt.get("context_hash") != context.context_hash
    ):
        raise ValueError("reject-all receipt does not bind the frozen context")
    candidates = receipt.get("rejected_candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("reject-all receipt requires rejected candidates")
    selection_modes = {
        str(row.get("selection_mode") or "compact_axiom_pack")
        for row in candidates
        if isinstance(row, Mapping)
    }
    if len(selection_modes) != 1:
        raise ValueError("reject-all candidates cross navigator selection modes")
    selection_mode = next(iter(selection_modes))
    context_epoch = int(navigation.get("context_epoch", 0))
    max_presentation_size = max(
        len(tuple(row.get("formula_ids") or ()))
        for row in candidates
        if isinstance(row, Mapping)
    )
    environment = resolve_leaf_workbench_environment(
        "axiompack",
        context=context,
        context_epoch=context_epoch,
        selection_mode=selection_mode,
        max_presentation_size=max_presentation_size,
    )
    handler = environment["action_handlers"]["select_theory_presentation"]
    for rejected in candidates:
        if not isinstance(rejected, Mapping):
            raise ValueError("reject-all candidate row is malformed")
        formulas = [str(row) for row in rejected.get("formula_ids") or ()]
        selection_inputs = {"formula_ids": formulas}
        if selection_mode == "theory_program":
            selection_inputs["prediction_formula_ids"] = [
                str(row) for row in rejected.get("prediction_formula_ids") or ()
            ]
        replay = handler(
            ".",
            {"input_refs": selection_inputs},
            None,
            environment["contract"],
        )
        summary = replay["output_summary"]
        residual = dict(
            (summary.get("program_yield") or {}).get("coordinates") or {}
            if rejected.get("selection_mode") == "theory_program"
            else summary.get("residual_yield") or {}
        )
        replay_residual_ids = (
            summary.get("residual_prediction_formula_ids")
            if rejected.get("selection_mode") == "theory_program"
            else summary.get("residual_synergy_formula_ids")
        )
        if selection_mode == "theory_program":
            expected_profile = rejected.get("prediction_profile")
            actual_profile = summary.get("prediction_profile")
            ok = bool(
                replay["receipt_id"] == rejected.get("selection_receipt_id")
                and bool(residual.get("baseline_ref"))
                and rejected.get("rejection_authority")
                == "anonymous_theory_navigator"
                and str(rejected.get("refusal_rationale") or "").strip()
                and isinstance(expected_profile, Mapping)
                and isinstance(actual_profile, Mapping)
                and expected_profile.get("receipt_sha256")
                == actual_profile.get("receipt_sha256")
            )
        else:
            ok = bool(
                replay["receipt_id"] == rejected.get("selection_receipt_id")
                and bool(residual.get("baseline_ref"))
                and float(residual.get("identification_bits", -1.0)) == 0.0
                and not replay_residual_ids
            )
        if not ok:
            raise ValueError("reject-all candidate does not replay its refusal basis")


@dataclass(frozen=True)
class FrontierExplorationRun:
    status: str
    brief_id: str
    attempt_dir: str
    blueprint_id: str = ""
    context_hash: str = ""
    packet_digest: str = ""
    navigation: Mapping[str, Any] | None = None
    adapter_gap: Mapping[str, Any] | None = None
    context_summary: Mapping[str, Any] | None = None
    provider_calls: int = 0
    preparation_provider_calls: int = 0
    budget_digest: str = ""
    budget_stop_receipt: Mapping[str, Any] | None = None
    schema: str = "leanmill.frontier_exploration_run.v1"

    def to_json(self) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "status": self.status,
            "brief_id": self.brief_id,
            "attempt_dir": self.attempt_dir,
            "blueprint_id": self.blueprint_id,
            "context_hash": self.context_hash,
            "packet_digest": self.packet_digest,
            "navigation": dict(self.navigation) if self.navigation is not None else None,
            "adapter_gap": dict(self.adapter_gap) if self.adapter_gap is not None else None,
            "context_summary": dict(self.context_summary) if self.context_summary is not None else None,
            "provider_calls": self.provider_calls,
            "preparation_provider_calls": self.preparation_provider_calls,
            "budget_digest": self.budget_digest,
            "budget_stop_receipt": (
                dict(self.budget_stop_receipt) if self.budget_stop_receipt is not None else None
            ),
        }
        return {**core, "run_digest": content_hash(core)}


def frontier_context_summary(
    context: Any,
    blueprint: FrontierTheoryBlueprint,
    *,
    context_epoch: int,
    proposed_formula_count: int = 0,
    proposed_semantic_profile_count: int = 0,
    language_expansion_requested: bool = False,
    labeled_object_count: int = 0,
) -> dict[str, Any]:
    """One read model for initial runs, resumes, and journal recovery."""

    # The frontier navigator pages a semantic read model on demand.  Do not
    # eagerly enumerate every syntactic presentation while recovering a run.
    generated_node_count = None
    formula_count = len(context.formula_ids)
    return {
        "context_kind": (
            "evidence_incidence"
            if isinstance(context, EvidenceTheoryContext)
            else "formal_model_incidence"
        ),
        "context_epoch": context_epoch,
        "context_exact": context.complete,
        "agent_proposed_formula_count": proposed_formula_count,
        "agent_proposed_semantic_profile_count": proposed_semantic_profile_count,
        "theory_language_expansion_requested": language_expansion_requested,
        "formula_count": formula_count,
        "semantic_formula_profile_count": len(context.semantic_formula_classes()),
        "observational_partition": context.incidence.observational_partition_summary(),
        "accepted_model_count": len(context.object_ids),
        "labeled_model_count": labeled_object_count,
        "generated_theory_node_count": generated_node_count,
        "generated_theory_node_count_policy": "deferred_to_semantic_navigator",
        "unordered_formula_pair_count": formula_count * (formula_count - 1) // 2,
    }


def _context_from_blueprint(blueprint: FrontierTheoryBlueprint):
    module = resolve_theory_adapter_module(blueprint.adapter_id)
    evidence_builder = getattr(module, "build_evidence_context", None)
    if blueprint.mode == "evidence_induced" and callable(evidence_builder):
        return evidence_builder(
            TheorySignature.from_json(blueprint.signature),
            adapter_config=blueprint.adapter_config,
            strata=blueprint.model_or_observation_strata,
        )
    formula_builder = getattr(module, "build_formulas", None)
    universe_builder = getattr(module, "build_model_universe", None)
    if not callable(formula_builder) or not callable(universe_builder):
        raise ValueError("registered adapter lacks formula/model construction for census mode")
    signature = TheorySignature.from_json(blueprint.signature)
    base_axioms = tuple(AxiomFormula.from_json(row) for row in blueprint.base_axioms)
    formulas = formula_builder(
        signature,
        adapter_config=blueprint.adapter_config,
        formula_grammar=blueprint.formula_grammar,
    )
    universe = universe_builder(
        signature,
        strata=blueprint.model_or_observation_strata,
        base_axioms=base_axioms,
        adapter_config=blueprint.adapter_config,
    )
    return build_formal_theory_context(
        signature=signature,
        formulas=formulas,
        universe=universe,
        base_axioms=base_axioms,
    )


def _context_from_snapshot(
    blueprint: FrontierTheoryBlueprint,
    reference: Mapping[str, str],
):
    """Replay and bind an existing complete context to an identical blueprint."""

    path = Path(str(reference["path"]))
    raw = read_json(path, None)
    if not isinstance(raw, Mapping):
        raise ValueError("frozen context snapshot is missing")
    if raw.get("snapshot_sha256") != reference.get("snapshot_sha256"):
        raise ValueError("frozen context snapshot digest differs from campaign YAML")
    if raw.get("schema") == "leanmill.formal_theory_context_snapshot.v1":
        context = load_formal_theory_context(path)
    elif raw.get("schema") == "leanmill.evidence_theory_context.v1":
        context = load_evidence_theory_context(path)
    else:
        raise ValueError("unsupported frozen context snapshot schema")
    if context.context_hash != reference.get("context_hash"):
        raise ValueError("frozen context hash differs from campaign YAML")
    if not context.complete:
        raise ValueError("only complete contexts may be reused as exact campaigns")
    signature = TheorySignature.from_json(blueprint.signature)
    if context.signature.content_hash != signature.content_hash:
        raise ValueError("frozen context signature differs from blueprint")
    expected_base = sorted(
        AxiomFormula.from_json(row).semantic_hash for row in blueprint.base_axioms
    )
    actual_base = sorted(row.semantic_hash for row in context.base_axioms)
    if actual_base != expected_base:
        raise ValueError("frozen context base theory differs from blueprint")
    if isinstance(context, EvidenceTheoryContext):
        if context.adapter_id != blueprint.adapter_id:
            raise ValueError("frozen evidence adapter differs from blueprint")
        module = resolve_theory_adapter_module(blueprint.adapter_id)
        evidence_builder = getattr(module, "build_evidence_context", None)
        if not callable(evidence_builder):
            raise ValueError("frozen evidence adapter cannot replay its context")
        expected_context = evidence_builder(
            signature,
            adapter_config=blueprint.adapter_config,
            strata=blueprint.model_or_observation_strata,
        )
        if context.context_hash != expected_context.context_hash:
            raise ValueError("frozen evidence context differs from blueprint")
    else:
        universe_row = context.universe.to_json()
        if universe_row.get("adapter_id") != blueprint.adapter_id:
            raise ValueError("frozen model adapter differs from blueprint")
        module = resolve_theory_adapter_module(blueprint.adapter_id)
        formulas = module.build_formulas(
            signature,
            adapter_config=blueprint.adapter_config,
            formula_grammar=blueprint.formula_grammar,
        )
        expected_ids = sorted("formula:" + row.semantic_hash for row in formulas)
        if list(context.formula_ids) != expected_ids:
            raise ValueError("frozen formula universe differs from blueprint")
        expected_strata = tuple(
            sorted(
                (dict(row) for row in blueprint.model_or_observation_strata),
                key=lambda row: content_hash(row),
            )
        )
        actual_strata = tuple(
            sorted(
                (dict(row) for row in context.universe.receipt.declared_strata),
                key=lambda row: content_hash(row),
            )
        )
        if actual_strata != expected_strata:
            raise ValueError("frozen model strata differ from blueprint")
        expected_image = blueprint.adapter_config.get("functor_image")
        actual_image = getattr(
            context.universe.receipt, "functor_image_receipt", {}
        )
        if expected_image is not None:
            if not isinstance(actual_image, Mapping):
                raise ValueError("frozen functor image lacks provenance")
            if (
                expected_image.get("source_context_hash")
                != actual_image.get("source_context_hash")
                or expected_image.get("source_object_count")
                != actual_image.get("source_object_count")
                or expected_image.get("canonical_model_count")
                != actual_image.get("canonical_image_model_count")
                or expected_image.get("receipt_sha256")
                != context.universe.receipt.receipt_digest
            ):
                raise ValueError("frozen functor image differs from blueprint")
        elif actual_image:
            raise ValueError("blueprint does not declare its model-universe image")
    return context


def admit_frontier_formula_epoch(
    context: FormalTheoryContext,
    expansion: Mapping[str, Any],
    *,
    journal: TheoryCampaignJournal,
    budget_ledger: ExplorationBudgetLedger,
    directory: Path,
    campaign_id: str,
    attempt_id: str,
    current_epoch: int,
) -> tuple[FormalTheoryContext, TypedAxiomProposal, int, Mapping[str, Any]]:
    """Admit one typed proposal by rebuilding, never mutating, its formal context."""

    rebuilt, proposals, epoch, admissions = admit_frontier_formula_epoch_batch(
        context,
        (expansion,),
        journal=journal,
        budget_ledger=budget_ledger,
        directory=directory,
        campaign_id=campaign_id,
        attempt_id=attempt_id,
        current_epoch=current_epoch,
    )
    return rebuilt, proposals[0], epoch, admissions[0]


def admit_frontier_formula_epoch_batch(
    context: FormalTheoryContext,
    expansions: Sequence[Mapping[str, Any]],
    *,
    journal: TheoryCampaignJournal,
    budget_ledger: ExplorationBudgetLedger,
    directory: Path,
    campaign_id: str,
    attempt_id: str,
    current_epoch: int,
) -> tuple[
    FormalTheoryContext,
    tuple[TypedAxiomProposal, ...],
    int,
    tuple[Mapping[str, Any], ...],
]:
    """Admit one agent-selected formula batch into a single rebuilt epoch."""

    rows = tuple(expansions)
    if not rows:
        raise ValueError("frontier formula batch must be nonempty")
    proposals: list[TypedAxiomProposal] = []
    formula_ids: list[str] = []
    coordinate_hashes: list[str] = []
    evidence_refs: list[str] = []
    known_coordinate_hashes = {
        logical_coordinate_hash(row.axiom.formula)
        for row in context.formula_profiles
    }
    for expansion in rows:
        if expansion.get("source_context_hash") != context.context_hash:
            raise ValueError("frontier formula expansion targets a stale context")
        if int(expansion.get("source_epoch", current_epoch)) != current_epoch:
            raise ValueError("frontier formula expansion targets a stale epoch")
        proposal_row = expansion.get("typed_axiom_proposal")
        if not isinstance(proposal_row, Mapping):
            raise ValueError("frontier formula expansion lacks a typed proposal")
        proposal = TypedAxiomProposal.from_json(proposal_row)
        if proposal.theory_signature_sha256 != context.signature.content_hash:
            raise ValueError("frontier formula proposal changed the frozen signature")
        if expansion.get("typed_proposal_sha256") not in {
            None,
            proposal.content_hash,
        }:
            raise ValueError("frontier formula proposal changed after its host receipt")
        formula_id = "formula:" + proposal.axiom.semantic_hash
        if formula_id != expansion.get("formula_id"):
            raise ValueError("frontier formula proposal changed identity after typecheck")
        if formula_id in context.formula_ids:
            raise ValueError("frontier formula expansion repeats an existing formula")
        coordinate_hash = logical_coordinate_hash(proposal.axiom.formula)
        if coordinate_hash in known_coordinate_hashes:
            raise ValueError(
                "frontier formula expansion repeats an existing logical coordinate"
            )
        proposals.append(proposal)
        formula_ids.append(formula_id)
        coordinate_hashes.append(coordinate_hash)
        evidence_refs.append(str(expansion.get("workbench_receipt_id") or ""))
    if len(set(formula_ids)) != len(formula_ids):
        raise ValueError("frontier formula batch repeats a formula identity")
    if len(set(coordinate_hashes)) != len(coordinate_hashes):
        raise ValueError("frontier formula batch repeats a logical coordinate")

    epoch_proposal = propose_context_epoch(
        journal,
        attempt_id=attempt_id,
        campaign_id=campaign_id,
        context_hash=context.context_hash,
        evidence_refs=evidence_refs,
        proposed_additions=tuple(
            {
                "kind": "typed_frontier_formula",
                "typed_axiom_proposal": proposal.to_json(),
            }
            for proposal in proposals
        ),
    )
    if epoch_proposal is None:
        raise ValueError("frontier formula expansion was not receipted")
    next_epoch = current_epoch + 1
    for index, proposal in enumerate(proposals):
        suffix = "" if len(proposals) == 1 else f".{index:03d}"
        write_json_atomic(
            directory
            / f"typed_formula_proposal.epoch-{next_epoch:03d}{suffix}.json",
            proposal.to_json(),
        )
    write_json_atomic(
        directory / f"context_epoch_proposal.epoch-{next_epoch:03d}.json",
        epoch_proposal.to_json(),
    )
    reservation = budget_ledger.reserve(
        f"context:epoch:{next_epoch}",
        "context",
        {"truth_cells": len(context.object_ids) * len(proposals)},
    )
    try:
        rebuilt = build_formal_theory_context(
            signature=context.signature,
            formulas=tuple(row.axiom for row in context.formula_profiles)
            + tuple(proposal.axiom for proposal in proposals),
            universe=context.universe,
            base_axioms=context.base_axioms,
        )
    except Exception:
        budget_ledger.commit(reservation)
        raise
    budget_ledger.commit(
        reservation,
        {"truth_cells": len(context.object_ids) * len(proposals)},
    )
    event = admit_rebuilt_context_epoch(
        journal,
        epoch_proposal,
        rebuilt,
        attempt_id=attempt_id,
        authority="formal-context-rebuild",
    )
    prior_profiles: dict[int, list[str]] = {}
    for row in context.formula_profiles:
        prior_profiles.setdefault(row.truth_bits, []).append(row.formula_id)
    rebuilt_profiles = {row.formula_id: row for row in rebuilt.formula_profiles}
    batch_profiles: dict[int, list[str]] = {}
    for formula_id in formula_ids:
        profile = rebuilt_profiles[formula_id]
        batch_profiles.setdefault(profile.truth_bits, []).append(formula_id)
    admissions: list[Mapping[str, Any]] = []
    for index, (formula_id, proposal) in enumerate(zip(formula_ids, proposals, strict=True)):
        admitted_profile = rebuilt_profiles[formula_id]
        equivalent_formula_ids = tuple(
            sorted(prior_profiles.get(admitted_profile.truth_bits, ()))
        )
        admission_core = {
            "schema": "leanmill.frontier_formula_epoch_admission.v1",
            "source_context_hash": context.context_hash,
            "target_context_hash": rebuilt.context_hash,
            "source_epoch": current_epoch,
            "target_epoch": event.epoch,
            "formula_id": formula_id,
            "formula_identity_new": True,
            "bounded_semantic_profile_new": not equivalent_formula_ids,
            "equivalent_prior_formula_ids": list(equivalent_formula_ids),
            "typed_proposal_sha256": proposal.content_hash,
            "context_epoch_proposal_id": epoch_proposal.proposal_id,
            "claim_boundary": (
                "formula identity and truth-profile comparison are exact only over "
                "the frozen finite model context"
            ),
        }
        if len(proposals) > 1:
            peers = tuple(
                row
                for row in batch_profiles[admitted_profile.truth_bits]
                if row != formula_id
            )
            admission_core.update(
                {
                    "batch_size": len(proposals),
                    "equivalent_selected_formula_ids": list(peers),
                    "bounded_semantic_coordinate_new": (
                        not equivalent_formula_ids
                        and formula_id
                        == min(batch_profiles[admitted_profile.truth_bits])
                    ),
                }
            )
        admission = {
            **admission_core,
            "receipt_sha256": content_hash(admission_core),
        }
        suffix = "" if len(proposals) == 1 else f".{index:03d}"
        write_json_atomic(
            directory
            / f"frontier_formula_epoch_admission.epoch-{event.epoch:03d}{suffix}.json",
            admission,
        )
        admissions.append(admission)
    save_formal_theory_context(
        rebuilt,
        directory / f"formal_context.epoch-{event.epoch:03d}.json",
    )
    save_formal_theory_context(rebuilt, directory / "formal_context.json")
    return rebuilt, tuple(proposals), event.epoch, tuple(admissions)


def freeze_frontier_formula_successor_request(
    directory: Path,
    navigation: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze an outbound epoch request without moving source-epoch finalists."""

    expansion = navigation.get("expansion_proposal")
    finalists = navigation.get("finalists")
    if not isinstance(expansion, Mapping) or not isinstance(finalists, list) or not finalists:
        raise ValueError("successor request requires a formula proposal and source-epoch finalist")
    source_context_hash = str(expansion.get("source_context_hash") or "")
    source_epoch = int(expansion.get("source_epoch", 0))
    if not source_context_hash or str(navigation.get("context_hash") or "") != source_context_hash:
        raise ValueError("successor request context identity does not match its finalists")
    if int(navigation.get("context_epoch", source_epoch)) != source_epoch:
        raise ValueError("successor request epoch identity does not match its finalists")
    for finalist in finalists:
        if not isinstance(finalist, Mapping) or not finalist.get("node_id"):
            raise ValueError("successor request contains a malformed finalist")
        if str(finalist.get("context_hash", source_context_hash)) != source_context_hash:
            raise ValueError("successor request would carry a finalist across contexts")
        if int(finalist.get("context_epoch", source_epoch)) != source_epoch:
            raise ValueError("successor request would carry a finalist across epochs")
    core = {
        "schema": "leanmill.frontier_formula_successor_request.v1",
        "source_context_hash": source_context_hash,
        "source_epoch": source_epoch,
        "target_epoch": source_epoch + 1,
        "source_finalist_node_ids": [str(row["node_id"]) for row in finalists],
        "expansion_proposal": dict(expansion),
        "status": "successor_epoch_required",
        "claim_boundary": (
            "the source finalists remain bound to their frozen context; the formula "
            "request has proposal authority only in a successor epoch"
        ),
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    filename = f"frontier_formula_successor_request.epoch-{source_epoch + 1:03d}.json"
    write_json_atomic(directory / filename, receipt)
    result = dict(navigation)
    result["epoch_transition"] = {
        "status": "successor_epoch_required",
        "request_ref": filename,
        "receipt_sha256": receipt["receipt_sha256"],
    }
    return result


def packet_for_frontier_context(
    blueprint: FrontierTheoryBlueprint,
    context: Any,
    *,
    campaign_id: str,
    formula_proposal_hashes: Sequence[str] = (),
    context_epoch: int = 0,
) -> FrontierCampaignPacket:
    """Bind a reviewed blueprint to its current immutable semantic epoch."""

    formula_contract: Mapping[str, Any] = blueprint.formula_grammar
    if formula_proposal_hashes:
        formula_contract = {
            "schema": "leanmill.frontier_formula_epoch.v1",
            "seed_grammar": dict(blueprint.formula_grammar),
            "typed_formula_proposal_sha256s": list(formula_proposal_hashes),
            "context_epoch": context_epoch,
        }
    return packet_for_context(
        campaign_id=campaign_id,
        blueprint_id=blueprint.blueprint_id,
        eigenquestion=blueprint.eigenquestion,
        context=context,
        formula_grammar=formula_contract,
        pack_arity=blueprint.pack_arity,
        navigator_contract=AXIOMPACK_LEAF_WORKBENCH_CONTRACT,
        sealed_context_manifest_digest=blueprint.sealed_evidence_manifest_digest,
        query_budget=blueprint.query_budget,
        stop_rule=blueprint.stop_rule,
        collapse_controls=blueprint.collapse_controls,
        authority_refs=blueprint.authority_refs,
        mode=blueprint.mode,
        model_strata=blueprint.model_or_observation_strata,
        codec_versions=blueprint.codec_versions,
        presentation_size=(
            dict(blueprint.navigator_contract["presentation_size"])
            if "presentation_size" in blueprint.navigator_contract
            else None
        ),
    )


@dataclass(frozen=True)
class FrontierNavigationDrive:
    context: Any
    context_epoch: int
    formula_proposal_hashes: tuple[str, ...]
    semantically_new_formula_count: int
    packet: FrontierCampaignPacket
    navigation: Mapping[str, Any]


def freeze_frontier_context_packet(
    directory: Path,
    blueprint: FrontierTheoryBlueprint,
    context: Any,
    *,
    campaign_id: str,
    context_epoch: int,
    formula_proposal_hashes: Sequence[str],
    packet_signer: PacketSigner,
) -> FrontierCampaignPacket:
    """Sign and publish one immutable context epoch."""

    packet = packet_for_frontier_context(
        blueprint,
        context,
        campaign_id=campaign_id,
        formula_proposal_hashes=formula_proposal_hashes,
        context_epoch=context_epoch,
    )
    signed = packet_signer(packet)
    if signed.packet.digest != packet.digest:
        raise ValueError("packet signer changed the frozen campaign")
    row = signed.to_json()
    write_json_atomic(directory / f"campaign.epoch-{context_epoch:03d}.json", row)
    write_json_atomic(directory / "campaign.json", row)
    return packet


def _write_navigation_checkpoint(
    directory: Path,
    context: Any,
    *,
    context_epoch: int,
    trace: Sequence[Mapping[str, Any]],
    provider_calls: int,
    formula_proposal_hashes: Sequence[str],
) -> None:
    write_json_atomic(
        directory / "navigation_epoch_checkpoint.json",
        {
            "schema": "leanmill.frontier_navigation_epoch_checkpoint.v1",
            "context_hash": context.context_hash,
            "context_epoch": context_epoch,
            "trace": [dict(row) for row in trace],
            "provider_calls": provider_calls,
            "typed_formula_proposal_sha256s": list(formula_proposal_hashes),
        },
    )


def _lineage_synthesis_route(
    synthesis: Mapping[str, Any],
    context: Any,
    context_epoch: int,
) -> tuple[str, list[dict[str, Any]]]:
    core = {key: value for key, value in synthesis.items() if key != "receipt_sha256"}
    if (
        synthesis.get("receipt_sha256") != content_hash(core)
        or synthesis.get("context_hash") != context.context_hash
        or int(synthesis.get("context_epoch", -1)) != context_epoch
    ):
        raise ValueError("lineage synthesis does not bind this context")
    route = str(synthesis.get("route") or "")
    if route not in {
        "admit_formulas",
        "escalate_language",
        "defer_all",
        "proceed_boundary",
        "continue_search",
    }:
        raise ValueError("lineage synthesis returned an unknown route")
    expansions: list[dict[str, Any]] = []
    if route == "admit_formulas":
        for selected in synthesis.get("selected_requests") or ():
            if not isinstance(selected, Mapping) or not isinstance(
                selected.get("proposal"), Mapping
            ):
                raise ValueError("lineage synthesis selected a malformed formula request")
            expansions.append(dict(selected["proposal"]))
    if route == "admit_formulas" and not expansions:
        raise ValueError("formula-admission synthesis selected no formula requests")
    return route, expansions


def _resolve_workbench_evidence_receipts(
    directory: Path,
    navigation: Mapping[str, Any],
    evidence_refs: Sequence[str],
    *,
    context: Any | None = None,
) -> list[dict[str, Any]]:
    """Resolve request refs to governed trace or frozen-context evidence.

    A language request may cite both workbench outputs and governed lifecycle
    evidence surfaced in its trace, as well as artifacts named by an immutable
    evidence-context payload. Resolution remains attempt-local and does not
    grant any cited item authority beyond its recorded category.
    """

    wanted = {str(row) for row in evidence_refs}
    found: dict[str, dict[str, Any]] = {}
    navigations = [navigation]
    for path in sorted(directory.glob("run.wave-*.json")):
        row = read_json(path, {})
        if isinstance(row, Mapping) and isinstance(row.get("navigation"), Mapping):
            navigations.append(row["navigation"])
    for source in navigations:
        for carried in source.get("carried_evidence_receipts") or ():
            if not isinstance(carried, Mapping) or not isinstance(
                carried.get("receipt"), Mapping
            ):
                raise ValueError("carried language evidence is malformed")
            evidence_ref = str(carried.get("evidence_ref") or "")
            receipt = dict(carried["receipt"])
            receipt_id = str(receipt.get("receipt_id") or "")
            receipt_sha = str(receipt.get("receipt_sha256") or "")
            if receipt_id:
                core = {
                    key: value for key, value in receipt.items() if key != "receipt_id"
                }
                verified = receipt_id == "sha256:" + content_hash(core)
            elif receipt_sha:
                core = {
                    key: value
                    for key, value in receipt.items()
                    if key != "receipt_sha256"
                }
                verified = receipt_sha == content_hash(core)
            else:
                verified = False
            if (
                evidence_ref in wanted
                and evidence_ref in {receipt_id, receipt_sha}
                and verified
            ):
                prior = found.get(evidence_ref)
                if prior is not None and prior != receipt:
                    raise ValueError("carried language evidence conflicts")
                found[evidence_ref] = receipt
        traces = [source.get("trace") or ()]
        traces.extend(
            (lineage.get("navigation") or {}).get("trace") or ()
            for lineage in source.get("lineages") or ()
            if isinstance(lineage, Mapping)
        )
        for trace in traces:
            for event in trace:
                receipt = event.get("receipt") if isinstance(event, Mapping) else None
                if not isinstance(receipt, Mapping):
                    continue
                receipt_id = str(receipt.get("receipt_id") or "")
                receipt_sha = str(receipt.get("receipt_sha256") or "")
                if receipt_id:
                    core = {
                        key: value
                        for key, value in receipt.items()
                        if key != "receipt_id"
                    }
                    if (
                        receipt_id in wanted
                        and receipt_id == "sha256:" + content_hash(core)
                    ):
                        found[receipt_id] = dict(receipt)
                if receipt_sha:
                    core = {
                        key: value
                        for key, value in receipt.items()
                        if key != "receipt_sha256"
                    }
                    if receipt_sha in wanted and receipt_sha == content_hash(core):
                        found[receipt_sha] = dict(receipt)
    if context is not None:
        context_hash = str(getattr(context, "context_hash", "") or "")

        def payload_scalars(value: Any, path: tuple[str, ...] = ()):
            if isinstance(value, Mapping):
                for key, item in value.items():
                    yield from payload_scalars(item, path + (str(key),))
            elif isinstance(value, (list, tuple)):
                for index, item in enumerate(value):
                    yield from payload_scalars(item, path + (str(index),))
            elif isinstance(value, str) and value:
                yield path, value

        for record in getattr(context, "object_records", ()) or ():
            object_id = str(getattr(record, "model_id", "") or "")
            payload = getattr(record, "payload", None)
            if not object_id or not isinstance(payload, Mapping):
                continue
            for payload_path, value in payload_scalars(payload):
                aliases = {value}
                if len(value) == 64 and all(
                    character in "0123456789abcdef" for character in value
                ):
                    aliases.add("sha256:" + value)
                for evidence_ref in sorted((wanted - set(found)) & aliases):
                    core = {
                        "schema": "leanmill.frozen_context_evidence_ref.v1",
                        "authority": "frozen_context_snapshot",
                        "evidence_ref": evidence_ref,
                        "context_hash": context_hash,
                        "object_id": object_id,
                        "payload_path": list(payload_path),
                        "payload_value": value,
                    }
                    found[evidence_ref] = {
                        **core,
                        "receipt_sha256": content_hash(core),
                    }
    missing = wanted - set(found)
    if missing:
        raise ValueError(
            "theory-language evidence refs do not resolve to governed trace receipts"
        )
    return [found[ref] for ref in evidence_refs]


def _workbench_evidence_binding(
    receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    pairs: set[tuple[str, str]] = set()
    evidence: list[dict[str, str]] = []
    for receipt in receipts:
        receipt_id = str(
            receipt.get("evidence_ref")
            or receipt.get("receipt_id")
            or receipt.get("receipt_sha256")
            or ""
        )
        if not receipt_id:
            raise ValueError("governed evidence receipt has no content identity")
        evidence.append(
            {
                "receipt_ref": receipt_id,
                "schema": str(receipt.get("schema") or ""),
                "authority": str(receipt.get("authority") or ""),
            }
        )
        summary = receipt.get("output_summary")
        contrast = (
            summary.get("contrast_truth_values")
            if isinstance(summary, Mapping)
            and summary.get("separates_contrast") is False
            else None
        )
        if isinstance(contrast, Mapping) and len(contrast) == 2:
            pairs.add(tuple(sorted(str(row) for row in contrast)))
    core = {
        "schema": (
            "leanmill.governed_mixed_evidence_binding.v1"
            if any(receipt.get("evidence_ref") for receipt in receipts)
            else "leanmill.governed_trace_evidence_binding.v1"
        ),
        "receipt_ids": [row["receipt_ref"] for row in evidence],
        "evidence": evidence,
        "contrast_object_pairs": [list(row) for row in sorted(pairs)],
    }
    return {**core, "receipt_sha256": content_hash(core)}


def lower_theory_language_request(
    request: TheoryLanguageExpansionRequest,
    context: Any,
    blueprint: FrontierTheoryBlueprint,
    *,
    context_epoch: int,
    directory: Path,
    navigation: Mapping[str, Any],
    approved_application: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile one language request through registered adapters, then type its gap."""

    if (
        request.source_context_hash != context.context_hash
        or request.source_epoch != context_epoch
    ):
        raise ValueError("theory-language request targets a stale context")
    binding = _workbench_evidence_binding(
        _resolve_workbench_evidence_receipts(
            directory, navigation, request.evidence_refs, context=context
        )
    )
    compilation = compile_theory_language_expansion(
        request,
        source_context=context,
        source_adapter_id=blueprint.adapter_id,
        formula_grammar=blueprint.formula_grammar,
        approved_application=approved_application,
    )
    from ztare.common.schema_routes import append_consequence_event

    append_consequence_event(
        directory / "workspace",
        contract_id="theory_language_compilation_outcome_totality.v1",
        subject_id=request.request_id,
        outcome=compilation.status,
        event="produced",
        evidence_refs=(str(binding["receipt_sha256"]),),
        idempotent=True,
    )
    if compilation.status == "compiled":
        return {
            "status": "compiled",
            "compiler_outcome": "compiled",
            "request": request,
            "context": compilation.context,
            "adapter_id": compilation.adapter_id,
            "context_transition": compilation.transition,
            "compiler_attempts": compilation.attempts,
            "evidence_binding": binding,
        }
    if compilation.status == "rejected" or approved_application is not None:
        return {
            "status": compilation.status,
            "compiler_outcome": compilation.status,
            "request": request,
            "reason": compilation.reason,
            "compiler_attempts": compilation.attempts,
            "evidence_binding": binding,
        }
    required_application = None
    if any(
        str(row.get("adapter_id") or "") == "generic_fol_finite.v1"
        and str(row.get("status") or "") == "unavailable"
        and str(row.get("reason") or "")
        == "approved_campaign_local_functor_application_required"
        for row in compilation.attempts
        if isinstance(row, Mapping)
    ):
        evidence_owned = isinstance(context, EvidenceTheoryContext)
        required_application = {
            "schema": "leanmill.theory_language_required_application.v1",
            "consumer": (
                "generic_fol_finite.v1:"
                "compile_theory_language_expansion"
            ),
            "application_kind": "finite_model_functor",
            "application_schema": (
                "leanmill.finite_model_functor_application.v2"
                if evidence_owned
                else "leanmill.finite_model_functor_application.v1"
            ),
            "source_context_kind": (
                "evidence_incidence" if evidence_owned else "formal_theory"
            ),
            "required_fields": (
                [
                    "functor_id",
                    "signature",
                    "formula_grammar",
                    "models",
                ]
                if evidence_owned
                else ["functor_id", "signature", "models"]
            ),
            "claim_boundary": (
                "the reviewed campaign-local application must build an "
                "executable successor context; coordinates alone are "
                "diagnostic and do not discharge this compiler gap"
            ),
        }
    gap = AdapterGap(
        brief_digest=blueprint.brief_digest,
        proposed_adapter_id=blueprint.adapter_id,
        primitive_semantics_contract={
            "source_adapter_id": blueprint.adapter_id,
            "theory_language_request": request.to_json(),
            "evidence_binding": binding,
            "compiler_attempts": [dict(row) for row in compilation.attempts],
            **(
                {"required_application": required_application}
                if required_application is not None
                else {}
            ),
        },
        raw_fixture_refs=request.evidence_refs,
        required_context_kind=(
            "exact" if getattr(context, "complete", False) else "sampled"
        ),
        required_operations=("lower_theory_language_request", "build_context"),
        required_receipts=(
            "determinism",
            "context_continuity",
            "semantic_profile_delta",
            "claim_boundary",
        ),
        forbidden_authorities=(
            "self_certified_exactness",
            "live_registry_mutation",
        ),
        acceptance_tests=(
            request.discriminating_test,
            "must_not_trigger: " + request.kill_condition,
        ),
        gap_kind="capability_missing",
        missing_capabilities=("theory_language:" + request.change_kind,),
    )
    return {
        "status": "adapter_gap",
        "compiler_outcome": "unavailable",
        "request": request,
        "adapter_gap": gap,
        "compiler_attempts": compilation.attempts,
        "evidence_binding": binding,
    }


def consume_theory_language_compilation(
    directory: Path,
    lowered: Mapping[str, Any],
    *,
    evidence_refs: Sequence[str] = (),
) -> None:
    """Receipt the state transition selected for one compiler outcome."""

    request = lowered.get("request")
    if not isinstance(request, TheoryLanguageExpansionRequest):
        raise ValueError("language compilation consumption lacks its request")
    outcome = str(lowered.get("compiler_outcome") or "")
    from ztare.common.schema_routes import append_consequence_event

    append_consequence_event(
        directory / "workspace",
        contract_id="theory_language_compilation_outcome_totality.v1",
        subject_id=request.request_id,
        outcome=outcome,
        event="consumed",
        evidence_refs=tuple(str(row) for row in evidence_refs),
        idempotent=True,
    )


def drive_frontier_navigation(
    context: Any,
    blueprint: FrontierTheoryBlueprint,
    *,
    directory: Path,
    campaign_id: str,
    attempt_id: str,
    journal: TheoryCampaignJournal,
    budget_ledger: ExplorationBudgetLedger,
    navigator_fn: NavigatorFn,
    packet_signer: PacketSigner,
    packet: FrontierCampaignPacket,
    context_epoch: int = 0,
    formula_proposal_hashes: Sequence[str] = (),
    semantically_new_formula_count: int = 0,
    pending_navigation: Mapping[str, Any] | None = None,
) -> FrontierNavigationDrive:
    """Run agent navigation and own every formula-context epoch transition."""

    if getattr(navigator_fn, "accepts_budget_ledger", False) is not True:
        raise ValueError("frontier navigator must accept the host budget ledger")
    hashes = list(formula_proposal_hashes)
    objective_review_history: list[dict[str, Any]] = []
    last_completed_navigation: dict[str, Any] | None = None
    navigation: dict[str, Any]
    pending = dict(pending_navigation) if pending_navigation is not None else None
    while True:
        conflicts, prior_conflicts = _freeze_theory_conflict_memory(
            context, directory, epoch=context_epoch
        )
        setattr(navigator_fn, "epoch", context_epoch)
        setattr(navigator_fn, "prior_conflict_rows", prior_conflicts)
        if pending is None:
            try:
                navigation = dict(
                    navigator_fn(
                        context,
                        blueprint,
                        journal,
                        budget_ledger=budget_ledger,
                    )
                )
            except BudgetExceeded:
                if last_completed_navigation is None:
                    raise
                navigation = last_completed_navigation
                break
        else:
            navigation, pending = pending, None
        _learn_navigation_conflicts(
            context,
            navigation,
            conflicts,
            journal,
            attempt_id=attempt_id,
            campaign_id=campaign_id,
            epoch=context_epoch,
        )

        synthesis = navigation.get("lineage_synthesis")
        if isinstance(synthesis, Mapping):
            route, expansions = _lineage_synthesis_route(
                synthesis, context, context_epoch
            )
            selected_requests = [
                dict(row)
                for row in synthesis.get("selected_requests") or ()
                if isinstance(row, Mapping)
            ]
            stale_selected = [
                row
                for row in selected_requests
                if not lineage_request_matches_context(
                    row,
                    context_hash=context.context_hash,
                    context_epoch=context_epoch,
                )
            ]
            if stale_selected:
                stale_core = {
                    "schema": "leanmill.stale_lineage_request_feedback.v1",
                    "context_hash": context.context_hash,
                    "context_epoch": context_epoch,
                    "source_synthesis_receipt_sha256": str(
                        synthesis.get("receipt_sha256") or ""
                    ),
                    "request_ids": sorted(
                        str(row.get("request_id") or "")
                        for row in stale_selected
                        if row.get("request_id")
                    ),
                    "route": "continue_search",
                    "continuation_mode": "current_context",
                    "program_ids": [],
                    "next_discriminator_request_ids": [],
                    "next_discriminator": (
                        "Author a request bound to the active context or continue "
                        "with current-context evidence."
                    ),
                    "kill_condition": (
                        "Do not admit or compile a request authored for a prior "
                        "context epoch."
                    ),
                    "authority": "host_context_identity_transition",
                }
                stale_feedback = {
                    **stale_core,
                    "receipt_sha256": content_hash(stale_core),
                }
                stale_path = directory / (
                    "stale_lineage_request_feedback."
                    f"epoch-{context_epoch:03d}."
                    f"wave-{int(navigation.get('search_wave', 0)):03d}.json"
                )
                prior_stale = read_json(stale_path, None)
                if isinstance(prior_stale, Mapping):
                    if dict(prior_stale) != stale_feedback:
                        raise ValueError("stale request feedback changed identity")
                else:
                    write_json_atomic(stale_path, stale_feedback)
                objective_review_history.append(stale_feedback)
                last_completed_navigation = {
                    **navigation,
                    "lineage_synthesis": stale_feedback,
                }
                setattr(navigator_fn, "objective_feedback", stale_feedback)
                begin_search_wave = getattr(
                    navigator_fn, "begin_search_wave", None
                )
                if callable(begin_search_wave):
                    begin_search_wave()
                continue
            if route == "continue_search":
                objective_review_history.append(dict(synthesis))
                last_completed_navigation = dict(navigation)
                setattr(navigator_fn, "objective_feedback", dict(synthesis))
                _refresh_theory_conflict_memory_after_wave(
                    context,
                    directory,
                    conflicts,
                    epoch=context_epoch,
                    search_wave=int(navigation.get("search_wave", 0)),
                )
                begin_search_wave = getattr(navigator_fn, "begin_search_wave", None)
                if callable(begin_search_wave):
                    begin_search_wave()
                continue
            if route == "escalate_language":
                request, composition = compose_selected_language_expansion(
                    synthesis
                )
                if composition is not None:
                    composition_path = directory / (
                        "theory_language_request_composition."
                        f"epoch-{context_epoch:03d}.json"
                    )
                    prior_composition = read_json(composition_path, None)
                    if isinstance(prior_composition, Mapping):
                        if dict(prior_composition) != composition:
                            raise ValueError(
                                "language request composition changed identity"
                            )
                    else:
                        write_json_atomic(composition_path, composition)
                    navigation["language_request_composition"] = composition
                write_json_atomic(
                    directory
                    / f"theory_language_expansion_request.epoch-{context_epoch:03d}.json",
                    request.to_json(),
                )
                navigation["language_expansion_request"] = request.to_json()
                break
            if route != "admit_formulas":
                break
            if not isinstance(context, FormalTheoryContext):
                raise ValueError("typed formula synthesis requires a formal finite context")
            source_epoch = context_epoch
            context, proposals, context_epoch, admissions = (
                admit_frontier_formula_epoch_batch(
                    context,
                    expansions,
                    journal=journal,
                    budget_ledger=budget_ledger,
                    directory=directory,
                    campaign_id=campaign_id,
                    attempt_id=attempt_id,
                    current_epoch=context_epoch,
                )
            )
            hashes.extend(proposal.content_hash for proposal in proposals)
            semantically_new_formula_count += sum(
                admission.get(
                    "bounded_semantic_coordinate_new",
                    admission.get("bounded_semantic_profile_new"),
                )
                is True
                for admission in admissions
            )
            packet = freeze_frontier_context_packet(
                directory,
                blueprint,
                context,
                campaign_id=campaign_id,
                context_epoch=context_epoch,
                formula_proposal_hashes=hashes,
                packet_signer=packet_signer,
            )
            trace = [
                {
                    "decision": "lineage_synthesis_admitted",
                    "synthesis_receipt_sha256": synthesis["receipt_sha256"],
                    "selected_request_ids": list(
                        synthesis.get("selected_request_ids") or ()
                    ),
                    "next_discriminator": str(
                        synthesis.get("next_discriminator") or ""
                    ),
                    "kill_condition": str(synthesis.get("kill_condition") or ""),
                    "admissions": [dict(row) for row in admissions],
                }
            ]
            _write_navigation_checkpoint(
                directory,
                context,
                context_epoch=context_epoch,
                trace=trace,
                provider_calls=int(navigation.get("provider_calls", 0)),
                formula_proposal_hashes=hashes,
            )
            begin_epoch = getattr(navigator_fn, "begin_context_epoch", None)
            if not callable(begin_epoch):
                raise ValueError("multi-lineage synthesis requires an epoch-aware navigator")
            setattr(navigator_fn, "initial_trace", tuple(trace))
            begin_epoch(source_epoch=source_epoch, target_epoch=context_epoch)
            continue

        language_row = navigation.get("language_expansion_request")
        if isinstance(language_row, Mapping):
            request = TheoryLanguageExpansionRequest.from_json(language_row)
            if (
                request.source_context_hash != context.context_hash
                or request.source_epoch != context_epoch
            ):
                raise ValueError("theory-language request targets a stale epoch")
            write_json_atomic(
                directory
                / f"theory_language_expansion_request.epoch-{context_epoch:03d}.json",
                request.to_json(),
            )
            break

        expansion = navigation.get("expansion_proposal")
        if not isinstance(expansion, Mapping):
            break
        if navigation.get("finalists"):
            navigation = freeze_frontier_formula_successor_request(
                directory, navigation
            )
            break
        if not isinstance(context, FormalTheoryContext):
            raise ValueError("typed formula expansion requires a formal finite context")
        context, proposal, context_epoch, admission = admit_frontier_formula_epoch(
            context,
            expansion,
            journal=journal,
            budget_ledger=budget_ledger,
            directory=directory,
            campaign_id=campaign_id,
            attempt_id=attempt_id,
            current_epoch=context_epoch,
        )
        hashes.append(proposal.content_hash)
        semantically_new_formula_count += int(
            admission.get(
                "bounded_semantic_coordinate_new",
                admission.get("bounded_semantic_profile_new"),
            )
            is True
        )
        packet = freeze_frontier_context_packet(
            directory,
            blueprint,
            context,
            campaign_id=campaign_id,
            context_epoch=context_epoch,
            formula_proposal_hashes=hashes,
            packet_signer=packet_signer,
        )
        turns = int(navigation.get("provider_calls", 0))
        trace = list(navigation.get("trace") or ()) + [
            {
                "round": turns,
                "decision": "context_epoch_admitted",
                "admission": dict(admission),
            }
        ]
        _write_navigation_checkpoint(
            directory,
            context,
            context_epoch=context_epoch,
            trace=trace,
            provider_calls=turns,
            formula_proposal_hashes=hashes,
        )
        for name, value in {
            "initial_trace": tuple(trace),
            "prior_agent_turns": turns,
            "round_offset": turns,
        }.items():
            setattr(navigator_fn, name, value)

    if objective_review_history:
        navigation = {
            **navigation,
            "objective_review_history": objective_review_history,
        }
    return FrontierNavigationDrive(
        context=context,
        context_epoch=context_epoch,
        formula_proposal_hashes=tuple(hashes),
        semantically_new_formula_count=semantically_new_formula_count,
        packet=packet,
        navigation=navigation,
    )


def finish_frontier_navigation(
    directory: Path,
    *,
    brief_id: str,
    blueprint: FrontierTheoryBlueprint,
    context: Any,
    context_epoch: int,
    campaign_id: str,
    packet_digest: str,
    navigation: Mapping[str, Any],
    provider_calls: int,
    preparation_provider_calls: int,
    budget_digest: str,
    formula_proposal_count: int,
    semantically_new_formula_count: int,
    labeled_object_count: int,
    budget_stop_receipt: Mapping[str, Any] | None = None,
) -> FrontierExplorationRun:
    """Validate one terminal navigation state and publish its read model."""

    navigation = dict(navigation)
    formula_requests = navigation.get("expansion_proposals")
    language_requests = navigation.get("theory_language_expansion_requests")
    adapter_gap = navigation.get("adapter_gap")
    language_feedback = navigation.get("language_compilation_feedback")
    has_request = bool(
        isinstance(adapter_gap, Mapping)
        or isinstance(language_feedback, Mapping)
        or isinstance(navigation.get("language_expansion_request"), Mapping)
        or isinstance(formula_requests, list)
        and formula_requests
        or isinstance(language_requests, list)
        and language_requests
    )
    if isinstance(formula_requests, list) and formula_requests or isinstance(
        language_requests, list
    ) and language_requests:
        core = {
            "schema": "leanmill.isolated_lineage_language_requests.v1",
            "source_context_hash": context.context_hash,
            "source_epoch": context_epoch,
            "formula_requests": list(formula_requests or ()),
            "theory_language_requests": list(language_requests or ()),
            "status": "outbound_requests_require_reviewed_successor_context",
            "authority": "proposal_only",
        }
        write_json_atomic(
            directory
            / f"isolated_lineage_language_requests.epoch-{context_epoch:03d}.json",
            {**core, "receipt_sha256": content_hash(core)},
        )
    exhausted = navigation.get("navigation_exhausted_receipt")
    pending_leaf_decisions = navigation.get("pending_leaf_decisions")
    pending_leaf_decision = navigation.get("pending_leaf_decision")
    leaf_decision_pending = bool(
        isinstance(pending_leaf_decisions, list) and pending_leaf_decisions
        or isinstance(pending_leaf_decision, Mapping)
    )
    budget_stopped = budget_stop_receipt is not None
    objective = frontier_objective_contract(blueprint)
    synthesis = navigation.get("lineage_synthesis")
    objective_route = (
        str(synthesis.get("route") or "") if isinstance(synthesis, Mapping) else ""
    )
    if (
        objective_route == "proceed_boundary"
        and isinstance(synthesis, Mapping)
        and synthesis.get("program_ids")
    ):
        synthesis_search_wave = int(
            navigation.get(
                "lineage_synthesis_search_wave",
                navigation.get("search_wave", 0),
            )
        )
        selected_program_ids = tuple(
            str(row) for row in synthesis.get("program_ids") or ()
        )
        if not selected_program_ids or len(set(selected_program_ids)) != len(
            selected_program_ids
        ):
            raise ValueError("boundary synthesis must select distinct theory programs")
        carried = [
            dict(row)
            for field in (
                "finalists",
                "deferred_finalists",
                "objective_survivors",
            )
            for row in navigation.get(field) or ()
            if isinstance(row, Mapping)
        ]
        unique: dict[str, dict[str, Any]] = {}
        for row in carried:
            identity = str(
                row.get("theory_program_id")
                or row.get("node_id")
                or content_hash(row)
            )
            unique.setdefault(identity, row)
        available_program_ids = {
            str(row.get("theory_program_id") or "") for row in unique.values()
        }
        if not set(selected_program_ids) <= available_program_ids:
            raise ValueError("boundary synthesis selected an unavailable theory program")
        selected_set = set(selected_program_ids)
        active = [
            row
            for row in unique.values()
            if str(row.get("theory_program_id") or "") in selected_set
        ]
        active.sort(
            key=lambda row: selected_program_ids.index(
                str(row.get("theory_program_id") or "")
            )
        )
        deferred = [
            row
            for row in unique.values()
            if str(row.get("theory_program_id") or "") not in selected_set
        ]
        frozen_program_ids = {
            str(row)
            for row in navigation.get("lineage_synthesis_frozen_program_ids")
            or available_program_ids
        }
        if not selected_set <= frozen_program_ids:
            raise ValueError("boundary synthesis crossed its frozen program input")
        selection_core = {
            "schema": "leanmill.lineage_synthesis_program_selection.v1",
            "context_hash": context.context_hash,
            "context_epoch": context_epoch,
            "search_wave": synthesis_search_wave,
            "synthesis_receipt_sha256": str(
                synthesis.get("receipt_sha256") or content_hash(synthesis)
            ),
            "selected_program_ids": list(selected_program_ids),
            "deferred_program_ids": sorted(frozen_program_ids - selected_set),
            "route": "proceed_boundary",
            "authority": "frontier_navigation_state_transition",
        }
        selection = {
            **selection_core,
            "receipt_sha256": content_hash(selection_core),
        }
        selection_path = directory / (
            "lineage_synthesis_program_selection."
            f"epoch-{context_epoch:03d}."
            f"wave-{synthesis_search_wave:03d}.json"
        )
        prior_selection = read_json(selection_path, None)
        if isinstance(prior_selection, Mapping):
            if dict(prior_selection) != selection:
                raise ValueError("boundary program selection changed identity")
        else:
            write_json_atomic(selection_path, selection)
        navigation["finalists"] = active
        navigation["deferred_finalists"] = deferred
        navigation["lineage_synthesis_program_selection"] = selection
    if (
        objective is not None
        and not objective_route
        and (
            isinstance(navigation.get("lineage_synthesis_budget_stop"), Mapping)
            or isinstance(navigation.get("lineage_synthesis_failure"), Mapping)
            or isinstance(navigation.get("navigation_exhausted_receipt"), Mapping)
        )
    ):
        objective_route = "continue_search"
    if (
        objective is not None
        and not leaf_decision_pending
        and not budget_stopped
        and objective_route not in {
        "proceed_boundary",
        "continue_search",
        "admit_formulas",
        "escalate_language",
        "defer_all",
        }
    ):
        raise ValueError("frontier objective lacks a valid late lineage disposition")
    if (
        not navigation.get("finalists")
        and not has_request
        and not budget_stopped
        and not leaf_decision_pending
    ):
        if isinstance(navigation.get("reject_all_receipt"), Mapping):
            _validate_no_candidate_navigation(context, navigation)
            sequence = _campaign_reject_all_sequence(
                directory,
                campaign_id=campaign_id,
                context_hash=context.context_hash,
                current_navigation=navigation,
            )
            navigation["reject_all_sequence_receipt"] = sequence
            navigation["stagnation_pressure"] = bool(sequence["stagnation_pressure"])
        elif isinstance(exhausted, Mapping):
            core = {key: value for key, value in exhausted.items() if key != "receipt_sha256"}
            if (
                exhausted.get("receipt_sha256") != content_hash(core)
                or exhausted.get("context_hash") != context.context_hash
            ):
                raise ValueError("navigation exhaustion receipt does not replay")
        else:
            raise ValueError(
                "frontier navigation ended without a finalist, request, refusal, or exhaustion receipt"
            )
    status = (
        "budget_stopped"
        if budget_stopped
        else "blocked_adapter_gap"
        if isinstance(adapter_gap, Mapping)
        else "frontier_objective_unmet"
        if isinstance(language_feedback, Mapping)
        else "frontier_leaf_decision_pending"
        if leaf_decision_pending
        else "frontier_objective_unmet"
        if objective is not None and objective_route in {"continue_search", "defer_all"}
        else "frontier_language_expansion_requested"
        if objective is not None and objective_route == "escalate_language"
        else "frontier_objective_unmet"
        if (
            objective is not None
            and objective_route == "proceed_boundary"
            and not navigation.get("finalists")
        )
        else "frontier_candidates_frozen_awaiting_boundary_approval"
        if navigation.get("finalists")
        else "frontier_language_expansion_requested"
        if has_request
        else "frontier_navigation_exhausted"
        if isinstance(exhausted, Mapping)
        else "frontier_no_candidate"
    )
    run = FrontierExplorationRun(
        status=status,
        brief_id=brief_id,
        attempt_dir=str(directory),
        blueprint_id=blueprint.blueprint_id,
        context_hash=context.context_hash,
        packet_digest=packet_digest,
        navigation=navigation,
        adapter_gap=(
            dict(adapter_gap)
            if isinstance(adapter_gap, Mapping)
            else None
        ),
        context_summary=frontier_context_summary(
            context,
            blueprint,
            context_epoch=context_epoch,
            proposed_formula_count=formula_proposal_count,
            proposed_semantic_profile_count=semantically_new_formula_count,
            language_expansion_requested=has_request,
            labeled_object_count=labeled_object_count,
        ),
        provider_calls=provider_calls,
        preparation_provider_calls=preparation_provider_calls,
        budget_digest=budget_digest,
        budget_stop_receipt=budget_stop_receipt,
    )
    write_json_atomic(directory / "run.json", run.to_json())
    return run


def explore_axiom_space(
    direction: str | FrontierExplorationBrief | Any,
    *,
    attempt_dir: str | Path,
    evidence_refs: Sequence[str] = (),
    source_mode: str = "human_directed",
    typed_draft: Mapping[str, Any] | None = None,
    draft_fn: DraftFn | None = None,
    semantic_review_fn: ReviewFn | None = None,
    compiler_ref: str = "frontier-blueprint-compiler",
    reviewer_ref: str = "frontier-blueprint-reviewer",
    packet_signer: PacketSigner | None = None,
    navigator_fn: NavigatorFn | None = None,
    budget: str | Mapping[str, Any] | ExplorationBudget | None = None,
    budget_compiler_fn: BudgetCompilerFn | None = None,
    frozen_context_ref: Mapping[str, str] | None = None,
    campaign_manifest: Mapping[str, Any] | None = None,
    navigation_ownership_fn: NavigationOwnershipFn | None = None,
    attempt_initializer: Callable[[Path], None] | None = None,
) -> FrontierExplorationRun:
    """Compile, freeze, construct, and navigate one immutable frontier attempt."""
    directory = Path(attempt_dir)
    existing = read_json(directory / "run.json", None)
    if isinstance(existing, dict) and existing:
        return FrontierExplorationRun(
            **{key: existing[key] for key in FrontierExplorationRun.__dataclass_fields__ if key in existing}
        )

    # The old candidate-template blueprint is deliberately not accepted here.
    if direction.__class__.__name__ == "AxiomPackBlueprint":
        brief_id = "legacy:" + content_hash(direction.to_json())
        run = FrontierExplorationRun(
            status="legacy_warm_route_required",
            brief_id=brief_id,
            attempt_dir=str(directory),
        )
        directory.mkdir(parents=True, exist_ok=True)
        write_json_atomic(directory / "run.json", run.to_json())
        return run
    campaign_definition = (
        direction if isinstance(direction, FrontierCampaignDefinition) else None
    )
    if frozen_context_ref is None and campaign_definition is not None:
        frozen_context_ref = campaign_definition.frozen_context_ref
    if campaign_definition is not None:
        brief, budget_contract, budget_preference = compile_campaign_brief(
            campaign_definition,
            budget=budget,
            budget_compiler_fn=budget_compiler_fn,
        )
    else:
        brief = (
            direction
            if isinstance(direction, FrontierExplorationBrief)
            else FrontierExplorationBrief.from_direction(
                str(direction), source_mode=source_mode, evidence_refs=evidence_refs
            )
        )
        budget_contract, budget_preference = compile_budget_preference(
            budget if budget is not None else (brief.resource_envelope or None),
            direction_text=brief.direction,
            compiler_fn=budget_compiler_fn,
        )
        brief = replace(
            brief,
            resource_envelope={
                **dict(brief.resource_envelope),
                "budget_contract": budget_contract.to_json(),
                "budget_preference_compilation": budget_preference.to_json(),
            },
        )
    preparation_provider_calls = int(
        budget_preference.source_mode == "compiled_campaign_yaml"
    )
    directory.mkdir(parents=True, exist_ok=False)
    if attempt_initializer is not None:
        attempt_initializer(directory)
    from ztare.leanmill.phase_timing import record_campaign

    record_campaign(
        "axiompack-frontier",
        run_tag=directory.name,
        target=brief.brief_id,
    )
    if campaign_manifest is not None:
        write_json_atomic(directory / "campaign_manifest.json", dict(campaign_manifest))
    if campaign_definition is not None:
        write_text_atomic(directory / "campaign_definition.yaml", campaign_definition.to_yaml())
    write_json_atomic(directory / "brief.json", brief.to_json())
    write_json_atomic(directory / "budget.json", budget_contract.to_json())
    write_text_atomic(
        directory / "campaign_budget.yaml",
        render_budget_yaml(
            budget_contract,
            delegated_stop_instruction=budget_preference.delegated_stop_instruction,
        ),
    )
    write_json_atomic(directory / "budget_preference_compilation.json", budget_preference.to_json())
    budget_ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        budget_contract,
        attempt_id=directory.name,
    )

    def budgeted_agent_call(
        callback: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        *,
        action_id: str,
    ) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
        role = getattr(callback, "call_role", None)
        if role is not None:
            role.budget_ledger = budget_ledger

        def invoke(payload: Mapping[str, Any]) -> Mapping[str, Any]:
            reservation = budget_ledger.reserve(
                action_id,
                "compilation",
                {"provider_calls": 1, "agent_turns": 1},
            )
            before = (
                int(getattr(role, "provider_call_count", getattr(role, "call_count", 0)))
                if role is not None else None
            )
            try:
                return callback(payload)
            except Exception:
                raise
            finally:
                after = (
                    int(getattr(role, "provider_call_count", getattr(role, "call_count", 0)))
                    if role is not None else None
                )
                used = 1 if before is None or after is None else max(0, min(1, after - before))
                budget_ledger.commit(
                    reservation,
                    {"provider_calls": used, "agent_turns": used},
                )

        invoke.call_role = role  # type: ignore[attr-defined]
        return invoke

    budgeted_draft_fn = (
        budgeted_agent_call(draft_fn, action_id="blueprint:compile")
        if draft_fn is not None else None
    )
    budgeted_review_fn = (
        budgeted_agent_call(semantic_review_fn, action_id="blueprint:semantic_review")
        if semantic_review_fn is not None else None
    )

    def stopped_run(
        reason: str,
        *,
        blueprint: FrontierTheoryBlueprint | None = None,
        context_hash: str = "",
        adapter_gap: Mapping[str, Any] | None = None,
    ) -> FrontierExplorationRun:
        receipt = budget_ledger.stop_receipt(reason, context_hash=context_hash).to_json()
        write_json_atomic(directory / "budget_stop_receipt.json", receipt)
        usage = budget_ledger.state()["usage"]
        run = FrontierExplorationRun(
            status="budget_stopped" if reason.startswith(("blocked_before_action", "hard_cap_reached", "marginal_", "user_stop", "operator_stop")) else "blocked_adapter_gap",
            brief_id=brief.brief_id,
            attempt_dir=str(directory),
            blueprint_id=blueprint.blueprint_id if blueprint is not None else "",
            context_hash=context_hash,
            adapter_gap=adapter_gap,
            provider_calls=int(usage["provider_calls"]) + preparation_provider_calls,
            preparation_provider_calls=preparation_provider_calls,
            budget_digest=budget_contract.digest,
            budget_stop_receipt=receipt,
        )
        write_json_atomic(directory / "run.json", run.to_json())
        return run

    try:
        if typed_draft is not None:
            blueprint = compile_structure_first_blueprint(brief, typed_draft)
        else:
            if budgeted_draft_fn is None or budgeted_review_fn is None:
                raise ValueError("NL directions require blueprint compiler and semantic reviewer callables")
            blueprint = compile_frontier_blueprint(
                brief,
                draft_fn=budgeted_draft_fn,
                semantic_review_fn=budgeted_review_fn,
                compiler_ref=compiler_ref,
                reviewer_ref=reviewer_ref,
            )
    except BudgetExceeded as exc:
        return stopped_run(exc.reason)
    except AdapterGapRequired as exc:
        write_json_atomic(directory / "adapter_gap.json", exc.gap.to_json())
        return stopped_run(
            "campaign_finished:blocked_adapter_gap",
            adapter_gap=exc.gap.to_json(),
        )
    write_json_atomic(directory / "blueprint.json", blueprint.to_json())
    write_json_atomic(directory / "cold_navigator_manifest.json", cold_navigator_manifest(blueprint))
    adapter_preflight = dict(
        blueprint.executable_preflight_receipt.get("adapter_preflight") or {}
    )
    formula_count = int(adapter_preflight.get("formula_count", 0))
    labeled_model_count = int(adapter_preflight.get("labeled_model_count", 0))
    context_model_budget_upper_bound = int(
        adapter_preflight.get("context_model_budget_upper_bound", labeled_model_count)
    )
    truth_cell_budget_upper_bound = int(
        adapter_preflight.get(
            "truth_cell_budget_upper_bound",
            formula_count * labeled_model_count,
        )
    )
    try:
        context_reservation = budget_ledger.reserve(
            "context:construct",
            "context",
            {
                "context_models": context_model_budget_upper_bound,
                "truth_cells": truth_cell_budget_upper_bound,
            },
        )
    except BudgetExceeded as exc:
        return stopped_run(exc.reason, blueprint=blueprint)
    try:
        context = (
            _context_from_snapshot(blueprint, frozen_context_ref)
            if frozen_context_ref is not None else _context_from_blueprint(blueprint)
        )
    except Exception as exc:
        budget_ledger.commit(context_reservation)
        failure_receipt = getattr(exc, "failure_receipt", None)
        if callable(failure_receipt):
            write_json_atomic(
                directory / "context_construction_failure.json",
                failure_receipt(),
            )
        partial_snapshot = getattr(exc, "partial_snapshot", None)
        if callable(partial_snapshot):
            write_json_atomic(
                directory / "partial_model_universe.json",
                partial_snapshot(),
            )
        raise
    budget_ledger.commit(
        context_reservation,
        {
            "context_models": (
                int(context.universe.receipt.accepted_labeled_count)
                if isinstance(context, FormalTheoryContext)
                and getattr(context.universe.receipt, "generation_policy", "")
                == "smt_isomorphism_class_enumeration.v1"
                else len(context.object_ids)
                if isinstance(context, FormalTheoryContext)
                and getattr(context.universe.receipt, "generation_policy", "")
                == "deterministic_pointwise_functor_image.v1"
                else labeled_model_count
            ),
            "truth_cells": formula_count * len(context.object_ids),
        },
    )
    if isinstance(context, EvidenceTheoryContext):
        save_evidence_theory_context(context, directory / "evidence_context.json")
    else:
        save_formal_theory_context(context, directory / "formal_context.json")
        save_formal_theory_context(
            context, directory / "formal_context.epoch-000.json"
        )
    if frozen_context_ref is not None:
        reuse_core = {
            "schema": "leanmill.frontier_context_reuse.v1",
            "source_path": str(frozen_context_ref["path"]),
            "source_snapshot_sha256": str(frozen_context_ref["snapshot_sha256"]),
            "context_hash": context.context_hash,
            "blueprint_id": blueprint.blueprint_id,
            "provider_calls": 0,
        }
        write_json_atomic(
            directory / "context_reuse_receipt.json",
            {**reuse_core, "receipt_sha256": content_hash(reuse_core)},
        )
    if packet_signer is None:
        raise ValueError("frontier campaign requires an injected packet authority signer")
    campaign_id = "campaign:" + blueprint.blueprint_id.split(":", 1)[1][:24]
    context_epoch = 0
    formula_proposal_hashes: list[str] = []
    semantically_new_formula_count = 0
    packet = freeze_frontier_context_packet(
        directory,
        blueprint,
        context,
        campaign_id=campaign_id,
        context_epoch=context_epoch,
        formula_proposal_hashes=formula_proposal_hashes,
        packet_signer=packet_signer,
    )
    navigation_owner = (
        navigation_ownership_fn(directory, context_epoch, context.context_hash)
        if navigation_ownership_fn is not None
        else None
    )
    if navigation_owner is not None:
        navigation_owner.__enter__()
    journal = TheoryCampaignJournal(directory / "events.jsonl")
    try:
        if navigator_fn is None:
            selection_mode = navigator_selection_mode(blueprint)
            if selection_mode != "compact_axiom_pack":
                raise ValueError(
                    "theory_program campaigns require an agent navigator; "
                    "the no-provider navigator is an explicit compact-pack control"
                )
            theory_conflicts, _prior_conflicts = _freeze_theory_conflict_memory(
                context, directory, epoch=context_epoch
            )
            max_finalists = min(
                int(blueprint.query_budget.get("max_finalists", 8)),
                budget_contract.stop_rule.max_finalists,
            )
            max_ranked_queries = int(
                blueprint.query_budget.get("max_ranked_queries", max_finalists * 2)
            )
            deterministic_bounds = (
                presentation_size_bounds(blueprint)
                if "presentation_size" in blueprint.navigator_contract
                else (blueprint.pack_arity, blueprint.pack_arity)
            )
            navigation_reservation = budget_ledger.reserve(
                "navigator:deterministic_control",
                "navigation",
                {"workbench_actions": max_finalists + max_ranked_queries},
            )
            navigation = run_deterministic_frontier_campaign(
                context,
                campaign_id=packet.campaign_id,
                attempt_id=directory.name,
                journal=journal,
                max_finalists=max_finalists,
                max_ranked_queries=max_ranked_queries,
                boundary_query_type=(
                    "raw_boundary_check"
                    if blueprint.mode == "evidence_induced"
                    else "conditional_lean_consequence"
                ),
                minimum_presentation_size=deterministic_bounds[0],
                maximum_presentation_size=deterministic_bounds[1],
                selection_mode=selection_mode,
            ).to_json()
            budget_ledger.commit(
                navigation_reservation,
                {
                    "workbench_actions": len(navigation["finalists"])
                    + len(navigation["ranked_queries"])
                },
            )
            _learn_navigation_conflicts(
                context,
                navigation,
                theory_conflicts,
                journal,
                attempt_id=directory.name,
                campaign_id=campaign_id,
                epoch=context_epoch,
            )
        else:
            driven = drive_frontier_navigation(
                context,
                blueprint,
                directory=directory,
                campaign_id=campaign_id,
                attempt_id=directory.name,
                journal=journal,
                budget_ledger=budget_ledger,
                navigator_fn=navigator_fn,
                packet_signer=packet_signer,
                packet=packet,
                context_epoch=context_epoch,
                formula_proposal_hashes=formula_proposal_hashes,
                semantically_new_formula_count=semantically_new_formula_count,
            )
            context = driven.context
            context_epoch = driven.context_epoch
            formula_proposal_hashes = list(driven.formula_proposal_hashes)
            semantically_new_formula_count = driven.semantically_new_formula_count
            packet = driven.packet
            navigation = dict(driven.navigation)
    except BudgetExceeded as exc:
        result = stopped_run(
            exc.reason, blueprint=blueprint, context_hash=context.context_hash
        )
    else:
        usage = budget_ledger.state()["usage"]
        result = finish_frontier_navigation(
            directory,
            brief_id=brief.brief_id,
            blueprint=blueprint,
            context=context,
            context_epoch=context_epoch,
            campaign_id=packet.campaign_id,
            packet_digest=packet.digest,
            navigation=navigation,
            provider_calls=int(usage["provider_calls"])
            + preparation_provider_calls,
            preparation_provider_calls=preparation_provider_calls,
            budget_digest=budget_contract.digest,
            formula_proposal_count=len(formula_proposal_hashes),
            semantically_new_formula_count=semantically_new_formula_count,
            labeled_object_count=labeled_model_count,
        )
    finally:
        if navigation_owner is not None:
            navigation_owner.__exit__(*sys.exc_info())
    return result


def _registered_boundary_task_contracts(
    navigation: Mapping[str, Any],
) -> frozenset[str]:
    """Return exact frozen contracts whose adjudicators have boundary handlers."""

    from ztare.leanmill.theory_task_boundary_registry import (
        registered_theory_task_boundary_handler,
    )

    refs: set[str] = set()
    for finalist in navigation.get("finalists") or ():
        program_row = (
            finalist.get("theory_program")
            if isinstance(finalist, Mapping)
            else None
        )
        if not isinstance(program_row, Mapping):
            continue
        program = TheoryProgram.from_json(program_row)
        refs.update(
            contract.sha256
            for contract in program.task_discharge_contracts
            if registered_theory_task_boundary_handler(
                contract.adjudicator_id
            )
            is not None
        )
    return frozenset(refs)


def _boundary_completion_covers(
    completion: Mapping[str, Any],
    verification_plan: Mapping[str, Any],
    navigation: Mapping[str, Any],
    *,
    lean_requested: bool,
    isabelle_requested: bool,
    theory_task_requested: bool = False,
    theory_task_requested_contracts: frozenset[str] | None = None,
) -> bool:
    boundary = completion.get("boundary_result") or {}
    boundary_core = {
        key: value for key, value in boundary.items() if key != "result_sha256"
    } if isinstance(boundary, Mapping) else {}
    if (
        not boundary_core
        or boundary.get("result_sha256") != content_hash(boundary_core)
    ):
        return False
    stop_reason = str(boundary.get("stop_reason") or "")
    if stop_reason.startswith("blocked_before_action"):
        return False
    rows = boundary.get("query_results") or ()
    expected_tasks: set[tuple[str, str]] = set()
    task_only_programs: set[str] = set()
    for finalist in navigation.get("finalists") or ():
        if not isinstance(finalist, Mapping) or not isinstance(
            finalist.get("theory_program"), Mapping
        ):
            continue
        program = TheoryProgram.from_json(finalist["theory_program"])
        expected_tasks.update(
            (program.program_id, contract.sha256)
            for contract in program.task_discharge_contracts
        )
        if not program.prediction_formula_ids and program.task_discharge_contracts:
            task_only_programs.add(program.program_id)
    if expected_tasks:
        task_bundle = completion.get("theory_task_discharge")
        if not isinstance(task_bundle, Mapping):
            return False
        task_core = {
            key: value for key, value in task_bundle.items()
            if key != "receipt_sha256"
        }
        if (
            task_bundle.get("receipt_sha256") != content_hash(task_core)
            or task_bundle.get("boundary_result_sha256")
            != boundary.get("result_sha256")
        ):
            return False
        observed: set[tuple[str, str]] = set()
        discharged: set[tuple[str, str]] = set()
        for row in task_bundle.get("rows") or ():
            if not isinstance(row, Mapping) or row.get("source") != "explicit_task":
                continue
            row_core = {
                key: value for key, value in row.items()
                if key != "receipt_sha256"
            }
            if row.get("receipt_sha256") != content_hash(row_core):
                return False
            key = (
                str(row.get("program_id") or ""),
                str(row.get("contract_sha256") or ""),
            )
            contract_row = row.get("contract")
            receipt_row = row.get("receipt")
            if not isinstance(contract_row, Mapping) or not isinstance(
                receipt_row, Mapping
            ):
                return False
            from ztare.common.task_discharge import bind_task_discharge_receipt

            contract, receipt = bind_task_discharge_receipt(
                contract_row, receipt_row
            )
            if (
                contract.sha256 != key[1]
            ):
                return False
            observed.add(key)
            if receipt.status == "discharged":
                discharged.add(key)
        if not expected_tasks <= observed:
            return False
        # A typed negative attempt is complete boundary evidence too.  It must
        # be consumed as navigation feedback, not archived and retried as if
        # the adjudicator never ran.
        requested_contracts = (
            frozenset(theory_task_requested_contracts)
            if theory_task_requested_contracts is not None
            else frozenset(contract for _program, contract in expected_tasks)
            if theory_task_requested
            else frozenset()
        )
        if requested_contracts:
            attempted_contracts = {
                str(row.get("contract_sha256") or "")
                for row in rows
                if isinstance(row, Mapping)
                and row.get("candidate_kind") == "theory_task"
            }
            if not requested_contracts <= attempted_contracts:
                return False
    formula_rows = [
        row
        for row in rows
        if isinstance(row, Mapping) and row.get("candidate_kind") != "theory_task"
    ]
    if not formula_rows:
        return bool(expected_tasks) and bool(task_only_programs)
    failure_statuses = {
        "refuted_in_seed_context", "refuted_by_replayed_countermodel",
        "refuted_by_larger_model", "refuted_by_kernel",
    }
    expected_vectors = {
        tuple(sorted((str(key), int(value)) for key, value in sizes.items()))
        for item in (
            verification_plan.get("larger_model_strata")
            or verification_plan.get("heldout_strata")
            or ()
        )
        if isinstance(item, Mapping)
        and isinstance((sizes := item.get("sort_sizes")), Mapping)
    }
    expected_carriers = {
        int(value) for value in verification_plan.get("larger_carriers") or ()
    }
    completed_finite_search_statuses = {
        "countermodel_found",
        "no_countermodel_at_fixed_size",
        "no_premise_model_at_fixed_size",
        "unknown",
    }

    def row_sources(row: Mapping[str, Any]) -> set[str]:
        sources = {str(row.get("target_formula_id") or "")}
        normalization = row.get("prediction_normalization") or {}
        for source in normalization.get("source_coordinates") or ():
            if isinstance(source, Mapping):
                sources.add(str(source.get("source_prediction_formula_id") or ""))
        return {value for value in sources if value}

    for finalist in navigation.get("finalists") or ():
        if not isinstance(finalist, Mapping):
            continue
        program_row = finalist.get("theory_program")
        if isinstance(program_row, Mapping) and not TheoryProgram.from_json(
            program_row
        ).prediction_formula_ids:
            continue
        premises = tuple(
            sorted(str(value) for value in finalist.get("formula_ids") or ())
        )
        finalist_rows = [
            row for row in formula_rows
            if isinstance(row, Mapping)
            and tuple(str(value) for value in row.get("premise_formula_ids") or ())
            == premises
        ]
        if not finalist_rows:
            return False
        if any(
            str(row.get("program_prediction_status") or "") in failure_statuses
            for row in finalist_rows
        ):
            continue
        covered_targets = set().union(*(row_sources(row) for row in finalist_rows))
        expected_targets = {
            str(value) for value in finalist.get("boundary_target_ids") or ()
        }
        if not expected_targets.issubset(covered_targets):
            return False
        for row in finalist_rows:
            terminal_without_search = (
                str(row.get("program_prediction_status") or "")
                in failure_statuses | {
                    "inadmissible_logical_product_coordinate",
                    "not_tested_query_limit",
                }
                or (row.get("logical_premise_ablation") or {}).get("status")
                in {
                    "refuted_by_known_single_premise",
                    "skipped_seed_context_counterexample",
                    "skipped_replayed_countermodel",
                    "skipped_inadmissible_prediction_identity",
                }
            )
            if terminal_without_search:
                continue
            searches = [
                receipt for receipt in row.get("countermodel_searches") or ()
                if isinstance(receipt, Mapping)
            ]
            if expected_vectors:
                covered_vectors = {
                    tuple(
                        sorted(
                            (str(key), int(value))
                            for key, value in dict(
                                receipt.get("sort_sizes") or {}
                            ).items()
                        )
                    )
                    for receipt in searches
                    if receipt.get("status") in completed_finite_search_statuses
                }
                if not expected_vectors.issubset(covered_vectors):
                    return False
            if expected_carriers:
                covered_carriers = {
                    int(receipt["carrier_size"])
                    for receipt in searches
                    if receipt.get("status") in completed_finite_search_statuses
                    and type(receipt.get("carrier_size")) is int
                }
                if not expected_carriers.issubset(covered_carriers):
                    return False
            if lean_requested and (row.get("lean") or {}).get("status") in {
                "not_requested", "task_rendered",
            }:
                return False
            if isabelle_requested and (row.get("isabelle") or {}).get("status") in {
                "not_requested", "task_rendered",
            }:
                return False
    return True


def _prior_boundary_query_results(
    directory: Path, *, context_hash: str
) -> tuple[Mapping[str, Any], ...]:
    """Replay prior boundary work by semantic query identity."""

    paths = {
        *directory.glob("boundary_attempts/*/boundary_result.json"),
        *directory.glob("boundary_result.wave-*.json"),
    }
    rows: list[Mapping[str, Any]] = []
    for path in sorted(paths):
        result = read_json(path, None)
        if not isinstance(result, Mapping):
            continue
        core = {key: value for key, value in result.items() if key != "result_sha256"}
        if result.get("result_sha256") != content_hash(core):
            raise ValueError(f"archived boundary result digest mismatch: {path.name}")
        if result.get("context_hash") != context_hash:
            continue
        rows.extend(
            dict(row) for row in result.get("query_results") or ()
            if isinstance(row, Mapping)
        )
    return tuple(rows)


def _recover_partial_boundary_feedback(
    directory: Path, run: Mapping[str, Any]
) -> Mapping[str, Any]:
    """Undo the legacy transition that treated a partial boundary as feedback."""

    if run.get("status") != "frontier_objective_unmet":
        return run
    for feedback_path in reversed(
        sorted(directory.glob("boundary_search_feedback.wave-*.json"))
    ):
        suffix = feedback_path.name.removeprefix("boundary_search_feedback.")
        source = read_json(directory / f"run.{suffix}", None)
        boundary = read_json(directory / f"boundary_result.{suffix}", None)
        feedback = read_json(feedback_path, None)
        if not all(
            isinstance(row, Mapping) for row in (source, boundary, feedback)
        ):
            continue
        source_core = {
            key: value for key, value in source.items() if key != "run_digest"
        }
        boundary_core = {
            key: value for key, value in boundary.items() if key != "result_sha256"
        }
        feedback_core = {
            key: value for key, value in feedback.items()
            if key != "receipt_sha256"
        }
        if (
            source.get("run_digest") != content_hash(source_core)
            or boundary.get("result_sha256") != content_hash(boundary_core)
            or feedback.get("receipt_sha256") != content_hash(feedback_core)
            or source.get("status")
            != "frontier_candidates_frozen_awaiting_boundary_approval"
            or not str(boundary.get("stop_reason") or "").startswith(
                "blocked_before_action"
            )
            or feedback.get("source_run_digest") != source.get("run_digest")
        ):
            continue
        navigation = dict(source.get("navigation") or {})
        navigation["objective_review_history"] = list(
            navigation.get("objective_review_history") or ()
        ) + [dict(feedback)]
        expected_core = {
            **source_core,
            "status": "frontier_objective_unmet",
            "navigation": navigation,
        }
        expected = {**expected_core, "run_digest": content_hash(expected_core)}
        if dict(run) != expected:
            continue
        write_json_atomic(directory / "run.json", dict(source))
        receipt_core = {
            "schema": "leanmill.partial_boundary_feedback_recovery.v1",
            "source_run_digest": str(source["run_digest"]),
            "partial_boundary_result": str(boundary["result_sha256"]),
            "discarded_feedback_receipt": str(feedback["receipt_sha256"]),
            "authority": "host_outcome_totality_replay",
        }
        write_json_atomic(
            directory / f"partial_boundary_feedback_recovery.{suffix}",
            {**receipt_core, "receipt_sha256": content_hash(receipt_core)},
        )
        return source
    return run


def _archive_incomplete_boundary(directory: Path, completion: Mapping[str, Any]) -> None:
    """Supersede one incomplete boundary attempt without erasing its evidence."""

    from ztare.leanmill.frontier_boundary import FROZEN_BOUNDARY_STOP_POLICY

    completion_core = {
        key: value for key, value in completion.items() if key != "completion_sha256"
    }
    # Recovery identity is derived from bytes, never from the row's claimed
    # digest.  A malformed marker therefore cannot select and conflict with an
    # unrelated archive directory.
    digest = content_hash(completion_core)
    archive = directory / "boundary_attempts" / digest[:16]
    names = (
        "boundary_result.json",
        "boundary_completion.json",
        "budget_stop_receipt.json",
        "theory_task_discharge.json",
        "theory_task_discharge_consumption.json",
        "boundary_governance_recheck.json",
        "campaign_closure_gate.json",
    )
    completion_bound = {
        "boundary_result.json": completion.get("boundary_result"),
        "boundary_completion.json": completion,
        "budget_stop_receipt.json": completion.get("budget_stop_receipt"),
        "theory_task_discharge.json": completion.get("theory_task_discharge"),
    }
    archived: dict[str, dict[str, Any]] = {}
    root_owned: set[str] = set()
    for name in names:
        source = directory / name
        target = archive / name
        source_row = read_json(source, None)
        target_row = read_json(target, None)
        bound_row = completion_bound.get(name)
        selected_row = (
            dict(bound_row)
            if isinstance(bound_row, Mapping)
            else dict(source_row)
            if isinstance(source_row, Mapping)
            else None
        )
        if isinstance(selected_row, Mapping):
            if isinstance(target_row, Mapping) and dict(target_row) != dict(selected_row):
                raise ValueError(f"boundary archive conflicts with {name}")
            if target_row is None:
                write_json_atomic(target, dict(selected_row))
            archived[name] = dict(selected_row)
            if isinstance(source_row, Mapping) and dict(source_row) == dict(selected_row):
                root_owned.add(name)
        elif isinstance(target_row, Mapping):
            archived[name] = dict(target_row)

    embedded_boundary = completion.get("boundary_result")
    embedded_stop = completion.get("budget_stop_receipt")
    boundary = archived.get("boundary_result.json") or (
        dict(embedded_boundary) if isinstance(embedded_boundary, Mapping) else {}
    )
    stop = archived.get("budget_stop_receipt.json") or (
        dict(embedded_stop) if isinstance(embedded_stop, Mapping) else {}
    )
    run = read_json(directory / "run.json", {})
    navigation = run.get("navigation") if isinstance(run, Mapping) else None
    source_reason = str(boundary.get("stop_reason") or stop.get("reason") or "")
    frozen_obligation = bool(
        isinstance(run, Mapping)
        and run.get("status")
        == "frontier_candidates_frozen_awaiting_boundary_approval"
        and isinstance(navigation, Mapping)
        and navigation.get("finalists")
    )
    legacy_soft_cancel = bool(
        frozen_obligation
        and source_reason == "marginal_yield_below_threshold"
        and not (boundary.get("query_results") or ())
    )
    boundary_core = {
        key: value for key, value in boundary.items() if key != "result_sha256"
    }
    stop_core = {
        key: value for key, value in stop.items() if key != "receipt_sha256"
    }
    receipt_core = {
        "schema": "leanmill.boundary_attempt_supersession.v1",
        "supersession_kind": (
            "navigation_soft_stop_cannot_cancel_frozen_boundary"
            if legacy_soft_cancel
            else "completion_does_not_cover_current_boundary_contract"
        ),
        "context_hash": str(
            boundary.get("context_hash")
            or completion.get("context_hash")
            or (run.get("context_hash") if isinstance(run, Mapping) else "")
            or ""
        ),
        "prior_run_digest": str(
            run.get("run_digest") if isinstance(run, Mapping) else ""
        ),
        "superseded_completion_sha256": str(
            completion.get("completion_sha256") or content_hash(completion)
        ),
        "superseded_completion_digest_valid": (
            completion.get("completion_sha256") == content_hash(completion_core)
        ),
        "superseded_boundary_result_sha256": str(
            boundary.get("result_sha256") or content_hash(boundary)
        ),
        "superseded_boundary_result_digest_valid": bool(
            boundary_core
            and boundary.get("result_sha256") == content_hash(boundary_core)
        ),
        "superseded_budget_stop_receipt_sha256": str(
            stop.get("receipt_sha256") or ""
        ),
        "superseded_budget_stop_digest_valid": bool(
            stop_core
            and stop.get("receipt_sha256") == content_hash(stop_core)
        ),
        "source_stop_reason": source_reason,
        "prior_stop_policy": str(boundary.get("stop_policy") or "legacy_unversioned"),
        "current_stop_policy": FROZEN_BOUNDARY_STOP_POLICY,
        "archive_relative_path": str(archive.relative_to(directory)),
        "authority": "deterministic_boundary_lifecycle",
    }
    receipt = {
        **receipt_core,
        "receipt_sha256": content_hash(receipt_core),
    }
    archive_receipt = archive / "boundary_attempt_supersession.json"
    root_receipt = directory / (
        "boundary_attempt_supersession."
        + str(receipt["receipt_sha256"])[:16]
        + ".json"
    )
    for path in (archive_receipt, root_receipt):
        prior = read_json(path, None)
        if isinstance(prior, Mapping) and dict(prior) != receipt:
            raise ValueError("boundary supersession changed after first fire")
        if prior is None:
            write_json_atomic(path, receipt)

    # Remove only artifacts proven to belong to this completion.  A newer
    # partial boundary may coexist with an older completion marker after a
    # crash; preserving its differing root bytes lets the retry resume it.
    for name in names:
        if name == "boundary_completion.json" or name not in root_owned:
            continue
        (directory / name).unlink(missing_ok=True)
    if "boundary_completion.json" in root_owned:
        (directory / "boundary_completion.json").unlink(missing_ok=True)


def _boundary_completion_stop_reason(
    budget_ledger: ExplorationBudgetLedger,
    boundary: Any,
) -> str:
    """Resolve terminal boundary state using only obligation-owning stops."""

    return budget_ledger.hard_stop_reason() or str(boundary.stop_reason)


def _adjudicate_theory_program_tasks(
    directory: Path,
    *,
    adapter_id: str,
    navigation: Mapping[str, Any],
    boundary_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Lower frozen program outputs after the boundary digest becomes immutable."""

    from ztare.common.schema_routes import append_consequence_event
    from ztare.leanmill.theory_adapter_registry import adjudicate_theory_adapter_task
    from ztare.leanmill.theory_program import TheoryProgram

    boundary_ref = str(boundary_result.get("result_sha256") or "")
    boundary_core = {
        key: value for key, value in boundary_result.items()
        if key != "result_sha256"
    }
    if not boundary_ref or boundary_ref != content_hash(boundary_core):
        raise ValueError("theory-task adjudication requires an immutable boundary result")
    path = directory / "theory_task_discharge.json"
    existing = read_json(path, None)
    if isinstance(existing, Mapping):
        core = {key: value for key, value in existing.items() if key != "receipt_sha256"}
        if existing.get("receipt_sha256") != content_hash(core):
            raise ValueError("theory-task discharge artifact crossed boundary identity")
        if existing.get("boundary_result_sha256") == boundary_ref:
            return dict(existing)

        predecessor_ref = str(existing.get("boundary_result_sha256") or "")
        predecessor_archives = []
        for archived_boundary_path in sorted(
            directory.glob("boundary_attempts/*/boundary_result.json")
        ):
            archived_boundary = read_json(archived_boundary_path, None)
            if not isinstance(archived_boundary, Mapping):
                continue
            archived_core = {
                key: value for key, value in archived_boundary.items()
                if key != "result_sha256"
            }
            if (
                archived_boundary.get("result_sha256") == predecessor_ref
                and predecessor_ref == content_hash(archived_core)
            ):
                predecessor_archives.append(archived_boundary_path.parent)
        if not predecessor_archives:
            raise ValueError("theory-task discharge artifact crossed boundary identity")
        for predecessor_archive in predecessor_archives:
            archived_discharge = predecessor_archive / path.name
            prior_archived = read_json(archived_discharge, None)
            if isinstance(prior_archived, Mapping):
                if dict(prior_archived) != dict(existing):
                    raise ValueError("archived theory-task discharge conflicts")
            else:
                write_json_atomic(archived_discharge, dict(existing))
        path.unlink()

    rows: list[dict[str, Any]] = []
    explicit_by_program: dict[str, list[str]] = {}
    for finalist in navigation.get("finalists") or ():
        if not isinstance(finalist, Mapping) or not isinstance(
            finalist.get("theory_program"), Mapping
        ):
            continue
        program = TheoryProgram.from_json(finalist["theory_program"])
        explicit = {row.sha256 for row in program.task_discharge_contracts}
        explicit_by_program[program.program_id] = []
        for contract in program.executable_task_contracts():
            receipt = adjudicate_theory_adapter_task(
                adapter_id,
                contract,
                boundary_result=boundary_result,
            )
            source = "explicit_task" if contract.sha256 in explicit else "legacy_prediction"
            row_core = {
                "schema": "leanmill.theory_task_discharge_row.v1",
                "program_id": program.program_id,
                "source": source,
                "contract": contract.to_dict(),
                "contract_sha256": contract.sha256,
                "receipt": receipt.to_dict(),
            }
            row = {**row_core, "receipt_sha256": content_hash(row_core)}
            rows.append(row)
            if source == "explicit_task":
                explicit_by_program[program.program_id].append(receipt.status)
            append_consequence_event(
                directory,
                contract_id="theory_program_task_outcome_totality.v1",
                subject_id=f"{program.program_id}:{contract.sha256}",
                outcome=receipt.status,
                event="produced",
                evidence_refs=(str(row["receipt_sha256"]),),
            )

    program_outcomes = {}
    for program_id, statuses in explicit_by_program.items():
        program_outcomes[program_id] = (
            "not_declared"
            if not statuses
            else "discharged"
            if all(status == "discharged" for status in statuses)
            else "unavailable"
            if any(status == "unavailable" for status in statuses)
            else "open"
        )
    declared = [status for status in program_outcomes.values() if status != "not_declared"]
    program_status = (
        "not_declared"
        if not declared
        else "discharged"
        if "discharged" in declared
        else "unavailable"
        if all(status == "unavailable" for status in declared)
        else "open"
    )
    core = {
        "schema": "leanmill.theory_task_discharge.v1",
        "adapter_id": adapter_id,
        "boundary_result_sha256": boundary_ref,
        "rows": rows,
        "program_outcomes": program_outcomes,
        "explicit_program_status": program_status,
        "authority": "registered_adapter_receipts_host_aggregation",
    }
    result = {**core, "receipt_sha256": content_hash(core)}
    write_json_atomic(path, result)
    return result


def _validated_construction_boundary_recovery_activation(
    directory: Path,
    run: Mapping[str, Any],
    *,
    lean_executor_fn: Callable[[Any], Mapping[str, Any]] | None,
    isabelle_executor_fn: Callable[..., Mapping[str, Any]] | None,
    raw_boundary_fn: Callable[..., Mapping[str, Any]] | None,
    countermodel_fn: Callable[..., Any] | None,
    single_premise_audit_fn: Callable[
        [tuple[str, ...], str], Mapping[str, Any]
    ]
    | None,
    theory_task_executor_fn: Callable[..., Mapping[str, Any]] | None,
) -> Mapping[str, Any] | None:
    """Admit one budget-stopped read model only to its witness executor."""

    navigation = run.get("navigation")
    activation = (
        navigation.get("construction_boundary_recovery_activation")
        if isinstance(navigation, Mapping)
        else None
    )
    if run.get("status") != "budget_stopped" or not isinstance(
        activation, Mapping
    ):
        return None
    active_run_core = {
        key: value for key, value in run.items() if key != "run_digest"
    }
    if run.get("run_digest") != content_hash(active_run_core):
        raise ValueError("construction recovery run digest mismatch")
    required = {
        "schema",
        "source_run_sha256",
        "rebuilt_run_sha256",
        "source_budget_stop_receipt_sha256",
        "latest_budget_stop_receipt_sha256",
        "execution_coordinate_sha256s",
        "executor_kind",
        "authority",
        "receipt_sha256",
    }
    activation_core = {
        key: value for key, value in activation.items() if key != "receipt_sha256"
    }
    if (
        set(activation) != required
        or activation.get("schema")
        != "leanmill.construction_boundary_recovery_activation.v1"
        or activation.get("receipt_sha256") != content_hash(activation_core)
        or activation.get("executor_kind")
        != "data_only_witness_construction"
        or activation.get("authority")
        != "reviewed_construction_campaign_transition"
        or theory_task_executor_fn is None
        or lean_executor_fn is not None
        or isabelle_executor_fn is not None
        or raw_boundary_fn is not None
        or countermodel_fn is not None
        or single_premise_audit_fn is not None
    ):
        raise ValueError("construction boundary recovery activation is invalid")
    activation_path = directory / (
        "construction_boundary_recovery_activation."
        f"{str(activation['receipt_sha256'])[:16]}.json"
    )
    activation_slot = read_bounded_json_authority_slot(
        activation_path,
        max_bytes=_MAX_CONSTRUCTION_RECOVERY_AUTHORITY_SLOT_BYTES,
        context="construction boundary recovery activation",
    )
    if activation_slot is None or activation_slot[0] != dict(activation):
        raise ValueError("construction boundary recovery activation is not frozen")

    source_digest = str(activation.get("source_run_sha256") or "")
    if len(source_digest) != 64 or any(
        character not in "0123456789abcdef" for character in source_digest
    ):
        raise ValueError("construction recovery source run digest is malformed")
    source_slot = read_bounded_json_authority_slot(
        directory / f"construction_recovery_source_run.{source_digest[:16]}.json",
        max_bytes=_MAX_CONSTRUCTION_RECOVERY_AUTHORITY_SLOT_BYTES,
        context="construction recovery source run",
    )
    source = source_slot[0] if source_slot is not None else None
    source_core = (
        {key: value for key, value in source.items() if key != "run_digest"}
        if isinstance(source, Mapping)
        else {}
    )
    source_stop_raw = (
        source.get("budget_stop_receipt")
        if isinstance(source, Mapping)
        else None
    )
    if (
        not isinstance(source, Mapping)
        or source.get("run_digest") != source_digest
        or source_digest != content_hash(source_core)
        or source.get("status") != "budget_stopped"
        or not isinstance(source_stop_raw, Mapping)
    ):
        raise ValueError("construction recovery source run is invalid")
    source_stop = BudgetStopReceipt.from_json(source_stop_raw)
    if source_stop.to_json()["receipt_sha256"] != activation.get(
        "source_budget_stop_receipt_sha256"
    ):
        raise ValueError("construction recovery source stop changed identity")
    source_stop_path = directory / (
        "construction_recovery_source_budget_stop."
        f"{source_stop.to_json()['receipt_sha256'][:16]}.json"
    )
    source_stop_slot = read_bounded_json_authority_slot(
        source_stop_path,
        max_bytes=_MAX_CONSTRUCTION_RECOVERY_AUTHORITY_SLOT_BYTES,
        context="construction recovery source budget stop",
    )
    if (
        source_stop_slot is None
        or source_stop_slot[0] != source_stop.to_json()
        or run.get("budget_stop_receipt") != source_stop.to_json()
        or run.get("context_hash") != source.get("context_hash")
        or int(run.get("provider_calls", -1))
        != int(source.get("provider_calls", -2))
    ):
        raise ValueError("construction recovery source stop is not preserved")

    budget = ExplorationBudget.from_json(read_json(directory / "budget.json", {}))
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        budget,
        attempt_id=directory.name,
    )
    latest_stop = ledger.latest_stop_receipt()
    latest_stop_json = latest_stop.to_json() if latest_stop is not None else None
    ledger_state = ledger.state()
    if (
        latest_stop is None
        or latest_stop_json is None
        or latest_stop_json.get("receipt_sha256")
        != activation.get("latest_budget_stop_receipt_sha256")
        or latest_stop.reason != source_stop.reason
        or latest_stop.budget_digest != source_stop.budget_digest
        or latest_stop.attempt_id != source_stop.attempt_id
        or latest_stop.context_hash != source_stop.context_hash
        or dict(latest_stop.usage) != dict(ledger_state["usage"])
        or dict(latest_stop.phase_usage) != dict(ledger_state["phase_usage"])
        or int(latest_stop.usage.get("provider_calls", -1))
        != int(run.get("provider_calls", -2))
    ):
        raise ValueError("construction recovery latest budget stop changed identity")

    active_navigation = dict(navigation)
    active_navigation.pop("construction_boundary_recovery_activation", None)
    rebuilt_core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "navigation": active_navigation,
    }
    if content_hash(rebuilt_core) != activation.get("rebuilt_run_sha256"):
        raise ValueError("construction recovery activation crossed rebuilt state")

    from ztare.leanmill.witness_construction_boundary import (
        GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR,
        WitnessConstructionCandidateEnvelope,
        witness_construction_parameters,
    )

    coordinates: list[str] = []
    finalists = navigation.get("finalists") or ()
    if not finalists:
        raise ValueError("construction recovery activation has no finalists")
    for finalist in finalists:
        if not isinstance(finalist, Mapping) or not isinstance(
            finalist.get("theory_program"), Mapping
        ):
            raise ValueError("construction recovery finalist is malformed")
        program = TheoryProgram.from_json(finalist["theory_program"])
        if program.prediction_formula_ids or not program.task_discharge_contracts:
            raise ValueError("construction recovery is not witness-executor-only")
        for contract in program.task_discharge_contracts:
            if (
                contract.adjudicator_id
                != GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR
            ):
                raise ValueError(
                    "construction recovery crossed its witness executor"
                )
            parameters = witness_construction_parameters(contract)
            candidate = WitnessConstructionCandidateEnvelope.from_json(
                parameters["candidate_envelope"]
            )
            coordinates.append(
                str(candidate.execution_coordinate["coordinate_sha256"])
            )
    if sorted(coordinates) != list(
        activation.get("execution_coordinate_sha256s") or ()
    ):
        raise ValueError("construction recovery coordinates changed identity")
    return activation


def execute_frontier_boundaries(
    attempt_dir: str | Path,
    *,
    lean_executor_fn: Callable[[Any], Mapping[str, Any]] | None = None,
    isabelle_executor_fn: Callable[..., Mapping[str, Any]] | None = None,
    raw_boundary_fn: Callable[..., Mapping[str, Any]] | None = None,
    countermodel_fn: Callable[..., Any] | None = None,
    single_premise_audit_fn: Callable[
        [tuple[str, ...], str], Mapping[str, Any]
    ]
    | None = None,
    theory_task_executor_fn: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Resume one frozen attempt at the separately approved boundary phase."""
    directory = Path(attempt_dir)
    preexisting_run = read_json(directory / "run.json", None)
    if isinstance(preexisting_run, Mapping):
        _validated_construction_boundary_recovery_activation(
            directory,
            preexisting_run,
            lean_executor_fn=lean_executor_fn,
            isabelle_executor_fn=isabelle_executor_fn,
            raw_boundary_fn=raw_boundary_fn,
            countermodel_fn=countermodel_fn,
            single_premise_audit_fn=single_premise_audit_fn,
            theory_task_executor_fn=theory_task_executor_fn,
        )
    existing = read_json(directory / "boundary_completion.json", None)
    if isinstance(existing, dict) and existing:
        prior_blueprint = read_json(directory / "blueprint.json", {})
        prior_run = read_json(directory / "run.json", {})
        plan = (
            prior_blueprint.get("verification_plan")
            if isinstance(prior_blueprint, Mapping)
            else {}
        ) or {}
        if _boundary_completion_covers(
            existing,
            plan,
            (prior_run.get("navigation") or {})
            if isinstance(prior_run, Mapping) else {},
            lean_requested=lean_executor_fn is not None,
            isabelle_requested=isabelle_executor_fn is not None,
            theory_task_requested=theory_task_executor_fn is not None,
            theory_task_requested_contracts=(
                _registered_boundary_task_contracts(
                    (prior_run.get("navigation") or {})
                    if isinstance(prior_run, Mapping)
                    else {}
                )
                if theory_task_executor_fn is not None
                else frozenset()
            ),
        ):
            if not isinstance(existing.get("theory_task_discharge"), Mapping):
                blueprint = FrontierTheoryBlueprint.from_json(prior_blueprint)
                task_discharge = _adjudicate_theory_program_tasks(
                    directory,
                    adapter_id=blueprint.adapter_id,
                    navigation=(prior_run.get("navigation") or {}),
                    boundary_result=(existing.get("boundary_result") or {}),
                )
                core = {
                    key: value for key, value in existing.items()
                    if key != "completion_sha256"
                }
                core["theory_task_discharge"] = task_discharge
                existing = {**core, "completion_sha256": content_hash(core)}
                write_json_atomic(directory / "boundary_completion.json", existing)
            return existing
        _archive_incomplete_boundary(directory, existing)
    run_row = read_json(directory / "run.json", None)
    blueprint_row = read_json(directory / "blueprint.json", None)
    campaign_row = read_json(directory / "campaign.json", None)
    budget_row = read_json(directory / "budget.json", None)
    if isinstance(run_row, Mapping):
        run_row = _recover_partial_boundary_feedback(directory, run_row)
    if not all(isinstance(row, dict) and row for row in (run_row, blueprint_row, campaign_row, budget_row)):
        raise ValueError("boundary execution requires a completed frozen campaign attempt")
    if run_row.get("status") == "frontier_no_candidate":
        core = {
            "schema": "leanmill.frontier_boundary_completion.v1",
            "status": "campaign_completed_no_candidate",
            "attempt_dir": str(directory),
            "context_hash": str(run_row.get("context_hash") or ""),
            "reject_all_receipt": dict(
                (run_row.get("navigation") or {}).get("reject_all_receipt") or {}
            ),
            "reject_all_sequence_receipt": dict(
                (run_row.get("navigation") or {}).get(
                    "reject_all_sequence_receipt"
                )
                or {}
            ),
            "provider_calls": int(run_row.get("provider_calls", 0)),
        }
        completion = {**core, "completion_sha256": content_hash(core)}
        write_json_atomic(directory / "boundary_completion.json", completion)
        return completion
    recovery_activation = _validated_construction_boundary_recovery_activation(
        directory,
        run_row,
        lean_executor_fn=lean_executor_fn,
        isabelle_executor_fn=isabelle_executor_fn,
        raw_boundary_fn=raw_boundary_fn,
        countermodel_fn=countermodel_fn,
        single_premise_audit_fn=single_premise_audit_fn,
        theory_task_executor_fn=theory_task_executor_fn,
    )
    if (
        run_row.get("status")
        != "frontier_candidates_frozen_awaiting_boundary_approval"
        and recovery_activation is None
    ):
        raise ValueError("campaign attempt is not awaiting boundary approval")
    blueprint = FrontierTheoryBlueprint.from_json(blueprint_row)
    if (directory / "formal_context.json").is_file():
        from ztare.leanmill.finite_theory_context import load_formal_theory_context

        context = load_formal_theory_context(directory / "formal_context.json")
    elif (directory / "evidence_context.json").is_file():
        from ztare.leanmill.evidence_theory_context import load_evidence_theory_context

        context = load_evidence_theory_context(directory / "evidence_context.json")
    else:
        raise ValueError("campaign context snapshot is missing")
    if context.context_hash != run_row.get("context_hash"):
        raise ValueError("campaign context differs from the frozen run")
    validate_campaign_artifact_binding(
        campaign_row,
        blueprint_id=blueprint.blueprint_id,
        context_hash=context.context_hash,
        expected_packet_digest=str(run_row.get("packet_digest") or ""),
    )
    if lean_executor_fn is not None or isabelle_executor_fn is not None:
        blueprint = replace(
            blueprint,
            verification_plan={
                **dict(blueprint.verification_plan),
                "conditional_lean": lean_executor_fn is not None,
                "conditional_isabelle": isabelle_executor_fn is not None,
            },
        )
    navigation = dict(run_row.get("navigation") or {})
    context_epoch = int((run_row.get("context_summary") or {}).get("context_epoch", 0))
    environment = resolve_leaf_workbench_environment(
        "axiompack",
        context=context,
        context_epoch=context_epoch,
        selection_mode=navigator_selection_mode(blueprint),
        max_presentation_size=blueprint.pack_arity,
    )
    select = environment["action_handlers"]["select_theory_presentation"]
    for finalist in navigation.get("finalists") or ():
        finalist_hash = str(finalist.get("context_hash") or "")
        finalist_epoch = finalist.get("context_epoch")
        if (
            finalist_hash
            and finalist_hash != context.context_hash
            or type(finalist_epoch) is int
            and finalist_epoch != context_epoch
        ):
            raise ValueError("boundary finalist belongs to another context epoch")
        formulas = [str(row) for row in finalist.get("formula_ids") or ()]
        selection_mode = str(
            finalist.get("candidate_kind") or navigator_selection_mode(blueprint)
        )
        nominated_targets = tuple(
            str(row) for row in finalist.get("boundary_target_ids") or ()
        )
        program = (
            TheoryProgram.from_json(finalist["theory_program"])
            if selection_mode == "theory_program"
            else None
        )
        selection_inputs = {"formula_ids": formulas}
        if selection_mode == "theory_program" and nominated_targets:
            selection_inputs["prediction_formula_ids"] = list(nominated_targets)
        receipt = select(
            ".",
            {"input_refs": selection_inputs},
            None,
            environment["contract"],
        )
        summary = dict(receipt.get("output_summary") or {})
        expected_residual = tuple(
            sorted(
                str(row)
                for row in (
                    finalist.get("residual_prediction_formula_ids")
                    if selection_mode == "theory_program"
                    else finalist.get("residual_joint_only_consequence_ids")
                )
                or ()
            )
        )
        actual_residual = tuple(
            sorted(
                str(row)
                for row in (
                    summary.get("residual_prediction_formula_ids")
                    if selection_mode == "theory_program"
                    else summary.get("residual_synergy_formula_ids")
                )
                or ()
            )
        )
        coordinates_source = (
            (summary.get("program_yield") or {}).get("coordinates")
            if selection_mode == "theory_program"
            else summary.get("residual_yield")
        )
        coordinates = dict(coordinates_source or {})
        frozen_coordinates = dict(finalist.get("residual_information_yield") or {})
        invalid = bool(
            finalist.get("selection_receipt_id")
            and receipt.get("receipt_id") != finalist.get("selection_receipt_id")
        ) or len(set(nominated_targets)) != len(nominated_targets)
        if selection_mode == "theory_program":
            frozen_profile = finalist.get("prediction_profile")
            replayed_profile = summary.get("prediction_profile")
            invalid = invalid or not isinstance(program, TheoryProgram) or (
                nominated_targets != program.prediction_formula_ids
            )
            if nominated_targets:
                invalid = invalid or not isinstance(
                    frozen_profile, Mapping
                ) or not isinstance(replayed_profile, Mapping) or (
                    frozen_profile.get("receipt_sha256")
                    != replayed_profile.get("receipt_sha256")
                )
            else:
                invalid = invalid or not program.task_discharge_contracts or (
                    frozen_profile is not None or replayed_profile is not None
                )
        else:
            invalid = invalid or (
                actual_residual != expected_residual
                or any(row not in actual_residual for row in nominated_targets)
                or (frozen_coordinates and coordinates != frozen_coordinates)
                or not actual_residual
                or float(coordinates.get("identification_bits", 0.0)) <= 0.0
            )
        if invalid:
            raise ValueError(
                "frozen finalist no longer passes deterministic "
                + ("selection replay" if selection_mode == "theory_program" else "residual replay")
            )
    program_finalists = [
        row
        for row in navigation.get("finalists") or ()
        if isinstance(row, Mapping)
        and isinstance(row.get("theory_program"), Mapping)
        and TheoryProgram.from_json(row["theory_program"]).prediction_formula_ids
    ]
    program_lineages = {
        str(row["theory_program"].get("lineage_id") or "")
        for row in program_finalists
    }
    isolation = navigation.get("isolation_receipt")
    if (
        len(program_finalists) >= 2
        and len(program_lineages) == len(program_finalists)
        and "" not in program_lineages
        and isinstance(isolation, Mapping)
    ):
        from ztare.leanmill.theory_program_disagreement_policy import (
            plan_theory_program_disagreement_lifts,
        )

        policy = plan_theory_program_disagreement_lifts(
            context,
            [TheoryProgram.from_json(row["theory_program"]) for row in program_finalists],
            isolation_receipt=isolation,
            max_queries=int(blueprint.query_budget.get("boundary_queries", 1)),
        )
        write_json_atomic(
            directory
            / f"theory_program_disagreement_policy.epoch-{context_epoch:03d}.json",
            policy,
        )
        priority = {
            row["program_id"]: index
            for index, row in enumerate(policy["boundary_lift_requests"])
        }
        navigation["finalists"] = sorted(
            navigation.get("finalists") or (),
            key=lambda row: priority.get(row.get("theory_program_id"), len(priority)),
        )
    budget_contract = ExplorationBudget.from_json(budget_row)
    budget_ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        budget_contract,
        attempt_id=directory.name,
    )
    from ztare.leanmill.frontier_boundary import run_frontier_boundaries

    kwargs: dict[str, Any] = {
        "lean_executor_fn": lean_executor_fn,
        "isabelle_executor_fn": isabelle_executor_fn,
        "raw_boundary_fn": raw_boundary_fn,
        "conflict_ledger": open_theory_conflict_ledger(
            context, directory.parent / "theory_conflicts.jsonl"
        ),
    }
    if theory_task_executor_fn is not None:
        kwargs["theory_task_executor_fn"] = theory_task_executor_fn
    if countermodel_fn is not None:
        kwargs["countermodel_fn"] = countermodel_fn
    if single_premise_audit_fn is None and recovery_activation is None:
        oracle_config = blueprint.verification_plan.get("single_premise_oracle")
        if oracle_config is not None:
            if not isinstance(oracle_config, Mapping):
                raise ValueError("single_premise_oracle must be an object")
            from ztare.leanmill.theory_adapter_registry import (
                materialize_theory_adapter_capability,
            )

            oracle = materialize_theory_adapter_capability(
                blueprint.adapter_id,
                "single_premise_implication_oracle",
                adapter_config=blueprint.adapter_config,
                oracle_config=oracle_config,
            )
            single_premise_audit_fn = oracle.audit
    if (
        single_premise_audit_fn is None
        and recovery_activation is None
        and not isinstance(
        context, EvidenceTheoryContext
        )
    ):
        from ztare.leanmill.finite_context_ablation import (
            audit_finite_context_single_premises,
        )

        single_premise_audit_fn = lambda premises, target: (
            audit_finite_context_single_premises(context, premises, target)
        )
    if single_premise_audit_fn is not None:
        kwargs["single_premise_audit_fn"] = single_premise_audit_fn
    kwargs["prior_query_results"] = _prior_boundary_query_results(
        directory, context_hash=context.context_hash
    )
    campaign_id = str(campaign_row.get("packet", {}).get("campaign_id") or "")
    boundary = run_frontier_boundaries(
        context,
        blueprint,
        navigation,
        TheoryCampaignJournal(directory / "events.jsonl"),
        budget_ledger,
        attempt_id=directory.name,
        campaign_id=campaign_id,
        **kwargs,
    )
    boundary_json = boundary.to_json()
    write_json_atomic(directory / "boundary_result.json", boundary_json)
    task_discharge = _adjudicate_theory_program_tasks(
        directory,
        adapter_id=blueprint.adapter_id,
        navigation=navigation,
        boundary_result=boundary_json,
    )
    stop_reason = _boundary_completion_stop_reason(budget_ledger, boundary)
    stop_receipt = budget_ledger.stop_receipt(
        stop_reason,
        context_hash=context.context_hash,
    ).to_json()
    write_json_atomic(directory / "budget_stop_receipt.json", stop_receipt)
    usage = budget_ledger.state()["usage"]
    core = {
        "schema": "leanmill.frontier_boundary_completion.v1",
        "status": (
            "campaign_completed"
            if stop_reason in {"campaign_finished", "target_reached"}
            else "campaign_stopped"
        ),
        "attempt_dir": str(directory),
        "context_hash": context.context_hash,
        "stop_policy": boundary_json.get("stop_policy"),
        "boundary_result": boundary_json,
        "theory_task_discharge": task_discharge,
        "budget_stop_receipt": stop_receipt,
        "provider_calls": int(usage["provider_calls"])
        + int(run_row.get("preparation_provider_calls", 0)),
    }
    completion = {**core, "completion_sha256": content_hash(core)}
    write_json_atomic(directory / "boundary_completion.json", completion)
    return completion


__all__ = [
    "FrontierExplorationRun", "admit_frontier_formula_epoch",
    "admit_frontier_formula_epoch_batch",
    "compile_campaign_brief", "consume_theory_language_compilation",
    "execute_frontier_boundaries",
    "explore_axiom_space", "lower_theory_language_request",
    "packet_for_frontier_context",
]
