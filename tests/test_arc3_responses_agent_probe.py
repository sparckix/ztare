from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


def _load():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts/public/control/arc3_responses_agent_probe.py"
    )
    spec = importlib.util.spec_from_file_location(
        "arc3_responses_agent_probe_under_test",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Responses:
    def __init__(self):
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        index = len(self.requests)
        return SimpleNamespace(
            id=f"response-{index}",
            reasoning=SimpleNamespace(context="all_turns"),
            output=[
                SimpleNamespace(
                    type="function_call",
                    name="take_arc_action",
                    call_id=f"call-{index}",
                    arguments='{"action":0,"prediction":"the marker moves"}',
                )
            ],
            usage=SimpleNamespace(
                input_tokens=10,
                output_tokens=5,
                input_tokens_details=SimpleNamespace(cached_tokens=index - 1),
            ),
        )


class _Adapter:
    action_arity = 2

    def __init__(self):
        self.levels_completed = 0
        self.current_epoch = 0
        self.actions = []

    def reset(self):
        return ((0, 0), (0, 1))

    def step(self, action):
        self.actions.append(action)
        self.current_epoch += 1
        if len(self.actions) == 2:
            self.levels_completed = 1
        return ((0, 0), (1, 0))


def test_probe_gives_one_continuing_reasoner_every_action() -> None:
    module = _load()
    responses = _Responses()
    adapter = _Adapter()

    payload = module.run_probe(
        client=SimpleNamespace(responses=responses),
        adapter=adapter,
        game_id="fake-game",
        budget=4,
        model_id="gpt-5.6-sol",
        reasoning_effort="xhigh",
        reasoning_context="all_turns",
        max_output_tokens=1024,
        timeout_seconds=30,
    )

    assert payload["status"] == "level_gained"
    assert payload["actions_executed"] == 4
    assert payload["levels_gained"] == 1
    assert payload["first_level_action"] == 2
    assert payload["level_boundary_actions"] == [{
        "action_count": 2,
        "from_levels_completed": 0,
        "to_levels_completed": 1,
    }]
    assert adapter.actions == [0, 0, 0, 0]
    assert responses.requests[1]["previous_response_id"] == "response-1"
    assert responses.requests[1]["input"][0]["type"] == "function_call_output"
    assert (
        responses.requests[1]["input"][0]["call_id"]
        == responses.requests[0]["input"][0].get("call_id", "call-1")
    )
    assert payload["output_tokens"] == 20
    assert payload["cached_input_tokens"] == 6
    assert len(payload["observations"]) == 5
    assert (
        payload["turns"][0]["source_observation_sha256"]
        == payload["observations"][0]["sha256"]
    )
    assert (
        payload["turns"][-1]["successor_observation_sha256"]
        == payload["observations"][-1]["sha256"]
    )


def test_frame_encoding_is_lossless_and_visual() -> None:
    module = _load()
    grid = ((0, 0, 2), (2, 2, 2))

    content = module.observation_content(
        grid,
        action_count=3,
        levels_completed=1,
        available_action_indices=(0, 1),
    )

    assert content[0]["type"] == "input_text"
    assert '"grid_rle_rows":["0x2,2x1","2x3"]' in content[0]["text"]
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/png;base64,")


class _SubscriptionThread:
    def __init__(self):
        self.calls = []

    def decide(self, observation):
        self.calls.append(observation)
        return {
            "schema": "ztare-codex-subscription-action-decision-v1",
            "turn_index": len(self.calls) - 1,
            "session_id": "session-1",
            "session_tick_count": len(self.calls),
            "action": 1,
            "prediction": "one cell changes",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "xhigh",
            "continuation": "codex_exec_resume",
        }


def test_subscription_probe_uses_one_resumed_actor() -> None:
    module = _load()
    adapter = _Adapter()
    actor = _SubscriptionThread()

    payload = module.run_subscription_probe(
        adapter=adapter,
        game_id="fake-game",
        budget=4,
        model_id="gpt-5.6-sol",
        reasoning_effort="xhigh",
        timeout_seconds=30,
        resume_session=True,
        thread=actor,
    )

    assert payload["status"] == "level_gained"
    assert payload["actions_executed"] == 4
    assert payload["first_level_action"] == 2
    assert payload["actor"]["reasoning_context_attested"] is False
    assert [row["action_count"] for row in payload["turns"]] == [1, 2, 3, 4]
    assert actor.calls[1]["action_count"] == 1
    assert len(payload["observations"]) == 5
    assert payload["sleep_cycles"] == []


def test_subscription_probe_restores_nonterminal_action_prefix() -> None:
    module = _load()
    adapter = _Adapter()
    actor = _SubscriptionThread()

    payload = module.run_subscription_probe(
        adapter=adapter,
        game_id="fake-game",
        budget=2,
        model_id="gpt-5.6-sol",
        reasoning_effort="xhigh",
        timeout_seconds=30,
        resume_session=True,
        thread=actor,
        restored_prefix_actions=(1,),
    )

    assert adapter.actions == [1, 1, 1]
    assert payload["actions_executed"] == 2
    assert payload["total_actions_executed"] == 3
    assert payload["first_level_action"] == 1
    assert payload["restored_prefix"]["actions"] == [1]
    assert payload["restored_prefix"]["primitive_action_cost"] == 1
    assert payload["observations"][0]["action_count"] == 1
    assert payload["observations"][0]["observation_index"] == 1
    assert actor.calls[0]["action_count"] == 1
    assert [row["action_count"] for row in payload["turns"]] == [1, 2]
    assert [row["total_action_count"] for row in payload["turns"]] == [2, 3]


class _SleepingSubscriptionThread(_SubscriptionThread):
    def __init__(self):
        super().__init__()
        self.sleep_calls = []
        self.active_sleep_digest = None
        self.injected_digests = []

    def queue_recall_digest(self, digest, *, consumption_receipt=None):
        assert self.active_sleep_digest is None
        self.active_sleep_digest = digest

    def decide(self, observation):
        if self.active_sleep_digest is not None:
            self.injected_digests.append(self.active_sleep_digest)
            self.active_sleep_digest = None
        return super().decide(observation)

    def consolidate(self, *, episode_turns, boundary_observation):
        self.sleep_calls.append((episode_turns, boundary_observation))
        return {
            "schema": "ztare-arc3-level-boundary-sleep-v1",
            "session_id": "session-1",
            "session_tick_count": 3,
            "after_action_count": boundary_observation["action_count"],
            "boundary_observation_sha256": boundary_observation["sha256"],
            "digest": {
                "schema": "ztare-arc3-level-boundary-sleep-digest-v1",
                "episode_summary": "learned movement semantics",
                "memories": [
                    {
                        "memory_id": "movement",
                        "claim": "action 1 changes position",
                        "guard_features": ["same-action-vocabulary"],
                        "support_action_counts": [1, 2],
                        "contradiction_action_counts": [],
                        "predicted_decision_delta": 0.7,
                        "retrieval_cost": 0.1,
                    },
                    {
                        "memory_id": "weak",
                        "claim": "an uncertain visual detail",
                        "guard_features": ["weak"],
                        "support_action_counts": [2],
                        "contradiction_action_counts": [],
                        "predicted_decision_delta": 0.1,
                        "retrieval_cost": 0.1,
                    },
                ],
                "active_uncertainties": ["new layout"],
                "next_decision_questions": ["which route is shortest?"],
            },
        }


def test_subscription_probe_runs_sparse_level_boundary_sleep() -> None:
    module = _load()
    adapter = _Adapter()
    actor = _SleepingSubscriptionThread()

    payload = module.run_subscription_probe(
        adapter=adapter,
        game_id="fake-game",
        budget=4,
        model_id="gpt-5.6-sol",
        reasoning_effort="xhigh",
        timeout_seconds=30,
        resume_session=True,
        thread=actor,
        level_boundary_sleep_top_k=1,
    )

    assert payload["actions_executed"] == 4
    assert payload["inference_tick_count"] == 5
    assert len(payload["sleep_cycles"]) == 1
    assert len(actor.sleep_calls) == 1
    sleep = payload["sleep_cycles"][0]
    assert sleep["after_action_count"] == 2
    assert len(sleep["selected_digest"]["memories"]) == 1
    assert sleep["selected_digest"]["memories"][0]["memory_id"] == "movement"
    assert len(sleep["recall"]["selections"]) == 1
    assert actor.active_sleep_digest is None
    assert len(actor.injected_digests) == 1
    assert actor.injected_digests[0]["schema"] == (
        "ztare-arc3-selected-sleep-memory-v1"
    )


def test_subscription_actor_burns_recall_after_one_decision() -> None:
    module = _load()
    prompts = []
    actor = module.CodexSubscriptionArcThread(
        model_id="gpt-5.6-sol",
        reasoning_effort="xhigh",
        instructions="choose one action",
        timeout_seconds=30,
    )

    def fake_run_json(*, prompt, output_schema):
        prompts.append(prompt)
        return (
            {"action": 0, "prediction": "one cell changes"},
            {
                "session_id": "session-1",
                "tick_count": len(prompts),
            },
        )

    actor._run_json = fake_run_json
    digest = {
        "schema": "ztare-arc3-selected-sleep-memory-v1",
        "memories": [{"claim": "a supported mechanic"}],
    }
    actor.queue_recall_digest(digest)
    observation = {
        "sha256": "observation-0",
        "action_count": 0,
    }
    first = actor.decide(observation)
    second = actor.decide(observation)

    assert "RECALLED CONSOLIDATED MEMORY" in prompts[0]
    assert "RECALLED CONSOLIDATED MEMORY" not in prompts[1]
    assert first["recall_injection"]["direct_injection_count"] == 1
    assert second["recall_injection"] is None


def test_subscription_actor_records_blind_proposal_and_offered_revision() -> None:
    module = _load()
    prompts = []
    actor = module.CodexSubscriptionArcThread(
        model_id="gpt-5.6-sol",
        reasoning_effort="xhigh",
        instructions="choose one action",
        timeout_seconds=30,
    )

    def fake_run_json(*, prompt, output_schema):
        prompts.append((prompt, output_schema))
        action = 0 if len(prompts) == 1 else 1
        return (
            {
                "action": action,
                "prediction": f"prediction-{action}",
                "plan_summary": f"plan-{action}",
                "uncertainty": "mapping",
            },
            {
                "session_id": "session-1",
                "tick_count": len(prompts),
            },
        )

    actor._run_json = fake_run_json
    observation = {
        "sha256": "observation-0",
        "action_count": 0,
    }
    pre = actor.propose(observation)
    actor.queue_recall_digest({
        "schema": "memory",
        "memories": [{"claim": "supported mechanism"}],
    })
    post = actor.revise(observation, pre_proposal=pre)

    assert pre["phase"] == "blind_pre_proposal"
    assert pre["action"] == 0
    assert pre["recall_injection"] is None
    assert post["phase"] == "post_proposal_commitment"
    assert post["action"] == 1
    assert post["recall_injection"]["direct_injection_count"] == 1
    assert post["extra_inference_tick_count"] == 1
    assert actor._turn_index == 1
    assert "BLIND PROPOSAL PHASE" in prompts[0][0]
    assert "RECALLED CONSOLIDATED MEMORY" in prompts[1][0]


def test_subscription_actor_binds_object_catalog_in_both_proposals() -> None:
    module = _load()
    prompts = []
    actor = module.CodexSubscriptionArcThread(
        model_id="gpt-5.6-sol",
        reasoning_effort="xhigh",
        instructions="choose one action",
        timeout_seconds=30,
    )
    object_ref = "object:" + ("a" * 64)
    catalog = {
        "schema": "ztare-grid-object-catalog-v1",
        "observation_sha256": "observation-0",
        "catalog_sha256": "catalog-0",
        "objects": [{
            "object_ref": object_ref,
            "bbox": [1, 2, 3, 4],
            "palette": [9, 12],
            "cell_count": 4,
        }],
    }

    def fake_run_json(*, prompt, output_schema):
        prompts.append((prompt, output_schema))
        return (
            {
                "action": 0,
                "prediction": "the selected object moves",
                "plan_summary": "move selected object",
                "uncertainty": "mapping",
                "controlled_object_ref": object_ref,
                "ordered_waypoint_refs": [],
            },
            {
                "session_id": "session-1",
                "tick_count": len(prompts),
            },
        )

    actor._run_json = fake_run_json
    observation = {
        "sha256": "observation-0",
        "action_count": 0,
    }
    pre = actor.propose(observation, object_catalog=catalog)
    actor.queue_recall_digest({"schema": "memory"})
    post = actor.revise(
        observation,
        pre_proposal=pre,
        object_catalog=catalog,
    )

    assert pre["catalog_sha256"] == "catalog-0"
    assert post["catalog_sha256"] == "catalog-0"
    assert pre["controlled_object_ref"] == object_ref
    assert post["controlled_object_ref"] == object_ref
    assert (
        prompts[0][1].name
        == "arc3_subscription_object_linked_proposal.schema.json"
    )
    assert "CONTENT-ADDRESSED OBJECT CATALOG" in prompts[0][0]
    assert "CONTENT-ADDRESSED OBJECT CATALOG" in prompts[1][0]


def test_subscription_actor_uses_catalog_scoped_handles() -> None:
    module = _load()
    prompts = []
    actor = module.CodexSubscriptionArcThread(
        model_id="gpt-5.6-sol",
        reasoning_effort="xhigh",
        instructions="choose one action",
        timeout_seconds=30,
    )
    presentation = {
        "schema": "ztare-grid-object-catalog-presentation-v1",
        "observation_sha256": "observation-0",
        "catalog_sha256": "catalog-0",
        "presentation_sha256": "presentation-0",
        "objects": [{
            "handle": "o00",
            "bbox": [1, 2, 3, 4],
            "palette": [9, 12],
            "cell_count": 4,
        }],
    }

    def fake_run_json(*, prompt, output_schema):
        prompts.append((prompt, output_schema))
        return (
            {
                "action": 0,
                "prediction": "the selected object moves",
                "plan_summary": "move selected object",
                "uncertainty": "mapping",
                "controlled_object_handle": "o00",
                "ordered_waypoint_handles": [],
            },
            {
                "session_id": "session-1",
                "tick_count": len(prompts),
            },
        )

    actor._run_json = fake_run_json
    observation = {
        "sha256": "observation-0",
        "action_count": 0,
    }
    pre = actor.propose(
        observation,
        object_catalog=presentation,
    )
    actor.queue_recall_digest({"schema": "memory"})
    post = actor.revise(
        observation,
        pre_proposal=pre,
        object_catalog=presentation,
    )

    assert pre["presentation_sha256"] == "presentation-0"
    assert post["controlled_object_handle"] == "o00"
    assert (
        prompts[0][1].name
        == "arc3_subscription_catalog_scoped_proposal.schema.json"
    )
    assert "CATALOG-SCOPED OBJECT PRESENTATION" in prompts[0][0]
    assert "exact object_ref" not in prompts[0][0]


def test_subscription_actor_withheld_revision_has_matched_second_call() -> None:
    module = _load()
    prompts = []
    actor = module.CodexSubscriptionArcThread(
        model_id="gpt-5.6-sol",
        reasoning_effort="xhigh",
        instructions="choose one action",
        timeout_seconds=30,
    )

    def fake_run_json(*, prompt, output_schema):
        prompts.append(prompt)
        return (
            {
                "action": 0,
                "prediction": "prediction",
                "plan_summary": "plan",
                "uncertainty": "mapping",
            },
            {
                "session_id": "session-1",
                "tick_count": len(prompts),
            },
        )

    actor._run_json = fake_run_json
    observation = {
        "sha256": "observation-0",
        "action_count": 0,
    }
    pre = actor.propose(observation)
    post = actor.revise(observation, pre_proposal=pre)

    assert post["recall_injection"] is None
    assert "CONTROL ASSIGNMENT" in prompts[1]
    assert "RECALLED CONSOLIDATED MEMORY" not in prompts[1]
