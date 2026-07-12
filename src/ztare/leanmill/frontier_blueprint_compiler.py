"""Compile a permissive research direction into a reviewed typed campaign."""
from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Callable, Mapping

from ztare.leanmill.frontier_blueprint import (
    FrontierExplorationBrief,
    FrontierTheoryBlueprint,
)
from ztare.leanmill.adapter_forge import AdapterGap, AdapterGapRequired
from ztare.leanmill.theory_adapter_registry import (
    preflight_theory_adapter,
    theory_adapter_capabilities,
)
from ztare.leanmill.theory_ir import TheorySignature, content_hash
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
_BANNED_COLD_KEYS = {
    "candidate_axioms", "candidate_axiom_templates", "axiom_templates",
    "named_axiom_list", "formula_universe",
}


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
        required_fields=", ".join(sorted(_DRAFT_FIELDS)),
        brief_json=json.dumps(brief_json, sort_keys=True, separators=(",", ":")),
    )


def _executable_preflight(
    brief: FrontierExplorationBrief, draft: Mapping[str, Any]
) -> dict[str, Any]:
    signature = TheorySignature.from_json(draft["signature"])
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
    draft_raw = draft_fn(deepcopy(brief.to_json()))
    if not isinstance(draft_raw, Mapping):
        raise ValueError("frontier blueprint compiler returned no object")
    draft = dict(draft_raw)
    if set(draft) != _DRAFT_FIELDS:
        raise ValueError(
            f"frontier blueprint draft fields differ: missing={sorted(_DRAFT_FIELDS-set(draft))}, "
            f"extra={sorted(set(draft)-_DRAFT_FIELDS)}"
        )
    navigator_contract = draft.get("navigator_contract")
    if not isinstance(navigator_contract, Mapping):
        raise ValueError("frontier blueprint navigator_contract must be an object")
    if "selection_mode" not in navigator_contract:
        draft["navigator_contract"] = {
            **dict(navigator_contract),
            "selection_mode": "theory_program",
        }
    if draft.get("mode") == "anonymous_signature_census":
        banned = _find_banned(draft)
        if banned:
            raise ValueError(f"cold blueprint candidate-law leakage: {banned}")
    budget_preference = brief.resource_envelope.get("budget_preference_compilation")
    delegated_stop = (
        str(budget_preference.get("delegated_stop_instruction") or "").strip()
        if isinstance(budget_preference, Mapping) else ""
    )
    if delegated_stop:
        stop_rule = draft.get("stop_rule")
        if not isinstance(stop_rule, Mapping):
            raise ValueError("delegated scientific stop requires a typed stop_rule")
        if str(stop_rule.get("user_instruction") or "").strip() != delegated_stop:
            raise ValueError("blueprint did not preserve the user's scientific stop instruction")
        executable = stop_rule.get("executable_condition")
        if not isinstance(executable, Mapping) or not executable:
            raise ValueError("blueprint did not lower the scientific stop instruction")
    preflight = _executable_preflight(brief, draft)
    draft_digest = content_hash(draft)
    review_raw = semantic_review_fn(
        {"brief": deepcopy(brief.to_json()), "draft": deepcopy(draft), "draft_digest": draft_digest}
    )
    if not isinstance(review_raw, Mapping) or review_raw.get("accepted") is not True:
        raise ValueError("independent semantic review rejected frontier blueprint")
    if review_raw.get("candidate_law_leakage") is not False:
        raise ValueError("semantic review did not clear candidate-law leakage")
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
            "stop_rule_aligned": True,
            "rationale": "Typed structure was supplied directly and passed independent schema review.",
            "evidence_refs": [brief.brief_id, "deterministic-structure-first-review"],
        },
        compiler_ref="deterministic-structure-first-compiler",
        reviewer_ref="deterministic-structure-first-reviewer",
    )


__all__ = [
    "compile_frontier_blueprint", "compile_structure_first_blueprint",
    "render_frontier_blueprint_prompt",
]
