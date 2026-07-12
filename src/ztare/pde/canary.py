"""PDE canary re-ingestion for hard estimate loops.

The readiness receipt says the kernel can dispatch work.  This module checks
the next step: a gate bundle from a physical canary must become reusable state:
precise next leaves, project-local failure memory rows, and formal-surface rows.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ztare.pde.formal_surface_status import build_pde_formal_surface_map


TICK669_PHYSICAL_CANARY_TARGETS = (
    "uniform_annular_riesz_l1_on_fixed_bandlimited_annular_carrier",
    "psd_trace_to_projected_tracefree_payment",
    "cutoff_commutator_tail_payment_on_same_stream",
    "selected_psd_owner_prefix_no_reuse_budget",
    "nonadaptive_annular_event_stream_identity",
)

PHYSICAL_ACCOUNTING_CANARY_TARGETS = (
    "physical_dimensional_homogeneity",
    "physical_balance_flux_boundary_invoice",
    "physical_localization_carrier_identity",
    "physical_sign_operator_tail_invoice",
)

EQUALITY_PROVENANCE_CANARY_TARGETS = (
    "source_equality_provenance",
    "source_equality_provenance_for_projected_packet_payment",
    "constructor_or_theorem_pays_tracefree_to_event_payment_identity",
    "anti_proxy_stream_binding_for_payment_equality",
)


_PHYSICAL_OBLIGATIONS = {
    "uniform_annular_riesz_l1_on_fixed_bandlimited_annular_carrier": {
        "physical_quantity": "same-carrier annular kernel mass",
        "must_pay": "operator endpoint payment on the fixed pre-payoff band",
        "forbidden_shortcut": "raw global CZ bound",
    },
    "psd_trace_to_projected_tracefree_payment": {
        "physical_quantity": "positive defect trace after Leray/Riesz projection",
        "must_pay": "projection loss or positivity-preserving exchange",
        "forbidden_shortcut": "signed moment treated as total variation",
    },
    "cutoff_commutator_tail_payment_on_same_stream": {
        "physical_quantity": "low-high/cutoff leakage energy",
        "must_pay": "tail invoice on the selected annular stream",
        "forbidden_shortcut": "discarded commutator",
    },
    "selected_psd_owner_prefix_no_reuse_budget": {
        "physical_quantity": "one PSD packet charged to one owner-prefix budget",
        "must_pay": "multiplicity/no-rebilling bound",
        "forbidden_shortcut": "one trace packet spent many times",
    },
    "nonadaptive_annular_event_stream_identity": {
        "physical_quantity": "pre-payoff selected event stream",
        "must_pay": "source identity before terminal radius-sum observation",
        "forbidden_shortcut": "post-selected annular packet",
    },
}


@dataclass(frozen=True)
class PDECanaryFailureMemoryRow:
    schema: str
    target: str
    source_gate_id: str
    failure_class: str
    witness: str
    rejected_substitutes: list[str]
    hostile_packets: list[str]
    next_targets: list[str]
    source_artifacts: list[str]
    leanmill_policy: str


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value in (None, ""):
        return []
    return [value]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _resolved_canary_targets(physical_receipt: dict[str, Any] | None) -> set[str]:
    receipt = physical_receipt or {}
    compression = (
        receipt.get("current_compression")
        if isinstance(receipt.get("current_compression"), dict)
        else {}
    )
    values = (
        _as_list(receipt.get("resolved_physical_targets"))
        + _as_list(receipt.get("paid_physical_targets"))
        + _as_list(receipt.get("paid_canary_targets"))
        + _as_list(receipt.get("upstream_explicit_targets"))
        + _as_list(receipt.get("out_of_scope_canary_targets"))
        + _as_list(compression.get("resolved_physical_targets"))
        + _as_list(compression.get("paid_physical_targets"))
        + _as_list(compression.get("paid_canary_targets"))
        + _as_list(compression.get("upstream_explicit_targets"))
        + _as_list(compression.get("out_of_scope_canary_targets"))
    )
    return {str(item) for item in values if str(item).strip()}


def _required_canary_targets(physical_receipt: dict[str, Any] | None) -> tuple[str, ...]:
    resolved = _resolved_canary_targets(physical_receipt)
    return tuple(
        target for target in TICK669_PHYSICAL_CANARY_TARGETS
        if target not in resolved
    )


def _result_by_gate(gate_run_bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _as_list(gate_run_bundle.get("results")):
        if isinstance(row, dict) and row.get("gate_id"):
            rows[str(row["gate_id"])] = row
    return rows


def _canonical_next_units(gate_run_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    units: list[dict[str, Any]] = []
    canonical = set(TICK669_PHYSICAL_CANARY_TARGETS)
    for unit in _as_list(gate_run_bundle.get("next_required_work_units")):
        if not isinstance(unit, dict):
            continue
        target = _text(unit.get("target"))
        if target not in canonical or target in seen:
            continue
        seen.add(target)
        merged = dict(unit)
        obligation = _PHYSICAL_OBLIGATIONS.get(target, {})
        if obligation:
            merged["physical_obligation"] = obligation
        units.append(merged)
    return units


def _physical_accounting_next_units(gate_run_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    units: list[dict[str, Any]] = []
    canonical = set(PHYSICAL_ACCOUNTING_CANARY_TARGETS)
    for unit in _as_list(gate_run_bundle.get("next_required_work_units")):
        if not isinstance(unit, dict):
            continue
        target = _text(unit.get("target"))
        if target not in canonical or target in seen:
            continue
        seen.add(target)
        units.append(dict(unit))
    return units


def _equality_provenance_next_units(gate_run_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    units: list[dict[str, Any]] = []
    canonical = set(EQUALITY_PROVENANCE_CANARY_TARGETS)
    for unit in _as_list(gate_run_bundle.get("next_required_work_units")):
        if not isinstance(unit, dict):
            continue
        target = _text(unit.get("target"))
        if target not in canonical or target in seen:
            continue
        seen.add(target)
        units.append(dict(unit))
    return units


def _failed_gate_witnesses(gate_run_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    for row in _as_list(gate_run_bundle.get("results")):
        if not isinstance(row, dict) or row.get("passed") is True:
            continue
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        witness = _text(result.get("classification")) or _text(row.get("error"))
        rejected = [str(item) for item in _as_list(row.get("rejected_substitutes"))]
        failed.append({
            "gate_id": _text(row.get("gate_id")),
            "complete": bool(row.get("complete")),
            "failure_class": witness or "gate_failed",
            "rejected_substitutes": rejected,
            "missing_fields": [str(item) for item in _as_list(row.get("missing_fields"))],
        })
    return failed


def build_pde_failure_memory_rows(
    *,
    target: str,
    gate_run_bundle: dict[str, Any],
    physical_receipt: dict[str, Any] | None = None,
    source_artifacts: list[str] | tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    """Build project-local PDE failure-memory rows from a canary gate bundle.

    These rows are not LeanMill no-good writes.  LeanMill's no-good store is
    statement-keyed; this memory is physical-obligation keyed until a formal
    Lean statement is supplied.
    """
    next_units = _canonical_next_units(gate_run_bundle)
    next_targets = [_text(unit.get("target")) for unit in next_units]
    artifacts = [str(item) for item in source_artifacts if str(item).strip()]
    receipt_path = _text((physical_receipt or {}).get("artifact"))
    if receipt_path:
        artifacts.append(receipt_path)
    rows: list[dict[str, Any]] = []
    for failed in _failed_gate_witnesses(gate_run_bundle):
        gate_id = failed["gate_id"]
        if gate_id not in (
            "G-PDE-OPERATOR-ADMISSIBILITY",
            "G-PDE-PHYSICAL-ACCOUNTING",
            "G-PDE-EQUALITY-PROVENANCE",
        ):
            continue
        hostile_packets = []
        candidate_units = list(next_units)
        if gate_id == "G-PDE-PHYSICAL-ACCOUNTING":
            candidate_units = _physical_accounting_next_units(gate_run_bundle)
        if gate_id == "G-PDE-EQUALITY-PROVENANCE":
            candidate_units = _equality_provenance_next_units(gate_run_bundle)
        for unit in candidate_units:
            must_return = unit.get("must_return")
            if isinstance(must_return, dict):
                packet = _text(must_return.get("hostile_packet_tested"))
                if packet and packet not in hostile_packets:
                    hostile_packets.append(packet)
        if gate_id == "G-PDE-PHYSICAL-ACCOUNTING":
            witness = (
                "raw pressure route did not pay physical balance, dimensional, "
                "flux/boundary, carrier, sign, projection, cutoff, and tail invoices"
            )
            next_for_row = [_text(unit.get("target")) for unit in candidate_units]
        elif gate_id == "G-PDE-EQUALITY-PROVENANCE":
            witness = (
                "raw pressure/CZ evidence exposed a projected payment equality "
                "without a constructor, theorem, or source-binding proof paying "
                "the identity between the tracefree valuation stream and the "
                "event-radius target stream"
            )
            next_for_row = [_text(unit.get("target")) for unit in candidate_units]
        else:
            witness = (
                "raw pressure/CZ evidence did not pay annular same-carrier "
                "operator, projection, cutoff, owner-prefix, and event-stream fields"
            )
            next_for_row = next_targets
        row = PDECanaryFailureMemoryRow(
            schema="pde-failure-memory-row-v1",
            target=_text(target),
            source_gate_id=gate_id,
            failure_class=failed["failure_class"] or "operator_admissibility_unpaid",
            witness=witness,
            rejected_substitutes=list(failed.get("rejected_substitutes") or []),
            hostile_packets=hostile_packets,
            next_targets=next_for_row,
            source_artifacts=artifacts,
            leanmill_policy=(
                "project_pde_memory_only_until_a_formal_statement_key_is_supplied"
            ),
        )
        rows.append(asdict(row))
    return rows


def _default_surface_records(
    *,
    source_profile: str,
    next_units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for unit in next_units:
        target = _text(unit.get("target"))
        if not target:
            continue
        obligation = _PHYSICAL_OBLIGATIONS.get(target, {})
        records.append({
            "primitive_id": target,
            "title": _text(unit.get("goal")) or target,
            "status": "informal_only",
            "source_profile": source_profile,
            "statement": _text((unit.get("must_return") or {}).get("target_inequality_or_statement"))
            if isinstance(unit.get("must_return"), dict) else "",
            "dependencies": [str(item) for item in _as_list(unit.get("required_gate_ids"))],
            "gaps": [
                _text(obligation.get("must_pay")),
                f"forbid: {_text(obligation.get('forbidden_shortcut'))}",
            ],
            "notes": _text(obligation.get("physical_quantity")),
        })
    return records


def build_pde_canary_reingestion_receipt(
    *,
    readiness_receipt: dict[str, Any],
    gate_run_bundle: dict[str, Any],
    physical_receipt: dict[str, Any] | None = None,
    formal_surface_records: list[dict[str, Any]] | None = None,
    source_profile: str = "tick669_c7_fresh_annular_same_source",
    source_artifacts: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    """Build the canary loop report requested by the PDE-kernel review."""
    target = _text(readiness_receipt.get("target")) or "annular_bandlimited_riesz_l1_psd_trace_payment"
    required_canary_targets = _required_canary_targets(physical_receipt)
    resolved_canary_targets = sorted(_resolved_canary_targets(physical_receipt))
    results = _result_by_gate(gate_run_bundle)
    next_units = _canonical_next_units(gate_run_bundle)
    physical_next_units = _physical_accounting_next_units(gate_run_bundle)
    equality_next_units = _equality_provenance_next_units(gate_run_bundle)
    next_targets = [_text(unit.get("target")) for unit in next_units]
    failure_rows = build_pde_failure_memory_rows(
        target=target,
        gate_run_bundle=gate_run_bundle,
        physical_receipt=physical_receipt,
        source_artifacts=source_artifacts,
    )
    surface_records = list(formal_surface_records or [])
    if not surface_records:
        surface_records = _default_surface_records(
            source_profile=source_profile,
            next_units=next_units,
        )
    surface_map = build_pde_formal_surface_map(
        surface_records,
        target=target,
        required_primitives=required_canary_targets,
        source_profile=source_profile,
    )
    readiness_scoreboard = (
        readiness_receipt.get("scoreboard")
        if isinstance(readiness_receipt.get("scoreboard"), dict)
        else {}
    )
    scoreboard = {
        "kernel_import_readiness": bool(readiness_scoreboard.get("kernel_import_readiness")),
        "cli_surface_completeness": bool(readiness_scoreboard.get("cli_surface_completeness")),
        "workbench_consumes_kernel": bool(readiness_scoreboard.get("workbench_consumes_kernel")),
        "tick669_work_order_generated": bool(readiness_receipt.get("canary_work_order")),
        "tick669_gates_run": (
            "G-PDE-ANALYTIC-SUBSTANCE" in results
            and "G-PDE-PHYSICAL-ACCOUNTING" in results
            and "G-PDE-EQUALITY-PROVENANCE" in results
            and "G-PDE-OPERATOR-ADMISSIBILITY" in results
        ),
        "next_work_units_emitted": set(required_canary_targets).issubset(set(next_targets)),
        "leaf_result_reingested": bool(gate_run_bundle.get("results")),
        "failure_memory_updated": bool(failure_rows),
        "formal_surface_row_updated": not bool(surface_map.get("missing_required_primitives")),
    }
    operator_result = results.get("G-PDE-OPERATOR-ADMISSIBILITY") or {}
    analytic_result = results.get("G-PDE-ANALYTIC-SUBSTANCE") or {}
    physical_result = results.get("G-PDE-PHYSICAL-ACCOUNTING") or {}
    equality_result = results.get("G-PDE-EQUALITY-PROVENANCE") or {}
    return {
        "schema": "pde-canary-reingestion-receipt-v1",
        "target": target,
        "source_profile": source_profile,
        "kernel_loop_ready": all(scoreboard.values()),
        "scoreboard": scoreboard,
        "gate_run_summary": (
            gate_run_bundle.get("summary")
            if isinstance(gate_run_bundle.get("summary"), dict)
            else {}
        ),
        "canary_math_verdict": {
            "candidate_route": "localized pressure CZ/Riesz pressure-tail control",
            "analytic_substance_passed": bool(analytic_result.get("passed")),
            "physical_accounting_passed": bool(physical_result.get("passed")),
            "equality_provenance_passed": bool(equality_result.get("passed")),
            "operator_payment_passed": bool(operator_result.get("passed")),
            "verdict": (
                "NEED_THEOREM"
                if not operator_result.get("passed") or not equality_result.get("passed")
                else "CLOSE"
            ),
            "first_failed_line": (
                "annular Riesz/Leray payment and projected payment equality "
                "were not paid on the same fixed source carrier after projection "
                "and cutoff"
            ),
        },
        "physical_accounting": {
            "workbench_blind_spot": (
                "a syntactically plausible pressure estimate is insufficient "
                "without carrier, projection, endpoint, cutoff, owner, and "
                "selection invoices"
            ),
            "obligations": _PHYSICAL_OBLIGATIONS,
            "resolved_canary_targets": resolved_canary_targets,
            "required_canary_targets": list(required_canary_targets),
        },
        "next_leaf_work_orders": next_units,
        "physical_accounting_work_orders": physical_next_units,
        "equality_provenance_work_orders": equality_next_units,
        "failure_memory_rows": failure_rows,
        "formal_surface_map": surface_map,
        "failed_gate_witnesses": _failed_gate_witnesses(gate_run_bundle),
        "credit_boundary": (
            "canary_reingestion_tracks_work; it grants no PDE estimate credit "
            "without the emitted leaf proofs, hostile-packet survival, and "
            "formal/compiler evidence where claimed"
        ),
    }


def write_pde_failure_memory_jsonl(rows: list[dict[str, Any]], path: str | Path) -> int:
    """Append failure-memory rows as JSONL. Returns number of rows written."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    existing: set[str] = set()
    if out.exists():
        existing = {
            line.strip()
            for line in out.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
    written = 0
    with out.open("a", encoding="utf-8") as handle:
        for row in rows:
            line = json.dumps(row, sort_keys=True)
            if line in existing:
                continue
            handle.write(line + "\n")
            existing.add(line)
            written += 1
    return written
