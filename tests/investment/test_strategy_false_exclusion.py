from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from ztare.common.equivariance import stable_sha256
from ztare.investment.strategy_false_exclusion import (
    compile_strategy_false_exclusion_contract,
    settle_strategy_false_exclusion_contract,
)
from ztare.investment.strategy_options import compile_company_strategy_frontier


def test_false_exclusion_contract_is_prospective_independent_and_power_gated() -> None:
    profile = yaml.safe_load(Path(
        "examples/jaggedthoughts/investment/company_strategy_options.yaml"
    ).read_text(encoding="utf-8"))
    parent = compile_company_strategy_frontier(profile)
    excluded = next(
        row["option_ids"] for row in parent["choice_space_certificate"]["feasible_bundles"]
        if len(row["option_ids"]) == 2
    )
    successor_profile = deepcopy(profile)
    predicate = {
        "predicate_kind": "incompatibility", "constraint_id": "observed_conflict",
        "option_ids": excluded, "evidence_refs": ["predicate-source"],
    }
    successor_profile.setdefault("feasibility_constraints", {}).setdefault(
        "incompatibilities", [],
    ).append({key: value for key, value in predicate.items() if key != "predicate_kind"})
    successor = compile_company_strategy_frontier(successor_profile)
    predicate_hash = stable_sha256(predicate)
    contract = compile_strategy_false_exclusion_contract(
        parent, successor, accepted_predicate_sha256s=[predicate_hash],
        predicate_source_ids=["predicate-source"],
        evidence_cutoff="2026-08-01T00:00:00Z", minimum_assessed_examples=2,
    )
    first = {
        "example_id": "admitted-1", "option_ids": excluded,
        "observed_at": "2026-08-02T00:00:00Z",
        "available_at": "2026-08-03T00:00:00Z", "source_ids": ["holdout-1"],
    }
    abstained = settle_strategy_false_exclusion_contract(
        contract, [first], assessed_at="2026-08-04T00:00:00Z",
    )
    assessed = settle_strategy_false_exclusion_contract(
        contract, [first, {
            "example_id": "admitted-2",
            "option_ids": successor["choice_space_certificate"]["feasible_bundles"][0]["option_ids"],
            "observed_at": "2026-08-02T00:00:00Z",
            "available_at": "2026-08-03T00:00:00Z", "source_ids": ["holdout-2"],
        }], assessed_at="2026-08-04T00:00:00Z",
    )

    assert abstained["status"] == "abstained_insufficient_examples"
    assert assessed["status"] == "assessed"
    assert assessed["false_exclusion_numerator"] == 1
    assert assessed["assessed_example_denominator"] == 2
    assert assessed["false_exclusion_rate"] == 0.5
    assert assessed["research_claim_eligible"] is assessed["capital_authority"] is False
    with pytest.raises(ValueError, match="not post-cutoff"):
        settle_strategy_false_exclusion_contract(
            contract, [{**first, "observed_at": contract["evidence_cutoff"]}],
            assessed_at="2026-08-04T00:00:00Z",
        )
    with pytest.raises(ValueError, match="not source-independent"):
        settle_strategy_false_exclusion_contract(
            contract, [{**first, "source_ids": ["predicate-source"]}],
            assessed_at="2026-08-04T00:00:00Z",
        )
