"""Unit tests for iter_action_policy dispatcher."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _setup(monkeypatch, tmp_path):
    """Redirect frontier_state to tmp + write a synthetic policy yaml."""
    from src.ztare.role_extensions import frontier_state as fs
    from src.ztare.role_extensions import iter_action_policy as iap
    monkeypatch.setattr(fs, "STATE_ROOT", tmp_path / "frontier_state")
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text("""
schema_version: 1
rules:
  - id: test_rule_obstruction_fork
    when:
      kind: obstruction_detected
      consecutive_count: ">=2"
    do:
      action_kind: fork_substrate
      params:
        evidence_diff_strategy: constructive_complement
    reason: test fork rule
    cooldown_seconds: 0
  - id: test_rule_axiom_cage
    when:
      kind: verified_axiom_emitted
    do:
      action_kind: create_lean_cage
      params:
        cage_dir: ztare_proofs/cages
    reason: test cage rule
""", encoding="utf-8")
    return policy_path


def test_event_matches_rule_and_queues_action(monkeypatch, tmp_path):
    policy_path = _setup(monkeypatch, tmp_path)
    from src.ztare.role_extensions.iter_action_policy import dispatch_event
    from src.ztare.role_extensions.frontier_state import load_state
    event = {
        "kind": "obstruction_detected",
        "project_slug": "test_proj",
        "iter_index": 3,
        "route_id": "gate_AMBIENT_CONTROL",
        "consecutive_count": 2,
        "ts": "2026-05-02T15:00:00Z",
    }
    queued = dispatch_event(event, policy_path=policy_path)
    assert len(queued) == 1
    rule_id, action = queued[0]
    assert rule_id == "test_rule_obstruction_fork"
    assert action["action_kind"] == "fork_substrate"
    assert action["params"]["project_slug"] == "test_proj"
    assert action["params"]["route_id"] == "gate_AMBIENT_CONTROL"
    s = load_state("test_proj")
    assert len(s.pending_actions) == 1


def test_numeric_threshold_below_does_not_match(monkeypatch, tmp_path):
    policy_path = _setup(monkeypatch, tmp_path)
    from src.ztare.role_extensions.iter_action_policy import dispatch_event
    event = {
        "kind": "obstruction_detected",
        "project_slug": "test_proj",
        "consecutive_count": 1,  # below threshold of 2
    }
    queued = dispatch_event(event, policy_path=policy_path)
    assert queued == []


def test_unrelated_event_kind_no_match(monkeypatch, tmp_path):
    policy_path = _setup(monkeypatch, tmp_path)
    from src.ztare.role_extensions.iter_action_policy import dispatch_event
    event = {
        "kind": "champion_promoted",
        "project_slug": "test_proj",
    }
    queued = dispatch_event(event, policy_path=policy_path)
    assert queued == []


def test_axiom_event_creates_lean_cage_action(monkeypatch, tmp_path):
    policy_path = _setup(monkeypatch, tmp_path)
    from src.ztare.role_extensions.iter_action_policy import dispatch_event
    event = {
        "kind": "verified_axiom_emitted",
        "project_slug": "test_proj",
        "axiom_label": "test_axiom",
    }
    queued = dispatch_event(event, policy_path=policy_path)
    assert len(queued) == 1
    assert queued[0][1]["action_kind"] == "create_lean_cage"


def test_cooldown_blocks_repeat_fire(monkeypatch, tmp_path):
    """A rule with cooldown_seconds should not fire twice within the window."""
    from src.ztare.role_extensions import frontier_state as fs
    monkeypatch.setattr(fs, "STATE_ROOT", tmp_path / "frontier_state")
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text("""
rules:
  - id: cooldown_test
    when: { kind: test_event }
    do:
      action_kind: escalate_to_principal
      params: {}
    reason: cooldown test
    cooldown_seconds: 3600
""", encoding="utf-8")
    from src.ztare.role_extensions.iter_action_policy import dispatch_event
    ev = {"kind": "test_event", "project_slug": "test_proj"}
    q1 = dispatch_event(ev, policy_path=policy_path)
    q2 = dispatch_event(ev, policy_path=policy_path)
    assert len(q1) == 1
    assert len(q2) == 0  # blocked by cooldown


def test_missing_project_slug_returns_empty(monkeypatch, tmp_path):
    policy_path = _setup(monkeypatch, tmp_path)
    from src.ztare.role_extensions.iter_action_policy import dispatch_event
    event = {"kind": "obstruction_detected", "consecutive_count": 5}
    queued = dispatch_event(event, policy_path=policy_path)
    assert queued == []
