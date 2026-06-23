from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from ztare.orchestration import agent_channels as ac
from ztare.orchestration import work_discovery as wd
from ztare.orchestration.work_discovery import Candidate


_AGENT_DAEMON_SPEC = importlib.util.spec_from_file_location(
    "agent_daemon_under_test",
    Path(__file__).resolve().parents[1] / "scripts" / "public" / "control" / "agent_daemon.py",
)
assert _AGENT_DAEMON_SPEC and _AGENT_DAEMON_SPEC.loader
agent_daemon = importlib.util.module_from_spec(_AGENT_DAEMON_SPEC)
_AGENT_DAEMON_SPEC.loader.exec_module(agent_daemon)


def _write_role(root: Path, role_id: str, *, delegates=(), escalates=()):
    lines = [
        "schema_version: 1",
        f"role_id: {role_id}",
        "role_class: test",
        "delegates_to:",
    ]
    lines.extend(f"  - role.{r}" for r in delegates)
    lines.append("escalates_to:")
    lines.extend(f"  - role.{r}" for r in escalates)
    (root / f"{role_id}.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def channel_env(tmp_path: Path, monkeypatch):
    roles = tmp_path / "roles"
    channels = tmp_path / "channels"
    transitions = tmp_path / "transitions.jsonl"
    roles.mkdir()
    _write_role(roles, "manager")
    _write_role(roles, "research_director", escalates=("manager",))
    _write_role(roles, "reviewer")
    monkeypatch.setattr(ac, "ROLES_DIR", roles)
    monkeypatch.setattr(ac, "CHANNELS_DIR", channels)
    return roles, channels, transitions


def test_send_message_writes_receiver_sender_and_transition(channel_env, monkeypatch):
    _, channels, transitions = channel_env
    monkeypatch.setattr(ac, "append_transition", lambda **kw: transitions.write_text(str(kw), encoding="utf-8"))

    msg = ac.send_agent_message(
        from_role="manager",
        to_role="research_director",
        kind="handoff",
        subject="review GP-167",
        body="Please review the channel implementation.",
        expects_response=True,
    )

    inbox = channels / "research_director" / "inbox" / f"{msg.message_id}.json"
    sent = channels / "manager" / "sent" / f"{msg.message_id}.json"
    assert inbox.exists()
    assert sent.exists()
    assert transitions.exists()
    assert ac.read_agent_message(role_id="research_director", message_id=msg.message_id) is not None


def test_channel_policy_blocks_unlinked_roles(channel_env):
    with pytest.raises(ac.ChannelPolicyError):
        ac.send_agent_message(
            from_role="reviewer",
            to_role="research_director",
            kind="request",
            subject="unlinked request",
            body="This should require explicit policy.",
        )


def test_status_update_syncs_sender_mirror(channel_env, monkeypatch):
    _, channels, _ = channel_env
    monkeypatch.setattr(ac, "append_transition", lambda **kw: None)
    msg = ac.send_agent_message(
        from_role="manager",
        to_role="research_director",
        kind="inform",
        subject="mirror",
        body="mirror sync",
    )

    ac.update_agent_message_status(
        role_id="research_director",
        message_id=msg.message_id,
        status="closed",
        actor="tester",
    )

    assert '"status": "closed"' in (
        channels / "manager" / "sent" / f"{msg.message_id}.json"
    ).read_text(encoding="utf-8")


def test_work_discovery_surfaces_open_agent_message(channel_env, monkeypatch):
    monkeypatch.setattr(ac, "append_transition", lambda **kw: None)
    ac.send_agent_message(
        from_role="manager",
        to_role="research_director",
        kind="request",
        subject="respond to this",
        body="This should appear as work.",
        expects_response=True,
    )

    cands = wd.discover_agent_channel_messages(
        assigned_to="role.research_director",
        max_per_source=10,
    )
    assert len(cands) == 1
    assert cands[0].source == "agent-channel"
    assert cands[0].severity == "warn"
    assert cands[0].metadata["kind"] == "request"


def test_daemon_closes_agent_channel_candidate_after_success(channel_env, monkeypatch):
    _, channels, _ = channel_env
    monkeypatch.setattr(ac, "append_transition", lambda **kw: None)
    msg = ac.send_agent_message(
        from_role="manager",
        to_role="research_director",
        kind="request",
        subject="close me",
        body="Daemon should close this after success.",
        expects_response=True,
    )
    candidate = Candidate(
        source="agent-channel",
        intent="respond to request from manager: close me",
        origin_path=None,
        scarcity_signal="open persistent-agent message requiring response",
        raw_text=msg.body,
        severity="warn",
        metadata={
            "message_id": msg.message_id,
            "to_role": "research_director",
        },
    )

    agent_daemon._close_candidate_task(
        candidate,
        session=object(),
        role_id="research_director",
        success=True,
        result={"success": True},
    )

    inbox_text = (
        channels / "research_director" / "inbox" / f"{msg.message_id}.json"
    ).read_text(encoding="utf-8")
    assert '"status": "closed"' in inbox_text


def test_agent_daemon_builds_claude_and_codex_commands():
    prompt = "read AGENTS.md then report"

    claude_cmd = agent_daemon.build_agent_command(
        agent_cli="claude",
        adapter="claude_print",
        prompt=prompt,
    )
    assert claude_cmd[:2] == ["claude", "--print"]
    assert claude_cmd[-2:] == ["-p", prompt]

    codex_cmd = agent_daemon.build_agent_command(
        agent_cli="codex",
        adapter="codex_exec",
        prompt=prompt,
    )
    assert codex_cmd[:2] == ["codex", "exec"]
    assert "--cd" in codex_cmd
    assert "workspace-write" in codex_cmd
    assert "never" in codex_cmd
    assert codex_cmd[-1] == prompt


def test_agent_daemon_infers_runtime_adapter():
    assert agent_daemon.infer_agent_adapter("codex") == "codex_exec"
    assert agent_daemon.infer_agent_adapter("/opt/homebrew/bin/codex") == "codex_exec"
    assert agent_daemon.infer_agent_adapter("claude") == "claude_print"
    assert agent_daemon.infer_agent_adapter("anything", "claude_print") == "claude_print"
    with pytest.raises(ValueError):
        agent_daemon.infer_agent_adapter("anything", "bad_adapter")
