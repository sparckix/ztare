"""Human-facing briefs and strict executable blueprints for AxiomPack."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ztare.leanmill.theory_ir import (
    AxiomFormula,
    TheorySignature,
    anonymous_formula_ir,
    content_hash,
    validate_axioms,
)


BRIEF_SCHEMA = "leanmill.frontier_exploration_brief.v1"
BLUEPRINT_SCHEMA = "leanmill.frontier_theory_blueprint.v1"
SOURCE_MODES = frozenset(
    {"human_directed", "residual_directed", "scout_directed", "structure_first"}
)
CAMPAIGN_MODES = frozenset(
    {"anonymous_signature_census", "evidence_induced", "domain_conditioned", "proof_gap_conditioned"}
)
NAVIGATOR_SELECTION_MODES = frozenset({"compact_axiom_pack", "theory_program"})
THEORY_TASK_CAPABILITY_SCOPE_SCHEMA = (
    "leanmill.theory_task_capability_scope.v1"
)
_CANDIDATE_FIELDS = frozenset(
    {
        "candidate_axioms", "candidate_axiom_templates", "axiom_templates",
        "named_axiom_list", "formula_universe",
    }
)

_BLUEPRINT_DRAFT_FIELDS = (
    "mode", "eigenquestion", "signature", "primitive_semantics", "base_axioms",
    "base_theory_status", "adapter_id", "adapter_config", "formula_grammar",
    "model_or_observation_strata", "pack_arity", "collapse_controls",
    "visible_evidence_manifest", "sealed_evidence_manifest_digest",
    "deanchoring_policy", "navigator_contract", "query_budget", "stop_rule",
    "verification_plan", "codec_versions", "authority_refs",
)


@dataclass(frozen=True)
class FrontierExplorationBrief:
    direction: str
    source_mode: str
    evidence_refs: tuple[str, ...] = ()
    requested_mode: str = ""
    deanchoring_intent: str = "cold_after_signature_compilation"
    resource_envelope: Mapping[str, Any] = field(default_factory=dict)
    forbidden_shortcuts: tuple[str, ...] = ()
    created_by: str = "user"
    schema: str = BRIEF_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != BRIEF_SCHEMA or self.source_mode not in SOURCE_MODES:
            raise ValueError("unsupported exploration brief schema or source mode")
        if not self.direction.strip() or not self.created_by.strip():
            raise ValueError("brief direction and creator must be non-empty")
        if self.requested_mode and self.requested_mode not in CAMPAIGN_MODES:
            raise ValueError("unsupported requested campaign mode")

    @property
    def brief_id(self) -> str:
        return "brief:" + content_hash(self.to_json(include_id=False))

    def to_json(self, *, include_id: bool = True) -> dict[str, Any]:
        value = {
            "schema": self.schema,
            "direction": self.direction,
            "source_mode": self.source_mode,
            "evidence_refs": list(self.evidence_refs),
            "requested_mode": self.requested_mode,
            "deanchoring_intent": self.deanchoring_intent,
            "resource_envelope": dict(self.resource_envelope),
            "forbidden_shortcuts": list(self.forbidden_shortcuts),
            "created_by": self.created_by,
        }
        return {**value, "brief_id": self.brief_id} if include_id else value

    @classmethod
    def from_direction(
        cls,
        direction: str,
        *,
        source_mode: str = "human_directed",
        evidence_refs: Sequence[str] = (),
    ) -> "FrontierExplorationBrief":
        return cls(
            direction=direction,
            source_mode=source_mode,
            evidence_refs=tuple(map(str, evidence_refs)),
        )


@dataclass(frozen=True)
class FrontierTheoryBlueprint:
    brief_digest: str
    mode: str
    eigenquestion: str
    signature: Mapping[str, Any]
    primitive_semantics: Mapping[str, Any]
    base_axioms: tuple[Mapping[str, Any], ...]
    base_theory_status: str
    adapter_id: str
    adapter_config: Mapping[str, Any]
    formula_grammar: Mapping[str, Any]
    model_or_observation_strata: tuple[Mapping[str, Any], ...]
    pack_arity: int
    collapse_controls: tuple[Mapping[str, Any], ...]
    visible_evidence_manifest: Mapping[str, Any]
    sealed_evidence_manifest_digest: str
    deanchoring_policy: Mapping[str, Any]
    navigator_contract: Mapping[str, Any]
    query_budget: Mapping[str, Any]
    stop_rule: Mapping[str, Any]
    verification_plan: Mapping[str, Any]
    codec_versions: Mapping[str, str]
    authority_refs: tuple[str, ...]
    compiler_receipt: Mapping[str, Any]
    semantic_review_receipt: Mapping[str, Any]
    executable_preflight_receipt: Mapping[str, Any]
    frozen: bool = True
    schema: str = BLUEPRINT_SCHEMA

    def __post_init__(self) -> None:
        mapping_fields = (
            "signature", "primitive_semantics", "adapter_config", "formula_grammar",
            "visible_evidence_manifest", "deanchoring_policy", "navigator_contract",
            "query_budget", "stop_rule", "verification_plan", "codec_versions",
            "compiler_receipt", "semantic_review_receipt", "executable_preflight_receipt",
        )
        for field in mapping_fields:
            if not isinstance(getattr(self, field), Mapping):
                raise ValueError(f"frontier blueprint field {field} must be an object")
        for field in ("base_axioms", "model_or_observation_strata", "collapse_controls"):
            if any(not isinstance(row, Mapping) for row in getattr(self, field)):
                raise ValueError(
                    f"frontier blueprint field {field} must contain objects"
                )
        if self.schema != BLUEPRINT_SCHEMA or self.mode not in CAMPAIGN_MODES:
            raise ValueError("unsupported frontier blueprint schema or mode")
        if not self.frozen:
            raise ValueError("frontier blueprint must be frozen")
        if not self.brief_digest.startswith("brief:") or not self.eigenquestion.strip():
            raise ValueError("blueprint must bind a brief and eigenquestion")
        if not self.adapter_id or type(self.pack_arity) is not int or self.pack_arity < 1:
            raise ValueError("blueprint adapter and pack arity are required")
        validate_navigator_contract(self.pack_arity, self.navigator_contract)
        task_scope = theory_task_capability_scope(self.navigator_contract)
        if (
            task_scope is not None
            and task_scope["adapter_id"] != self.adapter_id
        ):
            raise ValueError(
                "theory-task capability scope belongs to another adapter"
            )
        frontier_objective_contract(self)
        if not self.sealed_evidence_manifest_digest.startswith("sha256:"):
            raise ValueError("sealed evidence must be represented by a digest")
        if not self.authority_refs:
            raise ValueError("blueprint requires authority refs")
        if self.mode == "anonymous_signature_census":
            leaked = _candidate_field_paths(self.to_json(include_id=False))
            if leaked:
                raise ValueError(f"cold frontier blueprint contains candidate-law fields: {leaked}")
        signature = TheorySignature.from_json(self.signature)
        base = tuple(AxiomFormula.from_json(row) for row in self.base_axioms)
        validate_axioms(signature, base)
        if self.base_theory_status not in {"explicit_empty", "typed_resolved"}:
            raise ValueError("base theory must be explicit empty or typed resolved")
        if self.base_theory_status == "explicit_empty" and base:
            raise ValueError("explicit-empty base theory cannot contain axioms")
        if self.semantic_review_receipt.get("accepted") is not True:
            raise ValueError("frontier blueprint requires accepted semantic review")
        if self.executable_preflight_receipt.get("ok") is not True:
            raise ValueError("frontier blueprint requires executable preflight")
        compiler_role = str(self.compiler_receipt.get("authority_role") or "")
        reviewer_role = str(self.semantic_review_receipt.get("authority_role") or "")
        if not compiler_role or not reviewer_role or compiler_role == reviewer_role:
            raise ValueError("compiler and semantic reviewer roles must be separated")

    @property
    def blueprint_id(self) -> str:
        return "blueprint:" + content_hash(self.to_json(include_id=False))

    def to_json(self, *, include_id: bool = True) -> dict[str, Any]:
        value = {
            "schema": self.schema,
            "brief_digest": self.brief_digest,
            "mode": self.mode,
            "eigenquestion": self.eigenquestion,
            "signature": dict(self.signature),
            "primitive_semantics": dict(self.primitive_semantics),
            "base_axioms": [dict(row) for row in self.base_axioms],
            "base_theory_status": self.base_theory_status,
            "adapter_id": self.adapter_id,
            "adapter_config": dict(self.adapter_config),
            "formula_grammar": dict(self.formula_grammar),
            "model_or_observation_strata": [dict(row) for row in self.model_or_observation_strata],
            "pack_arity": self.pack_arity,
            "collapse_controls": [dict(row) for row in self.collapse_controls],
            "visible_evidence_manifest": dict(self.visible_evidence_manifest),
            "sealed_evidence_manifest_digest": self.sealed_evidence_manifest_digest,
            "deanchoring_policy": dict(self.deanchoring_policy),
            "navigator_contract": dict(self.navigator_contract),
            "query_budget": dict(self.query_budget),
            "stop_rule": dict(self.stop_rule),
            "verification_plan": dict(self.verification_plan),
            "codec_versions": dict(self.codec_versions),
            "authority_refs": list(self.authority_refs),
            "compiler_receipt": dict(self.compiler_receipt),
            "semantic_review_receipt": dict(self.semantic_review_receipt),
            "executable_preflight_receipt": dict(self.executable_preflight_receipt),
            "frozen": self.frozen,
        }
        return {**value, "blueprint_id": self.blueprint_id} if include_id else value

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "FrontierTheoryBlueprint":
        fields = set(cls.__dataclass_fields__)
        payload = {key: value[key] for key in fields if key in value}
        for key in (
            "base_axioms", "model_or_observation_strata", "collapse_controls",
            "authority_refs",
        ):
            if key in payload:
                payload[key] = tuple(payload[key])
        blueprint = cls(**payload)
        supplied = value.get("blueprint_id")
        if supplied is not None and supplied != blueprint.blueprint_id:
            raise ValueError("frontier blueprint digest mismatch")
        return blueprint


def _candidate_field_paths(value: Any, path: str = "") -> tuple[str, ...]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if str(key).lower() in _CANDIDATE_FIELDS:
                found.append(child_path)
            found.extend(_candidate_field_paths(child, child_path))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            found.extend(_candidate_field_paths(child, f"{path}[{index}]"))
    return tuple(found)


def _presentation_size_bounds(
    pack_arity: int,
    navigator_contract: Mapping[str, Any],
) -> tuple[int, int]:
    raw = navigator_contract.get("presentation_size")
    if raw is None:
        return 1, pack_arity
    if not isinstance(raw, Mapping):
        raise ValueError("navigator presentation_size must be an object")
    if set(raw) - {"minimum", "maximum"}:
        raise ValueError("navigator presentation_size has unknown fields")
    minimum = raw.get("minimum", 1)
    maximum = raw.get("maximum", pack_arity)
    if type(minimum) is not int or type(maximum) is not int:
        raise ValueError("navigator presentation_size bounds must be integers")
    if not 1 <= minimum <= maximum <= pack_arity:
        raise ValueError("navigator presentation_size must lie within pack_arity")
    return minimum, maximum


def validate_navigator_contract(
    pack_arity: int,
    navigator_contract: Mapping[str, Any],
) -> None:
    """Validate the candidate-search contract at its invariant-owning layer."""

    if type(pack_arity) is not int or pack_arity < 1:
        raise ValueError("blueprint pack arity must be positive")
    if not isinstance(navigator_contract, Mapping):
        raise ValueError("frontier blueprint navigator_contract must be an object")
    _presentation_size_bounds(pack_arity, navigator_contract)
    _topology_presentation_size(pack_arity, navigator_contract)
    selection_mode = navigator_contract.get(
        "selection_mode", "compact_axiom_pack"
    )
    if selection_mode not in NAVIGATOR_SELECTION_MODES:
        raise ValueError("unsupported navigator selection mode")
    _host_isolated_lineage_count(navigator_contract)
    theory_task_capability_scope(navigator_contract)


def theory_task_capability_scope(
    navigator_contract: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Return the optional adapter-scoped task envelope."""

    raw = navigator_contract.get("theory_task_capability_scope")
    if raw is None:
        return None
    required = {"schema", "adapter_id", "allowed_capability_ids"}
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise ValueError(
            "theory-task capability scope fields differ from its contract"
        )
    if raw.get("schema") != THEORY_TASK_CAPABILITY_SCOPE_SCHEMA:
        raise ValueError("unsupported theory-task capability scope schema")
    adapter_id = raw.get("adapter_id")
    allowed = raw.get("allowed_capability_ids")
    if not isinstance(adapter_id, str) or not adapter_id.strip():
        raise ValueError("theory-task capability scope requires an adapter")
    if (
        not isinstance(allowed, (list, tuple))
        or any(not isinstance(row, str) or not row.strip() for row in allowed)
        or len(set(allowed)) != len(allowed)
    ):
        raise ValueError(
            "theory-task capability scope requires unique string IDs"
        )
    return {
        "schema": THEORY_TASK_CAPABILITY_SCOPE_SCHEMA,
        "adapter_id": adapter_id,
        "allowed_capability_ids": tuple(allowed),
    }


def presentation_size_bounds(blueprint: FrontierTheoryBlueprint) -> tuple[int, int]:
    """Return the frozen candidate-presentation bounds for this campaign."""

    return _presentation_size_bounds(blueprint.pack_arity, blueprint.navigator_contract)


def _topology_presentation_size(
    pack_arity: int,
    navigator_contract: Mapping[str, Any],
) -> int:
    """Return the bounded orientation-map width, separate from candidate width."""

    value = navigator_contract.get("topology_presentation_size", min(2, pack_arity))
    if type(value) is not int or not 1 <= value <= pack_arity:
        raise ValueError("topology_presentation_size must lie within pack_arity")
    return value


def topology_presentation_size(blueprint: FrontierTheoryBlueprint) -> int:
    """Return how far the host materializes the anonymous topology overview."""

    return _topology_presentation_size(
        blueprint.pack_arity, blueprint.navigator_contract
    )


def navigator_selection_mode(blueprint: FrontierTheoryBlueprint) -> str:
    """Return the frozen research objective, preserving historical pack runs."""

    return str(
        blueprint.navigator_contract.get("selection_mode", "compact_axiom_pack")
    )


def _host_isolated_lineage_count(navigator_contract: Mapping[str, Any]) -> int:
    value = navigator_contract.get("host_isolated_lineages", 1)
    if type(value) is not int or not 1 <= value <= 8:
        raise ValueError("host_isolated_lineages must be an integer from 1 to 8")
    return value


def host_isolated_lineage_count(blueprint: FrontierTheoryBlueprint) -> int:
    """Return the frozen count of traces whose sibling outputs stay withheld."""

    return _host_isolated_lineage_count(blueprint.navigator_contract)


def frontier_objective_contract(
    blueprint: FrontierTheoryBlueprint,
) -> dict[str, Any] | None:
    """Return the optional leaf-judged outer objective.

    Local formula validity is the inner search predicate.  A delegated stop
    instruction may additionally require a late, independent review over
    frozen lineage receipts before boundary spend becomes admissible.
    """

    instruction = str(blueprint.stop_rule.get("user_instruction") or "").strip()
    condition = blueprint.stop_rule.get("executable_condition")
    if not instruction and condition is None:
        return None
    if not instruction or not isinstance(condition, Mapping):
        raise ValueError("frontier objective requires instruction and executable condition")
    if condition.get("kind") != "late_lineage_objective_review":
        raise ValueError("unsupported frontier objective condition kind")
    if set(condition) != {"kind"}:
        raise ValueError("late lineage objective condition has unknown fields")
    return {
        "schema": "leanmill.frontier_objective_contract.v1",
        "instruction": instruction,
        "review_stage": "post_lineage_freeze_pre_boundary",
        "authority": "independent_leaf_choice_host_receipt_validation",
    }


def frontier_blueprint_draft_payload(
    blueprint: FrontierTheoryBlueprint,
) -> dict[str, Any]:
    """Reconstruct the exact compiler draft governed by the review receipts."""

    payload: dict[str, Any] = {}
    for field_name in _BLUEPRINT_DRAFT_FIELDS:
        value = getattr(blueprint, field_name)
        if isinstance(value, Mapping):
            payload[field_name] = dict(value)
        elif isinstance(value, tuple):
            payload[field_name] = [
                dict(item) if isinstance(item, Mapping) else item for item in value
            ]
        else:
            payload[field_name] = value
    return payload


def validate_frontier_blueprint_authority_receipts(
    blueprint: FrontierTheoryBlueprint,
) -> dict[str, Any]:
    """Replay compiler, semantic-review, and executable-preflight identity.

    Historical blueprint loading remains schema-compatible, while transitions
    that grant terminal scientific credit can require this stronger replay.
    """

    draft_digest = content_hash(frontier_blueprint_draft_payload(blueprint))
    compiler = dict(blueprint.compiler_receipt)
    review = dict(blueprint.semantic_review_receipt)
    preflight = dict(blueprint.executable_preflight_receipt)
    compiler_core = {
        key: value for key, value in compiler.items() if key != "receipt_sha256"
    }
    review_core = {
        key: value for key, value in review.items() if key != "receipt_sha256"
    }
    preflight_core = {
        key: value for key, value in preflight.items() if key != "receipt_sha256"
    }
    if (
        compiler.get("schema")
        != "leanmill.frontier_blueprint_compiler_receipt.v1"
        or compiler.get("authority_role") != "frontier_blueprint_compiler"
        or compiler.get("brief_id") != blueprint.brief_digest
        or compiler.get("draft_digest") != draft_digest
        or compiler.get("receipt_sha256") != content_hash(compiler_core)
        or review.get("schema")
        != "leanmill.frontier_blueprint_semantic_review.v1"
        or review.get("authority_role")
        != "frontier_blueprint_semantic_reviewer"
        or review.get("accepted") is not True
        or review.get("substrate_constraints_executable") is not True
        or review.get("draft_digest") != draft_digest
        or review.get("receipt_sha256") != content_hash(review_core)
        or preflight.get("schema")
        != "leanmill.frontier_blueprint_executable_preflight.v1"
        or preflight.get("authority_role") != "deterministic_executable_preflight"
        or preflight.get("ok") is not True
        or preflight.get("adapter_id") != blueprint.adapter_id
        or preflight.get("receipt_sha256") != content_hash(preflight_core)
        or (
            frontier_objective_contract(blueprint) is not None
            and review.get("stop_rule_aligned") is not True
        )
    ):
        raise ValueError("frontier blueprint authority receipts do not replay")
    core = {
        "schema": "leanmill.frontier_blueprint_authority_replay.v1",
        "blueprint_id": blueprint.blueprint_id,
        "brief_digest": blueprint.brief_digest,
        "draft_digest": draft_digest,
        "compiler_receipt_sha256": str(compiler["receipt_sha256"]),
        "semantic_review_receipt_sha256": str(review["receipt_sha256"]),
        "executable_preflight_receipt_sha256": str(preflight["receipt_sha256"]),
        "authority": "deterministic_blueprint_receipt_replay",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def cold_navigator_manifest(blueprint: FrontierTheoryBlueprint) -> dict[str, Any]:
    signature = TheorySignature.from_json(blueprint.signature)
    minimum, maximum = presentation_size_bounds(blueprint)

    anonymous_base_theory = [
        {
            "base_formula_id": "base_formula:" + axiom.semantic_hash,
            "formula": anonymous_formula_ir(signature, axiom.formula),
        }
        for axiom in (
            AxiomFormula.from_json(dict(row)) for row in blueprint.base_axioms
        )
    ]
    objective = frontier_objective_contract(blueprint)
    return {
        "schema": "leanmill.frontier_cold_navigator_manifest.v2",
        "blueprint_id": blueprint.blueprint_id,
        "mode": blueprint.mode,
        "signature_shape": {
            "sorts": [f"sort_{index}" for index, _row in enumerate(signature.sorts)],
            "operations": [
                {
                    "id": f"op_{index}",
                    "arity": len(operation.arg_sorts),
                    "input_sort_indices": [
                        next(i for i, sort in enumerate(signature.sorts) if sort.name == name)
                        for name in operation.arg_sorts
                    ],
                    "output_sort_index": next(
                        i for i, sort in enumerate(signature.sorts)
                        if sort.name == operation.result_sort
                    ),
                }
                for index, operation in enumerate(signature.operations)
            ],
            "relations": [
                {
                    "id": f"rel_{index}",
                    "arity": len(relation.arg_sorts),
                    "input_sort_indices": [
                        next(i for i, sort in enumerate(signature.sorts) if sort.name == name)
                        for name in relation.arg_sorts
                    ],
                }
                for index, relation in enumerate(signature.relations)
            ],
        },
        "formula_grammar_digest": content_hash(dict(blueprint.formula_grammar)),
        "strata_digest": content_hash([dict(row) for row in blueprint.model_or_observation_strata]),
        "pack_arity": blueprint.pack_arity,
        "presentation_size": {"minimum": minimum, "maximum": maximum},
        "selection_mode": navigator_selection_mode(blueprint),
        "host_isolated_lineages": host_isolated_lineage_count(blueprint),
        "topology_presentation_size": topology_presentation_size(blueprint),
        "anonymous_base_theory": anonymous_base_theory,
        "navigator_contract": dict(blueprint.navigator_contract),
        "research_objective": objective,
        "query_budget": dict(blueprint.query_budget),
        "interpretation_labels_visible": False,
        "sealed_evidence_visible": False,
    }


__all__ = [
    "BLUEPRINT_SCHEMA", "BRIEF_SCHEMA", "CAMPAIGN_MODES",
    "NAVIGATOR_SELECTION_MODES", "SOURCE_MODES",
    "THEORY_TASK_CAPABILITY_SCOPE_SCHEMA",
    "FrontierExplorationBrief", "FrontierTheoryBlueprint", "cold_navigator_manifest",
    "frontier_blueprint_draft_payload", "frontier_objective_contract",
    "host_isolated_lineage_count", "navigator_selection_mode",
    "presentation_size_bounds", "topology_presentation_size",
    "theory_task_capability_scope",
    "validate_frontier_blueprint_authority_receipts", "validate_navigator_contract",
]
