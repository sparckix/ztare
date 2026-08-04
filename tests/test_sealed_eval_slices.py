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


def test_task_bound_archive_records_authoritative_empty_boundary_set(tmp_path):
    sys.path.insert(0, str(_ROOT / "scripts" / "public" / "control"))
    from arc3_play_loop import archive_sealed_eval_slice  # noqa: PLC0415
    from ztare.common.task_discharge import (
        TaskDischargeContract,
        TaskDischargeReceipt,
    )

    project = _project_dir(tmp_path)
    contract = TaskDischargeContract(
        contract_id="test.empty.boundaries.v1",
        adjudicator_id="test.adjudicator.v1",
        lifecycle_scope="current_run",
        owner="test",
    )
    receipt = TaskDischargeReceipt(
        contract_sha256=contract.sha256,
        adjudicator_id=contract.adjudicator_id,
        status="open",
        authority="test_adapter",
        observed={"done": False},
    )

    row = archive_sealed_eval_slice(
        project,
        _make_synthetic_log(2),
        source_carrier_sha256="a" * 64,
        task_contract=contract,
        task_discharge_receipt=receipt,
    )

    assert row["non_discharge_edge_indices"] == []
    stored = json.loads(
        (project / "workspace" / "sealed_eval_slices.jsonl")
        .read_text()
        .strip()
    )
    assert stored["non_discharge_edge_indices"] == []


def test_legacy_task_bound_archive_never_infers_missing_boundary_field(tmp_path):
    sys.path.insert(0, str(_ROOT / "scripts" / "public" / "control"))
    from arc3_play_loop import (  # noqa: PLC0415
        _sealed_non_discharge_edge_predicate,
        archive_sealed_eval_slice,
    )
    from ztare.common.task_discharge import (
        TaskDischargeContract,
        TaskDischargeReceipt,
    )

    project = _project_dir(tmp_path)
    contract = TaskDischargeContract(
        contract_id="test.legacy.typed.boundaries.v1",
        adjudicator_id="test.adjudicator.v1",
        lifecycle_scope="current_run",
        owner="test",
    )
    receipt = TaskDischargeReceipt(
        contract_sha256=contract.sha256,
        adjudicator_id=contract.adjudicator_id,
        status="open",
        authority="test_adapter",
        observed={"done": False},
    )
    row = archive_sealed_eval_slice(
        project,
        _make_synthetic_log(2),
        source_carrier_sha256="a" * 64,
        task_contract=contract,
        task_discharge_receipt=receipt,
    )
    # Simulate the typed archives emitted before the empty-set field became
    # mandatory. Their task identity is enough to forbid legacy frame inference.
    ledger = project / "workspace" / "sealed_eval_slices.jsonl"
    stored = json.loads(ledger.read_text())
    stored.pop("non_discharge_edge_indices")
    ledger.write_text(json.dumps(stored, sort_keys=True) + "\n")

    predicate, count, refs = _sealed_non_discharge_edge_predicate(
        project,
        source_carrier_sha256="a" * 64,
        task_contract_sha256=contract.sha256,
        report_payload={"cycles": []},
    )

    assert predicate is None
    assert count == 0


def test_goal_refutation_replays_only_in_same_task_chart_and_origin(tmp_path):
    sys.path.insert(0, str(_ROOT / "scripts" / "public" / "control"))
    from arc3_play_loop import (  # noqa: PLC0415
        _sealed_goal_hypothesis_refutations,
        archive_sealed_eval_slice,
    )
    from ztare.common.task_discharge import (
        TaskDischargeContract,
        TaskDischargeReceipt,
    )
    from ztare.worldmodel.goal_abduction import GoalHypothesisSet

    project = _project_dir(tmp_path)
    contract = TaskDischargeContract(
        contract_id="test.skill.v1",
        adjudicator_id="test.adjudicator.v1",
        lifecycle_scope="current_run",
        owner="test",
    )
    receipt = TaskDischargeReceipt(
        contract_sha256=contract.sha256,
        adjudicator_id=contract.adjudicator_id,
        status="open",
        authority="test_adapter",
        observed={"done": False},
    )
    origin = "b" * 64
    archive_sealed_eval_slice(
        project,
        _make_synthetic_log(3),
        source_carrier_sha256="a" * 64,
        task_contract=contract,
        task_discharge_receipt=receipt,
        source_epoch=2,
        origin_seed_sha256=origin,
        goal_hypothesis_refutations=("zero-state",),
    )

    goals = GoalHypothesisSet((
        ("rewritten-zero-state", lambda grid: grid == ((0, 0), (0, 0)), "test", {}),
    ))
    assert _sealed_goal_hypothesis_refutations(
        project,
        goals,
        task_contract=contract,
        source_epoch=2,
        origin_seed_sha256=origin,
    ) == ("rewritten-zero-state",)
    assert goals.active_count == 0

    changed_origin_goals = GoalHypothesisSet((
        ("rewritten-zero-state", lambda grid: grid == ((0, 0), (0, 0)), "test", {}),
    ))
    assert _sealed_goal_hypothesis_refutations(
        project,
        changed_origin_goals,
        task_contract=contract,
        source_epoch=2,
        origin_seed_sha256="c" * 64,
    ) == ()
    assert changed_origin_goals.active_count == 1


def test_sealed_non_discharge_edges_compile_only_to_search_control(tmp_path):
    sys.path.insert(0, str(_ROOT / "scripts" / "public" / "control"))
    from arc3_play_loop import (  # noqa: PLC0415
        _sealed_non_discharge_edge_predicate,
        archive_sealed_eval_slice,
    )
    from ztare.worldmodel.episode_log import EpisodeLog, Transition
    from ztare.worldmodel.transition_identity import TransitionIdentity

    project = _project_dir(tmp_path)
    source_sha = "a" * 64
    task_sha = "c" * 64
    regular = TransitionIdentity(
        kind="dynamics",
        authority="environment_adapter",
        source_epoch=2,
        target_epoch=2,
        evidence_refs=("test:dynamics",),
    )
    respawn = TransitionIdentity(
        kind="reset_boundary",
        authority="environment_adapter",
        source_epoch=2,
        target_epoch=3,
        boundary_kind="non_discharge_respawn",
    )
    completion = TransitionIdentity(
        kind="epoch_boundary",
        authority="environment_adapter",
        source_epoch=3,
        target_epoch=4,
        boundary_kind="level_completed",
    )
    ordinary_source, respawn_source, completion_source = (
        ((1,),), ((2,),), ((3,),)
    )
    row = archive_sealed_eval_slice(
        project,
        EpisodeLog([
            Transition(1, ordinary_source, 0, ((2,),), regular),
            Transition(2, respawn_source, 1, ((0,),), respawn),
            Transition(3, completion_source, 2, ((4,),), completion),
        ]),
        source_carrier_sha256=source_sha,
    )
    report = {
        "cycles": [{
            "task_discharged": False,
            "task_discharge_receipt": {
                "status": "open",
                "contract_sha256": task_sha,
            },
            "eval_slice": {"path": row["path"], "sha256": row["sha256"]},
        }]
    }

    predicate, count, refs = _sealed_non_discharge_edge_predicate(
        project,
        source_carrier_sha256=source_sha,
        task_contract_sha256=task_sha,
        report_payload=report,
    )

    assert count == 1
    assert refs == [{"path": row["path"], "sha256": row["sha256"]}]
    assert predicate(respawn_source, 1, 999) is True
    assert predicate(ordinary_source, 0, 1) is False
    assert predicate(completion_source, 2, 3) is False
    assert predicate.evidence_edges == ((
        respawn_source,
        1,
        f"{row['path']}#1",
        (0,),
    ),)
    assert len(predicate.history_trajectories) == 1
    assert predicate.history_trajectories[0].boundary_indices == frozenset({1})
    assert _sealed_non_discharge_edge_predicate(
        project,
        source_carrier_sha256="b" * 64,
        task_contract_sha256=task_sha,
        report_payload=report,
    ) == (None, 0, [])


def test_exact_law_witness_overrides_task_non_discharge_marker(tmp_path):
    sys.path.insert(0, str(_ROOT / "scripts" / "public" / "control"))
    from arc3_play_loop import (  # noqa: PLC0415
        _sealed_non_discharge_edge_predicate,
        archive_sealed_eval_slice,
    )
    from ztare.worldmodel.episode_log import EpisodeLog, Transition
    from ztare.worldmodel.transition_identity import TransitionIdentity

    project = _project_dir(tmp_path)
    source_sha = "a" * 64
    task_sha = "c" * 64
    identity = TransitionIdentity(
        kind="dynamics",
        authority="environment_adapter",
        source_epoch=2,
        target_epoch=2,
    )
    transition = Transition(7, ((1,),), 0, ((2,),), identity)
    row = archive_sealed_eval_slice(
        project,
        EpisodeLog([transition]),
        source_carrier_sha256=source_sha,
        non_discharge_edge_indices=(0,),
        source_epoch=2,
    )
    report = {
        "cycles": [{
            "task_discharged": False,
            "task_discharge_receipt": {
                "status": "open",
                "contract_sha256": task_sha,
            },
            "eval_slice": {"path": row["path"], "sha256": row["sha256"]},
        }]
    }

    predicate, count, _refs = _sealed_non_discharge_edge_predicate(
        project,
        source_carrier_sha256=source_sha,
        task_contract_sha256=task_sha,
        report_payload=report,
        source_epoch=2,
        transition_evidence=EpisodeLog([transition]),
    )

    assert predicate is None
    assert count == 0


def test_sealed_non_discharge_edges_preserve_typed_predecessor_chain(tmp_path):
    sys.path.insert(0, str(_ROOT / "scripts" / "public" / "control"))
    from arc3_play_loop import (  # noqa: PLC0415
        _sealed_non_discharge_edge_predicate,
        archive_sealed_eval_slice,
    )
    from ztare.common.task_discharge import (
        TaskDischargeContract,
        TaskDischargeReceipt,
    )
    from ztare.worldmodel.episode_log import EpisodeLog, Transition
    from ztare.worldmodel.transition_identity import TransitionIdentity

    project = _project_dir(tmp_path)
    source_sha = "a" * 64
    contract = TaskDischargeContract(
        contract_id="test.skill.v1",
        adjudicator_id="test.adjudicator.v1",
        lifecycle_scope="current_run",
        owner="test",
    )
    open_receipt = TaskDischargeReceipt(
        contract_sha256=contract.sha256,
        adjudicator_id=contract.adjudicator_id,
        status="open",
        authority="test_adapter",
        observed={"done": False},
    )
    boundary = TransitionIdentity(
        kind="reset_boundary",
        authority="environment_adapter",
        source_epoch=2,
        target_epoch=3,
        boundary_kind="non_discharge_respawn",
    )
    first_source, second_source = ((1,),), ((2,),)
    first = archive_sealed_eval_slice(
        project,
        EpisodeLog([Transition(1, first_source, 0, ((0,),), boundary)]),
        source_carrier_sha256=source_sha,
        task_contract=contract,
        task_discharge_receipt=open_receipt,
        non_discharge_edge_indices=(0,),
    )
    predicate, count, refs = _sealed_non_discharge_edge_predicate(
        project,
        source_carrier_sha256=source_sha,
        task_contract_sha256=contract.sha256,
        report_payload={"cycles": []},
    )
    assert count == 1
    assert predicate(first_source, 0, 99) is True
    projected_once, _, _ = _sealed_non_discharge_edge_predicate(
        project,
        source_carrier_sha256=source_sha,
        task_contract_sha256=contract.sha256,
        report_payload={"cycles": []},
        abstract_fn=lambda _state: "shared-support",
        coverage_fn=lambda identity: identity,
    )
    assert projected_once(((9,),), 0, 99) is False

    second = archive_sealed_eval_slice(
        project,
        EpisodeLog([Transition(2, second_source, 0, ((0,),), boundary)]),
        source_carrier_sha256=source_sha,
        task_contract=contract,
        task_discharge_receipt=open_receipt,
        search_control_predecessors=refs,
        non_discharge_edge_indices=(0,),
    )
    predicate, count, refs = _sealed_non_discharge_edge_predicate(
        project,
        source_carrier_sha256=source_sha,
        task_contract_sha256=contract.sha256,
        report_payload={"cycles": []},
        abstract_fn=lambda _state: "shared-support",
        coverage_fn=lambda identity: identity,
    )
    assert count == 2
    assert predicate(first_source, 0, 99) is True
    assert predicate(second_source, 0, 99) is True
    assert predicate(((9,),), 0, 99) is True
    assert predicate(((9,),), 1, 99) is False
    assert {item["path"] for item in refs} == {first["path"], second["path"]}


def test_sealed_edges_are_scoped_to_epoch_and_origin_seed(tmp_path):
    sys.path.insert(0, str(_ROOT / "scripts" / "public" / "control"))
    from arc3_play_loop import (  # noqa: PLC0415
        _sealed_non_discharge_edge_predicate,
        archive_sealed_eval_slice,
    )
    from ztare.common.task_discharge import (
        TaskDischargeContract,
        TaskDischargeReceipt,
    )
    from ztare.worldmodel.episode_log import EpisodeLog, Transition
    from ztare.worldmodel.transition_identity import TransitionIdentity

    project = _project_dir(tmp_path)
    source_sha = "a" * 64
    active_seed = "1" * 64
    stale_seed = "2" * 64
    contract = TaskDischargeContract(
        contract_id="test.epoch.scope.v1",
        adjudicator_id="test.adjudicator.v1",
        lifecycle_scope="current_run",
        owner="test",
    )
    receipt = TaskDischargeReceipt(
        contract_sha256=contract.sha256,
        adjudicator_id=contract.adjudicator_id,
        status="open",
        authority="test_adapter",
        observed={"done": False},
    )
    boundary = TransitionIdentity(
        kind="reset_boundary",
        authority="environment_adapter",
        source_epoch=2,
        target_epoch=3,
        boundary_kind="non_discharge_respawn",
    )
    stale_source = ((1,),)
    active_source = ((2,),)
    archive_sealed_eval_slice(
        project,
        EpisodeLog([Transition(1, stale_source, 0, ((0,),), boundary)]),
        source_carrier_sha256=source_sha,
        task_contract=contract,
        task_discharge_receipt=receipt,
        source_epoch=1,
        origin_seed_sha256=stale_seed,
        non_discharge_edge_indices=(0,),
    )
    active = archive_sealed_eval_slice(
        project,
        EpisodeLog([Transition(1, active_source, 0, ((0,),), boundary)]),
        source_carrier_sha256=source_sha,
        task_contract=contract,
        task_discharge_receipt=receipt,
        source_epoch=2,
        origin_seed_sha256=active_seed,
        non_discharge_edge_indices=(0,),
    )

    predicate, count, refs = _sealed_non_discharge_edge_predicate(
        project,
        source_carrier_sha256=source_sha,
        task_contract_sha256=contract.sha256,
        report_payload={"cycles": []},
        source_epoch=2,
        origin_seed_sha256=active_seed,
    )

    assert count == 1
    assert predicate(active_source, 0, 1) is True
    assert predicate(stale_source, 0, 1) is False
    assert refs == [{"path": active["path"], "sha256": active["sha256"]}]


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

    # plant an active holdout episode; run role alone must not expose it
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

    # Active holdout remains absent even in DISCOVERY.  Demotion requires a
    # typed evidence-role transition plus a successor withheld slice.
    episode_002_staged = list(pack.workbench.rglob("episode_002.jsonl"))
    assert episode_002_staged == []


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
