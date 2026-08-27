from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
from threading import Barrier

import pytest
import yaml

import ztare.investment.workspace as workspace_module


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "examples" / "jaggedthoughts" / "investment" / "company_strategy_options.yaml"


def test_strategy_frontier_projection_normalizes_legacy_and_explains_constraint() -> None:
    row = workspace_module._ui_strategy_frontier({
        "company": {"strategy_constraint_gate_sha256": "gate-1"},
        "choice_space_certificate": {
            "bounded_bundle_count": 4, "feasible_bundle_count": 3,
            "excluded_bundle_count": 1,
        },
        "feasibility_constraints": {"prerequisites": [{
            "constraint_id": "requires-platform", "option_id": "protection",
            "requires": ["platform"], "evidence_refs": ["filing-1"],
            "authority": "dossier_bound",
        }]},
        "constraint_witnesses": [{"option_ids": ["protection"]}],
        "certificate": {"representation_audit": {
            "status": "residual", "residuals": ["product profit unavailable"],
        }},
        "economic_bridge": {"next_transition": "calibrate_valuation"},
    })

    assert row["choice_space_certificate"]["constraint_authority"] == {}
    assert row["explanation_chain"] == {
        "schema": "jaggedthoughts-strategy-frontier-explanation-chain-v1",
        "evidence_refs": ["filing-1"],
        "predicates": [{
            "constraint_id": "requires-platform", "predicate_id": "implies_all_selected",
            "expression": "protection => platform", "evidence_refs": ["filing-1"],
            "authority": "dossier_bound",
        }],
        "gate": {
            "status": "accepted", "sha256": "gate-1",
            "evidence_grade": "legacy_ungraded",
            "research_claim_eligible": False,
        },
        "z3_delta": {
            "bounded_bundle_count": 4, "feasible_bundle_count": 3,
            "excluded_bundle_count": 1, "witness_count": 1,
        },
        "representation": {"status": "residual", "residuals": ["product profit unavailable"]},
        "valuation": {"status": "blocked", "next_transition": "calibrate_valuation"},
    }


def test_strategy_frontier_head_publish_is_compare_and_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "workspace.yaml").write_text(yaml.safe_dump({
        "schema": "jaggedthoughts-investment-workspace-v1",
        "owner": "paper", "golden_store": "state/golden_store.sqlite3",
    }), encoding="utf-8")
    base = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    base_path = tmp_path / "base.yaml"
    base_path.write_text(yaml.safe_dump(base), encoding="utf-8")
    first = workspace_module.compile_workspace_company_strategy(
        base_path, tmp_path, refresh_read_model=False, expected_head_sha256="",
    )["result"]

    paths = []
    compiled = {}
    for version in ("race-b", "race-c"):
        profile = deepcopy(base)
        profile["version"] = version
        path = tmp_path / f"{version}.yaml"
        path.write_text(yaml.safe_dump(profile), encoding="utf-8")
        paths.append(path)
        compiled[version] = workspace_module.compile_company_strategy_frontier(profile)

    barrier = Barrier(2)

    def compile_together(payload):
        result = deepcopy(compiled[payload["version"]])
        barrier.wait()
        return result

    monkeypatch.setattr(
        workspace_module, "compile_company_strategy_frontier", compile_together,
    )

    def publish(path: Path):
        return workspace_module.compile_workspace_company_strategy(
            path, tmp_path, refresh_read_model=False,
            expected_head_sha256=first["strategy_frontier_sha256"],
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(publish, path) for path in paths]
        outcomes = []
        for future in futures:
            try:
                outcomes.append(future.result()["result"])
            except workspace_module.StrategyFrontierHeadChangedError as error:
                outcomes.append(error)

    winners = [row for row in outcomes if isinstance(row, dict)]
    losers = [row for row in outcomes if isinstance(
        row, workspace_module.StrategyFrontierHeadChangedError,
    )]
    head = json.loads((tmp_path / "strategy_frontiers/heads/alpha.json").read_text())
    result_hashes = {
        json.loads(path.read_text())["strategy_frontier_sha256"]
        for path in (tmp_path / "strategy_frontiers/results").glob("*.json")
    }
    assert len(winners) == len(losers) == 1
    assert head["strategy_frontier_sha256"] == winners[0]["strategy_frontier_sha256"]
    assert losers[0].current == winners[0]["strategy_frontier_sha256"]
    assert result_hashes == {
        first["strategy_frontier_sha256"], winners[0]["strategy_frontier_sha256"],
    }
