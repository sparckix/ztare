"""Typed solver task for substrates missing an executable theory adapter."""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import shutil
from typing import TYPE_CHECKING, Any, Callable, Mapping

from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill import prompts
from ztare.leanmill.common import read_json, write_json_atomic

if TYPE_CHECKING:
    from ztare.leanmill.exploration_budget import ExplorationBudgetLedger


@dataclass(frozen=True)
class AdapterGap:
    brief_digest: str
    proposed_adapter_id: str
    primitive_semantics_contract: Mapping[str, Any]
    raw_fixture_refs: tuple[str, ...]
    required_context_kind: str
    required_operations: tuple[str, ...]
    required_receipts: tuple[str, ...]
    forbidden_authorities: tuple[str, ...]
    acceptance_tests: tuple[str, ...]
    gap_kind: str = "adapter_missing"
    missing_capabilities: tuple[str, ...] = ()
    schema: str = "leanmill.adapter_gap.v1"

    def __post_init__(self) -> None:
        if self.required_context_kind not in {"exact", "sampled"}:
            raise ValueError("adapter gap context kind must be exact or sampled")
        if not self.brief_digest or not self.proposed_adapter_id:
            raise ValueError("adapter gap identity is required")
        if self.gap_kind not in {"adapter_missing", "capability_missing"}:
            raise ValueError("adapter gap kind is invalid")
        if self.gap_kind == "capability_missing" and not self.missing_capabilities:
            raise ValueError("capability gap must name the missing capability")

    @property
    def gap_id(self) -> str:
        return "adapter-gap:" + content_hash(self.to_json(include_id=False))

    def to_json(self, *, include_id: bool = True) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "brief_digest": self.brief_digest,
            "proposed_adapter_id": self.proposed_adapter_id,
            "primitive_semantics_contract": dict(self.primitive_semantics_contract),
            "raw_fixture_refs": list(self.raw_fixture_refs),
            "required_context_kind": self.required_context_kind,
            "required_operations": list(self.required_operations),
            "required_receipts": list(self.required_receipts),
            "forbidden_authorities": list(self.forbidden_authorities),
            "acceptance_tests": list(self.acceptance_tests),
            "gap_kind": self.gap_kind,
            "missing_capabilities": list(self.missing_capabilities),
        }
        return {**core, "gap_id": self.gap_id} if include_id else core

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "AdapterGap":
        gap = cls(
            brief_digest=str(value["brief_digest"]),
            proposed_adapter_id=str(value["proposed_adapter_id"]),
            primitive_semantics_contract=dict(value["primitive_semantics_contract"]),
            raw_fixture_refs=tuple(str(row) for row in value["raw_fixture_refs"]),
            required_context_kind=str(value["required_context_kind"]),
            required_operations=tuple(str(row) for row in value["required_operations"]),
            required_receipts=tuple(str(row) for row in value["required_receipts"]),
            forbidden_authorities=tuple(str(row) for row in value["forbidden_authorities"]),
            acceptance_tests=tuple(str(row) for row in value["acceptance_tests"]),
            gap_kind=str(value.get("gap_kind") or "adapter_missing"),
            missing_capabilities=tuple(
                str(row) for row in value.get("missing_capabilities") or ()
            ),
            schema=str(value.get("schema") or "leanmill.adapter_gap.v1"),
        )
        supplied = value.get("gap_id")
        if supplied is not None and supplied != gap.gap_id:
            raise ValueError("adapter gap digest mismatch")
        return gap


class AdapterGapRequired(RuntimeError):
    def __init__(self, gap: AdapterGap) -> None:
        super().__init__(f"frontier campaign blocked on adapter {gap.proposed_adapter_id!r}")
        self.gap = gap


def render_adapter_forge_prompt(gap: AdapterGap) -> str:
    template = (
        prompts.ADAPTER_CAPABILITY_FORGE_PROMPT
        if gap.gap_kind == "capability_missing"
        else prompts.ADAPTER_FORGE_PROMPT
    )
    return template.format(
        gap_json=__import__("json").dumps(
            gap.to_json(), sort_keys=True, separators=(",", ":")
        )
    )


def adapter_forge_output_schema() -> dict[str, Any]:
    paths = {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "source_paths", "test_paths", "manifest", "self_test_receipts",
            "registry_mutation",
        ],
        "properties": {
            "source_paths": paths,
            "test_paths": paths,
            "manifest": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "capability_source", "interface", "request_id", "observable_paths"
                ],
                "properties": {
                    "capability_source": {"type": "string", "minLength": 1},
                    "interface": {
                        "type": "string",
                        "const": "leanmill.object_coordinates.v1",
                    },
                    "request_id": {"type": "string", "minLength": 1},
                    "observable_paths": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                        "minItems": 1,
                        "maxItems": 4,
                    },
                },
            },
            "self_test_receipts": paths,
            "registry_mutation": {"type": "boolean"},
        },
    }


def adapter_review_output_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["accepted", "reviewer_ref", "rationale", "evidence_refs"],
        "properties": {
            "accepted": {"type": "boolean"},
            "reviewer_ref": {"type": "string", "minLength": 1},
            "rationale": {"type": "string", "minLength": 1},
            "evidence_refs": {
                "type": "array", "items": {"type": "string", "minLength": 1},
            },
        },
    }


def stage_adapter_forge_workspace(
    attempt_dir: str | Path, gap: AdapterGap
) -> Path:
    directory = Path(attempt_dir)
    workspace = directory / "adapter_forge_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    write_json_atomic(workspace / "adapter_gap.json", gap.to_json())
    context_path = directory / "formal_context.json"
    if gap.gap_kind == "capability_missing" and not context_path.is_file():
        raise ValueError("capability forge requires a frozen formal context")
    if context_path.is_file():
        shutil.copy2(context_path, workspace / "formal_context.json")
        snapshot = json.loads(context_path.read_text(encoding="utf-8"))
        universe = dict(snapshot.get("model_universe") or {})
        models = list(universe.pop("models", ()) or ())
        write_json_atomic(
            workspace / "context_fixture.json",
            {
                "schema": "leanmill.adapter_forge_context_fixture.v1",
                "snapshot_keys": sorted(snapshot),
                "model_universe_without_models": universe,
                "model_count": len(models),
                "sample_models": models[:3],
            },
        )
    return workspace


def host_coordinate_conformance(
    proposal: Mapping[str, Any],
    gap: AdapterGap,
    *,
    workspace: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    """Execute a staged coordinate capability; the host measures its semantic delta."""

    root = Path(workspace).resolve()
    manifest = proposal.get("manifest")
    if not isinstance(manifest, Mapping):
        raise ValueError("capability proposal lacks a manifest")
    request = gap.primitive_semantics_contract.get("theory_language_request")
    if not isinstance(request, Mapping):
        raise ValueError("capability gap lacks its theory-language request")
    if (
        manifest.get("interface") != "leanmill.object_coordinates.v1"
        or manifest.get("request_id") != request.get("request_id")
    ):
        raise ValueError("capability manifest does not bind the frozen request")
    observable_paths = tuple(str(row) for row in manifest.get("observable_paths") or ())
    if not 1 <= len(observable_paths) <= 4 or len(set(observable_paths)) != len(observable_paths):
        raise ValueError("capability manifest requires one to four observable paths")

    def staged_path(value: Any) -> Path:
        path = (root / str(value)).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("capability proposal references a non-staged file")
        return path

    sources = [staged_path(row) for row in proposal.get("source_paths") or ()]
    tests = [staged_path(row) for row in proposal.get("test_paths") or ()]
    declared_source = str(manifest.get("capability_source") or "")
    candidate = (root / declared_source).resolve()
    source = candidate if candidate in sources else sources[0] if len(sources) == 1 else None
    if source is None or source not in sources or not tests:
        raise ValueError("capability source and checks must be staged and declared")
    spec = importlib.util.spec_from_file_location(
        "leanmill_quarantined_capability", source
    )
    if spec is None or spec.loader is None:
        raise ValueError("capability source cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    build = getattr(module, "build_coordinates", None)
    if not callable(build):
        raise ValueError("capability source lacks build_coordinates")
    snapshot = json.loads((root / "formal_context.json").read_text(encoding="utf-8"))
    first_raw = build(snapshot, dict(request))
    second_raw = build(snapshot, dict(request))
    if first_raw != second_raw:
        raise ValueError("capability coordinates are absent or nondeterministic")

    functor_image = None
    if isinstance(first_raw, Mapping) and set(first_raw) == {
        "coordinates", "functor_image"
    }:
        functor_image = first_raw["functor_image"]
        first_raw = first_raw["coordinates"]

    def coordinate_map(value: Any) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return {str(key): item for key, item in value.items()}
        if isinstance(value, list) and all(
            isinstance(row, Mapping) and row.get("object_id") for row in value
        ):
            rows = {str(row["object_id"]): dict(row) for row in value}
            if len(rows) == len(value):
                return rows
        raise ValueError("capability coordinates have an unsupported carrier")

    first = coordinate_map(first_raw)

    from ztare.leanmill.finite_theory_context import load_formal_theory_context

    context = load_formal_theory_context(root / "formal_context.json")
    if set(first) != set(context.object_ids):
        raise ValueError("capability coordinates do not cover the frozen objects exactly")
    image_receipt = None
    if functor_image is not None:
        if not isinstance(functor_image, Mapping) or set(functor_image) != {
            "functor_id", "signature", "models"
        }:
            raise ValueError("capability functor image has an unsupported envelope")
        from ztare.leanmill.finite_model import FiniteModel, validate_model
        from ztare.leanmill.theory_ir import TheorySignature

        signature = TheorySignature.from_json(functor_image["signature"])
        image_models = functor_image["models"]
        if (
            not isinstance(image_models, Mapping)
            or not image_models
            or not set(image_models) <= set(context.object_ids)
        ):
            raise ValueError("capability functor image has invalid source coverage")
        for row in image_models.values():
            validate_model(signature, FiniteModel.from_json(row))
        image_core = {
            "schema": "leanmill.finite_model_functor_application.v1",
            "gap_id": gap.gap_id,
            "context_hash": context.context_hash,
            "functor_id": str(functor_image["functor_id"]),
            "signature": signature.to_json(),
            "models": dict(image_models),
        }
        image_receipt = {**image_core, "receipt_sha256": content_hash(image_core)}
        write_json_atomic(
            Path(output_path).with_name("theory_language_functor_image.json"),
            image_receipt,
        )
    def observable(coordinate: Any) -> tuple[Any, ...]:
        if not isinstance(coordinate, Mapping):
            raise ValueError("capability coordinate must be an object")
        values = []
        for path in observable_paths:
            value: Any = coordinate
            for part in path.split("."):
                if not isinstance(value, Mapping) or part not in value:
                    raise ValueError("capability observable path is absent")
                value = value[part]
            if value is not None and not isinstance(value, (bool, int, float, str)):
                raise ValueError("capability observables must be scalar")
            values.append(value)
        return tuple(values)

    canonical = {
        object_id: json.dumps(observable(first[object_id]), separators=(",", ":"))
        for object_id in context.object_ids
    }
    classes: dict[tuple[bool, ...], list[str]] = {}
    for index, object_id in enumerate(context.object_ids):
        profile = tuple(bool(row.truth_bits & (1 << index)) for row in context.formula_profiles)
        classes.setdefault(profile, []).append(object_id)
    split_pairs = 0
    split_classes = 0
    for object_ids in classes.values():
        counts: dict[str, int] = {}
        for object_id in object_ids:
            counts[canonical[object_id]] = counts.get(canonical[object_id], 0) + 1
        separated = len(object_ids) * (len(object_ids) - 1) // 2 - sum(
            count * (count - 1) // 2 for count in counts.values()
        )
        split_pairs += separated
        split_classes += separated > 0
    if split_pairs == 0:
        raise ValueError("capability adds no coordinate to the frozen semantic geometry")
    payload_core = {
        "schema": "leanmill.object_coordinates.v1",
        "gap_id": gap.gap_id,
        "request_id": request["request_id"],
        "context_hash": context.context_hash,
        "coordinates": dict(first),
    }
    payload = {**payload_core, "receipt_sha256": content_hash(payload_core)}
    write_json_atomic(output_path, payload)
    coordinate_kinds: dict[str, int] = {}
    quotient_sizes: dict[str, int] = {}
    descent_values: dict[str, int] = {}
    for coordinate in first.values():
        if not isinstance(coordinate, Mapping):
            continue
        kind = str(coordinate.get("coordinate_kind") or "unspecified")
        coordinate_kinds[kind] = coordinate_kinds.get(kind, 0) + 1
        quotient = coordinate.get("quotient")
        if isinstance(quotient, Mapping):
            size = str(quotient.get("class_count"))
            quotient_sizes[size] = quotient_sizes.get(size, 0) + 1
        descent = coordinate.get("descent")
        if isinstance(descent, Mapping):
            value = str(descent.get("descends"))
            descent_values[value] = descent_values.get(value, 0) + 1

    def artifact(path: Path) -> dict[str, Any]:
        content = path.read_text(encoding="utf-8")
        return {
            "path": str(path.relative_to(root)),
            "content_sha256": content_hash({"bytes": content}),
            "content": content,
        }

    core = {
        "ok": True,
        "interface": "leanmill.object_coordinates.v1",
        "context_hash": context.context_hash,
        "object_count": len(context.object_ids),
        "split_indistinguishability_class_count": split_classes,
        "separated_indistinguishable_pair_count": split_pairs,
        "coordinate_receipt_sha256": payload["receipt_sha256"],
        "observable_paths": list(observable_paths),
        "functor_image_receipt_sha256": (
            image_receipt["receipt_sha256"] if image_receipt is not None else ""
        ),
        "functor_image_model_count": (
            len(image_receipt["models"]) if image_receipt is not None else 0
        ),
        "coordinate_kind_counts": coordinate_kinds,
        "quotient_class_count_distribution": quotient_sizes,
        "descent_distribution": descent_values,
        "source_artifacts": [artifact(path) for path in sources],
        "test_artifacts": [artifact(path) for path in tests],
        "manifest_capability_source": declared_source,
        "resolved_capability_source": str(source.relative_to(root)),
        "claim_boundary": "semantic delta measured only on the frozen finite context",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def run_adapter_forge(
    gap: AdapterGap,
    *,
    coding_agent_fn: Callable[[str], Mapping[str, Any]],
    host_conformance_fn: Callable[[Mapping[str, Any], AdapterGap], Mapping[str, Any]],
    independent_review_fn: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    budget_ledger: "ExplorationBudgetLedger | None" = None,
) -> dict[str, Any]:
    def provider_calls(fn: Any) -> int | None:
        role = getattr(fn, "call_role", fn)
        value = getattr(role, "provider_call_count", None)
        return int(value) if value is not None else None

    coding_reservation = None
    if budget_ledger is not None and not getattr(
        coding_agent_fn, "recovered_proposal", False
    ):
        coding_reservation = budget_ledger.reserve(
            f"adapter_forge:{gap.gap_id}:coding",
            "expansion",
            {"adapter_forge_attempts": 1, "provider_calls": 1, "agent_turns": 1},
        )
    coding_before = provider_calls(coding_agent_fn)
    try:
        proposal = coding_agent_fn(render_adapter_forge_prompt(gap))
    finally:
        if coding_reservation is not None:
            coding_after = provider_calls(coding_agent_fn)
            used = (
                max(0, min(1, coding_after - coding_before))
                if coding_before is not None and coding_after is not None
                else 1
            )
            budget_ledger.commit(
                coding_reservation,
                {
                    "adapter_forge_attempts": used,
                    "provider_calls": used,
                    "agent_turns": used,
                },
            )
    if not isinstance(proposal, Mapping):
        raise ValueError("AdapterForge returned no structured proposal")
    required = {"source_paths", "test_paths", "manifest", "self_test_receipts"}
    if not required <= set(proposal):
        raise ValueError("AdapterForge proposal lacks code/test/manifest receipts")
    if proposal.get("registry_mutation"):
        raise ValueError("AdapterForge may not mutate the live registry")
    conformance = host_conformance_fn(proposal, gap)
    if not isinstance(conformance, Mapping) or conformance.get("ok") is not True:
        raise ValueError("AdapterForge host conformance failed")
    review_reservation = None
    if budget_ledger is not None:
        review_reservation = budget_ledger.reserve(
            f"adapter_forge:{gap.gap_id}:review",
            "expansion",
            {"provider_calls": 1, "agent_turns": 1},
        )
    review_before = provider_calls(independent_review_fn)
    try:
        review = independent_review_fn(
            {"gap": gap.to_json(), "proposal": dict(proposal), "host_conformance": dict(conformance)}
        )
    finally:
        if review_reservation is not None:
            review_after = provider_calls(independent_review_fn)
            used = (
                max(0, min(1, review_after - review_before))
                if review_before is not None and review_after is not None
                else 1
            )
            budget_ledger.commit(
                review_reservation,
                {"provider_calls": used, "agent_turns": used},
            )
    if not isinstance(review, Mapping) or review.get("accepted") is not True:
        raise ValueError("AdapterForge independent semantic review failed")
    core = {
        "schema": "leanmill.adapter_forge_quarantine_receipt.v1",
        "gap_id": gap.gap_id,
        "proposed_adapter_id": gap.proposed_adapter_id,
        "proposal_digest": content_hash(dict(proposal)),
        "host_conformance": dict(conformance),
        "independent_review": dict(review),
        "status": "quarantined_registry_proposal",
        "live_registry_mutated": False,
        "exactness_authority_granted": False,
        "next_step": "code_review_and_registry_authority_then_new_blueprint_attempt",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def execute_adapter_forge_attempt(
    attempt_dir: str | Path,
    *,
    coding_agent_fn: Callable[[str], Mapping[str, Any]],
    host_conformance_fn: Callable[[Mapping[str, Any], AdapterGap], Mapping[str, Any]],
    independent_review_fn: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> dict[str, Any]:
    """Resume a typed adapter gap through quarantine without touching the registry."""
    directory = Path(attempt_dir)
    existing = read_json(directory / "adapter_forge_completion.json", None)
    if isinstance(existing, dict) and existing:
        return existing
    run_row = read_json(directory / "run.json", None)
    gap_row = read_json(directory / "adapter_gap.json", None)
    budget_row = read_json(directory / "budget.json", None)
    if not all(isinstance(row, dict) and row for row in (run_row, gap_row, budget_row)):
        raise ValueError("AdapterForge requires a blocked campaign with a typed gap")
    if run_row.get("status") != "blocked_adapter_gap":
        raise ValueError("campaign is not blocked on an adapter gap")
    from ztare.leanmill.exploration_budget import ExplorationBudget, ExplorationBudgetLedger

    budget = ExplorationBudget.from_json(budget_row)
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        budget,
        attempt_id=directory.name,
    )
    gap = AdapterGap.from_json(gap_row)
    ledger.recover_interrupted_wall_clock()
    ledger.resume_wall_clock()
    try:
        receipt = run_adapter_forge(
            gap,
            coding_agent_fn=coding_agent_fn,
            host_conformance_fn=host_conformance_fn,
            independent_review_fn=independent_review_fn,
            budget_ledger=ledger,
        )
    finally:
        ledger.freeze_wall_clock(reason="adapter_forge_exit")
    write_json_atomic(directory / "adapter_forge_receipt.json", receipt)
    core = {
        "schema": "leanmill.adapter_forge_completion.v1",
        "status": "quarantined_adapter_proposal_requires_authority_and_new_attempt",
        "attempt_dir": str(directory),
        "gap_id": gap.gap_id,
        "quarantine_receipt": receipt,
        "provider_calls": int(ledger.state()["usage"]["provider_calls"])
        + int(run_row.get("preparation_provider_calls", 0)),
    }
    completion = {**core, "completion_sha256": content_hash(core)}
    write_json_atomic(directory / "adapter_forge_completion.json", completion)
    return completion


__all__ = [
    "AdapterGap", "AdapterGapRequired", "adapter_forge_output_schema",
    "adapter_review_output_schema", "execute_adapter_forge_attempt",
    "host_coordinate_conformance", "render_adapter_forge_prompt",
    "run_adapter_forge", "stage_adapter_forge_workspace",
]
