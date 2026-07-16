from __future__ import annotations

import json
import hashlib

from ztare.common.schema_routes import (
    OperationalRouteObstruction,
    append_consequence_event,
    append_schema_route_event,
    assert_operational_routes_ready,
    audit_project_schema_routes,
    observe_dispatched_schema_route_delivery,
    validate_schema_route_registry,
)

import pytest


def test_operational_route_requires_paired_consume(tmp_path):
    project = tmp_path / "demo"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    ledger = workspace / "deterministic_candidate_producer_receipts.jsonl"
    materialized = {
        "schema": "ztare-deterministic-candidate-producer-receipt-v1",
        "event": "materialized",
        "candidate_sha256": "candidate-a",
        "phase": "checkpoint_identification",
        "producer_id": "compiler-a",
    }
    # Re-emitting the same governing identity is idempotent; it does not create
    # a second learning transaction that needs a second synthetic consume.
    ledger.write_text(
        json.dumps(materialized) + "\n" + json.dumps(materialized) + "\n"
    )
    first = audit_project_schema_routes(project)
    assert first["halt_required"] is True
    assert first["errors"][0]["kind"] == "operational_write_without_downstream_consume"
    with pytest.raises(OperationalRouteObstruction, match="OPERATIONAL_ROUTE_HALT"):
        assert_operational_routes_ready(project)

    consumed = {**materialized, "event": "consumed_by_project_gate", "gate_pass": False}
    with ledger.open("a") as handle:
        handle.write(json.dumps(consumed) + "\n")
    second = audit_project_schema_routes(project)
    assert second["halt_required"] is False
    assert second["status"] == "pass"
    assert_operational_routes_ready(project)
    assert validate_schema_route_registry() == ()


def test_consequence_contract_requires_every_produced_outcome_to_reach_control(tmp_path):
    project = tmp_path / "demo"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    fields = {
        "contract_id": "factored_search_outcome_totality.v1",
        "subject_id": "problem-a",
        "outcome": "projection_noncommuting",
        "evidence_refs": ("counterexample:a",),
    }
    append_consequence_event(workspace, event="produced", **fields)

    orphaned = audit_project_schema_routes(project)
    assert orphaned["halt_required"] is True
    assert any(
        row["kind"] == "produced_outcome_without_state_transition"
        for row in orphaned["errors"]
    )

    append_consequence_event(workspace, event="consumed", **fields)
    consumed = audit_project_schema_routes(project)
    assert consumed["halt_required"] is False
    route = next(
        row for row in consumed["routes"]
        if row["route_id"] == "factored_search_outcome_totality.v1"
    )
    assert route["produced_count"] == route["consumed_count"] == 1


def test_counterexample_observation_requires_candidate_synthesis_first_fire(tmp_path):
    project = tmp_path / "demo"
    join = {"observation_sha256": "observation-a", "task_id": "task-a"}
    append_schema_route_event(
        project,
        schema_id="ztare-counterexample-observation-triple-v1",
        event="materialized",
        join_values=join,
    )

    produced = audit_project_schema_routes(project)
    assert any(
        row["kind"] == "operational_write_without_downstream_consume"
        and row["route_id"] == "counterexample_observation_to_domain_refinement.v1"
        for row in produced["errors"]
    )
    entering = assert_operational_routes_ready(
        project,
        entering_phase="governed_run",
    )
    route = next(
        row for row in entering["routes"]
        if row["route_id"] == "counterexample_observation_to_domain_refinement.v1"
    )
    assert route["pending_for_entering_phase"] == "governed_run"
    with pytest.raises(OperationalRouteObstruction):
        assert_operational_routes_ready(project, entering_phase="unrelated_phase")

    append_schema_route_event(
        project,
        schema_id="ztare-counterexample-observation-triple-v1",
        event="first_fire",
        join_values=join,
    )
    consumed = audit_project_schema_routes(project)
    assert not any(
        row.get("route_id") == "counterexample_observation_to_domain_refinement.v1"
        for row in consumed["errors"]
    )


def test_prompt_delivery_is_observable_but_cannot_claim_first_fire(tmp_path):
    project = tmp_path / "demo"
    observation = "observation-identity-a"
    task_id = "task-a"
    append_schema_route_event(
        project,
        schema_id="ztare-counterexample-observation-triple-v1",
        event="materialized",
        join_values={"observation_sha256": observation, "task_id": task_id},
    )
    records = [{
        "consumer_projection": {"observation_sha256": observation},
        "route_delivery": {
            "schema_id": "ztare-counterexample-observation-triple-v1",
            "event": "delivered_to_synthesis_prompt",
            "join_values": {
                "observation_sha256": observation,
                "task_id": task_id,
            },
            "render_anchors": [observation],
        },
    }]

    assert observe_dispatched_schema_route_delivery(
        project,
        records=records,
        rendered_text="projection omitted",
        consumer="candidate_synthesis",
        attempt_id="attempt-a",
    ) == ()
    with pytest.raises(OperationalRouteObstruction):
        assert_operational_routes_ready(project)

    assert observe_dispatched_schema_route_delivery(
        project,
        records=records,
        rendered_text=f"consumer_projection={observation}",
        consumer="candidate_synthesis",
        attempt_id="attempt-a",
    ) == ("counterexample_observation_to_domain_refinement.v1",)
    with pytest.raises(OperationalRouteObstruction):
        assert_operational_routes_ready(project)
    route_rows = [
        json.loads(line)
        for line in (
            project / "workspace" / "counterexample_observation_routes.jsonl"
        ).read_text(encoding="utf-8").splitlines()
    ]
    assert any(
        row.get("event") == "delivered_to_synthesis_prompt"
        for row in route_rows
    )

    append_schema_route_event(
        project,
        schema_id="ztare-counterexample-observation-triple-v1",
        event="first_fire",
        join_values={"observation_sha256": observation, "task_id": task_id},
    )
    assert_operational_routes_ready(project)


def test_unpromoted_repair_frontier_uses_task_identity_for_route_delivery(
    tmp_path,
    monkeypatch,
):
    """A visible retry frontier remains active before root promotion."""
    from ztare.worldmodel import leaf_workbench
    from ztare.common.leaf_workbench_environment import (
        resolve_leaf_workbench_environment,
    )
    from ztare.common.leaf_workbench_executor import (
        _handler_implementation_sha256,
    )

    project = tmp_path / "demo"
    workspace = project / "workspace"
    submissions = workspace / "submissions"
    receipts = workspace / "leaf_workbench_action_receipts"
    submissions.mkdir(parents=True)
    receipts.mkdir()

    root_source = "def step(grid, action, t):\n    return grid\n"
    frontier_source = root_source + "# retry frontier\n"
    (project / "test_model.py").write_text(root_source, encoding="utf-8")
    frontier_ref = "workspace/submissions/frontier.py"
    (project / frontier_ref).write_text(frontier_source, encoding="utf-8")
    frontier_sha = hashlib.sha256(frontier_source.encode("utf-8")).hexdigest()
    observation = "observation-identity-frontier"
    task_id = "frontier-task"
    capability_id = "inspect_worldmodel_counterexample_context"
    handler_sha = _handler_implementation_sha256(
        resolve_leaf_workbench_environment("worldmodel")["action_handlers"]
        [capability_id]
    )
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "active_frontier": {
                    "candidate_sha": frontier_sha,
                    "source_ref": frontier_ref,
                },
                "workbench_task": {
                    "task_id": task_id,
                    "source_ref": frontier_ref,
                    "admissible_capability_ids": [capability_id],
                    "morphism_sequence": [capability_id],
                    "objective": "consume the retry-frontier observation",
                },
            }
        ),
        encoding="utf-8",
    )
    (receipts / "receipt.json").write_text(
        json.dumps(
            {
                "capability_id": capability_id,
                "request": {
                    "input_refs": {"task_id": task_id},
                },
                    "receipt": {
                        "capability_id": capability_id,
                        "input_hashes": {
                            "handler_implementation_sha256": handler_sha,
                        },
                    "output_summary": json.dumps(
                        {"observation_sha256": observation}
                    ),
                },
            }
        ),
        encoding="utf-8",
    )
    append_schema_route_event(
        project,
        schema_id="ztare-counterexample-observation-triple-v1",
        event="materialized",
        join_values={"observation_sha256": observation, "task_id": task_id},
    )

    # Recreate the former confuser: candidate memory/root still points at the
    # inferior carrier while the content-addressed retry frontier owns the task.
    monkeypatch.setattr(
        leaf_workbench,
        "_best_candidate_memory_record",
        lambda _path: {"submission": "test_model.py", "sha": "root-carrier"},
    )
    records = leaf_workbench.worldmodel_leaf_workbench_records(project)
    receipt_record = next(
        row
        for row in records
        if row.get("record_role") == "active_task_first_fire"
    )
    assert receipt_record["consumer_projection"]["task_id"] == task_id
    assert receipt_record["consumer_projection"]["observation_sha256"] == observation
    assert observe_dispatched_schema_route_delivery(
        project,
        records=records,
        rendered_text=f"observation identity: {observation}",
        consumer="candidate_synthesis",
        attempt_id="attempt-frontier",
    ) == ("counterexample_observation_to_domain_refinement.v1",)
    with pytest.raises(OperationalRouteObstruction):
        assert_operational_routes_ready(project)
    append_schema_route_event(
        project,
        schema_id="ztare-counterexample-observation-triple-v1",
        event="first_fire",
        join_values={"observation_sha256": observation, "task_id": task_id},
    )
    assert_operational_routes_ready(project)


def test_repair_task_scope_closes_only_for_gate_bound_descendant(tmp_path):
    """Ancestry and acceptance authority are jointly necessary and sufficient."""
    from ztare.common.leaf_workbench_executor import (
        active_workbench_task_capability_scope,
    )

    project = tmp_path / "demo"
    workspace = project / "workspace"
    submissions = workspace / "submissions"
    submissions.mkdir(parents=True)
    frontier = submissions / "frontier.py"
    frontier.write_text(
        "def step(grid, action, t):\n    return grid\n",
        encoding="utf-8",
    )
    frontier_sha = hashlib.sha256(frontier.read_bytes()).hexdigest()
    task = {
        "task_id": "frontier-task",
        "source_ref": "workspace/submissions/frontier.py",
        "admissible_capability_ids": [
            "inspect_worldmodel_counterexample_context"
        ],
    }
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "active_frontier": {
                    "candidate_sha": frontier_sha,
                    "source_ref": task["source_ref"],
                },
                "workbench_task": task,
            }
        ),
        encoding="utf-8",
    )

    # An unrelated mutable root cannot retire the visible frontier.
    root = project / "test_model.py"
    root.write_text(
        "def step(grid, action, t):\n    return grid\n# older root\n",
        encoding="utf-8",
    )
    assert active_workbench_task_capability_scope(project)[1]["task_id"] == (
        "frontier-task"
    )

    # Composition alone is still an unaccepted proposal.
    root.write_text(
        "PATCH_BASE = {\n"
        f"    'source_ref': '{task['source_ref']}',\n"
        f"    'sha256': '{frontier_sha}',\n"
        "}\n"
        "def PATCH_DELTA(base_next, state, action):\n"
        "    return base_next\n",
        encoding="utf-8",
    )
    root_sha = hashlib.sha256(root.read_bytes()).hexdigest()
    assert active_workbench_task_capability_scope(project)[0]

    # A receipt for another carrier cannot retire this task either.
    champion_path = project / "champion_eval_results.json"
    champion_path.write_text(
        json.dumps(
            {
                "artifact_role": "champion",
                "pre_judge_gate_payload": {
                    "gated_sha256": "0" * 16,
                    "pre_judge_decision": {
                        "candidate_promotion_authorized": True,
                        "gate_contract_closed": True,
                        "candidate_sha": "0" * 12,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    assert active_workbench_task_capability_scope(project)[0]

    # The same descendant becomes task-closing only when the champion receipt
    # binds the gate transition to its bytes.
    champion_path.write_text(
        json.dumps(
            {
                "artifact_role": "champion",
                "pre_judge_gate_payload": {
                    "gated_sha256": root_sha,
                    "pre_judge_decision": {
                        "candidate_promotion_authorized": True,
                        "gate_contract_closed": True,
                        "candidate_sha": root_sha,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    assert active_workbench_task_capability_scope(project) == (frozenset(), {})


def test_repair_task_scope_expires_when_evidence_epoch_moves(tmp_path):
    from ztare.common.leaf_workbench_executor import (
        active_workbench_task_capability_scope,
    )
    from ztare.common.observation_chart import capture_project_evidence_epoch

    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    episodes = project / "raw" / "episodes"
    workspace.mkdir(parents=True)
    episodes.mkdir(parents=True)
    source = project / "test_model.py"
    source.write_text("def step(grid, action, t):\n    return grid\n", encoding="utf-8")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    episode = episodes / "episode_001.jsonl"
    episode.write_text('{"t":0,"s":[[0]],"a":0,"s_next":[[1]]}\n', encoding="utf-8")
    epoch = capture_project_evidence_epoch(project).epoch_sha256
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "active_frontier": {
                    "candidate_sha": source_sha,
                    "source_ref": "test_model.py",
                },
                "workbench_task": {
                    "task_id": "epoch-bound-task",
                    "source_ref": "test_model.py",
                    "source_sha256": source_sha,
                    "evidence_epoch_sha256": epoch,
                    "admissible_capability_ids": ["run_visible_json_probe"],
                },
            }
        ),
        encoding="utf-8",
    )
    assert active_workbench_task_capability_scope(project)[0]

    episode.write_text(
        episode.read_text(encoding="utf-8")
        + '{"t":1,"s":[[1]],"a":0,"s_next":[[1]]}\n',
        encoding="utf-8",
    )
    assert active_workbench_task_capability_scope(project) == (frozenset(), {})


def test_repair_task_scope_fails_closed_when_lifecycle_owner_errors(
    tmp_path, monkeypatch
):
    from ztare.common import leaf_workbench_environment
    from ztare.common.leaf_workbench_executor import (
        active_workbench_task_capability_scope,
    )

    project = tmp_path / "demo"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    source = project / "test_model.py"
    source.write_text("def step(grid, action, t):\n    return grid\n", encoding="utf-8")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "active_frontier": {
                    "candidate_sha": source_sha,
                    "source_ref": "test_model.py",
                },
                "workbench_task": {
                    "task_id": "owner-error-task",
                    "source_ref": "test_model.py",
                    "source_sha256": source_sha,
                    "admissible_capability_ids": ["run_visible_json_probe"],
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        leaf_workbench_environment,
        "resolve_leaf_workbench_environment",
        lambda _adapter_id: {
            "task_identity_status_fn": lambda *_args: (_ for _ in ()).throw(
                RuntimeError("lifecycle unavailable")
            )
        },
    )

    assert active_workbench_task_capability_scope(project) == (frozenset(), {})
