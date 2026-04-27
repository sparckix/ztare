"""GP-131 work-discovery prototype — smoke tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

from src.ztare.orchestration.work_discovery import (
    Candidate,
    discover_damage_signals,
    discover_open_todos,
    format_candidate_for_inbox,
)


def test_discover_open_todos_against_live_seams():
    """Live repo should have at least one open TODO in mission seams
    (GP-128 has several). This guards against the scan regressing to 0."""
    candidates = discover_open_todos(max_per_source=20)
    assert len(candidates) >= 1
    assert all(c.source == "TODO-scan" for c in candidates)
    assert all(c.age_days is not None for c in candidates)


def test_discover_open_todos_from_synthetic_seam(tmp_path: Path):
    seam = tmp_path / "GP-999_test_seam.md"
    seam.write_text(
        "# GP-999\n\n"
        "Some prose.\n\n"
        "## Open items\n\n"
        "- [ ] First open TODO — investigate X\n"
        "- [x] Done item (should be skipped)\n"
        "- [ ] Second open TODO — revisit Y\n",
        encoding="utf-8",
    )
    cands = discover_open_todos(root=tmp_path, max_per_source=10)
    assert len(cands) == 2
    intents = [c.intent for c in cands]
    assert any("First open TODO" in i for i in intents)
    assert any("Second open TODO" in i for i in intents)
    assert not any("Done item" in i for i in intents)


def test_discover_open_todos_skips_short_noise(tmp_path: Path):
    seam = tmp_path / "GP-998_noise.md"
    seam.write_text(
        "- [ ] x\n"                    # too short
        "- [ ] longer valid TODO here\n",
        encoding="utf-8",
    )
    cands = discover_open_todos(root=tmp_path, max_per_source=10)
    assert len(cands) == 1
    assert "longer valid" in cands[0].intent


def test_damage_scan_empty_is_not_an_error():
    # Even if the damage dir has nothing, the function must return []
    # not raise.
    result = discover_damage_signals(max_per_source=5)
    assert isinstance(result, list)


def test_format_candidate_for_inbox_renders_all_fields():
    c = Candidate(
        source="TODO-scan",
        intent="test intent",
        origin_path=None,
        scarcity_signal="test scarcity",
        raw_text="raw excerpt content",
        age_days=1.5,
        severity="info",
        metadata={"seam": "GP-999.md"},
    )
    rendered = format_candidate_for_inbox(c)
    assert "TODO-scan" in rendered
    assert "test intent" in rendered
    assert "1.50" in rendered or "1.5" in rendered
    assert "raw excerpt" in rendered
