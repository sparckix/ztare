"""Tests for arc3_play_fleet.py — clone-and-real-sprint flow, mocked subprocess.

Tests:
  1. clone_selective_copy_correctness — rubric resolvable in clone, episode copied
  2. harvest_diff                     — original N rows, clone N+k → k harvested
  3. t19a1_counter                    — counts rows with t==19 and a==1
  4. merge_unchanged                  — dedup + net-new unchanged from prior contract
  5. guard_unchanged                  — refuses when play loop live
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

# ── load the fleet module without executing __main__ ────────────────────────
_spec = importlib.util.spec_from_file_location(
    "arc3_play_fleet",
    REPO / "scripts" / "public" / "control" / "arc3_play_fleet.py",
)
fleet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet)


# ── minimal stub helpers ──────────────────────────────────────────────────────

def _grid(val: int = 0, h: int = 6, w: int = 20):
    return tuple(tuple(val for _ in range(w)) for _ in range(h))


def _post_boundary_grid():
    """grid[5][19] == 3 → _context_post_boundary returns True."""
    g = [list(_grid()[r]) for r in range(6)]
    g[5][19] = 3
    return tuple(tuple(r) for r in g)


# ── test 1: clone selective-copy correctness ──────────────────────────────────

def test_clone_selective_copy_correctness(tmp_path: Path) -> None:
    """Clone must contain rubric-resolvable project name and copied episode files.

    We build a minimal fake real_project, call _make_clone, then verify:
      - clone_project/raw/episodes/episode_001.jsonl exists and has original rows
      - clone_root/rubrics symlinks to REPO/rubrics (rubric resolution works)
      - clone_root/scripts/public/control/arc3_play_loop.py exists (is a copy)
      - clone_project name matches project_name (arc3_ls20_gov)
    """
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.adapter import episode_log_path

    # Build fake real project
    real_project = tmp_path / "real_proj"
    ep1 = episode_log_path(real_project)
    ep1.parent.mkdir(parents=True, exist_ok=True)
    log = EpisodeLog()
    log.append(_grid(0), 0, _grid(1), t=5)
    log.append(_grid(1), 1, _grid(2), t=6)
    log.write_jsonl(ep1)
    # test_model.py
    (real_project / "test_model.py").write_text("# stub")
    # workspace files
    ws = real_project / "workspace"
    ws.mkdir()
    (ws / "candidate_memory.json").write_text("{}")
    (ws / "champion_spec.json").write_text("{}")

    clone_root = tmp_path / "clone_root"
    project_name = "arc3_ls20_gov"

    clone_project, original_count = fleet._make_clone(
        real_project=real_project,
        clone_root=clone_root,
        project_name=project_name,
    )

    # Episode copy present with correct row count
    clone_ep1 = clone_project / "raw" / "episodes" / "episode_001.jsonl"
    assert clone_ep1.exists(), "clone episode_001.jsonl must exist"
    cloned_log = EpisodeLog.read_jsonl(clone_ep1)
    assert len(cloned_log) == 2
    assert original_count == 2

    # Rubric link exists and points somewhere useful
    rubrics_link = clone_root / "rubrics"
    assert rubrics_link.exists(), "clone rubrics/ must exist"

    # play_loop script present (copy, not symlink — so __file__.resolve() lands in clone)
    play_loop = clone_root / "scripts" / "public" / "control" / "arc3_play_loop.py"
    assert play_loop.exists(), "play_loop.py must be copied into clone"
    assert not play_loop.is_symlink(), "play_loop.py must be a copy, not a symlink"

    # Project name is correct (arc3_ls20_gov resolves rubric by name)
    assert clone_project.name == project_name

    # Real project's episode_001 is NOT the same inode (isolated)
    import os
    assert os.stat(clone_ep1).st_ino != os.stat(ep1).st_ino, \
        "clone episode must be a copy (different inode)"


# ── test 2: harvest diff ──────────────────────────────────────────────────────

def test_harvest_diff(tmp_path: Path) -> None:
    """_run_member harvests exactly the net-new rows the sprint added.

    Setup: real_project has N rows; we plant a clone whose episode_001 has N+k
    rows by mocking subprocess.run to write extra rows into the clone's ep1.
    Verify: rows_banked == k and fleet_<runid>_<m>.jsonl has k rows.
    """
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.adapter import episode_log_path

    N, k = 3, 4

    real_project = tmp_path / "real_proj"
    ep1 = episode_log_path(real_project)
    ep1.parent.mkdir(parents=True, exist_ok=True)
    log = EpisodeLog()
    for i in range(N):
        log.append(_grid(i), i % 3, _grid(i + 1), t=i)
    log.write_jsonl(ep1)
    # Holdout
    ep2 = episode_log_path(real_project, episode=2)
    EpisodeLog().write_jsonl(ep2)
    (real_project / "test_model.py").write_text("# stub")
    (real_project / "workspace").mkdir(exist_ok=True)

    run_id = "test0001"
    member_idx = 0

    # We patch subprocess.run so instead of actually running a sprint it appends k
    # extra rows to the clone's episode_001.jsonl.
    real_subprocess_run = subprocess.run if False else None  # noqa: F841

    def fake_subprocess_run(cmd, **kwargs):
        # Find the clone's episode_001 and append k rows
        clone_root_candidate = Path(kwargs.get("cwd", "."))
        # episode_001 is at clone_root/projects/arc3_ls20_gov/raw/episodes/episode_001.jsonl
        # but member_k structure may be nested under fleet_tmpdir/member_0/
        # Search under clone_root
        ep1_candidates = list(clone_root_candidate.glob("**/episode_001.jsonl"))
        for ep1_path in ep1_candidates:
            existing = EpisodeLog.read_jsonl(ep1_path)
            for j in range(k):
                existing.append(_grid(N + j), j % 3, _grid(N + j + 1), t=N + j)
            existing.write_jsonl(ep1_path)
        import subprocess as _sp
        class FakeResult:
            returncode = 0
            stdout = "sprint 1: multilife depth=42 log=100\n"
            stderr = ""
        return FakeResult()

    import subprocess
    with patch.object(subprocess, "run", side_effect=fake_subprocess_run):
        fleet_tmpdir = tmp_path / "fleet_tmp"
        fleet_tmpdir.mkdir()
        receipt = fleet._run_member(
            game="ls20",
            project_name="arc3_ls20_gov",
            real_project_str=str(real_project),
            run_id=run_id,
            member_idx=member_idx,
            fleet_tmpdir=str(fleet_tmpdir),
        )

    assert receipt["rows_banked"] == k, f"expected {k} rows banked, got {receipt['rows_banked']}"
    out_path = real_project / "raw" / "episodes" / f"fleet_{run_id}_{member_idx}.jsonl"
    assert out_path.exists(), "fleet episode file must be written"
    harvested = EpisodeLog.read_jsonl(out_path)
    assert len(harvested) == k, f"fleet file must have exactly {k} rows"


# ── test 3: t19a1 counter ─────────────────────────────────────────────────────

def test_t19a1_counter(tmp_path: Path) -> None:
    """_count_t19_a1 counts only rows with t==19 AND a==1."""
    from ztare.worldmodel.episode_log import EpisodeLog

    g = _grid(0)
    log = EpisodeLog()
    log.append(g, 0, g, t=0)    # no
    log.append(g, 1, g, t=19)   # YES
    log.append(g, 0, g, t=19)   # t==19 but a!=1 → no
    log.append(g, 1, g, t=18)   # a==1 but t!=19 → no
    log.append(g, 1, g, t=19)   # YES

    rows = list(log)
    assert fleet._count_t19_a1(rows) == 2


# ── test 4: merge unchanged ────────────────────────────────────────────────────

def test_merge_unchanged(tmp_path: Path) -> None:
    """merge_fleet dedup + net-new contract is unchanged from prior version."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.adapter import episode_log_path

    project = tmp_path / "proj"
    ep1_path = episode_log_path(project)
    ep1_path.parent.mkdir(parents=True, exist_ok=True)

    g0, g1, g2 = _grid(0), _grid(1), _grid(2)

    existing = EpisodeLog()
    existing.append(g0, 0, g1, t=0)
    existing.write_jsonl(ep1_path)

    member_path = project / "raw" / "episodes" / "fleet_run001_0.jsonl"
    member_path.parent.mkdir(parents=True, exist_ok=True)
    m_log = EpisodeLog()
    m_log.append(g0, 0, g1, t=0)   # dup
    m_log.append(g1, 1, g2, t=1)   # new
    m_log.write_jsonl(member_path)

    receipts = [{
        "member": 0, "run_id": "run001", "rows_banked": 2,
        "episode_file": str(member_path.relative_to(project)),
    }]

    with patch.object(fleet, "_live_play_loop_running", return_value=False):
        merge = fleet.merge_fleet(project=project, run_id="run001", member_receipts=receipts)

    assert merge["status"] == "merged"
    assert merge["merged_rows"] == 1
    assert merge["dup_rows"] == 1
    assert merge["new_total"] == 2

    # fleet file archived
    assert not member_path.exists()
    archive = project / "raw" / "episodes" / "fleet_archive" / "fleet_run001_0.jsonl"
    assert archive.exists()

    final = EpisodeLog.read_jsonl(ep1_path)
    assert len(final) == 2


# ── test 5: guard unchanged ────────────────────────────────────────────────────

def test_guard_unchanged(tmp_path: Path) -> None:
    """merge refuses when live play loop detected."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.adapter import episode_log_path

    project = tmp_path / "proj"
    ep1_path = episode_log_path(project)
    ep1_path.parent.mkdir(parents=True, exist_ok=True)
    EpisodeLog().write_jsonl(ep1_path)

    with patch.object(fleet, "_live_play_loop_running", return_value=True):
        merge = fleet.merge_fleet(project=project, run_id="runXXX", member_receipts=[])

    assert merge["status"] == "refused_concurrent_run"
    assert len(EpisodeLog.read_jsonl(ep1_path)) == 0


# ── test 6: real member end-to-end sprint ────────────────────────────────────

@pytest.mark.slow
def test_fleet_member_actually_runs_sprint(tmp_path: Path) -> None:
    """One real member must enter sprint mode and run for >30s.

    A member that dies at wall_s=0 (clone-build failure, swallowed exception)
    or never enters sprint will FAIL this test.

    Marked slow — allow up to 250s.
    """
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.adapter import episode_log_path

    # Use the real project so we get a real champion_spec / workspace state
    real_project = REPO / "projects" / "arc3_ls20_gov"
    if not real_project.exists():
        pytest.skip("arc3_ls20_gov project not found — skip in CI")

    run_id = "slowtest01"
    fleet_tmpdir = tmp_path / "fleet_tmp"
    fleet_tmpdir.mkdir()

    receipt = fleet._run_member(
        game="ls20",
        project_name="arc3_ls20_gov",
        real_project_str=str(real_project),
        run_id=run_id,
        member_idx=0,
        fleet_tmpdir=str(fleet_tmpdir),
    )

    # Must not have failed at clone stage
    assert receipt.get("status") != "member_failed", (
        f"member_failed at stage={receipt.get('stage')}: {receipt.get('error')}"
    )

    wall_s = receipt.get("wall_s", 0)
    assert wall_s > 30, (
        f"wall_s={wall_s} — member finished impossibly fast; likely died before sprint"
    )

    # Sprint-phase marker must appear in the log
    sprint_log = receipt.get("sprint_log_tail", [])
    sprint_entered = any(
        "play mode: sprint" in line or "SPRINT" in line or "sprint 1:" in line
        for line in sprint_log
    )
    assert sprint_entered, (
        f"Sprint phase marker not found in log tail — sprint never entered.\n"
        f"Last 20 lines:\n" + "\n".join(sprint_log[-20:])
    )

    print(f"\n[slow-test] wall_s={wall_s} rows_banked={receipt.get('rows_banked')}")


# ── self-check ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pathlib, tempfile
    with tempfile.TemporaryDirectory() as td:
        test_t19a1_counter(pathlib.Path(td))
    print("self-check: t19a1 counter OK")
    with tempfile.TemporaryDirectory() as td:
        test_guard_unchanged(pathlib.Path(td))
    print("self-check: guard refusal OK")
    print("all self-checks passed")
