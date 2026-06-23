from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ztare.workspace.fetch_evidence import (
    _openai_search_model_id,
    already_fetched_queries,
    classify_fetch_error,
    fetch_via_web_search,
    filter_gaps,
    run_fetch,
    run_auto_compile,
    web_search_backend_for_model,
)


def _completed(returncode: int = 0) -> subprocess.CompletedProcess[list[str]]:
    return subprocess.CompletedProcess(args=[], returncode=returncode)


def test_fetch_evidence_auto_compile_runs_source_check_first(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_dir = tmp_path / "projects" / "demo_fetch"
    project_dir.mkdir(parents=True)
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs) -> subprocess.CompletedProcess[list[str]]:
        calls.append(cmd)
        return _completed(0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert run_auto_compile(project_dir=project_dir, model="gemini") is True

    assert calls == [
        [
            sys.executable,
            "-m",
            "ztare.scaffold.source_check",
            "--project",
            "demo_fetch",
        ],
        [
            sys.executable,
            "-m",
            "ztare.workspace.update_workspace",
            "--project",
            "demo_fetch",
            "--model",
            "gemini",
        ],
        [
            sys.executable,
            "-m",
            "ztare.workspace.compile_evidence",
            "--project",
            "demo_fetch",
            "--mode",
            "workspace",
            "--model",
            "gemini",
        ],
    ]


def test_fetch_evidence_auto_compile_stops_on_source_check_failure(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    project_dir = tmp_path / "projects" / "blocked_fetch"
    project_dir.mkdir(parents=True)
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs) -> subprocess.CompletedProcess[list[str]]:
        calls.append(cmd)
        return _completed(2)

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert run_auto_compile(project_dir=project_dir, model="deepseek") is False

    assert calls == [
        [
            sys.executable,
            "-m",
            "ztare.scaffold.source_check",
            "--project",
            "blocked_fetch",
        ]
    ]
    out = capsys.readouterr().out
    assert "source-check failed" in out
    assert "skipping workspace-update and evidence-compile" in out
    assert "ztare project source-check --project blocked_fetch --json" in out
    assert "make evidence-prepare PROJECT=blocked_fetch MODEL=deepseek" in out


def test_web_search_backend_selection_is_explicit() -> None:
    assert web_search_backend_for_model("gpt4.1") == "openai"
    assert web_search_backend_for_model("o3") == "openai"
    assert web_search_backend_for_model("claude") == "anthropic"
    assert web_search_backend_for_model("gemini") == "anthropic"
    assert web_search_backend_for_model("deepseek") == "anthropic"
    assert web_search_backend_for_model("kimi") == "anthropic"
    assert web_search_backend_for_model("grok") == "anthropic"
    assert web_search_backend_for_model("xai") == "anthropic"
    assert web_search_backend_for_model("deepseek", backend="openai") == "openai"
    assert web_search_backend_for_model("grok", backend="anthropic") == "anthropic"
    assert _openai_search_model_id("deepseek") == "gpt-4.1"


def test_fetch_error_classification_guides_retry_policy() -> None:
    assert classify_fetch_error("credit balance is too low") == {
        "failure_kind": "provider_quota",
        "retryable": False,
        "recovery_hint": "change billing state or choose another search backend",
    }
    assert classify_fetch_error("Connection error")["failure_kind"] == "provider_connection"
    assert classify_fetch_error("Connection error")["retryable"] is True
    assert classify_fetch_error("Error code: 429 rate_limit")["failure_kind"] == (
        "provider_rate_limit"
    )
    assert classify_fetch_error("invalid_api_key")["retryable"] is False


def test_filter_gaps_ignores_resolved_or_justified_rows() -> None:
    gaps = [
        {"id": "active", "severity": "degrading", "recovery_kind": "public_evidence"},
        {"id": "resolved", "severity": "degrading", "status": "resolved"},
        {"id": "justified", "severity": "degrading", "justified_at": "2026-06-20T00:00:00Z"},
        {"id": "other_severity", "severity": "blocking"},
    ]

    assert filter_gaps(gaps, "degrading") == [
        {"id": "active", "severity": "degrading", "recovery_kind": "public_evidence"}
    ]


def test_filter_gaps_ignores_repaired_local_artifact_gap(tmp_path: Path) -> None:
    project = tmp_path / "projects" / "demo"
    project.mkdir(parents=True)
    (project / "test_model.py").write_text("def I_model():\n    return 1.0\n", encoding="utf-8")
    gaps = [
        {
            "id": "repaired",
            "severity": "degrading",
            "target": "test_model.py",
            "description": "The falsification suite is missing.",
        },
        {
            "id": "active",
            "severity": "degrading",
            "target": "coverage",
            "description": "More public evidence is needed.",
            "recovery_kind": "public_evidence",
        },
    ]

    assert filter_gaps(gaps, "degrading", project_dir=project) == [
        {
            "id": "active",
            "severity": "degrading",
            "target": "coverage",
            "description": "More public evidence is needed.",
            "recovery_kind": "public_evidence",
        }
    ]


def test_already_fetched_queries_ignores_rejected_manifest_rows(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    evidence_txt = project / "evidence.txt"
    evidence_txt.write_text("", encoding="utf-8")
    (workspace / "evidence_fetch_manifest_20260621T000000Z.json").write_text(
        json.dumps(
            {
                "fetches": [
                    {
                        "gap_query": "failed transient provider query",
                        "status": "rejected",
                        "content_chars": 0,
                    },
                    {
                        "gap_query": "accepted query",
                        "status": "accepted",
                        "content_chars": 42,
                    },
                    {
                        "gap_query": "legacy successful query",
                        "content_chars": 17,
                    },
                    {
                        "gap_query": "legacy failed query",
                        "content_chars": 0,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    assert already_fetched_queries(evidence_txt) == {
        "accepted query",
        "legacy successful query",
    }


def test_filter_gaps_ignores_active_local_verifier_gap() -> None:
    gaps = [
        {
            "id": "packet-elements",
            "severity": "degrading",
            "target": "packet_elements",
            "description": (
                "No evidence that source/evidence references were actually checked "
                "for existence and correctness beyond their being named."
            ),
            "producer_rationale": "Existence of labels treated as proof",
        },
        {
            "id": "public",
            "severity": "degrading",
            "target": "external comparison",
            "description": "More public evidence is needed.",
        },
    ]

    assert filter_gaps(gaps, "degrading") == []
    assert filter_gaps(gaps, "degrading", allow_inferred_public=True) == [
        {
            "id": "public",
            "severity": "degrading",
            "target": "external comparison",
            "description": "More public evidence is needed.",
        }
    ]


def test_filter_gaps_uses_recovery_contract_booleans() -> None:
    gaps = [
        {
            "id": "local-by-contract",
            "severity": "degrading",
            "target": "source-preflight receipt",
            "description": "More public evidence is needed.",
            "can_public_fetch": False,
            "in_loop_consumable": True,
        },
        {
            "id": "public-by-contract",
            "severity": "degrading",
            "target": "external comparison",
            "description": "The text mentions local fixtures but the route is public.",
            "can_public_fetch": True,
            "in_loop_consumable": False,
        },
    ]

    assert filter_gaps(gaps, "degrading") == [
        {
            "id": "public-by-contract",
            "severity": "degrading",
            "target": "external comparison",
            "description": "The text mentions local fixtures but the route is public.",
            "can_public_fetch": True,
            "in_loop_consumable": False,
        }
    ]


def test_failed_fetch_is_manifest_only_not_source_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_dir = tmp_path / "projects" / "failed_fetch"
    workspace = project_dir / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "latest_evidence_gaps.json").write_text(
        (
            "{"
            '"evidence_gaps": ['
            '{"id": "gap-1", "severity": "degrading", '
            '"target": "external benchmark", '
            '"fetch_query": "external benchmark source", '
            '"description": "More public evidence is needed.", '
            '"recovery_kind": "public_evidence"}'
            "]}"
        ),
        encoding="utf-8",
    )

    def fail_fetch(
        _query: str,
        model: str = "",
        *,
        search_backend: str = "auto",
    ) -> tuple[str, str]:
        raise RuntimeError(f"simulated {model} failure")

    monkeypatch.setattr(
        "ztare.workspace.fetch_evidence.fetch_via_web_search",
        fail_fetch,
    )

    manifest = run_fetch(
        project_dir=project_dir,
        severity="degrading",
        max_fetches=3,
        auto_compile=False,
        model="kimi",
        dry_run=False,
    )

    assert manifest["total_attempted"] == 1
    assert manifest["total_accepted"] == 0
    assert manifest["fetches"][0]["status"] == "rejected"
    assert manifest["fetches"][0]["error_message"] == "simulated kimi failure"
    assert manifest["fetches"][0]["failure_kind"] == "provider_error"
    assert manifest["fetches"][0]["retryable"] is True
    assert manifest["failure_counts"] == {"provider_error": 1}
    assert manifest["fetches"][0]["content_chars"] == 0
    assert not (project_dir / "evidence.txt").exists()
    assert list((project_dir / "raw").glob("*.md")) == []
    manifest_files = list(workspace.glob("evidence_fetch_manifest_*.json"))
    assert len(manifest_files) == 1
    manifest_text = manifest_files[0].read_text(encoding="utf-8")
    assert '"status": "rejected"' in manifest_text
    assert '"error_message": "simulated kimi failure"' in manifest_text
    assert "[FETCH FAILED" not in manifest_text


def test_fetch_via_web_search_routes_by_backend(monkeypatch) -> None:
    calls: list[tuple[str, str, str]] = []

    def fake_openai(query: str, model: str) -> tuple[str, str]:
        calls.append(("openai", query, model))
        return "openai content", "openai source"

    def fake_anthropic(query: str, requested_model: str = "") -> tuple[str, str]:
        calls.append(("anthropic", query, requested_model))
        return "anthropic content", "anthropic source"

    monkeypatch.setattr(
        "ztare.workspace.fetch_evidence._fetch_via_openai_web_search",
        fake_openai,
    )
    monkeypatch.setattr(
        "ztare.workspace.fetch_evidence._fetch_via_anthropic_web_search",
        fake_anthropic,
    )

    assert fetch_via_web_search("q1", model="gpt4.1") == ("openai content", "openai source")
    assert fetch_via_web_search("q2", model="kimi") == (
        "anthropic content",
        "anthropic source",
    )
    assert fetch_via_web_search("q3", model="grok") == (
        "anthropic content",
        "anthropic source",
    )
    assert fetch_via_web_search(
        "q4",
        model="deepseek",
        search_backend="openai",
    ) == ("openai content", "openai source")

    assert calls == [
        ("openai", "q1", "gpt4.1"),
        ("anthropic", "q2", "kimi"),
        ("anthropic", "q3", "grok"),
        ("openai", "q4", "deepseek"),
    ]
