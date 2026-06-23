import argparse
import json
from pathlib import Path

from ztare.synthesis import synthesize as synth
from ztare.synthesis.synthesize import (
    AUTORESEARCH_REVIEW_CONTEXT_FILENAME,
    build_artifact_input_binding,
    build_report_support_contract,
    cached_ledger_matches_context,
    compact_autoresearch_trace_for_synthesis,
    derive_project_domain,
    load_autoresearch_review_context_for_context,
    qa_artifact,
    qa_blocking_issues,
    qa_artifact_with_repair,
    qa_passes_for_report_write,
    run_support_contract_only,
    synthesis_paths,
    write_report_support_contract,
)


def test_derive_project_domain_prefers_explicit_metadata_over_slug(tmp_path: Path) -> None:
    project_dir = tmp_path / "startup_named_policy_review"
    project_dir.mkdir()
    (project_dir / "project_metadata.json").write_text(
        json.dumps({"project_domain": "Organizational Diagnosis"}),
        encoding="utf-8",
    )

    assert derive_project_domain(project_dir.name, project_dir) == "organizational_diagnosis"


def test_derive_project_domain_reads_project_charter_domain(tmp_path: Path) -> None:
    project_dir = tmp_path / "ambiguous_project"
    project_dir.mkdir()
    (project_dir / "project_charter.md").write_text(
        "# Project Charter\n\n**Domain:** Technical Due Diligence\n",
        encoding="utf-8",
    )

    assert derive_project_domain(project_dir.name, project_dir) == "technical_due_diligence"


def test_autoresearch_review_context_compacts_evidence_readiness() -> None:
    context = compact_autoresearch_trace_for_synthesis(
        {
            "schema": "ztare-autoresearch-trace-v1",
            "project": "ops_demo",
            "readiness_canonical": "blocked_on_project_surfaces",
            "status": "partial_trace",
            "missing": ["evidence_replay_stale"],
            "blocking_missing": ["evidence_replay_stale"],
            "kernel_entry": {
                "status": "blocked",
                "can_enter_kernel": False,
                "blockers": [{"id": "evidence_replay_stale"}],
            },
            "recent_loop": {},
            "surfaces": {
                "evidence_compile_freshness": {"status": "fresh"},
                "evidence_output_binding": {"status": "fresh"},
                "evidence_replay": {
                    "required": True,
                    "status": "stale_or_invalid",
                },
                "claim_support": {
                    "status": "has_demotions",
                    "claim_count": 3,
                    "weak_or_unsourced_count": 1,
                    "source_context_blocked_count": 0,
                    "status_counts": {
                        "direct_source_support": 2,
                        "unsupported_no_sources": 1,
                    },
                    "source_context_status_counts": {"verified": 2},
                },
                "source_index_freshness": {"status": "fresh"},
                "source_preflight_ok": True,
                "launch_preflight_ok": True,
                "eval_history_rows": 2,
            },
            "graph_rd_actions": [],
            "health_evidence_gaps": [],
            "recovery_actions": [],
            "next_commands": [
                "ztare project evidence-replay --project ops_demo --json",
            ],
        }
    )

    assert context["surfaces"]["evidence_replay"] == {
        "required": True,
        "status": "stale_or_invalid",
    }
    assert context["surfaces"]["evidence_readiness"] == {
        "status": "blocked",
        "source_index_status": "fresh",
        "compile_provenance_status": "fresh",
        "output_binding_status": "fresh",
        "replay_required": True,
        "replay_status": "stale_or_invalid",
        "replay_ok": False,
    }
    assert context["surfaces"]["evidence_output_binding"] == {"status": "fresh"}
    assert context["surfaces"]["claim_support"]["weak_or_unsourced_count"] == 1
    assert context["surfaces"]["claim_support"]["source_context_blocked_count"] == 0
    assert context["blocking_missing"] == ["evidence_replay_stale"]
    assert context["next_actions"] == [
        {
            "label": "Inspect or repair the next trace surface.",
            "command": "ztare project evidence-replay --project ops_demo --json",
        }
    ]


def test_report_support_contract_preserves_trace_caveats_and_actions(tmp_path: Path) -> None:
    project_dir = tmp_path / "ops_demo"
    synth_dir = project_dir / "synthesis"
    synth_dir.mkdir(parents=True)
    review_context_path = synth_dir / AUTORESEARCH_REVIEW_CONTEXT_FILENAME
    review_context_path.write_text(
        json.dumps(
            {
                "schema": "ztare-synthesis-autoresearch-review-context-v1",
                "project": "ops_demo",
                "readiness": "ready_for_in_loop_candidate",
                "status": "complete_trace",
                "kernel_entry": {
                    "status": "ready",
                    "can_enter_kernel": True,
                    "blockers": [],
                },
                "recent_loop": {
                    "available": True,
                    "latest_provider_failure_observed": True,
                    "latest_run_exit_reason": "budget_exhausted",
                },
                "surfaces": {
                    "source_preflight_ok": True,
                    "launch_preflight_ok": False,
                    "launch_preflight_errors": ["missing launch receipt"],
                    "eval_history_rows": 4,
                    "evidence_compile_freshness": {"status": "fresh"},
                    "evidence_output_binding": {"status": "fresh"},
                    "evidence_replay": {
                        "required": True,
                        "status": "stale_or_invalid",
                    },
                    "claim_support": {
                        "status": "has_demotions",
                        "claim_count": 3,
                        "weak_or_unsourced_count": 1,
                        "source_context_blocked_count": 0,
                        "status_counts": {
                            "direct_source_support": 2,
                            "unsupported_no_sources": 1,
                        },
                        "source_context_status_counts": {"verified": 2},
                        "rows": [
                            {
                                "claim_id": "c1",
                                "claim": "The batching flag is source-supported.",
                                "field": "candidate_claims_to_test",
                                "support_status": "direct_source_support",
                                "source_ids": ["S001"],
                                "source_paths": ["change.md"],
                                "missing_source_ids": [],
                                "reason": "claim is bound to one source row",
                            },
                            {
                                "claim_id": "c2",
                                "claim": "The root cause is proven.",
                                "field": "candidate_claims_to_test",
                                "support_status": "unsupported_no_sources",
                                "source_ids": [],
                                "source_paths": [],
                                "missing_source_ids": ["S999"],
                                "reason": "missing source",
                            },
                        ],
                    },
                },
                "graph_rd_actions": [
                    {
                        "action_type": "in_loop_focus_receipt",
                        "targets": ["cache invalidation claim"],
                    }
                ],
                "health_evidence_gaps": [
                    {
                        "gap_id": "gap-1",
                        "recovery_kind": "local_verification",
                    }
                ],
                "next_actions": [
                    {
                        "label": "Run the model-free launch preflight.",
                        "command": "ztare autoresearch run --preflight-only",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    context = {
        "project_name": "ops_demo",
        "project_dir": str(project_dir),
        "renderer_type": "research_note",
        "artifact_paths": [str(review_context_path)],
    }
    ledger = {
        "_meta": {
            "artifact_paths": context["artifact_paths"],
            "artifact_input_digest": build_artifact_input_binding(
                context["artifact_paths"]
            )["digest"],
        },
        "supported_hypotheses": [
            {
                "claim": "The batching flag is a plausible mechanism.",
                "confidence": "medium",
                "evidence_summary": "Two source-backed incidents point to it.",
            }
        ],
        "unsupported_narratives": [
            {
                "claim": "The root cause is proven.",
                "confidence": "high",
                "why_unsupported": "The reproduction has not run yet.",
            }
        ],
        "overclaim_boundary": ["Do not state final root cause."],
        "review_status": {
            "readiness": "ready",
            "blockers": ["needs reproduction"],
            "runtime_risks": [
                "Validation compute budget exhausted on recent runs.",
                "prior provider timeout",
            ],
            "next_actions": ["run bounded reproduction"],
        },
        "confirmation_status": {
            "label": "directionally_supported",
            "why": "Evidence is convergent but not decisive.",
        },
    }

    loaded_trace = load_autoresearch_review_context_for_context(context)
    contract = build_report_support_contract(
        ledger=ledger,
        brief={},
        context=context,
        autoresearch_review_context=loaded_trace,
    )

    assert contract["schema"] == "ztare-synthesis-report-support-contract-v1"
    assert contract["ok"] is False
    assert contract["status"] == "blocked"
    assert contract["status_reasons"] == [
        "report_blockers_present",
        "evidence_readiness_blocked",
        "runtime_risks_present",
        "weak_or_unsourced_claim_support_present",
    ]
    assert contract["trace_status"] == "complete_trace"
    assert contract["trace_readiness"] == "ready_for_in_loop_candidate"
    assert contract["evidence_readiness_status"] == "blocked"
    assert contract["source_claim_support"]["claim_count"] == 3
    assert contract["synthesis_input_binding"]["status"] == "fresh"
    assert contract["source_claim_support"]["weak_or_unsourced_count"] == 1
    assert contract["source_claim_support"]["status_counts"] == {
        "direct_source_support": 2,
        "unsupported_no_sources": 1,
    }
    assert contract["source_claim_support"]["sample_rows"][0]["claim_id"] == "c1"
    assert contract["source_claim_support"]["problem_rows"][0]["claim_id"] == "c2"
    assert contract["supported_claims"][0]["claim"] == "The batching flag is a plausible mechanism."
    assert any(row["claim"] == "The root cause is proven." for row in contract["unsupported_or_unresolved"])
    assert "needs reproduction" in contract["blockers"]
    assert {
        "id": "evidence_readiness",
        "surface": "evidence_replay",
        "status": "stale_or_invalid",
        "reason": "Evidence readiness is blocked because compiled evidence replay is required but not verified.",
    } in contract["blockers"]
    assert "missing launch receipt" in contract["runtime_risks"]
    assert not any("budget exhausted" in str(risk).lower() for risk in contract["runtime_risks"])
    assert any("Provider/runtime failure observed" in risk for risk in contract["runtime_risks"])
    assert any("Evidence readiness is blocked" in risk for risk in contract["runtime_risks"])
    assert any("configured iteration budget" in caveat for caveat in contract["runtime_caveats"])
    assert contract["review_readiness"]["evidence_readiness"] == {
        "status": "blocked",
        "compile_provenance_status": "fresh",
        "output_binding_status": "fresh",
        "replay_required": True,
        "replay_status": "stale_or_invalid",
        "replay_ok": False,
    }
    assert contract["review_readiness"]["claim_support"] == {
        "status": "has_demotions",
        "claim_count": 3,
        "weak_or_unsourced_count": 1,
        "source_context_blocked_count": 0,
        "status_counts": {
            "direct_source_support": 2,
            "unsupported_no_sources": 1,
        },
        "source_context_status_counts": {"verified": 2},
    }
    assert contract["graph_and_gap_actions"]["graph_rd_actions"][0]["action_type"] == "in_loop_focus_receipt"
    assert any("--preflight-only" in action for action in contract["next_actions"])
    authority = contract["report_action_authority"]
    assert authority["schema"] == "ztare-report-action-authority-v1"
    assert any(
        row["label"] == "Run the model-free launch preflight.: ztare autoresearch run --preflight-only"
        for row in authority["allowed_now"]
    )
    assert any(
        row["label"] == "The root cause is proven."
        for row in authority["forbidden_upgrades"]
    )
    assert "Treat trace readiness" in " ".join(contract["required_report_rules"])
    assert "blocked evidence readiness" in " ".join(contract["required_report_rules"])
    assert "stale or unbound synthesis inputs" in " ".join(contract["required_report_rules"])
    assert "weak or unsourced claim-support rows" in " ".join(
        contract["required_report_rules"]
    )
    assert "stale or unverified claim-support source context" in " ".join(
        contract["required_report_rules"]
    )
    assert "Preserve tense and epistemic status" in " ".join(contract["required_report_rules"])
    assert "report_action_authority.allowed_now" in " ".join(contract["required_report_rules"])

    written = write_report_support_contract(
        project_dir,
        ledger=ledger,
        brief={},
        context=context,
        autoresearch_review_context=loaded_trace,
    )
    assert written == contract
    assert json.loads(synthesis_paths(project_dir)["report_support_contract"].read_text(encoding="utf-8")) == contract


def test_report_support_contract_blocks_unbound_synthesis_ledger(tmp_path: Path) -> None:
    project_dir = tmp_path / "ops_demo"
    project_dir.mkdir()
    evidence_path = project_dir / "evidence.txt"
    evidence_path.write_text("Evidence changed after the old ledger was created.", encoding="utf-8")

    contract = build_report_support_contract(
        ledger={"review_status": {"readiness": "ready"}},
        brief={},
        context={
            "project_name": "ops_demo",
            "renderer_type": "decision_brief",
            "artifact_paths": [str(evidence_path)],
        },
    )

    assert contract["status"] == "blocked"
    assert "synthesis_input_binding_unbound" in contract["status_reasons"]
    assert any(
        isinstance(blocker, dict) and blocker.get("id") == "synthesis_input_binding"
        for blocker in contract["blockers"]
    )
    assert contract["synthesis_input_binding"]["status"] == "unbound"


def test_report_support_contract_blocks_stale_synthesis_ledger(tmp_path: Path) -> None:
    project_dir = tmp_path / "ops_demo"
    project_dir.mkdir()
    evidence_path = project_dir / "evidence.txt"
    evidence_path.write_text("Original evidence.", encoding="utf-8")
    binding = build_artifact_input_binding([str(evidence_path)])
    evidence_path.write_text("Updated evidence.", encoding="utf-8")

    contract = build_report_support_contract(
        ledger={
            "_meta": {
                "artifact_paths": [str(evidence_path)],
                "artifact_input_digest": binding["digest"],
            },
            "review_status": {"readiness": "ready"},
        },
        brief={},
        context={
            "project_name": "ops_demo",
            "renderer_type": "decision_brief",
            "artifact_paths": [str(evidence_path)],
        },
    )

    assert contract["status"] == "blocked"
    assert "synthesis_input_binding_digest_mismatch" in contract["status_reasons"]
    assert contract["synthesis_input_binding"]["status"] == "digest_mismatch"


def test_ledger_cache_validation_recomputes_artifact_hashes(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.txt"
    evidence_path.write_text("Original evidence.", encoding="utf-8")
    binding = build_artifact_input_binding([str(evidence_path)])
    cached_ledger = {
        "_meta": {
            "artifact_paths": [str(evidence_path)],
            "artifact_input_digest": binding["digest"],
            "prompt_hash": "prompt-v1",
        }
    }
    context = {
        "artifact_paths": [str(evidence_path)],
        "artifact_input_binding": binding,
        "ledger_prompt_hash": "prompt-v1",
    }
    evidence_path.write_text("Updated evidence.", encoding="utf-8")

    assert cached_ledger_matches_context(cached_ledger, context) is False


def test_support_contract_only_refreshes_without_model_client(tmp_path: Path) -> None:
    project_dir = tmp_path / "ops_demo"
    synth_dir = project_dir / "synthesis"
    synth_dir.mkdir(parents=True)
    evidence_path = project_dir / "evidence.txt"
    evidence_path.write_text("Source-backed evidence.", encoding="utf-8")
    paths = synthesis_paths(project_dir)
    context = {
        "project_name": "ops_demo",
        "project_dir": str(project_dir),
        "project_type": "general_analysis",
        "renderer_type": "decision_brief",
        "history_mode": "focused",
        "output_paths": {
            "context": str(synth_dir / "context.decision_brief.json"),
            "ledger": str(paths["ledger"]),
            "brief": str(synth_dir / "brief.decision_brief.json"),
            "candidate_report": str(synth_dir / "Report.decision_brief.candidate.md"),
            "qa": str(synth_dir / "qa.decision_brief.json"),
            "final_report": str(project_dir / "Report.decision_brief.md"),
        },
    }
    Path(context["output_paths"]["context"]).write_text(
        json.dumps(context),
        encoding="utf-8",
    )
    binding = build_artifact_input_binding([str(evidence_path)])
    paths["ledger"].write_text(
        json.dumps(
            {
                "_meta": {
                    "artifact_paths": [str(evidence_path)],
                    "artifact_input_digest": binding["digest"],
                },
                "review_status": {"readiness": "ready"},
            }
        ),
        encoding="utf-8",
    )

    rc = run_support_contract_only(
        argparse.Namespace(
            project=str(project_dir),
            projects=None,
            renderer_type="decision_brief",
            pack=None,
        )
    )

    contract = json.loads(paths["report_support_contract"].read_text(encoding="utf-8"))
    assert rc == 0
    assert contract["status"] == "ready"
    assert contract["synthesis_input_binding"]["status"] == "fresh"


def test_report_support_contract_distinguishes_historical_provider_failures() -> None:
    contract = build_report_support_contract(
        ledger={
            "review_status": {
                "runtime_risks": [
                    "External validation provider failures observed during processing.",
                    "Validation compute budget exhausted on recent runs.",
                ]
            }
        },
        brief={},
        context={"project_name": "ops_demo", "renderer_type": "research_note"},
        autoresearch_review_context={
            "schema": "ztare-synthesis-autoresearch-review-context-v1",
            "project": "ops_demo",
            "readiness": "ready_for_in_loop_candidate",
            "status": "complete_trace",
            "kernel_entry": {"status": "ready", "blockers": []},
            "recent_loop": {
                "latest_provider_failure_observed": False,
                "provider_failure_observed": True,
                "latest_run_exit_reason": "budget_exhausted",
            },
            "surfaces": {
                "evidence_compile_freshness": {"status": "fresh"},
                "evidence_output_binding": {"status": "fresh"},
                "evidence_replay": {"required": True, "status": "ok", "ok": True},
                "claim_support": {
                    "status": "ready",
                    "ok": True,
                    "claim_count": 1,
                    "weak_or_unsourced_count": 0,
                    "source_context_blocked_count": 0,
                    "status_counts": {"direct_source_support": 1},
                    "source_context_status_counts": {"verified": 1},
                },
            },
        },
    )

    assert contract["status"] == "ready"
    assert contract["status_reasons"] == []
    assert not any("latest autoresearch trace" in risk for risk in contract["runtime_risks"])
    assert not any("External validation provider failures" in risk for risk in contract["runtime_risks"])
    assert any("External validation provider failures" in caveat for caveat in contract["runtime_caveats"])
    assert any("Historical provider/runtime failures" in caveat for caveat in contract["runtime_caveats"])


def test_qa_promotion_blocks_high_scoring_distortions() -> None:
    qa = {
        "faithful": True,
        "score": 97,
        "issues": [
            {
                "type": "distortion",
                "description": "The report adds a date that is not in the inputs.",
            },
            {
                "type": "unsupported_action",
                "description": "The report recommends a rollout step that is not in the inputs.",
            }
        ],
    }

    assert qa_blocking_issues(qa) == qa["issues"]
    assert not qa_passes_for_report_write(qa, threshold=85)


def test_report_action_authority_separates_immediate_conditional_and_deferred() -> None:
    contract = build_report_support_contract(
        ledger={
            "review_status": {
                "next_actions": ["Run source freshness before synthesis."],
            },
            "unsupported_narratives": [
                {"claim": "The diagnosis is proven.", "why_unsupported": "Mechanism missing."}
            ],
            "premature_focus_areas": [
                {"area": "Redesign the cache before the discriminator runs."}
            ],
        },
        brief={
            "prerequisite_action": "Run the discriminator first.",
            "decision_rule_plain": {
                "if_positive": "Open the cache investigation.",
                "if_negative": "Proceed with bounded export remediation.",
            },
            "what_to_defer": ["Production rollout until evidence freshness passes."],
        },
        context={"project_name": "ops_demo", "renderer_type": "decision_brief"},
    )

    authority = contract["report_action_authority"]
    assert contract["ok"] is True
    assert contract["status"] == "ready"
    assert contract["status_reasons"] == []
    assert [row["label"] for row in authority["allowed_now"]] == [
        "Run the discriminator first.",
        "Run source freshness before synthesis.",
    ]
    assert {row["condition"] for row in authority["conditional"]} == {
        "if_positive",
        "if_negative",
    }
    assert {row["label"] for row in authority["deferred"]} == {
        "Production rollout until evidence freshness passes.",
        "Redesign the cache before the discriminator runs.",
    }
    assert any(
        row["label"] == "The diagnosis is proven."
        for row in authority["forbidden_upgrades"]
    )


def test_qa_promotion_allows_non_blocking_style_notes() -> None:
    qa = {
        "faithful": True,
        "score": 91,
        "issues": [
            {
                "type": "style",
                "description": "One section could be shorter.",
            }
        ],
    }

    assert qa_blocking_issues(qa) == []
    assert qa_passes_for_report_write(qa, threshold=85)


def test_qa_cannot_write_final_report_when_support_contract_is_blocked(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "ops_demo"
    synth_dir = project_dir / "synthesis"
    synth_dir.mkdir(parents=True)
    final_report = project_dir / "Report.decision_brief.md"
    context = {
        "project_dir": str(project_dir),
        "renderer_type": "decision_brief",
        "output_paths": {
            "candidate_report": str(synth_dir / "Report.decision_brief.candidate.md"),
            "qa": str(synth_dir / "qa.decision_brief.json"),
            "final_report": str(final_report),
        },
    }
    synthesis_paths(project_dir)["report_support_contract"].write_text(
        json.dumps(
            {
                "schema": "ztare-synthesis-report-support-contract-v1",
                "ok": False,
                "status": "blocked",
                "status_reasons": ["synthesis_input_binding_unbound"],
            }
        ),
        encoding="utf-8",
    )

    class FakeQALLM:
        def call(self, _prompt: str) -> str:
            return json.dumps({"faithful": True, "score": 99, "issues": []})

    monkeypatch.setattr(synth, "ACTIVE_QA_LLM", FakeQALLM())
    monkeypatch.setattr(synth, "ACTIVE_QA_THRESHOLD", 85)

    qa = qa_artifact({}, {}, "Blocked contract draft.", context)

    assert qa["faithful"] is True
    assert qa["score"] == 99
    assert qa["_meta"]["report_written"] is False
    assert qa["_meta"]["report_write_blocked_by_support_contract"] is True
    assert qa["_meta"]["report_support_contract_status"] == "blocked"
    assert qa["_meta"]["report_support_contract_status_reasons"] == [
        "synthesis_input_binding_unbound"
    ]
    assert not final_report.exists()


def test_qa_repair_loop_uses_bounded_attempts(monkeypatch, tmp_path: Path) -> None:
    project_dir = tmp_path / "ops_demo"
    synth_dir = project_dir / "synthesis"
    synth_dir.mkdir(parents=True)
    context = {
        "project_dir": str(project_dir),
        "renderer_type": "decision_brief",
        "audience": "operator",
        "tone": "plain",
        "output_paths": {
            "candidate_report": str(synth_dir / "Report.decision_brief.candidate.md"),
            "qa": str(synth_dir / "qa.decision_brief.json"),
            "final_report": str(project_dir / "Report.decision_brief.md"),
        },
    }
    qa_sequence = [
        {
            "faithful": True,
            "score": 96,
            "issues": [{"type": "distortion", "description": "overstated mechanism"}],
        },
        {
            "faithful": True,
            "score": 96,
            "issues": [{"type": "overclaim", "description": "still overclaimed"}],
        },
        {"faithful": True, "score": 93, "issues": []},
    ]
    repairs = []

    def fake_qa(_ledger, _brief, _report, _context):
        payload = dict(qa_sequence.pop(0))
        payload["_meta"] = {"report_written": payload["issues"] == []}
        return payload

    def fake_repair(*, report, qa, ledger, brief, context):
        repairs.append((report, qa["score"]))
        return f"{report}\nrepair-{len(repairs)}"

    monkeypatch.setattr(synth, "ACTIVE_QA_REPAIR_ATTEMPTS", 2)
    monkeypatch.setattr(synth, "qa_artifact", fake_qa)
    monkeypatch.setattr(synth, "repair_artifact_after_qa", fake_repair)

    qa = qa_artifact_with_repair({}, {}, "draft", context)

    assert qa["issues"] == []
    assert qa["_meta"]["qa_repair_attempted"] is True
    assert qa["_meta"]["qa_repair_attempts"] == 2
    assert qa["_meta"]["qa_repair_attempt_limit"] == 2
    assert [row["source_blocking_issue_count"] for row in qa["_meta"]["qa_repair_history"]] == [1, 1]
    assert len(repairs) == 2
    assert Path(context["output_paths"]["candidate_report"]).read_text(encoding="utf-8").endswith("repair-2")
