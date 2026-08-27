"""Project accounting, research, and strategy artifacts into a business anatomy."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .company_quality import COMPANY_QUALITY_SCHEMA
from .contracts import canonical_timestamp, require_text, timestamp_key


BUSINESS_FINGERPRINT_SCHEMA = "jaggedthoughts-business-fingerprint-v1"

_DERIVED_COORDINATES = {
    "revenue_cagr": ("durability", "decimal_per_year"),
    "positive_revenue_growth_share": ("durability", "decimal"),
    "revenue_growth_volatility": ("fragility", "decimal"),
    "positive_owner_earnings_share": ("durability", "decimal"),
    "median_owner_earnings_margin": ("durability", "decimal"),
    "median_cash_conversion": ("durability", "multiple"),
    "median_accrual_ratio": ("durability", "decimal"),
    "owner_earnings_variability": ("fragility", "coefficient"),
    "latest_net_debt": ("fragility", "filing_currency"),
    "net_debt_to_owner_earnings": ("fragility", "multiple"),
    "revenue_durability": ("durability", "score"),
    "earnings_quality": ("durability", "score"),
    "balance_sheet_resilience": ("fragility", "score"),
    "durable_earnings_power": ("durability", "score"),
}


def _verified(payload: Mapping[str, Any], field: str, label: str) -> tuple[dict[str, Any], str]:
    body = dict(payload)
    declared = require_text(body.pop(field, ""), f"{label} {field}")
    if len(declared) != 64 or stable_sha256(body) != declared:
        raise ValueError(f"{label} content hash mismatch")
    return {**body, field: declared}, declared


def _dossier_identity(dossier: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    body = dict(dossier)
    declared = str(body.pop("dossier_sha256", "") or "")
    digest = stable_sha256(body)
    if declared and declared != digest:
        raise ValueError("research dossier content hash mismatch")
    payload = {**body, **({"dossier_sha256": declared} if declared else {})}
    return payload, {
        "sha256": declared or digest,
        "integrity": "declared_and_verified" if declared else "computed_unattested",
    }


def _observed_coordinate(quality: Mapping[str, Any]) -> dict[str, Any]:
    history = [{
        key: row.get(key) for key in (
            "observed_at", "available_at", "revenue", "operating_cash_flow",
            "capital_expenditure", "net_income", "assets", "observation_ids", "source_refs",
        )
    } for row in quality.get("history", ())]
    return {
        "coordinate_id": "aligned_annual_fundamental_history",
        "coordinate_kind": "observed",
        "axes": ["durability", "fragility"],
        "value": history,
        "unit": "filing_currency",
        "observation_ids": list(quality.get("observation_ids") or ()),
        "source_refs": list(quality.get("source_refs") or ()),
        "comparability_scope": "within_entity_time_series; accounting definitions must match",
    }


def _derived_coordinates(quality: Mapping[str, Any], report_sha: str) -> list[dict[str, Any]]:
    values = {**dict(quality.get("metrics") or {}), **dict(quality.get("scores") or {})}
    rows = []
    for coordinate_id, (axis, unit) in _DERIVED_COORDINATES.items():
        if coordinate_id not in values or values[coordinate_id] is None:
            continue
        rows.append({
            "coordinate_id": coordinate_id,
            "coordinate_kind": "derived",
            "axis": axis,
            "value": values[coordinate_id],
            "unit": unit,
            "derived_from_quality_report_sha256": report_sha,
            "observation_ids": list(quality.get("observation_ids") or ()),
            "source_refs": list(quality.get("source_refs") or ()),
            "comparability_scope": (
                "screen heuristic; not a cross-industry rank" if unit == "score"
                else "definition-matched public companies with accounting normalization"
            ),
        })
    return rows


def _qualitative_coordinates(dossier: Mapping[str, Any]) -> list[dict[str, Any]]:
    bridge = dict(dossier.get("durable_earnings_bridge") or {})
    industry = dict(dossier.get("industry") or {})
    strategy = dict(dossier.get("strategy") or {})
    source_refs = sorted({
        str(row.get("id")) for row in dossier.get("sources", ())
        if isinstance(row, Mapping) and row.get("id")
    })
    definitions = (
        ("revenue_concentration_narrative", "revenue_concentration",
         bridge.get("concentration_and_fragility")),
        ("revenue_durability_mechanism", "durability", bridge.get("revenue_durability")),
        ("earnings_quality_adjustments", "fragility", bridge.get("earnings_quality_adjustments")),
        ("reinvestment_and_capital_allocation", "durability",
         bridge.get("reinvestment_and_capital_allocation")),
        ("industry_customer_and_supplier_power", "fragility",
         industry.get("customer_and_supplier_power")),
        ("industry_cycle_and_regulation", "fragility", industry.get("cycle_and_regulation")),
        ("strategy_choice_system", "durability", {
            "choices": strategy.get("choices") or [],
            "reinforcing_edges": strategy.get("reinforcing_edges") or [],
            "tradeoffs": strategy.get("tradeoffs") or [],
        }),
    )
    return [{
        "coordinate_id": coordinate_id,
        "coordinate_kind": "qualitative",
        "axis": axis,
        "value": value,
        "unit": "source_bound_narrative",
        "source_refs": source_refs,
        "comparability_scope": "entity-specific mechanism; no scalar cross-industry ordering",
    } for coordinate_id, axis, value in definitions if value]


def _typed_business_coordinates(dossier: Mapping[str, Any]) -> list[dict[str, Any]]:
    axes = {
        "customer_revenue_concentration": "revenue_concentration",
        "segment_revenue_concentration": "revenue_concentration",
        "geographic_revenue_concentration": "revenue_concentration",
        "segment_economics": "durability",
    }
    return [{
        "coordinate_id": str(row["coordinate_id"]), "coordinate_kind": "observed",
        "axis": axes[str(row["coordinate_id"])],
        "value": {
            "observations": list(row.get("observations") or ()),
            "derivations": list(row.get("derivations") or ()),
        }, "unit": row.get("unit"),
        "observed_at": row.get("observed_at"), "available_at": row.get("available_at"),
        "source_refs": list(row.get("source_refs") or ()),
        "comparability_scope": str(row.get("scope_definition") or "entity-specific disclosure"),
    } for row in dossier.get("business_coordinates") or ()
        if isinstance(row, Mapping) and row.get("status") == "observed"
        and row.get("coordinate_id") in axes and row.get("observations")]


def _frontier_coordinate(frontier: Mapping[str, Any], frontier_sha: str) -> dict[str, Any]:
    return {
        "coordinate_id": "strategy_option_frontier_structure",
        "coordinate_kind": "derived",
        "axis": "durability",
        "value": {
            "program_count": len(frontier.get("programs") or ()),
            "frontier_program_count": len(frontier.get("frontier_program_ids") or ()),
            "local_peak_program_count": len(frontier.get("local_peak_program_ids") or ()),
            "scope_closed": bool(frontier.get("scope_closed")),
            "decision_closed": bool(frontier.get("decision_closed")),
            "pressure_to_option_coverage": dict(frontier.get("pressure_to_option_coverage") or {}),
        },
        "unit": "enumerated_program_topology",
        "strategy_frontier_sha256": frontier_sha,
        "comparability_scope": (
            "compiler topology only; ordinal company effects and option semantics are not "
            "cross-industry economic magnitudes"
        ),
    }


def compile_business_fingerprint(
    *, company_quality: Mapping[str, Any], research_dossier: Mapping[str, Any] | None = None,
    strategy_frontier: Mapping[str, Any] | None = None, compiled_at: str,
) -> dict[str, Any]:
    """Join existing evidence without producing a score, rank, or capital conclusion."""
    quality, quality_sha = _verified(
        company_quality, "quality_report_sha256", "company quality report"
    )
    if quality.get("schema") != COMPANY_QUALITY_SCHEMA:
        raise ValueError(f"business fingerprint requires {COMPANY_QUALITY_SCHEMA}")
    entity = require_text(quality.get("entity_id"), "business fingerprint entity_id").upper()
    compiled = canonical_timestamp(compiled_at, "business fingerprint compiled_at")
    components: dict[str, Any] = {
        "company_quality": {
            "sha256": quality_sha, "as_of": quality["as_of"],
            "available_at": quality["available_at"], "integrity": "declared_and_verified",
        }
    }
    coordinates = [_observed_coordinate(quality), *_derived_coordinates(quality, quality_sha)]
    unknowns = list(quality.get("residuals") or ())
    dossier: dict[str, Any] | None = None
    if research_dossier is not None:
        dossier, dossier_identity = _dossier_identity(research_dossier)
        if dossier.get("schema") != "jaggedthoughts-candidate-research-dossier-v1":
            raise ValueError("business fingerprint research dossier has an unsupported schema")
        if str(dossier.get("entity_id") or "").upper() != entity:
            raise ValueError("research dossier and company quality entities differ")
        if timestamp_key(canonical_timestamp(dossier.get("generated_at"), "dossier generated_at")) > timestamp_key(compiled):
            raise ValueError("business fingerprint compilation precedes its research dossier")
        components["research_dossier"] = {
            **dossier_identity, "candidate_leaf": dossier.get("candidate_leaf"),
            "as_of": dossier.get("as_of"), "generated_at": dossier.get("generated_at"),
        }
        coordinates.extend((*_qualitative_coordinates(dossier), *_typed_business_coordinates(dossier)))
        unknowns.extend((dossier.get("strategy") or {}).get("representation_residuals") or ())
        if not dossier.get("dossier_sha256"):
            unknowns.append("Research dossier has no declared content hash or submitted lifecycle identity.")
    else:
        unknowns.append("Source-bound qualitative research dossier is absent.")

    if strategy_frontier is not None:
        frontier, frontier_sha = _verified(
            strategy_frontier, "strategy_frontier_sha256", "company strategy frontier"
        )
        if frontier.get("schema") != "jaggedthoughts-company-strategy-frontier-v1":
            raise ValueError("business fingerprint strategy frontier has an unsupported schema")
        company = dict(frontier.get("company") or {})
        if str(company.get("id") or "").upper() != entity:
            raise ValueError("strategy frontier and company quality entities differ")
        if dossier and company.get("candidate_leaf") != dossier.get("candidate_leaf"):
            raise ValueError("strategy frontier and dossier candidate leaves differ")
        source_dossier_sha = company.get("source_dossier_sha256")
        if source_dossier_sha and source_dossier_sha != dossier.get("dossier_sha256"):
            raise ValueError("strategy frontier and dossier digests differ")
        if timestamp_key(canonical_timestamp(
            frontier.get("evidence_epoch"), "strategy frontier evidence_epoch"
        )) > timestamp_key(compiled):
            raise ValueError("business fingerprint compilation precedes its strategy frontier")
        components["strategy_frontier"] = {
            "sha256": frontier_sha, "evidence_epoch": frontier.get("evidence_epoch"),
            "scope_closed": bool(frontier.get("scope_closed")),
            "decision_closed": bool(frontier.get("decision_closed")),
            "integrity": "declared_and_verified",
        }
        coordinates.append(_frontier_coordinate(frontier, frontier_sha))
        if not frontier.get("scope_closed"):
            unknowns.append("Strategy option scope remains open.")
        if not frontier.get("decision_closed"):
            unknowns.append("Strategy enumeration does not settle a business decision.")
    else:
        unknowns.append("Source-bound strategy option frontier is absent.")

    kinds_by_axis = {
        axis: sorted({
            row["coordinate_kind"] for row in coordinates
            if row.get("axis") == axis or axis in row.get("axes", ())
        }) for axis in ("revenue_concentration", "fragility", "durability")
    }
    axis_coverage = {
        axis: {
            "coordinate_kinds": kinds,
            "status": "absent" if not kinds else "qualitative_only" if kinds == ["qualitative"]
            else "partial_multi_method",
        } for axis, kinds in kinds_by_axis.items()
    }
    if "observed" not in kinds_by_axis["revenue_concentration"]:
        unknowns.append(
            "Customer, segment, geography, and contract concentration lack typed numeric observations; "
            "figures embedded in dossier prose remain qualitative coordinates."
        )
    body = {
        "schema": BUSINESS_FINGERPRINT_SCHEMA,
        "fingerprint_id": f"business:{entity}:{quality_sha[:16]}",
        "entity_id": entity,
        "compiled_at": compiled,
        "component_identity": components,
        "coordinates": coordinates,
        "axis_coverage": axis_coverage,
        "unknowns": sorted(set(str(value) for value in unknowns if str(value).strip())),
        "cross_industry_comparability": {
            "allowed": False,
            "limits": [
                "Fixed quality scores are triage heuristics, not industry-neutral percentiles.",
                "Margins, cash conversion, accruals, leverage, and cyclicality require matched accounting and business-model definitions.",
                "Customer concentration requires matched customer grouping, period, and revenue denominator.",
                "Qualitative mechanisms and strategy-frontier ordinal effects have no shared economic scale across industries.",
            ],
        },
        "use_boundary": (
            "Business-understanding projection only; no expected-return estimate, opportunity rank, "
            "valuation conclusion, or capital authority."
        ),
        "capital_authority": False,
    }
    return {**body, "business_fingerprint_sha256": stable_sha256(body)}


def _latest_dossier(root: Path, entity_id: str) -> dict[str, Any] | None:
    rows = []
    for path in (root / "research" / "dossiers").glob(f"{entity_id}-*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if str(payload.get("entity_id") or "").upper() != entity_id:
            continue
        generated_at = timestamp_key(str(payload.get("generated_at") or ""))
        materialized_at = datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc,
        )
        if generated_at > materialized_at:
            continue
        rows.append(payload)
    return max(rows, key=lambda row: timestamp_key(str(row["generated_at"])), default=None)


def _matching_frontier(root: Path, entity_id: str, dossier: Mapping[str, Any]) -> dict[str, Any] | None:
    declared = (dossier.get("strategy") or {}).get("frontier_artifact")
    if declared:
        path = (root / str(declared)).resolve()
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError("strategy frontier path escapes investment workspace") from error
        return json.loads(path.read_text(encoding="utf-8"))
    dossier_sha = dossier.get("dossier_sha256")
    rows = []
    for path in (root / "strategy_frontiers" / "results").glob(f"{entity_id.lower()}-*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (payload.get("company") or {}).get("source_dossier_sha256") == dossier_sha:
            rows.append(payload)
    return max(rows, key=lambda row: timestamp_key(str(row["evidence_epoch"])), default=None)


def compile_workspace_business_fingerprint(
    workspace: str | Path, entity_id: str, *, compiled_at: str | None = None,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    entity = require_text(entity_id, "business fingerprint entity_id").upper()
    quality = json.loads((root / "quality" / f"{entity.lower()}.json").read_text(encoding="utf-8"))
    dossier = _latest_dossier(root, entity)
    frontier = _matching_frontier(root, entity, dossier) if dossier else None
    return compile_business_fingerprint(
        company_quality=quality, research_dossier=dossier, strategy_frontier=frontier,
        compiled_at=compiled_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entity_id")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(compile_workspace_business_fingerprint(
        args.workspace, args.entity_id,
    ), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BUSINESS_FINGERPRINT_SCHEMA", "compile_business_fingerprint",
    "compile_workspace_business_fingerprint",
]
