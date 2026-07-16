"""Typed observation charts, pointwise transport, and evidence-epoch pins.

There are three different objects here; keeping them separate prevents a
presentation repair from being mistaken for a scientific-law refinement.

``ObservationChart``
    Identity of one coordinate presentation of an observation packet.

``ChartTransportMorphism``
    A declarative, row-local map between charts.  It contains no Python
    callable supplied by a leaf.  Registered operations receive only the value
    at one packet path plus frozen JSON parameters.  The certificate also runs
    order/repetition metamorphisms, so a stateful registry implementation fails.

``EvidenceEpochSnapshot``
    Content identity of the evidence visible to one governed search round.
    A run pins this value; changing a chart, sidecar, or episode is a migration
    between rounds, never an in-round mutation of the leaf's data manifold.

Within-epoch symmetries remain in :mod:`ztare.common.equivariance`.  Cross-epoch
object genesis/annihilation remain in ``worldmodel.transition_identity``.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
import inspect
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Mapping, Sequence

from ztare.common.equivariance import stable_sha256


def _json_payload(value: Any) -> Any:
    """Return a deterministic JSON carrier or fail on process-local objects."""
    if isinstance(value, Mapping):
        return {
            str(key): _json_payload(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_json_payload(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "to_dict"):
        return _json_payload(value.to_dict())
    raise TypeError(
        f"observation-chart payloads must be JSON-stable, got {type(value).__qualname__}"
    )


def _frozen_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    payload = _json_payload(parameters)
    if not isinstance(payload, dict):  # pragma: no cover - Mapping guarantees it
        raise TypeError("operation parameters must be an object")
    return payload


@dataclass(frozen=True)
class ObservationChart:
    """Versioned coordinate presentation owned by a collector or adapter."""

    chart_id: str
    chart_version: str
    packet_schema_id: str
    coordinate_axes: tuple[str, ...]
    authority: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    schema: str = "ztare-observation-chart-v1"

    def __post_init__(self) -> None:
        for label, value in (
            ("chart_id", self.chart_id),
            ("chart_version", self.chart_version),
            ("packet_schema_id", self.packet_schema_id),
            ("authority", self.authority),
        ):
            if not str(value).strip():
                raise ValueError(f"{label} is required")
        if not self.coordinate_axes or len(set(self.coordinate_axes)) != len(
            self.coordinate_axes
        ):
            raise ValueError("coordinate_axes must be non-empty and unique")
        _frozen_parameters(self.parameters)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "chart_id": self.chart_id,
            "chart_version": self.chart_version,
            "packet_schema_id": self.packet_schema_id,
            "coordinate_axes": list(self.coordinate_axes),
            "authority": self.authority,
            "parameters": _frozen_parameters(self.parameters),
        }

    @property
    def sha256(self) -> str:
        return stable_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObservationChart":
        if payload.get("schema") not in (None, "ztare-observation-chart-v1"):
            raise ValueError("unsupported observation chart schema")
        axes = payload.get("coordinate_axes")
        if not isinstance(axes, list):
            raise ValueError("coordinate_axes must be a list")
        parameters = payload.get("parameters") or {}
        if not isinstance(parameters, Mapping):
            raise ValueError("chart parameters must be an object")
        return cls(
            chart_id=str(payload.get("chart_id") or ""),
            chart_version=str(payload.get("chart_version") or ""),
            packet_schema_id=str(payload.get("packet_schema_id") or ""),
            coordinate_axes=tuple(str(axis) for axis in axes),
            authority=str(payload.get("authority") or ""),
            parameters=dict(parameters),
        )


@dataclass(frozen=True)
class CounterexampleObservationTriple:
    """Chart-bound identity of a refuting observation.

    Adapters may localize each object before constructing the triple, but the
    localization is then part of ``chart`` identity.  Downstream consumers see
    the same source/proposal/consequence contract for text spans, graphs,
    arrays, volumes, interactive states, or another JSON-stable substrate.
    """

    chart: ObservationChart
    evidence_epoch_sha256: str
    evidence_ref: str
    observation_ref: str
    proposal_identity: Mapping[str, Any]
    intervention: Any
    source_observation: Any
    proposed_consequence: Any
    observed_consequence: Any
    transition_identity: Mapping[str, Any] = field(default_factory=dict)
    schema: str = "ztare-counterexample-observation-triple-v1"

    def __post_init__(self) -> None:
        if not str(self.evidence_epoch_sha256).strip():
            raise ValueError("evidence_epoch_sha256 is required")
        if not str(self.evidence_ref).strip() or not str(self.observation_ref).strip():
            raise ValueError("evidence_ref and observation_ref are required")
        for value in (
            self.proposal_identity,
            self.intervention,
            self.source_observation,
            self.proposed_consequence,
            self.observed_consequence,
            self.transition_identity,
        ):
            _json_payload(value)

    def to_dict(self) -> dict[str, Any]:
        """Return the carried packet, including resolvable provenance refs."""
        return {
            "schema": self.schema,
            "observation_chart": self.chart.to_dict(),
            "evidence_epoch": {
                "sha256": self.evidence_epoch_sha256,
                "evidence_ref": self.evidence_ref,
            },
            "observation_ref": self.observation_ref,
            "proposal_identity": _json_payload(self.proposal_identity),
            "intervention": _json_payload(self.intervention),
            "objects": {
                "source_observation": _json_payload(self.source_observation),
                "proposed_consequence": _json_payload(self.proposed_consequence),
                "observed_consequence": _json_payload(self.observed_consequence),
            },
            "transition_identity": _json_payload(self.transition_identity),
        }

    def identity_dict(self) -> dict[str, Any]:
        """Return the semantic relation used for equality and route joins.

        Evidence and observation refs locate the packet; they do not identify
        its contents.  Keeping them out of equality lets the same observation
        commute through a copied evidence bank or a different visible source
        path without creating a second counterexample obligation.
        """

        packet = self.to_dict()
        return {
            "schema": packet["schema"],
            "observation_chart": packet["observation_chart"],
            "evidence_epoch_sha256": self.evidence_epoch_sha256,
            "proposal_identity": packet["proposal_identity"],
            "intervention": packet["intervention"],
            "objects": packet["objects"],
            "transition_identity": packet["transition_identity"],
        }

    @property
    def sha256(self) -> str:
        return stable_sha256(self.identity_dict())


PointwiseOperationFn = Callable[[Any, Mapping[str, Any]], Any]


@dataclass(frozen=True)
class RegisteredPointwiseOperation:
    operation_id: str
    implementation_sha256: str
    authority: str
    apply: PointwiseOperationFn = field(compare=False, repr=False)


_POINTWISE_OPERATIONS: dict[str, RegisteredPointwiseOperation] = {}


def _immutable_dependency(value: Any, *, seen: set[int] | None = None) -> bool:
    """Conservative static screen for mutable closure/global dependencies."""
    if isinstance(value, (str, int, float, bool, bytes, type(None))):
        return True
    if isinstance(value, tuple):
        return all(_immutable_dependency(item, seen=seen) for item in value)
    if isinstance(value, frozenset):
        return all(_immutable_dependency(item, seen=seen) for item in value)
    if isinstance(value, ModuleType):
        return False
    if inspect.isfunction(value):
        seen = seen or set()
        if id(value) in seen:
            return True
        seen.add(id(value))
        closure = inspect.getclosurevars(value)
        return not closure.nonlocals and all(
            _immutable_dependency(item, seen=seen)
            for item in closure.globals.values()
        )
    return False


def register_pointwise_operation(
    operation_id: str,
    fn: PointwiseOperationFn,
    *,
    authority: str,
) -> RegisteredPointwiseOperation:
    """Register a statically screened row-local coordinate operation.

    Mutable closures, bound objects, and module globals are rejected.  This is
    deliberately conservative: a context-dependent operation belongs in a
    batch evidence migration, not in incremental image maintenance.
    """
    if not str(operation_id).strip() or not str(authority).strip():
        raise ValueError("operation_id and authority are required")
    if not inspect.isfunction(fn):
        raise TypeError("pointwise operations must be plain functions")
    signature = inspect.signature(fn)
    if len(signature.parameters) != 2:
        raise TypeError("pointwise operation must accept exactly (value, parameters)")
    closure = inspect.getclosurevars(fn)
    unsafe = {
        name: type(value).__qualname__
        for name, value in {**closure.nonlocals, **closure.globals}.items()
        if not _immutable_dependency(value)
    }
    if unsafe:
        raise ValueError(
            "pointwise operation closes over mutable/contextual state: "
            + ", ".join(f"{name}:{kind}" for name, kind in sorted(unsafe.items()))
        )
    try:
        source = inspect.getsource(fn)
    except (OSError, TypeError) as exc:  # pragma: no cover - module functions have source
        raise ValueError("pointwise operation source must be inspectable") from exc
    registered = RegisteredPointwiseOperation(
        operation_id=operation_id,
        implementation_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        authority=authority,
        apply=fn,
    )
    prior = _POINTWISE_OPERATIONS.get(operation_id)
    if prior is not None and prior.implementation_sha256 != registered.implementation_sha256:
        raise ValueError(f"operation_id {operation_id!r} is already registered")
    _POINTWISE_OPERATIONS[operation_id] = registered
    return registered


def _identity_operation(value: Any, parameters: Mapping[str, Any]) -> Any:
    if parameters:
        raise ValueError("identity operation takes no parameters")
    return value


def _integer_affine_operation(value: Any, parameters: Mapping[str, Any]) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("integer_affine requires an integer coordinate")
    scale = parameters.get("scale", 1)
    offset = parameters.get("offset", 0)
    if isinstance(scale, bool) or not isinstance(scale, int):
        raise TypeError("integer_affine scale must be an integer")
    if isinstance(offset, bool) or not isinstance(offset, int):
        raise TypeError("integer_affine offset must be an integer")
    return scale * value + offset


register_pointwise_operation("identity.v1", _identity_operation, authority="kernel")
register_pointwise_operation(
    "integer_affine.v1", _integer_affine_operation, authority="kernel"
)


def pointwise_operation_identity(operation_id: str) -> dict[str, str]:
    operation = _POINTWISE_OPERATIONS.get(operation_id)
    if operation is None:
        raise ValueError(f"unregistered pointwise operation: {operation_id}")
    return {
        "operation_id": operation.operation_id,
        "implementation_sha256": operation.implementation_sha256,
        "authority": operation.authority,
    }


@dataclass(frozen=True)
class CoordinateOperation:
    """One registered operation at one packet path."""

    path: tuple[str | int, ...]
    operation_id: str
    implementation_sha256: str
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("coordinate operation path is required")
        if not str(self.operation_id).strip() or not str(
            self.implementation_sha256
        ).strip():
            raise ValueError("operation identity is required")
        _frozen_parameters(self.parameters)

    @classmethod
    def bind(
        cls,
        *,
        path: Sequence[str | int],
        operation_id: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> "CoordinateOperation":
        registered = _POINTWISE_OPERATIONS.get(operation_id)
        if registered is None:
            raise ValueError(f"unregistered pointwise operation: {operation_id}")
        return cls(
            path=tuple(path),
            operation_id=operation_id,
            implementation_sha256=registered.implementation_sha256,
            parameters=dict(parameters or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": list(self.path),
            "operation_id": self.operation_id,
            "implementation_sha256": self.implementation_sha256,
            "parameters": _frozen_parameters(self.parameters),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CoordinateOperation":
        path = payload.get("path")
        parameters = payload.get("parameters") or {}
        if not isinstance(path, list) or not isinstance(parameters, Mapping):
            raise ValueError("coordinate operation needs path list and parameter object")
        normalized_path: list[str | int] = []
        for part in path:
            if isinstance(part, bool) or not isinstance(part, (str, int)):
                raise ValueError("coordinate path components must be strings or integers")
            normalized_path.append(part)
        return cls(
            path=tuple(normalized_path),
            operation_id=str(payload.get("operation_id") or ""),
            implementation_sha256=str(payload.get("implementation_sha256") or ""),
            parameters=dict(parameters),
        )


@dataclass(frozen=True)
class ChartTransportMorphism:
    """Declarative partial morphism between two chart identities."""

    transport_id: str
    source_chart_sha256: str
    target_chart_sha256: str
    operations: tuple[CoordinateOperation, ...]
    domain_witness_bank_sha256: str
    declared_domain: str
    min_witnesses: int = 2
    schema: str = "ztare-chart-transport-morphism-v1"

    def __post_init__(self) -> None:
        for label, value in (
            ("transport_id", self.transport_id),
            ("source_chart_sha256", self.source_chart_sha256),
            ("target_chart_sha256", self.target_chart_sha256),
            ("domain_witness_bank_sha256", self.domain_witness_bank_sha256),
            ("declared_domain", self.declared_domain),
        ):
            if not str(value).strip():
                raise ValueError(f"{label} is required")
        if self.min_witnesses < 1:
            raise ValueError("min_witnesses must be positive")
        paths = [operation.path for operation in self.operations]
        if len(paths) != len(set(paths)):
            raise ValueError("a chart transport may transform each path at most once")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "transport_id": self.transport_id,
            "source_chart_sha256": self.source_chart_sha256,
            "target_chart_sha256": self.target_chart_sha256,
            "operations": [operation.to_dict() for operation in self.operations],
            "domain_witness_bank_sha256": self.domain_witness_bank_sha256,
            "declared_domain": self.declared_domain,
            "min_witnesses": self.min_witnesses,
        }

    @property
    def sha256(self) -> str:
        return stable_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ChartTransportMorphism":
        if payload.get("schema") not in (
            None,
            "ztare-chart-transport-morphism-v1",
        ):
            raise ValueError("unsupported chart transport schema")
        operations = payload.get("operations")
        if not isinstance(operations, list):
            raise ValueError("chart transport operations must be a list")
        return cls(
            transport_id=str(payload.get("transport_id") or ""),
            source_chart_sha256=str(payload.get("source_chart_sha256") or ""),
            target_chart_sha256=str(payload.get("target_chart_sha256") or ""),
            operations=tuple(CoordinateOperation.from_dict(row) for row in operations),
            domain_witness_bank_sha256=str(
                payload.get("domain_witness_bank_sha256") or ""
            ),
            declared_domain=str(payload.get("declared_domain") or ""),
            min_witnesses=int(payload.get("min_witnesses", 2)),
        )


def _value_at_path(packet: Any, path: tuple[str | int, ...]) -> Any:
    value = packet
    for part in path:
        if isinstance(value, Mapping):
            value = value[part]
        elif isinstance(value, (list, tuple)) and isinstance(part, int):
            value = value[part]
        else:
            raise KeyError(f"path {path!r} is not present in packet")
    return value


def _replace_at_path(packet: Any, path: tuple[str | int, ...], replacement: Any) -> Any:
    if not path:
        return replacement
    head, *tail = path
    rest = tuple(tail)
    if isinstance(packet, Mapping):
        if head not in packet:
            raise KeyError(f"path {path!r} is not present in packet")
        out = dict(packet)
        out[head] = _replace_at_path(packet[head], rest, replacement)
        return out
    if isinstance(packet, tuple) and isinstance(head, int):
        out = list(packet)
        out[head] = _replace_at_path(packet[head], rest, replacement)
        return tuple(out)
    if isinstance(packet, list) and isinstance(head, int):
        out = list(packet)
        out[head] = _replace_at_path(packet[head], rest, replacement)
        return out
    raise KeyError(f"path {path!r} is not present in packet")


def apply_chart_transport(morphism: ChartTransportMorphism, packet: Any) -> Any:
    """Apply a compiled row-local morphism to one observation packet."""
    result = copy.deepcopy(packet)
    for operation_spec in morphism.operations:
        operation = _POINTWISE_OPERATIONS.get(operation_spec.operation_id)
        if operation is None:
            raise ValueError(
                f"unregistered pointwise operation: {operation_spec.operation_id}"
            )
        if operation.implementation_sha256 != operation_spec.implementation_sha256:
            raise ValueError(
                f"operation implementation drift: {operation_spec.operation_id}"
            )
        value = _value_at_path(result, operation_spec.path)
        replacement = operation.apply(
            copy.deepcopy(value),
            copy.deepcopy(_frozen_parameters(operation_spec.parameters)),
        )
        result = _replace_at_path(result, operation_spec.path, replacement)
    return result


@dataclass(frozen=True)
class TransportWitness:
    source_packet: Any
    target_packet: Any
    witness_ref: str

    def receipt_payload(self) -> dict[str, Any]:
        return {
            "source_packet": _json_payload(self.source_packet),
            "target_packet": _json_payload(self.target_packet),
            "witness_ref": self.witness_ref,
        }


@dataclass(frozen=True)
class PointwiseTransportCertificate:
    status: str
    morphism_sha256: str
    source_chart_sha256: str
    target_chart_sha256: str
    witness_bank_sha256: str
    tested: int
    coverage_ratio: float
    repetition_checks: int
    order_checks: int
    failures: tuple[Mapping[str, Any], ...]
    schema: str = "ztare-pointwise-transport-certificate-v1"

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": self.status,
            "morphism_sha256": self.morphism_sha256,
            "source_chart_sha256": self.source_chart_sha256,
            "target_chart_sha256": self.target_chart_sha256,
            "witness_bank_sha256": self.witness_bank_sha256,
            "tested": self.tested,
            "coverage_ratio": self.coverage_ratio,
            "repetition_checks": self.repetition_checks,
            "order_checks": self.order_checks,
            "failures": [dict(row) for row in self.failures],
        }


def certify_pointwise_transport(
    *,
    source_chart: ObservationChart,
    target_chart: ObservationChart,
    morphism: ChartTransportMorphism,
    witnesses: Sequence[TransportWitness],
    trusted_operation_authorities: frozenset[str] = frozenset(
        {"kernel", "substrate_adapter", "episode_collector"}
    ),
    failure_cap: int = 20,
) -> PointwiseTransportCertificate:
    """Certify exact transport plus repeat/order metamorphisms over a bank."""
    failures: list[dict[str, Any]] = []
    if morphism.source_chart_sha256 != source_chart.sha256:
        failures.append({"kind": "source_chart_mismatch"})
    if morphism.target_chart_sha256 != target_chart.sha256:
        failures.append({"kind": "target_chart_mismatch"})
    for operation_spec in morphism.operations:
        registered = _POINTWISE_OPERATIONS.get(operation_spec.operation_id)
        if registered is None:
            failures.append(
                {"kind": "unregistered_operation", "operation_id": operation_spec.operation_id}
            )
            continue
        if registered.implementation_sha256 != operation_spec.implementation_sha256:
            failures.append(
                {"kind": "operation_implementation_drift", "operation_id": operation_spec.operation_id}
            )
        if registered.authority not in trusted_operation_authorities:
            failures.append(
                {
                    "kind": "untrusted_operation_authority",
                    "operation_id": operation_spec.operation_id,
                    "authority": registered.authority,
                }
            )

    bank_sha = stable_sha256([witness.receipt_payload() for witness in witnesses])
    if morphism.domain_witness_bank_sha256 != bank_sha:
        failures.append(
            {
                "kind": "domain_witness_bank_mismatch",
                "declared": morphism.domain_witness_bank_sha256,
                "observed": bank_sha,
            }
        )
    first_outputs: dict[str, Any] = {}
    tested = repetition_checks = order_checks = 0

    def run_one(witness: TransportWitness, *, phase: str) -> None:
        nonlocal tested, repetition_checks, order_checks
        try:
            output = apply_chart_transport(morphism, witness.source_packet)
        except Exception as exc:  # noqa: BLE001 - becomes typed counterexample
            if len(failures) < failure_cap:
                failures.append(
                    {
                        "kind": "transport_error",
                        "phase": phase,
                        "witness_ref": witness.witness_ref,
                        "error": f"{type(exc).__name__}:{exc}",
                    }
                )
            return
        key = stable_sha256(witness.receipt_payload())
        if phase == "forward":
            tested += 1
            first_outputs[key] = output
            if _json_payload(output) != _json_payload(witness.target_packet):
                if len(failures) < failure_cap:
                    failures.append(
                        {
                            "kind": "target_mismatch",
                            "witness_ref": witness.witness_ref,
                            "output_sha256": stable_sha256(output),
                            "target_sha256": stable_sha256(witness.target_packet),
                        }
                    )
        else:
            if phase == "repeat":
                repetition_checks += 1
            else:
                order_checks += 1
            if key not in first_outputs or _json_payload(output) != _json_payload(
                first_outputs[key]
            ):
                if len(failures) < failure_cap:
                    failures.append(
                        {
                            "kind": "nonpointwise_or_nondeterministic",
                            "phase": phase,
                            "witness_ref": witness.witness_ref,
                        }
                    )

    for witness in witnesses:
        run_one(witness, phase="forward")
    for witness in witnesses:
        run_one(witness, phase="repeat")
    # Reversal and a deterministic rotation expose rolling/order-dependent maps.
    for witness in reversed(tuple(witnesses)):
        run_one(witness, phase="reverse_order")
    if len(witnesses) > 1:
        rotated = tuple(witnesses[1:]) + tuple(witnesses[:1])
        for witness in rotated:
            run_one(witness, phase="rotated_order")

    coverage = tested / len(witnesses) if witnesses else 0.0
    if len(witnesses) < morphism.min_witnesses:
        failures.append(
            {
                "kind": "insufficient_witnesses",
                "required": morphism.min_witnesses,
                "observed": len(witnesses),
            }
        )
    passed = tested == len(witnesses) and coverage == 1.0 and not failures
    return PointwiseTransportCertificate(
        status="pass" if passed else "fail",
        morphism_sha256=morphism.sha256,
        source_chart_sha256=source_chart.sha256,
        target_chart_sha256=target_chart.sha256,
        witness_bank_sha256=bank_sha,
        tested=tested,
        coverage_ratio=coverage,
        repetition_checks=repetition_checks,
        order_checks=order_checks,
        failures=tuple(failures[:failure_cap]),
    )


@dataclass(frozen=True)
class FiberReachabilityReceipt:
    """Authority receipt binding reachability to one exact presentation."""

    canonical_identity_sha256: str
    chart_sha256: str
    presentation_sha256: str
    status: str
    authority: str
    evidence_refs: tuple[str, ...]
    schema: str = "ztare-fiber-reachability-receipt-v1"

    def __post_init__(self) -> None:
        if self.status != "reachable":
            raise ValueError("fiber reachability receipt must attest reachable")
        for label, value in (
            ("canonical_identity_sha256", self.canonical_identity_sha256),
            ("chart_sha256", self.chart_sha256),
            ("presentation_sha256", self.presentation_sha256),
            ("authority", self.authority),
        ):
            if not str(value).strip():
                raise ValueError(f"{label} is required")
        if not tuple(ref for ref in self.evidence_refs if str(ref).strip()):
            raise ValueError("fiber reachability requires an evidence ref")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "canonical_identity_sha256": self.canonical_identity_sha256,
            "chart_sha256": self.chart_sha256,
            "presentation_sha256": self.presentation_sha256,
            "status": self.status,
            "authority": self.authority,
            "evidence_refs": list(self.evidence_refs),
        }

    @property
    def sha256(self) -> str:
        return stable_sha256(self.to_dict())


@dataclass(frozen=True)
class WitnessedFiberMember:
    """A presentation with a cryptographically bound reachability receipt."""

    canonical_identity_sha256: str
    chart_sha256: str
    presentation: Any
    reachability_receipt: FiberReachabilityReceipt

    def __post_init__(self) -> None:
        receipt = self.reachability_receipt
        if receipt.canonical_identity_sha256 != self.canonical_identity_sha256:
            raise ValueError("reachability receipt binds a different canonical identity")
        if receipt.chart_sha256 != self.chart_sha256:
            raise ValueError("reachability receipt binds a different destination chart")
        if receipt.presentation_sha256 != stable_sha256(_json_payload(self.presentation)):
            raise ValueError("reachability receipt binds different presentation bytes")


@dataclass(frozen=True)
class ConstrainedFiberSelection:
    status: str
    target_chart_sha256: str
    canonical_identity_sha256: str
    selected: WitnessedFiberMember | None
    candidates_considered: int
    reason: str
    schema: str = "ztare-constrained-fiber-selection-v1"


def select_witnessed_fiber(
    *,
    canonical_identity_sha256: str,
    target_chart_sha256: str,
    members: Sequence[WitnessedFiberMember],
) -> ConstrainedFiberSelection:
    """Lower only to a unique witnessed/reachable member of the target chart.

    This is a partial section.  Zero compatible members returns ``unreachable``;
    multiple compatible members returns ``ambiguous``.  The kernel never invents
    or hash-orders a presentation to make gamma total.
    """
    compatible = [
        member
        for member in members
        if member.canonical_identity_sha256 == canonical_identity_sha256
        and member.chart_sha256 == target_chart_sha256
        and member.reachability_receipt.status == "reachable"
    ]
    if not compatible:
        return ConstrainedFiberSelection(
            status="unreachable",
            target_chart_sha256=target_chart_sha256,
            canonical_identity_sha256=canonical_identity_sha256,
            selected=None,
            candidates_considered=0,
            reason="no witnessed reachable member in the requested destination chart",
        )
    if len(compatible) > 1:
        return ConstrainedFiberSelection(
            status="ambiguous",
            target_chart_sha256=target_chart_sha256,
            canonical_identity_sha256=canonical_identity_sha256,
            selected=None,
            candidates_considered=len(compatible),
            reason="destination chart constraint does not select a unique witnessed member",
        )
    return ConstrainedFiberSelection(
        status="selected",
        target_chart_sha256=target_chart_sha256,
        canonical_identity_sha256=canonical_identity_sha256,
        selected=compatible[0],
        candidates_considered=1,
        reason="unique witnessed reachable member",
    )


@dataclass(frozen=True)
class EvidenceEpochSnapshot:
    """Content-addressed evidence identity pinned for one governed run."""

    epoch_sha256: str
    artifact_sha256s: Mapping[str, str]
    artifact_count: int
    schema: str = "ztare-evidence-epoch-snapshot-v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "epoch_sha256": self.epoch_sha256,
            "artifact_sha256s": dict(self.artifact_sha256s),
            "artifact_count": self.artifact_count,
        }


class EvidenceEpochChangedError(RuntimeError):
    """Evidence/chart bytes changed while a governed round held a pin."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _active_episode_paths(project: Path) -> tuple[Path, ...]:
    """Resolve visible/holdout bank members without importing worldmodel code."""
    repo = project.parents[1] if len(project.parents) > 1 else project.parent

    def resolve(raw: Any, base: Path) -> Path | None:
        if not isinstance(raw, str) or not raw.strip():
            return None
        path = Path(raw)
        if not path.is_absolute():
            path = base / path
        return path if path.is_file() else None

    for config, base in (
        (project / "MANIFEST.json", project),
        (repo / "rubrics" / f"{project.name}.json", project),
    ):
        try:
            payload = json.loads(config.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        roles = payload.get("episode_roles") or {}
        if not isinstance(roles, Mapping):
            roles = {}
        visible = resolve(roles.get("visible") or payload.get("visible_episode"), base)
        holdout = resolve(roles.get("holdout") or payload.get("holdout_episode"), base)
        selected = tuple(path for path in (visible, holdout) if path is not None)
        if selected:
            return selected
    episodes = project / "raw" / "episodes"
    conventional = tuple(
        path
        for path in (episodes / "episode_001.jsonl", episodes / "episode_002.jsonl")
        if path.is_file()
    )
    if conventional:
        return conventional
    return tuple(sorted(episodes.glob("*.jsonl"))[:2]) if episodes.is_dir() else ()


def capture_project_evidence_epoch(project_dir: str | Path) -> EvidenceEpochSnapshot:
    """Hash active visible/holdout episodes and their chart/identity sidecars.

    Historical fleet logs and sealed eval archives are cold evidence, not part
    of the active bank unless a project manifest selects them.  Hashing every
    archive would make a cache identity scale with history rather than the
    current verifier footprint.
    """
    project = Path(project_dir).resolve()
    artifacts: dict[str, str] = {}
    selected: set[Path] = set(_active_episode_paths(project))
    for episode in tuple(selected):
        sidecar = episode.with_name(f"{episode.stem}.identity.json")
        if sidecar.is_file():
            selected.add(sidecar)
    for path in sorted(selected):
        try:
            rel = str(path.relative_to(project))
        except ValueError:
            rel = str(path)
        artifacts[rel] = _sha256_file(path)
    payload = {"artifacts": artifacts}
    return EvidenceEpochSnapshot(
        epoch_sha256=stable_sha256(payload),
        artifact_sha256s=artifacts,
        artifact_count=len(artifacts),
    )


def assert_project_evidence_epoch(
    project_dir: str | Path,
    expected: EvidenceEpochSnapshot,
) -> EvidenceEpochSnapshot:
    """Fail if a live round's evidence/chart identity moved."""
    current = capture_project_evidence_epoch(project_dir)
    if current.epoch_sha256 != expected.epoch_sha256:
        before = dict(expected.artifact_sha256s)
        after = dict(current.artifact_sha256s)
        changed = sorted(
            path
            for path in set(before) | set(after)
            if before.get(path) != after.get(path)
        )
        raise EvidenceEpochChangedError(
            "evidence epoch changed during an active governed round; pause leaf "
            "generation, migrate/rebuild the full bank, invalidate caches, and "
            f"start a new round. changed_artifacts={changed[:20]}"
        )
    return current
