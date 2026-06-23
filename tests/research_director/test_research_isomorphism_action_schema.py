import json
from pathlib import Path

from ztare.common.constraint_isomorphism import SurfacedIsomorphism
from ztare.common.kernel_action_schema import validate_kernel_action_schema
from ztare.research_director.research_isomorphism import (
    ResearchDomain,
    surface_for_research_ceiling,
)


def test_research_isomorphism_compiles_prescription_to_kernel_action_schema() -> None:
    domain = ResearchDomain()
    iso = SurfacedIsomorphism(
        theorem="Max-flow min-cut",
        field="network optimization",
        mechanism="dual certificate names the obstruction",
        mapping_hint="source residual -> target certificate",
    )

    prescription = domain.compile_to_test(iso, None)
    action = prescription.action_schema
    ok, missing = validate_kernel_action_schema(action or {})

    assert ok is True
    assert missing == []
    assert action is not None
    assert action["record_type"] == "kernel_action_schema"
    assert action["source_kind"] == "research_isomorphism"
    assert action["action_family"] == "structural_transfer"


def test_research_isomorphism_ledger_records_kernel_action_schema(tmp_path: Path) -> None:
    ledger = tmp_path / "research_isomorphism_candidates.jsonl"
    iso = SurfacedIsomorphism(
        theorem="Max-flow min-cut",
        field="network optimization",
        mechanism="dual certificate names the obstruction",
        mapping_hint="source residual -> target certificate",
    )

    surface_for_research_ceiling(
        {
            "constraint_class": "stalled residual needs certificate",
            "abstract_form": "target-side obstruction certificate",
            "home_field": "autoresearch",
        },
        query=lambda fp, n: [iso],
        ledger=ledger,
    )

    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    ok, missing = validate_kernel_action_schema(row["action_schema"])

    assert ok is True
    assert missing == []
    assert row["action_schema"]["target_mapping"] == "source residual -> target certificate"
