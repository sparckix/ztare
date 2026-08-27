from ztare.common.equivariance import stable_sha256
from ztare.investment.business_fingerprint_acquisition import (
    BUSINESS_FINGERPRINT_ACQUISITION_SCHEMA,
    compile_fingerprint_acquisition_plan,
)


def test_acquisition_plan_compounds_sources_without_inventing_coordinates() -> None:
    fingerprint_body = {
        "schema": "jaggedthoughts-business-fingerprint-v1",
        "fingerprint_id": "business:ACME:abc",
        "entity_id": "ACME",
        "compiled_at": "2026-08-12T00:00:00Z",
        "component_identity": {},
        "coordinates": [],
        "axis_coverage": {},
        "unknowns": ["Customer and segment concentration lack typed observations."],
        "cross_industry_comparability": {"allowed": False},
        "use_boundary": "business understanding only",
        "capital_authority": False,
    }
    fingerprint = {
        **fingerprint_body,
        "business_fingerprint_sha256": stable_sha256(fingerprint_body),
    }
    manifest = {
        "schema": "jaggedthoughts-public-source-manifest-v1",
        "sources": [
            {
                "id": "sec_acme_facts", "entity_id": "ACME",
                "adapter": "sec_companyfacts", "enabled": True,
            },
            {
                "id": "sec_acme_filings", "entity_id": "ACME",
                "adapter": "sec_submissions", "enabled": True,
            },
        ],
    }

    plan = compile_fingerprint_acquisition_plan(
        business_fingerprint=fingerprint,
        source_manifest=manifest,
        monitor_source_ids=("sec_acme_facts", "sec_acme_filings"),
        compiled_at="2026-08-12T01:00:00Z",
    )

    assert plan["schema"] == BUSINESS_FINGERPRINT_ACQUISITION_SCHEMA
    assert len(plan["coordinates"]) == 8
    assert [row["batch_id"] for row in plan["acquisition_batches"]] == [
        "filing_disaggregation",
        "capital_allocation_normalization",
        "commercial_kpi_disclosure",
    ]
    customer = next(row for row in plan["coordinates"] if row["coordinate_id"] == "customer_revenue_concentration")
    capex = next(row for row in plan["coordinates"] if row["coordinate_id"] == "maintenance_vs_growth_capex")
    retention = next(row for row in plan["coordinates"] if row["coordinate_id"] == "retention_and_churn")
    assert "complete exhaustive" in customer["deterministic_derivations"][1]["requires"]
    assert capex["public_availability"].startswith("not_generally_public")
    assert retention["deterministic_derivations"] == []
    assert plan["priority_contract"]["investment_attractiveness_used"] is False
    assert plan["capital_authority"] is False
    assert "score" not in str(plan).lower()
