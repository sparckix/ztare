from __future__ import annotations

import json
import hashlib
from pathlib import Path

from ztare.orchestrator.briefing_providers import surviving_candidates as sc
from ztare.orchestrator.briefing_providers.surviving_candidates import (
    SurvivingCandidatesProvider,
)
from ztare.orchestrator.mutator_briefing import BriefingContext
from ztare.common.observation_chart import capture_project_evidence_epoch


def _payload(exact: int, checked: int = 10, wrong_cells: int = 1, holdout: int = 0) -> dict:
    return {
        "score": 0.3333,
        "gates": {
            "grid_dsl_expressible": {"pass": True},
            "visible_replay_exact": {
                "pass": False,
                "detail": "replay mismatch",
                "diagnostics": {
                    "checked_rows": checked,
                    "exact_rows": exact,
                    "wrong_rows": checked - exact,
                    "wrong_cell_count": wrong_cells,
                    "first_mismatch": "replay mismatch at t=2 action=3",
                    "first_mismatch_signature": {
                        "bbox": [2, 8, 2, 10],
                        "pair_counts": [
                            {"predicted": 8, "real": 3, "count": 4},
                        ],
                        "color_displacement_hints": [{
                            "color": 9,
                            "count": 3,
                            "actual_minus_predicted": [0, -6],
                            "predicted_bbox": [2, 8, 2, 10],
                            "actual_bbox": [2, 2, 2, 4],
                        }],
                    },
                    "mismatch_classes": [{
                        "count": 36,
                        "first_row": 621,
                        "t": 128,
                        "action": 1,
                        "signature": {
                            "bbox": [61, 56, 62, 57],
                            "pair_counts": [
                                {"predicted": 8, "real": 3, "count": 4},
                            ],
                        },
                    }],
                },
            },
            "holdout_rollout_exact": {
                "pass": False,
                "value": holdout,
                "holdout_witness": {
                    "step_index": 0,
                    "t": 7,
                    "action": 1,
                    "entry_context_note": "holdout starts mid-episode at its first row t=7",
                    "divergent_cells": [
                        {"row": 0, "col": 0, "predicted": 9, "actual": 2},
                    ],
                },
            },
        },
    }


def _survivor_payload(checked: int = 10, holdout: int = 10) -> dict:
    return {
        "score": 1.0,
        "gates": {
            "grid_dsl_expressible": {"pass": True},
            "visible_replay_exact": {
                "pass": True,
                "diagnostics": {
                    "checked_rows": checked,
                    "exact_rows": checked,
                    "wrong_rows": 0,
                    "wrong_cell_count": 0,
                },
            },
            "holdout_rollout_exact": {"pass": True, "value": holdout},
        },
    }


def test_surviving_candidates_requires_producer_receipt_instead_of_prompt_gating(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    subs = project / "workspace" / "submissions"
    subs.mkdir(parents=True)
    (project / "gate_harness.py").write_text("# harness\n")
    weak = subs / "weak.py"
    strong = subs / "strong.py"
    weak.write_text("def step(grid, action, t): return grid\n")
    strong.write_text("def step(grid, action, t): return grid\n# better\n")

    ctx = BriefingContext(
        project_dir=project,
        iter_index=2,
        rubric={"briefing_compute_candidate_memory": True},
    )
    fragment = SurvivingCandidatesProvider().fragment(ctx)

    assert "DETERMINISTIC CANDIDATE MEMORY UNAVAILABLE" in fragment
    assert "prompt assembly is read-only" in fragment


def test_surviving_candidates_ignores_impure_cached_near_miss(tmp_path: Path) -> None:
    project = tmp_path / "project"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    (project / "gate_harness.py").write_text("# harness\n")
    (workspace / "candidate_memory.json").write_text(
        json.dumps(
            {
                "schema": "ztare-candidate-memory-v1",
                "records": [
                    {
                        "source_type": "deterministic_near_miss",
                        "submission": "workspace/submissions/impure.py",
                        "sha": "impure",
                        "visible_exact_rows": 99,
                        "visible_checked_rows": 100,
                        "visible_wrong_cells": 1,
                        "holdout_depth": 0,
                        "gate_score": 0.6667,
                        "source_excerpt": (
                            "_COUNT = 0\n"
                            "def PATCH_DELTA(base_next, state, action, t):\n"
                            "    global _COUNT\n"
                            "    _COUNT += 1\n"
                            "    return base_next\n"
                        ),
                    },
                    {
                        "source_type": "deterministic_near_miss",
                        "submission": "workspace/submissions/pure.py",
                        "sha": "pure",
                        "visible_exact_rows": 8,
                        "visible_checked_rows": 10,
                        "visible_wrong_cells": 2,
                        "holdout_depth": 0,
                        "gate_score": 0.3333,
                        "source_excerpt": "def step(grid, action, t): return grid\n",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    ctx = BriefingContext(project_dir=project, iter_index=2, rubric={})
    fragment = SurvivingCandidatesProvider().fragment(ctx)

    assert "pure.py" in fragment
    assert "impure.py" not in fragment


def test_surviving_candidates_reads_cache_without_prompt_time_gating(tmp_path: Path) -> None:
    project = tmp_path / "project"
    subs = project / "workspace" / "submissions"
    subs.mkdir(parents=True)
    (project / "gate_harness.py").write_text("# harness\n")
    candidate = subs / "near.py"
    candidate.write_text("def step(grid, action, t): return grid\n")
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=_payload(exact=8, checked=10, wrong_cells=2),
    )

    ctx = BriefingContext(project_dir=project, iter_index=2, rubric={})
    fragment = SurvivingCandidatesProvider().fragment(ctx)

    assert "Deterministic Candidate Memory" in fragment
    assert "visible 8/10" in fragment
    assert "### Mandatory Patch Base" in fragment
    assert "actual=predicted+(0,-6)" in fragment
    assert "Mismatch quotient classes" in fragment
    assert "n=36 row=621 t=128 a=1 bbox=[61, 56, 62, 57] 8->3x4" in fragment
    assert "def step(grid, action, t)" in fragment


def test_gate_writer_materializes_external_candidate_by_content_identity(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    candidate = tmp_path / "leaf_workbench" / "candidate.py"
    candidate.parent.mkdir()
    source = "def step(grid, action, t):\n    return grid\n"
    candidate.write_text(source, encoding="utf-8")
    digest = hashlib.sha256(source.encode()).hexdigest()

    gate_payload = _survivor_payload(checked=12, holdout=10)
    gate_payload["evidence_epoch"] = capture_project_evidence_epoch(project).to_dict()
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=gate_payload,
    )

    payload = json.loads(
        (project / "workspace" / "candidate_memory.json").read_text(encoding="utf-8")
    )
    record = payload["records"][0]
    assert record["submission"] == f"workspace/submissions/gated_{digest}.py"
    assert record["sha"] == digest
    assert record["carrier_evidence_identity"]["carrier_sha256"] == digest
    assert record["carrier_evidence_identity"]["evidence_epoch_sha256"] == (
        gate_payload["evidence_epoch"]["epoch_sha256"]
    )
    assert (project / record["submission"]).read_text(encoding="utf-8") == source


def test_surviving_candidates_renders_holdout_witness_from_record_payload(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    workspace = project / "workspace"
    submissions = workspace / "submissions"
    submissions.mkdir(parents=True)
    (project / "gate_harness.py").write_text("# harness\n")
    candidate = submissions / "winner.py"
    candidate.write_text("def step(grid, action, t):\n    return grid\n")
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=candidate,
        gate_payload={
            "score": 0.5,
            "gates": {
                "grid_dsl_expressible": {"pass": True},
                "visible_replay_exact": {
                    "pass": False,
                    "diagnostics": {
                        "checked_rows": 2,
                        "exact_rows": 1,
                        "wrong_rows": 1,
                        "wrong_cell_count": 2,
                        "first_mismatch": "replay mismatch at t=19 action=1",
                        "first_mismatch_signature": {"bbox": [61, 14, 62, 14]},
                    },
                },
                "holdout_rollout_exact": {
                    "pass": False,
                    "value": 0,
                    "holdout_witness": {
                        "step_index": 19,
                        "t": 19,
                        "action": 1,
                        "entry_context_note": "holdout starts mid-episode at its first row t=19",
                        "divergent_cells": [
                            {"row": 61, "col": 14, "predicted": 3, "actual": 11},
                            {"row": 62, "col": 14, "predicted": 3, "actual": 11},
                        ],
                    },
                },
            },
        },
    )

    fragment = SurvivingCandidatesProvider().fragment(
        BriefingContext(project_dir=project, iter_index=1, rubric={})
    )
    records = json.loads((workspace / "candidate_memory.json").read_text(encoding="utf-8"))

    assert "t=19" in fragment
    assert "(row=61,col=14) predicted 3 actual 11" in fragment
    assert records["records"][0]["holdout_witness"]["t"] == 19
    assert records["records"][0]["counterexample_trace"]["holdout_witness"]["divergent_cells"][1]["col"] == 14


def test_surviving_candidates_briefs_single_full_survivor(tmp_path: Path) -> None:
    project = tmp_path / "project"
    subs = project / "workspace" / "submissions"
    subs.mkdir(parents=True)
    (project / "gate_harness.py").write_text("# harness\n")
    candidate = subs / "winner.py"
    candidate.write_text("def step(grid, action, t):\n    return grid\n")
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=_survivor_payload(checked=12, holdout=10),
    )

    provider = SurvivingCandidatesProvider()
    ctx = BriefingContext(project_dir=project, iter_index=2, rubric={})
    fragment = provider.fragment(ctx)
    records = provider.structured_records(ctx)

    assert "BEST FULL SURVIVOR" in fragment
    assert "Mandatory Deterministic Baseline" in fragment
    assert "winner.py" in fragment
    assert "visible 12/12" in fragment
    assert records[0]["source_type"] == "full_survivor"
    assert records[0]["visible_exact_rows"] == 12


def test_candidate_memory_does_not_downgrade_an_unspecified_cegis_membrane(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    candidate = project / "workspace" / "submissions" / "winner.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("def step(grid, action, t): return grid\n")
    payload = _survivor_payload(checked=12, holdout=10)
    payload.update(
        {
            "run_role": "DISCOVERY",
            "withheld_refs": ["sealed_slice"],
            "exposed_refs": ["sealed_slice"],
        }
    )
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=payload,
    )

    unspecified = _survivor_payload(checked=12, holdout=10)
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=unspecified,
    )
    record = json.loads(
        (project / "workspace" / "candidate_memory.json").read_text(encoding="utf-8")
    )["records"][0]
    assert record["claim_class"] == "law_discovery"
    assert record["fresh_holdout_required"] is True
    assert record["withheld_refs"] == ["sealed_slice"]
    assert record["exposed_withheld_refs"] == ["sealed_slice"]

    evaluated = _survivor_payload(checked=12, holdout=10)
    evaluated["run_role"] = "EVALUATION"
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=evaluated,
    )
    record = json.loads(
        (project / "workspace" / "candidate_memory.json").read_text(encoding="utf-8")
    )["records"][0]
    assert record["claim_class"] == "clean_transfer"
    assert record["fresh_holdout_required"] is False


def test_surviving_candidates_ignores_stale_cached_full_survivor(tmp_path: Path) -> None:
    project = tmp_path / "project"
    subs = project / "workspace" / "submissions"
    subs.mkdir(parents=True)
    (project / "gate_harness.py").write_text("# harness\n")
    candidate = subs / "winner.py"
    candidate.write_text("def step(grid, action, t):\n    return grid\n")
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=_survivor_payload(checked=12, holdout=10),
    )
    candidate.write_text("def step(grid, action, t):\n    return tuple(grid)\n")

    provider = SurvivingCandidatesProvider()
    ctx = BriefingContext(project_dir=project, iter_index=2, rubric={})

    assert provider.fragment(ctx) == ""
    assert provider.structured_records(ctx) == []


def test_full_survivor_suppresses_near_miss_patch_base(tmp_path: Path) -> None:
    project = tmp_path / "project"
    subs = project / "workspace" / "submissions"
    subs.mkdir(parents=True)
    (project / "gate_harness.py").write_text("# harness\n")
    winner = subs / "winner.py"
    near = subs / "near.py"
    winner.write_text("def step(grid, action, t):\n    return grid\n# winner\n")
    near.write_text("def step(grid, action, t):\n    return grid\n# near\n")
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=near,
        gate_payload=_payload(exact=9, checked=10),
    )
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=winner,
        gate_payload=_survivor_payload(checked=10, holdout=10),
    )

    fragment = SurvivingCandidatesProvider().fragment(
        BriefingContext(project_dir=project, iter_index=2, rubric={})
    )

    assert "Mandatory Deterministic Baseline" in fragment
    assert "Mandatory Patch Base" not in fragment
    assert "# winner" in fragment
    assert "# near" not in fragment.split("Mandatory Deterministic Baseline", 1)[1]


def test_surviving_candidates_prompts_with_best_near_miss_source(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    subs = project / "workspace" / "submissions"
    subs.mkdir(parents=True)
    (project / "gate_harness.py").write_text("# harness\n")
    weak = subs / "weak.py"
    strong = subs / "strong.py"
    weak.write_text("def step(grid, action, t):\n    return grid\n# weak\n")
    strong.write_text("def step(grid, action, t):\n    return tuple(tuple(r) for r in grid)\n# strong\n")
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=weak,
        gate_payload=_payload(exact=2, checked=10),
    )
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=strong,
        gate_payload=_payload(exact=9, checked=10),
    )

    fragment = SurvivingCandidatesProvider().fragment(
        BriefingContext(project_dir=project, iter_index=2, rubric={})
    )

    assert "### Mandatory Patch Base" in fragment
    assert "# strong" in fragment
    assert "# weak" not in fragment.split("### Mandatory Patch Base", 1)[1]


def test_patch_base_demotion_is_indexed_by_blocking_run_lane(tmp_path: Path) -> None:
    project = tmp_path / "project"
    subs = project / "workspace" / "submissions"
    subs.mkdir(parents=True)
    (project / "gate_harness.py").write_text("# harness\n")
    candidate = subs / "near.py"
    candidate.write_text("def step(grid, action, t): return grid\n")
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=_payload(exact=9, checked=10),
    )
    ledger = project / "workspace" / "strategy_experiments.jsonl"
    advisory = {
        "failure_family_sha": "advisory",
        "lane": "advisory",
        "disposition": "open",
        "action_plan": {"required_next_gate": {"command": "phase_cost_regression"}},
    }
    ledger.write_text(json.dumps(advisory) + "\n", encoding="utf-8")
    ctx = BriefingContext(project_dir=project, iter_index=2, rubric={})

    assert "### Mandatory Patch Base" in SurvivingCandidatesProvider().fragment(ctx)

    blocking = {
        "failure_family_sha": "skill",
        "lane": "skill_acquisition",
        "disposition": "open",
        "action_plan": {"required_next_gate": {"command": "distinguishing_play"}},
    }
    ledger.write_text(
        json.dumps(advisory) + "\n" + json.dumps(blocking) + "\n",
        encoding="utf-8",
    )
    assert "### Diagnostic Patch Base" in SurvivingCandidatesProvider().fragment(ctx)


def test_root_near_miss_is_diagnostic_not_patch_base(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "workspace").mkdir()
    (project / "gate_harness.py").write_text("# harness\n")
    root_model = project / "test_model.py"
    root_model.write_text("def step(grid, action, t):\n    return grid\n# live root\n")
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=root_model,
        gate_payload=_payload(exact=8, checked=10, wrong_cells=2),
    )

    fragment = SurvivingCandidatesProvider().fragment(
        BriefingContext(project_dir=project, iter_index=2, rubric={})
    )

    assert "near-miss: test_model.py" in fragment
    assert "### Mandatory Patch Base" not in fragment
    assert "Use this carrier as the patch base" not in fragment


def test_worldmodel_near_miss_patch_base_is_artifact_first_not_inline_source(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    subs = project / "workspace" / "submissions"
    subs.mkdir(parents=True)
    (project / "gate_harness.py").write_text("# harness\n")
    candidate = subs / "near.py"
    candidate.write_text(
        "def step(grid, action, t):\n"
        "    return tuple(tuple(r) for r in grid)\n"
        "# stale narrative anchor should not be injected for worldmodel near-miss\n"
    )
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=_payload(exact=8, checked=10, wrong_cells=2),
    )

    fragment = SurvivingCandidatesProvider().fragment(
        BriefingContext(
            project_dir=project,
            iter_index=2,
            rubric={"substrate_class": "interactive_environment", "fit_expression_grammar": "grid_dsl"},
        )
    )

    assert "### Mandatory Patch Base" in fragment
    assert "Patch base file: `workspace/submissions/near.py`" in fragment
    assert hashlib.sha256(candidate.read_bytes()).hexdigest() in fragment
    assert "Mismatch quotient classes" in fragment
    assert "holdout=step=0 t=7 action=1" in fragment
    assert "stale narrative anchor" not in fragment
    assert "```python" not in fragment.split("### Mandatory Patch Base", 1)[1]


def test_worldmodel_near_miss_source_can_be_forced_inline_by_rubric(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    subs = project / "workspace" / "submissions"
    subs.mkdir(parents=True)
    (project / "gate_harness.py").write_text("# harness\n")
    candidate = subs / "near.py"
    candidate.write_text("def step(grid, action, t):\n    return grid\n# forced inline\n")
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=_payload(exact=8, checked=10, wrong_cells=2),
    )

    fragment = SurvivingCandidatesProvider().fragment(
        BriefingContext(
            project_dir=project,
            iter_index=2,
            rubric={
                "substrate_class": "interactive_environment",
                "fit_expression_grammar": "grid_dsl",
                "briefing_inline_near_miss_source": True,
            },
        )
    )

    assert "```python" in fragment
    assert "# forced inline" in fragment


def test_surviving_candidates_marks_stale_root_artifacts_lower_authority(tmp_path: Path) -> None:
    project = tmp_path / "project"
    subs = project / "workspace" / "submissions"
    subs.mkdir(parents=True)
    (project / "gate_harness.py").write_text("# harness\n")
    (project / "test_model.py").write_text("assert False, 'placeholder'\n")
    (project / "current_iteration.md").write_text("old prose about a prior carrier\n")
    candidate = subs / "near.py"
    candidate.write_text("def step(grid, action, t):\n    return tuple(tuple(r) for r in grid)\n")
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=_payload(exact=8, checked=10, wrong_cells=2),
    )

    fragment = SurvivingCandidatesProvider().fragment(
        BriefingContext(project_dir=project, iter_index=2, rubric={})
    )

    assert "Artifact authority notice" in fragment
    assert "Lower-authority root artifact" in fragment
    assert "Lower-authority prose artifact" in fragment
    assert "workspace/submissions/near.py" in fragment


def test_worldmodel_briefing_consumes_epoch_bound_repair_frontier(tmp_path: Path) -> None:
    project = tmp_path / "project"
    subs = project / "workspace" / "submissions"
    episodes = project / "raw" / "episodes"
    subs.mkdir(parents=True)
    episodes.mkdir(parents=True)
    (project / "gate_harness.py").write_text("# harness\n")
    episode = episodes / "episode_001.jsonl"
    episode.write_text('{"state":0}\n', encoding="utf-8")

    old = subs / "old.py"
    old.write_text("def step(grid, action, t):\n    return grid\n", encoding="utf-8")
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=old,
        gate_payload=_payload(exact=8, checked=10, wrong_cells=2),
    )
    new_source = "def step(grid, action, t):\n    return tuple(grid)\n"
    new = subs / "new.py"
    new.write_text(new_source, encoding="utf-8")
    root = project / "test_model.py"
    root.write_text(new_source, encoding="utf-8")
    sc.record_candidate_gate_payload(
        project_dir=project,
        candidate_path=root,
        gate_payload=_payload(exact=9, checked=10, wrong_cells=1),
    )
    old_sha = hashlib.sha256(old.read_bytes()).hexdigest()
    new_sha = hashlib.sha256(new.read_bytes()).hexdigest()
    epoch = capture_project_evidence_epoch(project)
    from ztare.validator.core.pre_judge_gate import evaluation_policy_sha256

    (project / "workspace" / "latest_patch_base_regression.json").write_text(
        json.dumps({
            "candidate_regression_receipt": {
                "candidate_relation": "improved_but_gate_failed",
                "candidate_submission": "workspace/submissions/new.py",
                "candidate_sha": new_sha,
                "candidate_exact_rows": 9,
                "candidate_wrong_cells": 1,
                "candidate_holdout_depth": 0,
                "candidate_gate_score": 0.3333,
                "best_prior_submission": "workspace/submissions/old.py",
                "best_prior_sha": old_sha,
                "best_prior_exact_rows": 8,
                "best_prior_wrong_cells": 2,
                "best_prior_holdout_depth": 0,
                "best_prior_gate_score": 0.3333,
            },
            "evidence_epoch": epoch.to_dict(),
            "evaluation_policy_sha256": evaluation_policy_sha256(),
        }),
        encoding="utf-8",
    )
    ctx = BriefingContext(
        project_dir=project,
        iter_index=2,
        rubric={
            "substrate_class": "interactive_environment",
            "fit_expression_grammar": "grid_dsl",
        },
    )

    fragment = SurvivingCandidatesProvider().fragment(ctx)
    assert "Best executable near-miss: workspace/submissions/new.py" in fragment

    episode.write_text('{"state":0}\n{"state":1}\n', encoding="utf-8")
    stale_fragment = SurvivingCandidatesProvider().fragment(ctx)
    assert "Best executable near-miss: workspace/submissions/old.py" in stale_fragment
