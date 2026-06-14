from __future__ import annotations

from types import SimpleNamespace

from src.ztare.reports import autoresearch_kernel_health as health


def _patch_common(
    monkeypatch,
    *,
    rubric_attention: int = 0,
    dispatch_findings: int = 0,
    subscription_ok: bool = True,
    subscription_status: str = "comparable",
    mechanism_summary: dict | None = None,
    route_rows_needed: int = 0,
    source_health_blockers: int = 0,
    source_health_warnings: int = 0,
    unexplained_bypasses: int = 0,
    parent_utility_ok: bool = True,
    primitive_open_misses: int = 0,
    primitive_malformed_misses: int = 0,
):
    monkeypatch.setattr(
        health,
        "_dispatch_validate",
        lambda repo: {
            "summary": {
                "findings": dispatch_findings,
                "dispatch_sites": 20,
                "wrapped_sites": 16,
                "direct_allowed_sites": 4,
            },
            "direct_allowed": [
                {
                    "path": "src/ztare/validator/autoresearch_loop.py",
                    "line": 1357,
                    "function": "safe_mutate",
                    "reason": "dispatch-covered mutator fallback",
                }
            ],
        },
    )
    monkeypatch.setattr(
        health,
        "_catalog_health",
        lambda repo: SimpleNamespace(
            ok=True,
            row_count=781,
            warnings=(),
            stale_outputs=(),
        ),
    )
    monkeypatch.setattr(
        health,
        "_primitive_parent_utility",
        lambda: {
            "ok": parent_utility_ok,
            "case_count": 6,
            "passed": 6 if parent_utility_ok else 5,
            "catalog_rank_recall": 1.0,
            "worker_rank_recall": 1.0 if parent_utility_ok else 0.5,
            "child_recall": 1.0,
        },
    )
    monkeypatch.setattr(
        health,
        "_primitive_miss_queue",
        lambda repo: {
            "path": "analytics/public/queries/primitive_amnesia_miss_queue.jsonl",
            "row_count": primitive_open_misses + primitive_malformed_misses,
            "open_count": primitive_open_misses,
            "malformed_count": primitive_malformed_misses,
            "status_counts": {"open": primitive_open_misses}
            if primitive_open_misses
            else {},
            "latest_open": [
                {
                    "miss_id": "miss1",
                    "case_id": "case1",
                    "query": "find overlap primitive",
                    "targets": ["jaccard"],
                }
            ][:primitive_open_misses],
        },
    )
    monkeypatch.setattr(
        health,
        "_mechanism_consequences",
        lambda **kwargs: {
            "summary": mechanism_summary or {
                "mechanism_count": 13,
                "evidence_status_counts": {"observed": 13},
                "evidence_quality_counts": {"usable": 13},
                "intrinsic_decorative_count": 0,
                "placeholder_only_count": 0,
            }
        },
    )
    monkeypatch.setattr(
        health,
        "_fixtures",
        lambda: {
            "passed": True,
            "num_passed": 12,
            "num_fixtures": 12,
            "mechanism_status": {"by_status": {"active": {"passed": 8, "total": 8}}},
        },
    )
    monkeypatch.setattr(
        health,
        "_rubric_modes",
        lambda **kwargs: {
            "summary": {
                "attention_count": rubric_attention,
                "status_counts": {"ok": 10},
                "mode_counts": {"newton": 10},
                "legacy_unset": {
                    "count": 0,
                    "with_project_count": 0,
                    "without_project_count": 0,
                    "charter_status_counts": {},
                },
            }
        },
    )
    monkeypatch.setattr(
        health,
        "_hill_climb",
        lambda **kwargs: {
            "workspace_count": 4,
            "stagnant_workspace_count": 2,
            "status_counts": {"escape_evidence_observed": 2},
            "post_control_outcome_totals": {
                "active_control_event_count": 3,
                "post_control_success_rate": 0.5,
            },
        },
    )
    monkeypatch.setattr(
        health,
        "_subscription_outcomes",
        lambda **kwargs: {
            "ok": subscription_ok,
            "status": subscription_status,
            "summary": {
                "node_count": 8,
                "transport_counts": {"api": 4, "subscription_cli": 4}
                if subscription_ok
                else {"unrecorded": 8},
                "api_rows": 4 if subscription_ok else 0,
                "subscription_rows": 4 if subscription_ok else 0,
            },
            "matched_run_plan": []
            if subscription_ok
            else [
                {
                    "project": "gp_example",
                    "rubric": "gp_example",
                    "suitability_score": 88,
                    "matched_pair_command": (
                        "make autoresearch-matched-transport-pair PROJECT=gp_example "
                        "RUBRIC=gp_example ITERS=1 MATCHED_RUN_ID=pair_gp_example_001"
                    ),
                }
            ],
            "action": "inspect deltas"
            if subscription_ok
            else "run fresh API and subscription-backed rows with worker metadata",
        },
    )
    monkeypatch.setattr(
        health,
        "_operations_intelligence",
        lambda repo: {
            "agentic_workbench": {
                "rows": 5,
                "ready_workbench_bypasses": 0,
                "missing_surface_preparations": 2,
                "route_row_coverage": {
                    "status": "route_rows_present"
                    if route_rows_needed == 0
                    else "sparse_route_logging",
                    "route_rows": 5 - route_rows_needed,
                    "recommended_min_route_rows": 5,
                    "additional_route_rows_needed": route_rows_needed,
                    "needs_logging_attention": route_rows_needed > 0,
                },
                "subscription_outcomes": {"status": subscription_status},
                "ready_workbench_bypasses_without_reason": unexplained_bypasses,
            },
            "source_health_summary": {
                "blocking_count": source_health_blockers,
                "warning_count": source_health_warnings,
                "issue_count": source_health_blockers + source_health_warnings,
                "issue_type_counts": (
                    {"fixture_warning": source_health_warnings}
                    if source_health_warnings
                    else {}
                ),
            },
        },
    )


def test_kernel_health_ready_when_components_ok(tmp_path, monkeypatch):
    _patch_common(monkeypatch)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "ok"
    assert report["summary"]["component_status"] == "ok"
    assert report["summary"]["component_counts"] == {
        "ok": 7,
        "attention": 0,
        "needs_attention": 0,
    }
    assert report["summary"]["evidence_gap_count"] == 0
    rendered = health.render_text(report)
    assert "Autoresearch kernel health" in rendered
    assert "next=make autoresearch-dispatch-validate JSON=1" in rendered
    operations = next(
        row for row in report["components"] if row["component"] == "operations_intelligence"
    )
    assert operations["summary"]["route_row_coverage_status"] == "route_rows_present"
    assert operations["next_command"] == "make operations-intelligence"
    rubric = next(row for row in report["components"] if row["component"] == "rubric_modes")
    assert rubric["summary"]["legacy_unset_count"] == 0
    dispatch = next(row for row in report["components"] if row["component"] == "dispatch")
    assert dispatch["summary"]["direct_allowed"][0]["reason"] == (
        "dispatch-covered mutator fallback"
    )
    catalog = next(row for row in report["components"] if row["component"] == "primitive_catalog")
    assert catalog["summary"]["parent_utility"]["ok"] is True


def test_kernel_health_attention_for_rubric_debt(tmp_path, monkeypatch):
    _patch_common(monkeypatch, rubric_attention=3)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "attention"
    rubric = next(row for row in report["components"] if row["component"] == "rubric_modes")
    assert rubric["status"] == "attention"
    assert rubric["summary"]["attention_count"] == 3
    assert rubric["next_command"] == "make autoresearch-rubric-mode-audit LIMIT=20"


def test_kernel_health_next_commands_preserve_scope(tmp_path, monkeypatch):
    _patch_common(monkeypatch, rubric_attention=1)

    report = health.build_autoresearch_kernel_health(
        repo=tmp_path,
        project="gp_example",
        workspace="projects/gp_example/workspace",
        rubric="rubrics/gp_example.json",
        stagnation_threshold=3,
    )

    mechanism = next(
        row for row in report["components"] if row["component"] == "mechanism_consequences"
    )
    rubric = next(row for row in report["components"] if row["component"] == "rubric_modes")
    hill = next(row for row in report["components"] if row["component"] == "hill_climb_controls")

    assert mechanism["next_command"] == (
        "make autoresearch-consequence-audit PROJECT=gp_example "
        "WORKSPACE=projects/gp_example/workspace JSON=1"
    )
    assert rubric["next_command"] == (
        "make autoresearch-rubric-mode-audit RUBRIC=rubrics/gp_example.json LIMIT=20"
    )
    assert hill["next_command"] == (
        "make autoresearch-hillclimb-audit PROJECT=gp_example STAGNATION_THRESHOLD=3 LIMIT=20"
    )


def test_kernel_health_needs_attention_when_parent_utility_fails(tmp_path, monkeypatch):
    _patch_common(monkeypatch, parent_utility_ok=False)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "needs_attention"
    catalog = next(row for row in report["components"] if row["component"] == "primitive_catalog")
    assert catalog["status"] == "needs_attention"
    assert catalog["summary"]["parent_utility"]["ok"] is False
    assert catalog["next_command"] == "make primitive-parent-utility JSON=1"


def test_kernel_health_attention_for_open_primitive_miss_queue(tmp_path, monkeypatch):
    _patch_common(monkeypatch, primitive_open_misses=1)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "attention"
    catalog = next(row for row in report["components"] if row["component"] == "primitive_catalog")
    assert catalog["status"] == "attention"
    assert catalog["summary"]["miss_queue"]["open_count"] == 1
    assert catalog["next_command"] == "make primitive-amnesia-eval RECORD_MISSES=1"


def test_kernel_health_needs_attention_for_malformed_primitive_miss_queue(tmp_path, monkeypatch):
    _patch_common(monkeypatch, primitive_malformed_misses=1)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "needs_attention"
    catalog = next(row for row in report["components"] if row["component"] == "primitive_catalog")
    assert catalog["status"] == "needs_attention"
    assert catalog["summary"]["miss_queue"]["malformed_count"] == 1


def test_kernel_health_needs_attention_for_placeholder_only_mechanisms(
    tmp_path, monkeypatch
):
    _patch_common(
        monkeypatch,
        mechanism_summary={
            "mechanism_count": 13,
            "evidence_status_counts": {"observed": 12, "placeholder_only": 1},
            "evidence_quality_counts": {"usable": 12, "placeholder_only": 1},
            "intrinsic_decorative_count": 0,
            "placeholder_only_count": 1,
        },
    )

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "needs_attention"
    mechanism = next(
        row for row in report["components"] if row["component"] == "mechanism_consequences"
    )
    assert mechanism["status"] == "needs_attention"
    assert mechanism["summary"]["placeholder_only_count"] == 1
    assert "placeholder-only" in mechanism["action"]


def test_kernel_health_surfaces_not_triggered_mechanisms_as_evidence_gap(
    tmp_path, monkeypatch
):
    _patch_common(
        monkeypatch,
        mechanism_summary={
            "mechanism_count": 13,
            "evidence_status_counts": {"observed": 10, "not_triggered": 3},
            "evidence_quality_counts": {"usable": 10, "not_triggered": 3},
            "intrinsic_decorative_count": 0,
            "placeholder_only_count": 0,
        },
    )
    monkeypatch.setattr(
        health,
        "_mechanism_consequences",
        lambda **kwargs: {
            "summary": {
                "mechanism_count": 13,
                "evidence_status_counts": {"observed": 10, "not_triggered": 3},
                "evidence_quality_counts": {"usable": 10, "not_triggered": 3},
                "intrinsic_decorative_count": 0,
                "placeholder_only_count": 0,
            },
            "rows": [
                {
                    "mechanism_id": "parallel_blitz",
                    "label": "Parallel mutator / blitz selection",
                    "trigger": "Rubric force flag or stagnation threshold enables K-way mutation.",
                    "evidence_status": "not_triggered",
                }
            ],
        },
    )

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "attention"
    assert report["summary"]["component_status"] == "ok"
    assert report["summary"]["evidence_gap_count"] == 1
    mechanism = next(
        row for row in report["components"] if row["component"] == "mechanism_consequences"
    )
    assert mechanism["status"] == "ok"
    assert mechanism["summary"]["not_triggered_count"] == 3
    gap = report["evidence_gaps"][0]
    assert gap["id"] == "not_triggered_mechanisms"
    assert gap["status"] == "not_triggered"
    assert gap["summary"]["count"] == 3
    assert gap["summary"]["examples"][0]["mechanism_id"] == "parallel_blitz"


def test_kernel_health_surfaces_subscription_outcome_gap_without_blocking(
    tmp_path, monkeypatch
):
    _patch_common(
        monkeypatch,
        subscription_ok=False,
        subscription_status="transport_metadata_missing",
    )

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "attention"
    assert report["summary"]["component_status"] == "ok"
    assert report["summary"]["component_counts"] == {
        "ok": 7,
        "attention": 0,
        "needs_attention": 0,
    }
    assert report["summary"]["evidence_gap_count"] == 1
    gap = report["evidence_gaps"][0]
    assert gap["id"] == "subscription_outcomes"
    assert gap["status"] == "transport_metadata_missing"
    assert gap["next_command"] == "make autoresearch-subscription-outcome-audit JSON=1"
    assert gap["summary"]["suggested_matched_pair_project"] == "gp_example"
    assert gap["summary"]["suggested_matched_pair_rubric"] == "gp_example"
    assert gap["summary"]["suggested_matched_pair_suitability"] == 88
    assert gap["summary"]["suggested_matched_pair_command"].startswith(
        "make autoresearch-matched-transport-pair PROJECT=gp_example"
    )
    rendered = health.render_text(report)
    assert "evidence_gaps=1" in rendered
    assert "evidence_gap:subscription_outcomes" in rendered


def test_kernel_health_needs_attention_for_sparse_route_logging(tmp_path, monkeypatch):
    _patch_common(monkeypatch, route_rows_needed=2)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "needs_attention"
    operations = next(
        row for row in report["components"] if row["component"] == "operations_intelligence"
    )
    assert operations["status"] == "needs_attention"
    assert operations["summary"]["additional_route_rows_needed"] == 2
    assert operations["next_command"] == "make operations-intelligence"


def test_kernel_health_needs_attention_for_blocking_action_sources(tmp_path, monkeypatch):
    _patch_common(monkeypatch, source_health_blockers=1)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "needs_attention"
    operations = next(
        row for row in report["components"] if row["component"] == "operations_intelligence"
    )
    assert operations["status"] == "needs_attention"
    assert operations["summary"]["source_health_blockers"] == 1


def test_kernel_health_surfaces_source_health_warnings_without_blocking(
    tmp_path, monkeypatch
):
    _patch_common(monkeypatch, source_health_warnings=2)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "ok"
    operations = next(
        row for row in report["components"] if row["component"] == "operations_intelligence"
    )
    assert operations["status"] == "ok"
    assert operations["summary"]["source_health_issues"] == 2
    assert operations["summary"]["source_health_warnings"] == 2
    assert operations["summary"]["source_health_blockers"] == 0
    assert operations["summary"]["source_health_issue_type_counts"] == {
        "fixture_warning": 2
    }


def test_kernel_health_needs_attention_for_unexplained_workbench_bypass(
    tmp_path, monkeypatch
):
    _patch_common(monkeypatch, unexplained_bypasses=1)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "needs_attention"
    operations = next(
        row for row in report["components"] if row["component"] == "operations_intelligence"
    )
    assert operations["status"] == "needs_attention"
    assert operations["summary"]["ready_workbench_bypasses_without_reason"] == 1


def test_main_strict_fails_on_subscription_outcome_evidence_gap(
    tmp_path, monkeypatch, capsys
):
    _patch_common(
        monkeypatch,
        subscription_ok=False,
        subscription_status="transport_metadata_missing",
    )
    monkeypatch.setattr(health, "REPO", tmp_path)

    rc = health.main(["--strict"])

    assert rc == 1
    out = capsys.readouterr().out
    assert "status=attention" in out
    assert "evidence_gaps=1" in out


def test_kernel_health_needs_attention_for_dispatch_findings(tmp_path, monkeypatch):
    _patch_common(monkeypatch, rubric_attention=3, dispatch_findings=1)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "needs_attention"
    dispatch = next(row for row in report["components"] if row["component"] == "dispatch")
    assert dispatch["status"] == "needs_attention"


def test_main_strict_fails_on_attention(tmp_path, monkeypatch, capsys):
    _patch_common(monkeypatch, rubric_attention=1)
    monkeypatch.setattr(health, "REPO", tmp_path)

    rc = health.main(["--strict"])

    assert rc == 1
    assert "status=attention" in capsys.readouterr().out
