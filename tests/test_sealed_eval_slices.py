"""Tests for the sealed-eval-slice gap-closure (GP-250 dual-use fix).

Three properties under test:
  1. archival: archive_sealed_eval_slice writes a slice file + ledger row with correct sha256
  2. SEAL PROOF: build_briefing_pack never stages raw/episodes/eval_slices/ into a pack
  3. optional gate: fresh_eval_rollout fires only when ZTARE_FRESH_EVAL_SLICE=1 + slice present
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_synthetic_log(n: int = 5):
    """5-transition EpisodeLog with trivial 2×2 grids (all zeros)."""
    from ztare.worldmodel.episode_log import EpisodeLog
    log = EpisodeLog()
    g0 = ((0, 0), (0, 0))
    for i in range(n):
        log.append(g0, i % 2, g0, t=i)
    return log


def _project_dir(tmp_path: Path) -> Path:
    p = tmp_path / "projects" / "arc3_test_gov"
    (p / "raw" / "episodes").mkdir(parents=True)
    (p / "workspace").mkdir(parents=True)
    return p


# ---------------------------------------------------------------------------
# 1. archival
# ---------------------------------------------------------------------------

def test_archive_creates_slice_file_and_ledger_row(tmp_path):
    sys.path.insert(0, str(_ROOT / "scripts" / "public" / "control"))
    from arc3_play_loop import archive_sealed_eval_slice  # noqa: PLC0415

    project = _project_dir(tmp_path)
    log = _make_synthetic_log(5)
    row = archive_sealed_eval_slice(
        project, log, source_carrier_sha256="a" * 64
    )

    # slice file exists inside eval_slices/
    slice_path = project / row["path"]
    assert slice_path.exists(), "slice file must be created"
    assert "eval_slices" in str(slice_path), "must live under eval_slices/"

    # sha256 matches
    actual_sha = hashlib.sha256(slice_path.read_bytes()).hexdigest()
    assert row["sha256"] == actual_sha, "sha256 in ledger must match file bytes"

    # ledger row
    ledger = project / "workspace" / "sealed_eval_slices.jsonl"
    assert ledger.exists(), "ledger must be created"
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["source"] == "live_play"
    assert rows[0]["steps"] == 5
    assert rows[0]["source_carrier_sha256"] == "a" * 64


def test_archive_appends_multiple_rows(tmp_path):
    sys.path.insert(0, str(_ROOT / "scripts" / "public" / "control"))
    from arc3_play_loop import archive_sealed_eval_slice  # noqa: PLC0415

    project = _project_dir(tmp_path)
    log = _make_synthetic_log(3)
    archive_sealed_eval_slice(project, log, source_carrier_sha256="a" * 64)
    archive_sealed_eval_slice(project, log, source_carrier_sha256="a" * 64)

    ledger = project / "workspace" / "sealed_eval_slices.jsonl"
    rows = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    assert len(rows) == 2, "each call appends one row"


def test_evidence_admission_drops_only_identical_observations(tmp_path):
    sys.path.insert(0, str(_ROOT / "scripts" / "public" / "control"))
    from arc3_play_loop import _append_observations  # noqa: PLC0415
    from ztare.worldmodel.episode_log import EpisodeLog, Transition

    project = _project_dir(tmp_path)
    episode = project / "raw" / "episodes" / "episode_001.jsonl"
    a, b, c = ((1,),), ((2,),), ((3,),)
    original = Transition(t=4, s=a, a=1, s_next=b)
    EpisodeLog([original]).write_jsonl(episode)
    prefix = episode.read_bytes()
    loaded = EpisodeLog.read_jsonl(episode)

    loaded, admitted = _append_observations(
        project,
        [original, Transition(t=4, s=a, a=1, s_next=c)],
        log=loaded,
    )

    assert admitted == 1
    assert episode.read_bytes().startswith(prefix)
    index = loaded.context_observation_index()
    assert len(index) == 1
    assert len(next(iter(index.values()))) == 2


def test_evidence_admission_preserves_identity_upgrade(tmp_path):
    sys.path.insert(0, str(_ROOT / "scripts" / "public" / "control"))
    from arc3_play_loop import _append_observations  # noqa: PLC0415
    from ztare.worldmodel.episode_log import EpisodeLog, Transition
    from ztare.worldmodel.transition_identity import TransitionIdentity

    project = _project_dir(tmp_path)
    episode = project / "raw" / "episodes" / "episode_001.jsonl"
    a, b = ((1,),), ((2,),)
    original = Transition(t=4, s=a, a=1, s_next=b)
    identified = Transition(
        t=4,
        s=a,
        a=1,
        s_next=b,
        identity=TransitionIdentity(
            kind="dynamics",
            authority="environment_adapter",
            source_epoch=2,
            target_epoch=2,
            evidence_refs=("adapter:last_transition_identity",),
        ),
    )
    EpisodeLog([original]).write_jsonl(episode)
    loaded = EpisodeLog.read_jsonl(episode)

    loaded, admitted = _append_observations(project, [identified], log=loaded)

    assert admitted == 1
    assert list(loaded)[-1].identity == identified.identity


# ---------------------------------------------------------------------------
# 2. SEAL PROOF — build_briefing_pack must never stage eval_slices/
# ---------------------------------------------------------------------------

def test_pack_excludes_eval_slices(tmp_path):
    """SEAL PROOF: plant an eval slice in raw/episodes/eval_slices/ under a
    synthetic project, build a DISCOVERY-mode briefing pack, and assert the
    slice file is absent from the workbench directory."""
    from ztare.common.briefing_pack import BriefingPackRequest, build_briefing_pack
    from ztare.common.cegis_membrane import DISCOVERY

    # --- set up a minimal fake repo shape ---
    repo = tmp_path / "repo"
    project_name = "arc3_ls20_gov"
    project = repo / "projects" / project_name
    ep_dir = project / "raw" / "episodes"
    eval_dir = ep_dir / "eval_slices"
    eval_dir.mkdir(parents=True)
    (project / "workspace").mkdir(parents=True)
    (project / "gate_harness.py").write_text("# stub\n")  # needed for authority_project_path resolution

    # plant a visible episode (episode_002 is staged in DISCOVERY)
    ep2 = ep_dir / "episode_002.jsonl"
    ep2.write_text('{"t":0,"s":[[0]],"a":0,"s_next":[[0]]}\n')

    # plant a SEALED eval slice — this must NOT appear in the pack
    sealed = eval_dir / "eval_20260101T000000Z.jsonl"
    sealed.write_text('{"t":0,"s":[[1]],"a":0,"s_next":[[1]]}\n')

    # plant a ledger entry referencing the slice
    ledger = project / "workspace" / "sealed_eval_slices.jsonl"
    ledger.write_text(json.dumps({
        "path": f"raw/episodes/eval_slices/{sealed.name}",
        "sha256": hashlib.sha256(sealed.read_bytes()).hexdigest(),
        "recorded_utc": "20260101T000000Z",
        "steps": 1,
        "source": "live_play",
    }) + "\n")

    # inject a fake mutator briefing record so the ref gets picked up
    br_path = project / "workspace" / "mutator_briefing_iter_1_records.json"
    br_path.write_text(json.dumps({
        "records": [{
            "provider": "test",
            "source_ref": f"raw/episodes/eval_slices/{sealed.name}",
        }]
    }))

    os.environ["ZTARE_AGENT_VISIBLE_WORKBENCH_ROOT"] = str(tmp_path / "workbench")
    try:
        pack = build_briefing_pack(BriefingPackRequest(
            repo=repo,
            agent_id=f"autoresearch_mutator_{project_name}",
            task="test task",
            context="test context",
            run_role=DISCOVERY,
        ))
    finally:
        os.environ.pop("ZTARE_AGENT_VISIBLE_WORKBENCH_ROOT", None)

    # SEAL PROOF: no file under eval_slices/ must appear in the workbench
    staged_eval_slices = list(pack.workbench.rglob("eval_*"))
    assert staged_eval_slices == [], (
        f"SEAL BROKEN: eval_slices files found in pack workbench: {staged_eval_slices}"
    )

    # sanity: episode_002.jsonl IS staged in DISCOVERY (control check)
    episode_002_staged = list(pack.workbench.rglob("episode_002.jsonl"))
    assert episode_002_staged, "episode_002.jsonl should be staged in DISCOVERY (control check)"


# ---------------------------------------------------------------------------
# 3. optional gate fires only with env=1 and a slice present
# ---------------------------------------------------------------------------

def _write_toy_episode(path: Path, n: int = 3) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for i in range(n):
            f.write(json.dumps({"t": i, "s": [[0, 0], [0, 0]], "a": 0,
                                "s_next": [[0, 0], [0, 0]]}) + "\n")


def _write_toy_ledger(project: Path, slice_rel_path: str, steps: int) -> None:
    slice_abs = project / slice_rel_path
    sha = hashlib.sha256(slice_abs.read_bytes()).hexdigest()
    ledger = project / "workspace" / "sealed_eval_slices.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a") as f:
        f.write(json.dumps({
            "path": slice_rel_path,
            "sha256": sha,
            "recorded_utc": "20260101T000000Z",
            "steps": steps,
            "source": "live_play",
            "source_carrier_sha256": hashlib.sha256(
                (project / "test_model.py").read_bytes()
            ).hexdigest(),
        }) + "\n")


def _identity_test_model() -> str:
    """Candidate that always predicts no change (identity function)."""
    return "def step(grid, action, t):\n    return grid\n"


def _make_harness_project(tmp_path: Path):
    """Set up a minimal arc3_ls20_gov-shaped project for gate_harness tests."""
    project = tmp_path / "projects" / "arc3_test_gate_gov"
    ep_dir = project / "raw" / "episodes"
    ep_dir.mkdir(parents=True)

    # visible episode (identity transitions)
    _write_toy_episode(ep_dir / "episode_001.jsonl", n=3)
    # holdout episode
    _write_toy_episode(ep_dir / "episode_002.jsonl", n=3)
    # test_model.py
    (project / "test_model.py").write_text(_identity_test_model())
    (project / "workspace").mkdir(parents=True)
    return project


def _run_harness(project: Path, env_extra: dict | None = None) -> dict:
    """Import gate_harness with _PROJECT_DIR patched to our temp project."""
    harness_path = (
        Path(__file__).resolve().parents[1]
        / "projects" / "arc3_ls20_gov" / "gate_harness.py"
    )
    harness_src = harness_path.read_text()

    env_backup = {}
    for k, v in (env_extra or {}).items():
        env_backup[k] = os.environ.get(k)
        os.environ[k] = v
    try:
        # provide __file__ so the module-level Path(__file__).resolve().parent works,
        # then immediately overwrite _PROJECT_DIR after exec.
        ns: dict = {"__name__": "gate_harness_test", "__file__": str(harness_path)}
        exec(compile(harness_src, str(harness_path), "exec"), ns)  # noqa: S102
        # Patch paths to point at our test project
        ns["_PROJECT_DIR"] = project
        ns["_VISIBLE"] = project / "raw" / "episodes" / "episode_001.jsonl"
        ns["_HOLDOUT"] = project / "raw" / "episodes" / "episode_002.jsonl"
        ns["_CANDIDATE_PATH"] = project / "test_model.py"
        return ns["run_gates"]()
    finally:
        for k, backup in env_backup.items():
            if backup is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = backup


def test_fresh_gate_absent_when_env_off(tmp_path):
    """fresh_eval_rollout gate must NOT appear when ZTARE_FRESH_EVAL_SLICE is unset."""
    project = _make_harness_project(tmp_path)
    os.environ.pop("ZTARE_FRESH_EVAL_SLICE", None)
    result = _run_harness(project)
    assert "fresh_eval_rollout" not in result["gates"], (
        "fresh gate must be absent when env var is off"
    )


def test_fresh_gate_absent_when_no_ledger(tmp_path):
    """fresh_eval_rollout must be absent even when env=1 if no ledger exists."""
    project = _make_harness_project(tmp_path)
    result = _run_harness(project, {"ZTARE_FRESH_EVAL_SLICE": "1"})
    assert "fresh_eval_rollout" not in result["gates"], (
        "fresh gate must be absent when ledger is missing"
    )


def test_fresh_gate_fires_with_env_and_slice(tmp_path):
    """fresh_eval_rollout fires and has tier=heldout when env=1 + slice present."""
    project = _make_harness_project(tmp_path)
    # create a sealed eval slice (identity transitions -> candidate should pass)
    slice_rel = "raw/episodes/eval_slices/eval_20260101T000000Z.jsonl"
    _write_toy_episode(project / slice_rel, n=3)
    _write_toy_ledger(project, slice_rel, steps=3)

    result = _run_harness(project, {"ZTARE_FRESH_EVAL_SLICE": "1"})
    assert "fresh_eval_rollout" in result["gates"], "fresh gate must fire"
    gate = result["gates"]["fresh_eval_rollout"]
    assert gate["tier"] == "heldout", "tier must be heldout"
    assert "slice_path" in gate["detail"], "detail must include slice_path"
    assert "recorded_utc" in gate["detail"], "detail must include timestamp"
    assert gate["detail"]["source_carrier_sha256"] == hashlib.sha256(
        (project / "test_model.py").read_bytes()
    ).hexdigest()


@pytest.mark.parametrize("mutated_identity", ["candidate", "slice"])
def test_fresh_gate_rejects_identity_mutation(tmp_path, mutated_identity):
    project = _make_harness_project(tmp_path)
    slice_rel = "raw/episodes/eval_slices/eval_20260101T000000Z.jsonl"
    _write_toy_episode(project / slice_rel, n=3)
    _write_toy_ledger(project, slice_rel, steps=3)
    if mutated_identity == "candidate":
        (project / "test_model.py").write_text(_identity_test_model() + "# changed\n")
    else:
        with (project / slice_rel).open("a") as handle:
            handle.write("\n")

    result = _run_harness(project, {"ZTARE_FRESH_EVAL_SLICE": "1"})
    gate = result["gates"]["fresh_eval_rollout"]
    assert gate["pass"] is False
    assert "identity" in gate["error"] or "bytes" in gate["error"]
