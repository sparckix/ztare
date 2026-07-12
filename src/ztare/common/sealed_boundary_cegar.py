from __future__ import annotations

import json
from typing import Any

from ztare.common.control_state_machine import (
    ControlLedgerSurface,
    ControlMorphism,
    ControlStateChart,
    ControlTransition,
    control_ledger_surfaces_object,
    render_control_state_chart_surface,
    render_control_state_surface,
)
from ztare.common.cegis_membrane import (
    CONSUMED_COUNTEREXAMPLE,
    EVIDENCE_STATUSES,
    normalize_evidence_statuses,
)
from ztare.common.science_output_policy import SCIENCE_OUTPUT_POLICY


SCHEMA = "ztare-sealed-boundary-cegar-automaton-v1"
LOWERABILITY_BLOCKED_SCHEMA = "ztare-lowerability-blocked-v1"


BOUNDARY_CEGAR_CHART = ControlStateChart(
    schema=SCHEMA,
    transitions=(
        ControlTransition(
            state="counterexample_open",
            event="request_typed_observation",
            next="observation_requested",
            invariant="the hidden evaluator remains sealed; only registered morphisms run",
        ),
        ControlTransition(
            state="counterexample_open",
            event="submit_candidate_delta",
            next="candidate_pending_gate",
            invariant="candidate may be attempted directly when visible evidence supports a transportable law",
        ),
        ControlTransition(
            state="counterexample_open",
            event="report_tool_gap",
            next="tool_gap_pending",
            invariant=(
                "missing instruments are reported as receipt-bound tool gaps; "
                "tool proposals are optional meta attachments, not candidate evidence"
            ),
        ),
        ControlTransition(
            state="observation_requested",
            event="receipt_returned",
            next="observation_receipt_available",
            invariant="receipt binds capability, inputs, and supported claims",
        ),
        ControlTransition(
            state="observation_receipt_available",
            event="request_typed_observation",
            next="observation_requested",
            invariant="additional registered observations may refine alpha before lowering",
        ),
        ControlTransition(
            state="observation_receipt_available",
            event="submit_candidate_delta",
            next="candidate_pending_gate",
            invariant="candidate may cite receipts but receipts cannot promote it",
        ),
        ControlTransition(
            state="observation_receipt_available",
            event="report_tool_gap",
            next="tool_gap_pending",
            invariant=(
                "missing instruments are reported as receipt-bound tool gaps; "
                "tool proposals are optional meta attachments, not candidate evidence"
            ),
        ),
        ControlTransition(
            state="candidate_pending_gate",
            event="gate_passed",
            next="candidate_accepted",
            invariant="promotion authority belongs to replay/holdout/external gate receipts",
        ),
        ControlTransition(
            state="candidate_pending_gate",
            event="gate_failed",
            next="counterexample_open",
            invariant="failed gate yields a new counterexample quotient",
        ),
        ControlTransition(
            state="tool_gap_pending",
            event="gap_rejected_or_budgeted",
            next="counterexample_open",
            invariant="bad or low-yield meta-work must be budgeted or archived",
        ),
        ControlTransition(
            state="tool_gap_pending",
            event="tool_synthesis_card_admitted",
            next="counterexample_open",
            invariant="new instruments alter future observations, not past verdicts",
        ),
    ),
)


BOUNDARY_CEGAR_INVARIANTS = (
    "verifiers and hidden fibers are immutable to the leaf",
    "observations/actions cross the boundary only through registered morphisms",
    "every boundary crossing returns or consumes a typed receipt",
    "tool/capability proposals are meta-work; they do not certify the current candidate",
    "candidate promotion requires gate receipts, not prose or analogy",
)


BOUNDARY_CEGAR_LEDGER_SURFACES: tuple[ControlLedgerSurface, ...] = (
    ControlLedgerSurface(
        surface="candidate_delta",
        contract="submission carrier / PATCH_BASE + PATCH_DELTA",
        authority="replay_holdout_or_external_gate",
    ),
    ControlLedgerSurface(
        surface="leaf_capability_proposal",
        contract="ztare.common.leaf_workbench_contract",
        authority="proposal ledger only; no current-candidate evidence",
    ),
    ControlLedgerSurface(
        surface="tool_synthesis_strategy_card",
        contract="ztare.common.tool_synthesis_contract",
        authority="Strategy Office card plus tool_synthesis_gate",
    ),
    ControlLedgerSurface(
        surface="operator_proposal_card",
        contract="ztare.common.operator_proposal_contract",
        authority="planted synthetic plus adoption gates",
    ),
    ControlLedgerSurface(
        surface="strategy_experiment_card",
        contract="workspace/strategy_experiments.jsonl",
        authority="declared next gate, Strategy discharge, or LOWERABILITY_BLOCKED obstruction",
    ),
)


def _json_object(raw: Any) -> Any:
    if isinstance(raw, (dict, list)):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return json.loads(raw, strict=False)
    except json.JSONDecodeError:
        return None


def validate_lowerability_blocked_receipt(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("LOWERABILITY_BLOCKED requires object `payload`.")
    visible = payload.get("visible_capabilities_attempted")
    if not isinstance(visible, list) or not any(str(item or "").strip() for item in visible):
        raise ValueError(
            "LOWERABILITY_BLOCKED requires non-empty visible_capabilities_attempted."
        )
    family_raw = payload.get("candidate_family_attempted")
    if isinstance(family_raw, list):
        family = ",".join(str(item).strip() for item in family_raw if str(item or "").strip())
    else:
        family = str(family_raw or "").strip()
    if not family:
        raise ValueError("LOWERABILITY_BLOCKED requires candidate_family_attempted.")
    obstruction = str(payload.get("obstruction") or "").strip()
    if not obstruction:
        raise ValueError("LOWERABILITY_BLOCKED requires obstruction.")
    missing = str(payload.get("missing_witness_or_sensor") or "").strip()
    if not missing:
        raise ValueError("LOWERABILITY_BLOCKED requires missing_witness_or_sensor.")
    next_action = str(payload.get("next_action") or "").strip()
    if not next_action:
        raise ValueError("LOWERABILITY_BLOCKED requires next_action.")
    evidence_refs = payload.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not any(str(ref or "").strip() for ref in evidence_refs):
        raise ValueError("LOWERABILITY_BLOCKED requires non-empty evidence_refs.")
    normalized = dict(payload)
    normalized["schema"] = str(normalized.get("schema") or LOWERABILITY_BLOCKED_SCHEMA)
    if normalized["schema"] != LOWERABILITY_BLOCKED_SCHEMA:
        raise ValueError(
            f"LOWERABILITY_BLOCKED schema must be {LOWERABILITY_BLOCKED_SCHEMA!r}."
        )
    normalized["visible_capabilities_attempted"] = [
        str(item).strip() for item in visible if str(item or "").strip()
    ]
    normalized["candidate_family_attempted"] = family
    normalized["obstruction"] = obstruction
    normalized["missing_witness_or_sensor"] = missing
    normalized["next_action"] = next_action
    normalized["evidence_refs"] = [
        str(ref).strip() for ref in evidence_refs if str(ref or "").strip()
    ]
    _validate_visible_attempt_evidence(normalized)
    _validate_missing_feature_search_receipts(normalized)
    ruled_out = normalized.get("ruled_out_visible_morphisms")
    if ruled_out is not None:
        normalized["ruled_out_visible_morphisms"] = _normalize_ruled_out_morphisms(ruled_out)
    evidence_statuses = normalize_evidence_statuses(normalized.get("evidence_statuses"))
    if evidence_statuses:
        normalized["evidence_statuses"] = list(evidence_statuses)
        _validate_consumed_counterexample_accounting(normalized, evidence_statuses)
        _validate_stopping_rationale(normalized, evidence_statuses)
        _validate_local_frontier_decision(normalized, evidence_statuses)
    elif "evidence_statuses" in normalized:
        raise ValueError(
            "LOWERABILITY_BLOCKED evidence_statuses must be a list of "
            f"{{ref,status}} rows with status in {sorted(EVIDENCE_STATUSES)}."
        )
    return normalized


def _validate_stopping_rationale(
    payload: dict[str, Any],
    evidence_statuses: tuple[dict[str, str], ...],
) -> None:
    if not any(row.get("status") == CONSUMED_COUNTEREXAMPLE for row in evidence_statuses):
        return
    rationale = str(
        payload.get("stopping_rationale")
        or payload.get("stop_rationale")
        or payload.get("stop_condition")
        or ""
    ).strip()
    if not rationale:
        raise ValueError(
            "LOWERABILITY_BLOCKED consumed counterexample refs require "
            "`stopping_rationale`: explain why the next visible local action is "
            "not worth or not possible in this same turn."
        )
    payload["stopping_rationale"] = rationale


def _validate_local_frontier_decision(
    payload: dict[str, Any],
    evidence_statuses: tuple[dict[str, str], ...],
) -> None:
    if not any(row.get("status") == CONSUMED_COUNTEREXAMPLE for row in evidence_statuses):
        return
    raw = payload.get("local_frontier_decision")
    if not isinstance(raw, dict):
        raise ValueError(
            "LOWERABILITY_BLOCKED consumed counterexample refs require "
            "`local_frontier_decision`: the visible stopping frontier that made "
            "stopping admissible."
        )
    decision = dict(raw)
    available = _normalize_frontier_actions(decision.get("available_actions"))
    attempted = _normalize_frontier_actions(decision.get("attempted_actions"))
    unattempted = _normalize_frontier_actions(decision.get("unattempted_actions"), allow_empty=True)
    chosen = str(decision.get("chosen") or "").strip().lower()
    if chosen not in {"continue", "stop"}:
        raise ValueError("local_frontier_decision.chosen must be 'continue' or 'stop'.")
    expected_info = str(decision.get("expected_info_note") or "").strip()
    stop_reason = str(decision.get("stop_reason") or "").strip()
    evidence_refs = _normalize_frontier_actions(decision.get("evidence_refs"))
    if not available:
        raise ValueError("local_frontier_decision.available_actions must be non-empty.")
    if not attempted:
        raise ValueError("local_frontier_decision.attempted_actions must be non-empty.")
    if not expected_info:
        raise ValueError("local_frontier_decision.expected_info_note is required.")
    if chosen == "stop" and not stop_reason:
        raise ValueError("local_frontier_decision.stop_reason is required when chosen='stop'.")
    decision["available_actions"] = available
    decision["attempted_actions"] = attempted
    decision["unattempted_actions"] = unattempted
    decision["chosen"] = chosen
    decision["expected_info_note"] = expected_info
    decision["stop_reason"] = stop_reason
    decision["evidence_refs"] = evidence_refs
    payload["local_frontier_decision"] = decision


def _normalize_frontier_actions(raw: object, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(raw, list):
        raise ValueError("local_frontier_decision fields must be lists where lists are expected.")
    out = [str(item or "").strip() for item in raw if str(item or "").strip()]
    if not out and not allow_empty:
        return []
    return out


def _validate_consumed_counterexample_accounting(
    payload: dict[str, Any],
    evidence_statuses: tuple[dict[str, str], ...],
) -> None:
    consumed = {
        str(row.get("ref") or "").strip()
        for row in evidence_statuses
        if row.get("status") == CONSUMED_COUNTEREXAMPLE and str(row.get("ref") or "").strip()
    }
    if not consumed:
        return
    raw_refs = payload.get("evidence_analysis_refs")
    if raw_refs is None:
        raw_refs = payload.get("analysis_refs")
    if not isinstance(raw_refs, list):
        raise ValueError(
            "LOWERABILITY_BLOCKED consumed counterexample refs require "
            "`evidence_analysis_refs`: derived scratch artifacts or visible receipts "
            "showing how the consumed evidence was used for alpha/gamma repair."
        )
    analysis_refs = [str(ref or "").strip() for ref in raw_refs if str(ref or "").strip()]
    if not analysis_refs:
        raise ValueError(
            "LOWERABILITY_BLOCKED consumed counterexample refs require non-empty "
            "`evidence_analysis_refs`."
        )
    if set(analysis_refs).issubset(consumed):
        raise ValueError(
            "LOWERABILITY_BLOCKED evidence_analysis_refs must cite derived analysis "
            "artifacts or visible receipts, not only the consumed raw evidence refs."
        )
    normalized_refs = tuple(dict.fromkeys(analysis_refs))
    payload["evidence_analysis_refs"] = list(normalized_refs)


_MISSING_FEATURE_CLAIM_TOKENS = (
    "missing",
    "lacks",
    "not exposed",
    "not available",
    "absent",
    "unavailable",
    "no exposed",
    "no selector",
    "no feature",
    "no sensor",
    "not derivable",
    "not observable",
    "unobservable",
    "no transportable",
)


def _claim_asserts_missing_feature(payload: dict[str, Any]) -> bool:
    """Return True when obstruction or missing_witness_or_sensor assert a missing state feature."""
    combined = " ".join(
        str(payload.get(key) or "")
        for key in ("obstruction", "missing_witness_or_sensor")
    ).lower()
    return any(token in combined for token in _MISSING_FEATURE_CLAIM_TOKENS)


def _all_receipt_refs(payload: dict[str, Any]) -> list[str]:
    refs = [str(ref or "").strip() for ref in payload.get("evidence_refs") or []]
    for key in ("visible_receipt_refs", "search_receipts"):
        extra = payload.get(key)
        if isinstance(extra, list):
            refs.extend(str(ref or "").strip() for ref in extra)
    return refs


def _validate_missing_feature_search_receipts(payload: dict[str, Any]) -> None:
    """Require search_receipts when obstruction asserts a missing state feature.

    An impossibility claim is a verdict; cite the probe receipts that searched
    for the feature, or run the probe first.
    """
    if not _claim_asserts_missing_feature(payload):
        return
    refs = _all_receipt_refs(payload)
    if any(ref.startswith("workspace/visible_cli_receipts/") for ref in refs):
        return
    raise ValueError(
        "LOWERABILITY_BLOCKED obstruction asserts a missing state feature or "
        "selector but cites no workspace/visible_cli_receipts/* probe receipt in "
        "evidence_refs, visible_receipt_refs, or search_receipts. An impossibility "
        "claim is a verdict; cite the probe receipts that searched for the feature, "
        "or run the probe first."
    )


def _validate_visible_attempt_evidence(payload: dict[str, Any]) -> None:
    attempted = payload.get("visible_capabilities_attempted")
    if not isinstance(attempted, list):
        return
    claim_text = " ".join(str(item or "") for item in attempted).lower()
    try:
        from ztare.common.visible_workbench_actions import visible_workbench_attempt_claim_ids

        tool_tokens = tuple(sorted(visible_workbench_attempt_claim_ids()))
    except Exception:  # noqa: BLE001
        tool_tokens = ()
    if not any(token in claim_text for token in tool_tokens):
        return
    refs = _all_receipt_refs(payload)
    if any(ref.startswith("workspace/visible_cli_receipts/") for ref in refs):
        return
    errors = payload.get("visible_command_errors")
    if isinstance(errors, list):
        for row in errors:
            if not isinstance(row, dict):
                continue
            command = str(row.get("command") or "").strip()
            error = str(row.get("error") or row.get("stderr") or row.get("reason") or "").strip()
            if command and error:
                return
    raise ValueError(
        "LOWERABILITY_BLOCKED visible_capabilities_attempted names visible tools "
        "but cites no workspace/visible_cli_receipts/* ref and no structured "
        "visible_command_errors row. Tool attempts are receipt-bound, not "
        "self-attested."
    )


def _normalize_ruled_out_morphisms(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        raise ValueError("LOWERABILITY_BLOCKED ruled_out_visible_morphisms must be a list.")
    rows: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError(
                "LOWERABILITY_BLOCKED ruled_out_visible_morphisms entries must be "
                "objects with capability_id and reason or evidence_ref."
            )
        capability_id = str(item.get("capability_id") or "").strip()
        reason = str(item.get("reason") or "").strip()
        evidence_ref = str(item.get("evidence_ref") or "").strip()
        if not capability_id or not (reason or evidence_ref):
            raise ValueError(
                "LOWERABILITY_BLOCKED ruled_out_visible_morphisms entries require "
                "capability_id and reason or evidence_ref."
            )
        row = {"capability_id": capability_id}
        if reason:
            row["reason"] = reason
        if evidence_ref:
            row["evidence_ref"] = evidence_ref
        rows.append(row)
    return rows


def _iter_receipt_output_summaries(carried_receipts_json: str) -> list[dict[str, Any]]:
    raw = _json_object(carried_receipts_json)
    if isinstance(raw, dict):
        rows = [raw]
    elif isinstance(raw, list):
        rows = raw
    else:
        return []

    summaries: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else row
        if not isinstance(payload, dict):
            continue
        summary = _json_object(payload.get("output_summary"))
        if isinstance(summary, dict):
            summaries.append(summary)
    return summaries


def _iter_receipt_payloads(carried_receipts_json: str) -> list[dict[str, Any]]:
    raw = _json_object(carried_receipts_json)
    if isinstance(raw, dict):
        rows = [raw]
    elif isinstance(raw, list):
        rows = raw
    else:
        return []

    payloads: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if isinstance(row.get("payload"), dict):
            payload = dict(row["payload"])
            receipt_type = str(row.get("type") or "").strip()
            if receipt_type and "type" not in payload:
                payload["type"] = receipt_type
        else:
            payload = row
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _iter_mapping_objects(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_mapping_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_mapping_objects(child)
    elif isinstance(value, str):
        parsed = _json_object(value)
        if parsed is not None and parsed is not value:
            yield from _iter_mapping_objects(parsed)


def _lowerability_signal(obj: dict[str, Any]) -> bool | None:
    if (
        obj.get("schema") == LOWERABILITY_BLOCKED_SCHEMA
        or str(obj.get("type") or "").strip() == "LOWERABILITY_BLOCKED"
    ):
        validate_lowerability_blocked_receipt(obj.get("payload") if "payload" in obj else obj)
        return False

    explicit = obj.get("candidate_delta_admissible")
    if isinstance(explicit, bool):
        return explicit

    status = str(obj.get("lowerability_status") or "").strip().lower()
    if status in {
        "zero_error_witness_found",
        "lowerable_selector_found",
        "candidate_delta_admissible",
    }:
        return True
    if status in {
        "no_zero_error_selector_found",
        "no_selector_found",
        "blocked_insufficient_visible_data",
        "underdetermined",
    }:
        return False

    predicates = obj.get("candidate_predicates")
    if isinstance(predicates, list):
        return bool(predicates)

    relation = str(obj.get("relation") or obj.get("candidate_relation") or "").strip()
    if relation == "hard_gate_failure_without_visible_quotient":
        return False
    return None


def _coverage_signature(obj: dict[str, Any]) -> tuple[str, tuple[str, ...], tuple[str, ...]] | None:
    coverage = obj.get("candidate_label_coverage")
    if not isinstance(coverage, dict):
        return None
    required_raw = coverage.get("required")
    covered_raw = coverage.get("covered")
    if not isinstance(required_raw, list) or not isinstance(covered_raw, list):
        return None
    required = tuple(sorted({str(row) for row in required_raw if str(row)}))
    covered = tuple(sorted({str(row) for row in covered_raw if str(row)}))
    if not required:
        return None
    source = str(
        obj.get("source_receipt")
        or obj.get("source_ref")
        or obj.get("receipt_ref")
        or obj.get("schema")
        or ""
    )
    return (source, required, covered)


def _receipt_family_has_complete_coverage(objects: list[dict[str, Any]]) -> bool:
    groups: dict[tuple[str, tuple[str, ...]], set[str]] = {}
    for obj in objects:
        signature = _coverage_signature(obj)
        if signature is None:
            continue
        source, required, covered = signature
        if not covered:
            continue
        groups.setdefault((source, required), set()).update(covered)
    for (_, required), covered in groups.items():
        if set(required).issubset(covered):
            return True
    return False


def _candidate_delta_lowerability_from_receipts(
    carried_receipts_json: str,
) -> bool | None:
    """Return whether current receipts authorize a candidate delta.

    ``None`` means the receipts do not speak this contract. ``False`` means a
    receipt explicitly exposes an alpha-chart distinction but no gamma-lowerable
    witness for executable carrier code.
    """

    blocked = False
    objects: list[dict[str, Any]] = []
    for summary in _iter_receipt_output_summaries(carried_receipts_json):
        for obj in _iter_mapping_objects(summary):
            objects.append(obj)
            signal = _lowerability_signal(obj)
            if signal is True:
                return True
            if signal is False:
                blocked = True
    for payload in _iter_receipt_payloads(carried_receipts_json):
        objects.append(payload)
        signal = _lowerability_signal(payload)
        if signal is True:
            return True
        if signal is False:
            blocked = True
        capability_id = str(payload.get("capability_id") or "").strip()
        if capability_id == "inspect_worldmodel_counterexample_context":
            output = str(payload.get("output_summary") or "").strip()
            if output:
                blocked = True
    if blocked:
        return False
    if _receipt_family_has_complete_coverage(objects):
        return True
    return None


def boundary_cegar_candidate_delta_lowerability(
    carried_receipts_json: str,
) -> bool | None:
    """Public query for whether carried receipts allow candidate lowering."""

    return _candidate_delta_lowerability_from_receipts(carried_receipts_json)


def boundary_cegar_admissible_events(
    *,
    state: str,
    carried_receipts_json: str = "",
) -> list[str]:
    events = BOUNDARY_CEGAR_CHART.admissible_events(state)
    if state != "observation_receipt_available":
        return events
    return events


def boundary_cegar_context(
    *,
    executed_morphisms: list[str] | None = None,
    carried_receipts_json: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "invariants": list(BOUNDARY_CEGAR_INVARIANTS),
        "executed_morphisms": executed_morphisms or [],
    }
    lowerability = _candidate_delta_lowerability_from_receipts(carried_receipts_json)
    if lowerability is False:
        context["candidate_delta_warning"] = "no_lowerable_receipt_witness"
        context["next_valid_move"] = (
            "try a transportable candidate if current evidence permits; otherwise "
            "request another typed observation or emit LOWERABILITY_BLOCKED with "
            "the consumed counterexample/status evidence named inside it"
        )
    elif lowerability is True:
        context["candidate_delta_witness"] = "receipt_candidate_predicates"
    if extra:
        context.update(extra)
    return context


def boundary_cegar_state_object(
    *,
    state: str,
    executed_morphisms: list[str] | None = None,
    carried_receipts_json: str = "",
    admissible_next: list[ControlMorphism] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged_context = boundary_cegar_context(
        executed_morphisms=executed_morphisms,
        carried_receipts_json=carried_receipts_json,
        extra=context,
    )
    obj: dict[str, Any] = {
        "schema": SCHEMA,
        "state": state,
        "invariants": list(BOUNDARY_CEGAR_INVARIANTS),
        "ledger_surfaces": control_ledger_surfaces_object(BOUNDARY_CEGAR_LEDGER_SURFACES),
        "executed_morphisms": executed_morphisms or [],
        "admissible_events": boundary_cegar_admissible_events(
            state=state,
            carried_receipts_json=carried_receipts_json,
        ),
        "transition_table": BOUNDARY_CEGAR_CHART.transition_table(),
    }
    if carried_receipts_json:
        obj["carried_receipts_json"] = carried_receipts_json
    if admissible_next:
        obj["admissible_next_morphisms"] = [m.request_object() for m in admissible_next]
    if merged_context:
        obj["context"] = merged_context
    return obj


def render_boundary_cegar_surface(
    *,
    state: str,
    executed_morphisms: list[str] | None = None,
    carried_receipts_json: str = "",
    admissible_next: list[ControlMorphism] | None = None,
    context: dict[str, Any] | None = None,
    heading: str = "SEALED BOUNDARY-CEGAR STATE",
) -> str:
    """Render the boundary protocol as a compact prompt/workbench projection."""

    return (
        f"{heading}:\n"
        + json.dumps(
            boundary_cegar_state_object(
                state=state,
                executed_morphisms=executed_morphisms,
                carried_receipts_json=carried_receipts_json,
                admissible_next=admissible_next,
                context=context,
            ),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        + "\n\n"
    )


def render_boundary_cegar_retry_surface(
    *,
    state: str,
    executed_morphisms: list[str],
    carried_receipts_json: str = "",
    admissible_next: list[ControlMorphism] | None = None,
    no_next_morphism_policy: str | None = None,
) -> str:
    """Retry-friendly surface preserving the existing control-state affordance."""

    events = boundary_cegar_admissible_events(
        state=state,
        carried_receipts_json=carried_receipts_json,
    )
    no_next_policy = (
        "try a candidate delta if current evidence permits; otherwise submit "
        "LOWERABILITY_BLOCKED with the missing witness/sensor and evidence statuses. "
        + SCIENCE_OUTPUT_POLICY.tool_gap_text()
        if "submit_candidate_delta" not in events
        else (
            "submit a candidate delta, request a registered capability, or emit "
            "LOWERABILITY_BLOCKED only if no gamma-lowerable candidate exists."
        )
    )
    context = boundary_cegar_context(
        executed_morphisms=executed_morphisms,
        carried_receipts_json=carried_receipts_json,
    )
    return render_control_state_surface(
        heading="WORKBENCH STATE",
        executed_morphisms=executed_morphisms,
        carried_receipts_json="",
        admissible_next=admissible_next,
        no_next_morphism_policy=no_next_morphism_policy or no_next_policy,
    ) + render_control_state_chart_surface(
        chart=BOUNDARY_CEGAR_CHART,
        state=state,
        context=context,
        admissible_events=events,
        boundary_rule=context.get("next_valid_move", ""),
        heading="SEALED BOUNDARY-CEGAR LIFECYCLE",
    )
