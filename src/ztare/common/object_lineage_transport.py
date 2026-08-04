"""Receipt-backed object lineage across appearance revision and occlusion.

An object occurrence belongs to one exact observation.  Its normalized colored
shape is an appearance identity, not a persistent carrier identity.  This
module compiles a separate lineage only from an ordered catalog path and
environment transition receipts.

The compiler is deliberately partial.  It admits four relations:

* a unique exact-type continuation;
* a unique fixed-support appearance revision;
* entry into a one-frame bracketed occlusion; and
* unique exact-type reappearance.

It does not consume task roles, memory text, condition names, embeddings, or
downstream outcomes.  Ambiguity or an unbracketed gap refuses the transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.observation_object_catalog import (
    GridObjectCatalog,
    GridObjectOccurrence,
)


SCHEMA = "ztare-object-lineage-transport-v1"
_RELATIONS = frozenset({
    "unique_exact_type",
    "unique_fixed_support_appearance_revision",
    "bracketed_occlusion_enter",
    "unique_reappearance_exit",
})
_TRACE_STATUSES = frozenset({"resolved", "unresolved"})
_TRANSPORT_STATUSES = frozenset({"transportable", "refused"})


def _nonempty(value: str, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must be nonempty")
    return text


def _canonical(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({
        str(value).strip() for value in values if str(value).strip()
    }))


def _transition_sha256(receipt: Mapping[str, Any]) -> str:
    return stable_sha256(dict(receipt))


@dataclass(frozen=True)
class ObjectLineageEvent:
    """One exact appearance-to-appearance or appearance-to-latent edge."""

    lineage_sha256: str
    hop_index: int
    source_observation_sha256: str
    source_catalog_sha256: str
    source_object_ref: str
    source_type_sha256: str
    target_observation_sha256: str
    target_catalog_sha256: str
    target_object_ref: str
    target_type_sha256: str
    relation: str
    transition_sha256: str
    preserved_features: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "lineage_sha256",
            "source_observation_sha256",
            "source_catalog_sha256",
            "source_type_sha256",
            "target_observation_sha256",
            "target_catalog_sha256",
            "transition_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if (
            isinstance(self.hop_index, bool)
            or not isinstance(self.hop_index, int)
            or self.hop_index <= 0
        ):
            raise ValueError("hop_index must be a positive integer")
        if self.relation not in _RELATIONS:
            raise ValueError(f"unknown lineage relation {self.relation!r}")
        source_ref = str(self.source_object_ref or "").strip()
        target_ref = str(self.target_object_ref or "").strip()
        target_type = str(self.target_type_sha256 or "").strip()
        if self.relation == "bracketed_occlusion_enter":
            if not source_ref or target_ref or target_type:
                raise ValueError("occlusion entry must end in latent state")
        elif self.relation == "unique_reappearance_exit":
            if source_ref or not target_ref or not target_type:
                raise ValueError(
                    "reappearance must start latent and end visible"
                )
        elif not source_ref or not target_ref or not target_type:
            raise ValueError("visible lineage edge requires both occurrences")
        features = _canonical(self.preserved_features)
        if not features:
            raise ValueError("lineage event requires preserved features")
        object.__setattr__(self, "preserved_features", features)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "object_lineage_event",
            "lineage_sha256": self.lineage_sha256,
            "hop_index": self.hop_index,
            "source_observation_sha256": (
                self.source_observation_sha256
            ),
            "source_catalog_sha256": self.source_catalog_sha256,
            "source_object_ref": self.source_object_ref,
            "source_type_sha256": self.source_type_sha256,
            "target_observation_sha256": (
                self.target_observation_sha256
            ),
            "target_catalog_sha256": self.target_catalog_sha256,
            "target_object_ref": self.target_object_ref,
            "target_type_sha256": self.target_type_sha256,
            "relation": self.relation,
            "transition_sha256": self.transition_sha256,
            "preserved_features": list(self.preserved_features),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class ObjectLineageTrace:
    """One root occurrence and its ordered appearance history."""

    lineage_sha256: str
    source_object_ref: str
    source_type_sha256: str
    target_object_ref: str
    target_type_sha256: str
    status: str
    reason: str
    events: tuple[ObjectLineageEvent, ...]

    def __post_init__(self) -> None:
        for name in (
            "lineage_sha256",
            "source_object_ref",
            "source_type_sha256",
            "reason",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.status not in _TRACE_STATUSES:
            raise ValueError(f"unknown lineage trace status {self.status!r}")
        if self.status == "resolved":
            _nonempty(self.target_object_ref, "target_object_ref")
            _nonempty(self.target_type_sha256, "target_type_sha256")
        if any(
            event.lineage_sha256 != self.lineage_sha256
            for event in self.events
        ):
            raise ValueError("lineage trace contains a foreign event")
        indices = [event.hop_index for event in self.events]
        if indices != sorted(indices):
            raise ValueError("lineage events are out of order")

    @property
    def appearance_revision_count(self) -> int:
        return sum(
            event.relation
            == "unique_fixed_support_appearance_revision"
            for event in self.events
        )

    @property
    def bracketed_occlusion_count(self) -> int:
        return sum(
            event.relation == "unique_reappearance_exit"
            for event in self.events
        )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "object_lineage_trace",
            "lineage_sha256": self.lineage_sha256,
            "source_object_ref": self.source_object_ref,
            "source_type_sha256": self.source_type_sha256,
            "target_object_ref": self.target_object_ref,
            "target_type_sha256": self.target_type_sha256,
            "status": self.status,
            "reason": self.reason,
            "appearance_revision_count": (
                self.appearance_revision_count
            ),
            "bracketed_occlusion_count": (
                self.bracketed_occlusion_count
            ),
            "events": [event.to_receipt() for event in self.events],
        }
        return {**payload, "sha256": stable_sha256(payload)}


@dataclass(frozen=True)
class CausalObjectLineageTransport:
    """A complete unique lift, or an inspectable refusal."""

    source_observation_sha256: str
    source_catalog_sha256: str
    target_observation_sha256: str
    target_catalog_sha256: str
    required_source_object_refs: tuple[str, ...]
    traces: tuple[ObjectLineageTrace, ...]
    status: str
    reason: str
    evidence_refs: tuple[str, ...]
    maximum_occlusion_frames: int = 1
    method: str = "receipt_backed_unique_lineage"

    def __post_init__(self) -> None:
        for name in (
            "source_observation_sha256",
            "source_catalog_sha256",
            "target_observation_sha256",
            "target_catalog_sha256",
            "reason",
            "method",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.status not in _TRANSPORT_STATUSES:
            raise ValueError(f"unknown lineage transport status {self.status!r}")
        if self.maximum_occlusion_frames != 1:
            raise ValueError("only one-frame bracketed occlusion is certified")
        required = _canonical(self.required_source_object_refs)
        if not required:
            raise ValueError("lineage transport requires source objects")
        object.__setattr__(
            self,
            "required_source_object_refs",
            required,
        )
        roots = [trace.source_object_ref for trace in self.traces]
        if len(roots) != len(set(roots)):
            raise ValueError("lineage transport repeats a source root")
        if not set(roots).issubset(set(required)):
            raise ValueError("lineage transport contains an unrequested root")
        if self.status == "transportable":
            if set(roots) != set(required) or any(
                trace.status != "resolved" for trace in self.traces
            ):
                raise ValueError(
                    "transportable lineage must resolve every source root"
                )
            targets = [
                trace.target_object_ref for trace in self.traces
            ]
            if len(targets) != len(set(targets)):
                raise ValueError("lineage transport merges target objects")
        evidence = _canonical(self.evidence_refs)
        if not evidence:
            raise ValueError("lineage transport requires evidence refs")
        object.__setattr__(self, "evidence_refs", evidence)

    def map_ref(self, source_object_ref: str) -> str:
        if self.status != "transportable":
            raise ValueError("refused lineage transport cannot map objects")
        matches = [
            trace.target_object_ref
            for trace in self.traces
            if trace.source_object_ref == str(source_object_ref)
        ]
        if len(matches) != 1:
            raise ValueError("source object is absent from lineage authority")
        return matches[0]

    def map_path(self, source_path: Iterable[str]) -> tuple[str, ...]:
        return tuple(self.map_ref(value) for value in source_path)

    @property
    def appearance_revision_count(self) -> int:
        return sum(
            trace.appearance_revision_count for trace in self.traces
        )

    @property
    def bracketed_occlusion_count(self) -> int:
        return sum(
            trace.bracketed_occlusion_count for trace in self.traces
        )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "causal_object_lineage_transport",
            "source_observation_sha256": (
                self.source_observation_sha256
            ),
            "source_catalog_sha256": self.source_catalog_sha256,
            "target_observation_sha256": (
                self.target_observation_sha256
            ),
            "target_catalog_sha256": self.target_catalog_sha256,
            "required_source_object_refs": list(
                self.required_source_object_refs
            ),
            "traces": [trace.to_receipt() for trace in self.traces],
            "status": self.status,
            "reason": self.reason,
            "appearance_revision_count": self.appearance_revision_count,
            "bracketed_occlusion_count": self.bracketed_occlusion_count,
            "maximum_occlusion_frames": self.maximum_occlusion_frames,
            "evidence_refs": list(self.evidence_refs),
            "method": self.method,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def _verify_receipt_sha256(receipt: Mapping[str, Any]) -> None:
    core = dict(receipt)
    claimed = str(core.pop("sha256", "") or "")
    if not claimed or stable_sha256(core) != claimed:
        raise ValueError("object lineage receipt sha256 mismatch")


def object_lineage_event_from_receipt(
    receipt: Mapping[str, Any],
) -> ObjectLineageEvent:
    _verify_receipt_sha256(receipt)
    if (
        receipt.get("schema") != SCHEMA
        or receipt.get("kind") != "object_lineage_event"
    ):
        raise ValueError("wrong object lineage event receipt")
    return ObjectLineageEvent(
        lineage_sha256=str(receipt["lineage_sha256"]),
        hop_index=int(receipt["hop_index"]),
        source_observation_sha256=str(
            receipt["source_observation_sha256"]
        ),
        source_catalog_sha256=str(receipt["source_catalog_sha256"]),
        source_object_ref=str(receipt.get("source_object_ref") or ""),
        source_type_sha256=str(receipt["source_type_sha256"]),
        target_observation_sha256=str(
            receipt["target_observation_sha256"]
        ),
        target_catalog_sha256=str(receipt["target_catalog_sha256"]),
        target_object_ref=str(receipt.get("target_object_ref") or ""),
        target_type_sha256=str(receipt.get("target_type_sha256") or ""),
        relation=str(receipt["relation"]),
        transition_sha256=str(receipt["transition_sha256"]),
        preserved_features=tuple(receipt["preserved_features"]),
    )


def object_lineage_trace_from_receipt(
    receipt: Mapping[str, Any],
) -> ObjectLineageTrace:
    _verify_receipt_sha256(receipt)
    if (
        receipt.get("schema") != SCHEMA
        or receipt.get("kind") != "object_lineage_trace"
    ):
        raise ValueError("wrong object lineage trace receipt")
    trace = ObjectLineageTrace(
        lineage_sha256=str(receipt["lineage_sha256"]),
        source_object_ref=str(receipt["source_object_ref"]),
        source_type_sha256=str(receipt["source_type_sha256"]),
        target_object_ref=str(receipt.get("target_object_ref") or ""),
        target_type_sha256=str(receipt.get("target_type_sha256") or ""),
        status=str(receipt["status"]),
        reason=str(receipt["reason"]),
        events=tuple(
            object_lineage_event_from_receipt(row)
            for row in receipt["events"]
        ),
    )
    if (
        trace.appearance_revision_count
        != int(receipt["appearance_revision_count"])
        or trace.bracketed_occlusion_count
        != int(receipt["bracketed_occlusion_count"])
    ):
        raise ValueError("object lineage trace summary drifted")
    return trace


def causal_object_lineage_transport_from_receipt(
    receipt: Mapping[str, Any],
) -> CausalObjectLineageTransport:
    _verify_receipt_sha256(receipt)
    if (
        receipt.get("schema") != SCHEMA
        or receipt.get("kind") != "causal_object_lineage_transport"
    ):
        raise ValueError("wrong causal object lineage transport receipt")
    transport = CausalObjectLineageTransport(
        source_observation_sha256=str(
            receipt["source_observation_sha256"]
        ),
        source_catalog_sha256=str(receipt["source_catalog_sha256"]),
        target_observation_sha256=str(
            receipt["target_observation_sha256"]
        ),
        target_catalog_sha256=str(receipt["target_catalog_sha256"]),
        required_source_object_refs=tuple(
            receipt["required_source_object_refs"]
        ),
        traces=tuple(
            object_lineage_trace_from_receipt(row)
            for row in receipt["traces"]
        ),
        status=str(receipt["status"]),
        reason=str(receipt["reason"]),
        evidence_refs=tuple(receipt["evidence_refs"]),
        maximum_occlusion_frames=int(
            receipt["maximum_occlusion_frames"]
        ),
        method=str(receipt["method"]),
    )
    if (
        transport.appearance_revision_count
        != int(receipt["appearance_revision_count"])
        or transport.bracketed_occlusion_count
        != int(receipt["bracketed_occlusion_count"])
    ):
        raise ValueError("causal object lineage summary drifted")
    return transport


def _lineage_sha256(
    catalog: GridObjectCatalog,
    object_ref: str,
) -> str:
    return stable_sha256({
        "schema": SCHEMA,
        "kind": "object_lineage_identity",
        "source_observation_sha256": catalog.observation_sha256,
        "source_catalog_sha256": catalog.sha256,
        "source_object_ref": object_ref,
    })


def _by_ref(catalog: GridObjectCatalog) -> dict[str, GridObjectOccurrence]:
    return {row.object_ref: row for row in catalog.objects}


def _exact_candidates(
    source: GridObjectOccurrence,
    target: GridObjectCatalog,
) -> list[GridObjectOccurrence]:
    return [
        row for row in target.objects
        if row.type_sha256 == source.type_sha256
    ]


def _revision_candidates(
    source: GridObjectOccurrence,
    target: GridObjectCatalog,
) -> list[GridObjectOccurrence]:
    return [
        row for row in target.objects
        if (
            row.type_sha256 != source.type_sha256
            and row.bbox == source.bbox
            and row.palette == source.palette
            and row.cell_count == source.cell_count
        )
    ]


def compile_causal_object_lineage_transport(
    catalogs: Sequence[GridObjectCatalog],
    transition_receipts: Sequence[Mapping[str, Any]],
    *,
    required_source_object_refs: Iterable[str],
    evidence_refs: Iterable[str],
    maximum_occlusion_frames: int = 1,
) -> CausalObjectLineageTransport:
    """Compile a unique appearance lift across an ordered transition path."""

    path = tuple(catalogs)
    transitions = tuple(dict(row) for row in transition_receipts)
    if len(path) < 2:
        raise ValueError("lineage path requires at least two catalogs")
    if len(transitions) != len(path) - 1:
        raise ValueError("transition count does not match catalog path")
    if maximum_occlusion_frames != 1:
        raise ValueError("only one-frame occlusion is currently certified")
    for index, (source, target, transition) in enumerate(
        zip(path, path[1:], transitions),
        start=1,
    ):
        if str(transition.get("source_observation_sha256") or "") != (
            source.observation_sha256
        ):
            raise ValueError(
                f"transition {index} crossed source observation"
            )
        successor = str(
            transition.get("successor_observation_sha256")
            or transition.get("target_observation_sha256")
            or ""
        )
        if successor != target.observation_sha256:
            raise ValueError(
                f"transition {index} crossed target observation"
            )

    required = _canonical(required_source_object_refs)
    source_objects = _by_ref(path[0])
    missing = set(required) - set(source_objects)
    if missing:
        raise ValueError(
            f"required lineage roots are absent: {sorted(missing)}"
        )
    states: dict[str, dict[str, Any]] = {}
    for source_ref in required:
        source = source_objects[source_ref]
        states[source_ref] = {
            "lineage_sha256": _lineage_sha256(path[0], source_ref),
            "source": source,
            "current": source,
            "occluded_type_sha256": "",
            "events": [],
            "status": "resolved",
            "reason": "lineage_path_complete",
        }

    transport_status = "transportable"
    transport_reason = "unique_lineage_path_complete"
    for zero_index, (source_catalog, target_catalog, transition) in enumerate(
        zip(path, path[1:], transitions),
    ):
        hop_index = zero_index + 1
        transition_sha = _transition_sha256(transition)
        assigned_targets: set[str] = set()
        for root_ref in required:
            state = states[root_ref]
            current = state["current"]
            lineage_sha = str(state["lineage_sha256"])
            if current is None:
                expected_type = str(state["occluded_type_sha256"])
                matches = [
                    row for row in target_catalog.objects
                    if row.type_sha256 == expected_type
                    and row.object_ref not in assigned_targets
                ]
                if len(matches) != 1:
                    transport_status = "refused"
                    transport_reason = (
                        "occluded_lineage_has_no_unique_reappearance"
                    )
                    state["status"] = "unresolved"
                    state["reason"] = transport_reason
                    break
                target = matches[0]
                assigned_targets.add(target.object_ref)
                state["events"].append(ObjectLineageEvent(
                    lineage_sha256=lineage_sha,
                    hop_index=hop_index,
                    source_observation_sha256=(
                        source_catalog.observation_sha256
                    ),
                    source_catalog_sha256=source_catalog.sha256,
                    source_object_ref="",
                    source_type_sha256=expected_type,
                    target_observation_sha256=(
                        target_catalog.observation_sha256
                    ),
                    target_catalog_sha256=target_catalog.sha256,
                    target_object_ref=target.object_ref,
                    target_type_sha256=target.type_sha256,
                    relation="unique_reappearance_exit",
                    transition_sha256=transition_sha,
                    preserved_features=("type_sha256",),
                ))
                state["current"] = target
                state["occluded_type_sha256"] = ""
                continue

            exact = [
                row for row in _exact_candidates(current, target_catalog)
                if row.object_ref not in assigned_targets
            ]
            if len(exact) == 1:
                target = exact[0]
                relation = "unique_exact_type"
                preserved = ("type_sha256",)
            elif len(exact) > 1:
                transport_status = "refused"
                transport_reason = "lineage_successor_is_ambiguous"
                state["status"] = "unresolved"
                state["reason"] = transport_reason
                break
            else:
                revisions = [
                    row
                    for row in _revision_candidates(
                        current,
                        target_catalog,
                    )
                    if row.object_ref not in assigned_targets
                ]
                if len(revisions) == 1:
                    target = revisions[0]
                    relation = (
                        "unique_fixed_support_appearance_revision"
                    )
                    preserved = ("bbox", "cell_count", "palette")
                elif len(revisions) > 1:
                    transport_status = "refused"
                    transport_reason = "lineage_successor_is_ambiguous"
                    state["status"] = "unresolved"
                    state["reason"] = transport_reason
                    break
                else:
                    lookahead = (
                        path[zero_index + 2]
                        if zero_index + 2 < len(path)
                        else None
                    )
                    reappearances = (
                        _exact_candidates(current, lookahead)
                        if lookahead is not None
                        else []
                    )
                    if len(reappearances) != 1:
                        transport_status = "refused"
                        transport_reason = (
                            "lineage_absence_is_not_uniquely_bracketed"
                        )
                        state["status"] = "unresolved"
                        state["reason"] = transport_reason
                        break
                    state["events"].append(ObjectLineageEvent(
                        lineage_sha256=lineage_sha,
                        hop_index=hop_index,
                        source_observation_sha256=(
                            source_catalog.observation_sha256
                        ),
                        source_catalog_sha256=source_catalog.sha256,
                        source_object_ref=current.object_ref,
                        source_type_sha256=current.type_sha256,
                        target_observation_sha256=(
                            target_catalog.observation_sha256
                        ),
                        target_catalog_sha256=target_catalog.sha256,
                        target_object_ref="",
                        target_type_sha256="",
                        relation="bracketed_occlusion_enter",
                        transition_sha256=transition_sha,
                        preserved_features=(
                            "lookahead_unique_type_sha256",
                        ),
                    ))
                    state["current"] = None
                    state["occluded_type_sha256"] = current.type_sha256
                    continue

            assigned_targets.add(target.object_ref)
            state["events"].append(ObjectLineageEvent(
                lineage_sha256=lineage_sha,
                hop_index=hop_index,
                source_observation_sha256=(
                    source_catalog.observation_sha256
                ),
                source_catalog_sha256=source_catalog.sha256,
                source_object_ref=current.object_ref,
                source_type_sha256=current.type_sha256,
                target_observation_sha256=(
                    target_catalog.observation_sha256
                ),
                target_catalog_sha256=target_catalog.sha256,
                target_object_ref=target.object_ref,
                target_type_sha256=target.type_sha256,
                relation=relation,
                transition_sha256=transition_sha,
                preserved_features=preserved,
            ))
            state["current"] = target
        if transport_status == "refused":
            break

    traces = []
    for root_ref in required:
        state = states[root_ref]
        current = state["current"]
        status = str(state["status"])
        reason = str(state["reason"])
        if transport_status == "refused" and not state["events"]:
            status = "unresolved"
            reason = "path_stopped_after_foreign_lineage_refusal"
        traces.append(ObjectLineageTrace(
            lineage_sha256=str(state["lineage_sha256"]),
            source_object_ref=root_ref,
            source_type_sha256=state["source"].type_sha256,
            target_object_ref=(
                current.object_ref
                if transport_status == "transportable"
                and current is not None
                else ""
            ),
            target_type_sha256=(
                current.type_sha256
                if transport_status == "transportable"
                and current is not None
                else ""
            ),
            status=(
                "resolved"
                if transport_status == "transportable"
                and current is not None
                else "unresolved"
            ),
            reason=(
                "lineage_path_complete"
                if transport_status == "transportable"
                else reason
            ),
            events=tuple(state["events"]),
        ))
    return CausalObjectLineageTransport(
        source_observation_sha256=path[0].observation_sha256,
        source_catalog_sha256=path[0].sha256,
        target_observation_sha256=path[-1].observation_sha256,
        target_catalog_sha256=path[-1].sha256,
        required_source_object_refs=required,
        traces=tuple(traces),
        status=transport_status,
        reason=transport_reason,
        evidence_refs=tuple(evidence_refs),
        maximum_occlusion_frames=maximum_occlusion_frames,
    )


__all__ = [
    "CausalObjectLineageTransport",
    "ObjectLineageEvent",
    "ObjectLineageTrace",
    "causal_object_lineage_transport_from_receipt",
    "compile_causal_object_lineage_transport",
    "object_lineage_event_from_receipt",
    "object_lineage_trace_from_receipt",
]
