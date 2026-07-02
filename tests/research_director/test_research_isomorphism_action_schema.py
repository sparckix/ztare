import json
from pathlib import Path

from ztare.common.constraint_isomorphism import SurfacedIsomorphism
from ztare.common.kernel_action_schema import validate_kernel_action_schema
from ztare.research_director.research_isomorphism import (
    ResearchDomain,
    debug_query_for_seam,
    prescribe_for_seam,
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


def test_prescribe_for_seam_passes_typed_invariants(monkeypatch) -> None:
    import ztare.common.constraint_isomorphism as ci

    seen = {}

    def fake_query(fp, n, *, provider, model, typed_mapping, mode):
        seen.update(
            {
                "provider": provider,
                "model": model,
                "typed_mapping": typed_mapping,
                "mode": mode,
                "invariants": dict(fp.invariants),
                "n": n,
            }
        )
        return [
            SurfacedIsomorphism(
                theorem="Kruskal tensor uniqueness",
                field="multilinear algebra",
                mechanism="rank condition gives identifiable tensor factors",
                mapping_hint="scalar statistic -> identifiable preimage after rank receipt",
            )
        ]

    monkeypatch.setattr(ci, "default_llm_query", fake_query)

    rx = prescribe_for_seam(
        "many-to-one scalar projection loses tensor preimage",
        abstract_form="kernel contains distinct tensor states",
        home_field="fluid PDE",
        model="deepseek",
        n=3,
        invariants={"projection": "many_to_one"},
        typed_mapping=True,
    )

    assert rx["candidate_count"] == 1
    assert rx["source_theorem"] == "Kruskal tensor uniqueness"
    assert seen == {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "typed_mapping": True,
        "mode": "solve",
        "invariants": {"projection": "many_to_one"},
        "n": 3,
    }


def test_debug_query_for_seam_reports_parse_status(monkeypatch) -> None:
    import ztare.common.constraint_isomorphism as ci

    monkeypatch.setattr(
        ci,
        "_dispatch_text",
        lambda *args, **kwargs: (
            '[{"theorem":"Whitney extension","field":"differential topology",'
            '"mechanism":"section obstruction","mapping_hint":"preimage selector"}]'
        ),
    )

    dbg = debug_query_for_seam(
        "many-to-one scalar projection loses tensor preimage",
        abstract_form="kernel contains distinct tensor states",
        home_field="fluid PDE",
        model="deepseek",
        n=2,
        invariants={"projection": "many_to_one"},
        typed_mapping=True,
    )

    assert dbg["provider"] == "deepseek"
    assert dbg["model"] == "deepseek-chat"
    assert dbg["parse_status"] == "parsed"
    assert dbg["candidate_count"] == 1
    assert dbg["candidates"] == [
        {"theorem": "Whitney extension", "field": "differential topology"}
    ]
