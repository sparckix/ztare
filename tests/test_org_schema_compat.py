"""Schema-compatibility: the loader must accept the frozen v1 org/ fixture.

This guards against breaking schema changes. If a new field is added
in v2 of the org/ schema, this fixture must still parse (the loader
must accept the absence of the new field). If a field is renamed or
removed, this fixture will fail — which is the intended alarm.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ztare.roles.loader import load_registry

FIXTURES_DIR = Path(__file__).parent / "fixtures"
V1_SNAPSHOT = FIXTURES_DIR / "org_schema_v1"


def test_v1_fixture_parses_with_validation():
    """The v1 snapshot must load cleanly through the current loader,
    including validation. A failure here means a breaking schema change
    snuck in without a v2 fixture + migration path."""
    reg = load_registry(org_dir=V1_SNAPSHOT, validate=True)

    # Core counts
    assert set(reg.roles.keys()) == {"principal", "manager"}
    assert set(reg.members.keys()) == {"principal_human", "agent_worker"}
    assert set(reg.workers.keys()) == {"test_worker"}
    assert len(reg.assignments) == 2


def test_v1_fixture_preserves_worker_membrane_fields():
    """Workers carry input_contract / output_contract fields (Hole 7).
    A v2 loader must still read these from v1 fixtures."""
    reg = load_registry(org_dir=V1_SNAPSHOT, validate=False)
    w = reg.worker("test_worker")
    assert w.input_contract["must_receive"] == ["task_prompt"]
    assert "does not edit files" in w.output_contract["contract_guarantees"]
    assert w.limits["single_action_cost_cap_usd"] == 1.00


def test_v1_fixture_assignment_time_bounds():
    """Assignments with valid_until=null must parse as open-ended."""
    reg = load_registry(org_dir=V1_SNAPSHOT, validate=False)
    active = reg.active_assignments()
    assert len(active) == 2
    assert all(a.valid_until is None for a in active)


def test_v1_fixture_gate_signers_single_source():
    """The delegation.yaml gate_signers table remains the single source
    of truth. principal signs TEST_GATE in the fixture."""
    reg = load_registry(org_dir=V1_SNAPSHOT, validate=True)
    signers = reg.gate_signers("TEST_GATE")
    assert len(signers) == 1
    assert signers[0].role_id == "principal"


def test_v1_fixture_unknown_gate_returns_empty():
    reg = load_registry(org_dir=V1_SNAPSHOT, validate=False)
    assert reg.gate_signers("GATE_THAT_DOES_NOT_EXIST") == ()


def test_validation_fails_on_orphan_gate_signer():
    """Drift guard: if a fixture lists a role as signer in delegation
    but the role's signs_gates omits it, validation must fail."""
    import tempfile
    import shutil

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        shutil.copytree(V1_SNAPSHOT, tmp_path / "org")
        # Mutate: remove TEST_GATE from principal's signs_gates
        pr = tmp_path / "org" / "roles" / "principal.yaml"
        text = pr.read_text(encoding="utf-8")
        text = text.replace("signs_gates:\n  - TEST_GATE", "signs_gates: []")
        pr.write_text(text, encoding="utf-8")

        with pytest.raises(ValueError, match="gate 'TEST_GATE'"):
            load_registry(org_dir=tmp_path / "org", validate=True)
