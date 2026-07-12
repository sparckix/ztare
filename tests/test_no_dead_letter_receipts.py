"""No-dead-letter-receipts invariant tests.

Structural test (real repo + arc3_ls20_gov): asserts the current dead-letter
set is empty or fully exempted.

Planted unit tests: verify the detector fires/quiets on synthetic fixtures.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from ztare.orchestrator.trace_auditor import (
    _DEAD_LETTER_EXEMPTIONS,
    _build_src_index,
    check_dead_letter_receipts,
)

SRC_ZTARE = REPO / "src" / "ztare"
REAL_PROJECT = REPO / "projects" / "arc3_ls20_gov"

# ── Known dead-letter debt (honest freeze; ratchet — remove entries when fixed) ──
# Each entry is a workspace filename (or fnmatch-style glob for numbered families)
# that is currently written but whose static filename string appears in ≤1 src/ztare
# module (the writer).  The test fails if NEW dead letters appear beyond this set.
# Remove entries once a reader lands (or the file is retired).
_KNOWN_DEBT: frozenset[str] = frozenset({
    # TODO: candidate_pool.jsonl — written+path-returned by worldmodel/candidate_pool.py;
    # machinery_contradictions.py receives it as a path argument (not a quoted literal),
    # so the index sees only 1 module.  Real reader exists but not detectable statically.
    "candidate_pool.jsonl",
    # TODO: harness_weakness_receipts.jsonl — written by common/harness_weakness.py;
    # callers read latest_harness_weakness.json instead.  The .jsonl ledger has no static reader.
    "harness_weakness_receipts.jsonl",
    # TODO: interface_inconsistency_receipts.jsonl — same pattern as harness_weakness_receipts.
    "interface_inconsistency_receipts.jsonl",
    # TODO: latest_frontier_scope.json — not referenced by any static src string.
    "latest_frontier_scope.json",
    # TODO: latest_interface_inconsistency.json — only referenced in common/interface_inconsistency.py
    # (the LATEST constant definition, which is a writer-side constant, not a reader import).
    "latest_interface_inconsistency.json",
    # TODO: latest_level_boundary_seed.json — not referenced by any static src string.
    "latest_level_boundary_seed.json",
    # TODO: latest_mutation_validation.json — only referenced in validator/autoresearch_loop.py
    # as a path string passed to an external command; the file's writer is not in src/ztare index.
    "latest_mutation_validation.json",
    # TODO: latest_replay_diagnostics_after_abduce.json — 1 static reference in
    # worldmodel/leaf_workbench.py (diagnostics_ref string); writer not separately indexed.
    "latest_replay_diagnostics_after_abduce.json",
    # TODO: latest_replay_residual_repair_sync.json — not referenced by any static src string.
    "latest_replay_residual_repair_sync.json",
    # TODO: ls20_residual_classes_receipt.json — not referenced by any static src string.
    "ls20_residual_classes_receipt.json",
    # TODO: strategy_experiment_probe_rows.jsonl — appended by worldmodel/experiment_executor.py;
    # no src/ztare module reads it back yet.
    "strategy_experiment_probe_rows.jsonl",
})

# The mutator_briefing_iter_*_projection_receipt.json family is written via f-string
# (mutator_briefing.py line: f"mutator_briefing_iter_{ctx.iter_index:03d}_projection_receipt.json")
# so no static filename literal exists in src; the index returns 0 modules for each.
# TODO: Add a static reader (e.g. briefing projection auditor) that reads these by pattern.
_KNOWN_DEBT_PATTERN_PREFIX = "mutator_briefing_iter_"
_KNOWN_DEBT_PATTERN_SUFFIX = "_projection_receipt.json"


def _in_known_debt(name: str) -> bool:
    if name in _KNOWN_DEBT:
        return True
    # Numbered mutator briefing projection receipts matched by stem pattern
    if name.startswith(_KNOWN_DEBT_PATTERN_PREFIX) and name.endswith(_KNOWN_DEBT_PATTERN_SUFFIX):
        return True
    return False


# ── helpers ───────────────────────────────────────────────────────────────────

def _ws(tmp_path: Path) -> Path:
    ws = tmp_path / "proj" / "workspace"
    ws.mkdir(parents=True)
    return ws


def _touch(path: Path, content: str = '{"x":1}\n') -> None:
    path.write_text(content, encoding="utf-8")


# ── planted unit tests ────────────────────────────────────────────────────────

def test_dead_letter_fires_on_unread_file(tmp_path):
    """A .jsonl written by exactly one fake module → anomaly."""
    ws = _ws(tmp_path)
    src = tmp_path / "fake_src" / "ztare"
    writer = src / "organ" / "writer.py"
    writer.parent.mkdir(parents=True)
    writer.write_text(
        'ledger = workspace / "orphan_receipts.jsonl"\n'
        'with ledger.open("a") as fh: fh.write(json.dumps(row))\n',
        encoding="utf-8",
    )
    _touch(ws / "orphan_receipts.jsonl")

    state: dict = {}
    f = check_dead_letter_receipts(ws, state, src)
    assert f["verdict"] == "anomaly"
    assert f["check_id"] == "dead_letter_receipts"
    names = [d["file"] for d in f["witness"]["dead_letters"]]
    assert "orphan_receipts.jsonl" in names


def test_dead_letter_quiet_when_reader_exists(tmp_path):
    """A .jsonl referenced by writer + reader module → ok."""
    ws = _ws(tmp_path)
    src = tmp_path / "fake_src" / "ztare"
    writer = src / "organ" / "writer.py"
    reader = src / "organ" / "reader.py"
    writer.parent.mkdir(parents=True)
    writer.write_text('open(workspace / "shared_receipts.jsonl", "a")\n', encoding="utf-8")
    reader.write_text('rows = jsonl_read(ws / "shared_receipts.jsonl")\n', encoding="utf-8")
    _touch(ws / "shared_receipts.jsonl")

    state: dict = {}
    f = check_dead_letter_receipts(ws, state, src)
    assert f["verdict"] == "ok"


def test_dead_letter_quiet_on_exempted_name(tmp_path):
    """Exempted filenames never fire even if unread."""
    ws = _ws(tmp_path)
    src = tmp_path / "fake_src" / "ztare"
    src.mkdir(parents=True)
    # Write an exempted file (trace_auditor_state.json) with no src module referencing it
    _touch(ws / "trace_auditor_state.json", '{"audit_count":1}\n')

    state: dict = {}
    f = check_dead_letter_receipts(ws, state, src)
    assert f["verdict"] == "ok"


def test_dead_letter_quiet_on_empty_file(tmp_path):
    """Empty files are not flagged (never actually written)."""
    ws = _ws(tmp_path)
    src = tmp_path / "fake_src" / "ztare"
    src.mkdir(parents=True)
    (ws / "empty_receipts.jsonl").write_text("", encoding="utf-8")

    state: dict = {}
    f = check_dead_letter_receipts(ws, state, src)
    assert f["verdict"] == "ok"


def test_dead_letter_quiet_on_pre_materialization_backup(tmp_path):
    """_pre_materialization_ backup files are exempt."""
    ws = _ws(tmp_path)
    src = tmp_path / "fake_src" / "ztare"
    src.mkdir(parents=True)
    _touch(ws / "candidate_pre_materialization_backup.jsonl")

    state: dict = {}
    f = check_dead_letter_receipts(ws, state, src)
    assert f["verdict"] == "ok"


def test_src_index_returns_consistent_results(tmp_path):
    """Second call with same state dict returns the same index content."""
    src = tmp_path / "fake_src" / "ztare"
    py = src / "mod.py"
    py.parent.mkdir(parents=True)
    py.write_text('LEDGER = "foo_receipts.jsonl"\n', encoding="utf-8")

    state: dict = {}
    idx1 = _build_src_index(src, state)
    # A second call with the same state should return the cached value
    idx2 = _build_src_index(src, state)
    assert idx1 == idx2
    assert "foo_receipts.jsonl" in idx1


# ── structural test against real repo + real project ─────────────────────────

@pytest.mark.skipif(
    not REAL_PROJECT.exists(),
    reason="projects/arc3_ls20_gov not present",
)
def test_real_project_dead_letters_within_known_debt():
    """No NEW dead letters beyond _KNOWN_DEBT; fails loudly if a new unread file appears.

    This is a ratchet: when a file in _KNOWN_DEBT gets a reader, remove it from
    _KNOWN_DEBT so the test enforces the fix.  Never add new entries without a TODO.
    """
    ws = REAL_PROJECT / "workspace"
    state: dict = {}
    f = check_dead_letter_receipts(ws, state, SRC_ZTARE)

    if f["verdict"] == "ok":
        return  # all clear

    actual_dead = frozenset(d["file"] for d in f["witness"]["dead_letters"])
    unexpected = frozenset(
        name for name in actual_dead
        if not _in_known_debt(name) and name not in _DEAD_LETTER_EXEMPTIONS
    )
    assert not unexpected, (
        f"NEW dead-letter receipt(s) found — add a reader or add to _KNOWN_DEBT with a TODO: "
        f"{sorted(unexpected)}"
    )
