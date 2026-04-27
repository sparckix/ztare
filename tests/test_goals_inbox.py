"""GP-132 goals-inbox tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ztare.orchestration import goals_inbox as gi


@pytest.fixture
def tmp_goals(tmp_path: Path) -> Path:
    (tmp_path / "pending").mkdir()
    (tmp_path / "active").mkdir()
    (tmp_path / "done").mkdir()
    return tmp_path


def _write_goal(root: Path, goal_id: str, **overrides):
    fm = {
        "goal_id": goal_id,
        "priority": overrides.get("priority", "medium"),
        "deadline": overrides.get("deadline"),
        "estimated_cost_usd": overrides.get("estimated_cost_usd", 0.0),
        "assigned_to": overrides.get("assigned_to", "role.manager"),
        "autonomous_scope_ok": overrides.get("autonomous_scope_ok", True),
        "created_by": "test_principal",
        "created_utc": "2026-04-23T12:00:00Z",
    }
    lines = ["---"]
    for k, v in fm.items():
        if v is None:
            lines.append(f"{k}: null")
        elif isinstance(v, bool):
            lines.append(f"{k}: {str(v).lower()}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {goal_id}")
    lines.append("")
    lines.append(overrides.get("body", "Test goal body."))
    (root / "pending" / f"{goal_id}.md").write_text("\n".join(lines), encoding="utf-8")


def test_list_pending_empty(tmp_goals: Path):
    assert gi.list_pending_goals(goals_root=tmp_goals) == []


def test_list_pending_returns_parsed(tmp_goals: Path):
    _write_goal(tmp_goals, "g1", priority="high", estimated_cost_usd=5.5)
    goals = gi.list_pending_goals(goals_root=tmp_goals)
    assert len(goals) == 1
    assert goals[0].goal_id == "g1"
    assert goals[0].priority == "high"
    assert goals[0].estimated_cost_usd == 5.5
    assert goals[0].autonomous_scope_ok is True


def test_sort_order_priority_then_deadline(tmp_goals: Path):
    _write_goal(tmp_goals, "g_low", priority="low", deadline="2026-04-24")
    _write_goal(tmp_goals, "g_urgent", priority="urgent", deadline="2026-05-01")
    _write_goal(tmp_goals, "g_high_early", priority="high", deadline="2026-04-24")
    _write_goal(tmp_goals, "g_high_late", priority="high", deadline="2026-04-30")
    goals = gi.list_pending_goals(goals_root=tmp_goals)
    ids = [g.goal_id for g in goals]
    assert ids == ["g_urgent", "g_high_early", "g_high_late", "g_low"]


def test_filter_by_assigned_to(tmp_goals: Path):
    _write_goal(tmp_goals, "g_manager", assigned_to="role.manager")
    _write_goal(tmp_goals, "g_engineer", assigned_to="role.engineer")
    goals = gi.list_pending_goals(
        goals_root=tmp_goals, assigned_to="role.manager"
    )
    assert len(goals) == 1
    assert goals[0].goal_id == "g_manager"


def test_claim_moves_to_active(tmp_goals: Path, tmp_path: Path, monkeypatch):
    # Isolate claims dir so we don't touch the real one
    from src.ztare.sessions import claims as claims_mod
    monkeypatch.setattr(claims_mod, "CLAIMS_DIR", tmp_path / "_claims")

    _write_goal(tmp_goals, "gx", priority="high")
    claimed = gi.claim_goal(
        goal_id="gx", session_id="sess_test", member_id="claude",
        role_id="manager", goals_root=tmp_goals,
    )
    assert claimed is not None
    assert claimed.path.parent.name == "active"
    assert not (tmp_goals / "pending" / "gx.md").exists()
    # Body annotation
    assert "## Claim" in claimed.path.read_text()


def test_claim_nonexistent_returns_none(tmp_goals: Path):
    assert gi.claim_goal(
        goal_id="missing", session_id="s", member_id="m",
        role_id="r", goals_root=tmp_goals,
    ) is None


def test_double_claim_fails_via_membrane(tmp_goals: Path, tmp_path: Path, monkeypatch):
    from src.ztare.sessions import claims as claims_mod
    monkeypatch.setattr(claims_mod, "CLAIMS_DIR", tmp_path / "_claims")

    _write_goal(tmp_goals, "gy")
    first = gi.claim_goal(
        goal_id="gy", session_id="sess1", member_id="claude",
        role_id="manager", goals_root=tmp_goals,
    )
    assert first is not None

    # Re-add a file in pending/ simulating an id collision / race
    _write_goal(tmp_goals, "gy")
    second = gi.claim_goal(
        goal_id="gy", session_id="sess2", member_id="claude",
        role_id="manager", goals_root=tmp_goals,
    )
    assert second is None  # claim membrane refuses


def test_mark_done_moves_to_done_and_appends_result(
    tmp_goals: Path, tmp_path: Path, monkeypatch,
):
    from src.ztare.sessions import claims as claims_mod
    monkeypatch.setattr(claims_mod, "CLAIMS_DIR", tmp_path / "_claims")

    _write_goal(tmp_goals, "gz")
    gi.claim_goal(
        goal_id="gz", session_id="s", member_id="m",
        role_id="r", goals_root=tmp_goals,
    )
    path = gi.mark_goal_done(
        goal_id="gz", session_id="s",
        result_summary="finished successfully",
        artifacts=["workspace/result.json", "findings.md"],
        cost_incurred_usd=0.75,
        goals_root=tmp_goals,
    )
    assert path is not None
    assert path.parent.name == "done"
    text = path.read_text()
    assert "## Result" in text
    assert "finished successfully" in text
    assert "workspace/result.json" in text
    assert "0.75" in text


def test_mark_blocked_stays_in_active(tmp_goals: Path, tmp_path: Path, monkeypatch):
    from src.ztare.sessions import claims as claims_mod
    monkeypatch.setattr(claims_mod, "CLAIMS_DIR", tmp_path / "_claims")

    _write_goal(tmp_goals, "gb")
    gi.claim_goal(
        goal_id="gb", session_id="s", member_id="m",
        role_id="r", goals_root=tmp_goals,
    )
    path = gi.mark_goal_blocked(
        goal_id="gb", session_id="s",
        blocker="needs principal authorization to widen scope",
        escalation_path="ztare_workspace/gates/pending/mgr_123.json",
        goals_root=tmp_goals,
    )
    assert path is not None
    assert path.parent.name == "active"  # stays active
    text = path.read_text()
    assert "## Blocked" in text
    assert "needs principal" in text
