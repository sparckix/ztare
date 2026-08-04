from __future__ import annotations

from dataclasses import replace

import pytest

from ztare.common.guarded_experiment_protocol import (
    CANONICAL_PRICING_ENGINE,
    GuardedExperimentProtocol,
    GuardedProtocolCandidate,
    ProtocolCost,
    ProtocolResponseHypothesis,
    ProtocolYieldWeights,
    price_guarded_protocol,
    select_guarded_protocol,
)


WEIGHTS = ProtocolYieldWeights(
    identification=1.0,
    compression=0.5,
    novelty=0.5,
)


def _protocol(
    protocol_id: str,
    *,
    preparation=("a", "b"),
    control_units=2,
    guard_admitted=True,
    novel=True,
):
    return GuardedExperimentProtocol(
        protocol_id=protocol_id,
        preparation=tuple(preparation),
        probe="probe",
        target_key=("target", protocol_id),
        cost=ProtocolCost(
            preparation_execution_units=len(preparation),
            probe_execution_units=1,
            control_units=control_units,
        ),
        novel_context=novel,
        guard_admitted=guard_admitted,
        guard_reason="" if guard_admitted else "preparation side exit",
    )


def _committee(labels=("x", "x", "y")):
    return tuple(
        ProtocolResponseHypothesis(
            hypothesis_id=f"h{index}",
            response=label,
            description_units=index + 1,
            evidence_refs=(f"evidence#{index}",),
        )
        for index, label in enumerate(labels)
    )


def test_price_delegates_to_canonical_information_engine():
    candidate = GuardedProtocolCandidate(
        protocol=_protocol("p"),
        committee=_committee(),
    )
    price = price_guarded_protocol(candidate, weights=WEIGHTS)
    receipt = price.to_receipt()

    assert price.status == "priced"
    assert price.committee_size == 3
    assert price.response_class_count == 2
    assert price.identification > 0
    assert price.compression_gain > 0
    assert price.novelty == 1
    assert price.yield_density == pytest.approx(
        price.weighted_yield / price.cost.total_units
    )
    assert receipt["canonical_pricing_engine"] == CANONICAL_PRICING_ENGINE


def test_extensional_equality_keeps_cheapest_partition_representative():
    expensive = GuardedProtocolCandidate(
        protocol=_protocol(
            "expensive",
            preparation=("a", "b", "c"),
            control_units=3,
        ),
        committee=_committee(("red", "red", "blue")),
    )
    cheap = GuardedProtocolCandidate(
        protocol=_protocol(
            "cheap",
            preparation=("z",),
            control_units=1,
        ),
        # Different response labels, same partition over the same hypotheses.
        committee=_committee(("left", "left", "right")),
    )
    selection = select_guarded_protocol(
        (expensive, cheap),
        weights=WEIGHTS,
    )

    assert selection.status == "selected"
    assert selection.selected_protocol_id == "cheap"
    assert selection.canonical_protocol_ids == ("cheap",)
    assert selection.deduplicated_protocol_ids == ("expensive",)


def test_skills_do_not_reduce_primitive_execution_cost():
    primitive = GuardedProtocolCandidate(
        protocol=_protocol(
            "primitive",
            preparation=("a", "b", "c", "d"),
            control_units=4,
        ),
        committee=_committee(),
    )
    compiled = replace(
        primitive,
        protocol=replace(
            primitive.protocol,
            protocol_id="compiled",
            cost=replace(primitive.protocol.cost, control_units=1),
        ),
    )
    primitive_price = price_guarded_protocol(primitive, weights=WEIGHTS)
    compiled_price = price_guarded_protocol(compiled, weights=WEIGHTS)

    assert primitive_price.cost.primitive_execution_units == 5
    assert compiled_price.cost.primitive_execution_units == 5
    assert compiled_price.cost.control_units == 1
    assert compiled_price.yield_density > primitive_price.yield_density


def test_guard_and_committee_fail_closed():
    rejected = GuardedProtocolCandidate(
        protocol=_protocol("rejected", guard_admitted=False),
        committee=_committee(),
    )
    unsupported = GuardedProtocolCandidate(
        protocol=_protocol("unsupported"),
        committee=(),
    )
    selection = select_guarded_protocol(
        (rejected, unsupported),
        weights=WEIGHTS,
    )

    assert selection.status == "no_valued_protocol"
    assert {
        row.protocol_id: row.status for row in selection.prices
    } == {
        "rejected": "guard_rejected",
        "unsupported": "committee_unavailable",
    }


def test_selection_is_invariant_to_protocol_and_committee_order():
    first = GuardedProtocolCandidate(
        protocol=_protocol("first", preparation=("a",)),
        committee=_committee(("x", "y", "z")),
    )
    second = GuardedProtocolCandidate(
        protocol=_protocol("second", preparation=("a", "b", "c")),
        committee=_committee(("x", "x", "y")),
    )
    forward = select_guarded_protocol((first, second), weights=WEIGHTS)
    reversed_input = select_guarded_protocol(
        (
            replace(second, committee=tuple(reversed(second.committee))),
            replace(first, committee=tuple(reversed(first.committee))),
        ),
        weights=WEIGHTS,
    )

    assert forward.to_receipt() == reversed_input.to_receipt()


def test_matched_task_value_reranks_without_changing_execution_cost():
    epistemic_best = GuardedProtocolCandidate(
        protocol=_protocol("epistemic-best", preparation=("a",)),
        committee=_committee(("x", "y", "z")),
    )
    task_credited = GuardedProtocolCandidate(
        protocol=_protocol(
            "task-credited",
            preparation=("a", "b", "c"),
        ),
        committee=_committee(("x", "x", "y")),
    )
    baseline = select_guarded_protocol(
        (epistemic_best, task_credited),
        weights=WEIGHTS,
    )
    calibrated = select_guarded_protocol(
        (epistemic_best, task_credited),
        weights=WEIGHTS,
        task_value_by_protocol_id={
            "epistemic-best": -1,
            "task-credited": 1,
        },
    )

    assert baseline.selected_protocol_id == "epistemic-best"
    assert calibrated.selected_protocol_id == "task-credited"
    baseline_costs = {
        row.protocol_id: row.cost.to_receipt()
        for row in baseline.prices
    }
    calibrated_costs = {
        row.protocol_id: row.cost.to_receipt()
        for row in calibrated.prices
    }
    assert calibrated_costs == baseline_costs
    assert calibrated.to_receipt()["task_value_by_protocol_id"] == {
        "epistemic-best": -1,
        "task-credited": 1,
    }

    contrast_completion = select_guarded_protocol(
        (epistemic_best, task_credited),
        weights=WEIGHTS,
        task_value_by_protocol_id={
            "epistemic-best": 0,
            "task-credited": 0,
        },
        contrast_priority_by_protocol_id={
            "epistemic-best": 0,
            "task-credited": 1,
        },
    )
    assert contrast_completion.selected_protocol_id == "task-credited"
    assert contrast_completion.to_receipt()[
        "contrast_priority_by_protocol_id"
    ] == {
        "epistemic-best": 0,
        "task-credited": 1,
    }
