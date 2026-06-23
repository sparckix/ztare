from __future__ import annotations

import importlib.util
import argparse
import json
import sys
from pathlib import Path

import pytest


RUNNER_PATH = Path(__file__).resolve().parents[2] / "benchmarks/constraint_memory/run_benchmark.py"
SPEC = importlib.util.spec_from_file_location("constraint_memory_run_benchmark", RUNNER_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def prompt_hash_for(specimen: dict, contract: dict) -> str:
    return runner.sha256_text(runner.normalize_prompt_text(runner.build_ordinary_review_prompt(specimen, contract)))


def test_ordinary_review_prompt_excludes_answer_key_fields(tmp_path: Path) -> None:
    specimen_dir = tmp_path / "specimen"
    specimen_dir.mkdir()
    (specimen_dir / "thesis.md").write_text("Claim text with no answer key.\n", encoding="utf-8")
    (specimen_dir / "evidence.txt").write_text("Evidence text.\n", encoding="utf-8")
    specimen = {
        "id": "demo",
        "rubric": "constraint_memory_benchmark",
        "_dir": specimen_dir,
        "expected_exploit": "SHOULD_NOT_APPEAR",
        "detection_keywords": ["LEAK_KEYWORD"],
        "structural_expected_flags": {"leak": True},
    }
    contract = {
        "review_prompt_contract": {
            "required_output_schema": {
                "accept_claim_as_stated": "boolean",
                "score": "number from 0 to 100",
                "fatal_flaw_identified": "boolean",
                "flaw_summary": "string",
                "confidence": "low | medium | high",
            }
        }
    }

    prompt = runner.build_ordinary_review_prompt(specimen, contract)

    assert "Claim text with no answer key." in prompt
    assert "Evidence text." in prompt
    assert "SHOULD_NOT_APPEAR" not in prompt
    assert "LEAK_KEYWORD" not in prompt
    assert "structural_expected_flags" not in prompt
    assert "Forbidden context" in prompt


def test_export_ordinary_review_prompt_packet_is_reviewer_safe(tmp_path: Path) -> None:
    specimen_dir = tmp_path / "specimen"
    specimen_dir.mkdir()
    (specimen_dir / "thesis.md").write_text("Claim text.\n", encoding="utf-8")
    (specimen_dir / "evidence.txt").write_text("Evidence text.\n", encoding="utf-8")
    specimen = {
        "id": "demo",
        "label": "bad",
        "rubric": "constraint_memory_benchmark",
        "_dir": specimen_dir,
        "expected_exploit": "SHOULD_NOT_APPEAR",
        "detection_keywords": ["LEAK_KEYWORD"],
        "structural_detection_keywords": ["STRUCTURAL_LEAK"],
        "structural_expected_flags": {"leak": True},
    }
    contract = {
        "review_prompt_contract": {
            "forbidden_context": [
                "expected_exploit fields",
                "detection_keywords fields",
                "prior condition outputs from A/B/C",
            ],
            "required_output_schema": {
                "accept_claim_as_stated": "boolean",
                "score": "number from 0 to 100",
                "fatal_flaw_identified": "boolean",
                "flaw_summary": "string",
                "confidence": "low | medium | high",
            },
        },
        "required_import_provenance": {
            "model": "non-empty model identifier",
            "timestamp": "timestamp",
            "prompt": "prompt hash",
            "provider_runtime": "provider/runtime",
        },
    }

    payload = runner.export_ordinary_review_prompt_packet(
        [specimen],
        contract,
        tmp_path / "packet",
        source_run="benchmarks/constraint_memory/runs/source",
    )

    assert payload["ok"] is True
    manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))
    template = json.loads(Path(payload["import_template_path"]).read_text(encoding="utf-8"))
    readme = Path(payload["readme_path"]).read_text(encoding="utf-8")
    prompt_path = Path(payload["output_dir"]) / manifest["prompts"][0]["prompt_path"]
    prompt = prompt_path.read_text(encoding="utf-8")

    assert "Claim text." in prompt
    assert "Evidence text." in prompt
    assert "SHOULD_NOT_APPEAR" not in prompt
    assert "LEAK_KEYWORD" not in prompt
    assert "STRUCTURAL_LEAK" not in prompt
    assert manifest["prompts"][0]["prompt_sha256"] == runner.sha256_text(prompt)
    assert "label" not in manifest["prompts"][0]
    assert manifest["answer_key_fields_omitted"]
    assert template["reviews"][0]["prompt_sha256"] == manifest["prompts"][0]["prompt_sha256"]
    assert manifest["source_run"] == "benchmarks/constraint_memory/runs/source"
    assert "benchmark-ordinary-review-validate-import" in readme
    assert "benchmark-ordinary-review BENCH_ORDINARY_IMPORT" in readme
    assert "benchmark-ordinary-review-freeze-check" in readme
    assert "benchmarks/constraint_memory/runs/source" in readme


def test_source_run_specimen_filter_matches_frozen_run_set() -> None:
    source_run = Path("benchmarks/constraint_memory/runs/20260404_195100")

    source_ids = runner.source_run_specimen_ids(source_run)
    specimens = runner.load_specimens(suite="main", specimen_ids=source_ids)

    assert len(source_ids) == 9
    assert sorted(specimen["id"] for specimen in specimens) == source_ids
    assert "hex_byte_parser" not in source_ids
    assert "t6_ai_inference_internal_price_floor" not in source_ids


def test_normalize_ordinary_review_and_summary_metrics() -> None:
    review = runner.normalize_ordinary_review(
        {
            "accept_claim_as_stated": False,
            "score": 42,
            "fatal_flaw_identified": True,
            "flaw_summary": "claim is under-supported",
            "confidence": "high",
        }
    )
    assert review["score"] == 42.0
    assert review["fatal_flaw_identified"] is True

    rows = [
        {
            "condition": runner.ORDINARY_REVIEW_CONDITION,
            "label": "bad",
            "score": 42.0,
            "passed_threshold": False,
            "family_detected": False,
            "structural_detected": True,
        },
        {
            "condition": runner.ORDINARY_REVIEW_CONDITION,
            "label": "good",
            "score": 88.0,
            "passed_threshold": True,
            "family_detected": False,
            "structural_detected": False,
        },
    ]
    summary = runner.summarize(rows, 60, {runner.ORDINARY_REVIEW_CONDITION: None})
    metrics = summary["conditions"][runner.ORDINARY_REVIEW_CONDITION]

    assert metrics["false_accept_rate"] == 0.0
    assert metrics["false_reject_rate"] == 0.0
    assert metrics["exploit_detection_rate"] == 1.0
    assert metrics["attempted_specimens"] == 2
    assert metrics["error_count"] == 0


def test_summary_surfaces_error_rows() -> None:
    rows = [
        {
            "condition": runner.ORDINARY_REVIEW_CONDITION,
            "label": "bad",
            "score": 42.0,
            "passed_threshold": False,
            "family_detected": False,
            "structural_detected": True,
        },
        {
            "condition": runner.ORDINARY_REVIEW_CONDITION,
            "label": "good",
            "specimen_id": "missing_good",
            "error": "ordinary review import missing specimen_id: missing_good",
        },
    ]

    summary = runner.summarize(rows, 60, {runner.ORDINARY_REVIEW_CONDITION: None})
    metrics = summary["conditions"][runner.ORDINARY_REVIEW_CONDITION]

    assert metrics["num_specimens"] == 1
    assert metrics["attempted_specimens"] == 2
    assert metrics["error_count"] == 1
    assert metrics["error_specimens"] == ["missing_good"]


def test_ordinary_review_freeze_manifest_tracks_promotion_readiness(tmp_path: Path) -> None:
    run_root = tmp_path / "runs" / "run1"
    prompt_dir = run_root / "demo" / runner.ORDINARY_REVIEW_CONDITION
    prompt_dir.mkdir(parents=True)
    prompt_path = prompt_dir / "ordinary_review_prompt.txt"
    raw_path = prompt_dir / "ordinary_review.raw.json"
    eval_path = prompt_dir / "eval_results.json"
    prompt_path.write_text("review prompt\n", encoding="utf-8")
    raw_path.write_text('{"score": 25}\n', encoding="utf-8")
    eval_path.write_text('{"ok": true}\n', encoding="utf-8")

    rows = [
        {
            "condition": runner.ORDINARY_REVIEW_CONDITION,
            "label": "bad",
            "specimen_id": "demo",
            "score": 25.0,
            "passed_threshold": False,
            "family_detected": False,
            "structural_detected": True,
            "ordinary_review_source": "imported",
            "ordinary_review_model": "external-reviewer",
            "ordinary_review_import_provenance": {
                "model": "external-reviewer",
                "timestamp": "2026-06-19T00:00:00Z",
                "prompt_sha256": runner.sha256_text("review prompt\n"),
                "provider": "external",
            },
            "ordinary_review_prompt_path": str(prompt_path),
            "ordinary_review_raw_path": str(raw_path),
            "eval_results_path": str(eval_path),
            "returncode": 0,
        }
    ]
    summary = runner.summarize(rows, 60, {runner.ORDINARY_REVIEW_CONDITION: None})
    args = argparse.Namespace(
        match_source_run="benchmarks/constraint_memory/runs/source",
        ordinary_review_import_results="ordinary_review_rows.json",
        ordinary_review_contract="benchmarks/evaluator_hardening_frozen/ordinary_review_arm_contract.json",
    )

    manifest = runner.build_ordinary_review_freeze_manifest(
        rows,
        summary,
        args,
        run_root,
        ["demo"],
    )

    assert manifest["can_promote_to_frozen_suite"] is True
    assert manifest["source_run_bound"] is True
    assert manifest["promotion_blockers"] == []
    assert manifest["prompt_hashes"] == {"demo": runner.sha256_text("review prompt\n")}
    assert manifest["rows"][0]["reviewed_at"] == "2026-06-19T00:00:00Z"
    assert manifest["rows"][0]["provider_runtime"] == "external"


def test_load_ordinary_review_imports_from_mapping(tmp_path: Path) -> None:
    import_path = tmp_path / "ordinary_reviews.json"
    import_path.write_text(
        json.dumps(
            {
                "demo": {
                    "review": {
                        "accept_claim_as_stated": False,
                        "score": 25,
                        "fatal_flaw_identified": True,
                        "flaw_summary": "unsupported scope",
                        "confidence": "medium",
                    },
                    "model": "external-reviewer",
                    "timestamp": "2026-06-18T00:00:00Z",
                    "prompt_sha256": "abc123",
                    "provider": "external",
                }
            }
        ),
        encoding="utf-8",
    )

    imported = runner.load_ordinary_review_imports(import_path)

    assert set(imported) == {"demo"}
    assert imported["demo"]["review"]["score"] == 25
    assert imported["demo"]["provenance"]["specimen_id"] == "demo"
    assert imported["demo"]["provenance"]["model"] == "external-reviewer"


def test_ordinary_review_import_path_does_not_call_provider(tmp_path: Path, monkeypatch) -> None:
    specimen_dir = tmp_path / "specimen"
    specimen_dir.mkdir()
    (specimen_dir / "thesis.md").write_text("A bounded claim.\n", encoding="utf-8")
    (specimen_dir / "evidence.txt").write_text("A bounded evidence packet.\n", encoding="utf-8")
    specimen = {
        "id": "demo",
        "label": "bad",
        "rubric": "constraint_memory_benchmark",
        "_dir": specimen_dir,
    }
    contract = {
        "review_prompt_contract": {
            "required_output_schema": {
                "accept_claim_as_stated": "boolean",
                "score": "number from 0 to 100",
                "fatal_flaw_identified": "boolean",
                "flaw_summary": "string",
                "confidence": "low | medium | high",
            }
        }
    }
    imported = {
        "demo": {
            "review": {
                "accept_claim_as_stated": False,
                "score": 25,
                "fatal_flaw_identified": True,
                "flaw_summary": "unsupported scope",
                "confidence": "medium",
            },
            "provenance": {
                "model": "external-reviewer",
                "timestamp": "2026-06-18T00:00:00Z",
                "prompt_sha256": prompt_hash_for(specimen, contract),
                "provider": "external",
            },
        }
    }

    def fail_provider(*_args, **_kwargs):
        raise AssertionError("provider should not be called for imported reviews")

    monkeypatch.setattr(runner, "_call_json_model", fail_provider)
    monkeypatch.setattr(runner, "RUNS_ROOT", tmp_path / "runs")

    row = runner.run_ordinary_review_one(
        specimen,
        "gemini",
        "run1",
        60,
        contract,
        imported_reviews=imported,
        require_imported_review=True,
    )

    assert row["returncode"] == 0
    assert row["ordinary_review_source"] == "imported"
    assert row["ordinary_review_reviewed_at"] == "2026-06-18T00:00:00Z"
    assert row["ordinary_review_import_provenance"]["model"] == "external-reviewer"
    assert row["ordinary_review_import_provenance"]["provider"] == "external"
    assert row["score"] == 25.0
    assert Path(row["ordinary_review_raw_path"]).exists()


def test_ordinary_review_import_prompt_path_resolves_from_import_file(tmp_path: Path, monkeypatch) -> None:
    specimen_dir = tmp_path / "specimen"
    specimen_dir.mkdir()
    (specimen_dir / "thesis.md").write_text("A bounded claim.\n", encoding="utf-8")
    (specimen_dir / "evidence.txt").write_text("A bounded evidence packet.\n", encoding="utf-8")
    specimen = {
        "id": "demo",
        "label": "bad",
        "rubric": "constraint_memory_benchmark",
        "_dir": specimen_dir,
    }
    contract = {
        "review_prompt_contract": {
            "forbidden_context": [],
            "required_output_schema": {
                "accept_claim_as_stated": "boolean",
                "score": "number from 0 to 100",
                "fatal_flaw_identified": "boolean",
                "flaw_summary": "string",
                "confidence": "low | medium | high",
            },
        },
        "required_import_provenance": {
            "model": "non-empty model identifier",
            "timestamp": "timestamp",
            "prompt": "prompt hash",
            "provider_runtime": "provider/runtime",
        },
    }
    packet = tmp_path / "packet"
    export = runner.export_ordinary_review_prompt_packet([specimen], contract, packet)
    template = json.loads(Path(export["import_template_path"]).read_text(encoding="utf-8"))
    row = template["reviews"][0]
    row.pop("prompt_sha256")
    row["prompt_path"] = "prompts/demo.txt"
    row["model"] = "external-reviewer"
    row["timestamp"] = "2026-06-18T00:00:00Z"
    row["provider_runtime"] = "external/manual"
    row["review"] = {
        "accept_claim_as_stated": False,
        "score": 25,
        "fatal_flaw_identified": True,
        "flaw_summary": "unsupported scope",
        "confidence": "medium",
    }
    import_path = packet / "ordinary_review_rows.json"
    import_path.write_text(json.dumps({"reviews": [row]}, indent=2) + "\n", encoding="utf-8")

    imported = runner.load_ordinary_review_imports(import_path)

    def fail_provider(*_args, **_kwargs):
        raise AssertionError("provider should not be called for imported reviews")

    monkeypatch.setattr(runner, "_call_json_model", fail_provider)
    monkeypatch.setattr(runner, "RUNS_ROOT", tmp_path / "runs")

    result = runner.run_ordinary_review_one(
        specimen,
        "gemini",
        "run1",
        60,
        contract,
        imported_reviews=imported,
        require_imported_review=True,
    )

    assert result["returncode"] == 0
    assert result["ordinary_review_source"] == "imported"
    assert result["ordinary_review_import_provenance"]["prompt_path"] == "prompts/demo.txt"


def test_validate_ordinary_review_import_packet_without_benchmark_run(tmp_path: Path, monkeypatch) -> None:
    specimen_dir = tmp_path / "specimen"
    specimen_dir.mkdir()
    (specimen_dir / "thesis.md").write_text("A bounded claim.\n", encoding="utf-8")
    (specimen_dir / "evidence.txt").write_text("A bounded evidence packet.\n", encoding="utf-8")
    specimen = {
        "id": "demo",
        "label": "bad",
        "rubric": "constraint_memory_benchmark",
        "_dir": specimen_dir,
    }
    contract = {
        "review_prompt_contract": {
            "forbidden_context": [],
            "required_output_schema": {
                "accept_claim_as_stated": "boolean",
                "score": "number from 0 to 100",
                "fatal_flaw_identified": "boolean",
                "flaw_summary": "string",
                "confidence": "low | medium | high",
            },
        },
        "required_import_provenance": {
            "model": "non-empty model identifier",
            "timestamp": "timestamp",
            "prompt": "prompt hash",
            "provider_runtime": "provider/runtime",
        },
    }
    packet = tmp_path / "packet"
    export = runner.export_ordinary_review_prompt_packet([specimen], contract, packet)
    template = json.loads(Path(export["import_template_path"]).read_text(encoding="utf-8"))
    row = template["reviews"][0]
    row["model"] = "external-reviewer"
    row["timestamp"] = "2026-06-18T00:00:00Z"
    row["provider_runtime"] = "external/manual"
    row["review"] = {
        "accept_claim_as_stated": False,
        "score": 25,
        "fatal_flaw_identified": True,
        "flaw_summary": "unsupported scope",
        "confidence": "medium",
    }
    import_path = packet / "ordinary_review_rows.json"
    import_path.write_text(json.dumps({"reviews": [row]}, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(runner, "RUNS_ROOT", tmp_path / "runs")

    imported = runner.load_ordinary_review_imports(import_path)
    payload = runner.validate_ordinary_review_import_packet([specimen], contract, imported)

    assert payload["ok"] is True
    assert payload["selected_specimen_count"] == 1
    assert payload["validated_row_count"] == 1
    assert payload["rows"][0]["specimen_id"] == "demo"
    assert payload["rows"][0]["prompt_sha256"] == row["prompt_sha256"]
    assert not (tmp_path / "runs").exists()


def test_validate_ordinary_review_import_packet_fails_on_missing_selected_row(tmp_path: Path) -> None:
    specimen_dir = tmp_path / "specimen"
    specimen_dir.mkdir()
    (specimen_dir / "thesis.md").write_text("A bounded claim.\n", encoding="utf-8")
    (specimen_dir / "evidence.txt").write_text("A bounded evidence packet.\n", encoding="utf-8")
    specimen = {
        "id": "demo",
        "label": "bad",
        "rubric": "constraint_memory_benchmark",
        "_dir": specimen_dir,
    }
    contract = {
        "review_prompt_contract": {
            "required_output_schema": {
                "accept_claim_as_stated": "boolean",
                "score": "number from 0 to 100",
                "fatal_flaw_identified": "boolean",
                "flaw_summary": "string",
                "confidence": "low | medium | high",
            }
        }
    }

    with pytest.raises(SystemExit, match="missing selected specimen ids"):
        runner.validate_ordinary_review_import_packet([specimen], contract, {})


def test_ordinary_review_reject_decision_controls_pass_status(tmp_path: Path, monkeypatch) -> None:
    specimen_dir = tmp_path / "specimen"
    specimen_dir.mkdir()
    (specimen_dir / "thesis.md").write_text("A claim with partial merit.\n", encoding="utf-8")
    (specimen_dir / "evidence.txt").write_text("Some evidence, but not enough.\n", encoding="utf-8")
    specimen = {
        "id": "demo",
        "label": "bad",
        "rubric": "constraint_memory_benchmark",
        "_dir": specimen_dir,
    }
    contract = {
        "review_prompt_contract": {
            "required_output_schema": {
                "accept_claim_as_stated": "boolean",
                "score": "number from 0 to 100",
                "fatal_flaw_identified": "boolean",
                "flaw_summary": "string",
                "confidence": "low | medium | high",
            }
        }
    }
    imported = {
        "demo": {
            "review": {
                "accept_claim_as_stated": False,
                "score": 95,
                "fatal_flaw_identified": True,
                "flaw_summary": "scope is not supported as stated",
                "confidence": "high",
            },
            "provenance": {
                "model": "external-reviewer",
                "timestamp": "2026-06-18T00:00:00Z",
                "prompt_sha256": prompt_hash_for(specimen, contract),
                "provider": "external",
            },
        }
    }

    monkeypatch.setattr(runner, "RUNS_ROOT", tmp_path / "runs")

    row = runner.run_ordinary_review_one(
        specimen,
        "gemini",
        "run1",
        60,
        contract,
        imported_reviews=imported,
        require_imported_review=True,
    )

    assert row["score"] == 95.0
    assert row["accept_claim_as_stated"] is False
    assert row["passed_threshold"] is False


def test_ordinary_review_import_rejects_wrong_prompt_hash(tmp_path: Path, monkeypatch) -> None:
    specimen_dir = tmp_path / "specimen"
    specimen_dir.mkdir()
    (specimen_dir / "thesis.md").write_text("A claim.\n", encoding="utf-8")
    (specimen_dir / "evidence.txt").write_text("Evidence.\n", encoding="utf-8")
    specimen = {
        "id": "demo",
        "label": "bad",
        "rubric": "constraint_memory_benchmark",
        "_dir": specimen_dir,
    }
    contract = {
        "review_prompt_contract": {
            "required_output_schema": {
                "accept_claim_as_stated": "boolean",
                "score": "number from 0 to 100",
                "fatal_flaw_identified": "boolean",
                "flaw_summary": "string",
                "confidence": "low | medium | high",
            }
        }
    }
    imported = {
        "demo": {
            "review": {
                "accept_claim_as_stated": False,
                "score": 25,
                "fatal_flaw_identified": True,
                "flaw_summary": "unsupported scope",
                "confidence": "medium",
            },
            "provenance": {
                "model": "external-reviewer",
                "timestamp": "2026-06-18T00:00:00Z",
                "prompt_sha256": "wrong-hash",
                "provider": "external",
            },
        }
    }

    def fail_provider(*_args, **_kwargs):
        raise AssertionError("provider fallback must not run when imported prompt hash is wrong")

    monkeypatch.setattr(runner, "_call_json_model", fail_provider)
    monkeypatch.setattr(runner, "RUNS_ROOT", tmp_path / "runs")

    row = runner.run_ordinary_review_one(
        specimen,
        "gemini",
        "run1",
        60,
        contract,
        imported_reviews=imported,
        require_imported_review=True,
    )

    assert row["returncode"] == 1
    assert row["ordinary_review_source"] == "imported"
    assert "prompt hash mismatch" in row["error"]


def test_ordinary_review_import_requires_provenance(tmp_path: Path) -> None:
    import_path = tmp_path / "ordinary_reviews.json"
    import_path.write_text(
        json.dumps(
            [
                {
                    "specimen_id": "demo",
                    "review": {
                        "accept_claim_as_stated": False,
                        "score": 25,
                        "fatal_flaw_identified": True,
                        "flaw_summary": "unsupported scope",
                        "confidence": "medium",
                    },
                    "model": "external-reviewer",
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="missing provenance"):
        runner.load_ordinary_review_imports(import_path)


def test_ordinary_review_import_required_fails_closed(tmp_path: Path, monkeypatch) -> None:
    specimen_dir = tmp_path / "specimen"
    specimen_dir.mkdir()
    (specimen_dir / "thesis.md").write_text("A claim.\n", encoding="utf-8")
    (specimen_dir / "evidence.txt").write_text("Evidence.\n", encoding="utf-8")
    specimen = {
        "id": "missing",
        "label": "bad",
        "rubric": "constraint_memory_benchmark",
        "_dir": specimen_dir,
    }
    contract = {
        "review_prompt_contract": {
            "required_output_schema": {
                "accept_claim_as_stated": "boolean",
                "score": "number from 0 to 100",
                "fatal_flaw_identified": "boolean",
                "flaw_summary": "string",
                "confidence": "low | medium | high",
            }
        }
    }

    def fail_provider(*_args, **_kwargs):
        raise AssertionError("provider fallback must not run when import is required")

    monkeypatch.setattr(runner, "_call_json_model", fail_provider)
    monkeypatch.setattr(runner, "RUNS_ROOT", tmp_path / "runs")

    row = runner.run_ordinary_review_one(
        specimen,
        "gemini",
        "run1",
        60,
        contract,
        imported_reviews={},
        require_imported_review=True,
    )

    assert row["returncode"] == 1
    assert row["ordinary_review_source"] == "missing_import"
    assert "missing specimen_id" in row["error"]


def test_runner_main_exits_nonzero_when_rows_error(tmp_path: Path, monkeypatch) -> None:
    specimen_dir = tmp_path / "specimen"
    specimen_dir.mkdir()
    (specimen_dir / "thesis.md").write_text("A claim.\n", encoding="utf-8")
    (specimen_dir / "evidence.txt").write_text("Evidence.\n", encoding="utf-8")
    specimen = {
        "id": "demo",
        "label": "bad",
        "rubric": "constraint_memory_benchmark",
        "_dir": specimen_dir,
    }

    monkeypatch.setattr(runner, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(runner, "load_specimens", lambda *args, **kwargs: [specimen])

    def error_row(*_args, **_kwargs):
        return {
            "condition": runner.ORDINARY_REVIEW_CONDITION,
            "label": "bad",
            "specimen_id": "demo",
            "returncode": 1,
            "error": "ordinary review failed in fixture",
        }

    monkeypatch.setattr(runner, "run_ordinary_review_one", error_row)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_benchmark.py",
            "--conditions",
            runner.ORDINARY_REVIEW_CONDITION,
            "--jobs",
            "1",
        ],
    )

    with pytest.raises(SystemExit, match="benchmark failed: 1 row\\(s\\) errored"):
        runner.main()

    run_roots = list((tmp_path / "runs").iterdir())
    assert len(run_roots) == 1
    summary = json.loads((run_roots[0] / "metrics_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_roots[0] / "ordinary_review_freeze_manifest.json").read_text(encoding="utf-8"))
    metrics = summary["conditions"][runner.ORDINARY_REVIEW_CONDITION]
    assert metrics["attempted_specimens"] == 1
    assert metrics["error_count"] == 1
    assert metrics["error_specimens"] == ["demo"]
    assert manifest["can_promote_to_frozen_suite"] is False
    assert manifest["error_count"] == 1
    assert "missing --match-source-run binding" in manifest["promotion_blockers"]
