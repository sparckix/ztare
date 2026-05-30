"""Unit tests for iter_action_executor handlers + safety rails."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _setup(monkeypatch, tmp_path):
    """Redirect frontier_state + signals + working dir to tmp."""
    from src.ztare.role_extensions import frontier_state as fs
    monkeypatch.setattr(fs, "STATE_ROOT", tmp_path / "frontier_state")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_unknown_action_kind_returns_error(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    from src.ztare.role_extensions.iter_action_executor import execute_action
    out = execute_action({"action_kind": "not_a_real_kind", "params": {}})
    assert out["ok"] is False
    assert "unknown action_kind" in out["outcome"]


def test_create_lean_cage_writes_stub(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    from src.ztare.role_extensions.iter_action_executor import execute_action
    action = {
        "action_kind": "create_lean_cage",
        "params": {"cage_dir": "ztare_proofs/cages"},
        "rule_id": "test_axiom_rule",
        "from_event": {
            "axiom_label": "test_axiom_X",
            "axiom_statement": "for all n, f(n) > 0",
        },
    }
    out = execute_action(action)
    assert out["ok"] is True
    assert "Lean cage stub" in out["outcome"]
    cage_files = list((tmp_path / "ztare_proofs" / "cages").glob("test_axiom_X_*.lean"))
    assert len(cage_files) == 1
    body = cage_files[0].read_text()
    assert "for all n, f(n) > 0" in body
    assert "test_axiom_rule" in body


def test_demote_route_when_in_ranking(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    from src.ztare.role_extensions.frontier_state import (
        load_state, update_route_ranking, RouteEntry,
    )
    from src.ztare.role_extensions.iter_action_executor import execute_action
    s = load_state("test_proj")
    update_route_ranking(s, [
        RouteEntry(route_id="route_A", label="A", rank=1),
        RouteEntry(route_id="route_B", label="B", rank=2),
    ])
    out = execute_action({
        "action_kind": "demote_route_in_packet",
        "params": {"project_slug": "test_proj", "route_id": "route_A", "new_rank": 99},
    })
    assert out["ok"] is True
    s2 = load_state("test_proj")
    assert any(r["route_id"] == "route_A" and r["rank"] == 99 for r in s2.route_ranking)


def test_demote_route_missing_returns_failure(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    from src.ztare.role_extensions.frontier_state import load_state
    from src.ztare.role_extensions.iter_action_executor import execute_action
    s = load_state("test_proj")  # empty ranking
    out = execute_action({
        "action_kind": "demote_route_in_packet",
        "params": {"project_slug": "test_proj", "route_id": "route_X"},
    })
    assert out["ok"] is False
    assert "not in ranking" in out["outcome"]


def test_mutate_evidence_appends(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    project_dir = tmp_path / "projects" / "test_proj"
    project_dir.mkdir(parents=True)
    (project_dir / "evidence.txt").write_text("# header\n")
    from src.ztare.role_extensions.iter_action_executor import execute_action
    out = execute_action({
        "action_kind": "mutate_evidence",
        "params": {
            "project_slug": "test_proj",
            "additions": ["row_a 1.0", "row_b 2.0"],
        },
        "reason": "test append",
    })
    assert out["ok"] is True
    body = (project_dir / "evidence.txt").read_text()
    assert "row_a 1.0" in body
    assert "row_b 2.0" in body
    assert "RD-1.12 co-drive append" in body


def test_mutate_charter_appends_section(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    project_dir = tmp_path / "projects" / "test_proj"
    project_dir.mkdir(parents=True)
    (project_dir / "project_charter.md").write_text("# Charter\n")
    from src.ztare.role_extensions.iter_action_executor import execute_action
    out = execute_action({
        "action_kind": "mutate_charter",
        "params": {
            "project_slug": "test_proj",
            "section": "Test Section",
            "content": "this is a test addendum",
        },
        "rule_id": "test_rule",
    })
    assert out["ok"] is True
    body = (project_dir / "project_charter.md").read_text()
    assert "Test Section" in body
    assert "this is a test addendum" in body


def test_fork_substrate_writes_spec(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    project_dir = tmp_path / "projects" / "test_proj"
    project_dir.mkdir(parents=True)
    from src.ztare.role_extensions.iter_action_executor import execute_action
    out = execute_action({
        "action_kind": "fork_substrate",
        "params": {
            "project_slug": "test_proj",
            "evidence_diff_strategy": "constructive_complement",
        },
        "rule_id": "test_fork_rule",
        "reason": "primary route obstructed",
        "from_event": {"kind": "obstruction_detected"},
    })
    assert out["ok"] is True
    spec = project_dir / "workspace" / "frontier_co_drive_fork_spec.md"
    assert spec.exists()
    body = spec.read_text()
    assert "Fork-substrate spec" in body
    assert "constructive_complement" in body


def test_queue_cold_shot_writes_packet(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    project_dir = tmp_path / "projects" / "test_proj"
    project_dir.mkdir(parents=True)
    from src.ztare.role_extensions.iter_action_executor import execute_action
    out = execute_action({
        "action_kind": "queue_cold_shot",
        "params": {
            "project_slug": "test_proj",
            "model_id": "gpt-5.5",
            "prompt_template": "test_template_v1",
        },
        "rule_id": "test_rule",
    })
    assert out["ok"] is True
    packets = list((project_dir / "workspace").glob("cold_shot_packet_*.json"))
    assert len(packets) == 1
    payload = json.loads(packets[0].read_text())
    assert payload["model_id"] == "gpt-5.5"
    assert payload["prompt_template"] == "test_template_v1"


def test_drain_pending_executes_in_order(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    project_dir = tmp_path / "projects" / "test_proj"
    project_dir.mkdir(parents=True)
    (project_dir / "evidence.txt").write_text("# header\n")
    (project_dir / "project_charter.md").write_text("# Charter\n")
    from src.ztare.role_extensions.frontier_state import load_state, queue_action
    from src.ztare.role_extensions.iter_action_executor import drain_pending
    s = load_state("test_proj")
    queue_action(s, {
        "action_kind": "mutate_charter",
        "params": {"project_slug": "test_proj", "section": "S1", "content": "c1"},
    })
    s = load_state("test_proj")
    queue_action(s, {
        "action_kind": "mutate_evidence",
        "params": {"project_slug": "test_proj", "additions": ["row 5.0"]},
    })
    outcomes = drain_pending("test_proj")
    assert len(outcomes) == 2
    assert outcomes[0]["ok"] is True
    assert outcomes[1]["ok"] is True
    s2 = load_state("test_proj")
    assert s2.pending_actions == []


def test_safety_rail_blocks_excess_spend(monkeypatch, tmp_path):
    """If spend_tracker says no, executor must return blocked_by_safety_rail."""
    _setup(monkeypatch, tmp_path)
    # Stub check_budget_allows to deny
    import src.ztare.role_extensions.iter_action_executor as iax

    def _denied(**kwargs):
        return False
    monkeypatch.setattr(
        "src.ztare.supervisor.spend_tracker.check_budget_allows",
        _denied,
    )
    out = iax.execute_action({
        "action_kind": "mutate_charter",
        "params": {
            "project_slug": "test_proj",
            "section": "X", "content": "y",
            "estimated_cost_usd": 100.0,  # high to trigger gate
        },
    })
    assert out["ok"] is False
    assert "USD spend gate" in out.get("blocked_reason", "")
