"""Compile a permissive research direction into a reviewed typed campaign."""
from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Callable, Mapping

from ztare.leanmill.frontier_blueprint import (
    FrontierExplorationBrief,
    FrontierTheoryBlueprint,
    theory_task_capability_scope,
    validate_navigator_contract,
)
from ztare.leanmill.adapter_forge import AdapterGap, AdapterGapRequired
from ztare.leanmill.theory_adapter_registry import (
    preflight_theory_adapter,
    theory_adapter_capabilities,
    theory_task_capability_catalog,
)
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    TheorySignature,
    content_hash,
    validate_axioms,
)
from ztare.leanmill import prompts


DraftFn = Callable[[Mapping[str, Any]], Mapping[str, Any]]
ReviewFn = Callable[[Mapping[str, Any]], Mapping[str, Any]]

_DRAFT_FIELDS = {
    "mode", "eigenquestion", "signature", "primitive_semantics", "base_axioms",
    "base_theory_status", "adapter_id", "adapter_config", "formula_grammar",
    "model_or_observation_strata", "pack_arity", "collapse_controls",
    "visible_evidence_manifest", "sealed_evidence_manifest_digest",
    "deanchoring_policy", "navigator_contract", "query_budget", "stop_rule",
    "verification_plan", "codec_versions", "authority_refs",
}
_HOST_DRAFT_FIELDS = {
    "visible_evidence_manifest", "sealed_evidence_manifest_digest", "authority_refs",
}
_MODEL_DRAFT_FIELDS = _DRAFT_FIELDS - _HOST_DRAFT_FIELDS
_BANNED_COLD_KEYS = {
    "candidate_axioms", "candidate_axiom_templates", "axiom_templates",
    "named_axiom_list", "formula_universe",
}
_MAPPING_FIELDS = frozenset(
    {
        "signature", "primitive_semantics", "adapter_config", "formula_grammar",
        "visible_evidence_manifest", "deanchoring_policy", "navigator_contract",
        "query_budget", "stop_rule", "verification_plan", "codec_versions",
    }
)
_MAPPING_SEQUENCE_FIELDS = frozenset(
    {"base_axioms", "model_or_observation_strata", "collapse_controls"}
)


def _canonicalize_verification_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Lower a common NL spelling to the executable boundary vocabulary."""
    canonical = dict(plan)
    alias = canonical.pop("holdout_strata", None)
    if alias is None:
        return canonical
    declared = canonical.get("heldout_strata")
    if declared is not None and declared != alias:
        raise ValueError("holdout and heldout strata disagree")
    canonical["heldout_strata"] = alias
    return canonical


def _find_banned(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            here = f"{path}.{key}" if path else str(key)
            if str(key).lower() in _BANNED_COLD_KEYS:
                found.append(here)
            found.extend(_find_banned(child, here))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_banned(child, f"{path}[{index}]"))
    return found


def render_frontier_blueprint_prompt(brief: FrontierExplorationBrief | Mapping[str, Any]) -> str:
    brief_json = brief.to_json() if isinstance(brief, FrontierExplorationBrief) else dict(brief)
    return prompts.FRONTIER_BLUEPRINT_COMPILER_PROMPT.format(
        required_fields=", ".join(sorted(_MODEL_DRAFT_FIELDS)),
        brief_json=json.dumps(brief_json, sort_keys=True, separators=(",", ":")),
    )


def _executable_preflight(
    brief: FrontierExplorationBrief, draft: Mapping[str, Any]
) -> dict[str, Any]:
    signature = TheorySignature.from_json(draft["signature"])
    base_axioms = tuple(AxiomFormula.from_json(row) for row in draft["base_axioms"])
    semantic_hashes = [row.semantic_hash for row in base_axioms]
    if len(set(semantic_hashes)) != len(semantic_hashes):
        duplicates = sorted(
            row.name
            for index, row in enumerate(base_axioms)
            if row.semantic_hash in semantic_hashes[:index]
        )
        raise ValueError(
            "typed base_axioms contain duplicate semantic formulas: "
            + ", ".join(duplicates)
        )
    validate_axioms(signature, base_axioms)
    base_status = draft.get("base_theory_status")
    if base_status not in {"explicit_empty", "typed_resolved"}:
        raise ValueError("base_theory_status must be explicit_empty or typed_resolved")
    if (base_status == "explicit_empty") != (not base_axioms):
        raise ValueError("base_theory_status does not match the typed base_axioms")
    semantics = draft.get("primitive_semantics")
    if not isinstance(semantics, Mapping):
        raise ValueError("primitive_semantics must be an object")
    operation_bindings = semantics.get("operation_bindings")
    relation_bindings = semantics.get("relation_bindings", {})
    if not isinstance(operation_bindings, Mapping) or not isinstance(relation_bindings, Mapping):
        raise ValueError("primitive semantics require operation/relation binding maps")
    if set(operation_bindings) != {row.name for row in signature.operations}:
        raise ValueError("primitive semantics do not bind every operation exactly")
    if set(relation_bindings) != {row.name for row in signature.relations}:
        raise ValueError("primitive semantics do not bind every relation exactly")
    try:
        adapter = preflight_theory_adapter(
            str(draft["adapter_id"]),
            signature,
            adapter_config=dict(draft["adapter_config"]),
            formula_grammar=dict(draft["formula_grammar"]),
            strata=tuple(dict(row) for row in draft["model_or_observation_strata"]),
        )
    except ValueError as exc:
        if "unregistered theory adapter" not in str(exc):
            raise
        raise AdapterGapRequired(
            AdapterGap(
                brief_digest=brief.brief_id,
                proposed_adapter_id=str(draft["adapter_id"]),
                primitive_semantics_contract=dict(semantics),
                raw_fixture_refs=brief.evidence_refs,
                required_context_kind=(
                    "exact" if draft["mode"] == "anonymous_signature_census" else "sampled"
                ),
                required_operations=tuple(row.name for row in signature.operations),
                required_receipts=(
                    "adapter_manifest", "determinism_self_test", "serialization_roundtrip",
                    "claim_boundary_test", "raw_checker_fixture_replay",
                ),
                forbidden_authorities=(
                    "live_registry_mutation", "self_certified_exactness", "provider_trust_root",
                ),
                acceptance_tests=(
                    "TheorySubstrateAdapter protocol parity",
                    "frozen fixture replay",
                    "sampled versus exact fail-closed behavior",
                    "cold navigator projection contains no sealed raw data",
                ),
            )
        ) from exc
    formula_count = adapter.get("formula_count")
    pack_arity = draft.get("pack_arity")
    if (
        type(formula_count) is not int
        or formula_count < 1
        or type(pack_arity) is not int
        or not 1 <= pack_arity <= formula_count
    ):
        raise ValueError(
            "blueprint pack_arity must fit the preflighted formula universe"
        )
    requested_capabilities = set()
    verification_plan = draft.get("verification_plan")
    if (
        isinstance(verification_plan, Mapping)
        and verification_plan.get("single_premise_oracle") is not None
    ):
        requested_capabilities.add("single_premise_implication_oracle")
    if isinstance(verification_plan, Mapping) and (
        verification_plan.get("larger_carriers")
        or verification_plan.get("larger_model_strata")
        or verification_plan.get("heldout_strata")
    ):
        requested_capabilities.add("fixed_size_countermodel_finder")
    missing_capabilities = requested_capabilities - set(
        theory_adapter_capabilities(str(draft["adapter_id"]))
    )
    if missing_capabilities:
        raise AdapterGapRequired(
            AdapterGap(
                brief_digest=brief.brief_id,
                proposed_adapter_id=str(draft["adapter_id"]),
                primitive_semantics_contract=dict(semantics),
                raw_fixture_refs=brief.evidence_refs,
                required_context_kind=(
                    "exact" if draft["mode"] == "anonymous_signature_census" else "sampled"
                ),
                required_operations=tuple(row.name for row in signature.operations),
                required_receipts=(
                    "capability_manifest",
                    "frozen_fixture_replay",
                    "serialization_roundtrip",
                    "claim_boundary_test",
                    "independent_review",
                ),
                forbidden_authorities=(
                    "live_registry_mutation",
                    "self_certified_source_semantics",
                    "provider_trust_root",
                ),
                acceptance_tests=(
                    "existing adapter identity remains unchanged",
                    "capability is declared in the adapter capability registry",
                    "frozen positive and negative source fixtures replay",
                    "missing or drifted source bytes fail closed",
                ),
                gap_kind="capability_missing",
                missing_capabilities=tuple(sorted(missing_capabilities)),
            )
        )
    task_scope = theory_task_capability_scope(draft["navigator_contract"])
    if task_scope is not None:
        adapter_id = str(draft["adapter_id"])
        if task_scope["adapter_id"] != adapter_id:
            raise ValueError(
                "theory-task capability scope belongs to another adapter"
            )
        registered_task_ids = {
            str(row["capability_id"])
            for row in theory_task_capability_catalog(
                adapter_id,
                adapter_config=dict(draft["adapter_config"]),
            )
        }
        unknown_task_ids = (
            set(task_scope["allowed_capability_ids"]) - registered_task_ids
        )
        if unknown_task_ids:
            raise ValueError(
                "theory-task capability scope names unregistered IDs: "
                + ", ".join(sorted(unknown_task_ids))
            )
    core = {
        "schema": "leanmill.frontier_blueprint_executable_preflight.v1",
        "ok": True,
        "authority_role": "deterministic_executable_preflight",
        "signature_hash": signature.content_hash,
        "adapter_id": str(draft["adapter_id"]),
        "adapter_preflight": adapter,
        "adapter_capabilities": list(
            theory_adapter_capabilities(str(draft["adapter_id"]))
        ),
    }
    if task_scope is not None:
        core["theory_task_capability_scope"] = {
            **task_scope,
            "allowed_capability_ids": list(
                task_scope["allowed_capability_ids"]
            ),
        }
    return {**core, "receipt_sha256": content_hash(core)}


def compile_frontier_blueprint(
    brief: FrontierExplorationBrief,
    *,
    draft_fn: DraftFn,
    semantic_review_fn: ReviewFn,
    compiler_ref: str,
    reviewer_ref: str,
) -> FrontierTheoryBlueprint:
    if not compiler_ref or not reviewer_ref or compiler_ref == reviewer_ref:
        raise ValueError("compiler and reviewer refs must be distinct")
    budget_preference = brief.resource_envelope.get("budget_preference_compilation")
    delegated_stop = (
        str(budget_preference.get("delegated_stop_instruction") or "").strip()
        if isinstance(budget_preference, Mapping) else ""
    )

    def validate(raw: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        if not isinstance(raw, Mapping):
            raise ValueError("frontier blueprint compiler returned no object")
        candidate = dict(raw)
        allowed_shapes = (
            (_DRAFT_FIELDS,)
            if brief.source_mode == "structure_first"
            else (_DRAFT_FIELDS, _MODEL_DRAFT_FIELDS)
        )
        if set(candidate) not in allowed_shapes:
            expected = (
                _DRAFT_FIELDS
                if brief.source_mode == "structure_first"
                else _MODEL_DRAFT_FIELDS
            )
            raise ValueError(
                "frontier blueprint draft fields differ: "
                f"missing={sorted(expected-set(candidate))}, "
                f"extra={sorted(set(candidate)-expected)}"
            )
        if brief.source_mode != "structure_first":
            evidence_manifest = {
                "schema": "leanmill.frontier_visible_evidence_manifest.v1",
                "brief_id": brief.brief_id,
                "source_mode": brief.source_mode,
                "evidence_refs": list(brief.evidence_refs),
                "forbidden_shortcuts": list(brief.forbidden_shortcuts),
            }
            candidate.update({
                "visible_evidence_manifest": evidence_manifest,
                "sealed_evidence_manifest_digest": "sha256:" + content_hash({
                    "brief_id": brief.brief_id,
                    "evidence_refs": list(brief.evidence_refs),
                }),
                "authority_refs": (brief.brief_id,),
            })
            budget_contract = brief.resource_envelope.get("budget_contract")
            hard_caps = (
                budget_contract.get("hard_caps")
                if isinstance(budget_contract, Mapping)
                else None
            )
            generation = candidate["adapter_config"].get("model_generation")
            if (
                isinstance(hard_caps, Mapping)
                and isinstance(generation, Mapping)
                and generation.get("mode") == "smt_exact"
            ):
                context_cap = int(hard_caps.get("context_models", 0))
                if context_cap < 1:
                    raise ValueError("exact census requires a positive host context-model budget")
                stratum_count = max(1, len(candidate["model_or_observation_strata"]))
                candidate["adapter_config"] = {
                    **dict(candidate["adapter_config"]),
                    "model_generation": {
                        **dict(generation),
                        "max_canonical_models_per_stratum": max(
                            1, context_cap // stratum_count
                        ),
                    },
                }
        for field in _MAPPING_FIELDS:
            if not isinstance(candidate[field], Mapping):
                raise ValueError(f"frontier blueprint field {field} must be an object")
        candidate["verification_plan"] = _canonicalize_verification_plan(
            candidate["verification_plan"]
        )
        for field in _MAPPING_SEQUENCE_FIELDS:
            rows = candidate[field]
            if not isinstance(rows, (list, tuple)) or any(
                not isinstance(row, Mapping) for row in rows
            ):
                raise ValueError(
                    f"frontier blueprint field {field} must be an array of objects"
                )
        if not isinstance(candidate["authority_refs"], (list, tuple)) or not candidate[
            "authority_refs"
        ] or any(
            not isinstance(row, str) or not row for row in candidate["authority_refs"]
        ):
            raise ValueError("frontier blueprint authority_refs must be nonempty strings")
        navigator_contract = candidate.get("navigator_contract")
        if not isinstance(navigator_contract, Mapping):
            raise ValueError("frontier blueprint navigator_contract must be an object")
        if brief.source_mode != "structure_first":
            # Overview width is a host rendering choice, independent of the
            # width of theory programs the navigator may author.
            navigator_contract = {
                key: value
                for key, value in navigator_contract.items()
                if key != "topology_presentation_size"
            }
            candidate["navigator_contract"] = navigator_contract
        if "selection_mode" not in navigator_contract:
            candidate["navigator_contract"] = {
                **dict(navigator_contract),
                "selection_mode": "theory_program",
            }
        validate_navigator_contract(
            candidate.get("pack_arity"), candidate["navigator_contract"]
        )
        if candidate.get("mode") == "anonymous_signature_census":
            banned = _find_banned(candidate)
            if banned:
                raise ValueError(f"cold blueprint candidate-law leakage: {banned}")
        stop_rule = candidate["stop_rule"]
        condition = stop_rule.get("executable_condition")
        if (
            not str(stop_rule.get("user_instruction") or "").strip()
            and isinstance(condition, Mapping)
            and str(condition.get("user_instruction") or "").strip()
            and set(condition) == {"kind", "user_instruction"}
        ):
            candidate["stop_rule"] = {
                "user_instruction": str(condition["user_instruction"]).strip(),
                "executable_condition": {"kind": condition.get("kind")},
            }
        if delegated_stop:
            stop_rule = candidate.get("stop_rule")
            if not isinstance(stop_rule, Mapping):
                raise ValueError("delegated scientific stop requires a typed stop_rule")
            if str(stop_rule.get("user_instruction") or "").strip() != delegated_stop:
                raise ValueError("blueprint did not preserve the user's scientific stop instruction")
            executable = stop_rule.get("executable_condition")
            if not isinstance(executable, Mapping) or not executable:
                raise ValueError("blueprint did not lower the scientific stop instruction")
            if executable != {"kind": "late_lineage_objective_review"}:
                raise ValueError("unsupported frontier objective condition kind")
        else:
            stop_rule = candidate["stop_rule"]
            instruction = str(stop_rule.get("user_instruction") or "").strip()
            executable = stop_rule.get("executable_condition")
            if bool(instruction) != isinstance(executable, Mapping):
                raise ValueError(
                    "frontier objective requires both nonempty stop_rule.user_instruction "
                    "and object stop_rule.executable_condition, or neither"
                )
            if instruction and executable != {"kind": "late_lineage_objective_review"}:
                raise ValueError("unsupported frontier objective condition kind")
        preflight = _executable_preflight(brief, candidate)
        if brief.source_mode != "structure_first":
            budget_contract = brief.resource_envelope.get("budget_contract")
            hard_caps = (
                budget_contract.get("hard_caps")
                if isinstance(budget_contract, Mapping)
                else None
            )
            generation = candidate["adapter_config"].get("model_generation")
            adapter_receipt = preflight.get("adapter_preflight")
            if (
                isinstance(hard_caps, Mapping)
                and isinstance(generation, Mapping)
                and generation.get("mode") == "smt_exact"
                and isinstance(adapter_receipt, Mapping)
            ):
                current_cap = int(generation["max_canonical_models_per_stratum"])
                affordable_cap = current_cap
                for budget_key, receipt_key in (
                    ("context_models", "context_model_budget_upper_bound"),
                    ("truth_cells", "truth_cell_budget_upper_bound"),
                ):
                    budget_value = int(hard_caps.get(budget_key, 0))
                    upper_bound = int(adapter_receipt.get(receipt_key, 0))
                    if budget_value > 0 and upper_bound > budget_value:
                        affordable_cap = min(
                            affordable_cap,
                            max(1, current_cap * budget_value // upper_bound),
                        )
                if affordable_cap < current_cap:
                    candidate["adapter_config"] = {
                        **dict(candidate["adapter_config"]),
                        "model_generation": {
                            **dict(generation),
                            "max_canonical_models_per_stratum": affordable_cap,
                        },
                    }
                    preflight = _executable_preflight(brief, candidate)
        return candidate, preflight

    draft_raw = draft_fn(deepcopy(brief.to_json()))
    for attempt in range(3):
        try:
            draft, preflight = validate(draft_raw)
            break
        except ValueError as exc:
            if brief.source_mode == "structure_first" or attempt == 2:
                raise
            repair_input = {
                **deepcopy(brief.to_json()),
                "compiler_feedback": {
                    "attempt": attempt + 1,
                    "error": str(exc),
                    "required_top_level_fields": sorted(_DRAFT_FIELDS),
                    "instruction": "Return the complete corrected draft; do not wrap it.",
                },
                "prior_draft": deepcopy(draft_raw),
            }
            draft_raw = draft_fn(repair_input)
    draft_digest = content_hash(draft)
    review_raw = semantic_review_fn(
        {
            "brief": deepcopy(brief.to_json()),
            "draft": deepcopy(draft),
            "draft_digest": draft_digest,
            "executable_preflight": deepcopy(preflight),
        }
    )
    if not isinstance(review_raw, Mapping) or review_raw.get("accepted") is not True:
        raise ValueError("independent semantic review rejected frontier blueprint")
    if review_raw.get("candidate_law_leakage") is not False:
        raise ValueError("semantic review did not clear candidate-law leakage")
    if review_raw.get("substrate_constraints_executable") is not True:
        raise ValueError(
            "semantic review did not trace every substrate constraint to executable authority"
        )
    if delegated_stop and review_raw.get("stop_rule_aligned") is not True:
        raise ValueError("semantic review did not approve the lowered scientific stop rule")
    compiler_receipt = {
        "schema": "leanmill.frontier_blueprint_compiler_receipt.v1",
        "authority_role": "frontier_blueprint_compiler",
        "compiler_ref": compiler_ref,
        "brief_id": brief.brief_id,
        "draft_digest": draft_digest,
    }
    compiler_receipt["receipt_sha256"] = content_hash(compiler_receipt)
    semantic_review = {
        "schema": "leanmill.frontier_blueprint_semantic_review.v1",
        "authority_role": "frontier_blueprint_semantic_reviewer",
        "reviewer_ref": reviewer_ref,
        "accepted": True,
        "candidate_law_leakage": False,
        "substrate_constraints_executable": True,
        "stop_rule_aligned": bool(review_raw.get("stop_rule_aligned", not delegated_stop)),
        "rationale": str(review_raw.get("rationale") or "").strip(),
        "evidence_refs": [str(row) for row in review_raw.get("evidence_refs") or []],
        "draft_digest": draft_digest,
    }
    if not semantic_review["rationale"] or not semantic_review["evidence_refs"]:
        raise ValueError("semantic review requires rationale and evidence refs")
    semantic_review["receipt_sha256"] = content_hash(semantic_review)
    return FrontierTheoryBlueprint(
        brief_digest=brief.brief_id,
        compiler_receipt=compiler_receipt,
        semantic_review_receipt=semantic_review,
        executable_preflight_receipt=preflight,
        **draft,
    )


def compile_structure_first_blueprint(
    brief: FrontierExplorationBrief,
    typed_draft: Mapping[str, Any],
) -> FrontierTheoryBlueprint:
    if brief.source_mode != "structure_first":
        raise ValueError("deterministic typed compilation requires structure_first source mode")
    return compile_frontier_blueprint(
        brief,
        draft_fn=lambda _brief: dict(typed_draft),
        semantic_review_fn=lambda _payload: {
            "accepted": True,
            "candidate_law_leakage": False,
            "substrate_constraints_executable": True,
            "stop_rule_aligned": True,
            "rationale": "Typed structure was supplied directly and passed independent schema review.",
            "evidence_refs": [brief.brief_id, "deterministic-structure-first-review"],
        },
        compiler_ref="deterministic-structure-first-compiler",
        reviewer_ref="deterministic-structure-first-reviewer",
    )


def compile_language_successor_blueprint(
    source: FrontierTheoryBlueprint,
    *,
    request_id: str,
    target_context: Any,
    transition: Mapping[str, Any],
    adapter_id: str,
    admission_receipt_sha256: str,
    admission_review: Mapping[str, Any],
) -> FrontierTheoryBlueprint:
    """Compile a registered or independently reviewed language successor."""

    if admission_review.get("accepted") is not True:
        raise ValueError("language successor requires accepted admission authority")
    from ztare.leanmill.finite_theory_context import FormalTheoryContext

    if not isinstance(target_context, FormalTheoryContext):
        raise ValueError(
            "finite-model language successor requires a formal target context"
        )
    signature = target_context.signature
    source_count = transition.get("source_object_count")
    image_count = transition.get("canonical_image_model_count")
    if (
        type(source_count) is not int
        or source_count < 1
        or type(image_count) is not int
        or image_count != len(target_context.object_ids)
    ):
        raise ValueError("language successor transition changed its image counts")
    strata_by_hash: dict[str, dict[str, Any]] = {}
    for record in target_context.universe.models:
        row = {"sort_sizes": dict(record.model.sort_sizes)}
        strata_by_hash[content_hash(row)] = row
    strata = tuple(strata_by_hash[key] for key in sorted(strata_by_hash))
    adapter_config = dict(
        transition.get("successor_adapter_config") or source.adapter_config
    )
    generative_representation = transition.get("generative_representation")
    if adapter_id == "generic_fol_finite.v1":
        adapter_config = {
            "functor_image": {
                "receipt_sha256": target_context.universe.receipt.receipt_digest,
                "source_context_hash": str(transition["source_context_hash"]),
                "source_object_count": source_count,
                "canonical_model_count": image_count,
            }
        }
        if isinstance(generative_representation, Mapping):
            adapter_config["generative_representation"] = dict(
                generative_representation
            )
    formula_grammar = transition.get("successor_formula_grammar")
    if not isinstance(formula_grammar, Mapping):
        raise ValueError("language successor lacks its compiled formula grammar")
    adapter_preflight = preflight_theory_adapter(
        adapter_id,
        signature,
        adapter_config=adapter_config,
        formula_grammar=formula_grammar,
        strata=strata,
    )
    image_only = (
        transition.get("complete_relative_to_source") is True
        and not isinstance(generative_representation, Mapping)
    )
    adapter_capabilities = list(theory_adapter_capabilities(adapter_id))
    verification_plan = dict(source.verification_plan)
    if image_only:
        adapter_capabilities = [
            capability
            for capability in adapter_capabilities
            if capability != "fixed_size_countermodel_finder"
        ]
        for key in ("larger_carriers", "larger_model_strata", "heldout_strata"):
            verification_plan.pop(key, None)
        verification_plan["successor_claim_boundary"] = {
            "model_scope": "exact_frozen_source_functor_image",
            "larger_model_generation": "unavailable_without_reviewed_generative_roundtrip",
        }
    elif isinstance(generative_representation, Mapping):
        successor_verification = transition.get("successor_verification_plan")
        if not isinstance(successor_verification, Mapping):
            raise ValueError("generative successor lacks its verification plan")
        for key in ("larger_carriers", "larger_model_strata", "heldout_strata"):
            verification_plan.pop(key, None)
        verification_plan.update(dict(successor_verification))
    preflight_core = {
        "schema": "leanmill.frontier_blueprint_executable_preflight.v1",
        "ok": True,
        "authority_role": "deterministic_executable_preflight",
        "signature_hash": signature.content_hash,
        "adapter_id": adapter_id,
        "adapter_preflight": adapter_preflight,
        "adapter_capabilities": adapter_capabilities,
    }
    compiler_core = {
        "schema": "leanmill.frontier_language_successor_compiler_receipt.v1",
        "authority_role": "frontier_language_successor_compiler",
        "request_id": request_id,
        "source_blueprint_id": source.blueprint_id,
        "transition_receipt_sha256": str(transition["receipt_sha256"]),
        "adapter_id": adapter_id,
        "admission_receipt_sha256": admission_receipt_sha256,
    }
    compiler_receipt = {
        **compiler_core,
        "receipt_sha256": content_hash(compiler_core),
    }
    review_core = {
        "schema": "leanmill.frontier_blueprint_semantic_review.v1",
        "authority_role": "frontier_language_successor_reviewer",
        "reviewer_ref": str(admission_review.get("reviewer_ref") or ""),
        "accepted": True,
        "candidate_law_leakage": False,
        "substrate_constraints_executable": True,
        "stop_rule_aligned": True,
        "rationale": str(admission_review.get("rationale") or "").strip(),
        "evidence_refs": [
            str(row) for row in admission_review.get("evidence_refs") or ()
        ],
        "draft_digest": content_hash(
            {
                "request_id": request_id,
                "signature": signature.to_json(),
                "transition": dict(transition),
            }
        ),
    }
    if (
        not review_core["reviewer_ref"]
        or not review_core["rationale"]
        or not review_core["evidence_refs"]
    ):
        raise ValueError("language successor review lacks attribution or evidence")
    review_receipt = {**review_core, "receipt_sha256": content_hash(review_core)}
    binding_authority = str(
        admission_review.get("binding_authority")
        or "registered_adapter_language_compiler"
    )
    operation_bindings = {
        operation.name: binding_authority for operation in signature.operations
    }
    relation_bindings = {
        relation.name: binding_authority for relation in signature.relations
    }
    successor_navigator_contract = dict(source.navigator_contract)
    source_task_scope = theory_task_capability_scope(
        successor_navigator_contract
    )
    if (
        source_task_scope is not None
        and source_task_scope["adapter_id"] != adapter_id
    ):
        successor_navigator_contract.pop(
            "theory_task_capability_scope", None
        )
    return FrontierTheoryBlueprint(
        brief_digest=source.brief_digest,
        mode="anonymous_signature_census",
        eigenquestion=source.eigenquestion,
        signature=signature.to_json(),
        primitive_semantics={
            "operation_bindings": operation_bindings,
            "relation_bindings": relation_bindings,
        },
        base_axioms=(),
        base_theory_status="explicit_empty",
        adapter_id=adapter_id,
        adapter_config=adapter_config,
        formula_grammar=dict(formula_grammar),
        model_or_observation_strata=strata,
        pack_arity=min(source.pack_arity, len(target_context.formula_ids)),
        collapse_controls=source.collapse_controls,
        visible_evidence_manifest={
            **dict(source.visible_evidence_manifest),
            "language_successor_request_id": request_id,
        },
        sealed_evidence_manifest_digest=source.sealed_evidence_manifest_digest,
        deanchoring_policy=dict(source.deanchoring_policy),
        navigator_contract=successor_navigator_contract,
        query_budget=dict(source.query_budget),
        stop_rule=dict(source.stop_rule),
        verification_plan=verification_plan,
        codec_versions=dict(source.codec_versions),
        authority_refs=tuple(
            dict.fromkeys(
                (*source.authority_refs, request_id, admission_receipt_sha256)
            )
        ),
        compiler_receipt=compiler_receipt,
        semantic_review_receipt=review_receipt,
        executable_preflight_receipt={
            **preflight_core,
            "receipt_sha256": content_hash(preflight_core),
        },
    )


__all__ = [
    "compile_frontier_blueprint", "compile_language_successor_blueprint",
    "compile_structure_first_blueprint",
    "render_frontier_blueprint_prompt",
]
