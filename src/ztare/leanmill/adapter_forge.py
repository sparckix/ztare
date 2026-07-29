"""Typed solver task for substrates missing an executable theory adapter."""
from __future__ import annotations

import ast
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
from typing import TYPE_CHECKING, Any, Callable, Mapping

from jsonschema import Draft202012Validator

from ztare.common.artifact_refs import canonical_sha256_ref, extract_sha256_refs
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.data_only_json import strict_json_data
from ztare.common.information_yield_pricing import (
    identification_bits,
    partition_by_prediction,
)
from ztare.leanmill import prompts
from ztare.leanmill.common import read_json, write_json_atomic
from ztare.leanmill.generative_representation import (
    CANDIDATE_SCHEMA as GENERATIVE_REPRESENTATION_INTERFACE,
    validate_materialized_generative_candidate,
)
from ztare.leanmill.finite_construction_family import (
    FINITE_CONSTRUCTION_FAMILY_SCHEMA,
    construction_witness_interface,
    finite_construction_family_authoring_contract,
    validate_finite_construction_family,
)
from ztare.leanmill.construction_parameterization import (
    CONSTRUCTION_PARAMETERIZATION_SCHEMA,
    ConstructionBackendCapabilityUnavailable,
    ConstructionResourceCeilingExceeded,
    admit_construction_parameterization,
    construction_parameterization_authoring_contract,
    validate_construction_parameterization,
)
from ztare.leanmill.witness_construction_boundary import (
    validate_witness_construction_interface,
)

if TYPE_CHECKING:
    from ztare.leanmill.exploration_budget import ExplorationBudgetLedger


ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT = (
    "leanmill.adapter_forge_host_conformance.v2"
)
ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT = (
    "leanmill.adapter_forge_construction_static_conformance.v2"
)
ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT = (
    "repairable_structural_contract_error"
)
ADAPTER_FORGE_REJECTION_PRE_REVIEW_LEAKAGE = (
    "epistemic_pre_review_outcome_leakage"
)
ADAPTER_FORGE_REJECTION_UNCLASSIFIED = "unclassified_host_conformance_error"
ADAPTER_FORGE_STAGED_ARTIFACT_RESOURCE_CONTRACT = (
    "leanmill.adapter_forge_staged_artifact_resources.v1"
)
THEORY_LANGUAGE_REQUIRED_APPLICATION_SCHEMA = (
    "leanmill.theory_language_required_application.v1"
)
FINITE_MODEL_FUNCTOR_APPLICATION_SCHEMA = (
    "leanmill.finite_model_functor_application.v1"
)
GRAMMAR_OWNING_FUNCTOR_APPLICATION_SCHEMA = (
    "leanmill.finite_model_functor_application.v2"
)
_MAX_STAGED_ARTIFACTS_PER_ROLE = 32
_MAX_STAGED_ARTIFACT_BYTES = 8 * 1024 * 1024
_MAX_STAGED_ARTIFACT_AGGREGATE_BYTES = 32 * 1024 * 1024
_MAX_ADAPTER_FORGE_PROPOSAL_BYTES = 1_000_000
_MAX_ADAPTER_FORGE_REVIEW_BYTES = 65_536
_MAX_ADAPTER_FORGE_PROTOCOL_INTEGER_BITS = 4_096
_MAX_ADAPTER_FORGE_REVIEW_REFS = 64
_MAX_ADAPTER_FORGE_CAPABILITY_DATA_BYTES = _MAX_STAGED_ARTIFACT_BYTES
_MAX_ADAPTER_FORGE_CONFORMANCE_BYTES = _MAX_STAGED_ARTIFACT_AGGREGATE_BYTES


class AdapterForgeHostConformanceRejected(ValueError):
    """Host rejection carrying a substrate-neutral recovery classification."""

    def __init__(
        self,
        reason: str,
        *,
        rejection_class: str,
        violations: tuple[Mapping[str, Any], ...],
    ) -> None:
        super().__init__(reason)
        self.rejection_class = str(rejection_class)
        self.violations = tuple(dict(row) for row in violations)


class AdapterForgeHostCapabilityUnavailable(RuntimeError):
    """A deterministic host resource ceiling prevented conformance replay."""

    def __init__(
        self,
        reason_code: str,
        *,
        interface: str,
        artifact_path: str = "",
        observed: int = 0,
        ceiling: int = 0,
        resource_contract: str = ADAPTER_FORGE_STAGED_ARTIFACT_RESOURCE_CONTRACT,
    ) -> None:
        self.reason_code = str(reason_code)
        self.interface = str(interface)
        self.artifact_path = str(artifact_path)
        self.observed = int(observed)
        self.ceiling = int(ceiling)
        self.resource_contract = str(resource_contract)
        super().__init__(self.reason_code)


def _forge_data_ingress(
    role: str,
    value: Any,
    *,
    interface: str = "",
    source_ref: str = "",
    malformed_is_unavailable: bool = False,
) -> Any:
    """Bound every campaign-controlled JSON value before equality or hashing."""

    ceilings = {
        "proposal": _MAX_ADAPTER_FORGE_PROPOSAL_BYTES,
        "review": _MAX_ADAPTER_FORGE_REVIEW_BYTES,
        "capability_source": _MAX_ADAPTER_FORGE_CAPABILITY_DATA_BYTES,
        "generated_capability_return": _MAX_ADAPTER_FORGE_CAPABILITY_DATA_BYTES,
        "host_conformance": _MAX_ADAPTER_FORGE_CONFORMANCE_BYTES,
    }
    maximum = ceilings.get(str(role))
    if maximum is None:
        raise ValueError("unknown AdapterForge data ingress role")
    try:
        return strict_json_data(
            value,
            context="AdapterForge " + str(role),
            max_wire_bytes=maximum,
            max_integer_bits=_MAX_ADAPTER_FORGE_PROTOCOL_INTEGER_BITS,
            allow_finite_floats=(role == "host_conformance"),
        )
    except (TypeError, ValueError, RecursionError) as exc:
        message = str(exc)
        resource_failure = any(
            token in message
            for token in (
                "maximum JSON wire size",
                "integer bit ceiling",
                "maximum nesting depth",
            )
        )
        if resource_failure or malformed_is_unavailable or role in {
            "generated_capability_return", "host_conformance",
        }:
            raise AdapterForgeHostCapabilityUnavailable(
                str(role) + "_resource_unavailable",
                interface=interface or str(role),
                artifact_path=source_ref,
                observed=0,
                ceiling=maximum,
            ) from exc
        raise


def _forge_json_text_ingress(
    role: str,
    text: str,
    *,
    interface: str = "",
    source_ref: str = "",
) -> Any:
    """Parse bounded JSON text without leaking parser recursion failures."""

    if not isinstance(text, str):
        raise ValueError("AdapterForge JSON source is not text")
    maximum = {
        "proposal": _MAX_ADAPTER_FORGE_PROPOSAL_BYTES,
        "review": _MAX_ADAPTER_FORGE_REVIEW_BYTES,
        "capability_source": _MAX_ADAPTER_FORGE_CAPABILITY_DATA_BYTES,
    }.get(role, _MAX_ADAPTER_FORGE_CAPABILITY_DATA_BYTES)
    observed = len(text.encode("utf-8"))
    if observed > maximum:
        raise AdapterForgeHostCapabilityUnavailable(
            str(role) + "_resource_unavailable",
            interface=interface or str(role),
            artifact_path=source_ref,
            observed=observed,
            ceiling=maximum,
        )
    try:
        value = json.loads(text)
    except RecursionError as exc:
        raise AdapterForgeHostCapabilityUnavailable(
            str(role) + "_resource_unavailable",
            interface=interface or str(role),
            artifact_path=source_ref,
            observed=observed,
            ceiling=maximum,
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValueError("AdapterForge capability source is not bounded JSON") from exc
    return _forge_data_ingress(
        role,
        value,
        interface=interface,
        source_ref=source_ref,
        malformed_is_unavailable=True,
    )


def _conformance_violation(
    *,
    code: str,
    category: str,
    artifact_role: str,
    artifact_path: str,
    json_path: str,
    summary: str,
    repair_scope: str,
) -> dict[str, str]:
    return {
        "code": str(code),
        "category": str(category),
        "artifact_role": str(artifact_role),
        "artifact_path": str(artifact_path),
        "json_path": str(json_path),
        "summary": str(summary),
        "repair_scope": str(repair_scope),
    }


_PRE_REVIEW_OUTCOME_WORDS = frozenset(
    {
        "accepted",
        "acceptance",
        "rejected",
        "rejection",
        "unavailable",
        "outcome",
        "outcomes",
        "observed",
        "observation",
        "predicate_satisfied",
        "verification_result",
        "verifier_result",
        "normalizer_result",
        "aggregate_outcome",
        "aggregate_outcomes",
        "outcome_count",
        "outcome_counts",
    }
)


def _normalized_identifier(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def _interface_outcome_words(interface: Mapping[str, Any]) -> frozenset[str]:
    """Derive observable names from the interface instead of substrate labels."""

    predicate = interface.get("predicate_ir")
    words = set(_PRE_REVIEW_OUTCOME_WORDS)
    if isinstance(predicate, Mapping):
        for key in predicate:
            normalized = _normalized_identifier(key)
            if normalized.startswith("required_") and len(normalized) > 9:
                words.add(normalized.removeprefix("required_"))
    for role in ("normalizer", "verifier"):
        descriptor = interface.get(role)
        if isinstance(descriptor, Mapping):
            capability_id = _normalized_identifier(
                descriptor.get("capability_id")
            )
            if capability_id:
                words.add(capability_id)
    return frozenset(words)


def _mapping_outcome_paths(
    value: Any,
    *,
    forbidden: frozenset[str],
    path: str,
) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = _normalized_identifier(key)
            child_path = f"{path}.{key}"
            if normalized in forbidden:
                found.append((child_path, normalized))
            found.extend(
                _mapping_outcome_paths(
                    child, forbidden=forbidden, path=child_path
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(
                _mapping_outcome_paths(
                    child, forbidden=forbidden, path=f"{path}[{index}]"
                )
            )
    return found


def _test_outcome_identifiers(
    content: str, *, forbidden: frozenset[str]
) -> tuple[tuple[int, str], ...]:
    """Return executable/check identifiers that expose target evaluation."""

    try:
        tree = ast.parse(content)
    except SyntaxError:
        # Non-Python checks remain inspectable through JSON keys.  Arbitrary
        # text is left to independent review rather than regex inference.
        try:
            value = _forge_json_text_ingress(
                "capability_source",
                content,
                interface="self_test",
                source_ref="self_test",
            )
        except (TypeError, ValueError):
            return ()
        return tuple(
            (0, name)
            for _path, name in _mapping_outcome_paths(
                value, forbidden=forbidden, path="$"
            )
        )
    found: set[tuple[int, str]] = set()
    for node in ast.walk(tree):
        identifier = ""
        if isinstance(node, ast.Name):
            identifier = node.id
        elif isinstance(node, ast.Attribute):
            identifier = node.attr
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            identifier = node.name
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            identifier = node.value
        normalized = _normalized_identifier(identifier)
        if normalized in forbidden:
            found.add((int(getattr(node, "lineno", 0)), normalized))
    return tuple(sorted(found))


def _finite_family_pre_review_violations(
    candidate: Any,
    *,
    source_artifact: _AdapterForgeStagedArtifact,
    tests: list[_AdapterForgeStagedArtifact],
    proposal: Mapping[str, Any],
    witness_interface: Mapping[str, Any],
) -> tuple[dict[str, str], ...]:
    """Inspect authorship/order boundaries before target execution or review."""

    structural: list[dict[str, str]] = []
    leakage: list[dict[str, str]] = []
    forbidden = _interface_outcome_words(witness_interface)
    if isinstance(candidate, Mapping):
        members = candidate.get("members")
        if isinstance(members, list):
            for index, member in enumerate(members):
                if not isinstance(member, Mapping):
                    continue
                refs = member.get("source_refs")
                if not isinstance(refs, list) or any(
                    not isinstance(ref, str) or not ref for ref in refs
                ):
                    structural.append(
                        _conformance_violation(
                            code="member_source_refs_not_string_identities",
                            category="structural_contract",
                            artifact_role="capability_source",
                            artifact_path=source_artifact.relative_path,
                            json_path=f"$.members[{index}].source_refs",
                            summary=(
                                "source_refs must contain nonempty identity strings; "
                                "embedded objects cross the family-reference contract"
                            ),
                            repair_scope="same_agent_new_bytes_permitted",
                        )
                    )
                for json_path, field in _mapping_outcome_paths(
                    member.get("derivation"),
                    forbidden=forbidden,
                    path=f"$.members[{index}].derivation",
                ):
                    leakage.append(
                        _conformance_violation(
                            code="pre_review_target_outcome_in_derivation",
                            category="epistemic_ordering",
                            artifact_role="capability_source",
                            artifact_path=source_artifact.relative_path,
                            json_path=json_path,
                            summary=(
                                "construction-only derivation carries target-evaluation "
                                f"field {field!r} before independent review"
                            ),
                            repair_scope="fresh_cold_reauthor_required",
                        )
                    )
        for json_path, field in _mapping_outcome_paths(
            {
                key: value
                for key, value in candidate.items()
                if key not in {"members", "family_spec", "symmetry_policy"}
            },
            forbidden=forbidden,
            path="$",
        ):
            leakage.append(
                _conformance_violation(
                    code="pre_review_target_outcome_in_family_envelope",
                    category="epistemic_ordering",
                    artifact_role="capability_source",
                    artifact_path=source_artifact.relative_path,
                    json_path=json_path,
                    summary=(
                        "family envelope carries target-evaluation field "
                        f"{field!r} before independent review"
                    ),
                    repair_scope="fresh_cold_reauthor_required",
                )
            )
    for artifact in tests:
        for line, identifier in _test_outcome_identifiers(
            artifact.text, forbidden=forbidden
        ):
            leakage.append(
                _conformance_violation(
                    code="pre_review_target_outcome_in_self_test",
                    category="epistemic_ordering",
                    artifact_role="self_test",
                    artifact_path=artifact.relative_path,
                    json_path=f"line:{line}" if line else "$",
                    summary=(
                        "pre-review self-test references target-evaluation "
                        f"identifier {identifier!r}"
                    ),
                    repair_scope="fresh_cold_reauthor_required",
                )
            )
    for index, receipt in enumerate(proposal.get("self_test_receipts") or ()):
        normalized = _normalized_identifier(receipt)
        matched = next(
            (
                word
                for word in forbidden
                if re.search(rf"(?:^|_){re.escape(word)}(?:_|$)", normalized)
            ),
            "",
        )
        if matched:
            leakage.append(
                _conformance_violation(
                    code="pre_review_target_outcome_in_self_test_receipt",
                    category="epistemic_ordering",
                    artifact_role="self_test_receipt",
                    artifact_path="proposal.self_test_receipts",
                    json_path=f"$[{index}]",
                    summary=(
                        "self-test receipt label reveals target-evaluation "
                        f"identifier {matched!r}"
                    ),
                    repair_scope="fresh_cold_reauthor_required",
                )
            )
    # Outcome leakage dominates structural repairability.  Structural defects
    # are retained in the evidence so a cold reauthor sees the complete shape.
    return tuple((*leakage, *structural))


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


def adapter_forge_gap_directory(
    attempt_dir: str | Path,
    gap_id: str,
    *,
    create: bool = False,
) -> Path:
    """Return the owner directory for one gap's shared staged workspace."""

    match = re.fullmatch(r"adapter-gap:([0-9a-f]{64})", str(gap_id))
    if match is None:
        raise ValueError("AdapterForge attempt requires a content-addressed gap id")
    path = Path(attempt_dir) / "adapter_forge_attempts" / match.group(1)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def adapter_forge_attempt_directory(
    attempt_dir: str | Path,
    gap_id: str,
    *,
    host_conformance_contract: str = ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
    create: bool = False,
) -> Path:
    """Return the immutable owner for one gap/host-contract evaluation."""

    gap_owner = adapter_forge_gap_directory(attempt_dir, gap_id, create=create)
    contract_digest = content_hash(
        {"host_conformance_contract": str(host_conformance_contract)}
    )
    path = gap_owner / "conformance_attempts" / contract_digest
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class _AdapterForgeReadBudget:
    """Bound the aggregate bytes retained by one cold artifact read."""

    ceiling: int | None = None
    reserved: int = 0

    def __post_init__(self) -> None:
        if self.ceiling is None:
            self.ceiling = _MAX_ADAPTER_FORGE_CONFORMANCE_BYTES

    def reserve(self, amount: int, *, context: str) -> None:
        ceiling = int(self.ceiling or 0)
        if amount < 0 or self.reserved + amount > ceiling:
            raise ValueError(
                f"{context} exceeds the AdapterForge aggregate byte ceiling"
            )
        self.reserved += amount


@dataclass(frozen=True)
class _AdapterForgeStagedArtifact:
    """One immutable UTF-8 snapshot from the staged workspace."""

    path: Path
    relative_path: str
    payload: bytes
    text: str
    content_sha256: str


def _read_adapter_forge_staged_artifact(
    root: Path,
    label: str,
    *,
    interface: str,
    budget: _AdapterForgeReadBudget,
    required: bool = True,
) -> _AdapterForgeStagedArtifact | None:
    """Open a staged file through a no-link directory chain and freeze its bytes."""

    relative = Path(label)
    if (
        not label
        or relative.is_absolute()
        or label != relative.as_posix()
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise ValueError("capability proposal references a malformed staged path")
    directory_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    directory_flags |= getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    file_flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptors: list[int] = []
    try:
        try:
            current_fd = os.open(root, directory_flags)
        except FileNotFoundError:
            if not required:
                return None
            raise ValueError("AdapterForge staged workspace is unavailable")
        except OSError as exc:
            raise ValueError("AdapterForge staged workspace is unavailable") from exc
        descriptors.append(current_fd)
        for part in relative.parts[:-1]:
            try:
                current_fd = os.open(
                    part,
                    directory_flags,
                    dir_fd=current_fd,
                )
            except FileNotFoundError:
                if not required:
                    return None
                raise ValueError(
                    "capability proposal references a non-staged directory"
                )
            except OSError as exc:
                raise ValueError(
                    "capability proposal references a non-staged directory"
                ) from exc
            descriptors.append(current_fd)
        try:
            file_fd = os.open(relative.parts[-1], file_flags, dir_fd=current_fd)
        except FileNotFoundError:
            if not required:
                return None
            raise ValueError(
                "capability proposal references a non-staged file"
            )
        except OSError as exc:
            raise ValueError(
                "capability proposal references a non-staged file"
            ) from exc
        descriptors.append(file_fd)
        metadata = os.fstat(file_fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("capability proposal references a non-regular file")
        if metadata.st_size > _MAX_STAGED_ARTIFACT_BYTES:
            raise AdapterForgeHostCapabilityUnavailable(
                "staged_artifact_byte_limit_exhausted",
                interface=interface,
                artifact_path=label,
                observed=int(metadata.st_size),
                ceiling=_MAX_STAGED_ARTIFACT_BYTES,
            )
        projected_aggregate = budget.reserved + int(metadata.st_size)
        if projected_aggregate > int(budget.ceiling or 0):
            raise AdapterForgeHostCapabilityUnavailable(
                "staged_artifact_aggregate_byte_limit_exhausted",
                interface=interface,
                artifact_path=label,
                observed=projected_aggregate,
                ceiling=int(budget.ceiling or 0),
            )
        budget.reserve(
            int(metadata.st_size),
            context="staged artifact aggregate",
        )
        chunks: list[bytes] = []
        observed = 0
        while observed < metadata.st_size:
            chunk = os.read(
                file_fd,
                min(1_048_576, int(metadata.st_size) - observed),
            )
            if not chunk:
                break
            chunks.append(chunk)
            observed += len(chunk)
        after = os.fstat(file_fd)
        if (
            after.st_dev != metadata.st_dev
            or after.st_ino != metadata.st_ino
            or after.st_size != metadata.st_size
            or after.st_size != observed
        ):
            raise ValueError("staged artifact changed while being read")
        payload = b"".join(chunks)
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("staged artifact is not UTF-8 text") from exc
        return _AdapterForgeStagedArtifact(
            path=root / relative,
            relative_path=relative.as_posix(),
            payload=payload,
            text=text,
            content_sha256=content_hash({"bytes": text}),
        )
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _read_adapter_forge_regular_bytes(
    path: Path,
    *,
    context: str,
    budget: _AdapterForgeReadBudget,
) -> bytes | None:
    """Read one bounded regular file without following a final symlink."""

    if not os.path.lexists(path):
        return None
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise ValueError(f"{context} is not readable") from exc
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"{context} is not a regular file")
    if before.st_size > _MAX_ADAPTER_FORGE_CONFORMANCE_BYTES:
        raise ValueError(f"{context} exceeds its byte ceiling")
    budget.reserve(before.st_size, context=context)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"{context} is not a readable regular file") from exc
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != before.st_dev
            or opened.st_ino != before.st_ino
        ):
            raise ValueError(f"{context} changed identity while opening")
        if opened.st_size > _MAX_ADAPTER_FORGE_CONFORMANCE_BYTES:
            raise ValueError(f"{context} exceeds its byte ceiling")
        if opened.st_size > before.st_size:
            budget.reserve(opened.st_size - before.st_size, context=context)
        chunks: list[bytes] = []
        observed = 0
        reserved_for_file = max(before.st_size, opened.st_size)
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            observed += len(chunk)
            if observed > _MAX_ADAPTER_FORGE_CONFORMANCE_BYTES:
                raise ValueError(f"{context} exceeds its byte ceiling")
            if observed > reserved_for_file:
                budget.reserve(observed - reserved_for_file, context=context)
                reserved_for_file = observed
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (
            after.st_dev != opened.st_dev
            or after.st_ino != opened.st_ino
            or after.st_size != observed
        ):
            raise ValueError(f"{context} changed while being read")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _parse_adapter_forge_json_bytes(
    payload: bytes,
    *,
    context: str,
) -> Any:
    """Decode one already-bounded AdapterForge artifact as strict JSON data."""

    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ValueError(f"{context} is malformed JSON") from exc
    try:
        return strict_json_data(
            value,
            context=context,
            max_wire_bytes=_MAX_ADAPTER_FORGE_CONFORMANCE_BYTES,
            max_integer_bits=_MAX_ADAPTER_FORGE_PROTOCOL_INTEGER_BITS,
            allow_finite_floats=True,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError(f"{context} is malformed JSON data") from exc


def _read_adapter_forge_json(
    path: Path,
    *,
    context: str,
    budget: _AdapterForgeReadBudget | None = None,
) -> Any:
    active_budget = budget or _AdapterForgeReadBudget()
    payload = _read_adapter_forge_regular_bytes(
        path,
        context=context,
        budget=active_budget,
    )
    if payload is None:
        return None
    return _parse_adapter_forge_json_bytes(payload, context=context)


def _persist_adapter_forge_exact(
    path: Path,
    value: Mapping[str, Any],
    *,
    context: str,
) -> None:
    """Create or exact-replay one immutable AdapterForge owner slot."""

    occupied = os.path.lexists(path)
    prior = _read_adapter_forge_json(
        path,
        context=context + " slot",
    )
    if occupied:
        if not isinstance(prior, Mapping) or dict(prior) != dict(value):
            raise ValueError(f"{context} slot conflicts with occupied bytes")
        return
    write_json_atomic(path, dict(value))


def _validate_adapter_forge_host_failure(
    value: Mapping[str, Any],
    *,
    gap_id: str,
    host_conformance_contract: str,
) -> tuple[dict[str, Any], bool]:
    """Validate one canonical host rejection/unavailability receipt."""

    row = dict(value)
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    if row.get("receipt_sha256") != content_hash(core):
        raise ValueError("AdapterForge host failure is not content-bound")
    if (
        row.get("gap_id") != gap_id
        or row.get("host_conformance_contract")
        != host_conformance_contract
        or row.get("ok") is not False
        or not isinstance(row.get("interface"), str)
        or not row["interface"]
        or re.fullmatch(r"[0-9a-f]{64}", str(row.get("proposal_digest") or ""))
        is None
    ):
        raise ValueError("AdapterForge host failure crossed attempt identity")
    if row.get("schema") == "leanmill.adapter_forge_host_unavailable.v1":
        required = {
            "schema", "gap_id", "interface", "host_conformance_contract",
            "proposal_digest", "ok", "outcome", "reason_code",
            "artifact_path", "observed", "ceiling", "resource_contract",
            "automatic_retry_performed", "recovery_route", "authority",
            "claim_boundary", "receipt_sha256",
        }
        if (
            set(row) != required
            or row.get("outcome") != "unavailable"
            or not isinstance(row.get("reason_code"), str)
            or not row["reason_code"]
            or not isinstance(row.get("artifact_path"), str)
            or type(row.get("observed")) is not int
            or int(row["observed"]) < 0
            or type(row.get("ceiling")) is not int
            or int(row["ceiling"]) < 0
            or not isinstance(row.get("resource_contract"), str)
            or not row["resource_contract"]
            or row.get("automatic_retry_performed") is not False
            or row.get("recovery_route")
            != "return_unavailable_to_theory_search"
            or row.get("authority")
            != "deterministic_adapter_forge_host_resources"
            or not isinstance(row.get("claim_boundary"), str)
            or not row["claim_boundary"]
        ):
            raise ValueError("AdapterForge host unavailability is malformed")
        return row, True
    required = {
        "schema", "gap_id", "interface", "host_conformance_contract",
        "proposal_digest", "ok", "error_type", "reason",
        "rejection_class", "violations", "same_agent_repair_allowed",
        "workspace_reuse_allowed", "automatic_retry_performed",
        "required_agent_identity", "recovery_route", "authority",
        "claim_boundary", "receipt_sha256",
    }
    relations = {
        ADAPTER_FORGE_REJECTION_PRE_REVIEW_LEAKAGE: (
            False,
            False,
            "fresh_cold_adapter_forge_leaf",
            "reauthor_in_fresh_cold_workspace_with_new_agent_identity",
        ),
        ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT: (
            True,
            True,
            "same_adapter_forge_leaf_permitted",
            "return_typed_structural_repair_to_campaign",
        ),
        ADAPTER_FORGE_REJECTION_UNCLASSIFIED: (
            False,
            False,
            "fresh_campaign_disposition_required",
            "return_rejection_to_theory_search",
        ),
    }
    relation = relations.get(str(row.get("rejection_class") or ""))
    violations = row.get("violations")
    violation_fields = {
        "code", "category", "artifact_role", "artifact_path", "json_path",
        "summary", "repair_scope",
    }
    if (
        set(row) != required
        or row.get("schema") != "leanmill.adapter_forge_host_rejection.v2"
        or relation is None
        or not isinstance(row.get("error_type"), str)
        or not row["error_type"]
        or not isinstance(row.get("reason"), str)
        or not row["reason"]
        or not isinstance(violations, list)
        or not violations
        or any(
            not isinstance(violation, Mapping)
            or set(violation) != violation_fields
            or any(
                not isinstance(violation.get(field), str)
                or (field != "artifact_path" and not violation[field])
                for field in violation_fields
            )
            for violation in violations
        )
        or (
            row.get("same_agent_repair_allowed"),
            row.get("workspace_reuse_allowed"),
            row.get("required_agent_identity"),
            row.get("recovery_route"),
        )
        != relation
        or row.get("automatic_retry_performed") is not False
        or row.get("authority") != "deterministic_host_conformance"
        or not isinstance(row.get("claim_boundary"), str)
        or not row["claim_boundary"]
    ):
        raise ValueError("AdapterForge host rejection is malformed")
    return row, False


def _validate_adapter_forge_skipped_review(
    value: Mapping[str, Any],
    *,
    host_receipt_sha256: str,
    unavailable: bool,
) -> dict[str, Any]:
    row = dict(value)
    expected = {
        "schema": "leanmill.adapter_forge_review_skipped.v1",
        "accepted": False,
        "rationale": (
            "host resources were unavailable before review"
            if unavailable
            else "host conformance rejected the proposal before review"
        ),
        "host_rejection_receipt_sha256": str(host_receipt_sha256),
        "authority": "host_lifecycle",
    }
    if row != expected:
        raise ValueError("AdapterForge skipped review is malformed")
    return row


def _validate_adapter_forge_review_unavailable(
    value: Mapping[str, Any],
    *,
    host_receipt_sha256: str,
) -> dict[str, Any]:
    row = dict(value)
    required = {
        "schema", "accepted", "outcome", "reason_code", "error_type",
        "reason", "host_receipt_sha256", "authority", "claim_boundary",
        "receipt_sha256",
    }
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    if (
        set(row) != required
        or row.get("schema") != "leanmill.adapter_forge_review_unavailable.v1"
        or row.get("accepted") is not False
        or row.get("outcome") != "unavailable"
        or row.get("reason_code")
        != "independent_review_capability_unavailable"
        or not isinstance(row.get("error_type"), str)
        or not row["error_type"]
        or not isinstance(row.get("reason"), str)
        or row.get("host_receipt_sha256") != host_receipt_sha256
        or row.get("authority") != "adapter_forge_review_lifecycle"
        or not isinstance(row.get("claim_boundary"), str)
        or not row["claim_boundary"]
        or row.get("receipt_sha256") != content_hash(core)
    ):
        raise ValueError("AdapterForge review unavailability is malformed")
    return row


def _adapter_forge_quarantine_projection(
    receipt: Mapping[str, Any],
    *,
    gap_id: str,
    host_conformance_contract: str,
) -> dict[str, Any]:
    row = dict(receipt)
    required = {
        "schema", "gap_id", "proposed_adapter_id", "proposal_digest",
        "host_conformance", "independent_review", "review_evidence_binding",
        "status", "live_registry_mutated", "exactness_authority_granted",
        "next_step", "receipt_sha256",
    }
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    host = row.get("host_conformance")
    review = row.get("independent_review")
    if (
        set(row) != required
        or row.get("schema")
        != "leanmill.adapter_forge_quarantine_receipt.v1"
        or row.get("gap_id") != gap_id
        or not isinstance(row.get("proposed_adapter_id"), str)
        or not row["proposed_adapter_id"]
        or re.fullmatch(r"[0-9a-f]{64}", str(row.get("proposal_digest") or ""))
        is None
        or row.get("live_registry_mutated") is not False
        or row.get("exactness_authority_granted") is not False
        or row.get("receipt_sha256") != content_hash(core)
        or not isinstance(host, Mapping)
        or not isinstance(review, Mapping)
    ):
        raise ValueError("AdapterForge quarantine receipt is malformed")
    host_core = {key: item for key, item in host.items() if key != "receipt_sha256"}
    if (
        host.get("host_conformance_contract") != host_conformance_contract
        or host.get("receipt_sha256") != content_hash(host_core)
    ):
        raise ValueError("AdapterForge completion crossed its host contract")
    binding = row.get("review_evidence_binding")
    if host.get("ok") is False:
        frozen_host, unavailable = _validate_adapter_forge_host_failure(
            host,
            gap_id=gap_id,
            host_conformance_contract=host_conformance_contract,
        )
        _validate_adapter_forge_skipped_review(
            review,
            host_receipt_sha256=str(frozen_host["receipt_sha256"]),
            unavailable=unavailable,
        )
        if binding is not None:
            raise ValueError("AdapterForge skipped review carried evidence binding")
        expected_status = (
            "quarantined_capability_unavailable"
            if unavailable
            else "quarantined_capability_rejected"
        )
        expected_next = str(frozen_host["recovery_route"])
    elif host.get("ok") is True and review.get("outcome") == "unavailable":
        _validate_adapter_forge_review_unavailable(
            review,
            host_receipt_sha256=str(host["receipt_sha256"]),
        )
        if binding is not None:
            raise ValueError("AdapterForge unavailable review carried a binding")
        expected_status = "quarantined_capability_unavailable"
        expected_next = "return_unavailable_to_theory_search"
    elif host.get("ok") is True:
        frozen_review = validate_adapter_forge_review(review)
        expected_binding = bind_adapter_review_evidence(frozen_review, host)
        if binding != expected_binding:
            raise ValueError("AdapterForge review evidence binding changed")
        accepted = frozen_review["accepted"] is True
        expected_status = (
            "quarantined_registry_proposal"
            if accepted
            else "quarantined_capability_rejected"
        )
        expected_next = (
            "execute_reviewed_construction_parameterization"
            if accepted
            and host.get("construction_parameterization_receipt_sha256")
            else "execute_reviewed_finite_construction_family"
            if accepted and host.get("finite_family_receipt_sha256")
            else "compile_campaign_local_functor_image_successor"
            if accepted
            and (
                host.get("functor_image_receipt_sha256")
                or host.get("candidate_receipt_sha256")
            )
            else "code_review_and_registry_authority_then_new_blueprint_attempt"
            if accepted
            else "return_rejection_to_theory_search"
        )
    else:
        raise ValueError("AdapterForge host outcome is malformed")
    if row.get("status") != expected_status or row.get("next_step") != expected_next:
        raise ValueError("AdapterForge quarantine outcome algebra changed")
    return row


def _adapter_forge_completion_projection(
    receipt: Mapping[str, Any],
) -> tuple[str, str, str, str]:
    host = receipt["host_conformance"]
    review = receipt["independent_review"]
    unavailable = receipt["status"] == "quarantined_capability_unavailable"
    status = (
        "unavailable"
        if unavailable
        else "reviewed_campaign_local_construction_parameterization_available"
        if receipt["status"] == "quarantined_registry_proposal"
        and receipt["next_step"]
        == "execute_reviewed_construction_parameterization"
        else "reviewed_campaign_local_finite_family_available"
        if receipt["status"] == "quarantined_registry_proposal"
        and receipt["next_step"] == "execute_reviewed_finite_construction_family"
        else "reviewed_campaign_local_functor_image_available"
        if receipt["status"] == "quarantined_registry_proposal"
        and receipt["next_step"] == "compile_campaign_local_functor_image_successor"
        else "quarantined_adapter_proposal_requires_authority_and_new_attempt"
        if receipt["status"] == "quarantined_registry_proposal"
        else "adapter_proposal_rejected_return_to_search"
    )
    if host.get("ok") is False and host.get("outcome") == "unavailable":
        reason = "host_capability_unavailable:" + str(host["reason_code"])
    elif host.get("ok") is False:
        reason = "host_conformance_rejected:" + str(host["reason"])
    elif review.get("outcome") == "unavailable":
        reason = "independent_review_capability_unavailable:" + str(
            review["reason_code"]
        )
    elif review.get("accepted") is False:
        reason = "independent_review_rejected:" + str(review["rationale"])
    else:
        reason = str(review.get("rationale") or receipt["status"])
    rejection_class = (
        str(host["rejection_class"])
        if host.get("ok") is False and host.get("outcome") != "unavailable"
        else ""
    )
    recovery_route = (
        str(receipt["next_step"])
        if receipt["status"]
        in {"quarantined_capability_rejected", "quarantined_capability_unavailable"}
        else ""
    )
    return status, reason, rejection_class, recovery_route


def _validated_adapter_forge_completion(
    value: Mapping[str, Any],
    *,
    gap_id: str,
    host_conformance_contract: str = ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
    allow_legacy_shell: bool = False,
) -> dict[str, Any]:
    row = dict(value)
    core = {
        key: item for key, item in row.items() if key != "completion_sha256"
    }
    if (
        row.get("schema") != "leanmill.adapter_forge_completion.v1"
        or row.get("gap_id") != gap_id
        or row.get("host_conformance_contract") != host_conformance_contract
        or row.get("completion_sha256") != content_hash(core)
    ):
        raise ValueError("AdapterForge completion crossed attempt identity")
    completion_fields = {
        "schema", "status", "attempt_dir", "gap_id",
        "host_conformance_contract", "quarantine_receipt", "reason",
        "rejection_class", "recovery_route", "evidence_refs",
        "provider_calls", "completion_sha256",
    }
    receipt = row.get("quarantine_receipt")
    if not isinstance(receipt, Mapping):
        if allow_legacy_shell:
            return row
        raise ValueError("AdapterForge scoped completion lacks its quarantine graph")
    if set(row) != completion_fields:
        raise ValueError("AdapterForge scoped completion fields changed identity")
    receipt = _adapter_forge_quarantine_projection(
        receipt,
        gap_id=gap_id,
        host_conformance_contract=host_conformance_contract,
    )
    expected_status, reason, rejection_class, recovery_route = (
        _adapter_forge_completion_projection(receipt)
    )
    if (
        row.get("status") != expected_status
        or row.get("reason") != reason
        or row.get("rejection_class") != rejection_class
        or row.get("recovery_route") != recovery_route
        or row.get("evidence_refs") != [receipt["receipt_sha256"]]
        or not isinstance(row.get("attempt_dir"), str)
        or not row["attempt_dir"]
        or type(row.get("provider_calls")) is not int
        or int(row["provider_calls"]) < 0
    ):
        raise ValueError("AdapterForge completion projection changed identity")
    return row


def read_adapter_forge_completion(
    attempt_dir: str | Path,
    gap: AdapterGap,
    *,
    migrate_legacy: bool = False,
) -> dict[str, Any] | None:
    """Resolve a completion only from the active gap's artifact namespace.

    A matching pre-namespace completion is migrated once for compatibility.
    A completion from another gap or host-conformance contract remains history.
    """

    directory = Path(attempt_dir)
    scoped_completions: list[dict[str, Any]] = []
    scoped_budget = _AdapterForgeReadBudget()
    for active_contract in (
        ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT,
        ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
    ):
        scoped = read_scoped_adapter_forge_completion(
            directory,
            gap_id=gap.gap_id,
            host_conformance_contract=active_contract,
            _read_budget=scoped_budget,
        )
        if scoped is not None:
            scoped_completions.append(scoped)
    if len(scoped_completions) > 1:
        raise ValueError("AdapterForge gap has conflicting host-contract completions")
    if scoped_completions:
        return scoped_completions[0]

    gap_owner = adapter_forge_gap_directory(directory, gap.gap_id)
    legacy_candidates = (
        gap_owner / "adapter_forge_completion.json",
        directory / "adapter_forge_completion.json",
    )
    legacy_path = None
    legacy: Mapping[str, Any] | None = None
    legacy_budget = _AdapterForgeReadBudget()
    for path in legacy_candidates:
        candidate = _read_adapter_forge_json(
            path,
            context="AdapterForge legacy completion slot",
            budget=legacy_budget,
        )
        if os.path.lexists(path) and not isinstance(candidate, Mapping):
            raise ValueError("AdapterForge legacy completion slot is malformed")
        if (
            isinstance(candidate, Mapping)
            and candidate.get("gap_id") == gap.gap_id
            and candidate.get("host_conformance_contract")
            == ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT
        ):
            legacy_path, legacy = path, candidate
            break
    if legacy_path is None:
        return None
    if not isinstance(legacy, Mapping):
        raise ValueError("AdapterForge legacy completion is malformed")
    completion = _validated_adapter_forge_completion(
        legacy,
        gap_id=gap.gap_id,
        allow_legacy_shell=True,
    )
    if not migrate_legacy:
        return completion
    owner = adapter_forge_attempt_directory(
        directory,
        gap.gap_id,
        host_conformance_contract=ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        create=True,
    )
    migrated = []
    migration_payloads: list[tuple[Path, dict[str, Any], str]] = []
    legacy_names = (
        "adapter_forge_receipt.json",
        "adapter_forge_completion.json",
        "adapter_forge_host_conformance.json",
        "theory_language_coordinates.json",
        "theory_language_functor_image.json",
        "theory_language_generative_candidate.json",
        "theory_language_generative_application.json",
    )
    # Read the complete fixed legacy set under one aggregate ceiling before
    # parsing or mutating the canonical owner.
    migration_read_budget = _AdapterForgeReadBudget()
    legacy_payload_bytes = {
        name: _read_adapter_forge_regular_bytes(
            legacy_path.with_name(name),
            context="AdapterForge legacy " + name,
            budget=migration_read_budget,
        )
        for name in legacy_names
    }
    for name in legacy_names:
        payload_bytes = legacy_payload_bytes[name]
        value = (
            _parse_adapter_forge_json_bytes(
                payload_bytes,
                context="AdapterForge legacy " + name,
            )
            if payload_bytes is not None
            else None
        )
        if not isinstance(value, Mapping):
            continue
        artifact_gap_id = str(value.get("gap_id") or "")
        if name == "adapter_forge_host_conformance.json":
            receipt = completion.get("quarantine_receipt") or {}
            if value != receipt.get("host_conformance"):
                continue
        elif name == "adapter_forge_receipt.json":
            if artifact_gap_id != gap.gap_id:
                continue
        elif name != "adapter_forge_completion.json" and artifact_gap_id != gap.gap_id:
            continue
        migration_payloads.append(
            (owner / name, dict(value), "AdapterForge migrated " + name)
        )
        migrated.append(
            {"name": name, "artifact_sha256": content_hash(dict(value))}
        )
    core = {
        "schema": "leanmill.adapter_forge_legacy_migration.v1",
        "gap_id": gap.gap_id,
        "owner_directory": str(owner.relative_to(directory)),
        "migrated_artifacts": migrated,
        "authority": "deterministic_adapter_forge_artifact_store",
    }
    migration_receipt = {**core, "receipt_sha256": content_hash(core)}
    migration_payloads.append(
        (
            owner / "legacy_migration.json",
            migration_receipt,
            "AdapterForge legacy migration",
        )
    )
    # Preflight every target before the first write so a later occupied slot
    # cannot leave a partially migrated owner graph.
    target_read_budget = _AdapterForgeReadBudget()
    occupied_payloads = {
        target: _read_adapter_forge_regular_bytes(
            target,
            context=context + " slot",
            budget=target_read_budget,
        )
        for target, _payload, context in migration_payloads
    }
    for target, payload, context in migration_payloads:
        prior_bytes = occupied_payloads[target]
        prior = (
            _parse_adapter_forge_json_bytes(
                prior_bytes,
                context=context + " slot",
            )
            if prior_bytes is not None
            else None
        )
        if prior_bytes is not None and (
            not isinstance(prior, Mapping) or dict(prior) != payload
        ):
            raise ValueError(f"{context} slot conflicts with occupied bytes")
    for target, payload, context in migration_payloads:
        _persist_adapter_forge_exact(target, payload, context=context)
    return _validated_adapter_forge_completion(
        completion,
        gap_id=gap.gap_id,
        host_conformance_contract=ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        allow_legacy_shell=True,
    )


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
    paths = {
        "type": "array",
        "items": {"type": "string", "minLength": 1, "maxLength": 4_096},
        "minItems": 1,
        "maxItems": _MAX_STAGED_ARTIFACTS_PER_ROLE,
        "uniqueItems": True,
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "source_paths", "test_paths", "manifest", "self_test_receipts",
        ],
        "properties": {
            "source_paths": paths,
            "test_paths": paths,
            "manifest": {
                "type": "object",
                "minProperties": 1,
                "maxProperties": 32,
                "propertyNames": {"type": "string", "maxLength": 128},
            },
            "self_test_receipts": {
                "type": "array",
                "items": {"type": "string", "minLength": 1, "maxLength": 512},
                "minItems": 1,
                "maxItems": 64,
                "uniqueItems": True,
            },
            "registry_mutation": {"type": "boolean"},
        },
    }


def adapter_forge_agent_output_schema() -> dict[str, Any]:
    """Return the strict subscription-role envelope before host validation."""

    paths = {
        "type": "array",
        "items": {"type": "string", "minLength": 1, "maxLength": 4_096},
        "minItems": 1,
        "maxItems": _MAX_STAGED_ARTIFACTS_PER_ROLE,
    }
    manifest = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "adapter_id",
            "request_id",
            "interface",
            "capability_source",
            "observable_paths",
        ],
        "properties": {
            "adapter_id": {
                "type": "string",
                "minLength": 1,
                "maxLength": 512,
            },
            "request_id": {
                "type": ["string", "null"],
                "maxLength": 512,
            },
            "interface": {
                "type": ["string", "null"],
                "maxLength": 512,
            },
            "capability_source": {
                "type": "string",
                "minLength": 1,
                "maxLength": 4_096,
            },
            "observable_paths": {
                "type": "array",
                "items": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 4_096,
                },
                "maxItems": 4,
            },
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "source_paths",
            "test_paths",
            "manifest",
            "self_test_receipts",
            "registry_mutation",
        ],
        "properties": {
            "source_paths": paths,
            "test_paths": paths,
            "manifest": manifest,
            "self_test_receipts": {
                "type": "array",
                "items": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 512,
                },
                "minItems": 1,
                "maxItems": 64,
            },
            "registry_mutation": {"type": "boolean", "const": False},
        },
    }


def _preflight_staged_artifact_paths(
    proposal: Mapping[str, Any],
    *,
    root: Path,
    interface: str,
) -> tuple[
    list[_AdapterForgeStagedArtifact],
    list[_AdapterForgeStagedArtifact],
    _AdapterForgeReadBudget,
]:
    """Resolve bounded staged artifacts before any source/test bytes are read."""

    resolved: dict[str, list[_AdapterForgeStagedArtifact]] = {}
    all_labels: set[str] = set()
    budget = _AdapterForgeReadBudget(
        ceiling=_MAX_STAGED_ARTIFACT_AGGREGATE_BYTES
    )
    for role, field in (("source", "source_paths"), ("test", "test_paths")):
        labels = proposal.get(field)
        if (
            not isinstance(labels, list)
            or not labels
            or any(
                not isinstance(label, str)
                or not label
                or len(label) > 4_096
                for label in labels
            )
        ):
            raise ValueError(f"capability {role} paths are malformed")
        if len(labels) > _MAX_STAGED_ARTIFACTS_PER_ROLE:
            raise AdapterForgeHostCapabilityUnavailable(
                "staged_artifact_count_limit_exhausted",
                interface=interface,
                artifact_path=field,
                observed=len(labels),
                ceiling=_MAX_STAGED_ARTIFACTS_PER_ROLE,
            )
        if len(labels) != len(set(labels)) or all_labels.intersection(labels):
            raise ValueError("capability proposal repeats a staged file")
        all_labels.update(labels)
        snapshots: list[_AdapterForgeStagedArtifact] = []
        for label in labels:
            snapshot = _read_adapter_forge_staged_artifact(
                root,
                label,
                interface=interface,
                budget=budget,
            )
            if snapshot is None:
                raise ValueError(
                    "capability proposal references a non-staged file"
                )
            snapshots.append(snapshot)
        resolved[role] = snapshots
    return resolved["source"], resolved["test"], budget


def adapter_review_output_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["accepted", "reviewer_ref", "rationale", "evidence_refs"],
        "properties": {
            "accepted": {"type": "boolean"},
            "reviewer_ref": {
                "type": "string",
                "minLength": 1,
                "maxLength": 512,
            },
            "rationale": {
                "type": "string",
                "minLength": 1,
                "maxLength": 4_096,
            },
            "evidence_refs": {
                "type": "array",
                "items": {"type": "string", "minLength": 64, "maxLength": 71},
                "minItems": 1,
                "maxItems": _MAX_ADAPTER_FORGE_REVIEW_REFS,
            },
        },
    }


def _validate_adapter_forge_proposal(value: Any) -> dict[str, Any]:
    """Bound and validate the coding-agent envelope before hashing or I/O."""

    interface = ""
    if isinstance(value, Mapping) and isinstance(value.get("manifest"), Mapping):
        interface = str(value["manifest"].get("interface") or "")
    try:
        row = _forge_data_ingress(
            "proposal", value, interface=interface
        )
    except ValueError as exc:
        if "maximum JSON wire size" in str(exc):
            raise AdapterForgeHostCapabilityUnavailable(
                "adapter_forge_proposal_byte_limit_exhausted",
                interface=interface,
                observed=_MAX_ADAPTER_FORGE_PROPOSAL_BYTES + 1,
                ceiling=_MAX_ADAPTER_FORGE_PROPOSAL_BYTES,
                resource_contract=(
                    "leanmill.adapter_forge_protocol_envelope_resources.v1"
                ),
            ) from exc
        raise
    if not isinstance(row, dict):
        raise ValueError("AdapterForge returned no structured proposal")
    for field in ("source_paths", "test_paths"):
        paths = row.get(field)
        if isinstance(paths, list) and len(paths) > _MAX_STAGED_ARTIFACTS_PER_ROLE:
            raise AdapterForgeHostCapabilityUnavailable(
                "staged_artifact_count_limit_exhausted",
                interface=interface,
                artifact_path=field,
                observed=len(paths),
                ceiling=_MAX_STAGED_ARTIFACTS_PER_ROLE,
            )
    errors = sorted(
        Draft202012Validator(adapter_forge_output_schema()).iter_errors(row),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        raise ValueError(
            "AdapterForge proposal schema mismatch: " + errors[0].message
        )
    return row


def _json_fragment(value: Any, fragment: str) -> Any:
    current = value
    for part in fragment.split(".") if fragment else ():
        if not isinstance(current, Mapping) or part not in current:
            raise ValueError("evidence artifact fragment is absent")
        current = current[part]
    return current


def _stage_evidence_context_artifacts(
    directory: Path,
    workspace: Path,
    snapshot: Mapping[str, Any],
    *,
    source_repo: Path,
) -> dict[str, Any]:
    """Materialize only manifest-declared files named by frozen object records."""

    manifest = read_json(directory / "campaign_manifest.json", {})
    metadata = manifest.get("metadata") if isinstance(manifest, Mapping) else None
    declared = metadata.get("evidence_refs") if isinstance(metadata, Mapping) else None
    if not isinstance(declared, list):
        declared = []
    candidates: dict[str, list[tuple[str, Path]]] = {}
    root = source_repo.resolve()
    for raw in declared:
        label = str(raw)
        path = (root / label).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("campaign evidence file is absent or outside the repository")
        candidates.setdefault(path.name, []).append((label, path))

    evidence_dir = workspace / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    staged_files: dict[Path, dict[str, Any]] = {}
    object_bindings: list[dict[str, Any]] = []
    for record in snapshot.get("object_records") or ():
        if not isinstance(record, Mapping):
            raise ValueError("evidence context object record is malformed")
        payload = record.get("payload")
        if not isinstance(payload, Mapping) or not payload.get("artifact_ref"):
            continue
        artifact_ref = str(payload["artifact_ref"])
        filename, separator, fragment = artifact_ref.partition("#")
        matches = candidates.get(Path(filename).name, [])
        if len(matches) != 1 or Path(filename).name != filename:
            raise ValueError("evidence artifact ref is not uniquely campaign-declared")
        declared_path, source = matches[0]
        raw_json = json.loads(source.read_text(encoding="utf-8"))
        selected = _json_fragment(raw_json, fragment if separator else "")
        declared_sha = str(payload.get("artifact_sha256") or "")
        if not declared_sha or declared_sha != content_hash(selected):
            raise ValueError("evidence artifact fragment digest mismatch")
        target = evidence_dir / source.name
        shutil.copy2(source, target)
        file_row = staged_files.setdefault(
            source,
            {
                "declared_path": declared_path,
                "staged_path": str(target.relative_to(workspace)),
                "bytes_sha256": content_hash(
                    {"bytes": source.read_text(encoding="utf-8")}
                ),
            },
        )
        object_bindings.append(
            {
                "object_id": str(record.get("object_id") or ""),
                "artifact_ref": artifact_ref,
                "artifact_sha256": declared_sha,
                "staged_path": file_row["staged_path"],
            }
        )
    core = {
        "schema": "leanmill.adapter_forge_evidence_materialization.v1",
        "context_hash": str(snapshot.get("context_hash") or ""),
        "files": [staged_files[path] for path in sorted(staged_files)],
        "object_bindings": object_bindings,
        "authority": "frozen_campaign_manifest_evidence_join",
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    write_json_atomic(workspace / "evidence_materialization.json", receipt)
    return receipt


def stage_adapter_forge_workspace(
    attempt_dir: str | Path,
    gap: AdapterGap,
    *,
    source_repo: str | Path | None = None,
) -> Path:
    directory = Path(attempt_dir)
    workspace = (
        adapter_forge_gap_directory(directory, gap.gap_id, create=True)
        / "workspace"
    )
    workspace.mkdir(parents=True, exist_ok=True)
    write_json_atomic(workspace / "adapter_gap.json", gap.to_json())
    contexts = [
        ("formal_theory", directory / "formal_context.json"),
        ("evidence_incidence", directory / "evidence_context.json"),
    ]
    available = [(kind, path) for kind, path in contexts if path.is_file()]
    if gap.gap_kind == "capability_missing" and len(available) != 1:
        raise ValueError("capability forge requires exactly one frozen context")
    if available:
        context_kind, context_path = available[0]
        shutil.copy2(context_path, workspace / context_path.name)
        snapshot = json.loads(context_path.read_text(encoding="utf-8"))
        evidence_materialization = None
        if context_kind == "evidence_incidence":
            evidence_materialization = _stage_evidence_context_artifacts(
                directory,
                workspace,
                snapshot,
                source_repo=Path.cwd() if source_repo is None else Path(source_repo),
            )
        universe = dict(snapshot.get("model_universe") or {})
        models = list(universe.pop("models", ()) or ())
        object_records = list(snapshot.get("object_records") or ())
        write_json_atomic(
            workspace / "context_fixture.json",
            {
                "schema": "leanmill.adapter_forge_context_fixture.v2",
                "context_kind": context_kind,
                "context_hash": str(snapshot.get("context_hash") or ""),
                "snapshot_keys": sorted(snapshot),
                "model_universe_without_models": universe,
                "model_count": len(models),
                "sample_models": models[:3],
                "object_count": len(object_records),
                "sample_objects": object_records[:3],
                "evidence_materialization_receipt_sha256": (
                    str(evidence_materialization["receipt_sha256"])
                    if evidence_materialization is not None
                    else ""
                ),
            },
        )
        blueprint = read_json(directory / "blueprint.json", None)
        if isinstance(blueprint, Mapping):
            write_json_atomic(workspace / "blueprint.json", dict(blueprint))
            try:
                interface = construction_witness_interface(
                    str(blueprint.get("adapter_id") or ""),
                    dict(blueprint.get("adapter_config") or {}),
                )
            except (KeyError, ValueError):
                interface = None
            if interface is not None:
                write_json_atomic(
                    workspace / "witness_construction_interface.json", interface
                )
                request = gap.primitive_semantics_contract.get(
                    "theory_language_request"
                )
                if isinstance(request, Mapping):
                    write_json_atomic(
                        workspace / "finite_construction_family_contract.json",
                        finite_construction_family_authoring_contract(
                            request_id=str(request.get("request_id") or ""),
                            gap_id=gap.gap_id,
                            context_hash=str(snapshot.get("context_hash") or ""),
                            adapter_id=str(blueprint.get("adapter_id") or ""),
                            witness_interface=interface,
                        ),
                    )
                    write_json_atomic(
                        workspace / "construction_parameterization_contract.json",
                        construction_parameterization_authoring_contract(
                            campaign_id="adapter-forge:" + gap.gap_id,
                            request_id=str(request.get("request_id") or ""),
                            gap_id=gap.gap_id,
                            context_hash=str(snapshot.get("context_hash") or ""),
                            context_epoch=int(request.get("source_epoch") or 0),
                            adapter_id=str(blueprint.get("adapter_id") or ""),
                            witness_interface=interface,
                        ),
                    )
    return workspace


def _normalize_object_coordinates(
    value: Any,
    *,
    request_id: str,
) -> dict[str, Any]:
    """Normalize the two declared carriers of an object-coordinate interface."""

    coordinates = value
    if isinstance(value, Mapping) and "coordinates" in value:
        if (
            value.get("schema") != "leanmill.object_coordinates.v1"
            or value.get("request_id") != request_id
        ):
            raise ValueError("capability coordinate envelope crossed its request")
        coordinates = value.get("coordinates")
    if isinstance(coordinates, Mapping):
        return {str(key): item for key, item in coordinates.items()}
    if isinstance(coordinates, list) and all(
        isinstance(row, Mapping) and row.get("object_id") for row in coordinates
    ):
        rows = {str(row["object_id"]): dict(row) for row in coordinates}
        if len(rows) == len(coordinates):
            return rows
    raise ValueError("capability coordinates have an unsupported carrier")


def _read_staged_context_snapshot(
    root: Path,
    *,
    interface: str,
    budget: _AdapterForgeReadBudget,
) -> tuple[str, dict[str, Any], _AdapterForgeStagedArtifact]:
    """Freeze and parse the sole staged context exactly once."""

    candidates = (
        ("formal_theory", "formal_context.json"),
        ("evidence_incidence", "evidence_context.json"),
    )
    available: list[tuple[str, _AdapterForgeStagedArtifact]] = []
    for context_kind, label in candidates:
        artifact = _read_adapter_forge_staged_artifact(
            root,
            label,
            interface=interface,
            budget=budget,
            required=False,
        )
        if artifact is not None:
            available.append((context_kind, artifact))
    if len(available) != 1:
        raise ValueError("capability requires exactly one staged context owner")
    context_kind, artifact = available[0]
    snapshot = _parse_adapter_forge_json_bytes(
        artifact.payload,
        context="AdapterForge staged context",
    )
    if not isinstance(snapshot, Mapping):
        raise ValueError("staged context snapshot must be one JSON object")
    return context_kind, dict(snapshot), artifact


def _load_staged_context_owner(
    root: Path,
    *,
    interface: str,
    budget: _AdapterForgeReadBudget,
) -> tuple[str, dict[str, Any], Any]:
    """Load the frozen context through the category that owns it."""

    from ztare.leanmill.evidence_theory_context import (
        evidence_theory_context_from_snapshot,
    )
    from ztare.leanmill.finite_theory_context import (
        formal_theory_context_from_snapshot,
    )

    context_kind, snapshot, _artifact = _read_staged_context_snapshot(
        root,
        interface=interface,
        budget=budget,
    )
    context = (
        formal_theory_context_from_snapshot(snapshot)
        if context_kind == "formal_theory"
        else evidence_theory_context_from_snapshot(snapshot)
    )
    if str(snapshot.get("context_hash") or "") != context.context_hash:
        raise ValueError("staged context owner changed identity")
    return context_kind, dict(snapshot), context


def _normalize_observable_path(value: Any) -> tuple[str, ...]:
    """Compile a declared coordinate projection to coordinate-local keys.

    The current interface spells projections as JSON pointers rooted at the
    coordinate wildcard. Coordinate-local dotted paths remain readable for
    proposals produced before that spelling was made explicit.
    """

    path = str(value)
    pointer_prefix = "/coordinates/*/"
    if path.startswith(pointer_prefix):
        encoded = path[len(pointer_prefix) :].split("/")
        if not encoded or any(not part for part in encoded):
            raise ValueError("capability observable path is malformed")
        parts = tuple(
            part.replace("~1", "/").replace("~0", "~") for part in encoded
        )
    elif path.startswith("/"):
        raise ValueError("capability observable pointer must select /coordinates/*")
    else:
        parts = tuple(path.split("."))
    if not parts or any(not part or part == "*" for part in parts):
        raise ValueError("capability observable path is malformed")
    return parts


def _bind_host_conformance_contract(
    value: Mapping[str, Any],
    *,
    gap_id: str,
) -> dict[str, Any]:
    """Bind a host verdict to the contract whose semantics produced it."""

    canonical = _forge_data_ingress(
        "host_conformance",
        value,
        interface=str(value.get("interface") or "host_conformance"),
        malformed_is_unavailable=True,
    )
    if not isinstance(canonical, dict):
        raise ValueError("AdapterForge host conformance must be one object")
    row = canonical
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    if row.get("receipt_sha256") != content_hash(core):
        raise ValueError("AdapterForge host conformance is not content-bound")
    expected_contract = (
        ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT
        if core.get("interface") == CONSTRUCTION_PARAMETERIZATION_SCHEMA
        else ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT
    )
    if core.get("gap_id") not in {None, gap_id} or core.get(
        "host_conformance_contract"
    ) not in {None, expected_contract}:
        raise ValueError("AdapterForge host conformance crossed attempt identity")
    bound = {
        **core,
        "gap_id": gap_id,
        "host_conformance_contract": expected_contract,
    }
    return {**bound, "receipt_sha256": content_hash(bound)}


def _construction_parameterization_host_fields(
    parameterization: Mapping[str, Any],
    *,
    witness_interface: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate only static source-neutral construction bytes."""

    frozen = validate_construction_parameterization(parameterization)
    interface = validate_witness_construction_interface(witness_interface)
    if frozen["target_interface_sha256"] != interface["interface_sha256"]:
        raise ValueError("construction parameterization crossed target interface")
    return {
        "campaign_id": frozen["campaign_id"],
        "request_id": frozen["request_id"],
        "gap_id": frozen["gap_id"],
        "context_hash": frozen["context_hash"],
        "context_epoch": frozen["context_epoch"],
        "adapter_id": frozen["adapter_id"],
        "target_interface_sha256": frozen["target_interface_sha256"],
        "construction_parameterization_id": frozen["parameterization_id"],
        "construction_parameterization_receipt_sha256": frozen[
            "receipt_sha256"
        ],
        "backend_problem_sha256": content_hash(frozen["backend_problem"]),
        "backend_sha256": content_hash(frozen["backend"]),
        "parameter_space_sha256": content_hash(frozen["parameter_space"]),
        "materializer_sha256": content_hash(frozen["materializer"]),
        "resource_limits_sha256": content_hash(frozen["resource_limits"]),
        "search_order_sha256": content_hash(frozen["search_order"]),
        "semantic_admission_deferred": True,
        "outcomes_evaluated": False,
        "generated_code_imported": False,
        "registry_mutated": False,
    }


def _validated_construction_artifact_receipts(
    source_artifacts: list[Mapping[str, Any]],
    test_artifacts: list[Mapping[str, Any]],
    *,
    manifest_capability_source: str,
    resolved_capability_source: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, str]:
    """Validate the bounded staged provenance graph carried by authority."""

    frozen_groups: list[list[dict[str, Any]]] = []
    seen_paths: set[str] = set()
    aggregate_bytes = 0
    for role, rows in (
        ("source", source_artifacts),
        ("test", test_artifacts),
    ):
        if type(rows) is not list or not rows:
            raise ValueError(
                f"construction AdapterForge requires staged {role} artifacts"
            )
        if len(rows) > _MAX_STAGED_ARTIFACTS_PER_ROLE:
            raise ValueError(
                f"construction AdapterForge {role} artifact count exceeds its ceiling"
            )
        frozen_rows: list[dict[str, Any]] = []
        for artifact in rows:
            if not isinstance(artifact, Mapping) or set(artifact) != {
                "path", "content_sha256", "content"
            }:
                raise ValueError(
                    "construction AdapterForge artifact receipt is malformed"
                )
            path = artifact.get("path")
            content = artifact.get("content")
            if (
                type(path) is not str
                or not path
                or len(path) > 4_096
                or Path(path).is_absolute()
                or any(part in {"", ".", ".."} for part in Path(path).parts)
                or path in seen_paths
                or type(content) is not str
            ):
                raise ValueError(
                    "construction AdapterForge artifact receipt is malformed"
                )
            try:
                byte_count = len(content.encode("utf-8"))
            except UnicodeEncodeError as exc:
                raise ValueError(
                    "construction AdapterForge artifact content is not UTF-8"
                ) from exc
            if byte_count > _MAX_STAGED_ARTIFACT_BYTES:
                raise ValueError(
                    "construction AdapterForge artifact exceeds its byte ceiling"
                )
            aggregate_bytes += byte_count
            if aggregate_bytes > _MAX_STAGED_ARTIFACT_AGGREGATE_BYTES:
                raise ValueError(
                    "construction AdapterForge artifacts exceed their aggregate byte ceiling"
                )
            if artifact.get("content_sha256") != content_hash({"bytes": content}):
                raise ValueError(
                    "construction AdapterForge artifact receipt is malformed"
                )
            seen_paths.add(path)
            frozen_rows.append(
                {
                    "path": path,
                    "content_sha256": str(artifact["content_sha256"]),
                    "content": content,
                }
            )
        frozen_groups.append(frozen_rows)
    if (
        type(manifest_capability_source) is not str
        or type(resolved_capability_source) is not str
    ):
        raise ValueError(
            "construction AdapterForge capability source paths are malformed"
        )
    manifest_source = manifest_capability_source
    resolved_source = resolved_capability_source
    source_paths = {row["path"] for row in frozen_groups[0]}
    if (
        not manifest_source
        or not resolved_source
        or manifest_source not in source_paths
        or resolved_source not in source_paths
    ):
        raise ValueError(
            "construction AdapterForge capability source lacks staged source membership"
        )
    return (
        frozen_groups[0],
        frozen_groups[1],
        manifest_source,
        resolved_source,
    )


def build_adapter_forge_construction_parameterization_conformance(
    parameterization: Mapping[str, Any],
    *,
    witness_interface: Mapping[str, Any],
    source_artifacts: list[Mapping[str, Any]],
    test_artifacts: list[Mapping[str, Any]],
    manifest_capability_source: str,
    resolved_capability_source: str,
) -> dict[str, Any]:
    """Build the canonical AdapterForge host receipt for a data-only problem."""

    fields = _construction_parameterization_host_fields(
        parameterization,
        witness_interface=witness_interface,
    )
    (
        frozen_sources,
        frozen_tests,
        manifest_source,
        resolved_source,
    ) = _validated_construction_artifact_receipts(
        source_artifacts,
        test_artifacts,
        manifest_capability_source=manifest_capability_source,
        resolved_capability_source=resolved_capability_source,
    )
    core = {
        "ok": True,
        "interface": CONSTRUCTION_PARAMETERIZATION_SCHEMA,
        "host_conformance_contract": (
            ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT
        ),
        **fields,
        "source_artifacts": frozen_sources,
        "test_artifacts": frozen_tests,
        "manifest_capability_source": manifest_source,
        "resolved_capability_source": resolved_source,
        "authority": "deterministic_adapter_forge_host_conformance",
        "claim_boundary": (
            "static_registered_backend_template_interface_and_limit_bytes_"
            "only_semantic_admission_and_outcomes_deferred"
        ),
    }
    return _bind_host_conformance_contract(
        {**core, "receipt_sha256": content_hash(core)},
        gap_id=str(fields["gap_id"]),
    )


def host_capability_conformance(
    proposal: Mapping[str, Any],
    gap: AdapterGap,
    *,
    workspace: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    """Validate one staged theory-language capability at its declared interface."""

    root = Path(workspace).resolve()
    manifest = proposal.get("manifest")
    if not isinstance(manifest, Mapping):
        raise ValueError("capability proposal lacks a manifest")
    request = gap.primitive_semantics_contract.get("theory_language_request")
    if not isinstance(request, Mapping):
        raise ValueError("capability gap lacks its theory-language request")
    binding = gap.primitive_semantics_contract.get("evidence_binding")
    if isinstance(binding, Mapping):
        binding_core = {
            key: value for key, value in binding.items() if key != "receipt_sha256"
        }
        if (
            binding.get("schema") not in {
                "leanmill.workbench_evidence_binding.v1",
                "leanmill.governed_trace_evidence_binding.v1",
                "leanmill.governed_mixed_evidence_binding.v1",
            }
            or binding.get("receipt_sha256") != content_hash(binding_core)
        ):
            raise ValueError("capability evidence binding digest mismatch")
        fixture_ids = {str(row) for row in binding.get("receipt_ids") or ()}
        contrast_pairs = {
            tuple(sorted(str(value) for value in row))
            for row in binding.get("contrast_object_pairs") or ()
            if isinstance(row, list) and len(row) == 2
        }
    else:
        fixtures = gap.primitive_semantics_contract.get("evidence_fixtures")
        if not isinstance(fixtures, list):
            raise ValueError("capability gap lacks a resolved evidence binding")
        fixture_ids: set[str] = set()
        contrast_pairs: set[tuple[str, str]] = set()
        for fixture in fixtures:
            if not isinstance(fixture, Mapping):
                raise ValueError("capability evidence fixture must be a receipt")
            receipt_id = str(fixture.get("receipt_id") or "")
            core = {key: value for key, value in fixture.items() if key != "receipt_id"}
            if receipt_id != "sha256:" + content_hash(core):
                raise ValueError("capability evidence fixture digest mismatch")
            fixture_ids.add(receipt_id)
            summary = fixture.get("output_summary")
            contrast = (
                summary.get("contrast_truth_values")
                if isinstance(summary, Mapping)
                and summary.get("separates_contrast") is False
                else None
            )
            if isinstance(contrast, Mapping) and len(contrast) == 2:
                contrast_pairs.add(tuple(sorted(str(row) for row in contrast)))
    if fixture_ids != {str(row) for row in request.get("evidence_refs") or ()}:
        raise ValueError("capability evidence fixtures do not bind the request")
    interface = str(manifest.get("interface") or "")
    if interface not in {
        "leanmill.object_coordinates.v1",
        GENERATIVE_REPRESENTATION_INTERFACE,
        FINITE_CONSTRUCTION_FAMILY_SCHEMA,
        CONSTRUCTION_PARAMETERIZATION_SCHEMA,
    } or manifest.get("request_id") != request.get("request_id"):
        raise ValueError("capability manifest does not bind the frozen request")
    declared_observable_paths = tuple(
        str(row) for row in manifest.get("observable_paths") or ()
    )
    if (
        interface == "leanmill.object_coordinates.v1"
        and not 1 <= len(declared_observable_paths) <= 4
    ) or len(declared_observable_paths) > 4:
        raise ValueError("capability manifest requires one to four observable paths")
    observable_paths = tuple(
        _normalize_observable_path(row) for row in declared_observable_paths
    )
    if len(set(observable_paths)) != len(observable_paths):
        raise ValueError("capability manifest repeats an observable path")

    sources, tests, staged_read_budget = _preflight_staged_artifact_paths(
        proposal,
        root=root,
        interface=interface,
    )
    declared_source = str(manifest.get("capability_source") or "")
    declared_matches = [
        artifact for artifact in sources
        if artifact.relative_path == declared_source
    ]
    source = (
        declared_matches[0]
        if len(declared_matches) == 1
        else sources[0]
        if not declared_source and len(sources) == 1
        else None
    )
    if source is None or not tests:
        raise ValueError("capability source and checks must be staged and declared")
    if interface == CONSTRUCTION_PARAMETERIZATION_SCHEMA:
        context_kind, snapshot, _context_artifact = (
            _read_staged_context_snapshot(
                root,
                interface=interface,
                budget=staged_read_budget,
            )
        )
        blueprint_artifact = _read_adapter_forge_staged_artifact(
            root,
            "blueprint.json",
            interface=interface,
            budget=staged_read_budget,
        )
        blueprint = (
            _parse_adapter_forge_json_bytes(
                blueprint_artifact.payload,
                context="AdapterForge staged blueprint",
            )
            if blueprint_artifact is not None
            else None
        )
        if not isinstance(blueprint, Mapping):
            raise ValueError(
                "construction parameterization requires the frozen blueprint"
            )
        witness_interface = construction_witness_interface(
            str(blueprint.get("adapter_id") or ""),
            dict(blueprint.get("adapter_config") or {}),
        )
        raw_parameterization = _forge_json_text_ingress(
            "capability_source",
            source.text,
            interface=interface,
            source_ref=source.relative_path,
        )
        if not isinstance(raw_parameterization, Mapping):
            raise ValueError(
                "construction parameterization source must be one JSON object"
            )
        forbidden = _interface_outcome_words(witness_interface)
        leakage = [
            _conformance_violation(
                code="pre_review_target_outcome_in_construction_self_test",
                category="epistemic_ordering",
                artifact_role="self_test",
                artifact_path=artifact.relative_path,
                json_path=f"line:{line}" if line else "$",
                summary=(
                    "pre-review self-test references target-evaluation "
                    f"identifier {identifier!r}"
                ),
                repair_scope="fresh_cold_reauthor_required",
            )
            for artifact in tests
            for line, identifier in _test_outcome_identifiers(
                artifact.text, forbidden=forbidden
            )
        ]
        if leakage:
            raise AdapterForgeHostConformanceRejected(
                "pre-review target-evaluation leakage contaminated the construction proposal",
                rejection_class=ADAPTER_FORGE_REJECTION_PRE_REVIEW_LEAKAGE,
                violations=tuple(leakage),
            )
        try:
            parameterization = validate_construction_parameterization(
                raw_parameterization,
                campaign_id="adapter-forge:" + gap.gap_id,
                request_id=str(request.get("request_id") or ""),
                gap_id=gap.gap_id,
                context_hash=str(snapshot.get("context_hash") or ""),
                context_epoch=int(request.get("source_epoch") or 0),
                adapter_id=str(blueprint.get("adapter_id") or ""),
                target_interface_sha256=str(
                    witness_interface["interface_sha256"]
                ),
            )
        except ConstructionResourceCeilingExceeded as exc:
            raise AdapterForgeHostCapabilityUnavailable(
                str(exc.reason_code),
                interface=interface,
                artifact_path=source.relative_path,
                observed=int(exc.observed),
                ceiling=int(exc.ceiling),
                resource_contract=(
                    "leanmill.construction_parameterization_resource_limits.v1"
                ),
            ) from exc
        except ConstructionBackendCapabilityUnavailable as exc:
            raise AdapterForgeHostCapabilityUnavailable(
                str(exc.reason_code),
                interface=interface,
                artifact_path=source.relative_path,
                resource_contract=(
                    "leanmill.construction_backend_runtime.v1"
                ),
            ) from exc
        except ValueError as exc:
            violation = _conformance_violation(
                code="construction_parameterization_contract_replay_failed",
                category="structural_contract",
                artifact_role="capability_source",
                artifact_path=source.relative_path,
                json_path="$",
                summary=str(exc)[:512],
                repair_scope="same_agent_new_bytes_permitted",
            )
            raise AdapterForgeHostConformanceRejected(
                str(exc),
                rejection_class=ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT,
                violations=(violation,),
            ) from exc

        def artifact(snapshot: _AdapterForgeStagedArtifact) -> dict[str, Any]:
            return {
                "path": snapshot.relative_path,
                "content_sha256": snapshot.content_sha256,
                "content": snapshot.text,
            }

        try:
            conformance = build_adapter_forge_construction_parameterization_conformance(
                parameterization,
                witness_interface=witness_interface,
                source_artifacts=[artifact(path) for path in sources],
                test_artifacts=[artifact(path) for path in tests],
                manifest_capability_source=declared_source,
                resolved_capability_source=source.relative_path,
            )
        except ConstructionResourceCeilingExceeded as exc:
            raise AdapterForgeHostCapabilityUnavailable(
                str(exc.reason_code),
                interface=interface,
                artifact_path=source.relative_path,
                observed=int(exc.observed),
                ceiling=int(exc.ceiling),
                resource_contract=(
                    "leanmill.construction_parameterization_resource_limits.v1"
                ),
            ) from exc
        except ConstructionBackendCapabilityUnavailable as exc:
            raise AdapterForgeHostCapabilityUnavailable(
                str(exc.reason_code),
                interface=interface,
                artifact_path=source.relative_path,
                resource_contract=(
                    "leanmill.construction_backend_runtime.v1"
                ),
            ) from exc
        write_json_atomic(
            Path(output_path).with_name(
                "theory_language_construction_parameterization_candidate.json"
            ),
            parameterization,
        )
        return conformance
    if interface == FINITE_CONSTRUCTION_FAMILY_SCHEMA:
        context_kind, snapshot, _context_artifact = (
            _read_staged_context_snapshot(
                root,
                interface=interface,
                budget=staged_read_budget,
            )
        )
        blueprint_artifact = _read_adapter_forge_staged_artifact(
            root,
            "blueprint.json",
            interface=interface,
            budget=staged_read_budget,
        )
        blueprint = (
            _parse_adapter_forge_json_bytes(
                blueprint_artifact.payload,
                context="AdapterForge staged blueprint",
            )
            if blueprint_artifact is not None
            else None
        )
        if not isinstance(blueprint, Mapping):
            raise ValueError("finite family requires the frozen blueprint")
        witness_interface = construction_witness_interface(
            str(blueprint.get("adapter_id") or ""),
            dict(blueprint.get("adapter_config") or {}),
        )
        candidate = _forge_json_text_ingress(
            "capability_source",
            source.text,
            interface=interface,
            source_ref=source.relative_path,
        )
        if not isinstance(candidate, Mapping):
            raise ValueError("finite construction family source must be one JSON object")
        violations = _finite_family_pre_review_violations(
            candidate,
            source_artifact=source,
            tests=tests,
            proposal=proposal,
            witness_interface=witness_interface,
        )
        if violations:
            contaminated = any(
                row["category"] == "epistemic_ordering" for row in violations
            )
            raise AdapterForgeHostConformanceRejected(
                (
                    "pre-review target-evaluation leakage contaminated the "
                    "family proposal"
                    if contaminated
                    else "finite-family proposal violates its structural contract"
                ),
                rejection_class=(
                    ADAPTER_FORGE_REJECTION_PRE_REVIEW_LEAKAGE
                    if contaminated
                    else ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT
                ),
                violations=violations,
            )
        try:
            family = validate_finite_construction_family(
                candidate,
                request_id=str(request.get("request_id") or ""),
                gap_id=gap.gap_id,
                context_hash=str(snapshot.get("context_hash") or ""),
                adapter_id=str(blueprint.get("adapter_id") or ""),
                witness_interface=witness_interface,
            )
        except ValueError as exc:
            violation = _conformance_violation(
                code="finite_family_interface_contract_replay_failed",
                category="structural_contract",
                artifact_role="capability_source",
                artifact_path=source.relative_path,
                json_path="$",
                summary=str(exc)[:512],
                repair_scope="same_agent_new_bytes_permitted",
            )
            raise AdapterForgeHostConformanceRejected(
                str(exc),
                rejection_class=ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT,
                violations=(violation,),
            ) from exc
        target = Path(output_path).with_name(
            "theory_language_finite_family_candidate.json"
        )
        write_json_atomic(target, family)

        def artifact(snapshot: _AdapterForgeStagedArtifact) -> dict[str, Any]:
            return {
                "path": snapshot.relative_path,
                "content_sha256": snapshot.content_sha256,
                "content": snapshot.text,
            }

        core = {
            "ok": True,
            "interface": FINITE_CONSTRUCTION_FAMILY_SCHEMA,
            "host_conformance_contract": ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
            "gap_id": gap.gap_id,
            "context_hash": str(snapshot.get("context_hash") or ""),
            "context_kind": (
                context_kind
            ),
            "adapter_id": str(blueprint.get("adapter_id") or ""),
            "family_id": str(family["family_id"]),
            "finite_family_receipt_sha256": str(family["receipt_sha256"]),
            "target_interface_sha256": str(family["target_interface_sha256"]),
            "declared_cardinality": int(family["declared_cardinality"]),
            "parameter_domain_sha256": str(family["parameter_domain_sha256"]),
            "unique_source_artifact_count": len(
                {str(row["artifact_sha256"]) for row in family["members"]}
            ),
            "family_spec": dict(family["family_spec"]),
            "symmetry_policy": dict(family["symmetry_policy"]),
            "source_artifacts": [artifact(path) for path in sources],
            "test_artifacts": [artifact(path) for path in tests],
            "manifest_capability_source": declared_source,
            "resolved_capability_source": source.relative_path,
            "outcomes_evaluated": False,
            "claim_boundary": (
                "family identity and exact finite domain validated before member "
                "outcomes; execution remains family-scoped and post-review"
            ),
        }
        return _bind_host_conformance_contract(
            {**core, "receipt_sha256": content_hash(core)},
            gap_id=gap.gap_id,
        )
    if interface == GENERATIVE_REPRESENTATION_INTERFACE:
        _context_kind, _snapshot, context = _load_staged_context_owner(
            root,
            interface=interface,
            budget=staged_read_budget,
        )
        candidate = _forge_json_text_ingress(
            "capability_source",
            source.text,
            interface=interface,
            source_ref=source.relative_path,
        )
        if not isinstance(candidate, Mapping):
            raise ValueError("generative representation source must be one JSON object")
        if (
            candidate.get("request_id") != request.get("request_id")
            or candidate.get("gap_id") != gap.gap_id
        ):
            raise ValueError("generative representation crossed its Forge request")
        conformance = _bind_host_conformance_contract(
            validate_materialized_generative_candidate(candidate, context),
            gap_id=gap.gap_id,
        )
        write_json_atomic(
            Path(output_path).with_name("theory_language_generative_candidate.json"),
            dict(candidate),
        )
        return conformance
    if source.path.suffix.lower() != ".json":
        raise AdapterForgeHostConformanceRejected(
            "object-coordinate capabilities must be inert JSON snapshots",
            rejection_class=ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT,
            violations=(
                _conformance_violation(
                    code="generated_code_execution_forbidden",
                    category="structural_contract",
                    artifact_role="capability_source",
                    artifact_path=source.relative_path,
                    json_path="$",
                    summary=(
                        "campaign-authored Python cannot become an executable "
                        "host capability"
                    ),
                    repair_scope="same_agent_data_only_reauthor_permitted",
                ),
            ),
        )
    context_kind, snapshot, context = _load_staged_context_owner(
        root,
        interface=interface,
        budget=staged_read_budget,
    )
    first_raw = _forge_json_text_ingress(
        "capability_source",
        source.text,
        interface=interface,
        source_ref=source.relative_path,
    )

    functor_image = None
    if isinstance(first_raw, Mapping) and set(first_raw) == {
        "coordinates", "functor_image"
    }:
        functor_image = first_raw["functor_image"]
        first_raw = first_raw["coordinates"]

    required_application = gap.primitive_semantics_contract.get(
        "required_application"
    )
    require_functor_image = False
    require_target_formula_grammar = False
    if required_application is not None:
        if (
            not isinstance(required_application, Mapping)
            or required_application.get("schema")
            != THEORY_LANGUAGE_REQUIRED_APPLICATION_SCHEMA
            or required_application.get("application_kind")
            != "finite_model_functor"
            or required_application.get("application_schema")
            not in {
                FINITE_MODEL_FUNCTOR_APPLICATION_SCHEMA,
                GRAMMAR_OWNING_FUNCTOR_APPLICATION_SCHEMA,
            }
            or not str(required_application.get("consumer") or "")
        ):
            raise ValueError(
                "capability gap has a malformed required application contract"
            )
        declared_context_kind = str(
            required_application.get("source_context_kind") or ""
        )
        if declared_context_kind and declared_context_kind != context_kind:
            raise ValueError(
                "required application crossed its source context category"
            )
        require_functor_image = True
        require_target_formula_grammar = (
            required_application.get("application_schema")
            == GRAMMAR_OWNING_FUNCTOR_APPLICATION_SCHEMA
        )
    else:
        # Compatibility for frozen gaps authored before the required-
        # application contract existed. The compiler's typed outcome already
        # selected this exact consumer, so replay may recover without changing
        # the historical gap identity.
        compiler_attempts = gap.primitive_semantics_contract.get(
            "compiler_attempts"
        )
        require_functor_image = any(
            isinstance(row, Mapping)
            and str(row.get("adapter_id") or "") == "generic_fol_finite.v1"
            and str(row.get("status") or "") == "unavailable"
            and str(row.get("reason") or "")
            == "approved_campaign_local_functor_application_required"
            for row in (
                compiler_attempts
                if isinstance(compiler_attempts, list)
                else ()
            )
        )
        require_target_formula_grammar = (
            require_functor_image and context_kind == "evidence_incidence"
        )
    if require_functor_image and functor_image is None:
        raise AdapterForgeHostConformanceRejected(
            "the compiler gap requires an executable finite-model functor image",
            rejection_class=ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT,
            violations=(
                _conformance_violation(
                    code="successor_functor_image_required",
                    category="structural_contract",
                    artifact_role="capability_source",
                    artifact_path=source.relative_path,
                    json_path="$",
                    summary=(
                        "coordinates alone have no executable successor "
                        "consumer for this frozen compiler gap"
                    ),
                    repair_scope="same_agent_data_only_reauthor_permitted",
                ),
            ),
        )

    first = _normalize_object_coordinates(
        first_raw,
        request_id=str(request["request_id"]),
    )

    if set(first) != set(context.object_ids):
        raise ValueError("capability coordinates do not cover the frozen objects exactly")
    image_receipt = None
    if functor_image is not None:
        image_fields = set(functor_image) if isinstance(functor_image, Mapping) else set()
        legacy_fields = {"functor_id", "signature", "models"}
        grammar_fields = {
            "functor_id",
            "signature",
            "formula_grammar",
            "models",
        }
        if image_fields != legacy_fields and image_fields != grammar_fields:
            raise ValueError("capability functor image has an unsupported envelope")
        from ztare.leanmill.finite_model import FiniteModel, validate_model
        from ztare.leanmill.theory_ir import TheorySignature

        signature = TheorySignature.from_json(functor_image["signature"])
        has_target_formula_grammar = "formula_grammar" in functor_image
        target_formula_grammar = functor_image.get("formula_grammar")
        if require_target_formula_grammar and not has_target_formula_grammar:
            raise AdapterForgeHostConformanceRejected(
                "the successor application requires a target formula grammar",
                rejection_class=ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT,
                violations=(
                    _conformance_violation(
                        code="successor_formula_grammar_required",
                        category="structural_contract",
                        artifact_role="capability_source",
                        artifact_path=source.relative_path,
                        json_path="$.functor_image",
                        summary=(
                            "the source context does not own an executable "
                            "target grammar; provide a v2 functor image"
                        ),
                        repair_scope="same_agent_data_only_reauthor_permitted",
                    ),
                ),
            )
        if has_target_formula_grammar:
            if not isinstance(target_formula_grammar, Mapping):
                raise ValueError(
                    "capability target formula grammar must be an object"
                )
            from ztare.leanmill.adapters.generic_fol_finite import build_formulas

            if not build_formulas(
                signature,
                adapter_config={},
                formula_grammar=target_formula_grammar,
            ):
                raise ValueError(
                    "capability target formula grammar produced no coordinates"
                )
        image_models = functor_image["models"]
        if (
            not isinstance(image_models, Mapping)
            or not image_models
            or set(image_models) != set(context.object_ids)
        ):
            raise ValueError(
                "capability functor image must cover every frozen source object exactly"
            )
        for row in image_models.values():
            validate_model(signature, FiniteModel.from_json(row))
        image_core = {
            "schema": (
                GRAMMAR_OWNING_FUNCTOR_APPLICATION_SCHEMA
                if has_target_formula_grammar
                else FINITE_MODEL_FUNCTOR_APPLICATION_SCHEMA
            ),
            "gap_id": gap.gap_id,
            "context_hash": context.context_hash,
            "context_kind": context_kind,
            "functor_id": str(functor_image["functor_id"]),
            "signature": signature.to_json(),
            "models": dict(image_models),
        }
        if has_target_formula_grammar:
            image_core["formula_grammar"] = dict(target_formula_grammar)
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
            for part in path:
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
    coordinate_cells = partition_by_prediction(
        context.object_ids, lambda object_id: canonical[object_id]
    )
    coordinate_class_count = len(coordinate_cells)
    if coordinate_class_count == len(context.object_ids):
        raise ValueError("capability observable is injective on the frozen objects")
    observable_bits = identification_bits(
        coordinate_cells, len(context.object_ids)
    )
    source_bits = math.log2(len(context.object_ids))
    if any(
        left not in canonical
        or right not in canonical
        or canonical[left] == canonical[right]
        for left, right in contrast_pairs
    ):
        raise ValueError("capability fails a frozen contrast pair")
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

    def artifact(snapshot: _AdapterForgeStagedArtifact) -> dict[str, Any]:
        return {
            "path": snapshot.relative_path,
            "content_sha256": snapshot.content_sha256,
            "content": snapshot.text,
        }

    core = {
        "ok": True,
        "interface": "leanmill.object_coordinates.v1",
        "host_conformance_contract": ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        "gap_id": gap.gap_id,
        "context_hash": context.context_hash,
        "context_kind": context_kind,
        "object_count": len(context.object_ids),
        "split_indistinguishability_class_count": split_classes,
        "separated_indistinguishable_pair_count": split_pairs,
        "required_contrast_pair_count": len(contrast_pairs),
        "separated_required_contrast_pair_count": len(contrast_pairs),
        "coordinate_class_count": coordinate_class_count,
        "coordinate_class_ratio": round(
            coordinate_class_count / len(context.object_ids), 8
        ),
        "observable_identity_bits": round(observable_bits, 8),
        "source_identity_bits": round(source_bits, 8),
        "retained_identity_fraction": round(observable_bits / source_bits, 8),
        "compression_bits": round(source_bits - observable_bits, 8),
        "coordinate_receipt_sha256": payload["receipt_sha256"],
        "observable_paths": [".".join(path) for path in observable_paths],
        "declared_observable_paths": list(declared_observable_paths),
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
        "resolved_capability_source": source.relative_path,
        "claim_boundary": "semantic delta measured only on the frozen finite context",
    }
    return _bind_host_conformance_contract(
        {**core, "receipt_sha256": content_hash(core)},
        gap_id=gap.gap_id,
    )


# Compatibility door for callers predating the generative data interface.
host_coordinate_conformance = host_capability_conformance


def validate_adapter_forge_review(review: Any) -> dict[str, Any]:
    try:
        frozen = _forge_data_ingress("review", review)
    except (TypeError, ValueError) as exc:
        raise ValueError("AdapterForge independent review is malformed") from exc
    row = frozen if isinstance(frozen, dict) else {}
    refs = row.get("evidence_refs")
    if (
        set(row) != {"accepted", "reviewer_ref", "rationale", "evidence_refs"}
        or type(row.get("accepted")) is not bool
        or not isinstance(row.get("reviewer_ref"), str)
        or not row["reviewer_ref"].strip()
        or len(row["reviewer_ref"]) > 512
        or not isinstance(row.get("rationale"), str)
        or not row["rationale"].strip()
        or len(row["rationale"]) > 4_096
        or not isinstance(refs, list)
        or not refs
        or len(refs) > _MAX_ADAPTER_FORGE_REVIEW_REFS
        or len(refs) != len(set(refs))
        or any(
            not isinstance(ref, str)
            or re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", ref) is None
            for ref in refs
        )
    ):
        raise ValueError("AdapterForge independent review is malformed")
    return row


def bind_adapter_review_evidence(
    review: Any, host_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    """Bind a review to the exact host receipt graph it adjudicates."""

    review = validate_adapter_forge_review(review)
    cited = set()
    for row in review.get("evidence_refs") or ():
        cited.update(extract_sha256_refs(row))
    root = canonical_sha256_ref(host_receipt.get("receipt_sha256"))
    descendants = {
        canonical_sha256_ref(value)
        for key, value in host_receipt.items()
        if str(key).endswith("receipt_sha256") and isinstance(value, str) and value
    }
    admissible = {root} if review["accepted"] is True else descendants
    matched = sorted(cited.intersection(admissible))
    if not root or not matched:
        raise ValueError(
            "AdapterForge review cites no admissible host receipt "
            f"(accepted={review['accepted']}, cited={sorted(cited)}, "
            f"admissible={sorted(admissible)})"
        )
    core = {
        "schema": "leanmill.review_evidence_binding.v1",
        "policy": (
            "current_host_envelope"
            if review["accepted"] is True
            else "current_host_receipt_graph"
        ),
        "host_receipt": root,
        "matched_refs": matched,
    }
    return {**core, "receipt_sha256": content_hash(core)}


def validate_reviewed_construction_parameterization_bytes_authority(
    parameterization: Mapping[str, Any],
    forge_quarantine_receipt: Mapping[str, Any],
    *,
    witness_interface: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Replay only the inert Forge graph and content identities.

    This cold reader does not invoke a construction backend or materialize a
    parameter assignment.  Semantic admission is an explicit later operation.
    """

    frozen = validate_construction_parameterization(parameterization)
    interface = validate_witness_construction_interface(witness_interface)
    receipt = dict(forge_quarantine_receipt)
    required = {
        "schema", "gap_id", "proposed_adapter_id", "proposal_digest",
        "host_conformance", "independent_review", "review_evidence_binding",
        "status", "live_registry_mutated", "exactness_authority_granted",
        "next_step", "receipt_sha256",
    }
    core = {
        key: item for key, item in receipt.items() if key != "receipt_sha256"
    }
    host = receipt.get("host_conformance")
    review = receipt.get("independent_review")
    binding = receipt.get("review_evidence_binding")
    if (
        set(receipt) != required
        or receipt.get("schema")
        != "leanmill.adapter_forge_quarantine_receipt.v1"
        or receipt.get("receipt_sha256") != content_hash(core)
        or receipt.get("gap_id") != frozen["gap_id"]
        or receipt.get("proposed_adapter_id") != frozen["adapter_id"]
        or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("proposal_digest") or ""))
        or receipt.get("status") != "quarantined_registry_proposal"
        or receipt.get("live_registry_mutated") is not False
        or receipt.get("exactness_authority_granted") is not False
        or receipt.get("next_step")
        != "execute_reviewed_construction_parameterization"
        or not isinstance(host, Mapping)
        or not isinstance(review, Mapping)
        or not isinstance(binding, Mapping)
        or review.get("accepted") is not True
    ):
        raise ValueError(
            "construction parameterization lacks accepted AdapterForge authority"
        )
    host_core = {
        key: item for key, item in host.items() if key != "receipt_sha256"
    }
    host_required = {
        "ok", "interface", "host_conformance_contract", "campaign_id",
        "request_id", "gap_id", "context_hash", "context_epoch",
        "adapter_id", "target_interface_sha256",
        "construction_parameterization_id",
        "construction_parameterization_receipt_sha256",
        "backend_problem_sha256", "backend_sha256",
        "parameter_space_sha256", "materializer_sha256",
        "resource_limits_sha256", "search_order_sha256",
        "semantic_admission_deferred", "outcomes_evaluated",
        "generated_code_imported", "registry_mutated", "source_artifacts",
        "test_artifacts", "manifest_capability_source",
        "resolved_capability_source", "authority", "claim_boundary",
        "receipt_sha256",
    }
    if (
        set(host) != host_required
        or
        host.get("receipt_sha256") != content_hash(host_core)
        or host.get("ok") is not True
        or host.get("interface") != CONSTRUCTION_PARAMETERIZATION_SCHEMA
        or host.get("host_conformance_contract")
        != ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT
    ):
        raise ValueError("construction AdapterForge host receipt is malformed")
    if (
        host.get("campaign_id") != frozen["campaign_id"]
        or host.get("request_id") != frozen["request_id"]
        or host.get("gap_id") != frozen["gap_id"]
        or host.get("context_hash") != frozen["context_hash"]
        or host.get("context_epoch") != frozen["context_epoch"]
        or host.get("adapter_id") != frozen["adapter_id"]
        or host.get("target_interface_sha256")
        != frozen["target_interface_sha256"]
        or host.get("construction_parameterization_id")
        != frozen["parameterization_id"]
        or host.get("construction_parameterization_receipt_sha256")
        != frozen["receipt_sha256"]
        or host.get("backend_problem_sha256")
        != content_hash(frozen["backend_problem"])
        or host.get("backend_sha256") != content_hash(frozen["backend"])
        or host.get("parameter_space_sha256")
        != content_hash(frozen["parameter_space"])
        or host.get("materializer_sha256")
        != content_hash(frozen["materializer"])
        or host.get("resource_limits_sha256")
        != content_hash(frozen["resource_limits"])
        or host.get("search_order_sha256")
        != content_hash(frozen["search_order"])
        or host.get("semantic_admission_deferred") is not True
        or host.get("outcomes_evaluated") is not False
        or host.get("generated_code_imported") is not False
        or host.get("registry_mutated") is not False
        or host.get("authority")
        != "deterministic_adapter_forge_host_conformance"
        or host.get("claim_boundary")
        != (
            "static_registered_backend_template_interface_and_limit_bytes_"
            "only_semantic_admission_and_outcomes_deferred"
        )
    ):
        raise ValueError("construction AdapterForge host identity does not join")
    source_artifacts = host.get("source_artifacts")
    test_artifacts = host.get("test_artifacts")
    if type(source_artifacts) is not list or type(test_artifacts) is not list:
        raise ValueError("construction AdapterForge artifacts are malformed")
    (
        frozen_sources,
        frozen_tests,
        manifest_source,
        resolved_source,
    ) = _validated_construction_artifact_receipts(
        source_artifacts,
        test_artifacts,
        manifest_capability_source=host.get("manifest_capability_source"),
        resolved_capability_source=host.get("resolved_capability_source"),
    )
    if (
        source_artifacts != frozen_sources
        or test_artifacts != frozen_tests
        or host.get("manifest_capability_source") != manifest_source
        or host.get("resolved_capability_source") != resolved_source
    ):
        raise ValueError("construction AdapterForge artifact graph changed identity")
    review = validate_adapter_forge_review(review)
    expected_binding = bind_adapter_review_evidence(review, host)
    if dict(binding) != expected_binding:
        raise ValueError(
            "construction AdapterForge review binding does not replay"
        )
    return frozen, receipt


def validate_reviewed_construction_parameterization_authority(
    parameterization: Mapping[str, Any],
    forge_quarantine_receipt: Mapping[str, Any],
    *,
    witness_interface: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compatibility name for structural Forge authority validation."""

    return validate_reviewed_construction_parameterization_bytes_authority(
        parameterization,
        forge_quarantine_receipt,
        witness_interface=witness_interface,
    )


def admit_reviewed_construction_parameterization_authority(
    parameterization: Mapping[str, Any],
    forge_quarantine_receipt: Mapping[str, Any],
    *,
    witness_interface: Mapping[str, Any],
):
    """Explicitly admit backend semantics after inert Forge graph validation."""

    frozen, receipt = (
        validate_reviewed_construction_parameterization_bytes_authority(
            parameterization,
            forge_quarantine_receipt,
            witness_interface=witness_interface,
        )
    )
    interface = validate_witness_construction_interface(witness_interface)
    admitted = admit_construction_parameterization(frozen)
    host = receipt["host_conformance"]
    expected_host = build_adapter_forge_construction_parameterization_conformance(
        admitted,
        witness_interface=interface,
        source_artifacts=host["source_artifacts"],
        test_artifacts=host["test_artifacts"],
        manifest_capability_source=str(host["manifest_capability_source"]),
        resolved_capability_source=str(host["resolved_capability_source"]),
    )
    if dict(host) != expected_host:
        raise ValueError(
            "construction AdapterForge semantic host receipt does not replay"
        )
    return admitted, receipt


def _host_rejection_receipt(
    *,
    gap: AdapterGap,
    proposal: Mapping[str, Any],
    error: ValueError,
    proposal_digest: str | None = None,
) -> dict[str, Any]:
    manifest = proposal.get("manifest")
    interface = (
        str(manifest.get("interface") or "")
        if isinstance(manifest, Mapping)
        else ""
    )
    host_contract = (
        ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT
        if interface == CONSTRUCTION_PARAMETERIZATION_SCHEMA
        else ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT
    )
    if isinstance(error, AdapterForgeHostConformanceRejected):
        rejection_class = error.rejection_class
        violations = [dict(row) for row in error.violations]
    else:
        reason = str(error).lower()
        structural_markers = (
            " field",
            "schema",
            "digest",
            "must be string",
            "must be an object",
            "manifest",
            "non-staged file",
            "do not cover",
            "does not bind",
            "crossed ",
        )
        structural = any(marker in reason for marker in structural_markers)
        rejection_class = (
            ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT
            if structural
            else ADAPTER_FORGE_REJECTION_UNCLASSIFIED
        )
        violations = [
            _conformance_violation(
                code=(
                    "host_interface_contract_replay_failed"
                    if structural
                    else "host_conformance_exception"
                ),
                category=(
                    "structural_contract"
                    if structural
                    else "unclassified_host_failure"
                ),
                artifact_role="proposal",
                artifact_path="",
                json_path="$",
                summary=str(error)[:512],
                repair_scope=(
                    "same_agent_new_bytes_permitted"
                    if structural
                    else "return_to_search_for_fresh_disposition"
                ),
            )
        ]
    if rejection_class == ADAPTER_FORGE_REJECTION_PRE_REVIEW_LEAKAGE:
        same_agent_repair_allowed = False
        workspace_reuse_allowed = False
        required_agent_identity = "fresh_cold_adapter_forge_leaf"
        recovery_route = (
            "reauthor_in_fresh_cold_workspace_with_new_agent_identity"
        )
    elif rejection_class == ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT:
        same_agent_repair_allowed = True
        workspace_reuse_allowed = True
        required_agent_identity = "same_adapter_forge_leaf_permitted"
        recovery_route = "return_typed_structural_repair_to_campaign"
    else:
        same_agent_repair_allowed = False
        workspace_reuse_allowed = False
        required_agent_identity = "fresh_campaign_disposition_required"
        recovery_route = "return_rejection_to_theory_search"
    core = {
        "schema": "leanmill.adapter_forge_host_rejection.v2",
        "gap_id": gap.gap_id,
        "interface": interface or "host_conformance",
        "host_conformance_contract": host_contract,
        "proposal_digest": str(
            proposal_digest or content_hash(dict(proposal))
        ),
        "ok": False,
        "error_type": type(error).__name__,
        "reason": str(error)[:512],
        "rejection_class": rejection_class,
        "violations": violations,
        "same_agent_repair_allowed": same_agent_repair_allowed,
        "workspace_reuse_allowed": workspace_reuse_allowed,
        "automatic_retry_performed": False,
        "required_agent_identity": required_agent_identity,
        "recovery_route": recovery_route,
        "authority": "deterministic_host_conformance",
        "claim_boundary": (
            "the quarantined proposal failed host conformance and grants no "
            "capability, registry, exactness, or campaign authority"
        ),
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _host_unavailability_receipt(
    *,
    gap: AdapterGap,
    proposal: Mapping[str, Any],
    error: AdapterForgeHostCapabilityUnavailable,
    proposal_digest: str | None = None,
) -> dict[str, Any]:
    """Project host resource exhaustion into the non-semantic outcome lane."""

    expected_contract = (
        ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT
        if error.interface == CONSTRUCTION_PARAMETERIZATION_SCHEMA
        else ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT
    )
    core = {
        "schema": "leanmill.adapter_forge_host_unavailable.v1",
        "gap_id": gap.gap_id,
        "interface": error.interface,
        "host_conformance_contract": expected_contract,
        "proposal_digest": str(
            proposal_digest or content_hash(dict(proposal))
        ),
        "ok": False,
        "outcome": "unavailable",
        "reason_code": error.reason_code,
        "artifact_path": error.artifact_path,
        "observed": error.observed,
        "ceiling": error.ceiling,
        "resource_contract": error.resource_contract,
        "automatic_retry_performed": False,
        "recovery_route": "return_unavailable_to_theory_search",
        "authority": "deterministic_adapter_forge_host_resources",
        "claim_boundary": (
            "host resources prevented conformance replay; the proposal was not "
            "semantically accepted or rejected"
        ),
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _review_unavailability_receipt(
    *, host_receipt: Mapping[str, Any], error: Exception
) -> dict[str, Any]:
    core = {
        "schema": "leanmill.adapter_forge_review_unavailable.v1",
        "accepted": False,
        "outcome": "unavailable",
        "reason_code": "independent_review_capability_unavailable",
        "error_type": type(error).__name__,
        "reason": str(error)[:512],
        "host_receipt_sha256": str(host_receipt.get("receipt_sha256") or ""),
        "authority": "adapter_forge_review_lifecycle",
        "claim_boundary": (
            "the independent review contract was unavailable; no semantic "
            "acceptance or rejection was granted"
        ),
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
    coding_error: Exception | None = None
    proposal: Mapping[str, Any] = {}
    try:
        proposal = coding_agent_fn(render_adapter_forge_prompt(gap))
    except Exception as exc:
        coding_error = exc
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
    proposal_resource_error = None
    proposal_contract_error = None
    if isinstance(coding_error, (TypeError, ValueError)):
        proposal_contract_error = coding_error
    elif coding_error is not None:
        proposal_resource_error = AdapterForgeHostCapabilityUnavailable(
            "adapter_forge_coding_agent_runtime_unavailable",
            interface="coding_agent",
            resource_contract="leanmill.adapter_forge_coding_agent_runtime.v1",
        )
    if proposal_resource_error is None:
        if proposal_contract_error is None:
            try:
                proposal = _validate_adapter_forge_proposal(proposal)
            except AdapterForgeHostCapabilityUnavailable as exc:
                proposal_resource_error = exc
            except (TypeError, ValueError) as exc:
                proposal_contract_error = exc
    proposal_digest = (
        content_hash(
            {
                "unavailable_proposal_envelope": {
                    "reason_code": proposal_resource_error.reason_code,
                    "interface": proposal_resource_error.interface,
                    "ceiling": proposal_resource_error.ceiling,
                }
            }
        )
        if proposal_resource_error is not None
        else content_hash(
            {
                "rejected_proposal_envelope": {
                    "error_type": type(proposal_contract_error).__name__,
                    "reason": str(proposal_contract_error)[:512],
                }
            }
        )
        if proposal_contract_error is not None
        else content_hash(dict(proposal))
    )
    if proposal_resource_error is not None:
        conformance = _host_unavailability_receipt(
            gap=gap,
            proposal=proposal,
            error=proposal_resource_error,
            proposal_digest=proposal_digest,
        )
    elif proposal_contract_error is not None:
        conformance = _host_rejection_receipt(
            gap=gap,
            proposal={},
            error=ValueError(str(proposal_contract_error)),
            proposal_digest=proposal_digest,
        )
    else:
        if proposal.get("registry_mutation"):
            conformance = _host_rejection_receipt(
                gap=gap,
                proposal=proposal,
                error=ValueError("AdapterForge may not mutate the live registry"),
                proposal_digest=proposal_digest,
            )
        else:
            try:
                conformance = host_conformance_fn(proposal, gap)
            except AdapterForgeHostCapabilityUnavailable as exc:
                conformance = _host_unavailability_receipt(
                    gap=gap,
                    proposal=proposal,
                    error=exc,
                    proposal_digest=proposal_digest,
                )
            except ValueError as exc:
                conformance = _host_rejection_receipt(
                    gap=gap, proposal=proposal, error=exc
                )
            except Exception as exc:
                manifest = proposal.get("manifest")
                interface = (
                    str(manifest.get("interface") or "")
                    if isinstance(manifest, Mapping)
                    else ""
                )
                conformance = _host_unavailability_receipt(
                    gap=gap,
                    proposal=proposal,
                    error=AdapterForgeHostCapabilityUnavailable(
                        "adapter_forge_host_runtime_unavailable",
                        interface=interface or "host_conformance",
                        resource_contract=(
                            "leanmill.adapter_forge_host_runtime.v1"
                        ),
                    ),
                    proposal_digest=proposal_digest,
                )
    if not isinstance(conformance, Mapping):
        raise TypeError("AdapterForge host conformance returned no receipt")
    conformance = _bind_host_conformance_contract(
        conformance,
        gap_id=gap.gap_id,
    )
    if conformance.get("ok") is not True:
        rejection = dict(conformance)
        rejection_core = {
            key: value for key, value in rejection.items() if key != "receipt_sha256"
        }
        if rejection.get("receipt_sha256") != content_hash(rejection_core):
            raise ValueError("AdapterForge host rejection is not content-bound")
        unavailable = rejection.get("outcome") == "unavailable"
        skipped_review = {
            "schema": "leanmill.adapter_forge_review_skipped.v1",
            "accepted": False,
            "rationale": (
                "host resources were unavailable before review"
                if unavailable
                else "host conformance rejected the proposal before review"
            ),
            "host_rejection_receipt_sha256": str(rejection["receipt_sha256"]),
            "authority": "host_lifecycle",
        }
        core = {
            "schema": "leanmill.adapter_forge_quarantine_receipt.v1",
            "gap_id": gap.gap_id,
            "proposed_adapter_id": gap.proposed_adapter_id,
            "proposal_digest": proposal_digest,
            "host_conformance": rejection,
            "independent_review": skipped_review,
            "review_evidence_binding": None,
            "status": (
                "quarantined_capability_unavailable"
                if unavailable
                else "quarantined_capability_rejected"
            ),
            "live_registry_mutated": False,
            "exactness_authority_granted": False,
            "next_step": str(
                rejection.get("recovery_route")
                or (
                    "return_unavailable_to_theory_search"
                    if unavailable
                    else "return_rejection_to_theory_search"
                )
            ),
        }
        return {**core, "receipt_sha256": content_hash(core)}
    effective_review_fn = independent_review_fn
    recover_for_host = getattr(
        independent_review_fn, "recover_for_host_receipt", None
    )
    if callable(recover_for_host):
        recovered = recover_for_host(conformance)
        if recovered is not None:
            if not isinstance(recovered, Mapping):
                raise ValueError("AdapterForge recovered review is malformed")

            def replay_review(_packet: Mapping[str, Any]) -> Mapping[str, Any]:
                return dict(recovered)

            replay_review.provider_call_count = 0  # type: ignore[attr-defined]
            replay_review.recovered_review = True  # type: ignore[attr-defined]
            effective_review_fn = replay_review
    review_reservation = None
    if budget_ledger is not None and not getattr(
        effective_review_fn, "recovered_review", False
    ):
        review_reservation = budget_ledger.reserve(
            f"adapter_forge:{gap.gap_id}:review",
            "expansion",
            {"provider_calls": 1, "agent_turns": 1},
        )
    review_before = provider_calls(effective_review_fn)
    review_error: Exception | None = None
    review: Mapping[str, Any] | None = None
    try:
        review = effective_review_fn(
            {"gap": gap.to_json(), "proposal": dict(proposal), "host_conformance": dict(conformance)}
        )
    except Exception as exc:
        review_error = exc
    finally:
        if review_reservation is not None:
            review_after = provider_calls(effective_review_fn)
            used = (
                max(0, min(1, review_after - review_before))
                if review_before is not None and review_after is not None
                else 1
            )
            budget_ledger.commit(
                review_reservation,
                {"provider_calls": used, "agent_turns": used},
            )
    if review_error is None:
        try:
            review = validate_adapter_forge_review(review)
            review_binding = bind_adapter_review_evidence(review, conformance)
        except (
            TypeError,
            ValueError,
            AdapterForgeHostCapabilityUnavailable,
        ) as exc:
            review_error = exc
    if review_error is not None:
        unavailable_review = _review_unavailability_receipt(
            host_receipt=conformance,
            error=review_error,
        )
        core = {
            "schema": "leanmill.adapter_forge_quarantine_receipt.v1",
            "gap_id": gap.gap_id,
            "proposed_adapter_id": gap.proposed_adapter_id,
            "proposal_digest": proposal_digest,
            "host_conformance": dict(conformance),
            "independent_review": unavailable_review,
            "review_evidence_binding": None,
            "status": "quarantined_capability_unavailable",
            "live_registry_mutated": False,
            "exactness_authority_granted": False,
            "next_step": "return_unavailable_to_theory_search",
        }
        return {**core, "receipt_sha256": content_hash(core)}
    if not isinstance(review, Mapping):
        raise ValueError("AdapterForge validated review is malformed")
    accepted = review["accepted"] is True
    campaign_local_image = bool(
        conformance.get("functor_image_receipt_sha256")
        or conformance.get("candidate_receipt_sha256")
    )
    finite_family = bool(conformance.get("finite_family_receipt_sha256"))
    construction_parameterization = bool(
        conformance.get("construction_parameterization_receipt_sha256")
    )
    core = {
        "schema": "leanmill.adapter_forge_quarantine_receipt.v1",
        "gap_id": gap.gap_id,
        "proposed_adapter_id": gap.proposed_adapter_id,
        "proposal_digest": proposal_digest,
        "host_conformance": dict(conformance),
        "independent_review": dict(review),
        "review_evidence_binding": review_binding,
        "status": (
            "quarantined_registry_proposal"
            if accepted
            else "quarantined_capability_rejected"
        ),
        "live_registry_mutated": False,
        "exactness_authority_granted": False,
        "next_step": (
            "execute_reviewed_construction_parameterization"
            if accepted and construction_parameterization
            else "execute_reviewed_finite_construction_family"
            if accepted and finite_family
            else "compile_campaign_local_functor_image_successor"
            if accepted and campaign_local_image
            else "code_review_and_registry_authority_then_new_blueprint_attempt"
            if accepted
            else "return_rejection_to_theory_search"
        ),
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
    run_row = read_json(directory / "run.json", None)
    gap_row = read_json(directory / "adapter_gap.json", None)
    budget_row = read_json(directory / "budget.json", None)
    if not all(isinstance(row, dict) and row for row in (run_row, gap_row, budget_row)):
        raise ValueError("AdapterForge requires a blocked campaign with a typed gap")
    if run_row.get("status") != "blocked_adapter_gap":
        raise ValueError("campaign is not blocked on an adapter gap")
    from ztare.leanmill.exploration_budget import ExplorationBudget, ExplorationBudgetLedger

    gap = AdapterGap.from_json(gap_row)
    existing = read_adapter_forge_completion(
        directory, gap, migrate_legacy=True
    )
    if existing is not None:
        return existing
    budget = ExplorationBudget.from_json(budget_row)
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        budget,
        attempt_id=directory.name,
    )
    ledger.recover_interrupted_wall_clock()
    ledger.recover_interrupted_reservations()
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
    host_row = receipt.get("host_conformance") or {}
    review_row = receipt.get("independent_review") or {}
    active_host_contract = str(
        host_row.get("host_conformance_contract")
        if isinstance(host_row, Mapping)
        else ""
    )
    if active_host_contract not in {
        ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT,
    }:
        raise ValueError("AdapterForge receipt lacks its active host contract")
    owner = adapter_forge_attempt_directory(
        directory,
        gap.gap_id,
        host_conformance_contract=active_host_contract,
        create=True,
    )
    receipt = _adapter_forge_quarantine_projection(
        receipt,
        gap_id=gap.gap_id,
        host_conformance_contract=active_host_contract,
    )
    _persist_adapter_forge_exact(
        owner / "adapter_forge_receipt.json",
        receipt,
        context="AdapterForge quarantine receipt",
    )
    host_unavailable = bool(
        isinstance(host_row, Mapping)
        and host_row.get("ok") is False
        and host_row.get("outcome") == "unavailable"
    )
    if host_unavailable:
        completion_reason = "host_capability_unavailable:" + str(
            host_row.get("reason_code") or "unspecified_host_resource"
        )
    elif isinstance(host_row, Mapping) and host_row.get("ok") is False:
        completion_reason = "host_conformance_rejected:" + str(
            host_row.get("reason") or "unspecified_host_rejection"
        )
    elif (
        isinstance(review_row, Mapping)
        and review_row.get("outcome") == "unavailable"
    ):
        completion_reason = "independent_review_capability_unavailable:" + str(
            review_row.get("reason_code") or "unspecified_review_failure"
        )
    elif isinstance(review_row, Mapping) and review_row.get("accepted") is False:
        completion_reason = "independent_review_rejected:" + str(
            review_row.get("rationale") or "unspecified_review_rejection"
        )
    else:
        completion_reason = str(
            (review_row.get("rationale") if isinstance(review_row, Mapping) else "")
            or receipt.get("status")
            or ""
        )
    core = {
        "schema": "leanmill.adapter_forge_completion.v1",
        "status": (
            "unavailable"
            if receipt["status"] == "quarantined_capability_unavailable"
            else "reviewed_campaign_local_construction_parameterization_available"
            if receipt["status"] == "quarantined_registry_proposal"
            and receipt.get("next_step")
            == "execute_reviewed_construction_parameterization"
            else "reviewed_campaign_local_finite_family_available"
            if receipt["status"] == "quarantined_registry_proposal"
            and receipt.get("next_step")
            == "execute_reviewed_finite_construction_family"
            else "reviewed_campaign_local_functor_image_available"
            if receipt["status"] == "quarantined_registry_proposal"
            and receipt.get("next_step")
            == "compile_campaign_local_functor_image_successor"
            else "quarantined_adapter_proposal_requires_authority_and_new_attempt"
            if receipt["status"] == "quarantined_registry_proposal"
            else "adapter_proposal_rejected_return_to_search"
        ),
        "attempt_dir": str(directory),
        "gap_id": gap.gap_id,
        "host_conformance_contract": active_host_contract,
        "quarantine_receipt": receipt,
        "reason": completion_reason,
        "rejection_class": (
            str(host_row.get("rejection_class") or "")
            if isinstance(host_row, Mapping) and host_row.get("ok") is False
            else ""
        ),
        "recovery_route": (
            str(receipt.get("next_step") or "")
            if receipt["status"] in {
                "quarantined_capability_rejected",
                "quarantined_capability_unavailable",
            }
            else ""
        ),
        "evidence_refs": [str(receipt["receipt_sha256"])],
        "provider_calls": int(ledger.state()["usage"]["provider_calls"])
        + int(run_row.get("preparation_provider_calls", 0)),
    }
    completion = {**core, "completion_sha256": content_hash(core)}
    completion = _validated_adapter_forge_completion(
        completion,
        gap_id=gap.gap_id,
        host_conformance_contract=active_host_contract,
    )
    _persist_adapter_forge_exact(
        owner / "adapter_forge_completion.json",
        completion,
        context="AdapterForge completion",
    )
    return completion


def read_scoped_adapter_forge_completion(
    attempt_dir: str | Path,
    *,
    gap_id: str,
    host_conformance_contract: str,
    quarantine_receipt_sha256: str | None = None,
    _read_budget: _AdapterForgeReadBudget | None = None,
) -> dict[str, Any] | None:
    """Read one canonical gap/contract completion without reconstructing a gap.

    This cold-path reader is deliberately O(1): it addresses the immutable
    owner directly, validates the complete quarantine graph, and optionally
    binds the exact quarantine receipt already frozen by a campaign transition.
    It never searches sibling or legacy namespaces.
    """

    owner = adapter_forge_attempt_directory(
        attempt_dir,
        gap_id,
        host_conformance_contract=host_conformance_contract,
    )
    path = owner / "adapter_forge_completion.json"
    value = _read_adapter_forge_json(
        path,
        context="AdapterForge scoped completion",
        budget=_read_budget,
    )
    if value is None and not os.path.lexists(path):
        return None
    if not isinstance(value, Mapping):
        raise ValueError("AdapterForge scoped completion slot is malformed")
    completion = _validated_adapter_forge_completion(
        value,
        gap_id=gap_id,
        host_conformance_contract=host_conformance_contract,
    )
    if quarantine_receipt_sha256 is not None:
        expected = str(quarantine_receipt_sha256)
        receipt = completion["quarantine_receipt"]
        if receipt.get("receipt_sha256") != expected:
            raise ValueError(
                "AdapterForge scoped completion crossed frozen receipt identity"
            )
    return completion


__all__ = [
    "ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT",
    "ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT",
    "ADAPTER_FORGE_REJECTION_PRE_REVIEW_LEAKAGE",
    "ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT",
    "ADAPTER_FORGE_REJECTION_UNCLASSIFIED",
    "AdapterGap", "AdapterGapRequired", "adapter_forge_attempt_directory",
    "AdapterForgeHostConformanceRejected",
    "adapter_forge_gap_directory",
    "adapter_forge_agent_output_schema",
    "adapter_forge_output_schema",
    "adapter_review_output_schema", "bind_adapter_review_evidence",
    "build_adapter_forge_construction_parameterization_conformance",
    "execute_adapter_forge_attempt",
    "host_capability_conformance", "host_coordinate_conformance",
    "read_adapter_forge_completion", "read_scoped_adapter_forge_completion",
    "render_adapter_forge_prompt",
    "run_adapter_forge", "stage_adapter_forge_workspace",
    "validate_adapter_forge_review",
    "admit_reviewed_construction_parameterization_authority",
    "validate_reviewed_construction_parameterization_authority",
    "validate_reviewed_construction_parameterization_bytes_authority",
]
