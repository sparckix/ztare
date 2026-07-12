from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ztare.common.structured_blocks import balanced_object_after_marker, json_object_span


CONTROL_RECEIPT_MARKERS: dict[str, str] = {
    "STRATEGY_CARD_DISCHARGE:": "STRATEGY_CARD_DISCHARGE",
    "LEAF_WORKBENCH_ACTION_REQUEST:": "LEAF_WORKBENCH_ACTION_REQUEST",
    "LEAF_WORKBENCH_RECEIPT:": "LEAF_WORKBENCH_RECEIPT",
    "VISIBLE_WORKBENCH_DIAGNOSTIC:": "VISIBLE_WORKBENCH_DIAGNOSTIC",
    "LEAF_WORKBENCH_CAPABILITY_PROPOSAL:": "LEAF_WORKBENCH_CAPABILITY_PROPOSAL",
    "LOWERABILITY_BLOCKED:": "LOWERABILITY_BLOCKED",
}

CONTROL_RECEIPT_LIST_KEYS: tuple[str, ...] = (
    "control_receipts",
    "control_receipt",
    "receipts",
    "typed_receipts",
)


@dataclass(frozen=True)
class ControlMorphism:
    """One typed boundary action available to an agent loop."""

    capability_id: str
    input_refs: dict[str, Any] = field(default_factory=dict)
    required_input_refs: dict[str, str] = field(default_factory=dict)
    claim_bindings: list[str] = field(default_factory=list)

    def identity(self) -> str:
        payload = {
            "capability_id": self.capability_id,
            "input_refs": self.input_refs,
            "required_input_refs": self.required_input_refs,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    def request_object(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "capability_id": self.capability_id,
            "claim_bindings": self.claim_bindings or [self.capability_id],
            "input_refs": self.input_refs,
        }
        if self.required_input_refs:
            payload["required_input_refs"] = self.required_input_refs
        return {
            "type": "LEAF_WORKBENCH_ACTION_REQUEST",
            "payload": payload,
        }


@dataclass(frozen=True)
class ControlTransition:
    """One executable transition in a control lifecycle."""

    state: str
    event: str
    next: str
    invariant: str = ""

    def as_dict(self) -> dict[str, str]:
        row = {
            "state": self.state,
            "event": self.event,
            "next": self.next,
        }
        if self.invariant:
            row["invariant"] = self.invariant
        return row


@dataclass(frozen=True)
class ControlLedgerSurface:
    """One existing ledger or contract touched by a control lifecycle."""

    surface: str
    contract: str
    authority: str

    def as_dict(self) -> dict[str, str]:
        return {
            "surface": self.surface,
            "contract": self.contract,
            "authority": self.authority,
        }


@dataclass(frozen=True)
class ControlStateChart:
    """Small declarative lifecycle shared by substrate adapters.

    This is intentionally lighter than a runtime state-machine framework: the
    repo boundary usually needs serializable contracts for agents and parsers,
    not long-lived Python objects with hidden mutable state.
    """

    schema: str
    transitions: tuple[ControlTransition, ...]

    def transition_table(self) -> list[dict[str, str]]:
        return [row.as_dict() for row in self.transitions]

    def next_state(self, state: str, event: str) -> str | None:
        for row in self.transitions:
            if row.state == state and row.event == event:
                return row.next
        return None

    def admissible_events(self, state: str) -> list[str]:
        return [row.event for row in self.transitions if row.state == state]

    def surface_object(
        self,
        *,
        state: str,
        context: dict[str, Any] | None = None,
        admissible_events: list[str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": self.schema,
            "state": state,
            "admissible_events": (
                admissible_events
                if admissible_events is not None
                else self.admissible_events(state)
            ),
            "transition_table": self.transition_table(),
        }
        if context:
            payload["context"] = context
        return payload


def render_control_state_chart_surface(
    *,
    chart: ControlStateChart,
    state: str,
    context: dict[str, Any] | None = None,
    admissible_events: list[str] | None = None,
    heading: str = "CONTROL LIFECYCLE",
    last_error: str = "",
    boundary_rule: str = "",
) -> str:
    lines = [
        f"{heading}:",
        json.dumps(
            chart.surface_object(
                state=state,
                context=context,
                admissible_events=admissible_events,
            ),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ),
    ]
    if boundary_rule:
        lines.append(f"boundary_rule: {boundary_rule}")
    if last_error:
        lines.append(f"last_error: {last_error[:1200]}")
    return "\n".join(lines) + "\n\n"


def control_ledger_surfaces_object(
    surfaces: tuple[ControlLedgerSurface, ...],
) -> list[dict[str, str]]:
    """Serializable read model for lifecycle-adjacent ledgers.

    This is deliberately not a proposal taxonomy. It only points to contracts
    that already own parser/gate behavior, so lifecycle projections cannot
    create a second authority path by naming a new class in prose.
    """

    return [surface.as_dict() for surface in surfaces]


def receipt_objects_after_marker(
    text: str,
    *,
    marker: str = "LEAF_WORKBENCH_RECEIPT:",
    receipt_type: str = "LEAF_WORKBENCH_RECEIPT",
) -> list[dict[str, Any]]:
    """Extract typed receipt objects from marker-bound JSON blocks."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in balanced_object_after_marker(text or "", marker):
        try:
            payload = json.loads(raw, strict=False)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            identity = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
            if identity in seen:
                continue
            seen.add(identity)
            rows.append({"type": receipt_type, "payload": payload})
    return rows


def control_receipt_rows(
    text: str,
    *,
    markers: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Normalize raw JSON and marker-rendered control receipts to one read model."""

    source = text or ""
    marker_map = CONTROL_RECEIPT_MARKERS if markers is None else markers
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(row: dict[str, Any]) -> None:
        normalized = _normalize_control_receipt_row(row)
        if normalized is None:
            return
        identity = json.dumps(normalized, sort_keys=True, separators=(",", ":"), default=str)
        if identity in seen:
            return
        seen.add(identity)
        rows.append(normalized)

    for payload in _json_payload_candidates(source):
        for row in _control_receipts_from_json_payload(payload):
            add(row)

    for marker, receipt_type in marker_map.items():
        for raw in balanced_object_after_marker(source, marker):
            try:
                payload = json.loads(raw, strict=False)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                add({"type": receipt_type, "payload": payload})
    return rows


def control_receipt_payloads(
    text: str,
    *,
    receipt_types: set[str] | frozenset[str] | tuple[str, ...],
) -> list[dict[str, Any]]:
    wanted = {str(row) for row in receipt_types}
    payloads: list[dict[str, Any]] = []
    for row in control_receipt_rows(text):
        if str(row.get("type") or "") not in wanted:
            continue
        payload = row.get("payload")
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _control_receipts_from_json_payload(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows: list[dict[str, Any]] = []
    for key in CONTROL_RECEIPT_LIST_KEYS:
        raw = payload.get(key)
        if raw is None:
            continue
        if isinstance(raw, list):
            rows.extend(row for row in raw if isinstance(row, dict))
        elif isinstance(raw, dict):
            rows.append(raw)
    return rows


def _json_payload_candidates(source: str) -> list[object]:
    payloads: list[object] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        try:
            payload = json.loads(raw, strict=False)
        except json.JSONDecodeError:
            return
        identity = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        if identity in seen:
            return
        seen.add(identity)
        payloads.append(payload)

    stripped = source.strip()
    if stripped:
        add(stripped)

    start = 0
    while True:
        idx = source.find("{", start)
        if idx < 0:
            break
        span = json_object_span(source, idx)
        if span is None:
            start = idx + 1
            continue
        add(source[span[0] : span[1]])
        start = span[1]
    return payloads


def _normalize_control_receipt_row(row: dict[str, Any]) -> dict[str, Any] | None:
    receipt_type = str(row.get("type") or row.get("marker") or "").strip()
    if not receipt_type and str(row.get("schema") or "") == "ztare-visible-workbench-cli-receipt-v1":
        receipt_obj = row.get("receipt")
        if isinstance(receipt_obj, dict):
            return _normalize_control_receipt_row(receipt_obj)
        return {"type": "LEAF_WORKBENCH_RECEIPT", "payload": row}
    if not receipt_type:
        return None
    payload = row.get("payload")
    if isinstance(payload, dict):
        return {"type": receipt_type, "payload": payload}
    return {
        "type": receipt_type,
        "payload": {
            key: value
            for key, value in row.items()
            if key not in {"type", "marker", "payload"}
        },
    }


def receipt_objects_json_after_marker(
    text: str,
    *,
    marker: str = "LEAF_WORKBENCH_RECEIPT:",
    receipt_type: str = "LEAF_WORKBENCH_RECEIPT",
) -> str:
    rows = receipt_objects_after_marker(
        text,
        marker=marker,
        receipt_type=receipt_type,
    )
    return json.dumps(rows, sort_keys=True, separators=(",", ":"), default=str) if rows else ""


def executed_morphism_ids_from_receipts(
    text: str,
    *,
    marker: str = "LEAF_WORKBENCH_RECEIPT:",
) -> list[str]:
    ids: list[str] = []
    if marker == "LEAF_WORKBENCH_RECEIPT:":
        rows = control_receipt_rows(text)
    else:
        rows = receipt_objects_after_marker(text, marker=marker)
    for row in rows:
        payload = row.get("payload") if isinstance(row, dict) else None
        if not isinstance(payload, dict):
            continue
        cap = str(payload.get("capability_id") or "").strip()
        if cap and cap not in ids:
            ids.append(cap)
    return ids


def render_control_state_surface(
    *,
    executed_morphisms: list[str],
    carried_receipts_json: str = "",
    admissible_next: list[ControlMorphism] | None = None,
    heading: str = "CONTROL STATE",
    include_receipt_objects: bool = False,
    no_next_morphism_policy: str = (
        "submit a carrier, emit the substrate's typed obstruction receipt, or "
        "request a different capability only if the latest error asks for one."
    ),
) -> str:
    """Render a compact state-machine surface for retry prompts.

    This keeps boundary state typed while leaving the worker's internal
    reasoning unconstrained. Callers provide substrate-specific morphisms; this
    renderer only states what already ran, what receipts must be carried, and
    what action remains admissible.
    """
    admissible_next = admissible_next or []
    lines = [
        f"{heading}:",
        f"- executed_morphisms: {json.dumps(executed_morphisms, sort_keys=True)}",
    ]
    if carried_receipts_json:
        lines.append(
            "- carried_receipts: kernel-retained; cite refs/facts, do not recreate receipt objects."
        )
    if admissible_next:
        lines.append(
            "- admissible_next_morphisms: "
            + json.dumps(
                [m.request_object() for m in admissible_next],
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
        )
    else:
        lines.append(f"- admissible_next_morphisms: {no_next_morphism_policy}")
    lines.append(
        "- repeat_policy: do not re-request an executed morphism with the same inputs."
    )
    if carried_receipts_json and include_receipt_objects:
        lines.append("Ready-to-use receipt object(s) for `control_receipts`:")
        lines.append(carried_receipts_json)
    return "\n".join(lines) + "\n\n"
