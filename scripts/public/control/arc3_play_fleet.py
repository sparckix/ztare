#!/usr/bin/env python3
"""Parallel Play Fleet for GP-250 evidence acquisition.

Runs K concurrent REAL sprint sessions — each in an isolated clone of the
project — merges banked rows into episode_001.jsonl once, after all members
exit.

Usage:
    python3 scripts/public/control/arc3_play_fleet.py \\
        --game ls20 --project arc3_ls20_gov --members 6 --steps 1500

Environment overrides:
    ZTARE_FLEET_MEMBERS  integer (default 6)
    ZTARE_PROBE_RIDER    0 to disable probe rider (passed through to members)

Member strategy — CLONE-AND-REAL-SPRINT:
  Each member k clones the project into
    $TMPDIR/ztare_fleet/<runid>/member_k/
  structured as a mini-repo so that arc3_play_loop.py's REPO derivation
  (Path(__file__).resolve().parents[3]) resolves to the clone root:
    member_k/
      scripts/public/control/arc3_play_loop.py   ← copy (not symlink; resolve() must land here)
      src/                                         ← symlink to real REPO/src
      rubrics/                                     ← symlink to real REPO/rubrics
      workspace/                                   ← dir with champion_spec.json symlink
      projects/arc3_ls20_gov/                      ← real clone
        raw/episodes/episode_001.jsonl             ← COPY (not hardlink; isolates writes)
        raw/episodes/episode_002.jsonl             ← COPY
        test_model.py                              ← copy
        workspace/                                 ← selective copy (no *.lock, no frontier/)
                                                    + frontier/ dir copied for visited warm-start
        gate_harness.py                            ← copy

  The real sprint (mode=sprint, cycles=1) runs inside the clone; its episode
  writes land in clone/projects/arc3_ls20_gov/raw/episodes/episode_001.jsonl.

  After the subprocess exits we diff the clone's episode_001 beyond the
  original row count → net-new rows → write to REAL project's
  raw/episodes/fleet_<runid>_<k>.jsonl for the existing merge step.

Project-dir resolution (what was found):
  arc3_play_loop.py main() derives project as:
      REPO = Path(__file__).resolve().parents[3]
      slug = f"arc3_{game_prefix}_gov"
      project = REPO / "projects" / slug
  There is NO --project CLI flag. The project dir is always REPO-relative.
  To redirect a member to a clone, we copy the play-loop script into
  member_k/scripts/public/control/ so __file__ resolves inside member_k/,
  making REPO = member_k/ and project = member_k/projects/arc3_ls20_gov/.

  Rubric: play_loop uses  REPO/"rubrics"/f"{slug}.json" for the dynamics
  assumption only (read-only); rubrics/ is a symlink → real repo rubrics/.

Concurrency: each clone is fully isolated (own scorecards, own episode file).
Cleanup: clone removed on success, kept on failure (receipt notes the path).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.worldmodel.adapter import episode_log_path  # noqa: E402
from ztare.worldmodel.episode_log import EpisodeLog  # noqa: E402


# ── helpers ──────────────────────────────────────────────────────────────────

def _resolve_game_id(game: str) -> "str | None":
    game = game.strip()
    if "-" in game:
        return game
    from ztare.substrates.arc_agi3 import list_games
    return next((g for g in list_games() if g.startswith(game)), None)


def _transition_hash(tr) -> str:
    """Content hash for dedup: (s, a, t, s_next) as canonical JSON."""
    payload = json.dumps(
        [tr.t, [list(r) for r in tr.s], tr.a, [list(r) for r in tr.s_next]],
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _count_post_boundary(rows) -> int:
    """Count rows whose pre-state is in the post-boundary regime."""
    from ztare.worldmodel.distinguishing_play import _context_post_boundary
    return sum(1 for tr in rows if _context_post_boundary(tr.s))


def _count_t19_a1(rows) -> int:
    return sum(1 for tr in rows if tr.t == 19 and tr.a == 1)


def _fleet_receipt_path(project: Path) -> Path:
    return project / "workspace" / "play_fleet.jsonl"


def _append_receipt(project: Path, row: dict) -> None:
    path = _fleet_receipt_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True, default=str) + "\n")


def _live_play_loop_running() -> bool:
    """True if a play-loop process OTHER than fleet's own children is alive.

    pgrep -f arc3_play_loop matches any process whose argv contains that string,
    including the fleet process itself (which imports play_loop) and its member
    subprocesses. We exclude our own PID so the guard only fires for EXTERNAL
    play-loop runs that would race on episode_001.jsonl.
    """
    try:
        result = subprocess.run(
            ["pgrep", "-f", "arc3_play_loop"],
            capture_output=True, timeout=5,
        )
        if result.returncode != 0:
            return False
        own_pid = os.getpid()
        pids = {int(p) for p in result.stdout.split() if p.strip().isdigit()}
        pids.discard(own_pid)
        return bool(pids)
    except Exception:  # noqa: BLE001
        return False


# ── clone construction ────────────────────────────────────────────────────────

_WORKSPACE_COPY_NAMES = {
    "candidate_memory.json",
    "champion_materialization.jsonl",
    "spec_receipts.jsonl",
    "distinguishing_play.jsonl",
    "abduced_core.json",
    "champion_spec.json",
    "candidate_pool.jsonl",
    "invariant_certificates.jsonl",
    "latest_sprint_receipt.json",
    "latest_frontier_scope.json",
    "open_world_brief.jsonl",
    "active_open_world_brief.json",
}

# Directories copied wholesale into the clone workspace. row_bitmaps/ is the
# content-addressed warm-start cache — without it each member re-derives
# identification from scratch and can burn its whole cycle before playing
# (fleet-v2 smoke: 206s of abduction, 0 rows banked).
_WORKSPACE_COPY_DIRS = {"row_bitmaps", "frontier"}


def _make_clone(
    *,
    real_project: Path,
    clone_root: Path,
    project_name: str,
) -> "tuple[Path, int]":
    """Build mini-repo clone at clone_root; return (clone_project, original_row_count).

    Structure:
        clone_root/
          scripts/public/control/arc3_play_loop.py  ← copy
          src/                                        ← symlink
          rubrics/                                    ← symlink
          workspace/champion_spec.json               ← symlink (legacy fallback)
          projects/<project_name>/                    ← real clone
    """
    # 1. scripts/public/control/arc3_play_loop.py (copy so __file__.resolve() lands here)
    play_loop_src = REPO / "scripts" / "public" / "control" / "arc3_play_loop.py"
    play_loop_dst = clone_root / "scripts" / "public" / "control" / "arc3_play_loop.py"
    play_loop_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(play_loop_src, play_loop_dst)

    # 2. src/ → symlink to real src (read-only modules, no writes)
    (clone_root / "src").symlink_to((REPO / "src").resolve())

    # 3. rubrics/ → symlink
    (clone_root / "rubrics").symlink_to((REPO / "rubrics").resolve())

    # 4. legacy workspace/champion_spec.json → symlink (best-effort)
    legacy_champ = REPO / "workspace" / "champion_spec.json"
    if legacy_champ.exists():
        clone_ws = clone_root / "workspace"
        clone_ws.mkdir(parents=True, exist_ok=True)
        (clone_ws / "champion_spec.json").symlink_to(legacy_champ.resolve())

    # 5. projects/<project_name>/ — the actual clone
    clone_project = clone_root / "projects" / project_name
    clone_project.mkdir(parents=True, exist_ok=True)

    # 5a. episode files — COPY to isolate writes
    ep1_src = episode_log_path(real_project)
    ep1_dst_dir = clone_project / "raw" / "episodes"
    ep1_dst_dir.mkdir(parents=True, exist_ok=True)
    ep1_dst = ep1_dst_dir / "episode_001.jsonl"
    shutil.copy2(ep1_src, ep1_dst)
    ep2_src = episode_log_path(real_project, episode=2)
    if ep2_src.exists():
        shutil.copy2(ep2_src, ep1_dst_dir / "episode_002.jsonl")

    # Count original rows before sprint
    original_log = EpisodeLog.read_jsonl(ep1_dst)
    original_count = len(original_log)

    # 5b. test_model.py — the champion carrier
    tm = real_project / "test_model.py"
    if tm.exists():
        shutil.copy2(tm, clone_project / "test_model.py")

    # 5c. gate_harness.py — gates need this
    gh = real_project / "gate_harness.py"
    if gh.exists():
        shutil.copy2(gh, clone_project / "gate_harness.py")

    # 5d. workspace/ — selective copy (no *.lock; frontier/ copied for visited warm-start)
    real_ws = real_project / "workspace"
    clone_ws_proj = clone_project / "workspace"
    clone_ws_proj.mkdir(parents=True, exist_ok=True)
    if real_ws.exists():
        for dname in _WORKSPACE_COPY_DIRS:
            src_d = real_ws / dname
            if src_d.is_dir():
                shutil.copytree(src_d, clone_ws_proj / dname, dirs_exist_ok=True)
        for name in _WORKSPACE_COPY_NAMES:
            src = real_ws / name
            if src.exists():
                shutil.copy2(src, clone_ws_proj / name)
        # ponytail: frontier/ already copied above via _WORKSPACE_COPY_DIRS; drop duplicate

    return clone_project, original_count


# ── member worker ─────────────────────────────────────────────────────────────

def _run_member(
    *,
    game: str,
    project_name: str,
    real_project_str: str,
    run_id: str,
    member_idx: int,
    fleet_tmpdir: str,
) -> dict:
    """One fleet member: clone → real sprint subprocess → harvest net-new rows."""
    t0 = time.monotonic()
    real_project = Path(real_project_str)
    clone_root = Path(fleet_tmpdir) / f"member_{member_idx}"
    clone_root.mkdir(parents=True, exist_ok=True)

    # Build clone
    try:
        clone_project, original_count = _make_clone(
            real_project=real_project,
            clone_root=clone_root,
            project_name=project_name,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "schema": "ztare-fleet-member-receipt-v1",
            "status": "member_failed",
            "stage": "clone",
            "error": f"{type(exc).__name__}: {str(exc)[:300]}",
            "run_id": run_id, "member": member_idx,
            "rows_banked": 0, "boundary_crossings": 0,
            "rider_fires": 0, "t19a1_rows": 0, "wall_s": 0,
            "clone_kept_for_debug": str(clone_root),
        }

    # Run REAL sprint in clone
    play_loop_in_clone = clone_root / "scripts" / "public" / "control" / "arc3_play_loop.py"
    venv_py = REPO / "venv" / "bin" / "python"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(clone_root / "src")
    env["ZTARE_PROBE_RIDER"] = env.get("ZTARE_PROBE_RIDER", "1")

    cmd = [
        str(venv_py),
        str(play_loop_in_clone),
        "--game", game,
        "--mode", "sprint",
        "--cycles", os.environ.get("ZTARE_FLEET_CYCLES", "2"),
    ]
    log_path = clone_root / "member_sprint.log"
    sprint_log_lines: list[str] = []
    try:
        result = subprocess.run(
            cmd,
            cwd=str(clone_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=1200,  # 20 min ceiling; parallel members inflate wall time ~1.7x vs solo
        )
        combined = result.stdout + result.stderr
        sprint_log_lines = combined.splitlines()
        log_path.write_text(combined, encoding="utf-8")
        if result.returncode not in (0, None):
            print(f"  [fleet:{member_idx}] sprint exited rc={result.returncode}", flush=True)
    except subprocess.TimeoutExpired:
        sprint_log_lines = ["TIMEOUT after 600s"]
        log_path.write_text("TIMEOUT", encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        sprint_log_lines = [f"subprocess error: {exc}"]
        log_path.write_text(str(exc), encoding="utf-8")

    # Harvest net-new rows from clone episode_001
    clone_ep1 = clone_project / "raw" / "episodes" / "episode_001.jsonl"
    harvested_rows: list = []
    try:
        clone_log = EpisodeLog.read_jsonl(clone_ep1)
        clone_all = list(clone_log)
        # Net-new = rows beyond the original count (sprint appended after)
        harvested_rows = clone_all[original_count:]
    except Exception:
        harvested_rows = []

    # Write harvested rows to real project's fleet file
    fleet_ep_dir = real_project / "raw" / "episodes"
    fleet_ep_dir.mkdir(parents=True, exist_ok=True)
    out_path = fleet_ep_dir / f"fleet_{run_id}_{member_idx}.jsonl"
    member_log = EpisodeLog()
    for tr in harvested_rows:
        member_log.append(tr.s, tr.a, tr.s_next, t=tr.t)
    member_log.write_jsonl(out_path)

    # Harvest rider rows from clone's distinguishing_play.jsonl
    rider_fires = 0
    try:
        clone_dp = clone_project / "workspace" / "distinguishing_play.jsonl"
        real_dp = real_project / "workspace" / "distinguishing_play.jsonl"
        if clone_dp.exists():
            clone_dp_lines = clone_dp.read_text(encoding="utf-8").splitlines()
            # Count lines beyond what we copied
            orig_dp_lines: list[str] = []
            if (real_project / "workspace" / "distinguishing_play.jsonl").exists():
                orig_dp_lines = real_dp.read_text(encoding="utf-8").splitlines()
            new_rider_lines = clone_dp_lines[len(orig_dp_lines):]
            rider_fires = len(new_rider_lines)
    except Exception:
        rider_fires = 0

    boundary_crossings = _count_post_boundary(harvested_rows)
    t19a1_rows = _count_t19_a1(harvested_rows)
    wall_s = round(time.monotonic() - t0, 2)

    receipt = {
        "schema": "ztare-fleet-member-receipt-v1",
        "run_id": run_id,
        "member": member_idx,
        "game": game,
        "original_count": original_count,
        "rows_banked": len(harvested_rows),
        "boundary_crossings": boundary_crossings,
        "rider_fires": rider_fires,
        "t19a1_rows": t19a1_rows,
        "wall_s": wall_s,
        "episode_file": str(out_path.relative_to(real_project)),
        "sprint_log_tail": sprint_log_lines[-50:] if sprint_log_lines else [],
        "clone_root": str(clone_root),
    }

    # Cleanup: remove clone on success, keep on failure
    if len(harvested_rows) > 0 or (wall_s > 30):
        # Consider it a successful run if it ran for a real amount of time
        try:
            shutil.rmtree(clone_root, ignore_errors=True)
            receipt.pop("clone_root", None)
        except Exception:
            pass
    else:
        # Keep clone for debugging
        receipt["clone_kept_for_debug"] = str(clone_root)

    return receipt


def _worker_entry(kwargs: dict, result_list_path: str) -> None:
    """Subprocess-friendly worker: run member and write receipt to a JSON file."""
    sys.path.insert(0, str(REPO / "src"))
    try:
        receipt = _run_member(**kwargs)
    except Exception as exc:  # noqa: BLE001
        receipt = {
            "schema": "ztare-fleet-member-receipt-v1",
            "status": "member_failed",
            "stage": "launch",
            "error": f"{type(exc).__name__}: {str(exc)[:300]}",
            "member": kwargs.get("member_idx", -1),
            "run_id": kwargs.get("run_id", ""),
            "rows_banked": 0, "boundary_crossings": 0,
            "rider_fires": 0, "t19a1_rows": 0, "wall_s": 0,
        }
    Path(result_list_path).write_text(json.dumps(receipt, default=str), encoding="utf-8")


# ── merge step ────────────────────────────────────────────────────────────────

def merge_fleet(
    *,
    project: Path,
    run_id: str,
    member_receipts: list[dict],
    dry_run: bool = False,
) -> dict:
    """Single-writer merge: dedup + append net-new rows to episode_001.jsonl.

    Dedup key = content hash of (t, s, a, s_next) — order-independent
    (confluence-tested in tests/test_order_independence.py).

    GUARD: refuses if a live play-loop process is detected (pgrep arc3_play_loop).
    """
    if _live_play_loop_running():
        receipt = {
            "schema": "ztare-fleet-merge-receipt-v1",
            "run_id": run_id,
            "status": "refused_concurrent_run",
            "reason": "live arc3_play_loop process detected (pgrep arc3_play_loop); "
                      "merge deferred to avoid concurrent writes to episode_001.jsonl",
        }
        _append_receipt(project, receipt)
        return receipt

    ep1_path = episode_log_path(project)
    try:
        ep1 = EpisodeLog.read_jsonl(ep1_path)
    except Exception:
        ep1 = EpisodeLog()

    existing_hashes = {_transition_hash(tr) for tr in ep1}
    before_total = len(ep1)

    fleet_rows: list = []
    for mr in member_receipts:
        ef = mr.get("episode_file")
        if not ef:
            continue
        fleet_path = project / ef
        if not fleet_path.exists():
            continue
        try:
            member_log = EpisodeLog.read_jsonl(fleet_path)
            fleet_rows.extend(member_log)
        except Exception:
            pass

    merged = 0
    dups = 0
    for tr in fleet_rows:
        h = _transition_hash(tr)
        if h in existing_hashes:
            dups += 1
            continue
        existing_hashes.add(h)
        ep1.append(tr.s, tr.a, tr.s_next, t=tr.t)
        merged += 1

    if not dry_run and merged > 0:
        ep1.write_jsonl(ep1_path)

    # archive fleet files
    archive_dir = project / "raw" / "episodes" / "fleet_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for mr in member_receipts:
        ef = mr.get("episode_file")
        if not ef:
            continue
        src = project / ef
        if src.exists():
            src.rename(archive_dir / src.name)

    rows_now = list(ep1)
    receipt = {
        "schema": "ztare-fleet-merge-receipt-v1",
        "run_id": run_id,
        "status": "merged",
        "merged_rows": merged,
        "dup_rows": dups,
        "new_total": len(rows_now),
        "post_boundary_rows": _count_post_boundary(rows_now),
        "t19_a1_rows": _count_t19_a1(rows_now),
    }
    _append_receipt(project, receipt)
    return receipt


# ── fleet driver ──────────────────────────────────────────────────────────────

def run_fleet(
    *,
    game: str = "ls20",
    project_slug: str | None = None,
    members: int | None = None,
    steps: int = 1500,
) -> dict:
    members = members or int(os.environ.get("ZTARE_FLEET_MEMBERS", "6"))
    if project_slug is None:
        prefix = game.split("-")[0]
        project_slug = f"arc3_{prefix}_gov"
    project = REPO / "projects" / project_slug

    game_id = _resolve_game_id(game)
    if game_id is None:
        return {"error": f"game {game} not found"}

    run_id = uuid.uuid4().hex[:8]
    print(f"[fleet] run={run_id} game={game_id} members={members} steps={steps}", flush=True)

    # Each member gets its own result file in a shared tmpdir
    fleet_tmpdir = Path(tempfile.gettempdir()) / "ztare_fleet" / run_id
    fleet_tmpdir.mkdir(parents=True, exist_ok=True)

    member_kwargs = [
        {
            "game": game,
            "project_name": project_slug,
            "real_project_str": str(project),
            "run_id": run_id,
            "member_idx": k,
            "fleet_tmpdir": str(fleet_tmpdir),
        }
        for k in range(members)
    ]

    # Launch members as concurrent subprocesses using multiprocessing
    import multiprocessing
    ctx = multiprocessing.get_context("spawn")

    result_files = [fleet_tmpdir / f"receipt_{k}.json" for k in range(members)]

    procs = [
        ctx.Process(
            target=_worker_entry,
            args=(kw, str(rf)),
        )
        for kw, rf in zip(member_kwargs, result_files)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join()

    receipts = []
    for k, rf in enumerate(result_files):
        try:
            receipts.append(json.loads(rf.read_text(encoding="utf-8")))
        except Exception:
            receipts.append({
                "schema": "ztare-fleet-member-receipt-v1",
                "member": k, "run_id": run_id,
                "error": "result_file_missing",
                "rows_banked": 0, "boundary_crossings": 0,
                "rider_fires": 0, "t19a1_rows": 0, "wall_s": 0,
            })
    receipts.sort(key=lambda r: r.get("member", 0))

    for r in receipts:
        _append_receipt(project, r)
        print(f"  member {r.get('member')}: rows={r.get('rows_banked')} "
              f"boundary_crossings={r.get('boundary_crossings')} "
              f"rider_fires={r.get('rider_fires')} "
              f"t19a1={r.get('t19a1_rows')} "
              f"wall_s={r.get('wall_s')}", flush=True)
        tail = r.get("sprint_log_tail", [])
        if tail:
            for line in tail[-5:]:
                print(f"    log: {line}", flush=True)

    merge = merge_fleet(project=project, run_id=run_id, member_receipts=receipts)
    print(f"\n[fleet] merge: {merge}", flush=True)
    if merge.get("status") == "merged":
        print(f"\n  post-boundary rows in episode_001: {merge['post_boundary_rows']}")
        print(f"  (t==19, a==1)   rows in episode_001: {merge['t19_a1_rows']}")
    return {"run_id": run_id, "members": receipts, "merge": merge}


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    a = sys.argv
    if "--help" in a or "-h" in a:
        print(
            "usage: arc3_play_fleet.py [--game GAME] [--project SLUG] "
            "[--members K] [--steps N]"
        )
        return 0
    game = a[a.index("--game") + 1] if "--game" in a else "ls20"
    project_slug = a[a.index("--project") + 1] if "--project" in a else None
    members = int(a[a.index("--members") + 1]) if "--members" in a else None
    steps = int(a[a.index("--steps") + 1]) if "--steps" in a else 1500

    result = run_fleet(game=game, project_slug=project_slug, members=members, steps=steps)
    if "error" in result:
        print(json.dumps(result))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
