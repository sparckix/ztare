from __future__ import annotations

from copy import deepcopy

import pytest

from ztare.leanmill.ratification_policy import (
    TARGET_GOVERNANCE_AUTHORITIES,
    TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256,
)
from ztare.leanmill.solver.closed_artifact import finalize_solver_validation
from ztare.leanmill.solver.deterministic import NativeHammerProbeResult

from ztare.leanmill.control_plane import StatementId, Verdict, VerdictKind
from ztare.leanmill.target_curriculum import (
    LEGACY_TARGET_CONJECTURE_WAVE_SCHEMA,
    TARGET_CONJECTURE_WAVE_SCHEMA,
    TARGET_FORMAL_CONTEXT_OWNER,
    build_target_conjecture_admission,
    build_target_statement_revision_feedback,
    preflight_target_conjecture_wave,
    revise_target_conjecture_wave,
)
from ztare.leanmill.target_curriculum_adjudication import (
    SOURCE_ADJACENT_SOLVER_OWNER,
    build_source_adjacent_candidate_queue,
    continue_target_conjecture_admission,
    provider_free_native_adjudicate,
)
from ztare.leanmill.theory_ir import content_hash


def _wave(*, schema: str = TARGET_CONJECTURE_WAVE_SCHEMA) -> dict:
    candidate_core = {
        "title": "A source-adjacent extension",
        "formal_status": "lean_candidate",
        "candidate_family": "hypothesis_minimization",
        "mathematical_statement": "A proposition implies itself.",
        "lean_signature": "(P : Prop) : P → P",
        "required_imports": ["ZtareProofs.AxiomPackOrbitAction"],
        "dependencies": ["Demo.seed"],
        "target_edge": "A small executable edge.",
        "expected_direction": "sufficient",
        "falsification_plan": "Ask the existing kernel solver for proof or negation.",
        "recurrence_risk": "This fixture is intentionally elementary.",
        "scope_limits": "Only the declared proposition.",
        "capability_request": "",
        "source_card_id": "result-card:one",
        "source_target_identity": "Demo.seed",
        "normalized_lean_signature": "(P : Prop) : P → P",
        "recurrence_status": "not_exact_card_statement",
        "candidate_id": "target-conjecture:fixture",
    }
    if schema == TARGET_CONJECTURE_WAVE_SCHEMA:
        candidate_core["formal_context"] = {
            "open_namespaces": ["AxiomPackOrbitAction"],
            "enclosing_namespace": "",
        }
    candidate = {
        **candidate_core,
        "candidate_sha256": content_hash(candidate_core),
        "also_proposed_from": [],
    }
    core = {
        "schema": schema,
        "deck_sha256": "d" * 64,
        "objective_sha256": "o" * 64,
        "card_count": 1,
        "candidate_count": 1,
        "candidates": [candidate],
        "call_receipts": [],
        "authority": "agent_proposals_pending_independent_guide_and_verification",
    }
    if schema == TARGET_CONJECTURE_WAVE_SCHEMA:
        core.update({
            "revision_epoch": 0,
            "predecessor_wave_sha256": "",
            "revision_feedback_sha256": "",
            "abandoned_predecessor_candidate_ids": [],
            "formal_context_owner": TARGET_FORMAL_CONTEXT_OWNER,
        })
    return {**core, "wave_sha256": content_hash(core)}


def _guide(candidate_id: str) -> dict:
    ranking = {
        "question_id": candidate_id,
        "rank": 1,
        "information_yield": "It checks the route.",
        "novelty_headroom": "Fixture only.",
        "harness_readiness": "Executable.",
        "fatal_confounder": "None in this fixture.",
        "discriminating_test": "Run the frozen solver task.",
        "kill_condition": "The statement does not elaborate.",
        "minimum_artifact": "A typed solver verdict.",
        "apparatus_vs_scarcity": "The route distinguishes them.",
    }
    core = {
        "schema": "leanmill.eigenquestion_review.v1",
        "authority": "advisory_only",
        "runtime": "codex",
        "model": "fixture",
        "prompt_sha256": "p" * 64,
        "recommended_question_id": candidate_id,
        "review": {
            "ranked_questions": [ranking],
            "portfolio_sequence": [candidate_id],
            "portfolio_rationale": "Run the only candidate.",
            "scope_notes": "Fixture.",
        },
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _admission(wave: dict, elaboration: dict, guide: dict) -> dict:
    return build_target_conjecture_admission(
        wave,
        elaboration,
        run_tag="fixture-run",
        deck_sha256=wave["deck_sha256"],
        replay_receipt_sha256="r" * 64,
        guide_receipt=guide,
        selected_candidate_ids=[wave["candidates"][0]["candidate_id"]],
    )


def _closed_result() -> dict:
    governance = {
        "governance_kernel": {
            "available": True,
            "passed": True,
            "policy_profile": "target_ratification",
            "required_authorities": sorted(TARGET_GOVERNANCE_AUTHORITIES),
            "authority_disposition": {
                authority: "passed"
                for authority in TARGET_GOVERNANCE_AUTHORITIES
            },
            "authority_roster_sha256": (
                TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256
            ),
        },
        "statement_integrity": {"ok": True},
        "integrity_unverified": False,
    }
    validation = finalize_solver_validation({
        "credit_ready_at_solver_layer": True,
        "positive_axiom_receipt_required": True,
        "discriminating_mnc_required": True,
        "receipts": {
            "kernel_compile_receipt": {"available": True, "passed": True},
            "matched_negative_control_receipt": {
                "available": True,
                "passed": True,
                "admitted_under_policy": True,
            },
            "axiom_allowlist_receipt": {"available": True, "passed": True},
        },
    }, governance)
    return {
        "results": [{
            "outcome": "closed",
            "proof_text": "by intro h; exact h",
            "contract_validation": validation,
        }],
        "governance": governance,
        "closure_certificate": "closure:fixture",
        "closure_lean": "closures/fixture.lean",
    }


def test_source_adjacent_first_fire_resumes_through_existing_solver(tmp_path) -> None:
    wave = _wave()
    elaboration = preflight_target_conjecture_wave(
        wave, lean_root=tmp_path, compile_fn=lambda _source, _root: True
    )
    guide = _guide(wave["candidates"][0]["candidate_id"])
    admission = _admission(wave, elaboration, guide)
    calls: list[dict] = []

    def unavailable(target_name, source_text, goal, **kwargs):
        calls.append({"target": target_name, "source": source_text, "goal": goal, **kwargs})
        return {"results": [{"outcome": "exact_gap"}]}

    first = continue_target_conjecture_admission(
        wave,
        elaboration,
        guide,
        admission,
        lean_root=tmp_path,
        artifact_dir=tmp_path / "run",
        solve_fn=unavailable,
    )
    assert first["status"] == "resumable"
    assert first["resumable_candidate_ids"] == [
        wave["candidates"][0]["candidate_id"]
    ]
    assert calls[0]["goal"] == ""
    assert calls[0]["require_positive_axiom_receipt"] is True
    assert "open AxiomPackOrbitAction" in calls[0]["source"]
    assert calls[0]["target"].startswith("targetCurriculumCandidate_")

    second = continue_target_conjecture_admission(
        wave,
        elaboration,
        guide,
        admission,
        lean_root=tmp_path,
        artifact_dir=tmp_path / "run",
        solve_fn=lambda *_args, **_kwargs: _closed_result(),
        prior_continuation=first,
    )
    assert second["status"] == "adjudicated"
    assert second["proved_candidate_ids"] == [
        wave["candidates"][0]["candidate_id"]
    ]
    assert [row["attempt_index"] for row in second["attempts"]] == [1, 2]
    assert second["attempts"][1]["previous_attempt_sha256"] == (
        second["attempts"][0]["attempt_sha256"]
    )
    assert second["attempts"][1]["solver_owner"] == SOURCE_ADJACENT_SOLVER_OWNER


def test_bound_kernel_refutation_is_typed(tmp_path) -> None:
    wave = _wave()
    elaboration = preflight_target_conjecture_wave(
        wave, lean_root=tmp_path, compile_fn=lambda *_args: True
    )
    guide = _guide(wave["candidates"][0]["candidate_id"])
    admission = _admission(wave, elaboration, guide)

    def refute(target_name, source_text, _goal, **_kwargs):
        block = "import Mathlib\ntheorem candidate_not : True := by trivial\n"
        verdict = Verdict(
            kind=VerdictKind.REFUTED,
            statement_id=StatementId.from_parts(
                target_name=target_name,
                source_text=source_text,
                closed_prop=source_text,
            ),
            provenance="fixture_kernel",
            artifacts={
                "lean_source": block,
                "lean_source_sha256": __import__("hashlib").sha256(
                    block.encode()
                ).hexdigest(),
            },
        )
        return {
            "results": [{"outcome": "falsified"}],
            "statement_false_verified": True,
            "control_verdict": verdict.to_json(),
        }

    result = continue_target_conjecture_admission(
        wave,
        elaboration,
        guide,
        admission,
        lean_root=tmp_path,
        solve_fn=refute,
    )
    assert result["refuted_candidate_ids"] == [
        wave["candidates"][0]["candidate_id"]
    ]
    assert result["attempts"][0]["reason_code"] == "kernel_verified_negation"


def test_rejected_statement_cannot_enter_source_adjacent_queue(tmp_path) -> None:
    wave = _wave()
    elaboration = preflight_target_conjecture_wave(
        wave, lean_root=tmp_path, compile_fn=lambda *_args: False
    )
    guide = _guide(wave["candidates"][0]["candidate_id"])
    with pytest.raises(ValueError, match="unreviewed or unelaborated"):
        _admission(wave, elaboration, guide)

    no_selection = build_target_conjecture_admission(
        wave,
        elaboration,
        run_tag="fixture-run",
        deck_sha256=wave["deck_sha256"],
        replay_receipt_sha256="r" * 64,
        guide_receipt=guide,
        selected_candidate_ids=[],
    )
    queue = build_source_adjacent_candidate_queue(
        wave, elaboration, guide, no_selection
    )
    assert queue["tasks"] == []
    assert queue["rejected_candidate_ids"] == [
        wave["candidates"][0]["candidate_id"]
    ]
    assert queue["formal_task_firewall"] == "preserved_mathlib_only"
    assert no_selection["next_authority"] == "target_conjecture_author_revision"
    continuation = continue_target_conjecture_admission(
        wave,
        elaboration,
        guide,
        no_selection,
        lean_root=tmp_path,
        solve_fn=lambda *_args, **_kwargs: pytest.fail(
            "a rejected statement reached the solver"
        ),
    )
    assert continuation["status"] == "revision_required"
    assert continuation["next_authority"] == (
        "target_conjecture_author_revision"
    )


def test_legacy_rejection_feedback_mints_new_context_owned_epoch(tmp_path) -> None:
    legacy = _wave(schema=LEGACY_TARGET_CONJECTURE_WAVE_SCHEMA)
    original = deepcopy(legacy)
    elaboration = preflight_target_conjecture_wave(
        legacy, lean_root=tmp_path, compile_fn=lambda *_args: False
    )
    feedback = build_target_statement_revision_feedback(
        legacy,
        elaboration,
        lean_root=tmp_path,
        successor_revision_epoch=1,
        diagnose_fn=lambda *_args: "error: unknown identifier 'orbitActionOp'",
    )
    assert feedback["candidate_feedback"][0]["diagnostic_category"] == (
        "lean_name_resolution_error"
    )
    successor = revise_target_conjecture_wave(
        legacy,
        elaboration,
        feedback,
        {
            "revisions": [{
                "predecessor_candidate_id": legacy["candidates"][0]["candidate_id"],
                "lean_signature": "(P : Prop) : P → P",
                "required_imports": ["ZtareProofs.AxiomPackOrbitAction"],
                "formal_context": {
                    "open_namespaces": ["AxiomPackOrbitAction"],
                    "enclosing_namespace": "",
                },
                "revision_summary": "Declared the source namespace explicitly.",
            }],
            "abandoned_candidate_ids": [],
        },
        call_receipt={"call_sha256": "c" * 64},
    )
    assert legacy == original
    assert successor["schema"] == TARGET_CONJECTURE_WAVE_SCHEMA
    assert successor["predecessor_wave_sha256"] == legacy["wave_sha256"]
    assert successor["candidates"][0]["candidate_id"] != (
        legacy["candidates"][0]["candidate_id"]
    )
    seen: list[str] = []
    successor_elaboration = preflight_target_conjecture_wave(
        successor,
        lean_root=tmp_path,
        compile_fn=lambda source, _root: seen.append(source) or True,
    )
    assert successor_elaboration["guide_eligible_candidate_ids"]
    assert "open AxiomPackOrbitAction" in seen[0]


def test_budget_refusal_precedes_injected_solver_dispatch(tmp_path) -> None:
    wave = _wave()
    elaboration = preflight_target_conjecture_wave(
        wave, lean_root=tmp_path, compile_fn=lambda *_args: True
    )
    guide = _guide(wave["candidates"][0]["candidate_id"])
    admission = _admission(wave, elaboration, guide)
    dispatched = []

    result = continue_target_conjecture_admission(
        wave,
        elaboration,
        guide,
        admission,
        lean_root=tmp_path,
        solve_fn=lambda *_args, **_kwargs: dispatched.append(True),
        provider_mode="delegated_solver",
        provider_call_budget_delegated=False,
    )

    assert dispatched == []
    assert result["attempts"][0]["reason_code"] == (
        "solver_unavailable:CumulativeProviderBudgetNotDelegated"
    )


def test_provider_free_native_miss_never_enters_ratification(
    tmp_path, monkeypatch
) -> None:
    from ztare.leanmill.solver import solver_core

    monkeypatch.setattr(
        solver_core,
        "_native_hammer_probe",
        lambda *_args, **_kwargs: NativeHammerProbeResult(
            "exhausted", transcript="native miss"
        ),
    )
    monkeypatch.setattr(
        solver_core,
        "solve_adhoc",
        lambda *_args, **_kwargs: pytest.fail(
            "native miss entered the generic solver"
        ),
    )

    raw = provider_free_native_adjudicate(
        "Demo.target",
        "import Mathlib\ntheorem target : True := by sorry\n",
        "",
        timeout_s=1,
        substrate=tmp_path,
    )

    assert raw["provider_calls_charged"] == 0
    assert raw["source_adjacent_unavailable_reason"] == (
        "provider_free_native_exhausted"
    )
    assert raw["results"][0]["admissible_negative"] is True


def test_no_delegated_budget_still_enters_provider_free_native_mode(
    tmp_path, monkeypatch
) -> None:
    import ztare.leanmill.target_curriculum_adjudication as adjudication

    wave = _wave()
    elaboration = preflight_target_conjecture_wave(
        wave, lean_root=tmp_path, compile_fn=lambda *_args: True
    )
    guide = _guide(wave["candidates"][0]["candidate_id"])
    admission = _admission(wave, elaboration, guide)
    native_calls = []

    def native(*_args, **_kwargs):
        native_calls.append(True)
        return {
            "results": [{"outcome": "provider_free_native_miss"}],
            "source_adjacent_unavailable_reason": (
                "provider_free_native_no_closure"
            ),
            "provider_calls_charged": 0,
        }

    monkeypatch.setattr(adjudication, "provider_free_native_adjudicate", native)
    result = continue_target_conjecture_admission(
        wave,
        elaboration,
        guide,
        admission,
        lean_root=tmp_path,
        provider_mode="provider_free_native",
        provider_call_budget_delegated=False,
    )

    assert native_calls == [True]
    assert result["attempts"][0]["reason_code"] == (
        "provider_free_native_no_closure"
    )


def test_provider_free_native_hit_uses_preverified_ratification_only(
    tmp_path, monkeypatch
) -> None:
    from ztare.leanmill.solver import solver_core

    seen = {}
    monkeypatch.setattr(
        solver_core,
        "_native_hammer_probe",
        lambda *_args, **_kwargs: NativeHammerProbeResult(
            "closed", "by trivial", "native close"
        ),
    )

    def ratify(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return _closed_result()

    monkeypatch.setattr(solver_core, "solve_adhoc", ratify)
    raw = provider_free_native_adjudicate(
        "Demo.target",
        "import Mathlib\ntheorem target : True := by sorry\n",
        "",
        timeout_s=1,
        substrate=tmp_path,
    )

    assert raw["provider_calls_charged"] == 0
    assert seen["kwargs"]["preverified_only"] is True
    assert seen["kwargs"]["preverified_proof"] == "by trivial"
    assert seen["kwargs"]["preverified_provider"] == "native_hammer"
    assert "provider" not in seen["kwargs"]
