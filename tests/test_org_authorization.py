from __future__ import annotations

import importlib.util
import json
from src.ztare.orchestration import task_authorization as ta
from src.ztare.orchestration import work_discovery as wd

from pathlib import Path


_AGENT_DAEMON_SPEC = importlib.util.spec_from_file_location(
    "agent_daemon_under_test_auth",
    Path(__file__).resolve().parents[1] / "scripts" / "agent_daemon.py",
)
assert _AGENT_DAEMON_SPEC and _AGENT_DAEMON_SPEC.loader
agent_daemon = importlib.util.module_from_spec(_AGENT_DAEMON_SPEC)
_AGENT_DAEMON_SPEC.loader.exec_module(agent_daemon)


def test_autonomous_scope_false_requires_principal_approval(monkeypatch):
    monkeypatch.setattr(
        ta,
        "_load_role",
        lambda role_id: {"budget": {"single_action_cap_usd": 5.0}},
    )

    decision = ta.authorize_dispatch(
        role_id="research_director",
        candidate_source="principal-goal",
        candidate_text="Review `docs/`.",
        metadata={"autonomous_scope_ok": False, "estimated_cost_usd": 0.0},
        unattended=False,
    )

    assert decision.allowed is False
    assert decision.required_approval == "principal"
    assert decision.terminal is False


def test_agent_channel_always_requires_approval_gate(monkeypatch):
    monkeypatch.setattr(
        ta,
        "_load_role",
        lambda role_id: {"budget": {"single_action_cap_usd": 5.0}},
    )

    decision = ta.authorize_dispatch(
        role_id="research_director",
        candidate_source="agent-channel",
        candidate_text="Respond to manager handoff.",
        metadata={},
        unattended=False,
    )

    assert decision.allowed is False
    assert decision.required_approval == "principal"
    assert "communication obligations" in decision.reason
    assert decision.terminal is False


def test_unattended_forbidden_path_is_terminal(monkeypatch):
    monkeypatch.setattr(
        ta,
        "_load_role",
        lambda role_id: {
            "budget": {"single_action_cap_usd": 5.0},
            "authorized_paths": ["docs/"],
            "forbidden_paths": ["org/mandates/"],
        },
    )

    decision = ta.authorize_dispatch(
        role_id="research_director",
        candidate_source="principal-goal",
        candidate_text="Edit `org/mandates/research_director_mandate.md`.",
        metadata={"autonomous_scope_ok": True, "estimated_cost_usd": 0.0},
        unattended=True,
    )

    assert decision.allowed is False
    assert decision.terminal is True
    assert "forbidden_paths" in decision.reason


def test_unattended_requires_explicit_cost_and_paths(monkeypatch):
    monkeypatch.setattr(
        ta,
        "_load_role",
        lambda role_id: {
            "budget": {"single_action_cap_usd": 5.0},
            "authorized_paths": ["docs/"],
            "forbidden_paths": [],
        },
    )

    missing_cost = ta.authorize_dispatch(
        role_id="research_director",
        candidate_source="principal-goal",
        candidate_text="Edit `docs/concepts/architecture.md`.",
        metadata={"autonomous_scope_ok": True},
        unattended=True,
    )
    assert missing_cost.allowed is False
    assert "estimated_cost_usd" in missing_cost.reason

    missing_path = ta.authorize_dispatch(
        role_id="research_director",
        candidate_source="principal-goal",
        candidate_text="Do some work.",
        metadata={"autonomous_scope_ok": True, "estimated_cost_usd": 0.0},
        unattended=True,
    )
    assert missing_path.allowed is False
    assert "declared paths" in missing_path.reason


def test_unattended_accepts_declared_authorized_path(monkeypatch):
    monkeypatch.setattr(
        ta,
        "_load_role",
        lambda role_id: {
            "budget": {"single_action_cap_usd": 5.0},
            "authorized_paths": ["docs/"],
            "forbidden_paths": [],
        },
    )

    decision = ta.authorize_dispatch(
        role_id="research_director",
        candidate_source="principal-goal",
        candidate_text="Update the landing-page docs.",
        metadata={
            "autonomous_scope_ok": True,
            "estimated_cost_usd": 0.0,
            "declared_paths": ["docs/concepts/architecture.md"],
        },
        unattended=True,
    )

    assert decision.allowed is True
    assert decision.matched_paths == ("docs/concepts/architecture.md",)


def test_discover_all_prioritizes_critical_damage(monkeypatch):
    critical = wd.Candidate(
        source="damage-scan",
        intent="HARD STOP: critical tool_escape signal",
        origin_path=None,
        scarcity_signal="critical damage",
        raw_text="critical",
        severity="critical",
        metadata={"kind": "tool_escape"},
    )
    goal = wd.Candidate(
        source="principal-goal",
        intent="execute normal principal goal",
        origin_path=None,
        scarcity_signal="principal directive",
        raw_text="goal",
        severity="info",
        metadata={"goal_id": "g1"},
    )
    channel = wd.Candidate(
        source="agent-channel",
        intent="respond to handoff",
        origin_path=None,
        scarcity_signal="open persistent-agent message",
        raw_text="handoff",
        severity="warn",
        metadata={"message_id": "m1"},
    )

    monkeypatch.setattr(wd, "discover_damage_signals", lambda **kwargs: [critical])
    monkeypatch.setattr(wd, "discover_principal_goals", lambda **kwargs: [goal])
    monkeypatch.setattr(wd, "discover_agent_channel_messages", lambda **kwargs: [channel])
    monkeypatch.setattr(wd, "discover_open_todos", lambda **kwargs: [])

    candidates = wd.discover_all(assigned_to="role.research_director")

    assert [c.source for c in candidates] == [
        "damage-scan",
        "principal-goal",
        "agent-channel",
    ]


def test_gate_resolution_requires_pending_gate_and_valid_option(tmp_path, monkeypatch):
    pending = tmp_path / "pending"
    resolved = tmp_path / "resolved"
    pending.mkdir()
    resolved.mkdir()
    monkeypatch.setattr(agent_daemon, "GATES_PENDING_DIR", pending)
    monkeypatch.setattr(agent_daemon, "GATES_RESOLVED_DIR", resolved)
    monkeypatch.setattr(agent_daemon, "append_transition", lambda **kwargs: None)

    gate_id = "proposal_test_abc"
    gate = {
        "gate_id": gate_id,
        "status": "pending",
        "options": [{"id": "approve"}, {"id": "skip"}, {"id": "stop"}],
    }
    (pending / f"{gate_id}.json").write_text(json.dumps(gate), encoding="utf-8")

    agent_daemon._write_resolved_gate_from_surface(
        gate_id,
        chosen_option="approve",
        surface="test",
        role_id="manager",
    )

    assert not (pending / f"{gate_id}.json").exists()
    assert (pending / f"{gate_id}.json.handled").exists()
    resolved_data = agent_daemon._read_resolved_gate(gate_id)
    assert resolved_data is not None
    assert resolved_data["resolution"]["chosen_option"] == "approve"


def test_gate_resolution_rejects_orphan_or_bad_option(tmp_path, monkeypatch):
    pending = tmp_path / "pending"
    resolved = tmp_path / "resolved"
    pending.mkdir()
    resolved.mkdir()
    monkeypatch.setattr(agent_daemon, "GATES_PENDING_DIR", pending)
    monkeypatch.setattr(agent_daemon, "GATES_RESOLVED_DIR", resolved)

    try:
        agent_daemon._write_resolved_gate_from_surface(
            "proposal_missing",
            chosen_option="approve",
            surface="test",
            role_id="manager",
        )
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("orphan gate resolution should fail")

    gate_id = "proposal_test_bad"
    (pending / f"{gate_id}.json").write_text(
        json.dumps({"gate_id": gate_id, "options": [{"id": "skip"}]}),
        encoding="utf-8",
    )
    try:
        agent_daemon._write_resolved_gate_from_surface(
            gate_id,
            chosen_option="approve",
            surface="test",
            role_id="manager",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("disallowed gate option should fail")
