from pathlib import Path

from src.ztare.synthesis.synthesize import (
    aggregated_corpus_digest,
    build_multi_project_history_summary,
    cached_multi_project_ledger_matches_context,
    multi_project_scoped_paths,
)


def test_multi_project_scoped_paths_are_fully_scoped() -> None:
    base = Path("/tmp/example_project")
    paths = multi_project_scoped_paths(base, "research_note", ["alpha_project", "beta_project"])
    assert "ledger.multi_project.research_note." in str(paths["ledger"])
    assert "history_summary.multi_project.research_note." in str(paths["history_summary"])
    assert "Report.multi_project.research_note." in str(paths["final_report"])


def test_build_multi_project_history_summary_merges_project_payloads() -> None:
    payloads = [
        {
            "project": "alpha_project",
            "domain": "alpha",
            "history_summary": {
                "summary_scope": "Alpha scope",
                "cross_run_patterns": ["Pattern A", "Pattern B"],
                "recurring_survivors": ["Survivor A"],
                "recurring_failures": ["Failure A"],
                "major_pivots": ["Pivot A"],
            },
        },
        {
            "project": "beta_project",
            "domain": "beta",
            "history_summary": {
                "summary_scope": "Beta scope",
                "cross_run_patterns": ["Pattern B", "Pattern C"],
                "recurring_survivors": ["Survivor B"],
                "recurring_failures": ["Failure B"],
                "major_pivots": ["Pivot B"],
            },
        },
    ]
    merged = build_multi_project_history_summary(payloads)
    assert merged["_meta"]["project_count"] == 2
    assert merged["_meta"]["project_names"] == ["alpha_project", "beta_project"]
    assert merged["cross_project_patterns"] == ["Pattern A", "Pattern B", "Pattern C"]
    assert len(merged["projects"]) == 2


def test_cached_multi_project_ledger_matches_context_checks_digest() -> None:
    aggregated = {"projects": [{"project": "alpha_project"}, {"project": "beta_project"}]}
    context = {
        "renderer_type": "research_note",
        "multi_project_names": ["alpha_project", "beta_project"],
        "aggregated_corpus": aggregated,
        "ledger_prompt_hash": "prompt-hash-a",
    }
    cached = {
        "_meta": {
            "renderer_type": "research_note",
            "project_names": ["alpha_project", "beta_project"],
            "aggregated_corpus_digest": aggregated_corpus_digest(aggregated),
            "prompt_hash": "prompt-hash-a",
        }
    }
    assert cached_multi_project_ledger_matches_context(cached, context) is True

    changed = dict(context)
    changed["aggregated_corpus"] = {"projects": [{"project": "alpha_project"}]}
    assert cached_multi_project_ledger_matches_context(cached, changed) is False

    prompt_changed = dict(context)
    prompt_changed["ledger_prompt_hash"] = "prompt-hash-b"
    assert cached_multi_project_ledger_matches_context(cached, prompt_changed) is False


def main() -> None:
    test_multi_project_scoped_paths_are_fully_scoped()
    test_build_multi_project_history_summary_merges_project_payloads()
    test_cached_multi_project_ledger_matches_context_checks_digest()
    print("synthesize_multi_project_fixture_regression: PASS")


if __name__ == "__main__":
    main()
