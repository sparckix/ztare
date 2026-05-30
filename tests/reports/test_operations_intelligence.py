from __future__ import annotations

import json
from pathlib import Path

from src.ztare.reports.operations_intelligence import build, parse_markdown_table


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_parse_markdown_table_skips_separator(tmp_path: Path) -> None:
    path = tmp_path / "table.md"
    write(path, "| A | B |\n|---|---|\n| x | y |\n")
    assert parse_markdown_table(path) == [["A", "B"], ["x", "y"]]


def test_build_extracts_focus_track_intelligence_and_source_health(tmp_path: Path) -> None:
    repo = tmp_path
    write(repo / "projects/ns_millennium_hunt/project_charter.md", "# NS Hunt\n")
    write(
        repo / "projects/ns_millennium_hunt/workspace/ns_residual_manifest.md",
        "# Residual Manifest\n\nLatest route: C7 fresh-radius invoice.\n",
    )
    write(
        repo / "analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md",
        "\n".join(
            [
                "| Date | Substrate / lane | Evidence pointer | GP-233 bottleneck named | Decision changed | Verdict |",
                "|---|---|---|---|---|---|",
                "| 2026-05-20 | NS Track B | `projects/ns_millennium_hunt/workspace/ns_residual_manifest.md` | `fresh_radius_invoice` | Changed next lever | positive |",
            ]
        ),
    )
    aggregate = {
        "contract_id": "tick999-ns-c7",
        "contract_question": "NS C7 fresh radius route",
        "aggregate": {"p_success": 0.2},
        "allocation_recommendation": {"action": "ask_another_independent_agent"},
    }
    write(repo / "analytics/public/forecast_pool/aggregates/tick999-ns-c7.json", json.dumps(aggregate))
    write(repo / "analytics/public/forecast_pool/contracts/tick999-ns-c7.json", "{}")
    write(
        repo / "analytics/public/queries/trajectory/trajectory_curves.json",
        json.dumps(
            {
                "curves": {
                    "confound_a_code_activity_density": {"2026-05-13": 10, "2026-05-20": 40},
                    "confound_b_total_artifact_creation_per_week": {"2026-05-13": 20, "2026-05-20": 80},
                    "insight_a_f_row_creates_per_week": {"2026-05-13": 3, "2026-05-20": 4},
                    "insight_b_f_row_closures_per_week": {"2026-05-13": 1, "2026-05-20": 1},
                    "insight_e_verified_axioms_added_per_week": {"2026-05-13": 1, "2026-05-20": 1},
                }
            }
        ),
    )
    write(
        repo / "research_areas/EXPERIMENT_TRACK_RECORD.md",
        "\n".join(
            [
                "| Date | Track | Status | Finding |",
                "|---|---|---|---|",
                "| 2026-05-20 | ns_millennium_hunt | active | result: C7 route remains blocked |",
            ]
        ),
    )
    write(
        repo / "analytics/public/ledgers/catch/catch_ledger.jsonl",
        json.dumps({"catch_id": "C-1", "category": "test", "status": "ratified", "load_bearing": True}) + "\n",
    )
    write(
        repo / "analytics/public/action_intelligence/state/source_health.json",
        json.dumps(
            {
                "counts": {"blocking": 1},
                "issues": [
                    {
                        "severity": "blocking",
                        "issue_type": "missing_decision_use",
                        "blocking_rule": "repair decision-use emitter",
                        "evidence_refs": ["analytics/public/forecast_pool/decision_use/decision_use_ledger.jsonl"],
                    }
                ],
            }
        ),
    )
    payload = build(repo, freshness_days=30, max_projects=10)
    assert payload["schema"] == "ztare-intelligence-surface-v1"
    assert payload["headline"]["active_focus_tracks"] == 1
    assert payload["headline"]["experiment_rows"] == 1
    assert payload["headline"]["source_health_blockers"] == 1
    assert payload["headline"]["forecast_decision_use_rate"] == 0.0
    track = next(row for row in payload["focus_tracks"]["rows"] if row["track_id"] == "ns_millennium_hunt")
    assert track["linkage_quality"] == "strong"
    assert track["signals"]["gp233_refs"] == 1
    assert track["signals"]["forecast_refs"] == 1
    assert track["signals"]["experiment_refs"] == 1
    assert payload["attention"][0]["kind"] == "source_health"
    assert payload["learning_candidates"][0]["observer_only"] is True
    assert payload["forecast_market"]["decision_use_gap"] == 1
    assert payload["activity_yield"]["verdict"] == "activity_outpacing_yield"
    assert payload["source_map"]["gap_count"] >= 1
    assert payload["source_improvement_backlog"]
    assert payload["etl_manifest"]["load"]["writes_official_state"] is False
    assert payload["etl_manifest"]["validate"]["issue_count"] >= 1
    assert payload["source_readiness"]["schema"] == "ztare-source-readiness-v1"
    assert payload["source_readiness"]["summary"]["blocked"] >= 1
    assert payload["executive_brief"]["schema"] == "ztare-intelligence-executive-brief-v1"
    assert payload["executive_brief"]["operating_status"] == "blocked_for_allocation"
    assert "forecast-market allocation claims" in " ".join(payload["executive_brief"]["do_not_use_for"])
    areas = payload["research_ops_metric_areas"]
    assert areas["schema"] == "ztare-research-ops-metric-areas-v1"
    assert {area["area_id"] for area in areas["areas"]} >= {"information_yield", "decision_use", "recursive_learning"}
    assert "implemented_source_blocked" in areas["status_counts"]
