from ztare.orchestrator.blitz_dispatch import (
    _baseline_candidate_score,
    _requires_lagrangian_contract,
    should_run_parallel,
)


PLAIN_FIT_CANDIDATE = """
Thesis
```python
PARAMETRIC_FORM = "params['a'] * features['x'] + params['b']"
PARAMETER_NAMES = ['a', 'b']
MODEL_PARAMS = {}

def I_model(features, params=MODEL_PARAMS):
    return params.get('a', 1.0) * features['x'] + params.get('b', 0.0)
```
"""


TRIVIAL_LAGRANGIAN_CANDIDATE = """
Thesis
```python
LAGRANGIAN = "0.5*q_dot**2 - 0.5*(q - mass_log10)**2"
PARAMETRIC_FORM = "params['a'] * features['x']"
PARAMETER_NAMES = ['a']
MODEL_PARAMS = {}

def I_model(features, params=MODEL_PARAMS):
    return params.get('a', 1.0) * features['x']
```
"""


def test_should_run_parallel_default_disabled_when_k_unset() -> None:
    run, k, reason = should_run_parallel(
        stagnation_count=10,
        iter_idx=1,
        rubric_data={},
    )

    assert run is False
    assert k == 1
    assert "parallel disabled" in reason


def test_should_run_parallel_respects_force_iters() -> None:
    run, k, reason = should_run_parallel(
        stagnation_count=0,
        iter_idx=2,
        rubric_data={"parallel_mutator_k": 3, "parallel_mutator_force_iters": [2]},
    )

    assert run is True
    assert k == 3
    assert "force_iters" in reason


def test_lagrangian_contract_detection_from_mode_and_flag() -> None:
    assert _requires_lagrangian_contract({"enable_lagrangian_derivation": True})
    assert _requires_lagrangian_contract({"rubric_modes": ["invariant_search"]})
    assert _requires_lagrangian_contract({"rubric_mode": "invariant_search"})
    assert not _requires_lagrangian_contract({"rubric_mode": "newton"})


def test_plain_candidate_not_penalized_for_missing_lagrangian_without_contract() -> None:
    score_without_contract = _baseline_candidate_score(PLAIN_FIT_CANDIDATE, rubric_data={})
    score_with_contract = _baseline_candidate_score(
        PLAIN_FIT_CANDIDATE,
        rubric_data={"rubric_modes": ["invariant_search"]},
    )

    assert score_without_contract > score_with_contract
    assert score_without_contract - score_with_contract == 1.5


def test_trivial_lagrangian_penalty_only_applies_when_contract_requires_it() -> None:
    score_without_contract = _baseline_candidate_score(TRIVIAL_LAGRANGIAN_CANDIDATE, rubric_data={})
    score_with_contract = _baseline_candidate_score(
        TRIVIAL_LAGRANGIAN_CANDIDATE,
        rubric_data={"enable_lagrangian_derivation": True},
    )

    assert score_without_contract > score_with_contract
    assert score_without_contract - score_with_contract == 2.0
