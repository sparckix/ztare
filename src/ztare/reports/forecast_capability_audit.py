"""Audit forecast/reflexive-market capability claims against implementation.

The report keeps three surfaces distinct:

* certified forecast-pool lifecycle: contract -> forecast -> aggregate ->
  resolve -> score -> calibrate;
* uncertified scratch forecasts: useful orientation, but excluded from GP-230
  calibration and membrane close;
* read models: prediction-contract normalization, decision-use rows, and
  operations intelligence.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class ForecastCapabilityRow:
    method_id: str
    implementation_sites: tuple[str, ...]
    required_markers: tuple[str, ...]
    supported_claim: str
    release_boundary: str
    status: str
    notes: str = ""
    markers_found: tuple[str, ...] = field(default_factory=tuple)
    present: bool = False


def _rows() -> tuple[ForecastCapabilityRow, ...]:
    pool = "scripts/public/control/forecast/pool.py"
    return (
        ForecastCapabilityRow(
            method_id="gp230_contract_schema_gate",
            implementation_sites=(
                pool,
                "scripts/public/validators/validate_forecast_contracts.py",
            ),
            required_markers=(
                "REQUIRED_CONTRACT_FIELDS",
                "Validate analytics/public/forecast_pool/contracts/*.json SCHEMA",
                "CONTRACTS = REPO",
                "objective_resolver",
                "success_threshold",
            ),
            supported_claim="forecast-pool contracts have a required schema and validator",
            release_boundary="schema-valid contract does not imply forecast quality or execution success",
            status="ready_receipt_path",
        ),
        ForecastCapabilityRow(
            method_id="read_only_forecast_emission",
            implementation_sites=(pool,),
            required_markers=(
                "REQUIRED_FORECAST_FIELDS",
                "--read-only-attestation is required",
                "cmd_add_forecast",
                "forecast_update_path",
            ),
            supported_claim="forecasters write sealed read-only price artifacts",
            release_boundary="one forecast row is a price, not an independent market signal",
            status="ready_receipt_path",
        ),
        ForecastCapabilityRow(
            method_id="aggregate_allocation_read_model",
            implementation_sites=(pool,),
            required_markers=(
                "def aggregate",
                "allocation_recommendation",
                "compact_aggregate_summary",
                "p_success",
            ),
            supported_claim="aggregates expose compact probability, effort, risk, and allocation hints",
            release_boundary="allocation hints remain advisory unless decision-use rows show causal use",
            status="ready_receipt_path",
        ),
        ForecastCapabilityRow(
            method_id="objective_resolution_scoring",
            implementation_sites=(pool,),
            required_markers=(
                "def cmd_score",
                "brier_score",
                "temporal_audit",
                "failure_mode_externality_score",
            ),
            supported_claim="resolved forecast-pool contracts receive artifact-backed Brier and externality scores",
            release_boundary="voided or unresolved contracts are not calibration evidence",
            status="ready_receipt_path",
        ),
        ForecastCapabilityRow(
            method_id="calibration_weight_update",
            implementation_sites=(pool,),
            required_markers=(
                "def calibration_payload",
                "bounded_weight_from_brier",
                "second_moment_channels",
                "requires_explicit_calibrate_write",
            ),
            supported_claim="score artifacts can update calibration weights and effort priors explicitly",
            release_boundary="small samples are shrunk; weights are advisory, not a veto or scheduler",
            status="ready_receipt_path",
        ),
        ForecastCapabilityRow(
            method_id="scratch_forecast_semantics",
            implementation_sites=(pool,),
            required_markers=(
                "def cmd_scratch_forecast",
                "excluded_from_calibration",
                "can_satisfy_membrane",
                "forecast_pool_semantics",
                "def cmd_scratch_resolve",
            ),
            supported_claim="scratch forecasts are explicit uncertified orientation/self-bet artifacts",
            release_boundary="scratch forecasts are not GP-230 contracts and cannot satisfy membrane close",
            status="ready_receipt_path",
        ),
        ForecastCapabilityRow(
            method_id="decision_use_logging",
            implementation_sites=(pool,),
            required_markers=(
                "def cmd_record_decision_use",
                "DECISION_USE_LEDGER",
                "decision_changed_bool",
                "failure_modes_adopted",
            ),
            supported_claim="forecast use can be logged as a causal action record",
            release_boundary="forecasts are allocation evidence only when decision-use rows exist",
            status="ready_receipt_path",
        ),
        ForecastCapabilityRow(
            method_id="prediction_contract_read_model",
            implementation_sites=(
                "src/ztare/forecasting/prediction_contract.py",
                "src/ztare/validator/autoresearch_prediction_contract.py",
            ),
            required_markers=(
                "normalize_prediction_contract",
                "scratch_contract",
                "forecast_pool",
                "missing_forecast_pool_authority_anchor",
                "score_binary_prediction_contract",
                "summarize_prediction_contract_rows",
                "_prediction_authority_summary",
                "routing_authority",
                "invalid_routing_authority_claim",
                "invalid_decision_use_bypass_claim",
            ),
            supported_claim=(
                "forecast-pool, scratch, prediction-ledger, and autoresearch rows "
                "share one scoreable read model with explicit authority boundaries"
            ),
            release_boundary=(
                "the read model scores and audits receipts; trace has no routing "
                "authority without separate decision-use evidence"
            ),
            status="ready_receipt_path",
        ),
        ForecastCapabilityRow(
            method_id="operations_intelligence_consumer",
            implementation_sites=("src/ztare/reports/operations_intelligence.py",),
            required_markers=(
                "summarize_forecast_market",
                "decision_use_gap",
                "decision_use_rate",
                "forecast_decision_use_rate",
            ),
            supported_claim="operations intelligence surfaces forecast coverage and decision-use gaps",
            release_boundary="low decision-use coverage means market signal is not yet allocation evidence",
            status="ready_receipt_path",
        ),
    )


def _read_site(repo: Path, site: str) -> str:
    path = repo / site
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _markers_found(repo: Path, row: ForecastCapabilityRow) -> tuple[str, ...]:
    texts = [_read_site(repo, site) for site in row.implementation_sites]
    found: list[str] = []
    for marker in row.required_markers:
        if any(marker in text for text in texts):
            found.append(marker)
    return tuple(found)


def build_forecast_capability_audit(repo: Path | str = REPO) -> dict:
    """Return the forecast/reflexive-market capability audit."""
    repo_path = Path(repo)
    rows: list[ForecastCapabilityRow] = []
    for row in _rows():
        found = _markers_found(repo_path, row)
        rows.append(
            ForecastCapabilityRow(
                **{
                    **asdict(row),
                    "markers_found": found,
                    "present": len(found) == len(row.required_markers),
                }
            )
        )

    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1

    missing_rows = [row.method_id for row in rows if not row.present]
    ready_paths = [
        row.method_id
        for row in rows
        if row.present and row.status == "ready_receipt_path"
    ]
    verdict = {
        "not_hidden_scheduler": True,
        "strongest_supported_claim": (
            "ZTARE has a sealed forecast-pool lifecycle, uncertified scratch "
            "self-bets, a shared prediction-contract read model, and "
            "decision-use accounting surfaces."
        ),
        "release_boundary": (
            "Do not claim forecasts steer autoresearch, LeanMill, or RD work "
            "unless resolved rows beat simple baselines and decision-use rows "
            "show causal routing. Scratch forecasts stay uncertified."
        ),
        "needs_before_stronger_claim": (
            "increase decision-use coverage and publish calibration/decision-use "
            "lift before promoting forecast scores into controllers"
        ),
    }
    return {
        "schema": "ztare-forecast-capability-audit-v1",
        "summary": {
            "row_count": len(rows),
            "present_count": sum(1 for row in rows if row.present),
            "missing_count": len(missing_rows),
            "status_counts": status_counts,
            "ready_receipt_paths": ready_paths,
            "missing_rows": missing_rows,
        },
        "verdict": verdict,
        "rows": [asdict(row) for row in rows],
    }


def render_text(report: dict) -> str:
    lines = ["Forecast capability audit", ""]
    summary = report["summary"]
    lines.append(
        f"Rows: {summary['row_count']} | present: {summary['present_count']} | "
        f"missing: {summary['missing_count']}"
    )
    lines.append(f"Strongest supported claim: {report['verdict']['strongest_supported_claim']}")
    lines.append(f"Release boundary: {report['verdict']['release_boundary']}")
    lines.append(f"Needs before stronger claim: {report['verdict']['needs_before_stronger_claim']}")
    lines.append("")
    for row in report["rows"]:
        status = "ok" if row["present"] else "missing"
        lines.append(f"- {row['method_id']}: {status} [{row['status']}]")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_forecast_capability_audit()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
