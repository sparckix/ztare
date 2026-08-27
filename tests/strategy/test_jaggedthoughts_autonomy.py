from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from ztare.strategy.autonomy import (
    compile_autonomous_profile_file,
    run_autonomous_step,
)
from ztare.strategy.probes import default_probe_adapter_registry


PROFILE = Path("examples/jaggedthoughts/autonomous_service_strategy.yaml")


def test_autonomous_profile_compiles_mechanisms_policies_and_probe() -> None:
    compiled = compile_autonomous_profile_file(PROFILE)

    assert compiled.version_space.survivor_ids == (
        "pressure_response",
        "stable_response",
    )
    assert compiled.policy_synthesis is not None
    assert compiled.policy_synthesis.certificate.scope_closed is True
    assert len(compiled.policy_synthesis.certificate.target_program_ids) == 202
    assert compiled.probe_agenda is not None
    assert compiled.probe_agenda.selection.selected_protocol_id == (
        "high_pressure_partner"
    )
    assert compiled.probe_agenda.selection.selected.identification == 1.0
    assert compiled.diagnostics.next_action == "execute_selected_probe"


def test_observation_prunes_models_and_stops_repeating_the_probe(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "run.json"
    first = run_autonomous_step(PROFILE)
    state_path.write_text(
        json.dumps(first.run_state.to_dict()),
        encoding="utf-8",
    )

    assert first.execution is not None
    assert first.execution.status == "observed"
    assert first.after.version_space.survivor_ids == ("pressure_response",)
    assert first.after.summary()["calibration_count"] == 1
    assert first.after.diagnostics.next_action == (
        "author_representation_challenger"
    )
    assert len(first.run_state.eligibility_edges) == 1
    assert len(first.run_state.eligibility_chains) == 1
    edge = first.run_state.eligibility_edges[0]
    assert edge["predicted_information_yield"] == 1.0
    assert edge["observed_information_yield"] == 1.0

    second = run_autonomous_step(PROFILE, run_state_path=state_path)
    assert second.execution is None
    assert second.after.status == "policy_frontier_ready"
    assert len(second.run_state.eligibility_edges) == 1


def test_adapter_rechecks_authority_at_execution() -> None:
    compiled = compile_autonomous_profile_file(PROFILE)
    assert compiled.probe_agenda is not None
    probe = compiled.probe_agenda.selected_probe
    assert probe is not None
    authority = replace(
        compiled.probe_agenda.authority,
        max_primitive_execution_units=0,
    )

    with pytest.raises(PermissionError, match="cost exceeds"):
        default_probe_adapter_registry().execute(
            probe,
            authority=authority,
            adapter_root=PROFILE.parent,
        )
