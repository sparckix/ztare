"""Compile public-source acquisition work for missing business coordinates."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

from ztare.common.equivariance import stable_sha256

from .business_fingerprint import (
    BUSINESS_FINGERPRINT_SCHEMA,
    compile_workspace_business_fingerprint,
)
from .contracts import canonical_timestamp, require_text, timestamp_key
from .research_jobs import RESEARCH_REQUEST_SCHEMA
from .research_monitor import material_monitor_source_ids
from .sources import (
    PUBLIC_SOURCE_MANIFEST_SCHEMA,
    load_source_manifest,
    source_requirements,
)


BUSINESS_FINGERPRINT_ACQUISITION_SCHEMA = (
    "jaggedthoughts-business-fingerprint-source-plan-v1"
)

_DOCUMENT_FAMILIES = {
    "filing_disaggregation": [
        "SEC annual report or 10-K major-customer disclosure",
        "SEC annual report or 10-K segment and geographic footnotes",
        "SEC 10-Q interim disclosure when definitions remain comparable",
        "issuer-filed earnings exhibit or supplement",
    ],
    "capital_allocation_normalization": [
        "SEC annual report or 10-K cash-flow, PP&E, R&D, and acquisition footnotes",
        "SEC 10-Q interim capital-allocation disclosure",
        "issuer investor-day or capital-allocation material",
    ],
    "commercial_kpi_disclosure": [
        "issuer earnings release or KPI supplement",
        "issuer investor presentation",
        "SEC annual report or 10-K contract and operating-KPI disclosure",
        "issuer-posted earnings-call transcript",
    ],
}

_COORDINATES: tuple[dict[str, Any], ...] = (
    {
        "coordinate_id": "customer_revenue_concentration",
        "batch_id": "filing_disaggregation",
        "public_availability": "disclosure_threshold_conditional",
        "typed_observation_contract": {
            "fields": [
                "tier_or_n", "revenue_share", "customer_grouping", "period",
                "revenue_denominator", "observed_at", "available_at", "source_ref",
            ],
            "unit": "decimal_share_of_revenue",
        },
        "deterministic_derivations": [
            {
                "operator": "customer_share",
                "expression": "customer_revenue / matched_total_revenue",
                "requires": "matched period, scope, grouping, and denominator",
            },
            {
                "operator": "customer_hhi",
                "expression": "sum(mutually_exclusive_customer_shares ** 2)",
                "requires": "complete exhaustive customer shares for one matched scope",
            },
        ],
        "forbidden_inference": "Do not infer customer HHI from one aggregate top-N share.",
        "downstream_contracts": [
            "business_fingerprint.revenue_concentration",
            "research_dossier.durable_earnings_bridge",
            "strategy_frontier.customer_power_pressure",
        ],
    },
    {
        "coordinate_id": "segment_revenue_concentration",
        "batch_id": "filing_disaggregation",
        "public_availability": "generally_public_for_reportable_segments",
        "typed_observation_contract": {
            "fields": [
                "segment_id", "segment_revenue", "consolidated_revenue", "period",
                "segment_definition", "observed_at", "available_at", "source_ref",
            ],
            "unit": "filing_currency",
        },
        "deterministic_derivations": [
            {
                "operator": "segment_share_and_hhi",
                "expression": "share = segment_revenue / consolidated_revenue; hhi = sum(shares ** 2)",
                "requires": "exhaustive, mutually exclusive segments under one reporting definition",
            },
        ],
        "forbidden_inference": "Do not bridge changed segment definitions without a disclosed recast.",
        "downstream_contracts": [
            "business_fingerprint.revenue_concentration",
            "research_dossier.durable_earnings_bridge",
            "strategy_frontier.portfolio_scope",
        ],
    },
    {
        "coordinate_id": "geographic_revenue_concentration",
        "batch_id": "filing_disaggregation",
        "public_availability": "generally_public_when_material_geographies_are_disclosed",
        "typed_observation_contract": {
            "fields": [
                "geography_id", "geography_basis", "geography_revenue",
                "consolidated_revenue", "period", "observed_at", "available_at", "source_ref",
            ],
            "unit": "filing_currency",
        },
        "deterministic_derivations": [
            {
                "operator": "geography_share_and_hhi",
                "expression": "share = geography_revenue / consolidated_revenue; hhi = sum(shares ** 2)",
                "requires": "exhaustive geographies with a matched location basis and denominator",
            },
        ],
        "forbidden_inference": "Do not mix customer-location, domicile, and asset-location bases.",
        "downstream_contracts": [
            "business_fingerprint.revenue_concentration",
            "research_dossier.industry_cycle_and_regulation",
            "strategy_frontier.geographic_pressure",
        ],
    },
    {
        "coordinate_id": "segment_economics",
        "batch_id": "filing_disaggregation",
        "public_availability": "generally_public_for_reportable_segment_profit_or_loss",
        "typed_observation_contract": {
            "fields": [
                "segment_id", "segment_revenue", "segment_profit_or_loss",
                "profit_measure_definition", "period", "observed_at", "available_at", "source_ref",
            ],
            "unit": "filing_currency",
        },
        "deterministic_derivations": [
            {
                "operator": "segment_margin",
                "expression": "segment_profit_or_loss / segment_revenue",
                "requires": "matched segment, period, and disclosed profit-measure definition",
            },
        ],
        "forbidden_inference": "Do not compare segment margins across definition changes without a bridge.",
        "downstream_contracts": [
            "business_fingerprint.durability",
            "research_dossier.durable_earnings_bridge",
            "strategy_frontier.option_economic_bridge",
        ],
    },
    {
        "coordinate_id": "maintenance_vs_growth_capex",
        "batch_id": "capital_allocation_normalization",
        "public_availability": "not_generally_public_unless_management_classifies_it",
        "typed_observation_contract": {
            "fields": [
                "maintenance_capex", "growth_capex", "classification_policy", "scope",
                "period", "observed_at", "available_at", "source_ref",
            ],
            "unit": "filing_currency_per_period",
        },
        "deterministic_derivations": [],
        "forbidden_inference": "Do not split total PP&E purchases using depreciation or total capex alone.",
        "downstream_contracts": [
            "business_fingerprint.durability",
            "company_quality.owner_earnings_normalization",
            "research_dossier.reinvestment_and_capital_allocation",
        ],
    },
    {
        "coordinate_id": "incremental_reinvestment_return",
        "batch_id": "capital_allocation_normalization",
        "public_availability": "derived_when_normalized_return_and_investment_inputs_exist",
        "typed_observation_contract": {
            "fields": [
                "normalized_return_measure", "incremental_investment_measure", "window",
                "lag_policy", "adjustment_policy", "observed_at", "available_at", "source_refs",
            ],
            "unit": "decimal_return_per_period",
        },
        "deterministic_derivations": [
            {
                "operator": "incremental_return_on_invested_capital",
                "expression": "change_in_normalized_nopat / lagged_change_in_invested_capital",
                "requires": "positive matched incremental capital, exact window, lag, and normalization policy",
            },
            {
                "operator": "incremental_owner_earnings_return",
                "expression": "change_in_normalized_owner_earnings / lagged_reinvestment",
                "requires": "typed reinvestment and maintenance-capex treatment",
            },
        ],
        "forbidden_inference": "Do not attribute aggregate return changes to a named initiative without evidence.",
        "downstream_contracts": [
            "business_fingerprint.durability",
            "company_quality.reinvestment_return",
            "research_dossier.reinvestment_and_capital_allocation",
            "strategy_frontier.option_economic_bridge",
        ],
    },
    {
        "coordinate_id": "retention_and_churn",
        "batch_id": "commercial_kpi_disclosure",
        "public_availability": "not_generally_public_unless_issuer_defines_and_discloses_it",
        "typed_observation_contract": {
            "fields": [
                "metric_definition", "cohort", "numerator", "denominator", "period",
                "observed_at", "available_at", "source_ref",
            ],
            "unit": "decimal_rate",
        },
        "deterministic_derivations": [],
        "forbidden_inference": "Do not infer retention or churn from revenue growth or customer tenure.",
        "downstream_contracts": [
            "business_fingerprint.durability",
            "research_dossier.revenue_durability",
            "strategy_frontier.customer_lock_in",
        ],
    },
    {
        "coordinate_id": "pricing_power",
        "batch_id": "commercial_kpi_disclosure",
        "public_availability": "not_generally_public_without_price_volume_mix_disclosure",
        "typed_observation_contract": {
            "fields": [
                "price_realization", "product_or_contract_scope", "volume_effect", "mix_effect",
                "period", "observed_at", "available_at", "source_ref",
            ],
            "unit": "decimal_change",
        },
        "deterministic_derivations": [],
        "forbidden_inference": "Do not infer pricing power from total revenue or margin without volume and mix.",
        "downstream_contracts": [
            "business_fingerprint.durability",
            "research_dossier.industry_customer_and_supplier_power",
            "strategy_frontier.pricing_option",
        ],
    },
)

_YIELD_ORDER = {
    "primary_filing_multi_coordinate": 0,
    "conditional_primary_disclosure": 1,
    "issuer_defined_or_not_generally_public": 2,
}


def _verified_fingerprint(payload: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    body = dict(payload)
    declared = require_text(
        body.pop("business_fingerprint_sha256", ""), "business fingerprint hash"
    )
    if body.get("schema") != BUSINESS_FINGERPRINT_SCHEMA or stable_sha256(body) != declared:
        raise ValueError("business fingerprint identity is invalid")
    return {**body, "business_fingerprint_sha256": declared}, declared


def compile_fingerprint_acquisition_plan(
    *, business_fingerprint: Mapping[str, Any], source_manifest: Mapping[str, Any],
    compiled_at: str, research_request: Mapping[str, Any] | None = None,
    monitor_source_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Map missing business coordinates to public evidence and admissible derivations."""
    fingerprint, fingerprint_sha = _verified_fingerprint(business_fingerprint)
    if source_manifest.get("schema") != PUBLIC_SOURCE_MANIFEST_SCHEMA:
        raise ValueError(f"source manifest schema must be {PUBLIC_SOURCE_MANIFEST_SCHEMA}")
    entity = require_text(fingerprint.get("entity_id"), "acquisition entity_id").upper()
    compiled = canonical_timestamp(compiled_at, "acquisition plan compiled_at")

    request_identity = None
    if research_request is not None:
        if research_request.get("schema") != RESEARCH_REQUEST_SCHEMA:
            raise ValueError("acquisition plan research request schema is unsupported")
        if str(research_request.get("entity_id") or "").upper() != entity:
            raise ValueError("acquisition plan research request targets another entity")
        request_identity = {
            key: research_request.get(key) for key in (
                "request_id", "request_sha256", "candidate_leaf", "created_at",
                "lifecycle_stage", "requested_measurements",
            )
        }

    entity_sources = [
        dict(row) for row in source_manifest.get("sources") or ()
        if isinstance(row, Mapping)
        and str(row.get("entity_id") or "").upper() == entity
        and row.get("enabled", True) is not False
    ]
    source_ids = {str(row.get("id") or "") for row in entity_sources}
    sec_facts = sorted(
        str(row["id"]) for row in entity_sources if row.get("adapter") == "sec_companyfacts"
    )
    sec_filings = sorted(
        str(row["id"]) for row in entity_sources if row.get("adapter") == "sec_submissions"
    )
    requirements = [
        row for row in source_requirements(source_manifest)
        if row.get("source_id") in source_ids
    ]

    coordinates = [dict(row) for row in _COORDINATES]
    batch_classes = {
        "filing_disaggregation": "primary_filing_multi_coordinate",
        "capital_allocation_normalization": "conditional_primary_disclosure",
        "commercial_kpi_disclosure": "issuer_defined_or_not_generally_public",
    }
    batches = []
    for batch_id, yield_class in batch_classes.items():
        batch_coordinates = [row for row in coordinates if row["batch_id"] == batch_id]
        contracts = sorted({
            contract for row in batch_coordinates for contract in row["downstream_contracts"]
        })
        batches.append({
            "batch_id": batch_id,
            "information_yield_class": yield_class,
            "coordinate_ids": [row["coordinate_id"] for row in batch_coordinates],
            "document_families": list(_DOCUMENT_FAMILIES[batch_id]),
            "configured_source_ids": sorted(set(sec_facts + sec_filings)),
            "change_detection_source_ids": sorted(set(sec_filings) & set(monitor_source_ids)),
            "acquisition_route": (
                "monitor_then_reassessment_or_bound_research_request"
                if sec_filings else "bound_research_request_for_primary_documents"
            ),
            "downstream_contracts": contracts,
            "downstream_contract_count": len(contracts),
            "unmonitored_boundary": (
                "Issuer-hosted materials are research-request inputs unless a dedicated "
                "primary-source adapter and monitor identity are configured."
            ),
        })
    batches.sort(key=lambda row: (
        _YIELD_ORDER[row["information_yield_class"]],
        -row["downstream_contract_count"],
        row["batch_id"],
    ))
    for rank, row in enumerate(batches, 1):
        row["acquisition_rank"] = rank

    body = {
        "schema": BUSINESS_FINGERPRINT_ACQUISITION_SCHEMA,
        "plan_id": f"business-source-plan:{entity}:{fingerprint_sha[:16]}",
        "entity_id": entity,
        "compiled_at": compiled,
        "business_fingerprint_sha256": fingerprint_sha,
        "fingerprint_unknowns": list(fingerprint.get("unknowns") or ()),
        "research_request_identity": request_identity,
        "source_environment_requirements": requirements,
        "monitor_source_ids": sorted(set(monitor_source_ids)),
        "coordinates": coordinates,
        "acquisition_batches": batches,
        "priority_contract": {
            "ordering": [
                "information_yield_class",
                "downstream_contract_count_descending",
                "batch_id_stable_tiebreak",
            ],
            "investment_attractiveness_used": False,
            "economic_conclusion_used": False,
        },
        "execution_boundary": (
            "This plan fetches nothing and writes nothing. Source adapters acquire bytes; "
            "research requests extract typed observations; deterministic derivations run only "
            "when their declared preconditions hold."
        ),
        "capital_authority": False,
    }
    return {**body, "source_plan_sha256": stable_sha256(body)}


def _latest_request(
    root: Path, entity_id: str, candidate_leaf: str | None,
) -> dict[str, Any] | None:
    try:
        read_model = json.loads((root / "state" / "read_model.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    rows = [
        dict(row) for row in read_model.get("research_requests") or ()
        if isinstance(row, Mapping)
        and str(row.get("entity_id") or "").upper() == entity_id
        and row.get("schema") == RESEARCH_REQUEST_SCHEMA
        and candidate_leaf
        and row.get("candidate_leaf") == candidate_leaf
    ]
    return max(
        rows,
        key=lambda row: timestamp_key(canonical_timestamp(row["created_at"], "request created_at")),
        default=None,
    )


def compile_workspace_fingerprint_acquisition_plan(
    workspace: str | Path, entity_id: str, *, compiled_at: str | None = None,
    source_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    entity = require_text(entity_id, "acquisition entity_id").upper()
    if source_manifest is None:
        workspace_config = yaml.safe_load(
            (root / "workspace.yaml").read_text(encoding="utf-8")
        )
        if not isinstance(workspace_config, Mapping):
            raise ValueError("investment workspace configuration must be an object")
        source_manifest = load_source_manifest(
            root / str(workspace_config.get("source_manifest") or "sources.yaml")
        )
    manifest = dict(source_manifest)
    fingerprint = compile_workspace_business_fingerprint(root, entity, compiled_at=compiled_at)
    candidate_leaf = (
        (fingerprint.get("component_identity") or {})
        .get("research_dossier", {})
        .get("candidate_leaf")
    )
    return compile_fingerprint_acquisition_plan(
        business_fingerprint=fingerprint,
        source_manifest=manifest,
        research_request=_latest_request(root, entity, candidate_leaf),
        monitor_source_ids=material_monitor_source_ids(root, entity),
        compiled_at=compiled_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entity_id")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(compile_workspace_fingerprint_acquisition_plan(
        args.workspace, args.entity_id,
    ), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BUSINESS_FINGERPRINT_ACQUISITION_SCHEMA", "compile_fingerprint_acquisition_plan",
    "compile_workspace_fingerprint_acquisition_plan",
]
