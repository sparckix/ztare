"""The `leanmill campaign` launcher: parses, arms the profile/model env, and calls the campaign door with the
blueprint — the mislaunch class can't recur because the internal module is never hand-invoked. Hermetic: the
door (`autoformalize_notes.main`) is stubbed, so no real run starts.

Runnable: `python tests/test_leanmill_cli.py`.
"""
import os
import json
import pathlib
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import ztare.leanmill.cli as cli  # noqa: E402


def _assert_terminal_budget_is_time_invariant(attempt, monkeypatch):
    import ztare.leanmill.exploration_budget as budget_module

    ledger_path = attempt / "budget.events.jsonl"
    rows = [json.loads(line) for line in ledger_path.read_text().splitlines()]
    assert rows[-1]["event_type"] == "wall_clock_frozen"
    assert rows[-1]["reason"] == "formalization_campaign_exit"
    frozen_ms = rows[-1]["elapsed_ms"]
    before = ledger_path.read_bytes()
    first = cli._formalization_campaign_view(attempt)["budget"]
    with monkeypatch.context() as clock:
        clock.setattr(budget_module.time, "time_ns", lambda: 10**24)
        second = cli._formalization_campaign_view(attempt)["budget"]
    assert first == second
    assert second["elapsed_ms"] == frozen_ms
    assert ledger_path.read_bytes() == before


def test_blueprint_not_found_returns_2_without_launching():
    assert cli.main(["campaign", "/no/such/blueprint.md"]) == 2


def test_profile_and_model_arm_the_env_then_call_the_door():
    import ztare.leanmill.solver.autoformalize_notes as an
    seen: dict = {}

    def fake_run(argv):
        seen["argv"] = list(argv)
        seen["env"] = {k: os.environ.get(k) for k in
                       ("ZTARE_LEANMILL_NOTES_TARGET_S", "ZTARE_CLAUDE_AGENT_MODEL",
                        "ZTARE_DEFAULT_SUBSCRIPTION_RUNTIME")}
        return 0

    orig = an.main
    an.main = fake_run
    prior_state_root = os.environ.get("ZTARE_LEANMILL_CAMPAIGN_STATE_ROOT")
    os.environ["ZTARE_LEANMILL_CAMPAIGN_STATE_ROOT"] = tempfile.mkdtemp()
    for k in ("ZTARE_LEANMILL_NOTES_TARGET_S", "ZTARE_CLAUDE_AGENT_MODEL", "ZTARE_DEFAULT_SUBSCRIPTION_RUNTIME"):
        os.environ.pop(k, None)
    try:
        bp = pathlib.Path(tempfile.mkstemp(suffix=".md")[1])
        bp.write_text("## Target\nsomething\n", encoding="utf-8")
        rc = cli.main(["campaign", str(bp), "--profile", "hard", "--model", "claude-fable-5"])
    finally:
        an.main = orig
        if prior_state_root is None:
            os.environ.pop("ZTARE_LEANMILL_CAMPAIGN_STATE_ROOT", None)
        else:
            os.environ["ZTARE_LEANMILL_CAMPAIGN_STATE_ROOT"] = prior_state_root
    assert rc == 0
    assert seen["argv"] == [str(bp)], seen
    assert seen["env"]["ZTARE_LEANMILL_NOTES_TARGET_S"] == "3600", seen["env"]        # hard profile applied
    assert seen["env"]["ZTARE_CLAUDE_AGENT_MODEL"] == "claude-fable-5", seen["env"]   # model armed
    assert seen["env"]["ZTARE_DEFAULT_SUBSCRIPTION_RUNTIME"] == "claude", seen["env"]  # → first leaf, not failover
    print("OK: not-found→2; hard profile + fable model arm the env; door called with the blueprint only")


def test_run_manifest_records_launch_authority_modes():
    import json
    import ztare.leanmill.solver.autoformalize_notes as an

    bp = pathlib.Path(tempfile.mkstemp(suffix=".md")[1])
    bp.write_text("## Target\nsomething\n", encoding="utf-8")
    scratch = "test_run_manifest_cli"
    old = {k: os.environ.get(k) for k in (
        "ZTARE_SOLVER_RUN_TAG",
        "ZTARE_LEANMILL_RUN_SCRATCH",
        "ZTARE_LEANMILL_STAGED_REUSE",
        "ZTARE_LEANMILL_BANK_ENV_RATIFY",
        "ZTARE_LEANMILL_PROPOSER_POOL",
        "ZTARE_LEANMILL_SOLVE_PROVIDERS",
        "ZTARE_DEFAULT_SUBSCRIPTION_RUNTIME",
        "ZTARE_CLAUDE_AGENT_MODEL",
        "ZTARE_LEANMILL_ROUNDTRIP_MODEL",
        "ZTARE_LEANMILL_CAMPAIGN_STATE_ROOT",
    )}
    try:
        os.environ["ZTARE_SOLVER_RUN_TAG"] = scratch
        os.environ["ZTARE_LEANMILL_RUN_SCRATCH"] = scratch
        os.environ["ZTARE_LEANMILL_STAGED_REUSE"] = "0"
        os.environ["ZTARE_LEANMILL_BANK_ENV_RATIFY"] = "1"
        os.environ["ZTARE_LEANMILL_PROPOSER_POOL"] = "0"
        os.environ["ZTARE_LEANMILL_SOLVE_PROVIDERS"] = "codex,claude"
        os.environ["ZTARE_DEFAULT_SUBSCRIPTION_RUNTIME"] = "codex"
        os.environ["ZTARE_CLAUDE_AGENT_MODEL"] = "claude-fable-5"
        os.environ["ZTARE_LEANMILL_ROUNDTRIP_MODEL"] = "gpt-5"
        os.environ["ZTARE_LEANMILL_CAMPAIGN_STATE_ROOT"] = tempfile.mkdtemp()
        path = an._write_run_manifest(bp)
        assert path is not None and path.exists(), path
        rec = json.loads(path.read_text(encoding="utf-8"))
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    assert rec["schema"] == "leanmill.run_manifest.v1"
    assert rec["run_tag"] == scratch
    assert rec["blueprint"]["sha256"]
    assert rec["blueprint"]["launch_snapshot_path"]
    assert rec["blueprint"]["launch_snapshot_sha256"] == rec["blueprint"]["sha256"]
    assert rec["blueprint"]["launch_snapshot_bytes"] == len("## Target\nsomething\n".encode("utf-8"))
    assert pathlib.Path(rec["blueprint"]["launch_snapshot_path"]).read_text(encoding="utf-8") == "## Target\nsomething\n"
    assert rec["providers"]["schema"] == "leanmill.provider_manifest.v1"
    assert rec["providers"]["solve_providers"] == ["codex", "claude"]
    assert rec["providers"]["subscription_runtime"] == "codex"
    assert rec["providers"]["claude_agent_model"] == "claude-fable-5"
    assert rec["providers"]["roundtrip_model"] == "gpt-5"
    assert rec["code_fingerprints"]["schema"] == "leanmill.code_fingerprints.v1"
    assert rec["code_fingerprints"]["files"]["src/ztare/leanmill/solver/autoformalize_notes.py"]
    assert rec["code_fingerprints"]["files"]["src/ztare/formal/repl_compile.py"]
    assert rec["authority_modes"]["staged_reuse"] == "0"
    assert rec["authority_modes"]["bank_env_ratify"] == "1"
    assert rec["authority_modes"]["proposer_pool"] == "0"
    assert rec["cache_authority_classes"]["proof_cache"] == "proof_credit"
    assert rec["cache_authority_classes"]["staged_reuse"] == "affordance"
    assert rec["cache_authority_classes"]["semantic_shelf"] == "affordance"
    print("OK: run manifest records authority modes, providers, input hash, and code fingerprints")


def test_axiompack_frontmatter_routes_through_the_shared_campaign_door(
    tmp_path, monkeypatch, capsys
):
    import ztare.leanmill.frontier_campaign_actions as actions
    import ztare.leanmill.frontier_campaign_runner as runner

    campaign = tmp_path / "axiompack.md"
    campaign.write_text(
        """---
schema: leanmill.campaign.v1
lane: axiompack
profile: smoke
source_mode: human_directed
runtime:
  transport: subscription_agent_runtime
  profile: smoke
  role_overrides: {}
---
Explore anonymous finite update theories.
""",
        encoding="utf-8",
    )
    seen = {}

    def fake_run(definition, *, output_root, typed_draft, campaign_manifest):
        seen["definition"] = definition
        seen["output_root"] = output_root
        seen["typed_draft"] = typed_draft
        seen["campaign_manifest"] = campaign_manifest
        return tmp_path / "attempt-1"

    def fake_drive(attempt, *, model, lean_root=None):
        seen["continuous"] = {
            "attempt": attempt,
            "model": model,
            "lean_root": lean_root,
        }
        return attempt

    monkeypatch.setattr(runner, "run_frontier_campaign_definition", fake_run)
    monkeypatch.setattr(runner, "drive_frontier_campaign", fake_drive)
    monkeypatch.setattr(
        actions,
        "frontier_campaign_status",
        lambda attempt: {"status": "frontier_candidates_frozen", "attempt_dir": str(attempt)},
    )
    assert cli.main([
        "campaign",
        str(campaign),
        "--output-root",
        str(tmp_path / "runs"),
        "--continuous",
    ]) == 0
    assert seen["definition"].direction == "Explore anonymous finite update theories."
    assert seen["definition"].budget.wall_clock_s == 1200
    assert seen["typed_draft"] is None
    assert seen["campaign_manifest"]["lane"] == "axiompack"
    assert seen["continuous"]["attempt"] == tmp_path / "attempt-1"
    assert '"status": "frontier_candidates_frozen"' in capsys.readouterr().out


def test_continuous_resume_enters_the_lifecycle_driver(
    tmp_path, monkeypatch, capsys
):
    import ztare.leanmill.frontier_campaign_actions as actions
    import ztare.leanmill.frontier_campaign_runner as runner

    seen = {}

    def fake_drive(
        attempt, *, model, lean_root=None, workbench_authority_ref=""
    ):
        seen.update(
            attempt=attempt,
            model=model,
            lean_root=lean_root,
            workbench_authority_ref=workbench_authority_ref,
        )
        return pathlib.Path(attempt)

    monkeypatch.setattr(runner, "drive_frontier_campaign", fake_drive)
    monkeypatch.setattr(
        runner,
        "resume_frontier_campaign_navigation",
        lambda _attempt: pytest.fail("continuous resume used the one-step door"),
    )
    monkeypatch.setattr(
        actions,
        "frontier_campaign_status",
        lambda attempt: {"status": "campaign_complete", "attempt_dir": str(attempt)},
    )

    assert cli.main([
        "resume",
        str(tmp_path / "attempt-1"),
        "--continuous",
        "--model",
        "campaign-model",
        "--lean-root",
        str(tmp_path / "lean"),
    ]) == 0
    assert seen == {
        "attempt": str(tmp_path / "attempt-1"),
        "model": "campaign-model",
        "lean_root": str(tmp_path / "lean"),
        "workbench_authority_ref": "",
    }
    assert '"status": "campaign_complete"' in capsys.readouterr().out


def test_formalization_frontmatter_uses_shared_budget_without_changing_solver_door(
    tmp_path, monkeypatch, capsys
):
    import ztare.leanmill.solver.autoformalize_notes as notes

    campaign = tmp_path / "formalize.md"
    campaign.write_text(
        """---
schema: leanmill.campaign.v1
lane: formalize
profile: smoke
budget:
  provider_calls: 2
  agent_turns: 2
  metered_api_usd: "0"
runtime:
  transport: subscription_agent_runtime
  profile: smoke
  defaults: {runtime: codex}
  role_overrides: {}
---
## Target
Prove the target.
""",
        encoding="utf-8",
    )
    seen = {}

    def fake_run(argv):
        seen["argv"] = argv
        seen["api_fallback"] = os.environ.get(
            "ZTARE_LEANMILL_FORMALIZE_API_FALLBACK"
        )
        return 0

    monkeypatch.setattr(notes, "main", fake_run)
    monkeypatch.setenv("ZTARE_LEANMILL_CAMPAIGN_STATE_ROOT", str(tmp_path / "state"))
    monkeypatch.setenv("ZTARE_SOLVER_RUN_TAG", "caller-family-tag")
    assert cli.main(["campaign", str(campaign)]) == 0
    assert seen == {"argv": [str(campaign)], "api_fallback": "0"}
    attempts = list((tmp_path / "state").iterdir())
    assert len(attempts) == 1
    budget = json.loads((attempts[0] / "budget.json").read_text(encoding="utf-8"))
    assert budget["allocation_policy"] == "roll_forward_protected_future"
    assert budget["hard_caps"]["provider_calls"] == 2
    completion = json.loads((attempts[0] / "completion.json").read_text(encoding="utf-8"))
    assert completion["solver_run_tag"] == attempts[0].name
    assert completion["requested_run_tag"] == "caller-family-tag"
    assert (attempts[0] / "diagnostics.json").is_file()
    assert (attempts[0] / "phase_timing.json").is_file()
    assert (attempts[0] / "theory_input.json").is_file()
    assert (attempts[0] / "theory_result.json").is_file()
    _assert_terminal_budget_is_time_invariant(attempts[0], monkeypatch)
    assert '"returncode": 0' in capsys.readouterr().out


def test_formalization_budget_freezes_when_runner_raises(
    tmp_path, monkeypatch
):
    import ztare.leanmill.solver.autoformalize_notes as notes

    campaign = tmp_path / "formalize-exception.md"
    campaign.write_text(
        """---
schema: leanmill.campaign.v1
lane: formalize
profile: smoke
budget:
  provider_calls: 2
  agent_turns: 2
  metered_api_usd: "0"
runtime:
  transport: subscription_agent_runtime
  profile: smoke
  defaults: {runtime: codex}
  role_overrides: {}
---
## Target
Prove the target.
""",
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "ZTARE_LEANMILL_CAMPAIGN_STATE_ROOT", str(tmp_path / "state")
    )
    monkeypatch.setattr(
        notes,
        "main",
        lambda _argv: (_ for _ in ()).throw(RuntimeError("runner failed")),
    )

    with pytest.raises(RuntimeError, match="runner failed"):
        cli.main(["campaign", str(campaign)])

    attempt = next((tmp_path / "state").iterdir())
    assert json.loads((attempt / "completion.json").read_text())["status"] == "failed"
    _assert_terminal_budget_is_time_invariant(attempt, monkeypatch)


def test_legacy_completed_formalization_status_does_not_rebill_idle_time(
    tmp_path, monkeypatch
):
    import ztare.leanmill.exploration_budget as budget_module
    from ztare.leanmill.exploration_budget import (
        ExplorationBudgetLedger,
        budget_preset,
    )

    attempt = tmp_path / "formalize-legacy"
    attempt.mkdir()
    budget = budget_preset("smoke_20m")
    (attempt / "campaign_manifest.json").write_text(
        json.dumps({"lane": "formalize", "campaign_id": "legacy"})
    )
    (attempt / "budget.json").write_text(json.dumps(budget.to_json()))
    ExplorationBudgetLedger(
        attempt / "budget.events.jsonl",
        budget,
        attempt_id=attempt.name,
        clock_ms=lambda: 1_000,
    )
    completion_path = attempt / "completion.json"
    completion_path.write_text(json.dumps({"status": "completed", "returncode": 0}))
    os.utime(completion_path, ns=(1_558_000_000, 1_558_000_000))
    before = (attempt / "budget.events.jsonl").read_bytes()

    with monkeypatch.context() as clock:
        clock.setattr(budget_module.time, "time_ns", lambda: 1_800_000_000_000)
        first = cli._formalization_campaign_view(attempt)["budget"]
        clock.setattr(budget_module.time, "time_ns", lambda: 3_600_000_000_000)
        second = cli._formalization_campaign_view(attempt)["budget"]

    assert first == second
    assert second["elapsed_ms"] == 558
    assert second["soft_stop_reason"] is None
    assert (attempt / "budget.events.jsonl").read_bytes() == before
    (attempt / "budget.events.jsonl").unlink()
    assert cli._formalization_campaign_view(attempt)["budget"]["elapsed_ms"] is None
    assert not (attempt / "budget.events.jsonl").exists()


def test_formalization_theory_head_lease_blocks_competing_attempt(
    tmp_path, monkeypatch, capsys
):
    import hashlib
    import ztare.leanmill.solver.autoformalize_notes as notes
    from ztare.leanmill import work_queue

    campaign = tmp_path / "formalize-theory.md"
    campaign.write_text(
        """---
schema: leanmill.campaign.v1
lane: formalize
profile: smoke
budget:
  provider_calls: 2
  agent_turns: 2
  metered_api_usd: "0"
runtime:
  transport: subscription_agent_runtime
  profile: smoke
  defaults: {runtime: codex}
  role_overrides: {}
---
## Target
Extend the theory.
## Theory file
T.lean
""",
        encoding="utf-8",
    )
    theory = tmp_path / "T.lean"
    theory.write_text("import Mathlib\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_declared_theory_path", lambda _notes: (theory.resolve(), "T.lean"))
    queue_db = tmp_path / "queue.sqlite"
    monkeypatch.setenv("ZTARE_LEANMILL_QUEUE_DB", str(queue_db))
    state_root = tmp_path / "state"
    monkeypatch.setenv("ZTARE_LEANMILL_CAMPAIGN_STATE_ROOT", str(state_root))

    work_id = "leanmill_theory_head__" + hashlib.sha256(
        str(theory.resolve()).encode("utf-8")
    ).hexdigest()[:24]
    cx = work_queue.connect(str(queue_db))
    try:
        work_queue.enqueue(
            cx,
            kind="leanmill_theory_head",
            priority=0,
            max_attempts=100,
            payload={"work_id": work_id, "theory_path": str(theory.resolve())},
        )
        assert work_queue.claim_specific(
            cx, work_id=work_id, worker_id="other-owner", lease_s=60
        )
    finally:
        cx.close()

    called = []
    original = notes.main
    notes.main = lambda argv: called.append(argv) or 0
    try:
        assert cli.main(["campaign", str(campaign)]) == 75
    finally:
        notes.main = original

    attempt = next(state_root.iterdir())
    completion = json.loads((attempt / "completion.json").read_text())
    assert completion["status"] == "blocked_by_theory_owner"
    assert completion["returncode"] == 75
    assert completion["usage"]["provider_calls"] == 0
    assert called == []
    _assert_terminal_budget_is_time_invariant(attempt, monkeypatch)
    capsys.readouterr()

    cx = work_queue.connect(str(queue_db))
    try:
        assert work_queue.finish_specific(
            cx, work_id=work_id, worker_id="other-owner", done=False
        )
    finally:
        cx.close()


def test_axiompack_preflight_replays_frozen_context_without_dispatch(capsys):
    campaign = pathlib.Path(__file__).resolve().parents[1] / (
        "research_areas/pre_registrations/"
        "axiompack_gp251_smoke_20260710/campaign.md"
    )

    assert cli.main(["preflight", str(campaign)]) == 0

    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "passed"
    assert receipt["provider_calls"] == 0
    assert receipt["runtime_resolution"]["navigator"] == {
        "runtime": "codex",
        "model": "gpt-5.5",
        "reasoning_effort": "low",
        "native_reasoning_effort": "low",
        "timeout_seconds": 1200,
    }
    assert receipt["formula_count"] == 410
    assert receipt["model_or_observation_count"] == 3340
    assert receipt["object_contrast_admissible"] is True
    assert receipt["observational_partition"] == {
        "class_count": 421,
        "largest_class_size": 1178,
        "non_singleton_class_count": 187,
    }
    assert receipt["context_hash"] == (
        "d22e5a390f117cbcbd4f1972dfb93d88b0e10db2bb5eaef1cf7b59c1f3e87206"
    )


def test_axiompack_preflight_returns_typed_incomplete_context(
    capsys, monkeypatch
):
    campaign = pathlib.Path(__file__).resolve().parents[1] / (
        "research_areas/pre_registrations/"
        "axiompack_gp251_smoke_20260710/campaign.md"
    )
    import ztare.leanmill.explore_axiom_space as inlet

    class IncompleteContext(ValueError):
        def failure_receipt(self):
            return {
                "schema": "leanmill.incomplete_finite_model_universe.v1",
                "status": "incomplete",
                "enumeration_receipt": {
                    "status": "unknown",
                    "canonical_model_count": 17,
                },
            }

    def fail_context(*_args, **_kwargs):
        raise IncompleteContext("census timed out")

    monkeypatch.setattr(inlet, "_context_from_snapshot", fail_context)
    monkeypatch.setattr(inlet, "_context_from_blueprint", fail_context)

    assert cli.main(["preflight", str(campaign)]) == 2

    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "incomplete_context"
    assert receipt["provider_calls"] == 0
    assert receipt["context_failure"]["enumeration_receipt"] == {
        "status": "unknown",
        "canonical_model_count": 17,
    }
    assert receipt["receipt_sha256"]


if __name__ == "__main__":
    test_blueprint_not_found_returns_2_without_launching()
    test_profile_and_model_arm_the_env_then_call_the_door()
    test_run_manifest_records_launch_authority_modes()
